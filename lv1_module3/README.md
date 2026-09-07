# 모듈 3 — 로봇 좌표 변환 수학 라이브러리

최성진 · Physical AI Lv.1

벡터 연산, 회전행렬, 동차변환과 좌표 체인을 구현함. 문제별 설명·계산 과정·검증 출력·그림은 노트북에 정리했고, 재사용 함수는 `src/`에 분리함.

## 문제별 실행 결과

2026-09-07에 JupyterLab에서 표준 venv 커널을 선택하고, 각 노트북의 Restart Kernel and Run All Cells를 실행한 뒤 출력을 저장함.

| 문제 | 노트북 | PASS 수 | 실행 결과 그림 수 | 실행 기록 |
| --- | --- | ---: | ---: | --- |
| 1. 벡터 연산과 정사영 | [01_vectors.ipynb](notebooks/01_vectors.ipynb) | 41 | 0 | [실행 로그](evidence/20260907/01_vectors.txt) |
| 2. 회전행렬과 합성 순서 | [02_rotation.ipynb](notebooks/02_rotation.ipynb) | 39 | 2 | [실행 로그](evidence/20260907/02_rotation.txt) |
| 3. 재직교화와 오류 검출 | [03_reorthogonalize.ipynb](notebooks/03_reorthogonalize.ipynb) | 23 | 1 | [실행 로그](evidence/20260907/03_reorthogonalize.txt) |
| 4. 가우스 소거와 풀이 방법 비교 | [04_linear_system.ipynb](notebooks/04_linear_system.ipynb) | 34 | 2 | [실행 로그](evidence/20260907/04_linear_system.txt) |
| 5. 동차변환과 최소자승 | [05_transform.ipynb](notebooks/05_transform.ipynb) | 43 | 2 | [실행 로그](evidence/20260907/05_transform.txt) |
| 6. 좌표 체인과 회전축 복원 | [06_chain.ipynb](notebooks/06_chain.ipynb) | 41 | 3 | [실행 로그](evidence/20260907/06_chain.txt) |

- 제공 검증 221개 통과, 전체 pytest 96개 통과함.
- 제공 검증·그림·소스 복구 셀 41개를 배포 템플릿과 비교해 동일함을 확인함.
- 그림 10장은 노트북 출력에 저장되어 있고 [images/20260907](images/20260907/)에도 PNG로 저장함.
- [전체 확인 결과](evidence/20260907/final_check.json), [pytest 출력](evidence/20260907/pytest_final.txt), [환경 기록](evidence/20260907/environment.json)을 함께 남김.

문제 3은 `rot_z`의 부호를 일부러 바꿔 오류를 검출하는 실험임. 고의 오류 상태에서 테스트 22개가 실패하고, 원본 복구 후 전체 96개가 통과함. 이 단계의 실패 출력은 실험 결과임.

문제 4의 속도 비교는 `threadpoolctl`로 두 방법 모두 BLAS 스레드 1개를 사용하도록 설정함. 실제 스레드 설정을 출력하고, 각 방법을 1회 워밍업한 뒤 10회 측정한 최솟값으로 비교함. 실행 시간은 컴퓨터와 실행 당시 부하에 따라 달라질 수 있음.

## 손글씨풍 핵심 계산 풀이

문제별 계산 흐름을 설명한 [그림 6장](images/handwritten_math/README.md)을 각 노트북 앞부분에 첨부함. 문제 3의 작은 벡터 예시는 원리 설명용이며 실제 누적 회전 실험과 구분함.

## 가상환경과 실행 방법

실행 환경은 WSL Ubuntu 22.04, Python 3.10.12임. 패키지는 [requirements.txt](requirements.txt)에 기록함. 그림은 한글과 음수 지수를 지원하는 Noto 글꼴을 사용함. WSL에서는 Windows의 `NotoSansKR-VF.ttf`를 읽고, 일반 Ubuntu에서는 `sudo apt install fonts-noto-cjk`로 설치함.

기존 가상환경을 사용하는 경우:

```bash
cd '/mnt/c/Desktop/coding/physicalai-lv1-최성진/lv1_module3'
source /home/chsjh/.venvs/physicalai-lv1-math/bin/activate
python -c "import sys; print(sys.executable)"
python -m jupyter lab --no-browser
```

실제 Python 경로는 `/home/chsjh/.venvs/physicalai-lv1-math/bin/python`임. 노트북의 환경 확인 셀에서도 이 경로와 `가상환경 사용: True`를 확인함.

새 환경에서는 과제 폴더에서 다음 순서로 설치함.

```bash
python3 -m venv ~/.venvs/physicalai-lv1-math
source ~/.venvs/physicalai-lv1-math/bin/activate
python -m pip install -r requirements.txt
python -m ipykernel install --user --name physicalai-lv1-math --display-name "Python (pose_lab)"
python -m jupyter lab --no-browser
```

브라우저에서 JupyterLab을 열고 `notebooks/`의 01~06을 순서대로 실행함. 커널은 **Python (pose_lab)**을 선택하고 **Kernel → Restart Kernel and Run All Cells**로 실행한 뒤 저장함.

문제 3 실행 중에는 같은 `src/rotation.py`를 사용하는 다른 노트북이나 pytest를 동시에 실행하지 않음. 실험이 잠시 소스를 수정한 다음 `finally`에서 복구하기 때문임.

전체 테스트와 환경 기록 갱신:

```bash
python -m pytest -v
python -m pip freeze > requirements.txt
```

## 구현 구성

| 파일 | 역할 |
| --- | --- |
| [vectors.py](src/vectors.py) | 내적, 정규화, 정사영, skew, 평면 법선, 가우스 소거, rank, 행렬식, 역행렬 |
| [rotation.py](src/rotation.py) | 축별 회전, Rodrigues, Gram-Schmidt, 축·각 복원, 쿼터니언 |
| [transform.py](src/transform.py) | 동차변환, 점·방향·점군 변환, 배치 역변환, 정규방정식 |
| [coordinate_chain.py](src/coordinate_chain.py) | base·link·camera 체인과 좌표 변환 |
| [tests/](tests/) | 회전 성질, 변환 왕복, 최소자승, 회전각 경계값 검사 |

핵심 연산은 직접 구현하고, `np.linalg`는 검산 또는 문제에서 지정한 비교에 사용함. 회전축 복원에 사용하는 `np.linalg.eig`는 배포 함수 계약에서 허용한 연산임. 난수는 `np.random.default_rng(42)`로 고정함.

회전축 복원은 0도, 180도, 180도 근처의 음수 방향 축도 검사함. 점군 변환과 배치 역변환은 반복문 없이 배열 연산으로 처리함.

가상환경, 캐시, 빌드 결과는 제출 파일에서 제외함. 제출 태그 `lv1-module3-submit`과 제출 폼 등록은 별도 제출 절차임.
