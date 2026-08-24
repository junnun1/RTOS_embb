# Instructions for Codex

이 repository는 STM32N657 + FreeRTOS 기반 real-time Edge AI 프로젝트이다.

## Project Objective

경량 CNN을 Knowledge Distillation과 INT8 Quantization으로 압축하고 STM32N657 MCU에 배포한다. 이후 FreeRTOS 환경에서 AI inference task와 다른 periodic task를 함께 실행하여 latency, resource utilization, deadline miss를 측정하고 adaptive QoS까지 구현한다.

## Current Phase

현재는 **보드 도착 전 PC-side preparation 단계**이다.

보드 없이 수행 가능한 작업을 먼저 완료해야 한다.

우선순위:

1. PyTorch baseline
2. ONNX export
3. STM32Cube AI compatibility
4. Knowledge Distillation
5. Quantization
6. Benchmark automation

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

초기 Student는 MobileNetV2 또는 MobileNetV3-Small을 우선 고려한다.
Teacher는 ResNet18을 기본으로 한다.

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
  -> Teacher Training
  -> Student Baseline
  -> Knowledge Distillation
  -> PTQ / QAT
  -> ONNX Export
  -> ONNX Runtime Validation
  -> STM32Cube AI Validation
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
