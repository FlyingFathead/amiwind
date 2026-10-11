// SPDX-License-Identifier: GPL-3.0-only
// The Toolkit Monitor page (amiwind-toolkit/monitor.html) on a sample run, for tests/test_toolkit_monitor.py:
//   node tests/test_toolkit_monitor.js amiwind-toolkit/monitor.html answers.json
// answers.json maps endpoint paths (without the query) to the server's answers. DOM stubbed: no browser claim.
'use strict';
const fs = require('fs'), vm = require('vm');
const [htmlFile, answersFile] = process.argv.slice(2);
const answers = JSON.parse(fs.readFileSync(answersFile, 'utf8'));
const elements = new Map(), requested = [];
function node(tag) {
  return {tag, textContent: '', className: '', value: '', checked: false, hidden: false, style: {}, children: [], title: '',
    scrollTop: 0, clientHeight: 100, get scrollHeight() { return this.textContent.length; }, innerHTML: '',
    get options() { return this.children; },
    append(...c) { this.children.push(...c); if (this.tag === 'select' && !this.value && c[0]) this.value = c[0].value; },
    replaceChildren(...c) { this.children = c; }, setAttribute(k, v) { this[k] = v; }, addEventListener() {}};
}
function element(id) {
  if (!elements.has(id)) {
    const e = node(['run', 'logpick'].includes(id) ? 'select' : 'div');
    if (id === 'follow') e.checked = true;
    elements.set(id, e);
  }
  return elements.get(id);
}
const context = vm.createContext({console, JSON, Math, Date, Number, String, Array, Object, Error, Infinity, NaN, Promise,
  URLSearchParams, URL, Float64Array,
  location: {href: 'http://127.0.0.1/amiwind-toolkit/monitor.html', search: ''},
  history: {replaceState() {}},
  document: {hidden: false, getElementById: element, createElement: node, addEventListener() {}},
  window: {}, setTimeout() { return 0; }, clearTimeout() {},
  fetch: async path => {
    requested.push(path);
    const key = path.split('?')[0], offset = Number((/[?&]offset=(-?\d+)/.exec(path) || [])[1]);
    let body = answers[key] || {ok: false, error: 'not in the sample'};
    // a range read from the end of the sample answers nothing new, as the server does for a log that did not grow
    if (body.ok && Number.isFinite(body.next) && offset >= body.next) body = Object.assign({}, body, {offset, next: offset, text: ''});
    return {json: async () => JSON.parse(JSON.stringify(body))};
  }});
const html = fs.readFileSync(htmlFile, 'utf8');
vm.runInContext(html.split(/<script>\s*/)[1].split('</script>')[0], context);
setTimeout(async () => {
  const facts = element('facts').children.map(c => c.textContent).join(' | ');
  const out = {status: element('status').textContent, facts, stages: element('stages').children.length,
    log: vm.runInContext('S.log', context), text: element('log').textContent,
    methods: requested.length, results: element('results').children.length,
    timeline: element('timelinenote').textContent, chart: element('timelinechart').innerHTML};
  // red stretches: under 2.5 cores held 30 s or more
  out.red = JSON.parse(vm.runInContext('JSON.stringify(redStretches([[0,1],[10,2],[40,1],[50,5],[60,2],[70,2],[80,6],[90,1],[100,1],[130,1]],2.5,30))', context));
  // a finished-run timeline with a red stretch: select it, then fullscreen on and off (the overlay fallback)
  vm.runInContext('renderTimeline([{name:"chim",status:"passed",start:0,end:200}],{cores:[[0,1],[10,1],[60,1],[70,9],[200,9]],now:200,label:"t"})', context);
  out.redLine = element('timelinechart').innerHTML.includes('stroke="#ff4040"');
  out.sel = JSON.parse(vm.runInContext('JSON.stringify(selectStretch(0))', context));
  out.detail = element('timelinedetail').textContent;
  out.highlight = element('timelinechart').innerHTML.includes('#ffe28a');
  out.full1 = vm.runInContext('toggleFullscreen()', context);
  out.fullClass = element('timeline').className;
  out.full2 = vm.runInContext('toggleFullscreen()', context);
  out.fullClassAfter = element('timeline').className;
  out.hover = vm.runInContext('S.tlGeom ? hoverAt(4 + (S.tlGeom.W - 8) * 30 / 200) : ""', context);
  // the run list read again: a new run is marked, the selection stays
  answers['/monitor/runs.json'] = {ok: true, runs: [{run: '2026_10_11_v0.0.36-dev3_miniwind-vivec-stage-a_abc1234', mtime: 9e9, progress: false},
    ...(answers['/monitor/runs.json'].runs || [])]};
  await vm.runInContext('refreshRuns()', context);
  out.runOptions = element('run').options.map(o => o.textContent);
  out.runValue = element('run').value;
  process.stdout.write(JSON.stringify(out) + '\n');
}, 300);
