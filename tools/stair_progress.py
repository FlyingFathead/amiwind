# SPDX-License-Identifier: GPL-3.0-only
"""How many steps and ramps a stair walk will check, counted before it starts, for the progress counter
(tools/progress_line.py: [done/total stairs | done/total frames or maps]).

A walk checks every candidate step and ramp that stair_walk.candidates finds in a core's polygons (polygons only,
no traces: cheap next to the walk). The count runs in the worker pool over the frames and maps that will be walked;
a reused one counts its recorded rows. Kept apart from the walkers (chim.collision, stair_walk): their code is part
of every stored walk's key, and a progress counter must not make stored walks go cold.
"""
import hashlib
import json
from pathlib import Path



def chim_count_task(task):
    """Worker: (frame index, steps and ramps the frame's walk will check) for TASK (world folder, frame index,
    [core...]), with the same polygon filter as chim.collision.stair_task."""
    from chim.collision import _poly_box, frame_polys, stair_polys
    from stair_walk import candidates
    out, frame_index, cores = task
    # the frame's own files only (chim.validate.load_frame), never the whole world per worker
    from chim.validate import load_frame
    row, models = load_frame(out, frame_index)
    world = {'frames': {frame_index: row}, 'models': models}
    polys = [(pts, ref, _poly_box(pts)) for pts, ref in frame_polys(world, frame_index)]
    total = 0
    for core in cores:
        total += len(candidates(stair_polys(polys, core)[1], core))
    return frame_index, total


def chim_core_counts_task(task):
    """Worker: (frame index, [steps and ramps per core]) for TASK (world folder, frame index, [core...][, walk
    area]): the count per core, in core order, with the same polygon filter as chim.collision.stair_task (with a
    walk area only the steps and ramps chim.collision.stair_task_in walks: riser point in the area). The CHIM stair
    gate's scheduler sizes its units by these counts and skips the cores without any (they walk nothing)."""
    from chim.collision import _poly_box, frame_polys, in_walk_area, stair_polys
    from stair_walk import candidates
    out, frame_index, cores = task[:3]
    area = task[3] if len(task) > 3 else None
    from chim.validate import load_frame
    row, models = load_frame(out, frame_index)
    world = {'frames': {frame_index: row}, 'models': models}
    polys = [(pts, ref, _poly_box(pts)) for pts, ref in frame_polys(world, frame_index)]
    found = []
    for core in cores:
        items = candidates(stair_polys(polys, core)[1], core)
        found.append(len(items) if area is None else sum(1 for i in items if in_walk_area(area, i['point'])))
    return frame_index, found


def count_map(task):
    """Worker: steps and ramps one legacy map's walk will check (its candidates, the scope applied), or the rows of
    its checked record when it is reused. TASK as stair_walk.check_map_cached."""
    from stair_walk import _faces, candidates, flight_items
    path, core, models, cache = task[:4]
    scope = task[4] if len(task) > 4 else 'all'
    again = task[5] if len(task) > 5 else False
    raw = Path(path).read_bytes()
    if cache is not None and not again:
        import stair_records
        record, mark = stair_records.lookup(cache, hashlib.sha256(raw).hexdigest() + ':' + json.dumps(core))
        if record is not None and mark is not None:
            return len(record['rows'])
    items = candidates(_faces(raw), core)
    return len(flight_items(items) if scope == 'flights' else items)
