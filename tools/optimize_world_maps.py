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


def prepare_candidate(path, transaction):
    """Worker: only read one input and write its private candidate/backup files."""
    path, transaction = Path(path), Path(transaction)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Expected regular staged map: '+path.name)
    original = path.read_bytes()
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
        (transaction/'original'/path.name).write_bytes(original)
        (transaction/'candidate'/path.name).write_bytes(final)
    return row


def prepare_candidates(candidates, transaction, jobs, report):
    """At most jobs outstanding maps; parent keeps deterministic receipt order.

    Pool shutdown waits for running workers before transaction cleanup. Workers
    never replace staged maps. A failed worker cancels pending work and the
    caller records failure without committing any candidate.
    """
    if jobs == 1:
        for index, path in enumerate(candidates):
            report['active_map'] = path.name
            yield index, prepare_candidate(path, transaction)
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
                pending[pool.submit(prepare_candidate, path, transaction)] = (index, path)
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
        for index, row in prepare_candidates(candidates, transaction, jobs, report):
            ordered_rows[index] = row
            completed += 1
            report['maps'] = [item for item in ordered_rows if item is not None]
            if completed == 1 or completed % 100 == 0 or completed == len(candidates):
                print(f'BSP optimizer verified {completed}/{len(candidates)} maps', flush=True)
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
    paths = sorted(Path(maps).glob('*.bsp'))
    actual = dict(zip((p.name for p in paths), hash_files(paths, jobs)))
    expected = {r['map']: r['output_sha256'] for r in report['maps']}
    if actual != expected:
        raise ValueError('Final staged maps no longer match optimizer receipt')


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
