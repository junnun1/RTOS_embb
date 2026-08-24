"""Create and evaluate a static INT8 QDQ model with ONNX Runtime PTQ."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import yaml
from onnxruntime.quantization import (
    CalibrationDataReader,
    CalibrationMethod,
    QuantFormat,
    QuantType,
    quantize_static,
)
from torch.utils.data import Subset

from training.data import build_cifar10_dataset


QUANT_TYPES = {
    "int8": QuantType.QInt8,
    "uint8": QuantType.QUInt8,
}
CALIBRATION_METHODS = {
    "minmax": CalibrationMethod.MinMax,
    "entropy": CalibrationMethod.Entropy,
    "percentile": CalibrationMethod.Percentile,
}


class CIFAR10CalibrationReader(CalibrationDataReader):
    """Yield deterministic normalized CIFAR-10 samples to ONNX Runtime."""

    def __init__(self, dataset: Subset, input_name: str) -> None:
        self.input_name = input_name
        self.iterator = iter(dataset)

    def get_next(self) -> dict[str, np.ndarray] | None:
        try:
            image, _ = next(self.iterator)
        except StopIteration:
            return None
        return {self.input_name: image.unsqueeze(0).numpy()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/cifar10_mobilenetv2.yaml"),
    )
    parser.add_argument("--input", type=Path, default=None, help="Override FP32 ONNX input.")
    parser.add_argument("--output", type=Path, default=None, help="Override INT8 QDQ output.")
    parser.add_argument(
        "--comparison-output",
        type=Path,
        default=None,
        help="Override comparison CSV output.",
    )
    parser.add_argument("--model-name", default="student_baseline")
    return parser.parse_args()


def evaluate_model(model_path: Path, dataset) -> float:
    session = ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    correct = 0

    for image, target in dataset:
        logits = session.run(
            [output_name],
            {input_name: image.unsqueeze(0).numpy()},
        )[0]
        correct += int(int(logits.argmax(axis=1)[0]) == int(target))
    return correct / len(dataset)


def write_comparison(
    path: Path,
    *,
    fp32_path: Path,
    int8_path: Path,
    fp32_accuracy: float,
    int8_accuracy: float,
    model_name: str = "student_baseline",
) -> None:
    rows = [
        {
            "model_name": f"{model_name}_fp32",
            "precision": "fp32",
            "accuracy": fp32_accuracy,
            "model_size_mb": fp32_path.stat().st_size / (1024 * 1024),
        },
        {
            "model_name": f"{model_name}_ptq",
            "precision": "int8_qdq",
            "accuracy": int8_accuracy,
            "model_size_mb": int8_path.stat().st_size / (1024 * 1024),
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    with args.config.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    quantization_config = config["quantization"]
    fp32_path = args.input or Path(config["paths"]["student_baseline_onnx"])
    int8_path = args.output or Path(config["paths"]["student_baseline_int8_onnx"])
    comparison_path = args.comparison_output or Path(config["paths"]["quantization_comparison"])
    if not fp32_path.is_file():
        raise FileNotFoundError(f"FP32 ONNX model not found: {fp32_path}")

    calibration_count = int(quantization_config["calibration_samples"])
    calibration_dataset = build_cifar10_dataset(config, train=True)
    if calibration_count > len(calibration_dataset):
        raise ValueError("calibration_samples exceeds the training dataset size")
    calibration_subset = Subset(calibration_dataset, range(calibration_count))

    validation_dataset = build_cifar10_dataset(config, train=False)
    fp32_session = ort.InferenceSession(
        str(fp32_path),
        providers=["CPUExecutionProvider"],
    )
    input_name = fp32_session.get_inputs()[0].name
    int8_path.parent.mkdir(parents=True, exist_ok=True)

    quantize_static(
        model_input=fp32_path,
        model_output=int8_path,
        calibration_data_reader=CIFAR10CalibrationReader(
            calibration_subset,
            input_name,
        ),
        quant_format=QuantFormat.QDQ,
        per_channel=bool(quantization_config["per_channel"]),
        activation_type=QUANT_TYPES[quantization_config["activation_type"]],
        weight_type=QUANT_TYPES[quantization_config["weight_type"]],
        calibrate_method=CALIBRATION_METHODS[
            quantization_config["calibration_method"]
        ],
        extra_options={
            "ActivationSymmetric": True,
            "WeightSymmetric": True,
        },
    )

    onnx.checker.check_model(onnx.load(int8_path))
    fp32_accuracy = evaluate_model(fp32_path, validation_dataset)
    int8_accuracy = evaluate_model(int8_path, validation_dataset)
    write_comparison(
        comparison_path,
        fp32_path=fp32_path,
        int8_path=int8_path,
        fp32_accuracy=fp32_accuracy,
        int8_accuracy=int8_accuracy,
        model_name=args.model_name,
    )

    fp32_size = fp32_path.stat().st_size / (1024 * 1024)
    int8_size = int8_path.stat().st_size / (1024 * 1024)
    print(f"format: QDQ {quantization_config['weight_type']}/{quantization_config['activation_type']}")
    print(f"calibration_samples: {calibration_count}")
    print(f"fp32_accuracy: {fp32_accuracy:.4f}")
    print(f"int8_accuracy: {int8_accuracy:.4f}")
    print(f"accuracy_delta_percentage_points: {(int8_accuracy - fp32_accuracy) * 100:.2f}")
    print(f"fp32_size_mb: {fp32_size:.2f}")
    print(f"int8_size_mb: {int8_size:.2f}")
    print(f"size_reduction_percent: {(1 - int8_size / fp32_size) * 100:.2f}")
    print(f"onnx: {int8_path}")
    print(f"comparison: {comparison_path}")
    print("validation: passed")


if __name__ == "__main__":
    main()
