# SPDX-License-Identifier: GPL-3.0-only
"""The game archives of the selected masters, as one archive directory (ASSETS-ARCHIVE-ORDER-32).

Beside mwad.masters (the merged master of the same AMIWIND_MASTERS selection): the base archive Morrowind.bsa, then
each selected layer's archive (Tribunal.bsa, Bloodmoon.bsa) in load order; an asset a later archive also holds is read
from that later archive, as the game does. With the base game alone the result is the plain mwad.audit.BSA of
Morrowind.bsa, so a --no-dlc build reads exactly what it read before. A layered entry carries the 'path' of the archive
it comes from; mwad.esm.read_bsa_asset and the readers that take an entry's extent read it from there.
"""
from .audit import BSA
from .masters import BASE_MASTER, is_base_only, selected_masters
from .paths import child_ci

BASE_ARCHIVE = 'Morrowind.bsa'
LAYER_ARCHIVES = {'Tribunal.esm': 'Tribunal.bsa', 'Bloodmoon.esm': 'Bloodmoon.bsa'}


def archive_names(masters=None):
    """The archive file names of the selected masters, in load order (the base archive first)."""
    return [BASE_ARCHIVE] + [LAYER_ARCHIVES[m] for m in selected_masters(masters) if m != BASE_MASTER]


def layered_bsa(data_files, masters=None):
    """One archive directory over the selected masters' archives (later archive wins). The base game alone: the plain
    BSA of Morrowind.bsa, unchanged."""
    masters = selected_masters(masters)
    base = BSA(child_ci(data_files, BASE_ARCHIVE))
    if is_base_only(masters):
        return base
    for name in archive_names(masters)[1:]:
        layer = BSA(child_ci(data_files, name))
        for key, entry in layer.entries.items():
            base.entries[key] = dict(entry, path=layer.path)
    return base
