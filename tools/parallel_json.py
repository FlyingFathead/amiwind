# SPDX-License-Identifier: GPL-3.0-only
"""JSON documents written by several workers, byte for byte what json.dumps writes (BUILD-CHIM-SERIAL-SECTIONS-44).

json.dumps with an indent runs the pure Python encoder: a CHIM world's source manifest (about 700 MB for 1,351
frames) and its statistics (about 110 MB) took most of a minute each on one core at the end of the world conversion
and in the statistics. The large lists of such a document are independent: each item's text depends only on the item
and on how deep the list sits. dumps() encodes the document without those lists, then the lists' items in batches on
the worker pool, and puts the texts together where json.dumps would have written them: the same bytes (tests compare
them with json.dumps). Only lists below dictionaries (a path of keys from the top) are split.
"""
import json

BATCH_ITEMS = 256           # items per worker task at most (small items such as a placement row are batched)
TASKS_PER_WORKER = 4        # and at least this many tasks per worker for a list (large items: a frame's section)


def _encode(items, prefix, indent, sort_keys):
    """Worker: the text of ITEMS as json.dumps writes them inside a list whose items sit at PREFIX."""
    return ',\n'.join(prefix + json.dumps(item, indent=indent, sort_keys=sort_keys).replace('\n', '\n' + prefix)
                      for item in items)


def _encode_task(task):
    return _encode(*task)


def dumps(value, paths, indent=1, sort_keys=True, jobs=1):
    """json.dumps(value, indent=INDENT, sort_keys=SORT_KEYS) with the lists at PATHS (tuples of dictionary keys from
    the top) encoded on up to JOBS workers. A path that does not lead to a list through dictionaries is encoded as
    part of the document, as before."""
    if not isinstance(indent, int) or indent < 0:
        raise ValueError('parallel_json.dumps needs a whole-number indent')
    skeleton, lists = _skeleton(value, [tuple(p) for p in paths])
    text = json.dumps(skeleton, indent=indent, sort_keys=sort_keys)
    if not lists:
        return text
    from build_parallel import ordered_map, stage_ceiling
    jobs = stage_ceiling(jobs)
    tasks, owners = [], []
    for n, (path, items, marker) in enumerate(lists):
        prefix = ' ' * (indent * (len(path) + 1))
        size = max(1, min(BATCH_ITEMS, -(-len(items) // (TASKS_PER_WORKER * max(1, jobs)))))
        for k in range(0, len(items), size):
            tasks.append((items[k:k + size], prefix, indent, sort_keys))
            owners.append(n)
    if jobs > 1 and len(tasks) > 1:
        texts = ordered_map(_encode_task, tasks, min(jobs, len(tasks)), cost=lambda t: len(t[0]))
    else:
        texts = map(_encode_task, tasks)
    parts = [[] for _ in lists]
    for n, piece in zip(owners, texts):
        parts[n].append(piece)
    for n, (path, items, marker) in enumerate(lists):
        if items:
            body = '[\n' + ',\n'.join(parts[n]) + '\n' + ' ' * (indent * len(path)) + ']'
        else:
            body = '[]'
        encoded = json.dumps(marker)
        if text.count(encoded) != 1:
            raise ValueError('parallel_json: the place of %s is not unique' % (path,))
        text = text.replace(encoded, body)
    return text


def _skeleton(value, paths):
    """(a copy of VALUE with each list at PATHS replaced by a unique marker string, [(path, list, marker)])."""
    lists = []
    taken = set()

    def walk(node, path):
        if not isinstance(node, dict):
            return node
        out = {}
        for key, item in node.items():
            here = path + (key,)
            if here in paths and isinstance(item, list) and here not in taken:
                taken.add(here)
                marker = '\u0000parallel-json-list-%d\u0000' % len(lists)
                lists.append((here, item, marker))
                out[key] = marker
            elif any(p[:len(here)] == here for p in paths):
                out[key] = walk(item, here)
            else:
                out[key] = item
        return out
    return walk(value, ()), lists
