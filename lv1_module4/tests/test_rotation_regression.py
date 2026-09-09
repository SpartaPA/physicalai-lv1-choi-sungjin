"""모듈 3에서 재사용한 회전 함수의 경계값 회귀 검사."""

import numpy as np
import pytest

from src.rotation import axis_angle_from_matrix, rodrigues


@pytest.mark.parametrize("axis", [[-1.0, 0.0, 0.0], [-3.0, 1.0, 2.0]])
@pytest.mark.parametrize("angle", [np.pi - 5e-7, np.pi, np.pi + 5e-7])
def test_axis_angle_roundtrip_near_pi(axis, angle):
    rotation = rodrigues(axis, angle)
    recovered_axis, recovered_angle = axis_angle_from_matrix(rotation)
    assert 0.0 <= recovered_angle <= np.pi
    assert np.isclose(np.linalg.norm(recovered_axis), 1.0, atol=1e-12, rtol=0.0)
    assert np.allclose(
        rodrigues(recovered_axis, recovered_angle), rotation, atol=1e-8, rtol=0.0
    )
    if angle == np.pi:
        assert recovered_axis[np.argmax(np.abs(recovered_axis))] > 0.0
