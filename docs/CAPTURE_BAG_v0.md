# Capture Bag Format — v0

**Project:** `open-real2sim-capture`  
**License:** Apache-2.0  
**Status:** draft — aligned to CTO milestone (2026-09-21)  
**Clean-room:** public Real2Sim product demos only  

**Consumers:** Reconstruct Eng (ingest), Sim Runtime, Env Commons (manifest later)

## Locked decisions (CTO)
- Primary on-disk: **MCAP**
- Secondary import: **rosbag2** (not HDF5 primary)
- Streams: **RGB required**; depth / IMU / LiDAR optional
- Per-frame timestamps; camera intrinsics + extrinsics; device provenance
- Platforms v0: **ROS2 robots** + **Android** RGB(/depth if easy); iOS later; tablet = phone path
- Greenfield repo; no closed cloud capture requirement

---

## Canonical package

A session is either:
1. **Preferred:** `session.mcap` + sibling `manifest.json`, or
2. Directory `session_<uuid>/` with the same logical content (dev convenience).

```
session_<uuid>/
  manifest.json              # required
  session.mcap               # required — primary stream store
  calibration/
    sensors.json             # intrinsics / extrinsics
  provenance/
    device.json              # hardware / OS / app / SDK versions
  checksums.sha256           # optional but recommended
```

All frame data lives in MCAP topics. Sidecar JSON is for discovery + non-stream metadata Reconstruct Eng can read without scanning the whole bag.

---

## `manifest.json`

```json
{
  "schema": "open-real2sim.capture.manifest/0.1",
  "session_id": "uuid",
  "created_at": "RFC3339",
  "capture_mode": "android" | "robot_ros2" | "tablet_android" | "ios_later",
  "purpose": "scene" | "object" | "demo_episode" | "calibration_only",
  "duration_s": 0.0,
  "mcap": "session.mcap",
  "streams": [
    {
      "name": "rgb",
      "type": "rgb",
      "required": true,
      "topic": "/or2s/rgb/image",
      "info_topic": "/or2s/rgb/camera_info",
      "frame_id": "camera_rgb",
      "rate_hz": 30,
      "encoding": "rgb8" | "jpeg"
    },
    {
      "name": "depth",
      "type": "depth",
      "required": false,
      "topic": "/or2s/depth/image",
      "frame_id": "camera_rgb",
      "unit": "mm_uint16" | "m_float32",
      "aligned_to": "camera_rgb"
    },
    {
      "name": "imu",
      "type": "imu",
      "required": false,
      "topic": "/or2s/imu",
      "frame_id": "imu"
    },
    {
      "name": "lidar",
      "type": "lidar",
      "required": false,
      "topic": "/or2s/lidar/points",
      "frame_id": "lidar"
    },
    {
      "name": "pose",
      "type": "pose",
      "required": false,
      "topic": "/or2s/pose",
      "frame_id": "device" | "base_link",
      "child_frame_id": "camera_rgb"
    }
  ],
  "calibration_ref": "calibration/sensors.json",
  "provenance_ref": "provenance/device.json",
  "time_domain": "unix_ns",
  "coordinate_convention": "RDF_optical" ,
  "license": "Apache-2.0",
  "attribution": { "contributor": "", "site": "", "notes": "" }
}
```

`coordinate_convention`: camera optical **RDF** (x right, y down, z forward). Robot base / world: document in `sensors.json` (`ENU` or `robot_base` as `parent_frame`).

---

## MCAP topics (v0)

| Topic | Msg / payload | Required |
|-------|----------------|----------|
| `/or2s/rgb/image` | Image (rgb8 or compressed jpeg) | **yes** |
| `/or2s/rgb/camera_info` | CameraInfo (K, D, width, height) | **yes** (or bake into sensors.json; prefer both) |
| `/or2s/depth/image` | Image uint16 mm **or** float32 m | no |
| `/or2s/imu` | Imu | no |
| `/or2s/lidar/points` | PointCloud2 XYZI or XYZ | no |
| `/or2s/pose` | PoseStamped (device/AR or robot) | recommended |
| `/tf` / `/tf_static` | TFMessage | robot path |

