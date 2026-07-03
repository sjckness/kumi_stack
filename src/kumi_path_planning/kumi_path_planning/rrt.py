"""
RRT path planner -- ported from the user's MATLAB implementation.

This keeps the original algorithm's structure on purpose:
  - sample a random point anywhere on the map
  - find the nearest existing node
  - step toward the sample by at most `eps` to get a *target* point
    (this is NOT the move taken -- just a direction to aim for)
  - Monte Carlo over `n_samples` candidate headings within +/- max_turn_angle
    of the previous node's heading, each producing a FIXED-LENGTH step of
    `b_length` -- pick whichever candidate lands closest to the target point
  - collision-check the straight segment AND the swept turning arc the
    robot sweeps through while changing heading
  - commit the node if both checks pass, track heading for the next iteration

Two bugs from the original MATLAB were fixed during the port:
  1. The stored maneuver angle indexed by the *parent* node index instead of
     the chosen candidate's index (manuver_angle(zz) = alpha_samples(I)).
  2. The stored heading indexed into the post-filter candidate list using an
     index computed on the post-filter list, but applied it to the
     *pre-filter* heading array (alpha_save(zz) = alpha_wrh(idx_best)), which
     drift apart whenever any candidate got rejected for being out of bounds.
This port avoids both by tracking (position, heading) together in lockstep
for each candidate, so there's never a separate index to misalign.

Works in continuous WORLD coordinates (meters), not grid indices -- this
matches how the MATLAB version queries occupancyMap/checkOccupancy directly,
and it's the right fit here since b_length is a physical stride length and
heading is a physical orientation, not grid-cell concepts.
"""

import math
import random

import numpy as np


class WorldOccupancyGrid:
    """
    Thin wrapper so the planner can query occupancy in world meters,
    mirroring MATLAB's occupancyMap + checkOccupancy.

    binary_grid: 2D numpy array indexed [row][col] i.e. [y][x], 0=free/1=occupied.
    resolution: meters per cell.
    origin_x, origin_y: world coordinates of grid cell (0, 0).
    """

    def __init__(self, binary_grid, resolution, origin_x, origin_y):
        self.grid = np.asarray(binary_grid)
        self.height, self.width = self.grid.shape
        self.resolution = resolution
        self.origin_x = origin_x
        self.origin_y = origin_y

    def world_limits(self):
        x_min = self.origin_x
        x_max = self.origin_x + self.width * self.resolution
        y_min = self.origin_y
        y_max = self.origin_y + self.height * self.resolution
        return x_min, x_max, y_min, y_max

    def is_occupied(self, x, y):
        return self.any_occupied(np.array([x]), np.array([y]))

    def any_occupied(self, xs, ys):
        """Vectorized occupancy check over arrays of world coordinates.
        Out-of-bounds points count as occupied (conservative default --
        see the earlier discussion on treating unknown/out-of-map space)."""
        xs = np.asarray(xs)
        ys = np.asarray(ys)
        gx = np.floor((xs - self.origin_x) / self.resolution).astype(int)
        gy = np.floor((ys - self.origin_y) / self.resolution).astype(int)
        out_of_bounds = (gx < 0) | (gx >= self.width) | (gy < 0) | (gy >= self.height)
        occupied = np.zeros_like(out_of_bounds)
        in_bounds = ~out_of_bounds
        occupied[in_bounds] = self.grid[gy[in_bounds], gx[in_bounds]] == 1
        return bool(np.any(occupied | out_of_bounds))


class Node:
    __slots__ = ("x", "y", "heading", "parent", "maneuver_angle")

    def __init__(self, x, y, heading, parent=None, maneuver_angle=0.0):
        self.x = x
        self.y = y
        self.heading = heading          # absolute heading at this node (radians)
        self.parent = parent            # index into the nodes list, or None for root
        self.maneuver_angle = maneuver_angle  # turn relative to parent's heading


