"""A deliberately slow depth-1 subscriber for the QoS history experiment."""

import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float32

from turtle_py.qos_utils import make_qos_profile


class SlowDistanceSubscriber(Node):
    def __init__(self) -> None:
        super().__init__('slow_distance_subscriber')
        self.declare_parameter('callback_delay', 0.20)
        self.declare_parameter('distance_topic', '/turtle_distance')

        self._delay = max(
            0.0, float(self.get_parameter('callback_delay').value))
        topic = str(self.get_parameter('distance_topic').value)
        self._count = 0
        self._started = time.monotonic()
        qos = make_qos_profile('best_effort', 'volatile', 1)
        self._subscription = self.create_subscription(
            Float32, topic, self._on_distance, qos)
        self.get_logger().info(
            f'depth-1 slow subscriber on {topic}; delay={self._delay:.2f} s')

    def _on_distance(self, message: Float32) -> None:
        self._count += 1
        elapsed = time.monotonic() - self._started
        self.get_logger().info(
            f'received #{self._count} at {elapsed:.2f} s: {message.data:.3f} m')
        time.sleep(self._delay)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SlowDistanceSubscriber()
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
