"""문제 5 — 점군 자세 추정: PCA · Kabsch · 최소제곱 평면 피팅. (학생 작성용 템플릿)

- `pca_axes`        : 공분산 고유분해로 물체의 주축 3개를 뽑는다
- `kabsch`          : 대응이 알려진 두 점군 사이의 최적 회전·병진을 SVD 로 구한다
- `fit_plane_lstsq` : 최소제곱으로 평면을 피팅하고 점별 잔차를 돌려준다
- `remove_outliers` : 잔차가 큰 점을 걸러낸다

`rotation_angle_deg` 는 제공 코드다 (두 회전행렬 사이 각도).
"""

from __future__ import annotations

import numpy as np

__all__ = ["pca_axes", "kabsch", "fit_plane_lstsq", "remove_outliers", "rotation_angle_deg"]


def rotation_angle_deg(R_a, R_b) -> float:
    """두 회전행렬 사이의 각도 [deg] — R_a^T R_b 의 회전각. (제공 코드)"""
    R_rel = np.asarray(R_a, dtype=float).T @ np.asarray(R_b, dtype=float)
    cos_theta = np.clip((np.trace(R_rel) - 1.0) / 2.0, -1.0, 1.0)
    return float(np.rad2deg(np.arccos(cos_theta)))


def pca_axes(P):
    """점군 (N,3) 의 주축을 고유분해로 뽑는다.

    1. centroid = P 의 평균, X = P - centroid
    2. C = X^T X / (N - 1)   (3x3 공분산)
    3. C 를 고유분해 (`np.linalg.eigh` — 대칭행렬 전용, 실수 고유값)
    4. 고유값 **내림차순**으로 정렬해 axes 의 열 0,1,2 가 각각 긴 축 -> 짧은 축이 되게 한다
    5. det(axes) = +1 이 되도록 (오른손 좌표계) 필요하면 마지막 열의 부호를 뒤집는다

    Returns
    -------
    axes : (3,3) 열이 주축 (단위벡터, 서로 직교, det = +1) — 회전행렬로 그대로 쓸 수 있다
    eigvals : (3,) 내림차순 고유값 (각 축 방향 분산)
    centroid : (3,) 점군 중심
    """
    P = np.asarray(P, dtype=float)
    if P.ndim != 2 or P.shape[1] != 3 or len(P) < 2:
        raise ValueError(f"shape (N,3), N>=2인 점군이 필요합니다. 받은 shape={P.shape}")
    centroid = P.mean(axis=0)
    X = P - centroid
    covariance = X.T @ X / (len(P) - 1)
    eigvals, axes = np.linalg.eigh(covariance)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    axes = axes[:, order]
    if np.linalg.det(axes) < 0.0:
        axes[:, -1] *= -1.0
    return axes, eigvals, centroid


def kabsch(P, Q):
    """대응이 알려진 두 점군 P, Q (N,3) 에 대해 Q ~ P @ R.T + t 를 만족하는 (R, t) 를 구한다.

    1. 두 점군의 중심 cP, cQ 를 빼서 X = P - cP, Y = Q - cQ
    2. H = X^T Y  (3x3 교차 공분산)
    3. U, S, Vt = svd(H)
    4. d = sign(det(V U^T)) — 반사가 나오면 (-1) 보정: D = diag(1, 1, d)
    5. R = V D U^T,  t = cQ - R cP

    Returns
    -------
    R : (3,3) 회전행렬 (det = +1)
    t : (3,) 병진
    """
    P = np.asarray(P, dtype=float)
    Q = np.asarray(Q, dtype=float)
    if P.shape != Q.shape or P.ndim != 2 or P.shape[1] != 3 or len(P) < 3:
        raise ValueError("P와 Q는 같은 shape (N,3), N>=3이어야 합니다")
    cP = P.mean(axis=0)
    cQ = Q.mean(axis=0)
    X = P - cP
    Y = Q - cQ
    U, _, Vt = np.linalg.svd(X.T @ Y)
    V = Vt.T
    D = np.eye(3)
    D[-1, -1] = 1.0 if np.linalg.det(V @ U.T) >= 0.0 else -1.0
    R = V @ D @ U.T
    t = cQ - R @ cP
    return R, t


