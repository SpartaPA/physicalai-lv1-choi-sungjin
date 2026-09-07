"""Recalculate the assignment assumptions, not physical robot measurements."""
from decimal import Decimal as D

frame_bytes = 1280 * 720 * 3
bytes_per_second = frame_bytes * 60
mbps = D(bytes_per_second * 8) / D(1_000_000)
assert frame_bytes == 2_764_800
assert bytes_per_second == 165_888_000
assert mbps == D('1327.104')
print(f'frame_bytes={frame_bytes}')
print(f'camera_MB_per_second={D(bytes_per_second) / D(1_000_000)}')
print(f'camera_Mbps={mbps}')
for capacity in (95, 100):
    print(f'LTE_{capacity}_Mbps: capacity_MB_per_second={D(capacity)/8}, camera_ratio={mbps/capacity:.6f}')
    assert mbps > capacity
for name, hz in [('encoder', 2000), ('IMU', 400), ('lidar', 15), ('camera', 60)]:
    print(f'{name}: {hz} Hz, period_ms={D(1000)/hz:.6f}')
print(f'assumed_encoder_and_IMU_bytes_per_second={2*4*2000 + 32*400}')
print(f'assumed_lidar_bytes_per_second={360*8*15}')
assert 2000 // 400 == 5
print('[PASS] camera bandwidth, sensor periods and explicit payload assumptions')
