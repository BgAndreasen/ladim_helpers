from pathlib import Path
from ladim_helpers import run_ladim_seeds

# Minimal example: run LADiM only, no publishing
run_ladim_seeds(
    seeds=[1, 2, 3],
    ladim_yaml_path=Path("ladim.yaml"),
    crecon_yaml_path=None,
    output_dir=Path("runs"),
    run_crecon=False,
)
