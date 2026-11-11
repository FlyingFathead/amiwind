# SPDX-License-Identifier: GPL-3.0-only
"""Collision census: the collision data of every CHIM model beside its drawn data.

Every model of a built image (the open-world store chim/ and the interior store chimi/, where the CHIM rooms keep
their meshes) is a BSP29 brush image. Its bytes split into two parts:

  drawing   everything the renderer needs: faces, edges, vertexes, texinfo, lighting, the hull 0 nodes and leaves
            (shared with point traces) and the planes the faces and nodes use;
  collision the clipnodes (the standing hulls 1 and 2, lump 9), the convex collision piece table of a placed model
            (lump 4, "PCS1": the pieces placed traces test, engine chim_placed_clip.c) and the planes only the
            clipnodes use.

Per model: faces, triangles, planes (used by faces, by nodes, by clipnodes only), nodes, clipnodes reached from
hull 1 and hull 2 and their deepest chain (a trace's worst walk), collision pieces, drawing and collision bytes, and
the collision / visual ratio as bytes and as counts (clipnodes + pieces per face).

    python3 tools/collision_census.py RUN_FOLDER [--out DIR] [--top 20]

RUN_FOLDER is a build run folder (chim-world/chim and chim-interiors/chimi, or image/boot/id1/chimi), or any folder
holding chim/world.cwi or chimi/world.cwi. Writes collision-census.json and collision-census.md (the models sorted
by the byte ratio) and prints a WARNING line for each model whose byte ratio is above the warning threshold.

The threshold is a ratio taken from the measured world (the dev3 census): WARN_RATIO below. Each census also
records its own spread (median, 90th and 99th percentiles), so a later world that drifts is seen.
"""
import argparse
import json
import math
import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from chim import format as F  # noqa: E402
# importing them lets chim.format read every world format the builder writes (0.8 to 0.13)
from chim import placed, reach, terc, thgt, placement_light, interior  # noqa: E402,F401

SCHEMA = 'amiwind-collision-census-1'
JSON_NAME = 'collision-census.json'
MD_NAME = 'collision-census.md'
PLANE = 20
# A model warns when its collision bytes are more than WARN_RATIO times its drawing bytes AND its collision part is
# at least WARN_MIN_BYTES (small props with a tiny box hull have large ratios that cost nothing). Chosen from the
# v0.0.64-dev3 census (37,706 models): the byte ratio's median is 0.044 over all models and 1.09 over the 632 models
# with at least 64 KiB of collision; their 90th percentile is 2.03 and the maximum 2.98. 2.0 is that 90th
# percentile (45 times the world median): 67 models warn, 50 of them tiles of the Heart Chamber cave.
WARN_RATIO = 2.0
WARN_MIN_BYTES = 64 * 1024
STORES = (('open world', ('chim-world/chim', 'chim', 'id1/chim')),
          ('rooms', ('chim-interiors/chimi', 'image/boot/id1/chimi', 'chimi', 'id1/chimi')))


def _refs(L, order):
    """Plane numbers of the faces, nodes and clipnodes, or None when one falls outside the plane table."""
    planes = len(L[1]) // PLANE
    faces = [struct.unpack_from(order + 'H', L[7], o)[0] for o in range(0, len(L[7]) - 19, 20)]
    nodes = [struct.unpack_from(order + 'i', L[5], o)[0] for o in range(0, len(L[5]) - 23, 24)]
    clips = [struct.unpack_from(order + 'i', L[9], o)[0] for o in range(0, len(L[9]) - 7, 8)]
    allp = faces + nodes + clips
    if allp and (min(allp) < 0 or max(allp) >= planes):
        return None
    return set(faces), set(nodes), set(clips)


def _hull(L, order, head):
    """Clipnodes reached from HEAD and the deepest chain (clipnodes walked by the worst trace)."""
    n = len(L[9]) // 8
    if head < 0 or head >= n:
        return 0, 0
    seen, deepest, stack = set(), 0, [(head, 1)]
    while stack:
        i, depth = stack.pop()
        if i in seen:
            continue
        seen.add(i)
        deepest = max(deepest, depth)
        for c in struct.unpack_from(order + 'hh', L[9], 8 * i + 4):
            if 0 <= c < n:
                stack.append((c, depth + 1))
    return len(seen), deepest


