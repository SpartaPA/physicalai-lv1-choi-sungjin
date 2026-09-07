"""문제 2·3 — 회전 행렬 모듈. (학생 작성용 템플릿)

축별 회전 행렬, 로드리게스 공식(임의 축 회전), Gram-Schmidt 재직교화,
회전행렬 판정과 고유값 분해 기반 축·각 복원을 직접 구현한다.

문제 1 에서 만든 `src/vectors.py` 를 그대로 재사용한다.
"""

from __future__ import annotations

import numpy as np

from .vectors import det, normalize, skew

__all__ = [
    "rot_x",
    "rot_y",
    "rot_z",
    "rodrigues",
    "gram_schmidt",
    "orthogonality_error",
    "is_rotation",
    "axis_angle_from_matrix",
    "quaternion_from_axis_angle",
]


# ------------------------------------------------------------ 축별 회전 행렬

def rot_x(theta: float) -> np.ndarray:
    """x축 기준 회전 행렬 (theta 는 **라디안**). x 성분은 보존된다."""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def rot_y(theta: float) -> np.ndarray:
    """y축 기준 회전 행렬 (theta 는 라디안). y 성분은 보존된다.

    부호 배치가 x·z 와 반대로 보이는 이유는 노트북 2-1 에서 설명한다.
    """
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def rot_z(theta: float) -> np.ndarray:
    """z축 기준 회전 행렬 (theta 는 라디안). z 성분은 보존된다."""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def rodrigues(axis, theta: float) -> np.ndarray:
    """로드리게스 공식으로 임의 축 회전 행렬을 만든다.

        R = I + sin(theta) * K + (1 - cos(theta)) * K @ K,   K = [k]_x

    - 축은 함수 안에서 단위벡터로 정규화한다
      (정규화되지 않은 축을 넣어도 같은 결과가 나와야 한다).
    - 문제 1 의 `skew` 를 반드시 사용한다.
    """
    k = normalize(axis)
    if k.shape != (3,):
        raise ValueError(f"회전축은 3차원이어야 합니다. 받은 shape={k.shape}")
    K = skew(k)
    return np.eye(3) + np.sin(theta) * K + (1.0 - np.cos(theta)) * (K @ K)


# ------------------------------------------------------------- 재직교화 관련

def gram_schmidt(A) -> np.ndarray:
    """**열벡터**에 대해 Gram-Schmidt 직교정규화를 수행한다.

        q1 = a1 / |a1|
        vj = aj - sum_{i<j} (qi · aj) qi
        qj = vj / |vj|

    각 열에서 앞선 열 방향 성분(정사영)을 빼고 정규화하는 것이며,
    문제 1 의 project / reject 와 같은 연산의 반복이다.

    수치적으로는 성분을 빼자마자 갱신하는 modified Gram-Schmidt 가 더 안정적이다.
    앞선 열들에 종속인 열이 있으면 ValueError.
    """
    A = np.asarray(A, dtype=float)
    if A.ndim != 2:
        raise ValueError(f"2차원 행렬이 필요합니다. 받은 shape={A.shape}")
    m, n = A.shape
    if n > m:
        raise ValueError("열 수가 행 수보다 많으면 모든 열을 직교정규화할 수 없습니다")
    Q = np.zeros_like(A, dtype=float)
    scale = float(np.max(np.abs(A))) if A.size else 0.0
    tol = max(m, n) * np.finfo(float).eps * max(1.0, scale)
    for j in range(n):
        v = A[:, j].copy()
        for i in range(j):
            v -= float(Q[:, i] @ v) * Q[:, i]
        length = float(np.sqrt(np.sum(v * v)))
        if length <= tol:
            raise ValueError("앞선 열들에 종속인 열은 직교정규화할 수 없습니다")
        Q[:, j] = v / length
    return Q


