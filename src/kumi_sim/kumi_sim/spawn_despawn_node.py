import os

import xacro
import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from std_srvs.srv import Trigger
from std_msgs.msg import String
from subprocess import DEVNULL, Popen, run, PIPE


class RobotManager(Node):
    """
    Nodo ROS 2 per gestire spawn e despawn di robot in Gazebo Harmonic.
    Processa kumi.xacro e spawna tramite ros_gz_sim create.

    Parametri:
        world           (str)   — nome del world in Gazebo        (default: 'my_empty')
        xacro_file      (str)   — nome del file xacro             (default: 'kumi.xacro')
        robot_name      (str)   — nome del robot nel xacro        (default: 'bruno')
        ros_namespace   (str)   — namespace ROS 2                 (default: 'kumi')
        enable_sensors  (bool)  — abilita sensori nel xacro       (default: true)
        spawn_x/y/z     (float) — posizione di spawn              (default: 0.0/0.0/0.1)

    Servizi esposti:
        /spawn_robot  (std_srvs/Trigger) — spawna un nuovo robot
        /despawn_all  (std_srvs/Trigger) — rimuove tutti i robot in scena
    """

    MODEL_BLACKLIST = {'ground_plane', 'sun', 'default', 'skybox'}

    def __init__(self):
        super().__init__('robot_manager')

        self.world_name = (
            self.declare_parameter('world', 'my_empty')
            .get_parameter_value().string_value
        )

        desc_share = get_package_share_directory('kumi_description')
        ctrl_share = get_package_share_directory('kumi_control')

        xacro_file = (
            self.declare_parameter('xacro_file', 'kumi.xacro')
            .get_parameter_value().string_value
        )
        if os.path.isabs(xacro_file):
            self.xacro_path = xacro_file
        else:
            self.xacro_path = os.path.join(desc_share, 'urdf', xacro_file)

        self.robot_name = (
            self.declare_parameter('robot_name', 'bruno')
            .get_parameter_value().string_value
        )
        self.ros_namespace = (
            self.declare_parameter('ros_namespace', 'kumi')
            .get_parameter_value().string_value
        )
        self.enable_sensors = (
            self.declare_parameter('enable_sensors', True)
            .get_parameter_value().bool_value
        )
        self.spawn_x = (
            self.declare_parameter('spawn_x', 0.0)
            .get_parameter_value().double_value
        )
        self.spawn_y = (
            self.declare_parameter('spawn_y', 0.0)
            .get_parameter_value().double_value
        )
        self.spawn_z = (
            self.declare_parameter('spawn_z', 0.4)
            .get_parameter_value().double_value
        )

        self.xacro_mappings = {
            'use_sim': 'true',
            'enable_sensors': str(self.enable_sensors).lower(),
            'robot_name': self.robot_name,
            'pkg_share': desc_share,
            'control_config': os.path.join(
                ctrl_share, 'config', 'trajectory_control_config.yaml'
            ),
            'ros_namespace': self.ros_namespace,
        }

        self._robot_counter = 0
        self._runtime_processes: dict[str, Popen] = {}

        self.create_service(Trigger, 'spawn_robot', self._spawn_callback)
        self.create_service(Trigger, 'despawn_all', self._despawn_all_callback)
        self.create_subscription(
            String,
            '/kumi_sim/register_robot',
            self._register_robot_callback,
            10,
        )
        self.create_subscription(
            String,
            '/kumi_sim/unregister_robot',
            self._unregister_robot_callback,
            10,
        )

        self.get_logger().info(
            f"RobotManager avviato — world: '{self.world_name}', "
            f"xacro: '{self.xacro_path}'"
        )

    # ------------------------------------------------------------------ #
    #  Spawn                                                               #
    # ------------------------------------------------------------------ #

    def _process_xacro(self) -> str | None:
        try:
            doc = xacro.process_file(self.xacro_path, mappings=self.xacro_mappings)
            return doc.toxml()
        except Exception as e:
            self.get_logger().error(f"Errore nel processing xacro: {e}")
            return None

    def spawn_robot(self, name: str,
                    x: float = 0.0, y: float = 0.0, z: float = 0.1) -> bool:
        robot_desc = self._process_xacro()
        if robot_desc is None:
            return False

        result = run(
            [
                'ros2', 'run', 'ros_gz_sim', 'create',
                '-string', robot_desc,
                '-name', name,
                '-x', str(x),
                '-y', str(y),
                '-z', str(z),
            ],
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            env=os.environ.copy(),
        )

        if result.returncode == 0:
            self.get_logger().info(f"Spawnato '{name}' in ({x}, {y}, {z})")
            return True

        self.get_logger().error(
            f"Spawn di '{name}' fallito: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
        return False

    def _spawn_callback(self, request, response):
        name = f'robot_{self._robot_counter}'
        self._robot_counter += 1

        ok = self.spawn_robot(
            name=name,
            x=self.spawn_x,
            y=self.spawn_y,
            z=self.spawn_z,
        )

        response.success = ok
        response.message = name if ok else f"Spawn di '{name}' fallito"
        return response

    def _launch_runtime_stack(self, robot_name: str):
        if not robot_name:
            return

        existing = self._runtime_processes.get(robot_name)
        if existing and existing.poll() is None:
            return

        process = Popen(
            [
                'ros2', 'launch', 'kumi_sim', 'robot_runtime.launch.py',
                f'namespace:={robot_name}',
                f'robot_name:={robot_name}',
                'use_sim_time:=true',
                f'enable_sensors:={str(self.enable_sensors).lower()}',
                'use_gz_bridge:=true',
                'use_control_gui:=false',
            ],
            stdout=DEVNULL,
            stderr=DEVNULL,
            text=True,
            env=os.environ.copy(),
        )
        self._runtime_processes[robot_name] = process
        self.get_logger().info(f"Runtime stack avviato per '{robot_name}'")

    def _stop_runtime_stack(self, robot_name: str):
        process = self._runtime_processes.pop(robot_name, None)
        if process is None:
            return

        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except Exception:
                process.kill()
        self.get_logger().info(f"Runtime stack fermato per '{robot_name}'")

    def _register_robot_callback(self, msg: String):
        robot_name = msg.data.strip()
        if not robot_name:
            return
        self._launch_runtime_stack(robot_name)

    def _unregister_robot_callback(self, msg: String):
        robot_name = msg.data.strip()
        if not robot_name:
            return
        self._stop_runtime_stack(robot_name)

    # ------------------------------------------------------------------ #
    #  Despawn                                                             #
    # ------------------------------------------------------------------ #

    def get_active_models(self) -> list[str]:
        result = run(
            ['gz', 'model', '--list'],
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            env=os.environ.copy(),
        )

        if result.returncode != 0:
            self.get_logger().error(
                f"Impossibile ottenere la lista modelli: {result.stderr.strip()}"
            )
            return []

        models = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped.startswith('- '):
                continue
            name = stripped[2:]
            if name not in self.MODEL_BLACKLIST:
                models.append(name)

        return models

    def despawn_robot(self, name: str) -> bool:
        result = run(
            [
                'gz', 'service',
                '-s', f'/world/{self.world_name}/remove/blocking',
                '--reqtype', 'gz.msgs.Entity',
                '--reptype', 'gz.msgs.Boolean',
                '--req', f'name: "{name}", type: 2',
                '--timeout', '5000',
            ],
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            env=os.environ.copy(),
        )

        if result.returncode == 0 and 'true' in result.stdout.lower():
            self.get_logger().info(f"Rimosso '{name}'")
            return True

        self.get_logger().warn(
            f"Despawn di '{name}' fallito: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
        return False

    def _despawn_all_callback(self, request, response):
        models = self.get_active_models()

        if not models:
            self.get_logger().info("Nessun modello da rimuovere")
            response.success = True
            response.message = 'Nessun modello presente in scena'
            return response

        self.get_logger().info(f"Modelli da rimuovere: {models}")

        removed, failed = [], []
        for name in models:
            if self.despawn_robot(name):
                self._stop_runtime_stack(name)
                removed.append(name)
            else:
                failed.append(name)

        response.success = len(failed) == 0
        response.message = (
            f"Rimossi {len(removed)}/{len(models)}"
            + (f" — falliti: {failed}" if failed else "")
        )
        return response


# ------------------------------------------------------------------ #
#  Entrypoint                                                          #
# ------------------------------------------------------------------ #

def main(args=None):
    rclpy.init(args=args)
    node = RobotManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        for robot_name in list(node._runtime_processes.keys()):
            node._stop_runtime_stack(robot_name)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
