"""문제 2 — camera 에서 base 로의 변환 파이프라인. (학생 작성용 템플릿)

모듈 ③ 의 회전·동차변환·좌표 체인 모듈을 한데 묶어 쓰는 `PosePipeline` 을 작성한다.

    base --T_base_link--> link --T_link_camera--> camera --(관측)--> 물체 점군

    T_base_camera = T_base_link @ T_link_camera
    P_base        = transform_points(T_base_camera, P_cam)      # (N,3) 한 번에

관절이 움직이면 link 변환이 바뀐다. 이 템플릿은 "link 가 자기 z축 둘레로 theta 만큼
돈다" 로 단순화한다 (`set_joint_angle`). 실제 로봇이라면 관절마다 축과 오프셋이 다르다.
"""

from __future__ import annotations

import numpy as np

from .rotation import rot_x, rot_y, rot_z
from .transform import inv_T, make_T, transform_points

__all__ = ["PosePipeline"]

_ROT = {"x": rot_x, "y": rot_y, "z": rot_z}


class PosePipeline:
    """base -> link -> camera 변환을 보관하고 카메라 점군을 base 좌표로 바꾼다.

    Parameters
    ----------
    T_base_link : (4,4) base 기준 link 자세 T(base <- link) — 관절 각도 0 일 때의 값
    T_link_camera : (4,4) link 기준 camera 자세 T(link <- camera)
    joint_axis : 관절 회전축 ("x" | "y" | "z"), link 좌표계 기준

    Examples
    --------
    >>> pipe = PosePipeline(T_base_link, T_link_camera)
    >>> P_base = pipe.camera_to_base(P_cam)          # (N,3) -> (N,3)
    >>> P_cam2 = pipe.base_to_camera(P_base)         # 왕복 -> P_cam 과 같아야 한다
    >>> pipe.set_joint_angle(np.deg2rad(30.0))       # 관절이 30도 돌아간 상황
    """

    def __init__(self, T_base_link, T_link_camera, joint_axis: str = "z"):
        T_base_link = np.asarray(T_base_link, dtype=float)
        T_link_camera = np.asarray(T_link_camera, dtype=float)
        if T_base_link.shape != (4, 4):
            raise ValueError(f"T_base_link는 4x4여야 합니다. 받은 shape={T_base_link.shape}")
        if T_link_camera.shape != (4, 4):
            raise ValueError(f"T_link_camera는 4x4여야 합니다. 받은 shape={T_link_camera.shape}")
        if joint_axis not in _ROT:
            raise ValueError("joint_axis는 'x', 'y', 'z' 중 하나여야 합니다")
        self._T_base_link0 = T_base_link.copy()
        self._T_link_camera = T_link_camera.copy()
        self.joint_axis = joint_axis
        self.joint_angle = 0.0

    # ------------------------------------------------------------- 변환 행렬

    @property
    def T_base_link(self) -> np.ndarray:
        """현재 관절 각도가 반영된 T(base <- link).

        관절이 link 의 joint_axis 둘레로 joint_angle 만큼 돈 것으로 본다:
            T_base_link = T_base_link0 @ make_T(R_axis(joint_angle), [0, 0, 0])
        """
        joint_rotation = make_T(_ROT[self.joint_axis](self.joint_angle), np.zeros(3))
        return self._T_base_link0 @ joint_rotation

    @property
    def T_link_camera(self) -> np.ndarray:
        """T(link <- camera) — 카메라는 link 에 고정돼 있으므로 관절과 무관하다."""
        return self._T_link_camera.copy()

    @property
    def T_base_camera(self) -> np.ndarray:
        """합성 변환 T(base <- camera) = T_base_link @ T_link_camera."""
        return self.T_base_link @ self._T_link_camera

    @property
    def T_camera_base(self) -> np.ndarray:
        """역변환 T(camera <- base) = inv_T(T_base_camera). 왕복 검증에 쓴다."""
        return inv_T(self.T_base_camera)

    # ------------------------------------------------------------- 관절

    def set_joint_angle(self, theta: float) -> "PosePipeline":
        """관절 각도 [rad] 를 바꾼다. 메서드 체이닝을 위해 self 를 돌려준다."""
        self.joint_angle = float(theta)
        return self

    # ------------------------------------------------------------- 점군 변환

    def camera_to_base(self, P_cam) -> np.ndarray:
        """카메라 기준 점군 (N,3) 또는 점 (3,) 을 base 기준으로 바꾼다.

        반복문을 쓰지 말고 모듈 ③ 의 `transform_points` 로 한 번에 변환한다.
        """
        return transform_points(self.T_base_camera, P_cam)

    def base_to_camera(self, P_base) -> np.ndarray:
        """base 기준 점군을 카메라 기준으로 되돌린다 (왕복 검증용)."""
        return transform_points(self.T_camera_base, P_base)

    def object_pose_in_base(self, T_camera_object) -> np.ndarray:
        """카메라 기준 물체 자세 T(camera <- object) 를 base 기준 T(base <- object) 로 바꾼다.

        문제 6 에서 추정한 물체 자세를 목표 자세로 옮길 때 쓴다.
        """
        T_camera_object = np.asarray(T_camera_object, dtype=float)
        if T_camera_object.shape != (4, 4):
            raise ValueError(f"T_camera_object는 4x4여야 합니다. 받은 shape={T_camera_object.shape}")
        return self.T_base_camera @ T_camera_object

    def __repr__(self) -> str:
        return "PosePipeline(joint_axis={!r}, joint_angle={:.4f} rad)".format(
            getattr(self, "joint_axis", "?"), getattr(self, "joint_angle", float("nan")))
