"""Download pretrained weights and create the CIFAR-10 student checkpoint."""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
import torch
import yaml

from training.models import build_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/cifar10_mobilenetv2.yaml"),
        help="Path to the experiment configuration.",
    )
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def count_parameters(model: torch.nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def main() -> None:
    args = parse_args()
    with args.config.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    seed = int(config["project"]["seed"])
    input_size = int(config["dataset"]["input_size"])
    num_classes = int(config["dataset"]["num_classes"])
    checkpoint_path = Path(config["paths"]["initial_checkpoint"])

    torch.hub.set_dir(config["paths"]["torch_cache"])
    set_seed(seed)
    model = build_model(config)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device).eval()
    sample = torch.randn(1, 3, input_size, input_size, device=device)
    with torch.inference_mode():
        output = model(sample)

    expected_shape = (1, num_classes)
    if tuple(output.shape) != expected_shape:
        raise RuntimeError(
            f"Unexpected output shape: {tuple(output.shape)} != {expected_shape}"
        )

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_name": config["model"]["name"],
            "pretrained_weights": config["model"].get("weights"),
            "dataset_name": config["dataset"]["name"],
            "num_classes": num_classes,
            "input_size": input_size,
            "seed": seed,
            "state_dict": model.cpu().state_dict(),
        },
        checkpoint_path,
    )

    checkpoint_mb = checkpoint_path.stat().st_size / (1024 * 1024)
    print(f"device: {device}")
    print(f"input_shape: {tuple(sample.shape)}")
    print(f"output_shape: {tuple(output.shape)}")
    print(f"parameters: {count_parameters(model):,}")
    print(f"checkpoint: {checkpoint_path} ({checkpoint_mb:.2f} MiB)")


if __name__ == "__main__":
    main()
