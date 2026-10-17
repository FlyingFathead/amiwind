# SPDX-License-Identifier: GPL-3.0-only
"""Stair-walk records: a stair walk is done once and reused while what it reads is unchanged.

The stair walk (tools/stair_walk.py for legacy maps, chim.collision.stair_gate for CHIM frames) is a check of the
collision, close to a short play test, and it is the slowest check of a build. Its result for one map or frame is
stored as a RECORD in the image passes cache (pass_cache.PassCache 'stair-walk', the shared cache of the build
workspace), under the SHA-256 of exactly what the walk reads plus the walk's own code and settings:

    entry = {'rows': [...], 'record': {format, key, walker, version, commit, run, request, time, counts,
                                       rows_sha256, record_sha256}}

record_sha256 is the SHA-256 of the record's canonical JSON without that field; rows_sha256 binds the rows, stored
once next to the record where the cache kept them before (a build of an earlier commit sharing the cache still
reads them: the walker's key did not change, so neither did its results). A record written by a run is a
CANDIDATE. It becomes reusable when the run that wrote it passed every gate as a build of the master builder
(tools/aw_service.py runs `stair_records.py promote` after a passed build): the promotion writes a check mark next
to the record, naming the record's SHA-256, the run, its request and the time. A later build reuses a record by its
mark only when the mark names exactly that record; anything else (a candidate of a failed, dry or local run, a
damaged record, a record written again since) is walked again. Every build also walks a seeded sample of the reused
ones again and stops on any difference (stair_walk.walk_sample): that would be a key that misses one of the walk's
inputs. BUILD-CHIM-STAIR-WALK-UNCACHED-36.

A CHIM frame's record also carries the walk's OUTCOME ('passed': no flight step the standing box cannot walk;
'failed') and its provenance: walked_at (ISO 8601 with the zone), the AmiWind and CHIM versions, the source commit
and the run. A passed walk is a pass (passed(), BUILD-STAIR-PASS-NOT-KEPT-41): development builds reuse it while its
key is unchanged without a check mark, whatever the rest of the build that walked it did, so a build that fails
late keeps every frame that passed (chim.collision.walk_reuse_rule). Release candidates and finals keep the
check-mark rule. Records without an outcome (the legacy maps' walks, records written before) need their mark.

One-time migration (`adopt`): the walks a passed master build stored in the cache's earlier form (rows only,
before these records) become checked records without walking them again, when nothing they depend on changed:
every frame's and map's input key is computed again with today's code from the run's own outputs, the old entry
is looked up under the old walker's exact key (from the run's own source tree), a seeded sample is walked again
with today's walker and must give the same rows; any difference adopts nothing.

promote and the records need only the standard library; adopt loads the walkers (it walks its sample again).
"""
import argparse
import datetime
import hashlib
import json
import os
import re
from pathlib import Path

FORMAT = 'aw-stair-walk-record-1'
MARK_FORMAT = 'aw-stair-walk-check-1'
MARK_FOLDER = 'stair-walk-checked'
# Run facts the builder puts into the environment for the records (bookkeeping: never part of a stage key).
RUN_ENV = {'run': 'AMIWIND_RUN_NAME', 'commit': 'AMIWIND_RUN_COMMIT', 'version': 'AMIWIND_RUN_VERSION',
           'request': 'AMIWIND_AW_REQUEST'}
REPORT_NAMES = ('chim-stairs.json', 'stair-walk.json')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), default=str)


