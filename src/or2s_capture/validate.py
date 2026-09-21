"""Validate capture session layout and required streams."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from mcap.reader import make_reader
from mcap_protobuf.decoder import DecoderFactory

TOPIC_RGB = "/or2s/rgb/image"
TOPIC_CAMERA_INFO = "/or2s/rgb/camera_info"
TOPIC_POSE = "/or2s/pose"


@dataclass
class Report:
    """Validation result."""

    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    path: str = ""

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "path": self.path,
        }


def validate(path: Path | str) -> Report:
    """Validate a session directory for Reconstruct Eng ingest.

    Required:
    - ``manifest.json``
    - ``session.mcap`` (or path in manifest)
    - ``calibration/sensors.json`` (or ``calibration_ref``)
    - MCAP topics ``/or2s/rgb/image`` and ``/or2s/rgb/camera_info`` with ≥1 msg

    Recommended (warnings if missing):
    - ``/or2s/pose``
    - ``provenance/device.json``
    - ``checksums.sha256`` (recommended; verified when present)
    """
    path = Path(path)
    if path.is_file() and path.name == "manifest.json":
        path = path.parent
    report = Report(ok=True, path=str(path))

    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        report.errors.append("missing manifest.json")
        report.ok = False
        return report

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        report.errors.append(f"manifest.json is not valid JSON: {e}")
        report.ok = False
        return report

    _validate_checksums(path, manifest, report)

    if manifest.get("schema") != "open-real2sim.capture.manifest/0.1":
        report.warnings.append(
            f"unexpected manifest schema: {manifest.get('schema')!r}"
        )

    mcap_rel = manifest.get("mcap", "session.mcap")
    mcap_path = path / mcap_rel
    if not mcap_path.is_file():
        report.errors.append(f"missing MCAP file: {mcap_rel}")
        report.ok = False

    cal_rel = manifest.get("calibration_ref", "calibration/sensors.json")
    cal_path = path / cal_rel
    if not cal_path.is_file():
        report.errors.append(f"missing calibration file: {cal_rel}")
        report.ok = False
    else:
        try:
            cal = json.loads(cal_path.read_text(encoding="utf-8"))
            sensors = cal.get("sensors") or []
            cams = [s for s in sensors if s.get("type") == "camera"]
            if not cams:
                report.errors.append("calibration has no camera sensor entry")
                report.ok = False
            else:
                intr = cams[0].get("intrinsics") or {}
                for k in ("fx", "fy", "cx", "cy"):
                    if k not in intr:
                        report.errors.append(f"camera intrinsics missing {k}")
                        report.ok = False
        except json.JSONDecodeError as e:
            report.errors.append(f"calibration JSON invalid: {e}")
            report.ok = False

    prov_rel = manifest.get("provenance_ref", "provenance/device.json")
    if not (path / prov_rel).is_file():
        report.warnings.append(f"missing provenance file: {prov_rel}")

    if mcap_path.is_file():
        counts = _topic_counts(mcap_path)
        if counts.get(TOPIC_RGB, 0) < 1:
            report.errors.append(f"MCAP missing required topic {TOPIC_RGB}")
            report.ok = False
        if counts.get(TOPIC_CAMERA_INFO, 0) < 1:
            report.errors.append(
                f"MCAP missing required topic {TOPIC_CAMERA_INFO}"
            )
            report.ok = False
        if counts.get(TOPIC_POSE, 0) < 1:
            report.warnings.append(
                f"MCAP has no {TOPIC_POSE} (recommended for Reconstruct Eng)"
            )
        if not counts:
            report.errors.append("MCAP contains no messages")
            report.ok = False

    return report


def _validate_checksums(path: Path, manifest: dict, report: Report) -> None:
    """Verify the optional sha256sum-compatible checksum sidecar."""
    checksum_path = path / "checksums.sha256"
    if not checksum_path.is_file():
        report.warnings.append("missing checksums.sha256")
        return

    try:
        lines = checksum_path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        report.errors.append(f"could not read checksums.sha256: {e}")
        report.ok = False
        return

    entries: dict[str, str] = {}
    for line_number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split(maxsplit=1)
        if len(fields) != 2 or len(fields[0]) != 64:
            report.errors.append(
                f"checksums.sha256 line {line_number} is invalid"
            )
            report.ok = False
            continue
        digest, rel_name = fields
        if rel_name.startswith("*"):
            rel_name = rel_name[1:]
        try:
            rel_path = Path(rel_name)
        except (TypeError, ValueError):
            report.errors.append(
                f"checksums.sha256 line {line_number} has invalid path"
            )
            report.ok = False
            continue
        if rel_path.is_absolute() or ".." in rel_path.parts:
            report.errors.append(
                f"checksums.sha256 line {line_number} has unsafe path: {rel_name}"
            )
            report.ok = False
            continue
        normalized = rel_path.as_posix()
        if normalized in entries:
            report.errors.append(f"checksums.sha256 has duplicate entry: {normalized}")
            report.ok = False
            continue
        entries[normalized] = digest.lower()

    expected = {
        "manifest.json",
        str(manifest.get("mcap", "session.mcap")),
        str(manifest.get("calibration_ref", "calibration/sensors.json")),
        str(manifest.get("provenance_ref", "provenance/device.json")),
    }
    for rel_name in sorted(expected):
        if rel_name not in entries:
            report.errors.append(f"checksums.sha256 missing entry: {rel_name}")
            report.ok = False

    for rel_name, expected_digest in entries.items():
        file_path = path / rel_name
        if not file_path.is_file():
            report.errors.append(
                f"checksums.sha256 references missing file: {rel_name}"
            )
            report.ok = False
            continue
        actual_digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_digest != expected_digest:
            report.errors.append(f"checksum mismatch: {rel_name}")
            report.ok = False


def _topic_counts(mcap_path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    with open(mcap_path, "rb") as f:
        reader = make_reader(f, decoder_factories=[DecoderFactory()])
        for _schema, channel, _message, _proto in reader.iter_decoded_messages():
            counts[channel.topic] = counts.get(channel.topic, 0) + 1
    return counts
