"""Draw a four-sided square with a pose-feedback ``for`` loop."""

import math
import threading

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_srvs.srv import SetBool, Trigger
from turtlesim.msg import Pose

from turtle_py.calculations import distance_to_goal, normalize_angle


class SquareDriver(Node):
    SQUARE_SIDES = 4
    CONTROL_PERIOD_SEC = 0.05

    def __init__(self) -> None:
        super().__init__('square_driver')

        self.declare_parameter('linear_speed', 1.0)
        self.declare_parameter('angular_speed', 2.0)
        self.declare_parameter('side_length', 2.0)
        self.declare_parameter('position_tolerance', 0.01)
        self.declare_parameter('angle_tolerance', 0.02)
        self.declare_parameter('linear_gain', 1.5)
        self.declare_parameter('angular_gain', 5.0)
        self.declare_parameter('cmd_vel_topic', '/turtle1/cmd_vel')
        self.declare_parameter('pose_topic', '/turtle1/pose')

        self._linear_speed = max(
            0.1, float(self.get_parameter('linear_speed').value))
        self._angular_speed = max(
            0.1, float(self.get_parameter('angular_speed').value))
        self._side_length = max(
            0.1, float(self.get_parameter('side_length').value))
        self._position_tolerance = max(
            0.005, float(self.get_parameter('position_tolerance').value))
        self._angle_tolerance = max(
            0.005, float(self.get_parameter('angle_tolerance').value))
        self._linear_gain = max(
            0.1, float(self.get_parameter('linear_gain').value))
        self._angular_gain = max(
            0.1, float(self.get_parameter('angular_gain').value))

        cmd_vel_topic = str(self.get_parameter('cmd_vel_topic').value)
        pose_topic = str(self.get_parameter('pose_topic').value)

        self._publisher = self.create_publisher(Twist, cmd_vel_topic, 10)
        self._pose_subscription = self.create_subscription(
            Pose,
            pose_topic,
            self._on_pose,
            10,
        )
        self._enable_service = self.create_service(
            SetBool,
            'set_driving',
            self._on_set_driving,
        )
        self._home_service = self.create_service(
            Trigger,
            'save_home',
            self._on_save_home,
        )

        self._latest_pose: Pose | None = None
        self._home_pose: tuple[float, float, float] | None = None
        self._enabled = True
        self._command_lock = threading.Lock()
        self._completed = False
        self._stop_event = threading.Event()
        self._start_square_event = threading.Event()
        self._start_square_event.set()
        self._worker = threading.Thread(
            target=self._square_worker,
            name='square-driver-worker',
            daemon=True,
        )
        self._worker.start()

        self.get_logger().info(
            'square driver started; for-loop sides=4; '
            'services: /set_driving and /save_home')

    def _on_pose(self, message: Pose) -> None:
        self._latest_pose = message

    def _on_set_driving(
        self,
        request: SetBool.Request,
        response: SetBool.Response,
    ):
        with self._command_lock:
            was_enabled = self._enabled
            self._enabled = bool(request.data)
            if was_enabled and not self._enabled:
                self._publisher.publish(Twist())
        if not self._enabled:
            response.message = 'square driving disabled and turtle stopped'
        else:
            if self._completed:
                self._restart_square()
            response.message = 'square driving enabled'
        response.success = True
        self.get_logger().info(response.message)
        return response

    def _on_save_home(
        self,
        request: Trigger.Request,
        response: Trigger.Response,
    ):
        del request
        pose = self._latest_pose
        if pose is None:
            response.success = False
            response.message = 'pose has not been received yet'
            self.get_logger().warning(response.message)
            return response

        self._home_pose = (
            float(pose.x),
            float(pose.y),
            float(pose.theta),
        )
        response.success = True
        response.message = (
            f'home saved at x={self._home_pose[0]:.3f}, '
            f'y={self._home_pose[1]:.3f}, theta={self._home_pose[2]:.3f}')
        self.get_logger().info(response.message)
        return response

    def _restart_square(self) -> None:
        self._completed = False
        self._start_square_event.set()
        self.get_logger().info('starting a new square')

    @staticmethod
    def _clamp(value: float, limit: float) -> float:
        return max(-limit, min(value, limit))

    def _wait_for_start_pose(self) -> Pose | None:
        while rclpy.ok() and not self._stop_event.is_set():
            pose = self._latest_pose
            ready = self._start_square_event.is_set() and self._enabled
            if ready and pose is not None:
                self._start_square_event.clear()
                return pose
            self._stop_event.wait(self.CONTROL_PERIOD_SEC)
        return None

    def _wait_until_enabled(self) -> bool:
        while rclpy.ok() and not self._stop_event.is_set():
            if self._enabled:
                return True
            self._stop_event.wait(self.CONTROL_PERIOD_SEC)
        return False

    def _drive_to(self, target_x: float, target_y: float) -> bool:
        while rclpy.ok() and not self._stop_event.is_set():
            if not self._wait_until_enabled():
                return False
            pose = self._latest_pose
            if pose is None:
                self._stop_event.wait(self.CONTROL_PERIOD_SEC)
                continue

            distance = distance_to_goal(
                pose.x,
                pose.y,
                target_x,
                target_y,
            )
            if distance <= self._position_tolerance:
                self.stop()
                return True

            target_heading = math.atan2(
                target_y - pose.y,
                target_x - pose.x,
            )
            heading_error = normalize_angle(target_heading - pose.theta)
            command = Twist()
            command.linear.x = min(
                self._linear_speed,
                max(0.08, self._linear_gain * distance),
            )
            if abs(heading_error) > 0.35:
                command.linear.x *= 0.25
            command.angular.z = self._clamp(
                self._angular_gain * heading_error,
                self._angular_speed,
            )
            self._publish_motion(command)
            self._stop_event.wait(self.CONTROL_PERIOD_SEC)
        return False

    def _turn_to(self, target_heading: float) -> bool:
        while rclpy.ok() and not self._stop_event.is_set():
            if not self._wait_until_enabled():
                return False
            pose = self._latest_pose
            if pose is None:
                self._stop_event.wait(self.CONTROL_PERIOD_SEC)
                continue

            heading_error = normalize_angle(target_heading - pose.theta)
            if abs(heading_error) <= self._angle_tolerance:
                self.stop()
                return True

            command = Twist()
            command.angular.z = self._clamp(
                self._angular_gain * heading_error,
                self._angular_speed,
            )
            self._publish_motion(command)
            self._stop_event.wait(self.CONTROL_PERIOD_SEC)
        return False

    def _draw_one_square(self, start_pose: Pose) -> bool:
        """Visit four fixed vertices with an explicit four-iteration loop."""
        desired_heading = float(start_pose.theta)
        vertex_x = float(start_pose.x)
        vertex_y = float(start_pose.y)

        for side_index in range(self.SQUARE_SIDES):
            target_x = (
                vertex_x + self._side_length * math.cos(desired_heading))
            target_y = (
                vertex_y + self._side_length * math.sin(desired_heading))
            self.get_logger().info(
                f'side {side_index + 1}/{self.SQUARE_SIDES} target: '
                f'x={target_x:.3f}, y={target_y:.3f}')

            if not self._drive_to(target_x, target_y):
                return False

            vertex_x = target_x
            vertex_y = target_y
            desired_heading = normalize_angle(
                desired_heading + 2.0 * math.pi / self.SQUARE_SIDES)
            if not self._turn_to(desired_heading):
                return False

            self.get_logger().info(
                f'completed side {side_index + 1}/{self.SQUARE_SIDES}')

        self.stop()
        return True

    def _square_worker(self) -> None:
        while rclpy.ok() and not self._stop_event.is_set():
            start_pose = self._wait_for_start_pose()
            if start_pose is None:
                return
            if self._draw_one_square(start_pose):
                self._completed = True
                self.get_logger().info('square completed; turtle stopped')

    def stop(self) -> None:
        with self._command_lock:
            if self._enabled:
                self._publisher.publish(Twist())

    def _publish_motion(self, command: Twist) -> None:
        with self._command_lock:
            if self._enabled and not self._stop_event.is_set():
                self._publisher.publish(command)

    def request_shutdown(self) -> None:
        self._stop_event.set()
        if rclpy.ok():
            self.stop()
        if self._worker.is_alive():
            self._worker.join(timeout=1.0)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SquareDriver()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        if rclpy.ok():
            node.get_logger().info('shutdown requested; stopping cleanly')
    finally:
        node.request_shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
