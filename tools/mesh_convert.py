#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Convert a model between the game's form, the AmiWind builder's forms and OBJ+MTL, in Morrowind units, Quake
(AmiWind) units or any scale (docs/MESH_CONVERT.md).

    python3 tools/mesh_convert.py IN OUT [--data-files DIR] [--units morrowind|quake | --scale N]
                                  [--in-units morrowind|quake | --in-scale N] [--textures] [--model N] [--frame N]

IN (by its form):
  meshes/l/light_com_lantern_02.nif   a model of your own game files by its path (loose or in an archive)
  light_com_lantern_02                a record id: its model, through the merged masters of your game files
  FILE.nif                            a NIF file
  FILE.obj                            an OBJ, with the MTL its mtllib line names; its units from the header line this
                                      tool writes, else --in-units / --in-scale (never guessed)
  FILE.bsp, FILE.chim                 a map as the build wrote it (BSP29-shaped): the faces of its model --model N
                                      (default 0; a CHIM map holds collision-only models: its geometry is in the CHIM world)
  FILE.mdl                            an actor or item model as the build wrote it (Quake alias model), frame --frame N
  FILE.mwg                            the builder's mesh form, as this tool writes it
OUT (by its extension):
  FILE.obj                            OBJ + MTL beside it; --textures also writes the textures as PNG beside it, from
                                      your own game files (private: a note file says so)
  FILE.mwg                            the builder's mesh form: the geometry packet the scenery export stores for every
                                      model (Morrowind units, mwad.scene), and FILE.mesh.json beside it (materials and
                                      their textures, units, counts, SHA-256)

Units: Morrowind units are the game's; Quake units (AmiWind units) are Morrowind units x 0.25 (docs/UNITS.md).
--units / --scale set the output (N = output units per Morrowind unit; default Morrowind units), --in-units /
--in-scale the input where the file does not say it itself (an OBJ without this tool's header line). Every OBJ this
tool writes names its units in its header, and the reader takes them from there, so nothing is multiplied by hand.
Both directions handle the conventions the same way: Z up (no axis swap); texture V counted from the bottom in OBJ
and from the top in the game's files (v_obj = 1 - v); faces counter-clockwise seen from their front in OBJ, the game's
NIF and the builder's form, clockwise in the engine's map and alias models (turned on the way in).

Made from your own game files, an output is private: keep it to yourself unless it is your own work. A NIF is never
written: nothing in the pipeline reads one back.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):          # src first (src/mwad before tools/mwad.py)
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

UNITS = {'morrowind': 1.0, 'quake': 0.25}            # output units per Morrowind unit (prepare_quake.SCALE)
QUAKE = UNITS['quake']
HEADER = '# amiwind-mesh:'                            # the machine-readable header line of every OBJ written here
FORMS = ('game', 'record', 'nif', 'obj', 'bsp', 'mdl', 'mwg')
MESH_FORM = 'amiwind-mesh-form-1'
PRIVATE_NOTE = ('Made from your own game files: keep these files to yourself. They hold the game\'s geometry or '
                'pictures; never share or publish them.\n')


class ConvertError(ValueError):
    """A refusal with its reason (a missing unit, an unreadable file, an output that exists)."""


def scale_of(units=None, scale=None, what='output'):
    """(name, output units per Morrowind unit) of --units / --scale, or (None, None) when neither is given."""
    if units and scale is not None:
        raise ConvertError('give the %s units or a scale, not both' % what)
    if units:
        if units not in UNITS:
            raise ConvertError('unknown %s units %r (known: %s)' % (what, units, ', '.join(UNITS)))
        return units, UNITS[units]
    if scale is not None:
        if not scale > 0:
            raise ConvertError('the %s scale must be above 0' % what)
        name = next((n for n, s in UNITS.items() if abs(s - scale) < 1e-12), 'scaled')
        return name, float(scale)
    return None, None


