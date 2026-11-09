#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""World-wide check of the flames of every CHIM window frame (FIREPIT-FLAMES-62).

The engine draws a region frame's fires from that frame map's aw_flame rows: the loaded map's own (at most
STATIC_FLAME_MAX) and, for a frame entered by a streamed crossing, the rows read when it joins the window (at most
SLOT_FLAMES a frame; engine/aga/src/aw_guard_torch.c). A frame with more rows than that would lose fires. This check
measures the rows of every frame of a built CHIM world (tools/chim/flames.py measure, or its saved --json output) and
fails on any frame over the bound.

    python3 tools/window_flames_check.py WORLD_DIR [--regions chim-regions.json] [--jobs N]
    python3 tools/window_flames_check.py --measured flames.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'engine/aga/src/aw_guard_torch.c'


def engine_bounds():
    """(STATIC_FLAME_MAX, SLOT_FLAMES) from the engine source."""
    text = ENGINE.read_text(encoding='latin-1')
    values = dict(re.findall(r'#define (STATIC_FLAME_MAX|SLOT_FLAMES) (\d+)', text))
    return int(values['STATIC_FLAME_MAX']), int(values['SLOT_FLAMES'])


def check(measured):
    """{'frames', 'busiest', 'over': [{cell, frame, emitters}], 'slot_flames', 'map_flames'} of a flames measure."""
    map_max, slot_max = engine_bounds()
    bound = min(map_max, slot_max)
    frames = measured.get('per_frame', [])
    over = [{'cell': f['cell'], 'frame': f.get('frame'), 'emitters': f['emitters']} for f in frames
            if f.get('emitters', 0) > bound]
    busiest = max((f.get('emitters', 0) for f in frames), default=0)
    return {'frames': len(frames), 'frames_with_flames': sum(1 for f in frames if f.get('emitters')),
            'busiest': busiest, 'slot_flames': slot_max, 'map_flames': map_max, 'over': over}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('world', nargs='?')
    ap.add_argument('--measured', help='a saved tools/chim/flames.py measure --json output')
    ap.add_argument('--regions')
    ap.add_argument('--jobs', type=int, default=1)
    a = ap.parse_args(argv)
    if a.measured:
        measured = json.loads(Path(a.measured).read_text(encoding='utf-8'))
    elif a.world:
        sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
        from chim import flames
        measured = flames.measure(a.world, regions=a.regions, jobs=a.jobs)
    else:
        ap.error('a CHIM world or --measured')
    result = check(measured)
    print('Window flames: %d frames (%d with flames), the busiest %d rows; bound %d a frame (window slot), %d a map; '
          '%d frames over' % (result['frames'], result['frames_with_flames'], result['busiest'], result['slot_flames'],
                              result['map_flames'], len(result['over'])), flush=True)
    for f in result['over']:
        print('  OVER: frame %s (%s): %d rows' % (f['cell'], f['frame'], f['emitters']))
    return 1 if result['over'] else 0


if __name__ == '__main__':
    sys.exit(main())
