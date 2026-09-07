"""ROS와 무관하게 단위 테스트할 수 있는 순수 계산 함수."""

import math


def _require_finite(*values: float) -> None:
    if not all(math.isfinite(value) for value in values):
        raise ValueError('all numeric inputs must be finite')


def distance_to_goal(x: float, y: float, goal_x: float, goal_y: float) -> float:
    """Return the Euclidean distance from the current point to the goal."""
    _require_finite(x, y, goal_x, goal_y)
    return math.hypot(goal_x - x, goal_y - y)


def normalize_angle(angle: float) -> float:
    """Normalize an angle to the half-open interval [-pi, pi)."""
    _require_finite(angle)
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def angle_to_goal(
    x: float,
    y: float,
    heading: float,
    goal_x: float,
    goal_y: float,
) -> float:
    """Return the normalized heading error toward the goal."""
    _require_finite(x, y, heading, goal_x, goal_y)
    target_heading = math.atan2(goal_y - y, goal_x - x)
    return normalize_angle(target_heading - heading)


def waypoint_reached(
    x: float,
    y: float,
    goal_x: float,
    goal_y: float,
    tolerance: float,
) -> bool:
    """Return True when the goal is within the inclusive tolerance boundary."""
    _require_finite(tolerance)
    if tolerance < 0.0:
        raise ValueError('tolerance must be zero or greater')
    return distance_to_goal(x, y, goal_x, goal_y) <= tolerance
