# SPDX-License-Identifier: GPL-3.0-only
"""Original CELL-aligned owned town cores; terrain aprons remain separate."""
import copy
import math

CELL = 8192


def owned_bounds(settings):
    """Half-open original CELL union, transformed at the stable town origin."""
    cells = settings['owned_cells']
    if (not isinstance(cells, list) or len(cells) != 2 or
            any(not isinstance(p, list) or len(p) != 2 for p in cells) or
            any(type(v) is not int for p in cells for v in p) or
            any(cells[0][k] >= cells[1][k] for k in range(2)) or settings['scale'] != .25):
        raise ValueError('Expected a nonempty half-open original-cell rectangle at scale0.25')
    bounds = [[(p[k] * CELL - settings['centre'][k]) * settings['scale'] for k in range(2)] for p in cells]
    if any(v != int(v) for p in bounds for v in p):
        raise ValueError('Owned cell boundaries must be integral map coordinates')
    bounds = [[int(v) for v in p] for p in bounds]
    if settings['bounds'] != bounds or settings.get('handoff_core') != bounds:
        raise ValueError('Source selection and runtime handoff must own the same original cells')
    return bounds


def audit_radius(settings):
    """The source audit includes every owned CELL, retaining its original IDs."""
    owned_bounds(settings)
    radius = settings['source_radius'];centre = settings['source_cell']
    if type(radius) is not int or radius < 0 or len(centre) != 2:
        raise ValueError('Invalid town source audit')
    if any(not centre[k]-radius <= v <= centre[k]+radius
           for k in range(2) for v in [settings['owned_cells'][0][k], settings['owned_cells'][1][k]-1]):
        raise ValueError('Source audit omits an owned original cell')
    return radius


def scenery_radius(settings, scene_centre, requested, padding=512):
    """Cover the full owned rectangle plus the existing source-origin margin.

    The historical radial crop cannot silently truncate a larger declared area.
    Object footprint and complete-assembly selection remain unchanged.
    """
    if 'owned_cells' not in settings:
        return requested
    low, high = owned_bounds(settings)
    corners = [(x, y) for x in [low[0]-padding, high[0]+padding]
               for y in [low[1]-padding, high[1]+padding]]
    need = max(math.hypot(*[(settings['centre'][k]+p[k]/settings['scale'])-scene_centre[k]
                           for k in range(2)]) for p in corners)
    return max(requested, math.ceil(need))


def extend_edge_layout(layout, bounds, ground_bounds, previous=((-2079,-2079),(2079,2079))):
    """Extend existing edge owners; preserve all names, interior cuts and IDs.

    Seyda already uses all64 directory rows. Extending its exterior owners
    changes no old point's region, rather than introducing new aliases.
    """
    if layout['bounds'] == [list(p) for p in bounds]:
        return layout
    if layout['bounds'] != [list(p) for p in previous]:
        raise ValueError('Unexpected Seyda source layout; cannot preserve its region IDs')
    if any(bounds[0][k] > previous[0][k] or bounds[1][k] < previous[1][k] for k in range(2)):
        raise ValueError('Cell-aligned town expansion must contain the old region core')
    # Validate frozen coverage before deriving the expansion; never repair a
    # malformed input into a passing layout. These are the historical ground
    # bounds from the unchanged original Seyda layout recipe.
    old_ground = ((-2048,-2560),(2432,2304))
    for row in layout['regions']:
        c = row['core']
        expected = [[min(c[0][i],max(old_ground[0][i],c[0][i]-896)) for i in range(2)],
                    [max(c[1][i],min(old_ground[1][i],c[1][i]+896)) for i in range(2)]]
        if row['coverage'] != expected:
            raise ValueError('Frozen Seyda source coverage/apron differs from its original recipe')
    out = copy.deepcopy(layout);out['bounds'] = [list(p) for p in bounds]
    for row in out['regions']:
        for edge in range(2):
            for k in range(2):
                if row['core'][edge][k] == previous[edge][k]:
                    row['core'][edge][k] = bounds[edge][k]
        c = row['core']
        row['coverage'] = [[min(c[0][i],max(ground_bounds[0][i],c[0][i]-896)) for i in range(2)],
                           [max(c[1][i],min(ground_bounds[1][i],c[1][i]+896)) for i in range(2)]]
    return out


def reference_ownership(references, settings):
    """Original reference identity and physical-origin owner, not footprint copies.

    Whole objects/assemblies may be needed in neighbouring frame catalogues.
    Keep them, but label dependency copies separately; duplicate original IDs
    inside this source frame are refused before conversion/adoption.
    """
    low, high = settings['owned_cells'];owned_bounds(settings)
    seen=set();owned=[];dependencies=[]
    for ref in references:
        identity=(ref.get('master', 'Morrowind.esm'), ref['number'])
        if identity in seen:
            raise ValueError('Duplicate original reference in one town source frame: %s' % (identity,))
        seen.add(identity)
        cell=[math.floor(ref['position'][k]/CELL) for k in range(2)]
        row={'master':identity[0], 'reference':identity[1], 'physical_cell':cell,
             'source_cell':ref.get('cell'), 'role':'owned_origin'}
        if all(low[k]<=cell[k]<high[k] for k in range(2)):
            owned.append(row)
        else:
            row['role']='footprint_or_assembly_dependency';dependencies.append(row)
    return {'owned_references':owned, 'dependency_references':dependencies,
            'adjacent_catalogue_comparison':'required after source export; dependency copies are not second logical owners'}
