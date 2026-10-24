#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Verified, transactional representation optimization of staged BSP29 maps.

Interpreter/source/data only: this module never compiles or runs a helper.
Prepare and independently verify every candidate before replacing any original.
Run after all entity/geometry edits and before actor-contact and final heap gates.
This is representation validation, not runtime or gameplay acceptance.
"""
import argparse
from concurrent.futures import wait, FIRST_COMPLETED
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from share_bsp_geometry import share_geometry
from deduplicate_bsp import deduplicate
from check_geometry_render_inputs import compare_render_inputs, compare_sample_sharing


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_report(path, report):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(report, indent=2)+'\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare_candidate(path, transaction, cache=None):
    """Worker: only read one input and write its private candidate/backup files.

    cache (pass_cache.PassCache or None): a recorded result for the same input
    bytes and optimizer sources is used instead of preparing the map again
    (BUILD-IMAGE-NOT-INCREMENTAL-33); the row and bytes are those it recorded."""
    path, transaction = Path(path), Path(transaction)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Expected regular staged map: '+path.name)
    original = path.read_bytes()
    if cache is not None:
        input_sha = sha(original)
        found = cache.load(input_sha)
        if found is not None:
            row, final = found
            row = {k: (path.name if k == 'map' else v) for k, v in row.items()}  # key order kept
            if row['changed']:
                from build_parallel import keep_original
                keep_original(path, transaction/'original'/path.name, original)
                (transaction/'candidate'/path.name).write_bytes(final)
            return row
        row, final = _prepare(path, transaction, original)
        row = json.loads(json.dumps(row))  # the form a cached row has
        import cache_provenance
        cache_provenance.name_unit(cache, input_sha, lambda: path.name, lambda: [('map bytes', input_sha)])
        cache.store(input_sha, row, final if row['changed'] else None)
        return row
    return _prepare(path, transaction, original)[0]


def _prepare(path, transaction, original):
    shared, geometry = share_geometry(original)
    geometry_oracle = compare_render_inputs(original, shared)
    final, samples = deduplicate(shared)
    sample_oracle = compare_sample_sharing(shared, final)
    changed = final != original
    row = {'map': path.name, 'input_sha256': sha(original), 'output_sha256': sha(final),
           'input_bytes': len(original), 'output_bytes': len(final),
           'file_bytes_saved': len(original)-len(final), 'changed': changed,
           'geometry': geometry, 'geometry_oracle': geometry_oracle,
           'sample_sharing': samples, 'sample_oracle': sample_oracle}
    if changed:
        from build_parallel import keep_original  # committed by os.replace, never rewritten
        keep_original(path, transaction/'original'/path.name, original)
        (transaction/'candidate'/path.name).write_bytes(final)
    return row, final


def prepare_candidates(candidates, transaction, jobs, report, cache=None):
    """At most jobs outstanding maps; parent keeps deterministic receipt order.

    Pool shutdown waits for running workers before transaction cleanup. Workers
    never replace staged maps. A failed worker cancels pending work and the
    caller records failure without committing any candidate.
    """
    if jobs == 1:
        for index, path in enumerate(candidates):
            report['active_map'] = path.name
            yield index, prepare_candidate(path, transaction, cache)
        return
    from build_parallel import process_pool, worker_environment
    with worker_environment(), process_pool(min(jobs, len(candidates))) as pool:
        pending = {}
        # Largest maps first; results keep their index, so the receipt order is unchanged.
        source = iter(sorted(enumerate(candidates), key=lambda item: (-item[1].stat().st_size, item[0])))
        def submit_next():
            item = next(source, None)
            if item is not None:
                index, path = item
                pending[pool.submit(prepare_candidate, path, transaction, cache)] = (index, path)
        for _ in range(min(jobs, len(candidates))):
            submit_next()
        try:
            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in sorted(done, key=lambda f: pending[f][0]):
                    index, path = pending.pop(future)
                    report['active_map'] = path.name
                    yield index, future.result()
                    submit_next()
        except BaseException:
            for future in pending:
                future.cancel()
            raise


def optimize_maps(maps, report_path, jobs=1):
    if type(jobs) is not int or jobs < 1:
        raise ValueError('Optimizer jobs must be a positive integer')
    maps = Path(maps)
    report_path = Path(report_path)
    candidates = sorted(maps.glob('*.bsp'))
    report = {'format': 'AmiWind verified staged BSP optimization 1', 'status': 'preparing',
              'acceptance': 'representation only; final heap gate and target validation pending',
              'source_sha256': {name: sha((Path(__file__).parent/name).read_bytes()) for name in
                  ('optimize_world_maps.py', 'share_bsp_geometry.py', 'deduplicate_bsp.py',
                   'check_geometry_render_inputs.py', 'player_hull.py')},
              'estimate_provenance': 'No ABI probe or numeric heap estimate in optimizer; '
                  'the subsequent receipt-bound final heap gate audits these output hashes.',
              'maps': [], 'committed_maps': [], 'preparation_jobs': jobs}
    if not candidates:
        report.update(status='failed', error='No staged BSP maps')
        write_report(report_path, report)
        raise ValueError(report['error'])
    transaction = Path(tempfile.mkdtemp(prefix='map-optimize-', dir=maps.parent))
    committed = []
    keep_backups = False
    try:
        (transaction/'candidate').mkdir()
        (transaction/'original').mkdir()
        ordered_rows = [None] * len(candidates)
        completed = 0
        # Development builds reuse results for unchanged map bytes (pass_cache.py).
        from pass_cache import PassCache
        cache = PassCache.open('optimize-world-maps', {}, (__file__, 'prepare_candidate'))  # the per-map worker's code only
        if cache is not None:
            report['pass_cache'] = {'sources_sha256': cache.sources}
        try:
            for index, row in prepare_candidates(candidates, transaction, jobs, report, cache):
                ordered_rows[index] = row
                completed += 1
                report['maps'] = [item for item in ordered_rows if item is not None]
                if completed == 1 or completed % 100 == 0 or completed == len(candidates):
                    print(f'BSP optimizer verified {completed}/{len(candidates)} maps', flush=True)
        finally:
            if cache is not None:
                # Hits and misses of this run in the receipt (release builds with --allow-release-reuse).
                report['pass_cache'] = cache.summary()
                print('BSP optimizer pass cache: %d maps reused, %d prepared.'
                      % (report['pass_cache']['hits'], report['pass_cache']['misses']), flush=True)
        # Refuse concurrent edits or new/deleted maps before the first replacement.
        if [p.name for p in sorted(maps.glob('*.bsp'))] != [r['map'] for r in report['maps']]:
            raise ValueError('Staged map set changed during optimization')
        from build_parallel import hash_files
        current = hash_files([maps/row['map'] for row in report['maps']], jobs)
        for row, actual in zip(report['maps'], current):
            if actual != row['input_sha256']:
                raise ValueError('Staged map changed during optimization: '+row['map'])
        report['status'] = 'committing'
        write_report(report_path, report)
        for row in report['maps']:
            if row['changed']:
                os.replace(transaction/'candidate'/row['map'], maps/row['map'])
                committed.append(row['map'])
        # CHIM room maps (maps/<room>.chim, IMAGE-ROOM-MAPS-OPTIMIZER-RECEIPT-48): written by the CHIM rooms install,
        # never optimized; they join the receipt unchanged so the later gates bind to the whole staged map set.
        from map_files import is_chim_room, map_files
        rooms = [p for p in map_files(maps) if p.suffix != '.bsp' and is_chim_room(p)]
        for path, value in zip(rooms, hash_files(rooms, jobs)):
            size = path.stat().st_size
            report['maps'].append({'map': path.name, 'input_sha256': value, 'output_sha256': value, 'input_bytes': size,
                                   'output_bytes': size, 'file_bytes_saved': 0, 'changed': False,
                                   'not_optimized': 'CHIM room map'})
        verify_optimized_maps(maps, report, require_committed=False, jobs=jobs)
        report.update(status='verified', committed_maps=committed,
                      map_count=len(report['maps']), changed_maps=len(committed),
                      file_bytes_saved=sum(r['file_bytes_saved'] for r in report['maps']))
        report.pop('active_map', None)
        write_report(report_path, report)
        return report
    except BaseException as error:
        rollback_errors = []
        for name in reversed(committed):
            try:
                os.replace(transaction/'original'/name, maps/name)
            except OSError as rollback:
                rollback_errors.append(name+': '+str(rollback))
        keep_backups = bool(rollback_errors)
        report.update(status='failed', error=str(error), committed_maps=committed,
                      rollback='failed; originals retained' if keep_backups else 'originals preserved/restored',
                      rollback_errors=rollback_errors)
        if keep_backups:
            report['recovery_directory'] = str(transaction)
        write_report(report_path, report)
        raise
    finally:
        if not keep_backups:
            if transaction.resolve().parent != maps.parent.resolve() or not transaction.name.startswith('map-optimize-'):
                raise ValueError('Refusing cleanup outside the owned transaction directory')
            shutil.rmtree(transaction)


def verify_optimized_maps(maps, report, require_committed=True, jobs=1):
    """Bind later gates to the exact complete optimized map set; no mutation."""
    from build_parallel import hash_files
    if require_committed and report.get('status') != 'verified':
        raise ValueError('Optimizer receipt has not completed verification')
    from map_files import map_files
    paths = map_files(maps)         # x.bsp and the CHIM frame maps x.chim (tools/map_files.py)
    actual = dict(zip((p.name for p in paths), hash_files(paths, jobs)))
    expected = {r['map']: r['output_sha256'] for r in report['maps']}
    if actual != expected:
        raise ValueError('Final staged maps no longer match optimizer receipt')


def rebind_chim_maps(maps, report, report_path, removed, jobs=1, replaced=()):
    """A CHIM image changes the optimized map set once, after the optimizer: it writes the CHIM frame
    maps (an empty world plus entities, found by their "_chim_frame" key; not optimized) and removes the legacy
    exterior maps it does not ship (`removed`: id1-relative 'maps/x.bsp' rows). The receipt follows:
    removed rows leave, frame maps join unchanged (input = output), the change is recorded under
    'chim_rebind', and the later gates (final heap audit, verify_optimized_maps) bind to the result.
    `replaced`: map file names removed and written again as CHIM region frame maps (tools/chim/regions.py: the
    frame map keeps the open-world map's name, as vfNNNN.chim or, with chim_frame_ext bsp, vfNNNN.bsp); they
    leave as removed rows and join as frame maps. Any other new or missing map stops the image."""
    from build_parallel import hash_files
    from map_files import is_chim_frame, map_files, map_stem
    maps = Path(maps)
    gone = sorted({Path(name).name for name in removed if name.startswith('maps/') and name.endswith('.bsp')})
    present = {p.name for p in map_files(maps)}
    replaced = {map_stem(name) for name in replaced}
    rows = [r for r in report['maps'] if r['map'] not in gone]
    missing = sorted(r['map'] for r in rows if r['map'] not in present)
    if missing:
        raise ValueError('Optimized maps missing after the CHIM frame maps: ' + ', '.join(missing[:8]))
    gone_stems = {map_stem(name) for name in gone}
    if replaced - gone_stems:
        raise ValueError('Replaced maps not in the removed list: ' + ', '.join(sorted(replaced - gone_stems)[:8]))
    present_stems = {map_stem(name): name for name in present}
    absent = sorted(replaced - set(present_stems))
    if absent:
        raise ValueError('CHIM region frame maps missing: ' + ', '.join(absent[:8]))
    still = sorted(name for name in set(gone) & present if map_stem(name) not in replaced)
    # a region frame written under the legacy name (chim_frame_ext bsp) is the frame map, not the legacy map
    still += sorted(name for name in set(gone) & present if map_stem(name) in replaced and not is_chim_frame(maps / name))
    if still:
        raise ValueError('Removed legacy maps still staged: ' + ', '.join(still[:8]))
    added = sorted(present - {r['map'] for r in rows})
    other = [name for name in added if not is_chim_frame(maps / name)]
    if other:
        raise ValueError('Maps added after the optimizer that are not CHIM frame maps: ' + ', '.join(other[:8]))
    for name, value in zip(added, hash_files([maps / name for name in added], jobs)):
        size = (maps / name).stat().st_size
        rows.append({'map': name, 'input_sha256': value, 'output_sha256': value, 'input_bytes': size,
                     'output_bytes': size, 'file_bytes_saved': 0, 'changed': False,
                     'not_optimized': 'CHIM region frame map' if map_stem(name) in replaced else 'CHIM frame map'})
    rows.sort(key=lambda r: r['map'])
    report['maps'] = rows
    report['committed_maps'] = [name for name in report.get('committed_maps', []) if name not in gone]
    report.update(map_count=len(rows), changed_maps=len(report['committed_maps']),
                  file_bytes_saved=sum(r['file_bytes_saved'] for r in rows),
                  chim_rebind=dict({'removed': gone, 'added_frame_maps': added},
                                   **({'replaced_by_region_frames': sorted(present_stems[n] for n in replaced)}
                                      if replaced else {})))
    write_report(report_path, report)
    verify_optimized_maps(maps, report, jobs=jobs)
    return report


def rebind_marked_maps(maps, report, report_path, names, mark, jobs=1):
    """A late mark written into maps the optimizer never optimizes (CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48: the room heap
    gate's "_chim_room_fast_mb" "32" in the worldspawn of the CHIM rooms that need 32 MB of Fast RAM). The caller
    checks the receipt (verify_optimized_maps) right before it writes the mark, so between that check and this call
    only the mark changed these maps. The receipt follows exactly the NAMES (map file names): each must be a receipt
    row that was not optimized and must be a CHIM room map; its row takes the marked bytes (input = output, as for
    every map the optimizer leaves as written) and keeps the hash before the mark ('marked_from_sha256'); the change
    is recorded under 'post_optimizer_marks' with MARK (the key and value written). Every other map must still match
    its row (verify_optimized_maps): any other change stops the image as before."""
    from build_parallel import hash_files
    from map_files import is_chim_room
    maps = Path(maps)
    names = sorted(set(names))
    rows = {r['map']: r for r in report['maps']}
    unknown = [n for n in names if n not in rows]
    if unknown:
        raise ValueError('Marked maps not in the optimizer receipt: ' + ', '.join(unknown[:8]))
    optimized = [n for n in names if rows[n].get('changed') or not rows[n].get('not_optimized')]
    if optimized:
        raise ValueError('Marked maps the optimizer optimized: ' + ', '.join(optimized[:8]))
    others = [n for n in names if not is_chim_room(maps / n)]
    if others:
        raise ValueError('Marked maps that are not CHIM room maps: ' + ', '.join(others[:8]))
    for name, value in zip(names, hash_files([maps / n for n in names], jobs)):
        row, size = rows[name], (maps / name).stat().st_size
        row.setdefault('marked_from_sha256', row['output_sha256'])
        row.update(input_sha256=value, output_sha256=value, input_bytes=size, output_bytes=size, marked=mark)
    marks = report.setdefault('post_optimizer_marks', [])
    marks.append({'mark': mark, 'maps': names})
    write_report(report_path, report)
    verify_optimized_maps(maps, report, jobs=jobs)
    return report


def bind_heap_report(optimization, heap, heap_path, report_path):
    """Record the actual later gate's provenance without changing BSP payloads."""
    expected = {r['map']: r['output_sha256'] for r in optimization['maps']}
    actual = {r['map']: r['file_sha256'] for r in heap['maps']}
    if expected != actual:
        raise ValueError('Final heap audit does not describe optimized map outputs')
    saved_heap = Path(heap_path).read_bytes()
    if json.loads(saved_heap) != heap:
        raise ValueError('Saved final heap receipt differs from the supplied audit')
    optimization['final_heap_gate'] = {
        'report': str(heap_path), 'sha256': sha(saved_heap),
        'passing_maps': heap['passing_maps'], 'failing_maps': heap['failing_maps'],
        'acceptance': heap['acceptance'],
        'baseline_reserve_bytes': heap['baseline_reserve_bytes'],
        'safety_headroom_bytes': heap['safety_headroom_bytes']}
    estimates = {r['map']: r for r in heap['maps']}
    for row in optimization['maps']:
        estimate = estimates[row['map']]
        row['final_estimate'] = {key: estimate[key] for key in
            ('resident_loader_bytes', 'peak_loader_bytes', 'estimated_clearance_bytes', 'gate')}
    write_report(report_path, optimization)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--maps', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=1, help='Concurrent Python map preparation workers')
    args = parser.parse_args()
    report = optimize_maps(args.maps, args.report, jobs=args.jobs)
    print(f"Verified {report['map_count']} maps; saved {report['file_bytes_saved']} file bytes. "
          'Final heap and target checks still required.', flush=True)


if __name__ == '__main__':
    main()
