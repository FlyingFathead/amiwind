# SPDX-License-Identifier: GPL-3.0-only
"""Explicit NPC grounding policy and source identity for runtime release audits."""
import json
from pathlib import Path
import re
from mwad.audit import records, subrecords, cell_data
from player_hull import lumps, pack_lumps
from audit_walkability import Scene
from functools import lru_cache

POLICY = Path(__file__).resolve().parents[1]/'config/actor_grounding.json'
INTRO_IDS = {1:'chargen name',2:'chargen boat guard 2',3:'chargen boat guard 3',
             4:'chargen boat guard 1',5:'chargen dock guard',6:'chargen class',
             7:'chargen captain',8:'chargen door guard'}


def initial_state(identifier):
    policy = json.loads(POLICY.read_text())
    if policy['format'] != 2 or policy['unclassified'] != 'error':
        raise ValueError('Unsupported grounding policy')
    identifier=identifier.casefold()
    rules={key.casefold():value for key,value in policy['exceptions'].items()}
    if identifier in rules:
        rule=rules[identifier]
        if rule['mode'] not in ('scripted_airborne','flying','levitating','swimming','authored_dead') or not rule.get('reason'):
            raise ValueError('Unknown or undocumented initial support state')
        return rule['mode']
    if identifier in policy['ground_npcs']:return 'ground'
    raise ValueError('Unclassified initial support state: '+identifier)


def fields(identifier):
    if any(c in identifier for c in ('"','\n','\r','\0')):raise ValueError('Invalid source ID')
    return {'aw_source_id': identifier, 'aw_ground_mode': int(initial_state(identifier)!='ground')}


def _actor_numbers(path):
    """Worker: the reference numbers of one map's actor entities, in order."""
    numbers = []
    for block in re.findall(r'\{[^{}]*\}', lumps(Path(path).read_bytes())[0].decode('cp1252')):
        e = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block))
        if e.get('classname') in ('aw_npc', 'aw_corpse'):
            numbers.append(int(float(e.get('aw_ref', '0'))))
    return numbers


def _annotate_map(task):
    """Worker: write source identity fields into one map's actor entities."""
    path, refs = task
    path = Path(path); rows = []
    data = lumps(path.read_bytes()); changed = [False]
    def update(match):
        block = match[0]; e = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block))
        if e.get('classname') not in ('aw_npc','aw_corpse'): return block
        identifier = refs.get(int(float(e.get('aw_ref', '0')))) or INTRO_IDS.get(int(float(e.get('aw_intro_role',0))))
        if not identifier:raise ValueError(path.name+': actor has no original identity')
        values = fields(identifier)
        for key in values: block = re.sub(r'\n"'+key+r'"\s+"[^"\n]*"', '', block)
        addition = ''.join(f'"{key}" "{value}"\n' for key, value in values.items())
        changed[0] = True
        rows.append(dict(map=path.stem, reference=e.get('aw_ref'), **values))
        return block[:-1]+addition+'}'
    text = re.sub(r'\{[^{}]*\}', update, data[0].decode('cp1252'))
    if changed[0]: data[0] = text.encode('cp1252'); path.write_bytes(pack_lumps(data))
    return rows


def annotate(maps, master, jobs=1, exclude=()):
    """Upgrade retained BSP entity metadata without changing geometry or placement.

    Up to `jobs` workers (shared pool) scan every map for actors and rewrite
    the maps that have them; each gets only the source identities it needs.
    The report keeps sorted map order, as in the serial pass. Map file names
    in `exclude` (recorded-stage maps, tools/recorded_stage.py) are not touched.
    """
    from build_parallel import ordered_map
    refs = {}
    for kind, flags, raw in records(Path(master).read_bytes()):
        if kind != 'CELL': continue
        for ref in cell_data(list(subrecords(raw)))['refs']:
            if not ref.get('deleted'): refs[ref['number']] = ref['id']
    paths = [p for p in sorted(Path(maps).glob('*.bsp')) if p.name not in exclude]
    numbers = list(ordered_map(_actor_numbers, [str(p) for p in paths], max(1, min(jobs, len(paths) or 1))))
    tasks = [(str(path), {n: refs[n] for n in found if n in refs}) for path, found in zip(paths, numbers) if found]
    report = []
    for rows in ordered_map(_annotate_map, tasks, max(1, min(jobs, len(tasks) or 1))):
        report.extend(rows)
    return report


