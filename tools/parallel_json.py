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
from pathlib import Path

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
    from build_parallel import in_order_map, ordered_map, stage_ceiling
    # in_order_map (BUILD-STATS-SERIAL-36): completed_map's scheduling, no scan of every held batch per submission;
    # AMIWIND_JSON_POOL=ordered keeps ordered_map (the method before v0.0.48). The same text either way.
    import os
    if os.environ.get('AMIWIND_JSON_POOL', 'in-order') != 'ordered':
        ordered_map = in_order_map
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


def _load_items(task):
    """Worker of load_list: the items of one byte range of the list (whole items, each followed by ',' or the end),
    each cut to the KEEP keys."""
    path, start, end, keep = task
    with open(path, 'rb') as stream:
        stream.seek(start)
        raw = stream.read(end - start)
    items = json.loads('[' + raw.decode('utf-8').rstrip().rstrip(',') + ']')
    return [{k: item[k] for k in keep if k in item} for item in items] if keep is not None else items


def _whole_list(path, key, keep):
    items = json.loads(Path(path).read_text(encoding='utf-8'))[key]
    return [{k: item[k] for k in keep if k in item} for item in items] if keep is not None else items


def load_list(path, key, keep=None, jobs=None, indent=1):
    """The list at the top-level KEY of the JSON document at PATH, written as dumps writes it (INDENT, one item per
    '{' line at the list's item indent), each item cut to the KEEP keys (None: whole): what
    json.loads(text)[key] gives, read on the worker pool (BUILD-IMAGE-UNDERUSED-32: the image step parsed the
    694 MB CHIM source manifest on one core for 8.5 to 12 s to keep three keys of each frame). The items' byte
    ranges are found in the file (no string holds a raw newline, so a line that opens a list item at the item
    indent is one), each worker parses whole items of its ranges. A document of any other layout, or
    AMIWIND_JSON_POOL=ordered (the method before), is parsed whole (a missing KEY: KeyError, as json.loads(...)[key])."""
    import mmap
    import os
    from build_jobs import resolve_jobs
    from build_parallel import in_order_map, stage_ceiling
    jobs = stage_ceiling(resolve_jobs(jobs))
    if os.environ.get('AMIWIND_JSON_POOL', 'in-order') == 'ordered' or jobs <= 1:
        return _whole_list(path, key, keep)
    pad = b' ' * indent
    with open(path, 'rb') as stream:
        if os.fstat(stream.fileno()).st_size == 0:
            return _whole_list(path, key, keep)
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
            opening = data.find(b'\n' + pad + json.dumps(key).encode('utf-8') + b': [\n')
            if opening < 0 or data[:2] != b'{\n':
                return _whole_list(path, key, keep)
            first = data.find(b'\n', opening + 1) + 1
            closing = data.find(b'\n' + pad + b']', first - 1)
            item = b'\n' + pad * 2 + b'{'
            starts, at = [first], first - 1
            if data[first:first + len(item) - 1] != item[1:] or closing < 0:
                return _whole_list(path, key, keep)
            while True:
                at = data.find(item, at + 1, closing)
                if at < 0:
                    break
                starts.append(at + 1)
    if len(starts) < 2:
        return _whole_list(path, key, keep)
    size = max(1, -(-len(starts) // (TASKS_PER_WORKER * jobs)))
    bounds = starts[::size] + [closing]
    tasks = [(str(path), bounds[k], bounds[k + 1], tuple(keep) if keep is not None else None)
             for k in range(len(bounds) - 1)]
    return [item for items in in_order_map(_load_items, tasks, min(jobs, len(tasks))) for item in items]


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
