# Edge RTOS AI Project

## 1. Project Summary

STM32N657 계열 MCU를 대상으로 FreeRTOS 기반 실시간 AI 파이프라인을 구현한다.
PC에서 학습한 경량 CNN을 Knowledge Distillation과 INT8 Quantization으로 최적화한 뒤 MCU에 배포하고, RTOS 환경에서 inference latency, memory usage, deadline miss, CPU/NPU utilization을 측정한다.

최종적으로 시스템 부하에 따라 AI 서비스 수준(QoS)을 조절하는 적응형 Edge AI 시스템까지 확장하는 것을 목표로 한다.

### Current Status

Student baseline과 FP32 배포 경로 검증을 완료했다.

| Item | Result |
|---|---:|
| Dataset | CIFAR-10 |
| Student | MobileNetV2, input 96x96 |
| Best validation accuracy | 95.46% |
| Parameters | 2,236,682 |
| FP32 ONNX size | 8.51 MiB |
| ONNX Runtime max absolute error | 0.00000083 |
| STM32N6 FP32 compile | Passed |
| STM32N6 weights / activations | 8.47 MiB / 1.58 MiB |
| STM32N6 epoch mapping | SW 100 / HW(EC) 1 |
| PTQ INT8 QDQ accuracy | 95.32% (-0.13%p) |
| PTQ INT8 QDQ size | 2.54 MiB (-70.14%) |
| STM32N6 INT8 epoch mapping | SW 0 / HW(EC) 55 |
| STM32N6 INT8 weights / activations | 2.26 MiB / 270 KiB |

FP32 모델은 STM32N6에서 변환되지만 대부분 software fallback으로 배치된다. PTQ INT8 모델은 정확도를 거의 유지하면서 모든 epoch이 Neural-ART hardware/EC에 매핑됐다. 현재 작업은 ResNet18 Teacher와 최소 Knowledge Distillation 비교 실험이다. 상세 분석은 [STM32 AI 분석 결과](docs/STM32_AI_ANALYSIS.md), 작업 재개 정보는 [resume.md](resume.md)에 기록한다.

### Core Keywords
- STM32N657 / Cortex-M55
- FreeRTOS
- Edge AI / TinyML
- CNN
- Knowledge Distillation
- INT8 Quantization
- PTQ / QAT
- ONNX
- STM32Cube AI Studio
- Neural-ART NPU
- Real-Time Scheduling
- Deadline / WCET / Utilization
- Adaptive QoS

---

## 2. Main Goal

단순히 "MCU에서 CNN이 동작한다"를 보여주는 것이 아니라 아래 trade-off를 정량적으로 분석한다.

> Accuracy vs Model Size vs Memory vs Inference Latency vs Real-Time Schedulability

최종 결과물은 다음 질문에 답할 수 있어야 한다.

1. Distillation이 작은 모델의 정확도를 얼마나 복구하는가?
2. INT8 Quantization이 모델 크기와 latency를 얼마나 줄이는가?
3. AI inference workload가 다른 RTOS task의 deadline에 어떤 영향을 주는가?
4. CPU/NPU 실행 방식에 따라 interference가 얼마나 달라지는가?
5. 시스템 부하에 따라 AI QoS를 낮추면 deadline miss를 줄일 수 있는가?

---

## 3. Proposed System Architecture

```text
PC Training Environment

Teacher CNN
   |
   | Knowledge Distillation
   v
Student CNN (FP32)
   |
   | PTQ / QAT
   v
Student CNN (INT8)
   |
   | ONNX Export
   v
STM32Cube AI Studio
   |
   v
STM32N657 Firmware

------------------------------------------------
FreeRTOS
------------------------------------------------
Camera / Input
    |
Capture Task
    |
   Queue
    v
Preprocess Task
    |
   Queue
    v
Inference Task ----> Neural-ART NPU / CPU
    |
   Queue
    v
Postprocess / Output Task

Resource Monitor Task
    |
    +-- CPU utilization
    +-- NPU utilization
    +-- inference latency
    +-- end-to-end latency
    +-- deadline miss ratio
    +-- queue occupancy

QoS Controller Task
    |
    +-- input resolution
    +-- inference period
    +-- model variant
```

---

## 4. Development Phases

### Phase 0 - Pre-board Preparation

보드 도착 전에 PC에서 완료할 영역.

- Python environment 구성
- Dataset 선정
- Teacher / Student baseline 학습
- Knowledge Distillation 구현
- PTQ / QAT 적용
- ONNX export
- STM32Cube AI Studio compatibility 확인
- Benchmark script 작성
- FreeRTOS architecture 사전 설계

### Phase 1 - Board Bring-up

