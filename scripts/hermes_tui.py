#!/usr/bin/env python3
"""Launcher para a TUI do Hermes Coach."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ui.app import run

if __name__ == "__main__":
    run()
