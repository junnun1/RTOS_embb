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

## INT8 Validation Plan

INT8 모델에 대해 다음 항목을 비교하도록 계획했고 모두 완료했다.

1. validation accuracy
2. model and weight size
3. activation RAM
4. software / hardware epoch ratio
5. board latency and throughput

ST Edge AI Core 4.x는 양자화 정보를 포함한 모델을 입력으로 사용한다. 최종 NPU 검증에는 QDQ ONNX 또는 도구가 지원하는 self-contained INT8 모델을 사용한다.

## INT8 Candidate

```text
Model: student_baseline_int8_qdq.onnx
Format: ONNX QDQ, static PTQ
Calibration: CIFAR-10 train 1,000 samples, MinMax
Weights / activations: INT8 / INT8, per-channel
Validation accuracy: 95.32% (-0.13%p)
Model size: 2.54 MiB (-70.14%)
Input / output boundary: FP32 / FP32
```

## STM32N6 INT8 Analysis

```text
Tool: ST Edge AI Core 4.0.1-20581
Target: STM32N6 Neural-ART NPU
Input: INT8 1x3x96x96, 27 KiB
Output: INT8 1x10, 10 B
```

| Metric | INT8 Result | FP32 Result | Change |
|---|---:|---:|---:|
| Weights | 2.26 MiB | 8.47 MiB | -73.3% |
| Activations | 270 KiB | 1.58 MiB | about -83.3% |
| Total mapped memory | 2.526 MiB | 10.049 MiB | about -74.9% |
| MACC | 56,534,389 | 55,041,829 | compiler representation differs |
| Software epochs | 0 | 100 | fully removed |
| Hardware/EC epochs | 55 | 1 | full NPU/EC mapping |

INT8 memory mapping:

| Memory | Used | Capacity | Usage |
|---|---:|---:|---:|
| npuRAM5 | 270 KiB | 448 KiB | 60.27% |
| octoFlash | 2.263 MiB | 112 MiB | 2.02% |
| cpuRAM2 | 0 B | 1 MiB | 0% |

`model_fmt: float` 표시는 QDQ ONNX의 표현 방식 때문이며 실패를 의미하지 않는다. 변환된 input/output tensor가 INT8이고 software epoch이 0이므로 실제 compiler mapping은 quantized Neural-ART 경로를 사용한다.

## Conclusion

- FP32: operator compatibility는 성공했지만 software fallback이 대부분이다.
- PTQ INT8: 정확도 손실 0.13%p, weights 73.3% 감소, activation 약 83.3% 감소.
- PTQ INT8의 모든 55 epoch이 hardware/EC에 매핑됐다.
- baseline Student에는 QAT가 필요하지 않다.
- KD PTQ도 SW 0 / HW(EC) 55로 전체 매핑됐으며 상세 결과는
  `docs/KD_STM32_AI_ANALYSIS.md`에 기록했다.
- 실제 latency와 throughput은 보드에서 profile해야 한다.