def contact_interval_choice(low, high, preferred):
    """Keep a numerical inset without discarding a narrow feasible sole interval."""
    import math
    if not all(math.isfinite(v) for v in (low, high, preferred)) or low > high:
        return None
    inset = min(.02, (high-low)/4)
    return min(high-inset, max(low+inset, preferred))


OFFSETS = sorted(((x*.5, y*.5) for x in range(-64, 65) for y in range(-64, 65)
                  if x*x+y*y <= 4096), key=lambda p: (p[0]*p[0]+p[1]*p[1], p))


class _Fitter:
    """Support fitting for actors owned by staged maps (one per worker)."""

    def __init__(self, maps):
        self.maps = Path(maps)
        self.scene = lru_cache(maxsize=8)(self._scene)
        self.setups = {}  # placement -> (samples, neighbourhood scene, centre support)
        self.soles = lru_cache(maxsize=128)(self._soles)

    def _scene(self, name):
        return Scene((self.maps/(name+'.bsp')).read_bytes(), hull=0)

    def _soles(self, model, angles, intro):
        from check_actor_ground import model_frames, contact_samples
        name = Path(model)
        if name.is_absolute() or '..' in name.parts: raise ValueError('Unsafe actor model path')
        return tuple(contact_samples(model_frames((self.maps.parent/name).read_bytes()), angles, intro))

    @staticmethod
    def contact(s, point, samples):
        for local in samples:
            foot = [point[k]+local[k] for k in range(3)]
            hit = s.floor((foot[0], foot[1], foot[2]+2), 6)
            if hit['status'] != 'supported' or not -.5 <= foot[2]-hit['height'] <= 1.0: return False
        return True

    def neighbourhood(self, name, point, samples):
        # Conservative visible-model bounds accelerate candidate searches only.
        # World collision is always retained. The final independent audit traces
        # the complete unfiltered scene and can reject any proposed placement.
        import itertools
        import struct
        from check_actor_ground import entities
        raw = (self.maps/(name+'.bsp')).read_bytes(); all_scene = self.scene(name)
        models = list(struct.iter_unpack('<9f7i', lumps(raw)[14]))
        objects = [dict(model='*0')]+[e for e in entities(raw)
                   if e.get('classname') == 'func_wall' and re.fullmatch(r'\*\d+', e.get('model', ''))]
        reach = 34+max(max(abs(v[0]), abs(v[1])) for v in samples)
        selected = []
        for brush, e in zip(all_scene.brushes, objects):
            root, origin, basis, ref = brush; m = models[int(e['model'][1:])]
            corners = [tuple(origin[i]+sum(v[j]*basis[j][i] for j in range(3)) for i in range(3))
                       for v in itertools.product(*[(m[k], m[k+3]) for k in range(3)])]
            if e['model'] == '*0' or all(max(v[k] for v in corners) >= point[k]-reach and
                                         min(v[k] for v in corners) <= point[k]+reach for k in (0, 1)):
                # Leave a small numerical margin at transformed model edges.
                box = None if e['model'] == '*0' else tuple(
                    [min(v[k] for v in corners)-.01 for k in (0, 1)]+
                    [max(v[k] for v in corners)+.01 for k in (0, 1)])
                selected.append((brush, box))
        return _SupportScene(all_scene, selected)

    @staticmethod
    def path_clear(s, old, new, base):
        import math
        distance = math.hypot(new[0]-old[0], new[1]-old[1])
        previous = [old[0], old[1], base+16]
        height = base
        for step in range(1, max(1, math.ceil(distance/2))+1):
            f = step/max(1, math.ceil(distance/2))
            xy = [old[k]+(new[k]-old[k])*f for k in range(2)]
            hit = s.floor([*xy, height+8], 16)
            if hit['status'] != 'supported' or abs(hit['height']-height) > 4.5: return False
            point = [*xy, hit['height']+16]
            if s.trace(previous, point): return False
            previous = point; height = hit['height']
        return True

    def _setup(self, name, e, authored, angles):
        key = (name, e['model'], e.get('aw_intro_role', 0), tuple(authored), angles)
        if key in self.setups:
            return self.setups[key]
        samples = self.soles(e['model'], angles, bool(float(e.get('aw_intro_role', 0))))
        s = self.neighbourhood(name, authored, samples)
        center = s.floor([*authored[:2], authored[2]+8], 40)
        if len(self.setups) >= 32:  # slices of many placements interleave in one worker
            self.setups.pop(next(iter(self.setups)))
        self.setups[key] = (samples, s, center)
        return samples, s, center

    def head(self, name, e, authored, angles):
        """(result, original) when the offset search is still needed, else (result, None)."""
        samples, s, center = self._setup(name, e, authored, angles)
        result = dict(map=name, reference=e.get('aw_ref'), source_id=e.get('aw_source_id'),
                      name=e.get('netname'), authored_origin=authored, authored_z=authored[2],
                      status=center['status'], support_reference=center.get('reference'))
        if center['status'] != 'supported': return result, None
        original = [*authored[:2], center['height']+.25]
        original = [round(v, 5) for v in original]
        # Retain already valid original placements exactly.
        if self.contact(s, original, samples):
            result.update(placed_origin=original, placed_z=original[2], mesh_contact='unchanged', attempts=0)
            return result, None
        return result, original

    def search(self, name, e, authored, angles, original, first, last):
        """The first passing offset in OFFSETS[first:last]: (attempt, fields) or None."""
        import math
        from check_actor_ground import owner
        samples, s, center = self._setup(name, e, authored, angles)
        for attempt, (dx, dy) in enumerate(OFFSETS[first:last], first+1):
            candidate = [authored[0]+dx, authored[1]+dy, 0]
            try: target = owner(self.maps, name, candidate)
            except ValueError: continue
            if target != name: continue
            support = s.floor([*candidate[:2], authored[2]+8], 40)
            if support['status'] != 'supported' or abs(support['height']-center['height']) > 16: continue
            low = authored[2]-32; high = authored[2]+8
            for local in samples:
                hit = s.floor([candidate[0]+local[0], candidate[1]+local[1], support['height']+local[2]+8], 24)
                if hit['status'] != 'supported': low = math.inf; break
                low = max(low, hit['height']-local[2]-.5)
                high = min(high, hit['height']-local[2]+1.0)
                if low > high: break
            if low > high: continue
            candidate[2] = contact_interval_choice(low, high, original[2])
            candidate = [round(v, 5) for v in candidate]
            if not self.contact(s, candidate, samples) or not self.path_clear(s, original, candidate, center['height']): continue
            return attempt, dict(placed_origin=candidate, placed_z=candidate[2], mesh_contact='fitted', attempts=attempt,
                                 correction_from_origin_grounding=[round(candidate[k]-original[k], 5) for k in range(3)])
        return None

    def fit(self, name, e, authored, angles):
        result, original = self.head(name, e, authored, angles)
        if original is None: return result
        found = self.search(name, e, authored, angles, original, 0, len(OFFSETS))
        return finish(result, found)


