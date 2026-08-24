# Project Plan

## 프로젝트명

**Adaptive Real-Time Edge AI on FreeRTOS**

대안:
- Real-Time Aware Edge AI Runtime on STM32
- Resource-Adaptive TinyML System on FreeRTOS
- Real-Time Edge AI with Model Compression and QoS Adaptation

---

## 1. Problem Statement

임베디드 시스템에서 AI inference는 많은 CPU/NPU 연산과 메모리를 요구한다. 동시에 센서 처리, 통신, 제어와 같은 실시간 task 역시 deadline을 만족해야 한다.

따라서 AI 정확도만 최대화하는 방식은 실제 embedded real-time system에서는 적합하지 않을 수 있다.

본 프로젝트는 경량 CNN과 model compression을 이용하여 AI workload를 MCU에 배포하고, FreeRTOS 환경에서 다른 task와 함께 실행했을 때 발생하는 latency, resource contention, deadline miss를 분석한다.

이후 시스템 상태에 따라 AI service quality를 조정하여 real-time 안정성을 높이는 적응형 구조를 구현한다.

---

## 2. Objectives

### Objective A - AI Compression

Teacher 모델의 지식을 작은 Student CNN에 전달하고 INT8 Quantization을 적용한다.

비교 대상:

```text
Student FP32
Student + KD FP32
Student INT8 PTQ
Student + KD INT8 PTQ
```

### Objective B - MCU Deployment

최적화된 모델을 STM32N657 계열 MCU에 배포한다.

### Objective C - RTOS Integration

AI inference를 독립 FreeRTOS task로 구성하고 다른 periodic task와 병행 실행한다.

### Objective D - Real-Time Analysis

AI workload 증가가 시스템 schedulability에 미치는 영향을 분석한다.

### Objective E - Adaptive QoS

deadline miss 또는 높은 utilization이 발생할 경우 AI workload를 낮추는 controller를 구현한다.

---

## 3. Hardware Target

### Primary Target

- NUCLEO-N657X0-Q 또는 STM32N657 기반 board

### Optional Peripherals

- Camera module
- UART adapter (필요 시)
- SD card
- External sensor

초기 단계에서는 camera 없이 static image/test vector를 firmware에 포함하여 inference부터 검증한다.

---

## 4. Software Stack

### PC

- Windows / WSL 선택 가능
- Python 3.11~3.12
- PyTorch
- torchvision
- ONNX
- ONNX Runtime
- NumPy
- pandas
- matplotlib

### Embedded

- STM32CubeIDE
- STM32CubeMX
- STM32Cube AI Studio
- FreeRTOS
- C / C++

### Environment Policy

초기 프로젝트에서는 Docker를 사용하지 않는다.

이유:
- ST-LINK / USB / GUI toolchain 접근 복잡성 감소
- 실제 target toolchain과 개발 환경을 단순하게 유지
- Python 환경은 venv 또는 conda로 재현성 관리

필수 dependency는 requirements.txt로 기록한다.

---

## 5. Milestones

### M0 - Planning
- repository 생성
- 문서 구조 작성
- dataset/model 결정

### M1 - ML Baseline
- teacher 학습
- student 학습
- baseline 결과 저장

### M2 - Compression
- KD
- PTQ
- ONNX export

QAT는 PTQ 정확도 손실이 커질 때만 수행하는 조건부 항목이다.

### M2.5 - Pre-board RTOS Preparation
- task/priority/period/deadline contract
- profiler and metrics interface
- UART CSV schema
- synthetic workload definition
- inference-period QoS policy
- portable firmware skeleton

### M3 - Board Bring-up
- UART
- FreeRTOS
- periodic task

### M4 - AI Runtime
- model integration
- inference validation
- latency 측정

### M5 - Real-Time Experiment
- background workload
- deadline 측정
- utilization logging

### M6 - Adaptive QoS
- heuristic controller
- QoS switching

### M7 - Portfolio
- README
- architecture diagram
- result plots
- demo video

### Current Milestone Status

| Milestone | Status | Evidence |
|---|---|---|
| M0 - Planning | Complete | repository/config/dataset/model 확정 |
| M1 - ML Baseline | Complete | Student 95.46%, Teacher 95.03% |
| M2 - Compression | Complete | baseline/KD FP32·PTQ 비교 및 NPU mapping 완료 |
| M2.5 - Pre-board RTOS | Next | architecture, profiler, metrics, workload, portable skeleton |
| M3 - Board Bring-up | Pending | UART, FreeRTOS periodic task, test-vector inference |
| M4 이후 | Pending | on-target inference 전 단계 |

현재 확정 구성은 CIFAR-10, ResNet18 Teacher, MobileNetV2 Student, static input
`1x3x96x96`이다. Teacher와 최소 KD는 baseline을 개선하지 못했으므로 baseline
PTQ INT8 모델을 배포 후보로 확정했다.

---

## 6. Success Criteria

최소 아래 결과를 수치로 제시할 수 있어야 한다.

1. KD 적용 전후 accuracy
2. FP32 → INT8 model size 감소율
3. FP32 → INT8 inference latency 변화
4. AI task 포함 전후 RTOS deadline miss 변화
5. QoS controller 적용 전후 deadline miss 변화

---

## 7. Risk Management

### Risk 1 - Unsupported ONNX Operator

대응:
- 초기에 STM32Cube AI Studio compatibility test 수행
- MobileNet 계열의 표준 연산 우선 사용
- custom operator 최소화

### Risk 2 - Model Too Large

대응:
- input resolution 감소
- width multiplier 감소
- custom student CNN 사용
- INT8 quantization 적용

### Risk 3 - Camera Bring-up Delay

대응:
- static image/test vector로 AI runtime부터 구현
- camera는 후순위 통합

### Risk 4 - RTOS Debugging Complexity

대응:
- UART + GPIO timing measurement부터 구현
- task를 한 개씩 추가

### Risk 5 - Scope Explosion

대응:
초기 MVP에는 아래만 포함:

```text
KD + INT8 + FreeRTOS + inference + deadline analysis
```

Camera / adaptive QoS / RL은 단계적으로 추가한다.
