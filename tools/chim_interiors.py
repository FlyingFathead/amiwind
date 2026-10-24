#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""CHIM rooms: the interior store and the room records of every converted room (tools/chim/interior.py).

    python3 tools/chim_interiors.py --rooms-from DIR [--rooms-from DIR ...] [--room-work DIR ...]
        --palette PALETTE --out OUT [--qbsp QBSP] [--unit-cache DIR] [--jobs N]

tools/build.py runs this as its `chim-interiors` stage (--interior-format chim, the default); the image installs
its output over the final room maps (tools/build_aga.py --chim-interiors). EXPERIMENTAL; see
docs/chim/INTERIOR_STORE.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from chim.interior import main  # noqa: E402

if __name__ == '__main__':
    main()