def finish(result, found):
    """Apply the first passing offset, or record the exhausted search."""
    if found is not None:
        result.update(found[1])
    else:
        result.update(status='unresolved-mesh-contact', attempts=len(OFFSETS))
    return result


class _SupportScene(Scene):
    def __init__(self, original, bounds):
        # Read-only collision data shared with the full scene. Bounds are
        # used only to propose placements; the final audit is unfiltered.
        self.__dict__.update(original.__dict__)
        self.bounds = bounds

    def _trace_brushes(self, start, end):
        for brush, box in self.bounds:
            if box is None or all(max(start[k], end[k]) >= box[k] and
                                  min(start[k], end[k]) <= box[k+2] for k in (0, 1)):
                yield brush


ENTITY_BLOCK = re.compile(r'\{[^{}]*\}')
ENTITY_FIELD = re.compile(r'"([^"\n]+)"\s+"([^"\n]*)"')


def _ground_key(maps, stem, e):
    """(owner, placement key, authored origin, angles) of one ground-mode actor."""
    import math
    from check_actor_ground import owner
    authored = list(map(float, e.get('aw_authored_origin', e['origin']).split()))
    authored[2] = float(e.get('aw_authored_z', authored[2]))
    angles = tuple(map(float, e.get('angles', '0 0 0').split()))
    if len(authored) != 3 or not all(map(math.isfinite, authored)): raise ValueError('Invalid authored position')
    selected = owner(maps, stem, authored)
    return selected, (selected, e.get('aw_ref'), tuple(authored), angles, e['model']), authored, angles


