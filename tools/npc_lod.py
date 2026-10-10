#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""NPC model levels of detail (docs/NPC_MODEL_CACHE.md, "NPC model levels of detail").

Every resident appearance is baked at up to four levels from the same recipe and
the same frame times:

  level 0  near: up to 666 triangles, the head as authored when it fits
           (progs/l0/a_<id>.mdl)
  level 1  the map's own model: today's 480-triangle budget bake, byte for byte
           (progs/a_<id>.mdl; precached, collision and QuakeC use it as before)
  level 2  mid distance: about 240 triangles, smaller body texel tiles (progs/l2/)
  level 3  crowds far away: about 120 triangles, small texel tiles (progs/l3/)

--npc-lod-levels N picks the levels: 2 = levels 0-1, 3 = 0-2, 4 = 0-3. Every
level has the same frame list (names, order and count) because the engine swaps
one for another mid-animation by frame index; frame_names / levels_check refuse
a set that does not. A level that gives nothing over level 1 (no more triangles
for level 0, no fewer for levels 2-3) is left out for that appearance.

Which actors get level 0 is a policy (--npc-face-lod): all, named (unique NPC
records: a display name no other NPC record shares), measured (head_error at or
above MEASURED_THRESHOLD) or list (record IDs in a file); only those ship a level-0
file. Levels 2 and 3 apply to every resident. The level table (MANIFEST, AWNL2) lists every appearance with its
level-0 use flag and the bytes of each level; the engine (aw_npc_lod.c) ranks the
actors by distance each frame and gives each the finest level its distance band
allows that still fits its byte budget, the map's own model otherwise.

    python3 tools/npc_lod.py survey --data-files DIR --palette LMP --out REPORT.json [--bake] [--jobs N]
    python3 tools/npc_lod.py check ID1      (level table + every set's frame list)
"""
import argparse
import hashlib
import inspect
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

MANIFEST = 'progs/npc-lod.txt'
MAGIC = 'AWNL2'
LEVEL_COUNT = 4
MAP_LEVEL = 1
OPTION = '--npc-lod'
MODES = ('on', 'off')
LEVELS_OPTION = '--npc-lod-levels'
LEVEL_SETS = {2: (0, 1), 3: (0, 1, 2), 4: (0, 1, 2, 3)}
POLICY_OPTION = '--npc-face-lod'
POLICIES = ('all', 'named', 'measured', 'list')
# Fallbacks of the shipped defaults. The shipped defaults are config/build-defaults.json (npc_lod,
# npc_lod_levels, npc_face_lod, npc_lod_disk_mib): the owner compares the levels in game before any of
# them becomes the default, so that is a config change, not a code change. A --build-config file
# overrides them, and the command line overrides both.
DEFAULT_MODE = 'off'
DEFAULT_LEVELS = 3
DEFAULT_POLICY = 'all'
# Level files (all but the map models) may take at most this much disk in one build.
DEFAULT_DISK_MIB = 96
CONFIG_KEYS = {'npc_lod': 'mode', 'npc_lod_levels': 'levels', 'npc_face_lod': 'policy', 'npc_lod_disk_mib': 'disk_mib'}


def check_config(values, origin='build config'):
    """Validate the NPC level keys of a build config (raises ValueError)."""
    if 'npc_lod' in values and values['npc_lod'] not in MODES:
        raise ValueError('Invalid npc_lod in %s: expected on or off' % origin)
    if 'npc_lod_levels' in values and (isinstance(values['npc_lod_levels'], bool)
                                       or values['npc_lod_levels'] not in LEVEL_SETS):
        raise ValueError('Invalid npc_lod_levels in %s: expected 2, 3 or 4' % origin)
    if 'npc_face_lod' in values and values['npc_face_lod'] not in POLICIES:
        raise ValueError('Invalid npc_face_lod in %s: expected all, named, measured or list' % origin)
    if 'npc_lod_disk_mib' in values and (isinstance(values['npc_lod_disk_mib'], bool)
                                         or not isinstance(values['npc_lod_disk_mib'], int)
                                         or values['npc_lod_disk_mib'] < 0):
        raise ValueError('Invalid npc_lod_disk_mib in %s: expected a whole number of MiB' % origin)
    return values


def shipped_defaults(path=None):
    """{'mode', 'levels', 'policy', 'disk_mib'} from config/build-defaults.json (fallbacks above)."""
    path = Path(path) if path else ROOT / 'config/build-defaults.json'
    out = {'mode': DEFAULT_MODE, 'levels': DEFAULT_LEVELS, 'policy': DEFAULT_POLICY, 'disk_mib': DEFAULT_DISK_MIB}
    try:
        values = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return out
    check_config(values, str(path))
    out.update({CONFIG_KEYS[k]: values[k] for k in CONFIG_KEYS if k in values})
    return out
# measured: a head whose level-1 bake moves its surface by at least this many Quake
# units somewhere (symmetric Hausdorff distance, rest pose) may use level 0.
MEASURED_THRESHOLD = 0.75
# Level 1: build_resident's budget ladder (unchanged). Level 0: the alias writer's
# standard ceiling (666 faces = 1998 vertices, no model-budgets.txt exception).
FAR_BUDGETS = (480, 384, 320, 256, 192)
NEAR_FACE_LIMIT = 666
NEAR_BUDGETS = (666, 640, 608, 576, 544, 512)
# Shares of each head kept whole by the level-0 bake, tried in order (near_head_faces).
NEAR_HEAD_SHARES = (1.0, 0.75, 0.5)
# Coarser levels: budget ladders and texel tiles (edge in texels; the bake samples 16).
LEVEL_SPECS = {
    0: {'dir': 'progs/l0', 'head_tile': 16, 'body_tile': 16},
    2: {'dir': 'progs/l2', 'budgets': (240, 224, 208, 192), 'head_tile': 16, 'body_tile': 8},
    3: {'dir': 'progs/l3', 'budgets': (120, 112, 104, 96), 'head_tile': 8, 'body_tile': 8},
}
BAKE_TILE = 16
SKIN_WIDTH = 512
SKIN_ROWS = 480         # the alias renderer's skin height bound
HEAD_SLOT = 0
# Engine bound on one path (aw_npc_lod.h AW_NPC_LOD_PATH).
PATH_CHARS = 63


def stem(identifier):
    """The resident model stem the area and town converters use (a_ + 12 hex)."""
    return 'a_' + hashlib.sha256(identifier.encode()).hexdigest()[:12]


def far_path(identifier):
    return 'progs/' + stem(identifier) + '.mdl'


def level_path(far, level):
    """Level LEVEL's file of the map model FAR (the engine derives it the same way)."""
    if level == MAP_LEVEL:
        return far
    return LEVEL_SPECS[level]['dir'] + '/' + far.rsplit('/', 1)[-1]


def add_options(parser):
    parser.add_argument(OPTION, choices=MODES, default=None,
                        help='NPC model levels of detail: on (every resident is also baked at the --npc-lod-levels '
                             'levels; the engine picks one by distance) or off (one model per resident, the earlier '
                             'method); default from config/build-defaults.json (npc_lod)')
    parser.add_argument(LEVELS_OPTION, type=int, choices=sorted(LEVEL_SETS), default=None,
                        help='Levels with --npc-lod on: 2 (near + the map model), 3 (+ mid distance) or 4 (+ crowds '
                             'far away); default from config/build-defaults.json (npc_lod_levels)')
    parser.add_argument(POLICY_OPTION, choices=POLICIES, default=None,
                        help='Which residents may use the near level: all, measured (heads the budget bake changes '
                             'most), named (unique NPC records) or list (--npc-face-lod-list FILE); default from '
                             'config/build-defaults.json (npc_face_lod)')
    parser.add_argument('--npc-face-lod-list', type=Path, metavar='FILE',
                        help='With --npc-face-lod list: NPC record IDs, one per line')
    parser.add_argument('--npc-lod-disk-mib', type=int, default=None, metavar='MIB',
                        help='Disk for the level files (all but the map models): coarse levels first, then '
                             'near levels by head error, until this many MiB; default from '
                             'config/build-defaults.json (npc_lod_disk_mib)')
    return parser


def resolve_options(args, defaults=None):
    """{'mode', 'levels', 'policy', 'list', 'disk_mib'}: the command line, else the --build-config file,
    else the shipped defaults; refuses list without a file and the reverse."""
    base = dict(defaults or shipped_defaults())
    selected = getattr(args, 'build_config', None)
    if selected:
        try:
            values = json.loads(Path(selected).expanduser().read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            raise ValueError('Cannot read build config %s: %s' % (selected, error)) from error
        if isinstance(values, dict):
            check_config(values, str(selected))
            base.update({CONFIG_KEYS[k]: values[k] for k in CONFIG_KEYS if k in values})

    def pick(name, key):
        value = getattr(args, name, None)
        return base[key] if value is None else value
    mode = pick('npc_lod', 'mode')
    levels = pick('npc_lod_levels', 'levels')
    policy = pick('npc_face_lod', 'policy')
    listed = getattr(args, 'npc_face_lod_list', None)
    if levels not in LEVEL_SETS:
        raise ValueError(LEVELS_OPTION + ' takes ' + ', '.join(map(str, sorted(LEVEL_SETS))))
    if policy == 'list' and listed is None:
        raise ValueError(POLICY_OPTION + ' list needs --npc-face-lod-list FILE')
    if policy != 'list' and listed is not None:
        raise ValueError('--npc-face-lod-list needs ' + POLICY_OPTION + ' list')
    disk = pick('npc_lod_disk_mib', 'disk_mib')
    if disk < 0:
        raise ValueError('--npc-lod-disk-mib cannot be negative')
    return {'mode': mode, 'levels': levels, 'policy': policy, 'list': str(listed) if listed else None,
            'disk_mib': disk}


def option_arguments(options, defaults=None):
    """Converter command-line arguments for resolved options: only what differs from the shipped defaults
    (the converters read those themselves), so default commands stay unchanged."""
    base = defaults or shipped_defaults()
    out = []
    if options['mode'] != base['mode']:
        out += [OPTION, options['mode']]
    if options['levels'] != base['levels']:
        out += [LEVELS_OPTION, str(options['levels'])]
    if options['policy'] != base['policy']:
        out += [POLICY_OPTION, options['policy']]
    if options['list']:
        out += ['--npc-face-lod-list', options['list']]
    if options.get('disk_mib', base['disk_mib']) != base['disk_mib']:
        out += ['--npc-lod-disk-mib', str(options['disk_mib'])]
    return out


def read_list(path):
    rows = set()
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.split('#', 1)[0].strip()
        if line:
            rows.add(line.casefold())
    return rows


def named_records(kinds):
    """NPC record IDs whose display name (FNAM) no other NPC record shares."""
    from mwad.npc import text
    count = {}
    for identifier, fields in kinds['NPC_'].items():
        name = text(fields, 'FNAM').casefold()
        count[name] = count.get(name, 0) + 1
    return {i for i, f in kinds['NPC_'].items() if count[text(f, 'FNAM').casefold()] == 1}


def uses_near(policy, identifier, metric, named=(), listed=()):
    """The level-0 use flag of one appearance under a policy."""
    if policy == 'all':
        return True
    if policy == 'named':
        return identifier in named
    if policy == 'list':
        return identifier in listed
    if policy == 'measured':
        return metric is not None and metric['hausdorff'] >= MEASURED_THRESHOLD
    raise ValueError('Unknown face LOD policy: ' + str(policy))


# ---------------------------------------------------------------- the head rule and the metrics

def head_indices(shapes):
    return [i for i, s in enumerate(shapes) if s['part'] == HEAD_SLOT]


def near_head_faces(shapes, budget=NEAR_FACE_LIMIT, share=1.0):
    """minimum_faces for the level-0 bake: every head shape (slot 0: head or helmet) whole when
    the heads plus a 4-face floor for every other shape fit the budget; otherwise the heads
    share what is left, in proportion to their faces. share < 1 protects only that share of
    each head's faces (the fallback when a whole head leaves too little for an outfit with many
    shapes). The one place the near level's head rule lives (the head-detail switch of
    npc_geometry plugs in here)."""
    heads = head_indices(shapes)
    names = [shapes[i].get('name', '') for i in heads]
    every = [s.get('name', '') for s in shapes]
    # minimum_faces is keyed by shape name: a protected name must name one shape only.
    if not heads or any(not n or every.count(n) != 1 for n in names):
        return {}
    room = budget - 4 * (len(shapes) - len(heads)) - 8
    total = sum(len(shapes[i]['faces']) for i in heads)
    if share < 1:
        if total * share > room:
            return {}
        return {shapes[i]['name']: min(len(shapes[i]['faces']), max(4, int(len(shapes[i]['faces']) * share)))
                for i in heads}
    if total <= room:
        return {shapes[i]['name']: len(shapes[i]['faces']) for i in heads}
    if room <= 4 * len(heads):
        return {}
    return {shapes[i]['name']: min(len(shapes[i]['faces']), max(4, int(len(shapes[i]['faces']) * room / total)))
            for i in heads}


def _actor_height(shapes):
    return max(s['positions'][0, :, 2].max() for s in shapes) - min(s['positions'][0, :, 2].min() for s in shapes)


def _decimated(shape, quota, actor_height=None, exact=False):
    """One shape's baked geometry in the rest pose: npc_geometry.bake's own steps."""
    import numpy as np
    from npc_geometry import simplify_shape
    p = shape['positions'][0]
    if exact:
        return p, shape['faces']
    points, ix = np.unique(np.round(p, 5), axis=0, return_inverse=True)
    ff = ix[shape['faces']]
    if len(ff) > quota:
        preserve = (actor_height is not None and shape['part'] == 3 and np.ptp(p[:, 2]) >= .2 * actor_height)
        points, ff = simplify_shape(points, ff.astype(np.int32), int(quota), preserve)
    return points, ff


def shape_face_counts(shapes, quotas, minimum_faces=None):
    """Faces each shape gets in a bake with these quotas (bake emits them in shape order)."""
    minimum_faces = minimum_faces or {}
    height = _actor_height(shapes)
    return [len(_decimated(s, q, height, minimum_faces.get(s.get('name', ''), 0) == len(s['faces']))[1])
            for s, q in zip(shapes, quotas)]


def _surface_samples(points, faces, steps=4):
    """Points on every triangle: its corners and a barycentric grid (steps per edge)."""
    import numpy as np
    weights = [(a / steps, b / steps, 1 - (a + b) / steps)
               for a in range(steps + 1) for b in range(steps + 1 - a)]
    w = np.array(weights)
    tri = points[faces]
    return np.einsum('wv,fvc->fwc', w, tri).reshape(-1, 3)


def surface_error(shapes, quotas, indices=None, minimum_faces=None):
    """How much a bake with these quotas moves the surface of the given shapes (default: all) in
    the rest pose. hausdorff / mean: symmetric distances in Quake units between dense surface
    samples; cut: share of their faces removed; faces / kept: before and after."""
    import numpy as np
    from scipy.spatial import cKDTree
    indices = range(len(shapes)) if indices is None else indices
    minimum_faces = minimum_faces or {}
    height = _actor_height(shapes)
    original, decimated, before, after = [], [], 0, 0
    for i in indices:
        s = shapes[i]
        original.append(_surface_samples(s['positions'][0], s['faces']))
        pts, ff = _decimated(s, quotas[i], height, minimum_faces.get(s.get('name', ''), 0) == len(s['faces']))
        decimated.append(_surface_samples(pts, ff))
        before += len(s['faces'])
        after += min(len(s['faces']), len(ff))
    if not before:
        return None
    a, b = np.concatenate(original), np.concatenate(decimated)
    ab, ba = cKDTree(b).query(a)[0], cKDTree(a).query(b)[0]
    return {'hausdorff': round(float(max(ab.max(), ba.max())), 4), 'mean': round(float((ab.mean() + ba.mean()) / 2), 4),
            'cut': round(1 - after / before, 4), 'faces': before, 'kept': after,
            'span': round(float(np.linalg.norm(np.ptp(a, axis=0))), 3)}


def head_error(shapes, quotas, minimum_faces=None):
    """surface_error of the head shapes (slot 0); None without one."""
    heads = head_indices(shapes)
    return surface_error(shapes, quotas, heads, minimum_faces) if heads else None


# ---------------------------------------------------------------- baking the levels

def head_detail_supported():
    """True when npc_geometry has the head-detail switch (--npc-head-detail original|budget)."""
    from npc_geometry import bake
    return 'head_detail' in inspect.signature(bake).parameters


def _detail(detail):
    """Keyword arguments selecting a head detail, when npc_geometry has the switch."""
    return {'head_detail': detail} if detail and head_detail_supported() else {}


def quotas_for(shapes, budget, face_limit=666, minimum_faces=None, detail='budget'):
    """npc_geometry.bake_quotas with a head detail (the budget split by default: the levels'
    own split; the original-head rule only where asked)."""
    from npc_geometry import bake_quotas
    return bake_quotas(shapes, budget, face_limit, minimum_faces, **_detail(detail))


def bake_far(shapes, materials, textures, palette, label='', detail=None):
    """build_resident's bake: (frames, faces, uv, skin, budget). detail None: npc_geometry's
    default (the single model of --npc-lod off); 'budget': the earlier bake, byte for byte
    (level 1 of --npc-lod on)."""
    from npc_geometry import bake
    for budget in FAR_BUDGETS:
        try:
            return (*bake(shapes, materials, textures, palette, budget=budget, **_detail(detail)), budget)
        except ValueError as error:
            if str(error) != 'Alias vertex budget exceeded' or budget == FAR_BUDGETS[-1]:
                raise ValueError(label + ': ' + str(error)) from error


def bake_near(shapes, materials, textures, palette, far_triangles):
    """The level-0 bake: (frames, faces, uv, skin, budget, protected) or None when no budget
    gives more triangles than level 1 (nothing to gain). With npc_geometry's head-detail
    switch it is that switch's original-head bake (its own rule and face limits; protected
    None). Otherwise each (head share, budget) pair is first counted with the bake's own
    decimation (shape_face_counts, no texture sampling); only the first that fits the alias
    face limit is baked."""
    from npc_geometry import bake, bake_quotas
    if head_detail_supported():
        try:
            frames, faces, uv, skin = bake(shapes, materials, textures, palette, budget=FAR_BUDGETS[0],
                                           **_detail('original'))
        except ValueError:
            return None
        if len(faces) <= far_triangles:
            return None
        return frames, faces, uv, skin, FAR_BUDGETS[0], None
    for share in NEAR_HEAD_SHARES:
        for budget in NEAR_BUDGETS:
            if budget <= far_triangles:
                break
            protected = near_head_faces(shapes, budget, share)
            if not protected:
                continue
            try:
                total = sum(shape_face_counts(shapes, bake_quotas(shapes, budget, NEAR_FACE_LIMIT, protected), protected))
            except ValueError:
                continue
            if total > NEAR_FACE_LIMIT:
                continue
            if total <= far_triangles:
                break
            try:
                frames, faces, uv, skin = bake(shapes, materials, textures, palette, budget=budget,
                                               face_limit=NEAR_FACE_LIMIT, minimum_faces=protected)
            except ValueError as error:
                if str(error) in ('Alias vertex budget exceeded', 'Too many separate shapes for budget'):
                    continue
                raise
            if len(faces) <= far_triangles:
                break
            return frames, faces, uv, skin, budget, protected
    return None


def bake_coarse(shapes, materials, textures, palette, level, far_triangles):
    """A coarser level's bake: (frames, faces, uv, skin, budget) or None when it does not save
    triangles over level 1."""
    from npc_geometry import bake
    for budget in LEVEL_SPECS[level]['budgets']:
        if budget >= far_triangles:
            continue
        try:
            if sum(shape_face_counts(shapes, quotas_for(shapes, budget))) >= far_triangles:
                continue
        except ValueError:
            continue
        try:
            frames, faces, uv, skin = bake(shapes, materials, textures, palette, budget=budget, **_detail('budget'))
        except ValueError as error:
            if str(error) in ('Alias vertex budget exceeded', 'Too many separate shapes for budget'):
                continue
            raise
        if len(faces) >= far_triangles:
            continue
        return frames, faces, uv, skin, budget
    return None


def retile(faces, uv, skin, palette, tiles):
    """Repack the bake's 16-texel face tiles at per-face edges TILES (<= 16, box-filtered) into a
    512-wide atlas: (uv, skin). Same faces and vertices; only texture coordinates and the skin
    change. Raises ValueError when the atlas would exceed the renderer's 480 rows."""
    import numpy as np
    from PIL import Image
    if all(t == BAKE_TILE for t in tiles):
        return uv, skin
    rgb = skin.convert('RGB')
    places, x, y, row = [], 0, 0, 0
    order = sorted(range(len(tiles)), key=lambda i: -tiles[i])     # rows of equal tiles, largest first
    for i in order:
        t = tiles[i]
        if not 1 <= t <= BAKE_TILE:
            raise ValueError('Texel tile outside 1..16')
        if x + t > SKIN_WIDTH:
            x, y, row = 0, y + row, 0
        places.append((i, x, y))
        x += t
        row = max(row, t)
    height = y + row
    height += (-height) % 4
    if height > SKIN_ROWS:
        raise ValueError('Retiled skin exceeds %d rows' % SKIN_ROWS)
    out = Image.new('RGB', (SKIN_WIDTH, max(4, height)))
    new_uv = np.array(uv, dtype=float).copy()
    for i, tx, ty in places:
        sx, sy = (i % 32) * BAKE_TILE, (i // 32) * BAKE_TILE
        t = tiles[i]
        tile = rgb.crop((sx, sy, sx + BAKE_TILE, sy + BAKE_TILE))
        if t != BAKE_TILE:
            tile = tile.resize((t, t), Image.Resampling.BOX)
        out.paste(tile, (tx, ty))
        new_uv[i * 3:i * 3 + 3] = [(tx, ty), (tx + t - 1, ty), (tx, ty + t - 1)]
    pal = Image.new('P', (1, 1))
    pal.putpalette(palette)
    return new_uv, out.quantize(palette=pal, dither=Image.Dither.NONE)


def level_tiles(shapes, quotas, level, minimum_faces=None):
    """Per-face tile edges of a level's bake: head shapes get head_tile, the rest body_tile."""
    spec = LEVEL_SPECS[level]
    if spec['head_tile'] == spec['body_tile'] == BAKE_TILE:
        return None
    counts = shape_face_counts(shapes, quotas, minimum_faces)
    tiles = []
    for s, n in zip(shapes, counts):
        tiles += [spec['head_tile'] if s['part'] == HEAD_SLOT else spec['body_tile']] * n
    return tiles


def frame_names(raw):
    """Frame names of an IDPO model, in file order (single frames only, as the bakers write)."""
    if raw[:8] != b'IDPO\x06\0\0\0':
        raise ValueError('Not an IDPO v6 model')
    skinwidth, skinheight, verts, tris, frames = struct.unpack_from('<5i', raw, 52)
    at = 84
    skins = struct.unpack_from('<i', raw, 48)[0]
    for _ in range(skins):
        kind = struct.unpack_from('<i', raw, at)[0]
        if kind != 0:
            raise ValueError('Grouped skins are not written by the bakers')
        at += 4 + skinwidth * skinheight
    at += verts * 12 + tris * 16
    names = []
    for _ in range(frames):
        kind = struct.unpack_from('<i', raw, at)[0]
        if kind != 0:
            raise ValueError('Grouped frames are not written by the bakers')
        names.append(raw[at + 12:at + 28].split(b'\0', 1)[0].decode('ascii'))
        at += 28 + verts * 4
    if at != len(raw):
        raise ValueError('Model size does not match its header')
    return names


def model_counts(raw):
    verts, tris, frames = struct.unpack_from('<3i', raw, 60)
    skinwidth, skinheight = struct.unpack_from('<2i', raw, 52)
    return {'vertices': verts, 'triangles': tris, 'frames': frames, 'skin': [skinwidth, skinheight]}


def pair_check(far_raw, near_raw):
    """Refuse two levels whose frame lists differ (names, order, count): the engine swaps models
    by frame index mid-animation."""
    a, b = frame_names(far_raw), frame_names(near_raw)
    if a != b:
        raise ValueError('Level frame list differs from the map model (%d vs %d frames)' % (len(a), len(b)))
    return a


def levels_check(raws):
    """pair_check of every level in {level: raw} against level 1."""
    names = frame_names(raws[MAP_LEVEL])
    for level, raw in raws.items():
        if level != MAP_LEVEL:
            pair_check(raws[MAP_LEVEL], raw)
    return names


# Repository modules a resident bake runs (npc_geometry.assemble/bake/animated_mdl and what they import:
# face/head geometry, NIF reading, BSA access, root rules, the head-detail switch). The pool key covers their source, so an edit to
# any of them never reuses an older bake; before, only npc_geometry and this module counted
# (BUILD-POOL-ARG-UNFINGERPRINTED-35; tests/test_build_pool_arg.py checks the list against the imports).
BAKE_MODULES = ('npc_geometry', 'npc_faces', 'prepare_scenery', 'nif_common', 'mesh_geometry_env', 'mwad.audit', 'mwad.esm',
                'mwad.paths')
BAKE_PACKAGES = ('numpy', 'scipy', 'Pillow', 'PyFFI', 'fast-simplification')


_CODE_IDENTITY = []


def code_identity():
    """Source of the code a resident bake depends on, plus the versions of the packages it computes with
    (pool keys). Computed once per process."""
    if _CODE_IDENTITY:
        return _CODE_IDENTITY[0]
    import importlib.metadata
    # Static imports: a computed import_module() name would make every stage's code closure uncertain.
    import mesh_geometry_env
    import mwad.audit
    import mwad.esm
    import mwad.paths
    import nif_common
    import npc_faces
    import npc_geometry
    import prepare_scenery
    modules = {'npc_geometry': npc_geometry, 'npc_faces': npc_faces, 'prepare_scenery': prepare_scenery,
               'nif_common': nif_common, 'mesh_geometry_env': mesh_geometry_env, 'mwad.audit': mwad.audit,
               'mwad.esm': mwad.esm, 'mwad.paths': mwad.paths}
    texts = [inspect.getsource(modules[name]) for name in BAKE_MODULES]
    texts.append(inspect.getsource(sys.modules[__name__]))
    versions = []
    for name in BAKE_PACKAGES:
        try:
            versions.append(f'{name}={importlib.metadata.version(name)}')
        except importlib.metadata.PackageNotFoundError:
            versions.append(f'{name}=absent')
    texts.append(sys.version + '\n' + '\n'.join(versions))
    _CODE_IDENTITY.append(hashlib.sha256('\0'.join(texts).encode('utf-8', 'surrogateescape')).hexdigest())
    return _CODE_IDENTITY[0]


def bake_levels(shapes, materials, textures, palette, label='', levels=(MAP_LEVEL,)):
    """({level: raw}, record): one resident appearance at the given levels. Level 1 is always
    baked and is the earlier single model byte for byte."""
    import time
    from npc_geometry import animated_mdl
    started = time.monotonic()
    # With levels, level 1 is the earlier budget bake (the map's own model, as before); the
    # single model of --npc-lod off follows npc_geometry's default head detail.
    frames, faces, uv, skin, budget = bake_far(shapes, materials, textures, palette, label,
                                               None if tuple(levels) == (MAP_LEVEL,) else 'budget')
    raws = {MAP_LEVEL: animated_mdl(frames, faces, uv, skin)}
    record = {'far_budget': budget, 'far_triangles': len(faces), 'frames': len(frames),
              'bounds': [frames.min((0, 1)).tolist(), frames.max((0, 1)).tolist()],
              'levels': {str(MAP_LEVEL): {'triangles': len(faces), 'bytes': len(raws[MAP_LEVEL]),
                                          'seconds': round(time.monotonic() - started, 3)}}}
    if levels == (MAP_LEVEL,):
        return raws, record
    far_quotas = quotas_for(shapes, budget)
    record['head_error'] = head_error(shapes, far_quotas)
    record['levels'][str(MAP_LEVEL)]['body_error'] = surface_error(shapes, far_quotas)
    for level in levels:
        if level == MAP_LEVEL:
            continue
        started = time.monotonic()
        if level == 0:
            found = bake_near(shapes, materials, textures, palette, len(faces))
            if found is None:
                record['levels']['0'] = None
                continue
            lf, lfaces, luv, lskin, lbudget, protected = found
            quotas = None if protected is None else quotas_for(shapes, lbudget, NEAR_FACE_LIMIT, protected)
        else:
            found = bake_coarse(shapes, materials, textures, palette, level, len(faces))
            if found is None:
                record['levels'][str(level)] = None
                continue
            lf, lfaces, luv, lskin, lbudget = found
            protected = None
            quotas = quotas_for(shapes, lbudget)
        tiles = level_tiles(shapes, quotas, level, protected) if quotas is not None else None
        if tiles is not None:
            if len(tiles) != len(lfaces):
                raise ValueError(label + ': level %d face count differs from its shape counts' % level)
            luv, lskin = retile(lfaces, luv, lskin, palette, tiles)
        raws[level] = animated_mdl(lf, lfaces, luv, lskin)
        pair_check(raws[MAP_LEVEL], raws[level])
        entry = {'budget': lbudget, 'triangles': len(lfaces), 'bytes': len(raws[level]),
                 'sha256': hashlib.sha256(raws[level]).hexdigest(), 'skin_rows': lskin.size[1],
                 'seconds': round(time.monotonic() - started, 3)}
        if level == 0:
            entry['head_protected'] = sum(protected.values()) if protected else None
        else:
            entry['body_error'] = surface_error(shapes, quotas)
            entry['head_error'] = head_error(shapes, quotas)
        record['levels'][str(level)] = entry
    return raws, record


# ---------------------------------------------------------------- the level table

def manifest_text(rows, levels):
    """AWNL2 level table: 'AWNL2 <rows> <levels in the build, e.g. 012>', then one row per
    appearance, sorted by map model path: '<map model> <level-0 use 0|1> <bytes of level 0..3>'
    (0 = that level is not shipped for it; level 1's bytes are the map model's). Paths <=
    PATH_CHARS, FFS names <= 30 characters, no spaces."""
    rows = sorted(rows, key=lambda r: r['far'])
    seen = set()
    lines = ['%s %d %s' % (MAGIC, len(rows), ''.join(map(str, sorted(levels))))]
    for r in rows:
        paths = [r['far']] + [level_path(r['far'], k) for k in range(LEVEL_COUNT) if k != MAP_LEVEL and r['bytes'][k]]
        for path in paths:
            if len(path) > PATH_CHARS or ' ' in path or not path.endswith('.mdl') or not path.startswith('progs/'):
                raise ValueError('Invalid NPC LOD path: ' + path)
            if any(len(part) > 30 for part in path.split('/')):
                raise ValueError('NPC LOD path name over 30 characters: ' + path)
        if r['far'].count('/') != 1:
            raise ValueError('NPC LOD map model must sit in progs/: ' + r['far'])
        if r['far'] in seen:
            raise ValueError('Duplicate NPC LOD row: ' + r['far'])
        if len(r['bytes']) != LEVEL_COUNT or not r['bytes'][MAP_LEVEL]:
            raise ValueError('NPC LOD row needs four byte counts and the map model: ' + r['far'])
        if any(r['bytes'][k] and k not in levels for k in range(LEVEL_COUNT)):
            raise ValueError('NPC LOD row has a level the build does not have: ' + r['far'])
        seen.add(r['far'])
        lines.append('%s %d %s' % (r['far'], 1 if r['use'] else 0, ' '.join(str(int(b)) for b in r['bytes'])))
    return '\n'.join(lines) + '\n'


def parse_manifest(text):
    lines = text.splitlines()
    head = lines[0].split(' ') if lines else []
    if len(head) != 3 or head[0] != MAGIC:
        raise ValueError('Not an NPC LOD level table')
    count, levels = int(head[1]), tuple(int(c) for c in head[2])
    rows = []
    for line in lines[1:]:
        far, use, *sizes = line.split(' ')
        if len(sizes) != LEVEL_COUNT:
            raise ValueError('NPC LOD row needs four byte counts: ' + line)
        rows.append({'far': far, 'use': use == '1', 'bytes': [int(b) for b in sizes]})
    if len(rows) != count:
        raise ValueError('NPC LOD level table row count differs from its header')
    return rows, levels


def merge_manifest(id1, rows, levels):
    """Add (or replace by map model) rows in ID1's level table; several converters write
    residents into one scene (Seyda Neen rooms, Balmora interiors, towns)."""
    path = Path(id1) / MANIFEST
    current = {}
    if path.is_file():
        old, old_levels = parse_manifest(path.read_text(encoding='ascii'))
        if tuple(old_levels) != tuple(sorted(levels)):
            raise ValueError('NPC LOD level table was written with other levels: %s' % (old_levels,))
        current = {r['far']: r for r in old}
    for r in rows:
        current[r['far']] = r
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest_text(current.values(), levels), encoding='ascii', newline='\n')
    return len(current)


def write_levels(id1, far, raws, use):
    """Write an appearance's level files (the map model is written by the caller); its table row."""
    sizes = [0] * LEVEL_COUNT
    for level, raw in raws.items():
        sizes[level] = len(raw)
        if level == MAP_LEVEL:
            continue
        target = Path(id1) / level_path(far, level)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return {'far': far, 'use': bool(use), 'bytes': sizes}


def check(id1):
    """Every table row: each level file present with its size and the map model's frame list."""
    id1 = Path(id1)
    rows, levels = parse_manifest((id1 / MANIFEST).read_text(encoding='ascii'))
    totals = [0] * LEVEL_COUNT
    for r in rows:
        raws = {}
        for k in range(LEVEL_COUNT):
            if r['bytes'][k]:
                raws[k] = (id1 / level_path(r['far'], k)).read_bytes()
                if len(raws[k]) != r['bytes'][k]:
                    raise ValueError('NPC LOD level table size differs: ' + level_path(r['far'], k))
                totals[k] += len(raws[k])
        levels_check(raws)
    return {'rows': len(rows), 'levels': list(levels), 'flagged': sum(r['use'] for r in rows), 'level_bytes': totals}


# ---------------------------------------------------------------- the resident converters

# The options a converter run uses (apply_options in its main); passed to the bake workers in
# their tasks (the builder's pool spawns workers: module state does not reach them).
SETTINGS = {'mode': 'off', 'levels': DEFAULT_LEVELS, 'policy': DEFAULT_POLICY, 'list': None,
            'disk_mib': DEFAULT_DISK_MIB, 'pool': None}
POOL_NAMESPACE = 'npc-resident-v2'


def add_converter_options(parser):
    add_options(parser)
    parser.add_argument('--npc-model-pool', type=Path, metavar='DIR',
                        help='Asset pool (development builds): reuse resident bakes stored by content')
    return parser


def apply_options(args):
    SETTINGS.update(resolve_options(args))
    pool = getattr(args, 'npc_model_pool', None)
    SETTINGS['pool'] = str(pool) if pool else None
    return dict(SETTINGS)


def task_settings():
    return dict(SETTINGS)


def baked_levels(settings):
    return LEVEL_SETS[settings.get('levels', DEFAULT_LEVELS)] if settings.get('mode') == 'on' else (MAP_LEVEL,)


def _pool(settings):
    from file_cache import FileCache
    return FileCache(settings.get('pool'), POOL_NAMESPACE, {'code': code_identity()})


_dependencies = {}


def _source_digest(data, appearance):
    """SHA-256 over every source file one appearance's bake reads (meshes, textures, skeleton):
    the gallery cache's dependency rule (gallery_cache.Dependencies)."""
    from gallery_cache import Dependencies, token
    key = str(data)
    if key not in _dependencies:
        _dependencies.clear()
        _dependencies[key] = Dependencies(data)
    spec = {'kind': 'NPC_', 'appearance': {k: appearance[k] for k in ('parts', 'skeleton', 'height', 'weight')}}
    return token(_dependencies[key].for_spec(spec))


def resident_bake(data, assets, skeleton, appearance, palette, times, settings=None):
    """({level: raw}, facts) of one resident: from the asset pool when every level is stored for
    exactly these inputs, else baked (and stored, one pool entry per level). Level 1 is the
    earlier single model, byte for byte."""
    import numpy as np
    from build_scratch import scratch_dir
    from npc_geometry import assemble
    settings = settings or {'mode': 'off', 'pool': None}
    levels = baked_levels(settings)
    pool = _pool(settings)
    keys = None
    if pool.enabled:
        source = _source_digest(data, appearance)
        common = {'appearance': appearance, 'times': [round(float(t), 9) for t in np.atleast_1d(times)],
                  'palette': hashlib.sha256(palette).hexdigest()}
        keys = {k: pool.key(source, dict(common, level=k)) for k in levels}
        with scratch_dir('npc-lod-', keep_on_failure=False) as tmp:
            raws, record, complete = {}, {}, True
            for k in levels:
                facts = pool.fetch(keys[k], Path(tmp) / str(k))
                if facts is None:
                    complete = False
                    break
                if facts.get('present', True):
                    raws[k] = (Path(tmp) / str(k)).read_bytes()
                for name, value in facts.get('record', {}).items():
                    if name == 'levels':
                        record.setdefault('levels', {}).update(value)
                    else:
                        record[name] = value
            if complete:
                return raws, record
    shapes, materials, textures = assemble(assets, appearance, skeleton, times)
    raws, record = bake_levels(shapes, materials, textures, palette, appearance.get('id', ''), levels)
    if keys is not None:
        with scratch_dir('npc-lod-', keep_on_failure=False) as tmp:
            for k in levels:
                path = Path(tmp) / str(k)
                path.write_bytes(raws.get(k, b''))     # an empty marker: the level gives nothing here
                if k == MAP_LEVEL:
                    stored = {n: record[n] for n in record if n != 'levels'}
                    stored['levels'] = {str(k): record['levels'][str(k)]}
                else:
                    stored = {'levels': {str(k): record['levels'].get(str(k))}}
                pool.store(keys[k], path, {'record': stored, 'present': k in raws})
    return raws, record


def fit_disk(candidates, budget, used=0):
    """Which level files ship within BUDGET bytes of level files (all but the map models),
    USED already taken by earlier converters of the same scene. candidates: [(identifier,
    {level: bytes}, priority)] (priority: the level-0 order, higher first). Coarse levels go
    first for every appearance (they save memory and triangles everywhere), level 3 before 2
    (smaller); then level 0 by priority. Returns ({identifier: set of levels}, dropped count)."""
    chosen = {i: {MAP_LEVEL} for i, _, _ in candidates}
    dropped = 0
    for level in (3, 2):
        for identifier, sizes, _ in candidates:
            if level in sizes:
                if used + sizes[level] <= budget:
                    used += sizes[level]
                    chosen[identifier].add(level)
                else:
                    dropped += 1
    for identifier, sizes, _ in sorted(candidates, key=lambda c: -c[2]):
        if 0 in sizes:
            if used + sizes[0] <= budget:
                used += sizes[0]
                chosen[identifier].add(0)
            else:
                dropped += 1
    return chosen, dropped


def publish(id1, models, kinds, settings=None):
    """Write the level files of a converter's residents and merge their table rows.

    models: {record id: record} as the converters keep them; a record carries 'model' (the map
    model path), 'lod' (bake facts) and '_levels' ({level: raw}, popped here). Level 0 ships
    only for the policy's appearances, and every level file only within --npc-lod-disk-mib
    (fit_disk; the scene's earlier rows count): disk is the binding limit (docs/NPC_MODEL_CACHE.md,
    "Disk"). The asset pool keeps every bake either way."""
    settings = settings or SETTINGS
    if settings.get('mode') != 'on':
        for record in models.values():
            record.pop('_levels', None)
        return {'mode': 'off'}
    levels = baked_levels(settings)
    named = named_records(kinds) if settings.get('policy') == 'named' else ()
    listed = read_list(settings['list']) if settings.get('policy') == 'list' else ()
    budget = int(settings.get('disk_mib', DEFAULT_DISK_MIB) * 1024 * 1024)
    path = Path(id1) / MANIFEST
    used = 0
    if path.is_file():
        old, _ = parse_manifest(path.read_text(encoding='ascii'))
        mine = {far_path(i) for i in models}
        used = sum(b for r in old if r['far'] not in mine for k, b in enumerate(r['bytes']) if k != MAP_LEVEL)
    candidates, pending = [], {}
    for identifier, record in sorted(models.items()):
        raws = record.pop('_levels', None)
        if raws is None:
            continue
        if record['model'] != far_path(identifier):
            raise ValueError('Resident model path is not the level table name: ' + record['model'])
        metric = (record.get('lod') or {}).get('head_error')
        if 0 in raws and not uses_near(settings['policy'], identifier, metric, named, listed):
            raws = {k: v for k, v in raws.items() if k != 0}
        pending[identifier] = raws
        candidates.append((identifier, {k: len(v) for k, v in raws.items() if k != MAP_LEVEL},
                           metric['hausdorff'] if metric else 0.0))
    chosen, dropped = fit_disk(candidates, budget, used)
    if dropped:
        print('NPC levels of detail: %d level files left out to stay within %d MiB of level files '
              '(--npc-lod-disk-mib); their actors use the map model there.' % (dropped, budget >> 20), flush=True)
    rows = []
    for identifier, raws in pending.items():
        raws = {k: v for k, v in raws.items() if k in chosen[identifier]}
        rows.append(write_levels(id1, far_path(identifier), raws, 0 in raws))
        models[identifier]['lod_levels'] = {str(k): level_path(far_path(identifier), k) for k in sorted(raws)}
        models[identifier]['near_use'] = 0 in raws
    total = merge_manifest(id1, rows, levels) if rows else None
    return {'mode': 'on', 'levels': list(levels), 'policy': settings['policy'], 'rows': len(rows),
            'flagged': sum(r['use'] for r in rows), 'disk_budget': budget, 'dropped_for_disk': dropped,
            'level_bytes': [sum(r['bytes'][k] for r in rows) for k in range(LEVEL_COUNT)],
            'table_rows': total}


# ---------------------------------------------------------------- the island-wide survey

_survey_state = {}


def _survey_one(task):
    data, palette, identifier, bake_models = task
    import time
    import numpy as np
    from mwad.audit import BSA
    from mwad.paths import child_ci
    from mwad.npc import load_master, outfit
    from npc_geometry import Assets, Skeleton, assemble
    key = str(data)
    if key not in _survey_state:
        _survey_state.clear()
        _survey_state[key] = {'assets': Assets(data, BSA(child_ci(data, 'Morrowind.bsa'))), 'rigs': {},
                              'kinds': load_master(child_ci(data, 'Morrowind.esm'))[0]}
    state = _survey_state[key]
    try:
        appearance = outfit(state['kinds'], identifier)
        rig = appearance['skeleton']
        if rig not in state['rigs']:
            state['rigs'][rig] = Skeleton(state['assets'], rig)
        skeleton = state['rigs'][rig]
        times = skeleton.idle_times(8)[0] if bake_models else np.array([skeleton.idle_times(8)[0][0]])
        started = time.monotonic()
        shapes, materials, textures = assemble(state['assets'], appearance, skeleton, times)
        assembled = round(time.monotonic() - started, 3)
        if not bake_models:
            # The level-1 budget of the rest-pose shapes (the ladder normally settles at 480).
            return identifier, {'head_error': head_error(shapes, quotas_for(shapes, FAR_BUDGETS[0]))}
        raws, record = bake_levels(shapes, materials, textures, palette, identifier, LEVEL_SETS[4])
        record['assemble_seconds'] = assembled
        return identifier, record
    except (ValueError, KeyError) as error:
        return identifier, {'error': str(error)}


def survey(data, palette, out, jobs=None, only=None, bake_models=False):
    """Head metric (and with bake_models every level's size, triangles, errors and bake time) of
    every humanoid NPC record's equipped appearance; the distribution and what each policy selects."""
    from mwad.npc import load_master
    from mwad.paths import child_ci, resolve_data_files
    from build_jobs import resolve_jobs
    from build_parallel import ordered_map
    data = resolve_data_files(Path(data))
    kinds = load_master(child_ci(data, 'Morrowind.esm'))[0]
    ids = sorted(kinds['NPC_']) if only is None else sorted(only)
    palette = Path(palette).read_bytes()
    tasks = [(data, palette, i, bake_models) for i in ids]
    results = dict(ordered_map(_survey_one, tasks, max(1, min(resolve_jobs(jobs), len(tasks)))))
    named = named_records(kinds)
    report = {'records': len(ids), 'threshold': MEASURED_THRESHOLD, 'actors': results,
              'summary': summarize(results, named)}
    Path(out).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return report['summary']


def summarize(results, named):
    import numpy as np
    good = {i: r['head_error'] for i, r in results.items() if r.get('head_error')}
    h = np.array([m['hausdorff'] for m in good.values()]) if good else np.zeros(1)
    cut = np.array([m['cut'] for m in good.values()]) if good else np.zeros(1)

    def pct(a):
        return {str(q): round(float(np.percentile(a, q)), 4) for q in (0, 10, 25, 50, 75, 90, 95, 99, 100)}
    edges = [0, .25, .5, .75, 1, 1.5, 2, 3, 99]
    out = {'measured': len(good), 'errors': sum(1 for r in results.values() if 'error' in r),
           'hausdorff': pct(h), 'cut': pct(cut),
           'hausdorff_histogram': {'%g-%g' % (a, b): int(((h >= a) & (h < b)).sum()) for a, b in zip(edges, edges[1:])},
           'policies': {p: sum(1 for i in good if uses_near(p, i, good[i], named)) for p in ('all', 'named', 'measured')}}
    baked = [r for r in results.values() if r.get('levels')]
    if baked:
        levels = {}
        for k in range(LEVEL_COUNT):
            rows = [r['levels'].get(str(k)) for r in baked]
            have = [x for x in rows if x]
            if not have:
                continue
            def stat(name, sub=None):
                values = [x[name][sub] if sub else x[name] for x in have if x.get(name) is not None]
                return pct(np.array(values)) if values else None
            levels[str(k)] = {'baked': len(have), 'left_out': len(rows) - len(have),
                              'bytes': stat('bytes'), 'triangles': stat('triangles'), 'seconds': stat('seconds'),
                              'bytes_total': int(sum(x['bytes'] for x in have)),
                              'body_hausdorff': stat('body_error', 'hausdorff'),
                              'head_hausdorff': stat('head_error', 'hausdorff')}
        out['levels'] = levels
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('survey')
    s.add_argument('--data-files', type=Path, required=True)
    s.add_argument('--palette', type=Path, required=True)
    s.add_argument('--out', type=Path, required=True)
    s.add_argument('--jobs', type=int)
    s.add_argument('--only', nargs='+', help='NPC record IDs (default: every NPC record)')
    s.add_argument('--only-file', type=Path, help='NPC record IDs, one per line')
    s.add_argument('--bake', action='store_true', help='also bake every level (sizes, errors, bake time; slower)')
    c = sub.add_parser('check')
    c.add_argument('id1', type=Path)
    a = p.parse_args()
    if a.command == 'survey':
        only = {i.casefold() for i in a.only} if a.only else None
        if a.only_file:
            only = (only or set()) | read_list(a.only_file)
        print(json.dumps(survey(a.data_files, a.palette, a.out, a.jobs, only, a.bake), indent=1))
    else:
        print(json.dumps(check(a.id1), indent=1))


if __name__ == '__main__':
    main()
