# Project Resume

이 파일은 작업 재개의 단일 진입점이다. 아래 내용은 2026-08-26 기준이며,
PC-side compression과 STM32N6 compiler validation을 완료하고 pre-board RTOS
portable module 구현을 시작한 상태를 기록한다.

## 1. Current State

현재 단계는 **보드 도착 전 RTOS preparation**이다. PC compression과 compiler
validation은 끝났으며, board-independent architecture와 portable firmware skeleton을
먼저 준비한 뒤 STM32N657 bring-up으로 이동한다.

첫 portable module로 task 실행 record와 cycle/time 변환을 담당하는
`system_metrics`를 구현하고 host test를 통과했다. 하드웨어 cycle reader를 함수
포인터로 주입하는 `profiler` interface와 host test도 구현했다. RTOS 구조는 synthetic
BackgroundTask 대신 세 periodic InferenceTask가 application NPU mutex를 경쟁하는
non-preemptive fixed-priority RM 방식으로 확정했다. Monitor와 QoSController는 분리하며,
다음 작업은 이 contract를 window metrics와 portable C interface로 옮기는 것이다.

완료된 end-to-end 경로:

```text
CIFAR-10
  -> Student baseline training
  -> FP32 ONNX export/runtime validation
  -> Static PTQ INT8 QDQ
  -> Full validation accuracy evaluation
  -> STM32N6 Neural-ART compiler analysis

ResNet18 Teacher
  -> KD Student training
  -> FP32 ONNX export/runtime validation
  -> Static PTQ INT8 QDQ
  -> Full validation accuracy evaluation
  -> STM32N6 Neural-ART compiler analysis
```

두 INT8 모델 모두 `SW 0 / HW(EC) 55`로 전체 NPU mapping에 성공했다.
정확도가 더 높은 **baseline PTQ INT8를 배포 후보로 확정**한다.

## 2. Fixed Configuration

```text
Dataset: CIFAR-10, train 50,000 / validation 10,000
Teacher: ResNet18, ImageNet pretrained
Student: MobileNetV2, ImageNet V2 pretrained
Input: static 1x3x96x96
Classes: 10
Seed: 42
Student epochs: 30
Teacher epochs: 60
KD epochs: 30
KD temperature: 4.0
KD alpha: 0.5
Python: 3.12.3
PyTorch: 2.13.0 + CUDA 13.0
GPU: NVIDIA GeForce RTX 5060 Ti 16 GB
ONNX opset: 17
PTQ: QDQ, INT8/INT8, per-channel, MinMax
Calibration: deterministic CIFAR-10 train samples 0..999
ST Edge AI Core: 4.0.1-20581
Neural-ART compiler: 1.1.3-275
Target: STM32N6 Neural-ART NPU
```

Authoritative config: `configs/cifar10_mobilenetv2.yaml`

## 3. Final PC Results

| Model | Accuracy | Delta vs baseline FP32 | ONNX size | PC role |
|---|---:|---:|---:|---|
| Student baseline FP32 | 95.45% | - | 8.51 MiB | Compatibility baseline |
| Student baseline PTQ INT8 | **95.32%** | -0.13%p | **2.54 MiB** | **Deployment candidate** |
| Teacher ResNet18 | 95.03% | -0.42%p | - | KD teacher |
| Student KD FP32 | 95.25% | -0.20%p | 8.51 MiB | KD comparison |
| Student KD PTQ INT8 | 95.21% | -0.24%p | 2.54 MiB | Deployable comparison |

Additional facts:

- Student training best was 95.46% at epoch 28/30.
- Teacher best was 95.03% at epoch 60/60.
- KD Student best was 95.25% at epoch 30/30.
- baseline FP32 to PTQ loss was 0.13%p.
- KD FP32 to PTQ loss was 0.04%p.
- both INT8 ONNX files are 70.14% smaller than their FP32 versions.
- baseline PyTorch/ONNX Runtime max absolute output error was 0.00000083.
- KD PyTorch/ONNX Runtime max absolute output error was 0.00000238.

Interpretation: Teacher가 Student보다 약했고 최소 KD 실험은 baseline을 개선하지
못했다. QAT는 PTQ 손실이 이미 작기 때문에 수행하지 않는다.

## 4. STM32N6 Compiler Results

