"""Island-wide height audit of a CHIM world and its frame maps (CHIM-RED-MOUNTAIN-SOLID-SKY-43).

Red Mountain's ground reaches 4,730 frame-local units while the chunk terrain and the frame maps closed at
the fixed terrain ceiling (2,048): faces lay outside their node boxes (Quake's renderer then projects them
unclipped: the view broke apart over 2,048), the frame map's bounds ended under the ground and the player
start was traced from inside the mountain. This audit compares, per frame:

- terrain: every chunk's highest ground (the frame record's zmax) against its terrain image's head node top
  (the box the renderer culls and clips by) and its faces' heights against their node boxes
  (chim.validate.world_tree does the face check for every chunk in the validate stage too);
- placements: every placed model's top against its chunk's node box top (its leaves' boxes cull it);
- frame map (with --maps): the map's world bounds top against the frame's ceiling for its highest ground and
  placements (chim.terrain.frame_ceiling), and the player start against the frame's own ground under it (traced from
  above the highest ground, chim.frame_map.frame_ground).

Prints one line per frame that fails (frame id, cell, the heights and the check) and a summary; exit 1 on a
failure. Read only; each frame is read from its own files (any world fits memory), frames run on a process pool
(--jobs, default all cores).

    python3 tools/chim/height_audit.py WORLD_DIR [--maps ID1/maps] [--jobs N] [--json OUT]
"""
import argparse
import json
import os
import re
import struct
import sys
import time
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]

from chim import format as F                                    # noqa: E402
from chim.terrain import TERRAIN_CEILING, frame_ceiling        # noqa: E402

_WORLD = None
TOLERANCE = 0.5             # stored bounds are shorts rounded outward
START_TOLERANCE = 2.0       # the start's ground against the traced ground


def chunk_rows(frame, chunks):
    """[(cx, cy, zmax, head node top, faces over their node)] of a frame's chunks."""
    from chim.validate import face_heights
    out = []
    for c in chunks:
        lumps = F.read_brush_image(c['image'])
        nodes = list(struct.iter_unpack('<ihh6h2H', lumps[5]))
        zs = face_heights(lumps)
        over = sum(1 for n in nodes for f in range(n[9], n[9] + n[10])
                   if f < len(zs) and zs[f] is not None and (zs[f][1] > n[8] + TOLERANCE or zs[f][0] < n[5] - TOLERANCE))
        out.append((c['cx'], c['cy'], c['zmax'], nodes[0][8] if nodes else None, over))
    return out


