"""Reusable classification training and evaluation loops."""

from __future__ import annotations

import torch
from torch.utils.data import DataLoader


def _accuracy(logits: torch.Tensor, targets: torch.Tensor) -> int:
    return int((logits.argmax(dim=1) == targets).sum().item())


def train_one_epoch(
    model: torch.nn.Module,
    loader: DataLoader,
    criterion: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    scaler: torch.amp.GradScaler,
    device: torch.device,
    *,
    mixed_precision: bool,
    max_batches: int | None = None,
) -> dict[str, float]:
    model.train()
    total_loss = 0.0
    total_correct = 0
    total_samples = 0

    for batch_index, (inputs, targets) in enumerate(loader):
        if max_batches is not None and batch_index >= max_batches:
            break
        inputs = inputs.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(
            device_type=device.type,
            dtype=torch.float16,
            enabled=mixed_precision,
        ):
            logits = model(inputs)
            loss = criterion(logits, targets)

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        batch_size = targets.size(0)
        total_loss += float(loss.item()) * batch_size
        total_correct += _accuracy(logits, targets)
        total_samples += batch_size

    return {
        "loss": total_loss / total_samples,
        "accuracy": total_correct / total_samples,
    }


@torch.inference_mode()
def evaluate(
    model: torch.nn.Module,
    loader: DataLoader,
    criterion: torch.nn.Module,
    device: torch.device,
    *,
    mixed_precision: bool,
    max_batches: int | None = None,
) -> dict[str, float]:
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total_samples = 0

    for batch_index, (inputs, targets) in enumerate(loader):
        if max_batches is not None and batch_index >= max_batches:
            break
        inputs = inputs.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        with torch.autocast(
            device_type=device.type,
            dtype=torch.float16,
            enabled=mixed_precision,
        ):
            logits = model(inputs)
            loss = criterion(logits, targets)

        batch_size = targets.size(0)
        total_loss += float(loss.item()) * batch_size
        total_correct += _accuracy(logits, targets)
        total_samples += batch_size

    return {
        "loss": total_loss / total_samples,
        "accuracy": total_correct / total_samples,
    }

