"""Subscribe to WaypointList with selectable durability and callback delay."""

import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtle_interfaces.msg import WaypointList

from turtle_py.qos_utils import make_qos_profile


class WaypointSubscriber(Node):
    def __init__(self) -> None:
        super().__init__('waypoint_subscriber')

        self.declare_parameter('waypoint_topic', '/waypoints')
        self.declare_parameter('reliability', 'reliable')
        self.declare_parameter('durability', 'transient_local')
        self.declare_parameter('qos_depth', 1)
        self.declare_parameter('callback_delay', 0.0)

        topic = str(self.get_parameter('waypoint_topic').value)
        reliability = str(self.get_parameter('reliability').value)
        durability = str(self.get_parameter('durability').value)
        depth = int(self.get_parameter('qos_depth').value)
        self._callback_delay = max(
            0.0, float(self.get_parameter('callback_delay').value))
        self._received_count = 0

        try:
            qos = make_qos_profile(reliability, durability, depth)
        except ValueError as error:
            self.get_logger().warning(f'{error}; using reliable/volatile/depth 1')
            qos = make_qos_profile('reliable', 'volatile', 1)

        self._subscription = self.create_subscription(
            WaypointList, topic, self._on_waypoints, qos)
        self.get_logger().info(
            f'waypoint subscriber on {topic}: '
            f'{reliability}/{durability}/depth {depth}, '
            f'delay {self._callback_delay:.3f} s')

    def _on_waypoints(self, message: WaypointList) -> None:
        self._received_count += 1
        labels = ', '.join(waypoint.label for waypoint in message.waypoints)
        self.get_logger().info(
            f'received waypoint message #{self._received_count}: '
            f'{len(message.waypoints)} point(s) [{labels}]')
        if self._callback_delay > 0.0:
            time.sleep(self._callback_delay)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WaypointSubscriber()
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
