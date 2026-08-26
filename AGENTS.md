# Repository Agent Instructions

이 repository는 STM32N657 + FreeRTOS 기반 adaptive real-time Edge AI 프로젝트다.
작업 시작 전 `git status --short`를 확인하고 사용자의 기존 변경을 보존한다.

## Read First

작업 재개 시 다음 순서로 현재 상태와 설계를 확인한다.

1. `resume.md`
2. `AGENTS.md`
3. `docs/TODO.md`
4. `docs/ARCHITECTURE.md`
5. `docs/EXPERIMENT_PLAN.md`

ML 결과의 세부 근거가 필요할 때만 `docs/STM32_AI_ANALYSIS.md`,
`docs/KD_STM32_AI_ANALYSIS.md`, config와 training source를 추가로 읽는다.

## Project Objective

MobileNetV2 CIFAR-10 모델을 INT8 QDQ로 압축하여 STM32N657 Neural-ART NPU에
배포한다. 동일한 모델을 실행하는 여러 periodic FreeRTOS inference task가 단일 NPU를
공유할 때의 blocking, logical NPU utilization, deadline-miss ratio를 측정하고 global
period QoS heuristic을 구현한다. 이후 동일한 state/action contract를 PC RL controller로
확장한다.

## Current Phase

현재는 **PC compression/compiler validation 완료 후 pre-board RTOS preparation** 단계다.

완료:

- Student baseline, Teacher/KD training과 비교
- FP32/INT8 QDQ ONNX export 및 ONNX Runtime validation
- baseline/KD INT8의 STM32N6 mapping: `SW 0 / HW(EC) 55`
- baseline PTQ INT8 deployment candidate 확정
- portable `system_metrics`와 host test
- injected cycle reader 기반 `profiler`와 host test
- multi-inference fixed-priority RM/NPU mutex architecture 확정

현재 다음 작업:

1. windowed logical NPU utilization과 DMR aggregation contract/implementation
2. `qos_window_state_t`와 `qos_action_t` portable interface
3. global QoS scale, lower band, hysteresis, cooldown
4. stream/mutex/window metrics와 UART schema
5. non-preemptive fixed-priority response-time analysis
6. hardware dependency를 분리한 portable C skeleton

## Fixed ML and Deployment Decision

```text
Dataset: CIFAR-10
Input: static 1x3x96x96
Classes: 10
Student: MobileNetV2, ImageNet V2 pretrained
Teacher: ResNet18, ImageNet pretrained
Deployment model: models/student_baseline_int8_qdq.onnx
Baseline PTQ accuracy: 95.32%
Weights: 2.26 MiB
Activations: 270 KiB
Neural-ART mapping: SW 0 / HW(EC) 55
```

KD는 baseline을 개선하지 못했다. PTQ accuracy loss가 0.13%p에 불과하므로 QAT는
의도적으로 생략했다. 명시적으로 accuracy 연구를 재개하지 않는 한 training,
KD tuning, QAT, compression 실험을 반복하지 않는다.

Authoritative experiment config:

```text
configs/cifar10_mobilenetv2.yaml
```

## Fixed RTOS Architecture

상세 근거와 contract는 `docs/ARCHITECTURE.md`가 authoritative source다.

- synthetic CPU `BackgroundTask`는 초기 핵심 실험에 사용하지 않는다.
- 동일 model을 실행하는 periodic `InferenceTask_A/B/C`를 둔다.
- 별도의 RM/EDF dispatcher를 직접 만들지 않는다.
- FreeRTOS fixed-priority scheduler를 사용한다.
- base period는 `T_A < T_B < T_C`, priority는 `A > B > C`로 RM 할당한다.
- application-level FreeRTOS mutex가 input binding부터 output copy까지 full inference를
  보호한다.
- 초기에는 runtime epoch-level parallel inference/interleaving을 사용하지 않는다.
- FreeRTOS mutex priority inheritance를 사용하고 binary semaphore로 대체하지 않는다.
- `MonitorTask`는 window state만 생성한다.
- `QoSControllerTask`는 action 선택, 검증, fallback을 담당한다.
- `LoggerTask`만 UART TX를 소유한다.
- 초기 global QoS scale은 모든 inference period를 함께 변경하여 RM 순서를 유지한다.
- 초기 reference는 logical NPU utilization `U*=0.67`, DMR `M*=0.05`다.
- `0.67`은 non-preemptive RM schedulability 보장값이 아니다.
- warm inference `C_i` 측정 전에는 base period와 QoS scale 수치를 확정하지 않는다.

Metrics 의미:

