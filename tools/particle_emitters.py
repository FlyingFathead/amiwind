#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The particle emitters the original meshes carry, swept over the user's own game data (MESH-PARTICLE-EMITTERS).

Morrowind draws chimney and campfire smoke, steam vents, torch and brazier flames, waterfall spray, blight clouds
and the like with NiParticleSystemController emitters inside the placed meshes. AmiWind draws the flames (aw_flame
rows: tools/prepare_scenery.model_flames, tools/chim/flames.py) and leaves every other emitter out
(prepare_scenery.FLAME_SKIP, chim.flames.NOT_FIRE_MESH). Before any of them is drawn (the maintainer, 27 October
2026: "it could be a shit simple sprite thing"), this sweep says what there is: every placed mesh with an emitter,
each emitter's kind (from its node, mesh and particle texture names), its particle texture, size, rise and birth
rate, and how often the mesh is placed outdoors and indoors.

    python3 tools/particle_emitters.py sweep --data-files DIR [--json OUT] [--jobs N]

Read only; the output names game files and stays private (a public doc summarises counts only).
"""
import argparse
from collections import Counter, defaultdict
import io
import json
from pathlib import Path
import struct
import sys

_HERE = Path(__file__).resolve().parent          # tools/ (an import path, never a data read: test_build_cache)
if str(_HERE) not in sys.path:
    sys.path.append(str(_HERE))
sys.path.insert(0, str(_HERE.parent / 'src'))    # the mwad package before tools/mwad.py

from mwad.audit import BSA, normpath, records, string, subrecords  # noqa: E402
from mwad.esm import GAME_ARCHIVES, GAME_MASTERS, is_deleted  # noqa: E402
from mwad.paths import child_ci  # noqa: E402

# The particle texture says best what an emitter draws (a fire's "SuperSpray01" emitter draws tx_firealpha10, its
# "ash" emitter the fire's own ash, tx_fireash00): texture words first, in this order, then the emitter's node name,
# then the mesh's, with KINDS. 'fire' are the ones AmiWind already draws (aw_flame rows).
TEXTURE_KINDS = (
    ('smoke', ('smoke',)),
    ('fire ash', ('fireash',)),
    ('spark', ('spark',)),
    ('fire', ('firealpha', 'flame')),
    ('steam', ('steam',)),
    ('spray', ('waterfall', 'spray', 'water')),
    ('lava', ('lava',)),
    ('blight', ('blight',)),
    ('mist', ('mist', 'fog', 'dust')),
    ('bubble', ('bubble',)),
)
KINDS = (
    ('smoke', ('smoke', 'chimney')),
    ('steam', ('steam', 'vent', 'geyser')),
    ('spray', ('spray', 'splash', 'waterfall', 'water')),
    ('blight', ('blight', 'cloud')),
    ('mist', ('mist', 'fog', 'dust')),
    ('spark', ('spark', 'ember')),
    ('bubble', ('bubble',)),
    ('fire', ('fire', 'flame', 'torch', 'candle', 'brazier', 'lantern', 'lamp', 'sconce', 'chandelier', 'pit')),
)
PLACED = frozenset('STAT DOOR MISC WEAP CONT LIGH ARMO CLOT REPA ACTI APPA LOCK PROB INGR BOOK ALCH'.split())


def kind_of(emitter, texture, mesh):
    """The emitter's kind (TEXTURE_KINDS by its particle texture, else KINDS by its node and mesh names), 'other' when
    no word matches."""
    low = (texture or '').casefold()
    for kind, words in TEXTURE_KINDS:
        if any(w in low for w in words):
            return kind
    for text in (emitter, mesh):
        low = (text or '').casefold()
        for kind, words in KINDS:
            if any(w in low for w in words):
                return kind
    return 'other'


def _name(value):
    if isinstance(value, bytes):
        return value.decode('cp1252', 'replace')
    return str(value or '')


def _texture(node):
    """The particle texture file of a particles node (its NiTexturingProperty's base texture), '' when none."""
    for prop in getattr(node, 'properties', None) or []:
        if prop is None or type(prop).__name__ != 'NiTexturingProperty':
            continue
        base = getattr(prop, 'base_texture', None)
        source = getattr(base, 'source', None) if base is not None else None
        name = _name(getattr(source, 'file_name', b'')) if source is not None else ''
        if name:
            return name.replace('\\', '/').rsplit('/', 1)[-1].casefold()
    return ''


def mesh_emitters(raw, N, mesh=''):
    """[{node, kind, texture, size, rise, rate, lifetime}] of every NiParticleSystemController in a NIF."""
    data = N.Data()
    try:
        data.read(io.BytesIO(raw))
    except Exception:
        return None
    out = []
    for block in data.blocks:
        if type(block).__name__ != 'NiParticleSystemController':
            continue
        emitter = getattr(block, 'emitter', None)
        node = _name(getattr(emitter, 'name', b'')) if emitter is not None else ''
        target = getattr(block, 'target', None)
        texture = _texture(target) if target is not None else ''
        speed, life = float(getattr(block, 'speed', 0.0)), float(getattr(block, 'lifetime', 0.0))
        rate = float(getattr(block, 'emit_rate', getattr(block, 'birth_rate', 0.0)) or 0.0)
        out.append({'node': node, 'kind': kind_of(node, texture, mesh), 'texture': texture,
                    'size': round(max(0.0, float(getattr(block, 'size', 0.0))), 2),
                    'rise': round(max(0.0, speed) * max(0.0, life), 1), 'rate': round(rate, 2),
                    'lifetime': round(max(0.0, life), 2)})
    return out


def _sources(data_files):
    """(masters present in load order, {normalised mesh path: (BSA path, entry) or loose Path})."""
    data_files = Path(data_files)
    masters = [p for p in (child_ci(data_files, m, required=False) for m in GAME_MASTERS) if p is not None]
    files = {}
    for name in GAME_ARCHIVES:
        archive = child_ci(data_files, name, required=False)
        if archive is None:
            continue
        bsa = BSA(archive)
        for path, entry in bsa.entries.items():
            if (path.startswith('meshes/') and path.endswith('.nif')) or path.startswith('textures/'):
                files[path] = (archive, entry)
    for folder, prefix, suffixes in (('Meshes', 'meshes/', ('.nif',)), ('Textures', 'textures/', ('.dds', '.tga', '.bmp'))):
        root = child_ci(data_files, folder, required=False)
        if root is not None and root.is_dir():
            for p in root.rglob('*'):
                if p.is_file() and p.suffix.casefold() in suffixes:
                    files[normpath(prefix + str(p.relative_to(root)))] = p
    return masters, files


def _read(source):
    if isinstance(source, Path):
        return source.read_bytes()
    archive, entry = source
    with archive.open('rb') as f:
        f.seek(entry['offset'])
        return f.read(entry['bytes'])


def placements(masters):
    """({object id: model path}, Counter of (model path, 'exterior'|'interior') placements) over the masters (a later
    master's record of the same ID wins)."""
    objects, refs = {}, []
    for master in masters:
        raw = master.read_bytes()
        for tag, flags, payload in records(raw):
            if tag in PLACED:
                s = dict(subrecords(payload))
                if 'NAME' not in s:
                    continue
                key = string(s['NAME']).casefold()
                if is_deleted(flags, s):
                    objects.pop(key, None)
                elif s.get('MODL'):
                    objects[key] = normpath('meshes/' + string(s['MODL']))
            elif tag == 'CELL':
                interior, ref_id, deleted = None, None, False
                for sub, value in subrecords(payload):
                    if sub == 'DATA' and interior is None and len(value) == 12:
                        interior = bool(struct.unpack_from('<I', value)[0] & 1)
                    elif sub == 'FRMR':
                        if ref_id is not None and not deleted:
                            refs.append((ref_id, interior))
                        ref_id, deleted = None, False
                    elif sub == 'NAME' and interior is not None and ref_id is None:
                        ref_id = string(value).casefold()
                    elif sub == 'DELE':
                        deleted = True
                if ref_id is not None and not deleted:
                    refs.append((ref_id, interior))
    counts = Counter()
    for ref_id, interior in refs:
        model = objects.get(ref_id)
        if model:
            counts[(model, 'interior' if interior else 'exterior')] += 1
    return objects, counts


def _sweep_one(task):
    path, source = task
    from prepare_scenery import nif_reader
    return path, mesh_emitters(_read(source), nif_reader(), path)


def sweep(data_files, jobs=1):
    """The sweep: per kind and per mesh, the emitters and the placements (read only)."""
    from build_parallel import ordered_map
    masters, files = _sources(data_files)
    _, counts = placements(masters)
    placed = sorted({m for m, _ in counts})
    missing = [m for m in placed if m not in files]
    results = list(ordered_map(_sweep_one, [(m, files[m]) for m in placed if m in files], max(1, int(jobs))))
    meshes, by_kind, unread = [], defaultdict(Counter), []
    for path, emitters in results:
        if emitters is None:
            unread.append(path)
            continue
        if not emitters:
            continue
        ext, inner = counts.get((path, 'exterior'), 0), counts.get((path, 'interior'), 0)
        kinds = Counter(e['kind'] for e in emitters)
        meshes.append({'mesh': path, 'exterior': ext, 'interior': inner, 'kinds': dict(kinds), 'emitters': emitters})
        for kind, n in kinds.items():
            k = by_kind[kind]
            k['meshes'] += 1
            k['emitters'] += n
            k['exterior_placements'] += ext
            k['interior_placements'] += inner
            k['exterior_emitters'] += n * ext
            k['interior_emitters'] += n * inner
    meshes.sort(key=lambda m: (-(m['exterior'] + m['interior']), m['mesh']))
    return {'masters': [p.name for p in masters], 'placed_meshes': len(placed), 'meshes_with_emitters': len(meshes),
            'meshes_not_found': len(missing), 'meshes_unreadable': len(unread),
            'by_kind': {k: dict(v) for k, v in sorted(by_kind.items())}, 'meshes': meshes}


# ---------------------------------------------------------------- the smoke table the engine draws (world/smoke.aws)

# AWS1 (engine/aga/src/aw_smoke.c): header 'AWS1' <I> rows; rows sorted by cell (x, then y), SMOKE_ROW each:
# <hh> exterior cell, <3f> emitter position (original units), <H> particle size, <H> rise (speed x lifetime, original
# units), <B> birth rate x 4 a second (at most 255), <B> lifetime x 20 (seconds), <BBB> colour (the particle
# texture's mean, alpha weighted), <B> kind (SMOKE_KINDS).
SMOKE_MAGIC = b'AWS1'
SMOKE_ROW = struct.Struct('<hh3fHHBB3BB')
SMOKE_KINDS = {'smoke': 1, 'steam': 2}
SMOKE_ROWS_MAX = 16384
SMOKE_GREY = (128, 128, 128)   # a texture that cannot be read
_PARTICLE_MARK = b'NiParticleSystemController'


def emitter_points(raw, N, kinds, mesh=''):
    """[(kind, (x, y, z) in the mesh's frame, emitter row)] of the emitters of the given kinds in a NIF: the emitter
    node's position under the same root rule as the flames (prepare_scenery.model_flames)."""
    import numpy as np
    from nif_common import first_record, scenery_root_local
    rows = mesh_emitters(raw, N, mesh) or []
    if not any(r['kind'] in kinds for r in rows):
        return []
    data = N.Data()
    data.read(io.BytesIO(raw))
    worlds = {}

    def collect(node, parent, root=False):
        if not isinstance(node, N.NiAVObject):
            return
        local = np.array(node.get_transform().as_list())
        if root:
            local = scenery_root_local(local, node, N, first_record(data, node))
        world = local @ parent
        worlds[id(node)] = world
        for child in getattr(node, 'children', []):
            if child is not None:
                collect(child, world)
    for root in data.roots:
        collect(root, np.eye(4), root=True)
    out, k = [], 0
    for block in data.blocks:
        if type(block).__name__ != 'NiParticleSystemController':
            continue
        row = rows[k]
        k += 1
        emitter = getattr(block, 'emitter', None)
        if row['kind'] not in kinds or emitter is None or id(emitter) not in worlds:
            continue
        out.append((row['kind'], tuple(float(v) for v in worlds[id(emitter)][3, :3]), row))
    return out


def texture_colour(files, name):
    """Mean colour (alpha weighted) of a particle texture in the archives or loose files, SMOKE_GREY when none."""
    if not name:
        return SMOKE_GREY
    stem = name.rsplit('.', 1)[0]
    for ext in ('.dds', '.tga', '.bmp'):
        source = files.get('textures/' + stem + ext)
        if source is None:
            continue
        try:
            from PIL import Image
            image = Image.open(io.BytesIO(_read(source))).convert('RGBA')
        except Exception:
            continue
        r = g = b = w = 0
        px = image.tobytes()
        for i in range(0, len(px), 4):
            pa = px[i + 3]
            r += px[i] * pa; g += px[i + 1] * pa; b += px[i + 2] * pa; w += pa
        if w:
            return (r // w, g // w, b // w)
    return SMOKE_GREY


def _placed_refs(masters, objects):
    """[(model, cell x, cell y, ref)] of every exterior placement whose object has a model."""
    from mwad.audit import cell_data
    out = []
    for master in masters:
        for tag, _flags, payload in records(master.read_bytes()):
            if tag != 'CELL':
                continue
            try:
                cell = cell_data(list(subrecords(payload)))
            except Exception:
                continue          # a cell the simple loader does not take (moved references): counted by nobody
            if cell['flags'] & 1:
                continue
            for ref in cell['refs']:
                model = objects.get(ref.get('id', '').casefold())
                if model and not ref.get('deleted') and 'position' in ref:
                    out.append((model, cell['x'], cell['y'], ref))
    return out


def smoke_table(data_files, kinds=('smoke', 'steam')):
    """(AWS1 bytes, report): every exterior placement of a mesh with a smoke or steam emitter, one row per emitter
    (MESH-PARTICLE-EMITTERS, simplest first). Only meshes whose bytes name a particle controller are parsed."""
    import numpy as np
    from prepare_scenery import nif_reader, reference_rotation
    masters, files = _sources(data_files)
    objects, _ = placements(masters)
    N = nif_reader()
    points, colours = {}, {}
    rows, by_kind, meshes = [], Counter(), Counter()
    for model, cx, cy, ref in _placed_refs(masters, objects):
        if model not in points:
            source = files.get(model)
            raw = _read(source) if source is not None else b''
            points[model] = emitter_points(raw, N, kinds, model) if _PARTICLE_MARK in raw else []
        if not points[model]:
            continue
        rotation = reference_rotation(ref)
        scale = float(ref.get('scale', 1.0))
        for kind, local, e in points[model]:
            p = rotation @ np.array(local) * scale + np.array(ref['position'])
            if e['texture'] not in colours:
                colours[e['texture']] = texture_colour(files, e['texture'])
            rows.append((cx, cy, *(float(v) for v in p), min(65535, int(round(e['size'] * scale))),
                         min(65535, int(round(e['rise'] * scale))), min(255, int(round(e['rate'] * 4))),
                         min(255, int(round(e['lifetime'] * 20))), *colours[e['texture']], SMOKE_KINDS[kind]))
            by_kind[kind] += 1
            meshes[model.rsplit('/', 1)[-1]] += 1
    if len(rows) > SMOKE_ROWS_MAX:
        raise ValueError('Smoke table exceeds runtime bounds: %d rows' % len(rows))
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3], r[4]))
    raw = SMOKE_MAGIC + struct.pack('<I', len(rows)) + b''.join(SMOKE_ROW.pack(*r) for r in rows)
    return raw, {'rows': len(rows), 'by_kind': dict(by_kind), 'meshes': dict(meshes.most_common()),
                 'textures': {k: list(v) for k, v in sorted(colours.items())}}


