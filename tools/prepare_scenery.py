#!/usr/bin/env python3
"""Export owned base-game static NIFs to a private indexed scene; no native loader yet."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import BSA, normpath
from mwad.paths import child_ci, ensure_external, read_workspace, resolve_data_files
from mwad.scene import pack_geometry, unpack_geometry, visible_refs, resident_set, read_asset
from scenery_selection import load_groups, select_source_refs, validate_groups


def nif_reader():
    # PyFFI 2.2.3 imports time.clock and picks the newer byte-sized duplicate
    # num_uv_sets field. TES3 4.0.0.2 stores that field as a ushort instead.
    # This process only accepts TES3; do not apply this adapter to newer NIFs.
    if not hasattr(time, 'clock'):
        time.clock = time.perf_counter
    from pyffi.formats.nif import NifFormat
    if not getattr(NifFormat, '_mwad_tes3_adapter', False):
        original = NifFormat.NiGeometryData.__init__
        def init(self, *args, **kwargs):
            original(self, *args, **kwargs)
            self._num_uv_sets_value_ = NifFormat.ushort()
        NifFormat.NiGeometryData.__init__ = init
        NifFormat._mwad_tes3_adapter = True
    return NifFormat


def bsa_read(bsa, name):
    e = bsa.entries[normpath(name)]
    with bsa.path.open('rb') as f:
        f.seek(e['offset'])
        raw = f.read(e['bytes'])
    if len(raw) != e['bytes']:
        raise ValueError('Truncated BSA asset')
    return raw


def model_geometry(raw, N, collision=False):
    import numpy as np
    if not raw.startswith(b'NetImmerse File Format, Version 4.0.0.2\n'):
        raise ValueError('Only base-game TES3 NIF 4.0.0.2 is supported')
    data = N.Data(); data.read(io.BytesIO(raw))
    vertices, faces, materials = [], [], []
    skipped = []
    def visit(node, parent, hidden=False, in_collision=False):
        if not isinstance(node, N.NiAVObject):
            return
        name = node.name.decode('cp1252')
        in_collision = in_collision or isinstance(node, N.RootCollisionNode) or name.casefold() == 'rootcollisionnode'
        hidden = hidden or bool(node.flags & 1)
        transform = np.array(node.get_transform().as_list()) @ parent
        if isinstance(node, N.NiTriShape) and (in_collision if collision else not hidden and not in_collision):
            if node.skin_instance is not None:
                skipped.append(name + ': skinned shape'); return
            g = node.data
            if g is None or not g.num_vertices or not g.num_triangles:
                return
            diffuse, alpha, texture = [1., 1., 1.], 1., None
            for p in ([] if collision else node.properties):
                if isinstance(p, N.NiMaterialProperty):
                    diffuse = [p.diffuse_color.r, p.diffuse_color.g, p.diffuse_color.b]; alpha = p.alpha
                if isinstance(p, N.NiTexturingProperty) and p.has_base_texture and p.base_texture.source:
                    texture = p.base_texture.source.file_name.decode('cp1252')
            material = len(materials)
            materials.append({'texture_source': texture, 'diffuse': diffuse, 'alpha': alpha,
                              'source_shape': name})
            start = len(vertices)
            for i, v in enumerate(g.vertices):
                position = np.array([v.x, v.y, v.z, 1.]) @ transform
                uv = g.uv_sets[0][i] if g.num_uv_sets and g.uv_sets else None
                colour = g.vertex_colors[i] if g.has_vertex_colors else None
                rgba = [colour.r, colour.g, colour.b, colour.a] if colour else [1., 1., 1., 1.]
                vertices.append([*map(float, position[:3]), uv.u if uv else 0., uv.v if uv else 0.,
                                 *[round(max(0., min(1., c)) * 255) for c in rgba]])
            faces.extend([start + a, start + b, start + c, material] for a, b, c in g.get_triangles())
        for child in getattr(node, 'children', []):
            if child is not None:
                visit(child, transform, hidden, in_collision)
    for root in data.roots:
        visit(root, np.eye(4))
    if not vertices or not faces:
        raise ValueError('No supported visible static triangles')
    packet = pack_geometry(vertices, faces, len(materials))
    unpack_geometry(packet)
    points = np.array(vertices)[:, :3]
    return packet, materials, [points.min(axis=0).tolist(), points.max(axis=0).tolist()], skipped


def world_bounds(bounds, ref):
    import numpy as np
    # TES3 reference rotations are clockwise about their axes (radians).
    x, y, z = [-a for a in ref['rotation_radians']]
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
    ry = np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
    rz = np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])
    corners = np.array([[a,b,c] for a in (bounds[0][0],bounds[1][0]) for b in (bounds[0][1],bounds[1][1]) for c in (bounds[0][2],bounds[1][2])])
    points = corners @ (rz @ ry @ rx).T * ref['scale'] + ref['position']
    return [points.min(axis=0).tolist(), points.max(axis=0).tolist()]


def prepare(workspace, out, radius=4096, texture_size=64):
    from PIL import Image
    workspace, state = read_workspace(workspace)
    data_files = resolve_data_files(state['data_files'])
    placements = json.loads((workspace / 'generated/seyda-neen/placements.json').read_text())
    centre = [-11200., -71504., 400.]
    refs, groups = select_source_refs(placements, centre, radius, load_groups())
    return export_refs(data_files,out,refs,groups,centre,radius,texture_size)


def export_refs(data_files,out,refs,groups,centre,radius=4096,texture_size=64,metadata=None):
    from PIL import Image
    out = ensure_external(out, 'scenery export'); out.mkdir(parents=True, exist_ok=False)
    bsa = BSA(child_ci(data_files, 'Morrowind.bsa'))
    profiles={name:profile for group in groups.values()
              for name,profile in group.get('visual_profiles',{}).items()}
    names = sorted({normpath('meshes/' + r['model']) for r in refs})
    N = nif_reader()
    index = {'format': 'MWSC1', 'version': 1, 'centre': centre, 'study_radius': radius,
             'units': 'original Morrowind world units; XYZ z-up; reference rotations retained',
             'scope': 'base master STAT/DOOR and explicitly grouped visible ACTI; static preview, no opening scripts',
             'groups': groups,
             'models': [], 'textures': [], 'references': [], 'errors': [], 'chunk_size': 2048, 'chunks': {}}
    if metadata:index.update(metadata)
    texture_ids = {}
    archive = out / 'scenery.mwpak'
    def put(f, raw):
        pad = (-f.tell()) % 512
        f.write(bytes(pad)); offset = f.tell(); f.write(raw)
        return {'offset': offset, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    with archive.open('xb') as f:
        for name in names:
            try:
                raw = bsa_read(bsa, name)
                packet, materials, bounds, skipped = model_geometry(raw, N)
                collision_record = None
                if profiles.get(name,{}).get('collision_source') == 'root_node':
                    cpacket, _, cbounds, cskipped = model_geometry(raw, N, collision=True)
                    cv, cf, _ = unpack_geometry(cpacket)
                    collision_record={'source':'NIF RootCollisionNode','bounds':cbounds,
                                      'vertices':len(cv),'triangles':len(cf),
                                      'skipped_shapes':cskipped, **put(f,cpacket)}
                texture_refs = []
                for material in materials:
                    path = material['texture_source']
                    material['texture_index'] = None
                    if not path: continue
                    requested = normpath(path)
                    if not requested.startswith('textures/'): requested = 'textures/' + requested
                    candidates = [str(Path(requested).with_suffix('.dds')), requested]
                    texture = next((p for p in candidates if p in bsa.entries), None)
                    if texture is None: raise ValueError('Missing base BSA texture: ' + requested)
                    if texture not in texture_ids:
                        source = bsa_read(bsa, texture)
                        with Image.open(io.BytesIO(source)) as image:
                            image = image.convert('RGBA'); image.thumbnail((texture_size, texture_size), Image.Resampling.LANCZOS)
                        w, h = image.size
                        encoded = struct.pack('>4sHH', b'MWT1', w, h) + image.tobytes()
                        texture_ids[texture] = len(index['textures'])
                        index['textures'].append({'source': texture, 'source_sha256': hashlib.sha256(source).hexdigest(),
                                                  'width': w, 'height': h, **put(f, encoded)})
                    ti = texture_ids[texture]; material['texture_index'] = ti; texture_refs.append(ti)
                index['models'].append({'source': name, 'source_sha256': hashlib.sha256(raw).hexdigest(),
                                        'vertices': len(unpack_geometry(packet)[0]), 'triangles': len(unpack_geometry(packet)[1]),
                                        'bounds': bounds, 'materials': materials, 'textures': sorted(set(texture_refs)),
                                        'collision': collision_record,
                                        'skipped_shapes': skipped, **put(f, packet)})
                print('model',len(index['models']),'/',len(names),name,flush=True)
            except (ValueError, KeyError, struct.error) as e:
                index['errors'].append({'source': name, 'error': str(e)})
    model_ids = {m['source']: i for i, m in enumerate(index['models'])}
    for ref in refs:
        name = normpath('meshes/' + ref['model'])
        if name not in model_ids: continue
        m = model_ids[name]
        bounds = world_bounds(index['models'][m]['bounds'], ref)
        n = len(index['references'])
        index['references'].append({**ref, 'model_index': m, 'bounds': bounds})
        for y in range(math.floor(bounds[0][1]/2048), math.floor(bounds[1][1]/2048)+1):
            for x in range(math.floor(bounds[0][0]/2048), math.floor(bounds[1][0]/2048)+1):
                index['chunks'].setdefault(f'{x},{y}', []).append(n)
    # A failed hull conversion must not silently leave an orphan hatch again.
    validate_groups(index['references'], groups)
    # Read every payload independently, through the same seek/extent contract.
    collisions=[m['collision'] for m in index['models'] if m.get('collision')]
    with archive.open('rb') as f:
        for record in index['models'] + index['textures'] + collisions: read_asset(f, record)
    report = {'scope': index['scope'], 'selected_references': len(refs), 'converted_references': len(index['references']),
              'models': len(index['models']), 'textures': len(index['textures']), 'archive_bytes': archive.stat().st_size,
              'geometry_bytes': sum(m['bytes'] for m in index['models']),
              'collision_bytes': sum(m['bytes'] for m in collisions), 'errors': index['errors'],
              'camera_spheres': {str(d): resident_set(index, visible_refs(index, centre, d)) for d in (768,1536,2304,3840)},
              'note': 'Host geometry/cache accounting only. No Amiga frame-rate or disk-throughput claim. RGBA textures are an intermediate, not a Paula/AGA format.'}
    (out/'scenery-index.json').write_text(json.dumps(index,indent=2)+'\n')
    (out/'scenery-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--radius',type=int,choices=range(512,16385),default=4096)
    p.add_argument('--texture-size',type=int,choices=(32,64,128),default=64)
    a=p.parse_args()
    print(json.dumps(prepare(a.workspace,a.out,a.radius,a.texture_size),indent=2))

if __name__=='__main__': main()
