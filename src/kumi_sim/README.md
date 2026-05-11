# kumi_sim

Gazebo simulation support for `kumi_stack` — worlds, models, robot spawning utilities, and the simulation launch files.

---

## Contents

| Path | Purpose |
|---|---|
| `worlds/*.sdf` | SDF world files |
| `models/` | Auxiliary world models (e.g. real-world stairs) |
| `launch/sim.launch.py` | Start Gazebo with a chosen world |
| `launch/robot_runtime.launch.py` | Robot spawn + controller spawner |
| `kumi_sim/spawn_despawn_node.py` | Service-based spawn/despawn helper used by the Gazebo GUI plugin |
| `config/kumi_gui.config` | Custom Gazebo GUI layout (loads `my_gz_gui_plugin`) |

---

## Worlds

| World | Description |
|---|---|
| `my_empty` | Empty ground plane (default) |
| `stairs` | Stairs world for locomotion tests |
| `piazza` | Open piazza scene |

Pass `world:=<name>` to `sim_bringup.launch.py` or `sim.launch.py`.

---

## Architecture

`kumi_sim` is the Gazebo-side half of the bringup. The launch orchestration is:

```
kumi_bringup/sim_bringup.launch.py
├── kumi_sim/sim.launch.py            ← starts Gazebo + bridges /clock
└── kumi_sim/robot_runtime.launch.py  ← spawns robot, brings up controller manager
```

The custom Gazebo GUI layout in `config/kumi_gui.config` loads the [`my_gz_gui_plugin`](../my_gz_gui_plugin/README.md) panel inside the simulator sidebar.

---

## Spawn / despawn at runtime

`kumi_sim/spawn_despawn_node.py` exposes ROS 2 services that the Gazebo GUI plugin calls to dynamically add or remove robots while the simulation is running. This is how the *Spawn* and *Despawn* buttons in the operator panel work.

The node is started automatically by `sim_bringup.launch.py`.

---

## Standalone Gazebo

Start Gazebo with a world (no robot, no controllers):

```bash
ros2 launch kumi_sim sim.launch.py world:=stairs
```

Arguments:

| Argument | Default | Description |
|---|---|---|
| `world` | `my_empty` | World name |
| `gui` | `true` | Open the Gazebo GUI |
| `gui_config` | `config/kumi_gui.config` | Override GUI layout |

To spawn a robot into an already-running Gazebo:

```bash
ros2 launch kumi_sim robot_runtime.launch.py robot_name:=bruno
```
