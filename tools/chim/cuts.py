# SPDX-License-Identifier: GPL-3.0-only
"""CHIM distance cuts and the fog: whole-structure cut groups and the fog rule.

Why (docs/bugs/CHIM-BRIDGE-POP-PIECES-44.md, HORIZON-HOLES-31, VIVEC-DISTANT-BRIDGES-32,
HORIZON-POP-29): a placement left out while the fog in front of it is still see-through pops in;
pieces of one long structure (a bridge, Vivec's walkways, a town wall, the Ghostfence) left out one
at a time leave a structure with its middle missing.

Two rules, both selectable in the engine (aw_fog.c):

- the fog rule (aw_cull + 8, dbg fog rule): no distance cut nearer than the fog's full-opacity depth. The fog
  table (AW_FogDepths) is a linear ramp from 44 % of the fog distance D (level 1) to D (level 15,
  every colour one), so a cut at 40-85 % of D (the size-scaled presets aw_cull 3, 4 and 6) leaves out
  pieces that are 0 to 73 % fogged;
- whole-structure cuts (aw_cull + 16, dbg cut groups): placements that form one long structure share one cut,
  made on the structure's box, so the structure is drawn, fogged and left out as one piece.

The structures are found here from the frame's own data, not from a hand list: placements of the
same mesh family (model names with their variant suffixes and trailing index numbers removed;
one name's stem a prefix of the other's, at least three name tokens) whose drawn boxes touch, joined
transitively; a joined set counts as a structure when it is longer than its longest member
(STRUCTURE_SPAN_FACTOR) and at least STRUCTURE_MIN_SPAN units long.

Sidecar (big-endian, as the 68k reads it), maps/<frame map>.cut beside maps/<frame map>.bsp, like
the far terrain (chim.far): not part of the CHIM world, its own version; an engine without it, or a
frame map without one, cuts every placement on its own (the method before).

    0  char[4]  'CHCT'
    4  u16      version (1)
    6  u16      header bytes (24)
    8  i16, i16 the frame's centre cell (must match the frame map's frame)
    12 u32      structures
    16 u32      members
    20 u32      CRC-32 (zlib) of everything after the header
    24 i16[6]   per structure: its cut box (frame-local mins, maxs: the union of its members' drawn boxes)
    then        per member, by placement id ascending: u32 placement id, u16 structure, u16 0
"""
import re
import struct
import zlib
from pathlib import Path

MAGIC = b'CHCT'
VERSION = 1
HEADER = struct.Struct('>4sHHhhIII')        # 24 bytes
BOX = struct.Struct('>6h')                  # 12 bytes
MEMBER = struct.Struct('>IHH')              # 8 bytes
SUFFIX = '.cut'
MAX_STRUCTURES = 65535

TOUCH_GAP = 64              # local units: drawn boxes this close join (Vivec's bridge pieces stand 51 apart)
MIN_FAMILY_TOKENS = 3       # a stem shorter than this joins only its own exact stem
STRUCTURE_SPAN_FACTOR = 0       # a structure's long side against its longest member's (0: any)
STRUCTURE_MIN_SPAN = 256    # local units (an eighth of a cell)

# The engine's fog (aw_fog.c AW_FogDepths): level L (1..15) from depth D*(10+L)/25; 15 is one colour.
FOG_LEVELS = 15
# aw_fog.c size_cut_share (aw_cull 3 "Light", 4 "Strong"; 6 = 4 + the detail step), by radius class.
SIZE_CLASSES = (32, 128, 512)
SIZE_CUT_SHARE = {1: (.50, .75, 1.0, 1.0), 2: (.40, .60, .85, 1.0)}
DETAIL_STEP_SHARE = .5      # aw_cull 5/6: far detail step from this share of D
FAR_PLANE_MARGIN = 16       # AW_CullBegin: far plane at D + 16


# ---------------------------------------------------------------- the fog and the cuts

def fog_level(depth, distance):
    """The fog level (0..15) the engine gives a pixel at view depth `depth` with fog distance `distance`."""
    level = int((25.0 * depth / distance) - 10 + 1e-9)
    return max(0, min(FOG_LEVELS, level))


def fog_full_depth(distance):
    """The depth from which the fog is fully opaque (level 15): the fog distance itself."""
    return float(distance)


def size_class(radius):
    return sum(1 for edge in SIZE_CLASSES if radius >= edge)