def fit_plane_lstsq(P):
    """점군 (N,3) 에 평면 n . p + d = 0 을 최소제곱으로 피팅한다.

    권장 방법 (정규방정식): z = a x + b y + c 로 두고
        A = [x, y, 1],  b = z,   (A^T A) [a, b, c]^T = A^T b
    를 풀면 평면 a x + b y - z + c = 0 이므로 법선 n = (a, b, -1) 을 정규화한다.
    평면이 z축과 나란해 설계행렬의 랭크가 부족하면 중심화한 점군의 SVD 로
    최소 분산 방향을 법선으로 쓴다. 한 직선이나 한 점으로는 평면을 정할 수 없다.

    Returns
    -------
    normal : (3,) 단위 법선
    d : float — 평면 상수 (n . p + d = 0)
    residuals : (N,) 각 점의 부호 있는 평면까지의 거리 n . p + d
    """
    P = np.asarray(P, dtype=float)
    if P.ndim != 2 or P.shape[1] != 3 or len(P) < 3:
        raise ValueError("shape (N,3), N>=3인 점군이 필요합니다")
    if not np.all(np.isfinite(P)):
        raise ValueError("평면 피팅에는 유한한 좌표가 필요합니다")
    centroid = P.mean(axis=0)
    centered = P - centroid
    _, singular_values, directions = np.linalg.svd(centered, full_matrices=False)
    rank_tolerance = max(centered.shape) * np.finfo(float).eps * singular_values[0]
    if np.count_nonzero(singular_values > rank_tolerance) < 2:
        raise ValueError("한 직선이나 한 점만으로는 평면을 결정할 수 없습니다")

    design = np.column_stack((P[:, 0], P[:, 1], np.ones(len(P))))
    coefficients = None
    if np.linalg.matrix_rank(design) == 3:
        try:
            coefficients = np.linalg.solve(design.T @ design, design.T @ P[:, 2])
        except np.linalg.LinAlgError:
            # 정규방정식에서 수치적으로 특이해진 경우에도 직교 거리로 피팅한다.
            pass
    if coefficients is None:
        normal = directions[-1].copy()
        if normal[np.argmax(np.abs(normal))] < 0.0:
            normal = -normal
        d = float(-normal @ centroid)
    else:
        normal = np.array([coefficients[0], coefficients[1], -1.0])
        length = float(np.linalg.norm(normal))
        normal /= length
        d = float(coefficients[2] / length)
    residuals = P @ normal + d
    return normal, d, residuals


def remove_outliers(P, residuals, k: float = 3.0):
    """평면 잔차의 MAD 기준으로 이상치를 반복 정제한다.

    최초 mask 는 전달받은 잔차로 구한다. 잔차 중앙값으로 중심을 맞추고
    |residual - median(residual)| < k * sigma 인 점을 남긴다.
        sigma = 1.4826 * median(|residual - median(residual)|)      (MAD)

    한 번의 최소제곱 피팅은 이상치 때문에 평면 자체가 기울어질 수 있다.
    남은 점에 중심화 SVD 를 적용해 직교 거리 최소제곱 평면을 다시 구하고,
    전체 점의 새 잔차에 같은 MAD 기준을 적용한다. mask 가 같아지면 종료하며
    최대 10회 반복한다. 이전에 제외한 점도 새 평면에 맞으면 다시 포함될 수 있다.
    점이 3개 미만이거나 일직선이면 재추정을 중단해 마지막 mask 를 유지한다.
    실제 이상치 여부나 참값 자세는 입력받거나 사용하지 않는다.

    Returns
    -------
    P_clean : (M,3) 남은 점
    mask : (N,) bool — True 가 남긴 점. P 와 대응 점군에 같은 mask 를 적용해야 Kabsch 대응이 유지된다
    """
    P = np.asarray(P, dtype=float)
    residuals = np.asarray(residuals, dtype=float)
    if P.ndim != 2 or P.shape[1] != 3 or residuals.shape != (len(P),):
        raise ValueError("P는 (N,3), residuals는 (N,)이어야 합니다")
    if not np.all(np.isfinite(P)) or not np.all(np.isfinite(residuals)):
        raise ValueError("점군과 잔차에는 유한한 값이 필요합니다")
    if not np.isfinite(k) or k <= 0.0:
        raise ValueError("k는 양수여야 합니다")
    if len(P) == 0:
        return P.copy(), np.zeros(0, dtype=bool)

    def mad_mask(values):
        median = float(np.median(values))
        sigma = float(1.4826 * np.median(np.abs(values - median)))
        if sigma <= np.finfo(float).eps:
            return np.isclose(values, median, atol=np.finfo(float).eps)
        return np.abs(values - median) < k * sigma

    mask = mad_mask(residuals)
    for _ in range(10):
        retained = P[mask]
        if len(retained) < 3:
            break
        center = retained.mean(axis=0)
        centered = retained - center
        if np.linalg.matrix_rank(centered) < 2:
            break
        _, _, directions = np.linalg.svd(centered, full_matrices=False)
        normal = directions[-1]
        new_mask = mad_mask((P - center) @ normal)
        if np.array_equal(new_mask, mask):
            break
        next_points = P[new_mask]
        if len(next_points) < 3 or np.linalg.matrix_rank(
            next_points - next_points.mean(axis=0)
        ) < 2:
            break
        mask = new_mask
    return P[mask], mask
