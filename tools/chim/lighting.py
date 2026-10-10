# SPDX-License-Identifier: GPL-3.0-only
"""CHIM lighting: measurements of the lighting options (docs/chim/LIGHTING.md) on a built CHIM world.

A CHIM world stores every model once and places it by reference, so per-placement light has a cost that a Quake
map does not show: a map bakes one lightmap per face of the world and of every brush entity, a CHIM ring holds one
copy of each model for all its placements. This module measures, per frame, what each option would add to the zone
ring the engine keeps locked (tools/chim/heap.py ring_peak, the engine's own rule), with the world's real faces:

  a   per-chunk terrain lightmaps + per-placement lightmaps for placed models (geometry shared, lightmaps per placement)
  b   per-chunk terrain lightmaps + one light sample per placement (as alias models: R_LightPoint), no model lightmaps
  c   per-chunk terrain lightmaps + per-placement vertex light (one byte per model vertex and placement)
  d   no stored light: dynamic lights for the nearest sources (0 bytes; per-frame cost instead)
  e   hybrid: terrain lightmaps + per-placement lightmaps only for placements a light source reaches (the others get
      the one light sample of b: sun and ambient need no lightmap on a flat face)

Lightmap size follows the engine (surface_grid: (extent / 16) + 1 samples per axis, one byte per sample and style).
Nothing here reads game data: the light placements come from the caller (tools/cell_lighting.py / light_sources.py).

Usage (inside the builder container):
  python3 -m chim.lighting measure WORLD_DIR --sdk SDK [--json OUT] [--styles N]
"""
import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from surface_grid import engine_grid, sample_dimensions  # noqa: E402

TEX_SPECIAL = 1
SAMPLE_BYTES = 1               # Quake lightmaps: one byte per sample and style
PLACEMENT_SAMPLE_BYTES = 4     # option b: light level, style, colour class, spare
VERTEX_BYTES = 1               # option c: one light byte per vertex and placement
OPTIONS = ('none', 'a', 'b', 'c', 'd', 'e')


def _a16(n):
    return (int(n) + 15) & ~15


def face_samples(lumps):
    """Lightmap samples of every face of a brush image (0 for special faces: sky, water), as the engine sizes them."""
    faces = list(struct.iter_unpack('<HhihH4Bi', bytes(lumps[7])))
    edges = list(struct.iter_unpack('<HH', bytes(lumps[12])))
    surfedges = [v[0] for v in struct.iter_unpack('<i', bytes(lumps[13]))]
    verts = np.frombuffer(bytes(lumps[3]), '<f4').reshape(-1, 3).astype(np.float64)
    out = np.zeros(len(faces), np.int64)
    for i, f in enumerate(faces):
        ti = f[4]
        vecs = np.array(struct.unpack_from('<8f', lumps[6], 40 * ti), np.float64).reshape(2, 4)
        flags = struct.unpack_from('<i', lumps[6], 40 * ti + 36)[0]
        if flags & TEX_SPECIAL:
            continue
        idx = [edges[e][0] if e >= 0 else edges[-e][1] for e in surfedges[f[2]:f[2] + f[3]]]
        _, ext = engine_grid(verts[idx], vecs)
        d = sample_dimensions(ext)
        out[i] = d[0] * d[1]
    return out


def reached(record, box_lights):
    """True when a light source's reach (2 x radius) touches the placement's stored box."""
    if not len(box_lights):
        return False
    o = np.asarray(record['origin'])
    lo = o + np.asarray(record['box'][0], float) - 1
    hi = o + np.asarray(record['box'][1], float) + 1
    c, r = box_lights[:, :3], box_lights[:, 3]
    d = np.maximum(np.maximum(lo - c, c - hi), 0)
    return bool(((d * d).sum(1) <= r * r).any())


