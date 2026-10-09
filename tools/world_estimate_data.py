# SPDX-License-Identifier: GPL-3.0-only
"""World estimate, data side: census, mesh scan and per-map features.

Everything here reads the user's own Morrowind files at run time; nothing
derived from them is stored in this repository.

- Census: every cell, placed reference and LAND record of each present master
  (Morrowind.esm, Tribunal.esm, Bloodmoon.esm), with the repository's TES3
  record readers (mwad.audit).
- Mesh scan: every mesh a placed reference uses, read with the converter's NIF
  reader (prepare_scenery.model_geometry) and measured with the converter's own
  surface and collision functions (mesh_geometry, prepare_mesh_bsp), once with
  the interior profile and once with the exterior profile. These per-mesh
  counts (faces, texture mappings, lightmap samples, point nodes, clipnodes,
  surface extent) are computed, not estimated.
- Features: one map per interior cell; exteriors as town-converter regions
  (town_regions.regions with the Balmora sub-cell settings) on a regular grid
  of 3x3-cell frames. Two scenarios per map: 'cur' (what the converters take
  today) and 'evr' (every placed object with a mesh as geometry, actors as
  edicts).
"""
import collections
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import records, subrecords, normpath  # noqa: E402

MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
SET_OF_MASTER = {'Morrowind.esm': 'vvardenfell', 'Tribunal.esm': 'tribunal', 'Bloodmoon.esm': 'bloodmoon'}
SCALE = 0.25          # Morrowind units -> Quake units (prepare_quake.SCALE)
CELL = 8192           # Morrowind units per exterior cell
OBJECT_TAGS = frozenset('STAT DOOR MISC WEAP CONT CREA LIGH NPC_ ARMO CLOT REPA ACTI APPA LOCK PROB INGR BOOK '
                        'ALCH LEVI LEVC BODY'.split())
ITEM_TAGS = frozenset({'MISC', 'WEAP', 'ARMO', 'CLOT', 'REPA', 'APPA', 'LOCK', 'PROB', 'INGR', 'BOOK', 'ALCH', 'LEVI'})
ACTOR_TAGS = frozenset({'NPC_', 'CREA', 'LEVC'})
SCAN_VERSION = 5      # bump when mesh_costs changes; invalidates mesh caches (5: reduce_for_profile)
LAMP_KINDS = ('lamp', 'torch', 'fire', 'candle')


def cstr(raw):
    return raw.split(b'\0')[0].decode('cp1252', 'replace')


def normmodel(model):
    model = normpath((model or '').strip())
    if not model:
        return ''
    return model if model.startswith('meshes/') else 'meshes/' + model


# ---------------------------------------------------------------- census

def _land_heights(vhgt):
    import numpy as np
    base = struct.unpack_from('<f', vhgt)[0]
    d = np.frombuffer(vhgt, np.int8, 4225, 4).reshape(65, 65).astype(np.float64)
    col0 = base + np.cumsum(d[:, 0])
    return (np.cumsum(np.column_stack([col0, d[:, 1:]]), axis=1) * 8).astype(np.float32)


