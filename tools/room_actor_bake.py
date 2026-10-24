# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM room actor bake (ROOM-ACTORS-FLOATING-48): the ground residents of every CHIM room map fitted on exactly the
collision the actor ground check measures them on, in the image step after the CHIM rooms install.

A regression of ACTOR-GROUND-BAKE-CHIM-ROOMS-48: the map bake (tools/actor_grounding.py bake_ground) skips CHIM room and
batch shell maps, so a batch room's residents kept their game-data height (1 to 15 units over the store floor) and dev2
try 11's actor check refused 1,662 of them. Kept apart from tools/actor_grounding.py on purpose: that module is read by
cached build units (CHIM world units, town and room stages), whose code keys include its import-time code; this module
is read by the image step only.
"""
import json
import os
from pathlib import Path
import re
from functools import lru_cache

from actor_grounding import (_Fitter, _SupportScene, _bake_map, _ground_entities, _ground_key, ENTITY_BLOCK,
                             ENTITY_FIELD, finish, search_offsets)
from player_hull import lumps, pack_lumps

ROOT = Path(__file__).resolve().parents[1]
ROOM_BOX_MARGIN = 4.0
ROOM_CELL_DROP = 8192 * .25      # OpenMW's trace-down length (one cell, 8192 game units) in AmiWind units
# The room residents' support probe: 'near' (the default) is the map bake's (actor_grounding.centre_support: 8 units
# over the spot, 32 under it, the first surface, walkable). 'footprint' (footprint_support with the collision-box test,
# slower: ROOM-BAKE-FOOTPRINT-SLOW-48) is the simple build-time equivalent of OpenMW's placement: the original game
# puts every NPC and creature on the ground below it at cell load however high the editor left it, and OpenMW traces
# far (OpenMW issue 3219: its initial trace-down limit of 500 game units was too small and was raised by pull request
# 1958, OpenMW 0.45; 0.51's World::adjustPosition traces one cell). Only the FIRST surface under the footprint is taken,
# only when it is walkable, a placed mesh of the room and within ROOM_HEADROOM: a resident on a balcony stays on the
# balcony, never moved to a lower storey.
ROOM_CELL_DROP_ENV = 'AMIWIND_ROOM_ACTOR_PROBE'
# Residents decided case by case (the bake's refusals): 'placements' {"<room> <reference>": {"origin": [x, y, z],
# "reason": "..."}} written as given and judged by the actor check; 'authored' {"<room> <reference>": {"id": ...,
# "reason": "..."}} kept where the game data puts them, reported by the check as explicit exceptions.
ROOM_PLACEMENTS = ROOT/'config/actor_room_placements.json'
ROOM_PLACEMENTS_FORMAT = 'AmiWind room actor placements 1'
OPENMW_LIFT = 20 * .25           # World::adjustPosition: the trace starts 20 game units over the reference position
# The headroom bound: a resident is lowered onto the first surface under it only when that surface is at most this far
# under its recorded spot; further down it is NOT moved but reported, to be decided case by case: in a multi-storey
# room the first surface under a gap is a lower storey. 32 units (128 game units) is the map bake's reach
# (centre_support) and covers the editor headroom measured on dev2 try 11 in every scene kind: CHIM batch rooms up to
# 30.6 (90% within 9.1), rooms converted whole up to 18.3, classic maps up to 26.7, CHIM frames up to 25.2.
ROOM_HEADROOM = 32.0
FOOTPRINT_SPREAD = 1.5           # sole drops further apart than this are reported (the soles disagree)
VISIT_GUARD = 'Cyclic or excessive collision tree'
FLOOR_SEGMENTS = (8.0, 4.0, 2.0)
# The CHIM room bake: 'store' (default) fits every CHIM room resident on its room's store collision in the image step;
# 'off' is the method before it (room residents keep the height the map bake or the room stage wrote; a batch room's
# residents keep their game-data height), kept for comparison.
ROOM_BAKE_ENV = 'AMIWIND_ROOM_ACTOR_BAKE'
ROOM_BAKE_MODES = ('store', 'off')


def _doc(path):
    path = Path(path or ROOM_PLACEMENTS)
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding='utf-8'))
    if doc.get('format') != ROOM_PLACEMENTS_FORMAT:
        raise ValueError('Unsupported room placements file: %s' % path.name)
    return doc


def room_placements(path=None):
    """{(room, reference): (origin, reason)} of the explicit room placements ({} when the file is missing)."""
    import math
    doc = _doc(path)
    out = {}
    for key, row in ((doc or {}).get('placements') or {}).items():
        room, reference = key.split()
        origin = [float(v) for v in row['origin']]
        if len(origin) != 3 or not all(map(math.isfinite, origin)) or not row.get('reason'):
            raise ValueError('Room placement %s needs an origin and a reason' % key)
        out[(room, reference)] = (origin, row['reason'])
    return out


def room_exceptions(path=None):
    """{(room, reference): (id lower case, reason)} of the CHIM room residents kept where the game data puts them
    (ROOM_PLACEMENTS 'authored'), each decided with its reason ({} when the file is missing). The room bake marks them
    aw_ground_mode 1 and the actor check reports them as explicit exceptions, as it does the grounding policy's."""
    doc = _doc(path)
    out = {}
    for key, row in ((doc or {}).get('authored') or {}).items():
        room, reference = key.split()
        if not row.get('id') or not row.get('reason'):
            raise ValueError('Room exception %s needs an id and a reason' % key)
        out[(room, reference)] = (row['id'].casefold(), row['reason'])
    return out


