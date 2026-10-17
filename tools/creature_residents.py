# SPDX-License-Identifier: GPL-3.0-only
"""Interior creatures in the resident stage (INTERIOR-CREATURES-MISSING-41).

The resident stage (tools/prepare_area.py populate) was written for humanoid NPC records. A creature
record (CREA) has its own model, skeleton and animation in one NIF and no race or body parts, so it
needs its own bake. This module decides which interior creature references the stage places and
bakes their models; every reference it leaves out is returned with its reason, so the stage's report
lists it (nothing is dropped silently).

Modes (--interior-creatures, environment AMIWIND_INTERIOR_CREATURES; part of the stage keys):
  listed  (default) the creatures listed in config/interior_creatures.json (Vivec first)
  all     every interior creature reference that the grounding policy classifies and whose model
          bakes; experimental, labelled so, every other one left out with its reason
  off     no creature (the method before v0.0.42)

Behaviour is not invented: a placed creature is an idle actor like the placed NPCs (the same aw_npc
entity, no combat, no dialogue). Its support state comes from the grounding policy
(config/actor_grounding.json): a class there, never a rule written for one ID in code.

The model: the creature's own NIF posed on its own skeleton (its text keys and keyframes), 8 frames
over one loop of its idle group, at the original scale, NOT moved to the floor: the height the
animation gives the body above the reference point is kept (Vivec's crossed-leg idle holds him above
the floor). The idle group and its range come from the gallery profile of the model
(config/gallery_model_quality.json "pose_event", e.g. "idle2: loop start") or else the 'idle' group.
"""
import hashlib
import json
import os
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config/interior_creatures.json'
ENV = 'AMIWIND_INTERIOR_CREATURES'
MODES = ('listed', 'all', 'off')
DEFAULT_MODE = 'listed'
FRAMES = 8                       # aw_npc_idle (engine/aga/qc/world.qc) steps through frames 0-7
BUDGETS = (480, 384, 320, 256, 192)


def mode():
    value = os.environ.get(ENV, '').strip() or DEFAULT_MODE
    if value not in MODES:
        raise ValueError('%s takes %s, not %r' % (ENV, ', '.join(MODES), value))
    return value


def add_option(parser):
    parser.add_argument('--interior-creatures', choices=MODES, default=DEFAULT_MODE,
                        help='Creatures in converted interiors (INTERIOR-CREATURES-MISSING-41): listed (default: '
                             'config/interior_creatures.json, Vivec first), all (experimental: every creature the '
                             'grounding policy classifies) or off (no creature: the method before v0.0.42). '
                             'Part of the resident stages\' cache keys (AMIWIND_INTERIOR_CREATURES)')
    return parser


def listed():
    report = json.loads(CONFIG.read_text())
    if report.get('format') != 1:
        raise ValueError('Unknown interior creature list format: ' + str(CONFIG))
    rows = {}
    for key, row in report['creatures'].items():
        if not row.get('reason') or not row.get('source'):
            raise ValueError('Interior creature %s: a listed creature needs a reason and a source' % key)
        rows[key.casefold()] = row
    return rows


def initially_dead(fields):
    """CREA NPDT (96 bytes): type, level, 8 attributes, then health (int32 at byte 40)."""
    from mwad.npc import first
    raw = first(fields, 'NPDT')
    return len(raw) == 96 and struct.unpack_from('<i', raw, 40)[0] <= 0


def select(refs, kinds, slug, selection=None):
    """(placed, left_out) creature references of one room.

    refs: the room's references (mwad.interior); kinds: mwad.npc.load_master kinds. placed: the
    CREA references to bake and place; left_out: {map, reference, id, type, reason} rows for every
    creature or levelled-creature reference not placed."""
    from actor_grounding import initial_state
    selection = selection or mode()
    names = listed() if selection == 'listed' else {}
    placed, left = [], []

    def leave(ref, reason):
        left.append({'map': slug, 'reference': ref['number'], 'id': ref['id'], 'type': ref['type'], 'reason': reason})
    for ref in refs:
        if ref['type'] not in ('CREA', 'LEVC'):
            continue
        key = ref['id'].casefold()
        if ref.get('deleted'):
            leave(ref, 'deleted in the master'); continue
        if ref['type'] == 'LEVC':
            leave(ref, 'levelled creature list: the pick is not resolved at build time (no invented roll)'); continue
        if selection == 'off':
            leave(ref, 'creatures off (--interior-creatures off)'); continue
        if selection == 'listed' and key not in names:
            leave(ref, 'not listed in config/interior_creatures.json (--interior-creatures listed)'); continue
        fields = kinds['CREA'].get(key)
        if fields is None:
            leave(ref, 'no creature record in the base master'); continue
        if abs(ref.get('scale', 1.) - 1) > 1e-5:
            leave(ref, 'instance scale %.3f needs its own bake' % ref['scale']); continue
        if initially_dead(fields):
            leave(ref, 'authored dead creature: no creature death pose bake yet'); continue
        try:
            state = initial_state(key)
        except ValueError as error:
            if selection == 'listed':
                raise ValueError('Listed interior creature %s: %s' % (key, error)) from error
            leave(ref, 'no grounding classification in config/actor_grounding.json'); continue
        if state == 'authored_dead':
            leave(ref, 'classified authored_dead: no creature death pose bake yet'); continue
        placed.append(ref)
    return placed, left


