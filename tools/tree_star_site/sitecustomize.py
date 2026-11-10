# SPDX-License-Identifier: GPL-3.0-only
"""Start-up hook of tools/chim_tree_star.py (TEST BUILDS ONLY, route D of TREES-DEPTH-56): the CHIM build's worker
pool spawns fresh interpreters, so the star prisms' mesh step is installed in each of them here, when
AMIWIND_TREE_STAR names the tree copies config. The interpreter's own sitecustomize (the one this file shadows) runs
first, unchanged. Only chim_tree_star.py puts this folder on PYTHONPATH."""
import os
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
for _entry in sys.path:
    try:
        _other = Path(_entry or '.').resolve() / 'sitecustomize.py'
    except OSError:
        continue
    if _other.parent != _here and _other.is_file():
        exec(compile(_other.read_bytes(), str(_other), 'exec'), {'__name__': 'sitecustomize', '__file__': str(_other)})
        break

if os.environ.get('AMIWIND_TREE_STAR'):
    import chim_tree_star
    chim_tree_star.install(*chim_tree_star.load_star(os.environ['AMIWIND_TREE_STAR']))
