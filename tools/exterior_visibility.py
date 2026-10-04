# SPDX-License-Identifier: GPL-3.0-only
"""Source-bound exterior visual exclusions; original geometry remains collision input."""
import hashlib
import json
import re

POLICY_FORMAT = 'AmiWind exterior visibility policy 1'
SELECTION_FORMAT = 'AmiWind exterior visibility selection 1'
DRAW_MODES = {0: 'application_default', 1: 'counter_clockwise',
              2: 'clockwise', 3: 'both'}


class VisibilityPolicyError(ValueError):
    """Invalid/stale policy is an acceptance failure, never an omitted model."""


def _require(condition, message):
    if not condition:
        raise VisibilityPolicyError(message)


def source_visibility_issues(materials):
    """Do not equate preserving metadata with implementing new raster policies."""
    issues = []
    for m in materials:
        v = m.get('source_visibility')
        if v is None:
            issues.append({'shape': m.get('source_shape'), 'reason': 'source visibility metadata unavailable'})
            continue
        mode = v['draw_mode']
        if mode not in (None, 1):
            issues.append({'shape_path': m['source_shape_path'], 'draw_mode': mode,
                           'reason': 'explicit source draw mode requires runtime/converter acceptance'})
        if v.get('stencil_enabled'):
            issues.append({'shape_path': m['source_shape_path'], 'reason': 'enabled source stencil test unsupported'})
        if v.get('ambiguous_properties'):
            issues.append({'shape_path': m['source_shape_path'], 'reason': 'multiple stencil properties need explicit acceptance'})
    return issues


def validate_policy(policy):
    _require(isinstance(policy, dict) and set(policy) == {'format', 'models'} and
             policy['format'] == POLICY_FORMAT, 'Invalid exterior visibility policy schema')
    _require(isinstance(policy['models'], list), 'Policy models must be a list')
    seen = set()
    for entry in policy['models']:
        _require(isinstance(entry, dict) and set(entry) == {'model', 'source_sha256', 'exclusions'},
                 'Invalid visibility model entry')
        name = entry['model']
        _require(isinstance(name, str) and re.fullmatch(r'meshes/[a-z0-9_./ -]+\.nif', name) and
                 '..' not in name.split('/') and name not in seen,
                 'Policy requires a unique normalized mesh path')
        seen.add(name)
        _require(isinstance(entry['source_sha256'], str) and
                 re.fullmatch(r'[0-9a-f]{64}', entry['source_sha256']), 'Invalid source asset hash')
        _require(isinstance(entry['exclusions'], list), 'Exclusions must be a list')
        ids = set()
        for rule in entry['exclusions']:
            _require(isinstance(rule, dict) and set(rule) ==
                     {'id', 'shape_path', 'triangles', 'classification', 'evidence'}, 'Invalid exclusion rule')
            _require(isinstance(rule['id'], str) and 0 < len(rule['id']) <= 128 and rule['id'] not in ids,
                     'Invalid or duplicate exclusion ID')
            ids.add(rule['id'])
            _require(isinstance(rule['shape_path'], str) and rule['shape_path'], 'Missing stable shape path')
            _require(rule['classification'] == 'verified_exterior_hidden' and
                     isinstance(rule['evidence'], str) and rule['evidence'].strip(),
                     'Exclusion requires reviewed exterior-hidden evidence')
            tri = rule['triangles']
            _require(tri == 'all' or (isinstance(tri, list) and tri and
                     all(type(x) is int and x >= 0 for x in tri) and len(set(tri)) == len(tri)),
                     'Triangle selection must be all or unique nonnegative source indices')
    return policy


