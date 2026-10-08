// SPDX-License-Identifier: GPL-3.0-only
// World Map "Map metrics" layer checks. Synthetic layer only (written by
// tests/test_world_metrics.py); DOM and canvas are inert stubs, no browser.
// Usage: node tests/test_world_metrics_layer.js amiwind-toolkit/world-map.html layer.json
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert');
const html = fs.readFileSync(process.argv[2] || path.join(__dirname, '..', 'amiwind-toolkit', 'world-map.html'), 'utf8');
if (!process.argv[3]) { console.error('usage: world-map.html layer.json'); process.exit(2); }
const LAYER = fs.readFileSync(process.argv[3], 'utf8');
const script = html.split(/<script>\s*/)[1].split('</script>')[0];
const SEQ = ['#e8f1fb', '#c6dcf4', '#9cc2eb', '#6ea4df', '#4387d2', '#2a6bb8'], HOT = '#c8423f';  // world heat map chart

function makePage(files, search) {
  const elements = new Map(), calls = [];
  const ctx = new Proxy({props: {}}, {
    get: (t, k) => k in t.props ? t.props[k] : (...args) => { calls.push({op: k, args, fill: t.props.fillStyle, stroke: t.props.strokeStyle}); return {}; },
    set: (t, k, v) => { t.props[k] = v; return true; },
  });
  function element(id) {
    if (!elements.has(id)) {
      const attrs = {};
      elements.set(id, {
        id, value: '', checked: false, hidden: false, innerHTML: '', textContent: '', style: {}, dataset: {}, tagName: 'DIV',
        width: 820, height: 820, clientWidth: 820, offsetWidth: 820, offsetHeight: 820, offsetLeft: 0, offsetTop: 0,
        classList: {add() {}, remove() {}, toggle() {}},
        setAttribute(k, v) { attrs[k] = String(v); }, getAttribute(k) { return attrs[k] === undefined ? null : attrs[k]; },
        addEventListener() {}, focus() {}, click() {}, appendChild() {}, scrollIntoView() {},
        getBoundingClientRect: () => ({left: 0, top: 0, width: 820, height: 820}),
        getContext: () => ctx,
        get firstChild() { return element(id + ':thumb'); },
      });
    }
    return elements.get(id);
  }
  const win = {addEventListener() {}, devicePixelRatio: 1, postMessage() {}};
  win.parent = win;
  const context = vm.createContext({
    console, setTimeout: f => 0, URLSearchParams, File: class {}, Image: class {},
    location: {search: search || '', pathname: '/amiwind-toolkit/world-map.html'},
    document: {getElementById: element, querySelector: q => element('q:' + q), createElement: t => element('new:' + t + Math.random()),
               addEventListener() {}, body: {classList: {add() {}}, appendChild() {}}, activeElement: {tagName: 'BODY'}},
    window: win, navigator: {},
    fetch: async url => {
      const name = url.split('/').pop();
      if (!(name in files)) return {ok: false};
      return {ok: true, json: async () => JSON.parse(files[name]), blob: async () => null};
    },
  });
  vm.runInContext(script, context);
  element('townlabels').checked = true;
  const run = code => vm.runInContext(code, context);
  return {run, element, calls, context};
}
const settle = () => new Promise(r => setImmediate(r));

