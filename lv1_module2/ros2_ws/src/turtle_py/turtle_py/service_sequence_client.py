"""Call four built-in turtlesim services sequentially with async clients."""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_srvs.srv import Empty
from turtlesim.srv import SetPen, Spawn, TeleportAbsolute


class ServiceSequenceClient(Node):
    def __init__(self) -> None:
        super().__init__('service_sequence_client')
        self._teleport = self.create_client(
            TeleportAbsolute, '/turtle1/teleport_absolute')
        self._set_pen = self.create_client(SetPen, '/turtle1/set_pen')
        self._spawn = self.create_client(Spawn, '/spawn')
        self._clear = self.create_client(Empty, '/clear')

    def _call(self, client, request, service_name: str):
        if not client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error(f'service unavailable: {service_name}')
            return None

        self.get_logger().info(f'calling {service_name} with call_async()')
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=8.0)
        if not future.done():
            self.get_logger().error(f'timeout waiting for {service_name}')
            return None
        try:
            response = future.result()
        except Exception as error:  # noqa: BLE001 - report ROS service failures
            self.get_logger().error(f'{service_name} failed: {error}')
            return None
        self.get_logger().info(f'{service_name} response: {response}')
        return response

    def run_sequence(self) -> bool:
        teleport_request = TeleportAbsolute.Request()
        teleport_request.x = 3.0
        teleport_request.y = 3.0
        teleport_request.theta = 0.0
        if self._call(
                self._teleport,
                teleport_request,
                '/turtle1/teleport_absolute') is None:
            return False

        pen_request = SetPen.Request()
        pen_request.r = 255
        pen_request.g = 80
        pen_request.b = 40
        pen_request.width = 3
        pen_request.off = 0
        if self._call(self._set_pen, pen_request, '/turtle1/set_pen') is None:
            return False

        spawn_request = Spawn.Request()
        spawn_request.x = 8.0
        spawn_request.y = 8.0
        spawn_request.theta = 0.0
        spawn_request.name = 'turtle2'
        spawn_response = self._call(self._spawn, spawn_request, '/spawn')
        if spawn_response is None or spawn_response.name != spawn_request.name:
            self.get_logger().error(
                'spawn failed to create turtle2; service sequence stopped')
            return False

        clear_request = Empty.Request()
        if self._call(self._clear, clear_request, '/clear') is None:
            return False

        self.get_logger().info('all four built-in service calls completed')
        return True


def main(args=None) -> int:
    rclpy.init(args=args)
    node = ServiceSequenceClient()
    exit_code = 1
    try:
        exit_code = 0 if node.run_sequence() else 1
    except (KeyboardInterrupt, ExternalShutdownException):
        exit_code = 130
    except Exception as error:
        node.get_logger().error(f'service sequence failed: {error}')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
