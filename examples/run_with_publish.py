from pathlib import Path
from ladim_helpers import run_ladim_seeds

run_ladim_seeds(
    seeds=[1, 2, 3],
    ladim_yaml_path=Path("ladim.yaml"),
    crecon_yaml_path=Path("crecon.yaml"),
    output_dir=Path(r"C:\ladim_tmp_runs"),
    publish_dir=Path(r"D:\SynologyDrive\project"),
    keep_temp=False,
    run_crecon=True,
)
