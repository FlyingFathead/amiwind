# SPDX-License-Identifier: GPL-3.0-only
"""CHIM far terrain: the resident distant-land layer of a frame (a sidecar of its frame map).

A CHIM frame map draws only the chunks of its active ring (the view distance
plus the hysteresis). Beyond them there is no ground at all, so the fully
fogged land outline that the legacy region maps drew at the fog plane (their
core plus 896 units of overlap on every side) was missing.

The far layer is the frame's land, coarse: one height every `step` Morrowind
units (default 512, every 4th LAND sample, 128 local units, the converter's
terrain step) over the frame plus `margin` cells on every side (default 1),
exact LAND heights at the samples (the same samples the chunk terrain uses),
the water level where the ground lies below it. Large placed objects (houses,
towers, big rocks) are stamped into it as their drawn boxes' tops (`stamps`),
kept apart so the engine can leave them out. The engine keeps it resident for
the whole map and draws it beyond the fog plane in the full fog colour, depth
tested, after the fog pass: the horizon method of record (aw_skyline_fill 0,
the land outline). No textures, no lighting, no collision, no BSP.

File (big-endian, as the 68k reads it; docs/chim/WORLD_FORMAT.md "Far terrain sidecar"):

    0  char[4]  'CHFL'
    4  u16      version (2; 1 = no stamps)
    6  u16      header bytes (40)
    8  i16, i16 the frame's centre cell (must match the frame map's _chim_frame)
    12 f32, f32 world position of sample (0, 0), Morrowind units
    20 f32      step between samples, Morrowind units
    24 f32      local units per Morrowind unit (0.25)
    28 u16, u16 samples across (x) and along (y)
    32 u16      block: quads per block side (the engine culls per block)
    34 u16      object stamps (version 2; 0 in version 1)
    36 u32      CRC-32 (zlib) of everything after the header
    40 i16[ny][nx] heights in local units (rows by y), max(ground, water level)
    then (version 2) u32[stamps] sample indices (j x nx + i, ascending), i16[stamps] heights,
    padded with zeros to a multiple of 4 bytes

The file is a sidecar of the frame map like a Quake .lit file: maps/<frame
map>.far beside maps/<frame map>.bsp. It is not part of the CHIM world
(chim/world.cwi does not list it) and has its own version, so it changes
neither the world format nor the disk-layout gate; an engine without far
terrain ignores it and a frame map without one draws no far land.
"""
import hashlib
import struct
import zlib
from pathlib import Path

import numpy as np

MAGIC = b'CHFL'
VERSION = 2
HEADER = struct.Struct('>4sHHhhffffHHHHI')      # 40 bytes
CELL = 8192                 # Morrowind units per exterior cell
LAND_SPACING = 128          # Morrowind units between LAND samples (65 per cell)
SCALE = 0.25                # local units per Morrowind unit (prepare_quake.SCALE)
WATER_LEVEL = 0.0           # local; the chunk terrain's water level (chim.terrain.WATER_LEVEL)
DEFAULT_STEP = 512          # Morrowind units: 128 local, the converter's terrain step
DEFAULT_MARGIN = 1          # cells beyond the frame on every side
DEFAULT_BLOCK = 16          # quads per block side (one cell at the default step)
STAMP_MIN_SIDE = 64         # local units: a drawn box narrower than this is not stamped (flora, lamps, crates)
STAMP_MIN_HEIGHT = 64       # local units above the ground under its centre
MAX_STAMPS = 65535
SUFFIX = '.far'


def land_heights(esm_path, cells=None):
    """{(cx, cy): 65 x 65 float array} of the LAND heights in a master (Morrowind units), as the
    town audit decodes them (mwad.audit.decode_heights: the same samples the chunk terrain uses).
    cells: only these cells (None: all)."""
    from mwad.audit import records, subrecords, decode_heights
    raw = Path(esm_path).read_bytes()
    out = {}
    for tag, _flags, payload in records(raw):
        if tag != 'LAND':
            continue
        s = dict(subrecords(payload))
        if len(s.get('INTV', b'')) != 8 or 'VHGT' not in s or 'DELE' in s:
            continue
        key = struct.unpack('<ii', s['INTV'])
        if cells is not None and key not in cells:
            continue
        out[key] = np.array(decode_heights(s['VHGT']), dtype=np.float64)
    return out