| Metric | Baseline FP32 | Baseline PTQ INT8 | KD PTQ INT8 |
|---|---:|---:|---:|
| Compile | Passed | Passed | Passed |
| Weights | 8.47 MiB | 2.26 MiB | 2.26 MiB |
| Activations | 1.58 MiB | 270 KiB | 270 KiB |
| Total mapped memory | 10.049 MiB | 2.526 MiB | 2.526 MiB |
| MACC | 55,041,829 | 56,534,389 | 56,534,389 |
| SW epochs | 100 | 0 | 0 |
| HW/EC epochs | 1 | 55 | 55 |
| npuRAM5 | 96.43% | 60.27% | 60.27% |
| octoFlash | 7.56% | 2.02% | 2.02% |

FP32는 변환 가능하지만 대부분 software fallback이므로 NPU 배포 후보가 아니다.
두 QDQ INT8 모델은 compiler 기준 완전한 Neural-ART hardware/EC mapping이다.

주의:

- source QDQ ONNX의 boundary는 FP32지만 ST 변환 결과는 INT8 input/output이다.
- `model_fmt: float` 표시는 QDQ 변환 실패를 의미하지 않는다.
- `--batch-size 10`은 static batch-1 ONNX shape를 바꾸지 않았다.
- ST의 `params # (8.47 MiB)`는 논리적 FP32-equivalent 표시다.
- compiler analyze는 실제 board latency 측정이 아니다.

## 5. Deployment Decision

선택 모델:

```text
models/student_baseline_int8_qdq.onnx
```

선택 이유:

1. validation accuracy 95.32%로 KD PTQ보다 0.11%p 높다.
2. FP32 대비 손실이 0.13%p에 불과하다.
3. weights 2.26 MiB와 activations 270 KiB가 지정 memory pool에 들어간다.
4. software fallback 없이 55개 epoch 전체가 HW/EC에 매핑된다.
5. KD 모델과 계산량·메모리가 같으므로 더 낮은 KD 정확도를 선택할 이유가 없다.

## 6. Local and Tracked Artifacts

Git ignored local artifacts:

```text
models/mobilenet_v2_cifar10_init.pth
models/student_baseline_best.pth
models/student_baseline_last.pth
models/student_baseline_fp32.onnx
models/student_baseline_int8_qdq.onnx
models/teacher_resnet18_best.pth
models/teacher_resnet18_last.pth
models/student_kd_best.pth
models/student_kd_last.pth
models/student_kd_fp32.onnx
models/student_kd_int8_qdq.onnx
results/raw_logs/student_baseline_history.csv
results/raw_logs/teacher_resnet18_history.csv
results/raw_logs/student_kd_history.csv
training/datasets/cifar-10-batches-py/
```

Tracked results:

```text
results/tables/quantization_comparison.csv
results/tables/kd_quantization_comparison.csv
results/tables/model_comparison.csv
results/reports/baseline_fp32_network_analyze_report.txt
results/reports/baseline_int8_network_analyze_report.txt
results/reports/kd_int8_network_analyze_report.txt
```

Do not commit `.pth`, `.onnx`, downloaded datasets, `.venv`, or raw epoch logs unless
the storage policy is intentionally changed.

## 7. Reproduction Commands

Run from repository root:

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

학습 스크립트는 `--smoke-test`를 지원한다. PTQ는 validation 10,000장을 모두
평가하므로 smoke test가 아니다.

### Pre-board RTOS host test

현재 `system_metrics` host test는 정상 record, deadline miss, 32-bit cycle counter
wrap-around, zero CPU clock을 검증한다.

```bash
cc -std=c11 \
  -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror \
  -Ifirmware/System \
  firmware/System/system_metrics.c \
  tests/firmware/test_system_metrics.c \
  -o /tmp/test_system_metrics \
  && /tmp/test_system_metrics
```

현재 구현 파일:

```text
firmware/System/system_metrics.c/.h
firmware/System/profiler.c/.h
tests/firmware/test_system_metrics.c
tests/firmware/test_profiler.c
```

`system_metrics`는 release/start/end cycle, execution/response cycle과 microsecond,
deadline miss, task/QoS/background metadata를 `task_run_record_t`로 정의한다. cycle
차이는 unsigned subtraction으로 계산하며, cycle-to-us 변환은 64-bit 중간 연산과
`UINT32_MAX` saturation을 사용한다.

