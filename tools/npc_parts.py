# SPDX-License-Identifier: GPL-3.0-only
"""Modular NPC parts library: each body part converted once, appearances composed.

docs/MODULAR_NPCS.md. A part is (skeleton, mesh, shape filter, attach bone, slot)
at one race scale; a part bake is that part at one per-shape triangle quota and
shell flag set. A recipe (one gallery appearance) is resolved like the whole
bake: the outfit's quotas (bake_quotas) at 480, then the lower budgets and the
extended 1,024-face profile when the composed model overflows the alias limit.
The composed model concatenates the part bakes in the outfit's shape order.

Policies: 'exact' bakes every part at exactly the quota and shell flag the whole
bake gives it in each outfit (the composed model equals the whole bake up to
floating-point effects of the gallery's translation); 'levelsN' keeps at most N
quota levels per part (nearest level per outfit, capped per actor; an outfit
over the cap falls back to its exact recipe).

Host-only. The persistent store is keyed by the full input identity of each
part (mesh, textures and skeleton bytes, quota, shell flags, scale, palette,
converter sources and package versions), never by a file name alone.
"""
import hashlib
import io
import json
import time
from pathlib import Path

import numpy as np

from mwad.audit import BSA, normpath
from mwad.paths import child_ci

FORMAT = 'AmiWind NPC parts library 1'
STAGE_BUDGETS = ((666, 480), (666, 384), (666, 320), (666, 256), (666, 192), (1024, 480))
# A part is baked under the largest alias face limit; the planner applies the
# limit of the cascade step to the composed model (a chest panel that keeps
# more faces than its quota for shell preservation must not fail on its own).
PART_FACE_LIMIT = 1024
PARTS_SOURCES = ('tools/npc_parts.py',)


def part_key(skeleton, part):
    """The same NIF is several parts (shirt chest and arms) and Left bones mirror."""
    return '|'.join((normpath(skeleton), normpath(part['mesh']), part['filter'].casefold(),
                     part['attach'].casefold(), str(part['slot'])))


