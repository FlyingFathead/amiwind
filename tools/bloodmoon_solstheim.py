#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The build module bloodmoon-solstheim: Solstheim's outdoor cells as a CHIM world of their own.

Solstheim's cells are exterior cells of Bloodmoon.esm on the game's one grid, north-west of Vvardenfell. The stage
bloodmoon-solstheim-data makes a data folder of the base master and Bloodmoon.esm
(tools/presented_data.py --masters Morrowind.esm,Bloodmoon.esm: the merged master under the base file's name, the
archives layered as in any build). This stage converts the module's cells, and only those, into their own world
folder with the outdoor converter, unchanged:

    tools/bloodmoon_solstheim.py <tools/chim_build.py arguments>

It runs tools/chim_build.py in this process with the module's own master list (MASTERS) in place of the build's
selection, so the converter reads that folder's master and layers Bloodmoon's archive over the base archive, and
nothing of another expansion. The image installs the result as the store chimsol with the frame maps slNNNN and the
rows file world/regions-sl.awr (tools/chim/layer_stores.py MODULE_STAGES, tools/chim/sol_test.py LANDS).

The module's rule (tools/build.py "THE EXPANSIONS AS BUILD MODULES"): its stages are in the plan only when Bloodmoon
is selected and the tracker reference calls at least one Solstheim cell finished
(tools/bloodmoon_solstheim_module.py), they are keyed by the base files, Bloodmoon's files and their own command
lines (tools/build_cache.py MODULE_STAGE_LAYERS), and no base stage reads their output: chim_build.py and the
converters are unchanged, and no base key moves.
"""
import os
from pathlib import Path
import sys

MASTERS = ('Morrowind.esm', 'Bloodmoon.esm')
POOL_OPTION = '--unit-pool'


def take_pool(argv):
    """(the pool folder or None, ARGV without the option): --unit-pool DIR is this runner's own option, never the
    converter's."""
    argv = list(argv)
    if POOL_OPTION not in argv:
        return None, argv
    at = argv.index(POOL_OPTION)
    if at + 1 >= len(argv):
        raise SystemExit('%s needs a folder' % POOL_OPTION)
    pool = Path(argv[at + 1])
    del argv[at:at + 2]
    return pool, argv


def pooled_units(pool):
    """The converter's unit cache backed by the shared storage pool POOL (chim.units.PooledUnitCache, the cache a
    CHIMport run uses): a unit a CHIMport run of the same cells stored is linked into the stage's own folder instead
    of being converted again, and a unit this stage converts is stored for the next reader
    (CHIMPORT-UNITS-NOT-SHARED-WITH-BUILD-68). Installed for this process only, in the converter's own name for its
    cache (chim.build.UnitCache): tools/chim_build.py and the base world's stage are not changed, and no base key
    moves. Returns the list the caches made are added to, for the stage's closing line."""
    import chim.build
    from chim.units import PooledUnitCache
    made = []

    class ModuleUnitCache(PooledUnitCache):
        def __init__(self, folder=None):
            super().__init__(folder, pool, link=True)
            made.append(self)

        def __reduce__(self):
            # The converter hands its cache to its worker processes, which pickles it; a class made inside this
            # function cannot be pickled by name (the v0.0.68-dev3 build stopped on that in the module's world
            # stage: SOL-MODULE-CACHE-NOT-PICKLED-68). In a worker it is the plain pooled cache it is, with the same
            # folder, pool and state; its counts stay in that worker, as a pooled cache's do in a CHIMport run.
            return (PooledUnitCache, (self.folder, self.pool), self.__dict__)

    chim.build.UnitCache = ModuleUnitCache
    return made


def pool_line(made):
    """The stage's closing line on the pool: what came from it and what went into it, over every cache made."""
    total = {}
    for cache in made:
        for key, value in cache.pool_stats.items():
            total[key] = total.get(key, 0) + value
    return ('MODULE bloodmoon-solstheim: storage pool: %d units (%.1f MB) taken from the pool, %d (%.1f MB) stored, '
            '%d (%.1f MB) already there, %d pool errors'
            % (total.get('reused_units', 0), total.get('reused_bytes', 0) / 1e6, total.get('stored_units', 0),
               total.get('stored_bytes', 0) / 1e6, total.get('linked_units', 0), total.get('linked_bytes', 0) / 1e6,
               total.get('errors', 0)))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    pool, argv = take_pool(argv)
    root = Path(__file__).resolve().parents[1]
    # src/ before tools/: the src/mwad package, not tools/mwad.py (as tools/chim_build.py orders them)
    for path in (root / 'tools', root / 'src'):
        while str(path) in sys.path:
            sys.path.remove(str(path))
        sys.path.insert(0, str(path))
    from mwad.masters import MASTERS_ENV
    # the module's own masters, for this process and the workers it starts (they inherit the environment)
    os.environ[MASTERS_ENV] = ','.join(MASTERS)
    print('MODULE bloodmoon-solstheim: Solstheim\'s outdoor cells, masters %s' % ', '.join(MASTERS), flush=True)
    import chim_build
    made = pooled_units(pool) if pool is not None else None
    if made is not None:
        print('MODULE bloodmoon-solstheim: units shared through the storage pool %s' % pool, flush=True)
    sys.argv = [str(Path(__file__).resolve().parent / 'chim_build.py'), *argv]
    try:
        return chim_build.main()
    finally:
        if made is not None:
            print(pool_line(made), flush=True)


if __name__ == '__main__':
    sys.exit(main())
