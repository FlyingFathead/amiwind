# SPDX-License-Identifier: GPL-3.0-only
"""Index a compiled convex-piece union without changing its solid volumes.

Large authored room shells otherwise test every convex piece for every trace.
A balanced bounds hierarchy adds cheap rejection planes. Original piece planes
and solid leaves are retained; only their empty continuations are redirected.
"""
import re
import struct
from player_hull import MINS, MAXS, lumps, pack_lumps


def index_model_collision(path, reference, leaf_size=8):
    data = lumps(path.read_bytes())
    entities = data[0].decode('cp1252')
    selected = []
    for block in re.findall(r'\{[^}]*\}', entities):
        values = dict(re.findall(r'"([^"\n]+)" "([^"\n]*)"', block))
        if values.get('aw_ref') == str(reference) and values.get('model', '').startswith('*'):
            selected.append(int(values['model'][1:]))
    if len(selected) != 1 or leaf_size < 2:
        raise ValueError('Collision index needs one placed model and leaf size >= 2')
    model = selected[0]
    roots = struct.unpack_from('<2i', data[14], model*64+36)
    before = [len(data[5])//24, len(data[9])//8, len(data[1])//20]

    def nodes(section):
        stride = 24 if section == 5 else 8
        result = []
        for offset in range(0, len(data[section]), stride):
            plane, a, b = struct.unpack_from('<iHH', data[section], offset)
            threshold = 32768 if section == 5 else 65520
            result.append([plane, a-65536 if a >= threshold else a,
                           b-65536 if b >= threshold else b])
        return result

    def pieces(tree, root):
        result = [];seen = set()
        while root >= 0:
            ids = [];outside = tree[root][1];n = root
            while n >= 0:
                if n in seen or n >= len(tree) or tree[n][1] != outside:
                    raise ValueError('Expected an unindexed convex-piece union')
                seen.add(n);ids.append(n);n = tree[n][2]
            result.append(ids);root = outside
        return result, root

    point_tree, clip_tree = nodes(5), nodes(9)
    point_parts, point_empty = pieces(point_tree, roots[0])
    clip_parts, clip_empty = pieces(clip_tree, roots[1])
    if len(point_parts) != len(clip_parts) or len(point_parts) < leaf_size*2:
        raise ValueError('Collision index needs matching, sufficiently large hulls')
    bounds = [struct.unpack_from('<6h', data[5], ids[0]*24+8) for ids in point_parts]
    source_planes = list(struct.iter_unpack('<4fi', data[1]))
    for ids, box in zip(clip_parts, bounds):
        for axis in range(3):
            for sign in (-1, 1):
                limit = box[axis+3]-MINS[axis] if sign>0 else -box[axis]+MAXS[axis]
                supported = False
                for n in ids:
                    p = source_planes[clip_tree[n][0]]
                    if all(abs(p[a]-(sign if a==axis else 0))<1e-5 for a in range(3)) and p[3]<=limit+.01:
                        supported = True;break
                if not supported:
                    raise ValueError('Standing piece lacks verified axial bounds')
    plane_cache = {}

    def plane(axis, sign, distance):
        key = (axis, sign, distance)
        if key not in plane_cache:
            normal = [0., 0., 0.];normal[axis] = sign
            plane_cache[key] = len(data[1])//20
            data[1] += struct.pack('<4fi', *normal, distance, 3)
        return plane_cache[key]

    def compile_tree(section, tree, parts, empty, expanded):
        stride = 24 if section == 5 else 8
        def emit(axis, sign, distance, outside, inside):
            index = len(tree)
            if index >= (32767 if section == 5 else 65520):
                raise ValueError('Collision index exceeds native node budget')
            tree.append([plane(axis, sign, distance), outside, inside])
            data[section] += bytes(stride)
            return index
        def build(ids, fallback, top=False):
            low = [min(bounds[i][a] for i in ids) for a in range(3)]
            high = [max(bounds[i][a+3] for i in ids) for a in range(3)]
            if len(ids) <= leaf_size:
                entry = fallback
                for i in reversed(ids):
                    for n in parts[i]:tree[n][1] = entry
                    entry = parts[i][0]
            else:
                axis = max(range(3), key=lambda a: max(bounds[i][a]+bounds[i][a+3] for i in ids)-min(bounds[i][a]+bounds[i][a+3] for i in ids))
                ids = sorted(ids, key=lambda i: (bounds[i][axis]+bounds[i][axis+3], i))
                mid = len(ids)//2
                second = build(ids[mid:], fallback)
                entry = build(ids[:mid], second)
            if not top:
                for a in range(3):
                    # Stored source bounds are rounded outward; pad numeric noise.
                    lo = low[a] - (MAXS[a] if expanded else 0) - .05
                    hi = high[a] - (MINS[a] if expanded else 0) + .05
                    entry = emit(a, -1., -lo, fallback, entry)
                    entry = emit(a, 1., hi, fallback, entry)
            return entry
        root = build(list(range(len(parts))), empty, top=True)
        # Quake validates every visited node against firstclipnode. Keep the
        # entry at the original lowest index, even though bounds were appended.
        first = parts[0][0]
        tree[first], tree[root] = tree[root], tree[first]
        for node in tree:
            for side in (1, 2):
                if node[side] == first:node[side] = root
                elif node[side] == root:node[side] = first
        root = first
        for i, (pi, front, back) in enumerate(tree):
            struct.pack_into('<iHH', data[section], i*stride, pi, front & 65535, back & 65535)
        return root

    new_point = compile_tree(5, point_tree, point_parts, point_empty, False)
    new_clip = compile_tree(9, clip_tree, clip_parts, clip_empty, True)
    for offset in range(0, len(data[14]), 64):
        if struct.unpack_from('<2i', data[14], offset+36) == roots:
            struct.pack_into('<4i', data[14], offset+36, new_point, new_clip, new_clip, new_clip)
    path.write_bytes(pack_lumps(data))
    return {'reference': reference, 'pieces': len(point_parts), 'leaf_size': leaf_size,
            'before_nodes_clipnodes_planes': before,
            'after_nodes_clipnodes_planes': [len(data[5])//24, len(data[9])//8, len(data[1])//20],
            'geometry': 'original convex piece planes and solid leaves retained'}
