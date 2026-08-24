# Experiment Plan

## Experiment 1 - Student Baseline

목적: MCU 배포 후보 모델의 기본 성능 확보.

비교:

```text
Teacher ResNet18
Student MobileNetV2
```

측정:
- validation accuracy
- parameters
- model file size
- PC inference latency

현재 결과:

| Model | Accuracy | Parameters | ONNX Size | Input |
|---|---:|---:|---:|---:|
| MobileNetV2 FP32 baseline | 95.46% | 2,236,682 | 8.51 MiB | 1x3x96x96 |

PC inference latency는 benchmark script 구현 후 추가한다.

---

## Experiment 2 - Knowledge Distillation

목적: Student 모델 정확도 개선 효과 확인.

Loss 예시:

```text
L = alpha * CE(student, label)
  + (1-alpha) * T^2 * KL(student/T, teacher/T)
```

변수:
- temperature T
- alpha

최소 실험:

| Model | Accuracy |
|---|---:|
| Student baseline | 95.46% |
| Student + KD | TBD |

---

## Experiment 3 - Quantization

### 3.1 PTQ

FP32 학습 모델을 calibration dataset을 이용해 INT8로 변환.

### 3.2 QAT

학습 과정에서 quantization error를 반영.

비교:

| Model | Accuracy | Size |
|---|---:|---:|
| KD Student FP32 | TBD | TBD |
| KD Student PTQ INT8 | TBD | TBD |
| KD Student QAT INT8 | TBD | TBD |

---

## Experiment 4 - Embedded Inference

보드 도착 후 수행.

보드 도착 전 ST Edge AI Core `analyze` 결과:

| Model | Format | Compile | Weights | Activations | MACC | Epoch mapping |
|---|---|---|---:|---:|---:|---|
| MobileNetV2 baseline | FP32 ONNX | Passed | 8.47 MiB | 1.58 MiB | 55,041,829 | SW 100 / HW(EC) 1 |

FP32 결과는 operator compatibility baseline이다. NPU 가속 평가는 INT8 모델과 실제 보드 측정으로 수행한다.

측정:

```text
Model
Precision
Execution target(CPU/NPU)
Latency avg
Latency p95
Latency max
Flash
RAM
```

---

## Experiment 5 - RTOS Interference

AI task와 background workload를 동시에 실행한다.

Background workload level:

```text
0%
20%
40%
60%
80%
```

측정:
- AI inference latency
- deadline miss ratio
- jitter
- CPU utilization
- queue backlog

---

## Experiment 6 - QoS Adaptation

### Baseline
고정 AI QoS

### Adaptive
resource monitor 결과를 이용해 QoS 변경

비교:

| Method | Accuracy proxy | Deadline miss | Avg latency | Utilization |
|---|---:|---:|---:|---:|
| Fixed High QoS | TBD | TBD | TBD | TBD |
| Fixed Low QoS | TBD | TBD | TBD | TBD |
| Adaptive QoS | TBD | TBD | TBD | TBD |

---

## Result Storage Convention

```text
results/
  raw_logs/
      YYYYMMDD_testname.csv
  tables/
      model_comparison.csv
      rtos_comparison.csv
  figures/
      accuracy_vs_latency.png
      utilization_vs_miss.png
```

모든 실험은 seed, model config, commit hash를 로그에 남긴다.
