#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Share exact immutable BSP geometry metadata without removing any faces.

World edge records retain distinct cache identities. Only inline-only edges may
share records: the engine's insubmodel renderer path bypasses cached-edge reuse.
Surface records, texture mappings, lighting, model ranges and collision stay
separate and unchanged. This is an offline candidate operation, not acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from player_hull import lumps, pack_lumps


def parse(raw):
    data = lumps(raw)
    formats = {3: '<3f', 5: '<i2h6h2H', 7: '<Hhihh4Bi',
               11: '<H', 12: '<HH', 13: '<i', 14: '<9f7i'}
    try:
        rows = {i: list(struct.iter_unpack(fmt, data[i])) for i, fmt in formats.items()}
    except struct.error as exc:
        raise ValueError('Invalid geometry record length') from exc
    if not rows[14] or not rows[12]:
        raise ValueError('Missing world model or reserved edge')
    for edge in rows[12]:
        if any(v >= len(rows[3]) for v in edge):
            raise ValueError('Invalid edge vertex index')
    for (edge,) in rows[13]:
        if abs(edge) >= len(rows[12]):
            raise ValueError('Invalid signed surface edge index')
    for face in rows[7]:
        first, count = face[2:4]
        if first < 0 or count < 1 or first+count > len(rows[13]):
            raise ValueError('Invalid face edge range')
    def checked_faces(first, count):
        if first < 0 or count < 0 or first+count > len(rows[7]):
            raise ValueError('Invalid model or node face range')
        return range(first, first+count)
    protected_faces = set(checked_faces(*rows[14][0][14:16]))
    for node in rows[5]:
        protected_faces.update(checked_faces(*node[9:11]))
    for (mark,) in rows[11]:
        if mark >= len(rows[7]):
            raise ValueError('Invalid leaf face reference')
        protected_faces.add(mark)
    for model in rows[14]:
        checked_faces(*model[14:16])
    protected_edges = {0}
    for index in protected_faces:
        face = rows[7][index]
        protected_edges.update(abs(row[0]) for row in rows[13][face[2]:face[2]+face[3]])
    return data, rows, protected_edges


def face_vertices(data, rows, face):
    points = []
    for (signed,) in rows[13][face[2]:face[2]+face[3]]:
        edge = rows[12][abs(signed)]
        vertex = edge[0 if signed >= 0 else 1]
        points.append(bytes(data[3][vertex*12:(vertex+1)*12]))
    return points


def share_geometry(raw):
    source, old, protected = parse(raw)
    out = [bytearray(part) for part in source]
    vertices = bytearray()
    vertex_lookup = {}
    vertex_map = []
    for offset in range(0, len(source[3]), 12):
        point = bytes(source[3][offset:offset+12])
        if point not in vertex_lookup:
            vertex_lookup[point] = len(vertices)//12
            vertices.extend(point)
        vertex_map.append(vertex_lookup[point])
    edges = []
    edge_map = {}
    # Reserve edge zero and retain a unique record for each protected world edge.
    for index in sorted(protected):
        edge_map[index] = (len(edges), 1)
        edges.append(tuple(vertex_map[v] for v in old[12][index]))
    inline_lookup = {}
    for index, edge in enumerate(old[12]):
        if index in protected:
            continue
        mapped = tuple(vertex_map[v] for v in edge)
        key = tuple(sorted(mapped))
        if key not in inline_lookup:
            inline_lookup[key] = len(edges)
            edges.append(key)
        edge_map[index] = (inline_lookup[key], 1 if mapped == key else -1)
    sequences = []
    sequence_lookup = {}
    for i, face in enumerate(old[7]):
        sequence = []
        for (signed,) in old[13][face[2]:face[2]+face[3]]:
            index, orientation = edge_map[abs(signed)]
            sequence.append(index*orientation*(-1 if signed < 0 else 1))
        key = tuple(sequence)
        if key not in sequence_lookup:
            sequence_lookup[key] = len(sequences)
            sequences.extend(sequence)
        struct.pack_into('<i', out[7], i*20+4, sequence_lookup[key])
    out[3] = vertices
    out[12] = bytearray().join(struct.pack('<HH', *edge) for edge in edges)
    out[13] = bytearray().join(struct.pack('<i', edge) for edge in sequences)
    result = pack_lumps(out)
    final, new, new_protected = parse(result)
    for index, (a, b) in enumerate(zip(old[7], new[7])):
        if a[:2]+a[3:] != b[:2]+b[3:] or face_vertices(source, old, a) != face_vertices(final, new, b):
            raise ValueError('Face order, geometry or non-edge metadata changed at '+str(index))
    if len(new[7]) != len(old[7]):
        raise ValueError('Face count changed')
    for index in set(range(15))-{3, 7, 12, 13}:
        if source[index] != final[index]:
            raise ValueError('Unexpected modification to BSP lump '+str(index))
    protected_mapped = {edge_map[i][0] for i in protected}
    inline_mapped = {edge_map[i][0] for i in edge_map if i not in protected}
    if len(protected_mapped) != len(protected) or protected_mapped & inline_mapped:
        raise ValueError('World edge cache identities were shared')
    return result, {'status': 'offline exact-sharing candidate; target playtest pending',
                    'source_sha256': hashlib.sha256(raw).hexdigest(),
                    'result_sha256': hashlib.sha256(result).hexdigest(),
                    'vertices_before': len(old[3]), 'vertices_after': len(new[3]),
                    'edges_before': len(old[12]), 'edges_after': len(new[12]),
                    'surfedges_before': len(old[13]), 'surfedges_after': len(new[13]),
                    'faces_verified': len(new[7]), 'world_edge_identities_preserved': len(protected),
                    'vertex_coordinates_and_face_winding': 'byte-identical',
                    'texinfo_light_models_collision_entities': 'unchanged lump bytes',
                    'file_bytes_before': len(raw), 'file_bytes_after': len(result)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.source.resolve() in (args.output.resolve(), args.report.resolve()):
        parser.error('Source must not be overwritten')
    result, report = share_geometry(args.source.read_bytes())
    args.output.write_bytes(result)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