def token(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def parse_policy(policy):
    if policy == 'exact':
        return None
    if policy.startswith('levels') and policy[6:].isdigit() and 1 <= int(policy[6:]) <= 16:
        return int(policy[6:])
    raise ValueError('Unknown NPC parts policy: ' + policy)


# ---------------------------------------------------------------- store

class Store:
    """Content-addressed entries: payload.npz + entry.json (the commit marker)."""

    def __init__(self, root):
        self.root = Path(root)

    def directory(self, ident):
        t = token(ident)
        return self.root / t[:2] / t

    def load(self, ident):
        directory = self.directory(ident)
        try:
            record = json.loads((directory / 'entry.json').read_text())
            if record['identity'] != ident:
                return None
            if 'npz_sha256' not in record:
                return record['result'], None
            raw = (directory / 'payload.npz').read_bytes()
            if hashlib.sha256(raw).hexdigest() != record['npz_sha256']:
                return None
            arrays = np.load(io.BytesIO(raw), allow_pickle=False)
            return record['result'], {k: arrays[k] for k in arrays.files}
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def result(self, ident):
        """The receipt only (no payload read); None when absent or for another identity."""
        try:
            record = json.loads((self.directory(ident) / 'entry.json').read_text())
            return record['result'] if record['identity'] == ident else None
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def exists(self, ident):
        return self.load(ident) is not None

    def publish(self, ident, result, arrays=None):
        from gallery_cache import atomic_write
        directory = self.directory(ident)
        record = {'identity': ident, 'result': result}
        if arrays is not None:
            buffer = io.BytesIO(); np.savez(buffer, **arrays); raw = buffer.getvalue()
            record['npz_sha256'] = hashlib.sha256(raw).hexdigest()
            atomic_write(directory / 'payload.npz', raw)
        atomic_write(directory / 'entry.json', (json.dumps(record, sort_keys=True) + '\n').encode())


# ---------------------------------------------------------------- workers

_assets = None
_data = None
_skeletons = {}
_parts = {}


def _assets_for(data):
    """The worker's asset index (loose files and BSA); no skeleton is parsed."""
    global _assets, _data
    from npc_geometry import Assets
    if _data != data:
        _assets = Assets(Path(data), BSA(child_ci(Path(data), 'Morrowind.bsa')))
        _data = data; _skeletons.clear(); _parts.clear()
    return _assets


def _context(data, skeleton_source):
    from npc_geometry import Skeleton
    _assets_for(data)
    if skeleton_source not in _skeletons:
        _skeletons[skeleton_source] = Skeleton(_assets, skeleton_source)
    return _assets, _skeletons[skeleton_source]


def _assemble(data, skeleton_source, part, scale):
    from npc_geometry import assemble
    assets, skeleton = _context(data, skeleton_source)
    times, _ = skeleton.idle_times(1)
    appearance = {'parts': [part], 'weight': scale[0], 'height': scale[1]}
    return assemble(assets, appearance, skeleton, times)


def census_task(task):
    """All parts of one mesh at their race scales (the NIF is parsed once per worker).

    Each entry keeps the posed frame-0 shapes, so the bake pass never poses again.
    """
    data, store, idents = task
    started = time.monotonic(); s = Store(store); out = []
    for ident in idents:
        found = s.load(ident)
        if found is not None:
            out.append((ident['part_key'], found[0], 'hit')); continue
        arrays = None
        try:
            shapes, materials, _ = _assemble(data, ident['skeleton'], ident['part'], ident['scale'])
            rows = [{'name': x['name'], 'part': int(x['part']), 'faces': int(len(x['faces'])), 'material': int(x['material']),
                     'zmin': float(x['positions'][0, :, 2].min()), 'zmax': float(x['positions'][0, :, 2].max())}
                    for x in shapes]
            points = np.concatenate([x['positions'][0] for x in shapes])
            result = {'status': 'ready', 'shapes': rows, 'materials': materials,
                      'low': points.min(0).tolist(), 'high': points.max(0).tolist()}
            arrays = {f's{i}_{field}': x[field] for i, x in enumerate(shapes)
                      for field in ('positions', 'faces', 'uv', 'colours')}
        except Exception as exc:  # recorded per part; every recipe using it fails visibly
            result = {'status': 'failed', 'error': type(exc).__name__ + ': ' + str(exc)}
        s.publish(ident, result, arrays)
        out.append((ident['part_key'], result, 'converted'))
    return out, time.monotonic() - started


def posed_shapes(store, census_ident):
    """The census entry's posed shapes, materials and textures (textures via the worker's assets)."""
    found = Store(store).load(census_ident)
    if found is None or found[1] is None:
        raise ValueError('Missing posed part ' + census_ident['part_key'])
    result, arrays = found
    shapes = [{'name': r['name'], 'part': r['part'], 'material': r['material'],
               **{field: arrays[f's{i}_{field}'] for field in ('positions', 'faces', 'uv', 'colours')}}
              for i, r in enumerate(result['shapes'])]
    textures = {}
    for material in result['materials']:
        name = material['texture_index']
        if name and name not in textures:
            textures[name] = _assets.texture(name)
    return shapes, result['materials'], textures


def bake_task(task):
    """One part at one scale; every requested (quota, shell) variant baked once."""
    data, store, palette, census_ident, variants = task
    from npc_geometry import bake
    started = time.monotonic(); results = []; shapes = None; s = Store(store)
    for ident in variants:
        found = s.load(ident)
        if found is not None:
            results.append((token(ident), found[0], 'hit')); continue
        try:
            t0 = time.monotonic()
            if shapes is None:
                _assets_for(data)
                shapes, materials, textures = posed_shapes(store, census_ident)
            t1 = time.monotonic()
            frames, faces, uv, skin = bake(shapes, materials, textures, palette, face_limit=ident['face_limit'],
                                           quotas=ident['quotas'], preserve=ident['preserve'])
            arrays = {'frames': frames, 'faces': faces.astype(np.int32), 'uv': uv.astype(np.int32),
                      'skin': np.array(skin, dtype=np.uint8)}
            result = {'status': 'ready', 'faces': int(len(faces)), 'vertices': int(frames.shape[1]),
                      'load_seconds': round(t1 - t0, 4), 'bake_seconds': round(time.monotonic() - t1, 4)}
            s.publish(ident, result, arrays)
        except Exception as exc:
            result = {'status': 'failed', 'error': type(exc).__name__ + ': ' + str(exc)}
            s.publish(ident, result)
        results.append((token(ident), result, 'converted'))
    return census_ident['part_key'], results, time.monotonic() - started


def dispatch(item):
    """One pool for part bakes and the whole-path creature models (longest first)."""
    kind, task = item
    if kind == 'bake':
        return kind, bake_task(task)
    from gallery_cache import convert_cached
    return kind, convert_cached(task)


def compose_arrays(parts, fill):
    """Concatenate part bakes as the whole bake lays them out: shape order, tile order."""
    frames = []; faces = []; tiles = []; base = 0
    for arrays in parts:
        frames.append(arrays['frames']); faces.append(arrays['faces'] + base); base += arrays['frames'].shape[1]
        skin = arrays['skin']
        for i in range(len(arrays['faces'])):
            tiles.append(skin[i // 32 * 16:i // 32 * 16 + 16, i % 32 * 16:i % 32 * 16 + 16])
    count = len(tiles); rows = ((count + 31) // 32) * 16
    atlas = np.full((rows, 512), fill, np.uint8); uv = []
    for i, tile in enumerate(tiles):
        tx, ty = i % 32 * 16, i // 32 * 16
        atlas[ty:ty + 16, tx:tx + 16] = tile; uv.extend([(tx, ty), (tx + 15, ty), (tx, ty + 15)])
    return np.concatenate(frames, axis=1), np.concatenate(faces), np.array(uv), atlas


def black_index(palette):
    """The palette index the whole bake's quantiser gives unused (black) atlas texels."""
    from PIL import Image
    pal = Image.new('P', (1, 1)); pal.putpalette(palette)
    return Image.new('RGB', (1, 1)).quantize(palette=pal, dither=Image.Dither.NONE).getpixel((0, 0))


def compose_task(task):
    """Write gallery models from resolved recipes (same files and receipt fields as whole)."""
    from PIL import Image
    from npc_geometry import animated_mdl
    from prepare_gallery import EXTENDED_PROFILE, GALLERY_FACE_LIMIT
    store, output, palette, recipes = task
    s = Store(store); fill = black_index(palette); out = []; pal_sha = hashlib.sha256(palette).hexdigest()
    for recipe in recipes:
        key = recipe['key']; started = time.monotonic()
        try:
            parts = []
            for ident in recipe['bakes']:
                t = token(ident)
                if t not in _parts:
                    found = s.load(ident)
                    if found is None or found[1] is None:
                        raise ValueError('Missing part bake for ' + ident['part_key'])
                    if len(_parts) > 4096:
                        _parts.clear()
                    _parts[t] = found[1]
                parts.append(_parts[t])
            frames, faces, uv, atlas = compose_arrays(parts, fill)
            frames = frames - np.array(recipe['shift'])
            skin = Image.fromarray(atlas, 'P'); skin.putpalette(palette)
            skin = skin.resize((skin.width // 2, skin.height // 2), Image.Resampling.NEAREST); uv = uv // 2
            raw = animated_mdl(frames, faces, uv, skin, vertex_limit=GALLERY_FACE_LIMIT * 3)
            (Path(output) / (key + '.mdl')).write_bytes(raw)
            low, high = np.array(recipe['low']), np.array(recipe['high'])
            result = dict(key=key, status='ready', source_bounds=[low.tolist(), high.tolist()],
                          dimensions=(high - low).tolist(), triangles=len(faces), vertices=frames.shape[1],
                          bytes=len(raw), face_limit=recipe['face_limit'],
                          geometry_profile=EXTENDED_PROFILE if recipe['face_limit'] == GALLERY_FACE_LIMIT else 'normal-v1',
                          quality_profile='', quality_settings=None, gallery_lift=0,
                          palette_sha256=pal_sha, sha256=hashlib.sha256(raw).hexdigest(),
                          atlas_profile='face8-v1', source_repairs=[], method='parts',
                          parts_policy=recipe['policy'], budget=recipe['budget'], parts=len(parts))
        except Exception as exc:
            result = dict(key=key, status='failed', error=type(exc).__name__ + ': ' + str(exc), method='parts')
        (Path(output) / (key + '.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
        out.append((result, time.monotonic() - started))
    return out


# ---------------------------------------------------------------- planner

def quota_shapes(rows, frames=1):
    """Stand-ins with the fields bake_quotas reads (face count, slot, frame count)."""
    return [{'name': r['name'], 'part': r['part'], 'faces': np.zeros((r['faces'], 3), np.int8),
             'positions': np.zeros((frames, 1, 3))} for r in rows]


class Planner:
    """Resolve every NPC gallery spec to part bakes, mirroring the whole bake."""

    def __init__(self, specs, census, palette, dependencies, sources, env, policy='exact'):
        self.specs = specs; self.census = census; self.palette_sha = hashlib.sha256(palette).hexdigest()
        self.dependencies = dependencies; self.sources = sources; self.env = env
        self.levels = parse_policy(policy); self.policy = policy
        self.level_table = {}
        self.exact_only = set()  # outfits over the per-actor cap with levels

    def scale(self, spec):
        a = spec['appearance']; return [a['weight'], a['height']]

    def census_ident(self, spec, part):
        a = spec['appearance']; key = part_key(a['skeleton'], part)
        deps = self.dependencies.for_spec({'kind': 'NPC_', 'appearance': {'skeleton': a['skeleton'], 'parts': [part]}})
        return {'format': FORMAT, 'kind': 'census', 'part_key': key, 'skeleton': a['skeleton'],
                'part': {k: part[k] for k in ('mesh', 'filter', 'attach', 'slot')},
                'scale': self.scale(spec), 'frames': 'idle start (1)', 'dependencies': deps,
                'sources': self.sources, 'environment': self.env}

    def outfit(self, spec):
        """Per part: census row, bounds; the appearance's bounds and shift; errors."""
        a = spec['appearance']; rows = []
        for part in a['parts']:
            ident = self.census_ident(spec, part)
            row = self.census[token(ident)]
            if row['status'] != 'ready':
                raise ValueError(row['error'])
            rows.append((part, ident, row))
        low = np.min([r['low'] for _, _, r in rows], axis=0); high = np.max([r['high'] for _, _, r in rows], axis=0)
        shift = [(low[0] + high[0]) / 2, (low[1] + high[1]) / 2, low[2]]
        return rows, low, high, shift

    def shell_flags(self, rows, shift):
        """The whole bake's shell test on its translated frame 0, per shape."""
        z = shift[2]; shapes = [s for _, _, r in rows for s in r['shapes']]
        top = max(s['zmax'] - z for s in shapes); bottom = min(s['zmin'] - z for s in shapes)
        height = top - bottom
        return [s['part'] == 3 and (s['zmax'] - z) - (s['zmin'] - z) >= .2 * height for s in shapes]

    def bake_ident(self, census_ident, quotas, preserve, rows):
        # Shell flags only matter on chest shapes simplified below their face count.
        preserve = [bool(p and s['part'] == 3 and s['faces'] > q) for p, s, q in zip(preserve, rows, quotas)]
        return {**{k: census_ident[k] for k in ('format', 'part_key', 'skeleton', 'part', 'scale', 'frames',
                                               'dependencies', 'sources', 'environment')},
                'kind': 'bake', 'quotas': [int(q) for q in quotas], 'preserve': preserve, 'face_limit': PART_FACE_LIMIT,
                'palette_sha256': self.palette_sha}

    def recipe(self, key, step):
        """The part bakes of one spec at one cascade step, plus its geometry facts."""
        from npc_geometry import bake_quotas
        spec = self.specs[key]; rows, low, high, shift = self.outfit(spec)
        face_limit, budget = STAGE_BUDGETS[step]
        shapes = [s for _, _, r in rows for s in r['shapes']]
        quotas = bake_quotas(quota_shapes(shapes), budget, face_limit)
        flags = self.shell_flags(rows, shift)
        use_levels = bool(self.levels) and step == 0 and key not in self.exact_only
        bakes = []; at = 0
        for part, ident, row in rows:
            n = len(row['shapes']); q = list(quotas[at:at + n]); f = flags[at:at + n]
            if use_levels:
                q = self.level_quota(ident['part_key'], row['shapes'], q)
            bakes.append(self.bake_ident(ident, q, f, row['shapes'])); at += n
        return {'key': key, 'bakes': bakes, 'census': [ident for _, ident, _ in rows], 'shift': shift,
                'low': low.tolist(), 'high': high.tolist(), 'face_limit': face_limit, 'budget': budget,
                'step': step, 'policy': self.policy if use_levels else 'exact'}

    # Levels: per part, at most N total-quota levels (quantiles of today's quotas).
    def prepare_levels(self, keys):
        from npc_geometry import bake_quotas
        wanted = {}
        for key in keys:
            try:
                rows, _, _, _ = self.outfit(self.specs[key])
            except ValueError:
                continue
            shapes = [s for _, _, r in rows for s in r['shapes']]
            try:
                quotas = bake_quotas(quota_shapes(shapes), 480, 666)
            except ValueError:
                continue
            at = 0
            for _, ident, row in rows:
                n = len(row['shapes'])
                total = sum(min(int(q), s['faces']) for q, s in zip(quotas[at:at + n], row['shapes']))
                wanted.setdefault(ident['part_key'], []).append(total); at += n
        for part, values in wanted.items():
            qs = sorted(values); count = self.levels
            self.level_table[part] = sorted({qs[min(len(qs) - 1, int(i * (len(qs) - 1) / max(1, count - 1) + .5))]
                                             for i in range(count)})

    def level_quota(self, part, rows, quotas):
        levels = self.level_table.get(part)
        if not levels:
            return quotas
        want = sum(min(int(q), r['faces']) for q, r in zip(quotas, rows))
        level = min(levels, key=lambda l: (abs(l - want), l))
        source = sum(r['faces'] for r in rows)
        if level >= source:
            return [max(1, r['faces']) for r in rows]
        return [max(1, round(level * r['faces'] / source)) for r in rows]


def run(specs, data, palette, store, dependencies, sources, env, jobs, policy='exact', face_cap=666, log=print,
        extra=()):
    """Census, bake and resolve every NPC spec. Returns (recipes, failures, report, extra results).

    extra: gallery_cache.convert_cached tasks (creatures) run in the first bake pass.
    """
    from build_parallel import completed_map
    started = time.monotonic(); report = {'format': FORMAT, 'policy': policy, 'face_cap': face_cap}
    Path(store).mkdir(parents=True, exist_ok=True)
    planner = Planner(specs, {}, palette, dependencies, sources, env, policy)
    census_idents = {}
    for spec in specs.values():
        for part in spec['appearance']['parts']:
            ident = planner.census_ident(spec, part); census_idents[token(ident)] = ident
    log(f'NPC parts: {len(specs)} appearances; {len(census_idents)} distinct parts at their race scales.')
    counts = {'hit': 0, 'converted': 0}; cpu = 0.
    by_mesh = {}
    for ident in census_idents.values():
        by_mesh.setdefault((ident['skeleton'], normpath(ident['part']['mesh'])), []).append(ident)
    tasks = [(str(data), str(store), group) for group in by_mesh.values()]
    tasks.sort(key=lambda t: -len(t[2]))
    for results, seconds in completed_map(census_task, tasks, jobs):
        cpu += seconds
        for _, _, action in results:
            counts[action] += 1
    for t, ident in census_idents.items():
        planner.census[t] = Store(store).result(ident)
    report['census'] = dict(parts=len(census_idents), seconds=round(time.monotonic() - started, 3),
                            worker_seconds=round(cpu, 3), **counts)
    log(f"NPC parts census: {counts['hit']} cached, {counts['converted']} posed, "
        f"{time.monotonic()-started:.1f}s.")
    if planner.levels:
        planner.prepare_levels(list(specs))
    pending = {key: 0 for key in specs}; recipes = {}; failures = {}; bake_stats = []
    baked = {}; extra = list(extra); extra_results = []
    while pending:
        plans = {}
        for key, step in pending.items():
            try:
                plans[key] = planner.recipe(key, step)
            except ValueError as exc:
                failures[key] = 'ValueError: ' + str(exc)
        groups = {}
        for plan in plans.values():
            for census_ident, ident in zip(plan['census'], plan['bakes']):
                t = token(ident)
                if t in baked:
                    continue
                groups.setdefault(token(census_ident), (census_ident, {}))[1][t] = ident
        tasks = [(str(data), str(store), palette, c, list(v.values())) for c, v in groups.values()]
        # Longest first: estimated bake work is the output faces requested.
        tasks.sort(key=lambda t: -sum(sum(i['quotas']) for i in t[4]))
        items = [('creature', t) for t in extra] + [('bake', t) for t in tasks]; extra = []
        phase = time.monotonic(); counts = {'hit': 0, 'converted': 0}; cpu = 0.
        for kind, value in completed_map(dispatch, items, jobs):
            if kind == 'creature':
                extra_results.append(value); continue
            _, results, seconds = value; cpu += seconds
            for t, result, action in results:
                baked[t] = result; counts[action] += 1
        bake_stats.append(dict(variants=sum(counts.values()), seconds=round(time.monotonic() - phase, 3),
                               worker_seconds=round(cpu, 3), **counts))
        log(f"NPC parts bake pass {len(bake_stats)}: {counts['hit']} cached, {counts['converted']} baked, "
            f"{time.monotonic()-phase:.1f}s.")
        pending = {}
        for key, plan in plans.items():
            results = [baked[token(i)] for i in plan['bakes']]
            bad = next((r for r in results if r['status'] != 'ready'), None)
            if bad is not None:
                failures[key] = bad['error']; continue
            total = sum(r['faces'] for r in results)
            limit = min(plan['face_limit'], face_cap) if plan['policy'] != 'exact' else plan['face_limit']
            if total <= limit:
                recipes[key] = plan
            elif plan['policy'] != 'exact':
                planner.exact_only.add(key); pending[key] = 0
            elif plan['step'] + 1 < len(STAGE_BUDGETS):
                pending[key] = plan['step'] + 1
            else:
                failures[key] = 'ValueError: Alias vertex budget exceeded'
    report['bake_passes'] = bake_stats
    report['recipes'] = len(recipes); report['failures'] = len(failures)
    report['steps'] = {}
    for plan in recipes.values():
        name = f"{plan['face_limit']}/{plan['budget']}" + ('' if plan['policy'] == 'exact' else ' ' + plan['policy'])
        report['steps'][name] = report['steps'].get(name, 0) + 1
    report['distinct_part_bakes'] = len({token(i) for p in recipes.values() for i in p['bakes']})
    report['levels_exact_fallback'] = len(planner.exact_only)
    report['seconds'] = round(time.monotonic() - started, 3)
    return recipes, failures, report, extra_results
