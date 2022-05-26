"""Pipeline functions."""

import json
from pathlib import Path
import re

from numpy import typing as npt
import numpy as np
import pandas as pd
from propshop import get_prop
from propshop.library import Mat, Prop
from scipy.constants import convert_temperature
from scipy.stats import linregress

from config.columns import Columns as C  # noqa: N817
from models import Project
from utils import get_project

# * -------------------------------------------------------------------------------- * #
# * MAIN

pd.options.mode.string_storage = "pyarrow"

UNITS_INDEX = "units"


def pipeline(proj: Project):

    dfs: list[pd.DataFrame] = []

    # Reduce data from CSV's of runs within trials, to single df w/ trials as records
    for trial in proj.trials:
        if trial.monotonic:
            df = (
                get_steady_state(trial.path, proj)  # Reduce many CSV's to one df
                .pipe(rename_columns, proj)  # Pull units out of columns for cleaner ref
                .pipe(fit, proj)
                .assign(**json.loads(trial.json()))  # Assign trial metadata
            )
            dfs.append(df)
    # TODO: Transform superscript/subscript in column names AND units. Prioritize renaming to pretty names. Also check on units

    # Post-processing
    (
        pd.concat(dfs)
        .pipe(set_units_row, proj)
        .pipe(transform_units_for_originlab)
        .pipe(prettify, proj)
        .to_csv(proj.dirs.results_file, index_label=proj.get_index().name)
    )


# * -------------------------------------------------------------------------------- * #
# * PER-TRIAL STAGES


def get_steady_state(path: Path, proj: Project) -> pd.DataFrame:
    """Get steady-state values for the trial."""

    files: list[Path] = sorted(path.glob("*.csv"))
    run_names: list[str] = [file.stem for file in files]
    runs: list[pd.DataFrame] = []
    for file in files:
        run = get_run(file, proj)
        if len(run) < proj.params.records_to_average:
            raise ValueError(
                f"There are not enough records in {file.name} to compute steady-state."
            )
        runs.append(run)

    runs_steady_state: list[pd.Series] = [
        df.iloc[-proj.params.records_to_average :, :].mean() for df in runs
    ]
    return pd.DataFrame(runs_steady_state, index=run_names).rename_axis(
        proj.get_index().name, axis="index"
    )


# * -------------------------------------------------------------------------------- * #
# * PRIMARY STAGES


def rename_columns(df: pd.DataFrame, proj: Project) -> pd.DataFrame:
    """Remove units from column labels."""

    return df.rename(
        {col.source: name for name, col in proj.cols.items() if not col.index},
        axis="columns",
    )


def fit(df: pd.DataFrame, proj: Project) -> pd.DataFrame:
    """Fit the data assuming one-dimensional, steady-state conduction."""

    # Constants
    cm_p_m = 100  # (cm/m) Conversion factor
    cm2_p_m2 = cm_p_m**2  # ((cm/m)^2) Conversion factor
    diameter = 0.009525 * cm_p_m  # (cm) 3/8"
    cross_sectional_area = np.pi / 4 * diameter**2  # (cm^2)

    # Column names
    temps_to_regress = [C.T_1, C.T_2, C.T_3, C.T_4, C.T_5]
    water_temps = [C.T_w1, C.T_w2, C.T_w3]

    # Computed values
    temperature_cols: pd.DataFrame = df.loc[:, temps_to_regress]
    water_temp_cols: pd.DataFrame = df.loc[:, water_temps]

    # Main pipeline
    df = df.pipe(
        linregress_apply,
        proj,
        temperature_cols,
        repeats_per_pair=proj.params.records_to_average,
        result_cols=[
            C.dT_dx,
            C.TLfit,
            C.rvalue,
            C.pvalue,
            C.stderr,
            C.intercept_stderr,
        ],
    ).assign(
        **{
            C.dT_dx_err: lambda df: (4 * df["stderr"]).abs(),
            C.k: get_prop(
                Mat.COPPER,
                Prop.THERMAL_CONDUCTIVITY,
                convert_temperature(temperature_cols.mean(axis="columns"), "C", "K"),
            ),
            # no negative due to reversed x-coordinate
            C.q: lambda df: df[C.k] * df[C.dT_dx] / cm2_p_m2,
            C.q_err: lambda df: (df[C.k] * df[C.dT_dx_err]).abs() / cm2_p_m2,
            C.Q: lambda df: df[C.q] * cross_sectional_area,
            C.DT: lambda df: (df[C.TLfit] - water_temp_cols.mean().mean()),
            C.DT_err: lambda df: (4 * df["intercept_stderr"]).abs(),
        }
    )

    if proj.fit.do_plot:
        df.apply(plot, args=(proj, temps_to_regress), axis="columns")

    return df


