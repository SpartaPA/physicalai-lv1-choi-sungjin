"""Launch turtlesim and the three assignment application nodes."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    package_share = get_package_share_directory('turtle_py')
    default_params_file = os.path.join(
        package_share, 'config', 'params.yaml')
    params_file = LaunchConfiguration('params_file')

    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params_file,
            description='Absolute path to the ROS 2 parameter YAML file',
        ),
        Node(
            package='turtlesim',
            executable='turtlesim_node',
            name='turtlesim',
            output='screen',
        ),
        Node(
            package='turtle_py',
            executable='distance_publisher',
            name='distance_publisher',
            parameters=[params_file],
            output='screen',
        ),
        Node(
            package='turtle_py',
            executable='warn_subscriber',
            name='warn_subscriber',
            parameters=[params_file],
            output='screen',
        ),
        Node(
            package='turtle_py',
            executable='draw_polygon_server',
            name='draw_polygon_server',
            parameters=[params_file],
            output='screen',
        ),
    ])
