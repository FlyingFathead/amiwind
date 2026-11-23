# SPDX-License-Identifier: GPL-3.0-only
"""Start-up hook of tools/chim_tree_rally.py (TEST BUILDS ONLY, the rally-game trees of SOLSTHEIM-TREES-THREE-LOD-68):
the CHIM build's worker pool spawns fresh interpreters, so the rally trees' mesh step and see-through atlas texture
are installed in each of them here, when AMIWIND_TREE_RALLY names the tree copies config (with the pane picture and
trunk kinds in AMIWIND_TREE_RALLY_PANES and AMIWIND_TREE_RALLY_TRUNK). The interpreter's own sitecustomize (the one
this file shadows) runs first, unchanged. Only chim_tree_rally.py puts this folder on PYTHONPATH."""
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

if os.environ.get('AMIWIND_TREE_RALLY'):
    import chim_tree_rally
    chim_tree_rally.install(*chim_tree_rally.load_rally(os.environ['AMIWIND_TREE_RALLY'],
                                                        pane_texture=os.environ.get('AMIWIND_TREE_RALLY_PANES') or None,
                                                        trunk=os.environ.get('AMIWIND_TREE_RALLY_TRUNK') or None))
