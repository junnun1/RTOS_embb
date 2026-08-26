# TODO

## Current Phase

PC-side compression과 ST Edge AI compiler 검증은 완료했다. 현재 배포 후보는
`student_baseline_int8_qdq.onnx`이다. 다음 단계는 보드 도착을 기다리지 않고
진행할 수 있는 RTOS architecture, measurement contract, portable firmware skeleton
준비다. 여러 periodic inference task가 단일 NPU mutex를 경쟁하는 non-preemptive
fixed-priority RM 구조와 metrics ownership을 확정했다. `system_metrics`와 `profiler`
host test도 완료했다. Windows에서는 NUCLEO-N657X0-Q FSBL+Appli FreeRTOS smoke project를
생성·빌드했으며, 다음은 window metrics/QoS portable C 구현과 on-target heartbeat
검증이다.

## Completed: PC Compression and Validation

### Environment and data

- [x] Python 3.12 virtual environment와 dependency 고정
- [x] CIFAR-10 download, preprocessing, deterministic loader 구성
- [x] static input `1x3x96x96`, seed 42 설정
- [x] YAML 기반 experiment configuration

### Student baseline

- [x] MobileNetV2 ImageNet V2 pretrained Student 학습
- [x] best validation accuracy 95.46% 확보
- [x] FP32 ONNX export/checker/ONNX Runtime 비교
- [x] FP32 ONNX full validation accuracy 95.45% 확인

### Teacher and KD

- [x] ResNet18 Teacher 구현 및 60-epoch 학습
- [x] Teacher best validation accuracy 95.03% 확인
- [x] KD loss 구현
- [x] `temperature=4`, `alpha=0.5`, 30-epoch 최소 KD 실험
- [x] KD Student FP32 accuracy 95.25% 확인
- [x] baseline 대비 KD 개선 없음 확인

### Quantization and benchmark

- [x] static PTQ, ONNX QDQ, INT8/INT8 per-channel 구현
- [x] CIFAR-10 train 1,000 sample MinMax calibration
- [x] baseline PTQ accuracy 95.32%, size 2.54 MiB 확인
- [x] KD PTQ accuracy 95.21%, size 2.54 MiB 확인
- [x] 네 모델 accuracy/size/PC latency CSV 자동화
- [x] QAT 불필요 판단
- [ ] 결과 plot 자동화 — 포트폴리오 정리 단계에서 수행

### STM32N6 compiler validation

- [x] baseline FP32 import/analyze
- [x] baseline PTQ INT8 전체 Neural-ART mapping: SW 0 / HW(EC) 55
- [x] KD PTQ INT8 전체 Neural-ART mapping: SW 0 / HW(EC) 55
- [x] weights 2.26 MiB, activations 270 KiB 확인
- [x] 세 raw analyze report 저장
- [x] baseline PTQ INT8를 최종 배포 후보로 선정

QAT는 미완료가 아니라 현재 조건에서 의도적으로 생략했다. baseline PTQ 손실이
0.13%p이고 KD PTQ 손실도 0.04%p이므로 추가 학습 비용의 근거가 없다.

## Next: Pre-board RTOS Preparation

### P0 — 바로 진행

- [x] 세 `InferenceTask`, `MonitorTask`, `QoSControllerTask`, `LoggerTask` 역할 확정
- [x] base-period RM relative priority와 deadline=period 정책 확정
- [ ] 보드 warm inference 측정 후 base period와 QoS scale 수치 확정
- [x] task 간 metrics/NPU/UART ownership 정의
- [x] full-inference application mutex와 priority inheritance 정책 확정
- [x] 상세 RTOS/QoS architecture와 설계 변경 근거 문서화
- [x] 공통 `task_run_record_t`와 execution/response/deadline 계산 구현
- [x] hardware cycle reader를 주입받는 portable profiler interface 구현
- [x] cycle counter wrap-around와 cycle-to-time 변환 정책 구현
- [x] `system_metrics` host test 작성 및 strict C11 build 통과
- [x] profiler host test 작성 및 strict C11 build 통과
- [ ] mean/min/max와 p95 집계 방식 결정
- [ ] UART CSV log schema 정의
- [ ] windowed logical NPU utilization과 DMR aggregation 구현
- [ ] global QoS scale과 hysteresis/cooldown 규칙 정의
- [ ] non-preemptive RM response-time analysis 방식 구현/검증
- [ ] hardware dependency를 분리한 portable C skeleton 작성

### Implemented portable modules

```text
firmware/System/system_metrics.c/.h
firmware/System/profiler.c/.h
tests/firmware/test_system_metrics.c
tests/firmware/test_profiler.c
```