def size_share(preset, radius, fog_rule=False):
    """Share of the fog distance past which a placement's near side is cut (aw_cull preset 1 Light / 2 Strong;
    any other: no size cut, 1). With the fog rule no share is below 1."""
    share = SIZE_CUT_SHARE[preset][size_class(radius)] if preset in SIZE_CUT_SHARE else 1.0
    return max(share, 1.0) if fog_rule else share


def aw_cull_preset(mode):
    """aw_cull value -> (size preset, detail step)."""
    return (1 if mode == 3 else 2 if mode in (4, 6) else 0), mode in (5, 6)


def cut_depths(mode, distance, fog_rule=False):
    """Every distance cut of aw_cull `mode` at fog distance D, as (name, near-side depth): the depth past
    which the cut removes geometry (fog-exact skipping, which changes no pixel, is not a cut)."""
    preset, detail = aw_cull_preset(mode)
    out = [] if mode == 0 else [('far plane', distance + FAR_PLANE_MARGIN)]
    if preset:
        for k, edge in enumerate((0,) + SIZE_CLASSES):
            out.append(('size cut, radius %d and over' % edge, distance * size_share(preset, edge, fog_rule)))
    if detail:
        out.append(('far detail step', distance * (1.0 if fog_rule else DETAIL_STEP_SHARE)))
    return out


def fog_cut_failures(settings, structures=None, members=None, modes=(), fog_rule=True):
    """Distance cuts nearer than the fog end (its full-opacity depth), as failure lines; [] when none.

    settings: the CHIM world's settings (draw_distance = the fog distance it is built for, hysteresis);
    structures/members: a frame's cut groups (structure boxes, {pid: (structure, member box)});
    modes: aw_cull values whose cuts to check with the fog rule as given."""
    fails = []
    distance = float(settings['draw_distance'])
    full = fog_full_depth(distance)
    if not distance > 0:
        fails.append('draw distance %r: no fog end' % settings['draw_distance'])
        return fails
    ring = distance + float(settings['hysteresis'])
    if ring < full:
        fails.append('chunk ring (draw distance %g + hysteresis %g = %g) ends before the fog end %g'
                     % (distance, settings['hysteresis'], ring, full))
    for mode in modes:
        for name, depth in cut_depths(mode, distance, fog_rule):
            if depth < full:
                fails.append('aw_cull %d %s at %g, before the fog end %g (fog level %d of 15 there)'
                             % (mode, name, depth, full, fog_level(depth, distance)))
    if structures is not None and members:
        for pid, (k, box) in sorted(members.items()):
            if not 0 <= k < len(structures):
                fails.append('placement %d: structure %d does not exist' % (pid, k))
                continue
            sb = structures[k]
            if any(box[0][i] < sb[0][i] or box[1][i] > sb[1][i] for i in range(3)):
                fails.append('placement %d reaches outside its structure %d\'s cut box: it would be cut on its own'
                             % (pid, k))
    return fails


# ---------------------------------------------------------------- structures

_INDEX_TOKEN = re.compile(r'^\d+[a-z]?$')


def stem(name):
    """A model name's mesh stem: variant suffixes (@..., #n), the folder kept, trailing index tokens removed."""
    base = name.split('@')[0].split('#')[0].lower()
    tokens = base.split('_')
    while len(tokens) > 1 and _INDEX_TOKEN.match(tokens[-1]):
        tokens.pop()
    return tuple(tokens)


def same_family(a, b):
    """Two stems of one mesh family: equal, or one a token prefix of the other of at least MIN_FAMILY_TOKENS."""
    if a == b:
        return True
    n = min(len(a), len(b))
    return n >= MIN_FAMILY_TOKENS and a[:n] == b[:n]


def touch(a, b, gap=TOUCH_GAP):
    return all(a[0][i] - gap <= b[1][i] and b[0][i] - gap <= a[1][i] for i in range(3))


def union_box(boxes):
    boxes = list(boxes)
    return (tuple(min(b[0][i] for b in boxes) for i in range(3)), tuple(max(b[1][i] for b in boxes) for i in range(3)))


def long_side(box):
    return max(box[1][0] - box[0][0], box[1][1] - box[0][1])


