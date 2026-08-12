"""Host-side test suite for hardware-independent timer behavior."""

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIRMWARE_ROOT = REPOSITORY_ROOT / "firmware"
sys.path.insert(0, str(FIRMWARE_ROOT))
