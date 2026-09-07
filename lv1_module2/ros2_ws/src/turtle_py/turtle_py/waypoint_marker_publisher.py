"""Convert custom waypoints into an RViz Marker sphere list."""

import rclpy
from geometry_msgs.msg import Point
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtle_interfaces.msg import WaypointList
from visualization_msgs.msg import Marker

from turtle_py.qos_utils import make_qos_profile


class WaypointMarkerPublisher(Node):
    def __init__(self) -> None:
        super().__init__('waypoint_marker_publisher')
        self.declare_parameter('waypoint_topic', '/waypoints')
        self.declare_parameter('marker_topic', '/waypoint_markers')

        waypoint_topic = str(self.get_parameter('waypoint_topic').value)
        marker_topic = str(self.get_parameter('marker_topic').value)
        transient_qos = make_qos_profile('reliable', 'transient_local', 1)

        self._publisher = self.create_publisher(
            Marker, marker_topic, transient_qos)
        self._subscription = self.create_subscription(
            WaypointList,
            waypoint_topic,
            self._on_waypoints,
            transient_qos,
        )
        self.get_logger().info(
            f'converting {waypoint_topic} to RViz marker {marker_topic}')

    def _on_waypoints(self, message: WaypointList) -> None:
        if not message.waypoints:
            self.get_logger().warning(
                'empty waypoint list received; marker was not published')
            return

        marker = Marker()
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.header.frame_id = message.header.frame_id or 'world'
        marker.ns = 'assignment_waypoints'
        marker.id = 0
        marker.type = Marker.SPHERE_LIST
        marker.action = Marker.ADD
        marker.pose.orientation.w = 1.0
        marker.scale.x = 0.25
        marker.scale.y = 0.25
        marker.scale.z = 0.25
        marker.color.r = 1.0
        marker.color.g = 0.35
        marker.color.b = 0.10
        marker.color.a = 1.0

        for waypoint in message.waypoints:
            point = Point()
            point.x = waypoint.x
            point.y = waypoint.y
            point.z = 0.0
            marker.points.append(point)

        self._publisher.publish(marker)
        self.get_logger().info(
            f'published RViz marker with {len(marker.points)} point(s)')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WaypointMarkerPublisher()
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
