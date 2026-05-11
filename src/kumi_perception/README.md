# kumi_perception

Perception pipeline for the Kumi robot.

> **Status:** placeholder. The package is currently a minimal ROS 2 scaffold; the perception pipeline is on the roadmap.

---

## Intended scope

The package is reserved for the perception side of the stack. It will consume the on-robot cameras (front RGB + depth, plus the optional corner RGB / depth pairs declared in [`kumi_description`](../kumi_description/README.md)) and produce higher-level state for downstream consumers — the behavior tree first, eventually a planner.

Planned components:

| Component | Responsibility |
|---|---|
| Sensor preprocessing | Rectification, time synchronization, undistortion |
| Object detection | Lightweight detector on the front RGB stream |
| Free-space estimation | Depth-based obstacle map for foot placement |
| Terrain classification | Per-step terrain label fed into the gait selector |

---

## Inputs

The package will subscribe to the standard camera topics published by the active simulator:

| Topic | Type |
|---|---|
| `/<robot>/front_camera/image` | `sensor_msgs/Image` |
| `/<robot>/front_camera/camera_info` | `sensor_msgs/CameraInfo` |
| `/<robot>/front_depth/image` | `sensor_msgs/Image` |
| `/<robot>/front_depth/camera_info` | `sensor_msgs/CameraInfo` |

---

## Outputs

To be defined as the pipeline takes shape. At minimum:

- `kumi_perception/free_space` — local obstacle / free-space grid
- `kumi_perception/terrain_class` — terrain class fed into gait switching

---

## Status

The current source contains only the ROS 2 package scaffolding (`package.xml`, `setup.py`). Nodes will be added incrementally.
