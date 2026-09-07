# 문제 2·3 실행 화면

| 단계 | 이미지 | 확인 결과 |
|---|---|---|
| Ubuntu와 가상환경 | [환경 확인](problem2_09_venv_user_history.png) | Ubuntu 22.04.5, 작업 경로, 가상환경 활성화와 Python 3.10.12 |
| 환경 조건 검사 | [환경 검사](problem2_01_wsl_venv.png) | 2026-09-07 11:18:33, Python 경로와 `venv_active=True` |
| SSH 서버 준비 | [패키지와 서비스](problem2_10_ssh_service_user_history.png) | openssh-server 설치 상태와 `active (running)` |
| SSH 키 재생성 | [키 생성](problem2_07_key_generation_user_history.png) | `physicalai_lv1_module1_ed25519` 키 파일을 덮어써 재생성함 |
| 공개키 등록 | [키 등록](problem2_08_key_registration_user_history.png) | `Number of key(s) added: 1`, `SHA256:RBU…` 지문 |
| 키 기반 SSH 접속 | [SSH 접속](problem2_02_ssh_proof.png) | 2026-09-07 11:11:45, `physicalai_lv1_module1_completion_ed25519` 키로 인증 후 원격 세션 확인 |
| SSH 재접속 | [재접속 결과](problem2_04_ssh_user_history.png) | 2026-09-07 11:28:18, 같은 키로 접속한 별도 세션 `/dev/pts/5` |
| scp 파일 전송 | [전송과 해시 비교](problem2_11_scp_verified.png) | 2026-09-07 12:13:15, 전송 전후 SHA256 일치 |
| 문자 장치 조사 | [tty 장치](problem2_05_tty_user_history.png) | 문자 장치 표시와 tty/dialout 소유 그룹 |
| loop 장치 속성 조사 | [udev 속성](problem2_06_udev_attributes_user_history.png) | loop 장치 생성과 `KERNEL=="loop0"`, `SUBSYSTEM=="block"` |
| 역순 재연결 | [고정 링크 확인](problem2_03_udev_reverse.png) | 2026-09-07 11:15:23, loop 번호가 바뀌어도 robot_lidar와 robot_imu가 각각 같은 backing file을 가리킴 |
| Git 이력 비교 | [merge와 rebase](problem3_01_git_graph_verified.png) | 2026-09-07 12:17:23, 로컬 비교 브랜치의 그래프와 `git diff` 종료 코드 0 |

키 생성·등록 화면의 `SHA256:RBU…` 키와 접속 화면의 `SHA256:mEp…` 키는 서로 다른 키임. 명령 실행 시각이 표시되지 않은 화면은 시각을 기재하지 않음.