`profiler`는 cycle reader 함수와 context, CPU clock을 주입받는다. host test는 fake
reader 주입, invalid argument, 일반 cycle 차이, 32-bit wrap-around, CPU clock 조회를
검증한다. 보드용 DWT CYCCNT adapter는 아직 미완료다.

## 8. Immediate Next Work

현재 compression 실험을 반복하지 않는다.

### Before board arrival

1. windowed logical NPU utilization과 DMR aggregate contract를 정의한다.
2. `qos_window_state_t`와 `qos_action_t` portable interface를 작성한다.
3. global QoS scale, lower band, hysteresis, cooldown 규칙을 정의한다.
4. stream ID, mutex wait, window index를 반영해 metrics/UART CSV schema를 갱신한다.
5. non-preemptive RM response-time analysis module/test 방식을 정한다.
6. HAL/FreeRTOS/AI runtime dependency를 adapter로 분리한 portable C skeleton을 확장한다.

완료된 항목:

- release/start/end cycle, execution/response cycle·time, deadline miss record
- unsigned subtraction 기반 32-bit cycle counter wrap-around 정책
- 64-bit 중간 연산과 saturation을 포함한 cycle-to-us 변환
- 함수 포인터와 context를 주입받는 board-independent profiler interface
- `system_metrics` host test 및 strict C11 warning-free build
- `profiler` host test 및 strict C11 warning-free build
- periodic inference task 3개와 base-period RM relative priority contract
- full-inference application NPU mutex와 priority inheritance policy
- Monitor/QoSController 분리 및 metrics single-writer ownership
- logical NPU utilization `U*=0.67`, DMR `M*=0.05` 초기 reference

보드가 없으므로 CPU clock, peripheral handle, memory address, generated AI symbol을
임의로 hardcode하지 않는다.

### After board arrival

1. STM32CubeIDE/CubeMX project 구조를 준비한다.
2. baseline PTQ generated Neural-ART runtime을 firmware에 통합한다.
3. preloaded CIFAR-10 test vector와 expected logits/class를 준비한다.
4. 단일 inference 결과를 ONNX Runtime output과 비교한다.
5. DWT CYCCNT profiler와 UART CSV logging을 구현한다.
6. latency mean/p50/p95/max, throughput, Flash/RAM을 보드에서 측정한다.
7. 동일 모델을 사용하는 periodic InferenceTask 3개와 공용 NPU mutex를 구성한다.
8. warm inference `C_i` 측정 후 `U*=0.67` 기준 base period/QoS scale을 확정한다.
9. fixed global QoS에서 blocking, logical NPU utilization, DMR을 측정한다.
10. board-local heuristic QoS를 구현한 뒤 PC RL state/action transport로 확장한다.

최초 bring-up에는 camera를 연결하지 않는다.

## 9. Deferred or Conditional Work

- QAT: future PTQ accuracy loss가 커질 때만 재검토
- Teacher/KD tuning: 추가 accuracy 연구가 필요할 때만 수행
- input-resolution/model-switching QoS: 각 variant를 다시 export/analyze한 뒤 수행
- camera: static test-vector inference 이후
- PC RL controller: board-local heuristic과 UART state/action contract 완료 이후
- pruning, object detection, dashboard: MVP 이후

## 10. Resume Reading Order

1. `resume.md`
2. `CODEX.md`
3. `docs/TODO.md`
4. `configs/cifar10_mobilenetv2.yaml`
5. `docs/EXPERIMENT_PLAN.md`
6. `docs/STM32_AI_ANALYSIS.md`
7. `docs/KD_STM32_AI_ANALYSIS.md`
8. `docs/ARCHITECTURE.md`
9. `docs/PROJECT_PLAN.md`
10. `training/models.py`
11. `training/data.py`
12. `training/engine.py`
13. `training/train_student.py`
14. `training/train_teacher.py`
15. `training/train_kd.py`
16. `training/export_onnx.py`
17. `training/quantize_ptq.py`
18. `benchmarks/benchmark_models.py`

Before editing, run `git status --short` and preserve unrelated user changes.

## 11. Git Reference

Last pushed commit before the current RTOS architecture documentation adjustment:

```text
5715b8f test: add portable profiler host coverage
```

Always use `git status --short` and `git log -1 --oneline` instead of assuming this
reference remains current.
