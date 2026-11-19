#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The build module tribunal-mournhold: Mournhold's outdoor districts as a CHIM world of their own.

Mournhold is not part of the Vvardenfell map. Its five outdoor districts (Godsreach, the Great Bazaar, Plaza Brindisi
Dorom, the Royal Palace courtyard and the Temple courtyard) are interior cells that behave like an exterior; the
stage tribunal-mournhold-data presents them as exterior cell blocks in a data folder of the base master and
Tribunal.esm (tools/presented_data.py --masters Morrowind.esm,Tribunal.esm). This stage converts those cells, and
only those, into their own world folder with the outdoor converter, unchanged:

    tools/tribunal_mournhold.py <tools/chim_build.py arguments>

It runs tools/chim_build.py in this process with the module's own master list (MASTERS) in place of the build's
selection, so the converter reads the presented master and layers Tribunal's archive over the base archive, and
nothing of another expansion. The image installs the result as the store chimmh with the frame maps mhNNNN and the
rows file world/regions-mh.awr (tools/chim/layer_stores.py MODULE_STAGES).

The module's rule (tools/build.py "THE EXPANSIONS AS BUILD MODULES"): its stages are in the plan only when Tribunal is
selected, they are keyed by the base files, Tribunal's files and their own command lines
(tools/build_cache.py MODULE_STAGE_LAYERS), and no base stage reads their output: chim_build.py and the converters are
unchanged, and no base key moves.
"""
import os
from pathlib import Path
import sys

MASTERS = ('Morrowind.esm', 'Tribunal.esm')


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(__file__).resolve().parents[1]
    # src/ before tools/: the src/mwad package, not tools/mwad.py (as tools/chim_build.py orders them)
    for path in (root / 'tools', root / 'src'):
        while str(path) in sys.path:
            sys.path.remove(str(path))
        sys.path.insert(0, str(path))
    from mwad.masters import MASTERS_ENV
    # the module's own masters, for this process and the workers it starts (they inherit the environment)
    os.environ[MASTERS_ENV] = ','.join(MASTERS)
    print('MODULE tribunal-mournhold: Mournhold\'s districts, masters %s' % ', '.join(MASTERS), flush=True)
    import chim_build
    sys.argv = [str(Path(__file__).resolve().parent / 'chim_build.py'), *argv]
    return chim_build.main()


if __name__ == '__main__':
    sys.exit(main())
