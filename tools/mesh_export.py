#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Export one mesh as Wavefront .OBJ files for an A/B look in the AmiWind Toolkit (Mesh Compare).

Each variant goes through the builder's own code, never a second implementation:

  original        the source NIF triangles as the converter reads them (prepare_scenery.model_geometry)
  current         the shipped converter: the mesh's reduction profile (static_lod.reduce_for_profile) and the
                  converter's face list (mesh_geometry.surface_polygons + split_surface)
  merge           current, then planar merge (tools/planar_merge.py)              } when this checkout has the
  meshopt+merge   meshoptimizer in place of the reducer, then planar merge        } mesh methods (mesh_methods.py)

Units are Quake units (Morrowind units x 0.25, as the converter writes them), Z up; the header line says so. Every
face is written counter-clockwise seen from its front (its own normal, as the converter computes it), which is what
OBJ viewers expect. The original's triangles keep their texture coordinates (vt, V counted from the bottom as OBJ
does; the game counts it from the top). Output is deterministic (fixed number format, fixed order) and each file is
recorded with its SHA-256. The .MTL names materials and their texture file names only (the reader's texture_source);
no texture or other game data is written. The OBJ files are made from your own game files: keep them private. To
convert a model to OBJ+MTL in either unit, with its textures, or back to the builder's form: tools/mesh_convert.py.

  python3 tools/mesh_export.py meshes/x/ex_hlaalu_b_01.nif --data-files DIR --methods original,current --out DIR
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

BASE_METHODS = ('original', 'current')
CANDIDATES = ('merge', 'meshopt+merge')
METHODS = BASE_METHODS + CANDIDATES
MESH_NAME = re.compile(r'^meshes/[a-z0-9_][a-z0-9_ ./-]{0,150}\.nif$')
QUAKE = 0.25


def check_mesh(name):
    """A mesh source name as the game data names it (meshes/.../x.nif, lower case, no '..')."""
    s = str(name).replace('\\', '/').lower()
    if not MESH_NAME.match(s) or '..' in s or '//' in s:
        raise ValueError('not a mesh name: %r' % name)
    return s


def available_methods():
    """The methods this checkout can export (the candidates need tools/planar_merge.py and tools/mesh_methods.py)."""
    return METHODS if all((ROOT / 'tools' / n).is_file() for n in ('planar_merge.py', 'mesh_methods.py')) else BASE_METHODS


def _converter_polygons(v, f, tex):
    try:
        from planar_merge import converter_polygons
        return converter_polygons(v, f, tex)
    except ImportError:                     # the same composition planar_merge.converter_polygons makes
        import numpy as np
        from mesh_geometry import split_surface, surface_polygons
        return [(patch, mat, ax, off, normal) for poly, mat, ax, off, normal in surface_polygons(v, f)
                for patch in split_surface(poly, np.column_stack((ax.T * tex, off * tex)))]


def profile_for(source, triangles, space=None):
    """The reduction profile the builder uses for this mesh: the town converter's (town_model_profile) where it
    reduces the mesh, else the scenery group's, the open world's or the interior's (seam_audit.converter_profiles,
    the paths that reduce it); {} when no path reduces it."""
    from seam_audit import converter_profiles
    profiles = converter_profiles(source, triangles)
    if space:
        return dict(profiles[space], space=space) if space in profiles else {}
    for key in ('town', 'group', 'world', 'interior'):
        if key in profiles:
            return dict(profiles[key], space=key)
    return {}


def load_mesh(data_files, source):
    """(vertices N x 5, faces M x 4, materials) of a mesh from your own game files, as the converter reads it."""
    import numpy as np
    from prepare_scenery import model_geometry, nif_reader
    from mwad.scene import unpack_geometry
    from world_estimate_data import MeshSource
    raw, _ = MeshSource(data_files).read(source)
    packet, materials, _, _ = model_geometry(raw, nif_reader(), repair_uv=True)
    vv, ff, _ = unpack_geometry(packet)
    return np.array(vv, float), np.array(ff, int), materials


def variants(v, f, materials, profile, methods, source='mesh'):
    """{method: [(polygon points (k x 3, Quake units, CCW about its normal), material index)]} for the methods."""
    import numpy as np
    from static_lod import reduce_for_profile
    tex = profile.get('texture_size', 64)
    out = {}
    for m in methods:
        if m not in METHODS:
            raise ValueError('unknown method %s (known: %s)' % (m, ', '.join(METHODS)))
        if m in CANDIDATES and m not in available_methods():
            raise ValueError('method %s needs the mesh methods (tools/mesh_methods.py) in this checkout' % m)
        if m == 'original':
            polys = []
            for face in f:
                p = v[face[:3], :3] * QUAKE
                polys.append((p, int(face[3]) if len(face) > 3 else 0))
            out[m] = polys
            continue
        prof = dict(profile)
        if m == 'meshopt+merge' and prof.get('ratio') and prof['ratio'] < 1:
            prof['reducer'] = 'meshopt'
        rv, rf, _ = reduce_for_profile(v, f, prof, materials, source)
        rv, rf = np.asarray(rv, float), np.asarray(rf, int)
        if m == 'current':
            faces = _converter_polygons(rv, rf, tex)
        else:
            from planar_merge import merged_polygons
            base = _converter_polygons(rv, rf, tex)
            merged = merged_polygons(rv, rf, tex)
            faces = merged if len(merged) < len(base) else base      # the builder keeps the smaller list
        out[m] = _front_facing(faces)
    return out


def _front_facing(faces):
    """[(polygon points, CCW about its normal, material)] of a converter face list."""
    import numpy as np
    polys = []
    for patch, mat, _ax, _off, normal in faces:
        pts = np.asarray(patch, float)
        if len(pts) >= 3:
            n = np.zeros(3)
            for i in range(len(pts)):
                n += np.cross(pts[i], pts[(i + 1) % len(pts)])
            if float(n @ np.asarray(normal, float)) < 0:
                pts = pts[::-1]
            polys.append((pts, int(mat)))
    return polys


def _grey(_material):
    """The picture a geometry-only panel bake reads (the panel's shape does not depend on its pixels)."""
    import numpy as np
    return np.full((1, 1, 3), 180, dtype=np.uint8)


def profile_faces(v, f, materials, profile, source='mesh'):
    """(faces, drawn vertices, drawn triangles) of one mesh under a COMPLETE converter profile, in the order
    prepare_mesh_bsp._prepare_model draws it: the profile's reduction (ratio, reducer, error bound), a flattened or
    panel profile's panel (its shape only: the picture is not baked here), a visual primitive in place of the mesh,
    then planar merge when the profile's faces are 'merge' (planar_merge.polygons: the smaller list), else the
    converter's faces, every face split at the engine's surface limit. faces = [(points in Quake units, CCW about the
    normal, material)] as variants() gives them; the drawn triangles are what the faces were made from, in Morrowind
    units, for the quality measures (mesh_methods.reduction_quality)."""
    import numpy as np
    from static_lod import reduce_for_profile
    tex = profile.get('texture_size', 64)
    rv, rf = np.asarray(v, float), np.asarray(f, int)
    if profile.get('ratio'):
        rv, rf, _ = reduce_for_profile(rv, rf, profile, materials, source)
        rv, rf = np.asarray(rv, float), np.asarray(rf, int)
    if profile.get('flatten') or profile.get('visual_panel'):
        from surface_flatten import bake_panel
        panel = profile.get('visual_panel')
        if panel:
            axis = int(panel['axis'])
            projection = dict(panel, plane=float(np.asarray(v, float)[:, axis].min()) + float(panel['front_offset']))
        else:
            projection = profile['flatten']
        rv, rf, _, _ = bake_panel(np.asarray(v, float), np.asarray(f, int), materials, _grey, projection)
        if panel and panel.get('two_sided'):
            rf = np.concatenate([rf, rf[:, [0, 2, 1, 3]]])
        rv, rf = np.asarray(rv, float), np.asarray(rf, int)
    if profile.get('visual_primitive'):
        from visual_primitives import make_visual
        rv, rf = make_visual(profile['visual_primitive'])
        rv, rf = np.asarray(rv, float), np.asarray(rf, int)
    if profile.get('faces') == 'merge':
        from planar_merge import polygons
        faces, _ = polygons(rv, rf, tex)
    else:
        faces = _converter_polygons(rv, rf, tex)
    return _front_facing(faces), rv, rf


def _num(x):
    s = '%.5f' % x
    s = s.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


UNITS_LINE = ('# units: quake (AmiWind units = Morrowind units x 0.25); Z up; texture V counted from the bottom (OBJ); '
              'faces counter-clockwise seen from their front')


def obj_text(polys, name, mtl=None, materials=None, uvs=None):
    """An OBJ document for a polygon list; shared vertices are written once (exact match, first-seen order). UVS: one
    (u, v) per corner of every polygon, in the game's convention (V counted from the top, as the NIF stores it); they
    are written as OBJ texture coordinates (V counted from the bottom: 1 - v) and every face as v/vt."""
    index, verts, tindex, tverts = {}, [], {}, []
    for k, (pts, _) in enumerate(polys):
        for i, p in enumerate(pts):
            key = tuple(_num(c) for c in p)
            if key not in index:
                index[key] = len(verts) + 1
                verts.append(key)
            if uvs is not None:
                u, v = uvs[k][i]
                tkey = (_num(u), _num(1.0 - v))
                if tkey not in tindex:
                    tindex[tkey] = len(tverts) + 1
                    tverts.append(tkey)
    out = ['# AmiWind mesh export: %s' % name, UNITS_LINE, '# %d faces, %d vertices' % (len(polys), len(verts))]
    if mtl:
        out.append('mtllib %s' % mtl)
    out += ['v %s %s %s' % k for k in verts]
    out += ['vt %s %s' % k for k in tverts]
    current = None
    for k, (pts, mat) in enumerate(polys):
        if mtl and mat != current:
            out.append('usemtl m%d' % mat)
            current = mat
        if uvs is None:
            out.append('f ' + ' '.join(str(index[tuple(_num(c) for c in p)]) for p in pts))
        else:
            out.append('f ' + ' '.join('%d/%d' % (index[tuple(_num(c) for c in p)], tindex[(_num(u), _num(1.0 - v))])
                                       for p, (u, v) in zip(pts, uvs[k])))
    return '\n'.join(out) + '\n', len(polys), len(verts)


def texture_name(material):
    """The file name of a material's texture as the game names it (no folder), or None. The NIF reader names it
    texture_source (prepare_scenery.model_geometry); texture and texture_name are the older spellings."""
    mat = material or {}
    tex = mat.get('texture_source') or mat.get('texture') or mat.get('texture_name')
    return Path(str(tex).replace('\\', '/')).name if tex else None


def mtl_text(materials, textures=None):
    """The MTL of a material list: one newmtl m<k> per material with its texture's file name (map_Kd). TEXTURES
    {material index: file name} names files written beside it (PNG pictures) in place of the game's names."""
    out = ['# AmiWind mesh export: material names and texture file names only (no texture data)']
    for k, mat in enumerate(materials or []):
        out.append('newmtl m%d' % k)
        tex = (textures or {}).get(k) or texture_name(mat)
        if tex:
            out.append('map_Kd %s' % tex)
    return '\n'.join(out) + '\n'


def file_stem(source, method):
    return re.sub(r'[^a-z0-9_.+-]', '_', source[len('meshes/'):-len('.nif')].replace('/', '__')) + '.' + method.replace('+', '-')


def export(v, f, materials, profile, methods, out_dir, source='meshes/mesh.nif'):
    """Write the OBJ files (and one MTL) of the methods into OUT_DIR; returns the record of each file."""
    import numpy as np
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = file_stem(source, 'x')[:-2]
    mtl_name = base + '.mtl'
    (out_dir / mtl_name).write_bytes(mtl_text(materials).encode('utf-8'))
    rows = []
    for method, polys in variants(v, f, materials, profile, methods, source).items():
        # the source triangles keep their texture coordinates (v / vt / f v/vt); a converter face list carries a
        # texture mapping per face, not per corner, and is written with positions only
        uvs = [np.asarray(v, float)[face[:3], 3:5] for face in f] if method == 'original' and np.asarray(v).shape[1] >= 5 else None
        text, nf, nv = obj_text(polys, '%s (%s)' % (source, method), mtl_name, materials, uvs)
        name = file_stem(source, method) + '.obj'
        data = text.encode('utf-8')
        (out_dir / name).write_bytes(data)
        rows.append({'source': source, 'method': method, 'file': name, 'faces': nf, 'vertices': nv,
                     'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    record = {'format': 'amiwind-mesh-export-1', 'source': source, 'profile': profile, 'files': rows}
    (out_dir / (base + '.export.json')).write_bytes((json.dumps(record, indent=1, sort_keys=True) + '\n').encode('utf-8'))
    return record


def export_mesh(data_files, source, methods, out_dir, space=None):
    source = check_mesh(source)
    v, f, materials = load_mesh(data_files, source)
    profile = profile_for(source, len(f), space)
    return export(v, f, materials, profile, methods, out_dir, source)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('mesh', help='mesh source name, e.g. meshes/x/ex_hlaalu_b_01.nif')
    p.add_argument('--data-files', required=True, help='your own Morrowind Data Files folder')
    p.add_argument('--methods', default='original,current', help='comma list of: ' + ', '.join(METHODS))
    p.add_argument('--space', choices=('town', 'group', 'world', 'interior'), help='the converter path whose profile to use')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(argv)
    methods = [m.strip() for m in a.methods.split(',') if m.strip()]
    record = export_mesh(a.data_files, a.mesh, methods, a.out, a.space)
    for row in record['files']:
        print('%-14s %6d faces %6d vertices  %s  %s' % (row['method'], row['faces'], row['vertices'], row['sha256'][:16], row['file']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
