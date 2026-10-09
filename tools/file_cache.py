#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Content-addressed asset pool with per-file reuse keys for converter outputs (development builds).

Files are stored once, by their own SHA-256, in ROOT/objects/SHA[:2]/SHA (the pool), whatever
stage, build or version made them. A converter that wants to reuse its work looks up a reuse
key made of everything an output's bytes depend on: the source file's SHA-256, the conversion
settings, the converter programs (binary SHA-256 and version text) and the source of the
conversion code. The key file, ROOT/keys/NAMESPACE/KEY[:2]/KEY.json, names the output's SHA-256
and the converter's own facts about it. A later build that needs the same output copies it from
the pool, verified against that SHA-256; a missing or damaged object is converted again and
stored again. So a changed input converts only the files it touches. Without a pool folder
nothing changes: every file is converted (the pool is an addition, never the only way). Nothing
is ever deleted from the pool by the builder.

Writes go through a temporary name and a rename, so builds sharing one pool never see a partial
file.
"""
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading

SCHEMA = 'amiwind-asset-pool-v1'


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def program_identity(program):
    """{'sha256', 'version'} of an external program (None values when it cannot be read)."""
    found = shutil.which(str(program)) or str(program)
    identity = {'sha256': None, 'version': None}
    try:
        identity['sha256'] = sha256_file(found)
    except OSError:
        pass
    try:
        result = subprocess.run([found, '-version'], capture_output=True, text=True, timeout=60)
        identity['version'] = result.stdout
    except (OSError, subprocess.SubprocessError):
        pass
    return identity


def code_identity(*objects):
    """SHA-256 over the source of the given functions or modules (the conversion code)."""
    return digest_json([inspect.getsource(item) for item in objects])


class FileCache:
    """One namespace of reuse keys over the shared pool; ROOT None = disabled (every lookup misses)."""

    def __init__(self, root, namespace, identity):
        self.pool = Path(root) if root else None
        self.root = self.pool / 'keys' / namespace if root else None
        self.identity = identity
        self.counts = {'hits': 0, 'misses': 0, 'stored': 0, 'rejected': 0}
        self._lock = threading.Lock()

    @property
    def enabled(self):
        return self.pool is not None

    def _count(self, name):
        with self._lock:
            self.counts[name] += 1

    def key(self, source_sha256, settings):
        return digest_json({'schema': SCHEMA, 'source_sha256': source_sha256, 'settings': settings,
                            'identity': self.identity})

    def _key_path(self, key):
        return self.root / key[:2] / f'{key}.json'

    def object_path(self, digest):
        return self.pool / 'objects' / digest[:2] / digest

    def fetch(self, key, target):
        """Copy the pooled output of KEY to TARGET when present and intact; its recorded facts, or None."""
        if not self.enabled:
            return None
        try:
            meta = json.loads(self._key_path(key).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            self._count('misses')
            return None
        if meta.get('schema') != SCHEMA or meta.get('key') != key or not meta.get('sha256'):
            self._count('misses')
            return None
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.pool-tmp')
        try:
            digest = hashlib.sha256()
            with open(self.object_path(meta['sha256']), 'rb') as reader, open(temporary, 'wb') as writer:
                for block in iter(lambda: reader.read(1 << 20), b''):
                    digest.update(block)
                    writer.write(block)
        except OSError:
            temporary.unlink(missing_ok=True)
            self._count('misses')
            return None
        if digest.hexdigest() != meta['sha256']:
            # A damaged object is never used: convert again (store writes a good copy back).
            temporary.unlink(missing_ok=True)
            self._count('rejected')
            return None
        os.replace(temporary, target)
        self._count('hits')
        return meta.get('facts') or {}

    def store(self, key, path, facts=None):
        """Pool a converted file (once per content) and point KEY at it; a pool that cannot be written is skipped."""
        if not self.enabled:
            return False
        suffix = f'.{os.getpid()}.{threading.get_ident()}.tmp'
        key_path = self._key_path(key)
        temporaries = []
        try:
            digest = sha256_file(path)
            blob = self.object_path(digest)
            intact = False
            try:
                intact = blob.is_file() and sha256_file(blob) == digest
            except OSError:
                pass
            if not intact:
                blob.parent.mkdir(parents=True, exist_ok=True)
                temporaries.append(str(blob) + suffix)
                shutil.copyfile(path, temporaries[-1])
                if sha256_file(temporaries[-1]) != digest:
                    raise OSError('pool copy does not match its source')
                os.replace(temporaries[-1], blob)
            meta = {'schema': SCHEMA, 'key': key, 'sha256': digest, 'bytes': Path(path).stat().st_size,
                    'facts': facts or {}}
            key_path.parent.mkdir(parents=True, exist_ok=True)
            temporaries.append(str(key_path) + suffix)
            # FACTS keep their order: a converter may write them back as its own receipt.
            Path(temporaries[-1]).write_text(json.dumps(meta) + '\n', encoding='utf-8')
            os.replace(temporaries[-1], key_path)
        except OSError as error:
            for leftover in temporaries:
                Path(leftover).unlink(missing_ok=True)
            print(f'[warning] Asset pool not written ({error}); the build continues.', flush=True)
            return False
        self._count('stored')
        return True


def write_report(path, stage, counts):
    """Per-file cache hits and misses for the build summary (never part of the stage outputs)."""
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({'stage': stage, 'groups': counts}, indent=1, sort_keys=True) + '\n')
    for group, row in counts.items():
        print(f"File cache ({group}): {row['hit']} reused, {row['miss']} converted"
              + ('' if row.get('enabled') else ' (no cache folder)'), flush=True)
