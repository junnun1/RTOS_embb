"""Train the MobileNetV2 student baseline on CIFAR-10."""

from __future__ import annotations

import argparse
import csv
import random
import time
from pathlib import Path

import numpy as np
import torch
import yaml

from training.data import build_cifar10_loaders
from training.engine import evaluate, train_one_epoch
from training.models import build_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/cifar10_mobilenetv2.yaml"),
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download CIFAR-10 when it is not available locally.",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run two training and validation batches for pipeline verification.",
    )
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def save_checkpoint(
    path: Path,
    *,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    validation_accuracy: float,
    config: dict,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "epoch": epoch,
            "validation_accuracy": validation_accuracy,
            "config": config,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
        },
        path,
    )


def write_history(path: Path, rows: list[dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    with args.config.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    seed = int(config["project"]["seed"])
    set_seed(seed)
    torch.hub.set_dir(config["paths"]["torch_cache"])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    mixed_precision = bool(config["training"]["mixed_precision"]) and device.type == "cuda"
    train_loader, validation_loader = build_cifar10_loaders(
        config,
        download=args.download,
    )
    model = build_model(config).to(device)
    criterion = torch.nn.CrossEntropyLoss(
        label_smoothing=float(config["training"]["label_smoothing"])
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["training"]["learning_rate"]),
        weight_decay=float(config["training"]["weight_decay"]),
    )
    epochs = 1 if args.smoke_test else int(config["training"]["epochs"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    scaler = torch.amp.GradScaler(device.type, enabled=mixed_precision)
    max_batches = 2 if args.smoke_test else None

    history: list[dict[str, float]] = []
    best_accuracy = -1.0
    print(f"device: {device}, mixed_precision: {mixed_precision}")
    print(f"train_samples: {len(train_loader.dataset):,}")
    print(f"validation_samples: {len(validation_loader.dataset):,}")

    for epoch in range(1, epochs + 1):
        start_time = time.perf_counter()
        train_metrics = train_one_epoch(
            model,
            train_loader,
            criterion,
            optimizer,
            scaler,
            device,
            mixed_precision=mixed_precision,
            max_batches=max_batches,
        )
        validation_metrics = evaluate(
            model,
            validation_loader,
            criterion,
            device,
            mixed_precision=mixed_precision,
            max_batches=max_batches,
        )
        scheduler.step()
        row = {
            "epoch": epoch,
            "train_loss": train_metrics["loss"],
            "train_accuracy": train_metrics["accuracy"],
            "validation_loss": validation_metrics["loss"],
            "validation_accuracy": validation_metrics["accuracy"],
            "learning_rate": scheduler.get_last_lr()[0],
            "elapsed_seconds": time.perf_counter() - start_time,
        }
        history.append(row)
        print(
            f"epoch {epoch:03d}/{epochs:03d} "
            f"train_acc={row['train_accuracy']:.4f} "
            f"val_acc={row['validation_accuracy']:.4f} "
            f"elapsed={row['elapsed_seconds']:.1f}s"
        )

        if not args.smoke_test and validation_metrics["accuracy"] > best_accuracy:
            best_accuracy = validation_metrics["accuracy"]
            save_checkpoint(
                Path(config["paths"]["student_best_checkpoint"]),
                model=model,
                optimizer=optimizer,
                epoch=epoch,
                validation_accuracy=best_accuracy,
                config=config,
            )

    if args.smoke_test:
        print("smoke_test: passed")
        return

    save_checkpoint(
        Path(config["paths"]["student_last_checkpoint"]),
        model=model,
        optimizer=optimizer,
        epoch=epochs,
        validation_accuracy=history[-1]["validation_accuracy"],
        config=config,
    )
    write_history(Path(config["paths"]["student_history"]), history)


if __name__ == "__main__":
    main()

