"""Export a trained student checkpoint and validate it with ONNX Runtime."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
import yaml

from training.models import build_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/cifar10_mobilenetv2.yaml"),
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Override the best Student checkpoint path from the config.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override the ONNX output path from the config.",
    )
    return parser.parse_args()


def load_model(config: dict, checkpoint_path: Path) -> torch.nn.Module:
    model_config = copy.deepcopy(config)
    model_config["model"]["pretrained"] = False
    model = build_model(model_config)

    checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )
    state_dict = checkpoint.get("model_state_dict", checkpoint.get("state_dict"))
    if state_dict is None:
        raise KeyError("Checkpoint does not contain a model state dictionary")
    model.load_state_dict(state_dict, strict=True)
    return model.eval()


def export_model(
    model: torch.nn.Module,
    sample_input: torch.Tensor,
    output_path: Path,
    *,
    opset_version: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        sample_input,
        output_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes=None,
        dynamo=False,
    )


def validate_onnx(
    model: torch.nn.Module,
    sample_input: torch.Tensor,
    onnx_path: Path,
    *,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> dict[str, float | int]:
    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)

    with torch.inference_mode():
        pytorch_output = model(sample_input).numpy()

    session = ort.InferenceSession(
        str(onnx_path),
        providers=["CPUExecutionProvider"],
    )
    onnx_output = session.run(
        ["logits"],
        {"input": sample_input.numpy()},
    )[0]

    difference = np.abs(pytorch_output - onnx_output)
    if not np.allclose(
        pytorch_output,
        onnx_output,
        atol=absolute_tolerance,
        rtol=relative_tolerance,
    ):
        raise RuntimeError(
            "ONNX Runtime output differs from PyTorch output: "
            f"max_abs_error={difference.max():.8f}"
        )

    pytorch_class = int(pytorch_output.argmax(axis=1)[0])
    onnx_class = int(onnx_output.argmax(axis=1)[0])
    if pytorch_class != onnx_class:
        raise RuntimeError(
            f"Predicted classes differ: PyTorch={pytorch_class}, ONNX={onnx_class}"
        )

    return {
        "max_absolute_error": float(difference.max()),
        "mean_absolute_error": float(difference.mean()),
        "predicted_class": pytorch_class,
        "node_count": len(onnx_model.graph.node),
    }


def main() -> None:
    args = parse_args()
    with args.config.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    checkpoint_path = args.checkpoint or Path(
        config["paths"]["student_best_checkpoint"]
    )
    output_path = args.output or Path(config["paths"]["student_baseline_onnx"])
    export_config = config["export"]
    batch_size = int(export_config["batch_size"])
    input_size = int(config["dataset"]["input_size"])

    torch.manual_seed(int(config["project"]["seed"]))
    model = load_model(config, checkpoint_path)
    sample_input = torch.randn(batch_size, 3, input_size, input_size)

    export_model(
        model,
        sample_input,
        output_path,
        opset_version=int(export_config["opset_version"]),
    )
    metrics = validate_onnx(
        model,
        sample_input,
        output_path,
        absolute_tolerance=float(export_config["absolute_tolerance"]),
        relative_tolerance=float(export_config["relative_tolerance"]),
    )

    model_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"checkpoint: {checkpoint_path}")
    print(f"onnx: {output_path} ({model_size_mb:.2f} MiB)")
    print(f"opset: {export_config['opset_version']}")
    print(f"input_shape: {tuple(sample_input.shape)}")
    print(f"output_shape: ({batch_size}, {config['dataset']['num_classes']})")
    print(f"graph_nodes: {metrics['node_count']}")
    print(f"max_absolute_error: {metrics['max_absolute_error']:.8f}")
    print(f"mean_absolute_error: {metrics['mean_absolute_error']:.8f}")
    print(f"predicted_class: {metrics['predicted_class']}")
    print("validation: passed")


if __name__ == "__main__":
    main()

