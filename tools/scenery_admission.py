# SPDX-License-Identifier: GPL-3.0-only
"""Mirror the strict immutable town catalogue admission, not a broad prefix.

Same rule as the engine's AW_SceneryMapEnabled (aw_scenery.c, aw_town.h): a
town with the scenery_catalogue flag, by its map name or prefix + 3 digits
below its region cap (Balmora: balmora, bm000..bm063).
"""
import re
from functools import lru_cache


@lru_cache(maxsize=None)
def _towns():
    from town_config import runtime_towns
    return tuple((t['name'], t['prefix'], t['region_cap']) for t in runtime_towns()
                 if 'scenery_catalogue' in t['flags'])


def admitted(name):
    for town, prefix, cap in _towns():
        if name == town:
            return True
        if re.fullmatch(prefix + r'[0-9]{3}', name):
            return int(name[2:]) < cap
    return False


def catalogue_count(name,entity_bytes):
    if not admitted(name):
        return 0
    # Runtime AW_SceneryBegin uses this exact canonical occurrence count.
    return entity_bytes.count(b'"classname" "func_wall"')