def _num(x, digits=7):
    s = ('%.' + str(digits) + 'f') % x
    s = s.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def form_of(name):
    """The form of an input by its name (FORMS)."""
    from map_files import FRAME_EXT, LEGACY_EXT      # the map file extensions (.chim, .bsp) from their one place
    low = str(name).replace('\\', '/').lower()
    path = Path(name)
    for ext, form in (('.obj', 'obj'), (LEGACY_EXT, 'bsp'), (FRAME_EXT, 'bsp'), ('.mdl', 'mdl'), ('.mwg', 'mwg')):
        if low.endswith(ext):
            return form
    if low.endswith('.nif'):
        return 'nif' if path.is_file() else 'game'
    if '/' in low or '.' in Path(low).name:
        raise ConvertError('%s: not a model path, a record id or a known file (.nif .obj .bsp .chim .mdl .mwg)' % name)
    return 'record'


def new_mesh(vertices, faces, materials, source, private, colours=None):
    """The one form every reader returns and every writer takes: vertices (n x 5: x y z in Morrowind units, u v with V
    counted from the top), faces (m x 4: a b c material, counter-clockwise seen from the front), materials [{name,
    texture}], RGBA per vertex."""
    import numpy as np
    v = np.asarray(vertices, float).reshape(-1, 5)
    f = np.asarray(faces, np.int64).reshape(-1, 4)
    if not len(f):
        raise ConvertError('%s: no triangles to convert' % source)
    if f[:, :3].min() < 0 or f[:, :3].max() >= len(v) or f[:, 3].min() < 0 or f[:, 3].max() >= len(materials):
        raise ConvertError('%s: a face names a vertex or material that is not there' % source)
    if not np.isfinite(v).all():
        raise ConvertError('%s: a position or texture coordinate is not a number' % source)
    c = np.full((len(v), 4), 255, np.uint8) if colours is None else np.asarray(colours, np.uint8).reshape(-1, 4)
    return {'vertices': v, 'faces': f, 'colours': c, 'materials': list(materials), 'source': str(source),
            'private': bool(private)}


# ------------------------------------------------------------------ the game side

def from_nif(raw, source):
    """A NIF as the builder's converter reads it (prepare_scenery.model_geometry: the visible static triangles, the
    game's root rule, Morrowind units)."""
    from mesh_export import texture_name
    from mwad.scene import unpack_geometry
    from prepare_scenery import model_geometry, nif_reader
    try:
        packet, materials, _, _ = model_geometry(raw, nif_reader(), repair_uv=True)
        vv, ff, count = unpack_geometry(packet)
    except Exception as exc:  # noqa: BLE001 - every reader failure becomes the one refusal
        raise ConvertError('%s: not readable as static triangles (%s: %s)' % (source, type(exc).__name__, exc)) from exc
    import numpy as np
    v = np.asarray(vv, float)
    mats = [{'name': 'm%d' % k, 'texture': texture_name(materials[k]) if k < len(materials) else None}
            for k in range(count)]
    return new_mesh(v[:, :5], ff, mats, source, True, v[:, 5:9])


def model_of_record(masters, record):
    """The model path of a record id through the merged masters (later masters win), or a refusal."""
    import world_estimate_data as D
    objects = {}
    for name in D.MASTERS:
        if name in masters:
            objects.update(masters[name]['objects'])
    o = objects.get(record.casefold())
    if o is None:
        raise ConvertError('no record %r in the game files' % record)
    if o.get('deleted'):
        raise ConvertError('record %r is deleted by a later master' % record)
    if not o.get('model'):
        raise ConvertError('record %r (%s) has no model' % (record, o['type']))
    return o['model']


def read_game(data_files, name, form):
    """A model of the game files by its path or by a record id."""
    import world_estimate_data as D
    from mesh_export import check_mesh
    if not data_files:
        raise ConvertError('a model of the game files needs --data-files (your own Data Files folder)')
    model = model_of_record(D.census(data_files), name) if form == 'record' else check_mesh(name)
    try:
        raw, where = D.MeshSource(data_files).read(model)
    except (OSError, KeyError) as exc:
        raise ConvertError('%s is not in the game files (%s)' % (model, exc)) from exc
    mesh = from_nif(raw, model)
    mesh['data_files'] = str(data_files)
    mesh['archive'] = where
    return mesh


