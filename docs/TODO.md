# TODO

## Current Phase

PC-side compression과 ST Edge AI compiler 검증은 완료했다. 현재 배포 후보는
`student_baseline_int8_qdq.onnx`이다. 다음 단계는 보드 도착을 기다리지 않고
진행할 수 있는 RTOS architecture, measurement contract, portable firmware skeleton
준비다. 그 다음에 STM32N657 board bring-up과 실제 inference를 수행한다.

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

- [ ] `InferenceTask`, `BackgroundTask`, `MonitorTask`, `LoggerTask` 역할 확정
- [ ] task period, relative deadline, priority 초깃값 확정
- [ ] task 간 공유 metrics 구조와 ownership 정의
- [ ] DWT CYCCNT 기반 profiler interface 설계
- [ ] cycle counter wrap-around와 cycle-to-time 변환 정책 정의
- [ ] mean/min/max와 p95 집계 방식 결정
- [ ] UART CSV log schema 정의
- [ ] synthetic workload의 0/20/40/60/80% 부하 생성 방식 정의
- [ ] QoS 33/66/100 ms와 hysteresis/cooldown 규칙 정의
- [ ] hardware dependency를 분리한 portable C skeleton 작성

### P1 — 보드 연동용 산출물 준비

- [ ] baseline PTQ input/output tensor interface 정의
- [ ] preloaded CIFAR-10 test vector와 expected output 생성
- [ ] ST Edge AI generated runtime adapter interface 정의
- [ ] CubeMX 생성 프로젝트에 연결할 integration checklist 작성

### Proposed initial tasks

| Task | Initial period | Relative deadline | Initial priority |
|---|---:|---:|---|
| Inference | 33 ms | 33 ms | High |
| Background workload | configurable | configurable | Medium |
| Monitor | 100 ms | 100 ms | Medium |
| Logger | 1000 ms | 1000 ms | Low |

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
background_load
queue_backlog
qos_level
```

### Initial UART CSV schema

```csv
timestamp_ms,task_name,iteration,period_ms,execution_us,response_us,deadline_miss,background_load,qos_level
```

### Portable firmware skeleton

```text
firmware/RTOS/task_inference.c/.h
firmware/RTOS/task_background.c/.h
firmware/RTOS/task_monitor.c/.h
firmware/RTOS/task_logger.c/.h
firmware/System/profiler.c/.h
firmware/System/system_metrics.c/.h
firmware/System/qos_controller.c/.h
firmware/AI/ai_model_adapter.c/.h
```

보드와 CubeMX 생성 파일이 없으므로 이 단계에서는 HAL·FreeRTOS 연결부를 adapter로
분리한다. 실제 board clock, memory address, peripheral handle은 임의로 확정하지 않는다.

## Board Arrival: First-Day Checklist

- [ ] ST-LINK firmware와 board connection 확인
- [ ] STM32CubeIDE sample build/flash
- [ ] LED blink
- [ ] UART output
- [ ] FreeRTOS single periodic task
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

- [ ] inference를 periodic FreeRTOS task로 구성
- [ ] synthetic background workload 구현
- [ ] load 0/20/40/60/80% 조건 구성
- [ ] task execution time과 jitter 측정
- [ ] deadline miss ratio 측정
- [ ] queue backlog와 CPU utilization 기록
- [ ] 필요하면 NPU/CPU contention 관찰 항목 추가

## Adaptive QoS

- [ ] fixed inference period baseline 측정
- [ ] QoS level을 33/66/100 ms inference period로 정의
- [ ] overload/underload threshold와 hysteresis 정의
- [ ] heuristic controller 구현
- [ ] fixed QoS와 adaptive QoS의 deadline miss/latency 비교

현재 모델은 static `96x96`이므로 초기 QoS는 input resolution이나 model switching이
아니라 inference period만 변경한다.

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
- multi-model/input-resolution QoS: 각 variant의 NPU mapping 검증 이후
- pruning, object detection, RL controller, dashboard: MVP 이후
