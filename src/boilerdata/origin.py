from contextlib import contextmanager
from pathlib import Path

import originpro as op


@contextmanager
def open_originlab(file, readonly=True):
    """Open an OriginLab file."""
    if Path(file).exists():
        op.set_show(True)  # required
        yield op.open(file=get_path(file), readonly=readonly)
    else:
        raise FileNotFoundError(f"File not found: {file}")
    op.exit()


def get_path(file, mkdirs=False):
    """Return the absolute path of a file for OriginLab interoperation."""
    path = Path(file)
    if mkdirs:
        path.mkdir(parents=True, exist_ok=True)
    return str(Path(file).resolve())
