// SPDX-License-Identifier: GPL-3.0-only
// The World Map's Local view and Show in 3D on a cell of the CHIM open world (TOOLKIT-LOCAL-CHIM-CELL-NO-MAP-67), run by
// tests/test_toolkit_cell_to_inspector.py: world-map.html's script against inert DOM stubs, fed a small synthetic tracker
// document and a served build's config, as toolkit_serve.py --progress --served-build serves them; then the Toolkit page
// (index.html) handing such a link to its 3D Inspector tab. Synthetic data only; no browser, no GPU claim.
// Usage: node tests/test_toolkit_cell_to_inspector.js amiwind-toolkit
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert');
const KIT = path.resolve(process.argv[2] || path.join(__dirname, '..', 'amiwind-toolkit'));
const settle = () => new Promise(r => setImmediate(r));

const CONFIG = {ok: true, label: 'synthetic build (abc1234)', version: '0.0.67', maps: ['vivec_city-chim'], rooms: ['mh_reception'],
  base: '/chim-world/build/', world: true, interiors: true};
const cell = (x, y, state, extra) => Object.assign({x, y, land: true, island: 1, name: '', region: 'Ashlands Region', set: 'base',
  chim: {state, converted: state !== 'not_started' && state !== 'solstheim'}, audits: {}, bugs: [], categories: {},
  contents: {}, entrances: [], ring: 1}, extra || {});
const DOC = {format: 'aw-cell-progress-1', generated: '2026-11-17T12:00:00+00:00', mechanisms: [], runs: [], releases: [],
  headline: {land_cells: 4, passed: 2, percent: 50, eligible_release: 'v0.0.67', in_game_label: 'v0.0.66 (abc1234)', islands: []},
  cells: {
    // in the game, the tracker's memory audit names its frame (its own)
    '-1,7': cell(-1, 7, 'terrain_complete_unlit', {audits: {memory_fit: {status: 'passed', numbers: {frame: 'frames/x-01/y+07/frame.ccf'}}},
      categories: {statics: {placed: 23, converted: 23, deferred: {}}, creatures: {placed: 5, converted: 0, deferred: {'creature simulation pending': 5}}}}),
    // in the game inside a town frame (Balmora's frame holds its neighbours)
    '-2,-2': cell(-2, -2, 'audits_passed', {name: 'Balmora', region: 'West Gash Region', audits: {memory_fit: {status: 'passed', numbers: {frame: 'frames/x-03/y-02/frame.ccf'}}}}),
    // a sea cell in the game without a memory audit: offered by its cell, the inspector finds its frame
    '5,5': cell(5, 5, 'sea_in_game', {land: false}),
    // not in the newest build
    '-20,20': cell(-20, 20, 'solstheim', {island: 2, region: 'Isinfier Plains'}),
  },
  // the rooms (tools/cell_progress_rooms.py): two of them are rooms of the served build (/build/rooms.json), one is not
  interior_rooms: {rooms: [
    {id: 'Mournhold, Royal Palace: Reception Area', name: 'Mournhold, Royal Palace: Reception Area', island: 'Mournhold', master: 'Tribunal.esm',
     state: 'on_chim_rooms', group: 'in_game', reasons: [], batch: 'later: Mournhold', entrance: null},
    {id: 'Mournhold Temple: Reception Area', name: 'Mournhold Temple: Reception Area', island: 'Mournhold', master: 'Tribunal.esm',
     state: 'not_started', group: 'not_in_game', reasons: [], batch: 'later: Mournhold', entrance: null},
    {id: 'Abaelun Mine', name: 'Abaelun Mine', island: 'Vvardenfell', master: 'Morrowind.esm', state: 'on_chim_rooms', group: 'in_game',
     reasons: [], batch: 38, entrance: '-1,7'}]}};
const ROOMS = {ok: true, format: 'aw-toolkit-rooms-1', base: '/chim-world/build/', rooms: {
  'Mournhold, Royal Palace: Reception Area': {room: 'rid3587e40b7', map: 'rid3587e40b7', types: [], default_type: null},
  'Abaelun Mine': {room: 'abaelunmine', map: 'abaelunmine', types: [], default_type: null}}};
