"""문제 2 — PosePipeline 검증 (pytest). [학생 작성용 템플릿]

지시문이 요구하는 "2개 이상" 을 아래 두 테스트로 채운다.

  1. camera_to_base 가 모듈 ③ 체인(행렬 곱)과 같은 결과를 주는가  -> test_camera_to_base_matches_chain
  2. base 로 갔다가 camera 로 되돌리면 원래 점군이 나오는가       -> test_roundtrip_restores_points

작성 요령
--------
- 비교는 `np.allclose` (기본 허용오차) 로 한다.
- 난수는 반드시 시드를 고정한다 (fixture `rng`).
- 관절 각도 0 에서 파이프라인이 default_chain 과 같은지, 각도를 바꾸면 결과가 달라지는지 등
  테스트를 더 붙이면 좋다 (아래 권장 예시).

실행: 프로젝트 루트에서  pytest tests/test_pose_pipeline.py -v
"""

import numpy as np
import pytest

from src.coordinate_chain import default_chain
from src.pose_pipeline import PosePipeline
from src.transform import make_T, transform_points
from src.rotation import rot_x, rot_y, rot_z


@pytest.fixture
def rng():
    """난수는 반드시 시드를 고정한다."""
    return np.random.default_rng(42)


@pytest.fixture
def pipeline():
    """모듈 ③ default_chain 과 같은 값으로 만든 파이프라인."""
    chain = default_chain()
    return PosePipeline(chain.get("base", "link"), chain.get("link", "camera"))


# --- 1. camera_to_base == 체인/행렬 곱 --------------------------------------

def test_camera_to_base_matches_chain(pipeline, rng):
    points = rng.normal(size=(300, 3))
    actual = pipeline.camera_to_base(points)
    chain = default_chain()
    expected_chain = chain.transform("base", "camera", points)
    expected_product = transform_points(
        pipeline.T_base_link @ pipeline.T_link_camera, points
    )
    assert np.allclose(actual, expected_chain)
    assert np.allclose(actual, expected_product)


# --- 2. 왕복 검증 -------------------------------------------------------------

def test_roundtrip_restores_points(pipeline, rng):
    point = rng.normal(size=3)
    points = rng.normal(size=(500, 3))
    assert np.allclose(pipeline.base_to_camera(pipeline.camera_to_base(point)), point)
    assert np.allclose(pipeline.base_to_camera(pipeline.camera_to_base(points)), points)


# --- 여기부터는 추가 테스트 (권장) -------------------------------------------
#
# 예) def test_joint_angle_zero_is_nominal(pipeline):
#         """set_joint_angle(0) 이면 T_base_link 가 생성자에 준 값 그대로."""
#
# 예) def test_joint_angle_changes_result(pipeline, rng):
#         """관절 각도를 바꾸면 같은 관측이 base 에서 다른 위치로 간다."""
#
# 예) def test_distance_is_preserved(pipeline, rng):
#         """강체 변환은 두 점 사이 거리를 보존한다."""
#
# 예) def test_rejects_wrong_shape():
#         """(3,3) 을 넣으면 ValueError."""


def test_joint_angle_zero_is_nominal(pipeline):
    nominal = pipeline.T_base_link.copy()
    assert pipeline.set_joint_angle(0.0) is pipeline
    assert np.allclose(pipeline.T_base_link, nominal)


def test_joint_angle_changes_result(pipeline, rng):
    points = rng.normal(size=(20, 3))
    nominal = pipeline.camera_to_base(points)
    changed = pipeline.set_joint_angle(np.deg2rad(30.0)).camera_to_base(points)
    assert not np.allclose(changed, nominal)


def test_distance_is_preserved(pipeline, rng):
    points = rng.normal(size=(100, 3))
    transformed = pipeline.camera_to_base(points)
    assert np.allclose(
        np.linalg.norm(points[1:] - points[:-1], axis=1),
        np.linalg.norm(transformed[1:] - transformed[:-1], axis=1),
    )


def test_rejects_wrong_shape():
    with pytest.raises(ValueError):
        PosePipeline(np.eye(3), np.eye(4))
    with pytest.raises(ValueError):
        PosePipeline(np.eye(4), np.eye(4), joint_axis="w")


@pytest.mark.parametrize("axis,rotation", [("x", rot_x), ("y", rot_y)])
def test_joint_rotation_uses_link_axis(axis, rotation):
    base_rotation = rot_z(0.6)
    camera_rotation = rot_x(-0.2)
    base_translation = np.array([0.3, 0.1, 0.4])
    camera_translation = np.array([0.2, -0.1, 0.3])
    pipe = PosePipeline(
        make_T(base_rotation, base_translation),
        make_T(camera_rotation, camera_translation), joint_axis=axis,
    ).set_joint_angle(0.8)
    point = np.array([0.4, 0.2, -0.1])
    expected = base_rotation @ (
        rotation(0.8) @ (camera_rotation @ point + camera_translation)
    ) + base_translation
    assert np.allclose(pipe.camera_to_base(point), expected)
    assert np.allclose(pipe.base_to_camera(expected), point)


def test_object_pose_matches_four_frame_chain(pipeline, rng):
    """물체 점이 object→camera→base를 거친 결과와 합성 자세가 일치한다."""
    pipeline.set_joint_angle(0.4)
    camera_object = make_T(rot_y(-0.3) @ rot_z(0.8), [0.2, 0.1, 0.5])
    object_points = rng.normal(size=(20, 3))
    expected = pipeline.camera_to_base(transform_points(camera_object, object_points))
    base_object = pipeline.object_pose_in_base(camera_object)
    assert np.allclose(transform_points(base_object, object_points), expected)
    assert np.allclose(base_object[:3, :3].T @ base_object[:3, :3], np.eye(3))
