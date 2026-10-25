# SPDX-License-Identifier: GPL-3.0-only
"""The engine's entity and message budgets, read from the engine headers.

One source for every builder check that counts entities against the engine:
the static entity limit (client.h MAX_STATIC_ENTITIES), edicts (quakedef.h
MAX_EDICTS), the sign-on message (quakedef.h MAX_MSGLEN), efrag links
(client.h MAX_EFRAGS, AW_EFRAG_PAGE_LINKS, AW_EFRAG_LIMIT) and model
indices (quakedef.h MAX_MODELS). The engine states the same names and its
use of them in the CHIM "chim" command; a test keeps the two in step."""
import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'engine/aga/src'
DEFINES = {
    'max_static_entities': ('client.h', 'MAX_STATIC_ENTITIES'),
    'max_streamed_statics': ('chim/chim_statics.c', 'CHIM_MAX_STATICS'),
    'max_edicts': ('quakedef.h', 'MAX_EDICTS'),
    'max_msglen': ('quakedef.h', 'MAX_MSGLEN'),
    'max_models': ('quakedef.h', 'MAX_MODELS'),
    'max_efrags': ('client.h', 'MAX_EFRAGS'),
    'efrag_page_links': ('client.h', 'AW_EFRAG_PAGE_LINKS'),
    'efrag_limit': ('client.h', 'AW_EFRAG_LIMIT'),
    'chim_efrag_reserve': ('chim/chim_local.h', 'CHIM_EFRAG_RESERVE'),
}


def chim_efrag_budget(source=SOURCE):
    """Efrag links CHIM placements may use (CHIM-EFRAG-UNCAPPED-35): the engine's AW_EFRAG_LIMIT less
    CHIM_EFRAG_RESERVE, where ChimChunks_Link makes the farthest placements wait unlinked."""
    return define('client.h', 'AW_EFRAG_LIMIT', source) - define('chim/chim_local.h', 'CHIM_EFRAG_RESERVE', source)


def define(header, name, source=SOURCE):
    """A literal integer #define of an engine header (comments ignored)."""
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', (Path(source) / header).read_text(encoding='utf-8', errors='replace'),
                  flags=re.S)
    match = re.search(r'^\s*#\s*define\s+' + name + r'\s+(\d+)\b', text, re.M)
    if not match:
        raise ValueError('Engine limit %s not found in %s' % (name, header))
    return int(match.group(1))


def cvar_default(path, name, source=SOURCE):
    """The default of an engine cvar written as {"name", "value"}."""
    text = (Path(source) / path).read_text(encoding='utf-8', errors='replace')
    match = re.search(r'\{\s*"' + name + r'"\s*,\s*"(-?\d+)"', text)
    if not match:
        raise ValueError('Engine cvar %s not found in %s' % (name, path))
    return int(match.group(1))


# Measured in FS-UAE (9 October 2026, A1200 profile, 11 MiB Hunk; CHIM-ZONE-RESERVE-EARLY-33): the Hunk
# every map holds before its BSP (the engine at start-up), and the per-map allocations the client makes
# after the map's entities have spawned (the same on Balmora's and Seyda Neen's CHIM maps and on the
# prison ship).
MEASURED_HUNK = {'before_map_bytes': 782416, 'client_per_map_bytes': 1589344}
ZONE_HEADER_BYTES = 64          # the zone's own Hunk header and alignment (chim_world.c MapBegin)


def chim_memory(source=SOURCE, heap_mb=None):
    """The CHIM map's memory defaults (chim/chim_world.c): the zone, the frame-world pool (one block of
    twice chim_pool_kib with the incremental frame world), the Hunk the zone leaves, all in KiB; and the
    zone's room for chunks, models and textures (the builder's CHIM heap gate budget).
    heap_mb: the build's own heap (engine-build.json heap_mb, from --heap-mb); default the engine source's.
    heap_safe_mb: the largest heap measured to run the whole game on the 16 MiB Fast RAM profile."""
    if heap_mb is None:
        heap_mb = define('sys_amiga.c', 'AMIWIND_HEAP_MB', source)
    zone = cvar_default('chim/chim_world.c', 'chim_zone_kib', source)
    pool = cvar_default('chim/chim_world.c', 'chim_pool_kib', source)
    reserve = cvar_default('chim/chim_world.c', 'chim_reserve_kib', source)
    ends = cvar_default('chim/chim_world.c', 'chim_zone_ends', source)
    return {'zone_kib': zone, 'pool_kib': pool, 'reserve_kib': reserve, 'pool_block_kib': 2 * pool, 'ends_kib': ends,
            'chunk_room_kib': zone - 2 * pool, 'heap_mb': heap_mb, 'hunk_bytes': heap_mb * 1024 * 1024,
            'gap_bytes': reserve * 1024, 'heap_safe_mb': define('sys_amiga.c', 'AMIWIND_HEAP_SAFE_MB', source)}


