"""Test configuration."""

from collections.abc import Callable
from importlib import import_module
from pathlib import Path

import pytest
import seaborn as sns
from boilercore import filter_certain_warnings
from boilercore.testing import get_nb_client, get_session_path
from ploomber_engine.ipython import PloomberClient

import boilerdata
from boilerdata_tests import nbs_to_execute, stages


# Can't be session scope
@pytest.fixture(autouse=True)
def _filter_certain_warnings():
    """Filter certain warnings."""
    filter_certain_warnings()


@pytest.fixture()
def plt(plt):
    """Configure plotting."""
    sns.set_theme(
        context="notebook", style="whitegrid", palette="bright", font="sans-serif"
    )
    plt.style.use(style=Path("data/config/plotting/base.mplstyle"))
    yield plt
    plt.saveas = f"{plt.saveas[:-4]}.png"


@pytest.fixture(scope="session", autouse=True)
def project_session_path(tmp_path_factory) -> Path:
    """Project session path."""
    return get_session_path(tmp_path_factory, boilerdata)


@pytest.fixture(scope="session")
def params(project_session_path):
    """Parameters."""
    from boilerdata.models.params import PARAMS

    return PARAMS


@pytest.fixture(params=stages)
def stage(request) -> str:
    """Stage module name."""
    return request.param


@pytest.fixture()
def main(stage) -> Callable[..., None]:
    """Main function for a stage."""
    return import_module(stage).main


@pytest.fixture(params=nbs_to_execute)
def nb_to_execute(request) -> Path:
    """Path to a notebook that should be executed only."""
    return request.param


@pytest.fixture()
def nb_client_to_execute(project_session_path, nb_to_execute) -> PloomberClient:
    """Notebook client to be executed only."""
    return get_nb_client(nb_to_execute, project_session_path)
