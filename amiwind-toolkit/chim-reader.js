// SPDX-License-Identifier: GPL-3.0-only
// CHIM reader for the Toolkit's 3D Map Inspector: CHIM maps (.chim frame maps) and the CHIM world files
// (chim/world.cwi index, chim/frames/x<X>/y<Y>/frame.ccf frame files, sNN.ccs sector files; world formats 0.5
// to 0.12), read in the browser from local files. Nothing is uploaded.
// It is a port of the builder's own reader, tools/chim/format.py (records, brush images, terrain references)
// with the later formats' modules (tools/chim/placed.py: 56-byte placed records with three angles, 0.8;
// tools/chim/reach.py: reach references, 0.9; tools/chim/terc.py: compact terrain records, 0.10;
// tools/chim/thgt.py: generated terrain records, 0.11; placement light levels in the flags, 0.12), and of the
// CHIM heap gate's ring model, tools/chim/heap.py (zone block sizes, the active ring, the 64-unit position scan);
// tests/test_toolkit_chim.py checks it against them on synthetic worlds of every format built by tools/chim.
// Layout: docs/chim/WORLD_FORMAT.md. A .chim file is CHIM's own map format (the modified BSP format), read
// here by its own reader (readChimMap), never by the inspector's Quake BSP reader.
(function (root) {
  'use strict';
  // Every world format the builder writes (tools/chim: chim.FORMAT_VERSION, REFS_FORMAT_VERSION and the
  // FORMAT_VERSION of placed, reach, terc, thgt and placement_light); tests/test_toolkit_chim.py fails when the
  // builder can write one this list does not name (TOOLKIT-WORLD-FORMAT-STALE-64).
  const READ_VERSIONS = [[0, 5], [0, 7], [0, 8], [0, 9], [0, 10], [0, 11], [0, 12]];
  const KINDS = ['INDX', 'FRAM', 'SECT'];
  const RECORD_KINDS = ['CHNK', 'TERR', 'MODL', 'TEXR'];
  const LUMPS = ['entities', 'planes', 'textures', 'vertexes', 'visibility', 'nodes', 'texinfo', 'faces',
    'lighting', 'clipnodes', 'leafs', 'marksurfaces', 'edges', 'surfedges', 'models'];
  const RECORD = {1: 20, 3: 12, 5: 24, 6: 40, 7: 20, 9: 8, 10: 28, 11: 2, 12: 4, 13: 4, 14: 64};
  const BSP_HEADER = 4 + 15 * 8;
  const HEADER = 32, SETTINGS = 40, TOC = 32, FILE_ROW = 60, MODEL_ROW = 24, TEXTURE_ROW = 24;
  const FRAME_BLOCK = 32, CHUNK_ROW = 28, SECTOR_ROW = 12, RECORD_ROW = 16, CHUNK_HEAD = 24, PLACEMENT = 48;
  const PLACED = 56;                // the placed record of 0.8 on (tools/chim/placed.py PLACEMENT)
  const CHUNK_MAGICS = ['CHK0', 'CHK1', 'CHK2', 'CHK3'];
  const TERRAIN_REF = 32;
  // A brush image's lumps in its file order (tools/chim/format.py FILE_ORDER: the loader's order, the clipnodes last).
  const FILE_ORDER = [3, 12, 13, 2, 8, 1, 6, 7, 11, 4, 10, 14, 5, 0, 9];
  const FLAG_OVER_16_LEAVES = 1, FLAG_STORY_HIDDEN = 2;
  // The heap ring's target ABI sizes (bytes). A build records its own, probed with the Amiga compiler from the
  // engine headers, as target_struct_sizes_bytes in the image's world-map-heap.json: load that file to use them.
  // These defaults are that probe's values for the v0.0.35 engine and are labelled as defaults on screen.
  const DEFAULT_SIZES = Object.freeze({pointer: 4, short: 2, int: 4, hunk: 16, dvertex: 12, dedge: 4, dplane: 20,
    dnode: 24, dclipnode: 8, clipnode: 8, dleaf: 28, texinfo: 40, dface: 20, dmodel: 64, mvertex: 12, medge: 4,
    mplane: 20, mtexinfo: 44, msurface: 48, mnode: 40, mleaf: 48, texture: 60, entity: 184, scenery: 212,
    model: 400});
  const SIZE_KEYS = Object.keys(DEFAULT_SIZES);
  // The engine's CHIM memory defaults (engine chim_zone_kib, chim_pool_kib, two frame-world slots), used only
  // when no chim-heap.json is loaded; the report carries the build's own values.
  const DEFAULT_MEMORY = Object.freeze({zone_kib: 6864, pool_kib: 384, pool_slots: 2});

  function u8(data) {
    if (data instanceof Uint8Array) return data;
    if (data instanceof ArrayBuffer) return new Uint8Array(data);
    if (ArrayBuffer.isView(data)) return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
    throw Error('Expected bytes');
  }
  const dv = b => new DataView(b.buffer, b.byteOffset, b.byteLength);
  const tag = (b, at) => String.fromCharCode(b[at], b[at + 1], b[at + 2], b[at + 3]);
  const a4 = n => (n + 3) & ~3;
  const a16 = n => (n + 15) & ~15;
  const utf8 = typeof TextDecoder === 'function' ? new TextDecoder('utf-8') : null;
  function cstring(b, at, end) {
    let stop = at;
    while (stop < end && b[stop] !== 0) stop++;
    if (stop >= end) throw Error('Name without its terminating zero');
    return utf8 ? utf8.decode(b.subarray(at, stop)) : String.fromCharCode.apply(null, b.subarray(at, stop));
  }

  let crcTable = null;
  function crc32(data) {
    const b = u8(data);
    if (!crcTable) {
      crcTable = new Uint32Array(256);
      for (let n = 0; n < 256; n++) {
        let c = n;
        for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
        crcTable[n] = c >>> 0;
      }
    }
    let c = 0xFFFFFFFF;
    for (let i = 0; i < b.length; i++) c = crcTable[(c ^ b[i]) & 255] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }
  function nameHash(name) {
    const bytes = typeof TextEncoder === 'function' ? new TextEncoder().encode(name) : Array.from(name, ch => ch.charCodeAt(0));
    let h = 0x811C9DC5;
    for (const x of bytes) h = Math.imul(h ^ x, 0x01000193) >>> 0;
    return h >>> 0;
  }

  // ------------------------------------------------------------ CHIM world files (big-endian structures)

  // A model store's index and a room record (the CHIM rooms, tools/chim/interior.py) keep the index layout of 0.5
  // in every later format: their reader takes formats 0.5 to 0.13.
  const STORE_VERSIONS = [5, 6, 7, 8, 9, 10, 11, 12, 13].map(m => [0, m]);
  function readHeader(data, kind, versions) {
    const b = u8(data), d = dv(b), allowed = versions || READ_VERSIONS;
    if (b.length < HEADER) throw Error('CHIM file shorter than its header');
    const magic = tag(b, 0), k = tag(b, 4);
    if (magic !== 'CHIM' || !(KINDS.includes(k) || (kind === 'ROOM' && k === 'ROOM'))) throw Error('Not a CHIM file');
    if (kind && k !== kind) throw Error('Expected a CHIM ' + kind + ' file, found ' + k);
    const version = [d.getUint16(8), d.getUint16(10)];
    if (!allowed.some(v => v[0] === version[0] && v[1] === version[1]))
      throw Error('CHIM world format ' + version.join('.') + ', expected ' + allowed.map(v => v.join('.')).join(' or '));
    const size = d.getUint32(12), count = d.getUint32(16), directory = d.getUint32(20), dataAt = d.getUint32(24),
      total = d.getUint32(28);
    if (size !== HEADER || total !== b.length || !(size <= directory && directory <= dataAt && dataAt <= total))
      throw Error('CHIM header offsets do not match the file');
    return {kind: k, count, directory, data: dataAt, bytes: total, version};
  }

  function readIndex(data, versions) {
    const b = u8(data), d = dv(b), h = readHeader(b, 'INDX', versions);
    let at = HEADER;
    const settings = {draw_distance: d.getFloat32(at), hysteresis: d.getFloat32(at + 4),
      collision_margin: d.getFloat32(at + 8), prefetch_margin: d.getFloat32(at + 12), grain: d.getUint16(at + 16),
      terrain_light: b[at + 18], reserved: b[at + 19], placements: d.getUint32(at + 20), models: d.getUint32(at + 24),
      textures: d.getUint32(at + 28), frames: d.getUint32(at + 32), sector_chunks: d.getUint16(at + 36),
      reserved2: d.getUint16(at + 38)};
    at += SETTINGS;
    const [filesAt, nfiles, modelsAt, nmodels, orderAt, texturesAt, ntextures, namesAt] =
      [0, 1, 2, 3, 4, 5, 6, 7].map(k => d.getUint32(at + 4 * k));
    if (filesAt !== h.directory || nfiles !== h.count || namesAt !== h.data || modelsAt !== filesAt + nfiles * FILE_ROW
        || orderAt !== modelsAt + nmodels * MODEL_ROW || texturesAt !== orderAt + 4 * nmodels
        || namesAt !== texturesAt + ntextures * TEXTURE_ROW)
      throw Error('Index table of contents does not match its tables');
    const files = [];
    for (let i = 0; i < nfiles; i++) {
      const o = filesAt + i * FILE_ROW;
      let end = o + 28;
      while (end < o + 60 && b[end]) end++;
      files.push({kind: tag(b, o), sector: d.getUint16(o + 4), cell: [d.getInt16(o + 6), d.getInt16(o + 8)],
        bytes: d.getUint32(o + 12), crc: d.getUint32(o + 16), entries: d.getUint32(o + 20),
        path: String.fromCharCode.apply(null, b.subarray(o + 28, end))});
    }
    const models = [];
    for (let i = 0; i < nmodels; i++) {
      const o = modelsAt + i * MODEL_ROW, name = cstring(b, namesAt + d.getUint32(o + 16), b.length);
      if (nameHash(name) !== d.getUint32(o + 20)) throw Error('Model name hash mismatch: ' + name);
      models.push({name, file: d.getUint16(o), offset: d.getUint32(o + 4), bytes: d.getUint32(o + 8),
        render: d.getUint32(o + 12)});
    }
    const textures = [];
    for (let i = 0; i < ntextures; i++) {
      const o = texturesAt + i * TEXTURE_ROW, name = cstring(b, namesAt + d.getUint32(o + 12), b.length);
      if (nameHash(name) !== d.getUint32(o + 16)) throw Error('Texture name hash mismatch: ' + name);
      textures.push({name, file: d.getUint16(o), offset: d.getUint32(o + 4), bytes: d.getUint32(o + 8),
        width: d.getUint16(o + 20), height: d.getUint16(o + 22)});
    }
    return {version: h.version, settings, files, models, textures};
  }

  function hilbert(n, x, y) {
    let d = 0;
    for (let s = n >> 1; s > 0; s >>= 1) {
      const rx = x & s ? 1 : 0, ry = y & s ? 1 : 0;
      d += s * s * ((3 * rx) ^ ry);
      if (ry === 0) {
        if (rx === 1) { x = s - 1 - x; y = s - 1 - y; }
        const t = x; x = y; y = t;
      }
    }
    return d;
  }
  function spatialOrder(nx, ny) {
    let n = 1;
    while (n < Math.max(nx, ny)) n *= 2;
    const cells = [];
    for (let x = 0; x < nx; x++) for (let y = 0; y < ny; y++) cells.push([x, y]);
    return cells.map(c => [hilbert(n, c[0], c[1]), c]).sort((p, q) => p[0] - q[0]).map(p => p[1]);
  }

  function readFrame(data) {
    const b = u8(data), d = dv(b), h = readHeader(b, 'FRAM'), at = HEADER;
    const frame = {cell: [d.getInt16(at), d.getInt16(at + 2)], centre: [d.getFloat32(at + 4), d.getFloat32(at + 8)],
      low: [d.getFloat32(at + 12), d.getFloat32(at + 16)], grain: d.getUint16(at + 20), nx: d.getUint16(at + 22),
      ny: d.getUint16(at + 24), sector_chunks: d.getUint16(at + 26), owned_total: d.getUint32(at + 28)};
    const s = frame.sector_chunks;
    if (!s || frame.nx % s || frame.ny % s || h.count !== frame.nx * frame.ny) throw Error('Frame file sizes do not agree');
    const nsec = (frame.nx / s) * (frame.ny / s);
    if (h.data + nsec * SECTOR_ROW !== b.length) throw Error('Frame file sector table size mismatch');
    const chunks = [];
    for (let i = 0; i < h.count; i++) {
      const o = h.directory + i * CHUNK_ROW;
      chunks.push({index: i, cx: d.getUint16(o), cy: d.getUint16(o + 2), sector: d.getUint16(o + 4),
        offset: d.getUint32(o + 8), render: d.getUint32(o + 12), collision: d.getUint32(o + 16),
        owned_count: d.getUint16(o + 20), reach_count: d.getUint16(o + 22), zmin: d.getInt16(o + 24),
        zmax: d.getInt16(o + 26)});
    }
    const sectors = [];
    for (let k = 0; k < nsec; k++) {
      const o = h.data + k * SECTOR_ROW;
      sectors.push({sx: d.getUint16(o), sy: d.getUint16(o + 2), bytes: d.getUint32(o + 4), crc: d.getUint32(o + 8)});
    }
    return {version: h.version, frame, chunks, sectors};
  }

  function readSector(data) {
    const b = u8(data), d = dv(b), h = readHeader(b, 'SECT'), out = [];
    let at = h.data;
    for (let i = 0; i < h.count; i++) {
      const o = h.directory + i * RECORD_ROW, kind = tag(b, o), id = d.getUint32(o + 4), offset = d.getUint32(o + 8),
        bytes = d.getUint32(o + 12);
      if (!RECORD_KINDS.includes(kind)) throw Error('Sector record ' + i + ' has an unknown kind');
      if (offset !== at || offset + bytes > b.length) throw Error('Sector record ' + i + ' is not where the previous one ended');
      out.push({kind, id, offset, bytes, data: b.subarray(offset, offset + bytes)});
      at = a4(offset + bytes);
    }
    if (at !== b.length) throw Error('Sector file has bytes after its last record');
    return out;
  }

  // A placement record: the 48 bytes of 0.4 to 0.7, or the 56-byte placed record of 0.8 on (tools/chim/placed.py:
  // the 48 bytes, then the pitch and the roll), whose `angles` are Quake's entity angles (pitch, yaw, roll). From 0.12
  // the high byte of the flags is the placement's light level (tools/chim/placement_light.py).
  function readPlacement(b, at, size) {
    const d = dv(b);
    const r = {pid: d.getUint32(at), ref: d.getUint32(at + 4), model: d.getUint32(at + 8),
      origin: [d.getFloat32(at + 12), d.getFloat32(at + 16), d.getFloat32(at + 20)], yaw: d.getFloat32(at + 24),
      owner: d.getUint16(at + 28), cell_dx: d.getInt8(at + 30), cell_dy: d.getInt8(at + 31),
      box: [[0, 1, 2].map(k => d.getInt16(at + 32 + 2 * k)), [0, 1, 2].map(k => d.getInt16(at + 38 + 2 * k))],
      leaves: d.getUint16(at + 44), flags: d.getUint16(at + 46)};
    if (size === PLACED) {
      r.angles = [d.getFloat32(at + 48), r.yaw, d.getFloat32(at + 52)];
      r.light = r.flags >> 8;
    }
    return r;
  }

  // A chunk record of any world format: CHK0 (terrain image inline) and CHK1 (terrain reference block, 0.7), whose
  // head names the placement record size in its last u16 (0: 48 bytes; 56 from 0.8, tools/chim/placed.py), and CHK2
  // / CHK3 (0.9, tools/chim/reach.py: the reach copies replaced by 4-byte references to the owner chunk's records,
  // `reach_refs`, resolved per frame by resolveReach).
  function readChunk(data) {
    const b = u8(data), d = dv(b), magic = tag(b, 0);
    if (!CHUNK_MAGICS.includes(magic)) throw Error('Not a chunk record');
    const nOwned = d.getUint16(4), nReach = d.getUint16(6), imageAt = d.getUint32(8), imageRender = d.getUint32(12),
      pvsBytes = d.getUint16(16), leaves = d.getUint16(18), pvlBytes = d.getUint16(20), named = d.getUint16(22);
    if (named !== 0 && named !== PLACED) throw Error('Chunk record names a placement record of ' + named + ' bytes');
    const size = named || PLACEMENT, refs = magic === 'CHK2' || magic === 'CHK3';
    if (refs && size !== PLACED) throw Error('A 0.9 chunk record names a placement record of ' + named + ' bytes');
    const owned = [];
    for (let k = 0; k < nOwned; k++) owned.push(readPlacement(b, CHUNK_HEAD + k * size, size));
    let at = CHUNK_HEAD + nOwned * size, reach = [], reachRefs = null;
    if (refs) {
      reachRefs = [];
      for (let k = 0; k < nReach; k++) reachRefs.push([d.getUint16(at + 4 * k), d.getUint16(at + 4 * k + 2)]);
      at += 4 * nReach;
    } else {
      for (let k = 0; k < nReach; k++) reach.push(readPlacement(b, at + k * size, size));
      at += nReach * size;
    }
    const pvsAt = at;
    if (imageAt < pvsAt + pvsBytes + pvlBytes || imageAt + imageRender > b.length) throw Error('Chunk record parts overlap or overrun');
    const out = {owned, reach, pvs: b.subarray(pvsAt, pvsAt + pvsBytes),
      pvl: b.subarray(pvsAt + pvsBytes, pvsAt + pvsBytes + pvlBytes), leaves, image: b.subarray(imageAt),
      image_render: imageRender, render: imageAt + imageRender, record_size: size};
    if (reachRefs) out.reach_refs = reachRefs;
    if (magic === 'CHK1' || magic === 'CHK3') {
      const r = imageAt;
      if (r + TERRAIN_REF > b.length) throw Error('Terrain reference block outside the chunk record');
      out.ref = {id: d.getUint32(r), file: d.getUint16(r + 4), offset: d.getUint32(r + 8), bytes: d.getUint32(r + 12),
        render: d.getUint32(r + 16), shift: [d.getFloat32(r + 20), d.getFloat32(r + 24), d.getFloat32(r + 28)]};
    }
    return out;
  }
  // Format 0.9: every chunk's reach references replaced by the owner records they name (tools/chim/reach.py
  // resolve_frame), so the frame holds the records a 0.8 frame stores as copies. chunks: one frame's chunks with
  // `index` and `owned`. Returns the problems found (a reference that names no owned record).
  function resolveReach(chunks) {
    const byIndex = new Map(chunks.map(c => [c.index, c])), problems = [];
    for (const c of chunks) {
      if (!c.reach_refs) continue;
      const out = [];
      for (const [owner, k] of c.reach_refs) {
        const o = byIndex.get(owner);
        if (!o || owner === c.index || k >= o.owned.length || o.owned[k].owner !== owner) {
          problems.push('chunk ' + c.index + ': reach reference (' + owner + ', ' + k + ') names no owned record');
          continue;
        }
        out.push(o.owned[k]);
      }
      c.reach = out;
    }
    return problems;
  }

  // ------------------------------------------------------------ brush images (little-endian BSP29 lump sets)

  function readBrushImage(data) {
    const b = u8(data), d = dv(b);
    if (b.length < BSP_HEADER || d.getInt32(0, true) !== 29) throw Error('Brush image is not BSP29');
    const lumps = [];
    for (let k = 0; k < 15; k++) {
      const o = d.getInt32(4 + 8 * k, true), n = d.getInt32(8 + 8 * k, true);
      if (o < BSP_HEADER || n < 0 || o + n > b.length) throw Error('Brush image lump ' + LUMPS[k] + ' outside the image');
      if (RECORD[k] && n % RECORD[k]) throw Error('Brush image lump ' + LUMPS[k] + ' is not a whole number of records');
      lumps.push(b.subarray(o, o + n));
    }
    return lumps;
  }
  function readTextureRefs(lump) {
    const b = u8(lump), d = dv(b);
    if (b.length < 4) throw Error('Texture reference lump too short');
    const n = d.getInt32(0, true);
    if (n < 0 || b.length !== 4 + 4 * n) throw Error('Texture reference lump size mismatch');
    const out = [];
    for (let i = 0; i < n; i++) out.push(d.getInt32(4 + 4 * i, true));
    return out;
  }
  // The 15 lumps of any brush image the world stores: a BSP29 image, a compact terrain record (TRC1, format 0.10)
  // or a generated one (THG1, 0.11), the latter two expanded as the engine expands them (decodeCompact,
  // generateTerrain). An array of lumps is returned as it is.
  function brushLumps(data) {
    if (Array.isArray(data)) return data;
    const b = u8(data), kind = b.length >= 4 ? tag(b, 0) : '';
    if (kind === 'THG1') return generateTerrain(b);
    if (kind === 'TRC1') return decodeCompact(b);
    return readBrushImage(b);
  }
  // Model to world for a placement (r_bsp.c R_BuildBmodelRotation, tools/chim/placed.py model_matrix): the yaw alone
  // as before; with a pitch or a roll (the placed records of 0.8 on), the whole rotation of Quake's entity angles.
  function placeTransform(place) {
    const origin = (place && place.origin) || [0, 0, 0], angles = place && place.angles;
    const rad = v => (v || 0) * Math.PI / 180;
    if (!angles || (!angles[0] && !angles[2])) {
      const yaw = rad(angles ? angles[1] : place && place.yaw), cy = Math.cos(yaw), sy = Math.sin(yaw);
      return (x, y, z) => [origin[0] + x * cy - y * sy, origin[1] + x * sy + y * cy, origin[2] + z];
    }
    const sp = Math.sin(rad(angles[0])), cp = Math.cos(rad(angles[0])), sy = Math.sin(rad(angles[1])), cy = Math.cos(rad(angles[1]));
    const sr = Math.sin(rad(angles[2])), cr = Math.cos(rad(angles[2]));
    const mul = (A, B) => A.map(row => [0, 1, 2].map(j => row[0] * B[0][j] + row[1] * B[1][j] + row[2] * B[2][j]));
    // world to model, rows: roll @ (pitch @ yaw); model to world is its transpose
    const E = mul([[1, 0, 0], [0, cr, sr], [0, -sr, cr]], mul([[cp, 0, -sp], [0, 1, 0], [sp, 0, cp]], [[cy, sy, 0], [-sy, cy, 0], [0, 0, 1]]));
    return (x, y, z) => [origin[0] + E[0][0] * x + E[1][0] * y + E[2][0] * z, origin[1] + E[0][1] * x + E[1][1] * y + E[2][1] * z,
      origin[2] + E[0][2] * x + E[1][2] * y + E[2][2] * z];
  }
  // The faces of a brush image (bytes, or its lumps) as polygons, moved by shift (a referenced terrain record) or
  // turned by the placement's angles (its yaw before 0.8) and moved to origin (a placement):
  // {vertices, polygons: [{vertices, texinfo, texture (global id), uv, ...}]}.
  function brushGeometry(data, place) {
    const lumps = brushLumps(data), L = lumps.map(dv), refs = lumps[2].length ? readTextureRefs(lumps[2]) : [];
    const nv = lumps[3].length / 12, ne = lumps[12].length / 4, nse = lumps[13].length / 4, nf = lumps[7].length / 20;
    const ntex = lumps[6].length / 40, npl = lumps[1].length / 20;
    let first = 0, count = nf;
    if (lumps[14].length >= 64) { first = L[14].getInt32(56, true); count = L[14].getInt32(60, true); }
    if (first < 0 || count < 0 || first + count > nf) throw Error('Brush image model face range outside its faces');
    const shift = (place && place.shift) || [0, 0, 0], turn = placeTransform(place);
    const used = new Map(), vertices = [], polygons = [];
    const vertex = j => {
      if (j < 0 || j >= nv) throw Error('Invalid vertex index');
      if (!used.has(j)) {
        const x = L[3].getFloat32(12 * j, true) + shift[0], y = L[3].getFloat32(12 * j + 4, true) + shift[1],
          z = L[3].getFloat32(12 * j + 8, true) + shift[2];
        used.set(j, vertices.length);
        vertices.push(turn(x, y, z));
      }
      return used.get(j);
    };
    for (let f = first; f < first + count; f++) {
      const o = 20 * f, plane = L[7].getUint16(o, true), side = L[7].getInt16(o + 2, true),
        firstEdge = L[7].getInt32(o + 4, true), numEdges = L[7].getInt16(o + 8, true), texinfo = L[7].getInt16(o + 10, true),
        lightofs = L[7].getInt32(o + 16, true);
      if (firstEdge < 0 || numEdges < 3 || firstEdge + numEdges > nse) throw Error('Invalid face edge range');
      const poly = [], uv = [];
      const t = texinfo >= 0 && texinfo < ntex ? Array.from({length: 8}, (_, k) => L[6].getFloat32(40 * texinfo + 4 * k, true)) : null;
      const local = t ? L[6].getInt32(40 * texinfo + 32, true) : -1;
      for (let k = 0; k < numEdges; k++) {
        const s = L[13].getInt32(4 * (firstEdge + k), true), e = Math.abs(s);
        if (e >= ne) throw Error('Invalid edge index');
        const j = L[12].getUint16(4 * e + (s >= 0 ? 0 : 2), true);
        poly.push(vertex(j));
        if (t) {
          const x = L[3].getFloat32(12 * j, true) + shift[0], y = L[3].getFloat32(12 * j + 4, true) + shift[1],
            z = L[3].getFloat32(12 * j + 8, true) + shift[2];
          uv.push([x * t[0] + y * t[1] + z * t[2] + t[3], x * t[4] + y * t[5] + z * t[6] + t[7]]);
        }
      }
      const polygon = {vertices: poly, texinfo, lightmapped: lightofs >= 0, local_texture: local,
        texture: local >= 0 && local < refs.length ? refs[local] : -1};
      if (t) polygon.uv = uv;
      if (plane < npl) polygon.planeNormalZ = L[1].getFloat32(20 * plane + 8, true) * (side ? -1 : 1);
      polygons.push(polygon);
    }
    return {vertices, polygons, faceCount: count, textureRefs: refs};
  }
  // A Quake miptex (16-byte name, size, four mip offsets): name, size and the first mip level's palette indices.
  function readMiptex(data) {
    const b = u8(data), d = dv(b);
    if (b.length < 40) throw Error('Texture record shorter than a miptex header');
    let end = 0;
    while (end < 16 && b[end]) end++;
    const name = String.fromCharCode.apply(null, b.subarray(0, end)), width = d.getUint32(16, true),
      height = d.getUint32(20, true), mip0 = d.getUint32(24, true);
    if (width < 1 || height < 1 || width > 4096 || height > 4096 || mip0 < 40 || mip0 + width * height > b.length)
      throw Error('Invalid texture record ' + name);
    return {name, width, height, pixels: Array.from(b.subarray(mip0, mip0 + width * height))};
  }

  // ------------------------------------------------------------ compact and generated terrain records (0.10, 0.11)

  // The bytes and render bytes of the BSP29 image of 15 lumps (tools/chim/format.py brush_image's layout).
  function imageLayout(lumps) {
    let body = 0, render = null;
    for (const k of FILE_ORDER) {
      if (k === 9 && render === null) render = BSP_HEADER + body;
      body = a4(body) + lumps[k].length;
    }
    return {bytes: a4(BSP_HEADER + body), render};
  }
  // Compact lump payloads (tools/chim/terc.py _unpack_lump): RAW, PLANES (axial normals as one-byte codes), UNIFORM
  // (one light value), CLIPNODES and NODES with 16-bit plane numbers. The payloads keep the little-endian bytes.
  function unpackLump(method, p) {
    const d = dv(p);
    if (method === 0) return p;
    if (method === 1) {
      const count = d.getUint32(0, true), codes = p.subarray(4, 4 + count), out = new Uint8Array(20 * count), o = dv(out);
      let at = 4 + a4(count);
      for (let k = 0; k < count; k++) {
        let c = codes[k];
        if (!c) { out.set(p.subarray(at, at + 20), 20 * k); at += 20; continue; }
        c -= 1;
        const kind = Math.floor(c / 24), axis = Math.floor((c % 24) / 8), negative = Math.floor((c % 8) / 4), signs = c % 4;
        const others = [0, 1, 2].filter(i => i !== axis);
        o.setFloat32(20 * k + 4 * axis, negative ? -1 : 1, true);
        o.setFloat32(20 * k + 4 * others[0], signs & 1 ? -0 : 0, true);
        o.setFloat32(20 * k + 4 * others[1], signs & 2 ? -0 : 0, true);
        out.set(p.subarray(at, at + 4), 20 * k + 12);
        o.setInt32(20 * k + 16, kind, true);
        at += 4;
      }
      return out;
    }
    if (method === 2) return new Uint8Array(d.getUint32(0, true)).fill(p[4]);
    if (method === 3) {
      const n = d.getUint32(0, true), out = new Uint8Array(8 * n), o = dv(out);
      for (let k = 0; k < n; k++) {
        o.setInt32(8 * k, d.getUint16(4 + 6 * k, true), true);
        o.setInt16(8 * k + 4, d.getInt16(4 + 6 * k + 2, true), true);
        o.setInt16(8 * k + 6, d.getInt16(4 + 6 * k + 4, true), true);
      }
      return out;
    }
    if (method === 4) {
      const n = d.getUint32(0, true), out = new Uint8Array(24 * n), o = dv(out);
      for (let k = 0; k < n; k++) {
        o.setInt32(24 * k, d.getUint16(4 + 22 * k, true), true);
        out.set(p.subarray(4 + 22 * k + 2, 4 + 22 * k + 22), 24 * k + 4);
      }
      return out;
    }
    throw Error('Unknown compact terrain method ' + method);
  }
  // A compact terrain record (TRC1, tools/chim/terc.py decode): its 15 lumps, checked against the image size in its head.
  function decodeCompact(data) {
    const b = u8(data), d = dv(b);
    if (tag(b, 0) !== 'TRC1') throw Error('Not a compact terrain record');
    const imageBytes = d.getUint32(4), render = d.getUint32(8), count = d.getUint16(12);
    if (count !== 15) throw Error('Compact terrain record with ' + count + ' lumps');
    const lumps = new Array(15);
    let at = 16 + 15 * 8;
    FILE_ORDER.forEach((k, slot) => {
      const method = b[16 + 8 * slot], n = d.getUint32(16 + 8 * slot + 4);
      at = a4(at);
      if (at + n > b.length) throw Error('Compact terrain lump outside the record');
      lumps[k] = unpackLump(method, b.subarray(at, at + n));
      at += n;
    });
    const got = imageLayout(lumps);
    if (got.bytes !== imageBytes || got.render !== render)
      throw Error('Compact terrain record expands to ' + got.bytes + ' bytes, its head says ' + imageBytes);
    return lumps;
  }
  // Python's round() of a float: half to even (the generator's vertex keys, tools/chim/thgt.py).
  function pyRound(x) {
    const r = Math.round(x);
    return Math.abs(x % 1) === 0.5 && r % 2 !== 0 ? r - 1 : r;
  }
  // The facts of a generated terrain record (THG1, tools/chim/thgt.py decode_facts): head, heights, tile facts
  // (version 1) or tiles and triangles (version 2), node planes, texture references, planes and the standing hull.
  function terrainFacts(data) {
    const b = u8(data), d = dv(b);
    if (tag(b, 0) !== 'THG1') throw Error('Not a generated terrain record');
    const version = d.getUint16(12);
    if (version !== 1 && version !== 2) throw Error('Generated terrain record version ' + version);
    const nx = d.getUint16(14), ny = d.getUint16(16), nn = d.getUint16(18), f = k => d.getFloat32(20 + 4 * k);
    const box = [f(0), f(1), f(2), f(3)], floor = f(4), ceiling = f(5), water = f(6), step = f(7);
    const samples = d.getUint16(52), light = b[54], ws = b[55], nPl = d.getUint32(56), nClip = d.getUint32(60),
      nRefs = d.getUint32(64), croot = d.getUint32(68);
    let at = 72;
    const gx = version === 1 ? nx + 1 : 4 * nx + 1, gy = version === 1 ? ny + 1 : 4 * ny + 1, heights = [];
    for (let j = 0; j < gy; j++) { const row = []; for (let i = 0; i < gx; i++) row.push(d.getFloat32(at + 4 * (j * gx + i))); heights.push(row); }
    at += 4 * gx * gy;
    const facts = [];
    if (version === 1) {
      for (let j = 0; j < ny; j++) { const row = []; for (let i = 0; i < nx; i++) row.push([b[at + 2 * (j * nx + i)], b[at + 2 * (j * nx + i) + 1]]); facts.push(row); }
      at += a4(2 * nx * ny);
    } else {
      const tableAt = at;
      at += a4(2 * nx * ny);
      let k = 0, tri = at;
      for (let j = 0; j < ny; j++) {
        const row = [];
        for (let i = 0; i < nx; i++) {
          const slot = b[tableAt + 2 * k], n = b[tableAt + 2 * k + 1], tris = [];
          k++;
          for (let t = 0; t < n; t++) tris.push([b[tri + 3 * t], b[tri + 3 * t + 1], b[tri + 3 * t + 2]]);
          tri += 3 * n;
          row.push([slot, tris]);
        }
        facts.push(row);
      }
      at += a4(tri - at);
    }
    const nodePlanes = [];
    for (let k = 0; k < nn; k++) nodePlanes.push(d.getUint16(at + 2 * k));
    at += a4(2 * nn);
    const refs = b.subarray(at, at + nRefs);
    at += nRefs;
    const planes = unpackLump(b[at], b.subarray(at + 4, at + nPl));
    at += nPl;
    const clipnodes = unpackLump(b[at], b.subarray(at + 4, at + nClip));
    const nTex = dv(refs).getInt32(0, true);
    return {version, box, step, floor, ceiling, water, tiles: [nx, ny], heights, tile_facts: facts, node_planes: nodePlanes,
      planes, texture_refs: refs.subarray(0, 4 + 4 * nTex), clipnodes, light, light_samples: samples, croot,
      water_slot: ws === 0xFF ? null : ws, image_bytes: d.getUint32(4), render_bytes: d.getUint32(8)};
  }
  // The engine's terrain generator (chim/chim_thgt.c), a port of tools/chim/thgt.py generate(): the 15 lumps of the
  // terrain image from its record's facts, by the builder's own rule (regular path: version 1; the converter's own
  // triangles: version 2). Every value is computed in IEEE double as the builder computes it, so the lumps are the
  // builder's byte for byte (tests/test_toolkit_chim.py compares them with tools/chim/thgt.py decode).
  const CONTENTS_EMPTY = -1, CONTENTS_WATER = -3, TEX_SPECIAL = 1, GUARD = 1 / 16;
  const PAIRS = [[[1, 0, 0], [0, -1, 0]], [[0, 1, 0], [0, 0, -1]], [[1, 0, 0], [0, 0, -1]]];
  const MAX_POLY = 16, MAX_CALL_VERTS = 32, MAX_PIECES = 16, MAX_TEXINFO = 64, MAX_ITEMS = 64, ARENA_POINTS = 6144;
  function generateTerrain(data) {
    const p = terrainFacts(data), lumps = generateLumps(p), got = imageLayout(lumps);
    if (got.bytes !== p.image_bytes) throw Error('Generated terrain record gives ' + got.bytes + ' bytes, its head says ' + p.image_bytes);
    return lumps;
  }
  function generateLumps(p) {
    const refuse = why => { throw Error('generated terrain: ' + why); };
    const [x0, y0, x1, y1] = p.box, step = p.step, ceiling = p.ceiling, water = p.water, [nx, ny] = p.tiles;
    const heights = p.heights, tiles = p.tile_facts, nodePlanes = p.node_planes;
    const verts = [], edges = [[0, 0]], surf = [], faces = [], texinfo = [], txIndex = new Map();
    const nodeRows = [], leafRows = [], marks = [];
    let leafCount = 1, arena = 0;
    const texinfoOf = (pair, slot, flags) => {
      const key = pair + ',' + slot + ',' + flags;
      if (!txIndex.has(key)) {
        if (txIndex.size >= MAX_TEXINFO) refuse('more texture mappings than the engine holds');
        txIndex.set(key, texinfo.length);
        texinfo.push([PAIRS[pair][0], PAIRS[pair][1], slot, flags]);
      }
      return txIndex.get(key);
    };
    const emit = (surfaces, plane) => {
      const first = faces.length, vmap = new Map(), emap = new Map();
      const vertex = pt => {
        const key = pyRound(pt[0] * 1e5) + ',' + pyRound(pt[1] * 1e5) + ',' + pyRound(pt[2] * 1e5);
        if (!vmap.has(key)) {
          if (vmap.size >= MAX_CALL_VERTS) refuse('more corners in one face call than the engine holds');
          vmap.set(key, verts.length);
          verts.push(pt);
        }
        return vmap.get(key);
      };
      for (const [pts, pair, slot, flags, side, light] of surfaces) {
        const tx = texinfoOf(pair, slot, flags);
        if (pts.length > MAX_POLY) refuse('a face of more corners than the engine holds');
        const vs = pts.slice().reverse().map(vertex), firstedge = surf.length;
        for (let k = 0; k < vs.length; k++) {
          const a = vs[k], c = vs[(k + 1) % vs.length];
          let ed;
          if (emap.has(a + ',' + c)) ed = emap.get(a + ',' + c);
          else if (emap.has(c + ',' + a)) ed = -emap.get(c + ',' + a);
          else {
            if (emap.size >= 2 * MAX_CALL_VERTS) refuse('more edges in one face call than the engine holds');
            ed = edges.length;
            emap.set(a + ',' + c, ed);
            edges.push([a, c]);
          }
          surf.push(ed);
        }
        faces.push([plane, side, firstedge, vs.length, tx, light ? [0, 255, 255, 255] : [255, 255, 255, 255], light ? 0 : -1]);
      }
      const out = [];
      for (let k = first; k < faces.length; k++) out.push(k);
      return out;
    };
    const addNode = bounds => { nodeRows.push([null, null, bounds, 0, 0]); return nodeRows.length - 1; };
    const addLeaf = (contents, bounds, fs) => {
      leafRows.push([contents, bounds, marks.length, fs.length]);
      marks.push(...fs);
      leafCount += 1;
      return -1 - (leafCount - 1);
    };
    const planeOf = k => { if (k >= nodePlanes.length) refuse('more nodes than the record names'); return nodePlanes[k]; };
    const crossing = (pt, q, d, e) => [0, 1, 2].map(k => pt[k] + (q[k] - pt[k]) * d / (d - e));
    const minZ = poly => Math.min(...poly.map(pt => pt[2]));
    const clipBelow = poly => {
      const out = [];
      for (let i = 0; i < poly.length; i++) {
        const pt = poly[i], q = poly[(i + 1) % poly.length], dp = pt[2] - water, dq = q[2] - water;
        if (dp <= 0) { if (out.length >= MAX_POLY) refuse('a water polygon of more corners than the engine holds'); out.push(pt); }
        if ((dp < 0 && 0 < dq) || (dq < 0 && 0 < dp)) {
          if (out.length >= MAX_POLY) refuse('a water polygon of more corners than the engine holds');
          out.push(crossing(pt, q, dp, dq));
        }
      }
      return out.length >= 3 ? out : null;
    };
    const splitSurface = (poly, pair) => {
      const axes = PAIRS[pair];
      // Python's sum() starts from 0, so a zero product of -0 sums to +0: the same here
      const uv = poly.map(pt => [0, 1].map(a => 0 + pt[0] * axes[a][0] + pt[1] * axes[a][1] + pt[2] * axes[a][2]));
      for (let a = 0; a < 2; a++) {
        const lo = Math.floor((Math.min(...uv.map(v => v[a])) - GUARD) / 16) * 16;
        const hi = Math.ceil((Math.max(...uv.map(v => v[a])) + GUARD) / 16) * 16;
        if (hi - lo <= 240) continue;
        const cut = lo + 224, dist = uv.map(v => v[a] - cut), front = [], back = [];
        for (let i = 0; i < poly.length; i++) {
          const j = (i + 1) % poly.length, d = dist[i], e = dist[j], pt = poly[i];
          if (front.length >= MAX_POLY - 1 || back.length >= MAX_POLY - 1) refuse('a texture split of more corners than the engine holds');
          if (d <= 1e-6) back.push(pt);
          if (d >= -1e-6) front.push(pt);
          if ((d > 1e-6 && e < -1e-6) || (d < -1e-6 && e > 1e-6)) { const q = crossing(pt, poly[j], d, e); front.push(q); back.push(q); }
        }
        if (back.length < 3 || front.length < 3) refuse('a texture split leaves a sliver');
        return splitSurface(back, pair).concat(splitSurface(front, pair));
      }
      return [poly];
    };
    const waterFaces = (flat, zlo, xy, fs, me) => {
      const wn = addNode([xy[0], xy[1], zlo - 1, xy[2], xy[3], ceiling]), wpi = planeOf(wn);
      const wf = emit([[flat, 0, p.water_slot, TEX_SPECIAL, 0, false], [flat.slice().reverse(), 0, p.water_slot, TEX_SPECIAL, 1, false]], wpi);
      nodeRows[wn][3] = wf[0]; nodeRows[wn][4] = wf.length;
      const tile = fs.concat(wf);
      nodeRows[wn][0] = addLeaf(CONTENTS_EMPTY, [xy[0], xy[1], water, xy[2], xy[3], ceiling], tile);
      nodeRows[wn][1] = addLeaf(CONTENTS_WATER, [xy[0], xy[1], zlo, xy[2], xy[3], water], tile);
      nodeRows[me][0] = wn;
    };
    const groundNode = (poly, xy, pair, slot) => {
      const zlo = minZ(poly), me = addNode([xy[0], xy[1], Math.min(zlo, water) - 1, xy[2], xy[3], ceiling]), pi = planeOf(me);
      const parts = splitSurface(poly, pair);
      if (parts.length > MAX_PIECES) refuse('more texture split pieces than the engine holds');
      const fs = emit(parts.map(part => [part, pair, slot, 0, 0, true]), pi);
      nodeRows[me][3] = fs[0]; nodeRows[me][4] = fs.length;
      return {zlo, me, fs};
    };
    const surfaceSubtree = (poly, xy, pair, slot, under) => {
      const {zlo, me, fs} = groundNode(poly, xy, pair, slot);
      if (under) {
        if (!(zlo < water)) refuse('a tile marked under water lies over it');
        const low = clipBelow(poly);
        if (low === null) refuse('a tile marked under water has no water face');
        waterFaces(low.map(pt => [pt[0], pt[1], water]), zlo, xy, fs, me);
      } else nodeRows[me][0] = addLeaf(CONTENTS_EMPTY, [xy[0], xy[1], zlo, xy[2], xy[3], ceiling], fs);
      nodeRows[me][1] = -1;
      return me;
    };
    // record version 2: the converter's own triangles (chim.terrain.chunk_terrain's irregular path)
    const areaXY = poly => { let s = 0; for (let k = 0; k < poly.length; k++) { const a = poly[k], b = poly[(k + 1) % poly.length]; s += a[0] * b[1] - a[1] * b[0]; } return 0.5 * s; };
    const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
    const length = n => Math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]);
    const groundPlane = poly => {
      const p0 = poly[0];
      let best = null, bl = 0;
      for (let i = 1; i < poly.length - 1; i++) {
        const a = [poly[i][0] - p0[0], poly[i][1] - p0[1], poly[i][2] - p0[2]], b = [poly[i + 1][0] - p0[0], poly[i + 1][1] - p0[1], poly[i + 1][2] - p0[2]];
        const n = cross(a, b), ln = length(n);
        if (best === null || ln > bl) { best = n; bl = ln; }
      }
      let n = [best[0] / bl, best[1] / bl, best[2] / bl];
      if (n[2] < 0) n = [-n[0], -n[1], -n[2]];
      return [n, n[0] * p0[0] + n[1] * p0[1] + n[2] * p0[2]];
    };
    const splitKeep = (poly, n, d, keep) => {
      const out = [];
      for (let i = 0; i < poly.length; i++) {
        const pt = poly[i], q = poly[(i + 1) % poly.length];
        const dp = keep * (n[0] * pt[0] + n[1] * pt[1] - d), dq = keep * (n[0] * q[0] + n[1] * q[1] - d);
        if (dp >= -1e-9) { if (out.length >= MAX_POLY) refuse('a split piece of more corners than the engine holds'); out.push(pt); }
        if ((dp > 1e-9 && dq < -1e-9) || (dp < -1e-9 && dq > 1e-9)) {
          const t = dp / (dp - dq);
          if (out.length >= MAX_POLY) refuse('a split piece of more corners than the engine holds');
          out.push([pt[0] + (q[0] - pt[0]) * t, pt[1] + (q[1] - pt[1]) * t, pt[2] + (q[2] - pt[2]) * t]);
        }
      }
      return out;
    };
    const cleanXY = (pts, eps = 1e-7) => {
      const out = [];
      for (const pt of pts) if (!out.length || Math.abs(pt[0] - out[out.length - 1][0]) > eps || Math.abs(pt[1] - out[out.length - 1][1]) > eps) out.push(pt);
      if (out.length > 1 && Math.abs(out[0][0] - out[out.length - 1][0]) <= eps && Math.abs(out[0][1] - out[out.length - 1][1]) <= eps) out.pop();
      let changed = true;
      while (changed && out.length > 3) {
        changed = false;
        for (let i = 0; i < out.length; i++) {
          const a = out[(i - 1 + out.length) % out.length], b = out[i], c = out[(i + 1) % out.length];
          if (Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) <= eps) { out.splice(i, 1); changed = true; break; }
        }
      }
      return out;
    };
    const splitLine = (region, items) => {
      let best = null, bestKey = null;
      for (const poly of items) for (let i = 0; i < poly.length; i++) {
        const a = poly[i], b = poly[(i + 1) % poly.length], ex = b[0] - a[0], ey = b[1] - a[1], ln = Math.sqrt(ex * ex + ey * ey);
        if (ln < 1e-6) continue;
        let n = [ey / ln, -ex / ln];
        if (n[0] < -1e-12 || (Math.abs(n[0]) <= 1e-12 && n[1] < 0)) n = [-n[0], -n[1]];
        const d = n[0] * a[0] + n[1] * a[1], side = region.map(([x, y]) => n[0] * x + n[1] * y - d);
        if (Math.max(...side) <= 1e-6 || Math.min(...side) >= -1e-6) continue;
        let cuts = 0, front = 0, back = 0;
        for (const q of items) {
          const dvs = q.map(pt => n[0] * pt[0] + n[1] * pt[1] - d), hi = Math.max(...dvs), lo = Math.min(...dvs);
          if (hi > 1e-6 && lo < -1e-6) cuts++; else if (hi > 1e-6) front++; else back++;
        }
        const score = [cuts, Math.abs(front - back)];
        if (bestKey === null || score[0] < bestKey[0] || (score[0] === bestKey[0] && score[1] < bestKey[1])) { best = [n, d]; bestKey = score; }
      }
      if (best === null) refuse('an irregular region no edge splits');
      return best;
    };
    const dedupe = (poly, eps = 1e-6) => {
      const out = [], far = (u, v) => Math.max(Math.abs(u[0] - v[0]), Math.abs(u[1] - v[1]), Math.abs(u[2] - v[2])) > eps;
      for (const pt of poly) if (!out.length || far(pt, out[out.length - 1])) out.push(pt);
      if (out.length > 1 && !far(out[0], out[out.length - 1])) out.pop();
      return out.length >= 3 ? out : null;
    };
    const irregularSurface = (poly, xy, slot) => {
      const a = [poly[1][0] - poly[0][0], poly[1][1] - poly[0][1], poly[1][2] - poly[0][2]];
      const b = [poly[2][0] - poly[0][0], poly[2][1] - poly[0][1], poly[2][2] - poly[0][2]];
      let n = cross(a, b);
      const ln = length(n);
      n = [n[0] / ln, n[1] / ln, n[2] / ln];
      let best = -1, pair = null;
      [n[2], -n[2], n[0], -n[0], n[1], -n[1]].forEach((c, k) => { if (c > best) { best = c; pair = Math.floor(k / 2); } });
      if (pair === null) refuse('a ground polygon without texture axes');
      const {zlo, me, fs} = groundNode(poly, xy, pair, slot);
      let low = clipBelow(poly);
      if (low !== null) low = dedupe(low);
      const flat = low !== null && zlo < water ? low.map(pt => [pt[0], pt[1], water]) : null;
      if (flat !== null && Math.abs(areaXY(flat)) > 1e-9) {
        if (p.water_slot === null) refuse('water without its texture slot');
        waterFaces(flat, zlo, xy, fs, me);
      } else nodeRows[me][0] = addLeaf(CONTENTS_EMPTY, [xy[0], xy[1], zlo, xy[2], xy[3], ceiling], fs);
      nodeRows[me][1] = -1;
      return me;
    };
    const regionSubtree = (region, items, slot) => {
      const xs = region.map(r => r[0]), ys = region.map(r => r[1]);
      const xy = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
      const planes = items.map(groundPlane), [n0, d0] = planes[0];
      if (planes.every(([n, d]) => Math.max(Math.abs(n[0] - n0[0]), Math.abs(n[1] - n0[1]), Math.abs(n[2] - n0[2])) < 1e-6 && Math.abs(d - d0) < 1e-3)) {
        const exact = new Map(), key6 = v => pyRound(v * 1e6);
        for (const poly of items) for (const pt of poly) exact.set(key6(pt[0]) + ',' + key6(pt[1]), pt[2]);
        const face = region.map(([x, y]) => {
          const z = exact.get(key6(x) + ',' + key6(y));
          return [x, y, z !== undefined ? z : (d0 - n0[0] * x - n0[1] * y) / n0[2]];
        });
        return irregularSurface(face, xy, slot);
      }
      const [n, d] = splitLine(region, items);
      let zlo = Infinity;
      for (const poly of items) for (const pt of poly) zlo = Math.min(zlo, pt[2]);
      const me = addNode([xy[0], xy[1], Math.min(zlo, water) - 1, xy[2], xy[3], ceiling]), sides = [], base = arena;
      for (const keep of [1, -1]) {
        const part = cleanXY(splitKeep(region.map(([x, y]) => [x, y, 0]), n, d, keep)), kept = [];
        for (const poly of items) {
          const piece = splitKeep(poly, n, d, keep);
          if (piece.length >= 3 && Math.abs(areaXY(piece)) > 1e-6) {
            if (kept.length >= MAX_ITEMS || arena + piece.length > ARENA_POINTS) refuse('more split pieces than the engine holds');
            arena += piece.length;
            kept.push(piece);
          }
        }
        if (!kept.length || part.length < 3) refuse('an irregular split leaves an empty side');
        sides.push(regionSubtree(part.map(pt => [pt[0], pt[1]]), kept, slot));
        arena = base;
      }
      nodeRows[me][0] = sides[0]; nodeRows[me][1] = sides[1];
      return me;
    };
    const irregularTile = (i, j) => {
      const x = x0 + i * step, y = y0 + j * step, [slot, tris] = tiles[j][i], items = [];
      for (const tri of tris) {
        let poly = tri.map(v => [x + 32 * (v % 5), y + 32 * Math.floor(v / 5), heights[4 * j + Math.floor(v / 5)][4 * i + v % 5]]);
        if (areaXY(poly) < 0) poly = poly.reverse();
        items.push(poly);
      }
      if (!items.length || items.length > MAX_ITEMS || 3 * items.length > ARENA_POINTS) refuse('a tile without triangles, or more than the engine holds');
      arena = 3 * items.length;
      return regionSubtree([[x, y], [x + step, y], [x + step, y + step], [x, y + step]], items, slot);
    };
    const tileSubtree = (i, j) => {
      if (p.version === 2) return irregularTile(i, j);
      const x = x0 + i * step, y = y0 + j * step, [slot, facts] = tiles[j][i], h = (a, b) => heights[j + b][i + a];
      const c = [[x, y, h(0, 0)], [x + step, y, h(1, 0)], [x + step, y + step, h(1, 1)], [x, y + step, h(0, 1)]];
      const xy = [x, y, x + step, y + step], under = !!(facts & 2);
      if (facts & 1) return surfaceSubtree(c, xy, (facts >> 2) & 3, slot, under);
      const zlo = minZ(c), me = addNode([x, y, Math.min(zlo, water) - 1, x + step, y + step, ceiling]);
      nodeRows[me][0] = surfaceSubtree([c[0], c[1], c[2]], xy, (facts >> 2) & 3, slot, under);
      nodeRows[me][1] = surfaceSubtree([c[0], c[2], c[3]], xy, (facts >> 4) & 3, slot, under);
      return me;
    };
    const gridSubtree = (i0, j0, i1, j1) => {
      if (i1 - i0 === 1 && j1 - j0 === 1) return tileSubtree(i0, j0);
      let halves;
      if (i1 - i0 >= j1 - j0) { const mid = Math.floor((i0 + i1) / 2); halves = [[mid, j0, i1, j1], [i0, j0, mid, j1]]; }
      else { const mid = Math.floor((j0 + j1) / 2); halves = [[i0, mid, i1, j1], [i0, j0, i1, mid]]; }
      const me = addNode(null);
      nodeRows[me][0] = gridSubtree(...halves[0]);
      nodeRows[me][1] = gridSubtree(...halves[1]);
      return me;
    };
    if (p.version !== 2 && p.water_slot === null && tiles.some(row => row.some(t => t[1] & 2))) refuse('water without its texture slot');
    gridSubtree(0, 0, nx, ny);
    if (nodeRows.length !== nodePlanes.length) refuse('the record names ' + nodePlanes.length + ' node planes, the tree has ' + nodeRows.length + ' nodes');
    for (let k = nodeRows.length - 1; k >= 0; k--) {
      if (nodeRows[k][2] !== null) continue;
      const kids = [nodeRows[k][0], nodeRows[k][1]].filter(c => c >= 0).map(c => nodeRows[c][2]);
      nodeRows[k][2] = [0, 1, 2].map(i => Math.min(...kids.map(b => b[i]))).concat([3, 4, 5].map(i => Math.max(...kids.map(b => b[i]))));
    }
    const shortBox = bx => bx.slice(0, 3).map(Math.floor).concat(bx.slice(3).map(Math.ceil));
    const pack = (n, write) => { const out = new Uint8Array(n), o = dv(out); write(o); return out; };
    const lumps = new Array(15).fill(new Uint8Array(0));
    lumps[1] = p.planes;
    lumps[2] = p.texture_refs;
    lumps[3] = pack(12 * verts.length, o => verts.forEach((v, k) => { o.setFloat32(12 * k, v[0], true); o.setFloat32(12 * k + 4, v[1], true); o.setFloat32(12 * k + 8, v[2], true); }));
    lumps[5] = pack(24 * nodeRows.length, o => nodeRows.forEach((r, k) => {
      const at = 24 * k, bx = shortBox(r[2]);
      o.setInt32(at, nodePlanes[k], true); o.setInt16(at + 4, r[0], true); o.setInt16(at + 6, r[1], true);
      bx.forEach((v, i) => o.setInt16(at + 8 + 2 * i, v, true));
      o.setUint16(at + 20, r[3], true); o.setUint16(at + 22, r[4], true);
    }));
    lumps[6] = pack(40 * texinfo.length, o => texinfo.forEach(([s, t, slot, flags], k) => {
      const at = 40 * k;
      [s[0], s[1], s[2], 0, t[0], t[1], t[2], 0].forEach((v, i) => o.setFloat32(at + 4 * i, v, true));
      o.setInt32(at + 32, slot, true); o.setInt32(at + 36, flags, true);
    }));
    lumps[7] = pack(20 * faces.length, o => faces.forEach((f, k) => {
      const at = 20 * k;
      o.setUint16(at, f[0], true); o.setInt16(at + 2, f[1], true); o.setInt32(at + 4, f[2], true); o.setInt16(at + 8, f[3], true);
      o.setUint16(at + 10, f[4], true); f[5].forEach((v, i) => o.setUint8(at + 12 + i, v)); o.setInt32(at + 16, f[6], true);
    }));
    lumps[8] = new Uint8Array(p.light_samples).fill(p.light);
    lumps[9] = p.clipnodes;
    lumps[10] = pack(28 * (1 + leafRows.length), o => {
      o.setInt32(0, -2, true); o.setInt32(4, -1, true);
      leafRows.forEach(([contents, bx, fm, nm], k) => {
        const at = 28 * (k + 1);
        o.setInt32(at, contents, true); o.setInt32(at + 4, -1, true);
        shortBox(bx).forEach((v, i) => o.setInt16(at + 8 + 2 * i, v, true));
        o.setUint16(at + 20, fm, true); o.setUint16(at + 22, nm, true);
      });
    });
    lumps[11] = pack(2 * marks.length, o => marks.forEach((m, k) => o.setUint16(2 * k, m, true)));
    lumps[12] = pack(4 * edges.length, o => edges.forEach(([a, c], k) => { o.setUint16(4 * k, a, true); o.setUint16(4 * k + 2, c, true); }));
    lumps[13] = pack(4 * surf.length, o => surf.forEach((e, k) => o.setInt32(4 * k, e, true)));
    lumps[14] = pack(64, o => {
      [x0, y0, p.floor, x1, y1, ceiling, 0, 0, 0].forEach((v, i) => o.setFloat32(4 * i, v, true));
      [0, p.croot, p.croot, p.croot, 0, 0, faces.length].forEach((v, i) => o.setInt32(36 + 4 * i, v, true));
    });
    return lumps;
  }

  // ------------------------------------------------------------ the heap gate's ring model (tools/chim/heap.py)

  function sizesFrom(doc) {
    const src = doc && (doc.target_struct_sizes_bytes || doc.sizes || doc);
    const out = {};
    for (const k of SIZE_KEYS) {
      const v = src ? src[k] : undefined;
      if (v === undefined && k === 'scenery') continue;
      if (!Number.isInteger(v) || v < 0) throw Error('Target size "' + k + '" missing or invalid');
      out[k] = v;
    }
    return out;
  }
  // One zone block for a brush image (chunk terrain or placed model): heap.image_bytes.
  function imageBytes(lumpLengths, sizes, pointHullOnly = false) {
    const count = (k, probe) => Math.floor(lumpLengths[k] / sizes[probe]);
    const nodes = count(5, 'dnode');
    const parts = [count(3, 'dvertex') * sizes.mvertex, (count(12, 'dedge') + 1) * sizes.medge,
      count(13, 'int') * sizes.int, lumpLengths[2] ? Math.floor(lumpLengths[2] / 4) * sizes.pointer : 0,
      lumpLengths[8], lumpLengths[4], lumpLengths[0], lumpLengths[9], count(1, 'dplane') * sizes.mplane,
      count(6, 'texinfo') * sizes.mtexinfo, count(7, 'dface') * sizes.msurface, count(11, 'short') * sizes.pointer,
      count(10, 'dleaf') * sizes.mleaf, count(14, 'dmodel') * sizes.dmodel, nodes * sizes.dclipnode, pointHullOnly ? 0 : nodes * sizes.mnode];
    const arena = parts.reduce((s, x) => s + a16(x), 0);
    return sizes.hunk + a16(sizes.model + arena);
  }
  function textureBytes(width, height, sizes) {
    return sizes.hunk + a16(sizes.texture + Math.floor(width * height / 64) * 85);
  }
  const lumpLengths = image => brushLumps(image).map(l => l.length);

  // The per-frame tables the ring needs: chunk blocks, which models and textures each chunk and model needs.
  function ringTables(frameData, sizes, extra) {
    const {frame, chunks, models, textures} = frameData;
    const entry = sizes.scenery !== undefined ? sizes.scenery : sizes.entity;
    const g = frame.grain, lx = frame.low[0], ly = frame.low[1];
    const modelIds = [...models.keys()].sort((p, q) => p - q), texIds = [...textures.keys()].sort((p, q) => p - q);
    const mLocal = new Map(modelIds.map((m, i) => [m, i])), tLocal = new Map(texIds.map((t, i) => [t, i]));
    const modelSize = modelIds.map(m => models.get(m).heap_bytes), texSize = texIds.map(t => textureBytes(textures.get(t).width, textures.get(t).height, sizes));
    const modelTex = modelIds.map(m => [...new Set(models.get(m).textures)].map(t => tLocal.get(t)));
    const own = [], chunkModels = [], chunkTex = [], lo = [];
    for (const c of chunks) {
      const records = c.owned.length + c.reach.length;
      own.push(c.heap_bytes + sizes.hunk + a16(records * (entry + sizes.pointer)) + ((extra && extra[c.index]) || 0));
      chunkModels.push([...new Set(c.owned.concat(c.reach).map(r => mLocal.get(r.model)))]);
      chunkTex.push([...new Set(c.terrain_textures)].map(t => tLocal.get(t)));
      lo.push([lx + c.cx * g, ly + c.cy * g]);
    }
    return {frame, chunks, g, own, chunkModels, chunkTex, modelSize, texSize, modelTex, modelIds, texIds, lo,
      owned: chunks.map(c => c.owned.length), mStamp: new Int32Array(modelIds.length), tStamp: new Int32Array(texIds.length), stamp: 0};
  }
  // The active ring at (x, y): chunks whose box lies within radius of the point (ChimChunks_ActiveRadius).
  function ringAt(T, x, y, radius, detail) {
    const r2 = radius * radius, g = T.g;
    T.stamp++;
    if (T.stamp >= 0x7fffffff) { T.mStamp.fill(0); T.tStamp.fill(0); T.stamp = 1; }
    const s = T.stamp;
    let chunkBytes = 0, modelBytes = 0, texBytes = 0, nchunks = 0, nmodels = 0, ntex = 0, placements = 0;
    const active = detail ? [] : null, modelList = detail ? [] : null;
    for (let k = 0; k < T.lo.length; k++) {
      const lx = T.lo[k][0], ly = T.lo[k][1];
      const dx = Math.max(Math.max(lx - x, x - (lx + g)), 0), dy = Math.max(Math.max(ly - y, y - (ly + g)), 0);
      if (dx * dx + dy * dy > r2) continue;
      nchunks++; chunkBytes += T.own[k]; placements += T.owned[k];
      if (active) active.push(k);
      for (const t of T.chunkTex[k]) if (T.tStamp[t] !== s) { T.tStamp[t] = s; texBytes += T.texSize[t]; ntex++; }
      for (const m of T.chunkModels[k]) if (T.mStamp[m] !== s) {
        T.mStamp[m] = s; modelBytes += T.modelSize[m]; nmodels++;
        if (modelList) modelList.push(T.modelIds[m]);
        for (const t of T.modelTex[m]) if (T.tStamp[t] !== s) { T.tStamp[t] = s; texBytes += T.texSize[t]; ntex++; }
      }
    }
    const out = {bytes: chunkBytes + modelBytes + texBytes, chunk_bytes: chunkBytes, model_bytes: modelBytes,
      texture_bytes: texBytes, ring_chunks: nchunks, ring_models: nmodels, ring_textures: ntex, ring_placements: placements};
    if (detail) { out.chunks = active; out.models = modelList; }
    return out;
  }
  // Every player position on the gate's grid (positions every `sample` units over the frame), as heap._frame_ring.
  function ringScan(T, radius, budget, sample) {
    sample = sample || 64;
    const f = T.frame, g = f.grain, lx = f.low[0], ly = f.low[1], xs = [], ys = [];
    for (let x = lx + sample / 2; x < lx + f.nx * g; x += sample) xs.push(x);
    for (let y = ly + sample / 2; y < ly + f.ny * g; y += sample) ys.push(y);
    const totals = new Float64Array(xs.length * ys.length);
    let best = -1, bestAt = 0, over = 0, i = 0;
    for (const y of ys) for (const x of xs) {
      const t = ringAt(T, x, y, radius).bytes;
      totals[i] = t;
      if (t > best) { best = t; bestAt = i; }
      if (t > budget) over++;
      i++;
    }
    const sorted = Float64Array.from(totals).sort(), n = sorted.length;
    const median = n ? (n % 2 ? sorted[(n - 1) / 2] : (sorted[n / 2 - 1] + sorted[n / 2]) / 2) : 0;
    const peak = n ? ringAt(T, xs[bestAt % xs.length], ys[Math.floor(bestAt / xs.length)], radius, true) : null;
    return {xs, ys, totals, positions: n, positions_over_budget: over, peak_bytes: n ? best : 0,
      peak_position: n ? [xs[bestAt % xs.length], ys[Math.floor(bestAt / xs.length)]] : null,
      median_bytes: Math.trunc(median), budget_bytes: budget, headroom_bytes: budget - (n ? best : 0), peak};
  }

  // ------------------------------------------------------------ loading a world from local files

  // source: {list: () => [relative paths], read: path => Promise<Uint8Array>} rooted at the build's chim-world/
  // folder (holding chim/ and the reports) or at chim/ itself.
  async function openWorld(source) {
    const paths = source.list ? await source.list() : [];
    let base = null;
    for (const p of paths) if (/(^|\/)world\.cwi$/.test(p)) { const b = p.slice(0, -'world.cwi'.length); if (base === null || b.length < base.length) base = b; }
    if (base === null) {
      if (paths.length) throw Error('No chim/world.cwi in the chosen files: choose the build\'s chim-world folder (or its chim folder)');
      base = 'chim/';
    }
    const index = readIndex(await source.read(base + 'world.cwi'));
    const reportBase = base.endsWith('chim/') ? base.slice(0, -'chim/'.length) : base;
    const world = {source, base, reportBase, index, cache: new Map(), paths};
    world.frames = index.files.map((f, row) => ({row, f})).filter(x => x.f.kind === 'FRAM')
      .map(x => ({path: x.f.path.replace(/\/frame\.ccf$/, ''), file: x.f.path, cell: x.f.cell, row: x.row}));
    return world;
  }
  // The frame of an open world that holds exterior cell (x, y), from the index alone: the frame the caller names when
  // the world has it (the served build's cell table or the tracker's memory audit name it per cell), else the frame
  // of the cell itself; null otherwise (frameHolding then reads the frames around it).
  function frameForCell(world, x, y, hint) {
    const path = hint ? String(hint).replace(/\/frame\.ccf$/, '').replace(/\/$/, '') : null;
    if (path) { const f = world.frames.find(q => q.path === path); if (f) return f; }
    return world.frames.find(q => q.cell[0] === x && q.cell[1] === y) || null;
  }
  // ... and when neither names it (a cell of a town frame: Balmora's frame x-03/y-02 holds nine cells, Seyda Neen's more):
  // the frame whose chunk area holds the cell's centre, read from the frame files around the cell; where two areas hold
  // it (Seyda Neen's and Vivec's at cell 1,-10), the one it lies deeper inside (an area is a town's cells and a margin;
  // tools/toolkit_serve.py served_cell_maps, the same rule). Units: a frame's centre is in game units, its chunk grid in
  // map units (a quarter), a cell 8,192 game units across. null when no frame holds it: never a guess.
  const CELL_UNITS = 8192, MAP_SCALE = 4, NEAR_CELLS = 6;
  async function frameHolding(world, x, y, hint) {
    const found = frameForCell(world, x, y, hint);
    if (found) return found;
    const cx = (x + 0.5) * CELL_UNITS, cy = (y + 0.5) * CELL_UNITS;
    let best = null, deepest = -Infinity;
    for (const q of world.frames) {
      if (Math.abs(q.cell[0] - x) > NEAR_CELLS || Math.abs(q.cell[1] - y) > NEAR_CELLS) continue;
      if (!q.block) {
        const item = await fileRow(world, q.row, []);
        if (!item) continue;
        try { q.block = readFrame(item.data).frame; } catch (e) { continue; }
      }
      const b = q.block, lo = [b.centre[0] + MAP_SCALE * b.low[0], b.centre[1] + MAP_SCALE * b.low[1]];
      const hi = [lo[0] + MAP_SCALE * b.nx * b.grain, lo[1] + MAP_SCALE * b.ny * b.grain];
      if (!(cx >= lo[0] && cx < hi[0] && cy >= lo[1] && cy < hi[1])) continue;
      const inset = Math.min(cx - lo[0], hi[0] - cx, cy - lo[1], hi[1] - cy);
      if (inset > deepest) { best = q; deepest = inset; }
    }
    return best;
  }
  async function fileRow(world, row, problems) {
    if (world.cache.has(row)) return world.cache.get(row);
    const f = world.index.files[row];
    if (!f) throw Error('File row ' + row + ' is not in the index');
    let data = null;
    try { data = await world.source.read(world.base + f.path); } catch (e) { data = null; }
    let item = null;
    if (!data) problems.push('missing file ' + f.path);
    else {
      if (data.length !== f.bytes || crc32(data) !== f.crc) problems.push('size/CRC differs from the index: ' + f.path);
      item = {data, records: f.kind === 'SECT' ? readSector(data) : null};
    }
    world.cache.set(row, item);
    return item;
  }
  // Reads the file rows not read yet, LIMIT at a time (each row once; fileRow keeps them).
  async function prefetchRows(world, rows, problems, limit = 8) {
    const todo = [...new Set(rows)].filter(r => r !== undefined && !world.cache.has(r));
    let next = 0;
    const worker = async () => { while (next < todo.length) { const r = todo[next++]; await fileRow(world, r, problems); } };
    await Promise.all(Array.from({length: Math.min(limit, todo.length)}, worker));
  }
  function recordAt(item, offset) {
    if (!item || !item.records) return null;
    for (const r of item.records) if (r.offset === offset) return r;
    return null;
  }
  // One frame with everything its chunks need: chunk records (terrain references resolved), the models their
  // placements name and every texture used. sizes: target ABI sizes for the zone block figures (optional).
  async function loadFrame(world, framePath, sizes) {
    const problems = [], idx = world.index;
    const frow = idx.files.findIndex(f => f.kind === 'FRAM' && (f.path === framePath || f.path === framePath + '/frame.ccf'));
    if (frow < 0) throw Error('No frame ' + framePath + ' in this world');
    const fitem = await fileRow(world, frow, problems);
    if (!fitem) throw Error('The frame file ' + idx.files[frow].path + ' is missing');
    const {frame, chunks: dir, sectors} = readFrame(fitem.data);
    const cell = idx.files[frow].cell;
    const sectorRows = new Map();
    idx.files.forEach((f, row) => { if (f.kind === 'SECT' && f.cell[0] === cell[0] && f.cell[1] === cell[1]) sectorRows.set(f.sector, row); });
    const chunks = [], models = new Map(), textures = new Map();
    const needModels = new Set(), needTextures = new Set(), terrainLumps = new Map();
    // the files a frame needs are read several at a time (a served world: one request each, a few hundred for a town)
    await prefetchRows(world, [...sectorRows.values()], problems);
    const parsed = [];
    for (const c of dir) {
      const row = sectorRows.get(c.sector), item = row === undefined ? null : await fileRow(world, row, problems);
      const rec = recordAt(item, c.offset);
      if (!rec || rec.kind !== 'CHNK' || rec.id !== c.index) { problems.push('chunk ' + c.index + ' record not found'); continue; }
      let parts;
      try { parts = readChunk(rec.data); } catch (e) { problems.push('chunk ' + c.index + ': ' + (e.message || e)); continue; }
      parsed.push([c, row, rec, parts]);
    }
    await prefetchRows(world, parsed.filter(p => p[3].ref).map(p => p[3].ref.file), problems);
    for (const [c, row, rec, parts] of parsed) {
      let image = parts.image, render = parts.image_render, shift = null, terrain = null, lumps = null;
      try {
        if (parts.ref) {
          const titem = await fileRow(world, parts.ref.file, problems), t = recordAt(titem, parts.ref.offset);
          if (!t || t.kind !== 'TERR' || t.id !== parts.ref.id || t.bytes !== parts.ref.bytes) { problems.push('chunk ' + c.index + ' terrain reference not found'); continue; }
          image = t.data; render = parts.ref.render; shift = parts.ref.shift;
          const form = tag(t.data, 0) === 'THG1' ? 'generated' : tag(t.data, 0) === 'TRC1' ? 'compact' : 'image';
          terrain = {id: parts.ref.id, file: idx.files[parts.ref.file].path, bytes: t.bytes, render: parts.ref.render, shift, form};
          // a record many chunks reference is expanded once per frame (generated and compact records: 0.10, 0.11)
          const key = parts.ref.file + ':' + parts.ref.offset;
          if (!terrainLumps.has(key)) terrainLumps.set(key, brushLumps(t.data));
          lumps = terrainLumps.get(key);
          if (form !== 'image') render = imageLayout(lumps).render;
        } else lumps = brushLumps(image);
      } catch (e) { problems.push('chunk ' + c.index + ' terrain: ' + (e.message || e)); continue; }
      const lens = lumps.map(l => l.length);
      const terrainTextures = lumps[2].length ? readTextureRefs(lumps[2]) : [];
      for (const t of terrainTextures) needTextures.add(t);
      chunks.push(Object.assign({}, c, {owned: parts.owned, reach: parts.reach, reach_refs: parts.reach_refs, leaves: parts.leaves,
        image, lumps, image_render: render, shift, terrain, record_bytes: rec.bytes, record_size: parts.record_size, file: idx.files[row].path,
        terrain_textures: terrainTextures, lump_lengths: lens, heap_bytes: sizes ? imageBytes(lens, sizes) : null}));
    }
    // format 0.9: the reach references name records of this frame's own chunks
    problems.push(...resolveReach(chunks));
    for (const c of chunks) for (const r of c.owned.concat(c.reach)) needModels.add(r.model);
    await prefetchRows(world, [...needModels].map(m => idx.models[m]).filter(Boolean).map(e => e.file), problems);
    for (const m of [...needModels].sort((p, q) => p - q)) {
      const e = idx.models[m];
      if (!e) { problems.push('model ' + m + ' is not in the index'); continue; }
      const item = await fileRow(world, e.file, problems), rec = recordAt(item, e.offset);
      if (!rec || rec.kind !== 'MODL' || rec.id !== m || rec.bytes !== e.bytes) { problems.push('model ' + m + ' record not found'); continue; }
      const lumps = brushLumps(rec.data), refs = lumps[2].length ? readTextureRefs(lumps[2]) : [];
      for (const t of refs) needTextures.add(t);
      const lens = lumps.map(l => l.length);
      models.set(m, {id: m, name: e.name, bytes: e.bytes, render: e.render, image: rec.data, textures: refs,
        file: idx.files[e.file].path, lump_lengths: lens, heap_bytes: sizes ? imageBytes(lens, sizes, true) : null});
    }
    await prefetchRows(world, [...needTextures].map(t => idx.textures[t]).filter(Boolean).map(e => e.file), problems);
    for (const t of [...needTextures].sort((p, q) => p - q)) {
      const e = idx.textures[t];
      if (!e) { problems.push('texture ' + t + ' is not in the index'); continue; }
      const item = await fileRow(world, e.file, problems), rec = recordAt(item, e.offset);
      textures.set(t, {id: t, name: e.name, width: e.width, height: e.height, bytes: e.bytes,
        file: idx.files[e.file].path, miptex: rec && rec.kind === 'TEXR' && rec.id === t ? rec.data : null});
      if (!rec || rec.kind !== 'TEXR' || rec.id !== t) problems.push('texture ' + t + ' record not found');
    }
    return {path: idx.files[frow].path, cell, frame, sectors, chunks, models, textures, problems, version: idx.version};
  }
  // Byte counts of a loaded frame (the figures tests compare with the Python reader).
  function frameSummary(fd) {
    const placements = fd.chunks.reduce((s, c) => s + c.owned.length, 0), reach = fd.chunks.reduce((s, c) => s + c.reach.length, 0);
    return {frame: fd.path, cell: fd.cell, chunks: fd.chunks.length, owned: placements, reach,
      chunk_record_bytes: fd.chunks.reduce((s, c) => s + c.record_bytes, 0),
      chunk_render_bytes: fd.chunks.reduce((s, c) => s + c.render, 0),
      chunk_collision_bytes: fd.chunks.reduce((s, c) => s + c.collision, 0),
      terrain_references: fd.chunks.filter(c => c.terrain).length,
      models: fd.models.size, model_bytes: [...fd.models.values()].reduce((s, m) => s + m.bytes, 0),
      textures: fd.textures.size, texture_bytes: [...fd.textures.values()].reduce((s, t) => s + t.bytes, 0),
      chunk_heap_bytes: fd.chunks.reduce((s, c) => s + (c.heap_bytes || 0), 0),
      model_heap_bytes: [...fd.models.values()].reduce((s, m) => s + (m.heap_bytes || 0), 0)};
  }

  // The CHIM heap report (chim-heap.json): the frames by path, with the root settings.
  function parseHeapReport(doc) {
    if (!doc || typeof doc !== 'object' || !Array.isArray(doc.frames)) {
      if (doc && doc.ok === null) throw Error('This chim-heap.json says the gate did not run: ' + (doc.status || ''));
      throw Error('Not a CHIM heap report (chim-heap.json)');
    }
    const frames = new Map();
    for (const f of doc.frames) {
      if (typeof f.frame !== 'string' || !Number.isFinite(f.peak_bytes) || !Number.isFinite(f.budget_bytes)) throw Error('Invalid frame row in the heap report');
      frames.set(f.frame.replace(/\/frame\.ccf$/, ''), f);
    }
    return {active_radius: doc.active_radius, load_radius: doc.load_radius, zone_kib: doc.zone_kib, pool_kib: doc.pool_kib,
      pool_slots: doc.pool_slots, sample_units: doc.sample_units || 64, gated_ring: doc.gated_ring, ok: doc.ok,
      status: doc.status, frames,
      over: [...frames.values()].filter(f => !f.ok).map(f => f.frame.replace(/\/frame\.ccf$/, ''))};
  }

  // ------------------------------------------------------------ CHIM maps (.chim)

  // A CHIM map (the CHIM frame map): CHIM's own map format, today laid out like a Quake BSP29 file (a version
  // word and 15 lumps), holding an empty world, the map's entities, collision-only clip models and the
  // "_chim_frame" key that names its frame in the CHIM world. Geometry lives in the CHIM world, never here.
  function parseEntities(text) {
    const out = [], re = /\{([^{}]*)\}/g;
    let m;
    while ((m = re.exec(text))) {
      const e = {}, kv = /"([^"\n]*)"\s*"([^"\n]*)"/g;
      let p;
      while ((p = kv.exec(m[1]))) e[p[1]] = p[2];
      out.push(e);
    }
    return out;
  }
  function readChimMap(data) {
    const b = u8(data), d = dv(b);
    if (b.length < BSP_HEADER) throw Error('CHIM map shorter than its header');
    const version = d.getInt32(0, true);
    if (version !== 29) throw Error('CHIM map layout ' + version + ' is not known to this reader (it reads the BSP29-shaped layout)');
    const lumps = [];
    for (let k = 0; k < 15; k++) {
      const o = d.getInt32(4 + 8 * k, true), n = d.getInt32(8 + 8 * k, true);
      if (o < BSP_HEADER || n < 0 || o + n > b.length) throw Error('CHIM map lump ' + LUMPS[k] + ' outside the file');
      if (RECORD[k] && n % RECORD[k]) throw Error('CHIM map lump ' + LUMPS[k] + ' is not a whole number of records');
      lumps.push({name: LUMPS[k], offset: o, length: n});
    }
    const end = Math.max(...lumps.map(l => l.offset + l.length));
    const text = new TextDecoder('windows-1252').decode(b.subarray(lumps[0].offset, lumps[0].offset + lumps[0].length));
    const entities = parseEntities(text), world = entities[0] || {};
    const frameKey = world._chim_frame;
    let frameCell = null;
    if (frameKey !== undefined) {
      const v = frameKey.trim().split(/\s+/).map(Number);
      if (v.length === 2 && v.every(Number.isInteger)) frameCell = v;
    }
    const L = lumps[14], models = [];
    for (let at = L.offset; at + 64 <= L.offset + L.length; at += 64) {
      models.push({mins: [0, 1, 2].map(k => d.getFloat32(at + 4 * k, true)), maxs: [0, 1, 2].map(k => d.getFloat32(at + 12 + 4 * k, true)),
        origin: [0, 1, 2].map(k => d.getFloat32(at + 24 + 4 * k, true)), firstface: d.getInt32(at + 56, true),
        numfaces: d.getInt32(at + 60, true)});
    }
    const faces = lumps[7].length / 20;
    return {format: 'chim-map', layout: 'BSP29-shaped', version, bytes: b.length, tail_bytes: b.length - end, lumps, entities,
      worldspawn: world, frame_key: frameKey === undefined ? null : frameKey, frame_cell: frameCell, models, faces,
      frame_path: frameCell ? 'frames/x' + sign2(frameCell[0]) + '/y' + sign2(frameCell[1]) : null,
      streamed_statics: world._chim_streamed_statics !== undefined ? Number(world._chim_streamed_statics) : null,
      hunk_rest: world._chim_hunk_rest !== undefined ? Number(world._chim_hunk_rest) : null};
  }
  // The frame folder name of a cell, as the builder writes it (x-03, y+02).
  function sign2(v) { return (v < 0 ? '-' : '+') + String(Math.abs(v)).padStart(2, '0'); }
  // True when a map file names a CHIM frame (its worldspawn has "_chim_frame"): the builder's own test
  // (tools/map_files.is_chim_frame), never the file name. Old builds wrote frame maps as .bsp.
  function isChimFrameMap(data) {
    try {
      const b = u8(data), d = dv(b);
      if (b.length < BSP_HEADER || d.getInt32(0, true) !== 29) return false;
      const o = d.getInt32(4, true), n = d.getInt32(8, true);
      if (o < BSP_HEADER || n < 0 || o + n > b.length) return false;
      const text = new TextDecoder('windows-1252').decode(b.subarray(o, o + n));
      const first = /\{([^{}]*)\}/.exec(text);
      return !!first && /"_chim_frame"\s*"/.test(first[1]);
    } catch (e) { return false; }
  }

  // ------------------------------------------------------------ zip archives (a zipped chim-world folder)

  // Reads the central directory of a zip (stored or deflated members; no zip64). blob: a File/Blob.
  async function zipSource(blob) {
    const size = blob.size, tailLen = Math.min(size, 65557);
    const tail = new Uint8Array(await blob.slice(size - tailLen).arrayBuffer()), td = dv(tail);
    let eocd = -1;
    for (let i = tail.length - 22; i >= 0; i--) if (td.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
    if (eocd < 0) throw Error('Not a zip file (no end of central directory)');
    const count = td.getUint16(eocd + 10, true), cdSize = td.getUint32(eocd + 12, true), cdAt = td.getUint32(eocd + 16, true);
    if (cdAt === 0xFFFFFFFF || count === 0xFFFF) throw Error('Zip64 archives are not supported: zip the chim-world folder in parts, or choose the folder');
    const cd = new Uint8Array(await blob.slice(cdAt, cdAt + cdSize).arrayBuffer()), cdv = dv(cd), entries = new Map();
    for (let at = 0, i = 0; i < count; i++) {
      if (cdv.getUint32(at, true) !== 0x02014b50) throw Error('Zip central directory is damaged');
      const method = cdv.getUint16(at + 10, true), csize = cdv.getUint32(at + 20, true), usize = cdv.getUint32(at + 24, true),
        nlen = cdv.getUint16(at + 28, true), xlen = cdv.getUint16(at + 30, true), clen = cdv.getUint16(at + 32, true),
        local = cdv.getUint32(at + 42, true);
      const name = new TextDecoder('utf-8').decode(cd.subarray(at + 46, at + 46 + nlen));
      if (!name.endsWith('/')) entries.set(name, {method, csize, usize, local});
      at += 46 + nlen + xlen + clen;
    }
    const read = async path => {
      const e = entries.get(path);
      if (!e) return null;
      const head = dv(new Uint8Array(await blob.slice(e.local, e.local + 30).arrayBuffer()));
      const start = e.local + 30 + head.getUint16(26, true) + head.getUint16(28, true);
      const raw = blob.slice(start, start + e.csize);
      if (e.method === 0) return new Uint8Array(await raw.arrayBuffer());
      if (e.method !== 8) throw Error('Zip member ' + path + ' uses an unsupported compression method');
      if (typeof DecompressionStream !== 'function') throw Error('This browser cannot inflate zip members; choose the folder instead');
      const out = new Uint8Array(await new Response(raw.stream().pipeThrough(new DecompressionStream('deflate-raw'))).arrayBuffer());
      if (out.length !== e.usize) throw Error('Zip member ' + path + ' inflated to the wrong size');
      return out;
    };
    return {list: () => [...entries.keys()], read};
  }
  // A folder chosen with a directory input (File objects with webkitRelativePath): paths below the chosen folder.
  function filesSource(fileList) {
    const map = new Map();
    for (const f of fileList) {
      const rel = (f.webkitRelativePath || f.name).replace(/\\/g, '/');
      const parts = rel.split('/');
      map.set(parts.length > 1 ? parts.slice(1).join('/') : rel, f);
    }
    return {list: () => [...map.keys()], read: async p => { const f = map.get(p); return f ? new Uint8Array(await f.arrayBuffer()) : null; }};
  }
  // A world served over HTTP (e.g. tools/toolkit_serve.py or a local file server): base URL of the chim-world folder.
  function urlSource(base) {
    const root = base.replace(/\/?$/, '/');
    return {list: async () => {
      for (const probe of ['chim/world.cwi', 'world.cwi']) {
        try { const r = await fetch(root + probe, {method: 'HEAD'}); if (r.ok) return [probe]; } catch (e) { /* next */ }
      }
      return [];
    }, read: async p => { const r = await fetch(root + p); return r.ok ? new Uint8Array(await r.arrayBuffer()) : null; }};
  }

  // ---------------------------------------------------------------- collision figures and CHIM rooms
  // The drawing and collision parts of one brush image, as tools/collision_census.py model_stats counts them:
  // collision = clipnodes (lump 9) + the placed collision piece table (lump 4, "PCS1") + the planes only clipnodes
  // use; drawing = the rest of the image.
  function collisionStats(data) {
    const b = u8(data), L = readBrushImage(b), D = L.map(dv);
    const refs = little => {
      const np = L[1].length / 20, f = new Set(), n = new Set(), c = new Set();
      for (let o = 0; o + 20 <= L[7].length; o += 20) f.add(D[7].getUint16(o, little));
      for (let o = 0; o + 24 <= L[5].length; o += 24) n.add(D[5].getInt32(o, little));
      for (let o = 0; o + 8 <= L[9].length; o += 8) c.add(D[9].getInt32(o, little));
      for (const s of [f, n, c]) for (const p of s) if (p < 0 || p >= np) return null;
      return {f, n, c};
    };
    let little = true, r = refs(true);
    if (!r) { little = false; r = refs(false); }
    if (!r) throw Error('plane numbers out of range in both byte orders');
    let triangles = 0;
    for (let o = 0; o + 20 <= L[7].length; o += 20) triangles += Math.max(0, D[7].getInt16(o + 8, little) - 2);
    let clipOnly = 0;
    for (const p of r.c) if (!r.f.has(p) && !r.n.has(p)) clipOnly++;
    const nclip = L[9].length / 8;
    const hull = head => {
      if (head < 0 || head >= nclip) return [0, 0];
      const seen = new Set(), stack = [[head, 1]];
      let deepest = 0;
      while (stack.length) {
        const [i, depth] = stack.pop();
        if (seen.has(i)) continue;
        seen.add(i); deepest = Math.max(deepest, depth);
        for (const k of [4, 6]) { const ch = D[9].getUint16(8 * i + k, little); if (ch < 0xFFF0 && ch < nclip) stack.push([ch, depth + 1]); }
      }
      return [seen.size, deepest];
    };
    const heads = L[14].length >= 64 ? [0, 1, 2, 3].map(k => D[14].getInt32(36 + 4 * k, little)) : [0, -1, -1, -1];
    const h1 = hull(heads[1]), h2 = hull(heads[2]);
    const pieces = L[4].length >= 16 && tag(L[4], 0).slice(0, 3) === 'PCS' ? D[4].getUint32(4, false) : 0;
    const faces = L[7].length / 20, coll = L[9].length + L[4].length + clipOnly * 20, draw = Math.max(b.length - coll, 0);
    const round3 = x => Math.round(x * 1000) / 1000;
    return {faces, triangles, planes: L[1].length / 20, face_planes: r.f.size, node_planes: r.n.size,
      clip_only_planes: clipOnly, nodes: L[5].length / 24, clipnodes: nclip, hull1_clipnodes: h1[0],
      hull2_clipnodes: h2[0], deepest_chain: Math.max(h1[1], h2[1]), pieces, piece_bytes: L[4].length,
      clipnode_bytes: L[9].length, bytes: b.length, draw_bytes: draw, collision_bytes: coll,
      ratio_bytes: draw ? round3(coll / draw) : null, ratio_counts: faces ? round3((nclip + pieces) / faces) : null};
  }
  // chimi/rooms/<room>.crm (tools/chim/interior.py room_record): header ROOM, room block (bounds, model count),
  // the model list, then the placed records.
  function readRoomRecord(data) {
    const b = u8(data), d = dv(b), h = readHeader(b, 'ROOM', STORE_VERSIONS);
    const n = d.getUint32(HEADER + 24);
    if (h.directory !== HEADER + 32 || h.data !== h.directory + 4 * n) throw Error('Room record offsets do not match its model list');
    // placed records of format 0.8 on are 56 bytes (tools/chim/placed.py: the 48-byte record + pitch and roll)
    const size = h.count ? (b.length - h.data) / h.count : 56;
    if (![48, 56].includes(size)) throw Error('Room record size does not match its placements');
    const models = [];
    for (let i = 0; i < n; i++) models.push(d.getUint32(h.directory + 4 * i));
    const placements = [];
    for (let i = 0; i < h.count; i++) placements.push(readPlacement(b, h.data + i * size, size));
    return {bounds: [[0, 1, 2].map(k => d.getFloat32(HEADER + 4 * k)), [3, 4, 5].map(k => d.getFloat32(HEADER + 4 * k))],
      models, placements, version: h.version};
  }
  // A CHIM room store in SOURCE: the first chimi/world.cwi (an image's id1, the build's chim-interiors folder or
  // the run folder); its room names from the listing (when the source can list) and its index.
  async function openRoomStore(source) {
    const paths = source.list ? await source.list() : [];
    let base = null;
    for (const p of paths) if (/(^|\/)chimi\/world\.cwi$/.test(p)) { const s = p.slice(0, -'world.cwi'.length); if (base === null || s.length < base.length) base = s; }
    if (base === null) base = 'chimi/';
    const raw = await source.read(base + 'world.cwi');
    if (!raw) throw Error('No chimi/world.cwi in the chosen files: choose the image\'s id1 folder or the build\'s chim-interiors folder');
    const index = readIndex(raw, STORE_VERSIONS);
    const rooms = paths.filter(p => p.startsWith(base + 'rooms/') && p.endsWith('.crm')).map(p => p.slice(base.length + 6, -4)).sort();
    return {source, base, index, rooms, packs: new Map()};
  }
  // One room: its record, and per store model the image bytes and its collision figures (only the packs that hold
  // its models are read).
  async function loadRoom(store, room) {
    const raw = await store.source.read(store.base + 'rooms/' + room + '.crm');
    if (!raw) throw Error('No room ' + room + ' in this store (' + store.base + 'rooms/' + room + '.crm)');
    const rec = readRoomRecord(raw), idx = store.index, models = new Map(), problems = [];
    const ids = [...new Set(rec.models.concat(rec.placements.map(p => p.model)))].sort((a, b) => a - b);
    for (const i of ids) {
      const m = idx.models[i];
      if (!m) { problems.push('model ' + i + ' is not in the store'); continue; }
      const path = idx.files[m.file].path;
      if (!store.packs.has(path)) store.packs.set(path, await store.source.read(store.base + path));
      const pack = store.packs.get(path);
      if (!pack || m.offset + m.bytes > pack.length) { problems.push('model ' + i + ' runs past its pack ' + path); continue; }
      const image = pack.subarray(m.offset, m.offset + m.bytes);
      let stats = null;
      try { stats = collisionStats(image); } catch (e) { problems.push(m.name + ': ' + (e.message || e)); }
      models.set(i, {id: i, name: m.name, bytes: m.bytes, render: m.render, image, file: path, collision: stats});
    }
    return {room, record: rec, models, problems};
  }
  // Per room totals of a loaded room: placed (each placement counts its model) and stored (each model once).
  function roomCollisionTotals(rd) {
    const sum = list => {
      const t = {faces: 0, triangles: 0, clipnodes: 0, pieces: 0, draw_bytes: 0, collision_bytes: 0};
      for (const s of list) if (s) for (const k of Object.keys(t)) t[k] += s[k];
      t.ratio_bytes = t.draw_bytes ? Math.round(1000 * t.collision_bytes / t.draw_bytes) / 1000 : null;
      t.ratio_counts = t.faces ? Math.round(1000 * (t.clipnodes + t.pieces) / t.faces) / 1000 : null;
      return t;
    };
    return {stored: sum([...rd.models.values()].map(m => m.collision)),
      placed: sum(rd.record.placements.map(p => (rd.models.get(p.model) || {}).collision))};
  }

  const api = {READ_VERSIONS, STORE_VERSIONS, collisionStats, readRoomRecord, openRoomStore, loadRoom, roomCollisionTotals, LUMPS, DEFAULT_SIZES, DEFAULT_MEMORY, FLAG_OVER_16_LEAVES, FLAG_STORY_HIDDEN, crc32, nameHash,
    FILE_ORDER, brushLumps, decodeCompact, terrainFacts, generateTerrain, imageLayout, resolveReach, placeTransform, frameForCell, frameHolding,
    readHeader, readIndex, readFrame, readSector, readChunk, readPlacement, readBrushImage, readTextureRefs,
    brushGeometry, readMiptex, spatialOrder, sizesFrom, imageBytes, textureBytes, lumpLengths, ringTables, ringAt,
    ringScan, openWorld, loadFrame, frameSummary, parseHeapReport, readChimMap, isChimFrameMap, parseEntities,
    zipSource, filesSource, urlSource, sign2};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AmiWindChim = api;
})(typeof self !== 'undefined' ? self : this);