def area(centre, low, span, margin=DEFAULT_MARGIN, step=DEFAULT_STEP):
    """The far layer's sample grid for a frame: (world x0, world y0, nx, ny), the frame box
    (centre in Morrowind units, low and span in local units) grown by `margin` cells and snapped
    outward to the step grid (aligned to the cell grid)."""
    if step <= 0 or CELL % step or step % LAND_SPACING:
        raise ValueError('The far step must divide a cell and be a whole number of LAND samples')
    wx0 = centre[0] + low[0] / SCALE - margin * CELL
    wy0 = centre[1] + low[1] / SCALE - margin * CELL
    wx1 = centre[0] + (low[0] + span[0]) / SCALE + margin * CELL
    wy1 = centre[1] + (low[1] + span[1]) / SCALE + margin * CELL
    x0, y0 = int(np.floor(wx0 / step)) * step, int(np.floor(wy0 / step)) * step
    x1, y1 = int(np.ceil(wx1 / step)) * step, int(np.ceil(wy1 / step)) * step
    return x0, y0, (x1 - x0) // step + 1, (y1 - y0) // step + 1


def sample(lands, x, y):
    """Ground height (Morrowind units) at a world point on the LAND grid; None without LAND."""
    cx, cy = x // CELL, y // CELL
    ix, iy = (x - cx * CELL) // LAND_SPACING, (y - cy * CELL) // LAND_SPACING
    grid = lands.get((cx, cy))
    if grid is not None:
        return float(grid[iy][ix])
    # The last sample row/column of a cell is the first of the next one: use the neighbour's.
    for dx, dy in ((1, 0), (0, 1), (1, 1)):
        if (ix == 0 or not dx) and (iy == 0 or not dy):
            g = lands.get((cx - dx, cy - dy))
            if g is not None:
                return float(g[64 if dy else iy][64 if dx else ix])
    return None


def heights(lands, x0, y0, nx, ny, step):
    """Rows (by y) of local heights: max(ground, water level), rounded to whole local units."""
    out = np.empty((ny, nx), dtype=np.int16)
    for j in range(ny):
        for i in range(nx):
            h = sample(lands, x0 + i * step, y0 + j * step)
            z = WATER_LEVEL if h is None else max(WATER_LEVEL, h * SCALE)
            out[j, i] = int(np.clip(np.rint(z), -32768, 32767))
    return out


