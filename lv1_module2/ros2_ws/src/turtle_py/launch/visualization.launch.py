"""Launch turtlesim, TF, waypoints, markers, and RViz2."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    package_share = get_package_share_directory('turtle_py')
    rviz_config = os.path.join(package_share, 'rviz', 'turtle_view.rviz')

    return LaunchDescription([
        Node(
            package='turtlesim',
            executable='turtlesim_node',
            name='turtlesim',
            output='screen',
        ),
        Node(
            package='turtle_py',
            executable='pose_tf_broadcaster',
            name='pose_tf_broadcaster',
            output='screen',
        ),
        Node(
            package='turtle_py',
            executable='waypoint_publisher',
            name='waypoint_publisher',
            output='screen',
        ),
        Node(
            package='turtle_py',
            executable='waypoint_marker_publisher',
            name='waypoint_marker_publisher',
            output='screen',
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config],
            output='screen',
        ),
    ])