def model_stats(image):
    """The drawing and collision figures of one brush image (bytes)."""
    L = F.read_brush_image(image)
    order = '<'
    refs = _refs(L, '<')
    if refs is None:
        order, refs = '>', _refs(L, '>')
    if refs is None:
        raise ValueError('plane numbers out of range in both byte orders')
    face_p, node_p, clip_p = refs
    faces = len(L[7]) // 20
    triangles = 0
    for o in range(0, len(L[7]) - 19, 20):
        edges = struct.unpack_from(order + 'h', L[7], o + 8)[0]
        triangles += max(0, edges - 2)
    clip_only = len(clip_p - face_p - node_p)
    heads = struct.unpack_from(order + '4i', L[14], 36) if len(L[14]) >= 64 else (0, -1, -1, -1)
    hull1, depth1 = _hull(L, order, heads[1])
    hull2, depth2 = _hull(L, order, heads[2])
    pieces = struct.unpack_from('>I', L[4], 4)[0] if len(L[4]) >= 16 and L[4][:3] == b'PCS' else 0
    coll = len(L[9]) + len(L[4]) + clip_only * PLANE
    draw = max(len(image) - coll, 0)
    return {'faces': faces, 'triangles': triangles, 'planes': len(L[1]) // PLANE, 'face_planes': len(face_p),
            'node_planes': len(node_p), 'clip_only_planes': clip_only, 'nodes': len(L[5]) // 24,
            'clipnodes': len(L[9]) // 8, 'hull1_clipnodes': hull1, 'hull2_clipnodes': hull2,
            'deepest_chain': max(depth1, depth2), 'pieces': pieces, 'piece_bytes': len(L[4]),
            'clipnode_bytes': len(L[9]), 'bytes': len(image), 'draw_bytes': draw, 'collision_bytes': coll,
            'ratio_bytes': round(coll / draw, 3) if draw else None,
            'ratio_counts': round((len(L[9]) // 8 + pieces) / faces, 3) if faces else None}


def find_stores(folder):
    """[(label, store folder)] of FOLDER: the first existing candidate per store."""
    folder = Path(folder)
    out = []
    for label, candidates in STORES:
        for c in candidates:
            if (folder / c / 'world.cwi').is_file():
                out.append((label, folder / c))
                break
    return out


def store_models(root, log=print):
    """Rows of every model of a store folder (world.cwi + its pack or sector files), read file by file."""
    _, files, models, _ = F.read_index((root / 'world.cwi').read_bytes())
    by_file = {}
    for i, m in enumerate(models):
        by_file.setdefault(m['file'], []).append(i)
    rows, done, last = [], 0, time.monotonic()
    for fi in sorted(by_file):
        data = (root / files[fi]['path']).read_bytes()
        for i in by_file[fi]:
            m = models[i]
            row = {'id': i, 'name': m['name'], 'file': files[fi]['path']}
            try:
                row.update(model_stats(data[m['offset']:m['offset'] + m['bytes']]))
            except (ValueError, struct.error) as exc:
                row['error'] = str(exc)
            rows.append(row)
            done += 1
        if time.monotonic() - last > 5:
            log('  %s: %d / %d models' % (root.name, done, len(models)), flush=True)
            last = time.monotonic()
    return rows


def percentile(values, q):
    if not values:
        return None
    v = sorted(values)
    k = (len(v) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return round(v[lo] + (v[hi] - v[lo]) * (k - lo), 3)


def warnings(rows, ratio=WARN_RATIO, min_bytes=WARN_MIN_BYTES):
    return [r for r in rows if r.get('ratio_bytes') is not None and r['ratio_bytes'] > ratio
            and r['collision_bytes'] >= min_bytes]


def warning_line(r, ratio=WARN_RATIO):
    return ('WARNING: collision-heavy model %s (%s): collision %s bytes against drawing %s bytes, ratio %.1f (warns '
            'above %.1f); %s faces, %s clipnodes, %s collision pieces' % (
                r['name'], r['store'], f"{r['collision_bytes']:,}", f"{r['draw_bytes']:,}", r['ratio_bytes'], ratio,
                f"{r['faces']:,}", f"{r['clipnodes']:,}", f"{r['pieces']:,}"))


def census(folder, log=print):
    """The census record of FOLDER (not written)."""
    stores = find_stores(folder)
    if not stores:
        raise SystemExit('refused: no chim/world.cwi or chimi/world.cwi under %s' % folder)
    rows = []
    for n, (label, root) in enumerate(stores, 1):
        log('=== PHASE %d/%d: %s store %s ===' % (n, len(stores), label, root), flush=True)
        for r in store_models(root, log):
            r['store'] = label
            rows.append(r)
    good = [r for r in rows if 'error' not in r]
    ratios = [r['ratio_bytes'] for r in good if r['ratio_bytes'] is not None]
    weighty = [r['ratio_bytes'] for r in good if r['ratio_bytes'] is not None and r['collision_bytes'] >= WARN_MIN_BYTES]
    good.sort(key=lambda r: -(r['ratio_bytes'] if r['ratio_bytes'] is not None else -1))
    total = {k: sum(r[k] for r in good) for k in ('draw_bytes', 'collision_bytes', 'faces', 'clipnodes', 'pieces')}
    spread = {'models': len(good), 'median': percentile(ratios, 0.5), 'p90': percentile(ratios, 0.9),
              'p99': percentile(ratios, 0.99), 'max': max(ratios) if ratios else None,
              'weighty_models': len(weighty), 'weighty_median': percentile(weighty, 0.5),
              'weighty_p90': percentile(weighty, 0.9), 'weighty_p99': percentile(weighty, 0.99)}
    warn = warnings(good)
    return {'schema': SCHEMA, 'folder': Path(folder).name, 'stores': [str(r) for _, r in stores],
            'threshold': {'ratio_bytes': WARN_RATIO, 'min_collision_bytes': WARN_MIN_BYTES},
            'total': dict(total, ratio_bytes=round(total['collision_bytes'] / total['draw_bytes'], 3)
                          if total['draw_bytes'] else None),
            'spread': spread, 'warned': [r['name'] for r in warn], 'errors': [r for r in rows if 'error' in r],
            'models': good}


def top(record, n=20):
    return record['models'][:n]


TOP_KEYS = ('name', 'store', 'faces', 'clipnodes', 'pieces', 'draw_bytes', 'collision_bytes', 'ratio_bytes',
            'ratio_counts', 'deepest_chain')


def top_rows(record, n=20):
    """The N worst models by byte ratio, short rows (the size ledger and the build summary)."""
    return [{k: r[k] for k in TOP_KEYS} for r in top(record, n)]


def markdown(record, n=20):
    s, t = record['spread'], record['total']
    lines = ['# Collision census: %s' % record['folder'], '',
             'Models: %d. Drawing %s bytes, collision %s bytes (ratio %s). Byte ratio spread: median %s, 90th %s, '
             '99th %s, max %s. Warns above %.1f with at least %s collision bytes: %d model(s).' % (
                 s['models'], f"{t['draw_bytes']:,}", f"{t['collision_bytes']:,}", t['ratio_bytes'], s['median'],
                 s['p90'], s['p99'], s['max'], record['threshold']['ratio_bytes'],
                 f"{record['threshold']['min_collision_bytes']:,}", len(record['warned'])), '',
             '| # | Model | Store | Faces | Clipnodes | Pieces | Drawing bytes | Collision bytes | Ratio (bytes) |'
             ' Ratio (counts) | Deepest chain |',
             '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for i, r in enumerate(top(record, n), 1):
        lines.append('| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            i, r['name'], r['store'], f"{r['faces']:,}", f"{r['clipnodes']:,}", f"{r['pieces']:,}",
            f"{r['draw_bytes']:,}", f"{r['collision_bytes']:,}", r['ratio_bytes'], r['ratio_counts'],
            r['deepest_chain']))
    return '\n'.join(lines) + '\n'


def write(record, out, n=20):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / JSON_NAME).write_text(json.dumps(record, indent=1) + '\n', encoding='utf-8', newline='\n')
    (out / MD_NAME).write_text(markdown(record, n), encoding='utf-8', newline='\n')
    return out / JSON_NAME, out / MD_NAME


def ledger_entry(run, log=print, n=20):
    """The size ledger's collision entry of a build run: the top N by ratio, the spread and the warnings (WARNING
    lines are printed; never raises, never fails a build). None when the run has no CHIM store."""
    try:
        if not find_stores(run):
            return None
        record = census(run, log=lambda *a, **k: None)
        write(record, Path(run))
        for r in warnings(record['models']):
            log(warning_line(r))
        return {'census': JSON_NAME, 'threshold': record['threshold'], 'total': record['total'],
                'spread': record['spread'], 'warned': record['warned'], 'top': top_rows(record, n)}
    except Exception as exc:  # noqa: BLE001 - a census problem is a note, never a failed build
        log('Collision census: not written (%s: %s); the build is unaffected' % (type(exc).__name__, exc))
        return {'error': '%s: %s' % (type(exc).__name__, exc)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('run', type=Path, help='a build run folder, or a folder holding chim/ or chimi/')
    p.add_argument('--out', type=Path, help='where the JSON and the Markdown go (default: the run folder)')
    p.add_argument('--top', type=int, default=20)
    a = p.parse_args(argv)
    started = time.monotonic()
    record = census(a.run)
    j, m = write(record, a.out or a.run, a.top)
    for r in warnings(record['models']):
        print(warning_line(r), flush=True)
    print(markdown(record, a.top), end='')
    print('Written %s and %s (took %.1f s)' % (j, m, time.monotonic() - started), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
