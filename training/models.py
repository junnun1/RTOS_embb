"""Model construction helpers for deployment-oriented image classifiers."""

from __future__ import annotations

import torch.nn as nn
from torchvision.models import MobileNet_V2_Weights, mobilenet_v2


def build_mobilenet_v2(
    *,
    num_classes: int,
    pretrained: bool = True,
    weights_name: str = "IMAGENET1K_V2",
    width_mult: float = 1.0,
    dropout: float = 0.2,
) -> nn.Module:
    """Build MobileNetV2 and replace its ImageNet classifier."""
    if num_classes <= 0:
        raise ValueError("num_classes must be positive")

    try:
        weights = MobileNet_V2_Weights[weights_name] if pretrained else None
    except KeyError as exc:
        supported = ", ".join(weight.name for weight in MobileNet_V2_Weights)
        raise ValueError(
            f"Unsupported MobileNetV2 weights: {weights_name}. "
            f"Available weights: {supported}"
        ) from exc
    model = mobilenet_v2(
        weights=weights,
        width_mult=width_mult,
        dropout=dropout,
    )

    input_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(input_features, num_classes)
    return model


def build_model(config: dict) -> nn.Module:
    """Build the model selected by a project configuration."""
    model_config = config["model"]
    dataset_config = config["dataset"]

    if model_config["name"] != "mobilenet_v2":
        raise ValueError(f"Unsupported model: {model_config['name']}")

    return build_mobilenet_v2(
        num_classes=int(dataset_config["num_classes"]),
        pretrained=bool(model_config.get("pretrained", True)),
        weights_name=str(model_config.get("weights", "IMAGENET1K_V2")),
        width_mult=float(model_config.get("width_mult", 1.0)),
        dropout=float(model_config.get("dropout", 0.2)),
    )
