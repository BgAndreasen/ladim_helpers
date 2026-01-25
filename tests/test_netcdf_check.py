from pathlib import Path
import numpy as np
import xarray as xr

from ladim_helpers.netcdf_check import find_first_bad_index


def test_find_first_bad_index_on_good_file(tmp_path: Path):
    fn = tmp_path / "ok.nc"
    ds = xr.Dataset(
        data_vars={"lon": (("particle_instance",), np.arange(1000, dtype=np.float32))},
        coords={},
    )
    ds.to_netcdf(fn)
    ds.close()

    bad = find_first_bad_index(fn, var="lon", dim="particle_instance", step=100)
    assert bad is None
