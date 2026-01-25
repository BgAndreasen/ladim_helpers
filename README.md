# ladim_helpers

![Tests](https://github.com/BgAndreasen/ladim_helpers/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Helper utilities for running **LADiM** and working with its NetCDF output.

`ladim_helpers` provides small, focused tools to:

- run LADiM across multiple random seeds
- detect corrupted NetCDF output files
- embed configuration files into NetCDF metadata
- safely copy results to long-term storage

The package is intentionally lightweight and designed to be used alongside existing LADiM workflows.

## Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/BgAndreasen/ladim_helpers.git
```

> `ladim`, `ladim-plugings`, and `ladim-aggregate`must already be installed in the environment.


## Quick example

Run LADiM for multiple seeds:

```python
from pathlib import Path
from ladim_helpers import run_ladim_seeds

run_ladim_seeds(
    seeds=[1, 2, 3],
    ladim_yaml_path=Path("ladim.yaml"),
    run_crecon=False,
)
```

This produces one NetCDF file per seed and continues even if individual runs fail.


## Publishing results safely

This is an option to use if you usually work from a directory where a syncing service is running, so that NetCDF corruption is avoided (I learned this the hard way 😏) 

The output files are written to a local directory (with no sync service running), the files are verified and then copied to the location you want.

- remeber to use path strings to match your OS!

```python
run_ladim_seeds(
    seeds=[1, 2, 3],
    ladim_yaml_path=Path("ladim.yaml"),
    crecon_yaml_path=Path("crecon.yaml"),
    output_dir=Path(r"C:\ladim_tmp_runs"),
    publish_dir=Path(r"D:\SynologyDrive\project"),
    run_crecon=True,
)
```