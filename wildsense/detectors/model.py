"""The compact event classifier -- a small MLP over a sliding window.

Role in the system: the statistical baseline (`baseline.py`) decides *whether*
something happened; this model decides *what kind* of thing happened and how
confident we are. They are complementary, and the split is what lets the
detector degrade gracefully -- with no model file present the statistics still
work, they just fall back to a coarser rule for the event type.

Design constraints, all driven by "must run comfortably on a Pi CPU":

  * ~6.5K parameters. Inference is well under a millisecond on a Pi 4.
  * Feature normalisation happens *inside* `forward`, so the TorchScript
    export is a complete, self-contained artifact: hand it a raw window of
    readings and it hands back logits. Nothing to reimplement at the edge.
  * Per-window standardisation makes the model climate-agnostic. It sees the
    *shape* of the last N readings, not their absolute values, so a model
    trained on desert nodes transfers to alpine ones. That property is also
    exactly what makes federated averaging across dissimilar nodes coherent.
"""

from __future__ import annotations

from pathlib import Path

import torch
from torch import nn

from core.contracts import EventType

#: Number of readings in the sliding window fed to the model.
DEFAULT_WINDOW = 32
#: Channels per reading: temperature, humidity.
CHANNELS = 2
#: Output classes, in `EventType.ordered()` order.
NUM_CLASSES = 4


class EventClassifier(nn.Module):
    """Classifies a window of readings as none / spike / drop / drift.

    Input:  float tensor of shape (batch, window, 2) -- raw temperature and
            humidity, in physical units, oldest sample first.
    Output: float tensor of shape (batch, 4) -- unnormalised logits.
    """

    def __init__(self, window: int = DEFAULT_WINDOW, hidden: int = 64) -> None:
        super().__init__()
        self.window = int(window)
        self.hidden = int(hidden)
        # Held as an instance attribute rather than read from the module-level
        # constant: TorchScript cannot close over a global int, so referencing
        # CHANNELS directly inside forward() breaks the export.
        self.channels = CHANNELS

        # Two standardised series (window each) plus one magnitude scalar per
        # channel. The magnitude features are what separate "flat and quiet"
        # from "flat-looking after normalisation but actually violent".
        in_features = self.channels * self.window + self.channels

        self.net = nn.Sequential(
            nn.Linear(in_features, self.hidden),
            nn.ReLU(),
            nn.Linear(self.hidden, self.hidden // 2),
            nn.ReLU(),
            nn.Linear(self.hidden // 2, NUM_CLASSES),
        )

    def forward(self, window: torch.Tensor) -> torch.Tensor:
        # Standardise each channel within the window. Variance is computed
        # explicitly rather than via Tensor.std so this stays trivially
        # scriptable across torch versions.
        mean = window.mean(dim=1, keepdim=True)  # (B, 1, 2)
        centred = window - mean
        var = (centred * centred).mean(dim=1, keepdim=True)
        std = torch.sqrt(var + 1e-8)  # (B, 1, 2)
        normalised = centred / std.clamp(min=1e-3)

        # (B, W, 2) -> (B, 2, W) -> (B, 2*W): temperature series, then humidity.
        batch = window.shape[0]
        flat = normalised.permute(0, 2, 1).reshape(batch, self.channels * self.window)

        # log1p keeps the magnitude feature on a sane scale: a quiet window
        # (std ~0.2) maps to ~0.18, a spiking one (std ~3.0) to ~1.39.
        magnitude = torch.log1p(std.reshape(batch, self.channels))

        return self.net(torch.cat([flat, magnitude], dim=1))

    # -- convenience -------------------------------------------------------

    @torch.no_grad()
    def predict(self, window: torch.Tensor) -> tuple[EventType, float]:
        """Classify a single window, returning (event type, confidence).

        Accepts either (window, 2) or (1, window, 2).
        """
        self.eval()
        if window.dim() == 2:
            window = window.unsqueeze(0)
        probabilities = torch.softmax(self(window), dim=1)[0]
        index = int(torch.argmax(probabilities).item())
        return EventType.from_index(index), float(probabilities[index].item())

    def parameter_count(self) -> int:
        return sum(p.numel() for p in self.parameters())


def export_torchscript(model: EventClassifier, path: str | Path) -> Path:
    """Serialise the model to TorchScript for lightweight edge inference.

    TorchScript rather than ONNX on purpose: it needs no runtime beyond the
    torch already required for training, which keeps the Pi's dependency list
    one package shorter.

    Note: `torch.jit.script` emits a DeprecationWarning on torch >= 2.13. It
    still works and remains the lightest option for this model, but the
    migration path when it is finally removed is `torch.export` (or ONNX via
    `torch.onnx.export`, at the cost of adding onnxruntime to the Pi). The
    export is self-contained either way, because normalisation lives inside
    `EventClassifier.forward`.
    """
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    model.eval()
    scripted = torch.jit.script(model)
    scripted.save(str(destination))
    return destination


def load_torchscript(path: str | Path) -> torch.jit.ScriptModule:
    """Load a TorchScript artifact for inference on CPU."""
    module = torch.jit.load(str(path), map_location="cpu")
    module.eval()
    return module
