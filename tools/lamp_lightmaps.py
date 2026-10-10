#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Night-lamp lightmaps for placed exterior meshes on a switchable lightstyle.

Quake bakes light entities into lightmaps and switches them with lightstyles:
a surface is ambient + sum over its (up to four) maps of map * style value
(r_surf.c R_BuildLightMap). Exterior lamps use style 32
(light_sources.STYLE_NIGHT_LAMPS). Their maps hold lamp light only, with no
ambient base, so the style adds a warm pool around each lamp and every other
surface keeps its current ambient-only look.

Terrain is world geometry: the region's lamps go into the terrain map as Quake
light entities and the map light compiler bakes them on the same style.

Placed meshes are func_wall submodels shared by every placement of a model,
and a BSP face has one lightmap. A submodel per lit placement would exceed the
inline model budget, so lit placements reuse the render pool already used by
the exterior culling pass (aw_render_pool / aw_render_ranges, engine
aw_render_ranges.c): each lit placement's faces are copied once into the pool
with that placement's own lamp maps, and the placement draws its pool range
instead of the shared faces. Collision, bounds and entity identity stay.

The sample grid of every baked face is computed from the serialized float32
vertices and texture vectors as the engine's CalcSurfaceExtents does. A face
whose grid differs between strict binary32 and wide-intermediate arithmetic is
left without a lamp map rather than baked on a guessed grid.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

import numpy as np

from check_geometry_render_inputs import project, project_wide
from interior_lighting import bake_surface
from player_hull import lumps, pack_lumps
import light_sources

LOCAL_SCALE = 0.25  # bake_surface and the region conversion use 1/4 scale


def attach_offset(nif_bytes, reader):
    """Model-space AttachLight point (original units) or None. The original
    game ignores the root node rotation but keeps its translation and scale."""
    from io import BytesIO
    data = reader.Data(); data.read(BytesIO(nif_bytes))
    found = []

    def walk(node, parent, root):
        if not isinstance(node, reader.NiAVObject):
            return
        local = np.array(node.get_transform().as_list(), dtype=float)
        if root:
            scale = float(node.scale)
            local[:3, :3] = np.eye(3) * scale
        matrix = local @ parent
        if node.name.decode('cp1252').casefold() == 'attachlight':
            found.append(matrix[3, :3].copy())
        for child in getattr(node, 'children', []):
            if child:
                walk(child, matrix, False)
    for root in data.roots:
        walk(root, np.eye(4), True)
    if len(found) > 1:
        raise ValueError('Ambiguous AttachLight nodes')
    return found[0] if found else None


def region_lamps(master, coverage, settings, *, classes=('lamp',), attach=None, references=()):
    """Exterior LIGH placements whose reach (2 radius) touches the coverage.

    Returns dicts in local compiled units: position, radius, colour, style.
    attach maps a lowercase model path to its AttachLight offset (or None);
    without one the light sits at the placement's bounds centre (references
    from the scenery index) or, for a model-less light, at the placement."""
    lights = light_sources.light_records(master)
    centre, scale = settings['centre'], settings['scale']
    attach = attach or {}
    by_position = {tuple(round(v, 2) for v in r['position']): r for r in references}
    out = []
    for key, identifier, position in light_sources.placements(master, lights):
        light = lights[identifier]
        if key[0] != 'exterior' or light['class'] not in classes:
            continue
        local = np.array([(position[0] - centre[0]) * scale, (position[1] - centre[1]) * scale, position[2] * scale])
        reach = 2 * light['radius'] * scale
        if not all(coverage[0][i] - reach <= local[i] <= coverage[1][i] + reach for i in range(2)):
            continue
        ref = by_position.get(tuple(round(v, 2) for v in position))
        model = light['model'].replace('\\', '/').casefold()
        source = np.array(position, dtype=float)
        offset = attach.get(model)
        if offset is not None:
            if ref is None:
                raise ValueError('AttachLight lamp without a converted placement: ' + identifier)
            from prepare_scenery import reference_rotation
            source = source + reference_rotation(ref) @ (np.asarray(offset) * ref['scale'])
            where = 'attachlight'
        elif ref is not None and light['model']:
            source = np.mean(np.array(ref['bounds'], dtype=float), axis=0)
            where = 'bounds_centre'
        else:
            where = 'placement'
        local = np.array([(source[0] - centre[0]) * scale, (source[1] - centre[1]) * scale, source[2] * scale])
        out.append({'id': light['id'], 'class': light['class'], 'number': ref['number'] if ref else None,
                    'position': local.tolist(), 'source_position': source.tolist(), 'placed_at': where,
                    'radius': light['radius'] * scale, 'colour': light['colour'], 'flags': light['flags'],
                    'style': light_sources.quake_style(light['class'], light['flags'], True)})
    return out


