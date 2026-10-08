# SPDX-License-Identifier: GPL-3.0-only
"""Final static exterior surface pass, with explicit settings and per-map receipts."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import struct
import time
from collections import Counter
from concurrent.futures import wait, FIRST_COMPLETED


def enabled_value(value=True):
    if type(value) is bool:
        return value
    if value in ('true', 'false'):
        return value == 'true'
    raise ValueError('hidden-surface-cull must be true or false')


def add_options(parser):
    parser.add_argument('--hidden-surface-cull', choices=('true', 'false'), default='true',
                        help='Cull proven permanently hidden static exterior surfaces before final map packaging (default: true); false preserves the input render geometry')


def bsp_counts(raw):
    if len(raw) < 124 or struct.unpack_from('<i', raw)[0] != 29:
        raise ValueError('Hidden-surface pass requires BSP29')
    result = {'file_bytes': len(raw)}
    for key, lump, size in (('stored_faces', 7, 20), ('vertices', 3, 12),
                            ('edges', 12, 4), ('texinfo', 6, 40)):
        offset, length = struct.unpack_from('<ii', raw, 4 + 8 * lump)
        if offset < 0 or length < 0 or offset + length > len(raw) or length % size:
            raise ValueError('Invalid BSP lump: ' + key)
        result[key] = length // size
    return result


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def proof_summary(detail):
    """Avoid retaining every triangle ID from every map in the build manifest."""
    if 'proofs' not in detail:
        return detail
    reasons = Counter(component.get('reason', component.get('status', 'unknown'))
                      for proof in detail['proofs'] for component in proof.get('components', []))
    return {key: value for key, value in detail.items()
            if key not in ('proofs', 'placements', 'removed_face_ids', 'unsupported_static_cases')} | {
        'removed_stored_faces': len(detail.get('removed_face_ids', [])),
        'proof_input_triangles': sum(p.get('input_triangles', 0) for p in detail['proofs']),
        'certified_occluders': sum(p.get('certified_occluders', 0) for p in detail['proofs']),
        'component_outcomes': dict(sorted(reasons.items())),
        'protected_nonstatic_placements': len(detail.get('unsupported_static_cases', []))}


def _prepare_hidden_map(source, work, enabled, exterior, processor):
    """Worker prepares private evidence only; parent installs after all checks."""
    source, work = Path(source), Path(work)
    if enabled and exterior and processor is None:
        from cull_bsp_hidden import cull_bsp
        processor = cull_bsp
    raw = source.read_bytes()
    before = bsp_counts(raw)
    if not enabled:
        output, detail = raw, {'status': 'disabled by explicit override'}
    elif not exterior:
        output, detail = raw, {'status': 'outside explicit exterior manifest'}
    else:
        output, detail = processor(raw, enabled=True, scene_kind='exterior')
    after = bsp_counts(output)
    if after['stored_faces'] > before['stored_faces']:
        raise ValueError('Hidden whole-surface removal increased stored faces: ' + source.stem)
    row = {'map': source.stem, 'enabled': enabled, 'scene_kind': 'exterior' if exterior else 'outside exterior pass',
           'input_sha256': digest(raw), 'output_sha256': digest(output),
           'before': before, 'after': after,
           'removed_stored_faces': before['stored_faces'] - after['stored_faces'],
           'file_bytes_saved': len(raw) - len(output), 'details': proof_summary(detail)}
    if output != raw:
        (work / 'originals' / source.name).write_bytes(raw)
        (work / 'candidates' / source.name).write_bytes(output)
        proof_path = (work / 'proofs') / (source.stem + '.json')
        proof_path.write_text(json.dumps(detail, indent=2) + '\n', encoding='utf-8', newline='\n')
        row['removal_proof'] = {'path': str(proof_path.relative_to(work)),
                                'sha256': digest(proof_path.read_bytes())}
    return row, detail.get('status', detail.get('acceptance', 'proof pass complete'))


def _prepared_maps(inputs, work, enabled, names, processor, jobs):
    if jobs == 1:
        for source in inputs:
            yield source, _prepare_hidden_map(source, work, enabled, source.stem in names, processor)
        return
    # Only jobs pending results: never retain the entire world's BSP bytes.
    from build_parallel import process_pool, worker_environment
    with worker_environment(), process_pool(min(jobs, len(inputs))) as pool:
        pending = {}
        # Largest maps first so no big map starts last (results are sorted afterwards).
        iterator = iter(sorted(inputs, key=lambda p: (-p.stat().st_size, p.name)))
        def submit(source):
            future = pool.submit(_prepare_hidden_map, source, work, enabled, source.stem in names, processor)
            pending[future] = source
        for _ in range(min(jobs, len(inputs))): submit(next(iterator))
        while pending:
            ready, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in ready:
                source = pending.pop(future)
                yield source, future.result()
                following = next(iterator, None)
                if following is not None: submit(following)


def cull_staged_maps(maps, work, exterior_maps, *, enabled=True, processor=None, jobs=1):
    """Prepare all results before replacing derived staging files; keep originals.

    This operates only on a build's private staging directory. Scene context is
    an explicit manifest supplied by the builder; unknown maps are never guessed
    to be exteriors from geometry or sky textures. Source game files are not used.
    """
    enabled = enabled_value(enabled)
    if type(jobs) is not int or jobs < 1:
        raise ValueError('Hidden-surface jobs must be a positive integer')
    maps, work = Path(maps).resolve(), Path(work).resolve()
    if maps == work or maps in work.parents or work in maps.parents:
        raise ValueError('Keep hidden-surface receipts separate from staged maps')
    names = set(exterior_maps)
    if any(not isinstance(n, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', n) for n in names):
        raise ValueError('Exterior manifest requires plain map names without extensions')
    inputs = sorted(maps.glob('*.bsp'))
    if not inputs:
        raise ValueError('No staged BSP maps')
    missing = names - {p.stem for p in inputs}
    if missing:
        raise ValueError('Exterior manifest maps missing: ' + ', '.join(sorted(missing)))
    if any(p.is_symlink() or p.resolve().parent != maps for p in inputs):
        raise ValueError('Staged BSPs must be regular files within the map directory')
    work.mkdir(parents=True, exist_ok=False)
    candidates = work / 'candidates'
    originals = work / 'originals'
    proofs = work / 'proofs'
    candidates.mkdir(); originals.mkdir(); proofs.mkdir()
    report = {'format': 'AmiWind hidden surface build 1',
              'started_at': datetime.now().astimezone().isoformat(), 'enabled': enabled,
              'method': 'certified opaque closed-shell containment',
              'status': 'running', 'maps': [], 'preparation_jobs': jobs,
              'acceptance': 'Bounded proof only; not a claim that all hidden interiors or terrain have been removed'}
    report_path = work / 'hidden-surfaces.json'

    saved = [0.0]

    def save(progress=False):
        # A progress save rewrites the whole growing receipt (megabytes for the
        # world): at most every 2 s, or the parent serializes instead of feeding
        # the workers. Start, end and failure always save.
        now = time.monotonic()
        if progress and now - saved[0] < 2:
            return
        saved[0] = now
        report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')

    save()
    try:
        if enabled and processor is None:
            from cull_bsp_hidden import cull_bsp
            processor = cull_bsp
        for source, (row, detail_status) in _prepared_maps(inputs, work, enabled, names, processor, jobs):
            before, after = row['before'], row['after']
            report['maps'].append(row)
            print('[hidden-surface-cull] {}: {}; {}; stored faces {} -> {}; removed {}; {}'.format(
                source.stem, 'ON' if enabled else 'OFF', row['scene_kind'],
                before['stored_faces'], after['stored_faces'], row['removed_stored_faces'],
                detail_status), flush=True)
            save(progress=True)
        report['maps'].sort(key=lambda row: row['map'])
        # Verify all inputs again before installing anything into build staging.
        for row in report['maps']:
            if digest((maps / (row['map'] + '.bsp')).read_bytes()) != row['input_sha256']:
                raise ValueError('Staged BSP changed during hidden-surface pass: ' + row['map'])
        for row in report['maps']:
            staged = candidates / (row['map'] + '.bsp')
            if staged.exists():
                if digest(staged.read_bytes()) != row['output_sha256']:
                    raise ValueError('Hidden-surface output checksum mismatch: ' + row['map'])
                staged.replace(maps / staged.name)
        for row in report['maps']:
            if digest((maps / (row['map'] + '.bsp')).read_bytes()) != row['output_sha256']:
                raise ValueError('Installed BSP checksum mismatch: ' + row['map'])
        report.update(status='completed', map_count=len(inputs), exterior_map_count=len(names),
                      removed_stored_faces=sum(r['removed_stored_faces'] for r in report['maps']),
                      file_bytes_saved=sum(r['file_bytes_saved'] for r in report['maps']))
    except Exception as exc:
        report.update(status='failed', error=str(exc))
        raise
    finally:
        report['finished_at'] = datetime.now().astimezone().isoformat()
        save()
    return report
