"""Build synthetic training data and fit the event classifier.

Run it directly:

    python -m detectors.train                 # train, evaluate, export
    python -m detectors.train --epochs 60     # train harder

Outputs land in `artifacts/`:

    event_classifier.pt        state_dict, used for federated weight exchange
    event_classifier.ts.pt     TorchScript, used for edge inference
    event_classifier.json      window size, class order, accuracy

The training windows are generated with the exact same anomaly shapes the
synthetic sensor emits (`sensors/synthetic.py`), so what the model learns and
what the demo produces cannot drift apart.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from dataclasses import replace
from pathlib import Path

import torch
from torch import nn

from core.config import PROJECT_ROOT
from core.contracts import EventType
from core.logging_setup import configure_logging
from detectors.model import DEFAULT_WINDOW, EventClassifier, export_torchscript
from sensors.synthetic import ClimateSeries, episode_offsets, get_profile, sample_episode

log = logging.getLogger(__name__)

ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
STATE_DICT_PATH = ARTIFACT_DIR / "event_classifier.pt"
TORCHSCRIPT_PATH = ARTIFACT_DIR / "event_classifier.ts.pt"
METADATA_PATH = ARTIFACT_DIR / "event_classifier.json"

#: Climates the shared model is trained across. Spanning several makes the
#: model rely on window *shape* rather than absolute temperatures.
DEFAULT_TRAIN_PROFILES = ["temperate", "coastal", "arid", "alpine"]


# ---------------------------------------------------------------------------
# Dataset construction
# ---------------------------------------------------------------------------


def build_dataset(
    profile_name: str = "temperate",
    samples_per_class: int = 400,
    window: int = DEFAULT_WINDOW,
    seed: int = 0,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Generate labelled windows for one climate.

    Windows are cut from a single continuous baseline series (sliding by one
    sample) so they share the underlying random walk, exactly as consecutive
    windows do at runtime. An anomaly episode is then overlaid on the tail of
    each non-`NONE` window, ending at the most recent sample -- because that
    is the situation the detector actually faces: an event in progress, seen
    from inside it.

    Returns:
        windows: float32 tensor (N, window, 2)
        labels:  int64 tensor (N,)
    """
    profile = get_profile(profile_name)
    rng = random.Random(seed + 555)
    series = ClimateSeries(profile, seed=seed)

    classes = EventType.ordered()
    order: list[EventType] = []
    for event_type in classes:
        order.extend([event_type] * samples_per_class)
    rng.shuffle(order)

    # One continuous baseline long enough to slide a window across every sample.
    baseline = [series.next() for _ in range(len(order) + window + 1)]

    windows: list[list[list[float]]] = []
    labels: list[int] = []

    for cursor, event_type in enumerate(order):
        chunk = [list(point) for point in baseline[cursor : cursor + window]]

        if event_type is not EventType.NONE:
            episode = sample_episode(rng, event_type)
            span = min(episode.length, window)
            # Re-express the episode over exactly `span` samples so the offset
            # reaches full magnitude on the final sample of the window.
            episode = replace(episode, length=span)
            for step in range(span):
                d_temp, d_humidity = episode_offsets(episode, step)
                index = window - span + step
                chunk[index][0] += d_temp
                chunk[index][1] = min(max(chunk[index][1] + d_humidity, 0.0), 100.0)

        windows.append(chunk)
        labels.append(event_type.index)

    return (
        torch.tensor(windows, dtype=torch.float32),
        torch.tensor(labels, dtype=torch.int64),
    )


