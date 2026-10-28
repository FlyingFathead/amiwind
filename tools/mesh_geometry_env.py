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


# How a head or hair shape is reduced when the whole-model bake reduces it (head detail budget, or hair over the
# limit in mode original; NPC-HEAD-DECIMATION-33, decided for the project 18 October 2026): locked (default) is the
# boundary-locked quadric reducer of the static meshes (mold_shell.quadric_simplify with the rim locked, the face
# turn limit static_lod.LOCKED_MAX_TURN), so the reduction opens no new hole in a face; default is the previous
# reducer (fast_simplification, npc_geometry.simplify_shape), byte for byte.
NPC_HEAD_REDUCERS = ('locked', 'default')
NPC_HEAD_REDUCER_VARIABLE = 'AMIWIND_NPC_HEAD_REDUCER'   # read by npc_geometry._bake


def npc_head_reducer(mode=None):
    """The head/hair reducer of the whole-model NPC bake: locked (default) or default (the previous reducer).
    An explicit MODE wins over the environment."""
    if mode is None:
        mode = os.environ.get(NPC_HEAD_REDUCER_VARIABLE, 'locked').strip() or 'locked'
    if mode not in NPC_HEAD_REDUCERS:
        raise ValueError(NPC_HEAD_REDUCER_VARIABLE + ' must be locked or default')
    return mode


def export_npc_head_reducer(mode):
    """Export the resolved npc_head_reducer for every converter worker."""
    os.environ[NPC_HEAD_REDUCER_VARIABLE] = npc_head_reducer(mode)
    return os.environ[NPC_HEAD_REDUCER_VARIABLE]


def export_npc_head_detail(mode):
    """Export the resolved npc_head_detail for every converter worker."""
    os.environ[NPC_HEAD_DETAIL_VARIABLE] = npc_head_detail(mode)
    return os.environ[NPC_HEAD_DETAIL_VARIABLE]


# How the CHIM model builder keeps collision that a convex proxy closes under an authored ceiling
# (CHIM-VOS-TEMPLE-WALKWAY-41, B16; tools/build.py and tools/chim_build.py --collision-underside). names (default):
# the list of mesh names town_regions.UNDERPASS_NAMES keeps all its authored collision surfaces with exact bevels.
# The general rules are EXPERIMENTAL (measured on every exterior mesh, v0.0.42; neither replaces the list yet):
# rule: a convex piece whose hull passes through an authored downward-facing surface of the mesh and fills more
# than mesh_geometry.UNDERSIDE_DEPTH under it becomes the authored plates of its triangles (+33 % standing clip
# nodes over 240 meshes; the Vos walkway step still starts in solid); split: such a piece is split further first,
# plates only where it cannot be; whole: such a mesh keeps all its authored surfaces, as the list does (the Vos
# walkway passes; x2.25 standing clip nodes over 238 meshes). Resolved by the orchestrator into each mesh's
# profile (so it is in every model's unit key).
UNDERSIDE_MODES = ('rule', 'split', 'whole', 'names')
UNDERSIDE_VARIABLE = 'AMIWIND_COLLISION_UNDERSIDE'


def underside_mode():
    mode = os.environ.get(UNDERSIDE_VARIABLE, '').strip() or 'names'
    if mode not in UNDERSIDE_MODES:
        raise ValueError(UNDERSIDE_VARIABLE + ' must be rule, split, whole or names, not %r' % mode)
    return mode


# How the CHIM model builder picks the points of a convex collision piece (mesh_geometry.collision_parts;
# CHIM-VIVEC-DOCK-WALKWAY-43). Every piece's hull is built from its extreme points along 14 directions; on a deck that
# runs level and then slopes (the Vivec docks) that hull lies up to 19 units under the planks. table (default from
# v0.0.43-dev3): the meshes of config/collision-hull-surface.json (measured island-wide: walkable collision more than a
# step under the pieces) keep all the points of a piece whose reduced hull leaves its source surface more than
# mesh_geometry.SURFACE_LOSS outside; every other mesh is built as before (the same unit keys). all: that rule for
# every mesh (measured cost in the bug page). extremes: the method before for every mesh, for A/B tests (the collision
# surface gate then reports without failing). Resolved into each mesh's profile (hull_surface_loss), so it is in
# every model's unit key. From v0.0.46 (CHIM-HULL-SURFACE-HEAP-46) the table meshes hold their WALKABLE surface
# (mesh_geometry.surface_hull: points of that surface added to the reduced hull until it is within SURFACE_LOSS);
# table-whole: the rule as first shipped (the hull of all a piece's points; six v0.0.46-dev1 frames over the CHIM
# zone), kept for A/B tests (profile hull_surface_points 'all').
HULL_POINTS_MODES = ('table', 'all', 'extremes', 'table-whole')
HULL_POINTS_VARIABLE = 'AMIWIND_COLLISION_HULL_POINTS'


def hull_points_mode():
    mode = os.environ.get(HULL_POINTS_VARIABLE, '').strip() or 'table'
    if mode not in HULL_POINTS_MODES:
        raise ValueError(HULL_POINTS_VARIABLE + ' must be table, all, extremes or table-whole, not %r' % mode)
    return mode