def find_texture(data_files, name):
    """(bytes, the name found) of a texture of the game files: the .dds the game loads first, else the named file;
    loose Data Files/Textures first, then the archives (later expansions first). None when not found."""
    from mwad.paths import child_ci
    from world_estimate_data import MeshSource
    from prepare_scenery import bsa_read
    stem = Path(name.replace('\\', '/')).name.lower()
    candidates = [str(Path(stem).with_suffix('.dds')), stem]
    loose = child_ci(Path(data_files), 'Textures', required=False)
    source = MeshSource(data_files)
    for cand in dict.fromkeys(candidates):
        if loose is not None and loose.is_dir():
            hit = child_ci(loose, cand, required=False)
            if hit is not None and hit.is_file():
                return hit.read_bytes(), cand
        for bsa in source.bsas:
            if 'textures/' + cand in bsa.entries:
                return bsa_read(bsa, 'textures/' + cand), cand
    return None


def write_textures(mesh, out_dir, stem):
    """{material index: PNG file name} of every material texture, decoded from the game files and written beside
    the output, with the private note. Each picture is named by its texture's own stem (tx_wood_brown_posts_02.png),
    so a model made from this OBJ and brought back still names the game's texture (the same stem), and two models
    converted into one folder share their pictures."""
    import io
    from PIL import Image
    data_files = mesh.get('data_files')
    if not data_files:
        raise ConvertError('--textures reads the pictures from your game files: give --data-files')
    out, done, missing = {}, {}, []
    for k, mat in enumerate(mesh['materials']):
        tex = mat.get('texture')
        if not tex:
            continue
        if tex not in done:
            found = find_texture(data_files, tex)
            if found is None:
                missing.append(tex)
                done[tex] = None
                continue
            png = '%s.png' % Path(found[1]).stem
            Image.open(io.BytesIO(found[0])).convert('RGBA').save(Path(out_dir) / png)
            done[tex] = png
        if done[tex]:
            out[k] = done[tex]
    (Path(out_dir) / ('%s.PRIVATE.txt' % stem)).write_text(PRIVATE_NOTE, encoding='utf-8', newline='\n')
    return out, missing


# ------------------------------------------------------------------ OBJ + MTL, both ways

def parse_header(text):
    """{key: value} of the header line this tool writes ('# amiwind-mesh: format=1 units=quake scale=0.25 ...')."""
    for line in text.splitlines()[:20]:
        if line.startswith(HEADER):
            return dict(part.split('=', 1) for part in line[len(HEADER):].split() if '=' in part)
    return {}


def read_mtl(path):
    """{material name: texture file name} of an MTL (map_Kd; the first one per material), in the MTL's order."""
    out, name = {}, None
    if not path.is_file():
        return out
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        parts = line.strip().split(None, 1)
        if not parts:
            continue
        if parts[0] == 'newmtl' and len(parts) > 1:
            name = parts[1].strip()
            out.setdefault(name, None)
        elif parts[0] == 'map_Kd' and name is not None and len(parts) > 1 and out.get(name) is None:
            out[name] = parts[1].strip().split()[-1]
    return out