def stamps(grid, x0l, y0l, stepl, boxes, min_side=STAMP_MIN_SIDE, min_height=STAMP_MIN_HEIGHT):
    """Object stamps: [(sample index, height)] ascending by index. Each drawn box (local mins, maxs)
    at least `min_side` wide both ways whose top stands `min_height` above the ground under its
    centre raises every sample inside its footprint (at least the one nearest its centre) to its
    top. x0l, y0l, stepl: the grid in frame-local units."""
    ny, nx = grid.shape
    out = {}
    for lo, hi in boxes:
        if hi[0] - lo[0] < min_side or hi[1] - lo[1] < min_side:
            continue
        cx, cy = (lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0
        ci, cj = int(round((cx - x0l) / stepl)), int(round((cy - y0l) / stepl))
        if not (0 <= ci < nx and 0 <= cj < ny):
            continue
        top = int(min(32767, np.ceil(hi[2])))
        if top - int(grid[cj, ci]) < min_height:
            continue
        i0, i1 = int(np.ceil((lo[0] - x0l) / stepl)), int(np.floor((hi[0] - x0l) / stepl))
        j0, j1 = int(np.ceil((lo[1] - y0l) / stepl)), int(np.floor((hi[1] - y0l) / stepl))
        cells = [(i, j) for j in range(max(j0, 0), min(j1, ny - 1) + 1) for i in range(max(i0, 0), min(i1, nx - 1) + 1)]
        for i, j in cells or [(ci, cj)]:
            if top > grid[j, i] and top > out.get(j * nx + i, -32768):
                out[j * nx + i] = top
    if len(out) > MAX_STAMPS:
        raise ValueError('More than %d far terrain stamps' % MAX_STAMPS)
    return sorted(out.items())


def encode(cell, x0, y0, step, grid, block=DEFAULT_BLOCK, stamp_list=()):
    """The sidecar's bytes (version 2)."""
    if not 1 <= block <= 16:
        raise ValueError('The far block must be 1..16 quads')
    ny, nx = grid.shape
    if not (2 <= nx <= 1025 and 2 <= ny <= 1025):
        raise ValueError('The far grid must be 2..1025 samples each way')
    stamp_list = list(stamp_list)
    if len(stamp_list) > MAX_STAMPS:
        raise ValueError('More than %d far terrain stamps' % MAX_STAMPS)
    body = grid.astype('>i2').tobytes()
    if stamp_list:
        body += np.array([k for k, _ in stamp_list], dtype='>u4').tobytes()
        body += np.array([h for _, h in stamp_list], dtype='>i2').tobytes()
        body += bytes((-len(body)) % 4)
    return HEADER.pack(MAGIC, VERSION, HEADER.size, int(cell[0]), int(cell[1]), float(x0), float(y0), float(step),
                       SCALE, nx, ny, block, len(stamp_list), zlib.crc32(body) & 0xFFFFFFFF) + body


def decode(data):
    """(header dict, int16 grid, stamps) of a sidecar (version 1 or 2); ValueError when it is not one."""
    if len(data) < HEADER.size:
        raise ValueError('Far terrain file too short')
    (magic, version, hbytes, cx, cy, x0, y0, step, scale, nx, ny, block, count, crc) = HEADER.unpack_from(data)
    if magic != MAGIC or version not in (1, 2) or hbytes != HEADER.size or (version == 1 and count):
        raise ValueError('Not a far terrain file of version 1 or 2')
    grid_bytes = 2 * nx * ny
    stamp_bytes = 6 * count + (-(grid_bytes + 6 * count) % 4 if count else 0)
    if len(data) != HEADER.size + grid_bytes + stamp_bytes:
        raise ValueError('Far terrain file size does not match its grid')
    body = data[HEADER.size:]
    if zlib.crc32(body) & 0xFFFFFFFF != crc:
        raise ValueError('Far terrain CRC mismatch')
    grid = np.frombuffer(body[:grid_bytes], dtype='>i2').reshape(ny, nx).astype(np.int16)
    idx = np.frombuffer(body[grid_bytes:grid_bytes + 4 * count], dtype='>u4')
    hts = np.frombuffer(body[grid_bytes + 4 * count:grid_bytes + 6 * count], dtype='>i2')
    if count and (int(idx.max()) >= nx * ny or (np.diff(idx.astype(np.int64)) <= 0).any()):
        raise ValueError('Far terrain stamps out of range or out of order')
    return {'cell': (cx, cy), 'origin': (x0, y0), 'step': step, 'scale': scale, 'size': (nx, ny),
            'block': block, 'version': version, 'stamps': count}, grid, list(zip(idx.tolist(), hts.tolist()))


def layer(lands, frame, margin=DEFAULT_MARGIN, step=DEFAULT_STEP, block=DEFAULT_BLOCK, boxes=()):
    """One frame's far layer: (bytes, record). frame: {'cell', 'centre', 'low', 'span'} (chim.build);
    boxes: drawn boxes (local mins, maxs) of the frame's placements, stamped as objects."""
    x0, y0, nx, ny = area(frame['centre'], frame['low'], frame['span'], margin, step)
    grid = heights(lands, x0, y0, nx, ny, step)
    x0l, y0l = (x0 - frame['centre'][0]) * SCALE, (y0 - frame['centre'][1]) * SCALE
    stamp_list = stamps(grid, x0l, y0l, step * SCALE, boxes)
    data = encode(frame['cell'], x0, y0, step, grid, block, stamp_list)
    missing = sum(1 for j in range(ny) for i in range(nx) if sample(lands, x0 + i * step, y0 + j * step) is None)
    record = {'cell': list(frame['cell']), 'origin': [x0, y0], 'step': step, 'margin_cells': margin,
              'size': [nx, ny], 'block': block, 'bytes': len(data), 'zmin': int(grid.min()),
              'zmax': int(grid.max()), 'samples_without_land': missing, 'stamps': len(stamp_list),
              'boxes_offered': len(boxes)}
    return data, record


def cells_needed(frames, margin=DEFAULT_MARGIN, step=DEFAULT_STEP):
    """Every cell whose LAND a set of frames' far layers sample (and the cells left/below them)."""
    need = set()
    for frame in frames:
        x0, y0, nx, ny = area(frame['centre'], frame['low'], frame['span'], margin, step)
        for cx in range(x0 // CELL - 1, (x0 + (nx - 1) * step) // CELL + 1):
            for cy in range(y0 // CELL - 1, (y0 + (ny - 1) * step) // CELL + 1):
                need.add((cx, cy))
    return need


def placement_boxes(chim_root):
    """{frame cell: [(mins, maxs)]}: the drawn boxes of every placement a CHIM world owns (reach
    copies left out), read from its frame and sector files (any format minor of major 0)."""
    from chim import format as F
    out = {}
    for frame_path in sorted(Path(chim_root).rglob('frame.ccf')):
        raw = frame_path.read_bytes()
        v = F.FRAME_BLOCK.unpack_from(raw, F.HEADER.size)
        boxes = out.setdefault((v[0], v[1]), [])
        for sector in sorted(frame_path.parent.rglob('s*.ccs')):
            data = sector.read_bytes()
            magic, kind, major, _minor, _hb, count, diro, _datao, total = F.HEADER.unpack_from(data)
            if magic != F.MAGIC or kind != b'SECT' or major != 0 or total != len(data):
                raise ValueError('Not a CHIM sector file: %s' % sector)
            for k in range(count):
                rkind, _rid, o, n = F.RECORD_ENTRY.unpack_from(data, diro + k * F.RECORD_ENTRY.size)
                if rkind == b'CHNK':
                    boxes += [r['box'] for r in F.read_chunk(data[o:o + n])['owned']]
    return out


def file_name(cell):
    """Name of a frame's layer in the CHIM output folder (far/): far/<cx>_<cy>.far."""
    return '%d_%d%s' % (cell[0], cell[1], SUFFIX)


def write_layers(out, frames, data_dir, margin=DEFAULT_MARGIN, step=DEFAULT_STEP, block=DEFAULT_BLOCK,
                 boxes=None):
    """Write OUT/far/<cx>_<cy>.far for every frame from Morrowind.esm in data_dir; the receipt rows.
    boxes: {frame cell: [(mins, maxs)]} to stamp (default: read from OUT/chim when it exists)."""
    from mwad.paths import child_ci
    esm = child_ci(Path(data_dir), 'Morrowind.esm')
    lands = land_heights(esm, cells_needed(frames, margin, step))
    if boxes is None:
        boxes = placement_boxes(Path(out) / 'chim') if (Path(out) / 'chim').is_dir() else {}
    folder = Path(out) / 'far'
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for frame in frames:
        data, record = layer(lands, frame, margin, step, block, boxes.get(tuple(frame['cell']), ()))
        path = folder / file_name(frame['cell'])
        path.write_bytes(data)
        rows.append(dict(record, file='far/' + path.name, sha256=hashlib.sha256(data).hexdigest()))
    return rows


def sidecar_name(frame_map):
    """maps/<name>.bsp -> maps/<name>.far (the engine looks for it beside the frame map)."""
    p = Path(frame_map)
    return str(p.with_suffix(SUFFIX)).replace('\\', '/')