def select_exterior_faces(policy, model, source_sha256, materials, faces, scene_kind):
    """Resolve reviewed source shape/triangle identities; no geometric guesswork."""
    validate_policy(policy)
    _require(scene_kind == 'exterior', 'Visibility exclusions require explicit exterior context')
    entry = next((x for x in policy['models'] if x['model'] == model), None)
    if entry is None:
        return None
    _require(entry['source_sha256'] == source_sha256, 'Stale exterior visibility asset hash: ' + model)
    shapes = {}
    for material, info in enumerate(materials):
        path = info.get('source_shape_path')
        _require(path and path not in shapes, 'Missing/ambiguous stable source shape provenance')
        span = info.get('source_face_range', {})
        start, count = span.get('start'), span.get('count')
        _require(type(start) is int and type(count) is int and start >= 0 and count > 0 and
                 start+count <= len(faces), 'Invalid source shape face range')
        _require(all(int(faces[i][3]) == material for i in range(start, start+count)),
                 'Source face provenance does not match packet materials')
        shapes[path] = (start, count)
    excluded = set(); provenance = []
    for rule in entry['exclusions']:
        _require(rule['shape_path'] in shapes, 'Unknown source shape path: ' + rule['shape_path'])
        start, count = shapes[rule['shape_path']]
        ids = list(range(count)) if rule['triangles'] == 'all' else rule['triangles']
        _require(all(i < count for i in ids), 'Source triangle outside selected shape')
        resolved = {start+i for i in ids}
        _require(not excluded & resolved, 'Overlapping visibility exclusion rules')
        excluded.update(resolved)
        provenance.append({**rule, 'resolved_packet_faces': sorted(resolved)})
    _require(len(excluded) < len(faces), 'Whole-model visual exclusion is not supported by this stage')
    used = {int(face[3]) for i, face in enumerate(faces) if i not in excluded}
    issues = source_visibility_issues([materials[i] for i in sorted(used)])
    _require(not issues, 'Unsupported retained source visibility prevents policy acceptance: ' + str(issues))
    return {'format': SELECTION_FORMAT, 'scene_kind': 'exterior', 'model': model,
            'source_sha256': source_sha256, 'source_packet_face_count': len(faces),
            'policy_sha256': hashlib.sha256(json.dumps(policy, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'excluded_packet_faces': sorted(excluded), 'rules': provenance,
            'collision': 'original packet retained; selection is visual only'}


def apply_exterior_selection(faces, model):
    """Called before visual LOD/merging, with the original collision array intact."""
    selection = model.get('exterior_visibility')
    if selection is None:
        return faces
    _require(selection.get('format') == SELECTION_FORMAT and selection.get('scene_kind') == 'exterior',
             'Invalid exterior visibility selection context')
    _require(selection.get('model') == model.get('source') and
             selection.get('source_sha256') == model.get('source_sha256') and
             selection.get('source_packet_face_count') == len(faces),
             'Visibility selection source mismatch')
    ids = selection.get('excluded_packet_faces')
    _require(isinstance(ids, list) and all(type(i) is int and 0 <= i < len(faces) for i in ids) and
             ids == sorted(set(ids)) and len(ids) < len(faces), 'Invalid visual face selection')
    # Re-resolve immutable source identities, instead of trusting edited packet indices.
    policy = {'format': POLICY_FORMAT, 'models': [{'model': model['source'],
              'source_sha256': model['source_sha256'], 'exclusions': [
                  {k: r[k] for k in ('id', 'shape_path', 'triangles', 'classification', 'evidence')}
                  for r in selection.get('rules', [])]}]}
    checked = select_exterior_faces(policy, model['source'], model['source_sha256'],
                                    model['materials'], faces, 'exterior')
    _require(checked['excluded_packet_faces'] == ids, 'Visibility packet indices differ from source selections')
    if not ids:
        return faces
    excluded = set(ids)
    return faces[[i for i in range(len(faces)) if i not in excluded]].copy()

def _hidden_orient_sign(a, b, c, p):
    """Exact orientation sign for the stored dyadic input coordinates."""
    from fractions import Fraction
    u = [Fraction(float(b[i])) - Fraction(float(a[i])) for i in range(3)]
    v = [Fraction(float(c[i])) - Fraction(float(a[i])) for i in range(3)]
    w = [Fraction(float(p[i])) - Fraction(float(a[i])) for i in range(3)]
    value = (u[1]*v[2]-u[2]*v[1])*w[0] + (u[2]*v[0]-u[0]*v[2])*w[1] + (u[0]*v[1]-u[1]*v[0])*w[2]
    return (value > 0) - (value < 0)


def auto_cull_hidden_surfaces(vertices, faces, materials, *, enabled=True,
                             scene_kind='exterior', clearance=1e-4,
                             max_shell_triangles=2048):
    """Remove triangles strictly inside certified opaque convex source shells.

    Exact-coordinate topology, consistent winding and original support planes
    certify each occluder; no new cap/hull, near-vertex welding, view sampling,
    or inward-normal classification. This bounded proof does not establish that
    all hidden geometry was removed. Returned IDs index the ORIGINAL face array.
    Input arrays and collision data are never modified.
    """
    import collections
    import math
    import numpy as np
    v = np.asarray(vertices, dtype=float)
    f = np.asarray(faces)
    if (v.ndim != 2 or v.shape[1] < 3 or f.ndim != 2 or f.shape[1] != 4 or
            not np.isfinite(v).all() or not np.issubdtype(f.dtype, np.integer) or
            (len(f) and (f[:, :3].min() < 0 or f[:, :3].max() >= len(v) or
                        f[:, 3].min() < 0 or f[:, 3].max() >= len(materials)))):
        raise ValueError('Invalid hidden-surface mesh arrays')
    if not math.isfinite(clearance) or clearance <= 0 or max_shell_triangles < 4:
        raise ValueError('Invalid hidden-surface proof limits')
    audit = {'format': 'AmiWind automatic hidden surface audit 1',
             'method': 'exact-topology opaque convex-shell strict containment',
             'enabled': bool(enabled), 'scene_kind': scene_kind,
             'input_triangles': len(f), 'kept_triangles': len(f),
             'removed_face_ids': [], 'kept_face_ids': list(range(len(f))),
             'components': [], 'certified_occluders': 0, 'witnesses': [],
             'clearance': clearance,
             'scope': 'partial proof class only; open/nonconvex/unknown-opacity surfaces retained',
             'collision': 'input unchanged; caller retains original collision representation'}
    if not enabled or scene_kind != 'exterior' or not len(f):
        audit['reason'] = 'disabled' if not enabled else 'separate interior/empty input'
        return f.copy(), audit

    # A topology seam is joined ONLY when its actual coordinates agree exactly.
    points, vertex_ids = np.unique(v[:, :3], axis=0, return_inverse=True)
    wf = vertex_ids[f[:, :3]]
    edges = collections.defaultdict(list)
    parent = list(range(len(f)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for face_id, tri in enumerate(wf):
        for a, b in zip(tri, np.roll(tri, -1)):
            edges[tuple(sorted((int(a), int(b))))].append((face_id, int(a), int(b)))
    for values in edges.values():
        for other in values[1:]:
            parent[find(other[0])] = find(values[0][0])
    components = collections.defaultdict(list)
    for i in range(len(f)):
        components[find(i)].append(i)
    component_edges = collections.defaultdict(list)
    for values in edges.values():
        component_edges[find(values[0][0])].append(values)

    def opaque(face_ids):
        selected_vertices = np.unique(f[face_ids, :3])
        if v.shape[1] >= 9 and not np.all(v[selected_vertices, 8] == 255):
            return False
        for mi in np.unique(f[face_ids, 3]):
            m = materials[int(mi)]
            if m.get('alpha') != 1 or (v.shape[1] < 9 and m.get('vertex_alpha_opaque') is not True):
                return False
            textured = m.get('texture_source') is not None or m.get('texture_index') is not None
            if textured and m.get('texture_alpha_opaque') is not True:
                return False
            visibility = m.get('source_visibility', {})
            if (visibility.get('draw_mode') not in (None, 1) or
                    visibility.get('stencil_enabled') or visibility.get('ambiguous_properties')):
                return False
        return True

    shells = []
    for root_id, face_ids in components.items():
        ee = component_edges[root_id]
        row = {'component_id': len(audit['components']), 'face_ids': face_ids,
               'triangles': len(face_ids), 'boundary_edges': sum(len(e) == 1 for e in ee),
               'nonmanifold_edges': sum(len(e) > 2 for e in ee), 'status': 'retained'}
        audit['components'].append(row)
        def reject(reason):
            row['reason'] = reason
        if len(face_ids) > max_shell_triangles:
            reject('proof budget: shell triangle limit'); continue
        if row['boundary_edges'] or row['nonmanifold_edges']:
            reject('open or nonmanifold exact-coordinate topology'); continue
        if any(len(e) != 2 or e[0][1:] != e[1][1:][::-1] for e in ee):
            reject('inconsistent edge winding'); continue
        unique_ids = np.unique(wf[face_ids])
        if len(unique_ids) - len(ee) + len(face_ids) != 2:
            reject('not a closed sphere topology'); continue
        if len({tuple(sorted(t)) for t in wf[face_ids]}) != len(face_ids):
            reject('duplicate triangles'); continue
        links = collections.defaultdict(list)
        for a, b, c in wf[face_ids]:
            links[int(a)].append((int(b), int(c)))
            links[int(b)].append((int(c), int(a)))
            links[int(c)].append((int(a), int(b)))
        valid_links = True
        for pairs in links.values():
            neighbors = collections.defaultdict(list)
            for a, b in pairs:
                neighbors[a].append(b); neighbors[b].append(a)
            if any(len(n) != 2 for n in neighbors.values()):
                valid_links = False; break
            pending = [next(iter(neighbors))]; reached = set()
            while pending:
                point = pending.pop()
                if point in reached:continue
                reached.add(point); pending.extend(neighbors[point])
            if len(reached) != len(neighbors):
                valid_links = False; break
        if not valid_links:
            reject('nonmanifold vertex link'); continue
        if not opaque(face_ids):
            reject('opacity/draw policy not certified'); continue
        tri = points[wf[face_ids]]
        u, w = tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]
        normal = np.cross(u, w); areas = np.linalg.norm(normal, axis=1)
        if np.any(areas == 0):
            reject('zero-area shell triangle'); continue
        # Check every original shell vertex against every original oriented face.
        # A positive determinant means that the shell is not outward convex.
        pp = points[unique_ids]
        if len(pp)*len(tri) > 20000:
            reject('proof budget: exact vertex/plane comparison limit'); continue
        convex = True
        for i, (a, b, c) in enumerate(tri):
            delta = pp-a
            values = delta @ normal[i]
            # Error filter only; borderline signs use exact rational arithmetic.
            error = 64*np.finfo(float).eps*np.maximum(1., np.abs(delta) @ np.abs(normal[i]) +
                    np.max(np.abs(delta), axis=1)*np.linalg.norm(u[i])*np.linalg.norm(w[i]))
            if np.any(values > error):
                convex = False; break
            # Every remaining sign is exact. The float filter can only reject
            # a shell early, never certify a sign used to delete geometry.
            for j in range(len(pp)):
                if np.array_equal(pp[j], a) or np.array_equal(pp[j], b) or np.array_equal(pp[j], c):
                    continue
                if _hidden_orient_sign(a, b, c, pp[j]) > 0:
                    convex = False; break
            if not convex:break
        if not convex:
            reject('not convex under exact oriented surface-plane tests'); continue
        center = pp.mean(axis=0)
        signed_volume = float(np.einsum('ij,ij->i', tri[:, 0]-center,
            np.cross(tri[:, 1]-center, tri[:, 2]-center)).sum()/6.)
        if not signed_volume > clearance**3:
            reject('zero/negative/uncertain enclosed volume'); continue
        row.update(status='certified opaque convex shell', signed_volume=signed_volume)
        shells.append((row['component_id'], set(face_ids), tri, normal/areas[:, None],
                       pp.min(axis=0), pp.max(axis=0)))
    audit['certified_occluders'] = len(shells)
    removed = set()
    triangles = v[f[:, :3], :3]
    for component_id, shell_faces, tri, normals, low, high in shells:
        candidate = np.flatnonzero(np.all(triangles.min(axis=1) > low+clearance, axis=1) &
                                   np.all(triangles.max(axis=1) < high-clearance, axis=1))
        for face_id in candidate:
            face_id = int(face_id)
            if face_id in shell_faces or face_id in removed:continue
            delta = triangles[face_id][:, None, :] - tri[None, :, 0, :]
            distances = np.einsum('ijk,jk->ij', delta, normals)
            error = 128*np.finfo(float).eps*np.maximum(1., np.max(np.abs(delta), axis=2))
            strict = np.all(distances < -clearance-error)
            if strict:
                strict = all(_hidden_orient_sign(a, b, c, point) < 0
                             for a, b, c in tri for point in triangles[face_id])
            if strict:
                removed.add(face_id)
                audit['witnesses'].append({'face_id': face_id, 'occluder_component_id': component_id,
                    'minimum_support_plane_clearance': float(-distances.max())})
    audit['removed_face_ids'] = sorted(removed)
    audit['kept_face_ids'] = [i for i in range(len(f)) if i not in removed]
    audit['kept_triangles'] = len(f)-len(removed)
    audit['reason'] = 'strict whole-triangle enclosure proof; all other faces retained'
    return f[audit['kept_face_ids']].copy(), audit