def parse_master(path):
    """Objects, cells (with references) and LAND heights of one master file."""
    raw = Path(path).read_bytes()
    objects, cells, lands, counts = {}, [], {}, collections.Counter()
    quoted = set()
    for tag, flags, payload in records(raw):
        counts[tag] += 1
        if tag in ('SCPT', 'INFO'):
            # Script source and dialogue result text: quoted strings name the cells
            # that scripts move the player to (PositionCell, COC).
            for k, v in subrecords(payload):
                if k in ('SCTX', 'BNAM'):
                    text = v.decode('cp1252', 'replace')
                    quoted.update(q.casefold() for q in re.findall(r'"([^"\n]+)"', text))
        elif tag in OBJECT_TAGS:
            s = {}
            for k, v in subrecords(payload):
                s.setdefault(k, v)
            if 'NAME' not in s:
                continue
            o = {'type': tag, 'model': normmodel(cstr(s.get('MODL', b''))),
                 'deleted': 'DELE' in s or bool(flags & 0x20)}
            if tag == 'LIGH' and len(s.get('LHDT', b'')) == 24:
                o['radius'] = struct.unpack_from('<I', s['LHDT'], 12)[0]
                o['lflags'] = struct.unpack_from('<I', s['LHDT'], 20)[0]
            objects[cstr(s['NAME']).casefold()] = o
        elif tag == 'CELL':
            header, refs, ref = {}, [], None
            for k, v in subrecords(payload):
                if k == 'FRMR' and len(v) == 4:
                    ref = {'n': struct.unpack('<I', v)[0], 's': 1.0}
                    refs.append(ref)
                elif k == 'MVRF':
                    ref = None
                elif ref is None:
                    header.setdefault(k, v)
                elif k == 'NAME':
                    ref['id'] = cstr(v).casefold()
                elif k == 'DATA' and len(v) == 24:
                    ref['p'] = list(struct.unpack('<3f', v[:12]))
                    ref['r'] = list(struct.unpack('<3f', v[12:]))
                elif k == 'XSCL' and len(v) == 4:
                    ref['s'] = struct.unpack('<f', v)[0]
                elif k == 'DELE':
                    ref['del'] = 1
                elif k == 'DODT':
                    ref['dest'] = 1
                elif k == 'DNAM':
                    ref['dcell'] = cstr(v)
            if len(header.get('DATA', b'')) != 12:
                continue
            cflags, x, y = struct.unpack('<Iii', header['DATA'])
            water = None
            if len(header.get('WHGT', b'')) == 4:
                water = struct.unpack('<f', header['WHGT'])[0]
            elif len(header.get('INTV', b'')) == 4:
                water = float(struct.unpack('<i', header['INTV'])[0])
            cells.append({'interior': bool(cflags & 1), 'flags': cflags, 'x': x, 'y': y,
                          'name': cstr(header.get('NAME', b'')), 'region': cstr(header.get('RGNN', b'')),
                          'water': water, 'deleted': bool(flags & 0x20) or 'DELE' in header,
                          'refs': [r for r in refs if 'id' in r]})
        elif tag == 'LAND':
            s = dict(subrecords(payload))
            if len(s.get('INTV', b'')) == 8 and len(s.get('VHGT', b'')) == 4232:
                lands[struct.unpack('<ii', s['INTV'])] = _land_heights(s['VHGT'])
    return {'objects': objects, 'cells': cells, 'lands': lands, 'counts': dict(counts), 'script_strings': quoted,
            'sha256': hashlib.sha256(raw).hexdigest()}


def census(data_files):
    """Parse every present master. Returns {master: parsed}."""
    from mwad.paths import child_ci
    out = {}
    for name in MASTERS:
        path = child_ci(Path(data_files), name, required=False)
        if path is not None and path.is_file():
            out[name] = parse_master(path)
    if 'Morrowind.esm' not in out:
        raise ValueError('Morrowind.esm not found in ' + str(data_files))
    return out


def census_summary(masters):
    summary = {}
    for name, m in masters.items():
        ints = [c for c in m['cells'] if c['interior']]
        exts = [c for c in m['cells'] if not c['interior']]
        types = collections.Counter(o['type'] for o in m['objects'].values())
        summary[name] = {'sha256': m['sha256'], 'objects_by_type': dict(types),
                         'interior_cells': len(ints), 'exterior_cells': len(exts), 'land_records': len(m['lands']),
                         'refs_interior': sum(len(c['refs']) for c in ints),
                         'refs_exterior': sum(len(c['refs']) for c in exts)}
    return summary


class World:
    """One master's cells with every object definition up to that master."""

    def __init__(self, masters, master, meshes):
        self.master = master
        self.objects = {}
        for name in MASTERS:
            if name not in masters:
                continue
            self.objects.update(masters[name]['objects'])
            if name == master:
                break
        self.cells = masters[master]['cells']
        self.land = dict(masters[master]['lands'])
        if master != 'Morrowind.esm':      # expansions also see the base terrain
            for k, h in masters['Morrowind.esm']['lands'].items():
                self.land.setdefault(k, h)
        self.meshes = meshes