Every message: log time = publish time in **unix nanoseconds** (or ROS time with `time_domain` declared and offset in provenance). No silent clock domains.

---

## Calibration — `calibration/sensors.json`

```json
{
  "schema": "open-real2sim.capture.calibration/0.1",
  "sensors": [
    {
      "frame_id": "camera_rgb",
      "type": "camera",
      "model": "pinhole_radtan",
      "width": 1920,
      "height": 1080,
      "intrinsics": { "fx": 0.0, "fy": 0.0, "cx": 0.0, "cy": 0.0 },
      "distortion": [0, 0, 0, 0, 0],
      "parent_frame": "imu",
      "T_parent_sensor": {
        "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
        "translation_m": [0.0, 0.0, 0.0]
      }
    }
  ],
  "rig_id": "android_default" | "robot_<name>",
  "calibration_date": "RFC3339",
  "method": "factory" | "arkit" | "arcore" | "kalibr" | "manual" | "unknown"
}
```

**Pose convention for Reconstruct Eng:**
- `T_parent_sensor` is **parent ← sensor** (transforms a point in sensor frame into parent).
- Quaternion **xyzw**.
- Depth (if present) is in the same optical frame as RGB when `aligned_to: camera_rgb`.

---

## Provenance — `provenance/device.json`

```json
{
  "schema": "open-real2sim.capture.device/0.1",
  "platform": "android" | "ros2",
  "device_model": "",
  "os_version": "",
  "app_or_node": "or2s-android/0.1.0",
  "sdk_versions": {},
  "time_sync": {
    "time_domain": "unix_ns",
    "source": "system" | "ros_clock" | "arcore",
    "notes": ""
  }
}
```

---

## Hand-off to Reconstruct Eng

**Minimum viable session for reconstruction ingest:**
1. `manifest.json` + `session.mcap` with `/or2s/rgb/image` (+ camera_info)
2. `calibration/sensors.json` with RGB intrinsics (extrinsics identity OK for monocular phone)
3. Optional but strongly preferred: depth aligned to RGB **or** `/or2s/pose` trajectory

**Not Capture Lead's job:** Isaac/MuJoCo mesh export formats — that is Sim Runtime / Reconstruct Eng. Capture emits observations + calib only.

**Still open (non-blocking):**
- Default depth unit: prefer `mm_uint16` when Android gives it; declare in manifest
- **Encoding (locked with Reconstruct Eng):** foxglove schemas for Android + `write_synthetic_session` (Image / CompressedImage / CameraCalibration / PoseInFrame). ROS2 CDR only on `import_rosbag2`.
- `/or2s/pose` strongly preferred for RGB-only phone sessions
- Future multi-rig: shared `world_frame` in provenance or sensors.json (not required for v0)

---

## Python SDK v0 (this week)

```
or2s_capture/
  write_synthetic_session(out_dir)  # RGB + fake poses → MCAP
  read_session(path) -> Session
  validate(path) -> Report
  import_rosbag2(bag, out_dir) -> Session   # stub OK
```

CLI: `or2s validate`, `or2s write-synthetic`, `or2s import-rosbag` (stub).

---

## Platforms

| Path | v0 |
|------|----|
| ROS2 robot | record → `import_rosbag2` → session |
| Android phone/tablet | RGB required; depth if Camera2/ARCore easy |
| iOS | deferred |

---

## Demo evidence (public, 2026-09-21)
Public Real2Sim-style demo video (Unitree-class humanoid + phone/tablet parity):
- Modalities shown: RGB, depth, point cloud, wireframe/mesh
- Robot-mounted and handheld device presented as equivalent capture paths
- No on-screen file format, sync markers, UI, or calibration procedure

No schema change required; reinforces RGB (+ depth / lidar optional) and dual platform paths.

## Change log
- 2026-09-21: initial draft
- 2026-09-21: CTO lock — MCAP primary, RGB required, Android+ROS2, no HDF5 primary
- 2026-09-21: foxglove schemas locked with Reconstruct Eng for synthetic/Android path