```text
execution time: NPU mutex 획득 후 full service 완료까지
response time: periodic release부터 full service 완료까지
mutex wait: mutex 요청부터 획득까지
logical NPU utilization: window와 겹치는 mutex 보유시간 합 / window duration
DMR: deadline을 놓친 판정 job 수 / window의 판정 job 수
```

## Windows and WSL Roles

ST GUI/toolchain은 Windows에 설치하고 WSL에 중복 설치하지 않는다.

```text
Windows:
- STM32CubeIDE
- STM32CubeMX
- STM32CubeProgrammer
- STM32CubeN6 package
- X-CUBE-FREERTOS
- ST-LINK flash/debug

WSL:
- Git and documentation
- Python/ONNX pipeline
- portable C host tests
```

Windows CubeIDE는 Windows clone을 사용하는 것을 우선한다. WSL clone과 Windows
clone은 Git push/pull로 동기화하고 같은 파일을 양쪽에서 동시에 수정하지 않는다.
`\\wsl.localhost\...` 경로를 CubeIDE workspace로 직접 사용하는 방식은 indexing,
build performance와 permission 문제 때문에 기본안으로 사용하지 않는다.

## STM32/FreeRTOS Bring-up Order

1. Windows tool versions, STM32CubeN6, X-CUBE-FREERTOS 확인
2. `STM32N657X0H3Q`, Secure domain only, FSBL+Appli 프로젝트 생성
3. Application context에서 X-CUBE-FREERTOS/CMSIS-RTOS2 활성화
4. HAL timebase TIM16, SysTick FreeRTOS tick 설정
5. LED default task build/flash
6. UART LoggerTask
7. 단일 InferenceTask와 warm inference timing
8. application NPU mutex
9. InferenceTask B/C와 RM priorities
10. metrics queue와 MonitorTask
11. QoSControllerTask와 local heuristic
12. UART state/action protocol과 PC RL selector

Neural-ART FreeRTOS integration에서 확인할 기본 설정:

```text
LL_ATON_PLATFORM=LL_ATON_PLAT_STM32N6
LL_ATON_OSAL=LL_ATON_OSAL_FREERTOS
LL_ATON_RT_MODE=LL_ATON_RT_ASYNC
ll_aton_osal_freertos.c
```

`FREERTOS_HAS_PARALLEL_NETWORKS`는 generated runtime과 실제 application mutex 범위를
확인한 뒤 확정한다. 추측으로 hardcode하지 않는다.

## Coding and Testing Rules

- portable System/QoS modules은 HAL, FreeRTOS, CMSIS device header를 직접 include하지
  않는다.
- hardware와 RTOS 호출은 adapter/wrapper 경계 뒤에 둔다.
- magic number는 config 또는 명명된 constant로 분리한다.
- shared mutable object에는 writer를 하나만 둔다.
- inference task는 미완성 metrics record를 공유하지 않는다.
- UART 출력은 inference task에서 직접 수행하지 않는다.
- interrupt/scheduler를 끈 채 NPU inference를 기다리지 않는다.
- model/activation/input/output 공유 접근은 full-inference mutex 범위 안에 둔다.
- 실제 board clock, peripheral handle, memory address, generated AI symbol은 CubeMX와
  generated runtime 확인 전까지 hardcode하지 않는다.
- C host tests는 strict C11 warning-free build를 유지한다.

현재 host test 명령:

```bash
cc -std=c11 \
  -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror \
  -Ifirmware/System \
  firmware/System/system_metrics.c \
  tests/firmware/test_system_metrics.c \
  -o /tmp/test_system_metrics \
  && /tmp/test_system_metrics

cc -std=c11 \
  -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror \
  -Ifirmware/System \
  firmware/System/profiler.c \
  tests/firmware/test_profiler.c \
  -o /tmp/test_profiler \
  && /tmp/test_profiler
```

## Artifact and Git Policy

다음은 local artifact이며 기본적으로 commit하지 않는다.

```text
.venv/
training/datasets/
models/*.pth
models/*.onnx
results/raw_logs/
200000943048_20260826140819.pdf
```

tracked result table/report와 문서만 저장한다. destructive Git command를 사용하지 않고,
commit 전 `git diff --check`와 관련 test를 실행한다.

## Deferred Scope

다음은 초기 board-local global QoS heuristic과 multi-inference baseline 완료 후에만 한다.

- task별 QoS vector와 dynamic priority reassignment
- PC RL/DQN, utilization predictor, safety shield
- epoch-level parallel network execution
- camera pipeline
- model/input-resolution switching
- pruning, object detection, dashboard

새 기능을 추가하기 전 다음을 확인한다.

> 이 작업이 STM32N657에서 multi-inference FreeRTOS scheduling, NPU mutex blocking,
> windowed utilization/DMR, global QoS MVP에 필요한가?

아니라면 후순위로 둔다.
