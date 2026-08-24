# Adaptive Real-Time Edge AI on FreeRTOS

STM32N657의 Neural-ART NPU에서 INT8 CNN을 실행하고, FreeRTOS task interference가
AI latency와 deadline에 미치는 영향을 측정한 뒤 adaptive QoS로 확장하는 프로젝트다.

현재 **PC-side compression과 ST Edge AI compiler 검증을 완료**했다. 다음 단계는
STM32N657 firmware bring-up과 on-target inference 측정이다.

## Current Results

```text
Dataset: CIFAR-10
Teacher: ResNet18, ImageNet pretrained
Student: MobileNetV2, ImageNet V2 pretrained
Input: static 1x3x96x96
Classes: 10
Seed: 42
ONNX opset: 17
Target: STM32N6 Neural-ART NPU
ST Edge AI Core: 4.0.1-20581
```

### PC accuracy and model size

| Model | Accuracy | ONNX size | Decision |
|---|---:|---:|---|
| Student baseline FP32 | 95.45% | 8.51 MiB | Compatibility baseline |
| Student baseline PTQ INT8 | **95.32%** | **2.54 MiB** | **Deployment candidate** |
| Teacher ResNet18 | 95.03% | - | Weaker than Student |
| Student KD FP32 | 95.25% | 8.51 MiB | No KD improvement |
| Student KD PTQ INT8 | 95.21% | 2.54 MiB | Deployable, not selected |

Student training best accuracy was 95.46%. Baseline FP32 ONNX accuracy was 95.45%,
and PTQ lost only 0.13%p while reducing ONNX size by 70.14%. KD used
`temperature=4`, `alpha=0.5` for 30 epochs, but did not improve the baseline.

### STM32N6 compiler analysis

| Model | Weights | Activations | MACC | Epoch mapping |
|---|---:|---:|---:|---|
| Baseline FP32 | 8.47 MiB | 1.58 MiB | 55,041,829 | SW 100 / HW(EC) 1 |
| Baseline PTQ INT8 | 2.26 MiB | 270 KiB | 56,534,389 | **SW 0 / HW(EC) 55** |
| KD PTQ INT8 | 2.26 MiB | 270 KiB | 56,534,389 | **SW 0 / HW(EC) 55** |

두 INT8 QDQ 모델 모두 software fallback 없이 Neural-ART hardware/epoch controller에
전체 매핑됐다. FP32는 operator compatibility 확인용이며 배포 후보가 아니다.
위 수치는 compiler estimate이고 실제 latency·throughput·전력은 보드에서 측정해야 한다.

## Why Baseline PTQ Is Selected

- baseline PTQ 정확도 95.32%로 네 후보 중 배포형 모델의 정확도가 가장 높다.
- FP32 대비 정확도 손실은 0.13%p에 불과하다.
- weights 2.26 MiB, activations 270 KiB로 STM32N6 memory pool에 매핑된다.
- 모든 55 epoch이 hardware/EC에 매핑된다.
- KD는 graph와 배포 비용을 바꾸지 않으면서 정확도만 0.11%p 낮췄다.
- QAT는 현재 PTQ 손실이 작아 수행하지 않는다.

## Pipeline

```text
CIFAR-10
  ├─ MobileNetV2 Student baseline
  │    ├─ FP32 ONNX validation
  │    └─ Static PTQ QDQ ──> baseline INT8 deployment candidate
  └─ ResNet18 Teacher
       └─ KD MobileNetV2
            ├─ FP32 ONNX validation
            └─ Static PTQ QDQ ──> KD INT8 comparison model

ONNX ──> ST Edge AI Core ──> STM32N6 Neural-ART analysis
```

## Reproduce PC Experiments

```bash
source .venv/bin/activate

python -m training.prepare_model --config configs/cifar10_mobilenetv2.yaml
python -m training.train_student --config configs/cifar10_mobilenetv2.yaml --download
python -m training.export_onnx --config configs/cifar10_mobilenetv2.yaml
python -m training.quantize_ptq --config configs/cifar10_mobilenetv2.yaml

python -m training.train_teacher --config configs/cifar10_mobilenetv2.yaml
python -m training.train_kd --config configs/cifar10_mobilenetv2.yaml

python -m training.export_onnx \
  --config configs/cifar10_mobilenetv2.yaml \
  --checkpoint models/student_kd_best.pth \
  --output models/student_kd_fp32.onnx

python -m training.quantize_ptq \
  --config configs/cifar10_mobilenetv2.yaml \
  --input models/student_kd_fp32.onnx \
  --output models/student_kd_int8_qdq.onnx \
  --comparison-output results/tables/kd_quantization_comparison.csv \
  --model-name student_kd

python -m benchmarks.benchmark_models --config configs/cifar10_mobilenetv2.yaml
```

세 학습 명령은 `--smoke-test`로 각각 두 batch의 파이프라인 검증을 지원한다.

## Repository Layout

```text
configs/       experiment configuration
training/      data, models, training, KD, ONNX export, PTQ
benchmarks/    accuracy, size, ONNX Runtime latency comparison
models/        local checkpoints and ONNX artifacts (Git ignored)
results/
  tables/      tracked comparison CSV files
  reports/     tracked ST Edge AI raw analyze reports
  raw_logs/    local epoch histories (Git ignored)
docs/          architecture, plans, TODO, detailed analyses
firmware/      future STM32N657/FreeRTOS implementation
```

## Next Phase

1. STM32CubeIDE project와 generated Neural-ART runtime을 통합한다.
2. preloaded test vector로 baseline PTQ 단일 inference를 검증한다.
3. DWT cycle counter로 latency를 측정하고 UART CSV 로그를 만든다.
4. inference를 FreeRTOS periodic task로 전환한다.
5. background workload 0/20/40/60/80%에서 latency, jitter, deadline miss를 측정한다.
6. 고정 QoS baseline 이후 inference period 기반 adaptive QoS를 구현한다.

초기 bring-up에는 camera를 사용하지 않는다. RL, pruning, object detection,
dashboard는 MVP 범위에 포함하지 않는다.

## Documentation

- [작업 재개 요약](resume.md)
- [전체 프로젝트 계획](docs/PROJECT_PLAN.md)
- [실험 계획과 결과](docs/EXPERIMENT_PLAN.md)
- [FP32 및 baseline INT8 STM32 분석](docs/STM32_AI_ANALYSIS.md)
- [KD INT8 STM32 분석](docs/KD_STM32_AI_ANALYSIS.md)
- [FreeRTOS/firmware architecture](docs/ARCHITECTURE.md)
- [현재 TODO](docs/TODO.md)
