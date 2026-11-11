# SPDX-License-Identifier: GPL-3.0-only
"""The hollow bevels setting (--chim-hollow-bevels, AMIWIND_HOLLOW_BEVELS; COLLISION-WORLDWIDE-REDUCTION-64).

A module of its own (BUILD-UNIT-KEYS-REACH-64): in tools/mesh_geometry_env.py its top-level constants were
import-time code of that module, so they entered the unit key of every bake that imports it (the NPC appearances,
creatures, the player view and its parts, the residents), and its setting name entered their keyed settings,
although none of them reads the hollow bevels. Only the code that calls hollow_bevels_default reaches it here.
"""
import os

HOLLOW_BEVELS_VARIABLE = 'AMIWIND_HOLLOW_BEVELS'
HOLLOW_BEVELS = (0, 1, 2)


def hollow_bevels_default():
    """The standing bevels of every hollow model's collision plates unless a room says otherwise
    (COLLISION-WORLDWIDE-REDUCTION-64; the maintainer's decision of 2026-11-10: approximate, as every solid model):
    the builder option --chim-hollow-bevels (exported as AMIWIND_HOLLOW_BEVELS), else config/chim-rooms.json
    "hollow_bevels" (2), else 2. 0 = exact on every plate (the method up to v0.0.64-dev4), 1 = exact on the
    near-horizontal plates only, 2 = approximate everywhere."""
    text = os.environ.get(HOLLOW_BEVELS_VARIABLE, '').strip()
    if text:
        value = int(text) if text.isdigit() else -1
    else:
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / 'config/chim-rooms.json'
        value = json.loads(path.read_text(encoding='utf-8')).get('hollow_bevels', 2) if path.is_file() else 2
    if value not in HOLLOW_BEVELS:
        raise ValueError('hollow bevels must be 0, 1 or 2 (%s or config/chim-rooms.json hollow_bevels)'
                         % HOLLOW_BEVELS_VARIABLE)
    return value


def export_hollow_bevels(value):
    """Export the builder option --chim-hollow-bevels for every converter worker (None: the config's default)."""
    if value is None:
        os.environ.pop(HOLLOW_BEVELS_VARIABLE, None)
        return hollow_bevels_default()
    if int(value) not in HOLLOW_BEVELS:
        raise ValueError('--chim-hollow-bevels must be 0, 1 or 2')
    os.environ[HOLLOW_BEVELS_VARIABLE] = str(int(value))
    return int(value)
