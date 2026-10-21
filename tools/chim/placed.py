# SPDX-License-Identifier: GPL-3.0-only
"""CHIM world format 0.8 (EXPERIMENTAL, build setting placement_format '0.8', default off): one stored model per
mesh + scale, the full rotation in the placement record, collision from the mesh's own convex pieces placed at run
time (docs/chim/WORLD_FORMAT.md "Format 0.8: placed models").

What changes against 0.7 (everything else is the 0.7 layout, read and written by chim.format):

- Placement record: 56 bytes, the 48 bytes of 0.7 followed by the pitch and the roll (f32, degrees). The three angles
  are Quake's entity angles (pitch, yaw, roll): the renderer turns the model with them as it turns any brush entity
  (r_bsp.c R_BuildBmodelRotation), and the engine's collision builds the same matrix from them
  (chim_placed_clip.c ChimPlaced_AnglesMatrix). The builder converts TES3's rotation (Z, then Y, then X of the negated
  angles: prepare_scenery.reference_rotation) once (quake_angles) and checks the result against it.
- A chunk record holding 56-byte records says so in its head: the last u16 of CHUNK_HEAD (0 until 0.7) is the record
  size. read_chunk reads either kind.
- A placed model (MODL) is built untilted (scale and the visual offset baked, as the untilted variants of 0.7), so
  one model serves every tilt of a mesh + scale. Its brush image's lump 4 (visibility, unused by a placed model)
  holds the piece table: the model's convex collision pieces unexpanded, in the model's frame (piece_table). The
  engine expands them by the world-aligned player box when a trace meets them (OpenMW's actor box rule; PLACED note).
  The stored standing hull stays in the image: the engine falls back to it when a table cannot be used.
- Models that clip their faces to the terrain (a visual recipe's clip_to_terrain) keep the 0.7 variant with the tilt
  baked (their culled faces depend on each placement's pose); their records carry the yaw only.

Nothing here is reached by a default build: the default unit kinds ('variant', 'tiles') and chim.format,
chim.models, chim.cut and prepare_mesh_bsp are unchanged (their cache keys stay), the 0.8 units have their own kinds
('variant-placed', 'tiles-placed': chim.units.CODE_ENTRIES).

Importing this module lets chim.format read and write world format 0.8 (chim.format.READ_VERSIONS gains it): 0.8
files are 0.7 files apart from the record size, which only read_chunk below needs.
"""
import math
import struct
from contextlib import contextmanager

from chim import format as F

FORMAT_VERSION = (0, 8)
SETTING = 'placement_format'
FORMATS = ('0.7', '0.8')        # '0.7': the records and models of formats 0.5/0.7 (default)
PLACEMENT = struct.Struct('>IIIffffHbb6hHHff')     # 56 bytes
RECORD_BYTES_AT = 22            # CHUNK_HEAD: the record size (0: the 48-byte record of 0.4-0.7)
PIECE_MAGIC = b'PCS1'
PIECE_HEAD = struct.Struct('>4sIII')               # magic, pieces, table bytes, 0
PIECE_ENTRY = struct.Struct('>HHHH6fI')            # planes, corners, edges, 0, box mins/maxs, data offset: 36 bytes
MAX_PIECE_PLANES = 128          # chim_placed_clip.h CHIM_PLACED_PIECE_PLANES: more is not expanded (fallback)
ANGLE_CHECK = 1e-5              # quake_angles: the matrix of the stored angles against reference_rotation

if FORMAT_VERSION not in F.READ_VERSIONS:
    F.READ_VERSIONS = F.READ_VERSIONS + (FORMAT_VERSION,)


def placement_format(settings):
    """The build setting placement_format: '0.7' (default) or '0.8' (EXPERIMENTAL)."""
    value = str((settings or {}).get(SETTING, '0.7'))
    if value not in FORMATS:
        raise ValueError('Unknown CHIM placement format: %s (0.7 or 0.8)' % value)
    return value


def placed_on(settings):
    return placement_format(settings) == '0.8'


