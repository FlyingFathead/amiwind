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


# How a listed creature's model is made (its row's "method" in config/interior_creatures.json; DON'T DELETE ANY METHOD):
#   baked     (default) 8 frames of its idle loop (bake_task, the method since v0.0.42)
#   skeletal  one skeletal model on the creature's own animation table (tools/creature_tables.py unit): every group of its text keys plays by name, so MWScript's PlayGroup reaches it (the Heart
#             of Lorkhan's Idle2 to Idle5 and Death1, HEART-OF-LORKHAN-LOOK-62); the idle loops the table's idle span
CREATURE_METHODS = ('baked', 'skeletal')


def method_of(identifier, rows=None):
    """The model method of a listed creature (CREATURE_METHODS); an unlisted one is baked."""
    row = (rows if rows is not None else listed()).get(identifier.casefold()) or {}
    value = row.get('method', 'baked')
    if value not in CREATURE_METHODS:
        raise ValueError('Interior creature %s: method %r, not one of %s' % (identifier, value, ', '.join(CREATURE_METHODS)))
    return value


def biped(fields):
    """CREA FLAG bit 0x01: two-legged (rule from OpenMW file components/esm3/loadcrea.hpp)."""
    from mwad.npc import first
    raw = first(fields, 'FLAG')
    return len(raw) >= 4 and bool(struct.unpack_from('<i', raw, 0)[0] & 0x01)


def idle_layout(layout):
    """(base, count, step) of the 'idle' entry of a kit layout (NAME:BASE:COUNT:STEP[:X] words, npc_anim.layout)."""
    for word in layout.split():
        parts = word.split(':')
        if parts[0] == 'idle' and len(parts) >= 4:
            return int(parts[1]), int(parts[2]), float(parts[3])
    raise ValueError('the layout has no idle group')


def skeletal_task(task):
    """Worker: (identifier, raw skeletal model, record) of one creature resident on its own animation table. The
    record carries '_files' [(game path, bytes)]: the table and the model's layout, written beside the model."""
    import creature_tables
    data, palette, app = task
    _mesh, out, error = creature_tables.unit((app['mesh'], data, palette, bool(app.get('biped')), False))
    if out is None:
        raise ValueError(error)
    rep = out['report']
    model, raw = rep['model'], out['model']
    layout_bytes = (out['layout'] + '\n').encode('ascii')
    files = {'table': (out['table'], rep['table']), 'standing_layout': (layout_bytes, model[:-4] + '.anm')}
    rec = {'triangles': rep.get('faces'), 'table_frames': rep['frames'], 'table': rep['table'],
           'table_bytes': rep['table_bytes'], 'table_groups': len(rep['groups']), 'scaled_bones': rep['scaled_bones'],
           'sha256': rep['model_sha256'], 'table_sha256': rep['table_sha256'],
           'effects_left_out': rep.get('effects_left_out')}
    base, count, step = idle_layout(out['layout'])
    record = {'appearance': {'id': app['id'], 'name': app['name'], 'kind': 'CREA', 'mesh': app['mesh']},
              'greeting': {'text': '', 'voice': ''}, 'method': 'skeletal', 'model': model,
              'step': float(step), 'triangles': int(rec['triangles'] or 0), 'frames': int(rec['table_frames']),
              'idle': {'group': 'idle', 'base': base, 'count': count, 'profile': 'table'},
              # the idle think loops the table's idle span (npc_anim.own_idle_fields: aw_idle_base / count / step)
              'anim': {'skeletal': {'own_idle': {'base': base, 'count': count, 'step': float(step)}}},
              'table': {'path': rec['table'], 'bytes': rec['table_bytes'], 'frames': rec['table_frames'],
                        'groups': rec['table_groups'], 'scaled_bones': rec['scaled_bones'],
                        'sha256': rec['table_sha256']},
              'sha256': rec['sha256'], 'voice_seconds': 0.,
              '_files': [(rec['table'], files['table'][0]), (model[:-4] + '.anm', files['standing_layout'][0])]}
    if rec.get('effects_left_out'):
        record['effects_left_out'] = rec['effects_left_out']
    return app['id'], raw, record


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
            state = initial_state(key, ref['number'])
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
    out = {'id': identifier, 'kind': 'CREA', 'name': text(fields, 'FNAM') or identifier,
           'mesh': normpath(text(fields, 'MODL'))}
    if method_of(identifier) == 'skeletal':
        # only for the skeletal method, so every baked creature's task (and key) stays as before
        out.update(method='skeletal', biped=biped(fields))
    return out


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


def effect_shape(material):
    """The reason a shape is left out of a creature resident's opaque model, or None (HEART-OF-LORKHAN-LOOK-62).
    An MDL skin has no translucency, so two kinds of shape would cover the creature instead of glowing around it:
    - material alpha 0: invisible at rest; the original fades it in with an alpha controller (OpenMW
      components/nifosg/controller.hpp AlphaController on the material alpha): the Heart's rays and glow quads,
      seen only in its death;
    - a translucent shell whose texture scrolls (alpha under 1 with a UV controller, controller.hpp UVController):
      the Heart's fire shield around it.
    Measured over every creature mesh of the three masters (2026-11-10): only the Heart of Lorkhan's shapes are
    either; the translucent bodies that do not scroll (ancestor ghosts, the dwarven specters, the netches) are kept."""
    alpha = float(material.get('alpha', 1.0))
    if alpha <= 0.0:
        return 'invisible at rest (material alpha 0)'
    if alpha < 1.0 and material.get('uv_scroll'):
        return 'translucent scrolling effect shell'
    return None


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
    shapes, textures, effects = [], {}, []
    for i, material in enumerate(materials):
        selected = f0[f0[:, 3] == i, :3]
        if not len(selected):
            continue
        why = effect_shape(material)
        if why:
            effects.append({'shape': material.get('source_shape'), 'triangles': int(len(selected)), 'reason': why})
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
    if profile and profile.get('encoding') == 'shared-vertex':
        # the whole original model, as the gallery bakes it (npc_geometry.shared_vertex_mdl: every triangle on the
        # original vertices, at most 1,999; Dagoth Ur's 2,254 triangles, CREATURE-DAGOTH-UR-ABSENT-52)
        from npc_geometry import shared_vertex_mdl
        frames, faces, uv, skin = shared_vertex_mdl(shapes, materials, textures, palette)
        raw = animated_mdl(frames, faces, uv, skin, vertex_limit=1999)
        budgets = ()
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
    if effects:
        record['effects_left_out'] = effects
    return app['id'], raw, record


def safe_bake(task):
    """Worker: bake_task; with --interior-creatures all a model that fails returns (id, None, error) so
    its references are left out with the error. A listed creature that fails stops the stage."""
    try:
        if task[2].get('method') == 'skeletal':
            return skeletal_task(task)
        return bake_task(task)
    except Exception as error:
        if mode() != 'all':
            raise ValueError('Creature resident %s: %s' % (task[2]['id'], error)) from error
        return task[2]['id'], None, '%s: %s' % (type(error).__name__, error)
