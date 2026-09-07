"""Publish a custom WaypointList once or repeatedly with configurable QoS."""

import rclpy
from rclpy.exceptions import ParameterUninitializedException
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtle_interfaces.msg import Waypoint, WaypointList

from turtle_py.qos_utils import make_qos_profile


class WaypointPublisher(Node):
    def __init__(self) -> None:
        super().__init__('waypoint_publisher')

        self.declare_parameter('waypoint_topic', '/waypoints')
        self.declare_parameter('x_values', [2.0, 2.0, 8.0, 8.0])
        self.declare_parameter('y_values', [2.0, 8.0, 8.0, 3.0])
        self.declare_parameter('tolerances', [0.20, 0.25, 0.25, 0.20])
        self.declare_parameter(
            'labels', ['start', 'upper_left', 'upper_right', 'finish'])
        self.declare_parameter('publish_rate', 1.0)
        self.declare_parameter('publish_once', True)
        self.declare_parameter('reliability', 'reliable')
        self.declare_parameter('durability', 'transient_local')
        self.declare_parameter('qos_depth', 1)

        self._topic = str(self.get_parameter('waypoint_topic').value)
        self._publish_rate = float(self.get_parameter('publish_rate').value)
        if self._publish_rate <= 0.0:
            self.get_logger().warning(
                'publish_rate must be greater than zero; using 1.0 Hz')
            self._publish_rate = 1.0
        self._publish_once = bool(self.get_parameter('publish_once').value)
        reliability = str(self.get_parameter('reliability').value)
        durability = str(self.get_parameter('durability').value)
        depth = int(self.get_parameter('qos_depth').value)

        try:
            qos = make_qos_profile(reliability, durability, depth)
        except ValueError as error:
            self.get_logger().warning(f'{error}; using transient_local defaults')
            qos = make_qos_profile('reliable', 'transient_local', 1)

        self._publisher = self.create_publisher(WaypointList, self._topic, qos)
        self._message = self._build_message()
        self._timer = self.create_timer(1.0 / self._publish_rate, self._publish)

        self.get_logger().info(
            f'waypoint publisher on {self._topic}: '
            f'{reliability}/{durability}/depth {depth}')

    def _build_message(self) -> WaypointList | None:
        x_values = self._read_array_parameter('x_values')
        y_values = self._read_array_parameter('y_values')
        tolerances = self._read_array_parameter('tolerances')
        labels = self._read_array_parameter('labels')

        lengths = {len(x_values), len(y_values), len(tolerances), len(labels)}
        if lengths == {0}:
            self.get_logger().warning(
                'empty waypoint list received; nothing will be published')
            return None
        if len(lengths) != 1:
            self.get_logger().warning(
                'waypoint parameter arrays have different lengths; '
                'nothing will be published')
            return None

        message = WaypointList()
        message.header.frame_id = 'world'
        for x_value, y_value, tolerance, label in zip(
                x_values, y_values, tolerances, labels):
            if tolerance < 0.0:
                self.get_logger().warning(
                    f'negative tolerance for {label}; using 0.0')
                tolerance = 0.0
            waypoint = Waypoint()
            waypoint.x = float(x_value)
            waypoint.y = float(y_value)
            waypoint.tolerance = float(tolerance)
            waypoint.label = str(label)
            message.waypoints.append(waypoint)
        return message

    def _read_array_parameter(self, name: str) -> list:
        try:
            value = self.get_parameter(name).value
        except ParameterUninitializedException:
            return []
        return list(value) if value is not None else []

    def _publish(self) -> None:
        if self._message is None:
            if self._publish_once:
                self._timer.cancel()
            return

        self._message.header.stamp = self.get_clock().now().to_msg()
        self._publisher.publish(self._message)
        self.get_logger().info(
            f'published {len(self._message.waypoints)} waypoint(s)')
        if self._publish_once:
            self._timer.cancel()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WaypointPublisher()
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
