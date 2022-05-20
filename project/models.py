from datetime import date
from enum import auto
from pathlib import Path

import numpy as np
from pydantic import BaseModel, DirectoryPath, Extra, Field, validator

from boilerdata.enums import GetNameEnum

# * -------------------------------------------------------------------------------- * #
# * PROJECT


class Fit(BaseModel):
    """Configure the linear regression of thermocouple temperatures vs. position."""

    thermocouple_pos: list[float] = Field(
        default=...,
        description="Thermocouple positions.",
    )
    do_plot: bool = Field(False, description="Whether to plot the linear regression.")

    @validator("thermocouple_pos")
    def _(cls, thermocouple_pos):
        return np.array(thermocouple_pos)


class Project(BaseModel, extra=Extra.forbid):
    """Configuration for the package."""

    base: DirectoryPath = Field(
        default=...,
        description="The base directory for the project data.",
    )
    trials: DirectoryPath = Field(
        default=...,
        description="The directory in which the individual trials are. Must be relative to the base directory.",
    )
    results: DirectoryPath = Field(
        default=...,
        description="The directory in which the results will go. Must be relative to the base directory. Will be created if it is missing.",
    )
    results_file: Path = Field(
        default="results.csv",
        description="The name of the results file. Will go in the results directory. Default: results.csv",
    )
    directory_per_trial: Path = Field(
        default=...,
        description="The directory in which the data are for a given trial. Must be relative to a trial folder, and all trials must share this pattern.",
    )
    fit: Fit

    @validator("trials", pre=True)  # "pre" because dir must exist pre-validation
    def validate_trials(cls, trials, values):
        return values["base"] / Path(trials)

    @validator("results", pre=True)  # "pre" because dir must exist pre-validation
    def validate_results(cls, results, values):
        results = values["base"] / Path(results)
        results.mkdir(parents=True, exist_ok=True)
        return results

    @validator("results_file", always=True)  # "always" so it'll run even if not in YAML
    def validate_results_file(cls, results_file, values):
        if results_file.suffix != ".csv":
            raise ValueError("The supplied results filename is not a CSV.")
        return values["results"] / results_file


# * -------------------------------------------------------------------------------- * #
# * TRIALS


class Rod(GetNameEnum):
    """The rod used in this trial."""

    W = auto()
    X = auto()
    Y = auto()


class Coupon(GetNameEnum):
    """The coupon attached to the rod for this trial."""

    A1 = auto()
    A2 = auto()
    A3 = auto()
    A4 = auto()
    A6 = auto()
    A7 = auto()
    A9 = auto()


class Sample(GetNameEnum):
    """The sample attached to the coupon in this trial."""

    NA = auto()  # If no sample is attached to the coupon.
    B3 = auto()


class Group(GetNameEnum):
    """The group that this sample belongs to."""

    control = auto()
    porous = auto()
    hybrid = auto()


class Joint(GetNameEnum):
    """The method used to join parts of the sample in this trial."""

    paste = auto()
    epoxy = auto()
    solder = auto()


class Trial(BaseModel, extra=Extra.forbid):
    """A trial."""

    date: date
    rod: Rod
    coupon: Coupon
    sample: Sample
    group: Group
    monotonic: bool = Field(
        default=...,
        description="Whether the boiling curve is monotonic.",
    )
    joint: Joint
    comment: str

    def get_path(self, project: Project) -> Path:
        """Get the path to the data for this trial."""
        return project.trials / self.date.isoformat() / project.directory_per_trial


class Trials(BaseModel):
    """The trials."""

    trials: list[Trial]


# * -------------------------------------------------------------------------------- * #
# * COLUMNS


class Column(BaseModel):
    units: str
