from pathlib import Path
import logging

from ladim_helpers.publish import publish_file


def test_publish_noop_same_dir(tmp_path: Path):
    logger = logging.getLogger("test")
    f = tmp_path / "a.txt"
    f.write_text("hi", encoding="utf-8")

    out = publish_file(f, tmp_path, logger=logger, keep_temp=False)
    assert out.exists()
    assert out.read_text(encoding="utf-8") == "hi"


def test_publish_copies_and_deletes(tmp_path: Path):
    logger = logging.getLogger("test")
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()

    f = src_dir / "a.txt"
    f.write_text("hi", encoding="utf-8")

    out = publish_file(f, dst_dir, logger=logger, keep_temp=False)
    assert out.exists()
    assert out.parent == dst_dir
    assert out.read_text(encoding="utf-8") == "hi"
    assert not f.exists()
