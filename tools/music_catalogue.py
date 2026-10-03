#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Generate the small AWOST1 manual-play catalogue from an owned manifest.

No audio is read, converted or bundled. Numeric IDs remain manifest positions;
the existing trackNN.mws naming is checked rather than renumbered. Runtime
header/file-size validation and Amiga command execution are separate checks.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile


def normalized_alias(value):
    value = value.replace('\\', '/').casefold()
    value = ''.join('_' if c.isspace() or c == '/' else c for c in value)
    return value if re.fullmatch(r'[a-z0-9_.+\-]{1,95}', value, re.ASCII) else None


def build_catalogue(manifest):
    tracks = manifest.get('tracks')
    if not isinstance(tracks, list) or not 1 <= len(tracks) <= 99:
        raise ValueError('Catalogue requires 1..99 tracks (IDs 0..98)')
    prepared = []
    for number, track in enumerate(tracks):
        if track.get('file') != f'track{number:02d}.mws':
            raise ValueError('Track file/index mismatch; numeric IDs must remain stable')
        source = track.get('source')
        digest = track.get('sha256')
        if not isinstance(source, str) or not source or '\0' in source:
            raise ValueError('Invalid original track source')
        path = PurePosixPath(source.replace('\\', '/'))
        if path.is_absolute() or '..' in path.parts or ':' in source:
            raise ValueError('Track source must be a relative game path')
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-fA-F]{64}', digest):
            raise ValueError('A verified stream SHA-256 is required for alias sharing')
        folder = path.parent.name.casefold()
        group = {'explore': 0, 'battle': 1}.get(folder, 2)
        prepared.append({'id': number, 'path': path, 'sha256': digest.lower(), 'group': group})
    # The existing player excludes canonical title audio from world shuffles.
    # A duplicate copy under Explore must also be a manual one-shot selection.
    titles = {r['sha256'] for r in prepared
              if r['group'] == 2 and r['path'].name.casefold() == 'morrowind title.mp3'}
    for row in prepared:
        if row['sha256'] in titles:
            row['group'] = 2
    proposed = {}
    omitted = []
    for row in prepared:
        path = row['path']; number = row['id']
        values = (path.name, path.stem, str(path), str(path.with_suffix('')),
                  f'track{number:02d}', f'track{number:02d}.mws')
        for value in values:
            alias = normalized_alias(value)
            if alias is None or alias.isdecimal():
                omitted.append({'id': number, 'source_alias': value,
                                'reason': 'unsupported/long alias or reserved numeric token'})
                continue
            proposed.setdefault(alias, set()).add(number)
    # One reserved numeric row per ID guarantees recall even when every source
    # name is ambiguous or cannot be represented in the native ASCII catalogue.
    rows = [(r['id'], r['group'], f"{r['id']:02d}") for r in prepared]
    canonical_aliases = []
    for alias, ids in sorted(proposed.items()):
        if len({prepared[i]['sha256'] for i in ids}) != 1:
            omitted.append({'alias': alias, 'ids': sorted(ids), 'reason': 'ambiguous different audio'})
            continue
        number = min(ids)
        rows.append((number, prepared[number]['group'], alias))
        if len(ids) > 1:
            canonical_aliases.append({'alias': alias, 'ids': sorted(ids), 'canonical_id': number})
    rows.sort(key=lambda row: (row[0], row[2]))
    content = ('AWOST1\n' + ''.join(f'{number:02d} {group} {alias}\n'
                                   for number, group, alias in rows)).encode('ascii')
    return content, {'format': 'AWOST1', 'track_count': len(tracks), 'alias_rows': len(rows),
                     'numeric_ids': list(range(len(tracks))), 'groups': [r['group'] for r in prepared],
                     'canonical_aliases': canonical_aliases, 'omitted_aliases': omitted,
                     'catalogue_sha256': hashlib.sha256(content).hexdigest(),
                     'acceptance': 'catalogue source/data only; compiled command and target playback not validated'}


def write_catalogue(manifest_path, output):
    manifest_path, output = Path(manifest_path), Path(output)
    raw = manifest_path.read_bytes()
    content, report = build_catalogue(json.loads(raw))
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=output.name+'.', suffix='.tmp', dir=output.parent)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(content)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    report['manifest_sha256'] = hashlib.sha256(raw).hexdigest()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(write_catalogue(args.manifest, args.out), indent=2))


if __name__ == '__main__':
    main()
