# Project Resume

이 문서는 작업을 중단했다가 다시 시작할 때 사용하는 단일 진입점이다. 현재 상태, 결과, 로컬 산출물, 재현 명령 및 다음 작업을 요약한다.

## 1. Project Goal

STM32N657 + FreeRTOS 환경에서 경량 CNN을 실행하고 Knowledge Distillation, INT8 quantization, Neural-ART NPU 가속, 실시간 task interference 및 adaptive QoS를 단계적으로 검증한다.

현재 단계는 보드 도착 전 PC-side compression이다.

## 2. Confirmed Configuration

```text
Dataset: CIFAR-10
Teacher: ResNet18 (selected, not trained yet)
Student: MobileNetV2, ImageNet V2 pretrained
Input: static 1x3x96x96
Classes: 10
Seed: 42
Python: 3.12.3
PyTorch: 2.13.0 + CUDA 13.0
GPU: NVIDIA GeForce RTX 5060 Ti 16 GB
ONNX opset: 17
STM32 tool: ST Edge AI Core 4.0.1-20581
Target: STM32N6 Neural-ART NPU
```

Main config: `configs/cifar10_mobilenetv2.yaml`

## 3. Completed Work

- Repository structure and Python virtual environment
- CIFAR-10 download and deterministic preprocessing
- MobileNetV2 10-class model construction
- Student baseline training for 30 epochs
- FP32 ONNX export, checker and ONNX Runtime comparison
- STM32Cube AI Studio FP32 import/analyze
- Static PTQ with ONNX QDQ, INT8 weights/activations, per-channel
- Full CIFAR-10 validation of FP32 and INT8 ONNX
- STM32Cube AI Studio INT8 import/analyze
- INT8 Neural-ART full hardware/EC mapping confirmation

## 4. Results

### PC Accuracy and Model Size

| Model | Accuracy | Accuracy Delta | ONNX Size | Size Reduction |
|---|---:|---:|---:|---:|
| Student FP32 ONNX | 95.45% | - | 8.51 MiB | - |
| Student PTQ INT8 QDQ | 95.32% | -0.13%p | 2.54 MiB | 70.14% |

Training best validation accuracy was 95.46% at epoch 28. PyTorch and FP32 ONNX Runtime max absolute output error was 0.00000083.

### STM32N6 Analyze

| Metric | FP32 | PTQ INT8 |
|---|---:|---:|
| Weights | 8.47 MiB | 2.26 MiB |
| Activations | 1.58 MiB | 270 KiB |
| Total mapped memory | 10.049 MiB | 2.526 MiB |
| Software epochs | 100 | 0 |
| Hardware/EC epochs | 1 | 55 |
| Main activation pool | npuRAM5 96.43% | npuRAM5 60.27% |

Interpretation: FP32 is compatible but mostly software fallback. PTQ INT8 preserves accuracy and maps the complete network to Neural-ART hardware/EC.

## 5. Local Artifacts

These files exist locally and are ignored by Git:

```text
models/mobilenet_v2_cifar10_init.pth
models/student_baseline_best.pth
models/student_baseline_last.pth
models/student_baseline_fp32.onnx
models/student_baseline_int8_qdq.onnx
results/raw_logs/student_baseline_history.csv
training/datasets/cifar-10-batches-py/
```

This final comparison table is tracked by Git:

```text
results/tables/quantization_comparison.csv
```

STM32Cube AI Studio raw reports currently remain in the Windows AI Studio workspace. Copy them into the tracked directory with descriptive names:

```text
results/reports/fp32_network_analyze_report.txt
results/reports/int8_network_analyze_report.txt
```

Do not commit `.pth`, `.onnx`, downloaded datasets, `.venv`, or raw epoch logs unless the repository storage policy is intentionally changed.

## 6. Reproduction Commands

Run from the repository root:

