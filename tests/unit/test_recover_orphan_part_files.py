import os
import time
from pathlib import Path


def test_recovers_old_part_files(monkeypatch, tmp_path: Path):
    """Part files older than the threshold should be renamed to remove .part suffix."""
    from douyu2bilibili import config
    from douyu2bilibili.encoder import recover_orphan_part_files

    processing = tmp_path / "processing"
    processing.mkdir()
    monkeypatch.setattr(config, "PROCESSING_FOLDER", str(processing))
    monkeypatch.setattr(config, "ORPHAN_PART_FILE_AGE_MINUTES", 120)

    # Create old .flv.part and .xml.part files
    flv_part = processing / "test录播2026-03-22T23_37_28.flv.part"
    xml_part = processing / "test录播2026-03-22T23_37_28.xml.part"
    flv_part.write_bytes(b"fake-flv")
    xml_part.write_bytes(b"fake-xml")

    # Set mtime to 3 hours ago (older than 120 min threshold)
    old_time = time.time() - 3 * 3600
    os.utime(flv_part, (old_time, old_time))
    os.utime(xml_part, (old_time, old_time))

    recovered = recover_orphan_part_files()

    assert recovered == 1
    assert (processing / "test录播2026-03-22T23_37_28.flv").exists()
    assert (processing / "test录播2026-03-22T23_37_28.xml").exists()
    assert not flv_part.exists()
    assert not xml_part.exists()


def test_skips_recent_part_files(monkeypatch, tmp_path: Path):
    """Part files newer than the threshold should NOT be renamed (still recording)."""
    from douyu2bilibili import config
    from douyu2bilibili.encoder import recover_orphan_part_files

    processing = tmp_path / "processing"
    processing.mkdir()
    monkeypatch.setattr(config, "PROCESSING_FOLDER", str(processing))
    monkeypatch.setattr(config, "ORPHAN_PART_FILE_AGE_MINUTES", 120)

    # Create a recent .flv.part (mtime = now)
    flv_part = processing / "active录播2026-03-25T22_00_00.flv.part"
    flv_part.write_bytes(b"fake-flv")

    recovered = recover_orphan_part_files()

    assert recovered == 0
    assert flv_part.exists()  # Still a .part file


def test_handles_flv_part_without_xml(monkeypatch, tmp_path: Path):
    """A lone .flv.part without matching .xml.part should still be recovered."""
    from douyu2bilibili import config
    from douyu2bilibili.encoder import recover_orphan_part_files

    processing = tmp_path / "processing"
    processing.mkdir()
    monkeypatch.setattr(config, "PROCESSING_FOLDER", str(processing))
    monkeypatch.setattr(config, "ORPHAN_PART_FILE_AGE_MINUTES", 120)

    flv_part = processing / "no_xml录播2026-03-20T10_00_00.flv.part"
    flv_part.write_bytes(b"fake-flv")

    old_time = time.time() - 3 * 3600
    os.utime(flv_part, (old_time, old_time))

    recovered = recover_orphan_part_files()

    assert recovered == 1
    assert (processing / "no_xml录播2026-03-20T10_00_00.flv").exists()
    assert not flv_part.exists()


def test_ignores_non_flv_part_files(monkeypatch, tmp_path: Path):
    """Files that don't end in .flv.part should be ignored."""
    from douyu2bilibili import config
    from douyu2bilibili.encoder import recover_orphan_part_files

    processing = tmp_path / "processing"
    processing.mkdir()
    monkeypatch.setattr(config, "PROCESSING_FOLDER", str(processing))
    monkeypatch.setattr(config, "ORPHAN_PART_FILE_AGE_MINUTES", 120)

    # Only .xml.part, no .flv.part — should not be touched
    xml_part = processing / "only_xml录播2026-03-20T10_00_00.xml.part"
    xml_part.write_bytes(b"fake-xml")

    old_time = time.time() - 3 * 3600
    os.utime(xml_part, (old_time, old_time))

    recovered = recover_orphan_part_files()

    assert recovered == 0
    assert xml_part.exists()  # Untouched
