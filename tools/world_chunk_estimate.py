#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Estimate a per-chunk exterior layout from today's overlapping region maps.

Reads the region BSPs of one converted town (or any set of overlapping
exterior regions) plus their region table, and answers: if every placed
object were stored once, in the chunk that holds its origin, and the terrain
once, in the chunk that holds each face, how large would each chunk be, how
much would be resident inside the draw distance, and how many bytes would a
chunk crossing read? See docs/WORLD_STREAMER.md.

Rules (the same as the design note):
- placements (func_wall entities) are identified by their `aw_ref` key and
  counted once, whichever regions repeat them; their geometry is identified
  across maps by a geometry signature (texture pixels, not per-map names);
- a placement's collision hull is kept only where a region needed it (core
  plus collision margin); the largest record per signature is used;
- world faces belong to the region whose core holds the face centroid;
- residency: render parts of every chunk whose content box comes within
  draw distance + hysteresis (+ prefetch) of the owned chunk; collision
  parts only within the collision margin;
- modes: `instanced` (each chunk stores its own copy of each variant),
  `library` (variants are shared model files, loaded once per ring).

Measurement only: no map is written. Region table rows: `name x0 y0 x1 y1
cx0 cy0 cx1 cy1` (core then coverage, map units); other lines are ignored.
"""
import argparse
import hashlib
import json
import math
import re
import statistics
import struct
import sys
from collections import defaultdict
from pathlib import Path

DISK = {'faces': 20, 'texinfo': 40, 'planes': 20, 'vertexes': 12, 'edges': 4, 'surfedges': 4,
        'nodes': 24, 'leafs': 28, 'marksurfaces': 2, 'clipnodes': 8, 'models': 64}
NUM = ('faces', 'texinfo', 'planes', 'vertexes', 'edges', 'surfedges', 'nodes', 'leafs', 'marksurfaces',
       'clipnodes', 'lighting')
COLLISION = ('planes', 'nodes', 'leafs', 'marksurfaces', 'clipnodes')
HEADER = 4 + 15 * 8


class Map:
    """Read-only BSP29 view with per-submodel cost decomposition."""

    def __init__(self, data):
        if len(data) < HEADER or struct.unpack_from('<i', data)[0] != 29:
            raise ValueError('Not a BSP29 map')
        self.data = data
        self.L = [struct.unpack_from('<ii', data, 4 + 8 * i) for i in range(15)]
        for o, n in self.L:
            if o < 0 or n < 0 or o + n > len(data):
                raise ValueError('BSP lump outside the file')
        lump = self.lump
        self.planes = list(struct.iter_unpack('<4fi', lump(1)))
        self.vertexes = list(struct.iter_unpack('<3f', lump(3)))
        self.nodes = list(struct.iter_unpack('<i2h6h2H', lump(5)))
        self.texinfo = list(struct.iter_unpack('<8fii', lump(6)))
        self.faces = list(struct.iter_unpack('<HhiHH4Bi', lump(7)))
        self.lighting_len = self.L[8][1]
        self.clipnodes = list(struct.iter_unpack('<iHH', lump(9)))
        self.leafs = list(struct.iter_unpack('<2i6h2H4B', lump(10)))
        self.edges = list(struct.iter_unpack('<2H', lump(12)))
        self.surfedges = [v[0] for v in struct.iter_unpack('<i', lump(13))]
        self.models = list(struct.iter_unpack('<9f7i', lump(14)))
        tex = lump(2)
        self.texkeys, self.texbytes = [], []
        if tex:
            count = struct.unpack_from('<i', tex)[0]
            for o in struct.unpack_from('<%di' % count, tex, 4):
                if o < 0:
                    self.texkeys.append(''); self.texbytes.append(0); continue
                w, h, ofs = struct.unpack_from('<III', tex, o + 16)
                pixels = tex[o + ofs:o + ofs + w * h] if ofs else b''
                self.texkeys.append('%dx%d-%s' % (w, h, hashlib.sha1(pixels).hexdigest()[:16]))
                self.texbytes.append(40 + w * h * 85 // 64)
        self.entities = []
        for block in re.findall(r'\{[^{}]*\}', lump(0).decode('cp1252').rstrip('\0')):
            d = dict(re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"', block))
            d['_bytes'] = len(block) + 1
            self.entities.append(d)

    def lump(self, i):
        o, n = self.L[i]
        return self.data[o:o + n]

    def face_vertexes(self, f):
        first, num = self.faces[f][2], self.faces[f][3]
        return [self.edges[e][0] if e >= 0 else self.edges[-e][1] for e in self.surfedges[first:first + num]]

    def lightmap_bytes(self, f):
        face = self.faces[f]
        styles = sum(1 for s in face[5:9] if s != 255)
        ti = self.texinfo[face[4]]
        if face[9] < 0 or not styles or ti[9] & 1:
            return 0
        lo, hi = [1e30, 1e30], [-1e30, -1e30]
        for v in self.face_vertexes(f):
            p = self.vertexes[v]
            for j in range(2):
                s = p[0] * ti[j * 4] + p[1] * ti[j * 4 + 1] + p[2] * ti[j * 4 + 2] + ti[j * 4 + 3]
                lo[j] = min(lo[j], s); hi[j] = max(hi[j], s)
        size = 1
        for j in range(2):
            size *= int(math.ceil(hi[j] / 16) - math.floor(lo[j] / 16)) + 1
        return size * styles

    def centroid(self, f):
        pts = [self.vertexes[v] for v in self.face_vertexes(f)]
        return [sum(p[i] for p in pts) / len(pts) for i in range(3)]

    def render_tree(self, head):
        """Nodes and leafs under head; shared subtrees (a DAG) count once."""
        nodes, leafs, stack, seen = [], [], [head], set()
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            if n < 0:
                leafs.append(-1 - n); continue
            nodes.append(n)
            stack.extend(self.nodes[n][1:3])
        return nodes, leafs

    def clip_tree(self, head):
        out, stack, seen = [], [head], set()
        while stack:
            n = stack.pop()
            if not 0 <= n < len(self.clipnodes) or n in seen:
                continue
            seen.add(n); out.append(n)
            stack.extend(c for c in self.clipnodes[n][1:] if c < 0xFFF0)
        return out

    def cost(self, faces, nodes=(), leafs=(), clipnodes=()):
        edges, verts, planes, texinfo, textures = set(), set(), set(), set(), set()
        surfedges = lighting = 0
        for f in faces:
            face = self.faces[f]
            planes.add(face[0]); texinfo.add(face[4]); textures.add(self.texinfo[face[4]][8])
            first, num = face[2], face[3]
            fe = [abs(e) for e in self.surfedges[first:first + num]]
            surfedges += len(fe); edges.update(fe)
            lighting += self.lightmap_bytes(f)
        for e in edges:
            verts.update(self.edges[e])
        planes.update(self.nodes[n][0] for n in nodes)
        planes.update(self.clipnodes[c][0] for c in clipnodes)
        return {'faces': len(faces), 'texinfo': len(texinfo), 'planes': len(planes), 'vertexes': len(verts),
                'edges': len(edges), 'surfedges': surfedges, 'nodes': len(nodes), 'leafs': len(leafs),
                'marksurfaces': sum(self.leafs[l][9] for l in leafs), 'clipnodes': len(clipnodes),
                'lighting': lighting,
                'textures': sorted(self.texkeys[t] for t in textures if 0 <= t < len(self.texkeys))}

    def submodel(self, index):
        m = self.models[index]
        faces = list(range(m[14], m[14] + m[15]))
        nodes, leafs = self.render_tree(m[9])
        record = self.cost(faces, nodes, leafs, self.clip_tree(m[10]) + self.clip_tree(m[11]))
        record['mins'], record['maxs'] = list(m[0:3]), list(m[3:6])
        rows = sorted((self.texkeys[self.texinfo[self.faces[f][4]][8]],
                       tuple(sorted(tuple(round(c, 1) for c in self.vertexes[v]) for v in self.face_vertexes(f))))
                      for f in faces)
        record['signature'] = hashlib.sha1(repr(rows).encode()).hexdigest()[:20]
        return record


def disk_bytes(c):
    return sum(c.get(k, 0) * DISK[k] for k in DISK) + c.get('lighting', 0)


def heap_bytes(c, sizes):
    """Target hunk payload of one loaded model record (texture pixels excluded)."""
    hunk = sizes['hunk']

    def a(n):
        return hunk + ((int(n) + 15) & ~15) if n else 0
    return (a(c['vertexes'] * sizes['mvertex']) + a((c['edges'] + 1) * sizes['medge']) + a(c['surfedges'] * 4)
            + a(c['lighting']) + a(c['planes'] * sizes['mplane']) + a(c['texinfo'] * sizes['mtexinfo'])
            + a(c['faces'] * sizes['msurface']) + a(c['marksurfaces'] * sizes['pointer'])
            + a(c['leafs'] * sizes['mleaf']) + a(c['nodes'] * sizes['mnode']) + a(c['nodes'] * sizes['clipnode'])
            + a(c['clipnodes'] * sizes['clipnode']) + a(c.get('models', 1) * sizes['dmodel']))


def angle_vectors(angles):
    p, y, r = (math.radians(a) for a in angles)
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    return ([cp * cy, cp * sy, -sp], [-sr * sp * cy + cr * sy, -sr * sp * sy - cr * cy, -sr * cp],
            [cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp])


def placed_box(origin, angles, mins, maxs):
    f, r, u = angle_vectors(angles)
    lo, hi = [1e30] * 3, [-1e30] * 3
    for j in range(8):
        c = [maxs[i] if j & (1 << i) else mins[i] for i in range(3)]
        for k in range(3):
            v = origin[k] + c[0] * f[k] - c[1] * r[k] + c[2] * u[k]
            lo[k] = min(lo[k], v); hi[k] = max(hi[k], v)
    return lo, hi


def read_regions(text):
    out = {}
    for line in text.splitlines():
        t = line.split()
        if len(t) == 9:
            try:
                v = [float(x) for x in t[1:]]
            except ValueError:
                continue
            out[t[0]] = {'core': v[0:4], 'cover': v[4:8]}
    if not out:
        raise ValueError('Region table has no rows')
    return out


def collect(maps, regions):
    """maps: {name: Map}. Returns placements, variants, terrain faces per region, texture bytes, today."""
    variants, placements, terrain, texbytes, today = {}, {}, {}, {}, {}
    for name in sorted(regions):
        m = maps[name]
        for k, b in zip(m.texkeys, m.texbytes):
            texbytes[k] = max(texbytes.get(k, 0), b)
        sub = {}
        for e in m.entities:
            if e.get('classname') != 'func_wall' or not e.get('model', '').startswith('*'):
                continue
            index = int(e['model'][1:])
            if index not in sub:
                sub[index] = m.submodel(index)
            c = sub[index]
            sig = c['signature']
            v = variants.setdefault(sig, dict(c, **{'min_' + k: c[k] for k in COLLISION}))
            for k in COLLISION:
                v[k] = max(v[k], c[k]); v['min_' + k] = min(v['min_' + k], c[k])
            origin = [float(x) for x in e.get('origin', '0 0 0').split()]
            angles = [float(x) for x in e.get('angles', '0 0 0').split()]
            ref = e.get('aw_ref') or '%s:%s:%s' % (name, e['model'], e.get('origin'))
            p = placements.setdefault(ref, {'origin': origin, 'sigs': set(), 'maps': [], 'bytes': e['_bytes'],
                                            'lo': None, 'hi': None})
            p['sigs'].add(sig); p['maps'].append(name)
            lo, hi = placed_box(origin, angles, c['mins'], c['maxs'])
            p['lo'] = lo if p['lo'] is None else [min(a, b) for a, b in zip(p['lo'], lo)]
            p['hi'] = hi if p['hi'] is None else [max(a, b) for a, b in zip(p['hi'], hi)]
        x0, y0, x1, y1 = regions[name]['core']
        w = m.models[0]
        owned = [f for f in range(w[14], w[14] + w[15]) if x0 <= m.centroid(f)[0] < x1 and y0 <= m.centroid(f)[1] < y1]
        nodes, leafs = m.render_tree(w[9])
        clip = m.clip_tree(w[10]) + m.clip_tree(w[11])
        terrain[name] = {'map': m, 'faces': owned, 'nodes': nodes, 'leafs': leafs, 'clip': clip}
        today[name] = {'file_bytes': len(m.data), 'placements': sum(1 for e in m.entities if e.get('classname') == 'func_wall'),
                       'submodels': len(sub)}
    return placements, variants, terrain, texbytes, today


def split(v):
    """Render part (no hull) and collision part of a variant record."""
    render = {k: v[k] for k in NUM}
    coll = {k: 0 for k in NUM}
    for k in COLLISION:
        render[k] = v['min_' + k]; coll[k] = v[k] - v['min_' + k]
    if v['faces'] == 0:
        render, coll = {k: 0 for k in NUM}, {k: v[k] for k in NUM}
    return render, coll


class Chunk:
    def __init__(self, key, box):
        self.key, self.box, self.cbox = key, list(box), list(box)
        self.render = {k: 0 for k in NUM}; self.coll = {k: 0 for k in NUM}
        self.variants, self.textures = {}, set()
        self.placements = self.entity_bytes = 0
        self.disk = self.cdisk = self.heap = self.cheap = 0


def gap(a, b):
    return math.hypot(max(0.0, a[0] - b[2], b[0] - a[2]), max(0.0, a[1] - b[3], b[1] - a[3]))


def build_chunks(placements, variants, terrain, low, span, grain, mode='instanced', rule='origin'):
    n = int(span // grain)
    if n < 1 or abs(n * grain - span) > 1e-6:
        raise ValueError('Chunk grain must divide the area span')
    chunks = {(i, j): Chunk((i, j), (low[0] + i * grain, low[1] + j * grain, low[0] + (i + 1) * grain,
                                     low[1] + (j + 1) * grain)) for i in range(n) for j in range(n)}

    def key(x, y):
        return (min(n - 1, max(0, int((x - low[0]) // grain))), min(n - 1, max(0, int((y - low[1]) // grain))))
    for p in placements.values():
        ch = chunks[key(p['origin'][0], p['origin'][1])]
        ch.placements += 1; ch.entity_bytes += p['bytes']
        if rule == 'origin':
            ch.cbox = [min(ch.cbox[0], p['lo'][0]), min(ch.cbox[1], p['lo'][1]),
                       max(ch.cbox[2], p['hi'][0]), max(ch.cbox[3], p['hi'][1])]
        render = max(p['sigs'], key=lambda s: (variants[s]['faces'], variants[s]['clipnodes']))
        used = {render}
        coll = max(p['sigs'], key=lambda s: variants[s]['clipnodes'])
        if coll != render and variants[coll]['faces'] == 0 and variants[render]['clipnodes'] == 0:
            used.add(coll)
        for s in used:
            ch.variants[s] = ch.variants.get(s, 0) + 1
    for t in terrain.values():
        m = t['map']
        groups = defaultdict(list)
        for f in t['faces']:
            c = m.centroid(f)
            groups[key(c[0], c[1])].append(f)
        share = defaultdict(list)
        for nd in t['nodes']:
            mm = m.nodes[nd][3:9]
            share[key((mm[0] + mm[3]) / 2, (mm[1] + mm[4]) / 2)].append(nd)
        owned_nodes = sum(len(v) for k, v in share.items() if k in groups)
        for k, faces in groups.items():
            c = m.cost(faces, share.get(k, []), ())
            ch = chunks[k]
            ch.textures.update(c.pop('textures'))
            for kk in NUM:
                ch.render[kk] += c[kk]
            if owned_nodes:
                ch.coll['clipnodes'] += round(len(t['clip']) * len(share.get(k, [])) / max(1, len(t['nodes'])))
    for ch in chunks.values():
        for s, count in ch.variants.items():
            r, c = split(variants[s])
            ch.textures.update(variants[s]['textures'])
            for kk in NUM:
                if mode == 'instanced':
                    ch.render[kk] += r[kk]
                ch.coll[kk] += c[kk]
    return chunks


def price(chunks, variants, sizes, mode='instanced', factors=None, scenery_bytes=0):
    f = factors or {}
    library = {}
    for ch in chunks.values():
        r = {k: int(round(ch.render[k] * f.get(k, 1.0))) for k in NUM}
        c = {k: int(round(ch.coll[k] * f.get(k, 1.0))) for k in NUM}
        r['models'] = 1 + (len(ch.variants) if mode == 'instanced' else 0); c['models'] = 0
        ch.disk = disk_bytes(r) + HEADER + ch.entity_bytes
        ch.cdisk = disk_bytes(c)
        ch.heap = heap_bytes(r, sizes) + ch.placements * scenery_bytes + sizes['hunk'] + ((ch.entity_bytes + 15) & ~15)
        nodes = c['nodes']; c['nodes'] = 0
        ch.cheap = heap_bytes(c, sizes) + (sizes['hunk'] + ((nodes * sizes['clipnode'] + 15) & ~15) if nodes else 0)
    if mode == 'library':
        for s in {s for ch in chunks.values() for s in ch.variants}:
            r = {k: int(round(split(variants[s])[0][k] * f.get(k, 1.0))) for k in NUM}
            r['models'] = 1
            library[s] = (disk_bytes(r) + HEADER, heap_bytes(r, sizes))
    return library


def ring(chunks, key, reach, grain):
    centre = chunks[key].box
    over = max(max(c.box[0] - c.cbox[0], c.box[1] - c.cbox[1], c.cbox[2] - c.box[2], c.cbox[3] - c.box[3])
               for c in chunks.values())
    r = int(math.ceil((reach + over) / grain)) + 1
    return [k for k in ((key[0] + dx, key[1] + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1))
            if k in chunks and gap(chunks[k].cbox, centre) <= reach]


def resident(chunks, keys, ckeys, texheap, library=None):
    heap = sum(chunks[k].heap for k in keys) + sum(chunks[k].cheap for k in ckeys)
    heap += sum(texheap.get(t, 0) for t in set().union(*(chunks[k].textures for k in keys)))
    if library:
        heap += sum(library[s][1] for s in set().union(*(chunks[k].variants for k in keys)))
    return heap


def crossing(chunks, old, new, cold, cnew, texdisk, library=None):
    add = [k for k in new if k not in set(old)]
    b = sum(chunks[k].disk for k in add) + sum(chunks[k].cdisk for k in cnew if k not in set(cold))
    had = set().union(*(chunks[k].textures for k in old)) if old else set()
    b += sum(texdisk.get(t, 0) for t in set().union(*(chunks[k].textures for k in add)) - had) if add else 0
    if library and add:
        had = set().union(*(chunks[k].variants for k in old)) if old else set()
        b += sum(library[s][0] for s in set().union(*(chunks[k].variants for k in add)) - had)
    return b


def summary(values):
    v = sorted(values)
    if not v:
        return {'n': 0}
    return {'n': len(v), 'median': statistics.median(v), 'max': v[-1], 'min': v[0], 'sum': sum(v)}


def estimate(maps, regions, sizes, grain, draw_distance, hysteresis, collision_margin, mode='instanced',
             rule='origin', prefetch=0):
    placements, variants, terrain, texbytes, today = collect(maps, regions)
    xs = [r['core'][0] for r in regions.values()] + [r['core'][2] for r in regions.values()]
    ys = [r['core'][1] for r in regions.values()] + [r['core'][3] for r in regions.values()]
    low, span = (min(xs), min(ys)), max(max(xs) - min(xs), max(ys) - min(ys))
    chunks = build_chunks(placements, variants, terrain, low, span, grain, mode, rule)
    library = price(chunks, variants, sizes, mode, scenery_bytes=sizes.get('scenery', 0))
    texheap = {t: sizes['hunk'] + ((sizes['texture'] + max(0, b - 40) + 15) & ~15) for t, b in texbytes.items()}
    reach = draw_distance + hysteresis + prefetch
    over = max(max(c.box[0] - c.cbox[0], c.box[1] - c.cbox[1], c.cbox[2] - c.box[2], c.cbox[3] - c.box[3])
               for c in chunks.values())
    valid = [k for k, c in chunks.items()
             if c.box[0] - reach - over >= low[0] and c.box[1] - reach - over >= low[1]
             and c.box[2] + reach + over <= low[0] + span and c.box[3] + reach + over <= low[1] + span]
    rings = {k: ring(chunks, k, reach, grain) for k in valid}
    crings = {k: ring(chunks, k, collision_margin, grain) for k in valid}
    heaps = [resident(chunks, rings[k], crings[k], texheap, library or None) for k in valid]
    moves = []
    for k in valid:
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            b = (k[0] + d[0], k[1] + d[1])
            if b in rings:
                moves.append(crossing(chunks, rings[k], rings[b], crings[k], crings[b], texbytes, library or None))
    used_tex = set().union(*(c.textures for c in chunks.values()))
    disk = sum(c.disk + c.cdisk for c in chunks.values()) + sum(texbytes[t] for t in used_tex)
    disk += sum(v[0] for v in library.values())
    stored = sum(len(p['maps']) for p in placements.values())
    return {'grain': grain, 'mode': mode, 'rule': rule, 'regions': len(regions),
            'today_disk': sum(t['file_bytes'] for t in today.values()),
            'placements_unique': len(placements), 'placements_stored': stored,
            'duplication_factor': stored / len(placements) if placements else 0.0,
            'variants': len(variants), 'chunks': len(chunks), 'chunk_disk_total': disk,
            'max_overhang': over, 'valid_centres': len(valid), 'resident_heap': summary(heaps),
            'crossing_bytes': summary(moves),
            'per_chunk': {'%d,%d' % k: {'disk': c.disk + c.cdisk, 'render_heap': c.heap, 'collision_heap': c.cheap,
                                        'placements': c.placements, 'variants': len(c.variants)}
                          for k, c in sorted(chunks.items())}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('maps', type=Path, help='folder with the region .bsp files')
    ap.add_argument('regions', type=Path, help='region table (name core cover)')
    ap.add_argument('--sizes', type=Path, help='JSON of target struct sizes (check_world_map_heap names)')
    ap.add_argument('--sdk', type=Path, help='Amiga SDK: compile the target struct sizes instead')
    ap.add_argument('--grain', type=float, default=512)
    ap.add_argument('--draw-distance', type=float, default=540)
    ap.add_argument('--hysteresis', type=float, default=96)
    ap.add_argument('--collision-margin', type=float, default=224)
    ap.add_argument('--prefetch', type=float, default=0)
    ap.add_argument('--mode', choices=('instanced', 'library'), default='instanced')
    ap.add_argument('--rule', choices=('origin', 'bounds'), default='origin')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args(argv)
    if a.sizes:
        sizes = json.loads(a.sizes.read_text(encoding='utf-8'))
    elif a.sdk:
        from check_world_map_heap import compile_target_sizes
        sizes, _ = compile_target_sizes(a.sdk)
    else:
        ap.error('one of --sizes or --sdk is required')
    regions = read_regions(a.regions.read_text(encoding='utf-8'))
    maps = {n: Map((a.maps / (n + '.bsp')).read_bytes()) for n in regions}
    result = estimate(maps, regions, sizes, a.grain, a.draw_distance, a.hysteresis, a.collision_margin,
                      a.mode, a.rule, a.prefetch)
    text = json.dumps(result, indent=1, sort_keys=True) + '\n'
    if a.out:
        a.out.write_bytes(text.encode('utf-8'))
    else:
        brief = {k: v for k, v in result.items() if k != 'per_chunk'}
        sys.stdout.write(json.dumps(brief, indent=1, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