def _ground_entities(path):
    """Worker: the ground-mode actor entities of one map, in file order."""
    found = []
    for block in ENTITY_BLOCK.findall(lumps(Path(path).read_bytes())[0].decode('cp1252')):
        e = dict(ENTITY_FIELD.findall(block))
        if e.get('classname') != 'aw_npc' or float(e.get('aw_ground_mode', 0)): continue
        list(map(float, e['origin'].split()))  # the serial pass parsed the origin first
        found.append(e)
    return found


_FITTER = [None, None]  # (call token, fitter) of the current bake in this process


def _fitter(token, maps):
    """A worker keeps one fitter (its collision scene cache) per bake call;
    the call token never reuses a stale one."""
    if _FITTER[0] != token:
        _FITTER[:] = [token, _Fitter(maps)]
    return _FITTER[1]


def _fit_head(task):
    """Worker: support and the unchanged-placement check of one placement."""
    token, maps, name, e, authored, angles = task
    return _fitter(token, maps).head(name, e, authored, angles)


def _fit_search(task):
    """Worker: one slice of one placement's offset search."""
    token, maps, name, e, authored, angles, original, first, last = task
    return _fitter(token, maps).search(name, e, authored, angles, original, first, last)


# Offsets per search task (OFFSETS holds 12,861). Small: one offset can cost
# 0.1 s in a dense interior (measured: a 512-offset slice took 54 s), and slices
# after the first hit are the only wasted work.
SEARCH_SLICE = 32


