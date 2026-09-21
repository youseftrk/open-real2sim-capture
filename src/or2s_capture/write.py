"""Write synthetic capture sessions (foxglove protobuf in MCAP)."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path

from foxglove_schemas_protobuf.CameraCalibration_pb2 import CameraCalibration
from foxglove_schemas_protobuf.CompressedImage_pb2 import CompressedImage
from foxglove_schemas_protobuf.PoseInFrame_pb2 import PoseInFrame
from foxglove_schemas_protobuf.Quaternion_pb2 import Quaternion
from foxglove_schemas_protobuf.Vector3_pb2 import Vector3
from google.protobuf.timestamp_pb2 import Timestamp
from mcap_protobuf.writer import Writer
from PIL import Image, ImageDraw

# Topics locked by CAPTURE_BAG_v0
TOPIC_RGB = "/or2s/rgb/image"
TOPIC_CAMERA_INFO = "/or2s/rgb/camera_info"
TOPIC_POSE = "/or2s/pose"

FRAME_ID = "camera_rgb"
WIDTH = 320
HEIGHT = 240
FX = 280.0
FY = 280.0
CX = WIDTH / 2.0
CY = HEIGHT / 2.0
DEFAULT_DURATION_S = 30.0
DEFAULT_FPS = 20.0
WALKAROUND_RADIUS_M = 2.0


def _ts_pb(unix_ns: int) -> Timestamp:
    return Timestamp(seconds=unix_ns // 1_000_000_000, nanos=unix_ns % 1_000_000_000)


def _jpeg_frame(i: int, n: int) -> bytes:
    """Synthetic RGB JPEG (textured room + frame index marker).

    The background is deliberately static so that the changing poses still
    describe one synthetic scene rather than a sequence of unrelated images.
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), (42, 54, 70))
    draw = ImageDraw.Draw(img)
    # Fixed high-contrast geometry/textures give the synthetic walkaround
    # recognizable features while keeping frame generation dependency-free.
    draw.rectangle([0, 0, WIDTH - 1, 150], fill=(78, 103, 132))
    draw.rectangle([0, 150, WIDTH - 1, HEIGHT - 1], fill=(91, 72, 55))
    for x in range(-40, WIDTH + 40, 40):
        draw.line(
            [x, 150, WIDTH // 2 + (x - WIDTH // 2) // 2, HEIGHT],
            fill=(133, 105, 78),
            width=2,
        )
    for y in range(165, HEIGHT, 18):
        draw.line([0, y, WIDTH, y], fill=(63, 51, 42), width=1)
    draw.rectangle([44, 54, 114, 122], fill=(208, 170, 99), outline=(21, 27, 37), width=3)
    draw.rectangle([56, 66, 102, 108], fill=(41, 91, 111), outline=(235, 220, 171), width=3)
    draw.ellipse([194, 66, 274, 146], fill=(177, 80, 61), outline=(43, 30, 36), width=3)
    draw.ellipse([211, 83, 257, 129], fill=(231, 190, 85), outline=(54, 42, 30), width=2)
    draw.rectangle([8, 8, 100, 36], fill=(0, 0, 0))
    draw.text((12, 12), f"f{i}/{n - 1}", fill=(255, 255, 0))
    from io import BytesIO

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _fake_pose(i: int, n: int) -> tuple[float, float, float, float, float, float, float]:
    """Overlapping horizontal walkaround loop with an inward-facing camera."""
    t = i / max(n - 1, 1)
    angle = 2.0 * math.pi * t
    x = WALKAROUND_RADIUS_M * math.cos(angle)
    y = WALKAROUND_RADIUS_M * math.sin(angle)
    z = 1.4
    # Face the center of the loop while orbiting around +Z. The final sample
    # revisits the initial pose, which makes the trajectory explicitly overlap.
    half = (angle + math.pi) / 2.0
    qx, qy, qz, qw = 0.0, 0.0, math.sin(half), math.cos(half)
    return x, y, z, qx, qy, qz, qw


def write_synthetic_session(
    out_dir: Path,
    duration_s: float = DEFAULT_DURATION_S,
    fps: float = DEFAULT_FPS,
) -> Path:
    """Create a minimal valid capture session under ``out_dir``.

    By default this writes a 30-second, 20 Hz walkaround (601 samples,
    including both ends of the loop). ``duration_s`` and ``fps`` can be
    lowered for quick plumbing tests or increased for reconstruction input.

    Layout::

        out_dir/
          manifest.json
          session.mcap
          calibration/sensors.json
          provenance/device.json
          checksums.sha256

    MCAP encoding: foxglove protobuf
    - ``/or2s/rgb/image`` → ``foxglove.CompressedImage`` (jpeg)
    - ``/or2s/rgb/camera_info`` → ``foxglove.CameraCalibration``
    - ``/or2s/pose`` → ``foxglove.PoseInFrame``

    Timestamps are unix nanoseconds (log_time == publish_time).
    Returns ``out_dir`` as a Path.
    """
    if not math.isfinite(duration_s) or duration_s <= 0:
        raise ValueError("duration_s must be a finite number greater than zero")
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("fps must be a finite number greater than zero")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "calibration").mkdir(exist_ok=True)
    (out_dir / "provenance").mkdir(exist_ok=True)

    session_id = str(uuid.uuid4())
    created = datetime.now(timezone.utc)
    created_rfc = created.isoformat().replace("+00:00", "Z")
    start_ns = int(created.timestamp() * 1e9)
    n_frames = max(2, int(round(duration_s * fps)) + 1)
    dt_ns = round(1e9 / fps)
    actual_duration_s = (n_frames - 1) * dt_ns / 1e9

    # --- calibration ---
    sensors = {
        "schema": "open-real2sim.capture.calibration/0.1",
        "sensors": [
            {
                "frame_id": FRAME_ID,
                "type": "camera",
                "model": "pinhole_radtan",
                "width": WIDTH,
                "height": HEIGHT,
                "intrinsics": {"fx": FX, "fy": FY, "cx": CX, "cy": CY},
                "distortion": [0.0, 0.0, 0.0, 0.0, 0.0],
                "parent_frame": "device",
                "T_parent_sensor": {
                    "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                    "translation_m": [0.0, 0.0, 0.0],
                },
            }
        ],
        "rig_id": "android_default",
        "calibration_date": created_rfc,
        "method": "manual",
    }
    (out_dir / "calibration" / "sensors.json").write_text(
        json.dumps(sensors, indent=2) + "\n", encoding="utf-8"
    )

    # --- provenance ---
    device = {
        "schema": "open-real2sim.capture.device/0.1",
        "platform": "android",
        "device_model": "synthetic",
        "os_version": "n/a",
        "app_or_node": "or2s-capture/0.1.0",
        "sdk_versions": {"or2s_capture": "0.1.0"},
        "time_sync": {
            "time_domain": "unix_ns",
            "source": "system",
            "notes": "synthetic session generated by write_synthetic_session",
        },
    }
    (out_dir / "provenance" / "device.json").write_text(
        json.dumps(device, indent=2) + "\n", encoding="utf-8"
    )

    # --- manifest ---
    manifest = {
        "schema": "open-real2sim.capture.manifest/0.1",
        "session_id": session_id,
        "created_at": created_rfc,
        "capture_mode": "android",
        "purpose": "scene",
        "duration_s": actual_duration_s,
        "mcap": "session.mcap",
        "streams": [
            {
                "name": "rgb",
                "type": "rgb",
                "required": True,
                "topic": TOPIC_RGB,
                "info_topic": TOPIC_CAMERA_INFO,
                "frame_id": FRAME_ID,
                "rate_hz": fps,
                "encoding": "jpeg",
            },
            {
                "name": "pose",
                "type": "pose",
                "required": False,
                "topic": TOPIC_POSE,
                "frame_id": "device",
                "child_frame_id": FRAME_ID,
            },
        ],
        "calibration_ref": "calibration/sensors.json",
        "provenance_ref": "provenance/device.json",
        "time_domain": "unix_ns",
        "coordinate_convention": "RDF_optical",
        "license": "Apache-2.0",
        "attribution": {
            "contributor": "or2s-capture",
            "site": "synthetic",
            "notes": "foxglove protobuf MCAP",
        },
        "mcap_encoding": {
            "format": "protobuf",
            "schemas": {
                TOPIC_RGB: "foxglove.CompressedImage",
                TOPIC_CAMERA_INFO: "foxglove.CameraCalibration",
                TOPIC_POSE: "foxglove.PoseInFrame",
            },
        },
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    # --- MCAP ---
    mcap_path = out_dir / "session.mcap"
    K = [FX, 0.0, CX, 0.0, FY, CY, 0.0, 0.0, 1.0]
    R = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    P = [FX, 0.0, CX, 0.0, 0.0, FY, CY, 0.0, 0.0, 0.0, 1.0, 0.0]
    D = [0.0, 0.0, 0.0, 0.0, 0.0]

    with open(mcap_path, "wb") as f, Writer(f) as writer:
        for i in range(n_frames):
            t_ns = start_ns + i * dt_ns
            ts = _ts_pb(t_ns)

            img = CompressedImage(
                timestamp=ts,
                frame_id=FRAME_ID,
                format="jpeg",
                data=_jpeg_frame(i, n_frames),
            )
            writer.write_message(
                TOPIC_RGB, img, log_time=t_ns, publish_time=t_ns, sequence=i
            )

            cal = CameraCalibration(
                timestamp=ts,
                frame_id=FRAME_ID,
                width=WIDTH,
                height=HEIGHT,
                distortion_model="plumb_bob",
                D=D,
                K=K,
                R=R,
                P=P,
            )
            writer.write_message(
                TOPIC_CAMERA_INFO,
                cal,
                log_time=t_ns,
                publish_time=t_ns,
                sequence=i,
            )

            x, y, z, qx, qy, qz, qw = _fake_pose(i, n_frames)
            pose = PoseInFrame(
                timestamp=ts,
                frame_id="device",
            )
            pose.pose.position.CopyFrom(Vector3(x=x, y=y, z=z))
            pose.pose.orientation.CopyFrom(Quaternion(x=qx, y=qy, z=qz, w=qw))
            writer.write_message(
                TOPIC_POSE, pose, log_time=t_ns, publish_time=t_ns, sequence=i
            )

    # --- checksums ---
    # Keep this in standard sha256sum-compatible format and deliberately omit
    # checksums.sha256 itself so the file does not need a fixed-point digest.
    checksum_paths = (
        Path("session.mcap"),
        Path("manifest.json"),
        Path("calibration/sensors.json"),
        Path("provenance/device.json"),
    )
    checksum_lines = []
    for rel_path in checksum_paths:
        digest = hashlib.sha256((out_dir / rel_path).read_bytes()).hexdigest()
        checksum_lines.append(f"{digest}  {rel_path.as_posix()}")
    (out_dir / "checksums.sha256").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )

    return out_dir
