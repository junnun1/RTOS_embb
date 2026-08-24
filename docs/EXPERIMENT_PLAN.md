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

PC latency는 `results/tables/model_comparison.csv`에 ONNX Runtime CPU, batch 1,
20 warmup/100 timed runs 조건으로 기록했다.

| Model | Accuracy | PC latency |
|---|---:|---:|
| Student baseline FP32 | 95.45% | 1.617 ms |
| Student KD FP32 | 95.25% | 0.834 ms |
| Student baseline PTQ INT8 | 95.32% | 2.152 ms |
| Student KD PTQ INT8 | 95.21% | 2.175 ms |

단일 PC 실행 결과이므로 runtime warm-up, CPU frequency, session optimization에 영향을
받는다. PC-side 참고값일 뿐이며 NPU 성능이나 모델 간 확정적 latency 우열로 해석하지 않는다.

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
| Teacher ResNet18 (60 epochs) | 95.03% |
| Student + KD (T=4, alpha=0.5) | 95.25% |

Teacher가 Student baseline보다 0.42%p 낮았으며, 최소 KD 실험도 baseline보다
0.20%p 낮았다. 따라서 현재 설정에서는 KD 정확도 개선 효과가 없다.

---

## Experiment 3 - Quantization

### 3.1 PTQ

FP32 학습 모델을 calibration dataset을 이용해 INT8로 변환.

### 3.2 QAT

학습 과정에서 quantization error를 반영.

현재 PTQ baseline 결과:

| Model | Accuracy | Accuracy Delta | ONNX Size | Size Reduction |
|---|---:|---:|---:|---:|
| Student FP32 | 95.45% | - | 8.51 MiB | - |
| Student PTQ INT8 QDQ | 95.32% | -0.13%p | 2.54 MiB | 70.14% |

PTQ는 CIFAR-10 train split의 deterministic sample 1,000장, MinMax calibration, INT8/INT8 per-channel 설정을 사용했다.

비교:

| Model | Accuracy | Size |
|---|---:|---:|
| KD Student FP32 | 95.25% | 8.51 MiB |
| KD Student PTQ INT8 | 95.21% | 2.54 MiB |
| KD Student QAT INT8 | Not run | Not required |

KD PTQ의 정확도 손실은 0.04%p이며 크기는 70.14% 감소했다. KD가 baseline을
개선하지 못했으므로 현재 baseline PTQ INT8 모델을 배포 후보로 유지한다.

---

## Experiment 4 - Embedded Inference

보드 도착 후 수행.

보드 도착 전 ST Edge AI Core `analyze` 결과:

| Model | Format | Compile | Weights | Activations | MACC | Epoch mapping |
|---|---|---|---:|---:|---:|---|
| MobileNetV2 baseline | FP32 ONNX | Passed | 8.47 MiB | 1.58 MiB | 55,041,829 | SW 100 / HW(EC) 1 |
| MobileNetV2 baseline PTQ | INT8 QDQ ONNX | Passed | 2.26 MiB | 270 KiB | 56,534,389 | SW 0 / HW(EC) 55 |
| MobileNetV2 KD PTQ | INT8 QDQ ONNX | Passed | 2.26 MiB | 270 KiB | 56,534,389 | SW 0 / HW(EC) 55 |

FP32 결과는 operator compatibility baseline이다. baseline과 KD INT8 모델은 모두
compiler 기준 전체 hardware/EC mapping에 성공했다. 실제 NPU latency와 throughput은
보드에서 측정한다.

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

보드 도착 전에 다음 실험 contract와 portable skeleton을 먼저 준비한다.

- Inference/Background/Monitor/Logger task 정의
- period, deadline, priority 초깃값
- DWT profiler와 공통 metrics record
- UART CSV schema
- 0/20/40/60/80% synthetic workload 정의
- 33/66/100 ms inference-period QoS 정의

실제 timing 결과는 보드에서만 기록한다. host stub이나 compiler estimate를
on-target RTOS 결과로 사용하지 않는다.

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
