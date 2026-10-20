# SPDX-License-Identifier: GPL-3.0-only
"""The heaviest CHIM frames of a build and the cells to check them with, before a converter change is merged.

A converter change that touches many meshes (a collision rule, a mesh method, a recipe for every cell) changes the
memory of every frame that places them. The CHIM heap gate finds a frame over the zone only at the end of the CHIM
stage of a full build (2 h 38 min for v0.0.46-dev1, CHIM-HULL-SURFACE-HEAP-46). This tool reads the last build's
CHIM world (chim-heap.json, chim-regions.json) and prints the frames closest to the zone, with the cell list of those
frames and their neighbours in the form tools/chim_build.py --chim-regions-cells takes: build that list with the
change (minutes) and the heap gate answers before the merge.

    python tools/chim_heaviest_frames.py WORLD_DIR [--headroom-kib 256] [--top 12] [--json]

WORLD_DIR: a build's chim-world folder. Frames with less than --headroom-kib KiB headroom, at least the --top
tightest. Prints one line per frame (peak, headroom) and the cell list last.
"""
import argparse
import json
import sys
from pathlib import Path


def heaviest(heap, headroom_bytes, top):
    """The frames of a chim-heap.json report closest to the zone: every frame under headroom_bytes of headroom, at
    least the `top` tightest; tightest first. Rows: (frame path, peak bytes, headroom bytes)."""
    rows = sorted(((f['frame'], int(f['peak_bytes']), int(f['headroom_bytes'])) for f in heap['frames']),
                  key=lambda r: r[2])
    return [r for k, r in enumerate(rows) if k < top or r[2] < headroom_bytes]


def frame_cell(path):
    """frames/x+17/y+04/frame.ccf -> (17, 4)."""
    parts = Path(path).parts
    return int(parts[1][1:]), int(parts[2][1:])


def check_cells(rows, regions):
    """The cells of the frames in rows and their eight neighbours that are CHIM cells of the build, with their kind
    (chim-regions.json cells: 'x,y' -> {'kind': land|seabed|ocean}), as --chim-regions-cells takes them."""
    cells = regions['cells']
    out = {}
    for path, _, _ in rows:
        x, y = frame_cell(path)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                key = '%d,%d' % (x + dx, y + dy)
                if key in cells:
                    out[key] = cells[key]['kind'][0]
    return ' '.join('%s:%s' % (k, out[k]) for k in sorted(out, key=lambda k: tuple(int(v) for v in k.split(','))))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('world', help="a build's chim-world folder (chim-heap.json, chim-regions.json)")
    ap.add_argument('--headroom-kib', type=int, default=256, help='frames with less headroom than this (KiB)')
    ap.add_argument('--top', type=int, default=12, help='at least this many of the tightest frames')
    ap.add_argument('--json', action='store_true', help='print the frames and the cell list as JSON')
    a = ap.parse_args(argv)
    world = Path(a.world)
    heap = json.loads((world / 'chim-heap.json').read_text(encoding='utf-8'))
    regions = json.loads((world / 'chim-regions.json').read_text(encoding='utf-8'))
    rows = heaviest(heap, a.headroom_kib * 1024, a.top)
    cells = check_cells(rows, regions)
    if a.json:
        print(json.dumps({'frames': [{'frame': f, 'peak_bytes': p, 'headroom_bytes': h} for f, p, h in rows],
                          'cells': cells}, indent=1))
        return 0
    for f, p, h in rows:
        print('%-28s peak %9d  headroom %8d' % (f, p, h))
    print('%d frames; check them with tools/chim_build.py --chim-regions-cells "%s" --validate --stats'
          % (len(rows), cells))
    return 0


if __name__ == '__main__':
    sys.exit(main())
