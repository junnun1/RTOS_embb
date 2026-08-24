# KD Student STM32N6 Analysis

## 1. Experiment Purpose

Knowledge Distillation로 학습한 MobileNetV2 Student를 INT8 QDQ로 양자화한 뒤,
STM32N6 Neural-ART NPU에 전체 매핑할 수 있는지 확인한다.

이 분석은 보드에서 측정한 결과가 아니라 ST Edge AI compiler의 정적 분석 결과다.

## 2. Model and Tool Configuration

```text
Dataset: CIFAR-10
Student: MobileNetV2, ImageNet V2 pretrained
Teacher: ResNet18, ImageNet pretrained
Input shape: static 1x3x96x96
Classes: 10
KD temperature: 4.0
KD alpha: 0.5
KD epochs: 30
Quantization: static PTQ, ONNX QDQ, INT8/INT8, per-channel
Calibration: CIFAR-10 train 1,000 samples, MinMax
ONNX opset: 17
ST Edge AI Core: 4.0.1-20581
Neural-ART compiler: 1.1.3-275
Target: STM32N6 Neural-ART NPU
Analyze mode: host
```

Analyzed model:

```text
models/student_kd_int8_qdq.onnx
```

The CLI included `--batch-size 10`, but the model remained the exported static batch-1
shape. The translated input tensor was `int8(1x3x96x96)` and the output tensor was
`int8(1x10)`.

## 3. PC Accuracy and Size

| Model | Accuracy | Accuracy Delta | ONNX Size | Size Reduction |
|---|---:|---:|---:|---:|
| Student baseline FP32 | 95.45% | - | 8.51 MiB | - |
| Student baseline PTQ INT8 | 95.32% | -0.13%p | 2.54 MiB | 70.14% |
| Student KD FP32 | 95.25% | -0.20%p vs baseline FP32 | 8.51 MiB | - |
| Student KD PTQ INT8 | 95.21% | -0.04%p vs KD FP32 | 2.54 MiB | 70.14% |

The Teacher validation accuracy was 95.03%. It did not exceed the 95.45% Student
baseline, and the minimal KD experiment did not improve Student accuracy. However,
the KD model was robust to PTQ: quantization reduced accuracy by only 0.04%p.

## 4. STM32N6 Analyze Result

### Network summary

| Metric | KD PTQ INT8 result |
|---|---:|
| Compile result | Passed |
| Logical parameters | 2,219,626 items |
| Logical FP32-equivalent parameter display | 8.47 MiB |
| Deployment weights | 2,372,720 B (2.26 MiB) |
| Activations | 276,480 B (270 KiB) |
| Total mapped memory | 2.526 MiB |
| MACC | 56,534,389 |
| Software epochs | 0 |
| Hybrid epochs | 0 |
| Hardware/EC epochs | 55 |

### Translated tensors

```text
Input:  int8 1x3x96x96, 27.00 KiB, scale=0.016744005, zero-point=0
Output: int8 1x10,       10 B,       scale=0.032991663, zero-point=0
```

Although the report displays `model_fmt: float`, the translated boundary tensors are
INT8 and all 55 epochs were compiled as hardware/epoch-controller epochs. Therefore,
`model_fmt: float` is not evidence of FP32 software execution for this QDQ model.

## 5. Memory Mapping

| Memory pool | Used | Capacity | Utilization | Contents |
|---|---:|---:|---:|---|
| npuRAM5 | 270 KiB | 448 KiB | 60.27% | Activations |
| octoFlash | 2.263 MiB | 112 MiB | 2.02% | Weights |
| Other configured pools | 0 B | - | 0% | - |

Used address ranges:

```text
npuRAM5:   0x342E0000-0x34323800
octoFlash: 0x71000000-0x71243470
```

The activation pool includes the input and output buffers.

## 6. Epoch Mapping

```text
Total epochs:       55
Pure software:       0
Hybrid:              0
Pure hardware/EC:   55
Epoch controller:    1 blob/meta epoch
```

This confirms complete Neural-ART hardware/EC mapping. There is no software fallback.

## 7. Comparison with Baseline PTQ

| Metric | Baseline PTQ INT8 | KD PTQ INT8 | Difference |
|---|---:|---:|---:|
| Accuracy | 95.32% | 95.21% | -0.11%p |
| ONNX size | 2.54 MiB | 2.54 MiB | None material |
| Weights | 2.26 MiB | 2.26 MiB | None material |
| Activations | 270 KiB | 270 KiB | None |
| MACC | 56,534,389 | 56,534,389 | None |
| SW epochs | 0 | 0 | None |
| HW/EC epochs | 55 | 55 | None |
| npuRAM5 utilization | 60.27% | 60.27% | None |

KD changes learned parameter values but not the MobileNetV2 graph structure. As a
result, deployment size, memory use, MACC, and epoch mapping are the same as the
baseline PTQ model. Only model accuracy differs.

## 8. Conclusion

The KD PTQ INT8 model is deployable on STM32N6 Neural-ART from the compiler's point
of view:

- compilation passed;
- input and output were translated to INT8;
- all 55 epochs mapped to hardware/EC;
- software fallback is zero;
- weights and activations fit the configured octoFlash and npuRAM5 pools.

However, KD did not improve PC validation accuracy. KD PTQ accuracy is 95.21%, which
is 0.11%p below the baseline PTQ model at 95.32%. The baseline PTQ INT8 model therefore
remains the preferred deployment candidate.

Actual latency, throughput, power consumption, and runtime memory behavior must be
measured on the board after arrival. Compiler analysis alone does not provide those
on-target measurements.

## 9. Raw Report Storage

The raw report was generated in the Windows STM32Cube AI Studio workspace as:

```text
C:\Users\SSAFY\.stm32cubeaistudio\workspace\asdf\.ai\run\run-3\.ai\st_ai_output\network_analyze_report.txt
```

It is tracked in the repository using this descriptive name:

```text
results/reports/kd_int8_network_analyze_report.txt
```
