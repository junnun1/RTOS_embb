# STM32N6 AI Analysis Results

## Test Information

```text
Date: 2026-08-24
Tool: ST Edge AI Core 4.0.1-20581
Target: STM32N6 Neural-ART NPU
Model: student_baseline_fp32.onnx
Model input: FP32 1x3x96x96
Model output: FP32 1x10
```

## Result

ST Edge AI Core의 ONNX import, graph optimization, Neural-ART compiler 실행 및 report 생성이 오류 없이 완료됐다.

| Metric | Value |
|---|---:|
| Model parameters reported by ST | 2,219,626 items |
| Weights | 8.47 MiB |
| Activations | 1.58 MiB |
| Input buffer | 108.00 KiB |
| Output buffer | 40 B |
| MACC | 55,041,829 |
| Epochs | 101 |
| Pure software epochs | 100 |
| Pure hardware/EC epochs | 1 |

## Memory Mapping

| Memory | Used | Capacity | Usage |
|---|---:|---:|---:|
| cpuRAM2 | 864 KiB | 1 MiB | 84.38% |
| npuRAM4 | 324 KiB | 448 KiB | 72.32% |
| npuRAM5 | 432 KiB | 448 KiB | 96.43% |
| octoFlash | 8.467 MiB | 112 MiB | 7.56% |

## Interpretation

- FP32 ONNX의 operator compatibility와 STM32N6 코드 생성 경로는 확인됐다.
- `not quantized` warning은 FP32 baseline에서 예상된 결과이며 compile failure가 아니다.
- Conv, Clip, Add 등 대부분의 연산이 software epoch으로 배치됐다.
- hardware/EC epoch 1개만으로 Neural-ART 연산 가속이 확보됐다고 판단하지 않는다.
- npuRAM5 사용률이 96.43%이므로 FP32 activation 배치의 여유가 작다.

## Next Validation

INT8 모델에 대해 동일한 분석을 실행하고 아래 항목을 비교한다.

1. validation accuracy
2. model and weight size
3. activation RAM
4. software / hardware epoch ratio
5. board latency and throughput

ST Edge AI Core 4.x는 양자화 정보를 포함한 모델을 입력으로 사용한다. 최종 NPU 검증에는 QDQ ONNX 또는 도구가 지원하는 self-contained INT8 모델을 사용한다.
