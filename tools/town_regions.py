# SPDX-License-Identifier: GPL-3.0-only
"""Deterministic exterior sub-cells with complete intersecting placements.

All coordinates are shared local world coordinates, including across regions.
Overlap is measured from the whole object bounds, never just its origin.
Generic for every converted town: the map prefix and the native region cap
come from the town block of the town's config (town_config.py); settings
without a town block keep Balmora's historical bm/64 layout.
"""
import math

from town_config import load_settings, town_field


# Meshes whose convex collision closes an authored underpass, kept as authored plates by name (the method before
# v0.0.42). The CHIM model builder finds them by a general rule instead (mesh_geometry.collision_parts underside,
# AMIWIND_COLLISION_UNDERSIDE rule, CHIM-VOS-TEMPLE-WALKWAY-41); 'names' keeps this list for it too.
UNDERPASS_NAMES = ('ex_velothi_temple_01.nif', 'ex_velothi_temple_02.nif')
# Mushrooms whose caps are several materials joined at the rim: reduced with the boundary lock in every
# town and CHIM area (MESH-VIVEC-CAP-GAP-38; the seam audit keeps them closed, config/seam-audit-known.json).
MUSHROOM_CAP_PREFIXES = ('flora_emp_parasol_', 'flora_t_mushroom_', 'flora_bc_mushroom_', 'flora_t_shelffungus_')


def visual_profile(source, triangles, underpass_names=True):
    """Reduce organic props only; open architectural shells must stay intact.

    Global triangle quotas collapse the boundaries of Hlaalu facade panels.
    Their original triangles are already modest and are merged into coplanar
    BSP surfaces by the subsequent conversion stage.

    underpass_names: the meshes of UNDERPASS_NAMES keep their authored collision surfaces (default; the legacy
    town builder); False when the converter applies the general underside rule instead (chim.build).
    """
    stem = source.replace('\\', '/').rsplit('/', 1)[-1].casefold()
    target = triangles
    texture_size = 32
    if stem.startswith('flora_'):
        target = 120
    elif stem == 'siltstrider.nif':
        # Share the inspected Seyda Neen profile. A separate 400-triangle target
        # collapses the Strider's open leg/body components into disconnected strips.
        from scenery_selection import load_groups
        return dict(load_groups()['silt_strider']['visual_profiles']['meshes/r/siltstrider.nif'])
    elif stem.startswith('terrain_rock_'):
        target = 64
        texture_size = 64
    profile = {'ratio': min(1., target / max(1, triangles)), 'texture_size': texture_size}
    if stem.startswith('flora_') and profile['ratio'] < 1:
        # the reduced copy keeps the height of every trunk and stem (static_lod.keeps_shape): a collapsed trunk
        # left Azura's Coast tree crowns floating (CHIM-AZURA-FLOATING-FLORA-43). lod_shape_guard 0 = the method
        # before v0.0.43-dev3
        from static_lod import SHAPE_GUARD, SHAPE_GUARD_AXES, SHAPE_GUARD_MIN
        profile.update(lod_shape_guard=SHAPE_GUARD, lod_shape_guard_min=SHAPE_GUARD_MIN,
                       lod_shape_guard_axes=list(SHAPE_GUARD_AXES))
    if stem.startswith(MUSHROOM_CAP_PREFIXES):
        # MESH-VIVEC-CAP-GAP-38: the default reducer works per material and collapses rim edges, so a
        # mushroom's cap materials pulled apart where they meet (open bands on Vivec's giant mushrooms and
        # every other town or CHIM-area placement). The boundary-locked reducer keeps rims and seams
        # exactly where the source has them (static_lod.reduce_mesh; 22-35 more triangles per parasol).
        profile['lock_boundaries'] = True
    # Convex approximation closes these authored underpasses. Keep each
    # collision surface instead, independent of visible mesh reduction.
    if stem.startswith(('ex_hlaalu_b_', 'ex_hlaalu_bal_', 'ex_hlaalu_bridge_',
                        'ex_hlaalu_dsteps_', 'ex_hlaalu_steps_', 'ex_hlaalu_wall_gate_')) or (
            underpass_names and stem in UNDERPASS_NAMES):
        # ex_velothi_temple_01: its convex pieces reach 2-5 units below the slab a walkway runs under (Vos, the
        # Vivec-style walkway into the temple base: 38 units of visible headroom over the top step, the
        # proxies leave less than the standing box; CHIM-VOS-TEMPLE-WALKWAY-41)
        profile['hollow_collision'] = True
        profile['exact_collision_bevels'] = True
    elif source.replace('\\', '/').casefold().startswith('meshes/x/'):
        # Other exterior architecture keeps its convex collision unless that
        # closes authored space deeper than a step (walkways buried under
        # invented solid, VIVEC-ARENA-ACTORS-32); measured per mesh by
        # mesh_geometry.collision_pieces, the same test for every town.
        from player_hull import STEP_HEIGHT
        profile['surface_collision_beyond'] = STEP_HEIGHT
        if stem.startswith('ex_hlaalu_canal_'):
            # the canal walkways that Hlaalu flights lead onto: a convex piece inventing a slope more than a step
            # over the visible walkway is split (mesh_geometry.clear_visible_treads, walkways; Suran,
            # CHIM-STAIR-STEPS-SOLID-43). Measured on every exterior mesh: the walkway test for all architecture
            # would change 234 meshes in 858 CHIM frames, for this family 2 meshes
            profile['visible_walkways'] = True
    return profile


