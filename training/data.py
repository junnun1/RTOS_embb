"""Dataset and DataLoader construction for image classification."""

from __future__ import annotations

import random

import numpy as np
import torch
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

CIFAR10_MEAN = (0.4914, 0.4822, 0.4465)
CIFAR10_STD = (0.2470, 0.2435, 0.2616)


def _seed_worker(worker_id: int) -> None:
    del worker_id
    worker_seed = torch.initial_seed() % (2**32)
    np.random.seed(worker_seed)
    random.seed(worker_seed)


def build_cifar10_loaders(
    config: dict,
    *,
    download: bool = False,
) -> tuple[DataLoader, DataLoader]:
    """Create reproducible CIFAR-10 training and validation loaders."""
    dataset_config = config["dataset"]
    training_config = config["training"]
    input_size = int(dataset_config["input_size"])

    train_transform = transforms.Compose(
        [
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.Resize((input_size, input_size), antialias=True),
            transforms.ToTensor(),
            transforms.Normalize(CIFAR10_MEAN, CIFAR10_STD),
        ]
    )
    validation_transform = transforms.Compose(
        [
            transforms.Resize((input_size, input_size), antialias=True),
            transforms.ToTensor(),
            transforms.Normalize(CIFAR10_MEAN, CIFAR10_STD),
        ]
    )

    class ConfiguredCIFAR10(datasets.CIFAR10):
        pass

    if dataset_config.get("download_url"):
        ConfiguredCIFAR10.url = str(dataset_config["download_url"])

    root = dataset_config["root"]
    train_dataset = ConfiguredCIFAR10(
        root=root,
        train=True,
        transform=train_transform,
        download=download,
    )
    validation_dataset = ConfiguredCIFAR10(
        root=root,
        train=False,
        transform=validation_transform,
        download=download,
    )

    seed = int(config["project"]["seed"])
    generator = torch.Generator().manual_seed(seed)
    common_loader_args = {
        "batch_size": int(training_config["batch_size"]),
        "num_workers": int(dataset_config.get("num_workers", 0)),
        "pin_memory": torch.cuda.is_available(),
        "worker_init_fn": _seed_worker,
        "generator": generator,
        "persistent_workers": int(dataset_config.get("num_workers", 0)) > 0,
    }

    train_loader = DataLoader(
        train_dataset,
        shuffle=True,
        **common_loader_args,
    )
    validation_loader = DataLoader(
        validation_dataset,
        shuffle=False,
        **common_loader_args,
    )
    return train_loader, validation_loader