# The smoke puff the engine draws (world/smoke.spr, MESH-PARTICLE-EMITTERS: "a shit simple sprite thing"): the
# chimneys' own particle texture as a Quake sprite (IDSP version 1, facing the view), SMOKE_SPRITE_FRAMES frames of
# SMOKE_SPRITE_SIZE square, each frame keeping fewer of the puff's texels (alpha above a rising threshold), so a
# puff thins out as it rises; transparent texels are palette index 255 as in every AmiWind sprite.
SMOKE_SPRITE_TEXTURE = 'tx_smokealpha00a'
SMOKE_SPRITE_SIZE = 32
SMOKE_SPRITE_FRAMES = 4
SMOKE_SPRITE_CUTS = (40, 90, 140, 190)


def smoke_sprite(data_files, palette, texture=SMOKE_SPRITE_TEXTURE):
    """The smoke puff sprite (IDSP bytes) from the user's own particle texture, or None when it cannot be read."""
    from PIL import Image
    _, files = _sources(data_files)
    image = None
    for ext in ('.dds', '.tga', '.bmp'):
        source = files.get('textures/' + texture + ext)
        if source is None:
            continue
        try:
            image = Image.open(io.BytesIO(_read(source))).convert('RGBA')
            break
        except Exception:
            image = None
    if image is None or len(palette) != 768:
        return None
    size = SMOKE_SPRITE_SIZE
    image = image.resize((size, size), Image.Resampling.BOX)
    pal = Image.new('P', (1, 1))
    pal.putpalette(palette)
    # nearest palette colours of the visible texels; index 255 stays the transparent one
    indices = image.convert('RGB').quantize(palette=pal, dither=Image.Dither.NONE).tobytes()
    alpha = image.tobytes()[3::4]
    raw = struct.pack('<4siifiiifi', b'IDSP', 1, 2, size * 0.5, size, size, SMOKE_SPRITE_FRAMES, 0.0, 0)
    for cut in SMOKE_SPRITE_CUTS[:SMOKE_SPRITE_FRAMES]:
        pixels = bytes(i if a > cut and i != 255 else 255 for i, a in zip(indices, alpha))
        raw += struct.pack('<5i', 0, -size // 2, size // 2, size, size) + pixels
    return raw


def read_smoke_table(raw):
    """Rows of an AWS1 table as dicts (tests, measurements)."""
    if raw[:4] != SMOKE_MAGIC:
        raise ValueError('Not a smoke table')
    count = struct.unpack_from('<I', raw, 4)[0]
    if len(raw) != 8 + count * SMOKE_ROW.size:
        raise ValueError('Smoke table has the wrong shape')
    names = ('cx', 'cy', 'x', 'y', 'z', 'size', 'rise', 'rate4', 'life20', 'r', 'g', 'b', 'kind')
    return [dict(zip(names, SMOKE_ROW.unpack_from(raw, 8 + i * SMOKE_ROW.size))) for i in range(count)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    s = sub.add_parser('sweep', help='every placed mesh with a particle emitter, by kind (read only)')
    s.add_argument('--data-files', required=True)
    s.add_argument('--json')
    s.add_argument('--jobs', type=int, default=1)
    t = sub.add_parser('smoke-table', help='write the exterior smoke and steam table (world/smoke.aws)')
    t.add_argument('--data-files', required=True)
    t.add_argument('--out', required=True)
    args = ap.parse_args(argv)
    if args.command == 'smoke-table':
        raw, report = smoke_table(args.data_files)
        Path(args.out).write_bytes(raw)
        print(json.dumps(report, indent=1, sort_keys=True))
        return 0
    print('[particle emitters] sweeping %s on %d workers' % (args.data_files, args.jobs), flush=True)
    result = sweep(args.data_files, args.jobs)
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    summary = {k: v for k, v in result.items() if k != 'meshes'}
    summary['top_meshes'] = [{k: m[k] for k in ('mesh', 'exterior', 'interior', 'kinds')} for m in result['meshes'][:40]]
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
