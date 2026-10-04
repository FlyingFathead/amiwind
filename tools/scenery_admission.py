# SPDX-License-Identifier: GPL-3.0-only
"""Mirror the strict immutable Balmora catalogue admission, not a broad prefix."""
import re

def catalogue_count(name,entity_bytes):
    if name!='balmora' and not re.fullmatch(r'bm0(?:[0-5][0-9]|6[0-3])',name):
        return 0
    # Runtime AW_SceneryBegin uses this exact canonical occurrence count.
    return entity_bytes.count(b'"classname" "func_wall"')