def _mark_exceptions(task):
    """Set aw_ground_mode 1 on one room map's listed residents; returns their (room, reference) keys."""
    path, listed = task
    path = Path(path)
    data = lumps(path.read_bytes())
    done = []

    def update(match):
        block = match[0]
        e = dict(ENTITY_FIELD.findall(block))
        key = (path.stem, e.get('aw_ref'))
        if e.get('classname') != 'aw_npc' or key not in listed:
            return block
        if (e.get('aw_source_id') or '').casefold() != listed[key]:
            raise ValueError('%s %s: the room exception names %s, the map %s'
                             % (key[0], key[1], listed[key], e.get('aw_source_id')))
        done.append(key)
        return re.sub(r'"aw_ground_mode"\s+"[^"\n]*"', '"aw_ground_mode" "1"', block)
    text = ENTITY_BLOCK.sub(update, data[0].decode('cp1252'))
    if done:
        data[0] = text.encode('cp1252')
        path.write_bytes(pack_lumps(data))
    return done


def footprint_support(scene, authored, samples):
    """A CHIM room resident's support by the simple equivalent of OpenMW's placement (World::adjustPosition with
    MovementSolver::traceDown: the actor's shape lowered from 20 game units over its recorded spot onto the first
    surface it meets). Each idle sole (SAMPLES, the soles the actor check measures; together the footprint) is traced
    down from OPENMW_LIFT over its recorded height to the headroom bound; lowering the actor, the first sole to touch
    stops it: the support is that sole's surface, and the origin goes where that sole rests on it (head adds 0.25,
    OpenMW's sGroundOffset of 1 game unit). The surface must be walkable and a placed mesh of the room, never its
    closing clip floor; otherwise the resident is reported, never moved past it. With no sole meeting a surface the
    centre is traced down a cell, for the report. Returns the centre_support-shaped dict ('height': the origin's resting
    height minus 0.25; 'spread': how far apart the soles' drops are)."""
    drops = []
    reach = OPENMW_LIFT+ROOM_HEADROOM+1
    for local in samples:
        foot = [authored[k]+local[k] for k in range(3)]
        hit = scene.floor([foot[0], foot[1], foot[2]+OPENMW_LIFT], reach)
        if hit['status'] != 'unsupported':
            drops.append((foot[2]-hit['height'], hit, local))
    probe = [*authored[:2], authored[2]+OPENMW_LIFT]
    if not drops:
        deep = scene.floor(probe, ROOM_CELL_DROP+OPENMW_LIFT)
        if deep['status'] == 'unsupported':
            return dict(point=probe, status='unsupported', footprint='no surface under the actor within a cell')
        return dict(deep, point=probe, height=deep['height'], footprint='the first surface is under the headroom bound')
    drop, hit, local = min(drops, key=lambda d: d[0])
    spread = max(d[0] for d in drops)-drop
    out = dict(hit, point=probe, height=authored[2]-drop, footprint_drop=round(drop, 5), spread=round(spread, 5),
               soles_hit=len(drops), soles=len(samples))
    if hit['status'] != 'supported':
        return dict(out, footprint='the first surface under the soles is %s' % hit['status'])
    if not str(hit.get('reference', '')).isdigit():
        return dict(point=probe, status='unsupported', below=hit.get('reference'),
                    footprint='the first surface under the soles is the room closing clip floor')
    return out


