"""Action server that draws a regular polygon with turtlesim velocity commands."""

import math
import threading
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from turtle_interfaces.action import DrawPolygon
from turtle_interfaces.srv import SetGain
from turtlesim.msg import Pose

from turtle_py.calculations import distance_to_goal, normalize_angle


class DrawPolygonServer(Node):
    def __init__(self) -> None:
        super().__init__('draw_polygon_server')

        self.declare_parameter('linear_speed', 1.0)
        self.declare_parameter('angular_speed', 1.5)
        self.declare_parameter('cmd_vel_topic', '/turtle1/cmd_vel')
        self.declare_parameter('pose_topic', '/turtle1/pose')
        self.declare_parameter('position_tolerance', 0.03)
        self.declare_parameter('angle_tolerance', 0.02)
        self.declare_parameter('linear_gain', 1.5)
        self.declare_parameter('angular_gain', 5.0)

        self._linear_speed = max(
            0.1, float(self.get_parameter('linear_speed').value))
        self._angular_speed = max(
            0.1, float(self.get_parameter('angular_speed').value))
        cmd_vel_topic = str(self.get_parameter('cmd_vel_topic').value)
        pose_topic = str(self.get_parameter('pose_topic').value)
        self._position_tolerance = max(
            0.005, float(self.get_parameter('position_tolerance').value))
        self._angle_tolerance = max(
            0.005, float(self.get_parameter('angle_tolerance').value))
        self._linear_gain = max(
            0.1, float(self.get_parameter('linear_gain').value))
        self._angular_gain = max(
            0.1, float(self.get_parameter('angular_gain').value))

        self._kp = self._angular_gain
        self._ki = 0.0
        self._kd = 0.0
        self._state_lock = threading.RLock()
        self._busy = False
        self._canceling = False
        self._distance_tracking = False
        self._distance_total = 0.0
        self._last_position = None
        self._callback_group = ReentrantCallbackGroup()
        self._latest_pose: Pose | None = None
        self._publisher = self.create_publisher(Twist, cmd_vel_topic, 10)
        self._pose_subscription = self.create_subscription(
            Pose,
            pose_topic,
            self._on_pose,
            10,
            callback_group=self._callback_group,
        )
        self._gain_service = self.create_service(
            SetGain,
            'set_polygon_gain',
            self._on_set_gain,
            callback_group=self._callback_group,
        )
        self._action_server = ActionServer(
            self,
            DrawPolygon,
            'draw_polygon',
            execute_callback=self._execute,
            goal_callback=self._on_goal,
            cancel_callback=self._on_cancel,
            callback_group=self._callback_group,
        )
        self.get_logger().info(
            f'DrawPolygon action server ready on /draw_polygon; '
            f'cmd_vel={cmd_vel_topic}')

    def _on_pose(self, message: Pose) -> None:
        with self._state_lock:
            self._latest_pose = message
            if self._distance_tracking:
                position = (float(message.x), float(message.y))
                if self._last_position is not None:
                    self._distance_total += math.hypot(
                        position[0] - self._last_position[0],
                        position[1] - self._last_position[1],
                    )
                self._last_position = position

    def _on_goal(self, goal_request: DrawPolygon.Goal) -> GoalResponse:
        if goal_request.sides < 3:
            self.get_logger().warning('rejecting polygon: sides must be at least 3')
            return GoalResponse.REJECT
        if not math.isfinite(goal_request.side_length) or goal_request.side_length <= 0.0:
            self.get_logger().warning(
                'rejecting polygon: side_length must be positive and finite')
            return GoalResponse.REJECT
        with self._state_lock:
            if self._busy:
                self.get_logger().warning('rejecting polygon: another goal is active')
                return GoalResponse.REJECT
            self._busy = True
            self._canceling = False
            self._distance_total = 0.0
        self.get_logger().info(
            f'accepting polygon: {goal_request.sides} sides, '
            f'{goal_request.side_length:.2f} m each')
        return GoalResponse.ACCEPT

    def _on_cancel(self, goal_handle) -> CancelResponse:
        del goal_handle
        with self._state_lock:
            self._canceling = True
            self._publisher.publish(Twist())
        self.get_logger().warning('polygon cancel request accepted; turtle stopped')
        return CancelResponse.ACCEPT

    def _on_set_gain(self, request: SetGain.Request, response: SetGain.Response):
        values = (request.kp, request.ki, request.kd)
        if not all(math.isfinite(value) and value >= 0.0 for value in values):
            response.success = False
            response.message = 'kp, ki, kd must be finite and zero or greater'
            self.get_logger().warning(response.message)
            return response

        self._kp, self._ki, self._kd = values
        response.success = True
        response.message = (
            f'gains stored: kp={self._kp:.2f}, '
            f'ki={self._ki:.2f}, kd={self._kd:.2f}')
        self.get_logger().info(response.message)
        return response

    @staticmethod
    def _clamp(value: float, limit: float) -> float:
        return max(-limit, min(value, limit))

    def _wait_for_pose(self, goal_handle) -> bool:
        for _ in range(100):
            if goal_handle.is_cancel_requested:
                return False
            if self._latest_pose is not None:
                return True
            time.sleep(0.05)
        self.get_logger().warning('pose was not received within 5 seconds')
        return False

    def _drive_to(self, goal_handle, target_x: float, target_y: float) -> bool:
        while rclpy.ok():
            if goal_handle.is_cancel_requested:
                self.stop()
                return False
            if self._latest_pose is None:
                time.sleep(0.05)
                continue

            distance = distance_to_goal(
                self._latest_pose.x,
                self._latest_pose.y,
                target_x,
                target_y,
            )
            if distance <= self._position_tolerance:
                self.stop()
                return True

            target_heading = math.atan2(
                target_y - self._latest_pose.y,
                target_x - self._latest_pose.x,
            )
            heading_error = normalize_angle(
                target_heading - self._latest_pose.theta)
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
            time.sleep(0.05)
        return False

    def _turn_to(self, goal_handle, target_heading: float) -> bool:
        while rclpy.ok():
            if goal_handle.is_cancel_requested:
                self.stop()
                return False
            if self._latest_pose is None:
                time.sleep(0.05)
                continue

            heading_error = normalize_angle(
                target_heading - self._latest_pose.theta)
            if abs(heading_error) <= self._angle_tolerance:
                self.stop()
                return True

            command = Twist()
            command.angular.z = self._clamp(
                self._kp * heading_error,
                self._angular_speed,
            )
            self._publish_motion(command)
            time.sleep(0.05)
        return False

    def _execute(self, goal_handle) -> DrawPolygon.Result:
        try:
            return self._execute_polygon(goal_handle)
        except Exception as error:
            self.stop()
            if goal_handle.is_active:
                goal_handle.abort()
            self.get_logger().error(f'polygon execution failed: {error}')
            result = DrawPolygon.Result()
            result.total_distance = self._measured_distance()
            return result
        finally:
            self.stop()
            with self._state_lock:
                self._distance_tracking = False
                self._busy = False

    def _execute_polygon(self, goal_handle) -> DrawPolygon.Result:
        sides = int(goal_handle.request.sides)
        side_length = float(goal_handle.request.side_length)
        turn_angle = 2.0 * math.pi / sides
        feedback = DrawPolygon.Feedback()
        result = DrawPolygon.Result()

        if not self._wait_for_pose(goal_handle):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
            else:
                goal_handle.abort()
            self.stop()
            result.total_distance = 0.0
            return result

        with self._state_lock:
            self._distance_total = 0.0
            self._last_position = (
                float(self._latest_pose.x), float(self._latest_pose.y))
            self._distance_tracking = True
            desired_heading = float(self._latest_pose.theta)

        for side_index in range(sides):
            target_x = (
                self._latest_pose.x + side_length * math.cos(desired_heading))
            target_y = (
                self._latest_pose.y + side_length * math.sin(desired_heading))
            self.get_logger().info(
                f'polygon side {side_index + 1}/{sides} target: '
                f'x={target_x:.3f}, y={target_y:.3f}')

            if not self._drive_to(goal_handle, target_x, target_y):
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    outcome = 'canceled'
                else:
                    goal_handle.abort()
                    outcome = 'aborted'
                result.total_distance = self._measured_distance()
                self.get_logger().warning(
                    f'polygon {outcome} after {side_index} complete side(s); '
                    f'distance={result.total_distance:.2f} m')
                return result

            feedback.completed_sides = side_index + 1
            feedback.progress = float((side_index + 1) / sides)
            goal_handle.publish_feedback(feedback)
            self.get_logger().info(
                f'polygon side {feedback.completed_sides}/{sides}; '
                f'progress={feedback.progress:.2f}')

            desired_heading = normalize_angle(desired_heading + turn_angle)
            if not self._turn_to(goal_handle, desired_heading):
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    outcome = 'canceled'
                else:
                    goal_handle.abort()
                    outcome = 'aborted'
                result.total_distance = self._measured_distance()
                self.get_logger().warning(
                    f'polygon {outcome} while turning; '
                    f'distance={result.total_distance:.2f} m')
                return result

        self.stop()
        goal_handle.succeed()
        result.total_distance = self._measured_distance()
        self.get_logger().info(
            f'polygon completed; total distance={result.total_distance:.2f} m')
        return result

    def stop(self) -> None:
        with self._state_lock:
            if rclpy.ok():
                self._publisher.publish(Twist())

    def _publish_motion(self, command: Twist) -> None:
        with self._state_lock:
            if not self._canceling and rclpy.ok():
                self._publisher.publish(command)

    def _measured_distance(self) -> float:
        with self._state_lock:
            return float(self._distance_total)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DrawPolygonServer()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        if rclpy.ok():
            node.get_logger().info('shutdown requested; stopping cleanly')
    finally:
        if rclpy.ok():
            node.stop()
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
