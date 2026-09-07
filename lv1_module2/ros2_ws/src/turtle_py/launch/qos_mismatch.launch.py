"""Reproduce a Best-Effort publisher versus Reliable subscriber mismatch."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        Node(
            package='turtlesim',
            executable='turtlesim_node',
            name='turtlesim',
            output='screen',
        ),
        Node(
            package='turtle_py',
            executable='distance_publisher',
            name='best_effort_distance_publisher',
            parameters=[{
                'reliability': 'best_effort',
                'qos_depth': 5,
            }],
            output='screen',
        ),
        Node(
            package='turtle_py',
            executable='warn_subscriber',
            name='reliable_warn_subscriber',
            parameters=[{
                'reliability': 'reliable',
            }],
            output='screen',
        ),
    ])
