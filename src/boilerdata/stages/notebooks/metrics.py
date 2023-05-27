from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any

import matplotlib as mpl
import numpy as np
import pandas as pd

# pyright 1.1.308, local/CI difference
from IPython.core.display import Markdown  # type: ignore
from IPython.display import display  # type: ignore
from matplotlib import pyplot as plt
from uncertainties import ufloat

from boilerdata.axes_enum import AxesEnum as A  # noqa: N814
from boilerdata.models.params import Params
from boilerdata.stages.common import get_tcs, get_trial

# * -------------------------------------------------------------------------------- * #
# * MODULE VARIABLES

idxs = pd.IndexSlice
"""Use to slice pd.MultiIndex indices."""

# * -------------------------------------------------------------------------------- * #
# * PLOTTING CONTEXTS


@contextmanager
def manual_subplot_spacing():
    """Context manager that allows custom spacing of subplots."""
    with mpl.rc_context({"figure.autolayout": False}):
        try:
            yield
        finally:
            ...


# * -------------------------------------------------------------------------------- * #
# * FUNCTIONS


def display_named(*args: tuple[Any, str]):
    """Display objects with names above them."""
    for elem, name in args:
        display(Markdown(f"##### {name}"))
        display(elem)


def tex_wrap(df: pd.DataFrame) -> tuple[pd.DataFrame, Mapping[str, str]]:
    """Wrap column titles in LaTeX flags if they contain underscores ($)."""
    mapper: dict[str, str] = {}
    for src_col in df.columns:
        col = f"${handle_subscript(src_col)}$" if "_" in src_col else src_col
        mapper[src_col] = col
    return df.rename(axis="columns", mapper=mapper), mapper


def add_units(
    df: pd.DataFrame, params: Params
) -> tuple[pd.DataFrame, Mapping[str, str]]:
    """Make the columns a multi-index representing units."""
    cols = params.axes.get_col_index()
    quantity = cols.get_level_values("quantity")
    units = cols.get_level_values("units")

    old = (col.name for col in params.axes.cols)
    new = (add_unit(q, u) for q, u in zip(quantity, units, strict=True))  # type: ignore  # pyright 1.1.310, pandas
    mapper = dict(zip(old, new, strict=True))
    return df.rename(axis="columns", mapper=mapper), mapper


# * -------------------------------------------------------------------------------- * #
# * HELPER FUNCTIONS


def handle_subscript(val: str) -> str:
    """Wrap everything after the first underscore and replace others with commas."""
    quantity, units = sep_unit(val)
    parts = quantity.split("_")
    quantity = f"{parts[0]}_" + "{" + ",".join(parts[1:]) + "}"
    return add_unit(quantity, units, tex=True)


def add_unit(quantity: str, units: str, tex: bool = False) -> str:
    """Append units to a quantity."""
    if not tex:
        return f"{quantity} ({units})" if units else quantity
    units = units.replace("-", r"{\cdot}")
    return rf"{quantity}\;({units})" if units else quantity


def sep_unit(val: str) -> tuple[str, str]:
    """Split a quantity and its units."""
    quantity, units = val.split(" (")
    units = units.removesuffix(")")
    return quantity, units


# * -------------------------------------------------------------------------------- * #
# * MODEL FITS


def plot_new_fits(grp: pd.DataFrame, params: Params, model):
    """Plot model fits for trials marked as new."""

    trial = get_trial(grp, params)
    if not trial.new:
        return grp

    tcs, tc_errors = get_tcs(trial)
    x_unique = list(trial.thermocouple_pos.values())
    figs = dict(
        zip(
            [
                params.paths.plot_new_fit_0,
                params.paths.plot_new_fit_1,
                params.paths.plot_new_fit_2,
            ],
            grp.iloc[
                [
                    0,
                    (len(grp) // 2) - 1,
                    len(grp) - 1,
                ]
            ].iterrows(),
            strict=True,
        )
    )

    for fig_dst, (ser_name, ser) in figs.items():
        y_unique = ser[tcs]

        # Plot setup
        fig, ax = plt.subplots(layout="constrained")
        run = ser_name[-1].isoformat()  # type: ignore  # pandas
        ax.margins(0, 0)
        ax.set_title(f"{run = }")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("T (C)")

        # Initial plot boundaries
        x_bounds = np.array([0, trial.thermocouple_pos[A.T_1]])
        y_bounds = model(x_bounds, **get_params_mapping(ser, params.model_params))
        ax.plot(
            x_bounds,
            y_bounds,
            "none",
        )

        # Measurements
        measurements_color = [0.2, 0.2, 0.2]
        ax.plot(
            x_unique,
            y_unique,
            ".",
            label="Measurements",
            color=measurements_color,
            markersize=10,
        )
        ax.errorbar(
            x=x_unique,
            y=y_unique,
            yerr=ser[tc_errors],
            fmt="none",
            color=measurements_color,
        )

        # Confidence interval
        (xlim_min, xlim_max) = ax.get_xlim()
        pad = 0.025 * (xlim_max - xlim_min)
        x_padded = np.linspace(xlim_min - pad, xlim_max + pad, 200)

        y_padded, y_padded_min, y_padded_max = model_with_error(
            model, x_padded, get_params_mapping_with_uncertainties(ser, params)
        )
        ax.plot(
            x_padded,
            y_padded,
            "--",
            label="Model Fit",
        )
        ax.fill_between(
            x=x_padded,
            y1=y_padded_min,  # type: ignore  # pydantic: use_enum_values # Only in CI
            y2=y_padded_max,  # type: ignore  # matplotlib
            color=[0.8, 0.8, 0.8],
            edgecolor=[1, 1, 1],
            label="95% CI",
        )

        # Extrapolation
        ax.plot(
            0,
            ser[A.T_s],
            "x",
            label="Extrapolation",
            color=[1, 0, 0],
        )

        # Finishing
        ax.legend()
        fig.savefig(
            fig_dst,  # type: ignore  # matplotlib
            dpi=300,
        )


# * -------------------------------------------------------------------------------- * #
# * HELPER FUNCTIONS


def get_params_mapping(
    grp: pd.Series | pd.DataFrame, model_params: list[Any]  # type: ignore  # pandas
) -> dict[str, Any]:
    """Get a mapping of parameter names to values."""
    # Reason: pydantic: use_enum_values
    return dict(zip(model_params, grp[model_params], strict=True))


def get_params_mapping_with_uncertainties(
    grp: pd.Series | pd.DataFrame, params: Params  # type: ignore  # pandas
) -> dict[str, Any]:
    """Get a mapping of parameter names to values with uncertainty."""
    # Reason: pydantic: use_enum_values
    model_params: list[str] = params.model_params  # type: ignore
    param_errors: list[str] = params.model_errors  # type: ignore
    model_param_uncertainties = [
        ufloat(model_param, model_error, tag)
        for model_param, model_error, tag in zip(
            grp[model_params], grp[param_errors], model_params, strict=True
        )
    ]
    return dict(zip(model_params, model_param_uncertainties, strict=True))


def model_with_error(model, x, model_param_uncertainties):
    """Evaluate the model for x and return y with errors."""
    u_x = [ufloat(v, 0, "x") for v in x]
    u_y = model(u_x, **model_param_uncertainties)
    y = np.array([v.nominal_value for v in u_y])
    y_min = y - [v.std_dev for v in u_y]  # type: ignore # pyright 1.1.308, local/CI difference
    y_max = y + [v.std_dev for v in u_y]
    return y, y_min, y_max
