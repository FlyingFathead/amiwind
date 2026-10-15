// SPDX-License-Identifier: GPL-3.0-only
// CHIM reader for the Toolkit's 3D Map Inspector: CHIM maps (.chim frame maps) and the CHIM world files
// (chim/world.cwi index, chim/frames/x<X>/y<Y>/frame.ccf frame files, sNN.ccs sector files; world format 0.5
// and 0.7), read in the browser from local files. Nothing is uploaded.
// It is a port of the builder's own reader, tools/chim/format.py (records, brush images, terrain references)
// and of the CHIM heap gate's ring model, tools/chim/heap.py (zone block sizes, the active ring, the 64-unit
// position scan); tests/test_toolkit_chim.py checks it against them on a synthetic world built by tools/chim.
// Layout: docs/chim/WORLD_FORMAT.md. A .chim file is CHIM's own map format (the modified BSP format), read
// here by its own reader (readChimMap), never by the inspector's Quake BSP reader.
(function (root) {
  'use strict';
  const READ_VERSIONS = [[0, 5], [0, 7]];
  const KINDS = ['INDX', 'FRAM', 'SECT'];
  const RECORD_KINDS = ['CHNK', 'TERR', 'MODL', 'TEXR'];
  const LUMPS = ['entities', 'planes', 'textures', 'vertexes', 'visibility', 'nodes', 'texinfo', 'faces',
    'lighting', 'clipnodes', 'leafs', 'marksurfaces', 'edges', 'surfedges', 'models'];
  const RECORD = {1: 20, 3: 12, 5: 24, 6: 40, 7: 20, 9: 8, 10: 28, 11: 2, 12: 4, 13: 4, 14: 64};
  const BSP_HEADER = 4 + 15 * 8;
  const HEADER = 32, SETTINGS = 40, TOC = 32, FILE_ROW = 60, MODEL_ROW = 24, TEXTURE_ROW = 24;
  const FRAME_BLOCK = 32, CHUNK_ROW = 28, SECTOR_ROW = 12, RECORD_ROW = 16, CHUNK_HEAD = 24, PLACEMENT = 48;
  const TERRAIN_REF = 32;
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

  function readHeader(data, kind) {
    const b = u8(data), d = dv(b);
    if (b.length < HEADER) throw Error('CHIM file shorter than its header');
    const magic = tag(b, 0), k = tag(b, 4);
    if (magic !== 'CHIM' || !KINDS.includes(k)) throw Error('Not a CHIM file');
    if (kind && k !== kind) throw Error('Expected a CHIM ' + kind + ' file, found ' + k);
    const version = [d.getUint16(8), d.getUint16(10)];
    if (!READ_VERSIONS.some(v => v[0] === version[0] && v[1] === version[1]))
      throw Error('CHIM world format ' + version.join('.') + ', expected ' + READ_VERSIONS.map(v => v.join('.')).join(' or '));
    const size = d.getUint32(12), count = d.getUint32(16), directory = d.getUint32(20), dataAt = d.getUint32(24),
      total = d.getUint32(28);
    if (size !== HEADER || total !== b.length || !(size <= directory && directory <= dataAt && dataAt <= total))
      throw Error('CHIM header offsets do not match the file');
    return {kind: k, count, directory, data: dataAt, bytes: total, version};
  }

  function readIndex(data) {
    const b = u8(data), d = dv(b), h = readHeader(b, 'INDX');
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

  function readPlacement(b, at) {
    const d = dv(b);
    return {pid: d.getUint32(at), ref: d.getUint32(at + 4), model: d.getUint32(at + 8),
      origin: [d.getFloat32(at + 12), d.getFloat32(at + 16), d.getFloat32(at + 20)], yaw: d.getFloat32(at + 24),
      owner: d.getUint16(at + 28), cell_dx: d.getInt8(at + 30), cell_dy: d.getInt8(at + 31),
      box: [[0, 1, 2].map(k => d.getInt16(at + 32 + 2 * k)), [0, 1, 2].map(k => d.getInt16(at + 38 + 2 * k))],
      leaves: d.getUint16(at + 44), flags: d.getUint16(at + 46)};
  }

  function readChunk(data) {
    const b = u8(data), d = dv(b), magic = tag(b, 0);
    if (magic !== 'CHK0' && magic !== 'CHK1') throw Error('Not a chunk record');
    const nOwned = d.getUint16(4), nReach = d.getUint16(6), imageAt = d.getUint32(8), imageRender = d.getUint32(12),
      pvsBytes = d.getUint16(16), leaves = d.getUint16(18), pvlBytes = d.getUint16(20);
    const recs = [];
    for (let k = 0; k < nOwned + nReach; k++) recs.push(readPlacement(b, CHUNK_HEAD + k * PLACEMENT));
    const pvsAt = CHUNK_HEAD + (nOwned + nReach) * PLACEMENT;
    if (imageAt < pvsAt + pvsBytes + pvlBytes || imageAt + imageRender > b.length) throw Error('Chunk record parts overlap or overrun');
    const out = {owned: recs.slice(0, nOwned), reach: recs.slice(nOwned), pvs: b.subarray(pvsAt, pvsAt + pvsBytes),
      pvl: b.subarray(pvsAt + pvsBytes, pvsAt + pvsBytes + pvlBytes), leaves, image: b.subarray(imageAt),
      image_render: imageRender, render: imageAt + imageRender};
    if (magic === 'CHK1') {
      const r = imageAt;
      if (r + TERRAIN_REF > b.length) throw Error('Terrain reference block outside the chunk record');
      out.ref = {id: d.getUint32(r), file: d.getUint16(r + 4), offset: d.getUint32(r + 8), bytes: d.getUint32(r + 12),
        render: d.getUint32(r + 16), shift: [d.getFloat32(r + 20), d.getFloat32(r + 24), d.getFloat32(r + 28)]};
    }
    return out;
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
  // The faces of a brush image as polygons, moved by shift (a referenced terrain record) or turned by yaw and
  // moved to origin (a placement): {vertices, polygons: [{vertices, texinfo, texture (global id), uv, ...}]}.
  function brushGeometry(data, place) {
    const lumps = readBrushImage(data), L = lumps.map(dv), refs = lumps[2].length ? readTextureRefs(lumps[2]) : [];
    const nv = lumps[3].length / 12, ne = lumps[12].length / 4, nse = lumps[13].length / 4, nf = lumps[7].length / 20;
    const ntex = lumps[6].length / 40, npl = lumps[1].length / 20;
    let first = 0, count = nf;
    if (lumps[14].length >= 64) { first = L[14].getInt32(56, true); count = L[14].getInt32(60, true); }
    if (first < 0 || count < 0 || first + count > nf) throw Error('Brush image model face range outside its faces');
    const origin = (place && place.origin) || [0, 0, 0], yaw = (place && place.yaw || 0) * Math.PI / 180;
    const shift = (place && place.shift) || [0, 0, 0], cy = Math.cos(yaw), sy = Math.sin(yaw);
    const used = new Map(), vertices = [], polygons = [];
    const vertex = j => {
      if (j < 0 || j >= nv) throw Error('Invalid vertex index');
      if (!used.has(j)) {
        const x = L[3].getFloat32(12 * j, true) + shift[0], y = L[3].getFloat32(12 * j + 4, true) + shift[1],
          z = L[3].getFloat32(12 * j + 8, true) + shift[2];
        used.set(j, vertices.length);
        vertices.push([origin[0] + x * cy - y * sy, origin[1] + x * sy + y * cy, origin[2] + z]);
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
  const lumpLengths = image => readBrushImage(image).map(l => l.length);

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
    const needModels = new Set(), needTextures = new Set();
    for (const c of dir) {
      const row = sectorRows.get(c.sector), item = row === undefined ? null : await fileRow(world, row, problems);
      const rec = recordAt(item, c.offset);
      if (!rec || rec.kind !== 'CHNK' || rec.id !== c.index) { problems.push('chunk ' + c.index + ' record not found'); continue; }
      const parts = readChunk(rec.data);
      let image = parts.image, render = parts.image_render, shift = null, terrain = null;
      if (parts.ref) {
        const titem = await fileRow(world, parts.ref.file, problems), t = recordAt(titem, parts.ref.offset);
        if (!t || t.kind !== 'TERR' || t.id !== parts.ref.id || t.bytes !== parts.ref.bytes) { problems.push('chunk ' + c.index + ' terrain reference not found'); continue; }
        image = t.data; render = parts.ref.render; shift = parts.ref.shift;
        terrain = {id: parts.ref.id, file: idx.files[parts.ref.file].path, bytes: t.bytes, render: parts.ref.render, shift};
      }
      const lumps = readBrushImage(image), lens = lumps.map(l => l.length);
      const terrainTextures = lumps[2].length ? readTextureRefs(lumps[2]) : [];
      for (const t of terrainTextures) needTextures.add(t);
      for (const r of parts.owned.concat(parts.reach)) needModels.add(r.model);
      chunks.push(Object.assign({}, c, {owned: parts.owned, reach: parts.reach, leaves: parts.leaves, image,
        image_render: render, shift, terrain, record_bytes: rec.bytes, file: idx.files[row].path,
        terrain_textures: terrainTextures, lump_lengths: lens, heap_bytes: sizes ? imageBytes(lens, sizes) : null}));
    }
    for (const m of [...needModels].sort((p, q) => p - q)) {
      const e = idx.models[m];
      if (!e) { problems.push('model ' + m + ' is not in the index'); continue; }
      const item = await fileRow(world, e.file, problems), rec = recordAt(item, e.offset);
      if (!rec || rec.kind !== 'MODL' || rec.id !== m || rec.bytes !== e.bytes) { problems.push('model ' + m + ' record not found'); continue; }
      const lumps = readBrushImage(rec.data), refs = lumps[2].length ? readTextureRefs(lumps[2]) : [];
      for (const t of refs) needTextures.add(t);
      const lens = lumps.map(l => l.length);
      models.set(m, {id: m, name: e.name, bytes: e.bytes, render: e.render, image: rec.data, textures: refs,
        file: idx.files[e.file].path, lump_lengths: lens, heap_bytes: sizes ? imageBytes(lens, sizes, true) : null});
    }
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

  const api = {READ_VERSIONS, LUMPS, DEFAULT_SIZES, DEFAULT_MEMORY, FLAG_OVER_16_LEAVES, FLAG_STORY_HIDDEN, crc32, nameHash,
    readHeader, readIndex, readFrame, readSector, readChunk, readPlacement, readBrushImage, readTextureRefs,
    brushGeometry, readMiptex, spatialOrder, sizesFrom, imageBytes, textureBytes, lumpLengths, ringTables, ringAt,
    ringScan, openWorld, loadFrame, frameSummary, parseHeapReport, readChimMap, isChimFrameMap, parseEntities,
    zipSource, filesSource, urlSource, sign2};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AmiWindChim = api;
})(typeof self !== 'undefined' ? self : this);