def build_multi_profile_dataset(
    profiles: list[str],
    samples_per_class: int = 400,
    window: int = DEFAULT_WINDOW,
    seed: int = 0,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Concatenate datasets from several climates into one training set."""
    all_windows: list[torch.Tensor] = []
    all_labels: list[torch.Tensor] = []
    for offset, profile_name in enumerate(profiles):
        windows, labels = build_dataset(
            profile_name,
            samples_per_class=samples_per_class,
            window=window,
            seed=seed + 100 * offset,
        )
        all_windows.append(windows)
        all_labels.append(labels)
    return torch.cat(all_windows), torch.cat(all_labels)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_model(
    profiles: list[str] | None = None,
    samples_per_class: int = 400,
    window: int = DEFAULT_WINDOW,
    hidden: int = 64,
    epochs: int = 40,
    learning_rate: float = 3e-3,
    batch_size: int = 64,
    validation_fraction: float = 0.2,
    seed: int = 0,
) -> tuple[EventClassifier, dict]:
    """Fit an `EventClassifier` and return it alongside its metrics."""
    torch.manual_seed(seed)
    profiles = profiles or DEFAULT_TRAIN_PROFILES

    windows, labels = build_multi_profile_dataset(
        profiles, samples_per_class=samples_per_class, window=window, seed=seed
    )

    # Shuffle before splitting so validation covers every climate and class.
    permutation = torch.randperm(windows.shape[0], generator=torch.Generator().manual_seed(seed))
    windows, labels = windows[permutation], labels[permutation]

    split = int(windows.shape[0] * (1.0 - validation_fraction))
    train_x, train_y = windows[:split], labels[:split]
    val_x, val_y = windows[split:], labels[split:]

    model = EventClassifier(window=window, hidden=hidden)
    optimiser = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.CrossEntropyLoss()

    log.info(
        "Training on %d windows (%d validation) from %s | %d parameters",
        train_x.shape[0],
        val_x.shape[0],
        ", ".join(profiles),
        model.parameter_count(),
    )

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        batches = 0
        for start in range(0, train_x.shape[0], batch_size):
            batch_x = train_x[start : start + batch_size]
            batch_y = train_y[start : start + batch_size]

            optimiser.zero_grad()
            loss = criterion(model(batch_x), batch_y)
            loss.backward()
            optimiser.step()

            epoch_loss += float(loss.item())
            batches += 1

        if epoch % 10 == 0 or epoch == epochs:
            accuracy = evaluate(model, val_x, val_y)
            log.info(
                "epoch %3d/%d  train_loss=%.4f  val_accuracy=%.3f",
                epoch,
                epochs,
                epoch_loss / max(batches, 1),
                accuracy,
            )

    metrics = {
        "window": window,
        "hidden": hidden,
        "parameters": model.parameter_count(),
        "profiles": profiles,
        "classes": [event.value for event in EventType.ordered()],
        "val_accuracy": evaluate(model, val_x, val_y),
        "per_class_accuracy": per_class_accuracy(model, val_x, val_y),
        "train_windows": int(train_x.shape[0]),
        "val_windows": int(val_x.shape[0]),
    }
    return model, metrics


@torch.no_grad()
def evaluate(model: EventClassifier, windows: torch.Tensor, labels: torch.Tensor) -> float:
    """Overall accuracy on a held-out set."""
    if windows.shape[0] == 0:
        return 0.0
    model.eval()
    predictions = model(windows).argmax(dim=1)
    return float((predictions == labels).float().mean().item())


@torch.no_grad()
def per_class_accuracy(
    model: EventClassifier, windows: torch.Tensor, labels: torch.Tensor
) -> dict[str, float]:
    """Accuracy broken down per event type -- the number that actually matters.

    Overall accuracy can look fine while the model never predicts `drift`.
    """
    model.eval()
    predictions = model(windows).argmax(dim=1)
    result: dict[str, float] = {}
    for event_type in EventType.ordered():
        mask = labels == event_type.index
        total = int(mask.sum().item())
        result[event_type.value] = (
            round(float((predictions[mask] == event_type.index).float().mean().item()), 4)
            if total
            else 0.0
        )
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the WildSense event classifier.")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--samples-per-class", type=int, default=400)
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)

    model, metrics = train_model(
        samples_per_class=args.samples_per_class,
        window=args.window,
        hidden=args.hidden,
        epochs=args.epochs,
        seed=args.seed,
    )

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), STATE_DICT_PATH)
    export_torchscript(model, TORCHSCRIPT_PATH)
    METADATA_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    log.info("Validation accuracy: %.3f", metrics["val_accuracy"])
    for name, accuracy in metrics["per_class_accuracy"].items():
        log.info("  %-6s %.3f", name, accuracy)
    log.info("Saved state_dict  -> %s", STATE_DICT_PATH)
    log.info("Saved TorchScript -> %s", TORCHSCRIPT_PATH)
    log.info("Saved metadata    -> %s", METADATA_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
