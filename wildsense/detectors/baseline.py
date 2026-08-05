"""Rolling statistical baseline: exponentially weighted mean and variance.

This is the "no hardcoded thresholds" half of the detector. Instead of asking
"is the temperature above 35 C?", we ask "is this reading far from what this
particular sensor has been reporting *lately*?".

The consequence is the intended one: 34 C is unremarkable in a desert whose
baseline sits at 33, and alarming on a mountain whose baseline sits at 6. The
same code, with no per-site tuning, does the right thing in both places.

Why exponentially weighted rather than a plain sliding window:
  * O(1) memory and O(1) update -- it is two floats, which matters on a Pi
  * it forgets smoothly instead of a value abruptly falling out of a window
  * `alpha` is a single, physically meaningful knob (how fast to forget)
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class EwmaBaseline:
    """Tracks an exponentially weighted mean and variance of a scalar stream.

    Update rule (West's incremental form of the EWMA variance):

        diff = x - mean
        incr = alpha * diff
        mean = mean + incr
        var  = (1 - alpha) * (var + diff * incr)

    Args:
        alpha: forgetting factor in (0, 1]. Larger adapts faster. The rough
            equivalent window length is `2 / alpha - 1` samples, so alpha=0.05
            behaves like a ~39-sample window.
        min_std: floor on the standard deviation used for z-scores. This is
            the guard that stops the detector from screaming at sensor
            quantisation noise: early on, or during a very flat stretch, the
            measured variance approaches zero and every z-score would explode.
            Set it to roughly the sensor's resolution.
        clip_z: winsorising limit, in standard deviations, on how far a single
            observation may move the baseline. See `observe` -- this is what
            stops an anomaly from poisoning the statistics used to detect it.
            Set to `None` to disable.
    """

    alpha: float = 0.05
    min_std: float = 0.15
    clip_z: float | None = 4.0

    mean: float = 0.0
    var: float = 0.0
    count: int = 0

    def __post_init__(self) -> None:
        if not 0.0 < self.alpha <= 1.0:
            raise ValueError(f"alpha must be in (0, 1], got {self.alpha}")
        if self.min_std <= 0.0:
            raise ValueError(f"min_std must be positive, got {self.min_std}")
        if self.clip_z is not None and self.clip_z <= 0.0:
            raise ValueError(f"clip_z must be positive or None, got {self.clip_z}")

    @property
    def std(self) -> float:
        """Standard deviation, floored at `min_std`."""
        return max(math.sqrt(max(self.var, 0.0)), self.min_std)

    def z_score(self, value: float) -> float:
        """How many standard deviations `value` sits from the current baseline.

        Does NOT mutate state, so it is safe to call for reporting.
        Returns 0.0 before any observation, since "far from nothing" is
        meaningless.
        """
        if self.count == 0:
            return 0.0
        return (value - self.mean) / self.std

    def observe(self, value: float) -> float:
        """Fold `value` into the baseline and return its z-score.

        Two things make this correct rather than merely plausible:

        1. The returned z-score is computed against the baseline *before* this
           value is absorbed. Scoring a reading against a baseline that already
           contains it would drag the mean toward the anomaly and
           systematically understate how extreme it was.

        2. The baseline update is **winsorised**: the observation's influence
           is capped at `clip_z` standard deviations, while the *returned*
           z-score is left untouched. Without this, one 10 °C spike lands a
           `diff**2` term of 100 in the variance recursion and inflates the
           standard deviation by more than an order of magnitude, for a
           hundred-plus samples -- during which the detector is effectively
           blind to everything that follows. The anomaly would poison the very
           statistics used to detect it. Clipping keeps detection at full
           sensitivity while bounding how much any single reading can move the
           baseline; a genuine regime change still migrates the mean, it just
           takes several samples rather than one.
        """
        if self.count == 0:
            self.mean = float(value)
            self.var = 0.0
            self.count = 1
            return 0.0

        z = self.z_score(value)

        diff = float(value) - self.mean
        if self.clip_z is not None:
            limit = self.clip_z * self.std
            diff = max(-limit, min(limit, diff))

        incr = self.alpha * diff
        self.mean += incr
        self.var = (1.0 - self.alpha) * (self.var + diff * incr)
        self.count += 1
        return z

    def reset(self) -> None:
        self.mean = 0.0
        self.var = 0.0
        self.count = 0

    def snapshot(self) -> dict[str, float]:
        """Current state, for the dashboard and for debugging."""
        return {
            "mean": round(self.mean, 3),
            "std": round(self.std, 3),
            "count": self.count,
        }
