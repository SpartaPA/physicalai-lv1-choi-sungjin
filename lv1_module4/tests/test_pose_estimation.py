"""점군 자세 추정 함수의 독립 회귀 테스트."""

import numpy as np
import pytest

from src.pose_estimation import (
    fit_plane_lstsq, kabsch, pca_axes, remove_outliers, rotation_angle_deg,
)
from src.rotation import rodrigues


def test_pca_axes_are_sorted_and_right_handed():
    rng = np.random.default_rng(42)
    points = rng.normal(0.0, [0.4, 0.1, 0.03], size=(500, 3))
    axes, values, center = pca_axes(points)
    assert np.all(np.diff(values) <= 0.0)
    assert np.allclose(axes.T @ axes, np.eye(3))
    assert np.isclose(np.linalg.det(axes), 1.0)
    assert np.allclose(center, points.mean(axis=0))


def test_kabsch_recovers_known_transform():
    rng = np.random.default_rng(42)
    P = rng.normal(size=(100, 3))
    R = rodrigues([1.0, 2.0, -0.5], 0.8)
    t = np.array([0.2, -0.1, 0.4])
    Q = P @ R.T + t
    R_hat, t_hat = kabsch(P, Q)
    assert np.allclose(R_hat, R)
    assert np.allclose(t_hat, t)


def test_plane_fit_and_mad_outlier_removal():
    rng = np.random.default_rng(42)
    xy = rng.uniform(-1.0, 1.0, size=(200, 2))
    z = 0.3 * xy[:, 0] - 0.2 * xy[:, 1] + 0.5 + rng.normal(0.0, 0.002, 200)
    points = np.column_stack((xy, z))
    points[:10, 2] += 0.4
    normal, d, residuals = fit_plane_lstsq(points)
    clean, mask = remove_outliers(points, residuals, k=3.0)
    assert np.isclose(np.linalg.norm(normal), 1.0)
    assert np.allclose(residuals, points @ normal + d)
    assert clean.shape[0] < points.shape[0]
    assert np.mean(~mask[:10]) >= 0.8


def test_plane_fit_accepts_vertical_plane():
    """z=f(x,y)로 표현할 수 없는 x=2 평면도 거리 잔차를 계산한다."""
    yz = np.array([[-2., -1.], [-1., 2.], [0., 0.], [2., -1.], [3., 4.]])
    points = np.column_stack((np.full(len(yz), 2.0), yz))
    normal, d, residuals = fit_plane_lstsq(points)
    assert np.allclose(normal, [1.0, 0.0, 0.0], atol=1e-12)
    assert np.isclose(d, -2.0)
    assert np.allclose(residuals, points @ normal + d)
    assert np.allclose(residuals, 0.0, atol=1e-12)


@pytest.mark.parametrize("points", [
    np.array([[0., 0., 0.], [1., 2., 3.], [2., 4., 6.], [3., 6., 9.]]),
    np.full((5, 3), 2.0),
])
def test_plane_fit_rejects_undetermined_plane(points):
    """한 직선이나 한 점만으로는 평면의 법선이 결정되지 않는다."""
    with pytest.raises(ValueError, match="평면"):
        fit_plane_lstsq(points)


@pytest.mark.parametrize("seed, outlier_count", [
    (42, 12),   # 공식 과제의 시드와 이상치 비율
    (42, 24), (123, 24), (999, 24),  # 기존 추가 회귀 조건
])
def test_iterative_mad_corrects_plane_biased_by_normal_outliers(seed, outlier_count):
    """공식 5% 조건과 추가 10% 조건에서 평면 정제 후 정합 오차를 확인한다."""
    rng = np.random.default_rng(seed)
    reference = rng.normal(0.0, [0.35, 0.10, 0.05], (240, 3))
    rotation = rodrigues([1.0, 2.0, 0.5], np.deg2rad(40.0))
    translation = np.array([0.10, -0.05, 0.02])
    observed = reference @ rotation.T + translation
    observed += rng.normal(0.0, 0.01, observed.shape)
    outlier_indices = rng.choice(len(observed), outlier_count, replace=False)
    offsets = rng.uniform(0.2, 0.5, outlier_count) * rng.choice([-1.0, 1.0], outlier_count)
    normal = rotation @ np.array([0.0, 0.0, 1.0])
    observed[outlier_indices] += (
        offsets[:, None] * normal + rng.normal(0.0, 0.03, (outlier_count, 3))
    )

    _, _, residuals = fit_plane_lstsq(observed)
    clean, mask = remove_outliers(observed, residuals, k=3.0)
    # 참값 라벨은 아래 검증에만 사용하고 정제 함수에는 전달하지 않는다.
    is_outlier = np.zeros(len(observed), dtype=bool)
    is_outlier[outlier_indices] = True
    assert np.mean(~mask[is_outlier]) >= 0.8
    assert np.mean(~mask[~is_outlier]) <= 0.1
    assert np.array_equal(clean, observed[mask])
    before = rotation_angle_deg(kabsch(reference, observed)[0], rotation)
    after = rotation_angle_deg(kabsch(reference[mask], clean)[0], rotation)
    assert after < before
    assert after < 3.0


def test_iterative_mad_keeps_mask_when_retained_points_are_collinear():
    points = np.column_stack((np.arange(5.0), np.zeros((5, 2))))
    clean, mask = remove_outliers(points, np.zeros(len(points)))
    assert np.array_equal(clean, points)
    assert mask.all()
