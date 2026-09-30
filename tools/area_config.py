# SPDX-License-Identifier: GPL-3.0-only
"""Public starting-area policy; original placements always come from owned data."""
import json
from pathlib import Path

AREA = json.loads((Path(__file__).resolve().parents[1] / 'config/seyda_area.json').read_text())
BALMORA_INTERIORS = json.loads((Path(__file__).resolve().parents[1] / 'config/balmora_interiors.json').read_text())['scenes']
SCENES = AREA['scenes'] + BALMORA_INTERIORS
MAP_NAMES = {s['cell'].casefold(): s['map'] for s in SCENES}
BOUNDS = AREA['bounds']


def inside(position, padding=0):
    local = [(position[a] - AREA['centre'][a]) * AREA['scale'] for a in range(2)]
    return all(BOUNDS[0][a]-padding <= local[a] <= BOUNDS[1][a]+padding for a in range(2))
