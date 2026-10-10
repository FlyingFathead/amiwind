#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Per-cell lava audit of the CHIM Progress Tracker: has the cell's molten lava become Quake liquid?

The one shared implementation of the test (docs/LAVA.md, LAVA-NOT-IMPLEMENTED-33), used by the tracker
(tools/cell_progress.py) and documented for the World Map's Lava layer.

Inputs per cell:
  molten  the number of molten lava pools the original places in the cell (objects whose script hurts a standing
          actor, tools/lava.molten_objects, counted by the tracker's census of your own master files); None when the
          census has no lava count (a census from before the lava census)
  build   what the build did with them: {"mode": "quake" | "static", "pools": pools converted in this cell}; None for
          a build from before the lava record (it converted none: rooms left pools out, frames placed them as models)
  converted  the cell is converted by a CHIM build

Status: none = no molten lava in the original cell; molten = lava pools mapped, not converted (the cell is not built,
or its build has no lava record); converted = every pool is a Quake liquid; partial = fewer pools converted than
placed; static = built with --lava static (the earlier rule, kept selectable); not_measured = no lava count.
"""
import collections

FORMAT = 'aw-cell-lava-1'
STATUSES = ('converted', 'partial', 'molten', 'static', 'none', 'not_measured')
STATUS_TEXT = collections.OrderedDict([
    ('converted', 'Converted: every molten lava pool of the cell is a Quake liquid (warp, lava contents, damage, tint).'),
    ('partial', 'Partial: fewer pools converted than the original places.'),
    ('molten', 'Mapped, not converted: the original places molten lava here; no build has turned it into liquid yet.'),
    ('static', 'Built with --lava static: the earlier rule (rooms leave the pool out, frames place it as a model).'),
    ('none', 'No molten lava in the original cell.'),
    ('not_measured', 'Not measured: the census has no lava count.'),
])


def audit(molten, build, converted):
    """The lava audit of one cell (see the module text)."""
    out = {'molten': molten, 'converted_pools': None, 'mode': None}
    if molten is None:
        return dict(out, status='not_measured', reason='the census has no lava count')
    if molten == 0:
        return dict(out, status='none', reason='no molten lava in the original cell')
    if not converted:
        return dict(out, status='molten', reason='%d lava pools mapped; the cell is not converted' % molten)
    if not build or build.get('mode') is None:
        return dict(out, status='molten', reason='%d lava pools mapped; the build has no lava record (before the lava '
                                                 'conversion: none converted)' % molten)
    pools = int(build.get('pools') or 0)
    out.update(mode=build['mode'], converted_pools=pools)
    if build['mode'] == 'static':
        return dict(out, status='static', reason='built with --lava static: %d pools not converted' % molten)
    if pools >= molten:
        return dict(out, status='converted', reason='%d of %d pools are Quake liquid' % (pools, molten))
    return dict(out, status='partial', reason='%d of %d pools are Quake liquid' % (pools, molten))


def headline(audits):
    """Island-wide lava line over audits: cells per status, pools placed and converted."""
    st = collections.Counter(a['status'] for a in audits)
    return {'cells': sum(st.values()), 'status': {k: st[k] for k in STATUSES},
            'cells_with_lava': sum(st[k] for k in ('converted', 'partial', 'molten', 'static')),
            'pools': sum(a['molten'] or 0 for a in audits),
            'pools_converted': sum(a['converted_pools'] or 0 for a in audits if a['status'] in ('converted', 'partial'))}
