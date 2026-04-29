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
SMOOTH_START = 171 - SQUAT_ROWS  # Phase 3 index where descent begins


class KeyStepTriggered(py_trees.behaviour.Behaviour):
    def __init__(self, name, node):
        super().__init__(name)
        self.node = node

    def update(self):
        if self.node.step_triggered:
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE


class ExecuteStepSequence(py_trees.behaviour.Behaviour):
    _PHASE1 = 1  # publish squat rows
    _PHASE2 = 2  # interactive rotation — wait for second UP press
    _PHASE3 = 3  # publish modified step rows

    def __init__(self, name, node):
        super().__init__(name)
        self.node = node
        self._phase = self._PHASE1
        self._row_idx = 0
        self._rows_squat: list = []
        self._rows_step_base: list = []
        self._rows_step: list = []
        self._last_positions: list = [0.0] * 6
        self._last_angle_sent: int | None = None
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
        # Called when UP is confirmed after Phase 2.
        # front_ank_z follows a cosine descent: starts at the selected angle
        # (robot is already there) and returns smoothly to 0 by the last row.
        offset = math.radians(self.node.angle_index * self.node.step_deg)
        n = len(self._rows_step_base)
        self._rows_step = []
        smooth_len = n - SMOOTH_START  # rows in the descent segment
        for i, row in enumerate(self._rows_step_base):
            if i < SMOOTH_START:
                factor = 1.0
            else:
                t = (i - SMOOTH_START) / (smooth_len - 1) if smooth_len > 1 else 1.0
                factor = 1.0 - t * t * t * (t * (6.0 * t - 15.0) + 10.0)
            modified = list(row)
            modified[2] = offset * factor  # column index 2 = front_ank_z
            self._rows_step.append(modified)
        self.node.get_logger().info(
            f'StepSequence: cosine descent applied — '
            f'angle_index={self.node.angle_index} ({math.degrees(offset):.1f}°)'
            f', rows={n}'
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
        # Hold all joints at squat-end position, move only front_ank_z.
        # Prefer live joint states; fall back to last published positions.
        positions = [
            self.node.current_joint_positions.get(j, self._last_positions[i])
            for i, j in enumerate(self.node.joint_names)
        ]
        positions[2] = math.radians(self.node.angle_index * self.node.step_deg)

        traj = JointTrajectory()
        traj.joint_names = self.node.joint_names
        pt = JointTrajectoryPoint()
        pt.positions = positions
        pt.time_from_start = Duration(sec=0, nanosec=500_000_000)  # 0.5 s per move
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
        self._last_angle_sent = None
        self._phase = self._PHASE1
        self.node.get_logger().info('StepSequence: Phase 1 — squat')

    def update(self):
        if self._phase == self._PHASE1:
            if self._row_idx < len(self._rows_squat):
                self._pub_row(self._rows_squat[self._row_idx])
                self._row_idx += 1
                return py_trees.common.Status.RUNNING
            # Squat done — enter interactive rotation; clear trigger so next
            # UP press is treated as "confirm angle and step"
            self.node.step_triggered = False
            self._last_angle_sent = None
            self._phase = self._PHASE2
            self.node.get_logger().info(
                'StepSequence: Phase 2 — select angle with LEFT/RIGHT, then UP to step'
            )
            return py_trees.common.Status.RUNNING

        if self._phase == self._PHASE2:
            # Send a rotation command whenever angle_index changes
            if self.node.angle_index != self._last_angle_sent:
                self._pub_rotation()
                self._last_angle_sent = self.node.angle_index
            # UP pressed again → confirm and proceed to step
            if self.node.step_triggered:
                self.node.step_triggered = False
                self._apply_step_offset()
                self._row_idx = 0
                self._phase = self._PHASE3
                self.node.get_logger().info('StepSequence: Phase 3 — step')
            return py_trees.common.Status.RUNNING

        if self._phase == self._PHASE3:
            if self._row_idx < len(self._rows_step):
                self._pub_row(self._rows_step[self._row_idx])
                self._row_idx += 1
                return py_trees.common.Status.RUNNING
            self._phase = self._PHASE1
            self.node.get_logger().info('StepSequence: complete')
            return py_trees.common.Status.SUCCESS

        return py_trees.common.Status.FAILURE

    def terminate(self, new_status):
        self._phase = self._PHASE1
        self._row_idx = 0
