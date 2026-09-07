"""Client for the custom DrawPolygon action with feedback and cancellation."""

import argparse
import math

import rclpy
from action_msgs.msg import GoalStatus
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtle_interfaces.action import DrawPolygon


class DrawPolygonClient(Node):
    def __init__(self, interactive_values: tuple[int, float] | None = None) -> None:
        super().__init__('draw_polygon_client')
        sides, side_length = interactive_values or (4, 2.0)
        self.declare_parameter(
            'sides', sides, ignore_override=interactive_values is not None)
        self.declare_parameter(
            'side_length', side_length, ignore_override=interactive_values is not None)
        self.declare_parameter('cancel_after_sec', -1.0)

        self._sides = int(self.get_parameter('sides').value)
        self._side_length = float(self.get_parameter('side_length').value)
        self._cancel_after = float(self.get_parameter('cancel_after_sec').value)
        self._client = ActionClient(self, DrawPolygon, 'draw_polygon')
        self._goal_handle = None
        self._cancel_timer = None
        self._cancel_future = None
        self._cancel_accepted = False

    def _on_feedback(self, feedback_message) -> None:
        feedback = feedback_message.feedback
        self.get_logger().info(
            f'polygon feedback: completed={feedback.completed_sides}, '
            f'progress={feedback.progress:.2f}')

    def _request_cancel(self) -> None:
        if self._cancel_timer is not None:
            self._cancel_timer.cancel()
        if self._goal_handle is None:
            return
        self.get_logger().warning('requesting DrawPolygon cancellation')
        future = self._goal_handle.cancel_goal_async()
        self._cancel_future = future
        future.add_done_callback(self._on_cancel_response)

    def _on_cancel_response(self, future) -> None:
        response = future.result()
        self._cancel_accepted = bool(response.goals_canceling)
        self.get_logger().info(
            f'cancel response: {len(response.goals_canceling)} goal(s)')

    def run(self) -> bool:
        if not self._client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('DrawPolygon action server is unavailable')
            return False

        goal = DrawPolygon.Goal()
        goal.sides = self._sides
        goal.side_length = self._side_length
        self.get_logger().info(
            f'sending polygon goal: sides={self._sides}, '
            f'side_length={self._side_length:.2f}')

        send_future = self._client.send_goal_async(
            goal, feedback_callback=self._on_feedback)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=5.0)
        if not send_future.done():
            self.get_logger().error('timed out waiting for polygon goal acceptance')
            return False
        self._goal_handle = send_future.result()
        if self._goal_handle is None or not self._goal_handle.accepted:
            self.get_logger().error('polygon goal was rejected')
            return False

        if self._cancel_after > 0.0:
            self._cancel_timer = self.create_timer(
                self._cancel_after, self._request_cancel)

        result_future = self._goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=120.0)
        if not result_future.done():
            self.get_logger().error('timed out waiting for polygon result')
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
        self.get_logger().info(
            f'polygon result: {status_name}, '
            f'total_distance={wrapped_result.result.total_distance:.2f} m')
        expected_status = (
            GoalStatus.STATUS_CANCELED if self._cancel_after > 0.0
            else GoalStatus.STATUS_SUCCEEDED
        )
        if wrapped_result.status != expected_status:
            self.get_logger().error('polygon outcome did not match the requested scenario')
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


def read_polygon_input() -> tuple[int, float]:
    """Read valid polygon dimensions from the terminal, retrying invalid input."""
    while True:
        try:
            sides = int(input('변의 개수를 입력하세요 (3 이상 정수): ').strip())
        except ValueError:
            print('변의 개수는 3 이상의 정수로 입력하세요.')
            continue
        if 3 <= sides <= 2_147_483_647:
            break
        print('변의 개수는 3 이상 2147483647 이하로 입력하세요.')

    while True:
        try:
            side_length = float(input('한 변의 길이를 입력하세요 (m, 0보다 큰 수): ').strip())
        except ValueError:
            print('한 변의 길이는 0보다 큰 유한한 숫자로 입력하세요.')
            continue
        if math.isfinite(side_length) and side_length > 0.0:
            return sides, side_length
        print('한 변의 길이는 0보다 큰 유한한 숫자로 입력하세요.')


def main(args=None) -> int:
    parser = argparse.ArgumentParser(description='다각형 목표를 ROS 2 액션 서버에 전송합니다.')
    parser.add_argument(
        '--interactive', action='store_true',
        help='터미널에서 변의 개수와 한 변의 길이를 입력합니다.')
    options, ros_args = parser.parse_known_args(args)
    interactive_values = None
    if options.interactive:
        try:
            interactive_values = read_polygon_input()
        except (EOFError, KeyboardInterrupt):
            print('\n입력을 종료했습니다. 다각형 목표를 보내지 않았습니다.')
            return 0
        print(
            f'입력한 목표: {interactive_values[0]}각형, '
            f'한 변의 길이 {interactive_values[1]:g} m')

    rclpy.init(args=ros_args)
    node = DrawPolygonClient(interactive_values=interactive_values)
    exit_code = 1
    try:
        exit_code = 0 if node.run() else 1
    except (KeyboardInterrupt, ExternalShutdownException):
        exit_code = 130
    except Exception as error:
        node.get_logger().error(f'polygon action failed: {error}')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
