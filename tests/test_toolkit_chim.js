// SPDX-License-Identifier: GPL-3.0-only
// The Toolkit's CHIM reader (amiwind-toolkit/chim-reader.js) on a CHIM world folder, for tests/test_toolkit_chim.py:
//   node tests/test_toolkit_chim.js world WORLD_DIR|ZIP SIZES_JSON [FRAME...]   per frame: byte counts and the ring scan
//   node tests/test_toolkit_chim.js map MAP_FILE                           a CHIM map (.chim) as the reader sees it
//   node tests/test_toolkit_chim.js heap HEAP_JSON                         the heap report as the page parses it
//   node tests/test_toolkit_chim.js page HTML WORLD_DIR SIZES_JSON FRAME MAP_FILE
//                                       the 3D Map Inspector's own CHIM code (DOM/WebGL stubbed: no GPU claim)
// Prints one JSON document. Synthetic data only in the test suite; nothing here reads game data by itself.
'use strict';
const fs = require('fs'), path = require('path');
const R = require(path.join(__dirname, '..', 'amiwind-toolkit', 'chim-reader.js'));

function dirSource(root) {
  const list = [];
  (function walk(dir, rel) {
    for (const e of fs.readdirSync(dir, {withFileTypes: true})) {
      const r = rel ? rel + '/' + e.name : e.name;
      if (e.isDirectory()) walk(path.join(dir, e.name), r); else list.push(r);
    }
  })(root, '');
  return {list: () => list, read: async p => { const f = path.join(root, p); return fs.existsSync(f) ? new Uint8Array(fs.readFileSync(f)) : null; }};
}

async function world(dir, sizesFile, frames) {
  const sizes = R.sizesFrom(JSON.parse(fs.readFileSync(sizesFile, 'utf8')));
  // a zip of the chim-world folder (stored or deflated members) reads as the folder does
  const zipped = /\.zip$/i.test(dir);
  const w = await R.openWorld(zipped ? await R.zipSource(new Blob([fs.readFileSync(dir)])) : dirSource(dir));
  const out = {version: w.index.version, settings: w.index.settings, frames: w.frames.map(f => f.path), loaded: []};
  let heap = null;
  const heapRaw = await w.source.read(w.reportBase + 'chim-heap.json');
  if (heapRaw) heap = R.parseHeapReport(JSON.parse(new TextDecoder().decode(heapRaw)));
  for (const frame of frames.length ? frames : out.frames) {
    const fd = await R.loadFrame(w, frame, sizes);
    const T = R.ringTables(fd, sizes);
    const radius = heap && heap.active_radius ? heap.active_radius : w.index.settings.draw_distance + w.index.settings.hysteresis;
    const row = heap ? heap.frames.get(frame.replace(/\/frame\.ccf$/, '')) : null;
    const budget = row ? row.budget_bytes : (R.DEFAULT_MEMORY.zone_kib - 2 * R.DEFAULT_MEMORY.pool_kib) * 1024;
    const scan = R.ringScan(T, radius, budget, heap ? heap.sample_units : 64);
    const geometry = {terrain_faces: 0, placement_faces: 0};
    for (const c of fd.chunks) geometry.terrain_faces += R.brushGeometry(c.image, {shift: c.shift || [0, 0, 0]}).faceCount;
    for (const c of fd.chunks) for (const r of c.owned) geometry.placement_faces += R.brushGeometry(fd.models.get(r.model).image, r).faceCount;
    out.loaded.push(Object.assign(R.frameSummary(fd), {problems: fd.problems, geometry,
      chunk_heap: fd.chunks.map(c => c.heap_bytes), model_heap: [...fd.models.values()].map(m => [m.id, m.heap_bytes]),
      scan: {peak_bytes: scan.peak_bytes, peak_position: scan.peak_position, positions: scan.positions,
        positions_over_budget: scan.positions_over_budget, median_bytes: scan.median_bytes, budget_bytes: scan.budget_bytes,
        ring_chunks: scan.peak.ring_chunks, ring_models: scan.peak.ring_models, ring_textures: scan.peak.ring_textures},
      report: row ? {peak_bytes: row.peak_bytes, peak_position: row.peak_position, positions_over_budget: row.positions_over_budget,
        ring_chunks: row.ring_chunks, ring_models: row.ring_models, ring_textures: row.ring_textures, budget_bytes: row.budget_bytes} : null}));
  }
  return out;
}

function map(file) {
  const m = R.readChimMap(new Uint8Array(fs.readFileSync(file)));
  return {format: m.format, layout: m.layout, version: m.version, bytes: m.bytes, tail_bytes: m.tail_bytes, faces: m.faces,
    entities: m.entities.length, frame_key: m.frame_key, frame_cell: m.frame_cell, frame_path: m.frame_path,
    models: m.models.length, classnames: m.entities.map(e => e.classname || null), is_frame_map: R.isChimFrameMap(fs.readFileSync(file))};
}

function heap(file) {
  const h = R.parseHeapReport(JSON.parse(fs.readFileSync(file, 'utf8')));
  return {active_radius: h.active_radius, zone_kib: h.zone_kib, pool_kib: h.pool_kib, over: h.over,
    frames: [...h.frames.entries()].map(([k, f]) => [k, f.peak_bytes, f.budget_bytes, f.ok])};
}