def used_meshes(masters):
    """Placement count per mesh path, over every master."""
    used = collections.Counter()
    objects = {}
    for name in MASTERS:
        if name not in masters:
            continue
        objects.update(masters[name]['objects'])
        for cell in masters[name]['cells']:
            for r in cell['refs']:
                o = objects.get(r['id'])
                if o and o['model']:
                    used[o['model']] += 1
    return used


# ---------------------------------------------------------------- mesh scan

INTERIOR_AREA = 'balmora'   # the production interior entry policy (config/balmora_interiors.json rooms)


def interior_profile(model, triangles):
    """The interior converter's visual/collision profile (prepare_area, Balmora interior entries)."""
    from prepare_area import interior_visual_profile
    from static_lod import rock_profile
    profile = interior_visual_profile(model, INTERIOR_AREA)
    return profile if profile is not None else rock_profile(model, triangles)


def exterior_profile(model, triangles):
    """The town converter's profile (import_town.prepare)."""
    from town_regions import visual_profile
    return {'collision_source': 'root_node_or_visual', **visual_profile(model, triangles)}


def mesh_costs(vertices, faces, collision, profile, materials=None):
    """Per-variant BSP cost of one mesh under one converter profile.

    Mirrors prepare_mesh_bsp._prepare_model and the per-surface/per-piece
    loops of append_meshes: faces after split_surface, texture mappings,
    lightmap samples (scale-invariant: texture vectors follow the placement),
    point-hull nodes, standing-box clipnodes, largest surface extent (exact,
    and as the target computes it from the stored 32-bit values)."""
    import numpy as np
    from mesh_geometry import surface_polygons, split_surface, collision_pieces
    from prepare_mesh_bsp import standing_planes
    v, f = vertices, faces
    visual_v, visual_f = v, f
    ratio = profile.get('ratio')
    if ratio and ratio < 1:
        from static_lod import reduce_for_profile
        visual_v, visual_f, _ = reduce_for_profile(v, f, profile, materials)
    texsize = profile.get('texture_size', 64)
    out = {'faces': 0, 'texinfo': 0, 'luxels': 0, 'nodes': 0, 'clipnodes': 0, 'max_extent': 0.0,
           'max_extent_target': 0.0, 'area_q': 0.0}
    mappings = set()
    if not profile.get('collision_only'):
        for poly, material, axes, offset, normal in surface_polygons(visual_v, visual_f):
            ax = np.column_stack((axes.T * texsize, offset * texsize))
            mappings.add((int(material), *np.round(ax.flatten(), 4)))
            ax32 = ax.astype(np.float32).astype(float)
            for patch in split_surface(poly, ax):
                out['faces'] += 1
                uv = patch @ ax[:, :3].T + ax[:, 3]
                es = math.ceil(uv[:, 0].max() / 16) * 16 - math.floor(uv[:, 0].min() / 16) * 16
                et = math.ceil(uv[:, 1].max() / 16) * 16 - math.floor(uv[:, 1].min() / 16) * 16
                out['luxels'] += int((es // 16 + 1) * (et // 16 + 1))
                out['max_extent'] = max(out['max_extent'], float(max(es, et)))
                # Target rounding (MESH-EXTENT-GRID-31): the BSP stores vertices and texture
                # vectors as 32-bit floats; the 68040 evaluates them in extended precision,
                # so a grid-exact end can move across a 16-texel line. Emulate a placement
                # at unit scale without tilt: stored values, double-precision evaluation.
                uv32 = patch.astype(np.float32).astype(float) @ ax32[:, :3].T + ax32[:, 3]
                gs = math.ceil(uv32[:, 0].max() / 16) * 16 - math.floor(uv32[:, 0].min() / 16) * 16
                gt = math.ceil(uv32[:, 1].max() / 16) * 16 - math.floor(uv32[:, 1].min() / 16) * 16
                out['max_extent_target'] = max(out['max_extent_target'], float(max(gs, gt)))
                rel = patch - patch[0]
                out['area_q'] += float(np.linalg.norm(np.cross(rel, np.roll(rel, -1, axis=0)).sum(axis=0)) / 2)
    out['texinfo'] = len(mappings)
    if not profile.get('collision_none'):
        cv, cf = collision if (collision is not None and profile.get('collision_source')) else (v, f)
        pieces, exact, _ = collision_pieces(cv, cf, profile)
        for k, (points, hull, ids, error) in enumerate(pieces):
            point_eq = np.unique(np.round(hull.equations, 5), axis=0)
            out['nodes'] += len(point_eq)
            out['clipnodes'] += len(standing_planes(points, point_eq, exact is True or (bool(exact) and k in exact)))
    return out


class MeshSource:
    """Loose Data Files/Meshes first, then BSAs (Bloodmoon > Tribunal > Morrowind)."""

    def __init__(self, data_files):
        from mwad.audit import BSA
        from mwad.paths import child_ci
        self.data = Path(data_files)
        self.loose = {}
        meshes = child_ci(self.data, 'Meshes', required=False)
        if meshes is not None and meshes.is_dir():
            for q in meshes.rglob('*'):
                if q.is_file():
                    self.loose['meshes/' + q.relative_to(meshes).as_posix().casefold()] = q
        self.bsas = []
        for name in ('Bloodmoon.bsa', 'Tribunal.bsa', 'Morrowind.bsa'):
            p = child_ci(self.data, name, required=False)
            if p is not None and p.is_file():
                self.bsas.append(BSA(p))

    def read(self, name):
        if name in self.loose:
            return self.loose[name].read_bytes(), 'loose'
        from prepare_scenery import bsa_read
        for b in self.bsas:
            if name in b.entries:
                return bsa_read(b, name), b.path.name
        raise FileNotFoundError(name)


_SOURCE = {}


def _scan_worker(task):
    data_files, name = task
    if data_files not in _SOURCE:
        _SOURCE.clear()
        _SOURCE[data_files] = MeshSource(data_files)
    return scan_mesh(_SOURCE[data_files], name)


def scan_mesh(source, name):
    """Measure one mesh; never raises (status 'missing' / 'nogeom')."""
    import numpy as np
    from prepare_scenery import nif_reader, model_geometry, model_flames
    from mwad.scene import unpack_geometry
    out = {'model': name, 'scan_version': SCAN_VERSION}
    try:
        raw, src = source.read(name)
    except (OSError, ValueError, KeyError) as exc:
        out.update(status='missing', error=str(exc)[:200])
        return out
    out.update(source=src, sha256=hashlib.sha256(raw).hexdigest())
    N = nif_reader()
    try:
        geometry, materials, bounds, _ = model_geometry(raw, N, repair_uv=True)
        vv, ff, _ = unpack_geometry(geometry)
        v = np.array(vv, dtype=float)
        f = np.array(ff, dtype=int)
        P = v[:, :3]
        F = f[:, :3]
        a = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
        out.update(status='ok', tris=int(len(F)), verts=int(len(P)), bounds=bounds,
                   area=float(np.linalg.norm(a, axis=1).sum() / 2), materials=len(materials),
                   textures=sorted({(m['texture_source'] or '').casefold() for m in materials}),
                   emissive=sum(1 for m in materials if m.get('emissive')))
    except Exception as exc:  # noqa: BLE001 - any reader failure is a per-mesh status
        out.update(status='nogeom', error=('%s: %s' % (type(exc).__name__, exc))[:200])
        return out
    collision = None
    try:
        cg, _, _, _ = model_geometry(raw, N, collision=True)
        cvv, cff, _ = unpack_geometry(cg)
        collision = (np.array(cvv, dtype=float), np.array(cff, dtype=int))
        out['coll_tris'] = len(cff)
    except Exception:  # noqa: BLE001 - no collision node: converters fall back to the visual mesh
        out['coll_tris'] = 0
    try:
        out['flames'] = len(model_flames(raw, N, name))
    except Exception:  # noqa: BLE001
        out['flames'] = 0
    out['costs'] = {}
    for space, profile in (('interior', interior_profile(name, out['tris'])),
                           ('exterior', exterior_profile(name, out['tris']))):
        try:
            out['costs'][space] = mesh_costs(v, f, collision, profile, materials)
        except Exception as exc:  # noqa: BLE001 - recorded; the estimator falls back to triangle ratios
            out['costs'][space] = {'error': ('%s: %s' % (type(exc).__name__, exc))[:200]}
    return out


def scan_meshes(data_files, names, cache_path=None, jobs=1, progress=None):
    """Scan meshes, reusing a cache keyed by mesh name, content hash and SCAN_VERSION."""
    from build_parallel import ordered_map
    cache = {}
    if cache_path is not None and Path(cache_path).is_file():
        cache = json.loads(Path(cache_path).read_text(encoding='utf-8'))
    source = MeshSource(data_files)
    rows, todo = {}, []
    for name in names:
        row = cache.get(name)
        if row and row.get('scan_version') == SCAN_VERSION and row.get('status') != 'missing':
            try:
                raw, _ = source.read(name)
            except (OSError, ValueError, KeyError):
                raw = None
            if raw is not None and hashlib.sha256(raw).hexdigest() == row.get('sha256'):
                rows[name] = row
                continue
        todo.append(name)
    for i, row in enumerate(ordered_map(_scan_worker, [(str(data_files), n) for n in todo], jobs)):
        rows[row['model']] = row
        if progress and (i % 250 == 0 or i == len(todo) - 1):
            progress('mesh scan %d/%d' % (i + 1, len(todo)))
    if cache_path is not None:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cache_path).write_text(json.dumps(rows, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return rows


# ---------------------------------------------------------------- features

def light_kind(ident, model, flags):
    from light_sources import classify
    return classify(ident, model, flags)


def light_style(kind, flags, exterior):
    from light_sources import quake_style
    return quake_style(kind, flags, exterior)


def interior_policy(ref, o):
    """mwad.interior.omission_reason: None = the interior converter keeps it."""
    from mwad.interior import omission_reason
    return omission_reason({'number': ref['n'], 'id': ref['id'], 'type': o['type'],
                            'model': o['model'][len('meshes/'):]})


def exterior_policy(ref, o):
    """import_town.collect: actors/levelled lists and marker meshes are deferred."""
    if o['type'] in ('NPC_', 'CREA', 'LEVC', 'LEVI'):
        return 'actor or levelled list'
    m = o['model']
    if not m or m.rsplit('/', 1)[-1].startswith('marker_'):
        return 'nonvisual source marker'
    return None


def everything_policy(ref, o):
    """Extra references the 'evr' scenario takes beyond 'cur' (see ref_info)."""
    if o['type'] in ACTOR_TAGS:
        return 'actor (edict)'
    m = o['model']
    if not m:
        return 'no mesh'
    if 'marker' in m.rsplit('/', 1)[-1]:
        return 'editor marker'
    return None


def tilted(r):
    return any(abs(math.sin(a)) > 1e-7 or math.cos(a) < 0 for a in r[:2])


def variant_key(model, ref):
    """prepare_mesh_bsp._instance_key without per-instance lighting."""
    r = ref.get('r', [0.0, 0.0, 0.0])
    t = tilted(r)
    return (model, round(ref['s'], 6), round(r[0], 6), round(r[1], 6), round(r[2], 6) if t else None)


def rotation(r):
    import numpy as np
    x, y, z = [-a for a in r]
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rx @ ry @ rz


def world_bounds(b, ref):
    import numpy as np
    c = np.array([[a, bb, cc] for a in (b[0][0], b[1][0]) for bb in (b[0][1], b[1][1]) for cc in (b[0][2], b[1][2])])
    p = c @ rotation(ref.get('r', [0, 0, 0])).T * ref['s'] + ref['p']
    return p.min(0), p.max(0)


def ref_info(world, ref, space):
    o = world.objects.get(ref['id'])
    if o is None or ref.get('del') or 'p' not in ref:
        return None
    mesh = world.meshes.get(o['model']) if o['model'] else None
    if mesh is not None and mesh.get('status') != 'ok':
        mesh = None
    cur = (interior_policy if space == 'interior' else exterior_policy)(ref, o)
    if cur is None and mesh is None:
        cur = 'mesh without geometry'
    # 'evr' adds to what the converters take; it never drops a reference 'cur'
    # keeps (ESTIMATE-EVR-BELOW-CUR-31: the exterior converter keeps meshes whose
    # name merely contains 'marker', the 'evr' marker rule alone dropped them).
    evr = None if cur is None else everything_policy(ref, o)
    if evr is None and mesh is None:
        evr = 'mesh without geometry'
    return o, mesh, cur, evr


def summarise(world, refs, space, exterior_lights):
    """Feature dict of the references belonging to one map."""
    import numpy as np
    f = {'refs_total': 0, 'by_type': collections.Counter(), 'cur_refs': 0, 'evr_refs': 0,
         'npc': 0, 'creatures': 0, 'levc': 0, 'lights': 0, 'lights_animated': 0, 'styles': set(),
         'doors': 0, 'containers': 0, 'items': 0, 'activators': 0, 'load_doors': 0,
         'cur_flames': 0, 'evr_flames': 0}
    cv, ev = collections.Counter(), collections.Counter()
    ctex, etex = set(), set()
    lo = np.full(3, 1e18)
    hi = -lo
    for ref in refs:
        info = ref_info(world, ref, space)
        if info is None:
            continue
        o, mesh, cur, evr = info
        f['refs_total'] += 1
        t = o['type']
        f['by_type'][t] += 1
        lo = np.minimum(lo, ref['p'])
        hi = np.maximum(hi, ref['p'])
        if t == 'NPC_':
            f['npc'] += 1
        elif t == 'CREA':
            f['creatures'] += 1
        elif t == 'LEVC':
            f['levc'] += 1
        elif t == 'DOOR':
            f['doors'] += 1
            f['load_doors'] += 1 if ref.get('dest') else 0
        elif t == 'CONT':
            f['containers'] += 1
        elif t == 'ACTI':
            f['activators'] += 1
        elif t in ITEM_TAGS:
            f['items'] += 1
        if t == 'LIGH' and 'lflags' in o:
            kind = light_kind(ref['id'], o['model'], o['lflags'])
            if kind != 'off':
                f['lights'] += 1
                st = light_style(kind, o['lflags'], exterior_lights)
                f['styles'].add(st)
                if st not in (0, 32):
                    f['lights_animated'] += 1
        if cur is None:
            f['cur_refs'] += 1
            cv[variant_key(o['model'], ref)] += 1
            ctex.update(mesh['textures'])
            f['cur_flames'] += mesh.get('flames', 0)
        if evr is None:
            f['evr_refs'] += 1
            ev[variant_key(o['model'], ref)] += 1
            etex.update(mesh['textures'])
            f['evr_flames'] += mesh.get('flames', 0)
    f['by_type'] = dict(f['by_type'])
    f['styles'] = sorted(f['styles'])
    f['cur_variants'] = [[k[0], n] for k, n in cv.items()]
    f['evr_variants'] = [[k[0], n] for k, n in ev.items()]
    f['cur_textures'] = len(ctex)
    f['evr_textures'] = len(etex)
    f['span_mw'] = (hi - lo).tolist() if f['refs_total'] else [0, 0, 0]
    return f


def coord_max(refs):
    """Largest |x|,|y|,|z| reference origin of a room in Quake units (rooms keep the cell origin)."""
    m = 0.0
    for r in refs:
        if 'p' in r and not r.get('del'):
            m = max(m, max(abs(v) for v in r['p']))
    return m * SCALE


def interior_maps(world, prefix, cells=None):
    names = sorted((c for c in (cells if cells is not None else world.cells) if c['interior'] and not c['deleted']),
                   key=lambda c: c['name'].casefold())
    for i, c in enumerate(names, 1):
        f = summarise(world, c['refs'], 'interior', bool(c['flags'] & 0x80))
        f.update(map='%s%04d' % (prefix, i), space='interior', cell=c['name'], region=c['region'],
                 water=c['water'], behave_exterior=bool(c['flags'] & 0x80), coord_max=coord_max(c['refs']))
        yield f


def region_settings():
    """Sub-cell layout of the town converter (Balmora settings, frame-relative)."""
    from town_config import load_settings
    s = dict(load_settings('balmora'))
    s['region_core_overrides'] = {}
    return s


def land_fraction(world, wx0, wy0, wx1, wy1, water_by_cell):
    """Share of height samples above the cell's water level inside a world
    rectangle, whether any LAND exists, and the highest sample (world units)."""
    import numpy as np
    tot = above = 0
    anyland = False
    hmax = None
    for cx in range(math.floor(wx0 / CELL), math.ceil(wx1 / CELL)):
        for cy in range(math.floor(wy0 / CELL), math.ceil(wy1 / CELL)):
            h = world.land.get((cx, cy))
            if h is None:
                continue
            anyland = True
            xs = np.arange(65) * 128 + cx * CELL
            ys = np.arange(65) * 128 + cy * CELL
            mx = (xs >= wx0) & (xs <= wx1)
            my = (ys >= wy0) & (ys <= wy1)
            sub = h[np.ix_(my, mx)]
            if sub.size:
                hmax = float(sub.max()) if hmax is None else max(hmax, float(sub.max()))
            tot += sub.size
            above += int((sub > water_by_cell.get((cx, cy), 0.0)).sum())
    return (above / tot if tot else 0.0), anyland, hmax


def exterior_frames(world, frames, settings, cells=None):
    """frames: list of (frame_id, (cx, cy)). Yields one feature dict per region."""
    import numpy as np
    from town_regions import regions
    by_cell, water = collections.defaultdict(list), {}
    for c in (cells if cells is not None else world.cells):
        if c['interior'] or c['deleted']:
            continue
        by_cell[(c['x'], c['y'])].extend(c['refs'])
        if c['water'] is not None:
            water[(c['x'], c['y'])] = c['water']
    lamp_cells = collections.Counter()
    for key, refs in by_cell.items():
        for r in refs:
            o = world.objects.get(r['id'])
            if o and o['type'] == 'LIGH' and 'lflags' in o and not r.get('del'):
                if light_kind(r['id'], o['model'], o['lflags']) in LAMP_KINDS:
                    lamp_cells[key] += 1
    entries = regions(settings)
    for fid, (fx, fy) in frames:
        centre = ((fx + .5) * CELL, (fy + .5) * CELL)
        cells3 = [(x, y) for x in range(fx - 1, fx + 2) for y in range(fy - 1, fy + 2)]
        placed = []
        for k in cells3:
            for r in by_cell.get(k, []):
                info = ref_info(world, r, 'exterior')
                if info is None:
                    continue
                mesh = info[1]
                if mesh is not None:
                    b0, b1 = world_bounds(mesh['bounds'], r)
                else:
                    b0 = b1 = np.array(r['p'])
                placed.append((r, (b0[:2] - centre) * SCALE, (b1[:2] - centre) * SCALE, r['p'][:2]))
        if not placed and not any(k in world.land for k in cells3):
            continue
        for n, entry in enumerate(entries):
            core, cov = entry['core'], entry['coverage']
            wc = [(centre[0] + core[0][0] / SCALE, centre[1] + core[0][1] / SCALE),
                  (centre[0] + core[1][0] / SCALE, centre[1] + core[1][1] / SCALE)]
            core_cells = sorted({(math.floor(wx / CELL), math.floor(wy / CELL))
                                 for wx in (wc[0][0] + 1, wc[1][0] - 1) for wy in (wc[0][1] + 1, wc[1][1] - 1)})
            sel = [r for r, b0, b1, p in placed
                   if b1[0] >= cov[0][0] and b0[0] <= cov[1][0] and b1[1] >= cov[0][1] and b0[1] <= cov[1][1]]
            core_refs = [r for r, b0, b1, p in placed
                         if wc[0][0] <= p[0] < wc[1][0] and wc[0][1] <= p[1] < wc[1][1]]
            wcov = [centre[0] + cov[0][0] / SCALE, centre[1] + cov[0][1] / SCALE,
                    centre[0] + cov[1][0] / SCALE, centre[1] + cov[1][1] / SCALE]
            lf_cov, anyland, _ = land_fraction(world, *wcov, water)
            lf_core, _, hcore = land_fraction(world, wc[0][0], wc[0][1], wc[1][0], wc[1][1], water)
            f = summarise(world, sel, 'exterior', True)
            fc = summarise(world, core_refs, 'exterior', True)
            lamps3 = max(sum(lamp_cells.get((a + dx, b + dy), 0) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
                         for a, b in core_cells)
            f.update(map=fid + '%03d' % n, space='exterior', frame=fid, centre_cell=[fx, fy], region='r%02d' % n,
                     core=core, coverage=cov, core_cells=['%d,%d' % c for c in core_cells],
                     cov_area=(cov[1][0] - cov[0][0]) * (cov[1][1] - cov[0][1]),
                     land_frac_cov=round(lf_cov, 4), land_frac_core=round(lf_core, 4), any_land=anyland,
                     core_refs_total=fc['refs_total'], core_npc=fc['npc'], core_creatures=fc['creatures'] + fc['levc'],
                     core_evr_refs=fc['evr_refs'], core_cur_refs=fc['cur_refs'], core_items=fc['items'],
                     core_lights=fc['lights'], lamps_3x3=lamps3, coord_max=float(max(abs(v) for v in settings['bounds'][1])),
                     terrain_max_q=round(hcore * SCALE, 1) if hcore is not None else None)
            yield f


def world_frames(world, prefix, anchor, cells=None):
    """Regular 3x3-cell frame grid covering every exterior cell with references or LAND.
    anchor: one frame centre cell; the grid is every third cell from it."""
    pool = [c for c in (cells if cells is not None else world.cells) if not c['interior']
            and (c['refs'] or (c['x'], c['y']) in world.land)]
    if not pool:
        return []
    xs = [c['x'] for c in pool]
    ys = [c['y'] for c in pool]
    ax, ay = anchor
    x0 = ax + 3 * math.floor((min(xs) - 1 - ax) / 3)
    y0 = ay + 3 * math.floor((min(ys) - 1 - ay) / 3)
    frames = []
    for fx in range(x0, max(xs) + 3, 3):
        for fy in range(y0, max(ys) + 3, 3):
            frames.append(('%s%+03d%+03d' % (prefix, fx, fy), (fx, fy)))
    return frames


def reachable_interiors(masters):
    """Interior cell names (casefolded) a player can reach: through load doors
    from any exterior cell, or from a cell that a script or dialogue result
    names (scripts move the player with PositionCell), over every master."""
    doors, named, interiors = collections.defaultdict(set), set(), set()
    for m in masters.values():
        named |= m.get('script_strings', set())
        for c in m['cells']:
            if c['interior'] and not c['deleted']:
                interiors.add(c['name'].casefold())
            here = c['name'].casefold() if c['interior'] else None
            for r in c['refs']:
                if r.get('dest') and not r.get('del'):
                    doors[here].add(r['dcell'].casefold() if r.get('dcell') else None)
    seen, stack = set(), [None, *(n for n in interiors if n in named)]
    while stack:
        cell = stack.pop()
        if cell in seen:
            continue
        seen.add(cell)
        stack.extend(doors.get(cell, ()))
    return {n for n in interiors if n in seen}