# ---------------------------------------------------------------- angles

def untilted(rotation):
    """True when x and y turn nothing (chim.models.variant_ref's rule): the placement is a yaw only."""
    return not any(abs(math.sin(a)) > 1e-7 or math.cos(a) < 0 for a in rotation[:2])


def entity_rotation(angles):
    """r_bsp.c R_BuildBmodelRotation for Quake angles (pitch, yaw, roll, degrees): world to model (rows)."""
    import numpy as np
    sp, cp = math.sin(math.radians(angles[0])), math.cos(math.radians(angles[0]))
    sy, cy = math.sin(math.radians(angles[1])), math.cos(math.radians(angles[1]))
    sr, cr = math.sin(math.radians(angles[2])), math.cos(math.radians(angles[2]))
    yaw = np.array([[cy, sy, 0], [-sy, cy, 0], [0, 0, 1]])
    if not angles[0] and not angles[2]:
        return yaw
    pitch = np.array([[cp, 0, -sp], [0, 1, 0], [sp, 0, cp]])
    roll = np.array([[1, 0, 0], [0, cr, sr], [0, -sr, cr]])
    return roll @ (pitch @ yaw)


def model_matrix(angles):
    """Model to world for Quake angles: world = origin + model_matrix(angles) @ point."""
    return entity_rotation(angles).T


def quake_angles(ref):
    """(pitch, yaw, roll) in degrees, single precision, whose model_matrix is the placement's TES3 rotation
    (prepare_scenery.reference_rotation); a yaw-only placement gets chim.models.yaw_degrees exactly (the 0.7
    record's yaw)."""
    import numpy as np
    from prepare_scenery import reference_rotation
    rot = ref['rotation_radians']
    if untilted(rot):
        return (0.0, F32(-rot[2] * 180 / math.pi), 0.0)
    m = reference_rotation(ref)
    e = m.T
    sp = max(-1.0, min(1.0, -e[0][2]))
    pitch = math.degrees(math.asin(sp))
    if abs(math.cos(math.radians(pitch))) > 1e-6:
        yaw = math.degrees(math.atan2(e[0][1], e[0][0]))
        roll = math.degrees(math.atan2(e[1][2], e[2][2]))
    else:                       # pitch +-90: yaw and roll turn about one axis; roll 0
        yaw = math.degrees(math.atan2(-e[1][0], e[1][1]))
        roll = 0.0
    angles = (F32(pitch), F32(yaw), F32(roll))
    error = float(np.abs(model_matrix(angles) - m).max())
    if error > ANGLE_CHECK:
        raise ValueError('Placement %s: Quake angles %s are %.3g from its rotation' % (ref.get('number'), angles, error))
    return angles


def F32(x):
    return struct.unpack('>f', struct.pack('>f', float(x)))[0]


def untilt(ref):
    """The placement as the shared model is built: no rotation (scale, visual offset, flattening kept)."""
    return dict(ref, rotation_radians=[0.0, 0.0, 0.0])


# ---------------------------------------------------------------- records

def placement(pid, ref, model, origin, angles, owner, cell_dx, cell_dy, box, leaves, story_hidden=False):
    """A 0.8 record: chim.format.placement's 48 bytes with angles[1] as the yaw, then pitch and roll."""
    head = F.placement(pid, ref, model, origin, angles[1], owner, cell_dx, cell_dy, box, leaves, story_hidden)
    return head + struct.pack('>ff', angles[0], angles[2])


def read_placement(data, offset=0):
    v = PLACEMENT.unpack_from(data, offset)
    r = F.read_placement(data, offset)
    r['angles'] = (v[18], v[6], v[19])
    return r


def _with_record_bytes(data):
    return data[:RECORD_BYTES_AT] + struct.pack('>H', PLACEMENT.size) + data[RECORD_BYTES_AT + 2:]


