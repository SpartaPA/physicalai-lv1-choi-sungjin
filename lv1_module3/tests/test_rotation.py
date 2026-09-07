"""문제 3 — 회전 행렬의 수학적 성질 검증 (pytest). [학생 작성용 템플릿]

지시문이 요구하는 4가지를 각각 테스트 함수로 작성한다.

  1. 회전행렬의 열이 서로 직교하는 단위벡터인가   -> test_columns_are_orthonormal
  2. 행렬식이 1인가                               -> test_determinant_is_one
  3. 역행렬이 전치와 같은가                       -> test_inverse_equals_transpose
  4. 재직교화 결과가 직교행렬인가                 -> test_gram_schmidt_restores_orthogonality

작성 요령
--------
- `@pytest.mark.parametrize` 로 여러 축 x 여러 각도를 한 함수에서 검사하면
  테스트 하나가 여러 케이스를 담당한다 (아래 ANGLES / MAKERS 참고).
- 비교는 반드시 `np.isclose` / `np.allclose` 로 한다 (부동소수점).
- `np.linalg` 는 검산용으로만 쓰고, 쓸 때는 주석으로 검산임을 밝힌다.
- assert 에 실패 메시지를 붙이면 어디가 깨졌는지 바로 보인다.
- 4개는 **최소 개수**다. 반사 행렬 반례, 로드리게스 일치, 축·각 왕복 같은
  테스트를 더 붙이면 좋다.

실행: 프로젝트 루트에서  pytest -v
"""

import numpy as np
import pytest

from src.rotation import (
    axis_angle_from_matrix,
    gram_schmidt,
    is_rotation,
    orthogonality_error,
    rodrigues,
    rot_x,
    rot_y,
    rot_z,
)

ANGLES = [0.0, np.deg2rad(22.5), np.pi / 6, np.pi / 4, np.pi / 2, 2.0, np.pi, -1.234]
MAKERS = [rot_x, rot_y, rot_z]


@pytest.fixture
def rng():
    """난수는 반드시 시드를 고정한다."""
    return np.random.default_rng(42)


# --- 1. 열이 서로 직교하는 단위벡터인가 -------------------------------------

@pytest.mark.parametrize("maker", MAKERS)
@pytest.mark.parametrize("theta", ANGLES)
def test_columns_are_orthonormal(maker, theta):
    R = maker(theta)
    gram = R.T @ R
    assert np.allclose(np.diag(gram), np.ones(3), atol=1e-12)
    assert np.allclose(gram - np.diag(np.diag(gram)), np.zeros((3, 3)), atol=1e-12)


# --- 2. 행렬식이 1인가 --------------------------------------------------------

@pytest.mark.parametrize("maker", MAKERS)
@pytest.mark.parametrize("theta", ANGLES)
def test_determinant_is_one(maker, theta):
    R = maker(theta)
    # np.linalg.det은 직접 구현한 회전행렬의 성질을 검산하는 데만 사용한다.
    assert np.isclose(np.linalg.det(R), 1.0, atol=1e-12)


# --- 3. 역행렬 == 전치 --------------------------------------------------------

@pytest.mark.parametrize("maker", MAKERS)
@pytest.mark.parametrize("theta", ANGLES)
def test_inverse_equals_transpose(maker, theta):
    R = maker(theta)
    # np.linalg.inv는 전치 역행렬 공식을 검산하는 데만 사용한다.
    assert np.allclose(np.linalg.inv(R), R.T, atol=1e-12)
    assert np.allclose(R.T @ R, np.eye(3), atol=1e-12)


# --- 4. 재직교화 결과가 직교행렬인가 -----------------------------------------

def test_gram_schmidt_restores_orthogonality(rng):
    R = rot_z(0.7) @ rot_y(-0.3) @ rot_x(0.2)
    noisy = R + rng.normal(0.0, 1e-3, size=(3, 3))
    before = orthogonality_error(noisy)
    restored = gram_schmidt(noisy)
    after = orthogonality_error(restored)
    assert before > 1e-6
    assert after < 1e-12
    assert np.isclose(np.linalg.det(restored), 1.0, atol=1e-12)
    assert is_rotation(restored)


# --- 여기부터는 추가 테스트 (권장) -------------------------------------------
#
# 예) def test_reflection_is_not_a_rotation():
#         """det = -1 인 반사 행렬은 직교여도 회전이 아니다."""
#
# 예) def test_rodrigues_matches_rot_z(theta): ...
# 예) def test_axis_angle_roundtrip(rng): ...


def test_reflection_is_not_a_rotation():
    reflection = np.diag([1.0, 1.0, -1.0])
    assert np.allclose(reflection.T @ reflection, np.eye(3))
    assert not is_rotation(reflection)


@pytest.mark.parametrize("theta", ANGLES)
def test_rodrigues_matches_rot_z(theta):
    assert np.allclose(rodrigues([0.0, 0.0, 4.0], theta), rot_z(theta), atol=1e-12)


def test_axis_angle_roundtrip(rng):
    axis = rng.normal(size=3)
    angle = 1.1
    R = rodrigues(axis, angle)
    recovered_axis, recovered_angle = axis_angle_from_matrix(R)
    assert np.isclose(recovered_angle, angle, atol=1e-10)
    assert np.allclose(rodrigues(recovered_axis, recovered_angle), R, atol=1e-10)


@pytest.mark.parametrize("axis", [[-1.0, 0.0, 0.0], [-3.0, 1.0, 2.0]])
@pytest.mark.parametrize("angle", [np.pi - 5e-7, np.pi, np.pi + 5e-7])
def test_axis_angle_roundtrip_near_pi(axis, angle):
    """pi에 가까워도 반대칭 성분에 남아 있는 회전 방향을 보존한다."""
    R = rodrigues(axis, angle)
    recovered_axis, recovered_angle = axis_angle_from_matrix(R)
    expected_angle = min(angle, 2.0 * np.pi - angle)
    assert 0.0 <= recovered_angle <= np.pi
    assert np.isclose(np.sum(recovered_axis ** 2), 1.0, atol=1e-12, rtol=0.0)
    # trace/arccos의 pi 근처 반올림은 허용하되 잘못된 축 부호는 검출한다.
    assert np.isclose(recovered_angle, expected_angle, atol=1e-8, rtol=0.0)
    assert np.allclose(rodrigues(recovered_axis, recovered_angle), R,
                       atol=1e-8, rtol=0.0)
    if angle == np.pi:
        assert recovered_axis[np.argmax(np.abs(recovered_axis))] > 0.0


def test_axis_angle_identity_uses_positive_x_axis():
    axis, angle = axis_angle_from_matrix(np.eye(3))
    assert np.array_equal(axis, np.array([1.0, 0.0, 0.0]))
    assert angle == 0.0