def measure(world, sizes, styles=1, lights_of_frame=None):
    """Per frame and option: stored light bytes (whole frame) and the zone ring peaks with those bytes added
    (tools/chim/heap.py ring_peak with chunk_extra), against the same budget the heap gate uses."""
    from chim import format as F
    from chim.heap import ring_peak
    models = world['models']
    m_samples, m_faces, m_verts = [], [], []
    for m in models:
        lumps = F.read_brush_image(m['image'])
        s = face_samples(lumps)
        m_samples.append(int(s.sum()))
        m_faces.append(len(s))
        m_verts.append(len(lumps[3]) // 12)
    base = ring_peak(world, sizes)
    out = {'styles': styles, 'models': len(models), 'model_samples': int(sum(m_samples)),
           'model_faces': int(sum(m_faces)), 'frames': []}
    for (path, frame, chunks), fb in zip(world['frames'], base['frames']):
        cell = tuple(frame['cell'])
        fl = lights_of_frame(frame) if lights_of_frame else []
        box_lights = np.array([[*L['origin'], FADE * L['qradius']] for L in fl], float).reshape(-1, 4)
        reached_placements = 0
        terr = {}
        per = {o: {} for o in OPTIONS}
        placements = 0
        stored = {o: 0 for o in OPTIONS}
        terrain_samples = 0
        model_placement_samples = 0
        for c in chunks:
            lumps = F.read_brush_image(c['image'])
            ts = face_samples(lumps)
            shared = len(lumps[8])                       # today's one shared block
            tbytes = _a16(int(ts.sum()) * SAMPLE_BYTES * styles) - _a16(shared)
            terrain_samples += int(ts.sum())
            terr[c['index']] = max(0, tbytes)
            owned = c['owned']
            placements += len(owned)
            pa = sum(m_samples[r['model']] for r in owned) * SAMPLE_BYTES * styles
            model_placement_samples += sum(m_samples[r['model']] for r in owned)
            pc = sum(m_verts[r['model']] for r in owned) * VERTEX_BYTES
            pb = len(owned) * PLACEMENT_SAMPLE_BYTES
            # per-placement light data is its own block per placement (header + data) in option a and c
            hdr = sizes.get('hunk', 16)
            per['a'][c['index']] = terr[c['index']] + sum(_a16(m_samples[r['model']] * styles) + hdr for r in owned)
            per['b'][c['index']] = terr[c['index']] + _a16(pb)
            per['c'][c['index']] = terr[c['index']] + sum(_a16(m_verts[r['model']]) + hdr for r in owned)
            per['d'][c['index']] = 0
            hit = [r for r in owned if reached(r, box_lights)]
            reached_placements += len(hit)
            per['e'][c['index']] = (terr[c['index']] + sum(_a16(m_samples[r['model']] * styles) + hdr for r in hit)
                                    + _a16((len(owned) - len(hit)) * PLACEMENT_SAMPLE_BYTES))
            stored['e'] += (tbytes + sum(m_samples[r['model']] for r in hit) * SAMPLE_BYTES * styles
                            + (len(owned) - len(hit)) * PLACEMENT_SAMPLE_BYTES)
            stored['a'] += tbytes + pa
            stored['b'] += tbytes + pb
            stored['c'] += tbytes + pc
        row = {'frame': path, 'cell': list(cell), 'chunks': len(chunks), 'placements': placements,
               'terrain_samples': terrain_samples, 'placement_model_samples': model_placement_samples,
               'budget_bytes': fb['budget_bytes'], 'lights': len(fl), 'placements_reached_by_a_light': reached_placements,
               'options': {}}
        for o in OPTIONS:
            if o == 'none':
                r = fb
            else:
                one = dict(world, frames=[(path, frame, chunks)])
                r = ring_peak(one, sizes, chunk_extra={cell: per[o]})['frames'][0]
            row['options'][o] = {'stored_bytes': stored[o], 'active_peak_bytes': r['peak_bytes'],
                                 'active_headroom_bytes': r['headroom_bytes'],
                                 'load_peak_bytes': r['load_ring']['peak_bytes'],
                                 'load_headroom_bytes': r['load_ring']['headroom_bytes'],
                                 'positions_over_budget': r['positions_over_budget'],
                                 'positions': r['positions']}
        out['frames'].append(row)
    return out


# ---------------------------------------------------------------- the light sources and the bake

SCALE = 0.25                   # Morrowind units to CHIM / Quake units (prepare_quake.SCALE)
FADE = 2.0                     # the original fades a light from its radius to twice its radius (no light beyond)


def frame_lights(lights, frame):
    """The lights of a frame in frame-local Quake units: lights = [{pos (Morrowind units), radius, colour, class,
    style, mesh}] (light_sources.py records, placed); keeps the lights whose reach (2 x radius) touches the frame."""
    cx, cy = frame['centre']
    lx, ly = frame['low']
    hx, hy = lx + frame['nx'] * frame['grain'], ly + frame['ny'] * frame['grain']
    out = []
    for L in lights:
        if L['class'] == 'off':
            continue
        x, y, z = ((L['pos'][0] - cx) * SCALE, (L['pos'][1] - cy) * SCALE, L['pos'][2] * SCALE)
        r = max(16, L['radius']) * SCALE
        if lx - FADE * r <= x <= hx + FADE * r and ly - FADE * r <= y <= hy + FADE * r:
            out.append(dict(L, origin=(x, y, z), qradius=r))
    return out


def face_sample_points(lumps):
    """[(face index, normal, sample points (N x 3))] of the lit faces of a brush image: the engine's lightmap grid
    (texturemins + 16 * i) mapped back onto the face plane, as the light compiler places its samples."""
    faces = list(struct.iter_unpack('<HhihH4Bi', bytes(lumps[7])))
    edges = list(struct.iter_unpack('<HH', bytes(lumps[12])))
    surfedges = [v[0] for v in struct.iter_unpack('<i', bytes(lumps[13]))]
    verts = np.frombuffer(bytes(lumps[3]), '<f4').reshape(-1, 3).astype(np.float64)
    planes = np.frombuffer(bytes(lumps[1]), '<f4').reshape(-1, 5)[:, :4].astype(np.float64)
    out = []
    for i, f in enumerate(faces):
        plane, side, ti = f[0], f[1], f[4]
        vecs = np.array(struct.unpack_from('<8f', lumps[6], 40 * ti), np.float64).reshape(2, 4)
        if struct.unpack_from('<i', lumps[6], 40 * ti + 36)[0] & TEX_SPECIAL:
            continue
        idx = [edges[e][0] if e >= 0 else edges[-e][1] for e in surfedges[f[2]:f[2] + f[3]]]
        mins, ext = engine_grid(verts[idx], vecs)
        w, h = sample_dimensions(ext)
        n, d = planes[plane, :3], planes[plane, 3]
        if side:
            n, d = -n, -d
        A = np.array([vecs[0, :3], vecs[1, :3], n])
        if abs(np.linalg.det(A)) < 1e-9:
            continue
        s = mins[0] + 16.0 * np.arange(w) - vecs[0, 3]
        t = mins[1] + 16.0 * np.arange(h) - vecs[1, 3]
        S, T = np.meshgrid(s, t)
        rhs = np.stack([S.ravel(), T.ravel(), np.full(S.size, d)], axis=1)
        out.append((i, n, np.linalg.solve(A, rhs.T).T))
    return out


def illumination(points, normals, lights):
    """Original light of each point (0..): sum over lights of colour luminance x N.L x 1 / (3 d / r), faded to 0
    between r and 2 r (OpenMW 0.51 defaults: linear attenuation 3 / radius, smooth cut-off); negative lights subtract.
    points (N x 3), normals (N x 3) or one normal. Returns (steady, animated) arrays (animated: lights with a style)."""
    steady = np.zeros(len(points))
    moving = np.zeros(len(points))
    for L in lights:
        o = np.asarray(L['origin'])
        v = o - points
        dist = np.sqrt((v * v).sum(1))
        r = L['qradius']
        near = dist < FADE * r
        if not near.any():
            continue
        dn = np.maximum(dist[near], 1e-3)
        nl = (v[near] * (normals[near] if normals.ndim == 2 else normals)).sum(1) / dn
        lam = np.clip(nl, 0, 1)
        illum = np.minimum(1.0, r / (3.0 * dn))
        x = np.clip(dn / r - 1.0, 0, 1)
        illum *= 1.0 - (1.0 - (1.0 - x * x) ** 2)
        c = np.asarray(L['colour'], float) / 255.0
        lum = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
        val = lum * lam * illum * (-1 if L['class'] == 'negative' else 1)
        (moving if L.get('style') not in (0, None) and L['class'] != 'negative' else steady)[near] += val
    return steady, moving


def exterior_lights(raw):
    """Every placed exterior light of a master: [{pos, radius, colour, class, style, flags, mesh}] (light_sources.py)."""
    from light_sources import light_records, placements, quake_style
    recs = light_records(raw)
    out = []
    for key, ident, pos in placements(raw, recs):
        if key[0] != 'exterior':
            continue
        L = recs[ident]
        out.append({'pos': tuple(pos), 'radius': L['radius'], 'colour': L['colour'], 'class': L['class'],
                    'flags': L['flags'], 'style': quake_style(L['class'], L['flags'], True), 'mesh': bool(L['model']),
                    'cell': key[1:]})
    return out


def bake_work(world, lights_of_frame):
    """Per frame: how many lights, terrain samples and placed-model samples (option a) fall within the reach of a
    light, and the time this module takes to light them (numpy, no shadows: the measure of option a/b bake cost)."""
    import time
    from chim import format as F
    models = world['models']
    model_pts = {}
    rows = []
    for path, frame, chunks in world['frames']:
        lights = lights_of_frame(frame)
        t0 = time.perf_counter()
        terrain = lit = 0
        for c in chunks:
            for _, n, pts in face_sample_points(F.read_brush_image(c['image'])):
                s, m = illumination(pts, n, lights)
                terrain += len(pts)
                lit += int(((s + m) > 0.004).sum())
        t_terrain = time.perf_counter() - t0
        t0 = time.perf_counter()
        placed = placed_lit = 0
        for c in chunks:
            for r in c['owned']:
                mi = r['model']
                if mi not in model_pts:
                    model_pts[mi] = face_sample_points(F.read_brush_image(models[mi]['image']))
                yaw = np.radians(r['yaw'])
                R = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
                o = np.asarray(r['origin'])
                for _, n, pts in model_pts[mi]:
                    s, m = illumination(pts @ R.T + o, R @ n, lights)
                    placed += len(pts)
                    placed_lit += int(((s + m) > 0.004).sum())
        rows.append({'frame': path, 'lights': len(lights),
                     'by_class': {k: sum(1 for L in lights if L['class'] == k) for k in sorted({L['class'] for L in lights})},
                     'terrain_samples': terrain, 'terrain_samples_lit_by_sources': lit, 'terrain_bake_s': round(t_terrain, 2),
                     'placed_samples': placed, 'placed_samples_lit_by_sources': placed_lit,
                     'placed_bake_s': round(time.perf_counter() - t0, 2)})
    return rows


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('measure')
    m.add_argument('world', type=Path)
    m.add_argument('--sdk', type=Path, required=True)
    m.add_argument('--styles', type=int, default=1, help='light styles per face (1 = steady only)')
    m.add_argument('--json', type=Path)
    m.add_argument('--master', type=Path, help='your own Morrowind.esm (option e: which placements a light reaches)')
    w = sub.add_parser('bakework', help='lights per frame and the time to light every terrain and placed-model sample')
    w.add_argument('world', type=Path)
    w.add_argument('--master', type=Path, required=True, help='your own Morrowind.esm')
    w.add_argument('--json', type=Path)
    a = p.parse_args(argv)
    if a.cmd == 'bakework':
        from chim.validate import Failures, load_world
        fails = Failures()
        settings, files, disk, textures, models, frames = load_world(a.world, fails)
        lights = exterior_lights(a.master.read_bytes())
        rows = bake_work({'models': models, 'frames': frames}, lambda fr: frame_lights(lights, fr))
        text = json.dumps(rows, indent=1, sort_keys=True) + '\n'
        if a.json:
            a.json.write_bytes(text.encode('utf-8'))
        sys.stdout.write(text)
        return 0
    from check_world_map_heap import compile_target_sizes
    from chim.validate import Failures, load_world
    sizes = compile_target_sizes(a.sdk)[0]
    fails = Failures()
    settings, files, disk, textures, models, frames = load_world(a.world, fails)
    if fails:
        raise SystemExit('world does not read back: %s' % fails[0])
    lights = exterior_lights(a.master.read_bytes()) if a.master else None
    rep = measure({'settings': settings, 'textures': textures, 'models': models, 'frames': frames}, sizes, a.styles,
                  (lambda fr: frame_lights(lights, fr)) if lights else None)
    text = json.dumps(rep, indent=1, sort_keys=True) + '\n'
    if a.json:
        a.json.write_bytes(text.encode('utf-8'))
    sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