def appearance(kinds, identifier):
    from mwad.npc import text
    from mwad.audit import normpath
    fields = kinds['CREA'][identifier]
    return {'id': identifier, 'kind': 'CREA', 'name': text(fields, 'FNAM') or identifier,
            'mesh': normpath(text(fields, 'MODL'))}


def idle_range(skeleton, profile):
    """(group, start, stop) of the loop to sample: the profile's pose event group, else 'idle'."""
    group = 'idle'
    if profile and profile.get('pose_event'):
        group = profile['pose_event'].split(':', 1)[0].strip().casefold()
    events = skeleton.events
    for a, b in (('%s: loop start' % group, '%s: loop stop' % group), ('%s: start' % group, '%s: stop' % group)):
        if a in events and b in events and events[b] > events[a]:
            return group, float(events[a]), float(events[b])
    raise ValueError('no %s animation range in the model\'s text keys' % group)


_assets = {}


def bake_task(task):
    """Worker: (identifier, raw mdl, record) of one creature resident."""
    import numpy as np
    from mwad.audit import BSA, normpath
    from mwad.paths import child_ci
    from mwad.scene import unpack_geometry
    from npc_geometry import Assets, Skeleton, bake, animated_mdl
    from prepare_scenery import model_geometry, nif_reader
    from prepare_gallery import quality_profiles
    data, palette, app = task
    key = str(Path(data).resolve())
    if key not in _assets:
        _assets[key] = Assets(Path(data), BSA(child_ci(Path(data), 'Morrowind.bsa')))
    assets = _assets[key]
    mesh = 'meshes/' + app['mesh']
    profile = quality_profiles().get(normpath(app['mesh']))
    skeleton = Skeleton(assets, normpath(mesh))
    group, start, stop = idle_range(skeleton, profile)
    times = np.linspace(start, stop, FRAMES, endpoint=False)
    raw_nif = assets.read(normpath(mesh)); reader = nif_reader()
    per_frame = []
    for t in times:
        packet, materials, _bounds, skipped = model_geometry(raw_nif, reader, repair_uv=True,
                                                             pose_world=skeleton.pose(float(t)))
        vertices, faces, _ = unpack_geometry(packet)
        per_frame.append((np.array(vertices), np.array(faces, dtype=int), materials))
    v0, f0, materials = per_frame[0]
    for v, f, _ in per_frame[1:]:
        if v.shape != v0.shape or not np.array_equal(f, f0):
            raise ValueError('posed frames do not share one topology')
    shapes, textures = [], {}
    for i, material in enumerate(materials):
        selected = f0[f0[:, 3] == i, :3]
        if not len(selected):
            continue
        source = material.pop('texture_source'); material['texture_index'] = source
        if source and source not in textures:
            textures[source] = assets.texture(source)
        used, remap = np.unique(selected, return_inverse=True)
        # Morrowind units to Quake units (0.25), every frame; the source origin is kept (no floor shift).
        positions = np.stack([v[used, :3] * .25 for v, _, _ in per_frame])
        shapes.append(dict(name=material['source_shape'], part=-1, positions=positions,
                           faces=remap.reshape(-1, 3), uv=v0[used, 3:5], colours=v0[used, 5:9] / 255, material=i))
    if not shapes:
        raise ValueError('no visible geometry')
    budgets = (profile['budget'],) if profile else BUDGETS
    for budget in budgets:
        try:
            frames, faces, uv, skin = bake(shapes, materials, textures, palette, budget=budget,
                                           minimum_faces=(profile or {}).get('minimum_faces') or None)
            raw = animated_mdl(frames, faces, uv, skin)
            break
        except ValueError as error:
            if 'Alias' not in str(error) or budget == budgets[-1]:
                raise
    low = frames.min((0, 1)); high = frames.max((0, 1))
    record = {'appearance': {'id': app['id'], 'name': app['name'], 'kind': 'CREA', 'mesh': app['mesh']},
              'greeting': {'text': '', 'voice': ''},
              'step': float((stop - start) / FRAMES), 'triangles': len(faces), 'frames': len(frames),
              'bounds': [low.tolist(), high.tolist()],
              'idle': {'group': group, 'start': start, 'stop': stop,
                       'profile': (profile or {}).get('id', 'default')},
              # the lowest point of the posed body above the reference point (Quake units): Vivec's float
              'lift': float(low[2]),
              'sha256': hashlib.sha256(raw).hexdigest(), 'voice_seconds': 0.}
    return app['id'], raw, record


def safe_bake(task):
    """Worker: bake_task; with --interior-creatures all a model that fails returns (id, None, error) so
    its references are left out with the error. A listed creature that fails stops the stage."""
    try:
        return bake_task(task)
    except Exception as error:
        if mode() != 'all':
            raise ValueError('Creature resident %s: %s' % (task[2]['id'], error)) from error
        return task[2]['id'], None, '%s: %s' % (type(error).__name__, error)