def from_obj(path, in_scale=None):
    """An OBJ (and its MTL): positions divided by its scale into Morrowind units, texture V counted from the top again,
    polygons fanned into triangles in their order; the materials in the MTL's order (so a file this tool wrote keeps
    its material numbers), then any usemtl name the MTL does not list, in the order of first use."""
    path = Path(path)
    text = path.read_text(encoding='utf-8', errors='replace')
    head = parse_header(text)
    scale = float(head['scale']) if 'scale' in head else None
    if in_scale is not None and scale is not None and abs(in_scale - scale) > 1e-12 * max(1.0, scale):
        raise ConvertError('%s says its units are %s (scale %s), not the %s given' % (
            path.name, head.get('units'), head['scale'], _num(in_scale)))
    scale = scale if scale is not None else in_scale
    if scale is None:
        raise ConvertError('%s does not say its units: give --in-units morrowind|quake or --in-scale N' % path.name)
    positions, coords, polys, names = [], [], [], []
    current, library = None, {}
    for number, line in enumerate(text.splitlines(), 1):
        parts = line.split()
        if not parts or parts[0].startswith('#'):
            continue
        key = parts[0]
        try:
            if key == 'v':
                positions.append([float(x) for x in parts[1:4]])
            elif key == 'vt':
                coords.append([float(parts[1]), float(parts[2]) if len(parts) > 2 else 0.0])
            elif key == 'mtllib':
                library.update(read_mtl(path.parent / Path(line.split(None, 1)[1].strip()).name))
                names += [n for n in library if n not in names]
            elif key == 'usemtl':
                current = line.split(None, 1)[1].strip()
            elif key == 'f':
                if current not in names:
                    names.append(current)
                corners = []
                for c in parts[1:]:
                    bits = c.split('/')
                    vi = int(bits[0])
                    vi = vi - 1 if vi > 0 else len(positions) + vi
                    ti = None
                    if len(bits) > 1 and bits[1]:
                        ti = int(bits[1])
                        ti = ti - 1 if ti > 0 else len(coords) + ti
                    if not 0 <= vi < len(positions) or (ti is not None and not 0 <= ti < len(coords)):
                        raise ConvertError('%s line %d: an index past the vertices given so far' % (path.name, number))
                    corners.append((vi, ti))
                if len(corners) >= 3:
                    polys.append((corners, names.index(current)))
        except (IndexError, ValueError) as exc:
            if isinstance(exc, ConvertError):
                raise
            raise ConvertError('%s line %d: %s' % (path.name, number, line.strip()[:80])) from exc
    index, vertices, faces = {}, [], []
    if len(coords) == len(positions) and all(vi == ti for corners, _ in polys for vi, ti in corners):
        # one vt per v, used together (as this tool writes them): the file's own vertex order, so a round trip keeps it
        for i, (p, (u, v)) in enumerate(zip(positions, coords)):
            index[(i, i)] = i
            vertices.append([c / scale for c in p] + [u, 1.0 - v])
    for corners, mat in polys:
        ids = []
        for vi, ti in corners:
            if (vi, ti) not in index:
                index[(vi, ti)] = len(vertices)
                u, v = coords[ti] if ti is not None else (0.0, 1.0)
                vertices.append([c / scale for c in positions[vi]] + [u, 1.0 - v])
            ids.append(index[(vi, ti)])
        for i in range(1, len(ids) - 1):
            faces.append([ids[0], ids[i], ids[i + 1], mat])
    mats = [{'name': n or 'default', 'texture': library.get(n) if n else None} for n in names]
    private = any(line.startswith('# private') for line in text.splitlines()[:20])
    return new_mesh(vertices, faces, mats, path.name, private)


