"""
This code is used to test the RRT planner in isolation, without ROS. It creates a simple occupancy grid with a wall and attempts to plan a path around it.
"""

import numpy as np
from kumi_path_planning.rrt import RRTPlanner, WorldOccupancyGrid

# 50x50 grid, 0.1 m/cell -> 5m x 5m world, all free
grid = np.zeros((50, 50), dtype=int)

# a vertical wall from row 20 to 30, column 20 (blocks a straight line through it)
#grid[20:30, 20] = 1

# a wall with a gap (forces the planner through a corridor)
grid[20:30, 20] = 1
grid[24:26, 20] = 0   # 2-cell-wide gap in the middle of the wall


occ = WorldOccupancyGrid(grid, resolution=0.1, origin_x=0.0, origin_y=0.0)

planner = RRTPlanner(occ)
path = planner.plan(start=(1, 0.5), goal=(3.5, 4.0))

if path is None:
    print("FAILED: no path found")
else:
    print(f"SUCCESS: {len(path)} waypoints")
    for x, y, heading, maneuver_angle in path:
        print(f"  x={x:.2f} y={y:.2f} heading={heading:.2f} turn={maneuver_angle:.2f}")