def chunk_record(owned, reach, pvs, image, image_render, leaves, pvl=b''):
    """chim.format.chunk_record for 56-byte records (the head says the record size)."""
    data, render, collision = F.chunk_record(owned, reach, pvs, image, image_render, leaves, pvl)
    return _with_record_bytes(data), render, collision


def chunk_record_ref(owned, reach, pvs, ref, leaves, pvl=b''):
    data, render, collision = F.chunk_record_ref(owned, reach, pvs, ref, leaves, pvl)
    return _with_record_bytes(data), render, collision


def record_size(raw):
    """Placement record bytes of a chunk record: 56 (format 0.8) or 48."""
    n = struct.unpack_from('>H', raw, RECORD_BYTES_AT)[0]
    if n not in (0, PLACEMENT.size):
        raise ValueError('Chunk record names a placement record of %d bytes' % n)
    return n or F.PLACEMENT.size


def read_chunk(raw):
    """chim.format.read_chunk for either record size (a 0.8 record also has 'angles')."""
    if record_size(raw) == F.PLACEMENT.size:
        return F.read_chunk(raw)
    magic, n_owned, n_reach, image_at, image_render, pvs_bytes, leaves, pvl_bytes, _ = F.CHUNK_HEAD.unpack_from(raw)
    if magic not in (F.CHUNK_MAGIC, F.CHUNK_MAGIC_REF):
        raise ValueError('Not a chunk record')
    recs = [read_placement(raw, F.CHUNK_HEAD.size + k * PLACEMENT.size) for k in range(n_owned + n_reach)]
    pvs_at = F.CHUNK_HEAD.size + (n_owned + n_reach) * PLACEMENT.size
    if image_at < pvs_at + pvs_bytes + pvl_bytes or image_at + image_render > len(raw):
        raise ValueError('Chunk record parts overlap or overrun')
    return {'owned': recs[:n_owned], 'reach': recs[n_owned:], 'pvs': raw[pvs_at:pvs_at + pvs_bytes],
            'pvl': raw[pvs_at + pvs_bytes:pvs_at + pvs_bytes + pvl_bytes],
            'leaves': leaves, 'image': raw[image_at:], 'image_render': image_render,
            'render': image_at + image_render,
            **({'ref': F.read_terrain_ref(raw[image_at:])} if magic == F.CHUNK_MAGIC_REF else {})}


def placed_box(origin, angles, lo, hi):
    """Drawn box of a placement turned by its three angles (aw_scenery.c AW_SceneryCapture: AngleVectors)."""
    from world_chunk_estimate import placed_box as box
    return box(origin, tuple(angles), lo, hi)


def place_points(points, origin, angles):
    """Model-frame points placed with an origin and Quake angles."""
    import numpy as np
    p = np.asarray(points, float)
    return p @ model_matrix(angles).T + np.asarray(origin, float)


# ---------------------------------------------------------------- piece table

def piece_rows(parts):
    """[(planes [(nx, ny, nz, d)] with n.x < d inside, corners [(x, y, z)], edges [(plane a, plane b, corner)],
    (mins, maxs))] of convex pieces (points, ...) in the model frame. Planes are the piece's own faces rounded as the
    point hull stores them (chim.models.BrushLumps.collider: 1e-5); an edge is a pair of planes that share two hull
    corners (qhull's facets, so coplanar facets are one plane)."""
    import numpy as np
    from scipy.spatial import ConvexHull
    out = []
    for piece in parts:
        points = np.asarray(piece[0], float)
        hull = ConvexHull(points)
        keys = np.round(hull.equations, 5)
        planes, index = np.unique(keys, axis=0, return_inverse=True)
        index = np.asarray(index).reshape(-1)
        corners_of = [set() for _ in range(len(planes))]
        for facet, simplex in enumerate(hull.simplices):
            corners_of[index[facet]].update(int(v) for v in simplex)
        ids = sorted(set(int(v) for v in hull.vertices))
        at = {v: k for k, v in enumerate(ids)}
        edges = []
        for a in range(len(planes)):
            for b in range(a + 1, len(planes)):
                shared = corners_of[a] & corners_of[b]
                if len(shared) >= 2:
                    edges.append((a, b, at[min(shared)]))
        out.append(([(float(e[0]), float(e[1]), float(e[2]), float(-e[3])) for e in planes],
                    [tuple(float(v) for v in points[i]) for i in ids], edges,
                    ([float(v) for v in points.min(axis=0)], [float(v) for v in points.max(axis=0)])))
    return out