def orthogonality_error(R) -> float:
    """직교성 이탈 지표: || R^T R - I ||_F  (프로베니우스 노름).

    완전한 직교행렬이면 0 이고, 클수록 직교성이 무너진 것이다.
    """
    R = np.asarray(R, dtype=float)
    if R.ndim != 2 or R.shape[0] != R.shape[1]:
        raise ValueError(f"정사각 행렬이 필요합니다. 받은 shape={R.shape}")
    error = R.T @ R - np.eye(R.shape[0])
    return float(np.sqrt(np.sum(error * error)))


def is_rotation(R, atol: float = 1e-8) -> bool:
    """회전행렬 판정: 직교(R^T R = I) **그리고** det(R) = +1 이면 True.

    det = -1 이면 직교이긴 하지만 반사가 섞여 있어 회전이 아니다.
    3x3 이 아니면 False.
    """
    R = np.asarray(R, dtype=float)
    if R.shape != (3, 3):
        return False
    return orthogonality_error(R) <= atol and abs(det(R) - 1.0) <= atol


# --------------------------------------------------- 회전축·회전각·쿼터니언

def axis_angle_from_matrix(R, atol: float = 1e-8):
    """고유값 분해로 회전축을, 대각합으로 회전각을 복원한다.

    - 회전축은 고유값 1 에 대응하는 실수 고유벡터다 (R k = k).
      -> 여기서는 `np.linalg.eig` 를 써도 된다 (검산이 아니라 축 복원이 목적).
    - 회전각은 trace(R) = 1 + 2 cos(theta) 에서 구한다.
    - arccos 의 치역이 [0, pi] 라 '어느 쪽으로 도는지'는 알 수 없고,
      고유벡터도 부호가 정해지지 않는다. 반대칭 성분
      R - R^T = 2 sin(theta) [k]_x 를 이용해 부호를 맞춘다.
    - theta = 0 (회전 없음) 과 theta = pi (sin = 0) 는 따로 처리해야 한다.
      두 경우에 어떤 규약을 쓸지 정하고 주석으로 남긴다.

    Returns
    -------
    axis : 단위 회전축 (3,)
    angle : 회전각 [rad], 0 <= angle <= pi
    """
    R = np.asarray(R, dtype=float)
    if not is_rotation(R, atol=max(atol, 1e-7)):
        raise ValueError("3x3 회전행렬이 필요합니다")

    cosine = float(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0))
    angle = float(np.arccos(cosine))

    # 무회전에서는 축이 정해지지 않으므로 관례적으로 +x축을 반환한다.
    if angle <= atol:
        return np.array([1.0, 0.0, 0.0]), 0.0

    values, vectors = np.linalg.eig(R)
    index = int(np.argmin(np.abs(values - 1.0)))
    axis = normalize(np.real(vectors[:, index]))

    signed_axis = np.array(
        [R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]
    )
    # pi 근처라도 반대칭 성분에 회전 방향이 남아 있으면 그 부호를 보존한다.
    # 정확한 pi에서는 이 성분이 반올림 수준이므로 축 부호를 고정해도 동치다.
    sign_tol = 16.0 * np.finfo(float).eps
    if np.max(np.abs(signed_axis)) > sign_tol:
        if float(axis @ signed_axis) < 0.0:
            axis = -axis
    else:
        # 반대칭 성분이 소실된 pi 회전은 가장 큰 축 성분을 양수로 둔다.
        dominant = int(np.argmax(np.abs(axis)))
        if axis[dominant] < 0.0:
            axis = -axis
    return axis, angle


def quaternion_from_axis_angle(axis, angle: float) -> np.ndarray:
    """축-각에서 단위 쿼터니언을 만든다.

        q = (k * sin(theta/2), cos(theta/2))

    반환 순서는 SciPy `Rotation.as_quat()` 와 같은 **(x, y, z, w)** 로 맞춘다
    (그래야 문제 6-5 에서 바로 비교할 수 있다).
    """
    axis = normalize(axis)
    if axis.shape != (3,):
        raise ValueError(f"회전축은 3차원이어야 합니다. 받은 shape={axis.shape}")
    half = angle / 2.0
    return np.concatenate((axis * np.sin(half), [np.cos(half)]))