# * -------------------------------------------------------------------------------- * #
# * FINISHING STAGES


def set_units_row(df: pd.DataFrame, proj: Project) -> pd.DataFrame:
    """Move units out of column labels and into a row just below the column labels."""
    units_row = pd.DataFrame(
        {
            name: pd.Series(col.units, index=[UNITS_INDEX])
            for name, col in proj.cols.items()
            if not col.index
        }
    )

    return pd.concat([units_row, df])


def transform_units_for_originlab(df: pd.DataFrame) -> pd.DataFrame:
    units = df.loc[UNITS_INDEX, :].replace(re.compile(r"\^(\d)"), r"\+(\1)")
    df.loc[UNITS_INDEX, :] = units
    return df


def prettify(df: pd.DataFrame, proj: Project) -> pd.DataFrame:
    return df.rename(
        {name: col.pretty_name for name, col in proj.cols.items()}, axis="columns"
    )


# * -------------------------------------------------------------------------------- * #
# * HELPER FUNCTIONS


def get_run(file: Path, proj: Project) -> pd.DataFrame:
    source_cols = {name: col for name, col in proj.cols.items() if col.source}
    dtypes = {name: col.dtype for name, col in source_cols.items()}
    return pd.read_csv(
        file,
        usecols=[col.source for col in source_cols.values()],  # pyright: ignore
        index_col=proj.get_index().source,
        dtype=dtypes,
    )


def linregress_apply(
    df: pd.DataFrame,
    proj: Project,
    repeats_per_pair: int,
    temperature_cols: pd.DataFrame,
    result_cols: list[str],
) -> pd.DataFrame:
    return pd.concat(
        axis="columns",
        objs=[
            df,
            temperature_cols.apply(
                axis="columns",
                func=lambda ser: linregress_series(
                    x=proj.fit.thermocouple_pos,
                    series_of_y=ser,
                    repeats_per_pair=repeats_per_pair,
                    regression_stats=result_cols,
                ),
            ),
        ],
    )


def linregress_series(
    x: npt.ArrayLike,
    series_of_y: pd.Series,
    repeats_per_pair: int,
    regression_stats: list[str],
) -> pd.Series:
    """Perform linear regression of a series of y's with respect to given x's.

    Given x-values and a series of y-values, return a series of linear regression
    statistics.
    """

    # Assume the ordered pairs are repeated with zero standard deviation in x and y
    x = np.repeat(x, repeats_per_pair)
    y = np.repeat(series_of_y, repeats_per_pair)
    r = linregress(x, y)

    # Unpacking would drop r.intercept_stderr, so we have to do it this way.
    # See "Notes" section of SciPy documentation for more info.
    return pd.Series(
        [r.slope, r.intercept, r.rvalue, r.pvalue, r.stderr, r.intercept_stderr],
        index=regression_stats,
    )


def plot(ser, proj, temps_to_regress):
    import matplotlib
    from matplotlib import pyplot as plt

    matplotlib.use("QtAgg")

    plt.figure()
    plt.title("Temperature Profile in Post")
    plt.xlabel("x (m)")
    plt.ylabel("T (C)")
    plt.plot(
        proj.fit.thermocouple_pos,
        ser.loc[temps_to_regress],
        "*",
        label="Measured Temperatures",
        color=[0.2, 0.2, 0.2],
    )
    x_smooth = np.linspace(thermocouple_pos[0], thermocouple_pos[-1])  # type: ignore
    plt.plot(
        x_smooth,
        ser[C.TLfit] + ser[C.dT_dx] * x_smooth,
        "--",
        label=f"Linear Regression $(r^2={round(ser.rvalue**2,4)})$",
    )
    plt.plot(
        0, ser[C.TLfit], "x", label="Extrapolated Surface Temperature", color=[1, 0, 0]
    )
    plt.legend()
    plt.show()


# * -------------------------------------------------------------------------------- * #

if __name__ == "__main__":
    pipeline(get_project())
