"""
Control with teleop, with backflip
"""

#!/usr/bin/env python3
from operator import index

import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

import csv
import math
import threading
import sys
import termios
import tty
import time
import select
from pathlib import Path
import yaml
from ament_index_python.packages import get_package_share_directory

DEFAULT_JOINT_NAMES = [
    'front_sh', 'front_ank_y', 'front_ank_z',
    'rear_sh', 'rear_ank_y', 'rear_ank_z'
]

POINT_DURATION = 0.85


class CSVJointTrajectory(Node):
    def __init__(self):
        
        super().__init__('csv_joint_trajectory')

        # Publisher
        self.pub = self.create_publisher(
            JointTrajectory,
            '/multi_joint_trajectory_controller/joint_trajectory',
            10
        )

        pkg_share = Path(get_package_share_directory('kumi'))

        csv_files = {
            1: pkg_share / 'resource/flip.csv',
            2: pkg_share / 'resource/bflip.csv',
            3: pkg_share / 'resource/flip_sx.csv',
            4: pkg_share / 'resource/flip_dx.csv',
            5: pkg_share / 'resource/bflip_sx.csv',
            6: pkg_share / 'resource/bflip_dx.csv',
            7: pkg_share / 'resource/rac.csv',
            8: pkg_share / 'resource/extend.csv'
        }
        
        controller_config = pkg_share / 'config/trajectory_control_config.yaml'

        # Angle for turning
        self.turn = 0.2

        # Initial position
        self.position = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        # Joint names (auto-read by the controller when possible)
        self.joint_names = self._load_joint_names(controller_config)
        self.declare_parameter('joint_names', self.joint_names)
        self.joint_names = [str(j) for j in self.get_parameter('joint_names').value]

        # iterate to load all the positions inside a dictionary
        self.trajectories = {}
        for movement_id, path in csv_files.items():
            if path.exists():
                self.trajectories[movement_id] = self.load_csv_in_radians(path,len(self.joint_names))
                self.get_logger().info(f"Uploaded {len(self.trajectories[movement_id])} poses from CSV {path.name} (in radiants).")
            else:
                raise FileNotFoundError(f"CSV not found: {path.name}, movement {movement_id}")  
        
        
        self.get_logger().info("Ready.\nW/S: straight frontflip/backflip.\nQ/A: sx frontflip/backflip.\nE/D: dx frontflip/backflip.\nC: compact.\nPress R to reset. Ctrl+C to exit.")

        self.lock = threading.Lock()

        # Management of raw terminal (we save and restore it)
        self.fd = sys.stdin.fileno()
        self.old_term = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)  # less invasive than setraw

        # Stop flag for the thread
        self._stop_event = threading.Event()

        # Thread to listen for keyboard input (non-blocking)
        self.keyboard_thread = threading.Thread(target=self.keyboard_listener, daemon=True)
        self.keyboard_thread.start()

        # When ROS is shutting down, stop the thread and restore the terminal
        rclpy.get_default_context().on_shutdown(self.on_shutdown)

    def on_shutdown(self):
        # Signal stop to the thread and restore the terminal
        self._stop_event.set()
        try:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_term)
        except Exception:
            pass

    def destroy_node(self):
        # Ensure restoration even if destroy_node is called explicitly
        self.on_shutdown()
        super().destroy_node()

    def load_csv_in_radians(self, path: Path, expected_len: int):
        """
        use same function to upload positions from the different csv files
        """

        positions = []
        with open(path, 'r') as f:
            reader = csv.reader(f)
            for row_idx, row in enumerate(reader, start=1):
                if not row:
                    continue
                if len(row) != expected_len:
                    raise ValueError(
                        f"Row {row_idx} of {path} has {len(row)} values: "
                        f"expected {expected_len} (joint: {self.joint_names})"
                    )
                degrees = [float(v) for v in row]
                radians = [math.radians(v) for v in degrees]
                positions.append(radians)

        return positions                                                              # saved in positions the list of the positions in radians, read from the csv file, where each row is a list of joint angles in radians. 

    def getch_nonblocking(self, timeout_s: float = 0.1):
        # Returns 1 character if available within timeout, otherwise None.
        dr, _, _ = select.select([sys.stdin], [], [], timeout_s)
        if dr:
            return sys.stdin.read(1)
        return None

    def keyboard_listener(self):

        KEY_MAP = {
            'w':1, 's':2,       # flip, bflip
            'q':3, 'e':4,       # flip_sx, bflip_sx
            'a':5, 'd':6,       # flip_dx, bflip_dx
            'c':7, 'v':8        # rac (compact), extend
        }

        self.last_ch = None
        rotation = 0

        # Loop until ROS is ok and we are not asked to stop
        while rclpy.ok() and not self._stop_event.is_set():
            ch = self.getch_nonblocking(0.1)
            with self.lock:
                if ch in KEY_MAP:
                    self.send_points(KEY_MAP[ch],rotation)
                    self.last_ch = ch
                    rotation = 0                                          # reinitialization of the rotation value
                if ch == 'z':       # turn left
                    if self.last_ch not in ('z','x'):
                        self.position = list(self.trajectories[7][-1])    # reset the start position
                    self.position[2] += self.turn
                    self.next_pos()
                    self.last_ch = ch
                    rotation = self.position[2]                           # total of rotation
                if ch == 'x':       # turn right
                    if self.last_ch not in ('z','x'):
                        self.position = list(self.trajectories[7][-1])    # reset the start position
                    self.position[2] -= self.turn
                    self.next_pos() 
                    self.last_ch = ch
                    rotation = self.position[2]                           # total of rotation
                if ch == 'r':       # reset
                    self.position = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                    self.next_pos()
                    self.last_ch = ch                

    def send_points(self, movement_id: int, rotation: float):
        """
        Sends all positions one by one in the trajectory for the csv file corresponding to movement_id
        """

        positions_list = self.trajectories.get(movement_id)      # select set of positions according to the movement to execute
        if not positions_list:
            self.get_logger().warn("CSV empty: no points to send.")
            return

        for idx, positions in enumerate(positions_list):         # read index and positions from the list of positions on the CSV file
            traj = JointTrajectory()
            traj.joint_names = self.joint_names

            # add saved yaw to joint 3
            pos = list(positions)
            pos[2] += rotation

            point = JointTrajectoryPoint()
            point.positions = pos
            point.time_from_start = Duration(sec=0, nanosec=500_000_000)  # 0.5s

            traj.points.append(point)
            self.pub.publish(traj)
            self.get_logger().info(f"[{idx+1}/{len(positions_list)}] sent point: {pos}")

            time.sleep(POINT_DURATION)  # wait for the position to be reached before sending the next one

        if movement_id==7:      # if the movement is compactation, possible next manipulations: yaw and expand + reset
            self.get_logger().info("Compactation complete. Z/X: rotate the robot. V: expand.\nPress R to reset. Ctrl+C to exit.")
        else:
            self.get_logger().info("Sequence finished.\nW/S: straight frontflip/backflip.\nQ/A: sx frontflip/backflip.\nE/D: dx frontflip/backflip.\nC: compact.\nPress R to reset. Ctrl+C to exit.") 

    def next_pos(self):
        """
        Published a single pose (used for turn and reset to initial position)
        """
        traj = JointTrajectory()
        traj.joint_names = self.joint_names

        point = JointTrajectoryPoint()
        point.positions = self.position
        point.time_from_start = Duration(sec=0, nanosec=500_000_000)  # 0.5s

        traj.points.append(point)
        self.pub.publish(traj)
        self.get_logger().info(f"Point published: {point.positions}")
        self.get_logger().info("Sequence finished.\nW/S: straight frontflip/backflip.\nQ/A: sx frontflip/backflip.\nE/D: dx frontflip/backflip.\nC: compact.\nPress R to reset. Ctrl+C to exit.") 

    def _load_joint_names(self, config_path: Path):
        if not config_path.exists():
            self.get_logger().warn(
                f"Config {config_path} not found. Using default list {DEFAULT_JOINT_NAMES}"
            )
            return DEFAULT_JOINT_NAMES.copy()

        try:
            data = yaml.safe_load(config_path.read_text()) or {}
            joints = (
                data.get('multi_joint_trajectory_controller', {})
                .get('ros__parameters', {})
                .get('joints', [])
            )
            if not joints:
                self.get_logger().warn(
                    f"No 'joints' list found in {config_path}. Using default {DEFAULT_JOINT_NAMES}"
                )
                return DEFAULT_JOINT_NAMES.copy()
            return [str(j) for j in joints]
        except Exception as exc:
            self.get_logger().warn(
                f"Error reading {config_path}: {exc}. Using default {DEFAULT_JOINT_NAMES}"
            )
            return DEFAULT_JOINT_NAMES.copy()


def main(args=None):
    rclpy.init(args=args)

    node = CSVJointTrajectory()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        # Ctrl+C almost always enters here, but if it doesn't:
        # on_shutdown/destroy_node restore anyways
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
