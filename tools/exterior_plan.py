# SPDX-License-Identifier: GPL-3.0-only
"""Exterior ownership checklist, resolved before conversion; interiors are separate.

Town cores use the same half-open rectangles and town-first priority as
AW_WorldMapTarget. Drawing aprons are not ownership and must not be clipped.
"""
import hashlib
import json
from pathlib import Path
import struct

from world_payload import bounds, subtract

FORMAT = 'AmiWind exterior build checklist 1'


def source_cells(master):
    """Read exterior CELL plus height-bearing LAND identities, as the world survey does."""
    from mwad.esm import records, subrecords, is_deleted
    raw = Path(master).read_bytes()
    cells, lands = set(), set()
    for tag, flags, payload in records(raw):
        if tag not in ('CELL', 'LAND'):
            continue
        fields = {}
        for key, value in subrecords(payload):
            if key == 'FRMR':
                break
            fields[key] = value
        if is_deleted(flags, fields):
            continue
        if tag == 'CELL':
            if len(fields.get('DATA', b'')) != 12:
                raise ValueError('Invalid exterior CELL identity')
            bits, x, y = struct.unpack('<Iii', fields['DATA'])
            if not bits & 1:
                if (x, y) in cells:
                    raise ValueError('Duplicate exterior CELL identity')
                cells.add((x, y))
            continue
        if 'VHGT' not in fields:
            continue
        if len(fields.get('INTV', b'')) != 8:
            raise ValueError('Invalid LAND identity in exterior checklist')
        cell = struct.unpack('<ii', fields['INTV'])
        if cell in lands:
            raise ValueError('Duplicate LAND identity in exterior checklist')
        lands.add(cell)
    cells |= lands
    if not cells:
        raise ValueError('Exterior checklist has no terrain cells')
    return sorted(cells), hashlib.sha256(raw).hexdigest()


def town_cores(areas):
    from town_config import load_registry, handoff
    root = Path(__file__).resolve().parents[1]
    result = []
    registry = load_registry(root)
    unknown = set(areas) - {r['id'] for r in registry['towns']}
    if unknown:
        raise ValueError('Unknown exterior area: ' + ', '.join(sorted(unknown)))
    for row in registry['towns']:
        if row['id'] not in areas:
            continue
        settings = json.loads((root / 'config' / row['config']).read_bytes())
        origin, core = handoff(settings)
        result.append({'owner': row['id'], 'core': list(bounds(origin, sum(core, [])))})
    return result


def residual(box, towns):
    parts = [tuple(box)]
    for row in towns:
        parts = [piece for part in parts for piece in subtract(part, row['core'])]
    return parts


def make(cells, chim_cells, towns=(), master_sha256=None, *, ocean_cells=()):
    """One row per original exterior LAND; partially covered cells name the BSP remainder."""
    cells = [tuple(c) for c in cells]
    selected = [tuple(c) for c in chim_cells]
    if len(cells) != len(set(cells)) or len(selected) != len(set(selected)):
        raise ValueError('Duplicate exterior cell owner')
    ocean = {tuple(c) for c in ocean_cells}
    if not ocean <= set(selected):
        raise ValueError('Ocean routing must be explicitly selected for CHIM')
    extra_ocean = ocean - set(cells)
    if set(selected) - set(cells) != extra_ocean:
        raise ValueError('CHIM selection contains cells absent from the source LAND inventory')
    selected = set(selected)
    rows = []
    for x, y in sorted(set(cells) | extra_ocean):
        box = (x * 2048, y * 2048, (x + 1) * 2048, (y + 1) * 2048)
        overlaps = [t['owner'] for t in towns if subtract(box, t['core']) != [box]]
        rest = residual(box, towns)
        if (x, y) in selected and overlaps:
            raise ValueError('CHIM region and town claim the same exterior cell: %d,%d' % (x, y))
        kind = 'chim-region' if (x, y) in selected else 'bsp' if rest else 'chim-town'
        rows.append({'cell': [x, y], 'format': kind, 'town_owners': overlaps,
                     'bsp_core': [list(p) for p in rest] if kind == 'bsp' else []})
    return {'format': FORMAT, 'master_sha256': master_sha256, 'towns': list(towns), 'cells': rows,
            **({'ocean_cells': [list(c) for c in sorted(extra_ocean)]} if extra_ocean else {}),
            'summary': {kind: sum(r['format'] == kind for r in rows)
                        for kind in ('bsp', 'chim-region', 'chim-town')},
            'interiors': 'Independent; no interior is selected, retired or converted by this checklist.'}


def read(path):
    value = json.loads(Path(path).read_bytes())
    return validate(value)


def validate(value):
    """Check an embedded checklist by the same rules as the prebuild file."""
    if value.get('format') != FORMAT:
        raise ValueError('Invalid exterior checklist format')
    ocean = {tuple(c) for c in value.get('ocean_cells', [])}
    expected = make([r['cell'] for r in value['cells'] if tuple(r['cell']) not in ocean],
                    [r['cell'] for r in value['cells'] if r['format'] == 'chim-region'],
                    value['towns'], value['master_sha256'], ocean_cells=ocean)
    if value != expected:
        raise ValueError('Exterior checklist is inconsistent')
    return value


