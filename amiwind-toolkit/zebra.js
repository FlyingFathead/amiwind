// SPDX-License-Identifier: GPL-3.0-only
// The Toolkit's zebra fill: the 3D inspector's markup-zone tile (map-inspector.html, style.zebra: 12 x 12, the base
// colour crossed by two 4-pixel diagonal stripes) as a shared helper, used by the CHIM Progress Tracker's "awaiting
// lighting" cells (world-map.html). The inspector keeps its inline copy because it is exported as one standalone file
// (tools/export_mesh_inspection.py); tests/test_cell_progress.py checks that both draw the same tile.
// ZebraTile(base, stripe) returns the tile canvas; ZebraPattern(ctx, base, stripe) the repeating pattern for
// ctx.fillStyle. Default stripe: the inspector's grey.
(function () {
  const cache = new Map();
  function ZebraTile(base, stripe) {
    stripe = stripe || '#444b53';
    const tile = document.createElement('canvas'); tile.width = 12; tile.height = 12;
    const t = tile.getContext('2d');
    t.fillStyle = base; t.fillRect(0, 0, 12, 12);
    t.strokeStyle = stripe; t.lineWidth = 4;
    t.beginPath(); t.moveTo(-3, 12); t.lineTo(12, -3); t.moveTo(3, 15); t.lineTo(15, 3); t.stroke();
    return tile;
  }
  function ZebraPattern(ctx, base, stripe) {
    const key = base + '|' + (stripe || '');
    if (!cache.has(key)) cache.set(key, ZebraTile(base, stripe));
    return ctx.createPattern(cache.get(key), 'repeat');
  }
  window.ZebraTile = ZebraTile;
  window.ZebraPattern = ZebraPattern;
})();
