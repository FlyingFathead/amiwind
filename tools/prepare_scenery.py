#!/usr/bin/env python3
"""Export owned base-game static NIFs to a private indexed scene; no native loader yet."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import BSA, normpath
from mwad.esm import NIF_MAGIC, NIF_TES3_HEADER, read_bsa_asset
from mwad.paths import child_ci, ensure_external, read_workspace, resolve_data_files
from mwad.scene import pack_geometry, unpack_geometry, visible_refs, resident_set, read_asset
from build_jobs import add_jobs, resolve_jobs
from nif_common import root_local
from build_parallel import ordered_map
from scenery_selection import load_groups, select_source_refs, validate_groups
from area_config import BOUNDS, inside
from exterior_visibility import (DRAW_MODES, VisibilityPolicyError, validate_policy,
                                 select_exterior_faces, source_visibility_issues)


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
    quiet_struct_logging()
    return NifFormat


def quiet_struct_logging():
    """PyFFI formats a debug line for every attribute it reads (StructBase._log_struct:
    the value, its type and the stream offset) before the logger drops it: about a fifth of
    every NIF read (base_anim.nif 3.8 s -> 3.1 s). Format it only when that logger really
    writes debug lines; what is read is unchanged."""
    import logging
    from pyffi.object_models.xml import struct_
    original = struct_.StructBase._log_struct
    if getattr(original, '_mwad_quiet', False):
        return

    def _log_struct(self, stream, attr):
        if self.logger.isEnabledFor(logging.DEBUG):
            original(self, stream, attr)
    _log_struct._mwad_quiet = True
    struct_.StructBase._log_struct = _log_struct


def check_nif_reader():
    """Exercise the actual reader without original game files or disk output."""
    N = nif_reader()
    original = N.Data(version=0x04000002)
    original.roots = [N.NiNode()]
    stream = io.BytesIO()
    original.write(stream)
    stream.seek(0)
    decoded = N.Data()
    decoded.read(stream)
    if decoded.version != 0x04000002 or len(decoded.roots) != 1 or not isinstance(decoded.roots[0], N.NiNode):
        raise ValueError('Synthetic TES3 NIF round-trip failed')
    print('[ok] PyFFI TES3 reader: synthetic NIF write/read passed; no game files used.', flush=True)


bsa_read = read_bsa_asset  # the one shared BSA asset read (mwad.esm)


def model_geometry(raw, N, collision=False, repair_uv=False, pose_world=None):
    import numpy as np
    if not raw.startswith(NIF_TES3_HEADER):
        raise ValueError('Only base-game TES3 NIF 4.0.0.2 is supported')
    data = N.Data(); data.read(io.BytesIO(raw))
    vertices, faces, materials = [], [], []
    skipped = []
    worlds = {}
    def collect(node, parent, root=False):
        if not isinstance(node, N.NiAVObject):return
        local = np.array(node.get_transform().as_list())
        if root:
            # Morrowind ignores the root node's authored rotation (e.g. the
            # 90-degree yaw on Velothi interior kit pieces) but keeps its
            # translation and scale: crates with a -32 root offset rest exactly
            # on the floor only when that offset is applied.
            # BALMORA-TEMPLE-GEOMETRY-29.
            # Round the recovered scale: a rotated unit-scale root gives e.g.
            # 0.99999994, which breaks exact vertex sharing between pieces.
            local = root_local(local)
        transform = local @ parent
        if pose_world and isinstance(node,N.NiNode):transform=pose_world(node.name.decode('cp1252'))
        worlds[id(node)] = transform
        for child in getattr(node, 'children', []):
            if child is not None:collect(child, transform)
    for root in data.roots:collect(root, np.eye(4), root=True)
    def visit(node, parent, hidden=False, in_collision=False, path="root[0]", inherited_stencil=None):
        if not isinstance(node, N.NiAVObject):
            return
        name = node.name.decode('cp1252')
        in_collision = in_collision or isinstance(node, N.RootCollisionNode) or name.casefold() == 'rootcollisionnode'
        hidden = hidden or bool(node.flags & 1)
        transform = worlds[id(node)]
        stencil = inherited_stencil
        local_stencils = [p for p in getattr(node, 'properties', [])
                          if isinstance(p, getattr(N, 'NiStencilProperty', ()))]
        if local_stencils:
            p = local_stencils[-1]
            stencil = {'draw_mode': int(p.draw_mode), 'stencil_enabled': bool(p.stencil_enabled),
                       'property_flags': int(p.flags), 'origin_path': path,
                       'ambiguous_properties': len(local_stencils) > 1}
        if isinstance(node, N.NiTriShape) and not collision and (hidden or in_collision):
            skipped.append({'shape': name, 'shape_path': path,
                            'reason': 'collision_node' if in_collision else 'hidden_node',
                            'triangles': int(node.data.num_triangles) if node.data else 0})
        if isinstance(node, N.NiTriShape) and (in_collision if collision else not hidden and not in_collision):
            g = node.data
            if g is None or not g.num_vertices or not g.num_triangles:
                return
            diffuse, alpha, texture, emissive = [1., 1., 1.], 1., None, 0
            for p in ([] if collision else node.properties):
                if isinstance(p, N.NiMaterialProperty):
                    diffuse = [p.diffuse_color.r, p.diffuse_color.g, p.diffuse_color.b]; alpha = p.alpha
                    # Self-lit strength 0..9 from the brightest emissive channel; the
                    # engine raises such surfaces' light (aw_emissive).
                    glow = max(p.emissive_color.r, p.emissive_color.g, p.emissive_color.b)
                    emissive = max(0, min(9, int(round(glow * 9)))) if glow > 0.05 else 0
                if isinstance(p, N.NiTexturingProperty) and p.has_base_texture and p.base_texture.source:
                    texture = p.base_texture.source.file_name.decode('cp1252')
            material = len(materials)
            visibility = dict(stencil) if stencil else {
                'draw_mode': None, 'stencil_enabled': False, 'property_flags': None,
                'origin_path': None, 'ambiguous_properties': False}
            visibility['draw_mode_name'] = DRAW_MODES.get(visibility['draw_mode'],
                'unspecified' if visibility['draw_mode'] is None else 'unknown')
            visibility.update({'hidden': hidden, 'collision_node': in_collision,
                               'runtime_policy': 'existing one-sided winding; metadata is not new raster support'})
            materials.append({'texture_source': texture, 'diffuse': diffuse, 'alpha': alpha, 'emissive': emissive,
                              'source_shape': name, 'source_shape_path': path,
                              'source_face_range': {'start': len(faces), 'count': int(g.num_triangles)},
                              'source_visibility': visibility})
            start = len(vertices)
            hom = np.array([[v.x,v.y,v.z,1.] for v in g.vertices])
            positions = hom @ transform
            if node.skin_instance is not None:
                positions = np.zeros((len(hom),4)); weights = np.zeros(len(hom))
                for bone, info in zip(node.skin_instance.bones, node.skin_instance.data.bone_list):
                    if bone is None or id(bone) not in worlds:raise ValueError('Missing static skin bone')
                    ids = np.array([w.index for w in info.vertex_weights], int)
                    values = np.array([w.weight for w in info.vertex_weights])
                    if not len(ids):continue
                    positions[ids] += (hom[ids] @ np.array(info.get_transform().as_list()) @ worlds[id(bone)]) * values[:,None]
                    weights[ids] += values
                if np.any(np.abs(weights-1)>.02):raise ValueError('Invalid static skin weights')
                positions /= weights[:,None]
            coords=np.array([[u.u,u.v] for u in g.uv_sets[0]]) if g.num_uv_sets and g.uv_sets else np.zeros((len(g.vertices),2))
            invalid=~np.isfinite(coords).all(axis=1)
            if repair_uv and invalid.any():
                triangles=np.array(g.get_triangles(),dtype=int)
                original=coords.copy()
                for index in np.flatnonzero(invalid):
                    adjacent=np.unique(triangles[np.any(triangles==index,axis=1)])
                    adjacent=adjacent[~invalid[adjacent]]
                    if not len(adjacent):raise ValueError('Malformed source UV has no finite neighbouring values')
                    neighbours=original[adjacent]
                    coords[index]=neighbours.mean(axis=0)
                    skipped.append(dict(repair='nonfinite-source-uv',shape=name,vertex=int(index),
                                        replacement=coords[index].tolist(),neighbours=adjacent.tolist()))
            for i, v in enumerate(g.vertices):
                position = positions[i]
                colour = g.vertex_colors[i] if g.has_vertex_colors else None
                rgba = [colour.r, colour.g, colour.b, colour.a] if colour else [1., 1., 1., 1.]
                vertices.append([*map(float, position[:3]), *map(float,coords[i]),
                                 *[round(max(0., min(1., c)) * 255) for c in rgba]])
            faces.extend([start + a, start + b, start + c, material] for a, b, c in g.get_triangles())
        for child_index, child in enumerate(getattr(node, 'children', [])):
            if child is not None:
                visit(child, transform, hidden, in_collision,
                      path + '/children[' + str(child_index) + ']', stencil)
    for root_index, root in enumerate(data.roots):
        visit(root, np.eye(4), path='root[' + str(root_index) + ']')
    if not vertices or not faces:
        raise ValueError('No supported visible static triangles')
    packet = pack_geometry(vertices, faces, len(materials))
    unpack_geometry(packet)
    points = np.array(vertices)[:, :3]
    return packet, materials, [points.min(axis=0).tolist(), points.max(axis=0).tolist()], skipped


# Particle emitters that are not flames.
FLAME_SKIP = ('smoke', 'ash', 'spark', 'steam', 'dust', 'mist', 'bubble', 'fog')


def model_flames(raw, N, name=''):
    """Particle flames [x, y, z, size, particle, rise, spread] for a light mesh.

    One entry per NiParticleSystemController emitter (candle, lantern, fire,
    brazier), skipping smoke/ash/spark-type emitters. Uses the same root-node
    rule as model_geometry (rotation dropped, translation and scale kept).
    x, y, z are NIF units; size is the legacy engine flame scale class;
    particle (particle size), rise (speed x lifetime) and spread (cone radius
    at the top of the rise) are NIF units taken from the emitter itself, so
    a hearth draws as wide and as tall as in the original.
    The engine draws these as static flames (aw_flame entities)."""
    import numpy as np
    data = N.Data()
    try:
        data.read(io.BytesIO(raw))
    except Exception:
        return []  # geometry reading decides whether the model is usable
    worlds = {}
    def collect(node, parent, root=False):
        if not isinstance(node, N.NiAVObject): return
        local = np.array(node.get_transform().as_list())
        if root:
            local = root_local(local)
        world = local @ parent; worlds[id(node)] = world
        for child in getattr(node, 'children', []):
            if child is not None: collect(child, world)
    for root in data.roots: collect(root, np.eye(4), root=True)
    stem = name.lower()
    # Engine flame height is about 1.5 x size map units (a torch flame is 1).
    size = (0.8 if any(k in stem for k in ('candle', 'lantern', 'sconce', 'lamp', 'chandelier', 'torch'))
            else 8.0 if any(k in stem for k in ('fire', 'brazier', 'pit')) else 2.0)
    flames = []
    for block in data.blocks:
        if type(block).__name__ != 'NiParticleSystemController' or block.emitter is None: continue
        if id(block.emitter) not in worlds: continue
        if any(k in block.emitter.name.decode('cp1252', 'replace').lower() for k in FLAME_SKIP): continue
        p = worlds[id(block.emitter)][3, :3]
        rise = max(0.0, float(block.speed)) * max(0.0, float(block.lifetime))
        spread = rise * math.tan(min(max(float(block.vertical_angle), 0.0), 1.2))
        flames.append([round(float(p[0]), 3), round(float(p[1]), 3), round(float(p[2]), 3), size,
                       round(max(0.0, float(block.size)), 3), round(rise, 3), round(spread, 3)])
    return flames


def reference_rotation(ref):
    import numpy as np
    # TES3 uses Z then Y then X on column vectors, all clockwise.
    # Keep the same convention as the authored chargen collision boxes.
    x, y, z = [-a for a in ref['rotation_radians']]
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
    ry = np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
    rz = np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])
    return rx @ ry @ rz


def world_bounds(bounds, ref):
    import numpy as np
    corners = np.array([[a,b,c] for a in (bounds[0][0],bounds[1][0]) for b in (bounds[0][1],bounds[1][1]) for c in (bounds[0][2],bounds[1][2])])
    points = corners @ reference_rotation(ref).T * ref['scale'] + ref['position']
    return [points.min(axis=0).tolist(), points.max(axis=0).tolist()]


def prepare(workspace, out, radius=11500, texture_size=64, jobs=None, visibility_policy=None):
    from PIL import Image
    workspace, state = read_workspace(workspace)
    data_files = resolve_data_files(state['data_files'])
    placements = json.loads((workspace / 'generated/seyda-neen/placements.json').read_text())
    centre = [-11200., -71504., 400.]
    refs, groups = select_source_refs(placements, centre, radius, load_groups())
    # Keep a generous origin margin while the actual geometry bounds are not yet
    # known. Runtime selection intersects the converted bounds, including rocks
    # whose origins lie outside the playable rectangle.
    refs = [r for r in refs if r.get('scene_groups') or inside(r['position'], 512)]
    return export_refs(data_files,out,refs,groups,centre,radius,texture_size,
                       metadata={'runtime_bounds': BOUNDS, 'scene_kind': 'exterior'},
                       jobs=jobs,visibility_policy=visibility_policy)


def _read_model(task):
    name, path, extent, collision = task
    try:
        with Path(path).open('rb') as source:
            source.seek(extent['offset'])
            raw = source.read(extent['bytes'])
        if len(raw) != extent['bytes']:
            raise ValueError('Truncated BSA model')
        N = nif_reader()
        result = model_geometry(raw, N)
        collision_result = None
        if collision:
            try:collision_result = model_geometry(raw, N, collision=True)
            except ValueError as exc:
                if collision != 'root_node_or_visual' or str(exc) != 'No supported visible static triangles':raise
        # The flame emitters are read here too, beside the other models, not in the single writer
        # (export_refs read every model a second time there). A failure is handed back and raised
        # where the writer used to read them, so the archive and the error list stay the same.
        flames = None
        if raw.startswith(NIF_MAGIC):
            try:flames = model_flames(raw, N, name)
            except (ValueError, KeyError, struct.error) as exc:flames = FlamesError(str(exc))
        return name, raw, (result, flames), collision_result, None
    except (ValueError, KeyError, struct.error) as exc:
        return name, None, None, None, str(exc)


class FlamesError(str):
    """A model_flames failure in a _read_model worker, raised again by the writer (_flames)."""


def _flames(flames):
    if isinstance(flames, FlamesError):
        raise ValueError(str(flames))
    return [] if flames is None else flames


def export_refs(data_files,out,refs,groups,centre,radius=4096,texture_size=64,metadata=None,jobs=None,
                visibility_policy=None):
    from PIL import Image
    if visibility_policy is not None:
        validate_policy(visibility_policy)
        if not metadata or metadata.get('scene_kind') != 'exterior':
            raise VisibilityPolicyError('Visibility exclusions require explicit exterior context')
    out = ensure_external(out, 'scenery export'); out.mkdir(parents=True, exist_ok=False)
    bsa = BSA(child_ci(data_files, 'Morrowind.bsa'))
    profiles={name:profile for group in groups.values()
              for name,profile in group.get('visual_profiles',{}).items()}
    names = sorted({normpath('meshes/' + r['model']) for r in refs})
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
    tasks = [(name, bsa.path, bsa.entries.get(name, {'offset': 0, 'bytes': 0}),
              profiles.get(name, {}).get('collision_source') if profiles.get(name, {}).get('collision_source') in ('root_node', 'root_node_or_visual') else None) for name in names]
    workers = min(resolve_jobs(jobs), max(1, len(tasks)))
    print(f'Scenery geometry workers: {workers}', flush=True)
    with archive.open('xb') as f:
        for name, raw, result, collision_result, error in ordered_map(_read_model, tasks, workers):
            try:
                if error is not None:
                    raise ValueError(error)
                (packet, materials, bounds, skipped), flames = result
                visibility_selection = None
                if visibility_policy is not None:
                    visibility_selection = select_exterior_faces(visibility_policy, name,
                        hashlib.sha256(raw).hexdigest(), materials, unpack_geometry(packet)[1],
                        metadata['scene_kind'])
                collision_record = None
                if collision_result is not None:
                    cpacket, _, cbounds, cskipped = collision_result
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
                    candidates = [str(PurePosixPath(requested).with_suffix('.dds')), requested]
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
                                        'source_visibility_issues': source_visibility_issues(materials),
                                        'exterior_visibility': visibility_selection,
                                        'skipped_shapes': skipped,
                                        'flames': _flames(flames), **put(f, packet)})
                print('model',len(index['models']),'/',len(names),name,flush=True)
            except VisibilityPolicyError:
                raise
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
    if index['errors']:
        (out/'conversion-errors.json').write_text(json.dumps(index['errors'],indent=2)+'\n',encoding='utf-8',newline='\n')
    try:
        validate_groups(index['references'], groups)
    except ValueError as exc:
        raise ValueError(str(exc)+'; '+str(index['errors'])) from exc
    # Read every payload independently, through the same seek/extent contract.
    collisions=[m['collision'] for m in index['models'] if m.get('collision')]
    with archive.open('rb') as f:
        for record in index['models'] + index['textures'] + collisions: read_asset(f, record)
    report = {'scope': index['scope'], 'selected_references': len(refs), 'converted_references': len(index['references']),
              'models': len(index['models']), 'textures': len(index['textures']), 'archive_bytes': archive.stat().st_size,
              'geometry_bytes': sum(m['bytes'] for m in index['models']),
              'collision_bytes': sum(m['bytes'] for m in collisions), 'errors': index['errors'],
              'source_visibility_acceptance': {
                  'status': 'incomplete' if any(m['source_visibility_issues'] for m in index['models']) else 'existing one-sided policy',
                  'issues': [{'model': m['source'], **issue} for m in index['models'] for issue in m['source_visibility_issues']],
                  'note': 'Metadata retained; alternate draw modes need explicit runtime/converter acceptance.'},
              'exterior_visual_triangles_selected': sum(len(m['exterior_visibility']['excluded_packet_faces'])
                  for m in index['models'] if m.get('exterior_visibility')),
              'camera_spheres': {str(d): resident_set(index, visible_refs(index, centre, d)) for d in (768,1536,2304,3840)},
              'note': 'Host geometry/cache accounting only. No Amiga frame-rate or disk-throughput claim. RGBA textures are an intermediate, not a Paula/AGA format.'}
    (out/'scenery-index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8',newline='\n')
    (out/'scenery-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--radius',type=int,choices=range(512,16385),default=11500)
    p.add_argument('--texture-size',type=int,choices=(32,64,128),default=64)
    p.add_argument('--exterior-visibility-policy',type=Path,
                   help='Optional reviewed model/hash-bound exterior visual exclusions; no production entries are bundled')
    add_jobs(p);a=p.parse_args()
    policy=json.loads(a.exterior_visibility_policy.read_text(encoding='utf-8')) if a.exterior_visibility_policy else None
    print(json.dumps(prepare(a.workspace,a.out,a.radius,a.texture_size,a.jobs,policy),indent=2))

if __name__=='__main__': main()
