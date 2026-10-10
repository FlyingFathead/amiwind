#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Stage output hashes and reference checksums per release (docs/BUILD_CACHE.md).

Every stage's output hash: the SHA-256 of its sorted (path, SHA-256) output list without diagnostics
(tools/build_cache.py diagnostic), so two builds can be compared stage by stage even when a disk image wrapper
differs. A release's reference file (checksums/v<VERSION>.json, written by the release tooling from the release
build) holds, per game edition, those stage hashes, the payload's per-file hashes and the disk image hashes.
A build of the same VERSION compares itself with it and REPORTS: it never stops or changes a build.
Hashes only: no game content and no local paths; file names are the build's own output names.

  python3 tools/build_reference.py write RUN          release tooling: write checksums/v<VERSION>.json
  python3 tools/build_reference.py verify RUN [--against vX.Y.Z]
"""
import argparse
import json
from pathlib import Path
import sys

if str(Path(__file__).resolve().parent) not in sys.path:  # run as a script; never ahead of src/ when imported
    sys.path.append(str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'checksums'
FORMAT = 'AmiWind release reference 1'


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def stage_hash(manifest):
    """A stage's output hash: the top of its unit tree (units -> segments -> stage, diagnostics left out;
    tools/unit_tree.py)."""
    from unit_tree import of_manifest
    return (manifest.get('tree') or of_manifest(manifest))['stage_hash']


def stage_trees(run):
    """{stage: {'hash', 'segments': {segment: hash}}} of RUN, for the reference file."""
    from build_cache import load_manifest
    from unit_tree import of_manifest
    state = load(Path(run) / 'build-state.json') or {}
    result = {}
    for step in state.get('steps', []):
        manifest = load_manifest(run, step['name'])
        if manifest and manifest.get('status') == 'complete':
            found = manifest.get('tree') or of_manifest(manifest)
            result[step['name']] = {'hash': found['stage_hash'],
                                    'segments': {s: v['hash'] for s, v in found['segments'].items()}}
    return result


def stage_hashes(run):
    """{stage: output hash} for every stage of RUN with an output record, in build order."""
    from build_cache import load_manifest
    state = load(Path(run) / 'build-state.json') or {}
    result = {}
    for step in state.get('steps', []):
        manifest = load_manifest(run, step['name'])
        if manifest and manifest.get('status') == 'complete':
            result[step['name']] = stage_hash(manifest)
    return result


def edition(run):
    """The game edition the run was built from (the input check), or 'unknown'."""
    state = load(Path(run) / 'build-state.json') or {}
    found = ((state.get('known_inputs') or {}).get('edition') or {}).get('edition')
    return found or 'unknown'


def payload(run):
    """{payload path: SHA-256} of the finished image (boot volume files and world partitions), and the drives."""
    image = Path(run) / 'image'
    record = load(image / 'build.json') or {}
    files = {}
    boot = image / 'boot'
    if boot.is_dir():
        from build_parallel import hash_files
        paths = sorted(p for p in boot.rglob('*') if p.is_file())
        files.update({p.relative_to(boot).as_posix(): h for p, h in zip(paths, hash_files(paths))})
    for partition in (load(image / 'world-partitions.json') or {}).get('partitions', []):
        for row in partition.get('files', []):
            files[partition['volume'] + ':' + row['path']] = row['sha256']
    drives = {row['file']: row['sha256'] for row in record.get('hdf_files') or [] if row.get('sha256')}
    return files, drives


def reference_path(version):
    return FOLDER / f'v{version}.json'


def write(run, version=None):
    from project_version import public_version
    version = version or public_version()
    files, drives = payload(run)
    path = reference_path(version)
    document = load(path) or {'format': FORMAT, 'version': version, 'editions': {}}
    document['editions'][edition(run)] = {'stages': stage_hashes(run), 'segments': {
        name: tree['segments'] for name, tree in stage_trees(run).items()}, 'payload': files, 'drives': drives}
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(document, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return path


def verify(run, version=None):
    """The comparison with the reference for VERSION (warn only): a dict with status 'no-reference', 'match' or
    'differs', and the stages, payload files and drives that differ."""
    from project_version import public_version
    version = version or public_version()
    document = load(reference_path(version))
    found = edition(run)
    if not document:
        return {'status': 'no-reference', 'version': version, 'edition': found}
    reference = (document.get('editions') or {}).get(found)
    if reference is None:
        return {'status': 'no-reference', 'version': version, 'edition': found,
                'editions': sorted(document.get('editions') or {})}
    stages = stage_hashes(run)
    differ = [name for name in reference.get('stages', {}) if name in stages and stages[name] != reference['stages'][name]]
    missing = [name for name in reference.get('stages', {}) if name not in stages]
    files, drives = payload(run)
    payload_differ = sorted(path for path in set(reference.get('payload', {})) | set(files)
                            if reference.get('payload', {}).get(path) != files.get(path)) if files else None
    drive_match = bool(drives) and drives == reference.get('drives')
    status = 'match' if not differ and not missing and drive_match else 'differs'
    segments = []
    if differ and reference.get('segments'):
        mine = stage_trees(run).get(differ[0], {}).get('segments', {})
        theirs = reference['segments'].get(differ[0], {})
        segments = sorted(s for s in set(mine) | set(theirs) if mine.get(s) != theirs.get(s))
    return {'status': status, 'version': version, 'edition': found, 'stages': len(reference.get('stages', {})),
            'stages_matching': len(reference.get('stages', {})) - len(differ) - len(missing),
            'stages_differing': differ, 'stages_missing': missing, 'first_differing': (differ or [None])[0],
            'payload_differing': payload_differ, 'drives_match': drive_match, 'first_differing_segments': segments}


def verify_line(result):
    """One line for the end summary (warn only)."""
    if result['status'] == 'no-reference':
        return f"Reference check: no reference checksums for v{result['version']} ({result['edition']}) yet"
    if result['status'] == 'match':
        return f"Reference check vs v{result['version']} ({result['edition']}): HDF matches the official release image"
    payload = result['payload_differing']
    files = (f", payload files differing: {len(payload)}" if payload else ', payload files match') if payload is not None else ''
    first = f", first differing stage: {result['first_differing']}" if result['first_differing'] else ''
    if result.get('first_differing_segments'):
        first += ' (segments ' + ', '.join(result['first_differing_segments'][:3]) + ')'
    return (f"WARNING: reference check vs v{result['version']} ({result['edition']}): {result['stages_matching']}/"
            f"{result['stages']} stages match{first}{files}; drives {'match' if result['drives_match'] else 'differ'}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    w = sub.add_parser('write')
    w.add_argument('run', type=Path)
    v = sub.add_parser('verify')
    v.add_argument('run', type=Path)
    v.add_argument('--against', help='release version, e.g. v0.0.33 (default: this checkout\'s VERSION)')
    args = parser.parse_args(argv)
    if args.command == 'write':
        print('Wrote ' + str(write(args.run)))
        return 0
    result = verify(args.run, (args.against or '').lstrip('v') or None)
    print(verify_line(result))
    return 0  # a report, never a failure


if __name__ == '__main__':
    raise SystemExit(main())