// The inspector page's CHIM code with stubbed DOM and WebGL (as tests/test_polycount_markup.js): a .chim map, the
// same bytes named .bsp, a CHIM world frame with the memory overlay, a picked ring and the object descriptions.
async function page(htmlFile, dir, sizesFile, frame, mapFile) {
  const vm = require('vm'), elements = new Map(), draws = [];
  const ctx2d = new Proxy({}, {get: (_, k) => typeof k === 'string' && /^[A-Z_]+$/.test(k) ? k : k.startsWith && k.startsWith('get') ? () => true : (...a) => { draws.push(k); return {}; }, set: () => true});
  function element(id) {
    const DEFAULTS = {bin: '64', terrainoverlap: '0.5', markmode: 'inspect', zonecolor: '#aeb6bf', zoneopacity: '0.25', speed: '200', textureoverride: '-1', mode: 'white'};
    if (!elements.has(id)) elements.set(id, {id, value: DEFAULTS[id] || '', checked: ['terrain', 'chimheat', 'chimworst'].includes(id), style: {}, textContent: '', className: '',
      files: null, tagName: 'DIV', clientWidth: 800, clientHeight: 600, width: 800, height: 600, options: [],
      addEventListener() {}, replaceChildren() { this.options = []; }, append(o) { this.options.push(o); if (!this.value) this.value = o.value; },
      focus() {}, blur() {}, getBoundingClientRect() { return {left: 0, top: 0, width: 800, height: 600}; }, getContext: () => ctx2d});
    return elements.get(id);
  }
  const context = vm.createContext({console, DataView, TextDecoder, TextEncoder, Uint8Array, Float32Array, Map, Set, Math, Array, Number, Error, JSON,
    Object, Infinity, AmiWindChim: R, performance: {now: () => 0}, requestAnimationFrame() {}, setTimeout() {}, URL: {}, Blob: class {},
    document: {addEventListener() {}, getElementById: element, activeElement: {tagName: 'BODY'}, createElement: () => ({value: '', textContent: ''})},
    window: {addEventListener() {}}});
  const html = fs.readFileSync(htmlFile, 'utf8');
  vm.runInContext(html.split(/<script>\s*/)[1].split('</script>')[0], context);
  const out = {};
  const raw = fs.readFileSync(mapFile), ab = raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.length);
  context.raw = ab;
  await vm.runInContext('openFile({name:"town-chim.chim",size:raw.byteLength,arrayBuffer:async()=>raw})', context);
  out.map = {hint: element('hint').textContent, objects: JSON.parse(vm.runInContext('JSON.stringify(objects.map(o=>o.name))', context))};
  await vm.runInContext('openFile({name:"town-chim.bsp",size:raw.byteLength,arrayBuffer:async()=>raw})', context);
  out.map_named_bsp = {hint: element('hint').textContent};
  context.src = dirSource(dir);
  await vm.runInContext('chimOpenWorld(src,"synthetic world",' + JSON.stringify(frame) + ')', context);
  context.sizesDoc = JSON.parse(fs.readFileSync(sizesFile, 'utf8'));
  vm.runInContext('chim.sizes=AmiWindChim.sizesFrom(sizesDoc);chim.sizesLabel="sizes.json";chimHeapUpdate()', context);
  out.world = JSON.parse(vm.runInContext('JSON.stringify({objects:objects.length,chunks:objects.filter(o=>o.chim&&o.chim.kind==="chunk").length,' +
    'placements:objects.filter(o=>o.chim&&o.chim.kind==="placement").length,markers:objects.filter(o=>o.chim&&o.chim.kind==="map-entity").length,' +
    'textures:scene.textures.length,frames:Array.from($("chimframe").options,o=>o.value),scan:{peak_bytes:chim.scan.peak_bytes,' +
    'peak_position:chim.scan.peak_position,positions_over_budget:chim.scan.positions_over_budget,positions:chim.scan.positions},' +
    'hint:$("hint").textContent,info:$("chiminfo").textContent})', context));
  vm.runInContext('chimRingAt(chim.scan.peak_position[0],chim.scan.peak_position[1])', context);
  out.ring = JSON.parse(vm.runInContext('JSON.stringify({bytes:chim.ring.bytes,chunks:chim.ring.chunks.length,info:$("chiminfo").textContent})', context));
  out.describe = JSON.parse(vm.runInContext('JSON.stringify({chunk:chimDescribe(objects.find(o=>o.chim&&o.chim.kind==="chunk")),' +
    'placement:chimDescribe(objects.find(o=>o.chim&&o.chim.kind==="placement"))})', context));
  draws.length = 0;
  vm.runInContext('drawChimOverlay($("areaoverlay").getContext("2d"))', context);
  out.overlay_draw_calls = draws.length;
  return out;
}

(async () => {
  const [mode, ...args] = process.argv.slice(2);
  let out;
  if (mode === 'world') out = await world(args[0], args[1], args.slice(2));
  else if (mode === 'map') out = map(args[0]);
  else if (mode === 'heap') out = heap(args[0]);
  else if (mode === 'page') out = await page(args[0], args[1], args[2], args[3], args[4]);
  else throw Error('usage: world|map|heap|page ...');
  process.stdout.write(JSON.stringify(out) + '\n');
})().catch(e => { process.stderr.write(String(e && e.stack || e) + '\n'); process.exit(1); });