def structures(placements, names, gap=TOUCH_GAP, span_factor=STRUCTURE_SPAN_FACTOR, min_span=STRUCTURE_MIN_SPAN):
    """The long structures among a frame's placements.

    placements: [{'pid', 'model', 'box'}] (box: drawn box (mins, maxs), frame-local); names: model id -> name.
    Returns [{'box', 'members': [pid...], 'stems': [...], 'span'}], ordered by the first member's pid."""
    rows = [p for p in placements]
    stems = [stem(names[p['model']]) for p in rows]
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    # neighbours through a coarse grid of the boxes' footprints
    grid = {}
    cell = 256
    for i, p in enumerate(rows):
        (x0, y0, _), (x1, y1, _) = p['box']
        for gx in range(int((x0 - gap) // cell), int((x1 + gap) // cell) + 1):
            for gy in range(int((y0 - gap) // cell), int((y1 + gap) // cell) + 1):
                grid.setdefault((gx, gy), []).append(i)
    for bucket in grid.values():
        for a in range(len(bucket)):
            i = bucket[a]
            for j in bucket[a + 1:]:
                if find(i) != find(j) and same_family(stems[i], stems[j]) and touch(rows[i]['box'], rows[j]['box'], gap):
                    parent[find(i)] = find(j)
    sets = {}
    for i in range(len(rows)):
        sets.setdefault(find(i), []).append(i)
    out = []
    for idx in sets.values():
        if len(idx) < 2:
            continue
        box = union_box(rows[i]['box'] for i in idx)
        span = long_side(box)
        longest = max(long_side(rows[i]['box']) for i in idx)
        if span < min_span or span < span_factor * longest:
            continue
        out.append({'box': box, 'members': sorted(rows[i]['pid'] for i in idx),
                    'stems': sorted({'_'.join(stems[i]) for i in idx}), 'span': span})
    out.sort(key=lambda s: s['members'][0])
    if len(out) > MAX_STRUCTURES:
        raise ValueError('More than %d structures in one frame' % MAX_STRUCTURES)
    return out


# ---------------------------------------------------------------- the sidecar

def encode(cell, found):
    """The sidecar's bytes for a frame's structures (structures())."""
    if len(found) > MAX_STRUCTURES:
        raise ValueError('More than %d structures in one frame' % MAX_STRUCTURES)
    members = sorted((pid, k) for k, s in enumerate(found) for pid in s['members'])
    if len({pid for pid, _ in members}) != len(members):
        raise ValueError('A placement belongs to two structures')
    body = b''.join(BOX.pack(*s['box'][0], *s['box'][1]) for s in found)
    body += b''.join(MEMBER.pack(pid, k, 0) for pid, k in members)
    return HEADER.pack(MAGIC, VERSION, HEADER.size, int(cell[0]), int(cell[1]), len(found), len(members),
                       zlib.crc32(body) & 0xFFFFFFFF) + body


def decode(data):
    """(header dict, [structure box], {pid: structure}); ValueError when it is not a version 1 sidecar."""
    if len(data) < HEADER.size:
        raise ValueError('Cut groups file too short')
    magic, version, hbytes, cx, cy, n, m, crc = HEADER.unpack_from(data)
    if magic != MAGIC or version != VERSION or hbytes != HEADER.size:
        raise ValueError('Not a cut groups file of version 1')
    if len(data) != HEADER.size + n * BOX.size + m * MEMBER.size:
        raise ValueError('Cut groups file size does not match its counts')
    body = data[HEADER.size:]
    if zlib.crc32(body) & 0xFFFFFFFF != crc:
        raise ValueError('Cut groups CRC mismatch')
    boxes = []
    for k in range(n):
        v = BOX.unpack_from(body, k * BOX.size)
        boxes.append((tuple(v[:3]), tuple(v[3:])))
    members, last = {}, -1
    for k in range(m):
        pid, s, _ = MEMBER.unpack_from(body, n * BOX.size + k * MEMBER.size)
        if pid <= last or s >= n:
            raise ValueError('Cut groups members out of order or out of range')
        members[pid] = s
        last = pid
    return {'cell': (cx, cy), 'structures': n, 'members': m}, boxes, members


def file_name(cell):
    """Name of a frame's cut groups in the CHIM output folder (cuts/): cuts/<cx>_<cy>.cut."""
    return '%d_%d%s' % (cell[0], cell[1], SUFFIX)


def sidecar_name(frame_map):
    """maps/<name>.bsp -> maps/<name>.cut (the engine looks for it beside the frame map)."""
    p = Path(frame_map)
    return str(p.with_suffix(SUFFIX)).replace('\\', '/')


# ---------------------------------------------------------------- reading a world

def model_names(chim_root):
    from chim import reach  # noqa: F401 (reads world formats 0.8 and 0.9)
    from chim import format as F
    _, _, models, _ = F.read_index((Path(chim_root) / 'world.cwi').read_bytes())
    return [m['name'] for m in models]


def frame_placements(frame_path):
    """(frame dict, [placement record]) of every placement one frame owns (reach copies left out), from its
    frame file and the sector files beside it."""
    from chim import reach  # noqa: F401 (reads world formats 0.8 and 0.9)
    from chim import format as F
    frame_path = Path(frame_path)
    frame, _, _ = F.read_frame(frame_path.read_bytes())
    rows = []
    for sector in sorted(frame_path.parent.rglob('s*.ccs')):
        for rec in F.read_sector(sector.read_bytes()):
            if rec['kind'] == b'CHNK':
                from chim.reach import read_chunk_any as read_chunk     # format 0.8 and 0.9 too
                rows += read_chunk(rec['data'])['owned']
    rows.sort(key=lambda r: r['pid'])
    return frame, rows


def frame_structures(frame_path, names):
    frame, rows = frame_placements(frame_path)
    return frame, rows, structures(rows, names)


_NAMES = {}


def _world_names(chim_root):
    """Model names of a world, read once per worker process."""
    key = str(chim_root)
    if key not in _NAMES:
        from chim import reach  # noqa: F401 (reads world formats 0.8 and 0.9)
        from chim import format as F
        settings, _, models, _ = F.read_index((Path(chim_root) / 'world.cwi').read_bytes())
        _NAMES.clear()
        _NAMES[key] = (settings, [m['name'] for m in models])
    return _NAMES[key]


def frame_failures(frame, rows, found, settings):
    """The fog check of one frame (fog_cut_failures), each line naming the frame."""
    by_pid = {r['pid']: r for r in rows}
    members = {pid: (k, by_pid[pid]['box']) for k, s in enumerate(found) for pid in s['members']}
    return ['frame %d,%d: %s' % (frame['cell'][0], frame['cell'][1], line)
            for line in fog_cut_failures(settings, [s['box'] for s in found], members)]


def _write_task(task):
    frame_path, chim_root, out_path = task
    settings, names = _world_names(chim_root)
    frame, rows, found = frame_structures(frame_path, names)
    data = encode(frame['cell'], found)
    Path(out_path).write_bytes(data)
    import hashlib
    return {'cell': list(frame['cell']), 'structures': len(found), 'members': sum(len(s['members']) for s in found),
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'failures': frame_failures(frame, rows, found, settings)}


def write_groups(out, jobs=1):
    """OUT/cuts/<cx>_<cy>.cut for every frame of the world in OUT/chim; the receipt rows, frame order. One frame
    per worker task with JOBS > 1 (each frame is independent), largest first through the shared pool.

    The fog check runs on every frame (fog_cut_failures: the chunk ring against the fog end, every structure's
    box against its members): a world with a cut nearer than its fog end is refused (ValueError naming the
    frames and cuts)."""
    rows = _write_groups(out, jobs)
    fails = [line for r in rows for line in r.pop('failures')]
    if fails:
        raise ValueError('CHIM distance cuts nearer than the fog end (%d): %s' % (len(fails), '; '.join(fails[:10])))
    return rows


def _write_groups(out, jobs=1):
    root = Path(out) / 'chim'
    frames = sorted(root.rglob('frame.ccf'))
    folder = Path(out) / 'cuts'
    folder.mkdir(parents=True, exist_ok=True)
    tasks = []
    for path in frames:
        from chim import reach  # noqa: F401 (reads world formats 0.8 and 0.9)
        from chim import format as F
        frame, _, _ = F.read_frame(path.read_bytes())
        tasks.append((str(path), str(root), str(folder / file_name(frame['cell']))))
    from build_parallel import ordered_map, stage_ceiling
    jobs = stage_ceiling(jobs)
    if jobs > 1 and len(tasks) > 1:
        return list(ordered_map(_write_task, tasks, min(jobs, len(tasks)),
                                cost=lambda t: Path(t[0]).stat().st_size))
    return [_write_task(t) for t in tasks]


# ---------------------------------------------------------------- cost on paper

class PaperFrame:
    """A frame's placements prepared for drawn_counts (numpy arrays, one row per owned placement)."""

    def __init__(self, rows, found, frame, faces=None):
        import numpy as np
        self.frame = frame
        g, (lx, ly) = frame['grain'], frame['low']
        lo = np.array([r['box'][0] for r in rows], float).reshape(-1, 3)
        hi = np.array([r['box'][1] for r in rows], float).reshape(-1, 3)
        org = np.array([r['origin'] for r in rows], float).reshape(-1, 3)
        # the squares of the chunks a drawn box touches (residency: any of them active)
        self.chunk_lo = np.stack([lx + np.floor((lo[:, 0] - lx) / g) * g, ly + np.floor((lo[:, 1] - ly) / g) * g], 1)
        self.chunk_hi = np.stack([lx + (np.floor((hi[:, 0] - lx) / g) + 1) * g,
                                  ly + (np.floor((hi[:, 1] - ly) / g) + 1) * g], 1)
        corners = np.stack([np.stack([np.where(k & 1, hi[:, 0], lo[:, 0]), np.where(k & 2, hi[:, 1], lo[:, 1]),
                                      np.where(k & 4, hi[:, 2], lo[:, 2])], 1) for k in range(8)], 1)
        self.radius = np.sqrt(((corners - org[:, None, :]) ** 2).sum(2)).max(1)     # the model's sphere at its origin
        self.origin = org[:, :2]
        self.faces = np.array([(faces or {}).get(r['model'], 0) for r in rows], float)
        # structure members: the structure's box and its half diagonal
        self.group = np.full(len(rows), -1)
        index = {r['pid']: i for i, r in enumerate(rows)}
        boxes = []
        for k, s in enumerate(found):
            boxes.append(s['box'])
            for pid in s['members']:
                self.group[index[pid]] = k
        self.group_lo = np.array([b[0] for b in boxes], float).reshape(-1, 3)
        self.group_hi = np.array([b[1] for b in boxes], float).reshape(-1, 3)
        self.group_radius = .5 * np.sqrt(((self.group_hi - self.group_lo) ** 2).sum(1))

    def shares(self, radius, preset, fog_rule):
        import numpy as np
        if not preset:
            return np.ones_like(radius)
        table = np.array(SIZE_CUT_SHARE[preset])
        share = table[(radius >= SIZE_CLASSES[0]).astype(int) + (radius >= SIZE_CLASSES[1]) + (radius >= SIZE_CLASSES[2])]
        return np.maximum(share, 1.0) if fog_rule else share


def _box_near(lo, hi, viewer):
    import numpy as np
    dx = np.maximum(np.maximum(lo[:, 0] - viewer[0], 0), viewer[0] - hi[:, 0])
    dy = np.maximum(np.maximum(lo[:, 1] - viewer[1], 0), viewer[1] - hi[:, 1])
    return np.sqrt(dx * dx + dy * dy)


def drawn_counts(paper, viewer, distance, hysteresis, mode=4, fog_rule=False, groups=False):
    """(placements, faces) inside the distance cuts from `viewer` (all around: no frustum, no occlusion, no
    fog-exact skipping; horizontal distances), as the engine's tests decide them (aw_fog.c AW_ModelVisible,
    AW_BrushPassFar, the structure test AW_PassVisible) for resident placements (chunk ring)."""
    import numpy as np
    preset, _ = aw_cull_preset(mode)
    resident = _box_near(paper.chunk_lo, paper.chunk_hi, viewer) <= distance + hysteresis
    near = np.sqrt(((paper.origin - np.asarray(viewer)) ** 2).sum(1)) - paper.radius
    radius = paper.radius
    if groups and len(paper.group_radius):
        member = paper.group >= 0
        gnear = _box_near(paper.group_lo, paper.group_hi, viewer)
        near = np.where(member, gnear[np.maximum(paper.group, 0)], near)
        radius = np.where(member, paper.group_radius[np.maximum(paper.group, 0)], radius)
    keep = resident.copy()
    if mode:
        keep &= near <= distance + FAR_PLANE_MARGIN
    if preset:
        keep &= near <= distance * paper.shares(radius, preset, fog_rule)
    return int(keep.sum()), float(paper.faces[keep].sum())


def cost_report(frame_path, chim_root, distance=540.0, hysteresis=96.0, step=128, mode=4, faces=None):
    """The cost on paper of the fog rule and of whole-structure cuts in one frame: placements and faces inside
    the cuts per viewpoint (a grid every `step` units over the frame's own cells), for aw_cull `mode`
    (default 4, Strong) and aw_cull 1 (Full) for reference."""
    import statistics
    names = model_names(chim_root)
    frame, rows, found = frame_structures(frame_path, names)
    if faces is None:
        faces = {}
    g = frame['grain']
    lx, ly = frame['low']
    span_x, span_y = frame['nx'] * g, frame['ny'] * g
    # the frame less a margin of half a cell on every side (where its own cells are)
    own = min(span_x, span_y) - 2048
    x0, y0 = lx + (span_x - own) / 2, ly + (span_y - own) / 2
    variants = [('A aw_cull %d, per placement (today)' % mode, mode, False, False),
                ('B fog rule', mode, True, False),
                ('C structures', mode, False, True),
                ('D fog rule + structures', mode, True, True),
                ('E aw_cull 1 Full, per placement', 1, False, False),
                ('F aw_cull 1 Full + structures', 1, False, True)]
    table = {v[0]: ([], []) for v in variants}
    paper = PaperFrame(rows, found, frame, faces)
    k = 0
    for i in range(int(own // step)):
        for j in range(int(own // step)):
            viewer = (x0 + (i + .5) * step, y0 + (j + .5) * step)
            k += 1
            for name, m, rule, grp in variants:
                n, f = drawn_counts(paper, viewer, distance, hysteresis, m, rule, grp)
                table[name][0].append(n)
                table[name][1].append(f)
    base = table[variants[0][0]]
    out = {'frame': list(frame['cell']), 'placements': len(rows), 'structures': len(found),
           'structure_members': sum(len(s['members']) for s in found),
           'largest_structures': [{'members': len(s['members']), 'span': s['span'], 'stems': s['stems'][:4]}
                                  for s in sorted(found, key=lambda s: -len(s['members']))[:8]],
           'viewpoints': k, 'distance': distance, 'variants': {}}
    for name, _, _, _ in variants:
        n, f = table[name]
        out['variants'][name] = {
            'placements_mean': round(statistics.mean(n), 1), 'placements_p95': sorted(n)[int(.95 * (len(n) - 1))],
            'faces_mean': round(statistics.mean(f), 1) if faces else None,
            'placements_vs_A': '%+.1f %%' % (100.0 * (sum(n) - sum(base[0])) / max(1, sum(base[0]))),
            'faces_vs_A': ('%+.1f %%' % (100.0 * (sum(f) - sum(base[1])) / max(1, sum(base[1])))) if faces else None}
    return out


def main(argv=None):
    import argparse
    import json
    ap = argparse.ArgumentParser(description='CHIM whole-structure cut groups and the fog rule (cost on paper, '
                                             'sidecar writing, the fog check).')
    ap.add_argument('world', help='a CHIM output folder (holding chim/)')
    ap.add_argument('--report', action='append', metavar='CX,CY',
                    help='cost report for this frame (repeatable; --report=-3,-2 for a negative cell)')
    ap.add_argument('--faces', action='store_true', help='count faces too (decodes every model the frames place)')
    ap.add_argument('--write', action='store_true', help='write OUT/cuts/<cx>_<cy>.cut for every frame')
    ap.add_argument('--jobs', type=int, default=1)
    a = ap.parse_args(argv)
    root = Path(a.world) / 'chim'
    if a.write:
        rows = write_groups(a.world, a.jobs)
        print(json.dumps({'frames': len(rows), 'structures': sum(r['structures'] for r in rows),
                          'members': sum(r['members'] for r in rows)}))
    for spec in a.report or ():
        cx, cy = (int(v) for v in spec.split(','))
        from chim.world import frame_dir, frame_subdir
        path = root / 'frames' / frame_dir((cx, cy)) / frame_subdir((cx, cy)) / 'frame.ccf'
        faces = None
        if a.faces:
            from chim import format as F
            from chim.stats import faces_of
            _, files, mdir, _ = F.read_index((root / 'world.cwi').read_bytes())
            _, rows = frame_placements(path)
            faces = {}
            for i in {r['model'] for r in rows}:
                e = mdir[i]
                with open(root / files[e['file']]['path'], 'rb') as fh:
                    fh.seek(e['offset'])
                    faces[i] = faces_of(fh.read(e['bytes']))
        print(json.dumps(cost_report(path, root, faces=faces), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