def sha256_of(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def stamp():
    return datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')


def run_facts(environ=None):
    environ = os.environ if environ is None else environ
    return {name: environ.get(var) or None for name, var in RUN_ENV.items()}


def counts(rows):
    """Results of a walk by kind: passed, failed (gating or not), untestable, and the rows in all."""
    out = {'rows': len(rows)}
    for r in rows:
        out[r.get('result', '?')] = out.get(r.get('result', '?'), 0) + 1
    return out


def make_record(full_key, rows, walker, facts=None, time=None, extra=None):
    """A candidate record of one walk (rows) under the cache's full key."""
    facts = run_facts() if facts is None else facts
    record = {'format': FORMAT, 'key': full_key, 'walker': walker, 'time': time or stamp(), 'counts': counts(rows),
              'rows_sha256': sha256_of(rows), **facts, **(extra or {})}
    record['record_sha256'] = sha256_of(record)
    return record


def intact(record):
    """Is this a record whose SHA-256 matches its content?"""
    if not isinstance(record, dict) or record.get('format') != FORMAT:
        return False
    body = {k: v for k, v in record.items() if k != 'record_sha256'}
    return record.get('record_sha256') == sha256_of(body)


def mark_path(root, full_key):
    return Path(root) / MARK_FOLDER / full_key[:2] / (full_key + '.json')


def read_mark(root, full_key):
    try:
        mark = json.loads(mark_path(root, full_key).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    body = {k: v for k, v in mark.items() if k != 'mark_sha256'}
    if mark.get('format') != MARK_FORMAT or mark.get('mark_sha256') != sha256_of(body):
        return None
    return mark


def lookup(cache, input_sha256):
    """(record, mark) for one walk input: record None when there is no intact record, mark None when the record is
    not master-checked (no mark, or a mark naming another record). Reuse only when both are given."""
    found = cache.load(input_sha256)
    row = (found[0] or {}) if found is not None else {}
    record, rows = row.get('record'), row.get('rows')
    if not intact(record) or not isinstance(rows, list) or sha256_of(rows) != record.get('rows_sha256'):
        return None, None
    record = dict(record, rows=rows)
    full_key = cache.key(input_sha256)
    mark = read_mark(cache.root, full_key)
    if mark is None or mark.get('record_sha256') != record['record_sha256']:
        # the record may have come from the --reuse-from workspace's cache (pass_cache.load pools it here): its
        # check mark is there too, pooled here the same way
        mark = None
        try:
            from file_cache import fallback_root
            other = fallback_root(cache.root)
        except ImportError:
            other = None
        found = read_mark(other, full_key) if other is not None else None
        if found is not None and found.get('record_sha256') == record['record_sha256']:
            mark = found
            _write_mark(cache.root, full_key, mark)
    if mark is None:
        return record, None
    return record, mark


ROOT = Path(__file__).resolve().parents[1]
OUTCOMES = ('passed', 'failed')


def _version_file(name):
    try:
        return (ROOT / name).read_text(encoding='utf-8').strip() or None
    except OSError:
        return None


def walk_facts(outcome, environ=None):
    """The outcome and provenance fields of a walk's record: outcome, walked_at (ISO 8601 with the zone), the CHIM
    version (the builder's AMIWIND_RUN_CHIM_VERSION, else this tree's CHIM_VERSION) and the AmiWind version and
    commit when the builder did not give them (this tree's VERSION, AMIWIND_SOURCE_COMMIT)."""
    if outcome not in OUTCOMES:
        raise ValueError('A walk outcome is one of %s, not %r' % (', '.join(OUTCOMES), outcome))
    environ = os.environ if environ is None else environ
    facts = run_facts(environ)
    if not facts['version']:
        facts['version'] = _version_file('VERSION')
    if not facts['commit']:
        facts['commit'] = environ.get('AMIWIND_SOURCE_COMMIT') or None
    facts.update(outcome=outcome, walked_at=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
                 chim_version=environ.get('AMIWIND_RUN_CHIM_VERSION') or _version_file('CHIM_VERSION'))
    return facts


def passed(record):
    """True for an intact record of a walk that passed (a pass is reused while its key is unchanged); RECORD as
    lookup() gives it (with its rows) or as stored."""
    if not isinstance(record, dict):
        return False
    return intact({k: v for k, v in record.items() if k != 'rows'}) and record.get('outcome') == 'passed'


def pass_provenance(record):
    """'reused pass from RUN (VERSION, COMMIT, TIME)' of a passed walk's record."""
    return 'reused pass from %s (%s, %s, %s)' % (record.get('run') or '?', record.get('version') or '?',
                                                 record.get('commit') or '?', record.get('walked_at') or
                                                 record.get('time') or '?')


def store(cache, input_sha256, rows, outcome=None, derived_from=None):
    """Store this run's walk as a record (a candidate until promoted; with an OUTCOME it carries walk_facts, and a
    passed one is a pass); returns what the run's report lists for the promotion. DERIVED_FROM: the record a walk
    restricted to a frame's walk area was taken from (chim.collision.derive_area_rows: its key, record SHA-256,
    run, checked), kept in the record; nothing was walked for it."""
    full_key = cache.key(input_sha256)
    # the rows keep the walk's own key order (reports read the same with or without reuse); the SHA-256 is taken
    # over the canonical form
    rows = json.loads(json.dumps(rows, default=str))
    record = make_record(full_key, rows, cache.sources, facts=walk_facts(outcome) if outcome else None,
                         extra={'derived_from': derived_from} if derived_from else None)
    cache.store(input_sha256, {'rows': rows, 'record': record})
    return {'root': str(cache.root), 'name': cache.name, 'key': full_key, 'record_sha256': record['record_sha256']}


def provenance(mark):
    """'reused from RUN (VERSION, COMMIT, TIME)' of a check mark."""
    return 'reused from %s (%s, %s, %s)' % (mark.get('run') or '?', mark.get('version') or '?',
                                            mark.get('commit') or '?', mark.get('record_time') or '?')


def entry_path(root, name, full_key):
    return Path(root) / name / full_key[:2] / (full_key + '.json')


def reports(run_dir):
    """The stair reports of a run (CHIM frames: chim-world/chim-stairs.json; legacy maps: the image's
    stair-walk.json), wherever the stages wrote them, at most three folders deep."""
    run_dir = Path(run_dir)
    found = []
    for depth in ('', '*/', '*/*/', '*/*/*/'):
        for name in REPORT_NAMES:
            found += sorted(run_dir.glob(depth + name))
    return found


def promote(run_dir, request=None, environ=None):
    """Mark every record the run stored as master-checked (call it only for a run that passed every gate as a
    build of the master builder). Each record is read back and its SHA-256 checked first; a record that changed
    since (another run wrote the same key) is not marked. Returns counts."""
    run_dir = Path(run_dir)
    facts = run_facts(environ)
    out = {'run': run_dir.name, 'reports': 0, 'marked': 0, 'already': 0, 'changed': 0, 'missing': 0}
    for report_path in reports(run_dir):
        try:
            report = json.loads(report_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        cache = report.get('pass_cache') or {}
        taken = list((cache.get('frames') or cache.get('maps') or {}).values())
        out['reused'] = out.get('reused', 0) + sum(1 for t in taken if str(t).startswith('reused'))
        out['walked'] = out.get('walked', 0) + sum(1 for t in taken if not str(t).startswith('reused'))
        stored = cache.get('stored') or []
        if not stored:
            continue
        out['reports'] += 1
        for item in stored:
            try:
                meta = json.loads(entry_path(item['root'], item['name'], item['key']).read_text(encoding='utf-8'))
                record, rows = meta['row']['record'], meta['row']['rows']
            except (OSError, ValueError, KeyError, TypeError):
                out['missing'] += 1
                continue
            if (not intact(record) or record['record_sha256'] != item['record_sha256']
                    or sha256_of(rows) != record.get('rows_sha256')):
                out['changed'] += 1
                continue
            old = read_mark(item['root'], item['key'])
            if old is not None and old.get('record_sha256') == record['record_sha256']:
                out['already'] += 1
                continue
            if _write_mark(item['root'], item['key'], make_mark(
                    record, run_dir.name, request or record.get('request') or facts.get('request'))):
                out['marked'] += 1
            else:
                out['missing'] += 1
    return out


def make_mark(record, run_name, request):
    """The check mark of one record: the run that passed as a master build and its request."""
    mark = {'format': MARK_FORMAT, 'key': record['key'], 'record_sha256': record['record_sha256'],
            'run': record.get('run') or run_name, 'version': record.get('version'), 'commit': record.get('commit'),
            'record_time': record.get('time'), 'request': request, 'promoted': stamp(),
            'walker': record.get('walker'), 'counts': record.get('counts')}
    mark['mark_sha256'] = sha256_of(mark)
    return mark


def _write_mark(root, full_key, mark):
    """Write a check mark atomically; False when it could not be written (never fails a build)."""
    path = mark_path(root, full_key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.%d.tmp' % os.getpid())
        tmp.write_text(json.dumps(mark, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        os.replace(tmp, path)
        return True
    except OSError:
        return False


# ---- one-time migration of the cache's earlier form (rows only) ---------------------------------------------

def passed_master_build(run_dir, request, aw_result):
    """None when RUN passed as a build of the master builder under REQUEST (its aw result and its own
    build-state.json both say so), else why not."""
    try:
        result = json.loads(Path(aw_result).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return 'aw result unreadable: %s' % exc
    run_dir = Path(run_dir)
    wrong = [name for name, want in (('run_name', run_dir.name), ('request_id', request), ('kind', 'build'),
                                     ('status', 'passed')) if result.get(name) != want]
    if wrong:
        return 'aw result does not show this run passing as request %s (%s)' % (request, ', '.join(
            '%s=%r' % (name, result.get(name)) for name in wrong))
    try:
        state = json.loads((run_dir / 'build-state.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 'the run has no readable build-state.json'
    if state.get('status') != 'passed':
        return 'build-state.json says %r' % state.get('status')
    return None


def _key_form(root):
    """(import-time form, excluded paths) of the pass keys the tree at ROOT writes: form 2 without the cache module
    from BUILD-PASS-KEY-OVERBROAD-36 on (its pass_cache.py names PASS_KEY_FORM), form 1 with it before."""
    try:
        text = (Path(root) / 'tools' / 'pass_cache.py').read_text(encoding='utf-8')
    except OSError:
        text = ''
    match = re.search(r'^PASS_KEY_FORM = (\d+)$', text, re.M)
    if match is None:
        return 1, frozenset()
    return int(match.group(1)), frozenset({'tools/pass_cache.py'})


def walker_sources(root, script):
    """(pass cache sources digest, {path: unit digest}) of a walker script in a source tree: the same digest
    pass_cache.source_digest gives in that tree."""
    from build_cache import SourceIndex
    form, exclude = _key_form(root)
    index = SourceIndex(root, top_format=form)
    path = (Path(root) / script).resolve()
    value, _, uncertain = index.digest(path, exclude)
    selected = {name: digest for name, digest in index.selection(path)[0].items() if name not in exclude}
    parts = [[path.name, value, uncertain]]
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest(), selected


def _walked_time(cache, input_sha256):
    try:
        mtime = cache._paths(input_sha256)[0].stat().st_mtime
    except OSError:
        return None
    return datetime.datetime.fromtimestamp(mtime).astimezone().strftime('%Y-%m-%d %H:%M:%S %z')


def _old_rows(cache, input_sha256):
    found = cache._load(input_sha256)        # read only: no fallback, no pooling
    row = found[0] if found is not None else None
    if not isinstance(row, dict) or not isinstance(row.get('rows'), list):
        return None
    return row['rows']


def _chim_part(run_dir, old_root, cache_root):
    """The CHIM frames of the run: (name, old cache, new cache, [(name, input key, old rows)], walk again)."""
    world_dir = Path(run_dir) / 'chim-world'
    if not (world_dir / 'chim-stairs.json').is_file():
        return None
    from chim import collision
    from chim.validate import Failures, load_world
    from mesh_geometry_env import stair_mode
    from pass_cache import PassCache, source_digest
    fails = Failures()
    world = load_world(world_dir, fails)
    if fails:
        raise ValueError('the run\'s CHIM world does not read back: %s' % fails[0])
    frames, models = world[5], world[4]
    options = {'stair_mode': stair_mode(), 'world': 'chim-frame', 'tile': collision.STAIR_TILE}
    old_sources, old_units = walker_sources(old_root, 'tools/chim/collision.py')
    old = PassCache('stair-walk', options, old_sources, cache_root)
    # today's key form: the frame worker and what it reaches (chim.collision.stair_key_sources, as the gate opens it)
    new = PassCache('stair-walk', options, collision.stair_key_sources(), cache_root)
    found, missing = [], []
    for fi, frame in enumerate(frames):
        key = collision.frame_stair_key(frame, models)
        rows = _old_rows(old, key)
        if rows is None or any(r.get('map') != frame[0] for r in rows):
            missing.append(frame[0])
        else:
            found.append((frame[0], key, rows, fi))

    def walk(items):
        from build_parallel import ordered_map
        wanted = {item[3] for item in items}
        tasks = [t for t in collision.stair_tasks(world_dir, frames) if t[1] in wanted]
        walked = {fi: [] for fi in wanted}
        for task, rows in zip(tasks, ordered_map(collision.stair_task, tasks, 1)):
            walked[task[1]].extend(rows)
        return {frames[fi][0]: rows for fi, rows in walked.items()}
    new_units = walker_sources(Path(collision.__file__).resolve().parents[2], 'tools/chim/collision.py')[1]
    return dict(part='chim frames', old=old, new=new, found=found, missing=missing, walk=walk,
                changed_sources=sorted(k for k in set(old_units) | set(new_units)
                                       if old_units.get(k) != new_units.get(k)))


def _legacy_part(run_dir, old_root, cache_root):
    """The legacy maps of the run's image step (RUN/image/boot/id1), the same shape as _chim_part."""
    image = Path(run_dir) / 'image'
    report_path, id1 = image / 'stair-walk.json', image / 'boot' / 'id1'
    if not report_path.is_file():
        return None
    if not (id1 / 'maps').is_dir():
        return dict(part='legacy maps', found=[], missing=['(the walked maps are no longer in the run)'])
    import stair_walk
    from mesh_geometry_env import stair_mode
    from pass_cache import PassCache, source_digest
    report = json.loads(report_path.read_text(encoding='utf-8'))
    tasks = stair_walk.map_tasks(id1, None)
    scope = 'flights' if report.get('scope') else 'all'
    options = {'stair_mode': stair_mode(), 'models': hashlib.sha256(json.dumps({}, sort_keys=True).encode()).hexdigest()}
    if scope != 'all':
        options['scope'] = scope
    old_sources, old_units = walker_sources(old_root, 'tools/stair_walk.py')
    old = PassCache('stair-walk', options, old_sources, cache_root)
    # today's key form: the walk's workers and what they reach (stair_walk.walk_key_sources)
    new = PassCache('stair-walk', options, source_digest(*stair_walk.walk_key_sources()), cache_root)
    found, missing, seen = [], [], set()
    for path, core, models in tasks:
        key = hashlib.sha256(Path(path).read_bytes()).hexdigest() + ':' + json.dumps(core)
        if key in seen:
            continue                              # an alias of a map already taken (the same bytes and core)
        seen.add(key)
        rows = _old_rows(old, key)
        if rows is None:
            missing.append(Path(path).stem)
        else:
            found.append((Path(path).stem, key, rows, (path, core, models, scope)))

    def walk(items):
        out = {}
        for name, _, _, task in items:
            out[name] = [{k: (name if k == 'map' else v) for k, v in row.items()}
                         for row in json.loads(json.dumps(stair_walk.check_map(task)[1]))]
        return out
    new_units = walker_sources(Path(stair_walk.__file__).resolve().parents[1], 'tools/stair_walk.py')[1]
    return dict(part='legacy maps', old=old, new=new, found=found, missing=missing, walk=walk,
                changed_sources=sorted(k for k in set(old_units) | set(new_units)
                                       if old_units.get(k) != new_units.get(k)))


def adopt(run_dir, request, aw_result, old_source, cache_root, sample=2, dry_run=False):
    """Turn the walks RUN stored in the cache's earlier form (rows only) into checked records, without walking
    them again: only when RUN passed as a master build under REQUEST; only entries whose input key, computed
    again with today's code from RUN's own outputs, finds the entry the old walker (OLD_SOURCE: RUN's source
    tree) stored; and only when a seeded sample walked again with today's walker gives the same rows (any
    difference adopts nothing). Returns counts; writes nothing when refused. dry_run: only what would be found
    (and whether the run passed yet), nothing walked or written."""
    run_dir = Path(run_dir)
    out = {'run': run_dir.name, 'request': request, 'adopted': 0, 'already': 0, 'parts': {}, 'refused': None}
    why = passed_master_build(run_dir, request, aw_result)
    if why and not dry_run:
        out['refused'] = why
        return out
    out['passed_master_build'] = why or 'yes'
    try:
        result = json.loads(Path(aw_result).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        result = {}
    facts = {'run': run_dir.name, 'commit': result.get('commit'), 'version': str(result.get('version', '')).lstrip('v')
             or None, 'request': request}
    parts = [p for p in (_chim_part(run_dir, old_source, cache_root), _legacy_part(run_dir, old_source, cache_root))
             if p is not None]
    # 1. walk a seeded sample again with today's walker: the old rows must be what it gives today
    for part in parts:
        found = part['found']
        names = pick_sample_names([f[0] for f in found], sample, 'adopt:%s:%s' % (run_dir.name, part['part']))
        items = [f for f in found if f[0] in names]
        if dry_run:
            out['parts'][part['part']] = {'found': len(found), 'missing': len(part['missing']),
                                          'missing_names': part['missing'][:20],
                                          'changed_sources': part.get('changed_sources', [])}
            continue
        again = part['walk'](items) if items else {}
        digest = lambda rows: sha256_of(json.loads(json.dumps(rows, default=str)))  # noqa: E731
        named = lambda name, rows: [dict(r, map=name) for r in rows]   # aliases share one stored walk  # noqa: E731
        differ = [f[0] for f in items if digest(named(f[0], again[f[0]])) != digest(named(f[0], f[2]))]
        out['parts'][part['part']] = {'found': len(found), 'missing': len(part['missing']),
                                      'missing_names': part['missing'][:20], 'walked_again': sorted(names),
                                      'changed_sources': part.get('changed_sources', [])}
        if differ:
            out['refused'] = ('%s: walked again with today\'s walker, %s differ from the stored rows: the walker '
                              'changed what it finds; nothing adopted' % (part['part'], ', '.join(differ)))
            return out
    # 2. store the adopted walks as records under today's key, checked by the run's request
    for part in parts if not dry_run else ():
        old, new = part.get('old'), part.get('new')
        for name, key, rows, _ in part['found']:
            record, mark = lookup(new, key)
            if mark is not None:
                out['already'] += 1
                continue
            record = make_record(new.key(key), rows, new.sources, facts, time=_walked_time(old, key),
                                 extra={'adopted_from': {'key': old.key(key), 'walker': old.sources,
                                                         'adopted': stamp()}})
            new.store(key, {'rows': rows, 'record': record})
            stored = lookup(new, key)[0]
            if stored is None or stored['record_sha256'] != record['record_sha256']:
                continue                      # the cache could not be written: those stay unadopted
            if _write_mark(new.root, record['key'], make_mark(record, run_dir.name, request)):
                out['adopted'] += 1
    return out


# ---------------------------------------------------------------- known-good stair records (shipped with the source)
#
# The records above live in a build workspace's cache. The known-good stair records are the same walks as public
# data in the repository (config/stair-records/*.json), so that a build from the same game data does not walk
# again (B14, v0.0.42 plan 1.0b): one entry per CHIM frame, under the frame walk's full key (the SHA-256 of exactly
# what the walk reads, chim.collision.frame_stair_parts plus its walk area, with the walker's code digest and the
# stair rule: PassCache.key). An entry holds the frame's path and cell, the key, the walker digest and the rule, the
# outcome, the counts by result, the SHA-256 of all its rows, and every flight step with its place (placement
# reference, riser point, direction) and behaviour (result, rise, status). Hashes, references and coordinates only:
# no game data. tools/build.py --stair-walk-cache records (the default without --developer-mode) reuses a frame
# whose key is there; a frame whose key is not there (another converter or other game data) is reported by name
# and walked only on request (--stair-walk-cache cached). Written by `stair_records.py export` from a full walk.
SHIPPED_FORMAT = 'aw-stair-records-1'
SHIPPED_FOLDER = ROOT / 'config' / 'stair-records'
SHIPPED_ENV = 'AMIWIND_STAIR_RECORDS'      # another folder of shipped records (tests, a nightly build's own)
NL = chr(10)


def flight_row(row):
    """The compact, canonical form of one flight step's row in the shipped records:
    [reference, kind, x, y, z, direction x, direction y, rise, result, status]."""
    detail = row.get('detail') or {}
    point, direction = row.get('point') or (0, 0, 0), row.get('direction') or (0, 0)
    return [str(row.get('ref')), row.get('kind'), round(float(point[0]), 3), round(float(point[1]), 3),
            round(float(point[2]), 3), round(float(direction[0]), 4), round(float(direction[1]), 4),
            None if row.get('rise') is None else round(float(row['rise']), 3), row.get('result'),
            detail.get('status') or detail.get('error')]


def flight_rows(rows):
    """The flight steps of a walk, in walk order (the rows that can stop a build), as flight_row gives them."""
    return [flight_row(r) for r in rows if r.get('kind') == 'step' and r.get('flight')]


def shipped_entry(path, cell, key, walker, rule, rows, area, outcome):
    """One frame's entry in the shipped records (see above); OUTCOME as the walk's record ('passed': no flight
    step the standing box cannot walk); entry_sha256 binds it."""
    if outcome not in OUTCOMES:
        raise ValueError('A walk outcome is one of %s, not %r' % (', '.join(OUTCOMES), outcome))
    flights = flight_rows(rows)
    entry = {'path': path, 'cell': cell, 'key': key, 'walker': walker, 'rule': rule, 'area': area,
             'outcome': outcome,
             'counts': counts(rows), 'rows_sha256': sha256_of(json.loads(json.dumps(rows, default=str))),
             'flights': flights, 'flights_sha256': sha256_of(flights)}
    entry['entry_sha256'] = sha256_of(entry)
    return entry


def shipped_intact(entry):
    if not isinstance(entry, dict) or not isinstance(entry.get('flights'), list):
        return False
    body = {k: v for k, v in entry.items() if k != 'entry_sha256'}
    return entry.get('entry_sha256') == sha256_of(body) and entry.get('flights_sha256') == sha256_of(entry['flights'])


def write_shipped(path, meta, entries):
    """Write a shipped records file: one JSON object, one frame entry per line (diffs stay readable), UTF-8 + LF."""
    head = dict(meta, format=SHIPPED_FORMAT, frames=len(entries))
    lines = ['{"head": %s,' % canonical(head), ' "entries": [']
    body = sorted(entries, key=lambda e: e['path'])
    for i, entry in enumerate(body):
        lines.append('  ' + canonical(entry) + (',' if i + 1 < len(body) else ''))
    lines.append(']}')
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(NL.join(lines) + NL, encoding='utf-8', newline=NL)
    return {'path': str(path), 'frames': len(body), 'bytes': Path(path).stat().st_size,
            'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def load_shipped(folder=None):
    """({full key: entry}, notes) of every shipped records file (SHIPPED_FOLDER, or AMIWIND_STAIR_RECORDS, or
    FOLDER). An entry whose SHA-256 does not match is left out and named in the notes (it is never reused)."""
    folder = Path(folder or os.environ.get(SHIPPED_ENV) or SHIPPED_FOLDER)
    found, notes = {}, {'files': [], 'damaged': []}
    for path in sorted(folder.glob('*.json')) if folder.is_dir() else ():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            notes['damaged'].append('%s: %s' % (path.name, exc))
            continue
        if not isinstance(data, dict) or (data.get('head') or {}).get('format') != SHIPPED_FORMAT:
            notes['damaged'].append('%s: not a %s file' % (path.name, SHIPPED_FORMAT))
            continue
        notes['files'].append({'file': path.name, 'version': data['head'].get('version'),
                               'commit': data['head'].get('commit'), 'frames': len(data.get('entries') or ())})
        for entry in data.get('entries') or ():
            if shipped_intact(entry):
                found[entry['key']] = dict(entry, file=path.name, version=data['head'].get('version'))
            else:
                notes['damaged'].append('%s: %s' % (path.name, (entry or {}).get('path')))
    return found, notes


def shipped_rows(entry, path):
    """The rows of a frame reused from the shipped records: its flight steps (the rows that gate a build), in walk
    order, in the form the stair report lists them; the other rows (advisory) are counted in entry['counts']."""
    out = []
    for ref, kind, x, y, z, dx, dy, rise, result, status in entry['flights']:
        try:
            ref = int(ref)
        except ValueError:
            pass
        row = {'kind': kind, 'ref': ref, 'point': [x, y, z], 'direction': [dx, dy], 'flight': True,
               'result': result, 'map': path, 'shipped': True}
        if rise is not None:
            row['rise'] = rise
        if status is not None:
            row['detail'] = {'status': status}
        out.append(row)
    return out


def shipped_provenance(entry):
    return 'reused from the shipped records (%s, %s)' % (entry.get('version') or '?', entry.get('file') or '?')


def export(world, cache_root, out, version, commit, run):
    """Write the known-good stair records of the CHIM world WORLD (every frame walked into CACHE_ROOT) to OUT;
    refuses (writes nothing) when a frame has no stored walk. Loads the walkers' key code (chim.collision)."""
    from chim.collision import shipped_entries
    from chim.validate import Failures, load_world
    loaded = load_world(str(world), Failures())
    frames, models = loaded[5], loaded[4]
    entries, missing = shipped_entries(str(world), frames, models, str(cache_root))
    result = {'frames': len(frames), 'entries': len(entries), 'missing': missing[:20], 'missing_count': len(missing)}
    if missing:
        return result
    walkers = sorted({e['walker'] for e in entries})
    meta = {'version': version, 'commit': commit, 'run': run, 'made': stamp(), 'walkers': walkers,
            'rules': sorted({e['rule'] for e in entries}),
            'note': 'known-good stair walks of the CHIM frames (hashes, references and coordinates only; no game '
                    'data): tools/stair_records.py, docs/BUILD_PROFILE.md "Known-good stair records"'}
    result.update(write_shipped(out, meta, entries))
    result['flight_steps'] = sum(len(e['flights']) for e in entries)
    result['outcomes'] = {o: sum(1 for e in entries if e['outcome'] == o) for o in OUTCOMES}
    return result


def pick_sample_names(names, count, seed):
    """A seeded choice of COUNT names (stair_walk.pick_sample's rule, standard library only)."""
    import random
    names = sorted(names)
    return sorted(random.Random(seed).sample(names, min(count, len(names))))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = p.add_subparsers(dest='command', required=True)
    pr = sub.add_parser('promote', help='mark the records of a run that passed every gate as master-checked')
    pr.add_argument('--run', type=Path, required=True, help='the run folder')
    pr.add_argument('--request', help='the master builder request id of the run')
    ad = sub.add_parser('adopt', help='one-time: adopt the stair walks a passed master build stored in the '
                                      'earlier cache form, without walking them again')
    ad.add_argument('--from-run', type=Path, required=True, help='the run folder')
    ad.add_argument('--request', required=True, help='the master builder request id of the run')
    ad.add_argument('--aw-result', type=Path, required=True, help="the master builder's result of that request")
    ad.add_argument('--old-source', type=Path, required=True, help="the run's own source tree (its commit)")
    ad.add_argument('--cache', type=Path, help='the image passes cache (default: AMIWIND_PASS_CACHE, else the '
                                              "run's workspace cache/image-passes)")
    ad.add_argument('--sample', type=int, default=2, help='frames and maps walked again to check (default 2 each)')
    ad.add_argument('--dry-run', action='store_true', help='only report what would be adopted; walk and write nothing')
    ex = sub.add_parser('export', help='write the known-good stair records of a CHIM world whose every frame was '
                                       'walked into a pass cache (a full stair gate in cached mode)')
    ex.add_argument('--world', type=Path, required=True, help='the CHIM world folder (chim-world)')
    ex.add_argument('--cache', type=Path, required=True, help='the pass cache folder the walk stored its records in')
    ex.add_argument('--out', type=Path, required=True, help='the records file (config/stair-records/NAME.json)')
    ex.add_argument('--version', required=True, help='the AmiWind version of the world (e.g. 0.0.41)')
    ex.add_argument('--commit', required=True, help='the source commit the world was built from')
    ex.add_argument('--run', required=True, help='the build run the world comes from')
    a = p.parse_args(argv)
    if a.command == 'export':
        result = export(a.world, a.cache, a.out, a.version, a.commit, a.run)
        print(json.dumps(result, sort_keys=True))
        return 1 if result['missing'] else 0
    if a.command == 'adopt':
        cache = a.cache or (os.environ.get('AMIWIND_PASS_CACHE') or None)
        cache = Path(cache) if cache else a.from_run.resolve().parents[1] / 'cache' / 'image-passes'
        result = adopt(a.from_run, a.request, a.aw_result, a.old_source, cache, a.sample, a.dry_run)
        print(json.dumps(result, sort_keys=True))
        return 1 if result['refused'] else 0
    print(json.dumps(promote(a.run, a.request), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
