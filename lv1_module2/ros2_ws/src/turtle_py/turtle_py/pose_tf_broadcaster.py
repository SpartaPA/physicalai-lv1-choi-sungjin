"""Broadcast the world to turtle1 transform from turtlesim Pose messages."""

import math

import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from tf2_ros import TransformBroadcaster
from turtlesim.msg import Pose


class PoseTfBroadcaster(Node):
    def __init__(self) -> None:
        super().__init__('pose_tf_broadcaster')
        self.declare_parameter('pose_topic', '/turtle1/pose')
        self.declare_parameter('parent_frame', 'world')
        self.declare_parameter('child_frame', 'turtle1')

        self._parent_frame = str(self.get_parameter('parent_frame').value)
        self._child_frame = str(self.get_parameter('child_frame').value)
        pose_topic = str(self.get_parameter('pose_topic').value)

        self._broadcaster = TransformBroadcaster(self)
        self._subscription = self.create_subscription(
            Pose, pose_topic, self._on_pose, 10)
        self.get_logger().info(
            f'broadcasting {self._parent_frame} -> {self._child_frame} '
            f'from {pose_topic}')

    def _on_pose(self, message: Pose) -> None:
        transform = TransformStamped()
        transform.header.stamp = self.get_clock().now().to_msg()
        transform.header.frame_id = self._parent_frame
        transform.child_frame_id = self._child_frame
        transform.transform.translation.x = float(message.x)
        transform.transform.translation.y = float(message.y)
        transform.transform.translation.z = 0.0
        transform.transform.rotation.x = 0.0
        transform.transform.rotation.y = 0.0
        transform.transform.rotation.z = math.sin(message.theta / 2.0)
        transform.transform.rotation.w = math.cos(message.theta / 2.0)
        self._broadcaster.sendTransform(transform)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PoseTfBroadcaster()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        if rclpy.ok():
            node.get_logger().info('shutdown requested; stopping cleanly')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