def room_cell_drop():
    """True for ROOM_CELL_DROP_ENV 'footprint' (footprint_support and the collision-box test), False for 'near' (the
    default: centre_support, the map bake's probe: 8 units over the spot, 32 under it, the same headroom bound)."""
    mode = os.environ.get(ROOM_CELL_DROP_ENV, '').strip() or 'near'
    if mode not in ('footprint', 'near'):
        raise ValueError('%s takes footprint or near, not %r' % (ROOM_CELL_DROP_ENV, mode))
    return mode == 'footprint'


class _RoomSupportScene(_SupportScene):
    """A room's support scene for the bake's probes. A downward probe that raises the trace visit guard on a store
    model's hull (ROOM-TRACE-VISIT-GUARD-48: ri89f2ec9f11, Assumanu Mantiti, placement 11970: any probe longer than
    8 units over his floor raises it, an 8-unit one finds the floor) is made again as consecutive shorter probes
    over the same span, top down (8, then 4, then 2 units each): the first segment with a hit gives the support, as
    the long probe's first hit would. Only the bake's fitting reads this; the packaged check traces as before.
    WHOLE: the room's complete RoomScene (the final contact test, _RoomFitter.contact)."""

    def __init__(self, original, bounds):
        super().__init__(original, bounds)
        self.whole = original

    def floor(self, point, drop):
        # once a probe of this room raised the guard, longer probes go straight to segments (the guard is reached only
        # after the trace's whole visit budget: hundreds of thousands of node visits each time)
        last = None
        if not (getattr(self.whole, 'guarded', False) and drop > FLOOR_SEGMENTS[0]):
            try:
                return super().floor(point, drop)
            except ValueError as error:
                if str(error) != VISIT_GUARD:
                    raise
                last = error
                self.whole.guarded = True
        for step in FLOOR_SEGMENTS:
            try:
                return self._segmented_floor(point, drop, step)
            except ValueError as error:
                if str(error) != VISIT_GUARD:
                    raise
                last = error
        raise last

    def _segmented_floor(self, point, drop, step):
        import math
        count = max(1, math.ceil(drop/step))
        for k in range(count):
            top = point[2]-drop*k/count
            length = drop/count
            hit = super().floor((point[0], point[1], top), length)
            if hit['status'] != 'unsupported':
                # a later segment starting inside solid is the long probe's hit at that segment's top
                return dict(hit, point=list(point), segmented=step)
        return dict(point=list(point), status='unsupported')