// toolkit_serve.py /build/room-faces.json (synthetic model names and figures)
const FACES = {ok: true, format: 'aw-toolkit-room-faces-1', rooms: {
  rid3587e40b7: {faces: 46629, placements: 151, models: 34, top: [['i/test_corner_01@s1', 382, 15, 5730], ['l/test_lamp_05@s1', 265, 18, 4770]]},
  abaelunmine: {faces: 12000, placements: 80, models: 20, top: [['i/test_rock@s1', 300, 10, 3000]]}}};

function makePage(parentLink) {
  const elements = new Map(), created = [], fills = [];
  const ctx = new Proxy({props: {}}, {
    get: (t, k) => k in t.props ? t.props[k] : (...args) => { if (k === 'fillText') fills.push(args[0]); return {width: 10}; },
    set: (t, k, v) => { t.props[k] = v; return true; },
  });
  function element(id) {
    if (!elements.has(id)) {
      const attrs = {};
      elements.set(id, {id, value: '', checked: false, hidden: false, innerHTML: '', textContent: '', style: {}, dataset: {}, tagName: 'DIV',
        disabled: false, src: '', children: [], options: [], width: 512, height: 512, clientWidth: 820, offsetWidth: 820, offsetHeight: 820, offsetLeft: 0, offsetTop: 0,
        classList: {add() {}, remove() {}, toggle() {}, contains() { return false; }},
        setAttribute(k, v) { attrs[k] = String(v); }, getAttribute(k) { return attrs[k] === undefined ? null : attrs[k]; },
        addEventListener() {}, focus() {}, click() {}, scrollIntoView() {}, remove() {}, append() {}, querySelector() { return null; }, querySelectorAll() { return []; },
        appendChild(c) { this.children.push(c); if (this.id === 'mapselect' && !this.value) this.value = c.value; },
        getBoundingClientRect: () => ({left: 0, top: 0, width: 820, height: 820}), getContext: () => ctx,
        contentWindow: {postMessage(m) { elements.get(id).posted = (elements.get(id).posted || []).concat([m]); }},
        get firstChild() { return element(id + ':thumb'); }});
    }
    return elements.get(id);
  }
  const posted = [];
  const store = {};
  const win = {addEventListener() {}, devicePixelRatio: 1, innerHeight: 1000, scrollY: 0,
    localStorage: {getItem: k => store[k] === undefined ? null : store[k], setItem: (k, v) => { store[k] = String(v); }}};
  win.parent = parentLink ? {postMessage: m => posted.push(m)} : win;
  win.postMessage = () => {};
  // the served build's own cell table (toolkit_serve.py /build/cell-maps.json) names Balmora's frame and its frame map
  const files = {'config.json': CONFIG, 'cell-progress.json': DOC, 'index.json': ['balmora-chim', 'mh_reception'], 'rooms.json': ROOMS, 'room-faces.json': FACES,
    'cell-maps.json': {ok: true, format: 'aw-toolkit-cell-maps-1', cells: {'-2,-2': {frame: 'frames/x-03/y-02', frame_id: null, maps: ['balmora-chim']}}}};
  const doc = {getElementById: element, querySelector: q => element('q:' + q), querySelectorAll: () => [],
    createElement: t => { const e = element('new:' + t + ':' + created.length); created.push(e); return e; },
    addEventListener() {}, body: {classList: {add() {}}, appendChild() {}}, activeElement: {tagName: 'BODY'}, head: {appendChild() {}}};
  win.document = doc;
  const context = vm.createContext({console, setTimeout: () => 0, clearTimeout() {}, setInterval: () => 0, clearInterval() {}, URLSearchParams,
    File: class {}, Image: class {}, Date, Math, JSON, Map, Set, Array, Object, Number, String, isFinite, Intl, ZebraPattern: () => '#7dffa6',
    location: {search: '?served=1', pathname: '/amiwind-toolkit/world-map.html', origin: 'http://127.0.0.1:8031'},
    document: doc, window: win, navigator: {},
    fetch: async url => {
      const name = String(url).split('?')[0].split('/').pop();
      if (!(name in files)) return {ok: false, status: 404, headers: {get: () => null}};
      return {ok: true, status: 200, headers: {get: () => null}, json: async () => JSON.parse(JSON.stringify(files[name])), blob: async () => null};
    }});
  context.window = win;
  // the page's pure legend and map layout, the interior tracker and the view switch (pure functions; the fold block is optional)
  win.ChimLegend = require(path.join(KIT, 'chim-legend.js'));
  win.AmiWindInteriors = require(path.join(KIT, 'interior-tracker.js'));
  win.AmiWindViews = require(path.join(KIT, 'expansion-views.js'));
  win.ChimHead = require(path.join(KIT, 'chim-head.js'));
  const html = fs.readFileSync(path.join(KIT, 'world-map.html'), 'utf8');
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  vm.runInContext(scripts[scripts.length - 1], context);
  return {run: code => vm.runInContext(code, context), element, created, fills, posted};
}
const cta = page => page.created.filter(e => e.className === 'cta').pop();