# Measured in FS-UAE (23 October 2026, A1200 profile, 32 MiB Fast RAM, the interiors A/B runs A32/B32 of the
# v0.0.48-dev2 Balmora sandboxes): "Memory: 14 MiB Fast RAM free of 32 MiB; CHIM cache 8 MiB in 1 bank
# (automatic)" with the 13 MiB heap. What the system, the engine binary and its static buffers take before
# the heap is sized: 32 - 13 - 14 = 5 MiB (the 16 MiB smoke runs: 0 MiB free with the 11 MiB heap).
# The safe minimum Fast RAM (decided for the project, 23 October 2026, RAM-REQUIREMENT-32MB-48) and the baseline that
# still starts.
MIN_FAST_RAM_MIB = 32
BASELINE_FAST_RAM_MIB = 16
# Measured again in FS-UAE (24 October 2026, the v0.0.50 final's 32 MiB door check): "Memory: 13 MiB Fast RAM free of
# 32 MiB; CHIM cache off (not enough extra Fast RAM, standard memory)" with the 13 MiB heap: 6 MiB before the heap.
# With the 8 MiB least first bank of then that 7 MiB budget gave no bank (CHIM-AUTO-BANK-CLIFF-51).
MEASURED_FAST = {'fast_mib': 32, 'heap_mib': 13, 'free_after_heap_mib': 13, 'bank_mib': 0,
                 'system_mib': 6, 'run': 'v0.0.50 final door check at 32 MiB, 24 October 2026'}


def _mib_define(header, name, source=SOURCE):
    """A #define written as (N UL*CHIM_AUTO_MIB) in chim_zone.h, in MiB."""
    text = (Path(source) / header).read_text(encoding='utf-8', errors='replace')
    match = re.search(r'#\s*define\s+' + name + r'\s+\(\s*(\d+)UL\s*\*\s*CHIM_AUTO_MIB\s*\)', text)
    if not match:
        raise ValueError('Engine value %s not found in %s' % (name, header))
    return int(match.group(1))


def fast_ram_memory(fast_mib, source=SOURCE, system_mib=None):
    """What a machine with fast_mib MiB of Fast RAM gives a CHIM map, by the engine's own start-up rules: the heap
    (aw_heapsize.c AW_HeapAuto: margin 2 MiB plus an eighth of all Fast RAM; it grows when the room past the margin
    holds the built heap plus AW_HEAP_GROW_MIN_MB, by a quarter of what is beyond the built size, to
    AW_HEAP_AUTO_MAX_MB), then the automatic CHIM cache banks of the Fast RAM left (chim_zone.c ChimZone_AutoBudget
    and ChimZone_AutoStep, one memory region), and the zone a map takes from the heap (chim_zone_kib at most).
    The Fast RAM the system takes before the heap is the measured MEASURED_FAST['system_mib'].
    Models and textures prefer the cache banks (chim_zone.c AllocIn), so a CHIM room's models and textures fit when
    they fit the banks and the zone together (aw_autoram 1, the default)."""
    system = MEASURED_FAST['system_mib'] if system_mib is None else system_mib
    built = define('sys_amiga.c', 'AMIWIND_HEAP_MB', source)
    grow_min = define('aw_heapsize.h', 'AW_HEAP_GROW_MIN_MB', source)
    auto_max = define('aw_heapsize.h', 'AW_HEAP_AUTO_MAX_MB', source)
    floor = _mib_define('chim/chim_zone.h', 'CHIM_AUTO_FLOOR', source)
    keep = _mib_define('chim/chim_zone.h', 'CHIM_AUTO_KEEP', source)
    first_min = _mib_define('chim/chim_zone.h', 'CHIM_AUTO_FIRST', source)
    bank_max = _mib_define('chim/chim_zone.h', 'CHIM_AUTO_BANK_MAX', source)
    largest = max(0, fast_mib - system)
    margin = floor + fast_mib / 8.0
    room = int(largest - margin) if largest > margin else 0
    heap = built
    if room >= built + grow_min:
        heap = min(auto_max, built + (room - built) // 4)
        heap = max(heap, built)
    free = max(0, largest - heap)
    budget = max(0, int(free - margin))
    bank = min(max(0, free - keep), budget, bank_max)
    if bank < first_min:
        bank = 0
    memory = chim_memory(source, heap_mb=heap)
    return {'fast_mib': fast_mib, 'system_mib': system, 'heap_mb': heap, 'free_after_heap_mib': free,
            'bank_bytes': bank * 1024 * 1024, 'zone_bytes': memory['zone_kib'] * 1024,
            'buffer_bytes': cvar_default('chim/chim_world.c', 'chim_buffer_kib', source) * 1024}


def whole_map_zone(before_zone_bytes, after_zone_bytes, memory=None):
    """The whole-map Hunk rule of a CHIM map (CHIM-ZONE-RESERVE-EARLY-33), which the engine keeps and the
    builder's heap gate checks: the Hunk holds what the map loads before its zone (the engine at start-up
    and the frame map's BSP), the zone, and what the map loads after the zone (its entities' models and
    sprites, then the client's per-map allocations), and keeps chim_reserve_kib (the 2 MiB Hunk-gap
    safety) free at its load peak:

        before_zone + zone + header + after_zone + reserve <= Hunk

    The frame map states after_zone as "_chim_hunk_rest" BYTES; the engine sizes the zone so the rule
    holds (never more than chim_zone_kib), measures after_zone when the map has loaded and says so when it
    was larger. Returns the largest zone in bytes, rounded down to 16 KiB as the defaults are, and 0
    when nothing is left."""
    memory = memory or chim_memory()
    room = memory['hunk_bytes'] - memory['gap_bytes'] - before_zone_bytes - after_zone_bytes - ZONE_HEADER_BYTES
    return max(0, room // (16 * 1024) * 16 * 1024)


def limits(source=SOURCE):
    values = {key: define(header, name, source) for key, (header, name) in DEFINES.items()}
    # cl_visedicts holds every edict and every static entity (client.h MAX_VISEDICTS).
    values['max_visedicts'] = values['max_edicts'] + values['max_static_entities']
    return values