def obj_text(mesh, scale, units, mtl_name, textures=None):
    """(OBJ text, MTL text) of a mesh at SCALE (output units per Morrowind unit)."""
    v, f = mesh['vertices'], mesh['faces']
    out = ['# AmiWind mesh: %s' % mesh['source'],
           '%s format=1 units=%s scale=%s up=z v=up winding=ccw' % (HEADER, units, _num(scale, 12)),
           '# units: %s (%s per Morrowind unit; Quake units = Morrowind units x 0.25); Z up; texture V counted from the '
           'bottom; faces counter-clockwise seen from their front' % (units, _num(scale, 12)),
           '# %d triangles, %d vertices, %d materials' % (len(f), len(v), len(mesh['materials']))]
    if mesh['private']:
        out.append('# private: made from your own game files')
    out.append('mtllib %s' % mtl_name)
    out += ['v %s %s %s' % tuple(_num(c * scale) for c in p[:3]) for p in v]
    out += ['vt %s %s' % (_num(p[3]), _num(1.0 - p[4])) for p in v]
    names = [m['name'] for m in mesh['materials']]
    current = None
    for a, b, c, m in f:                                  # the faces in their order, a usemtl where the material changes
        if m != current:
            out.append('usemtl %s' % names[m])
            current = m
        out.append('f %d/%d %d/%d %d/%d' % (a + 1, a + 1, b + 1, b + 1, c + 1, c + 1))
    mtl = ['# AmiWind mesh: the materials of %s' % mesh['source']]
    if textures:
        mtl.append('# private: the pictures beside this file are made from your own game files')
    for k, m in enumerate(mesh['materials']):
        mtl += ['newmtl %s' % m['name'], 'Kd 1 1 1']
        tex = (textures or {}).get(k) or m.get('texture')
        if tex:
            mtl.append('map_Kd %s' % tex)
    return '\n'.join(out) + '\n', '\n'.join(mtl) + '\n'


def to_obj(mesh, path, scale, units, textures=False):
    path = Path(path)
    pictures, missing = ({}, [])
    if textures:
        pictures, missing = write_textures(mesh, path.parent, path.stem)
    obj, mtl = obj_text(mesh, scale, units, path.with_suffix('.mtl').name, pictures)
    path.write_text(obj, encoding='utf-8', newline='\n')
    path.with_suffix('.mtl').write_text(mtl, encoding='utf-8', newline='\n')
    return {'files': [path.name, path.with_suffix('.mtl').name] + sorted(set(pictures.values())), 'missing': missing}


# ------------------------------------------------------------------ the builder's mesh form

def to_mwg(mesh, path):
    """The geometry packet (mwad.scene.pack_geometry: Morrowind units, the game's texture convention, RGBA) and its
    record beside it (PATH.mesh.json)."""
    from mwad.scene import pack_geometry
    path = Path(path)
    rows = [tuple(float(x) for x in p) + tuple(int(c) for c in col) for p, col in zip(mesh['vertices'], mesh['colours'])]
    try:
        packet = pack_geometry(rows, [tuple(int(x) for x in face) for face in mesh['faces']], len(mesh['materials']))
    except ValueError as exc:
        raise ConvertError('%s: does not fit the builder\'s mesh form (%s)' % (mesh['source'], exc)) from exc
    path.write_bytes(packet)
    record = {'format': MESH_FORM, 'source': mesh['source'], 'units': 'morrowind', 'texture_v': 'from the top',
              'winding': 'counter-clockwise seen from the front', 'packet': path.name,
              'packet_sha256': hashlib.sha256(packet).hexdigest(), 'vertices': len(mesh['vertices']),
              'triangles': len(mesh['faces']), 'materials': mesh['materials'], 'private': mesh['private']}
    side = path.with_name(path.stem + '.mesh.json')
    side.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return {'files': [path.name, side.name], 'missing': []}


def from_mwg(path):
    import numpy as np
    from mwad.scene import unpack_geometry
    path = Path(path)
    raw = path.read_bytes()
    try:
        vv, ff, count = unpack_geometry(raw)
    except ValueError as exc:
        raise ConvertError('%s: not the builder\'s mesh form (%s)' % (path.name, exc)) from exc
    side = path.with_name(path.stem + '.mesh.json')
    record = json.loads(side.read_text(encoding='utf-8')) if side.is_file() else {}
    mats = record.get('materials') or [{'name': 'm%d' % k, 'texture': None} for k in range(count)]
    if len(mats) != count:
        raise ConvertError('%s: its record names %d materials, the packet %d' % (side.name, len(mats), count))
    v = np.asarray(vv, float)
    return new_mesh(v[:, :5], ff, mats, record.get('source') or path.name, record.get('private', False), v[:, 5:9])


