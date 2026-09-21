> **Status:** draft — do not publish until the GitHub org (`youseftrk`) is confirmed.

# Architecture — open-real2sim-capture

Capture owns the **observation + calibration** half of Open Real2Sim. It records multi-sensor sessions from phones, tablets, and robots into a versioned bag that reconstruction and simulation can ingest without inventing alternate layouts.

## Role in Open Real2Sim

```
open-real2sim-capture          reconstruct (upstream/downstream of this path)
        │                              │
        ▼                              ▼
  capture session                 scene package
  (MCAP + manifest)          (visual + collision)
        │                              │
        └──────────────┬───────────────┘
                       ▼
              open-physical-sim
                       ↕
              open-env-commons
```

- **This repo emits:** `session.mcap` + `manifest.json` + calibration/provenance sidecars.
- **Does not emit:** Isaac/MuJoCo meshes, 3DGS/NeRF checkpoints, or Env Commons `env.json`. Those belong to reconstruct tooling and the other two public repos.
- **Reconstruct** (`open-real2sim-reconstruct`) is the fourth locked public repo: ingest capture bags, export scene packages. Capture documents the input half only.

## Components

| Component | Responsibility |
|-----------|----------------|
| Recording clients | Android (phone/tablet) and ROS2 robot paths; iOS deferred |
| MCAP writer | Primary on-disk stream store for all frame data |
| Sidecar JSON | `manifest.json`, `calibration/sensors.json`, `provenance/device.json` for discovery without scanning the bag |
| Python SDK (`or2s_capture`) | `write_synthetic_session`, `read_session`, `validate`, `import_rosbag2` |
| CLI (`or2s`) | `validate`, `write-synthetic`, `import-rosbag` (rosbag2 import may be stub in early v0) |

## Data flow

1. Device or robot produces RGB (required) plus optional depth / IMU / LiDAR / pose.
2. Writer stores frames on MCAP topics under `/or2s/...` (and `/tf` / `/tf_static` on the robot path).
3. Sidecars record schema id, stream index, intrinsics/extrinsics, and device provenance.
4. Downstream: reconstruct validates + normalizes the session, then exports a scene package for `open-physical-sim`. Env Commons may later reference capture session IDs in env provenance.

## Platforms (v0)

| Path | v0 scope |
|------|----------|
| ROS2 robot | Record → `or2s import-rosbag` → session package |
| Android phone/tablet | RGB required; depth when Camera2/ARCore makes it easy; tablet uses the phone path |
| iOS | Deferred |

## Sync and coordinates

- Per-frame timestamps; default time domain `unix_ns`. No silent clock domains — declare ROS time + offset in provenance when used.
- Camera optical convention: **RDF** (x right, y down, z forward), locked as `coordinate_convention: RDF_optical`.
- Extrinsics: `T_parent_sensor` is parent ← sensor; quaternion **xyzw**; units **meters**.

## Ownership

| Surface | Owner |
|---------|-------|
| Bag layout, MCAP topics, `manifest.json` / calibration / provenance schemas | Capture Lead |
| Scene package (`scene.json`, splat, collision mesh) | Reconstruct + Sim Runtime |
| Gymnasium env ids / robot URDFs | Physical Sim / Policy |
| Env registry manifests | Env Commons |

## Non-goals (v0)

- Closed cloud capture requirement or SaaS-only recording.
- HDF5 as the primary bag format (rosbag2 is a secondary **import** path only).
- Emitting sim-ready meshes or splat assets from this repo.
- Multi-rig merge into one world frame (single-session ingest for reconstruct v0; multi-session co-registration is open).
- Marketplace incentive programs (out of scope for v0 public docs).

## Demo reference robots

Unitree H1 and G1 appear elsewhere in Open Real2Sim as **demo reference robots** for sim and policy smoke. Capture itself is robot-agnostic: any ROS2 rig that can fill the locked topics is in scope.
