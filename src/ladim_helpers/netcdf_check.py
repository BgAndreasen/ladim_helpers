from __future__ import annotations

from pathlib import Path
from typing import Optional

import xarray as xr


def find_first_bad_index(
    nc_path: Path,
    var: str = "lon",
    dim: str = "particle_instance",
    step: int = 10_000,
    logger=None,
) -> Optional[int]:
    """
    Exponential + binary search to find the first failing read index.

    Returns:
      - None: file readable for [0:n)
      - int: first failing index (approx exact for chunk-corruption)
      - 0: cannot even open dataset (very broken)
    """
    nc_path = Path(nc_path).resolve()

    def log(msg: str):
        if logger:
            logger.info(msg)

    try:
        ds = xr.open_dataset(nc_path)
    except Exception as e:
        log(f"FAILED to open dataset: {e}")
        return 0

    try:
        if dim not in ds.sizes:
            log(f"Dimension '{dim}' not found; skipping scan.")
            return None
        if var not in ds:
            log(f"Variable '{var}' not found; skipping scan.")
            return None

        n = ds.sizes[dim]
        log(f"Total {dim}: {n}")

        def ok(stop: int) -> bool:
            try:
                _ = ds[var].isel({dim: slice(0, stop)}).values
                return True
            except Exception:
                return False

        # exponential search
        k = step
        last_ok = 0
        while k < n and ok(k):
            log(f"OK up to {k}")
            last_ok = k
            k *= 2

        if k >= n and ok(n):
            log("NetCDF fully readable")
            return None

        lo = last_ok
        hi = min(k, n)

        # binary search
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if ok(mid):
                lo = mid
            else:
                hi = mid

        log(f"❌ Fails at index {hi} (last good {lo})")
        return hi

    finally:
        ds.close()
