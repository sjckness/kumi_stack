# kumi_bringup

Top-level launch orchestration for `kumi_stack`. Composes the robot description, Gazebo, controllers, and the behavior tree into a single command.

---

## Launch files

| File | Purpose |
|---|---|
| `launch/sim_bringup.launch.py` | Full Gazebo simulation stack |

---

## `sim_bringup.launch.py`

Brings up, in this order:

1. **Gazebo** with the chosen world (`kumi_sim/sim.launch.py`)
2. **Robot description** publisher (`kumi_description/description.launch.py`)
3. **Robot spawn** in the world, delayed by `spawn_delay`
4. **Controller manager** and spawners, delayed by `spawner_delay`
5. **Behavior tree** node (`kumi_behavior/bt_node`)
6. *(Optional)* **RViz** and the **control GUI**

### Arguments

| Argument | Default | Description |
|---|---|---|
| `world` | `my_empty` | World name (`my_empty`, `stairs`, `piazza`) |
| `robot_name` | `bruno` | Name of the spawned robot |
| `ros_namespace` | `bruno` | ROS namespace for controllers and nodes |
| `robot_xacro` | `kumi.xacro` | Xacro file to use |
| `enable_sensors` | `true` | Enable front RGB + depth cameras |
| `use_sim_time` | `true` | Source clock from `/clock` |
| `use_rviz` | `false` | Launch RViz |
| `use_joint_state_publisher_gui` | `false` | Joint state publisher GUI |
| `use_control_gui` | `false` | Launch `kumi_control_gui` |
| `use_keyboard` | `false` | Launch the keyboard control node |
| `spawn_delay` | `8.0` | Seconds before spawning the robot |
| `spawner_delay` | `10.0` | Seconds before activating controllers |

### Example

```bash
ros2 launch kumi_bringup sim_bringup.launch.py \
  world:=stairs \
  enable_sensors:=true \
  use_control_gui:=true
```

---

## Composition diagram

```
sim_bringup.launch.py
├── kumi_sim/sim.launch.py                   ← Gazebo + /clock bridge
├── kumi_description/description.launch.py   ← robot_state_publisher
├── kumi_sim/robot_runtime.launch.py         ← spawn + controller_manager
├── kumi_control/control.launch.py           ← controller spawners + control GUI
└── kumi_behavior/bt_node                    ← py_trees BT @ 10 Hz
```

Each child launch is documented next to its source — see [`kumi_sim`](../kumi_sim/README.md), [`kumi_description`](../kumi_description/README.md), [`kumi_control`](../kumi_control/README.md), and [`kumi_behavior`](../kumi_behavior/README.md).