- STM32CubeIDE project 생성
- Clock / memory / cache 확인
- ST-LINK 연결
- UART logging
- FreeRTOS basic task 동작
- periodic task timing 검증

### Phase 2 - AI Deployment

- ONNX model import
- generated runtime integration
- inference test vector 실행
- output 비교
- latency 측정
- memory footprint 측정

### Phase 3 - RTOS AI Pipeline

- Input/Capture task
- Preprocessing task
- Inference task
- Output task
- Queue / Semaphore
- DMA / Interrupt 필요 시 적용

### Phase 4 - Real-Time Evaluation

- task period 설정
- execution time 측정
- WCET 근사
- CPU load 증가 실험
- deadline miss 측정
- queue backlog 측정

### Phase 5 - Adaptive QoS

초기 버전은 heuristic 기반으로 구현한다.

```text
if deadline_miss_ratio > threshold:
    decrease_ai_qos()

else if utilization < lower_threshold:
    increase_ai_qos()
```

QoS 후보:

- inference period
- input resolution
- student model size
- CPU/NPU execution target

RL 기반 제어는 선택 확장사항이며 MVP 범위에는 포함하지 않는다.

---

## 5. Selected Model Setup

### Teacher
- ResNet18

### Student
- MobileNetV2
- ImageNet V2 pretrained backbone
- CIFAR-10 10-class classifier
- static input `1x3x96x96`

FP32 ONNX의 STM32Cube AI operator compatibility는 확인했다. INT8 변환 후 Neural-ART hardware mapping을 다시 측정한다.

### Compression Pipeline

```text
Teacher FP32
      |
      v
Student FP32 baseline
      |
      +--> Student + Knowledge Distillation
                         |
                         v
                    PTQ / QAT
                         |
                         v
                    INT8 Student
```

---

## 6. Evaluation Metrics

### ML Metrics
- Accuracy
- F1 score (필요 시)
- Model size
- Parameter count

### Embedded Metrics
- Flash usage
- SRAM usage
- Peak RAM usage
- Inference latency
- End-to-end latency
- Throughput

### Real-Time Metrics
- Task execution time
- WCET approximation
- CPU utilization
- NPU utilization
- Deadline miss ratio
- Queue occupancy
- Jitter

---

## 7. Suggested Repository Structure

```text
edge-rtos-ai/
|
+-- README.md
+-- CODEX.md
+-- resume.md
+-- requirements.txt
+-- configs/
|   +-- cifar10_mobilenetv2.yaml
+-- models/
+-- docs/
|   +-- PROJECT_PLAN.md
|   +-- ARCHITECTURE.md
|   +-- EXPERIMENT_PLAN.md
|   +-- STM32_AI_ANALYSIS.md
|   +-- TODO.md
|
+-- training/
|   +-- datasets/
|   +-- data.py
|   +-- engine.py
|   +-- models.py
|   +-- prepare_model.py
|   +-- train_student.py
|   +-- export_onnx.py
|   +-- quantize_ptq.py
|
+-- benchmarks/
|
+-- firmware/
|   +-- Core/
|   +-- App/
|   +-- AI/
|   +-- RTOS/
|   +-- System/
|
+-- results/
    +-- tables/
    +-- reports/
    +-- figures/
    +-- raw_logs/
```

### PC Pipeline Commands

```bash
source .venv/bin/activate
python -m training.prepare_model --config configs/cifar10_mobilenetv2.yaml
python -m training.train_student \
  --config configs/cifar10_mobilenetv2.yaml \
  --download \
  --smoke-test
python -m training.export_onnx --config configs/cifar10_mobilenetv2.yaml
python -m training.quantize_ptq --config configs/cifar10_mobilenetv2.yaml
```

`--smoke-test`를 제거하면 config에 지정된 전체 baseline 학습을 실행한다.

---

## 8. Definition of MVP

MVP 완료 조건:

- [ ] Teacher / Student 학습 완료
- [ ] Distillation 적용 완료
- [ ] INT8 모델 생성 완료
- [x] FP32 ONNX export 성공
- [x] STM32Cube AI Studio FP32 import/analyze 성공
- [ ] FreeRTOS에서 inference task 실행
- [ ] latency 측정
- [ ] RAM / Flash 사용량 측정
- [ ] 최소 1개의 periodic background task와 함께 실행
- [ ] deadline miss 측정
- [ ] FP32/KD/INT8 결과 비교 표 작성

---

## 9. Non-Goals for Initial Version

초기 버전에서 아래 기능은 의도적으로 제외한다.

- Docker 기반 embedded toolchain
- Kubernetes / cloud deployment
- 복잡한 RL controller
- multi-board distributed system
- pruning + distillation + quantization 동시 최적화
- object detection부터 시작

프로젝트 안정화 이후 확장 가능하다.
