"""문제 5 — 동차변환 inv_T 검증 (pytest). [학생 작성용 템플릿]

지시문이 요구하는 것은 `inv_T` 검증이지만,
점/방향 구분과 벡터화, 최소자승까지 함께 검증해 두면 이후 문제에서 안전하다.

실행: 프로젝트 루트에서  pytest -v
"""

import numpy as np
import pytest

from src.rotation import rot_x, rot_y, rot_z
from src.transform import (
    inv_T,
    least_squares_normal_equation,
    make_T,
    transform_direction,
    transform_point,
    transform_points,
)


@pytest.fixture
def T():
    """테스트에 쓸 대표 동차변환 하나."""
    R = rot_z(0.9) @ rot_y(-0.35) @ rot_x(1.3)
    return make_T(R, [0.35, -0.15, 0.55])


def test_inv_T_gives_identity(T):
    T_inv = inv_T(T)
    assert np.allclose(T_inv @ T, np.eye(4), atol=1e-12)
    assert np.allclose(T @ T_inv, np.eye(4), atol=1e-12)


def test_inv_T_matches_generic_inverse(T):
    # np.linalg.inv는 동차변환 전용 역변환 공식을 검산하는 데만 사용한다.
    assert np.allclose(inv_T(T), np.linalg.inv(T), atol=1e-12)


def test_point_and_direction_differ(T):
    value = np.array([0.2, -0.7, 1.1])
    as_point = transform_point(T, value)
    as_direction = transform_direction(T, value)
    assert not np.allclose(as_point, as_direction)
    assert np.allclose(as_point - as_direction, T[:3, 3], atol=1e-12)
    assert np.isclose(np.linalg.norm(as_direction), np.linalg.norm(value), atol=1e-12)


def test_transform_points_is_vectorized(T):
    points = np.random.default_rng(42).normal(size=(100, 3))
    vectorized = transform_points(T, points)
    loop_result = np.vstack([transform_point(T, point) for point in points])
    assert np.allclose(vectorized, loop_result, atol=1e-12)


def test_roundtrip_through_inverse(T):
    points = np.random.default_rng(42).uniform(-2.0, 2.0, size=(200, 3))
    restored = transform_points(inv_T(T), transform_points(T, points))
    assert np.allclose(restored, points, atol=1e-12)


def test_least_squares_matches_lstsq():
    rng = np.random.default_rng(42)
    A = rng.normal(size=(80, 4))
    expected = np.array([0.5, -1.2, 2.0, 0.3])
    b = A @ expected + rng.normal(0.0, 0.01, size=80)
    actual, residual = least_squares_normal_equation(A, b)
    # np.linalg.lstsq는 직접 구현한 정규방정식 해를 검산하는 데만 사용한다.
    reference, *_ = np.linalg.lstsq(A, b, rcond=None)
    assert np.allclose(actual, reference, atol=1e-10)
    assert np.allclose(A.T @ residual, np.zeros(A.shape[1]), atol=1e-10)
