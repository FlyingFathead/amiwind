# SPDX-License-Identifier: GPL-3.0-only
"""The stair rule setting shared by the builder, every converter and the image step.

follow_original_stair_rules (config/build-defaults.json, true by default;
--follow-original-stair-rules / --no-follow-original-stair-rules) is resolved
once by tools/build.py and exported as AMIWIND_STAIR_MITIGATION, which worker
processes inherit:

- on (default): mesh_geometry.mitigate_stairs replaces convex proxies that bury
  stair treads with the authored surface plates (clip ramp past the plate
  budget), and the image step runs the stair walkability gate (stair_walk).
- ramps: the cheapest variant, a walkable clip ramp wherever possible (a
  measurement aid; not a build default).
- off: debugging builds only; the proxy is kept and the gate is skipped.

The model hull setting (model_hull, config/build-defaults.json, auto by default;
--model-hull auto|chain|routed) is exported the same way as AMIWIND_MODEL_HULL:
how a placed model's standing hull is written when it is not compiled by qbsp
(routed_hull): auto routes models above routed_hull.ROUTE_PIECES convex pieces
(nested routing in x, y and z), chain keeps every piece in one chain (the
converters' form before INTERIOR-HULL-CHAIN-33), routed routes every model,
balanced is the first routing (parts by piece counts, xy cuts).

Kept free of numpy/scipy so the builder can import it before any converter.
"""
import os

MODES = ('on', 'ramps', 'off')
VARIABLE = 'AMIWIND_STAIR_MITIGATION'


def stair_mode():
    mode = os.environ.get(VARIABLE, 'on').strip() or 'on'
    if mode not in MODES:
        raise ValueError(VARIABLE + ' must be on, ramps or off')
    return mode


def stair_rules_enabled():
    return stair_mode() != 'off'


def export_stair_rules(follow):
    """Export the resolved follow_original_stair_rules; an explicit 'ramps'
    measurement setting survives a true value."""
    if not follow:
        os.environ[VARIABLE] = 'off'
    elif os.environ.get(VARIABLE, '').strip() != 'ramps':
        os.environ[VARIABLE] = 'on'
    return stair_mode()


MODEL_HULLS = ('auto', 'chain', 'routed', 'balanced', 'compiled')
CHIM_STREAM_VARIABLE = 'AMIWIND_CHIM_STREAM_STATICS'   # read by chim.frame_map.stream_enabled


def export_chim_stream_statics(enabled):
    """Export the resolved chim_stream_statics (frame maps tag their statics to stream with their chunks)."""
    os.environ[CHIM_STREAM_VARIABLE] = '1' if enabled else '0'
    return bool(enabled)
MODEL_HULL_VARIABLE = 'AMIWIND_MODEL_HULL'


def model_hull_mode():
    mode = os.environ.get(MODEL_HULL_VARIABLE, 'auto').strip() or 'auto'
    if mode not in MODEL_HULLS:
        raise ValueError(MODEL_HULL_VARIABLE + ' must be auto, chain, routed, balanced or compiled')
    return mode


from contextlib import contextmanager


@contextmanager
def model_hull_override(mode):
    """Convert with another model hull mode inside the block (one map's retry), then restore the setting.
    A map whose routed hulls go past its clipnode reserve is converted again with chains
    (BUILD-ROUTED-FLORA-RESERVE-33): routing never costs a map its admission."""
    before = os.environ.get(MODEL_HULL_VARIABLE)
    os.environ[MODEL_HULL_VARIABLE] = mode
    try:
        yield mode
    finally:
        if before is None:
            os.environ.pop(MODEL_HULL_VARIABLE, None)
        else:
            os.environ[MODEL_HULL_VARIABLE] = before


def export_model_hull(mode):
    """Export the resolved model_hull for every converter worker."""
    if mode not in MODEL_HULLS:
        raise ValueError('model_hull must be auto, chain, routed, balanced or compiled')
    os.environ[MODEL_HULL_VARIABLE] = mode
    return mode


NPC_HEAD_DETAILS = ('original', 'budget')
NPC_HEAD_DETAIL_VARIABLE = 'AMIWIND_NPC_HEAD_DETAIL'   # read by npc_geometry.head_plan / bake


def npc_head_detail(mode=None):
    """Humanoid head geometry in whole-model NPC bakes (npc_geometry.head_plan): original
    (default: head and hair/helmet keep every original triangle) or budget (the previous
    480-triangle split that decimated heads). An explicit MODE wins over the environment."""
    if mode is None:
        mode = os.environ.get(NPC_HEAD_DETAIL_VARIABLE, 'original').strip() or 'original'
    if mode not in NPC_HEAD_DETAILS:
        raise ValueError(NPC_HEAD_DETAIL_VARIABLE + ' must be original or budget')
    return mode


def export_npc_head_detail(mode):
    """Export the resolved npc_head_detail for every converter worker."""
    os.environ[NPC_HEAD_DETAIL_VARIABLE] = npc_head_detail(mode)
    return os.environ[NPC_HEAD_DETAIL_VARIABLE]