현재 상태:

- `system_metrics`: release/start/end cycle, execution/response cycle·microsecond,
  deadline miss와 task/QoS/background metadata 정의
- cycle 변환: zero clock 방어, 64-bit 중간 연산, `UINT32_MAX` saturation
- wrap-around: 32-bit unsigned subtraction 정책 적용 및 host test 통과
- `profiler`: cycle reader 함수 포인터/context/CPU clock 주입 구조 구현
- hardware boundary: HAL, FreeRTOS, CMSIS/DWT 직접 의존성 없음
- profiler test: fake reader, invalid argument, 일반 cycle 차이, wrap-around, clock getter 검증
- pending: STM32N657 DWT adapter
- architecture: periodic inference task 3개, FreeRTOS fixed priority, shared NPU mutex
- control split: Monitor는 state 생성, QoSController는 action 선택/검증
- resource state: logical NPU busy ratio와 inference DMR, 초기 reference 0.67/0.05

### P1 — 보드 연동용 산출물 준비

- [ ] baseline PTQ input/output tensor interface 정의
- [ ] preloaded CIFAR-10 test vector와 expected output 생성
- [ ] ST Edge AI generated runtime adapter interface 정의
- [ ] CubeMX 생성 프로젝트에 연결할 integration checklist 작성

### Windows toolchain and FreeRTOS setup

ST GUI/toolchain은 Windows에 설치하고 WSL에 중복 설치하지 않는다. WSL은 현재
portable C/Python 개발과 Git 작업에 사용하고, CubeMX/CubeIDE/Programmer는 Windows에서
실행한다.

- [x] STM32CubeIDE 2.2.0, STM32CubeMX 6.18.1, bundled Programmer CLI 2.23.0 확인
- [x] STM32Cube FW_N6 V1.4.1 설치/생성 프로젝트 적용 확인
- [x] X-CUBE-FREERTOS 1.6.0, FreeRTOS kernel 11.2.0 설치
- [x] `NUCLEO-N657X0-Q`/`STM32N657X0H3Q`, Secure domain only, FSBL+Appli 생성
- [x] Application context에서 X-CUBE-FREERTOS/CMSIS-RTOS2 활성화
- [x] HAL timebase TIM16, SysTick FreeRTOS kernel tick 설정
- [x] preemption, time slicing, 1 kHz tick, mutex, stack overflow check 설정
- [x] FSBL/Application build와 500 ms default-task heartbeat build
- [ ] 보드에서 heartbeat 증가와 FreeRTOS Task List 확인
- [ ] board-default free GPIO의 runtime-context warning 정리
- [ ] LED default task build/flash
- [ ] 보드 도착 후 DEV boot, flash/debug, FreeRTOS Task List 확인
- [ ] UART LoggerTask 추가
- [ ] 단일 InferenceTask와 warm inference timing 검증
- [ ] priority inheritance가 설정된 application NPU mutex 추가
- [ ] InferenceTask B/C와 RM fixed priority 추가
- [ ] metrics queue, MonitorTask, QoSControllerTask 순서로 추가
- [ ] Neural-ART runtime에 FreeRTOS OSAL 연동
  - `LL_ATON_PLATFORM=LL_ATON_PLAT_STM32N6`
  - `LL_ATON_OSAL=LL_ATON_OSAL_FREERTOS`
  - `LL_ATON_RT_MODE=LL_ATON_RT_ASYNC`
  - `ll_aton_osal_freertos.c` 포함
- [ ] generated runtime 확인 후 `FREERTOS_HAS_PARALLEL_NETWORKS` 정책 확정
- [ ] application mutex가 input binding부터 output copy까지 full inference를 보호하는지 확인

### Proposed initial tasks

| Task | Initial period | Relative deadline | Relative priority |
|---|---:|---:|---|
| InferenceTask_A | `T_A`, profiling 후 확정 | current period | highest inference priority |
| InferenceTask_B | `T_B`, profiling 후 확정 | current period | middle inference priority |
| InferenceTask_C | `T_C`, profiling 후 확정 | current period | lowest inference priority |
| Monitor | control window `W` | `W` | above inference, short execution |
| QoSController | window notification | before next window | below Monitor, short execution |
| Logger | event-driven 또는 1000 ms | non-critical | Low |

Capture와 camera는 최초 inference 검증 이후 추가한다.

### Required metrics fields

```text
release_timestamp
start_timestamp
end_timestamp
execution_time
response_time
deadline_miss
iteration
stream_id
mutex_wait_time
ready_or_waiting_jobs
qos_level
```

### Initial UART CSV schema