# ericw light keys fitted to the mesh bake (original falloff, N.L): the 1/x
# entity default reaches every terrain face in the region (measured on bm019:
# 1,436 of 2,352 faces, lit 1,500 units from the nearest lamp). Linear falloff
# to 1.757 r with light 300 and pure cosine matches the original-falloff means
# on bm019 terrain within ~10 % in the 45-112 unit bands (out/calib-D).
ORIGINAL_FIT = {'delay': '0', '_anglescale': '1', 'light': '300',
                '_falloff': lambda lamp: '%.1f' % (1.757 * lamp['radius'])}


def terrain_entities(lamps, settings, extra=None, coverage=None):
    """Light entity text for the terrain map (light_sources.entity) with the
    original source position; extra replaces or adds compiler keys (a value
    may be a function of the lamp). A point entity outside the sealed coverage
    box would leak the map, so lamps outside coverage are left out."""
    texts = []
    for lamp in lamps:
        if coverage and not all(coverage[0][i] < lamp['position'][i] < coverage[1][i] for i in range(2)):
            continue
        record = {'class': lamp['class'], 'radius': lamp['radius'] / settings['scale'],
                  'colour': lamp['colour'], 'flags': lamp['flags']}
        text = light_sources.entity(record, lamp['source_position'], centre=settings['centre'],
                                    scale=settings['scale'], exterior=True)
        for key, value in (extra or {}).items():
            line = '"%s" "%s"\n' % (key, value(lamp) if callable(value) else value)
            pattern = re.compile(r'^"%s" "[^"\n]*"\n' % re.escape(key), re.M)
            if pattern.search(text):
                text = pattern.sub(lambda match: line, text)
            else:
                text = text[:-1] + line + '}'
        texts.append(text)
    return texts


def strip_light_entities(entity_lump):
    """Light entities are compiler input; the runtime spawns no 'light'."""
    text = bytes(entity_lump).rstrip(b'\0').decode('latin-1')
    kept = [b for b in re.findall(r'\{[^{}]*\}', text) if not re.search(r'"classname"\s+"light"', b)]
    return ('\n'.join(kept) + '\n\0').encode('latin-1')


def engine_grid(points, vecs):
    """CalcSurfaceExtents grid (texturemins, sample size) of a face from its
    float32 vertices and texture vectors, or None when strict binary32 and
    wide-intermediate arithmetic disagree."""
    grids = []
    for policy in (project, project_wide):
        uv = [[policy(p, v) for v in vecs] for p in points]
        low = [math.floor(min(999999.0, *(u[a] for u in uv)) / 16) for a in (0, 1)]
        high = [math.ceil(max(-99999.0, *(u[a] for u in uv)) / 16) for a in (0, 1)]
        extent = [max(16, (high[a] - low[a]) * 16) for a in (0, 1)]
        grids.append((tuple(v * 16 for v in low), tuple((e >> 4) + 1 for e in extent)))
    return grids[0] if grids[0] == grids[1] else None


def polygon_distance(point, polygon, normal):
    """Distance from a point to a convex planar polygon."""
    d = float(normal @ (point - polygon[0]))
    foot = point - d * normal
    inside = True
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
        if np.cross(b - a, foot - a) @ normal < -1e-9:
            inside = False
            break
    if inside:
        return abs(d)
    best = math.inf
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
        e = b - a
        t = 0.0 if not e @ e else min(1.0, max(0.0, float((point - a) @ e / (e @ e))))
        best = min(best, float(np.linalg.norm(point - (a + t * e))))
    return best