# Which meshes the CHIM model builder keeps the standing room over an authored floor open for
# (mesh_geometry.collision_parts standing_room, DOOR-USE-COLLISION-FILLED-53): a convex piece that fills the room a
# player stands in over a floor of the mesh more than mesh_geometry.STANDING_ROOM_DEPTH is split, and a piece that
# cannot be split becomes the authored plates of its triangles (Morrowind collides with the triangles themselves).
# table (default from v0.0.54): the meshes of config/collision-standing-room.json (measured: a door or a walk route
# the rule clears; the Redoran guard tower first, 8 entrances), every other mesh keeps its unit key and bytes; all:
# every mesh, for measurement only (190 of 1,380 meshes change, +1.7 MB of collision island-wide); off: the method
# before. Resolved into each mesh's profile (standing_room), so it is in every model's unit key. A release VERSION
# refuses all and off (refuse_in_release).
STANDING_ROOM_MODES = ('table', 'all', 'off')
STANDING_ROOM_VARIABLE = 'AMIWIND_COLLISION_STANDING_ROOM'


def refuse_in_release(what, mode, default, version=None):
    """A debug-only method (a mode other than DEFAULT) is refused for a release version string (rc or final): a
    shipped build takes the repository's default, never a machine's environment (the public builder builds what we
    ship; DOOR-USE-COLLISION-FILLED-53). No version given: not checked here (the converters never read the version: a
    version change may not re-key the CHIM world); the build entry checks it before any stage (debug_collision_waivers,
    called by the exclusion refusals)."""
    if mode == default or not version:
        return mode
    import re
    # the private-test version rule, inline: importing the module that reads the version file would key every CHIM
    # stage by it
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]+', version.strip()):
        raise ValueError('%s %s is a debug-only method: a release build (version %s) takes the default %s'
                         % (what, mode, version, default))
    return mode


def debug_collision_waivers():
    """The debug-only collision methods this environment selects, as waiver names: the build entry refuses them for
    rc and final builds and lists them for release readiness."""
    out = []
    if standing_room_mode() != 'table':
        out.append('%s=%s' % (STANDING_ROOM_VARIABLE, standing_room_mode()))
    if plate_bevels_mode() != 'mesh':
        out.append('%s=%s' % (PLATE_BEVELS_VARIABLE, plate_bevels_mode()))
    return out


def standing_room_mode(version=None):
    mode = os.environ.get(STANDING_ROOM_VARIABLE, '').strip() or 'table'
    if mode not in STANDING_ROOM_MODES:
        raise ValueError(STANDING_ROOM_VARIABLE + ' must be table, all or off, not %r' % mode)
    return refuse_in_release(STANDING_ROOM_VARIABLE, mode, 'table', version)


from pathlib import Path  # noqa: E402
STANDING_ROOM_TABLE = Path(__file__).resolve().parents[1] / 'config/collision-standing-room.json'


def standing_room_meshes(path=STANDING_ROOM_TABLE):
    """{source path in lower case} of config/collision-standing-room.json (aw-collision-standing-room-1)."""
    import json
    path = Path(path)
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('format') != 'aw-collision-standing-room-1' or not isinstance(data.get('meshes'), dict):
        raise ValueError('%s: format aw-collision-standing-room-1 with a meshes table expected' % path)
    from mesh_tables import tracked      # each cached result keys the rows it reads (BUILD-KEY-MESH-TABLE-WHOLE-54)
    return tracked({k.replace(chr(92), '/').casefold() for k in data['meshes']}, path)


def standing_room_applies(source, mode=None, meshes=None):
    """Whether the standing-room rule is in the profile of the mesh SOURCE under MODE (standing_room_mode)."""
    mode = standing_room_mode() if mode is None else mode
    if mode == 'all':
        return True
    if mode == 'off':
        return False
    return source.replace(chr(92), '/').casefold() in (standing_room_meshes() if meshes is None else meshes)


# Which standing bevels a CHIM model gets when its converter asked for exact bevels on some of its pieces only (the
# plates of the stair rules, steep toes, walkable faces left deep, authored ramps: prepare_mesh_bsp lod
# collision_bevels_pieces; DOOR-USE-COLLISION-FILLED-53). mesh (default from v0.0.54): the whole model takes exact
# bevels (chim.models.variant_unit then compiles its standing hull, checked and patched), as the visible-tread rule
# already asks for; a thin plate with the approximate axial bevels grows its standing hull over the treads beside it
# (COLLISION-STAIR-SLOPE-32): the 24 Daedric shrine entrances' steps (ex_dae_ruin_entry) slid the player off. drop: the
# method before (the positions dropped, approximate bevels unless the whole mesh asked for exact), for A/B tests.
# Part of every model variant's unit key (its exact flag).
PLATE_BEVELS_MODES = ('mesh', 'drop')
PLATE_BEVELS_VARIABLE = 'AMIWIND_COLLISION_PLATE_BEVELS'


def plate_bevels_mode(version=None):
    mode = os.environ.get(PLATE_BEVELS_VARIABLE, '').strip() or 'mesh'
    if mode not in PLATE_BEVELS_MODES:
        raise ValueError(PLATE_BEVELS_VARIABLE + ' must be mesh or drop, not %r' % mode)
    return refuse_in_release(PLATE_BEVELS_VARIABLE, mode, 'mesh', version)
