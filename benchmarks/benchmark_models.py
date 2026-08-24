"""Evaluate accuracy, size, parameter count, and PC latency of ONNX models."""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
import yaml

from training.data import build_cifar10_dataset
from training.models import build_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/cifar10_mobilenetv2.yaml"))
    parser.add_argument("--warmup-runs", type=int, default=20)
    parser.add_argument("--latency-runs", type=int, default=100)
    parser.add_argument("--max-validation-samples", type=int, default=None)
    parser.add_argument("--allow-missing", action="store_true")
    return parser.parse_args()


def benchmark_onnx(
    path: Path,
    dataset,
    *,
    warmup_runs: int,
    latency_runs: int,
    max_validation_samples: int | None,
) -> tuple[float, float]:
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    sample = dataset[0][0].unsqueeze(0).numpy()
    for _ in range(warmup_runs):
        session.run([output_name], {input_name: sample})
    latencies = []
    for _ in range(latency_runs):
        start = time.perf_counter()
        session.run([output_name], {input_name: sample})
        latencies.append((time.perf_counter() - start) * 1000.0)

    sample_count = len(dataset)
    if max_validation_samples is not None:
        sample_count = min(sample_count, max_validation_samples)
    correct = 0
    for index in range(sample_count):
        image, target = dataset[index]
        logits = session.run([output_name], {input_name: image.unsqueeze(0).numpy()})[0]
        correct += int(int(logits.argmax(axis=1)[0]) == int(target))
    return correct / sample_count, float(np.mean(latencies))


def main() -> None:
    args = parse_args()
    if args.warmup_runs < 0 or args.latency_runs <= 0:
        raise ValueError("warmup-runs must be non-negative and latency-runs must be positive")
    with args.config.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    dataset = build_cifar10_dataset(config, train=False)
    student_config = dict(config)
    student_config["model"] = dict(config["model"], pretrained=False)
    parameter_count = sum(p.numel() for p in build_model(student_config).parameters())
    candidates = [
        ("student_baseline_fp32", "fp32", "student_baseline_onnx"),
        ("student_kd_fp32", "fp32", "student_kd_onnx"),
        ("student_baseline_ptq", "int8_qdq", "student_baseline_int8_onnx"),
        ("student_kd_ptq", "int8_qdq", "student_kd_int8_onnx"),
    ]
    rows = []
    for model_name, precision, path_key in candidates:
        path = Path(config["paths"][path_key])
        if not path.is_file():
            if args.allow_missing:
                print(f"skip_missing: {path}")
                continue
            raise FileNotFoundError(f"Model not found: {path}")
        accuracy, latency = benchmark_onnx(
            path, dataset, warmup_runs=args.warmup_runs,
            latency_runs=args.latency_runs,
            max_validation_samples=args.max_validation_samples,
        )
        row = {
            "model_name": model_name,
            "precision": precision,
            "accuracy": accuracy,
            "parameter_count": parameter_count,
            "model_size_mb": path.stat().st_size / (1024 * 1024),
            "pc_latency_ms": latency,
            "notes": "ONNX Runtime CPUExecutionProvider; batch=1",
        }
        rows.append(row)
        print(f"{model_name}: accuracy={accuracy:.4f}, latency_ms={latency:.3f}")
    if not rows:
        raise RuntimeError("No model artifacts were found")
    output_path = Path(config["paths"]["model_comparison"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"comparison: {output_path}")


if __name__ == "__main__":
    main()
