# SPDX-License-Identifier: GPL-3.0-only
"""The coordinate range a build's engine uses (CHIM-FRAME-COORD-RANGE-33; engine/aga/src/aw_coord.h).

Quake sends every position as a 16-bit integer of eighths of a unit, so a position wraps past about +/-4,096
units and the engine keeps a frame's player area within +/-4,000 of its origin ("narrow", the method before
v0.0.36). The wide range (the default since v0.0.36, so all of Vivec fits one CHIM frame) sends 24 bits of
1/256 units: +/-32,768, the range of the BSP node and leaf bounds, one byte more per coordinate, and its own
protocol number. tools/build.py --coord-range picks one for the whole build: the engine is compiled with it
(narrow: -DAW_COORD_NARROW) and the builder's checks follow it through AMIWIND_COORD_RANGE (set by
tools/build.py only for narrow, so a default build's stage commands stay as they were).

Light: no numpy; the numbers are those of aw_coord.h (tests/test_coord_range.py reads them back).
"""
import os

ENV = 'AMIWIND_COORD_RANGE'
DEFAULT = 'wide'
RANGES = {
    # bound: player areas, arrivals, spawn checks (AW_COORD_BOUND); bytes: one coordinate on the wire
    # (AW_COORD_BYTES); protocol: PROTOCOL_VERSION (AW_COORD_PROTOCOL); define: the engine compile switch
    'wide': {'bound': 32000, 'bytes': 3, 'protocol': 1015, 'define': None},
    'narrow': {'bound': 4000, 'bytes': 2, 'protocol': 15, 'define': '-DAW_COORD_NARROW'},
}
NARROW_BOUND = RANGES['narrow']['bound']
WIDE_BOUND = RANGES['wide']['bound']


def current(value=None):
    """The build's coordinate range: value, else AMIWIND_COORD_RANGE, else the default (wide)."""
    name = value if value is not None else (os.environ.get(ENV) or DEFAULT)
    if name not in RANGES:
        raise ValueError('Unknown coordinate range %r (wide or narrow)' % name)
    return name


def bound(value=None):
    """AW_COORD_BOUND of the build's range: a player area or arrival must lie strictly inside +/- this."""
    return RANGES[current(value)]['bound']


def coord_bytes(value=None):
    return RANGES[current(value)]['bytes']


def extra_baseline_bytes(value=None):
    """Bytes a baseline or static entity (three coordinates) needs beyond the narrow message."""
    return 3 * (coord_bytes(value) - RANGES['narrow']['bytes'])


def core_problem(core, value=None):
    """None, or why a handoff core [[x0, y0], [x1, y1]] (frame-local units) does not fit the range."""
    limit = bound(value)
    if all(-limit < core[0][k] < core[1][k] < limit for k in range(2)):
        return None
    need = max(max(-core[0][k], core[1][k]) for k in range(2))
    return ('handoff core %s reaches %g units from the frame origin, over the %s coordinate bound %d%s'
            % (core, need, current(value), limit,
               ' (needs --coord-range wide)' if need < WIDE_BOUND else ''))
