# SPDX-License-Identifier: GPL-3.0-only
"""Which triangles of a Morrowind model collide with the player: one rule for every mesh converter
(COLLISION-RCN-SCOPE-32, COLLISION-NC-FLAGS-32; docs/COLLISION_MESHES.md recommendation 1).

The rules follow OpenMW 0.51 (learned from its behaviour, our own code): rule from OpenMW
components/nifbullet/bulletnifloader.cpp (handleRoot, handleNode, handleGeometry), applied in
apps/openmw/mwphysics/physicssystem.cpp (PhysicsSystem::addObject):

- a RootCollisionNode that is a direct child of a root node makes the model's collision authored: only the geometry
  under RootCollisionNodes collides (source 'rcn');
- such a node with no triangles under it: OpenMW gives the model camera collision only; AmiWind has no camera
  collision, so the model does not block the player (source 'none');
- without one, the drawn triangles collide (source 'visual'); a RootCollisionNode deeper in the tree does not make the
  model authored (in the base game only the two Dagoth Ur bridges, which carry a root string RCN instead);
- a root NiStringExtraData starting with NC (any case) means no actor collision; with an upper-case C as its third
  letter (NCC) camera collision only. Both are nonsolid for the player here (source 'none');
- a root string MRK drops the "Tri EditorMarker" shapes from drawing and collision (mwad.markers, in
  prepare_scenery.model_geometry);
- geometry under an AvoidNode is an NPC path-avoidance shape, never player collision.

AMIWIND_COLLISION_SOURCE (tools/collision_source_env.py) 'profile' keeps the rule before v0.0.48-dev2 for A/B: the
converter profile opts into the RootCollisionNode, only the exact strings NC and NCO (anywhere) make a model nonsolid.
"""
import io

from collision_source_env import collision_source_mode

# The profile values a converter may give (prepare_scenery.export_refs): root_node = the root RootCollisionNode is
# required (a model without one is an export error); root_node_or_visual = the rule; visual = the drawn triangles
# (an explicit opt-out, never a default).
PROFILE_SOURCES = ('root_node', 'root_node_or_visual', 'visual')
RCN_LABEL = 'NIF RootCollisionNode'
AVOID_LABEL = 'NIF drawn triangles without AvoidNode subtrees'
EMPTY_RCN = 'empty root RootCollisionNode'


def export_collision(profile_value, mode=None):
    """The collision a converter's export reads for a model whose profile gives PROFILE_VALUE (None: not given):
    'root_node', 'root_node_or_visual' or None (the drawn triangles only, no RootCollisionNode read)."""
    mode = mode or collision_source_mode()
    if mode == 'profile':
        return profile_value if profile_value in ('root_node', 'root_node_or_visual') else None
    if profile_value == 'root_node':
        return 'root_node'
    if profile_value == 'visual':
        return None
    return 'root_node_or_visual'


def uses_authored(profile, mode=None):
    """True when a converter (or an estimate of it) collides a model of PROFILE with its RootCollisionNode when the
    model has one."""
    return export_collision((profile or {}).get('collision_source'), mode) is not None


def string_flags(strings):
    """(kind, strings) of a model's root NiStringExtraData strings: kind 'NCC' (camera collision only), 'NC' (no
    actor collision) or None; strings: the NC strings found. Rule from OpenMW bulletnifloader.cpp handleRoot: a string
    starting with "NC" in any case; NCC when its third letter is an upper-case C."""
    found = [s for s in strings if s[:2].casefold() == 'nc']
    if not found:
        return None, []
    kind = 'NCC' if any(len(s) > 2 and s[2] == 'C' for s in found) else 'NC'
    return kind, found


def _is_rcn(node, N):
    name = node.name.decode('cp1252') if getattr(node, 'name', None) is not None else ''
    return isinstance(node, N.RootCollisionNode) or name.casefold() == 'rootcollisionnode'


def tree_facts(data, N):
    """What the collision rule reads from a parsed NIF (PyFFI Data): root strings, whether a root has a
    RootCollisionNode child and how many triangles lie under it, whether a RootCollisionNode sits deeper only, and
    the shape paths under AvoidNodes (the paths prepare_scenery.model_geometry gives its materials)."""
    from mwad.markers import is_marker_shape, root_strings, MARKER_STRING
    strings = []
    for root in data.roots:
        strings.extend(root_strings(root, getattr(N, 'NiStringExtraData', ())))
    marked = MARKER_STRING in strings
    avoid_type = getattr(N, 'AvoidNode', ())
    facts = {'strings': strings, 'root_rcn': False, 'root_rcn_triangles': 0, 'deep_rcn': False, 'avoid_paths': []}

    def triangles(node):
        if isinstance(node, N.NiTriShape):
            if is_marker_shape(node.name.decode('cp1252'), marked):
                return 0
            return int(node.data.num_triangles) if node.data is not None and node.data.num_vertices else 0
        if avoid_type and isinstance(node, avoid_type):
            return 0
        return sum(triangles(c) for c in getattr(node, 'children', []) if c is not None)

    def visit(node, path, avoid, depth):
        if not isinstance(node, N.NiAVObject):
            return
        if depth == 1 and _is_rcn(node, N):
            facts['root_rcn'] = True
            facts['root_rcn_triangles'] += triangles(node)
        elif depth > 1 and _is_rcn(node, N):
            facts['deep_rcn'] = True
        avoid = avoid or bool(avoid_type and isinstance(node, avoid_type))
        if avoid and isinstance(node, N.NiTriShape):
            facts['avoid_paths'].append(path)
        for k, child in enumerate(getattr(node, 'children', [])):
            if child is not None:
                visit(child, path + '/children[' + str(k) + ']', avoid, depth + 1)
    for k, root in enumerate(data.roots):
        visit(root, 'root[' + str(k) + ']', False, 0)
    return facts


