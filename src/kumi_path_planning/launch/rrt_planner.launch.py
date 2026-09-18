import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('kumi_path_planning')
    params_file = os.path.join(pkg_share, 'config', 'rrt_params.yaml')

    world_name = LaunchConfiguration('world_name', default='simple_world')

    return LaunchDescription([

        DeclareLaunchArgument(
            'world_name',
            default_value='simple_world',
            description='Name of the Gazebo world to use'
        ),

        Node(
            package='kumi_path_planning',
            executable='gz_pose_bridge',
            name='gz_pose_bridge',
            parameters=[
                {'world_name': world_name}
            ]
        ),

        Node(
            package='kumi_path_planning',
            executable='yolo_to_occupancy_grid',
            name='yolo_to_occupancy_grid'
        ),
        
        Node(
            package='kumi_path_planning',
            executable='rrt_planner_node',
            name='rrt_planner_node'
        ),
    ])