def town_model_profile(group_profile, source, triangles, underpass_names=True):
    """The profile a town converter uses for one mesh: the scenery index's group profile with
    visual_profile on top. One reading for the legacy town builder (import_town), the CHIM model
    builder (chim.build) and the seam audit (seam_audit), so the audit measures what is built
    (MESH-LOD-OPEN-SEAMS-33). underpass_names as visual_profile."""
    return {**group_profile, **visual_profile(source, triangles, underpass_names)}


def config(town='balmora'):
    return load_settings(town)


def intersects(a, b):
    return all(a[1][i] >= b[0][i] and a[0][i] <= b[1][i] for i in range(2))


def local_bounds(reference, centre, scale):
    return [[(point[i] - centre[i]) * scale for i in range(2)]
            for point in reference['bounds']]


def regions(settings):
    size = settings['core_size']
    low, high = settings['bounds']
    apron = settings.get('reference_margin', 0)
    if not 0 <= apron <= settings['overlap']:
        raise ValueError('Scenery apron must fit the sub-cell overlap')
    if size <= 0 or any((high[i] - low[i]) % size for i in range(2)):
        raise ValueError('Sub-cell bounds must contain complete cores')
    if settings['overlap'] < math.sqrt(2) * settings['draw_distance'] + settings['hysteresis'] + 32:
        raise ValueError('Overlap must cover visibility, hysteresis and collision margin')
    prefix, cap = town_field(settings, 'map_prefix'), town_field(settings, 'region_cap')
    out = []
    for y in range(low[1], high[1], size):
        for x in range(low[0], high[0], size):
            name = f'{prefix}{len(out):03d}'
            core = settings.get('region_core_overrides', {}).get(name, [[x, y], [x + size, y + size]])
            margin = settings['overlap']
            coverage = [[max(low[i] - apron, core[0][i] - margin) for i in range(2)],
                        [min(high[i] + apron, core[1][i] + margin) for i in range(2)]]
            out.append({'name': name, 'core': core, 'coverage': coverage})
    if len(out) > cap:
        raise ValueError('Region directory exceeds native capacity')
    validate_partition(out, settings)
    return out



def validate_partition(entries, settings):
    """Exact rectangular tiling: no holes, overlap, invalid names or hidden slots."""
    low, high = settings['bounds']
    names = {e['name'] for e in entries}
    if set(settings.get('region_core_overrides', {})) - names:
        raise ValueError('Unknown region override')
    area = 0
    for i, entry in enumerate(entries):
        a, b = entry['core']
        if any(type(v) is not int for v in (*a, *b)) or any(
                not low[k] <= a[k] < b[k] <= high[k] for k in range(2)):
            raise ValueError('Invalid region core bounds')
        if any((v-low[k]) % settings['terrain_step'] for point in (a,b) for k,v in enumerate(point)):
            raise ValueError('Region core must align with terrain grid')
        area += (b[0]-a[0])*(b[1]-a[1])
        for other in entries[:i]:
            c,d=other['core']
            if all(max(a[k],c[k]) < min(b[k],d[k]) for k in range(2)):
                raise ValueError('Region cores overlap')
    if area != (high[0]-low[0])*(high[1]-low[1]):
        raise ValueError('Region core coverage has a hole')


def owner(point, entries, current=None, hysteresis=0):
    if not all(math.isfinite(v) for v in point[:2]):
        raise ValueError('Nonfinite region position')
    if current is not None:
        a, b = entries[current]['core']
        if all(a[i] - hysteresis <= point[i] <= b[i] + hysteresis for i in range(2)):
            return current
    for i, entry in enumerate(entries):
        a, b = entry['core']
        if all(a[k] <= point[k] < b[k] for k in range(2)):
            return i
    # The outermost east/north edge belongs to its final core.
    for i, entry in enumerate(entries):
        a, b = entry['core']
        if all(a[k] <= point[k] <= b[k] for k in range(2)):
            return i
    return None


def select_references(index, entry, settings):
    return [r['number'] for r in index['references']
            if intersects(local_bounds(r, settings['centre'], settings['scale']), entry['coverage'])]


def town_references(index, settings):
    """Placements whose footprint reaches the core or its explicit scenery apron.

    Source collection already measures reference_margin. Retain that same
    selection here instead of silently dropping apron objects before packing.
    The core and logical original-cell ownership remain unchanged.
    """
    margin = settings.get('reference_margin', 0)
    low, high = settings['bounds']
    coverage = [[v - margin for v in low], [v + margin for v in high]]
    return [r['number'] for r in index['references']
            if intersects(local_bounds(r, settings['centre'], settings['scale']), coverage)]


def audit_coverage(index, entries, settings):
    selected = [set(select_references(index, e, settings)) for e in entries]
    expected = set(town_references(index, settings))
    present = set().union(*selected)
    if present != expected:
        raise ValueError('Sub-cell union loses or invents references')
    return {'source_references': len(index['references']), 'covered_references': len(present),
            'lost_references': sorted(expected - present), 'region_count': len(entries),
            'max_region_references': max(map(len, selected), default=0),
            'overlap': settings['overlap'], 'hysteresis': settings['hysteresis'],
            'draw_distance': settings['draw_distance']}


def collision_coverage(entry, settings):
    """Physical/interaction overlap; rendering retains its independent overlap."""
    margin=settings['collision_margin']
    # 96-unit hysteresis + 72 interaction reach + 32 normal frame movement
    # (320 units/s at the 0.1s frame cap) + 8 standing half-width.
    if margin<settings['hysteresis']+72+32+8:raise ValueError('Insufficient collision overlap')
    return [[entry['core'][0][i]-margin for i in range(2)],
            [entry['core'][1][i]+margin for i in range(2)]]
