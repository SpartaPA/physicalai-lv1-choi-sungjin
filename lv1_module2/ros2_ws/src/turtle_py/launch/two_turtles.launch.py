"""Launch two turtles and one namespaced distance publisher per turtle."""

from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    spawn_turtle2 = ExecuteProcess(
        cmd=[
            'ros2', 'service', 'call', '/spawn', 'turtlesim/srv/Spawn',
            "{x: 2.0, y: 2.0, theta: 0.0, name: 'turtle2'}",
        ],
        output='screen',
    )

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
            name='distance_publisher',
            parameters=[{
                'pose_topic': '/turtle1/pose',
                'distance_topic': '/turtle_distance',
            }],
            output='screen',
        ),
        TimerAction(period=2.0, actions=[spawn_turtle2]),
        Node(
            package='turtle_py',
            executable='distance_publisher',
            namespace='turtle2',
            name='distance_publisher',
            parameters=[{
                'pose_topic': '/turtle2/pose',
                'distance_topic': 'turtle_distance',
            }],
            output='screen',
        ),
    ])
