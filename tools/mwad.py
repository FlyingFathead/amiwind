#!/usr/bin/env python3
"""Run directly from a source checkout without installing a package."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mwad.cli import main

if __name__ == "__main__":
    main()