def omitted_paths(terrain, id1, *, planned_towns=None):
    """Bind never-compiled town-owned rows to final routing and live CHIM owners.

    A stable directory row is not a promised BSP. Only omissions proved by the
    original checklist may leave the fingerprint, and missing owners fail.
    The early image preflight may supply towns from the validated CHIM world
    receipt before their frame maps are written; final checks require frames.
    """
    from map_files import is_chim_frame, map_file
    from town_config import runtime_towns
    terrain, id1 = Path(terrain), Path(id1)
    receipt = json.loads((terrain / 'world-regions.json').read_bytes())
    if not receipt.get('exterior_checklist'):
        if any(r.get('routing_only') for r in receipt['regions']):
            raise ValueError('Routing-only terrain has no exterior checklist')
        return []
    plan = validate(receipt['exterior_checklist'])
    if plan['towns'] != town_cores([t['owner'] for t in plan['towns']]):
        raise ValueError('Exterior checklist town cores differ from the build configuration')
    kinds = classify_regions(plan, receipt['regions'], receipt['master_sha256'],
                             [r['cell'] for r in plan['cells'] if r['format'] == 'chim-region'])
    packet = (id1 / 'world/regions.awr').read_bytes()
    rows = receipt['regions']
    if (packet[:4] != b'AWR2' or len(packet) != 64 + 52 * len(rows)
            or struct.unpack_from('<I', packet, 4)[0] != len(rows)):
        raise ValueError('Exterior checklist final directory differs')
    owners = {t['id']: t['name'] for t in runtime_towns()}
    result = []
    for i, row in enumerate(rows):
        name = 'vf%04d' % i
        kind = 'chim-region' if row.get('chim_region') else 'routing-only' if row.get('routing_only') else 'bsp'
        if row['name'] != name or kinds[name] != kind:
            raise ValueError('Exterior ownership changed before fingerprint: ' + name)
        if kind != 'routing-only':
            continue
        expected = struct.pack('<8s11f', name.encode('ascii'), *row['origin'],
                               *row['core'][0], *row['core'][1], *row['coverage'][0], *row['coverage'][1])
        if packet[64 + i*52:64 + (i+1)*52] != expected:
            raise ValueError('Omitted exterior routing row changed: ' + name)
        if (terrain / name / 'scene.bsp').exists() or map_file(id1 / 'maps', name).exists():
            raise ValueError('Never-built exterior map was compiled or staged: ' + name)
        box = bounds(row['origin'], sum(row['core'], []))
        for town in plan['towns']:
            if subtract(box, town['core']) == [box]:
                continue
            owner = owners.get(town['owner'])
            if planned_towns is not None:
                if owner is None or town['owner'] not in planned_towns:
                    raise ValueError('Omitted exterior has no planned CHIM town owner: ' + name)
                continue
            frame = map_file(id1 / 'maps', owner + '-chim') if owner else None
            if frame is None or not frame.is_file() or not is_chim_frame(frame):
                raise ValueError('Omitted exterior has no active CHIM town owner: ' + name)
        if (id1 / ('harvest-' + name + '.txt')).exists():
            raise ValueError('Never-built exterior has an unused harvest catalogue: ' + name)
        result.append('maps/' + name + '.bsp')
    return result


def bind_steps(steps, path):
    targets = {'world-terrain', 'world-scenery', 'world-flora'}
    return [(name, [*command, '--exterior-plan', str(path)] if name in targets else
             [*command, '--exterior-terrain', str(Path(path).parent / 'world-terrain')] if name == 'image' else command)
            for name, command in steps]


def classify_regions(plan, entries, master_sha256, chim_cells, *, before_ocean_routing=False):
    """Resolve subdivided map cores before a compiler starts; keep directory rows for save IDs."""
    if master_sha256 != plan['master_sha256']:
        raise ValueError('Exterior checklist master differs from the terrain survey')
    planned = {tuple(r['cell']): r for r in plan['cells']}
    expected_cells = set(planned)
    if before_ocean_routing:
        expected_cells -= {tuple(c) for c in plan.get('ocean_cells', [])}
    if {tuple(e['cell']) for e in entries} != expected_cells:
        raise ValueError('Terrain survey cells differ from the exterior checklist')
    selected = {c for c, row in planned.items() if row['format'] == 'chim-region'}
    if selected != {tuple(cell) for cell in chim_cells}:
        raise ValueError('CHIM conversion selection differs from the exterior checklist')
    out = {}
    for row in entries:
        cell = tuple(row['cell'])
        box = bounds(row['origin'], sum(row['core'], []))
        if cell in selected:
            out[row['name']] = 'chim-region'
        elif not residual(box, plan['towns']):
            out[row['name']] = 'routing-only'
        else:
            out[row['name']] = 'bsp'
    return out


def no_legacy_map(row):
    return bool(row.get('chim_region') or row.get('routing_only'))


def skipped_row(row):
    return {key: row[key] for key in ('chim_region', 'routing_only') if row.get(key)}


def verify_stage(path, terrain):
    """Refuse stale or independently changed work lists before scenery/flora conversion."""
    if not path:
        return
    plan = read(path)
    receipt = json.loads((Path(terrain) / 'world-regions.json').read_bytes())
    kinds = classify_regions(plan, receipt['regions'], receipt['master_sha256'],
                             [r['cell'] for r in plan['cells'] if r['format'] == 'chim-region'])
    for row in receipt['regions']:
        expected = kinds[row['name']]
        actual = 'chim-region' if row.get('chim_region') else 'routing-only' if row.get('routing_only') else 'bsp'
        if expected != actual:
            raise ValueError('Exterior ownership changed between stages: ' + row['name'])


def reference_in_chim_town(reference, plan):
    """A missing town placement must be inside its core by position, not just cell membership.

    Regional CHIM cells are checked by the caller's existing set lookup.
    """
    position = reference.get('position')
    if not position or len(position) < 2:
        return False
    x, y = position[0] * .25, position[1] * .25
    return any(t['core'][0] <= x < t['core'][2] and t['core'][1] <= y < t['core'][3]
               for t in plan['towns'])
