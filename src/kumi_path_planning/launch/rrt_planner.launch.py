import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('kumi_path_planning')
    params_file = os.path.join(pkg_share, 'config', 'rrt_params.yaml')

    rrt_node = Node(
        package='kumi_path_planning',
        executable='rrt_planner_node',
        name='rrt_planner_node',
        output='screen',
        parameters=[params_file],
    )

    return LaunchDescription([rrt_node])
