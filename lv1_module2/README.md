# 모듈 2 — turtlesim ROS 2 패키지

Ubuntu 22.04 / ROS 2 Humble에서 가상환경 Python으로 실행하는 과제 폴더임. 구현과 문제별 실험 기록은 [report.md](report.md)에 정리함.

## 1. 가상환경과 빌드

WSL 터미널에서 실행함.

```bash
cd '/mnt/c/Desktop/coding/physicalai-lv1-최성진/lv1_module2'
source scripts/use_env.sh
cd ros2_ws
python /usr/bin/colcon build \
  --build-base "$HOME/physicalai_lv1_build/module2_20260907/build" \
  --symlink-install \
  --cmake-args -DPython3_EXECUTABLE=/home/chsjh/.venvs/ros2-humble/bin/python
cd ..
source scripts/use_env.sh
python -c 'import sys; print(sys.executable)'
```

Python 경로는 `/home/chsjh/.venvs/ros2-humble/bin/python`임. 한글 경로를 처리하는 Humble 인터페이스 생성 단계의 문제를 피하기 위해 빌드 중간 파일만 홈 폴더의 영문 경로에 생성함. 소스와 설치 결과는 이 과제 폴더에 유지함.

`use_env.sh`는 가상환경과 ROS 패키지 경로를 설정한 뒤 로컬 UDP 통신 설정을 적용함. [fastdds_loopback.xml](config/fastdds_loopback.xml)의 전송 인터페이스는 `127.0.0.1`로 제한함.

## 2. 터미널 입력으로 다각형 그리기

첫 번째 터미널에서 시뮬레이터와 액션 서버를 실행함.

```bash
cd '/mnt/c/Desktop/coding/physicalai-lv1-최성진/lv1_module2'
source scripts/use_env.sh
ros2 launch turtle_py turtle_system.launch.py
```

두 번째 터미널에서 입력 프로그램을 실행함.

```bash
cd '/mnt/c/Desktop/coding/physicalai-lv1-최성진/lv1_module2'
source scripts/use_env.sh
ros2 run turtle_py draw_polygon_client --interactive
```

예를 들어 첫 질문에 `3`, 두 번째 질문에 `1.5`를 입력함.

```text
변의 개수를 입력하세요 (3 이상 정수): 3
한 변의 길이를 입력하세요 (m, 0보다 큰 수): 1.5
```

| 변 개수 | 그리는 도형 | 한 변을 그린 후 회전하는 각도 |
| ---: | --- | ---: |
| 3 | 삼각형 | 120° |
| 4 | 사각형 | 90° |
| 5 | 오각형 | 72° |
| 8 | 팔각형 | 45° |

변의 개수는 3 이상의 정수, 길이는 0보다 큰 유한한 수로 입력함. 잘못된 입력은 다시 물어봄. 시뮬레이터 화면 안에서 도형을 보기 위해 처음에는 길이 1~1.5로 실행함.

[draw_polygon_server.py](ros2_ws/src/turtle_py/turtle_py/draw_polygon_server.py)의 `for side_index in range(sides)`가 입력한 변의 개수만큼 반복함. 각 반복에서 한 변을 전진하고 진행률을 보내며, 외각 `360 / sides`만큼 회전함. 전진과 회전 중에는 현재 자세를 계속 읽어 목표에 도달했는지 확인함.

변을 마칠 때 `completed`와 `progress`가 출력되고, 마지막에는 `SUCCEEDED`와 실제 자세 변화로 누적한 `total_distance`가 출력됨. 제어 허용 오차가 있으므로 총 이동 거리는 `변 개수 × 길이`와 약간 다를 수 있음.

다른 도형을 새 화면에 그릴 때는 아래 명령으로 위치와 선을 초기화한 다음 입력 프로그램을 다시 실행함.

```bash
ros2 service call /reset std_srvs/srv/Empty '{}'
ros2 run turtle_py draw_polygon_client --interactive
```

입력 질문 없이 값을 명령에 직접 넣는 방식도 지원함.

```bash
ros2 run turtle_py draw_polygon_client --ros-args -p sides:=5 -p side_length:=1.5
```

## 3. 폴더 구성

- `cpp_basics/`: 문제 1·2 C++ 구현
- `ros2_ws/src/turtle_py/`: Python 노드와 테스트
- `ros2_ws/src/turtle_cpp/`: C++ 거리 발행·구독 노드
- `ros2_ws/src/turtle_interfaces/`: 메시지·서비스·액션 정의
- `evidence/20260907/`: 실행 로그
- `screenshots/20260907/`: 실행 화면
- `bags/`: 기록·재생 실험 데이터
- `config/`, `scripts/`: 실행 환경 설정

`turtle_interfaces`의 필드 규격은 배포 예제와 일치함. `turtle_examples`는 구현을 참고하는 예제 패키지이며, 이 폴더의 실행 패키지는 `turtle_py`와 `turtle_cpp`임.
