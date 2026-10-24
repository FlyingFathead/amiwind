#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Interior store: every room's mesh models and textures stored once (docs/chim/INTERIOR_STORE.md).

EXPERIMENTAL (v0.0.48 line, off by default). Made from the rooms the builder makes today: each room map is read,
each placement's inline model (the func_wall "*N" of a placed mesh) is cut out into a brush image of its own
(the CHIM model record form, docs/chim/WORLD_FORMAT.md "Model record": texture lump = global texture references,
lighting lump empty, face light offsets relative to the model's own lightmap layout), and equal images (SHA-256)
are one store model. Each placement keeps the light samples it had, as a block of its own. So a room drawn from
the store has the same faces, mapping, light and collision as the room it was cut from.

    python3 tools/interior_store.py measure --maps DIR [--maps DIR ...] --out FILE [--jobs N]
        cut every room map (*.bsp) in DIR and write the receipt: models met, stored once, bytes A and B.

Nothing derived from your files is part of this repository.
"""
import argparse
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chim.format import brush_image, texture_content  # noqa: E402

BSPVERSION = 29
HEADER_BYTES = 4 + 15 * 8
PLANE = struct.Struct('<4fi')
VERTEX = struct.Struct('<3f')
NODE = struct.Struct('<i2h6h2H')
TEXINFO = struct.Struct('<8fii')
FACE = struct.Struct('<HhiHH4Bi')
CLIPNODE = struct.Struct('<i2h')
LEAF = struct.Struct('<2i6h2H4B')
EDGE = struct.Struct('<2H')
MODEL = struct.Struct('<9f7i')
TEX_SPECIAL = 1
# Placement entities: a placed mesh is a func_wall naming an inline model (prepare_mesh_bsp.placement_entity).
PLACEMENT_CLASSES = ('func_wall',)
INLINE = re.compile(r'^\*(\d+)$')


def _records(data, st):
    if len(data) % st.size:
        raise ValueError('Lump of %d bytes is not a whole number of %d-byte records' % (len(data), st.size))
    return list(st.iter_unpack(data))


def parse_entities(text):
    """[(dict, block text)] in file order; keys keep their first value as Quake's parser does."""
    out = []
    for block in re.findall(r'\{[^{}]*\}', text):
        d = {}
        for k, v in re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"', block):
            d.setdefault(k, v)
        out.append(d)
    return out


class Room:
    """A room map (BSP29) read for cutting: raw lumps and decoded records."""

    def __init__(self, data, name=''):
        if len(data) < HEADER_BYTES or struct.unpack_from('<i', data)[0] != BSPVERSION:
            raise ValueError('%s: not a BSP29 map' % name)
        self.name, self.data = name, data
        self.lumps = []
        for i in range(15):
            o, n = struct.unpack_from('<ii', data, 4 + 8 * i)
            if o < 0 or n < 0 or o + n > len(data):
                raise ValueError('%s: lump %d outside the file' % (name, i))
            self.lumps.append(data[o:o + n])
        L = self.lumps
        self.planes = _records(L[1], PLANE)
        self.vertexes = _records(L[3], VERTEX)
        self.nodes = _records(L[5], NODE)
        self.texinfo = _records(L[6], TEXINFO)
        self.faces = _records(L[7], FACE)
        self.lighting = L[8]
        self.clipnodes = _records(L[9], CLIPNODE)
        self.leafs = _records(L[10], LEAF)
        self.marksurfaces = [v[0] for v in struct.iter_unpack('<H', L[11])]
        self.edges = _records(L[12], EDGE)
        self.surfedges = [v[0] for v in struct.iter_unpack('<i', L[13])]
        self.models = _records(L[14], MODEL)
        self.miptex = self._miptex(L[2])
        self.entities = parse_entities(L[0].decode('cp1252', 'replace').rstrip('\0'))

    @staticmethod
    def _miptex(lump):
        """[(engine name, miptex bytes) or None] per texture index."""
        if not lump:
            return []
        count = struct.unpack_from('<i', lump)[0]
        offsets = struct.unpack_from('<%di' % count, lump, 4)
        ends = sorted(o for o in offsets if o >= 0) + [len(lump)]
        out = []
        for o in offsets:
            if o < 0:
                out.append(None)
                continue
            end = min(e for e in ends if e > o)
            name = lump[o:o + 16].split(b'\0')[0].decode('ascii', 'replace')
            out.append((name, bytes(lump[o:end])))
        return out

    def face_vertexes(self, f):
        first, num = self.faces[f][2], self.faces[f][3]
        return [self.edges[e][0] if e >= 0 else self.edges[-e][1] for e in self.surfedges[first:first + num]]

    def light_bytes(self, f):
        """Bytes of a face's light samples, as the engine sizes them (CalcSurfaceExtents: 16-unit blocks)."""
        face = self.faces[f]
        styles = sum(1 for s in face[5:9] if s != 255)
        ti = self.texinfo[face[4]]
        if face[9] < 0 or not styles or ti[9] & TEX_SPECIAL:
            return 0
        lo, hi = [math.inf, math.inf], [-math.inf, -math.inf]
        for v in self.face_vertexes(f):
            p = self.vertexes[v]
            for j in range(2):
                s = p[0] * ti[j * 4] + p[1] * ti[j * 4 + 1] + p[2] * ti[j * 4 + 2] + ti[j * 4 + 3]
                lo[j], hi[j] = min(lo[j], s), max(hi[j], s)
        size = 1
        for j in range(2):
            size *= (math.ceil(hi[j] / 16) - math.floor(lo[j] / 16)) + 1
        return size * styles

    def placements(self):
        """[(entity index, inline model number, entity)] of the placed meshes."""
        out = []
        for i, e in enumerate(self.entities):
            m = INLINE.match(e.get('model', ''))
            if e.get('classname') in PLACEMENT_CLASSES and m and int(m.group(1)) > 0:
                out.append((i, int(m.group(1)), e))
        return out


class _Renumber:
    """First-seen numbering: the cut image's order is the order of use, so equal models cut equal."""

    def __init__(self, first=0):
        self.index, self.order, self.first = {}, [], first

    def __call__(self, key):
        if key not in self.index:
            self.index[key] = self.first + len(self.order)
            self.order.append(key)
        return self.index[key]


def cut_model(room, number):
    """One inline model cut out of ROOM: (lumps, texture list, light block, face light layout).

    lumps: 15 BSP29 lumps of a one-model image; lump 2 is filled by the caller (texture references), lump 8 is empty
    and every lit face's light offset is relative to the model's own block. texture list: [(engine name, miptex)]
    by local index. light block: the samples this placement had, in face order."""
    if not 0 < number < len(room.models):
        raise ValueError('%s: no inline model %d' % (room.name, number))
    m = room.models[number]
    first_face, num_faces = m[14], m[15]
    heads = m[9:13]
    planes, verts, texinfos, textures = _Renumber(), _Renumber(), _Renumber(), _Renumber()
    edges = _Renumber(first=1)                       # edge 0 is never used (a surfedge's sign is its direction)
    out_faces, out_surfedges, block, layout = [], [], bytearray(), []
    for f in range(first_face, first_face + num_faces):
        planenum, side, fe, ne, ti, s0, s1, s2, s3, ofs = room.faces[f]
        se = []
        for e in room.surfedges[fe:fe + ne]:
            n = edges(abs(e))
            se.append(-n if e < 0 else n)
        new_ti = texinfos(ti)
        size = room.light_bytes(f)
        if size and ofs >= 0:
            if ofs + size > len(room.lighting):
                raise ValueError('%s model %d face %d: light samples past the light lump' % (room.name, number, f))
            rel = len(block)
            block += room.lighting[ofs:ofs + size]
        else:
            rel = -1
        layout.append((rel, size if rel >= 0 else 0))
        out_faces.append(FACE.pack(planes(planenum), side, len(out_surfedges), len(se), new_ti,
                                   s0, s1, s2, s3, rel))
        out_surfedges.extend(se)
    # hull 0: nodes in depth-first order (child 0 first), leaf 0 (the shared solid leaf) kept as leaf 0
    node_ids, leaf_ids = _Renumber(), _Renumber()
    leaf_ids(0)
    order, stack = [], [heads[0]]
    while stack:
        n = stack.pop()
        if n < 0:
            leaf_ids(-1 - n)
            continue
        if n in node_ids.index:
            continue
        node_ids(n)
        order.append(n)
        stack.extend(reversed(room.nodes[n][1:3]))
    out_nodes = []
    for n in order:
        planenum, c0, c1, *box, ff, nf = room.nodes[n]
        if nf and not (first_face <= ff and ff + nf <= first_face + num_faces):
            raise ValueError('%s model %d node %d: faces outside the model' % (room.name, number, n))
        kids = [node_ids.index[c] if c >= 0 else -1 - leaf_ids.index[-1 - c] for c in (c0, c1)]
        out_nodes.append(NODE.pack(planes(planenum), kids[0], kids[1], *box, (ff - first_face) if nf else 0, nf))
    out_leafs, out_marks = [], []
    for l in leaf_ids.order:
        contents, visofs, *box, fm, nm, a0, a1, a2, a3 = room.leafs[l]
        # an appended model's empty side is the world's shared empty leaf, which marks the world's faces; a brush
        # entity is drawn by its nodes' faces, never by leaf marks, so only marks of the model's own faces stay
        marks = [k - first_face for k in room.marksurfaces[fm:fm + nm] if first_face <= k < first_face + num_faces]
        out_leafs.append(LEAF.pack(contents, -1, *box, len(out_marks), len(marks), a0, a1, a2, a3))
        out_marks.extend(marks)
    # hulls 1 to 3: clipnodes in depth-first order per hull, shared subtrees once
    clip_ids, clip_order, new_heads = _Renumber(), [], [0]
    for head in heads[1:]:
        if head < 0 or head >= len(room.clipnodes):
            new_heads.append(head if head < 0 else 0)
            continue
        stack = [head]
        while stack:
            c = stack.pop()
            if c < 0 or c in clip_ids.index:
                continue
            clip_ids(c)
            clip_order.append(c)
            stack.extend(reversed([k for k in room.clipnodes[c][1:] if k >= 0]))
        new_heads.append(clip_ids.index[head])
    out_clip = []
    for c in clip_order:
        planenum, k0, k1 = room.clipnodes[c]
        out_clip.append(CLIPNODE.pack(planes(planenum), *(clip_ids.index[k] if k >= 0 else k for k in (k0, k1))))
    out_texinfo = []
    for ti in texinfos.order:
        *vecs, miptex, flags = room.texinfo[ti]
        out_texinfo.append(TEXINFO.pack(*vecs, textures(miptex), flags))
    lumps = [b''] * 15
    lumps[1] = b''.join(PLANE.pack(*room.planes[p]) for p in planes.order)
    lumps[3] = b''.join(VERTEX.pack(*room.vertexes[v]) for v in verts_of(room, edges.order, verts))
    lumps[5] = b''.join(out_nodes)
    lumps[6] = b''.join(out_texinfo)
    lumps[7] = b''.join(out_faces)
    lumps[9] = b''.join(out_clip)
    lumps[10] = b''.join(out_leafs)
    lumps[11] = struct.pack('<%dH' % len(out_marks), *out_marks)
    lumps[12] = EDGE.pack(0, 0) + b''.join(EDGE.pack(*(verts.index[v] for v in room.edges[e])) for e in edges.order)
    lumps[13] = struct.pack('<%di' % len(out_surfedges), *out_surfedges)
    head0 = node_ids.index[heads[0]] if heads[0] >= 0 else -1 - leaf_ids.index[-1 - heads[0]]
    lumps[14] = MODEL.pack(*m[0:9], head0, *new_heads[1:], m[13], 0, num_faces)
    texture_list = [room.miptex[t] if 0 <= t < len(room.miptex) else None for t in textures.order]
    return lumps, texture_list, bytes(block), layout


def verts_of(room, edge_order, verts):
    """Number the vertexes in the order the edges use them; returns that order."""
    for e in edge_order:
        for v in room.edges[e]:
            verts(v)
    return verts.order


def texture_key(entry):
    """Content identity of a texture (chim.format.texture_content), as hex; '' for a missing one."""
    if entry is None:
        return ''
    name, mip = entry
    return hashlib.sha256(texture_content(name, mip)).hexdigest()


def model_key(lumps, texture_list):
    """SHA-256 of a cut model: its image with the texture lump holding the textures' content keys."""
    keyed = list(lumps)
    keyed[2] = '\n'.join(texture_key(t) for t in texture_list).encode('ascii')
    image, _ = brush_image(keyed)
    return hashlib.sha256(image).hexdigest()


def measure_room(path):
    """Receipt rows of one room map: per placement its model key and bytes; the room's own bytes."""
    data = Path(path).read_bytes()
    room = Room(data, Path(path).name)
    rows, cut = [], {}
    for _, number, e in room.placements():
        if number not in cut:
            lumps, textures, block, layout = cut_model(room, number)
            image, render = brush_image(lumps)
            cut[number] = {'key': model_key(lumps, textures), 'image_bytes': len(image), 'render_bytes': render,
                           'light_bytes': len(block), 'light_sha256': hashlib.sha256(block).hexdigest(),
                           'textures': [texture_key(t) for t in textures],
                           'texture_bytes': {texture_key(t): len(t[1]) for t in textures if t}}
        rows.append(dict(cut[number], model=number, ref=e.get('aw_ref')))
    placed = set(cut)
    # bytes of the room's own part: everything but the cut models (world, other inline models, entities)
    return {'map': room.name, 'bytes': len(data), 'models': len(room.models), 'placements': rows,
            'cut_models': len(placed), 'light_lump': len(room.lighting)}


def summarize(rooms):
    store, textures = {}, {}
    a_bytes = sum(r['bytes'] for r in rooms)
    light = placed_bytes = 0
    for r in rooms:
        seen = set()
        for p in r['placements']:
            store.setdefault(p['key'], p['image_bytes'])
            for k, n in p['texture_bytes'].items():
                textures.setdefault(k, n)
            if p['model'] not in seen:
                seen.add(p['model'])
                placed_bytes += p['image_bytes']
                light += p['light_bytes']
    cut = sum(r['cut_models'] for r in rooms)
    return {'rooms': len(rooms), 'room_bytes_a': a_bytes, 'inline_models_cut': cut,
            'placements': sum(len(r['placements']) for r in rooms),
            'store_models': len(store), 'store_model_bytes': sum(store.values()),
            'store_textures': len(textures), 'store_texture_bytes': sum(textures.values()),
            'cut_image_bytes_a': placed_bytes, 'placement_light_bytes': light,
            'models_per_store_model': round(cut / max(1, len(store)), 2)}


def _measure_task(path):
    try:
        return measure_room(path)
    except ValueError as exc:
        return {'map': Path(path).name, 'error': str(exc)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('measure', help='cut every room map in --maps and write the receipt')
    m.add_argument('--maps', action='append', required=True)
    m.add_argument('--out', required=True)
    m.add_argument('--jobs', type=int, default=1)
    args = ap.parse_args(argv)
    paths = sorted(p for d in args.maps for p in Path(d).glob('*.bsp'))
    from build_parallel import ordered_map
    rooms = list(ordered_map(_measure_task, [str(p) for p in paths], max(1, args.jobs)))
    good = [r for r in rooms if 'error' not in r and r['placements']]
    receipt = {'format': 'aw-interior-store-measure-1', 'summary': summarize(good),
               'errors': [r for r in rooms if 'error' in r],
               'maps_without_placements': sorted(r['map'] for r in rooms if 'error' not in r and not r['placements']),
               'rooms': [{k: v for k, v in r.items() if k != 'placements'} for r in good]}
    Path(args.out).write_text(json.dumps(receipt, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(receipt['summary'], indent=1))
    print('errors: %d, maps without placements: %d' % (len(receipt['errors']), len(receipt['maps_without_placements'])))


if __name__ == '__main__':
    main()
