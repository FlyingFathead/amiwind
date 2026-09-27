"""Asset-independent geometry packets and spatial queries for host experiments."""
import hashlib
import math
import struct

HEADER = struct.Struct('>4sHHII')
VERTEX = struct.Struct('>5f4B')  # position XYZ, UV, baked vertex RGBA
FACE = struct.Struct('>4H')     # three vertex indices and material index


def pack_geometry(vertices, faces, material_count):
    if not 0 < len(vertices) <= 65535 or not 0 < len(faces) <= 1000000:
        raise ValueError('Geometry count outside packet bounds')
    if not 0 < material_count <= 65535:
        raise ValueError('Invalid material count')
    out = bytearray(HEADER.pack(b'MWG1', 1, material_count, len(vertices), len(faces)))
    for v in vertices:
        if len(v) != 9 or not all(math.isfinite(x) and abs(x) < 1e7 for x in v[:5]):
            raise ValueError('Invalid geometry vertex')
        out.extend(VERTEX.pack(*v))
    for face in faces:
        if len(face) != 4 or any(i < 0 or i >= len(vertices) for i in face[:3]) or not 0 <= face[3] < material_count:
            raise ValueError('Invalid geometry face')
        out.extend(FACE.pack(*face))
    return bytes(out)


def unpack_geometry(data):
    if len(data) < HEADER.size:
        raise ValueError('Truncated geometry header')
    magic, version, materials, nv, nf = HEADER.unpack_from(data)
    if magic != b'MWG1' or version != 1 or not 0 < nv <= 65535 or not 0 < nf <= 1000000 or not materials:
        raise ValueError('Unsupported geometry packet')
    split = HEADER.size + nv * VERTEX.size
    if len(data) != split + nf * FACE.size:
        raise ValueError('Geometry length mismatch')
    vertices = list(VERTEX.iter_unpack(data[HEADER.size:split]))
    faces = list(FACE.iter_unpack(data[split:]))
    if any(not math.isfinite(x) or abs(x) >= 1e7 for v in vertices for x in v[:5]):
        raise ValueError('Nonfinite or excessive geometry coordinate')
    if any(any(i >= nv for i in f[:3]) or f[3] >= materials for f in faces):
        raise ValueError('Geometry index outside packet')
    return vertices, faces, materials


def distance_to_bounds(point, bounds):
    return math.sqrt(sum(max(lo - x, 0, x - hi) ** 2 for x, lo, hi in zip(point, bounds[0], bounds[1])))


def visible_refs(index, position, distance):
    """Conservative sphere/AABB broad phase; no frustum or occlusion claim."""
    if distance <= 0 or not math.isfinite(distance) or len(position) != 3:
        raise ValueError('Invalid visibility query')
    if not all(math.isfinite(x) for x in position):
        raise ValueError('Invalid camera position')
    return [r for r in index['references'] if distance_to_bounds(position, r['bounds']) <= distance]


def resident_set(index, refs):
    """Account for shared model packets and all required texture payloads once."""
    models = {r['model_index'] for r in refs}
    textures = {t for m in models for t in index['models'][m]['textures']}
    return {'models': sorted(models), 'textures': sorted(textures),
            'geometry_bytes': sum(index['models'][m]['bytes'] for m in models),
            'texture_bytes': sum(index['textures'][t]['bytes'] for t in textures),
            'placed_triangles': sum(index['models'][r['model_index']]['triangles'] for r in refs),
            'references': len(refs)}


def read_asset(archive, record):
    """Seek just the required asset; reject truncated/modified payloads."""
    offset, size = record['offset'], record['bytes']
    if offset < 0 or offset % 512 or size <= 0 or size > 64 * 1024 * 1024:
        raise ValueError('Invalid scene archive extent')
    archive.seek(offset)
    data = archive.read(size)
    if len(data) != size or hashlib.sha256(data).hexdigest() != record['sha256']:
        raise ValueError('Scene archive payload mismatch')
    return data
