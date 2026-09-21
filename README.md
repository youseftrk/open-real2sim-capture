# or2s-capture

Minimal **Apache-2.0** Python package for Open Real2Sim **capture bags** (v0 stub).

Primary on-disk format: **MCAP** + sidecar JSON (`manifest.json`, calibration, provenance).
See [`docs/CAPTURE_BAG_v0.md`](docs/CAPTURE_BAG_v0.md) for the locked schema.

Consumers: **Reconstruct Eng** (ingest), Sim Runtime, Env Commons.

## Install

```bash
cd /workspace/open-real2sim-capture
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## CLI

```bash
or2s write-synthetic OUT_DIR
# Optional: --duration SECONDS --fps HZ (defaults: 30 s at 20 Hz)
or2s validate SESSION_DIR
or2s import-rosbag BAG -o OUT_DIR   # stub → NotImplementedError
```

Demo sessions in this checkout:

- `_demo_session/` is the short plumbing demo (the original ~0.9 s / 10-frame session).
- `_demo_session_30s/` is the reconstruction demo: a 30 s, 20 Hz JPEG + pose
  walkaround loop with overlapping views. Generate another session with
  `or2s write-synthetic OUT_DIR --duration 30 --fps 20`.

## Layout

```
session_<uuid>/                 # or any OUT_DIR from write-synthetic
  manifest.json                 # required
  session.mcap                  # required — primary stream store
  calibration/
    sensors.json                # RGB intrinsics / extrinsics
  provenance/
    device.json                 # hardware / OS / app
  checksums.sha256              # SHA-256 sidecar (recommended)
```

## MCAP encoding (chosen for v0)

| Topic | Schema | Notes |
|-------|--------|-------|
| `/or2s/rgb/image` | `foxglove.CompressedImage` | JPEG bytes in `data`, `format=jpeg` |
| `/or2s/rgb/camera_info` | `foxglove.CameraCalibration` | K, D, R, P, width, height |
| `/or2s/pose` | `foxglove.PoseInFrame` | position + orientation (xyzw) in `frame_id=device` |

- Serialization: **Protobuf** via `mcap-protobuf-support` + `foxglove-schemas-protobuf`
- Timestamps: **unix nanoseconds** (`log_time` = `publish_time`)
- No ROS install required for the synthetic path
- ROS2 CDR is reserved for `import_rosbag2` (stub only in v0)

Manifest also records this under `mcap_encoding`.

## Python API

```python
from pathlib import Path
from or2s_capture import write_synthetic_session, read_session, validate

out = write_synthetic_session(Path("/tmp/or2s_demo"))  # 30 s at 20 Hz by default
report = validate(out)
assert report.ok

session = read_session(out)
print(session.list_streams())
for frame in session.iter_rgb():
    print(frame.log_time_ns, frame.encoding, len(frame.data))
for pose in session.iter_poses():
    print(pose.position_m, pose.orientation_xyzw)
```

## How Reconstruct Eng ingests

Minimum viable session:

1. `manifest.json` + `session.mcap` with `/or2s/rgb/image` and `/or2s/rgb/camera_info`
2. `calibration/sensors.json` with RGB pinhole intrinsics (`fx/fy/cx/cy`)
3. Preferred: `/or2s/pose` trajectory (included in synthetic writer)

Coordinate convention: camera optical **RDF** (x right, y down, z forward). Quaternions **xyzw**.
`T_parent_sensor` is parent ← sensor.

Capture emits observations + calib only — mesh / Isaac / MuJoCo export is Reconstruct Eng / Sim Runtime.

## Tests

```bash
pytest
```

## License

Apache-2.0 — see [`LICENSE`](LICENSE).
