"""Helpers for selecting ROS 2 QoS policies from string parameters."""

from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
    qos_profile_sensor_data,
)


def make_qos_profile(
    reliability: str = 'reliable',
    durability: str = 'volatile',
    depth: int = 10,
) -> QoSProfile:
    """Build a QoS profile and reject misspelled or invalid settings."""
    if depth < 1:
        raise ValueError('QoS depth must be at least 1')

    reliability_key = reliability.strip().lower()
    durability_key = durability.strip().lower()

    reliability_map = {
        'reliable': QoSReliabilityPolicy.RELIABLE,
        'best_effort': QoSReliabilityPolicy.BEST_EFFORT,
    }
    durability_map = {
        'volatile': QoSDurabilityPolicy.VOLATILE,
        'transient_local': QoSDurabilityPolicy.TRANSIENT_LOCAL,
    }

    if reliability_key not in reliability_map:
        raise ValueError('reliability must be reliable or best_effort')
    if durability_key not in durability_map:
        raise ValueError('durability must be volatile or transient_local')

    # 과제 7에서 요구한 센서 데이터 프로파일을 명시적으로 사용한다.
    if (
        reliability_key == 'best_effort'
        and durability_key == 'volatile'
        and depth == qos_profile_sensor_data.depth
    ):
        return qos_profile_sensor_data

    return QoSProfile(
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=depth,
        reliability=reliability_map[reliability_key],
        durability=durability_map[durability_key],
    )
