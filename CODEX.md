# Instructions for Codex

이 repository는 STM32N657 + FreeRTOS 기반 real-time Edge AI 프로젝트이다.

## Project Objective

경량 CNN을 Knowledge Distillation과 INT8 Quantization으로 압축하고 STM32N657 MCU에 배포한다. 이후 FreeRTOS 환경에서 AI inference task와 다른 periodic task를 함께 실행하여 latency, resource utilization, deadline miss를 측정하고 adaptive QoS까지 구현한다.

## Current Phase

현재는 **보드 도착 전 compression 단계**이다.

Student baseline, PTQ INT8 및 STM32N6 Neural-ART mapping 분석까지 완료했다. 다음 작업은 Teacher/KD 최소 비교 실험이다.

우선순위:

1. ResNet18 Teacher baseline
2. 최소 Knowledge Distillation 비교
3. KD Student PTQ INT8
4. KD INT8 ONNX Runtime / STM32N6 Neural-ART validation
5. FP32 / KD / INT8 benchmark automation
6. 필요할 때만 QAT INT8

## Confirmed Baseline

```text
Dataset: CIFAR-10
Student: MobileNetV2 (ImageNet V2 pretrained)
Teacher: ResNet18
Input: static FP32 1x3x96x96
Classes: 10
Seed: 42
```

확보된 Student 결과:

```text
validation accuracy: 95.46%
parameters: 2,236,682
ONNX size: 8.51 MiB
PyTorch/ONNX Runtime max abs error: 0.00000083
```

STM32Cube AI Studio / ST Edge AI Core 4.0.1의 STM32N6 분석 결과:

```text
FP32 ONNX compilation: passed
weights: 8.47 MiB
activations: 1.58 MiB
MACC: 55,041,829
epoch mapping: SW 100 / HW(EC) 1
```

FP32 모델은 operator compatibility 확인용 baseline이다. 대부분 software epoch이므로 NPU 배포 성공으로 간주하지 않는다. INT8 모델에서 Neural-ART HW mapping을 다시 확인한다.

PTQ INT8 QDQ 결과:

```text
calibration: CIFAR-10 train 1,000 samples, MinMax
weights/activations: INT8/INT8, per-channel
validation accuracy: 95.32% (-0.13%p vs FP32 ONNX)
ONNX size: 2.54 MiB (-70.14%)
QDQ nodes: QuantizeLinear 101 / DequantizeLinear 207
model input/output: FP32 boundary, static 1x3x96x96 -> 1x10
```

STM32N6 PTQ INT8 분석 결과:

```text
weights: 2.26 MiB
activations: 270 KiB
epoch mapping: SW 0 / HW(EC) 55
npuRAM5: 270 KiB / 448 KiB (60.27%)
octoFlash: 2.263 MiB / 112 MiB (2.02%)
```

PTQ 손실이 0.13%p에 불과하고 전체 NPU mapping이 성공했으므로 baseline에는 QAT를 적용하지 않는다. KD는 프로젝트 비교 근거를 위한 최소 실험으로 수행하고 개선이 없으면 현재 PTQ 모델을 최종 배포 후보로 유지한다.

작업을 재개할 때는 repository root의 `resume.md`를 먼저 읽고, 그 문서의 reference order를 따른다.

## Coding Rules

- Python 코드는 가능한 모듈화한다.
- magic number를 최소화하고 config로 분리한다.
- 모든 실험은 reproducible seed를 지원한다.
- model checkpoint와 result file path를 hardcoding하지 않는다.
- training code와 evaluation code를 분리한다.
- embedded deployment를 고려하여 exotic operator 사용을 피한다.
- ONNX export 가능성을 항상 고려한다.
- 불필요한 dependency를 추가하지 않는다.
- Docker를 기본 개발환경으로 도입하지 않는다.

## Model Policy

Student는 MobileNetV2, Teacher는 ResNet18로 확정했다.
입력 크기는 96x96, 클래스 수는 10으로 고정한다.

첫 번째 목표는 높은 정확도가 아니라 **배포 가능한 end-to-end pipeline 확보**이다.

## Embedded Constraints

향후 target:
- STM32N657
- FreeRTOS
- STM32Cube AI Studio
- Neural-ART NPU

따라서 모델 변경 시 반드시 다음을 고려한다.

- operator compatibility
- activation memory
- parameter size
- INT8 conversion 가능성
- static tensor shape 선호

## Expected PC Pipeline

```text
Dataset
  -> Student Baseline
  -> FP32 ONNX Compatibility Check
  -> Teacher Training
  -> Knowledge Distillation
  -> PTQ / QAT
  -> INT8 ONNX Export
  -> ONNX Runtime Validation
  -> STM32N6 Neural-ART Validation
```

## Benchmark Output

모델 benchmark 결과는 CSV로 저장한다.

필수 column 예시:

```text
model_name
precision
accuracy
parameter_count
model_size_mb
pc_latency_ms
notes
```

향후 embedded column 추가:

```text
flash_kb
ram_kb
board_latency_ms
wcet_ms
cpu_utilization
npu_utilization
deadline_miss_ratio
```

## Do Not Do Yet

현재 단계에서는 아래 작업을 하지 않는다.

- 복잡한 RL controller 구현
- camera driver 구현
- pruning 추가
- object detection으로 scope 확대
- Docker 환경 구축
- web/backend/dashboard 개발

## When Unsure

새 기능을 추가하기 전에 다음 질문을 우선한다.

> 이 작업이 STM32에서 KD + INT8 CNN을 FreeRTOS task로 안정적으로 실행하는 MVP에 필요한가?

아니라면 후순위로 둔다.