```csv
window_index,npu_util_permille,dmr_permille,qos_level,task_id,job_id,period_ms,execution_us,response_us,deadline_miss,mutex_wait_us
```

### Portable firmware skeleton

```text
firmware/RTOS/task_inference.c/.h
firmware/RTOS/task_monitor.c/.h
firmware/RTOS/task_qos_controller.c/.h
firmware/RTOS/task_logger.c/.h
firmware/System/profiler.c/.h
firmware/System/system_metrics.c/.h
firmware/System/qos_controller.c/.h
firmware/AI/ai_model_adapter.c/.h
```

로컬 CubeMX smoke project는 아래 Windows workspace에 있으며 repository에는 추적하지
않는다.

```text
C:\Users\SSAFY\STM32CubeIDE\workspace_2.2.0\NUCLEO_RTOS_TEST
```

이 project는 target toolchain과 CMSIS-RTOS2 생성/빌드 검증용이다. 최종 target project를
repository에 통합할 때도 HAL·FreeRTOS 연결부를 adapter로 분리하며, 실제 board clock,
memory address와 generated AI symbol은 runtime 확인 전 임의로 확정하지 않는다.

## Board Arrival: First-Day Checklist

- [ ] ST-LINK firmware와 board connection 확인
- [x] STM32CubeIDE FSBL/Application sample build
- [ ] DEV boot flash/debug launch
- [ ] LED blink
- [ ] UART output
- [x] FreeRTOS single heartbeat task compile/link
- [ ] FreeRTOS single heartbeat task on-target 실행
- [ ] DWT cycle counter 동작 확인
- [ ] baseline PTQ generated model 최소 inference
- [ ] test vector의 output을 ONNX Runtime 결과와 비교

## On-Target AI Validation

- [ ] cold/warm inference 분리 측정
- [ ] latency mean, p50, p95, max 측정
- [ ] throughput 측정
- [ ] Flash/RAM 실측값 기록
- [ ] 반복 inference output 안정성 확인
- [ ] compiler estimate와 실제 측정값 비교

## RTOS Interference Experiment

- [ ] 동일 모델을 사용하는 periodic inference task 3개 구성
- [ ] base period 기준 RM fixed priority 적용
- [ ] full-inference 범위 application NPU mutex 적용
- [ ] mutex priority inheritance와 blocking trace 확인
- [ ] fixed QoS별 offered logical NPU utilization 조건 구성
- [ ] task execution time과 jitter 측정
- [ ] deadline miss ratio 측정
- [ ] mutex wait, ready/waiting job 수, logical NPU busy ratio 기록
- [ ] non-preemptive response-time analysis와 실측 결과 비교

## Adaptive QoS

- [ ] fixed global QoS period-scale baseline 측정
- [ ] warm inference time과 `U*=0.67` 기준으로 base period/QoS scale 확정
- [ ] overload/underload threshold와 hysteresis 정의
- [ ] MonitorTask와 QoSControllerTask 분리 구현
- [ ] board-local heuristic controller 구현
- [ ] fixed QoS와 adaptive QoS의 utilization/DMR/QoS 비교
- [ ] UART state/action protocol과 PC action timeout/fallback 정의

현재 모델은 static `96x96`이므로 초기 QoS는 input resolution이나 model switching이
아니라 세 inference stream의 공통 period scale만 변경한다. task별 QoS vector와 PC RL
controller는 global heuristic 안정화 이후 확장한다.

## Required Local Artifacts

Git에서 제외되지만 board 작업 전에 로컬에 있어야 한다.

```text
models/student_baseline_best.pth
models/student_baseline_fp32.onnx
models/student_baseline_int8_qdq.onnx
models/student_kd_fp32.onnx
models/student_kd_int8_qdq.onnx
```

추적되는 결과:

```text
results/tables/quantization_comparison.csv
results/tables/kd_quantization_comparison.csv
results/tables/model_comparison.csv
results/reports/baseline_fp32_network_analyze_report.txt
results/reports/baseline_int8_network_analyze_report.txt
results/reports/kd_int8_network_analyze_report.txt
```

## Deferred Work

- QAT: 현재 PTQ 정확도 손실이 작아 보류
- Teacher/KD 재튜닝: 추가 accuracy 연구가 필요할 때만 수행
- camera driver: static test-vector inference 이후
- synthetic CPU BackgroundTask: 여러 inference stream 기반 NPU 경쟁으로 대체
- task별 QoS vector/priority 재배치: global QoS baseline 이후
- multi-model/input-resolution QoS: 각 variant의 NPU mapping 검증 이후
- pruning, object detection, RL controller, dashboard: MVP 이후