(async () => {
  // 1. No --metrics: the layer stays hidden and off; existing layers untouched.
  let page = makePage({}, '?served=1');
  await settle(); await settle();
  assert.equal(page.run('metrics'), null);
  assert.equal(page.run('metricsOn()'), false);
  assert.match(html, /<div id="metricsbar" hidden>/, 'Metrics bar starts hidden');
  assert(!page.element('layers').innerHTML.includes('layer-metrics'), 'Not in the main layer bar');
  assert(page.element('layers').innerHTML.includes('layer-terrain'), 'Existing layers still listed');
  assert.equal(page.run("LAYERS.find(L => L.id === 'metrics').on"), false);
  assert.match(html, /fetch\('\.\.\/data\/' \+ name\)/);
  assert(html.includes("get('world-metrics.json', 'json')"), 'Served layer read from ../data/world-metrics.json');
  page.run('setMetrics({format: "something-else"})');
  assert.equal(page.run('metrics'), null, 'Wrong format refused');
  assert.match(page.element('metricssummary').textContent, /Not a map metrics layer/);
  console.log('PASS metrics hidden without a layer: bar hidden, layer off, served fetch 404 keeps it off, wrong format refused.');

  // 2. Served layer: shown and on, chart colour scale, counts by metric, content and texinfo limit.
  page = makePage({'world-metrics.json': LAYER}, '?served=1');
  await settle(); await settle();
  const {run, element, calls} = page;
  assert.equal(run('metrics.format'), 'aw-world-metrics-1');
  assert.equal(element('metricsbar').hidden, false);
  assert.equal(element('layer-metrics').checked, true);
  assert.equal(run('metricsOn()'), true);
  assert.equal(run('metricsFileName'), 'served:world-metrics.json');
  assert.deepEqual(JSON.parse(run('JSON.stringify(METRIC_SEQ)')), SEQ);
  assert.equal(run('METRIC_OVER'), HOT);
  for (const [r, c] of [[0, SEQ[0]], [.5, SEQ[0]], [.5001, SEQ[1]], [.6, SEQ[1]], [.75, SEQ[3]], [.9, SEQ[4]], [.95, SEQ[5]],
                        [1, SEQ[5]], [1.0001, HOT], [3, HOT]]) assert.equal(run('metricColour(' + r + ')'), c, 'ratio ' + r);
  assert.equal(run('metricColour(null)'), null);
  assert.deepEqual(JSON.parse(run('JSON.stringify(metrics.bounds)')), [-20, 0, 1, 20]);
  assert.equal(run('metricsCountText()'), '2 cells hold at least one region over budget \u00b7 3 cells with objects');
  assert.equal(element('metricscount').textContent, run('metricsCountText()'));
  run("mset.mode = 'cur'");
  assert.equal(run('metricsCounts().over'), 0, 'Current content stays under budget');
  run("mset.mode = 'evr'; mset.metric = 'texinfo'");
  assert.equal(run('metricsCountText()'), '1 cell hold at least one region over the limit \u00b7 3 cells with objects');
  run("mset.texinfo = 'planned'");
  assert.equal(run("metricLimit('texinfo')"), 65535);
  assert.equal(run('metricsCounts().over'), 0, 'Planned texinfo limit');
  run("mset.texinfo = 'today'; mset.metric = 'lights'");
  assert.equal(run('metricsCounts().over'), 1, 'Lights against MAX_DLIGHTS');
  run("mset.metric = 'heap'; metricsUi()");
  // Drawing with the layer alone (no world-progress.json): two red cells, Bloodmoon outlined.
  calls.length = 0; run('draw()');
  const fills = calls.filter(c => c.op === 'fillRect');
  assert.equal(fills.filter(c => c.fill === HOT).length, 2);
  assert.equal(fills.filter(c => c.fill === SEQ[5]).length, 1, 'Bloodmoon region at 95 %');
  assert.equal(calls.filter(c => c.op === 'strokeRect' && c.stroke === '#000000').length, 1, 'One Bloodmoon cell outlined');
  const legend = element('legend').innerHTML;
  assert(legend.includes('&lt;= 50%') && legend.includes('&gt; 100% (over)') && legend.includes('Bloodmoon'), legend);
  assert(legend.includes(SEQ[0]) && legend.includes(HOT));
  element('layer-metrics').checked = false; run('metricsUi()');
  assert.equal(element('metricscount').textContent, '', 'Counts hidden with the layer off');
  calls.length = 0; run('draw()');
  assert.equal(calls.filter(c => c.op === 'fillRect' && c.fill === HOT).length, 0, 'Nothing drawn with the layer off');
  element('layer-metrics').checked = true; run('metricsUi()');
  console.log('PASS metrics colours and counts: chart scale and legend, over-budget counts per metric, content and texinfo limit, layer without world-progress, off draws nothing.');

  // 3. Hover tooltip and the clicked cell's region panel with 3D links.
  const tip = run("metricsTip(0, 0, '\\n')");
  assert.match(tip, /^Map metrics \(everything\): worst estimated map heap 11\.53 MB, 100% of budget\nin region w000 of 2$/);
  assert.equal(run("describe(0, 0, undefined, '\\n')").split('\n')[0], 'cell 0, 0');
  assert.match(run("describe(0, 0, undefined, '\\n')"), /\nMap metrics/);
  assert.equal(run('metricsTip(7, 7, " ")'), '', 'No tip outside the layer');
  run('servedMaps = new Set(["w000"])');
  run('showMetricsCell(0, 0)');
  const panel = element('metricspanel').innerHTML;
  assert.equal(element('metricspanel').hidden, false);
  assert(panel.includes('cell 0, 0') && panel.includes('2 sub-cell regions'), panel);
  assert(panel.includes('<td class="l">w000</td>') && panel.includes('<td class="l">w001</td>'));
  assert(panel.includes('<button data-map="w000"'), 'Built map gets a 3D button');
  assert(!panel.includes('data-map="w001"'), 'No 3D button without a map');
  assert((panel.match(/class="worst"/g) || []).length >= 11, 'The worst region is marked per metric');
  assert(panel.includes('11.53 MB') && panel.includes('100%'), 'Values with their share of the limit');
  run('showMetricsCell(9, 9)');
  assert.match(element('metricspanel').innerHTML, /No estimated region/);
  run('showMetricsCell(0, 0)');
  console.log('PASS metrics hover and panel: tooltip with cell and worst value, region table with every metric, worst marked, 3D link only for available maps.');

  // 4. Interiors table: sets, over-limit filter, sorting.
  element('ifset').value = ''; element('ifover').value = 'all'; element('ifname').value = '';
  element('interiorsview').hidden = true; element('interiorsbtn').onclick();
  assert.equal(element('interiorsview').hidden, false);
  const rows = () => (element('interiorstable').innerHTML.match(/<tr><td/g) || []).length;
  assert.equal(rows(), 2);
  assert(element('interiorstable').innerHTML.indexOf('i0001') < element('interiorstable').innerHTML.indexOf('ti0001'), 'Heaviest first');
  element('ifset').value = 'tribunal'; element('ifset').onchange();
  assert.equal(rows(), 1); assert(element('interiorstable').innerHTML.includes('ti0001'));
  element('ifset').value = ''; element('ifover').value = 'any'; element('ifover').onchange();
  assert.equal(rows(), 1); assert(element('interiorstable').innerHTML.includes('>i0001<'));
  element('ifover').value = 'metric'; element('ifover').onchange();
  assert.equal(rows(), 1);
  run("mset.mode = 'cur'"); run('renderInteriors()');
  assert.equal(rows(), 0, 'Current content interior under budget');
  run("mset.mode = 'evr'"); element('ifover').value = 'all'; element('ifname').value = 'ti0'; element('ifname').oninput();
  assert.equal(rows(), 1);
  element('ifname').value = '';
  element('interiorstable').onclick({target: {closest: () => ({dataset: {key: 'name'}})}});
  assert.equal(run('mset.sort.key'), 'name'); assert.equal(run('mset.sort.dir'), 1);
  element('interiorstable').onclick({target: {closest: () => ({dataset: {key: 'name'}})}});
  assert.equal(run('mset.sort.dir'), -1, 'Second click reverses');
  assert(element('interiorstable').innerHTML.indexOf('ti0001') < element('interiorstable').innerHTML.indexOf('>i0001<'));
  assert.match(element('ifcount').textContent, /^2 of 2 interiors/);
  console.log('PASS metrics interiors table: set and name filters, over any / selected limit, current vs everything, sortable both ways.');

  // 5. Copy state carries the layer and the selection.
  run('metricPick = {x: 0, y: 0}');
  const state = JSON.parse(run('JSON.stringify(stateJson())'));
  assert.equal(state.data.metrics.format, 'aw-world-metrics-1');
  assert.equal(state.data.metrics.cells, 3);
  assert.equal(state.map_metrics.metric, 'heap');
  assert.equal(state.map_metrics.content, 'evr');
  assert.equal(state.map_metrics.counts.over, 2);
  assert.deepEqual(state.map_metrics.cell.regions, ['w000', 'w001']);
  assert(state.layers_on.includes('metrics'));
  console.log('PASS metrics state: copy state names the layer, metric, content, counts and picked cell.');
})().catch(e => { console.error(e); process.exit(1); });