# ------------------------------------------------------------------ the AmiWind side: maps and alias models

def from_bsp(path, model=0):
    """The faces of one model of a BSP29-shaped map as the build wrote it (Quake units, faces clockwise seen from the
    front, texture coordinates in texels): read through the face validator's lump reader (check_faces)."""
    import numpy as np
    from check_faces import (EDGES, FACES, FACE_DT, MODELS, MODEL_DT, SURFEDGES, TEXINFO, TEXINFO_DT, TEXTURES,
                             VERTEXES, MapError, records, split_lumps, texture_names)
    path = Path(path)
    raw = path.read_bytes()
    try:
        lumps = split_lumps(raw)
        verts = records(lumps[VERTEXES], np.dtype(('<f4', 3)), VERTEXES)
        edges = records(lumps[EDGES], np.dtype(('<u2', 2)), EDGES)
        surf = records(lumps[SURFEDGES], np.dtype('<i4'), SURFEDGES)
        faces = records(lumps[FACES], FACE_DT, FACES)
        texinfo = records(lumps[TEXINFO], TEXINFO_DT, TEXINFO)
        models = records(lumps[MODELS], MODEL_DT, MODELS)
    except MapError as exc:
        raise ConvertError('%s: not a BSP29-shaped map (%s)' % (path.name, exc)) from exc
    if not 0 <= model < len(models):
        raise ConvertError('%s has %d models; --model %d is not one' % (path.name, len(models), model))
    names = texture_names(lumps[TEXTURES])
    sizes = _miptex_sizes(lumps[TEXTURES])
    first, count = int(models[model]['firstface']), int(models[model]['numfaces'])
    if count <= 0:
        raise ConvertError('%s model %d draws no faces (a CHIM map keeps its geometry in the CHIM world)' % (path.name, model))
    vertices, out_faces, mats = [], [], {}
    for fi in range(first, first + count):
        face = faces[fi]
        fe, ne = int(face['firstedge']), int(face['numedges'])
        corners = [int(edges[e][0]) if e >= 0 else int(edges[-e][1]) for e in surf[fe:fe + ne]]
        info = texinfo[int(face['texinfo'])]
        miptex = int(info['miptex'])
        name = names[miptex] if 0 <= miptex < len(names) and names[miptex] else 'texture%d' % miptex
        w, h = sizes[miptex] if 0 <= miptex < len(sizes) and sizes[miptex] else (64, 64)
        mat = mats.setdefault(name, len(mats))
        vecs = np.asarray(info['vecs'], float)
        ids = []
        for corner in reversed(corners):              # clockwise seen from the front -> counter-clockwise
            p = np.asarray(verts[corner], float)
            s, t = p @ vecs[0, :3] + vecs[0, 3], p @ vecs[1, :3] + vecs[1, 3]
            ids.append(len(vertices))
            vertices.append([*(p / QUAKE), s / w, t / h])
        for i in range(1, len(ids) - 1):
            out_faces.append([ids[0], ids[i], ids[i + 1], mat])
    materials = [{'name': n, 'texture': n} for n, _ in sorted(mats.items(), key=lambda kv: kv[1])]
    return new_mesh(vertices, out_faces, materials, '%s model %d' % (path.name, model), True)


def _miptex_sizes(lump):
    """[(width, height) or None] of a BSP textures lump (each miptex: a 16-byte name, then width and height)."""
    if len(lump) < 4:
        return []
    count = struct.unpack_from('<i', lump)[0]
    out = []
    for i in range(max(count, 0)):
        if 4 + 4 * i + 4 > len(lump):
            break
        start = struct.unpack_from('<i', lump, 4 + 4 * i)[0]
        out.append(struct.unpack_from('<II', lump, start + 16) if 0 <= start and start + 24 <= len(lump) else None)
    return out


MDL_HEADER = struct.Struct('<4si3f3ff3f8if')


