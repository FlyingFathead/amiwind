#!/usr/bin/env python3
"""Prerendered store: finished stage outputs kept by version and area, reused by fingerprint.

A thin layer on the stage cache (tools/build_cache.py, docs/BUILD_PROFILE.md). The cache
fingerprints every stage and records a manifest of the files it wrote; `--reuse-from RUN`
reuses unchanged stages of ONE earlier run. The store keeps the same manifests and files of
chosen stages across runs and workspaces, in folders a person can browse:

    STORE/chim/<CHIM version>/<world format>/<areas>/<fingerprint>/   CHIM worlds and frame maps
    STORE/interiors/<fingerprint>/                                   converted interior maps
    STORE/legacy/<AmiWind version>/<stage>/<fingerprint>/            region and town maps
    STORE/stages/<AmiWind version>/<stage>/<fingerprint>/            any other stage (--prerendered-stages)

Each entry holds receipt.json (stage, versions, source and builder commit, input digest,
size, created), manifest.json (the stage's output manifest) and files/ (the outputs, at their
paths in the run folder). STORE/index.json lists the entries; STORE/usage.jsonl records every
build that stored or used one. The version folders are for people; the fingerprint alone
decides reuse, so an entry is found wherever it sits.

A build with `tools/build.py --prerendered DIR`:
  * reads: a stage that --reuse-from does not reuse and whose fingerprint has an entry is
    applied from the entry like a reused stage (every SHA-256 verified while copying; any
    doubt runs the stage). The fingerprint covers the stage's command, the code it can reach,
    the game inputs, tools, environment and the fingerprints of every stage it depends on.
  * writes: each chosen stage is copied aside when it passes; the copies become entries only
    when the whole build passed (every later gate included). A failed or cancelled build
    stores nothing. Release candidates and finals write but do not read (from-scratch rule).

Commands (the files never leave the store; deleting entries is the owner's decision):
  prerendered.py list DIR                 entries, sizes, ages and the builds that used them
  prerendered.py verify DIR [--jobs N]    SHA-256 of every stored file against its manifest
  prerendered.py prune DIR [--days N]     report removal candidates (superseded, unused); deletes nothing
  prerendered.py import DIR RUN --source CHECKOUT [--stages ...]
                                          store the passed stages of an earlier run, fingerprinted
                                          with CHECKOUT, which must be the code that built RUN
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import contextlib
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'amiwind-prerendered-v1'
INDEX = 'index.json'
USAGE = 'usage.jsonl'
PENDING = '.pending'
RECEIPT = 'receipt.json'
MANIFEST = 'manifest.json'
FILES = 'files'
ACTIONS = ('list', 'verify', 'prune')
# Stages stored by default: the heavy per-area outputs. Any other reusable stage on request.
INTERIOR_STAGES = ('interior', 'balmora-interiors')
LEGACY_STAGES = ('balmora', 'area', 'world-terrain', 'world-scenery', 'world-flora')
DEFAULT_STAGES = ('chim', 'interior', 'balmora-interiors', 'balmora', 'area', 'town-*')


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_stages(text):
    """'default', 'all' or a comma list of stage names (town-* style patterns allowed)."""
    text = (text or 'default').strip()
    if text in ('default', 'all'):
        return text
    names = [part.strip() for part in text.split(',') if part.strip()]
    if not names or any(not re.fullmatch(r'[a-z0-9_*-]+', name) for name in names):
        raise ValueError(f'--prerendered-stages: "default", "all" or a comma list of stage names, not {text!r}')
    return names


def selected(name, stages):
    patterns = DEFAULT_STAGES if stages in (None, 'default') else None if stages == 'all' else stages
    if patterns is None:
        return True
    return any(name == pattern or (pattern.endswith('*') and name.startswith(pattern[:-1])) for pattern in patterns)


def _part(value):
    return re.sub(r'[^A-Za-z0-9._+-]', '_', str(value)) or 'unknown'


def _option_values(command, option):
    command = [str(part) for part in command]
    return [command[i + 1] for i, part in enumerate(command[:-1]) if part == option]


def entry_folder(name, fingerprint, metadata, command):
    """The entry's path in the store (relative): versions and area for people, then the fingerprint."""
    version = _part(metadata.get('runtime_version') or 'unknown')
    if name == 'chim':
        areas = '+'.join(_part(area) for area in _option_values(command, '--area')) or 'world'
        return '/'.join(('chim', _part(metadata.get('chim_version') or 'unknown'),
                         _part(metadata.get('world_format') or 'unknown'), areas, fingerprint))
    if name in INTERIOR_STAGES:
        return f'interiors/{fingerprint}'
    if name in LEGACY_STAGES or name.startswith('town-'):
        return f'legacy/{version}/{_part(name)}/{fingerprint}'
    return f'stages/{version}/{_part(name)}/{fingerprint}'