def _fit_all(tasks, jobs):
    """Heads, then the sliced offset searches, in ONE worker pool.

    A placement whose authored spot fails searches OFFSETS in slices. Slices of
    all such placements are fed round-robin into the pool, so one long search
    (an unresolvable actor tries all 12,861 offsets) keeps every worker busy,
    and the pool starts once (each worker builds its scenes once). The first
    passing offset in OFFSETS order wins, as in the serial search: slices are
    submitted in order, slices after a placement's first hit are cancelled or
    ignored, and every slice before it completes. Returns the head results and
    {task index: (attempt, fields)}.
    """
    from concurrent.futures import FIRST_COMPLETED, wait
    from build_parallel import live_jobs, process_pool, worker_environment
    slices = -(-len(OFFSETS) // SEARCH_SLICE)
    # The stage's current share, not its start value: actor-contact started with
    # one worker and so fitted every placement serially (BUILD-IDLE-STAGES-33).
    jobs = live_jobs(jobs)

    def search_task(index, number, head):
        first = number * SEARCH_SLICE
        return (*tasks[index], head[1], first, min(first + SEARCH_SLICE, len(OFFSETS)))
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


def _bake_map(task):
    """Worker: write the fitted placements into one map that has ground actors."""
    path, results = task
    path = Path(path); maps = path.parent
    data = lumps(path.read_bytes()); changed = [False]

    def update(match):
        block = match[0]; e = dict(ENTITY_FIELD.findall(block))
        if e.get('classname') != 'aw_npc' or float(e.get('aw_ground_mode', 0)): return block
        _, key, authored, _ = _ground_key(maps, path.stem, e)
        result = results[key]
        # Never leave stale certification on an unresolved placement.
        for field in ('aw_ground_valid', 'aw_ground_baked', 'aw_authored_origin', 'aw_authored_z'):
            block = re.sub(r'\n"'+field+r'"\s+"[^"\n]*"', '', block)
        placed = result.get('placed_origin')
        if placed is not None:
            block = re.sub(r'"origin"\s+"[^"\n]*"', '"origin" "'+' '.join(f'{v:.5f}' for v in placed)+'"', block)
            block = block[:-1]+'"aw_ground_valid" "1"\n"aw_ground_baked" "'+' '.join(f'{v:.5f}' for v in placed)+'"\n}'
        addition = '"aw_authored_origin" "'+' '.join(f'{v:.5f}' for v in authored)+'"\n'+f'"aw_authored_z" "{authored[2]:.5f}"\n'
        changed[0] = True
        return block[:-1]+addition+'}'
    text = ENTITY_BLOCK.sub(update, data[0].decode('cp1252'))
    if changed[0]: data[0] = text.encode('cp1252'); path.write_bytes(pack_lumps(data))
    return path.name


def bake_ground(maps, jobs=1, exclude=()):
    """Fit rendered idle soles to converted support, preserving authored inputs.

    Try vertical correction first, then the nearest half-unit XY point within
    32 units. Never cross an owner core, wall, unsupported gap, or a storey-sized
    support change. The independent packaged audit remains the release gate.

    Up to `jobs` workers (shared pool) read maps, fit placements (grouped by
    owning map) and write maps. The first copy of a placement in sorted map
    order is the one fitted and reported, as in the serial pass; fitting reads
    only world and func_wall collision, which baking never changes. Map file
    names in `exclude` (recorded-stage maps) are neither fitted nor written;
    their recorded placements stay as they are and the packaged audit checks them.
    """
    from build_parallel import ordered_map
    maps = Path(maps)
    paths = [p for p in sorted(maps.glob('*.bsp')) if p.name not in exclude]

    def workers(count):
        return max(1, min(jobs, count))
    found = list(ordered_map(_ground_entities, [str(p) for p in paths], workers(len(paths))))
    order, keyed, pending = [], {}, {}
    for path, actors in zip(paths, found):
        for e in actors:
            selected, key, authored, angles = _ground_key(maps, path.stem, e)
            if key in keyed: continue
            keyed[key] = (selected, len(pending.setdefault(selected, [])))
            pending[selected].append((selected, e, authored, angles))
            order.append((key, selected, e))
    # One task per placement, grouped by owning map so a worker mostly reuses
    # its cached collision scene; placements are independent.
    import uuid
    token = uuid.uuid4().hex
    owners = sorted(pending)
    tasks = [(token, str(maps), *item) for o in owners for item in pending[o]]
    heads, best = _fit_all(tasks, jobs)
    flat = iter([result if original is None else finish(result, best.get(index))
                 for index, (result, original) in enumerate(heads)])
    fitted = {o: [next(flat) for _ in pending[o]] for o in owners}
    results, report = {}, []
    for key, selected, e in order:
        owner_name, index = keyed[key]
        results[key] = fitted[owner_name][index]; report.append(results[key])
        print('Actor support:', selected, e.get('aw_ref', 'intro'),
              results[key].get('mesh_contact', results[key]['status']), flush=True)
    tasks = [(str(path), {key: results[key] for key in {_ground_key(maps, path.stem, e)[1] for e in actors}})
             for path, actors in zip(paths, found) if actors]
    list(ordered_map(_bake_map, tasks, workers(len(tasks))))
    return report
