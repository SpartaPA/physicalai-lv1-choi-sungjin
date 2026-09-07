"""Send a turtlesim RotateAbsolute goal, print feedback, and optionally cancel."""

import rclpy
from action_msgs.msg import GoalStatus
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtlesim.action import RotateAbsolute
from turtlesim.msg import Pose


class RotateActionClient(Node):
    def __init__(self) -> None:
        super().__init__('rotate_action_client')
        self.declare_parameter('target_angle', 1.57)
        self.declare_parameter('cancel_after_sec', -1.0)

        self._target_angle = float(self.get_parameter('target_angle').value)
        self._cancel_after = float(self.get_parameter('cancel_after_sec').value)
        self._latest_angle: float | None = None
        self._goal_handle = None
        self._cancel_timer = None
        self._cancel_future = None
        self._cancel_accepted = False

        self._pose_subscription = self.create_subscription(
            Pose, '/turtle1/pose', self._on_pose, 10)
        self._client = ActionClient(
            self, RotateAbsolute, '/turtle1/rotate_absolute')

    def _on_pose(self, message: Pose) -> None:
        self._latest_angle = float(message.theta)

    def _on_feedback(self, feedback_message) -> None:
        remaining = feedback_message.feedback.remaining
        self.get_logger().info(f'rotation remaining: {remaining:.4f} rad')

    def _request_cancel(self) -> None:
        if self._cancel_timer is not None:
            self._cancel_timer.cancel()
        if self._goal_handle is None:
            return
        angle_text = (
            'unknown' if self._latest_angle is None
            else f'{self._latest_angle:.4f} rad')
        self.get_logger().warning(
            f'requesting action cancel at turtle angle {angle_text}')
        cancel_future = self._goal_handle.cancel_goal_async()
        self._cancel_future = cancel_future
        cancel_future.add_done_callback(self._on_cancel_response)

    def _on_cancel_response(self, future) -> None:
        response = future.result()
        self._cancel_accepted = bool(response.goals_canceling)
        self.get_logger().info(
            f'cancel response: {len(response.goals_canceling)} goal(s) canceling')

    def run(self) -> bool:
        if not self._client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('RotateAbsolute action server is unavailable')
            return False

        goal = RotateAbsolute.Goal()
        goal.theta = float(self._target_angle)
        self.get_logger().info(
            f'sending target angle {self._target_angle:.4f} rad')
        send_future = self._client.send_goal_async(
            goal, feedback_callback=self._on_feedback)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=5.0)
        if not send_future.done():
            self.get_logger().error('timed out waiting for rotation goal acceptance')
            return False
        self._goal_handle = send_future.result()
        if self._goal_handle is None or not self._goal_handle.accepted:
            self.get_logger().error('rotation goal was rejected')
            return False

        self.get_logger().info('rotation goal accepted')
        if self._cancel_after > 0.0:
            self._cancel_timer = self.create_timer(
                self._cancel_after, self._request_cancel)

        result_future = self._goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=30.0)
        if not result_future.done():
            self.get_logger().error('timed out waiting for action result')
            cancel_future = self._goal_handle.cancel_goal_async()
            rclpy.spin_until_future_complete(self, cancel_future, timeout_sec=5.0)
            return False

        wrapped_result = result_future.result()
        status_names = {
            GoalStatus.STATUS_SUCCEEDED: 'SUCCEEDED',
            GoalStatus.STATUS_CANCELED: 'CANCELED',
            GoalStatus.STATUS_ABORTED: 'ABORTED',
        }
        status_name = status_names.get(wrapped_result.status, str(wrapped_result.status))
        self.get_logger().info(f'rotation action finished: {status_name}')
        expected_status = (
            GoalStatus.STATUS_CANCELED if self._cancel_after > 0.0
            else GoalStatus.STATUS_SUCCEEDED
        )
        if wrapped_result.status != expected_status:
            self.get_logger().error('rotation outcome did not match the requested scenario')
            return False
        if self._cancel_future is not None and not self._cancel_future.done():
            rclpy.spin_until_future_complete(
                self, self._cancel_future, timeout_sec=5.0)
        if self._cancel_future is not None and self._cancel_future.done():
            self._cancel_accepted = bool(
                self._cancel_future.result().goals_canceling)
        if self._cancel_after > 0.0 and not self._cancel_accepted:
            self.get_logger().error('cancellation was not acknowledged by the server')
            return False
        return True


def main(args=None) -> int:
    rclpy.init(args=args)
    node = RotateActionClient()
    exit_code = 1
    try:
        exit_code = 0 if node.run() else 1
    except (KeyboardInterrupt, ExternalShutdownException):
        exit_code = 130
    except Exception as error:
        node.get_logger().error(f'rotation action failed: {error}')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
