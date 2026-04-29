from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_gui = LaunchConfiguration('use_gui')
    use_rviz = LaunchConfiguration('use_rviz')

    declare_use_gui = DeclareLaunchArgument(
        'use_gui',
        default_value='true',
        description='Launch the Tkinter control GUI',
    )
    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz',
        default_value='false',
        description='Launch RViz',
    )

    xacro_file = PathJoinSubstitution(
        [FindPackageShare('kumi_description'), 'urdf', 'kumi.xacro']
    )

    robot_description_content = Command([
        'xacro ', xacro_file,
        ' use_sim:=false',
        ' enable_sensors:=false',
        ' robot_name:=kumi',
        ' pkg_share:=', FindPackageShare('kumi_description'),
    ])

    robot_description = {
        'robot_description': ParameterValue(robot_description_content, value_type=str)
    }

    # robot_state_publisher legge joint_states da Isaac (/kumi/joint_states)
    # e pubblica i TF del robot
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[robot_description, {'use_sim_time': False}],
        remappings=[('joint_states', '/kumi/joint_states')],
        output='screen',
    )

    # Sequenziatore CSV: pubblica JointState su /kumi/joint_commands
    seq_traj_controller = Node(
        package='kumi_control',
        executable='kumi_seq_traj_controller',
        name='kumi_seq_traj_controller',
        parameters=[{
            'use_isaac': True,
            'joint_commands_topic': '/kumi/joint_commands',
            'enable_topic': '/kumi/kumi_seq_traj_controller/enabled',
            'gait_topic': '/kumi/kumi_seq_traj_controller/gait',
        }],
        output='screen',
    )

    # GUI: rimappa i topic sul namespace /kumi/
    control_gui = Node(
        package='kumi_control',
        executable='kumi_control_gui',
        name='kumi_control_gui',
        output='screen',
        condition=IfCondition(use_gui),
        remappings=[
            ('/kumi_seq_traj_controller/enabled', '/kumi/kumi_seq_traj_controller/enabled'),
            ('/kumi_seq_traj_controller/gait', '/kumi/kumi_seq_traj_controller/gait'),
        ],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        declare_use_gui,
        declare_use_rviz,
        robot_state_publisher,
        seq_traj_controller,
        control_gui,
        rviz,
    ])
