import csv
import math
from pathlib import Path

import py_trees
from ament_index_python.packages import get_package_share_directory
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

# Phase boundaries (0-indexed row numbers in flip.csv, rows 1-indexed in spec)
FRONT_TURN_START = 45   # spec rows 46–106
FRONT_TURN_END = 105
REAR_TURN_START = 150   # spec rows 151–240
REAR_TURN_END = 239

# Column indices (0-indexed) — authoritative per specification
FRONT_ANK_Z_COL = 2    # front_ank_z  → column 3 (1-indexed)
REAR_ANK_Z_COL = 5     # back_ank_z   → column 6 (1-indexed)

MAX_TURN_DEG = 20.0


def _load_csv() -> list:
    pkg = Path(get_package_share_directory('kumi_control'))
    rows = []
    with open(pkg / 'moves' / 'flip.csv') as f:
        for line in csv.reader(f):
            rows.append([math.radians(float(v)) for v in line])
    return rows


def _phase_info(idx: int):
    """Return (active_col, other_col, phase_end) for turning phases, or (None, None, None)."""
    if FRONT_TURN_START <= idx <= FRONT_TURN_END:
        return FRONT_ANK_Z_COL, REAR_ANK_Z_COL, FRONT_TURN_END
    if REAR_TURN_START <= idx <= REAR_TURN_END:
        return REAR_ANK_Z_COL, FRONT_ANK_Z_COL, REAR_TURN_END
    return None, None, None


class IsManualMode(py_trees.behaviour.Behaviour):
    """Gate condition: SUCCESS when manual_mode is True, FAILURE otherwise."""

    def __init__(self, name, node):
        super().__init__(name)
        self.node = node

    def update(self):
        return (
            py_trees.common.Status.SUCCESS
            if self.node.manual_mode
            else py_trees.common.Status.FAILURE
        )


class ManualIndexController(py_trees.behaviour.Behaviour):
    """Advances manual_current_index based on step inputs. Returns SUCCESS each tick."""

    def __init__(self, name, node):
        super().__init__(name)
        self.node = node

    def update(self):
        n = self.node.manual_row_count
        if n == 0:
            return py_trees.common.Status.SUCCESS

        should_step = self.node.manual_step_once or self.node.manual_continuous
        if self.node.manual_step_once:
            self.node.manual_step_once = False

        if should_step:
            self.node.manual_current_index = (self.node.manual_current_index + 1) % n

        return py_trees.common.Status.SUCCESS

    def terminate(self, new_status):
        self.node.manual_step_once = False
        self.node.manual_continuous = False


class ManualTurningController(py_trees.behaviour.Behaviour):
    """Loads CSV on activation and applies turning angle to modified_rows in-place.
    Returns SUCCESS each tick."""

    def __init__(self, name, node):
        super().__init__(name)
        self.node = node
        self._last_angle: float | None = None
        self._last_phase_col: int | None = None

    def initialise(self):
        base_rows = _load_csv()
        self.node.manual_modified_rows = base_rows  # start fresh each activation
        self.node.manual_row_count = len(base_rows)
        self._last_angle = None
        self._last_phase_col = None
        self.node.get_logger().info(
            f'ManualWalk: CSV loaded ({self.node.manual_row_count} rows), '
            f'index={self.node.manual_current_index}'
        )

    def _apply_angle(self, from_idx: int):
        col, other_col, phase_end = _phase_info(from_idx)
        if col is None:
            return
        angle_rad = math.radians(self.node.manual_angle)
        rows = self.node.manual_modified_rows
        for i in range(from_idx, phase_end + 1):
            row = list(rows[i])
            row[col] = angle_rad    # active turning joint
            row[other_col] = 0.0   # opposite turning joint hard-reset
            rows[i] = row

    def update(self):
        n = self.node.manual_row_count
        if n == 0:
            return py_trees.common.Status.SUCCESS

        idx = self.node.manual_current_index % n
        col, _other, _end = _phase_info(idx)

        angle_changed = self.node.manual_angle != self._last_angle
        phase_changed = col != self._last_phase_col

        if col is not None and (angle_changed or phase_changed):
            self._apply_angle(idx)
            self._last_angle = self.node.manual_angle
            self.node.get_logger().debug(
                f'ManualTurn: angle={self.node.manual_angle:.1f}° col={col} idx={idx}'
            )

        self._last_phase_col = col
        return py_trees.common.Status.SUCCESS

    def terminate(self, new_status):
        self._last_angle = None
        self._last_phase_col = None


class ManualCommandPublisher(py_trees.behaviour.Behaviour):
    """Publishes the trajectory row at current_index. Returns RUNNING to hold the branch."""

    def __init__(self, name, node):
        super().__init__(name)
        self.node = node

    def update(self):
        n = self.node.manual_row_count
        if n == 0:
            return py_trees.common.Status.RUNNING

        idx = self.node.manual_current_index % n
        positions = self.node.manual_modified_rows[idx]

        traj = JointTrajectory()
        traj.joint_names = self.node.joint_names
        pt = JointTrajectoryPoint()
        pt.positions = positions
        pt.time_from_start = Duration(sec=0, nanosec=20_000_000)
        traj.points.append(pt)
        self.node.traj_pub.publish(traj)

        return py_trees.common.Status.RUNNING
