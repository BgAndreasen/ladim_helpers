from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional
from logging import Logger

import xarray as xr


def attach_text_as_attr(
    nc_path: Path,
    attr_name: str,
    text: str,
    extra_attrs: Optional[dict] = None,
    logger: Optional[Logger] = None,
    ) -> None:
    """
    Attach a string attribute (e.g., YAML) to a NetCDF file.

    Writes:
      - attr_name: full text
      - attr_name_sha256: hash for quick comparison
      - any extra attrs (stringified)
    """
    nc_path = Path(nc_path).resolve()

    try:
        with xr.open_dataset(nc_path, mode="a", engine = "netcdf4") as ds:
            ds.attrs[attr_name] = text
            ds.attrs[f"{attr_name}_sha256"] = hashlib.sha256(
                text.encode("utf-8")
                ).hexdigest()
            if extra_attrs:
                for k, v in extra_attrs.items():
                    ds.attrs[str(k)] = v if isinstance(v, str) else repr(v)

        if logger:
            logger.info("Attached attribute %s to %s", attr_name, nc_path.name)
            
    except Exception as e:
        if logger:
            logger.exception("Failed to attach attribute %s to %s: %s", attr_name, nc_path, e)
        else:
            raise
