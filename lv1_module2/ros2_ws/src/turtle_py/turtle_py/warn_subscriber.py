"""Warn when the turtle distance exceeds a configurable threshold."""

import rclpy
from rcl_interfaces.msg import SetParametersResult
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float32

from turtle_py.qos_utils import make_qos_profile


class WarnSubscriber(Node):
    def __init__(self) -> None:
        super().__init__('warn_subscriber')

        self.declare_parameter('warn_distance', 2.5)
        self.declare_parameter('distance_topic', '/turtle_distance')
        self.declare_parameter('reliability', 'reliable')
        self.declare_parameter('durability', 'volatile')
        self.declare_parameter('qos_depth', 10)

        self._warn_distance = float(self.get_parameter('warn_distance').value)
        if self._warn_distance < 0.0:
            self.get_logger().warning(
                'warn_distance cannot be negative; using 2.5 m')
            self._warn_distance = 2.5

        distance_topic = str(self.get_parameter('distance_topic').value)
        reliability = str(self.get_parameter('reliability').value)
        durability = str(self.get_parameter('durability').value)
        qos_depth = int(self.get_parameter('qos_depth').value)

        try:
            qos = make_qos_profile(reliability, durability, qos_depth)
        except ValueError as error:
            self.get_logger().warning(
                f'{error}; using reliable/volatile/depth 10')
            qos = make_qos_profile()

        self._subscription = self.create_subscription(
            Float32,
            distance_topic,
            self._on_distance,
            qos,
        )
        self.add_on_set_parameters_callback(self._on_parameters)

        self.get_logger().info(
            f'listening on {distance_topic}; warning above '
            f'{self._warn_distance:.2f} m ({reliability}/{durability})')

    def _on_distance(self, message: Float32) -> None:
        if message.data > self._warn_distance:
            self.get_logger().warning(
                f'distance warning: {message.data:.3f} m '
                f'> {self._warn_distance:.3f} m')

    def _on_parameters(self, parameters) -> SetParametersResult:
        for parameter in parameters:
            if parameter.name == 'warn_distance':
                requested_distance = float(parameter.value)
                if requested_distance < 0.0:
                    reason = 'warn_distance must be zero or greater'
                    self.get_logger().warning(reason)
                    return SetParametersResult(successful=False, reason=reason)
                self._warn_distance = requested_distance
                self.get_logger().info(
                    f'warn_distance changed to {self._warn_distance:.2f} m')
        return SetParametersResult(successful=True)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WarnSubscriber()
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