class _RoomFitter(_Fitter):
    """Support fitting for the residents of CHIM room maps (maps/<room>.chim) on the collision the packaged check
    measures them on: chim.room_scene.RoomScene, the room map's own world and clip models plus every placement of its
    room record (the store models)."""

    def __init__(self, maps):
        super().__init__(maps)
        self._boxes = {}
        self.hull = lru_cache(maxsize=4)(self._hull)

    def _hull(self, name):
        """The room's standing-hull collision (the converted humanoid box, the resident's own box), for fits()."""
        from chim.room_scene import RoomScene
        from map_files import map_file
        whole = RoomScene(map_file(self.maps, name), hull=1)
        boxes = self.boxes(name)
        if len(boxes) != len(whole.brushes):
            return _RoomSupportScene(whole, [(brush, None) for brush in whole.brushes])
        grow = 8.0   # each trace reads only the brushes whose box, grown by the hull's half width, its segment meets
        return _RoomSupportScene(whole, [(brush, None if box is None else
                                          (box[0]-grow, box[1]-grow, box[2]+grow, box[3]+grow))
                                         for brush, box in zip(whole.brushes, boxes)])

    def _scene(self, name):
        from chim.room_scene import RoomScene
        from map_files import map_file
        try:
            return RoomScene(map_file(self.maps, name), hull=0)
        except ValueError as error:   # every failure names its unit (the room map)
            raise ValueError(name + '.chim: ' + str(error)) from error

    def boxes(self, name):
        """The xy box (x0, y0, x1, y1) of every brush of the room's RoomScene, in its order (None: always traced):
        the map's world (None) and clip models, then each record placement's store model bounds turned and moved."""
        if name not in self._boxes:
            import itertools
            import struct
            from audit_walkability import axes
            from check_actor_ground import entities
            from chim import format as F
            from chim.interior import installed_room, store_model_images
            from map_files import map_file
            path = map_file(self.maps, name)
            raw = path.read_bytes()
            models = list(struct.iter_unpack('<9f7i', lumps(raw)[14]))
            objects = [dict(model='*0')] + [e for e in entities(raw)
                                             if e.get('classname') == 'func_wall' and re.fullmatch(r'\*\d+', e.get('model', ''))]

            def box(m, origin, basis):
                corners = [tuple(origin[i]+sum(v[j]*basis[j][i] for j in range(3)) for i in range(3))
                           for v in itertools.product(*[(m[k], m[k+3]) for k in range(3)])]
                # a margin: a store model's hull can reach past its bounds (the final contact test reads every brush)
                return tuple([min(v[k] for v in corners)-ROOM_BOX_MARGIN for k in (0, 1)] +
                             [max(v[k] for v in corners)+ROOM_BOX_MARGIN for k in (0, 1)])
            out = []
            for e in objects:
                if e['model'] == '*0':
                    out.append(None)
                    continue
                origin = tuple(map(float, e.get('origin', '0 0 0').split()))
                out.append(box(models[int(e['model'][1:])], origin, axes(tuple(map(float, e.get('angles', '0 0 0').split())))))
            room = installed_room(path)
            images = store_model_images(self.maps.parent, room['store'], [p['model'] for p in room['placements']])
            bounds = {}
            for p in room['placements']:
                if p['model'] not in bounds:
                    bounds[p['model']] = struct.unpack_from('<9f7i', F.read_brush_image(images[p['model']])[14])
                out.append(box(bounds[p['model']], tuple(p['origin']), axes(tuple(p['angles']))))
            self._boxes[name] = out
        return self._boxes[name]

    def neighbourhood(self, name, point, samples):
        # As _Fitter.neighbourhood: conservative model bounds only speed up the search; the room's whole collision is
        # kept for every brush near the spot, and the final contact test reads the complete RoomScene.
        whole = self.scene(name)
        boxes = self.boxes(name)
        if len(boxes) != len(whole.brushes):
            near = _RoomSupportScene(whole, [(brush, None) for brush in whole.brushes])
        else:
            reach = 34+max(max(abs(v[0]), abs(v[1])) for v in samples)
            selected = [(brush, box) for brush, box in zip(whole.brushes, boxes)
                        if box is None or (box[2] >= point[0]-reach and box[0] <= point[0]+reach and
                                           box[3] >= point[1]-reach and box[1] <= point[1]+reach)]
            near = _RoomSupportScene(whole, selected)
        near.room = name
        return near

    def contact(self, s, point, samples):
        """The final test of a spot, on the room's whole collision: every sole on the floor exactly as the packaged
        check traces it (a store model's hull can reach past its model bounds: ri68c97f8719, placement 91935, 1 unit,
        so the filtered scene only proposes spots), and, with the footprint probe, the resident's box free (fits)."""
        try:
            if not _Fitter.contact(getattr(s, 'whole', s), point, samples):
                return False
        except ValueError as error:   # a trace the check could not make either: not a contact
            if str(error) != VISIT_GUARD:
                raise
            return False
        room = getattr(s, 'room', None)
        return room is None or not room_cell_drop() or self.fits(room, point)

    def owned(self, name, candidate):
        """A room owns all its space (no owner cores inside a room)."""
        return True

    def _setup(self, name, e, authored, angles):
        """As _Fitter._setup; with the footprint probe (room_cell_drop) the support of footprint_support instead of
        centre_support, a first surface further than ROOM_HEADROOM under the recorded spot reported (storey_below,
        with the nearest surfaces below and above), never used."""
        key = (name, e['model'], e.get('aw_intro_role', 0), tuple(authored), angles)
        known = key in self.setups
        samples, s, center = super()._setup(name, e, authored, angles)
        if known or not room_cell_drop():
            return samples, s, center
        center = footprint_support(s, authored, list(samples))
        if 'height' in center and authored[2]-center['height'] > ROOM_HEADROOM:
            start = [*authored[:2], authored[2]+OPENMW_LIFT]
            try:
                above = s.trace(start, [start[0], start[1], start[2]+512])
            except ValueError:
                above = None
            center = dict(point=center.get('point'), status='unsupported', footprint=center.get('footprint'),
                          storey_below=round(authored[2]-center['height'], 5),
                          nearest_below=round(center['height'], 5), nearest_below_status=center['status'],
                          nearest_below_reference=center.get('reference'),
                          nearest_above=round(start[2]+512*above['fraction'], 5) if above else None,
                          nearest_above_reference=above.get('reference') if above else None)
        self.setups[key] = (samples, s, center)
        return samples, s, center

    def fits(self, name, point):
        """The resident's collision box (the standing hull, feet at POINT) is in no solid: no wall, table or railing
        through it."""
        hull = self.hull(name)
        centre = [point[0], point[1], point[2]+16.625]   # player_hull.MINS[2]: the box's centre over its feet
        try:
            return hull.floor([centre[0], centre[1], centre[2]+.05], .1)['status'] != 'blocked'
        except ValueError as error:
            if str(error) != VISIT_GUARD:
                raise
            return False

    def head(self, name, e, authored, angles):
        override = room_placements().get((name, str(e.get('aw_ref'))))
        if override is not None:
            result = dict(map=name, reference=e.get('aw_ref'), source_id=e.get('aw_source_id'), name=e.get('netname'),
                          authored_origin=authored, authored_z=authored[2], status='supported',
                          placed_origin=override[0], placed_z=override[0][2], mesh_contact='override',
                          override_reason=override[1], attempts=0)
            return result, None
        result, original = super().head(name, e, authored, angles)
        samples, s, center = self._setup(name, e, authored, angles)
        for field in ('storey_below', 'nearest_below', 'nearest_below_status', 'nearest_below_reference',
                      'nearest_above', 'nearest_above_reference', 'footprint', 'footprint_drop', 'spread',
                      'soles_hit'):
            if field in center:
                result[field] = center[field]
        if center.get('spread', 0) > FOOTPRINT_SPREAD:
            result['soles_disagree'] = True
        return result, original


