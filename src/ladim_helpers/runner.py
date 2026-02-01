from __future__ import annotations

import io
from contextlib import contextmanager
import logging
import random
from copy import deepcopy
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import yaml

from .attrs import attach_text_as_attr
from .netcdf_check import find_first_bad_index
from .publish import publish_file

@contextmanager
def capture_root_to(handler: logging.Handler, level: int):
    root = logging.getLogger()
    old_level = root.level
    root.addHandler(handler)
    root.setLevel(min(old_level, level) if old_level else level)
    try:
        yield
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)

def _configure_seed_logger(log_path: Path, name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Create a per-seed logger that logs to `log_path` without clobbering global/root logging.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # don't double-log into root handlers

    # Remove old handlers if this logger name is reused
    for h in list(logger.handlers):
        logger.removeHandler(h)

    fh = logging.FileHandler(str(log_path), mode="w", encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(fh)
    return logger

def _status(msg: str, verbose: bool) -> None:
    if verbose:
        print(msg, flush=True)


def run_ladim_seeds(
    seeds: Iterable[int],
    ladim_yaml_path: Path,
    crecon_yaml_path: Optional[Path] = None,
    output_dir: Path = Path("."),
    publish_dir: Optional[Path] = None,
    keep_temp: bool = False,
    run_crecon: bool = False,
    embed_ladim_yaml: bool = True,
    embed_crecon_yaml: bool = False,
    check_var: str = "lon",
    check_dim: str = "particle_instance",
    loglevel: int = logging.INFO,
    verbose: bool = True,
) -> None:
    """
    Run LADiM across multiple seeds with:
      - per-seed output filename
      - NetCDF chunk-corruption check (pinpoints first bad index)
      - embed ladim.yaml text as NetCDF attribute BEFORE publish
      - optional crecon (continues on failure)
      - publish outputs to publish_dir
    """
    
    _status(f"Running LADiM for {len(list(seeds))} seeds", verbose)

    # Lazy imports so package is usable even if LADiM isn't installed in some envs
    import ladim
    from ladim_aggregate import script as agg_script

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if publish_dir is None:
        publish_dir = output_dir
    publish_dir = Path(publish_dir).resolve()
    publish_dir.mkdir(parents=True, exist_ok=True)

    base_cfg = yaml.safe_load(Path(ladim_yaml_path).read_text(encoding="utf-8"))

    out_template = Path(base_cfg["files"]["output_file"]).name
    out_stem = Path(out_template).stem
    out_suf = Path(out_template).suffix or ".nc"

    for seed in seeds:

        _status(f"[seed {seed}] starting", verbose)

        log_path = output_dir / f"ladim_seed{seed}.log"
        logger = _configure_seed_logger(log_path, name=f"ladim_helpers.seed{seed}", level=loglevel)

        logger.info("=== Seed %s ===", seed)
        random.seed(seed)
        np.random.seed(seed)

        # copy config
        cfg = deepcopy(base_cfg)
        cfg.setdefault("files", {})

        out_name = f"{out_stem}_seed{seed}{out_suf}"
        out_path = (output_dir / out_name).resolve()
        cfg["files"]["output_file"] = str(out_path)

        if out_path.exists():
            out_path.unlink()
            logger.info("Deleted old output file: %s", out_path)

        cfg_text = yaml.safe_dump(cfg, sort_keys=False)
        cfg_stream = io.StringIO(cfg_text)

        # --- LADiM ---
        try:
            fh = next(h for h in logger.handlers if isinstance(h, logging.FileHandler))
            logger.info("Starting LADiM: output=%s", out_path)
            with capture_root_to(fh, loglevel):
                ladim.main(config_stream=cfg_stream, loglevel=loglevel)
            #ladim.main(config_stream=cfg_stream, loglevel=loglevel)
            logger.info("Finished LADiM")
            _status(f"[seed {seed}] LADiM finished", verbose)
        except Exception as e:
            logger.exception("LADiM FAILED for seed=%s", seed)
            # publish the log even on failure
            publish_file(log_path, publish_dir, logger=logger, keep_temp=keep_temp)
            _status(f"[seed {seed}] ⚠️ LADiM failed (see log)", verbose)
            continue

        # --- Integrity check ---
        bad = find_first_bad_index(out_path, var=check_var, dim=check_dim, logger=logger)
        if bad is not None:
            logger.error(
                "NetCDF corruption detected at %s=%s; skipping downstream for seed=%s",
                check_dim,
                bad,
                seed,
            )
            publish_file(out_path, publish_dir, logger=logger, keep_temp=keep_temp)
            publish_file(log_path, publish_dir, logger=logger, keep_temp=keep_temp)
            _status(f"[seed {seed}] ❌ NetCDF corruption detected — skipping", verbose)
            continue

        # --- Embed LADiM YAML before publish ---
        if embed_ladim_yaml:
            attach_text_as_attr(
                out_path,
                attr_name="ladim_config_yaml",
                text=cfg_text,
                extra_attrs={"ladim_config_path": str(Path(ladim_yaml_path).resolve())},
                logger=logger,
            )

        conc_path: Optional[Path] = None
        tmp_cfg: Optional[Path] = None

        # --- Optional CRECON ---
        if run_crecon and crecon_yaml_path is not None:
            try:
                crecon_cfg = yaml.safe_load(Path(crecon_yaml_path).read_text(encoding="utf-8"))
                crecon_cfg["infile"] = str(out_path)

                conc_path = (output_dir / f"conc_seed{seed}.nc").resolve()
                crecon_cfg["outfile"] = str(conc_path)

                tmp_cfg = output_dir / f"crecon_seed{seed}.tmp.yaml"
                tmp_cfg.write_text(yaml.safe_dump(crecon_cfg, sort_keys=False), encoding="utf-8")

                logger.info("Starting CRECON using %s", tmp_cfg)
                agg_script.main(str(tmp_cfg))
                logger.info("Finished CRECON")

                if embed_crecon_yaml and conc_path.exists():
                    attach_text_as_attr(
                        conc_path,
                        attr_name="crecon_config_yaml",
                        text=tmp_cfg.read_text(encoding="utf-8"),
                        extra_attrs={"crecon_config_path": str(Path(crecon_yaml_path).resolve())},
                        logger=logger,
                    )
            except Exception:
                logger.exception("CRECON FAILED for seed=%s", seed)
            finally:
                if tmp_cfg is not None:
                    try:
                        if tmp_cfg.exists():
                            tmp_cfg.unlink()
                    except Exception:
                        logger.exception("Could not delete temp CRECON config for seed=%s", seed)

        # --- Publish (copy) ---
        publish_file(out_path, publish_dir, logger=logger, keep_temp=keep_temp)
        if conc_path is not None and conc_path.exists():
            publish_file(conc_path, publish_dir, logger=logger, keep_temp=keep_temp)
        publish_file(log_path, publish_dir, logger=logger, keep_temp=keep_temp)

        logger.info("Seed %s complete.", seed)
        _status(f"[seed {seed}] ✅ done", verbose)