def parse(raw, N):
    data = N.Data()
    data.read(io.BytesIO(raw))
    return data


def source_of(facts):
    """The rule's source for a model: ('rcn' | 'visual' | 'none', reason)."""
    kind, found = string_flags(facts['strings'])
    if kind == 'NCC':
        return 'none', 'root string %s: camera collision only (no camera collision here)' % found[0]
    if kind == 'NC':
        return 'none', 'root string %s: no actor collision' % found[0]
    if facts['root_rcn']:
        if not facts['root_rcn_triangles']:
            return 'none', EMPTY_RCN + ' (no triangles under it besides editor markers and AvoidNodes)'
        return 'rcn', 'root RootCollisionNode'
    if facts['deep_rcn']:
        return 'visual', 'RootCollisionNode below the root only (not authored collision)'
    return 'visual', 'no RootCollisionNode'


def collision_metadata(raw, N, facts=None):
    """The source_collision record of a model under the rule (prepare_scenery.source_collision_metadata's form:
    mode 'nonsolid' or 'unchanged' and the NC strings found; 'reason' only for an empty root RootCollisionNode)."""
    from mwad.esm import NIF_MAGIC
    if not raw.startswith(NIF_MAGIC):
        return {'mode': 'unchanged', 'no_collision_markers': []}
    facts = facts if facts is not None else tree_facts(parse(raw, N), N)
    kind, found = string_flags(facts['strings'])
    if kind:
        return {'mode': 'nonsolid', 'no_collision_markers': sorted(set(found))}
    if facts['root_rcn'] and not facts['root_rcn_triangles']:
        return {'mode': 'nonsolid', 'no_collision_markers': [], 'reason': EMPTY_RCN}
    return {'mode': 'unchanged', 'no_collision_markers': []}


def _without_paths(result, paths):
    """A model_geometry result (packet, materials, bounds, skipped) without the faces of the shapes at PATHS; None when
    nothing is left."""
    from mwad.scene import pack_geometry, unpack_geometry
    packet, materials, bounds, skipped = result
    paths = set(paths)
    drop = {k for k, m in enumerate(materials) if m.get('source_shape_path') in paths}
    if not drop:
        return result
    vertices, faces, _ = unpack_geometry(packet)
    kept = [face for face in faces if face[3] not in drop]
    skipped = list(skipped) + [{'shape': materials[k]['source_shape'], 'shape_path': materials[k]['source_shape_path'],
                                'reason': 'avoid_node', 'triangles': materials[k]['source_face_range']['count']}
                               for k in sorted(drop)]
    if not kept:
        return None
    used = sorted({i for face in kept for i in face[:3]})
    remap = {old: new for new, old in enumerate(used)}
    out_v = [vertices[i] for i in used]
    out_f = [(remap[a], remap[b], remap[c], m) for a, b, c, m in kept]
    points = [v[:3] for v in out_v]
    low = [min(p[i] for p in points) for i in range(3)]
    high = [max(p[i] for p in points) for i in range(3)]
    return pack_geometry(out_v, out_f, len(materials)), materials, [low, high], skipped


def model_collision(raw, N, collision='root_node_or_visual'):
    """The collision geometry the rule gives a model, as prepare_scenery._read_model hands it to the export:
    (source, result, reason). result: a model_geometry tuple of the collision triangles, or None when the drawn
    triangles are the collision as they are (source 'visual') or nothing collides (source 'none').
    COLLISION 'root_node': a model without a root RootCollisionNode is an error (ValueError)."""
    from prepare_scenery import model_geometry
    facts = tree_facts(parse(raw, N), N)
    source, reason = source_of(facts)
    if collision == 'root_node' and not facts['root_rcn']:
        raise ValueError('No root RootCollisionNode (authored collision required)')
    if facts['root_rcn'] and facts['root_rcn_triangles']:
        try:
            result = _without_paths(model_geometry(raw, N, collision=True), facts['avoid_paths'])
        except ValueError as exc:
            if str(exc) != 'No supported visible static triangles':
                raise
            result = None      # only editor-marker shapes under it (MRK): nothing collides, as in OpenMW
        if result is None:
            return 'none', None, 'root RootCollisionNode holds no player collision (AvoidNode or marker shapes only)'
        return source, result, reason
    if source == 'visual' and facts['avoid_paths']:
        result = _without_paths(model_geometry(raw, N), facts['avoid_paths'])
        if result is None:
            return 'none', None, 'drawn triangles under AvoidNodes only'
        return 'visual', result, reason + '; AvoidNode subtrees left out'
    return source, None, reason