_FITTER = [None, None]   # (call token, fitter) of the current bake in this process


def _fitter(token, maps):
    if _FITTER[0] != token:
        _FITTER[:] = [token, _RoomFitter(maps)]
    return _FITTER[1]


def _fit_head(task):
    """Worker: support and the vertical fit of one placement."""
    token, maps, name, e, authored, angles = task
    return _fitter(token, maps).head(name, e, authored, angles)


def _fit_search(task):
    """Worker: one slice of one placement's offset search."""
    token, maps, name, e, authored, angles, original, first, last = task
    return _fitter(token, maps).search(name, e, authored, angles, original, first, last)


SEARCH_SLICE = 32


def _fit_all(tasks, jobs):
    """actor_grounding._fit_all with the room fitter: heads, then the sliced offset searches, in one worker pool; the
    first passing offset in search order wins."""
    from concurrent.futures import FIRST_COMPLETED, wait
    from build_parallel import live_jobs, process_pool, worker_environment
    offsets = len(search_offsets())
    slices = -(-offsets // SEARCH_SLICE)
    jobs = live_jobs(jobs)

    def search_task(index, number, head):
        first = number * SEARCH_SLICE
        return (*tasks[index], head[1], first, min(first + SEARCH_SLICE, offsets))
    if jobs <= 1 or not tasks:
        heads = [_fit_head(task) for task in tasks]
        found = {}
        for index, head in enumerate(heads):
            if head[1] is None:
                continue
            for number in range(slices):
                hit = _fit_search(search_task(index, number, head))
                if hit is not None:
                    found[index] = hit
                    break
        return heads, found
    workers = max(1, min(jobs, len(tasks) * slices))
    with worker_environment(), process_pool(workers) as pool:
        heads = list(pool.map(_fit_head, tasks))
        open_ = [index for index, head in enumerate(heads) if head[1] is not None]
        following = dict.fromkeys(open_, 0)
        first_hit, found, pending = {}, {}, {}
        turn = [0]

        def wanted(index):
            return following[index] < min(slices, first_hit.get(index, slices))

        def submit():
            while len(pending) < 2 * workers:
                candidates = [index for index in open_ if wanted(index)]
                if not candidates:
                    return
                index = candidates[turn[0] % len(candidates)]
                turn[0] += 1
                number = following[index]
                following[index] += 1
                pending[pool.submit(_fit_search, search_task(index, number, heads[index]))] = (index, number)
        try:
            submit()
            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    index, number = pending.pop(future)
                    hit = future.result()
                    if hit is not None and number < first_hit.get(index, slices):
                        first_hit[index], found[index] = number, hit
                for future, (index, number) in list(pending.items()):
                    if number > first_hit.get(index, slices) and future.cancel():
                        pending.pop(future)
                submit()
        finally:
            for future in pending:
                future.cancel()
    return heads, found


def _bake(maps, paths, jobs, token):
    """actor_grounding.bake_ground's fit and write over PATHS (room maps in MAPS) with the room fitter."""
    from build_parallel import ordered_map

    def workers(count):
        return max(1, min(jobs, count))
    found = list(ordered_map(_ground_entities, [str(p) for p in paths], workers(len(paths))))
    order, keyed, pending = [], {}, {}
    for path, actors in zip(paths, found):
        for e in actors:
            selected, key, authored, angles = _ground_key(maps, path.stem, e)
            if key in keyed:
                continue
            keyed[key] = (selected, len(pending.setdefault(selected, [])))
            pending[selected].append((selected, e, authored, angles))
            order.append((key, selected, e))
    owners = sorted(pending)
    tasks = [(token, str(maps), *item) for o in owners for item in pending[o]]
    heads, best = _fit_all(tasks, jobs)
    flat = iter([result if original is None else finish(result, best.get(index))
                 for index, (result, original) in enumerate(heads)])
    fitted = {o: [next(flat) for _ in pending[o]] for o in owners}
    results, report = {}, []
    for key, selected, e in order:
        owner_name, index = keyed[key]
        results[key] = fitted[owner_name][index]
        report.append(results[key])
    tasks = [(str(path), {key: results[key] for key in {_ground_key(maps, path.stem, e)[1] for e in actors}})
             for path, actors in zip(paths, found) if actors]
    list(ordered_map(_bake_map, tasks, workers(len(tasks))))
    return report


def unfitted_ground_residents(maps, exclude=()):
    """[(map, reference)] of the ground residents of every scene the actor check reads as a map (check_actor_ground:
    map_files.scene_maps, every x.bsp and every CHIM room map, whole or batch) that no ground bake visited: a bake
    writes aw_authored_origin on every resident it fits or refuses. CHIM frame residents are fitted by their town stage
    (chim_town.ground_actors) and judged through its results, not here. Map file names in EXCLUDE (recorded-stage maps)
    are left out. The guard of ROOM-ACTORS-FLOATING-48: a scene kind a bake skips shows here, before the check."""
    from map_files import scene_maps
    out = []
    for path in scene_maps(maps):
        if path.name in exclude:
            continue
        for e in _ground_entities(path):
            if 'aw_authored_origin' not in e:
                out.append((path.stem, e.get('aw_ref', 'intro')))
    return out


def require_fitted(maps, exclude=()):
    """Raise when a ground resident of a scene map was never fitted (unfitted_ground_residents)."""
    missing = unfitted_ground_residents(maps, exclude)
    if missing:
        rooms = sorted({m for m, _ in missing})
        raise ValueError('%d ground residents in %d maps were never fitted by a ground bake (first: %s; '
                         'ROOM-ACTORS-FLOATING-48)' % (len(missing), len(rooms), ', '.join(rooms[:5])))
    return 0


def room_bake_mode():
    mode = os.environ.get(ROOM_BAKE_ENV, '').strip() or 'store'
    if mode not in ROOM_BAKE_MODES:
        raise ValueError('%s takes %s, not %r' % (ROOM_BAKE_ENV, ' or '.join(ROOM_BAKE_MODES), mode))
    return mode


def actor_state_classes(maps, master):
    """{class: count} of the ground-mode residents of every CHIM room map by their record (MASTER: the game data's
    bytes): 'npc', 'creature: walks', 'creature: flies, does not walk', 'creature: swims, does not walk' (CREA FLAG,
    creature_library.SWIMS/FLIES/WALKS), 'unknown record'; and the residents a ground fit would wrongly put on the
    floor (a creature that flies or swims and does not walk)."""
    import collections
    from creature_library import plan, SWIMS, FLIES, WALKS
    from map_files import room_maps
    from mwad.audit import records, subrecords, string
    creatures = {k: v['flags'] for k, v in plan(master)['bases'].items()}
    npcs = set()
    for tag, flags, payload in records(master):
        if tag == 'NPC_':
            name = next((d for t, d in subrecords(payload) if t == 'NAME'), None)
            if name is not None:
                npcs.add(string(name, errors='replace').casefold())
    counts, wrong = collections.Counter(), []
    for path in room_maps(maps):
        for e in _ground_entities(path):
            ident = (e.get('aw_source_id') or '').casefold()
            if ident in creatures:
                fl = creatures[ident]
                kind = ('creature: flies, does not walk' if fl & FLIES and not fl & WALKS else
                        'creature: swims, does not walk' if fl & SWIMS and not fl & WALKS else 'creature: walks')
                if kind != 'creature: walks':
                    wrong.append((path.stem, e.get('aw_ref'), ident, kind))
            else:
                kind = 'npc' if ident in npcs else 'unknown record'
            counts[kind] += 1
    return dict(sorted(counts.items())), wrong


def bake_room_ground(maps, jobs=1, master=None):
    """Fit the ground residents of every CHIM room map in MAPS (maps/<room>.chim) on exactly the collision the
    packaged check measures (chim.room_scene.RoomScene): the first walkable surface under the resident within the
    probe (8 units over, 32 under: the headroom bound), the origin 0.25 over it (OpenMW's 1 game unit), every idle sole
    within the check's -0.5..1.0 on the room's whole collision, else the map bake's offset search for the nearest spot;
    anything else is refused and reported. Residents decided case by case (ROOM_PLACEMENTS) are kept where the game
    data puts them ('authored', marked aw_ground_mode 1) or placed as given ('placements'). With MASTER (the game data's
    bytes' path) the ground residents are classified by record first: a creature that flies or swims and does not walk
    stops the bake. The fields are the map bake's (origin, aw_ground_valid, aw_ground_baked, aw_authored_origin/z).

    Runs in the image step after the CHIM rooms install and before the actor ground check. Returns the counts and the
    rows: unchanged = the fitted origin is the one the map already had, fitted = moved, refused = no supporting spot
    (left where it was, the check reports it)."""
    from map_files import room_maps
    maps = Path(maps)
    mode = room_bake_mode()
    if mode == 'off':
        return dict(mode=mode, rooms=0, residents=0, unchanged=0, fitted=0, refused=0, refused_by_status={},
                    storey_below=0, soles_disagree=0, overrides=0, room_exceptions=0, record_classes=None, rows=[])
    import collections
    import uuid
    classes = None
    if master is not None:
        classes, wrong = actor_state_classes(maps, Path(master).read_bytes())
        print('CHIM room actor bake: ground residents by record: %s' % ', '.join('%s %d' % kv for kv in classes.items()),
              flush=True)
        if wrong:
            raise ValueError('%d CHIM room residents are ground residents but their creature record flies or swims '
                             'and does not walk (first: %s); classify them (config/actor_grounding.json)'
                             % (len(wrong), ', '.join('%s %s %s' % w[:3] for w in wrong[:5])))
    paths = room_maps(maps)
    listed = room_exceptions()
    marked = []
    for path in paths:
        mine = {k: v[0] for k, v in listed.items() if k[0] == path.stem}
        if mine:
            marked += _mark_exceptions((str(path), mine))
    if marked:
        print('CHIM room actor bake: %d residents kept where the game data puts them (config/actor_room_placements.json)'
              % len(marked), flush=True)
    before = {}
    for path in paths:
        for e in _ground_entities(path):
            before.setdefault((path.stem, e.get('aw_ref')), [float(v) for v in e['origin'].split()])
    report = _bake(maps, paths, jobs, 'room:' + uuid.uuid4().hex)
    counts = {'unchanged': 0, 'fitted': 0, 'refused': 0}
    rows = []
    for r in report:
        placed = r.get('placed_origin')
        old = before.get((r['map'], r.get('reference')))
        if placed is None:
            kind = 'refused'
        elif old is not None and max(abs(a - b) for a, b in zip(placed, old)) <= 1e-4:
            kind = 'unchanged'
        else:
            kind = 'fitted'
        counts[kind] += 1
        rows.append(dict(r, room_bake=kind, previous_origin=old))
    refused = collections.Counter('storey below' if 'storey_below' in r else
                                  r['status'] if r['status'] != 'supported' else r.get('mesh_contact', 'unresolved')
                                  for r in rows if r['room_bake'] == 'refused')
    flags = dict(storey_below=sum(1 for r in rows if 'storey_below' in r),
                 soles_disagree=sum(1 for r in rows if r.get('soles_disagree')),
                 overrides=sum(1 for r in rows if r.get('mesh_contact') == 'override'))
    print('CHIM room actor bake: %d residents in %d rooms on their store collision: %d fitted, %d unchanged, '
          '%d refused (%s); %d kept as decided; reported: %d with the first surface more than %.0f units under them '
          '(not moved), %d whose soles disagree by more than %.1f; %d explicit placements'
          % (len(rows), len({r['map'] for r in rows}), counts['fitted'], counts['unchanged'], counts['refused'],
             ', '.join('%s %d' % kv for kv in sorted(refused.items())) or 'none', len(marked), flags['storey_below'],
             ROOM_HEADROOM, flags['soles_disagree'], FOOTPRINT_SPREAD, flags['overrides']), flush=True)
    return dict(mode=mode, rooms=len(paths), residents=len(rows), **counts, refused_by_status=dict(sorted(refused.items())),
                **flags, record_classes=classes, room_exceptions=len(marked), rows=rows)
