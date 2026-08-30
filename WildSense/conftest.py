"""pytest configuration.

Puts the project root on `sys.path` so the tests import the same top-level
packages (`core`, `sensors`, `detectors`, ...) that `run.py` does, regardless
of the directory pytest was started from.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
