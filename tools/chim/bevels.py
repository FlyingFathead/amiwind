# SPDX-License-Identifier: GPL-3.0-only
"""Edge bevels on CHIM model standing hulls (EXPERIMENTAL, build setting model_bevels; CHIM-COMPILED-HULL-OVERFILL-46).

Each convex collision piece of a model is expanded by the standing box with prepare_mesh_bsp.standing_planes: its own
planes moved out plus six axial bounding planes, and edge bevels only for the meshes whose profile asks for them. Where
two faces meet at an edge off the axes, that expansion reaches past the exact Minkowski sum (up to 82 units on the
v0.0.46 world's rocks). This module adds the bevels:

- 'exact': every model gets the exact expansion (the build passes exact=True, no code of this module runs);
- 'tol:N': every model gets the edge bevels whose omission lets its hull reach more than N units past the exact
  expansion (needed_bevels), through its own unit kinds ('variant-bevels', 'tiles-bevels': chim.units.CODE_ENTRIES).

Nothing here is reached by a default build: the default units ('variant', 'tiles') and the shared converter
(prepare_mesh_bsp) are unchanged, so their cache keys stay as they were (the 30-minute rebuild goal). The bevel
planes do not fit the CHIM zone at the heaviest frames, so the default stays 'profile'.
"""
import math
from contextlib import contextmanager

MODES = ('profile', 'exact')


def model_bevels_mode(settings):
    """The build setting model_bevels: 'profile' (default: only the meshes whose profile asks for collision bevels,
    the method before), 'exact', or 'tol:N' (returned as the float N >= 0)."""
    mode = str((settings or {}).get('model_bevels', 'profile'))
    if mode in MODES:
        return mode
    if mode.startswith('tol:'):
        return bevel_tolerance_mode(mode[4:])
    raise ValueError('Unknown model bevel mode: %s (profile, exact or tol:N)' % mode)


def bevel_tolerance_mode(value):
    """A bevel tolerance in units: a finite number, 0 or more."""
    try:
        t = float(value)
    except (TypeError, ValueError):
        raise ValueError('A bevel tolerance must be a number of units: %r' % (value,))
    if not (t >= 0 and math.isfinite(t)):
        raise ValueError('A bevel tolerance must be a finite number of units, 0 or more: %r' % (value,))
    return t


def needed_bevels(points, planes, tolerance):
    """planes (a piece expanded without edge bevels, as prepare_mesh_bsp.standing_planes(exact=False) returns them)
    plus every plane of the exact expansion that the bevel-less hull reaches more than `tolerance` units past.
    Tolerance 0 gives the exact solid set (the bevel-less planes are kept; they are faces or supports of it)."""
    import numpy as np
    from scipy.spatial import HalfspaceIntersection
    from prepare_mesh_bsp import standing_planes
    exact = np.asarray(standing_planes(points, None, exact=True))
    planes = np.asarray(planes)
    try:
        corners = HalfspaceIntersection(planes, points.mean(axis=0)).intersections
    except Exception:          # a degenerate piece: every bevel, which is the exact expansion
        return np.unique(np.round(np.vstack((planes, exact)), 5), axis=0)
    over = (corners @ exact[:, :3].T + exact[:, 3]).max(axis=0)
    keep = exact[over > tolerance]
    return np.unique(np.round(np.vstack((planes, keep)), 5), axis=0) if len(keep) else planes


@contextmanager
def bevel_tolerance(tolerance):
    """Inside the block, prepare_mesh_bsp.standing_planes(exact=False) returns needed_bevels(..., tolerance); the
    callers (BrushLumps.collider, routed_hull.expand) import it at call time. None: no change."""
    import prepare_mesh_bsp
    if tolerance is None:
        yield
        return
    tolerance = bevel_tolerance_mode(tolerance)
    original = prepare_mesh_bsp.standing_planes

    def standing_planes(points, equations, exact=False):
        result = original(points, equations, exact)
        if exact:
            return result
        return needed_bevels(points, result, tolerance)
    prepare_mesh_bsp.standing_planes = standing_planes
    try:
        yield
    finally:
        prepare_mesh_bsp.standing_planes = original


def variant_unit_bevels(task):
    """chim.models.variant_unit with the task's bevel tolerance (unit kind 'variant-bevels')."""
    from chim.models import variant_unit
    with bevel_tolerance(task.get('bevel_tolerance')):
        return variant_unit(task)


def tile_unit_bevels(task):
    """chim.cut.tile_unit with the task's bevel tolerance (unit kind 'tiles-bevels')."""
    from chim.cut import tile_unit
    with bevel_tolerance(task.get('bevel_tolerance')):
        return tile_unit(task)
