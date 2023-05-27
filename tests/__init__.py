"""Helper functions for tests."""

from pathlib import Path

from nbqa.__main__ import _get_nb_to_tmp_mapping, _save_code_sources  # type: ignore


def get_nb_content(nb: Path) -> str:
    """Get the contents of a notebook."""
    _, (newlinesbefore, _) = _save_code_sources(
        _get_nb_to_tmp_mapping(
            [str(nb)],
            None,
            None,
            False,
        ),
        [],
        [],
        False,
        "abc",
    )
    script = [Path(script) for script in list(newlinesbefore.keys())][0]
    contents = script.read_text(encoding="utf-8")
    script.unlink()
    return contents