```bash
source .venv/bin/activate

python -m training.prepare_model \
  --config configs/cifar10_mobilenetv2.yaml

python -m training.train_student \
  --config configs/cifar10_mobilenetv2.yaml \
  --download \
  --smoke-test

# Remove --smoke-test for the configured 30-epoch run.
python -m training.train_student \
  --config configs/cifar10_mobilenetv2.yaml

python -m training.export_onnx \
  --config configs/cifar10_mobilenetv2.yaml

python -m training.quantize_ptq \
  --config configs/cifar10_mobilenetv2.yaml
```

The PTQ command uses 1,000 deterministic CIFAR-10 training samples for MinMax calibration and evaluates both FP32 and INT8 models on all 10,000 validation images.

## 7. Next Work

Recommended order:

1. Copy the two STM32 `network_analyze_report.txt` files into `results/reports/`.
2. Implement and train the ResNet18 Teacher with the same input and preprocessing.
3. Confirm that Teacher accuracy is higher than the 95.45% Student baseline.
4. Implement one minimal KD experiment using initial `temperature=4`, `alpha=0.5`.
5. Compare Student baseline FP32, Student KD FP32, baseline PTQ INT8 and KD PTQ INT8.
6. Quantize the KD Student with the same QDQ PTQ pipeline.
7. Run STM32N6 analyze for the KD INT8 model.
8. Keep the current baseline PTQ model as the final deployment candidate if KD gives less than 0.2%p improvement.
9. Implement PC latency/model comparison automation.
10. After board arrival, perform on-target accuracy, latency, throughput and memory validation before RTOS integration.

QAT is not currently required because baseline PTQ accuracy loss is only 0.13%p. Reconsider QAT only if KD PTQ has a materially larger loss or a future model fails quantization.

## 8. Explicit Reference Order

When resuming, read these files in order:

1. `resume.md` — current status, exact results, local artifacts and next work.
2. `CODEX.md` — repository rules, current priorities and scope restrictions.
3. `docs/TODO.md` — completed and pending checklist.
4. `configs/cifar10_mobilenetv2.yaml` — authoritative model/training/export/PTQ settings.
5. `docs/STM32_AI_ANALYSIS.md` — detailed FP32 vs INT8 STM32N6 analysis.
6. `docs/EXPERIMENT_PLAN.md` — required experiment comparison tables.
7. `training/models.py` — model factory and classifier replacement.
8. `training/data.py` — preprocessing and reproducible data loaders.
9. `training/engine.py` — shared training/evaluation loops.
10. `training/train_student.py` — baseline training and checkpoint schema.
11. `training/export_onnx.py` — FP32 ONNX export and output validation.
12. `training/quantize_ptq.py` — QDQ PTQ calibration and accuracy comparison.
13. `docs/ARCHITECTURE.md` — future FreeRTOS/firmware architecture.
14. `docs/PROJECT_PLAN.md` — full project milestones and risk policy.

Do not infer results from filenames alone. Use `results/tables/quantization_comparison.csv` for PC quantization results and `docs/STM32_AI_ANALYSIS.md` for the manually measured STM32 analysis.

## 9. Known Notes and Caveats

- The source QDQ ONNX has FP32 boundary tensors, but ST Edge AI translated input/output to INT8 and mapped SW 0 / HW 55.
- AI Studio `model_fmt: float` does not indicate failure for this QDQ model; use the translated tensor types and epoch mapping as evidence.
- The CLI `--batch-size 10` did not change the static model shape; the analyzed model remains batch 1.
- ST `params # (8.47 MiB)` is a logical FP32-equivalent parameter display. Actual INT8 deployment weights are 2.26 MiB.
- STM32 analyze results are compiler estimates, not on-board latency measurements.
- Model checkpoints contain optimizer state and are larger than deployment-only state dictionaries.

## 10. Git State

The last pushed commit before PTQ work is:

```text
7eb72a9 Add student baseline and STM32 AI validation
```

PTQ code, results and documentation changes after that commit are currently uncommitted unless a later commit has been made. Run `git status --short` before continuing and preserve unrelated user changes.