def map_rows(path):
    """(world bounds (mins, maxs), {frame cell: start origin}) of a frame map."""
    lumps = F.read_brush_image(Path(path).read_bytes())
    m = struct.unpack('<9f7i', lumps[14][:64])
    text = lumps[0].rstrip(b'\0').decode('latin-1')
    rows = [dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', block)) for block in re.findall(r'\{([^{}]*)\}', text)]
    world = rows[0] if rows else {}
    start = next((r for r in rows if r.get('classname') == 'info_player_start'), None)
    return (m[0:3], m[3:6]), world.get('_chim_frame'), start


def audit_frame(index):
    """Failures of frame INDEX of the loaded world: [(check, text)], plus its numbers."""
    from chim.validate import load_frame
    row, models = load_frame(_WORLD['dir'], index)        # this frame's files only: the island fits any memory
    path, frame, chunks = row
    rows = chunk_rows(frame, chunks)
    zmax = max(r[2] for r in rows)
    fails = []
    ptop = None
    for c, (cx, cy, z, top, over) in zip(chunks, rows):
        if top is None or z > top + TOLERANCE:
            fails.append(('terrain-bounds', 'chunk %d,%d ground up to %d over its node box top %s' % (cx, cy, z, top)))
        if over:
            fails.append(('terrain-faces', 'chunk %d,%d: %d faces outside their node boxes' % (cx, cy, over)))
        # a placement is linked into its chunk's leaves; a leaf box under the model's top culls it while its top
        # is in view
        tall = [r for r in c.get('owned', ()) if top is not None and r['box'][1][2] > top + TOLERANCE]
        for r in c.get('owned', ()):
            ptop = r['box'][1][2] if ptop is None else max(ptop, r['box'][1][2])
        if tall:
            worst = max(tall, key=lambda r: r['box'][1][2])
            fails.append(('placement-bounds', 'chunk %d,%d: %d placements over its node box top %s (ref %s top %d)'
                          % (cx, cy, len(tall), top, worst['ref'], worst['box'][1][2])))
    info = {'id': frame.get('id', path), 'cell': list(frame['cell']), 'zmax': zmax, 'placement_top': ptop,
            'zmin': min(c['zmin'] for c in chunks), 'over_ceiling': zmax > TERRAIN_CEILING}
    maps = _WORLD['maps'].get(tuple(frame['cell']))
    if maps is not None:
        from chim.frame_map import frame_ground
        name, (bounds, start) = maps
        info['map'], info['map_top'] = name, bounds[1][2]
        want = frame_ceiling(zmax, ptop)
        if bounds[1][2] + TOLERANCE < want:
            fails.append(('map-bounds', 'map %s world top %.0f under %d (ground %d, placements up to %s)'
                          % (name, bounds[1][2], want, zmax, ptop)))
        if start is not None:
            sx, sy, sz = (float(v) for v in start.get('origin', '0 0 0').split())
            ground = frame_ground({'frames': [row], 'models': models}, frame['cell'], (sx, sy))
            info['start_z'], info['ground'] = sz, ground
            # START_HEIGHT over the ground at the start (tools/chim/frame_map.py region_task), frame origin z 0
            if ground is None or abs(sz - 24.0 - ground) > START_TOLERANCE:
                fails.append(('map-start', 'map %s start z %.1f, ground under it %s' % (name, sz, ground)))
    return info, fails


def load_maps(maps_dir, cells):
    """{frame cell: (map name, (bounds, start))} of the region frame maps in MAPS_DIR (by their _chim_frame)."""
    out = {}
    for p in sorted(Path(maps_dir).glob('*.chim')):
        try:
            bounds, frame, start = map_rows(p)
        except Exception:                                   # not a region frame map image: not ours to judge
            continue
        if not frame:
            continue
        cell = tuple(int(v) for v in frame.split())
        if cell in cells:
            out[cell] = (p.name, (bounds, start))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('world', help='CHIM world folder (holds chim/world.cwi)')
    ap.add_argument('--maps', help='the image\'s id1/maps folder: also audit the region frame maps')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--json', help='write the per-frame report here')
    ap.add_argument('--cells', help='only these cells, "x,y;x,y"')
    a = ap.parse_args(argv)
    global _WORLD
    t0 = time.time()
    _, files, _, _ = F.read_index((Path(a.world) / 'chim' / 'world.cwi').read_bytes())
    cells = [tuple(f['cell']) for f in files if f['kind'] == b'FRAM']
    maps = load_maps(a.maps, set(cells)) if a.maps else {}
    _WORLD = {'dir': a.world, 'maps': maps}
    wanted = None if not a.cells else {tuple(int(v) for v in c.split(',')) for c in a.cells.split(';')}
    indices = [i for i, c in enumerate(cells) if wanted is None or c in wanted]
    jobs = max(1, min(a.jobs, len(indices)))
    print('height audit: %d frames, %d frame maps, %d workers (asked %d)' % (len(indices), len(maps), jobs, a.jobs),
          flush=True)
    def progress(it):
        out = []
        for n, r in enumerate(it, 1):
            out.append(r)
            if n % 100 == 0 or n == len(indices):
                print('height audit: %d of %d frames, %.0f s' % (n, len(indices), time.time() - t0), flush=True)
        return out
    if jobs > 1:
        import multiprocessing
        with multiprocessing.get_context('fork').Pool(jobs) as pool:
            results = progress(pool.imap(audit_frame, indices, chunksize=4))
    else:
        results = progress(audit_frame(i) for i in indices)
    failed = 0
    for info, fails in results:
        for check, text in fails:
            print('FAIL %s cell %d,%d (zmin %d zmax %d): %s: %s' % (info['id'], *info['cell'], info['zmin'], info['zmax'],
                                                                 check, text))
        failed += bool(fails)
    high = sum(1 for info, _ in results if info['over_ceiling'])
    top = max(results, key=lambda r: r[0]['zmax'])[0]
    ptops = [r[0] for r in results if r[0]['placement_top'] is not None]
    if ptops:
        p = max(ptops, key=lambda i: i['placement_top'])
        print('highest ground %d (frame %s cell %d,%d); highest placement top %d (frame %s cell %d,%d)'
              % (top['zmax'], top['id'], *top['cell'], p['placement_top'], p['id'], *p['cell']))
    near = sum(1 for info, _ in results if info['zmax'] > TERRAIN_CEILING - 256)
    print('frames with ground within 256 of the %d ceiling or over it: %d' % (TERRAIN_CEILING, near))
    print('height audit: %d frames, %d with ground over the %d ceiling, %d failing; took %.1f s, %d cores'
          % (len(results), high, TERRAIN_CEILING, failed, time.time() - t0, jobs))
    if a.json:
        Path(a.json).write_text(json.dumps([dict(info, fails=fails) for info, fails in results], indent=1) + '\n',
                                encoding='utf-8', newline='\n')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
