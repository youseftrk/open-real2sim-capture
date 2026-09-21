"""write-synthetic → validate passes."""

from __future__ import annotations

from pathlib import Path

from or2s_capture import read_session, validate, write_synthetic_session


def test_write_synthetic_validate_passes(tmp_path: Path) -> None:
    out = write_synthetic_session(tmp_path / "session")
    report = validate(out)
    assert report.ok, report.errors
    assert not report.errors

    assert (out / "manifest.json").is_file()
    assert (out / "session.mcap").is_file()
    assert (out / "calibration" / "sensors.json").is_file()
    assert (out / "provenance" / "device.json").is_file()

    session = read_session(out)
    streams = {s.topic: s for s in session.list_streams()}
    assert "/or2s/rgb/image" in streams
    assert "/or2s/rgb/camera_info" in streams
    assert "/or2s/pose" in streams
    assert streams["/or2s/rgb/image"].message_count >= 1

    frames = list(session.iter_rgb())
    poses = list(session.iter_poses())
    assert len(frames) == streams["/or2s/rgb/image"].message_count
    assert len(poses) == streams["/or2s/pose"].message_count
    assert frames[0].encoding in ("jpeg", "jpg")
    assert len(frames[0].data) > 0
    assert len(poses[0].orientation_xyzw) == 4
    assert len(poses[0].position_m) == 3


def test_validate_missing_calib_fails(tmp_path: Path) -> None:
    out = write_synthetic_session(tmp_path / "session")
    (out / "calibration" / "sensors.json").unlink()
    report = validate(out)
    assert not report.ok
    assert any("calibration" in e for e in report.errors)