def from_mdl(path, frame=0):
    """One frame of a Quake alias model as the build wrote it (IDPO 6): its positions (Quake units, unpacked by the
    model's scale and origin), the skin's texture coordinates (a back-facing triangle on a seam reads the skin's
    right half, as the engine does) and its triangles (clockwise seen from the front, turned here)."""
    path = Path(path)
    raw = path.read_bytes()
    if len(raw) < MDL_HEADER.size or raw[:4] != b'IDPO' or struct.unpack_from('<i', raw, 4)[0] != 6:
        raise ConvertError('%s: not a Quake alias model (IDPO 6)' % path.name)
    head = MDL_HEADER.unpack_from(raw)
    scale, origin = head[2:5], head[5:8]
    nskins, w, h, nverts, ntris, nframes = head[12:18]
    at = MDL_HEADER.size
    try:
        for _ in range(nskins):
            kind = struct.unpack_from('<i', raw, at)[0]
            if kind == 0:
                at += 4 + w * h
            else:
                n = struct.unpack_from('<i', raw, at + 4)[0]
                at += 8 + 4 * n + n * w * h
        st = [struct.unpack_from('<3i', raw, at + 12 * i) for i in range(nverts)]
        at += 12 * nverts
        tris = [struct.unpack_from('<4i', raw, at + 16 * i) for i in range(ntris)]
        at += 16 * ntris
        frames = []
        for _ in range(nframes):
            kind = struct.unpack_from('<i', raw, at)[0]
            at += 4
            if kind == 0:
                frames.append(at + 24)
                at += 24 + 4 * nverts
            else:
                n = struct.unpack_from('<i', raw, at)[0]
                at += 4 + 8 + 4 * n
                for _k in range(n):
                    frames.append(at + 24)
                    at += 24 + 4 * nverts
        if not 0 <= frame < len(frames):
            raise ConvertError('%s has %d frames; --frame %d is not one' % (path.name, len(frames), frame))
        packed = raw[frames[frame]:frames[frame] + 4 * nverts]
        if len(packed) != 4 * nverts:
            raise struct.error('frame past the end of the file')
    except struct.error as exc:
        raise ConvertError('%s: truncated alias model (%s)' % (path.name, exc)) from exc
    vertices, faces, index = [], [], {}
    for front, *ids in tris:
        corners = []
        for vi in ids:
            onseam, s, t = st[vi]
            back = bool(onseam and not front)
            if (vi, back) not in index:
                x, y, z = packed[4 * vi:4 * vi + 3]
                p = [(c * scale[i] + origin[i]) / QUAKE for i, c in enumerate((x, y, z))]
                index[(vi, back)] = len(vertices)
                vertices.append(p + [(s + (w / 2 if back else 0) + 0.5) / w, (t + 0.5) / h])
            corners.append(index[(vi, back)])
        a, b, c = corners
        faces.append([a, c, b, 0])                        # clockwise seen from the front -> counter-clockwise
    return new_mesh(vertices, faces, [{'name': 'skin', 'texture': None}], '%s frame %d' % (path.name, frame), True)


# ------------------------------------------------------------------ the command

def read(name, data_files=None, in_scale=None, model=0, frame=0):
    """The mesh of IN, by its form (module text); in_scale only for an OBJ without this tool's header line."""
    form = form_of(name)
    if form in ('game', 'record'):
        return read_game(data_files, name, form), form
    if not Path(name).is_file():
        raise ConvertError('%s: no such file' % name)
    if form == 'nif':
        return from_nif(Path(name).read_bytes(), Path(name).name), form
    if form == 'obj':
        return from_obj(name, in_scale), form
    if form == 'bsp':
        return from_bsp(name, model), form
    if form == 'mdl':
        return from_mdl(name, frame), form
    return from_mwg(name), form


FIXED_UNITS = {'game': 'morrowind', 'record': 'morrowind', 'nif': 'morrowind', 'mwg': 'morrowind', 'bsp': 'quake',
               'mdl': 'quake'}