(async () => {
  // 1. Served, with the tracker and the served build's world: a cell in the game offers its CHIM frame, Show in 3D opens it.
  let page = makePage(false);
  for (let i = 0; i < 6; i++) await settle();
  assert.ok(page.run('!!chim'), 'the tracker loaded');
  assert.equal(page.run('servedBuild && servedBuild.label'), CONFIG.label, 'the served build is known');
  page.run('picked = {x: -1, y: 7}; showSelected(-1, 7)');
  assert.match(cta(page).textContent, /Local view \(2D \+ 3D\)/, 'a cell on CHIM is never "2D only"');
  const sel = page.element('mapselect');
  assert.equal(sel.children.length, 1);
  assert.equal(sel.children[0].value, 'frame:frames/x-01/y+07');
  assert.match(sel.children[0].textContent, /CHIM open world: frame x-01\/y\+07 · synthetic build \(abc1234\)/);
  assert.equal(page.element('open3d').disabled, false);
  assert.equal(page.element('localhint').textContent, '');
  await page.run('showMap()');
  const src = page.element('inspector3d').src;
  assert.ok(src.startsWith('map-inspector.html?'), src);
  const q = new URLSearchParams(src.split('?')[1]);
  assert.equal(q.get('world'), '/chim-world/build/');
  assert.equal(q.get('frame'), 'frames/x-01/y+07');
  assert.equal(q.get('cell'), '-1,7');
  console.log('PASS cell on CHIM: its frame in the Map list, Local view 2D + 3D, Show in 3D opens the frame of the served world');

  // 2. A town cell opens the town frame that holds it; a sea cell in the game without a memory audit is offered by its cell.
  page.element('mapselect').children.length = 0; page.element('mapselect').value = '';
  page.run('showSelected(-2, -2)');
  const town = page.element('mapselect').children.map(o => o.value);
  assert.deepEqual(town, ['frame:frames/x-03/y-02', 'balmora-chim'], 'the frame, then the frame map of the served build');
  assert.match(page.element('mapselect').children[1].textContent, /balmora-chim \(CHIM frame map: its entities\)/);
  page.element('mapselect').children.length = 0; page.element('mapselect').value = '';
  page.run('showSelected(5, 5)');
  const sea = page.element('mapselect').children[0];
  assert.equal(sea.value, 'frame:5,5');
  assert.match(sea.textContent, /the frame of cell 5, 5/);
  page.element('inspector3d').src = ''; page.run('inspectorReady = false');
  await page.run('showMap()');
  const q2 = new URLSearchParams(page.element('inspector3d').src.split('?')[1]);
  assert.equal(q2.get('cell'), '5,5'); assert.equal(q2.get('frame'), null);
  console.log('PASS town and sea cells: the town frame that holds the cell, a sea cell by its cell');

  // 3. Nothing to open: the button is never dead, a click says why.
  page.element('mapselect').children.length = 0; page.element('mapselect').value = '';
  page.run('showSelected(-20, 20)');
  assert.match(cta(page).textContent, /2D only: not in the newest build/);
  assert.equal(page.element('open3d').disabled, false, 'never a dead button');
  assert.match(page.element('localhint').textContent, /Nothing to open in 3D for this cell: not in the newest build/);
  page.element('localhint').textContent = '';
  await page.run('showMap()');
  assert.equal(page.element('localhint').textContent, 'Nothing to open in 3D for cell -20, 20: not in the newest build.');
  console.log('PASS nothing to open: the Local view button names why, Show in 3D says why when clicked');

  // 4. The Local view without island-cells.json, served: the tracker's record, never a request to load a file by hand.
  page.fills.length = 0;
  page.run('drawLocal(-1, 7)');
  assert.ok(!page.fills.some(t => /Load your island-cells/.test(t)), page.fills.join(' | '));
  assert.ok(page.fills.some(t => /this server has no island-cells\.json/.test(t)), page.fills.join(' | '));
  assert.match(page.element('locallegend').innerHTML, /statics: 23 \/ 23/);
  assert.match(page.element('locallegend').innerHTML, /creatures: 0 \/ 5 <span class="muted">\(5 creature simulation pending\)<\/span>/);
  assert.match(page.element('localtitle').innerHTML, /Ashlands Region/, 'the place name from the tracker record');
  console.log('PASS Local view without island data: the tracker record of the cell, its objects by type, no file asked for by hand');

  // 4b. Room tiles (TOOLKIT-TILE-TO-INSPECTOR-67): a 3D button on every room the served build holds, a dash on the others; the
  // button and the Mournhold screen's picked tile open the room in the inspector.
  page.run('itFold = null; itRender()');
  const list = page.element('itlist').innerHTML;
  assert.match(list, /data-room3d="Mournhold, Royal Palace: Reception Area"[^>]*title="Open Mournhold, Royal Palace: Reception Area \(room rid3587e40b7\)/);
  assert.match(list, /data-room3d="Abaelun Mine"/);
  assert.ok(!/data-room3d="Mournhold Temple: Reception Area"/.test(list), 'no button for a room the build does not hold');
  assert.match(list, /<th class="l">3D<\/th>/);
  page.element('inspector3d').src = ''; page.run('inspectorReady = false');
  assert.equal(page.run('openRoom3d("Mournhold, Royal Palace: Reception Area")'), true);
  const rq = new URLSearchParams(page.element('inspector3d').src.split('?')[1]);
  assert.equal(rq.get('rooms'), '/chim-world/build/'); assert.equal(rq.get('room'), 'rid3587e40b7');
  assert.equal(page.run('openRoom3d("Mournhold Temple: Reception Area")'), false);
  page.run('viewSelect("mournhold"); evPicked = itIr.rooms[0]; mhRender()');
  assert.equal(page.element('mh3d').hidden, false);
  assert.equal(page.element('mh3d').textContent, '▶ Open Mournhold, Royal Palace: Reception Area in 3D');
  assert.match(page.element('mhlist').innerHTML, /data-room3d="Mournhold, Royal Palace: Reception Area"/);
  page.run('evPicked = itIr.rooms[1]; mhRender()');
  assert.match(page.element('mh3d').textContent, /not a room of the build/);
  page.element('mh3d').onclick();
  assert.match(page.element('mhtip').textContent, /nothing to open in 3D/);
  console.log('PASS room tiles: a 3D button per room of the served build, a dash otherwise; the button and the picked Mournhold tile open the room');

  // 4c. The rooms heatmap on the Mournhold screen (TOOLKIT-DLC-VIEWS-64): drawn faces per room from /build/room-faces.json, the
  // heaviest rooms with their heaviest models, each opening in the inspector with the polygon heatmap.
  page.element('mhcolour').value = 'faces';
  await page.run('loadRoomFaces()');
  const heavy = page.element('mhlist').innerHTML;
  assert.match(heavy, /<h3>Heaviest rooms by drawn faces<\/h3>/);
  assert.match(heavy, /Mournhold, Royal Palace: Reception Area<\/td><td>46,629<\/td><td>151<\/td>/);
  assert.match(heavy, /l\/test_lamp_05@s1 265 faces x 18 = 4,770/);
  assert.match(heavy, /data-room3d="Mournhold, Royal Palace: Reception Area" data-heat="visual"/);
  assert.match(page.element('mhlegend').innerHTML, /Drawn faces per room of synthetic build \(abc1234\)/);
  page.run('evPicked = itIr.rooms[0]');
  assert.match(page.run('mhText(evPicked)'), /46,629 faces drawn, heaviest: i\/test_corner_01@s1 5,730/);
  page.element('inspector3d').src = ''; page.run('inspectorReady = false');
  page.run('openRoom3d("Mournhold, Royal Palace: Reception Area", "visual")');
  assert.equal(new URLSearchParams(page.element('inspector3d').src.split('?')[1]).get('heat'), 'visual');
  page.element('mhcolour').value = 'state';
  page.run('viewSelect("vvardenfell")');
  console.log('PASS rooms heatmap: faces per room, the heaviest rooms with their heaviest models, opening with the polygon heatmap');

  // 5. Inside the Toolkit page: the link goes to the Toolkit, which opens its 3D Inspector tab.
  page = makePage(true);
  for (let i = 0; i < 6; i++) await settle();
  page.run('showSelected(-1, 7)');
  await page.run('showMap()');
  const msg = page.posted.find(m => m.type === 'amiwind-open-inspector');
  assert.ok(msg && msg.link, JSON.stringify(page.posted));
  assert.deepEqual(JSON.parse(JSON.stringify(msg.link)), {world: '/chim-world/build/', frame: 'frames/x-01/y+07', cell: '-1,7', label: CONFIG.label});
  // the headline the page sends carries the expansions' rooms and cells, the cards' own figures (TOOLKIT-DLC-VIEWS-64)
  const headMsg = page.posted.filter(m => m.type === 'amiwind-chim-head').pop();
  const trib = headMsg.expansions.find(e => e.id === 'tribunal');
  assert.deepEqual([trib.rooms.done, trib.rooms.total], [1, 2]);
  console.log('PASS embedded: Show in 3D hands the link to the Toolkit page; the headline message carries the expansion figures');

  // 6. The Toolkit page (index.html) opens its inspector tab on the link: the first time by address, later by message.
  const els = new Map(), el = id => {
    if (!els.has(id)) els.set(id, {id, src: '', classList: {t: new Set(), toggle(c, on) { on ? this.t.add(c) : this.t.delete(c); }, contains(c) { return this.t.has(c); }},
      setAttribute() {}, getAttribute: () => 'false', contentWindow: {postMessage(m) { (el(id).posted = el(id).posted || []).push(m); }}, addEventListener() {}});
    return els.get(id);
  };
  let onMessage = null;
  const ictx = vm.createContext({console, URLSearchParams, File: class {}, history: {replaceState() {}},
    location: {search: '?served=1', pathname: '/amiwind-toolkit/index.html', hash: '#world'},
    document: {getElementById: el, addEventListener() {}},
    window: {addEventListener: (k, f) => { if (k === 'message') onMessage = f; }, AmiWindToolkitHeader: {help() {}}, ChimHead: {render() {}, setSummary() {}}}});
  const ihtml = fs.readFileSync(path.join(KIT, 'index.html'), 'utf8');
  vm.runInContext([...ihtml.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).pop(), ictx);
  const world = el('world'), inspector = el('inspector');
  const link = {world: '/chim-world/build/', frame: 'frames/x-01/y+07', cell: '-1,7', label: CONFIG.label};
  onMessage({source: world.contentWindow, data: {type: 'amiwind-open-inspector', link}});
  assert.ok(inspector.classList.contains('active'), 'the 3D Inspector tab is shown');
  const iq = new URLSearchParams(inspector.src.split('?')[1]);
  assert.equal(inspector.src.split('?')[0], 'map-inspector.html');
  assert.equal(iq.get('world'), '/chim-world/build/'); assert.equal(iq.get('frame'), 'frames/x-01/y+07'); assert.equal(iq.get('cell'), '-1,7');
  inspector.onload();
  onMessage({source: world.contentWindow, data: {type: 'amiwind-open-inspector', link: {rooms: '/chim-world/build/', room: 'mh_reception'}}});
  const sent = (inspector.posted || []).pop();
  assert.deepEqual(JSON.parse(JSON.stringify(sent)), {type: 'amiwind-open-link', rooms: '/chim-world/build/', room: 'mh_reception'});
  console.log('PASS Toolkit page: the 3D Inspector tab opens the link, by address the first time and by message after');
  console.log('cell to inspector ok');
})().catch(e => { console.error(e && e.stack || e); process.exit(1); });
