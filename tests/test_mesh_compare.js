// SPDX-License-Identifier: GPL-3.0-only
// Mesh Compare (amiwind-toolkit/mesh-compare.html) on a synthetic .OBJ, for tests/test_mesh_compare.py:
//   node tests/test_mesh_compare.js amiwind-toolkit/mesh-compare.html cube.obj
// DOM and WebGL stubbed (draw calls recorded): no browser claim.
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');
const [htmlFile, objFile] = process.argv.slice(2);
const obj = fs.readFileSync(objFile, 'utf8');
const draws = [];
function fakeGL(tag) {
  const gl = {
    getProgramParameter: () => true, getProgramInfoLog: () => '', getAttribLocation: (p, n) => n, getUniformLocation: (p, n) => n,
    uniform3fv: (n, v) => { if (n === 'eye') draws.push({tag, kind: 'eye', v: Array.from(v)}); },
    drawArrays: (mode, first, count) => draws.push({tag, kind: 'draw', mode, count})};
  return new Proxy(gl, {get: (t, k) => k in t ? t[k] : (typeof k === 'string' && /^[A-Z_]+$/.test(k) ? k : () => ({}))});
}
const elements = new Map();
function node(tag, id) {
  return {tag, id, textContent: '', innerHTML: '', value: '', checked: false, style: {}, dataset: {}, children: [],
    clientWidth: 400, clientHeight: 300, width: 0, height: 0, type: '', files: null,
    get options() { return this.children; },
    append(...c) { this.children.push(...c); }, replaceChildren(...c) { this.children = c; },
    addEventListener() {}, focus() {}, setAttribute(k, v) { this[k] = v; },
    getContext() { return tag === 'canvas' ? fakeGL(id) : null; }};
}
function element(id) {
  if (!elements.has(id)) elements.set(id, node(/^canvas/.test(id) ? 'canvas' : 'div', id));
  return elements.get(id);
}
element('speed').value = '683.67';
const context = vm.createContext({console, JSON, Math, Number, String, Array, Object, Error, Infinity, NaN, Promise, Set, Map,
  Float32Array, RegExp, parseInt, encodeURIComponent,
  location: {protocol: 'file:', search: ''}, window: {},
  document: {getElementById: element, createElement: t => node(t), addEventListener() {}},
  fetch: async () => { throw Error('no server in this test'); }});
vm.runInContext(fs.readFileSync(path.join(path.dirname(htmlFile), 'view-camera.js'), 'utf8'), context);
const html = fs.readFileSync(htmlFile, 'utf8');
vm.runInContext(html.split(/<script>\s*/)[1].split('</script>')[0], context);
context.OBJ = obj;
const run = code => vm.runInContext(code, context);
const out = {};
const m = JSON.parse(run('JSON.stringify((()=>{const m=parseOBJ(OBJ);return {faces:m.faceCount,vertices:m.vertexCount,triangles:m.triangles,bad:m.bad};})())'));
Object.assign(out, m);
run("showMesh(views[0],OBJ,'A');showMesh(views[1],OBJ,'B')");
out.countsA = Object.assign({}, element('countsA').dataset);
out.countsB = Object.assign({}, element('countsB').dataset);
out.edges = run('meshArrays(parseOBJ(OBJ)).edges.length/6');
out.pivotAfterReset = run('cam.pivot.slice()');
const lines = () => draws.filter(d => d.kind === 'draw' && d.mode === 'LINES').length;
draws.length = 0; run('drawAll()');
const eyes = draws.filter(d => d.kind === 'eye');
out.linked = eyes.length === 2 && eyes[0].tag !== eyes[1].tag && JSON.stringify(eyes[0].v) === JSON.stringify(eyes[1].v);
out.linesOff = lines();
element('wire').checked = true;
draws.length = 0; run('drawAll()');
out.linesOn = lines();
// WASD flight: one second of W at the slider's factor times the size-scaled base speed; Alt held = 4x slower
out.expectedFlight = run("VC().keySpeed(moveBase,VC().factorOf(document.getElementById('speed').value),{})");
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
let e0 = run('cam.eye.slice()');
run("keys.add('w');flyStep(1)");
out.flown = dist(e0, run('cam.eye.slice()'));
e0 = run('cam.eye.slice()');
run("keys.add('alt');flyStep(1);keys.clear()");
out.flownSlow = dist(e0, run('cam.eye.slice()'));
// the Inspector's mouse: orbit keeps the distance to the pivot, middle-drag dollies closer, pan moves eye and pivot together
run('resetView()');
const r0 = run('Math.hypot(...cam.eye.map((v,i)=>v-cam.pivot[i]))'), before = run('cam.eye.slice()');
run('orbitBy(40,15)');
out.orbitMoved = dist(before, run('cam.eye.slice()')) > 1e-6;
out.orbitRadius = [r0, run('Math.hypot(...cam.eye.map((v,i)=>v-cam.pivot[i]))')];
run('dollyBy(-100)');
out.dollied = run('Math.hypot(...cam.eye.map((v,i)=>v-cam.pivot[i]))');
const off0 = run('cam.eye.map((v,i)=>v-cam.pivot[i])'), p0 = run('cam.pivot.slice()');
run('panBy(30,-20,300)');
const off1 = run('cam.eye.map((v,i)=>v-cam.pivot[i])');
out.panKeptOffset = dist(off0, off1) < 1e-9 && dist(p0, run('cam.pivot.slice()')) > 1e-6;
process.stdout.write(JSON.stringify(out) + '\n');
