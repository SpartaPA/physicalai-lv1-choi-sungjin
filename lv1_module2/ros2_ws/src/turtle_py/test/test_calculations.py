"""Unit tests for the pure navigation calculation helpers."""

import math

import pytest

from turtle_py.calculations import (
    angle_to_goal,
    distance_to_goal,
    normalize_angle,
    waypoint_reached,
)


def test_distance_to_goal_normal_zero_and_invalid() -> None:
    assert distance_to_goal(0.0, 0.0, 3.0, 4.0) == pytest.approx(5.0)
    assert distance_to_goal(2.0, -1.0, 2.0, -1.0) == pytest.approx(0.0)
    with pytest.raises(ValueError):
        distance_to_goal(math.nan, 0.0, 1.0, 1.0)


def test_normalize_and_angle_to_goal() -> None:
    assert normalize_angle(0.0) == pytest.approx(0.0)
    assert normalize_angle(math.pi) == pytest.approx(-math.pi)
    assert normalize_angle(3.0 * math.pi) == pytest.approx(-math.pi)
    assert angle_to_goal(0.0, 0.0, 0.0, 0.0, 1.0) == pytest.approx(
        math.pi / 2.0)
    with pytest.raises(ValueError):
        normalize_angle(math.inf)


def test_waypoint_reached_inclusive_boundary_and_invalid_tolerance() -> None:
    assert waypoint_reached(0.0, 0.0, 0.3, 0.4, 0.5)
    assert not waypoint_reached(0.0, 0.0, 0.3, 0.4, 0.499)
    with pytest.raises(ValueError):
        waypoint_reached(0.0, 0.0, 1.0, 1.0, -0.1)
