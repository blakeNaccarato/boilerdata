copier -rf 8b707c6
.venv/Scripts/activate
pip install -U pip  # throws [WinError 5], but still works on its own
pip install -U setuptools wheel  # must be done separately from above
pip install -r tooling/requirements_dev.txt
flit install -s
pip uninstall -y boilerdata
pip install -e .