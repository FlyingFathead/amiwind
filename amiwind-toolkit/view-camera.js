// SPDX-License-Identifier: GPL-3.0-only
// The Toolkit's shared 3D view controls: the 3D Map Inspector and Mesh Compare move the same way.
//   orbit(eye, pivot, dx, dy)      the Inspector's orbit: drag turns the eye around the pivot (azimuth and elevation)
//   aim(eye, pivot)                yaw and pitch that look from the eye at the pivot
//   basis(yaw, pitch)              forward, right and up of a view
//   zoomFocal(focal, deltaY)       the wheel: the Inspector's field-of-view zoom (position unchanged)
//   dolly(eye, pivot, dy)          middle-button drag: closer to or farther from the pivot
//   pan(eye, pivot, b, dx, dy, k)  move eye and pivot together along the view's right and up
//   Movement speed for WASD / arrow flying: a slider factor (0.05x to 4x, logarithmic, default 1x) times a base
//   speed from the size of what is loaded, so a small room is not twitchy and a town frame is not slow;
//   Shift = 4x faster, Ctrl or Alt = 4x slower while held. The factor is remembered per browser.
(function (root) {
  'use strict';
  const add = (a, b) => a.map((v, i) => v + b[i]), sub = (a, b) => a.map((v, i) => v - b[i]), mul = (a, s) => a.map(v => v * s);
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const norm = a => mul(a, 1 / (Math.hypot(...a) || 1));
  const ORBIT_RATE = 0.008, SPEED_MIN = 0.05, SPEED_MAX = 4, SLIDER_MAX = 1000, FAST = 4, SLOW = 0.25;
  const STORE = 'amiwind-toolkit-move-speed';
  function basis(yaw, pitch) {
    const f = [Math.cos(pitch) * Math.cos(yaw), Math.cos(pitch) * Math.sin(yaw), Math.sin(pitch)], r = [Math.sin(yaw), -Math.cos(yaw), 0];
    return {f, r, u: cross(r, f)};
  }
  function aim(eye, pivot) {
    const f = norm(sub(pivot, eye));
    return {yaw: Math.atan2(f[1], f[0]), pitch: Math.asin(Math.max(-1, Math.min(1, f[2])))};
  }
  function orbit(eye, pivot, dx, dy) {
    const offset = sub(eye, pivot), radius = Math.max(0.1, Math.hypot(...offset));
    const azimuth = Math.atan2(offset[1], offset[0]) - dx * ORBIT_RATE;
    const elevation = Math.max(-Math.PI / 2 + 0.001, Math.min(Math.PI / 2 - 0.001, Math.atan2(offset[2], Math.hypot(offset[0], offset[1])) + dy * ORBIT_RATE));
    const out = add(pivot, [radius * Math.cos(elevation) * Math.cos(azimuth), radius * Math.cos(elevation) * Math.sin(azimuth), radius * Math.sin(elevation)]);
    return Object.assign({eye: out}, aim(out, pivot));
  }
  function zoomFocal(focal, deltaY) { return Math.max(0.65, Math.min(6, focal * Math.exp(-deltaY * 0.001))); }
  function dolly(eye, pivot, dy) {
    const offset = sub(eye, pivot), radius = Math.max(0.1, Math.hypot(...offset)), next = Math.max(0.1, radius * Math.exp(dy * 0.005));
    return add(pivot, mul(offset, next / radius));
  }
  function pan(eye, pivot, b, dx, dy, k) {
    const shift = add(mul(b.r, -dx * k), mul(b.u, dy * k));
    return {eye: add(eye, shift), pivot: add(pivot, shift)};
  }
  // speed: slider position 0..SLIDER_MAX <-> factor SPEED_MIN..SPEED_MAX, logarithmic
  function factorOf(slider) {
    const s = Math.max(0, Math.min(SLIDER_MAX, Number(slider)));
    return SPEED_MIN * Math.pow(SPEED_MAX / SPEED_MIN, s / SLIDER_MAX);
  }
  function sliderOf(factor) {
    const f = Math.max(SPEED_MIN, Math.min(SPEED_MAX, Number(factor) || 1));
    return SLIDER_MAX * Math.log(f / SPEED_MIN) / Math.log(SPEED_MAX / SPEED_MIN);
  }
  // units per second at 1x for something of this size (the diagonal of its bounds): about 1/12 of it per second
  function baseSpeed(lo, hi) {
    if (!lo || !hi) return 200;
    const d = Math.hypot(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]);
    return Number.isFinite(d) && d > 0 ? Math.max(4, Math.min(1600, d / 12)) : 200;
  }
  function keySpeed(base, factor, mods) {
    mods = mods || {};
    return base * factor * (mods.fast ? FAST : 1) * (mods.slow ? SLOW : 1);
  }
  function loadFactor() {
    try { const v = Number(root.localStorage && root.localStorage.getItem(STORE)); return v >= SPEED_MIN && v <= SPEED_MAX ? v : 1; } catch (e) { return 1; }
  }
  function saveFactor(f) { try { if (root.localStorage) root.localStorage.setItem(STORE, String(f)); } catch (e) { /* private mode: not remembered */ } }
  function label(f) { return '×' + (f < 0.1 ? f.toFixed(3) : f.toFixed(2)); }
  const api = {basis, aim, orbit, zoomFocal, dolly, pan, factorOf, sliderOf, baseSpeed, keySpeed, loadFactor, saveFactor, label,
    SPEED_MIN, SPEED_MAX, SLIDER_MAX, FAST, SLOW};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AmiWindViewCamera = api;
})(typeof self !== 'undefined' ? self : this);
