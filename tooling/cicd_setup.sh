pip install -U pip wheel
pip install pipx
pipx install copier==6.0.0a9
copier -f -r 5adc48e
pip install -r tooling/requirements_cicd.txt
flit install