class RRTPlanner:
    def __init__(self, occ_map, eps=0.4, b_length=0.3, n_samples=500,
                 max_turn_angle=math.pi / 2, goal_tolerance=0.3,
                 max_iterations=300, line_points=100, sector_points=60):
        """
        occ_map: WorldOccupancyGrid instance.
        eps: max distance (m) used to compute the "target" direction point --
             mirrors MATLAB's `eps`. NOT the actual step length.
        b_length: fixed stride length (m) actually taken each accepted step --
             mirrors MATLAB's `b_length`. Set this to your robot's real step length.
        n_samples: number of candidate headings tried via Monte Carlo each iteration.
        max_turn_angle: max heading change per step (radians), each side --
             mirrors the +/- 90 degree limit in MATLAB.
        goal_tolerance: success distance to goal, in meters.
        max_iterations: RRT iterations before giving up.
        line_points, sector_points: collision-check sampling density. Lower
             these if planning is too slow; raise for finer safety margins.
        """
        self.map = occ_map
        self.eps = eps
        self.b_length = b_length
        self.n_samples = n_samples
        self.max_turn_angle = max_turn_angle
        self.goal_tolerance = goal_tolerance
        self.max_iterations = max_iterations
        self.line_points = line_points
        self.sector_points = sector_points

    def plan(self, start, goal, start_heading=0.0):
        """
        start, goal: (x, y) tuples in world meters.
        start_heading: robot's current heading in radians (0 = facing +x).
        Returns a list of (x, y, heading, maneuver_angle) tuples from start
        to goal, or None if no path was found within max_iterations.
        """
        if self.map.is_occupied(*start) or self.map.is_occupied(*goal):
            return None

        x_min, x_max, y_min, y_max = self.map.world_limits()
        nodes = [Node(start[0], start[1], start_heading, parent=None)]

        for _ in range(self.max_iterations):
            # 1. sample anywhere on the map
            x_rand_t = random.uniform(x_min, x_max)
            y_rand_t = random.uniform(y_min, y_max)

            # 2. nearest existing node
            near_idx, nearest = self._nearest(nodes, x_rand_t, y_rand_t)

            # 3. step toward the sample by at most eps -> target direction point
            dist = math.hypot(x_rand_t - nearest.x, y_rand_t - nearest.y)
            if dist > self.eps:
                angle = math.atan2(y_rand_t - nearest.y, x_rand_t - nearest.x)
                x_target = nearest.x + self.eps * math.cos(angle)
                y_target = nearest.y + self.eps * math.sin(angle)
            else:
                x_target, y_target = x_rand_t, y_rand_t

            # 4. quick reject on the straight line toward the target
            if self._line_collision(nearest.x, nearest.y, x_target, y_target):
                continue

            # 5. Monte Carlo over feasible headings: fixed step b_length,
            #    turn bounded to +/- max_turn_angle from the parent's heading.
            #    Track position+heading together so there's no separate
            #    index to drift out of sync (this is what fixes bug #2 above).
            best = None
            best_dist = float("inf")
            for i in range(self.n_samples):
                rel_angle = 0.0 if i == self.n_samples - 1 else \
                    random.uniform(-self.max_turn_angle, self.max_turn_angle)
                abs_heading = nearest.heading + rel_angle
                cx = nearest.x + self.b_length * math.cos(abs_heading)
                cy = nearest.y + self.b_length * math.sin(abs_heading)
                if not (x_min < cx < x_max and y_min < cy < y_max):
                    continue
                d = math.hypot(cx - x_target, cy - y_target)
                if d < best_dist:
                    best_dist = d
                    best = (cx, cy, abs_heading, rel_angle)

            if best is None:
                continue
            best_x, best_y, best_heading, best_rel_angle = best

            # 6. collision-check the chosen straight segment
            if self._line_collision(nearest.x, nearest.y, best_x, best_y):
                continue

            # 7. collision-check the swept turning arc between old and new heading
            if self._sector_collision(nearest.x, nearest.y, nearest.heading, best_heading):
                continue

            # 8. commit the new node
            nodes.append(Node(best_x, best_y, best_heading,
                               parent=near_idx, maneuver_angle=best_rel_angle))

            # 9. goal check
            if math.hypot(best_x - goal[0], best_y - goal[1]) < self.goal_tolerance:
                return self._build_path(nodes, len(nodes) - 1)

        return None  # no path found within max_iterations

    # ---- internals -------------------------------------------------

    def _nearest(self, nodes, x, y):
        best_idx = 0
        best_dist = float("inf")
        for i, n in enumerate(nodes):
            d = (n.x - x) ** 2 + (n.y - y) ** 2
            if d < best_dist:
                best_dist = d
                best_idx = i
        return best_idx, nodes[best_idx]

    def _line_collision(self, x1, y1, x2, y2):
        xs = np.linspace(x1, x2, self.line_points)
        ys = np.linspace(y1, y2, self.line_points)
        return self.map.any_occupied(xs, ys)

    def _sector_collision(self, x_near, y_near, heading_from, heading_to):
        theta = np.linspace(heading_from, heading_to, self.sector_points)
        r = np.linspace(-self.b_length, 0.0, self.sector_points)
        theta_grid, r_grid = np.meshgrid(theta, r)
        sector_x = x_near + r_grid * np.cos(theta_grid)
        sector_y = y_near + r_grid * np.sin(theta_grid)
        return self.map.any_occupied(sector_x.ravel(), sector_y.ravel())

    def _build_path(self, nodes, end_idx):
        path = []
        idx = end_idx
        while idx is not None:
            n = nodes[idx]
            path.append((n.x, n.y, n.heading, n.maneuver_angle))
            idx = n.parent
        path.reverse()
        return path

