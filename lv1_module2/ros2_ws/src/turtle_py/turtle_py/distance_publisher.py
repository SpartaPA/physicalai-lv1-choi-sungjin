"""Publish the turtle's distance from the origin at a configurable rate."""

import math

import rclpy
from rcl_interfaces.msg import SetParametersResult
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float32
from turtlesim.msg import Pose

from turtle_py.qos_utils import make_qos_profile


class DistancePublisher(Node):
    def __init__(self) -> None:
        super().__init__('distance_publisher')

        self.declare_parameter('publish_rate', 10.0)
        self.declare_parameter('pose_topic', '/turtle1/pose')
        self.declare_parameter('distance_topic', '/turtle_distance')
        self.declare_parameter('pose_timeout', 1.0)
        self.declare_parameter('reliability', 'reliable')
        self.declare_parameter('durability', 'volatile')
        self.declare_parameter('qos_depth', 10)

        self._publish_rate = float(self.get_parameter('publish_rate').value)
        if self._publish_rate <= 0.0:
            self.get_logger().warning(
                'publish_rate must be greater than zero; using 10.0 Hz')
            self._publish_rate = 10.0

        pose_topic = str(self.get_parameter('pose_topic').value)
        distance_topic = str(self.get_parameter('distance_topic').value)
        self._pose_timeout = max(
            0.0, float(self.get_parameter('pose_timeout').value))
        reliability = str(self.get_parameter('reliability').value)
        durability = str(self.get_parameter('durability').value)
        qos_depth = int(self.get_parameter('qos_depth').value)

        try:
            distance_qos = make_qos_profile(reliability, durability, qos_depth)
        except ValueError as error:
            self.get_logger().warning(
                f'{error}; using reliable/volatile/depth 10')
            distance_qos = make_qos_profile()

        self._latest_pose: Pose | None = None
        self._last_pose_time = None
        self._pose_stale_warned = False
        self._publisher = self.create_publisher(Float32, distance_topic, distance_qos)
        self._subscription = self.create_subscription(
            Pose,
            pose_topic,
            self._on_pose,
            10,
        )
        self._timer = self.create_timer(1.0 / self._publish_rate, self._on_timer)
        self.add_on_set_parameters_callback(self._on_parameters)

        self.get_logger().info(
            f'distance publisher: {pose_topic} -> {distance_topic}, '
            f'{self._publish_rate:.1f} Hz, {reliability}/{durability}')

    def _on_pose(self, message: Pose) -> None:
        # 구독 콜백은 최신 자세만 저장한다.
        self._latest_pose = message
        self._last_pose_time = self.get_clock().now()
        self._pose_stale_warned = False

    def _on_timer(self) -> None:
        # 실제 발행은 타이머 콜백에서 수행한다.
        if self._latest_pose is None:
            return
        if self._pose_timeout > 0.0 and self._last_pose_time is not None:
            pose_age = (
                self.get_clock().now() - self._last_pose_time
            ).nanoseconds / 1_000_000_000.0
            if pose_age > self._pose_timeout:
                if not self._pose_stale_warned:
                    self.get_logger().warning(
                        f'no fresh pose for {pose_age:.2f} s; '
                        'suppressing /turtle_distance output')
                    self._pose_stale_warned = True
                return
        message = Float32()
        message.data = float(math.hypot(self._latest_pose.x, self._latest_pose.y))
        self._publisher.publish(message)

    def _on_parameters(self, parameters) -> SetParametersResult:
        for parameter in parameters:
            if parameter.name == 'publish_rate':
                requested_rate = float(parameter.value)
                if requested_rate <= 0.0:
                    reason = 'publish_rate must be greater than zero'
                    self.get_logger().warning(reason)
                    return SetParametersResult(successful=False, reason=reason)

                self._publish_rate = requested_rate
                self.destroy_timer(self._timer)
                self._timer = self.create_timer(
                    1.0 / self._publish_rate,
                    self._on_timer,
                )
                self.get_logger().info(
                    f'publish_rate changed to {self._publish_rate:.1f} Hz')

        return SetParametersResult(successful=True)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DistancePublisher()
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