def _parse(raw):
    data = lumps(raw)
    text = bytes(data[0]).rstrip(b'\0').decode('latin-1')
    blocks = re.findall(r'\{[^{}]*\}', text)
    records = [dict(re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"', b)) for b in blocks]
    rows = {'planes': list(struct.iter_unpack('<4fi', data[1])),
            'verts': np.frombuffer(bytes(data[3]), '<f4').reshape(-1, 3),
            'texinfo': list(struct.iter_unpack('<8fii', data[6])),
            'faces': [list(f) for f in struct.iter_unpack('<Hhihh4Bi', data[7])],
            'edges': list(struct.iter_unpack('<HH', data[12])),
            'surfedges': [e for (e,) in struct.iter_unpack('<i', data[13])],
            'models': [list(m) for m in struct.iter_unpack('<9f7i', data[14])]}
    return data, blocks, records, rows


def _face_points(rows, face):
    first, count = face[2], face[3]
    return np.array([rows['verts'][rows['edges'][e][0] if e >= 0 else rows['edges'][-e][1]]
                     for e in rows['surfedges'][first:first + count]], dtype=np.float32)


def _placement(record):
    origin = np.array([float(v) for v in record.get('origin', '0 0 0').split()], dtype=float)
    angles = [float(v) for v in record.get('angles', '0 0 0').split()]
    if len(angles) != 3 or angles[0] or angles[2]:
        raise ValueError('Unsupported placement transform for lamp lighting')
    y = math.radians(angles[1])
    return origin, np.array([[math.cos(y), -math.sin(y), 0], [math.sin(y), math.cos(y), 0], [0, 0, 1]])


def _bake_lights(lamp):
    # bake_surface takes original units (it multiplies by 1/4).
    return {'position': [v / LOCAL_SCALE for v in lamp['position']], 'radius': lamp['radius'] / LOCAL_SCALE,
            'color': lamp['colour']}


def _entity_maps(rows, models, record, m, lamps, lamp_points, report, light, shared, min_peak=1):
    """{face offset in the model: lit face record} for one placement."""
    faces, texinfo, planes = rows['faces'], rows['texinfo'], rows['planes']
    mins, maxs = np.array(models[m][0:3]), np.array(models[m][3:6])
    first, count = models[m][14], models[m][15]
    origin, rotation = _placement(record)
    centre = rotation @ ((mins + maxs) / 2) + origin
    radius = float(np.linalg.norm(maxs - mins)) / 2
    near = [k for k, p in enumerate(lamp_points) if np.linalg.norm(p - centre) < radius + 2 * lamps[k]['radius']]
    out = {}
    if not near:
        return out
    report['placements_considered'] += 1
    for offset in range(count):
        face = list(faces[first + offset])
        points = _face_points(rows, face)
        normal = np.array(planes[face[0]][:3], dtype=float) * (-1 if face[1] else 1)
        world = points.astype(float) @ rotation.T + origin
        wnormal = rotation @ normal
        reach = [k for k in near if polygon_distance(lamp_points[k], world, wnormal) < 2 * lamps[k]['radius']]
        if not reach:
            continue
        report['faces_near'] += 1
        vecs = np.array(texinfo[face[4]][:8], dtype=np.float32).reshape(2, 4)
        grid = engine_grid([tuple(p) for p in points], [tuple(v) for v in vecs])
        if grid is None:
            report['faces_ambiguous_grid'] += 1
            continue
        if face[9] >= 0 and face[5] != 255:
            report['faces_existing_map_skipped'] += 1
            continue
        size = grid[1][0] * grid[1][1]
        maps = []
        for style in sorted({lamps[k]['style'] for k in reach}):
            lighting = {'ambient': [0, 0, 0], 'falloff': 'original', 'facing': True,
                        'lights': [_bake_lights(lamps[k]) for k in reach if lamps[k]['style'] == style]}
            samples = bake_surface(points.astype(float), vecs[:, :3].T.astype(float), vecs[:, 3].astype(float),
                                   rotation, origin, lighting, sample_grid=grid, front=normal)
            if len(samples) != size:
                raise ValueError('Lamp map size differs from the engine grid')
            if max(samples) >= min_peak:
                maps.append((style, samples))
        if not maps:
            report['faces_near_unlit'] += 1
            continue
        if len(maps) > 4:
            report['faces_style_limit_skipped'] += 1
            continue
        block = b''.join(s for _, s in maps)
        if block in shared:
            report['lightmap_blocks_shared'] += 1
        else:
            shared[block] = len(light); light += block
            report['lightmap_bytes_added'] += len(block)
        face[5:9] = [s for s, _ in maps] + [255] * (4 - len(maps))
        face[9] = shared[block]
        report['faces_baked'] += 1
        report['grid_samples'] += size
        report['max_sample'] = max(report['max_sample'], *(max(s) for _, s in maps))
        for s, _ in maps:
            report['styles'][str(s)] = report['styles'].get(str(s), 0) + 1
        out[offset] = face
    return out


def add_lamp_pool(raw, lamps, model_budget=None, min_peak=1):
    """Return (bsp, report): lamp maps for every placed face within 2 radius
    of a lamp whose brightest sample reaches min_peak. Raises on an existing
    render pool.

    Per shared face range, faces lit for any placement move to the end of the
    range (the tail). A lit placement's submodel then draws only the never-lit
    part; its render ranges draw the tail faces it does not light in place
    and its own lit copies, appended after all faces. The pool model spans
    from the first tail to the end, so ranges reach both. Mixed submodels get
    a shortened header variant while model_budget (submodels, world excluded)
    allows; otherwise the shared header is shortened and its unlit placements
    draw the tail through one range."""
    data, blocks, records, rows = _parse(raw)
    if not records or records[0].get('classname') != 'worldspawn':
        raise ValueError('Expected worldspawn first')
    if 'aw_render_pool' in records[0]:
        raise ValueError('Lamp pool requires a map without an existing render pool')
    faces, models = rows['faces'], rows['models']
    light = bytearray(data[8])
    shared = {}
    lamp_points = [np.array(l['position'], dtype=float) for l in lamps]
    report = {'lamps': len(lamps), 'placements_considered': 0, 'placements_lit': 0, 'faces_near': 0,
              'faces_baked': 0, 'faces_near_unlit': 0, 'faces_ambiguous_grid': 0, 'faces_existing_map_skipped': 0,
              'faces_style_limit_skipped': 0, 'lamp_sensitive_faces': 0, 'pool_faces': 0, 'lightmap_bytes_added': 0,
              'lightmap_blocks_shared': 0, 'headers_shortened': 0, 'model_variants_added': 0,
              'unlit_tail_ranges': 0, 'pool_copies': 0, 'grid_samples': 0, 'max_sample': 0, 'styles': {}}
    users = {}
    for i, record in enumerate(records):
        if record.get('classname') == 'func_wall' and record.get('model', '').startswith('*'):
            m = int(record['model'][1:])
            if m <= 0 or m >= len(models):
                raise ValueError('Invalid placement model')
            users.setdefault(m, []).append(i)
    spans = {}
    for m in users:
        spans.setdefault((models[m][14], models[m][15]), []).append(m)
    ordered = sorted(spans)
    for a, b in zip(ordered, ordered[1:]):
        if a[0] + a[1] > b[0]:
            raise ValueError('Overlapping placement face ranges')
    lit = {}
    for m, indices in sorted(users.items()):
        for ei in indices:
            maps = _entity_maps(rows, models, records[ei], m, lamps, lamp_points, report, light, shared, min_peak)
            if maps:
                lit[ei] = maps
    ranges = {}        # entity index -> [[absolute first face, count], ...]
    copies = []        # (entity index, its lit face records)
    candidates = []    # mixed headers: (unlit count, model, lit users, unlit users, span)
    tails = {}
    for span in ordered:
        first, count = span
        lit_users = [ei for m in spans[span] for ei in users[m] if ei in lit]
        if not lit_users:
            continue
        sensitive = {o for ei in lit_users for o in lit[ei]}
        # Faces lit by the same placements stay together, so the unlit part
        # of the tail is a few runs for each placement.
        groups = {}
        for o in sorted(sensitive):
            groups.setdefault(tuple(ei for ei in lit_users if o in lit[ei]), []).append(o)
        tail = [o for key in sorted(groups, key=lambda k: (-len(k), k)) for o in groups[key]]
        keep = [o for o in range(count) if o not in sensitive]
        original = faces[first:first + count]
        faces[first:first + count] = [original[o] for o in keep] + [original[o] for o in tail]
        base = first + len(keep)
        tails[span] = (base, len(tail), len(keep))
        report['lamp_sensitive_faces'] += len(tail)
        for ei in lit_users:
            runs = []
            for i, o in enumerate(tail):
                if o in lit[ei]:
                    continue
                if runs and runs[-1][0] + runs[-1][1] == base + i:
                    runs[-1][1] += 1
                else:
                    runs.append([base + i, 1])
            ranges[ei] = runs
            copies.append((ei, [lit[ei][o] for o in tail if o in lit[ei]]))
        for m in spans[span]:
            mine = [ei for ei in users[m] if ei in lit]
            other = [ei for ei in users[m] if ei not in lit]
            if not mine:
                continue
            if other:
                candidates.append((len(other), m, mine, other, span))
            else:
                models[m][15] = len(keep)
                report['headers_shortened'] += 1
    room = math.inf if model_budget is None else model_budget - (len(models) - 1) - 1
    for unlit_count, m, mine, other, span in sorted(candidates, key=lambda c: (-c[0], c[1])):
        base, size, kept = tails[span]
        if room > 0:
            variant = list(models[m]); variant[15] = kept
            index = len(models); models.append(variant); room -= 1
            report['model_variants_added'] += 1
            for ei in mine:
                records[ei]['model'] = '*%d' % index
        else:
            # Out of headers: shorten the shared one; unlit placements draw
            # the original tail in place.
            models[m][15] = kept
            report['headers_shortened'] += 1
            report['unlit_tail_ranges'] += len(other)
            for ei in other:
                ranges[ei] = [[base, size]]
    pool_first = min((t[0] for t in tails.values()), default=len(faces))
    for ei, block in copies:
        ranges[ei].append([len(faces), len(block)])
        faces.extend(block)
        report['pool_copies'] += len(block)
    for ei, runs in ranges.items():
        records[ei]['aw_render_ranges'] = ','.join('%d:%d' % (start - pool_first, n) for start, n in runs)
    report['range_records'] = len(ranges)
    report['ranges_total'] = sum(len(r) for r in ranges.values())
    report['ranges_max_per_record'] = max((len(r) for r in ranges.values()), default=0)
    report['pool_faces'] = len(faces) - pool_first
    report['placements_lit'] = len(lit)
    if ranges:
        header = list(models[0]); header[9:13] = [-1, -1, -1, -1]; header[14:16] = [pool_first, report['pool_faces']]
        records[0]['aw_render_pool'] = '*%d' % len(models)
        models.append(header)
    report['submodels_total'] = len(models) - 1
    if model_budget is not None and report['submodels_total'] > model_budget:
        raise ValueError('Lamp pool exceeds the model budget')

    def block_text(record, original):
        if record == dict(re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"', original)):
            return original
        return '{\n' + ''.join('"%s" "%s"\n' % kv for kv in record.items()) + '}'
    text = '\n'.join(block_text(r, b) for r, b in zip(records, blocks))
    data[0] = bytearray((text + '\n\0').encode('latin-1'))
    data[7] = bytearray(b''.join(struct.pack('<Hhihh4Bi', *f) for f in faces))
    data[8] = light
    data[14] = bytearray(b''.join(struct.pack('<9f7i', *m) for m in models))
    return pack_lumps(data), report


def check_lamp_grids(raw):
    """Every face with a style >= 32 map: its lightmap fits and its sample count
    per style matches the engine grid. Returns (faces checked, mismatches)."""
    data, blocks, records, rows = _parse(raw)
    checked, bad = 0, []
    for fi, face in enumerate(rows['faces']):
        styles = [s for s in face[5:9] if s != 255]
        if not any(s >= 32 for s in styles) or face[9] < 0:
            continue
        points = _face_points(rows, face)
        vecs = np.array(rows['texinfo'][face[4]][:8], dtype=np.float32).reshape(2, 4)
        grid = engine_grid([tuple(p) for p in points], [tuple(v) for v in vecs])
        checked += 1
        if grid is None or face[9] + grid[1][0] * grid[1][1] * len(styles) > len(data[8]):
            bad.append(fi)
    return checked, bad


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('bsp', type=Path)
    parser.add_argument('lamps', type=Path, help='JSON list from region_lamps')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error('Output exists')
    raw, report = add_lamp_pool(args.bsp.read_bytes(), json.loads(args.lamps.read_text(encoding='utf-8')))
    args.out.write_bytes(raw)
    report['sha256'] = hashlib.sha256(raw).hexdigest()
    sys.stdout.write(json.dumps(report, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
