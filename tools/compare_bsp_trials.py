#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Read-only storage/count ledger for BSP trials and explicitly listed assets.

Measurements are not geometry, collision, memory, native, or acceptance proofs.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import tempfile

LUMPS = ('entities', 'planes', 'textures', 'vertices', 'visibility', 'nodes',
         'texinfo', 'faces', 'lighting', 'clipnodes', 'leaves', 'marksurfaces',
         'edges', 'surfedges', 'models')
RECORD_BYTES = {1: 20, 3: 12, 5: 24, 6: 40, 7: 20, 9: 8,
                10: 28, 11: 2, 12: 4, 13: 4, 14: 64}
STATUS = 'measurement only; geometry/collision/native/memory unvalidated here'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def measure_bsp(raw):
    if len(raw) < 124 or struct.unpack_from('<i', raw)[0] != 29:
        raise ValueError('Expected BSP29 header')
    intervals = []
    metrics = {'bsp_file_bytes': len(raw)}
    parts = []
    for i, name in enumerate(LUMPS):
        offset, size = struct.unpack_from('<ii', raw, 4 + i * 8)
        if offset < 0 or size < 0 or offset + size > len(raw) or (size and offset < 124):
            raise ValueError('Invalid lump range: ' + name)
        if size:
            intervals.append((offset, offset + size))
        parts.append(raw[offset:offset + size])
        metrics['lump.' + name + '.bytes'] = size
        if i in RECORD_BYTES:
            stride = RECORD_BYTES[i]
            if size % stride:
                raise ValueError('Malformed record stride: ' + name)
            metrics['stored.' + name + '.records'] = size // stride
    intervals.sort()
    if any(a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
        raise ValueError('Overlapping BSP lumps')
    # Includes the fixed header and any alignment gaps or trailing bytes.
    metrics['non_lump_bytes'] = len(raw) - sum(len(part) for part in parts)
    fan = 0
    valid_fan = True
    for position in range(0, len(parts[7]), 20):
        edges = struct.unpack_from('<h', parts[7], position + 8)[0]
        if edges < 3:
            valid_fan = False
        else:
            fan += edges - 2
    metrics['stored.faces.fan_triangle_count'] = fan if valid_fan else None
    return metrics


def read_phase(bsp, assets):
    bsp = Path(bsp).resolve()
    assets = [Path(p).resolve() for p in assets]
    if len(set(assets)) != len(assets) or bsp in assets:
        raise ValueError('Asset list must not double-count BSP or duplicate files')
    raw = bsp.read_bytes()
    metrics = measure_bsp(raw)
    checked = {bsp: sha(raw)}
    resource_rows = []
    for path in assets:
        content = path.read_bytes()
        checked[path] = sha(content)
        resource_rows.append({'path': str(path), 'bytes': len(content), 'sha256': sha(content)})
    metrics['external_assets.file_count'] = len(assets)
    metrics['external_assets.bytes'] = sum(r['bytes'] for r in resource_rows)
    metrics['included_storage.bytes'] = metrics['bsp_file_bytes'] + metrics['external_assets.bytes']
    return {'bsp': {'path': str(bsp), 'sha256': sha(raw), 'bytes': len(raw)},
            'external_assets': resource_rows,
            'external_asset_scope': 'explicit paths only' if assets else 'none explicitly listed; unlisted assets are excluded',
            'metrics': metrics}, checked


def differences(reference, output):
    result = {}
    for name, old in reference.items():
        new = output[name]
        result[name] = {'reference': old, 'output': new,
                        'change_output_minus_reference': None if old is None or new is None else new - old,
                        'saving_reference_minus_output': None if old is None or new is None else old - new,
                        'interpretation': 'unknown' if old is None or new is None else
                                          'increase' if new > old else 'decrease' if new < old else 'unchanged'}
    return result


def markdown(report):
    lines = ['# BSP trial measurement', '', '**Status:** ' + STATUS, '',
             '**Created UTC:** ' + report['created_at_utc'], '',
             '**Created host local:** ' + report['created_at_local'], '',
             '**Method:** ' + report['method'], '',
             'Scope: BSP plus explicitly listed assets only. This is not a whole-game bundle measurement.', '',
             'Positive saving means a reduction; negative saving means an increase.', '']
    for name in ('original', 'before', 'after'):
        row = report['phases'][name]
        lines += [f'## {name}', '', f"BSP: `{row['bsp']['path']}`", '',
                  f"SHA256: `{row['bsp']['sha256']}`", '',
                  f"BSP bytes: {row['bsp']['bytes']}; explicitly included total bytes: {row['metrics']['included_storage.bytes']}", '',
                  'Assets: ' + row['external_asset_scope'], '']
        for asset in row['external_assets']:
            lines += [f"- `{asset['path']}`: {asset['bytes']} bytes; SHA256 `{asset['sha256']}`"]
        lines.append('')
    lines += ['## Output changes', '', '| Metric | Original | Immediate input | Output | Saving vs original | Saving vs immediate input |',
              '|---|---:|---:|---:|---:|---:|']
    for metric, original in report['deltas']['after_vs_original'].items():
        before = report['deltas']['after_vs_before'][metric]
        value = lambda v: 'unknown' if v is None else str(v)
        lines += ['| ' + ' | '.join((metric, value(original['reference']), value(before['reference']),
                                     value(original['output']), value(original['saving_reference_minus_output']),
                                     value(before['saving_reference_minus_output']))) + ' |']
    lines += ['', 'Counts describe stored BSP records. Placed/visible/submitted face counts are unsupported here.',
              'Fan triangles are derived from stored polygon edge counts, not measured renderer submissions.',
              'Net count changes cannot identify created or deleted geometry; those quantities remain unknown.',
              'No memory receipt or native validation is inferred from disk bytes.', '']
    return '\n'.join(lines)


def compare_trials(*, original, before, after, out_dir, method,
                   original_assets=(), before_assets=(), after_assets=()):
    if not isinstance(method, str) or not method.strip():
        raise ValueError('Nonempty method description required')
    destination = Path(out_dir).resolve()
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError('Fresh output directory with an existing parent required')
    phases = {}
    hashes = {}
    for name, bsp, assets in (('original', original, original_assets),
                              ('before', before, before_assets), ('after', after, after_assets)):
        phase, checked = read_phase(bsp, assets)
        phases[name] = phase
        for path, digest in checked.items():
            if path == destination or destination in path.parents:
                raise ValueError('Output directory aliases or contains an input')
            if path in hashes and hashes[path] != digest:
                raise ValueError('Input changed between reads')
            hashes[path] = digest
    created = datetime.now(timezone.utc)
    report = {'format': 'AmiWind BSP trial ledger 1', 'status': STATUS, 'method': method.strip(),
              'created_at_utc': created.isoformat(),
              'created_at_local': created.astimezone().isoformat(),
              'created_at_local_basis': 'timezone-aware host local time; creation clock, not input hash time',
              'scope': 'BSP plus explicit listed external assets only; not whole-game bundle',
              'phases': phases,
              'record_bytes': {LUMPS[i]: n for i, n in RECORD_BYTES.items()},
              'variable_lumps_without_record_count': [LUMPS[i] for i in range(15) if i not in RECORD_BYTES],
              'deltas': {name: differences(phases[reference]['metrics'], phases[output]['metrics'])
                         for name, reference, output in (('before_vs_original', 'original', 'before'),
                                                         ('after_vs_original', 'original', 'after'),
                                                         ('after_vs_before', 'before', 'after'))},
              'unsupported_metrics': {'placed_faces': None, 'visible_faces': None, 'submitted_faces': None,
                                      'created_vertices': None, 'deleted_vertices': None,
                                      'created_faces': None, 'deleted_faces': None,
                                      'resident_memory_bytes': None, 'native_runtime_validation': None}}
    payload_json = json.dumps(report, indent=2) + '\n'
    payload_md = markdown(report)
    for path, expected in hashes.items():
        if sha(path.read_bytes()) != expected:
            raise ValueError('Input changed before output: ' + str(path))
    temporary = Path(tempfile.mkdtemp(prefix='.' + destination.name + '-trial-', dir=destination.parent))
    reserved = False
    installed = []
    prepared = []
    try:
        for name, payload in (('comparison.json', payload_json), ('comparison.md', payload_md)):
            path = temporary / name
            with path.open('x', encoding='utf-8', newline='\n') as output:
                prepared.append(path)
                output.write(payload)
        # Atomic fresh-directory reservation also prevents replacing an empty
        # directory that appears concurrently on POSIX. Inputs were fully parsed
        # and both outputs prepared before any final destination is created.
        destination.mkdir(exist_ok=False)
        reserved = True
        for name in ('comparison.json', 'comparison.md'):
            target = destination / name
            with target.open('xb') as output:
                installed.append(target)
                output.write((temporary / name).read_bytes())
    except Exception:
        for target in installed:
            target.unlink()
        if reserved:
            # Never recursively remove a directory: foreign concurrent content
            # makes rmdir fail rather than being removed by this transaction.
            try:
                destination.rmdir()
            except OSError:
                pass
        raise
    finally:
        for path in prepared:
            path.unlink(missing_ok=True)
        # Exact owned files only; unexpected foreign content is retained.
        try:
            temporary.rmdir()
        except OSError:
            pass
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'before', 'after', 'out-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--method', required=True)
    for name in ('original', 'before', 'after'):
        parser.add_argument('--' + name + '-asset', type=Path, action='append', default=[])
    args = parser.parse_args()
    try:
        report = compare_trials(original=args.original, before=args.before, after=args.after,
                                out_dir=args.out_dir, method=args.method,
                                original_assets=args.original_asset, before_assets=args.before_asset,
                                after_assets=args.after_asset)
    except (OSError, ValueError, struct.error) as exc:
        parser.exit(1, 'Error: ' + str(exc) + '\n')
    storage = report['deltas']['after_vs_original']['included_storage.bytes']
    print(json.dumps({'status': STATUS, 'output': str(args.out_dir.resolve()),
                      'included_bytes_saving_vs_original': storage['saving_reference_minus_output']}, indent=2))


if __name__ == '__main__':
    main()