def _read_head(root):
    """HEAD's commit read from the repository files (for builder images without git); None if unknown."""
    git = Path(root) / '.git'
    try:
        if git.is_file():  # a worktree: "gitdir: PATH"
            git = Path(git.read_text().split(':', 1)[1].strip())
        head = (git / 'HEAD').read_text().strip()
        if not head.startswith('ref: '):
            return head or None
        ref = head[5:]
        for folder in (git, Path((git / 'commondir').read_text().strip()) if (git / 'commondir').is_file() else git):
            folder = folder if folder.is_absolute() else git / folder
            if (folder / ref).is_file():
                return (folder / ref).read_text().strip()
            packed = folder / 'packed-refs'
            if packed.is_file():
                for line in packed.read_text().splitlines():
                    if line.endswith(' ' + ref):
                        return line.split()[0]
    except (OSError, IndexError):
        return None
    return None


def git_commit(root):
    """'<commit>' or '<commit>+changes' of the checkout ROOT ('<commit>' unchecked without git); None if unknown."""
    try:
        head = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True,
                              timeout=30, check=True).stdout.strip()
        dirty = subprocess.run(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=no'],
                               capture_output=True, text=True, timeout=60, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return _read_head(root)
    return head + ('+changes' if dirty else '') if head else None


@contextlib.contextmanager
def locked(folder):
    """An exclusive lock on FOLDER/.lock while the index is rewritten (POSIX; no-op elsewhere)."""
    folder.mkdir(parents=True, exist_ok=True)
    try:
        import fcntl
    except ImportError:
        yield
        return
    with open(folder / '.lock', 'a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


class Store:
    def __init__(self, root):
        self.root = Path(root)

    def entries(self):
        """{fingerprint: entry folder} for every complete entry (receipt + manifest), by scanning."""
        found = {}
        if not self.root.is_dir():
            return found
        for folder, directories, names in os.walk(self.root):
            here = Path(folder)
            if here == self.root:
                directories[:] = [d for d in directories if d != PENDING]
            if RECEIPT in names and MANIFEST in names:
                directories[:] = []
                found[here.name] = here
            elif FILES in directories and here != self.root:
                directories.remove(FILES)
        return found

    def find(self, fingerprint):
        """The entry folder of FINGERPRINT, or None. The index is a shortcut; a scan is the truth."""
        try:
            relative = json.loads((self.root / INDEX).read_text())['entries'][fingerprint]['path']
            folder = self.root / relative
            if (folder / RECEIPT).is_file() and (folder / MANIFEST).is_file():
                return folder
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return self.entries().get(fingerprint)

    def receipt(self, folder):
        return json.loads((Path(folder) / RECEIPT).read_text())

    def manifest(self, folder):
        return json.loads((Path(folder) / MANIFEST).read_text())

    def usage(self):
        rows = []
        try:
            lines = (self.root / USAGE).read_text().splitlines()
        except OSError:
            return rows
        for line in lines:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
        return rows

    def log(self, rows):
        if not rows:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        with open(self.root / USAGE, 'a') as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + '\n')

    def reindex(self):
        """Rewrite index.json from the entries on disk (under the store lock)."""
        with locked(self.root):
            entries = {}
            for fingerprint, folder in sorted(self.entries().items()):
                try:
                    receipt = self.receipt(folder)
                except (OSError, ValueError):
                    continue
                entries[fingerprint] = {'path': folder.relative_to(self.root).as_posix(), 'stage': receipt.get('stage'),
                                        'kind': receipt.get('kind'), 'size': receipt.get('size'),
                                        'files': receipt.get('files'), 'created': receipt.get('created'),
                                        'versions': receipt.get('versions')}
            index = {'schema': SCHEMA, 'updated': now(), 'entries': entries}
            temporary = self.root / (INDEX + '.tmp')
            temporary.write_text(json.dumps(index, indent=1, sort_keys=True) + '\n')
            temporary.replace(self.root / INDEX)
        return index


# --------------------------------------------------------------------------
# Reading (tools/build_cache.prepare)

def plan_hits(steps, fingerprints, problems, dependencies, config, taken=()):
    """({stage: reuse plan from the store}, record for build-state.json)."""
    import build_cache
    store = Store(config['dir'])
    record = {'dir': str(store.root), 'read': bool(config.get('read')), 'write': bool(config.get('write')),
              'stages': config.get('stages') or 'default', 'hits': {}, 'misses': {},
              'unfingerprinted': sorted(name for name, issues in problems.items() if issues),
              'source_commit': config.get('source_commit'), 'builder_commit': config.get('builder_commit')}
    if config.get('read_refused'):
        record['read_refused'] = config['read_refused']
    hits = {}
    if not config.get('read'):
        return hits, record
    entries = store.entries() if store.root.is_dir() else {}
    lineage = {}

    def ancestors(name):
        if name not in lineage:
            found = set()
            for dep in dependencies.get(name, ()):
                found |= {dep} | ancestors(dep)
            lineage[name] = found
        return lineage[name]

    for name, _ in steps:
        if name in taken:
            continue
        if name in build_cache.NON_REUSABLE:
            record['misses'][name] = build_cache.NON_REUSABLE[name]
            continue
        if problems.get(name):
            record['misses'][name] = '; '.join(problems[name])
            continue
        folder = entries.get(fingerprints[name])
        if folder is None:
            record['misses'][name] = 'not stored'
            continue
        try:
            manifest = store.manifest(folder)
        except (OSError, ValueError) as exc:
            record['misses'][name] = f'entry {folder} unreadable: {exc}'
            continue
        if (manifest.get('schema') != build_cache.MANIFEST_SCHEMA or manifest.get('status') != 'complete'
                or manifest.get('fingerprint') != fingerprints[name] or not manifest.get('reusable')):
            record['misses'][name] = f'entry {folder} is not a complete reusable manifest for this fingerprint'
            continue
        relative = folder.relative_to(store.root).as_posix()
        # Same plan shape as --reuse-from (build_cache.plan_reuse), applied by build_cache.apply_stage.
        # The fingerprint already covers every stage this one depends on; the stage's run-folder
        # inputs are checked against the stored hashes before anything is copied.
        hits[name] = {'from': str(folder / FILES), 'prerendered': str(folder), 'fingerprint': fingerprints[name],
                      'files': manifest['files'], 'links': manifest.get('links', {}),
                      'directories': manifest.get('directories', []), 'deleted': manifest.get('deleted', []),
                      'deleted_directories': manifest.get('deleted_directories', []),
                      'inputs': manifest.get('inputs', {}), 'ancestors': sorted(ancestors(name)),
                      'skipped_later_replaced': 0, 'rebuild_hazard': [], 'rebuild_hazard_count': 0}
        record['hits'][name] = relative
    if record['read']:
        print(f"Prerendered store {store.root}: {len(hits)} of {len(steps)} stages from stored entries.", flush=True)
        for name in hits:
            print(f'  stored  {name} ({record["hits"][name]})', flush=True)
    return hits, record


# --------------------------------------------------------------------------
# Writing (tools/build_cache.Recorder)

class Writer:
    """Copies chosen passed stages aside as they finish; commits them when the build passed."""

    def __init__(self, run, metadata, config, components=None, summary=True):
        self.run = Path(run)
        self.components = components  # fingerprint components; default: the run's profile/fingerprints.json
        self.summary = summary        # write RUN/profile/prerendered.json
        self.metadata = metadata
        self.config = config
        self.store = Store(config['dir'])
        self.write = bool(config.get('write'))
        self.stages = config.get('stages') or 'default'
        self.unfingerprinted = set(config.get('unfingerprinted') or ())
        self.hits = dict(config.get('hits') or {})
        self.pending = self.store.root / PENDING / f'{_part(self.run.name)}-{uuid.uuid4().hex[:12]}'
        self.captured = {}
        self.skipped = {}
        self.commands = {}
        for name, entry in ((metadata.get('stage_cache') or {}).get('reused') or {}).items():
            self.commands[name] = entry.get('original_command')

    def capture(self, name, manifest, command=None):
        fingerprint = manifest.get('fingerprint')
        if not self.write or not selected(name, self.stages):
            return
        if name in self.hits:
            return  # applied from the store: already an entry
        if not fingerprint or name in self.unfingerprinted:
            self.skipped[name] = 'fingerprint incomplete'
            return
        if not manifest.get('reusable'):
            self.skipped[name] = 'outputs not reusable: ' + '; '.join(manifest.get('reasons') or ['unknown'])
            return
        if self.store.find(fingerprint) is not None:
            self.skipped[name] = 'already stored'
            return
        began = time.monotonic()
        target = self.pending / name / FILES
        target.mkdir(parents=True, exist_ok=True)
        for relative, info in sorted(manifest['files'].items()):
            source, destination = self.run / relative, target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            with open(source, 'rb') as reader, open(destination, 'wb') as writer:
                for block in iter(lambda: reader.read(1024 * 1024), b''):
                    digest.update(block)
                    writer.write(block)
            if digest.hexdigest() != info['sha256']:
                shutil.rmtree(self.pending / name, ignore_errors=True)
                self.skipped[name] = f'{relative} changed while it was copied'
                return
            os.chmod(destination, info.get('mode', 0o644) & ~0o222)
        self.captured[name] = {'seconds': round(time.monotonic() - began, 3), 'command': command}
        print(f"Prerendered store: {name} copied aside ({manifest['counts']['files']} files, "
              f"{manifest['counts']['bytes']:,} bytes); stored when the build passes.", flush=True)

    def _receipt(self, name, manifest, folder, components):
        meta = self.metadata
        size = sum(info['size'] for info in manifest['files'].values())
        return {'schema': SCHEMA, 'stage': name, 'kind': folder.split('/')[0], 'fingerprint': manifest['fingerprint'],
                'cache_schema': (meta.get('stage_cache') or {}).get('schema'),
                'created': now(), 'run': self.run.name,
                'versions': {'amiwind': meta.get('runtime_version'), 'builder': meta.get('builder'),
                             'chim': meta.get('chim_version'), 'world_format': meta.get('world_format')},
                'source_commit': self.config.get('source_commit'), 'builder_commit': self.config.get('builder_commit'),
                'inputs_digest': digest_json(meta.get('input_sha256') or {}),
                'source_digest': digest_json(meta.get('source_sha256') or {}),
                'size': size, 'files': len(manifest['files']), 'adopted': self.config.get('adopted'),
                'fingerprint_components': components}

    def finish(self, receipt, manifests):
        """Commit the captured stages if the build passed; otherwise store nothing."""
        status = receipt.get('status')
        stored, rows = {}, []
        stamp = now()
        fallback = self.run / 'profile' / 'reuse-fallback'
        for name, relative in sorted(self.hits.items()):
            if not (fallback / f'{name}.txt').is_file():
                rows.append({'time': stamp, 'action': 'used', 'stage': name, 'path': relative, 'run': str(self.run),
                             'status': status})
        if status != 'passed':
            shutil.rmtree(self.pending, ignore_errors=True)
            if self.captured:
                print(f'Prerendered store: nothing stored, the build {status} ({len(self.captured)} copies discarded).',
                      flush=True)
            self.skipped.update({name: f'build {status}' for name in self.captured})
            self.captured = {}
        components = self.components
        if components is None:
            try:
                components = json.loads((self.run / 'profile' / 'fingerprints.json').read_text())
            except (OSError, ValueError):
                components = {}
        for name in sorted(self.captured):
            manifest = manifests.get(name) or {}
            if not manifest.get('reusable'):
                self.skipped[name] = 'outputs not reusable: ' + '; '.join(manifest.get('reasons') or ['unknown'])
                continue
            command = self.captured[name].get('command') or self.commands.get(name) or receipt_command(receipt, name)
            relative = entry_folder(name, manifest['fingerprint'], self.metadata, command or [])
            final = self.store.root / relative
            source = self.pending / name
            (source / MANIFEST).write_text(json.dumps(manifest, separators=(',', ':')) + '\n')
            (source / RECEIPT).write_text(json.dumps(self._receipt(name, manifest, relative, components.get(name)),
                                                     indent=1, sort_keys=True) + '\n')
            if self.store.find(manifest['fingerprint']) is not None:
                self.skipped[name] = 'already stored'
                continue
            final.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.rename(source, final)
            except OSError as exc:
                self.skipped[name] = f'not moved into place: {exc}'
                continue
            stored[name] = relative
            rows.append({'time': stamp, 'action': 'stored', 'stage': name, 'path': relative, 'run': str(self.run),
                         'status': status})
        shutil.rmtree(self.pending, ignore_errors=True)
        try:
            self.pending.parent.rmdir()
        except OSError:
            pass
        if stored:
            self.store.reindex()
        self.store.log(rows)
        summary = {'schema': SCHEMA, 'dir': str(self.store.root), 'status': status, 'used': self.hits,
                   'stored': stored, 'not_stored': self.skipped,
                   'capture_seconds': {name: info['seconds'] for name, info in self.captured.items()}}
        if self.summary:
            try:
                (self.run / 'profile' / 'prerendered.json').write_text(json.dumps(summary, indent=1, sort_keys=True)
                                                                       + '\n')
            except OSError:
                pass
        for name, relative in stored.items():
            print(f'Prerendered store: stored {name} as {relative}', flush=True)
        return summary


def receipt_command(receipt, name):
    for step in receipt.get('steps', []):
        if step.get('name') == name:
            return step.get('command')
    return None


def configure(directory, version, allow_release=False, stages='default', write=True, root=ROOT):
    """The 'prerendered' config for build_cache.prepare: reads only for -devN builds (or allowed)."""
    directory = Path(directory).expanduser().resolve()
    config = {'dir': str(directory), 'read': True, 'write': write, 'stages': parse_stages(stages)}
    if not (re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]+', version) or allow_release):
        config['read'] = False
        config['read_refused'] = (f'{version} is a release candidate or final: stored entries are not used '
                                  '(from-scratch rule); passed stages are still stored')
        print('Prerendered store: ' + config['read_refused'] + '.', flush=True)
    commit = git_commit(root)
    config.update(source_commit=commit, builder_commit=commit)
    return config


# --------------------------------------------------------------------------
# list / verify / prune / import

def _age(created):
    try:
        then = datetime.strptime(created, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None
    return (datetime.now(timezone.utc) - then).total_seconds() / 86400


def rows(store):
    usage = store.usage()
    result = []
    for fingerprint, folder in sorted(store.entries().items(), key=lambda item: str(item[1])):
        try:
            receipt = store.receipt(folder)
        except (OSError, ValueError):
            receipt = {}
        relative = folder.relative_to(store.root).as_posix()
        used = [row for row in usage if row.get('path') == relative and row.get('action') == 'used']
        made = [row for row in usage if row.get('path') == relative and row.get('action') == 'stored']
        # Position of the entry's latest event in the append-only usage log: orders entries created or
        # used within the same second (timestamps have one-second resolution).
        last_event = max((index for index, row in enumerate(usage) if row.get('path') == relative
                          and row.get('action') in ('used', 'stored')), default=-1)
        result.append({'path': relative, 'stage': receipt.get('stage'), 'size': receipt.get('size') or 0,
                       'files': receipt.get('files'), 'created': receipt.get('created'),
                       'age_days': _age(receipt.get('created')), 'uses': len(used),
                       'used_by': sorted({Path(row['run']).name for row in used}),
                       'stored_by': sorted({Path(row['run']).name for row in made}),
                       'last_used': max((row['time'] for row in used), default=None),
                       'adopted': receipt.get('adopted'), 'fingerprint': fingerprint, 'last_event': last_event})
    return result


def action_list(store, as_json=False):
    table = rows(store)
    if as_json:
        print(json.dumps(table, indent=1))
        return 0
    total = sum(row['size'] for row in table)
    print(f'Prerendered store {store.root}: {len(table)} entries, {total / 1e6:,.1f} MB')
    for row in table:
        age = 'age ?' if row['age_days'] is None else f"{row['age_days']:.1f} d old"
        used = ', '.join(row['used_by'][-3:]) if row['used_by'] else 'never used'
        print(f"  {row['path']}\n      {row['stage']}: {row['size'] / 1e6:,.1f} MB, {row['files']} files, {age}, "
              f"used {row['uses']}x ({used}); stored by {', '.join(row['stored_by']) or row['adopted'] or '?'}")
    pending = store.root / PENDING
    if pending.is_dir() and any(pending.iterdir()):
        print(f'  {PENDING}/: copies of builds still running or stopped ({len(list(pending.iterdir()))} folders)')
    return 0


def action_verify(store, jobs=None):
    entries = store.entries()
    work, broken = [], {}
    for fingerprint, folder in sorted(entries.items(), key=lambda item: str(item[1])):
        try:
            manifest = store.manifest(folder)
            receipt = store.receipt(folder)
        except (OSError, ValueError) as exc:
            broken[str(folder)] = [f'unreadable receipt or manifest: {exc}']
            continue
        if manifest.get('fingerprint') != fingerprint or receipt.get('fingerprint') != fingerprint:
            broken.setdefault(str(folder), []).append('fingerprint does not match its folder')
        for relative, info in manifest['files'].items():
            work.append((folder, relative, info))

    def check(item):
        folder, relative, info = item
        path = folder / FILES / relative
        try:
            if path.stat().st_size != info['size']:
                return folder, relative, 'size differs'
            return folder, relative, None if sha256_file(path) == info['sha256'] else 'SHA-256 differs'
        except OSError:
            return folder, relative, 'missing'

    with ThreadPoolExecutor(max_workers=max(1, jobs or min(8, os.cpu_count() or 1))) as pool:
        for folder, relative, problem in pool.map(check, work):
            if problem:
                broken.setdefault(str(folder), []).append(f'{relative}: {problem}')
    print(f'Prerendered store {store.root}: {len(entries)} entries, {len(work)} files checked; '
          f'{len(broken)} damaged.')
    for folder, problems in sorted(broken.items()):
        print(f'  DAMAGED {folder}: {problems[0]}' + (f' (and {len(problems) - 1} more)' if len(problems) > 1 else ''))
    return 1 if broken else 0


def action_prune(store, days=14):
    """Report removal candidates; never deletes (the owner decides)."""
    table = rows(store)
    groups = {}
    for row in table:
        groups.setdefault((row['path'].rsplit('/', 1)[0], row['stage']), []).append(row)
    candidates = []
    recent = datetime.now(timezone.utc).timestamp() - days * 86400

    def used_recently(row):
        try:
            when = datetime.strptime(row['last_used'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return False
        return when.timestamp() > recent

    for (group, stage), members in groups.items():
        # The entry last created or used stays; another one of the same stage, area and version is a
        # candidate unless a build used it in the last DAYS days (another line may still need it).
        # Ties (same second) go by the usage log, never by folder name: entry folders are named by
        # fingerprint, so a name order would change whenever fingerprints do.
        members.sort(key=lambda row: (max(row['created'] or '', row['last_used'] or ''), row['last_event']))
        for row in members[:-1]:
            if not used_recently(row):
                candidates.append((row, f'superseded: a newer {stage} entry in {group}/'))
    for row in table:
        if row['age_days'] is not None and row['age_days'] > days and not row['last_used'] and \
                not any(row is other for other, _ in candidates):
            candidates.append((row, f'never used, older than {days} days'))
    pending = store.root / PENDING
    stale = [path for path in (pending.iterdir() if pending.is_dir() else [])
             if time.time() - path.stat().st_mtime > 86400]
    total = sum(row['size'] for row, _ in candidates)
    print(f'Prerendered store {store.root}: {len(candidates)} removal candidates, {total / 1e6:,.1f} MB '
          '(nothing is deleted; remove a folder by hand if you agree, then run list to refresh the index).')
    for row, reason in candidates:
        print(f"  {row['path']}  {row['size'] / 1e6:,.1f} MB  {reason}")
    for path in stale:
        print(f'  {path.relative_to(store.root).as_posix()}  copies of a build that stopped over a day ago')
    return 0


def action_import(store, run, source, stages='default', python_check=True, source_commit=None):
    """Store the passed stages of RUN, fingerprinted with SOURCE (the checkout that built RUN).

    Refused unless SOURCE has the content the run recorded (its source_sha256), the run used
    this Python, and each stage's outputs are still in RUN with their recorded SHA-256 (a file
    a later stage of RUN replaced cannot be stored from it).
    """
    import build_cache
    run, source = Path(run).resolve(), Path(source).resolve()
    state = json.loads((run / 'build-state.json').read_text())
    if state.get('status') != 'passed':
        raise ValueError(f'{run.name} did not pass ({state.get("status")}): nothing is stored from it')
    if python_check and state.get('python') != sys.version:
        raise ValueError(f'{run.name} ran on Python {state.get("python")!r}, this is {sys.version!r}: '
                         'fingerprints would differ; import with the builder that made the run')
    recorded = state.get('source_sha256') or {}
    differ = [path for path, digest in sorted(recorded.items())
              if not (source / path).is_file() or sha256_file(source / path) != digest]
    if not recorded or differ:
        raise ValueError(f'{source} is not the code that built {run.name}: '
                         + (f'{len(differ)} files differ (first: {differ[0]})' if differ else 'no source record'))
    steps, _ = build_cache.old_run_steps(run, source)
    old = {}
    try:
        old = json.loads((run / 'profile' / 'fingerprints.json').read_text())
    except (OSError, ValueError):
        pass
    environment = {}
    for components in old.values():
        environment.update({key: value for key, value in (components.get('environment') or {}).items()
                            if key.startswith(build_cache.ENV_PREFIX) and value is not None})
    saved = {key: value for key, value in os.environ.items() if key.startswith(build_cache.ENV_PREFIX)}
    try:
        for key in saved:
            del os.environ[key]
        os.environ.update(environment)
        index = build_cache.SourceIndex(source, scope=(state.get('stage_cache') or {}).get('scope') or 'symbols')
        fingerprints, components, problems, _ = build_cache.fingerprint_steps(steps, run, state, index)
    finally:
        for key in [key for key in os.environ if key.startswith(build_cache.ENV_PREFIX)]:
            del os.environ[key]
        os.environ.update(saved)
    statuses = {step['name']: step.get('status') for step in state.get('steps', [])}
    manifests = {name: build_cache.load_manifest(run, name) for name, _ in steps}
    writers = {}
    for name in sorted((n for n in manifests if manifests[n]), key=lambda n: (manifests[n]['window'][1] or 0, n)):
        for path in (*manifests[name]['files'], *manifests[name]['links'], *manifests[name]['deleted']):
            writers.setdefault(path, []).append(name)
    meta = dict(state, stage_cache={'schema': build_cache.CACHE_SCHEMA, 'fingerprints': fingerprints})
    config = {'dir': str(store.root), 'write': True, 'stages': parse_stages(stages) if isinstance(stages, str) else stages,
              'source_commit': source_commit or git_commit(source), 'builder_commit': git_commit(ROOT),
              'adopted': f'imported from {run.name} with the checkout it was built from'}
    # The run is only read: the summary goes to standard output, nothing is written into RUN.
    writer = Writer(run, meta, config, components=components, summary=False)
    adopted = {}
    for name, command in steps:
        if not selected(name, writer.stages):
            continue
        manifest = manifests.get(name)
        reason = None
        if statuses.get(name) != 'passed':
            reason = f'not passed in {run.name}'
        elif name in build_cache.NON_REUSABLE:
            reason = build_cache.NON_REUSABLE[name]
        elif problems.get(name):
            reason = '; '.join(problems[name])
        elif not manifest or manifest.get('status') != 'complete' or not manifest.get('reusable'):
            reason = 'no complete reusable output manifest'
        else:
            later = [writers[path][writers[path].index(name) + 1:] for path in manifest['files'] if path in writers]
            replaced = sorted({stage for chain in later for stage in chain})
            if replaced:
                reason = 'outputs replaced later in the run by ' + ', '.join(replaced)
        if reason:
            writer.skipped[name] = reason
            continue
        adopted[name] = dict(manifest, fingerprint=fingerprints[name])
        writer.capture(name, adopted[name], command)
    summary = writer.finish({'status': 'passed', 'steps': state.get('steps', [])}, adopted)
    for name, why in sorted(summary['not_stored'].items()):
        print(f'  not stored {name}: {why}')
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    listing = sub.add_parser('list', help='entries, sizes, ages and the builds that used them')
    listing.add_argument('dir', type=Path)
    listing.add_argument('--json', action='store_true')
    verify = sub.add_parser('verify', help='SHA-256 of every stored file against its manifest')
    verify.add_argument('dir', type=Path)
    verify.add_argument('--jobs', type=int)
    prune = sub.add_parser('prune', help='report removal candidates (deletes nothing)')
    prune.add_argument('dir', type=Path)
    prune.add_argument('--days', type=int, default=14)
    imp = sub.add_parser('import', help='store the passed stages of an earlier run (see the module help)')
    imp.add_argument('dir', type=Path)
    imp.add_argument('run', type=Path)
    imp.add_argument('--source', type=Path, required=True, help='the checkout that built RUN')
    imp.add_argument('--stages', default='default', help='default, all or a comma list of stage names')
    imp.add_argument('--source-commit', help='commit label recorded in the receipts (default: git of --source)')
    args = parser.parse_args(argv)
    store = Store(args.dir)
    if args.action == 'list':
        if store.root.is_dir():
            store.reindex()
        return action_list(store, args.json)
    if args.action == 'verify':
        return action_verify(store, args.jobs)
    if args.action == 'prune':
        return action_prune(store, args.days)
    action_import(store, args.run, args.source, args.stages, source_commit=args.source_commit)
    return 0


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'tools'))
    raise SystemExit(main())
