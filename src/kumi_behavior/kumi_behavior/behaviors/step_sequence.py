import csv
import math
from pathlib import Path

import py_trees
from ament_index_python.packages import get_package_share_directory
from builtin_interfaces.msg import Duration
from std_msgs.msg import Bool
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

# flip.csv rows [0, SQUAT_ROWS) = squat; rows [SQUAT_ROWS, end) = step completion
SQUAT_ROWS = 24


class KeyStepTriggered(py_trees.behaviour.Behaviour):
    def __init__(self, name, node):
        super().__init__(name)
        self.node = node

    def update(self):
        if self.node.step_triggered:
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE


class ExecuteStepSequence(py_trees.behaviour.Behaviour):
    _PHASE1 = 1       # publish squat rows
    _PHASE2_SEND = 2  # send rotation goal once
    _PHASE2_WAIT = 3  # wait for rotation to complete
    _PHASE3 = 4       # publish modified step rows

    def __init__(self, name, node):
        super().__init__(name)
        self.node = node
        self._phase = self._PHASE1
        self._row_idx = 0
        self._phase2_start = None
        self._rows_squat: list = []
        self._rows_step: list = []
        self._last_positions: list = [0.0] * 6
        self._enable_pub = node.create_publisher(
            Bool, 'kumi_seq_traj_controller/enabled', 10
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_csv(self):
        pkg = Path(get_package_share_directory('kumi_control'))
        all_rows = []
        with open(pkg / 'moves' / 'flip.csv') as f:
            for line in csv.reader(f):
                all_rows.append([math.radians(float(v)) for v in line])

        self._rows_squat = all_rows[:SQUAT_ROWS]
        self._rows_step_base = all_rows[SQUAT_ROWS:]  # no offset yet

    def _apply_step_offset(self):
        # Called when Phase 1 ends — captures angle_index at that moment
        offset = math.radians(self.node.angle_index * self.node.step_deg)
        self._rows_step = []
        for row in self._rows_step_base:
            modified = list(row)
            modified[2] += offset  # front_ank_z is column index 2
            self._rows_step.append(modified)
        self.node.get_logger().info(
            f'StepSequence: offset applied — angle_index={self.node.angle_index}'
            f' ({math.degrees(offset):.1f}°)'
        )

    def _pub_row(self, positions: list):
        traj = JointTrajectory()
        traj.joint_names = self.node.joint_names
        pt = JointTrajectoryPoint()
        pt.positions = positions
        pt.time_from_start = Duration(sec=0, nanosec=20_000_000)
        traj.points.append(pt)
        self.node.traj_pub.publish(traj)
        self._last_positions = list(positions)

    def _pub_rotation(self):
        # Prefer live joint states; fall back to last published positions
        positions = [
            self.node.current_joint_positions.get(j, self._last_positions[i])
            for i, j in enumerate(self.node.joint_names)
        ]
        positions[2] = math.radians(self.node.angle_index * self.node.step_deg)

        wait_sec = self.node.rotation_wait_sec
        traj = JointTrajectory()
        traj.joint_names = self.node.joint_names
        pt = JointTrajectoryPoint()
        pt.positions = positions
        pt.time_from_start = Duration(
            sec=int(wait_sec),
            nanosec=int((wait_sec % 1) * 1_000_000_000),
        )
        traj.points.append(pt)
        self.node.traj_pub.publish(traj)

    # ------------------------------------------------------------------
    # py_trees lifecycle
    # ------------------------------------------------------------------

    def initialise(self):
        self._load_csv()
        msg = Bool()
        msg.data = False
        self._enable_pub.publish(msg)  # ensure CSV controller is silent
        self._row_idx = 0
        self._phase = self._PHASE1
        self.node.get_logger().info('StepSequence: Phase 1 — squat')

    def update(self):
        if self._phase == self._PHASE1:
            if self._row_idx < len(self._rows_squat):
                self._pub_row(self._rows_squat[self._row_idx])
                self._row_idx += 1
                return py_trees.common.Status.RUNNING
            self._phase = self._PHASE2_SEND
            self.node.get_logger().info('StepSequence: Phase 2 — rotate ankle')
            return py_trees.common.Status.RUNNING

        if self._phase == self._PHASE2_SEND:
            self._pub_rotation()
            self._phase2_start = self.node.get_clock().now()
            self._phase = self._PHASE2_WAIT
            return py_trees.common.Status.RUNNING

        if self._phase == self._PHASE2_WAIT:
            elapsed = (
                self.node.get_clock().now() - self._phase2_start
            ).nanoseconds / 1e9
            if elapsed >= self.node.rotation_wait_sec + 0.5:
                self._row_idx = 0
                self._phase = self._PHASE3
                self.node.get_logger().info('StepSequence: Phase 3 — step')
            return py_trees.common.Status.RUNNING

        if self._phase == self._PHASE3:
            if self._row_idx < len(self._rows_step):
                self._pub_row(self._rows_step[self._row_idx])
                self._row_idx += 1
                return py_trees.common.Status.RUNNING
            self.node.step_triggered = False
            self._phase = self._PHASE1
            self.node.get_logger().info('StepSequence: complete')
            return py_trees.common.Status.SUCCESS

        return py_trees.common.Status.FAILURE

    def terminate(self, new_status):
        self._phase = self._PHASE1
        self._row_idx = 0
