# SPDX-License-Identifier: GPL-3.0-only
"""CHIM builder: the world stored once and placed by reference.

CHIM is the world streamer that replaces today's overlapping region maps
(the legacy builder). Every shared model, texture and terrain face is written
once; placements name a shared model. The binary layout is specified in
docs/chim/WORLD_FORMAT.md and implemented in chim.format.
"""
from pathlib import Path as _Path


def _chim_version():
    """CHIM's own version: the CHIM_VERSION file at the repository root (project_version)."""
    import re
    value = (_Path(__file__).resolve().parents[2] / 'CHIM_VERSION').read_text().strip()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', value):
        raise ValueError('CHIM_VERSION must contain one version such as 0.1.0')
    return value


CHIM_VERSION = _chim_version()
FORMAT_VERSION = (0, 5)
BUILDER = 'chim'
