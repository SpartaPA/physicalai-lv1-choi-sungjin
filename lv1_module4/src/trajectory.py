"""문제 4 — 궤적 보간. (학생 작성용 템플릿)

경유점(waypoint)을 지나는 궤적을 선형 보간 / 큐빅 스플라인으로 만들고,
시작·끝에서 속도와 가속도가 0 이 되는 5차 다항식 프로파일을 구현한다.

입력 규약
--------
- t_wp : (M,) 경유점 시각, 오름차순
- q_wp : (M,) 스칼라 궤적 또는 (M, D) 다차원 궤적 (예: 3차원 위치는 D = 3)
- t    : (N,) 평가할 시각 (t_wp[0] <= t <= t_wp[-1])
- 반환 : q_wp 가 (M,) 이면 (N,), (M, D) 이면 (N, D)

큐빅 스플라인은 `scipy.interpolate.CubicSpline` 을 써도 된다 (axis=0).
"""

from __future__ import annotations

import numpy as np
from scipy.interpolate import CubicSpline

__all__ = ["linear_interp", "cubic_spline_interp", "quintic_profile", "finite_diff"]


def linear_interp(t_wp, q_wp, t) -> np.ndarray:
    """경유점 사이를 직선으로 잇는 보간. 각 차원마다 `np.interp` 를 쓰면 된다.

    위치는 이어지지만 경유점에서 속도가 불연속(꺾임)이다.
    """
    t_wp = np.asarray(t_wp, dtype=float)
    q_wp = np.asarray(q_wp, dtype=float)
    t = np.asarray(t, dtype=float)
    _validate_interpolation_inputs(t_wp, q_wp, t)
    if q_wp.ndim == 1:
        return np.interp(t, t_wp, q_wp)
    return np.column_stack([np.interp(t, t_wp, q_wp[:, column])
                            for column in range(q_wp.shape[1])])


def cubic_spline_interp(t_wp, q_wp, t, bc_type: str = "natural") -> np.ndarray:
    """경유점을 지나는 큐빅 스플라인 보간 (위치·속도·가속도가 모두 연속, C2).

    bc_type : 양끝 경계 조건. "natural" (양끝 가속도 0) 또는 "clamped" (양끝 속도 0).
    """
    t_wp = np.asarray(t_wp, dtype=float)
    q_wp = np.asarray(q_wp, dtype=float)
    t = np.asarray(t, dtype=float)
    _validate_interpolation_inputs(t_wp, q_wp, t)
    if bc_type not in {"natural", "clamped"}:
        raise ValueError("bc_type은 'natural' 또는 'clamped'여야 합니다")
    return np.asarray(CubicSpline(t_wp, q_wp, axis=0, bc_type=bc_type)(t))


def quintic_profile(t, t0: float, tf: float, q0, qf,
                    v0=0.0, vf=0.0, a0=0.0, af=0.0):
    """5차 다항식 궤적 q(t) 와 그 도함수 (q, qd, qdd) 를 돌려준다.

    경계 조건 6개 — q(t0)=q0, q(tf)=qf, qd(t0)=v0, qd(tf)=vf, qdd(t0)=a0, qdd(tf)=af —
    로 계수 6개 (c0 ~ c5) 를 정한다. 경계 속도·가속도가 모두 0 인 기본형은

        tau = (t - t0) / (tf - t0)
        s(tau) = 10 tau^3 - 15 tau^4 + 6 tau^5
        q(t) = q0 + (qf - q0) s(tau)

    로 닫힌 꼴이 있고, 일반형은 6x6 선형계를 풀면 된다. 어느 쪽으로 구현해도 된다.
    q0, qf 가 스칼라이면 (N,), (D,) 이면 (N, D) 를 돌려준다.

    Returns
    -------
    q, qd, qdd : 위치, 속도, 가속도 (해석적 미분. 유한차분이 아니다)
    """
    t = np.asarray(t, dtype=float)
    if t.ndim != 1:
        raise ValueError(f"t는 1차원이어야 합니다. 받은 shape={t.shape}")
    duration = float(tf - t0)
    if duration <= 0.0:
        raise ValueError("tf는 t0보다 커야 합니다")

    q0, qf, v0, vf, a0, af = np.broadcast_arrays(
        np.asarray(q0, dtype=float), np.asarray(qf, dtype=float),
        np.asarray(v0, dtype=float), np.asarray(vf, dtype=float),
        np.asarray(a0, dtype=float), np.asarray(af, dtype=float),
    )
    scalar = q0.ndim == 0
    q0f, qff = q0.reshape(-1), qf.reshape(-1)
    v0f, vff = v0.reshape(-1), vf.reshape(-1)
    a0f, aff = a0.reshape(-1), af.reshape(-1)

    c0 = q0f
    c1 = v0f
    c2 = 0.5 * a0f
    T = duration
    matrix = np.array([
        [T ** 3, T ** 4, T ** 5],
        [3.0 * T ** 2, 4.0 * T ** 3, 5.0 * T ** 4],
        [6.0 * T, 12.0 * T ** 2, 20.0 * T ** 3],
    ])
    rhs = np.vstack([
        qff - (c0 + c1 * T + c2 * T ** 2),
        vff - (c1 + 2.0 * c2 * T),
        aff - 2.0 * c2,
    ])
    c3, c4, c5 = np.linalg.solve(matrix, rhs)

    s = (t - t0)[:, None]
    q = c0 + c1 * s + c2 * s ** 2 + c3 * s ** 3 + c4 * s ** 4 + c5 * s ** 5
    qd = c1 + 2.0 * c2 * s + 3.0 * c3 * s ** 2 + 4.0 * c4 * s ** 3 + 5.0 * c5 * s ** 4
    qdd = 2.0 * c2 + 6.0 * c3 * s + 12.0 * c4 * s ** 2 + 20.0 * c5 * s ** 3
    if scalar:
        return q[:, 0], qd[:, 0], qdd[:, 0]
    shape = (len(t),) + q0.shape
    return q.reshape(shape), qd.reshape(shape), qdd.reshape(shape)


def finite_diff(y, t) -> np.ndarray:
    """시간축(axis 0)에 대한 수치 미분. `np.gradient(y, t, axis=0)` 를 쓰면 된다.

    y : (N,) 또는 (N, D),  t : (N,)
    속도 = finite_diff(q, t),  가속도 = finite_diff(속도, t)
    """
    y = np.asarray(y, dtype=float)
    t = np.asarray(t, dtype=float)
    if t.ndim != 1 or y.ndim not in {1, 2} or y.shape[0] != t.shape[0]:
        raise ValueError("y의 첫 축과 1차원 t의 길이가 같아야 합니다")
    return np.gradient(y, t, axis=0)


def _validate_interpolation_inputs(t_wp, q_wp, t) -> None:
    if t_wp.ndim != 1 or len(t_wp) < 2:
        raise ValueError("t_wp는 길이 2 이상인 1차원 배열이어야 합니다")
    if q_wp.ndim not in {1, 2} or q_wp.shape[0] != len(t_wp):
        raise ValueError("q_wp의 첫 축 길이는 t_wp와 같아야 합니다")
    if t.ndim != 1:
        raise ValueError("t는 1차원 배열이어야 합니다")
    if np.any(np.diff(t_wp) <= 0.0):
        raise ValueError("t_wp는 엄격히 증가해야 합니다")
    if np.any(t < t_wp[0]) or np.any(t > t_wp[-1]):
        raise ValueError("평가 시각 t는 경유점 시간 범위 안에 있어야 합니다")
