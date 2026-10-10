#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Lava census: every lava surface of the island, from your own Morrowind files.

Morrowind has no lava "water type". Lava is ordinary art:

- lava meshes (pools, rivers, flows and fields) whose shapes carry a lava texture
  (`tx_lava*`-style names); a few carry an `AvoidNode` so actors path around them;
- lava ground textures in the LTEX table, painted on LAND cells (VTEX) like any other ground.

This tool reads the masters (Morrowind.esm, Tribunal.esm, Bloodmoon.esm), finds every mesh
whose shapes use a lava texture (read with the converter's own NIF reader,
prepare_scenery.model_geometry), and every land texture whose file is a lava texture, then
lists every placement and every painted land square per cell, exteriors and interiors:

    python3 tools/lava_census.py --data-files DIR --out lava-census.json [--jobs N]

Output (format aw-lava-census-1): summary counts, per-mesh lava area (Morrowind units^2, all
lava faces and the upward-facing part that a liquid surface replaces), per-texture use, per
cell the placements (object id, type, mesh, position, scale, lava area) and the painted land
squares. `--cells-out FILE` also writes the small per-cell stat that the progress trackers
read (cells.lava, docs/LAVA.md). Nothing derived from your files is part of this repository.
"""
import argparse
import collections
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))

from mwad.audit import records, subrecords  # noqa: E402
from lava import UP_NZ, is_lava_texture, script_contract  # noqa: E402,F401

FORMAT = 'aw-lava-census-1'
CELLS_FORMAT = 'aw-lava-cells-1'
MESH_FIELDS = ('area', 'up_area', 'footprint', 'faces', 'up_faces', 'textures', 'bounds', 'avoid_node')
CELL = 8192                  # Morrowind units per exterior cell
VTEX_SIDE = 16               # land texture squares per cell side
VTEX_AREA = (CELL // VTEX_SIDE) ** 2


def cell_key(cell):
    """'x,y' for an exterior cell, the cell name for an interior."""
    return cell['name'] if cell['interior'] else '%d,%d' % (cell['x'], cell['y'])


# ---------------------------------------------------------------- master records

def master_extras(raw):
    """LTEX table, LAND texture grids, object scripts and damage scripts of one master (the
    census parser world_estimate_data.parse_master leaves these out)."""
    ltex, vtex, scripts, contracts = {}, {}, {}, {}
    for tag, _flags, payload in records(raw):
        if tag == 'SCPT':
            s = dict(subrecords(payload))
            name = s.get('SCHD', b'')[:32].split(b'\0')[0].decode('cp1252', 'replace')
            dps, sound = script_contract(s.get('SCTX', b'').decode('cp1252', 'replace'))
            if name and (dps or sound):
                contracts[name.casefold()] = {'dps': dps, 'sound': sound}
        elif tag == 'LTEX':
            s = dict(subrecords(payload))
            if len(s.get('INTV', b'')) == 4:
                ltex[struct.unpack('<i', s['INTV'])[0]] = {
                    'id': s.get('NAME', b'').split(b'\0')[0].decode('cp1252', 'replace'),
                    'texture': s.get('DATA', b'').split(b'\0')[0].decode('cp1252', 'replace')}
        elif tag == 'LAND':
            s = dict(subrecords(payload))
            if len(s.get('INTV', b'')) == 8 and len(s.get('VTEX', b'')) == 512:
                vtex[struct.unpack('<ii', s['INTV'])] = struct.unpack('<256H', s['VTEX'])
        elif tag in ('STAT', 'ACTI', 'DOOR', 'CONT', 'LIGH', 'MISC'):
            s = {}
            for k, v in subrecords(payload):
                s.setdefault(k, v)
            if 'NAME' in s and 'SCRI' in s:
                scripts[s['NAME'].split(b'\0')[0].decode('cp1252', 'replace').casefold()] = \
                    s['SCRI'].split(b'\0')[0].decode('cp1252', 'replace')
    return {'ltex': ltex, 'vtex': vtex, 'scripts': scripts, 'contracts': contracts}


def land_lava(ltex, vtex):
    """{(x, y): squares} of land texture squares painted with a lava ground texture.
    VTEX values are LTEX index + 1 of the same master (0 = the default ground)."""
    lava_ids = {i + 1 for i, t in ltex.items() if is_lava_texture(t['texture'])}
    out = {}
    for xy, grid in vtex.items():
        n = sum(1 for v in grid if v in lava_ids)
        if n:
            out[xy] = n
    return out


# ---------------------------------------------------------------- meshes

def lava_faces(vertices, faces, materials):
    """Lava part of a mesh: dict(footprint, area, up_area, faces, up_faces, textures, bounds) in
    mesh units. footprint = the plan (x/y) extent of the upward-facing lava faces: Morrowind's
    pools stack a molten and a crust layer, so their face area counts the surface twice.
    vertices: rows starting x, y, z; faces: rows a, b, c, material; materials: dicts with
    texture_source. Empty dict when no shape uses a lava texture."""
    import numpy as np
    lava = [i for i, m in enumerate(materials) if is_lava_texture(m.get('texture_source'))]
    if not lava:
        return {}
    P = np.asarray(vertices, dtype=float)[:, :3]
    F = np.asarray(faces, dtype=int)
    F = F[np.isin(F[:, 3], lava)]
    if not len(F):
        return {}
    n = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
    length = np.linalg.norm(n, axis=1)
    area = length / 2
    nz = np.divide(n[:, 2], length, out=np.zeros_like(length), where=length > 0)
    up = nz >= UP_NZ
    pts = P[np.unique(F[:, :3])]
    top = P[np.unique(F[up][:, :3])] if up.any() else pts[:0]
    footprint = float(np.prod(top[:, :2].max(axis=0) - top[:, :2].min(axis=0))) if len(top) else 0.0
    return {'footprint': round(footprint, 1), 'area': round(float(area.sum()), 1),
            'up_area': round(float(area[up].sum()), 1),
            'faces': int(len(F)), 'up_faces': int(up.sum()),
            'textures': sorted({materials[i]['texture_source'].casefold() for i in lava}),
            'bounds': [[round(float(c), 1) for c in pts.min(axis=0)], [round(float(c), 1) for c in pts.max(axis=0)]]}


def scan_lava_mesh(source, name):
    """One mesh: {'model', 'status', ...lava_faces, 'avoid_node'}; never raises."""
    out = {'model': name}
    try:
        raw, src = source.read(name)
    except (OSError, ValueError, KeyError) as exc:
        out.update(status='missing', error=str(exc)[:200])
        return out
    low = raw.lower()
    out['avoid_node'] = b'avoidnode' in low
    out['sha256'] = hashlib.sha256(raw).hexdigest()
    if b'lava' not in low:
        out['status'] = 'none'
        return out
    from prepare_scenery import nif_reader, model_geometry
    from mwad.scene import unpack_geometry
    try:
        geometry, materials, _bounds, _ = model_geometry(raw, nif_reader(), repair_uv=True)
        vv, ff, _ = unpack_geometry(geometry)
    except Exception as exc:  # noqa: BLE001 - any reader failure is a per-mesh status
        out.update(status='nogeom', error=('%s: %s' % (type(exc).__name__, exc))[:200])
        return out
    found = lava_faces(vv, ff, materials)
    out.update(found)
    out['status'] = 'lava' if found else 'name-only'
    return out


_SOURCE = {}


def _scan_worker(task):
    data_files, name = task
    if data_files not in _SOURCE:
        from world_estimate_data import MeshSource
        _SOURCE.clear()
        _SOURCE[data_files] = MeshSource(data_files)
    return scan_lava_mesh(_SOURCE[data_files], name)


# ---------------------------------------------------------------- census

def build_census(masters, extras, meshes):
    """masters: world_estimate_data.census(); extras: {master: master_extras()};
    meshes: {model: scan_lava_mesh()}. Returns the census dict.

    Every placement is one of two kinds, decided by the game's own records, never by colour:
    'molten' = the object's script hurts an actor standing on it (Morrowind's lava pools,
    script "lava"); 'rock' = a lava-named texture on rock, cave walls or vents (Molag Amur
    basalt, lava caverns), which only looks volcanic. Land squares painted with a lava ground
    texture are rock: no land record carries damage."""
    from world_estimate_data import MASTERS
    lava_models = {m: r for m, r in meshes.items() if r.get('status') == 'lava'}
    objects, scripts, contracts = {}, {}, {}
    cells = collections.OrderedDict()
    texture_use = collections.Counter()

    def entry(cell, master):
        key = ('int:' if cell['interior'] else 'ext:') + cell_key(cell)
        if key not in cells:
            cells[key] = {'cell': cell_key(cell), 'interior': cell['interior'],
                          'x': None if cell['interior'] else cell['x'],
                          'y': None if cell['interior'] else cell['y'],
                          'region': cell.get('region') or '', 'master': master,
                          'placements': [], 'land_squares': 0}
        elif cell.get('region') and not cells[key]['region']:
            cells[key]['region'] = cell['region']
        return cells[key]
    for name in MASTERS:
        if name not in masters:
            continue
        objects.update(masters[name]['objects'])
        scripts.update(extras[name]['scripts'])
        contracts.update(extras[name]['contracts'])
        for cell in masters[name]['cells']:
            if cell.get('deleted'):
                continue
            for r in cell['refs']:
                if r.get('del'):
                    continue
                o = objects.get(r['id'])
                if not o or o.get('deleted') or o['model'] not in lava_models:
                    continue
                m = lava_models[o['model']]
                s = float(r.get('s', 1.0))
                p = r.get('p', [0.0, 0.0, 0.0])
                script = scripts.get(r['id'], '')
                contract = contracts.get(script.casefold(), {})
                e = entry(cell, name)
                e['placements'].append({
                    'id': r['id'], 'type': o['type'], 'model': o['model'], 'script': script,
                    'kind': 'molten' if contract.get('dps') else 'rock',
                    'dps': contract.get('dps', 0.0), 'sound': contract.get('sound', ''),
                    'pos': [round(c, 1) for c in p], 'rot': [round(c, 4) for c in r.get('r', [0, 0, 0])],
                    'scale': round(s, 4), 'area': round(m['area'] * s * s, 1),
                    'up_area': round(m['up_area'] * s * s, 1),
                    'footprint': round(m['footprint'] * s * s, 1), 'avoid_node': m['avoid_node']})
                for t in m['textures']:
                    texture_use[t] += 1
        land = land_lava(extras[name]['ltex'], extras[name]['vtex'])
        for (x, y), n in land.items():
            e = entry({'interior': False, 'x': x, 'y': y, 'name': '', 'region': ''}, name)
            e['land_squares'] = max(e['land_squares'], n)
    rows = []
    for e in cells.values():
        e['placements'].sort(key=lambda p: (p['model'], p['pos']))
        molten = [p for p in e['placements'] if p['kind'] == 'molten']
        e['placement_count'] = len(e['placements'])
        e['molten'] = len(molten)
        e['rock'] = e['placement_count'] - e['molten']
        e['molten_area'] = round(sum(p['footprint'] for p in molten), 1)
        e['area'] = round(sum(p['area'] for p in e['placements']), 1)
        e['land_area'] = e['land_squares'] * VTEX_AREA
        e['meshes'] = sorted({p['model'] for p in e['placements']})
        e['molten_meshes'] = sorted({p['model'] for p in molten})
        rows.append(e)
    rows.sort(key=lambda e: (e['interior'], e['cell'] if e['interior'] else '', e['x'] or 0, e['y'] or 0))
    ltex_lava = sorted({(name, t['id'], t['texture']) for name in extras for t in extras[name]['ltex'].values()
                        if is_lava_texture(t['texture'])})
    per_mesh = collections.Counter(p['model'] for e in rows for p in e['placements'])
    kind_of = {p['model']: p['kind'] for e in rows for p in e['placements']}
    ext = [e for e in rows if not e['interior']]
    ints = [e for e in rows if e['interior']]
    regions = collections.Counter()
    for e in rows:
        if e['molten']:
            regions[e['region'] or ('(interior)' if e['interior'] else '(no region)')] += e['molten']
    summary = {
        'lava_meshes': len(lava_models), 'name_only_meshes': sorted(m for m, r in meshes.items()
                                                                    if r.get('status') == 'name-only'),
        'molten_meshes': sorted(m for m, k in kind_of.items() if k == 'molten'),
        'avoid_node_meshes': sorted(m for m, r in lava_models.items() if r['avoid_node']),
        'damage_scripts': {k: v for k, v in sorted(contracts.items()) if v['dps']},
        'placements': sum(e['placement_count'] for e in rows),
        'molten_placements': sum(e['molten'] for e in rows),
        'molten_placements_exterior': sum(e['molten'] for e in ext),
        'molten_placements_interior': sum(e['molten'] for e in ints),
        'rock_placements': sum(e['rock'] for e in rows),
        'cells': len(rows), 'exterior_cells': len(ext), 'interior_cells': len(ints),
        'molten_cells_exterior': sum(1 for e in ext if e['molten']),
        'molten_cells_interior': sum(1 for e in ints if e['molten']),
        'exterior_cells_with_land_lava_rock': sum(1 for e in ext if e['land_squares']),
        'molten_area': round(sum(e['molten_area'] for e in rows), 1),
        'molten_area_exterior': round(sum(e['molten_area'] for e in ext), 1),
        'molten_area_interior': round(sum(e['molten_area'] for e in ints), 1),
        'molten_by_region': dict(regions.most_common()),
        'land_area': sum(e['land_area'] for e in rows),
        'lava_land_textures': [{'master': m, 'id': i, 'texture': t} for m, i, t in ltex_lava],
        'texture_placements': dict(sorted(texture_use.items())),
    }
    return {'format': FORMAT, 'units': 'Morrowind units (area in units^2; 1 Quake unit = 4)',
            'masters': {n: masters[n]['sha256'] for n in masters}, 'summary': summary,
            'meshes': [dict(model=m, placements=per_mesh.get(m, 0), kind=kind_of.get(m, 'unplaced'),
                            **{k: r[k] for k in MESH_FIELDS})
                       for m, r in sorted(lava_models.items())],
            'cells': rows}


def cell_stats(census):
    """The small per-cell lava stat for the trackers: {format, summary, cells: {key: stat}}.
    Keys: exterior 'x,y', interior the cell name. status: 'molten' (has lava pools, not yet
    converted as a Quake liquid: converters raise it to 'converted' in their own results),
    'rock' (volcanic rock/ground only: nothing to convert)."""
    out = {}
    for e in census['cells']:
        out[e['cell']] = {'interior': e['interior'], 'molten': e['molten'], 'rock': e['rock'],
                          'molten_area': e['molten_area'], 'land_squares': e['land_squares'],
                          'molten_meshes': e['molten_meshes'],
                          'status': 'molten' if e['molten'] else 'rock'}
    keys = ('molten_placements', 'molten_cells_exterior', 'molten_cells_interior', 'rock_placements',
            'exterior_cells_with_land_lava_rock')
    return {'format': CELLS_FORMAT, 'summary': {k: census['summary'][k] for k in keys}, 'cells': out}


def run(data_files, jobs=None):
    from world_estimate_data import MASTERS, census, used_meshes
    from mwad.paths import child_ci
    from build_parallel import ordered_map
    masters = census(data_files)
    extras = {}
    for name in MASTERS:
        if name in masters:
            extras[name] = master_extras(child_ci(Path(data_files), name).read_bytes())
    names = sorted(used_meshes(masters))
    meshes = {}
    for r in ordered_map(_scan_worker, [(str(data_files), n) for n in names], jobs=jobs):
        meshes[r['model']] = r
    out = build_census(masters, extras, meshes)
    out['summary']['meshes_scanned'] = len(names)
    out['summary']['meshes_missing'] = sum(1 for r in meshes.values() if r.get('status') == 'missing')
    return out


def main(argv=None):
    from build_jobs import add_jobs, resolve_jobs
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--data-files', required=True, help='your Morrowind Data Files folder')
    p.add_argument('--out', required=True, help='census JSON')
    p.add_argument('--cells-out', help='per-cell lava stat JSON for the trackers')
    add_jobs(p)
    a = p.parse_args(argv)
    out = run(a.data_files, resolve_jobs(a.jobs))
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8', newline='\n')
    if a.cells_out:
        Path(a.cells_out).write_text(json.dumps(cell_stats(out), indent=1, sort_keys=True) + '\n',
                                     encoding='utf-8', newline='\n')
    s = out['summary']
    print('lava census: molten lava %d placements (%d exterior in %d cells, %d interior in %d cells), '
          'molten surface %.0f units^2; volcanic rock %d placements; lava-rock ground in %d exterior cells'
          % (s['molten_placements'], s['molten_placements_exterior'], s['molten_cells_exterior'],
             s['molten_placements_interior'], s['molten_cells_interior'], s['molten_area'],
             s['rock_placements'], s['exterior_cells_with_land_lava_rock']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
