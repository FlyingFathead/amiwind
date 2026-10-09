# SPDX-License-Identifier: GPL-3.0-only
"""Item cost history for longest-first worker pools.

A pool hands out work longest first when it knows what each item costs
(build_parallel.ordered_map(cost=...)): the long items then start early instead
of finishing last on a few workers while the rest sit idle. Costs come from:

1. history: the seconds each item took in an earlier build of the same
   workspace (the builder sets AMIWIND_COST_HISTORY to WORKSPACE/cache/item-costs;
   one JSON file per pool, item key -> seconds); the most reliable source;
2. a fallback measure the stage supplies when an item has no history (for the
   open-world regions: the source triangles of their survey cell), scaled to
   seconds by the items that have both.

Costs change only the order work is handed out; outputs keep their input order
and bytes (tests compare them with the serial path). Without the environment
variable nothing is read or written.
"""
import json
import os
from pathlib import Path

ENV = 'AMIWIND_COST_HISTORY'


def _path(name):
    folder = os.environ.get(ENV)
    if not folder:
        return None
    safe = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in name)
    return Path(folder) / f'{safe}.json'


def load(name):
    """{item key: seconds} recorded for pool `name`; {} without history."""
    path = _path(name)
    if path is None or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return {str(k): float(v) for k, v in data.get('seconds', {}).items()}
    except (OSError, ValueError, AttributeError):
        return {}


def record(name, keys, seconds):
    """Merge this run's item times into the history of pool `name` (atomic write)."""
    path = _path(name)
    if path is None:
        return
    try:
        merged = load(name)
        merged.update({str(k): round(float(s), 3) for k, s in zip(keys, seconds)})
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(f'{path.name}.{os.getpid()}.tmp')
        partial.write_text(json.dumps({'format': 'AmiWind item costs 1', 'seconds': dict(sorted(merged.items()))},
                                      indent=1) + '\n', encoding='utf-8')
        os.replace(partial, path)
    except OSError:
        pass  # history is a scheduling hint; it never fails a build


def estimator(name, keys, fallback=None):
    """cost(key) for ordered_map: history seconds where known, otherwise the
    fallback measure scaled to seconds by the median ratio over items that have
    both (1 when none do). None when neither source knows anything."""
    history = load(name)
    keys = [str(k) for k in keys]
    if fallback is None:
        if not any(k in history for k in keys):
            return None
        known = sorted(history[k] for k in keys if k in history)
        middle = known[len(known) // 2]
        return lambda key: history.get(str(key), middle)
    measures = {k: float(fallback(k)) for k in keys}
    ratios = sorted(history[k] / measures[k] for k in keys if k in history and measures[k] > 0)
    scale = ratios[len(ratios) // 2] if ratios else 1.0
    return lambda key: history[str(key)] if str(key) in history else measures[str(key)] * scale


def costed_map(name, function, items, keys, jobs=None, fallback=None):
    """build_parallel.ordered_map that hands items out longest first by their
    cost (history, else `fallback(key)`), yields results in input order and
    records this run's item times for the next build. `keys` name the items
    (one per item, stable between builds)."""
    from build_parallel import ordered_map
    items = list(items)
    keys = [str(k) for k in keys]
    if len(keys) != len(items):
        raise ValueError('costed_map needs one key per item')
    estimate = estimator(name, keys, fallback)
    by_item = {id(item): key for item, key in zip(items, keys)}
    cost = None if estimate is None else (lambda item: estimate(by_item[id(item)]))
    timings = []
    yield from ordered_map(function, items, jobs, cost=cost, timings=timings)
    record(name, keys, timings)


def room_sizes(data, rooms):
    """{map: placed references + 1} for rooms [(map, cell name)], read in one pass
    over the game data's master: the fallback cost of a room with no history. {}
    when the master or a cell does not resolve (the room conversion reports that)."""
    try:
        from mwad.interior import read_interiors
        from mwad.paths import child_ci
        cells = read_interiors(child_ci(data, 'Morrowind.esm'), [cell for _, cell in rooms])
    except (OSError, ValueError, KeyError):
        return {}
    return {name: len(cell['refs']) + 1 for (name, _), cell in zip(rooms, cells)}