def convert(source, output, data_files=None, units=None, scale=None, in_units=None, in_scale=None, textures=False,
            model=0, frame=0, overwrite=False):
    """Read SOURCE, write OUTPUT; returns the record of what was written."""
    out_name, out_scale = scale_of(units, scale, 'output')
    if out_scale is None:
        out_name, out_scale = 'morrowind', 1.0
    in_name, in_value = scale_of(in_units, in_scale, 'input')
    form = form_of(source)
    if in_value is not None and form in FIXED_UNITS and abs(UNITS[FIXED_UNITS[form]] - in_value) > 1e-12:
        raise ConvertError('a %s input is in %s units; --in-units / --in-scale do not apply' % (form, FIXED_UNITS[form]))
    output = Path(output)
    kind = output.suffix.lower()
    if kind not in ('.obj', '.mwg'):
        raise ConvertError('%s: the output is .obj (OBJ + MTL) or .mwg (the builder\'s mesh form)' % output.name)
    if kind == '.mwg' and out_scale != 1.0:
        raise ConvertError('the builder\'s mesh form is in Morrowind units; --units / --scale do not apply')
    if textures and kind != '.obj':
        raise ConvertError('--textures writes PNG pictures beside an OBJ')
    if output.exists() and not overwrite:
        raise ConvertError('%s exists (give --overwrite to replace it)' % output)
    mesh, form = read(source, data_files, in_value, model, frame)
    if data_files and not mesh.get('data_files'):
        mesh['data_files'] = str(data_files)              # the pictures of a NIF file come from the game files too
    output.parent.mkdir(parents=True, exist_ok=True)
    written = to_obj(mesh, output, out_scale, out_name, textures) if kind == '.obj' else to_mwg(mesh, output)
    return {'source': mesh['source'], 'form': form, 'triangles': int(len(mesh['faces'])),
            'vertices': int(len(mesh['vertices'])), 'materials': len(mesh['materials']),
            'units': 'morrowind' if kind == '.mwg' else out_name, 'scale': 1.0 if kind == '.mwg' else out_scale,
            'private': mesh['private'], **written}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('input', help='a model path, a record id, or a .nif .obj .bsp .chim .mdl .mwg file')
    p.add_argument('output', help='a .obj (OBJ + MTL) or .mwg (the builder\'s mesh form) file')
    p.add_argument('--data-files', help='your own Morrowind Data Files folder (a model path, a record id, --textures)')
    p.add_argument('--units', choices=sorted(UNITS), help='the output\'s units (default morrowind)')
    p.add_argument('--scale', type=float, help='the output\'s scale: output units per Morrowind unit')
    p.add_argument('--in-units', choices=sorted(UNITS), help='an OBJ\'s units when its header does not say them')
    p.add_argument('--in-scale', type=float, help='an OBJ\'s scale (its units per Morrowind unit)')
    p.add_argument('--textures', action='store_true', help='write the textures as PNG beside the OBJ (private)')
    p.add_argument('--model', type=int, default=0, help='the model of a .bsp / .chim map (default 0)')
    p.add_argument('--frame', type=int, default=0, help='the frame of a .mdl (default 0)')
    p.add_argument('--overwrite', action='store_true', help='replace an existing output')
    a = p.parse_args(argv)
    try:
        record = convert(a.input, a.output, a.data_files, a.units, a.scale, a.in_units, a.in_scale, a.textures,
                         a.model, a.frame, a.overwrite)
    except ConvertError as exc:
        print('mesh_convert: %s' % exc, file=sys.stderr)
        return 2
    print('%s (%s): %d triangles, %d vertices, %d materials -> %s (%s units%s)' % (
        record['source'], record['form'], record['triangles'], record['vertices'], record['materials'],
        ', '.join(record['files']), record['units'], ', private' if record['private'] else ''))
    for tex in record['missing']:
        print('  texture not found in the game files: %s' % tex)
    return 0


if __name__ == '__main__':
    sys.exit(main())
