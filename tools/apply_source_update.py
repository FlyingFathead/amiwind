#!/usr/bin/env python3
"""Apply a verified source update, backing up replacements and checking conflicts."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil


def apply(source, target, backup):
    source, target, backup = (Path(p).resolve() for p in (source, target, backup))
    if source == target or source in target.parents or target in source.parents:
        raise ValueError('Use a separate extracted source directory')
    if backup == target or target in backup.parents or backup.exists():
        raise ValueError('Choose a new backup directory outside the checkout')
    if not (target/'VERSION').is_file():
        raise ValueError('Target is not an AmiWind checkout')
    manifest = json.loads((source/'docs/PACKAGE_MANIFEST.json').read_text())
    bases = json.loads((source/'docs/RECONCILE-BASES.json').read_text())
    operations, conflicts = [], []
    for name in sorted(set(manifest['files']) | set(bases['removed'])):
        rel = PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name:
            raise ValueError('Unsafe source path')
        dest = target.joinpath(*rel.parts)
        if any(p.is_symlink() for p in [dest, *dest.parents] if p != target.parent):
            raise ValueError('Symlink destination: '+name)
        if dest.exists() and not dest.is_file():
            raise ValueError('Non-file destination: '+name)
        current = hashlib.sha256(dest.read_bytes()).hexdigest() if dest.is_file() else None
        expected = manifest['files'].get(name)
        desired = expected['sha256'] if expected else None
        mode = 0o755 if name in bases['executables'] else 0o644
        if expected and not (source/name).exists() and name not in bases['touched']:
            continue
        if expected:
            data = (source/name).read_bytes()
            if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != desired:
                raise ValueError('Source checksum mismatch: '+name)
        if current == desired:
            if current is not None and dest.stat().st_mode & 0o777 != mode:
                operations.append((name, 'mode', mode))
            continue
        # Paths identical in every baseline are outside this update; preserve edits.
        if name not in bases['touched'] and name not in bases['removed'] and current is not None:
            continue
        known = bases['known'].get(name, [])
        if current is not None and current not in known:
            conflicts.append(name)
        elif current is None and expected and known and name not in bases['may_be_absent']:
            conflicts.append(name+' (locally deleted)')
        else:
            operations.append((name, 'write' if expected else 'delete', mode))
    if conflicts:
        raise ValueError('Conflicts; no files changed:\n'+'\n'.join(conflicts))
    backup.mkdir(parents=True)
    for name, action, mode in operations:
        dest = target/name
        if dest.exists():
            saved = backup/name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, saved)
    (backup/'operations.json').write_text(json.dumps(operations, indent=2)+'\n')
    for name, action, mode in operations:
        dest = target/name
        if action == 'delete':
            dest.unlink(missing_ok=True)
        elif action == 'mode':
            dest.chmod(mode)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source/name, dest)
            dest.chmod(mode)
    print(f'Applied {len(operations)} changes. Backup: {backup}. Review git diff before committing.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    args = parser.parse_args()
    apply(args.source, args.target, args.backup)


if __name__ == '__main__':
    main()
