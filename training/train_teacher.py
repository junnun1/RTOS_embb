"""Train the ResNet18 teacher on CIFAR-10."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import torch
import yaml

from training.data import build_cifar10_loaders
from training.engine import evaluate, train_one_epoch
from training.models import build_model
from training.train_student import save_checkpoint, set_seed, write_history


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/cifar10_mobilenetv2.yaml"))
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.config.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    set_seed(int(config["project"]["seed"]))
    torch.hub.set_dir(config["paths"]["torch_cache"])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    mixed_precision = bool(config["training"]["mixed_precision"]) and device.type == "cuda"
    train_loader, validation_loader = build_cifar10_loaders(config, download=args.download)
    model = build_model(config, model_key="teacher_model").to(device)
    settings = config["teacher_training"]
    criterion = torch.nn.CrossEntropyLoss(label_smoothing=float(settings["label_smoothing"]))
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(settings["learning_rate"]),
        weight_decay=float(settings["weight_decay"]),
    )
    epochs = 1 if args.smoke_test else int(settings["epochs"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    scaler = torch.amp.GradScaler(device.type, enabled=mixed_precision)
    max_batches = 2 if args.smoke_test else None
    history = []
    best_accuracy = -1.0

    print(f"device: {device}, mixed_precision: {mixed_precision}")
    for epoch in range(1, epochs + 1):
        start_time = time.perf_counter()
        train_metrics = train_one_epoch(
            model, train_loader, criterion, optimizer, scaler, device,
            mixed_precision=mixed_precision, max_batches=max_batches,
        )
        validation_metrics = evaluate(
            model, validation_loader, criterion, device,
            mixed_precision=mixed_precision, max_batches=max_batches,
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
        print(f"epoch {epoch:03d}/{epochs:03d} train_acc={row['train_accuracy']:.4f} val_acc={row['validation_accuracy']:.4f} elapsed={row['elapsed_seconds']:.1f}s")
        if not args.smoke_test and row["validation_accuracy"] > best_accuracy:
            best_accuracy = row["validation_accuracy"]
            save_checkpoint(Path(config["paths"]["teacher_best_checkpoint"]), model=model, optimizer=optimizer, epoch=epoch, validation_accuracy=best_accuracy, config=config)

    if args.smoke_test:
        print("smoke_test: passed")
        return
    save_checkpoint(Path(config["paths"]["teacher_last_checkpoint"]), model=model, optimizer=optimizer, epoch=epochs, validation_accuracy=history[-1]["validation_accuracy"], config=config)
    write_history(Path(config["paths"]["teacher_history"]), history)


if __name__ == "__main__":
    main()
