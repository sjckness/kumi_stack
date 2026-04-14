import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, TextSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    namespace = LaunchConfiguration('namespace')
    robot_name = LaunchConfiguration('robot_name')
    use_sim_time = LaunchConfiguration('use_sim_time')
    enable_sensors = LaunchConfiguration('enable_sensors')
    spawner_delay = LaunchConfiguration('spawner_delay')
    use_gz_bridge = LaunchConfiguration('use_gz_bridge')
    use_control_gui = LaunchConfiguration('use_control_gui')
    use_rviz = LaunchConfiguration('use_rviz')
    use_joint_state_publisher_gui = LaunchConfiguration('use_joint_state_publisher_gui')
    absolute_namespace = PathJoinSubstitution([
        TextSubstitution(text='/'),
        namespace
    ])

    declare_namespace = DeclareLaunchArgument(
        'namespace',
        description='Namespace for this robot runtime stack'
    )

    declare_robot_name = DeclareLaunchArgument(
        'robot_name',
        default_value=namespace,
        description='Robot name for this runtime stack'
    )

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation clock if true'
    )

    declare_enable_sensors = DeclareLaunchArgument(
        'enable_sensors',
        default_value='true',
        description='Enable sensors in the robot description'
    )

    declare_spawner_delay = DeclareLaunchArgument(
        'spawner_delay',
        default_value='10.0',
        description='Delay before spawning controllers'
    )

    declare_use_gz_bridge = DeclareLaunchArgument(
        'use_gz_bridge',
        default_value='true',
        description='Bridge Gazebo topics to ROS 2'
    )

    declare_use_control_gui = DeclareLaunchArgument(
        'use_control_gui',
        default_value='false',
        description='Launch the standalone control GUI'
    )

    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz',
        default_value='false',
        description='Launch RViz from description.launch.py'
    )

    declare_use_joint_state_publisher_gui = DeclareLaunchArgument(
        'use_joint_state_publisher_gui',
        default_value='false',
        description='Launch joint_state_publisher_gui from description.launch.py'
    )

    controllers_file = PathJoinSubstitution([
        FindPackageShare('kumi_control'),
        'config',
        'trajectory_control_config.yaml'
    ])

    description_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                FindPackageShare('kumi_description').find('kumi_description'),
                'launch',
                'description.launch.py'
            )
        ),
        launch_arguments={
            'use_sim': 'true',
            'use_sim_time': use_sim_time,
            'enable_sensors': enable_sensors,
            'use_joint_state_publisher_gui': use_joint_state_publisher_gui,
            'use_rviz': use_rviz,
            'robot_name': robot_name,
            'ros_namespace': namespace,
            'control_config': controllers_file,
        }.items()
    )

    controller_manager_name = PathJoinSubstitution([
        TextSubstitution(text='/'),
        namespace,
        'controller_manager'
    ])

    control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                FindPackageShare('kumi_control').find('kumi_control'),
                'launch',
                'control.launch.py'
            )
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'use_sim': 'true',
            'enable_sensors': enable_sensors,
            'robot_name': robot_name,
            'start_controller_manager': 'false',
            'controller_manager_name': controller_manager_name,
            'spawner_delay': spawner_delay,
            'namespace': namespace,
            'use_gui': use_control_gui,
            'controllers_file': controllers_file,
        }.items()
    )

    gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='robot_gz_bridge',
        arguments=[
            PathJoinSubstitution([
                TextSubstitution(text='/'),
                namespace,
                'front_camera',
                'image@sensor_msgs/msg/Image[gz.msgs.Image',
            ]),
            PathJoinSubstitution([
                TextSubstitution(text='/'),
                namespace,
                'front_camera',
                'camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            ]),
            PathJoinSubstitution([
                TextSubstitution(text='/'),
                namespace,
                'front_depth',
                'image@sensor_msgs/msg/Image[gz.msgs.Image',
            ]),
            PathJoinSubstitution([
                TextSubstitution(text='/'),
                namespace,
                'front_depth',
                'camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            ]),
            PathJoinSubstitution([
                TextSubstitution(text='/'),
                namespace,
                'kumi_behavior',
                'emergency@std_msgs/msg/Bool[gz.msgs.Boolean',
            ]),
            PathJoinSubstitution([
                TextSubstitution(text='/'),
                namespace,
                'kumi_seq_traj_controller',
                'enabled@std_msgs/msg/Bool[gz.msgs.Boolean',
            ]),
            PathJoinSubstitution([
                TextSubstitution(text='/'),
                namespace,
                'kumi_seq_traj_controller',
                'gait@std_msgs/msg/String[gz.msgs.StringMsg',
            ]),
        ],
        output='screen',
        condition=IfCondition(use_gz_bridge),
    )

    bt_node = Node(
        package='kumi_behavior',
        executable='bt_node',
        namespace=absolute_namespace,
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    return LaunchDescription([
        declare_namespace,
        declare_robot_name,
        declare_use_sim_time,
        declare_enable_sensors,
        declare_spawner_delay,
        declare_use_gz_bridge,
        declare_use_control_gui,
        declare_use_rviz,
        declare_use_joint_state_publisher_gui,
        description_launch,
        control_launch,
        gz_bridge,
        bt_node,
    ])
