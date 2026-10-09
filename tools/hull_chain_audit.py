#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Standing-hull chain audit: the brush models whose collision a trace walks node by node.

A converted model's standing hull (Quake hull 1) is written as a chain of its convex pieces unless it
is compiled by qbsp or routed (tools/routed_hull.py). A chain's depth is its length, and every trace
that reaches the model's box walks it: the Arena Pit's main mesh was one chain of 36,545 clipnodes
(INTERIOR-HULL-CHAIN-33), the Arena canton bodies' chains cost minutes of stair gate
(CHIM-HULL-CHAIN-COST-33). This reads BSP29 maps and reports, per brush model, its hull-1 clipnodes
and the longest path from the root (the worst case of SV_HullPointContents), sorted worst first.

    hull_chain_audit.py MAP.bsp|DIR [...] [--min-depth N] [--json OUT] [--jobs N]
"""
import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

CONTENTS_FIRST = 0xFFF0        # clipnode children at or above this are contents


def lumps_of(data):
    if struct.unpack_from('<i', data)[0] != 29:
        raise ValueError('Not a BSP29 map')
    return [data[o:o + n] for o, n in struct.iter_unpack('<ii', data[4:124])]


def hull_depth(clips, root):
    """(clipnodes reachable from root, longest root-to-contents path in clipnodes) of one hull tree."""
    if root < 0:
        return 0, 0
    count = len(clips) // 8
    depth, visiting = {}, set()
    stack = [(root, False)]
    while stack:                                   # post-order without recursion (chains are deep)
        n, done = stack.pop()
        if n >= count:
            raise ValueError('Clipnode %d outside the lump' % n)
        _, front, back = struct.unpack_from('<iHH', clips, 8 * n)
        kids = [c for c in (front, back) if c < CONTENTS_FIRST]
        if done:
            depth[n] = 1 + max([depth[c] for c in kids] or [0])
            visiting.discard(n)
            continue
        if n in depth:
            continue
        if n in visiting:
            raise ValueError('Cyclic clipnode tree at %d' % n)
        visiting.add(n)
        stack.append((n, True))
        stack += [(c, False) for c in kids if c not in depth]
    return len(depth), depth[root]


def below_head(children, root, contents_first=CONTENTS_FIRST):
    """Nodes reachable from root whose index is below root. Quake walks a model's hull only from its
    head node upwards (SV_RecursiveHullCheck: firstclipnode = the head; anything lower is "bad node
    number"), so such a node crashes the engine on load (ROUTED-HULL-NODE-ORDER-33). children(n): the two
    child numbers of node n."""
    if root < 0:
        return []
    bad, seen, stack = [], set(), [root]
    while stack:
        n = stack.pop()
        if n in seen or n < 0 or n >= contents_first:
            continue
        seen.add(n)
        if n < root:
            bad.append(n)
        stack += [c for c in children(n) if 0 <= c < contents_first]
    return sorted(bad)


def audit_map(path):
    data = Path(path).read_bytes()
    if len(data) < 124 or struct.unpack_from('<i', data)[0] != 29:
        return {'map': Path(path).name, 'bytes': len(data), 'skipped': 'not a BSP29 map', 'models': []}
    lumps = lumps_of(data)
    clips = lumps[9]
    rows = []
    models = list(struct.iter_unpack('<9f7i', lumps[14]))
    refs = model_refs(lumps[0])
    for i, m in enumerate(models):
        nodes, depth = hull_depth(clips, m[10])
        low = below_head(lambda n: struct.unpack_from('<iHH', clips, 8 * n)[1:], m[10]) if i else []
        rows.append({'model': i, 'clipnodes': nodes, 'depth': depth, 'faces': m[15], 'below_head': len(low),
                     'aw_ref': refs.get(i), 'mins': [round(v, 1) for v in m[0:3]], 'maxs': [round(v, 1) for v in m[3:6]]})
    return {'map': Path(path).name, 'bytes': len(data), 'clipnodes': len(clips) // 8, 'models': rows}


def model_refs(entity_lump):
    """{brush model number: aw_ref} from the entity text."""
    import re
    text = entity_lump.split(b'\0')[0].decode('latin-1')
    out = {}
    for block in re.findall(r'\{([^}]*)\}', text):
        keys = dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', block))
        m = keys.get('model', '')
        if m.startswith('*') and m[1:].isdigit():
            out[int(m[1:])] = keys.get('aw_ref')
    return out


def maps_in(paths):
    out = []
    for p in map(Path, paths):
        out += sorted(p.glob('*.bsp')) if p.is_dir() else [p]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('paths', nargs='+', help='BSP maps or folders of them')
    ap.add_argument('--min-depth', type=int, default=256, help='list models whose hull depth is at least this')
    ap.add_argument('--json', type=Path)
    ap.add_argument('--jobs', type=int)
    a = ap.parse_args(argv)
    from build_jobs import resolve_jobs
    from build_parallel import ordered_map
    maps = maps_in(a.paths)
    results = list(ordered_map(audit_map, maps, min(resolve_jobs(a.jobs), max(1, len(maps)))))
    worst = sorted(((r['map'], m) for r in results for m in r['models'] if m['depth'] >= a.min_depth),
                   key=lambda x: (-x[1]['depth'], x[0], x[1]['model']))
    for name, m in worst:
        print('%-28s *%-5d depth %6d  clipnodes %6d  faces %6d  aw_ref %s' % (name, m['model'], m['depth'],
                                                                              m['clipnodes'], m['faces'], m['aw_ref']))
    skipped = [r['map'] for r in results if 'skipped' in r]
    if skipped:
        print('skipped (not BSP29): ' + ', '.join(skipped))
    print('%d maps, %d models with hull depth >= %d' % (len(results) - len(skipped), len(worst), a.min_depth))
    broken = [(r['map'], m['model']) for r in results for m in r['models'] if m.get('below_head')]
    if broken:
        print('MODELS WITH CLIPNODES BELOW THEIR HEAD NODE (the engine stops on load): %d, first %s' % (len(broken), broken[0]))
        return 1
    if a.json:
        a.json.write_text(json.dumps({'min_depth': a.min_depth, 'maps': results}, indent=1) + '\n',
                          encoding='utf-8', newline='\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