def piece_table(parts):
    """The piece table of a placed model (lump 4 of its brush image), big-endian:
    head (PCS1, pieces, bytes, 0); one 36-byte entry per piece (planes, corners, edges, 0, box mins and maxs, offset
    of its data from the table's start); per piece its planes (4 x f32: normal, distance; inside n.x < d), corners
    (3 x f32) and edges (3 x u16: plane a, plane b, corner), padded to 4 bytes."""
    rows = piece_rows(parts)
    at = PIECE_HEAD.size + PIECE_ENTRY.size * len(rows)
    entries, body = [], bytearray()
    for planes, corners, edges, (lo, hi) in rows:
        if max(len(planes), len(corners), len(edges)) > 65535:
            raise ValueError('A collision piece is too large for the piece table')
        entries.append(PIECE_ENTRY.pack(len(planes), len(corners), len(edges), 0, *lo, *hi, at + len(body)))
        for p in planes:
            body += struct.pack('>4f', *p)
        for c in corners:
            body += struct.pack('>3f', *c)
        for e in edges:
            body += struct.pack('>3H', *e)
        body += bytes(F.align(len(body)) - len(body))
    total = at + len(body)
    return PIECE_HEAD.pack(PIECE_MAGIC, len(rows), total, 0) + b''.join(entries) + bytes(body)


def read_piece_table(data):
    """[(planes, corners, edges, (mins, maxs))] of a piece table (piece_table's rows, single precision)."""
    magic, n, total, _ = PIECE_HEAD.unpack_from(data)
    if magic != PIECE_MAGIC or total > len(data):
        raise ValueError('Not a piece table')
    out = []
    for k in range(n):
        np_, nc, ne, _, *box, at = PIECE_ENTRY.unpack_from(data, PIECE_HEAD.size + k * PIECE_ENTRY.size)
        planes = [struct.unpack_from('>4f', data, at + 16 * j) for j in range(np_)]
        at += 16 * np_
        corners = [struct.unpack_from('>3f', data, at + 12 * j) for j in range(nc)]
        at += 12 * nc
        edges = [struct.unpack_from('>3H', data, at + 6 * j) for j in range(ne)]
        out.append((planes, corners, edges, (tuple(box[:3]), tuple(box[3:]))))
    return out


def table_usable(data):
    """True when the engine can expand every piece of the table (at most MAX_PIECE_PLANES planes each)."""
    return all(len(planes) <= MAX_PIECE_PLANES for planes, *_ in read_piece_table(data))


@contextmanager
def piece_tables():
    """Inside the block every model image chim.models.model_image_lumps writes carries its pieces' table in lump 4
    (the callers, chim.models.variant_unit and chim.cut.tile_unit, import it at call time)."""
    import chim.models as M
    original = M.model_image_lumps

    def model_image_lumps(surfaces, parts, *args, **kw):
        lumps, keys = original(surfaces, parts, *args, **kw)
        lumps = list(lumps)
        lumps[4] = bytearray(piece_table(parts))
        return lumps, keys
    M.model_image_lumps = model_image_lumps
    try:
        yield
    finally:
        M.model_image_lumps = original


def variant_unit_placed(task):
    """chim.models.variant_unit with the piece table in the model image (unit kind 'variant-placed')."""
    from chim.models import variant_unit
    with piece_tables():
        return variant_unit(task)


def tile_unit_placed(task):
    """chim.cut.tile_unit with the piece table in every tile's image (unit kind 'tiles-placed')."""
    from chim.cut import tile_unit
    with piece_tables():
        return tile_unit(task)
