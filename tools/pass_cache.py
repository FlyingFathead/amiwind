# SPDX-License-Identifier: GPL-3.0-only
"""Content-addressed results of the image step's per-map passes (development builds).

A per-map pass (BSP optimizer, hidden-surface cull) turns one map's bytes into
new bytes and a receipt row, and nothing else: its result depends only on the
input bytes, the pass options and the pass's own source code. A development
build that changed a few maps therefore need not run the pass again on the
others. The key is

    SHA-256(pass name, pass options, SHA-256 of the pass's repository sources
            (its module and every repository module and data file it reads,
            transitively, build_cache.SourceIndex), input map SHA-256)

and the value is the receipt row plus the output bytes when they differ from
the input. A stored output is checked against its recorded SHA-256 when it is
read; a damaged entry is ignored and the pass runs. Entries are written
atomically, so builds can share the folder.

The builder sets AMIWIND_PASS_CACHE to WORKSPACE/cache/image-passes for
development (-devN) builds only: release candidates and finals run every pass
on every map (build.py; the from-scratch gate). Without the variable, or with
it set to "off", nothing is read or written. Outputs are byte-identical with
and without the cache (tests/test_pass_cache.py; BUILD-IMAGE-NOT-INCREMENTAL-33).
"""
import hashlib
import json
import os
from pathlib import Path

ENV = 'AMIWIND_PASS_CACHE'
FORMAT = 'AmiWind image pass cache 1'
ROOT = Path(__file__).resolve().parents[1]


def folder():
    """The cache folder, or None when the cache is off."""
    value = os.environ.get(ENV, '')
    if not value or value.lower() == 'off':
        return None
    return Path(value)


def setting(version, workspace):
    """The builder's value for ENV: the workspace cache for development (-devN)
    versions, "off" for release candidates and finals (every pass on every map)."""
    import re
    if re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]+', version):
        return str(Path(workspace).resolve() / 'cache' / 'image-passes')
    return 'off'


_DIGESTS = {}


def source_digest(*scripts):
    """SHA-256 of the repository sources the given pass modules read, transitively
    (computed once per process: the repository index hashes every source file)."""
    key = tuple(str(Path(script).resolve()) for script in scripts)
    if key not in _DIGESTS:
        _DIGESTS[key] = _source_digest(scripts)
    return _DIGESTS[key]


def _source_digest(scripts):
    from build_cache import SourceIndex
    index = SourceIndex(ROOT)
    parts = []
    for script in scripts:
        value, _, uncertain = index.digest(Path(script).resolve())
        parts.append([str(Path(script).name), value, uncertain])
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


class PassCache:
    """One pass's view of the cache; picklable, so pool workers get it in their task."""

    def __init__(self, name, options, sources, root=None):
        self.name = name
        self.options = options
        self.sources = sources
        self.root = None if root is None else str(root)

    @classmethod
    def open(cls, name, options, *scripts):
        """None when the cache is off; otherwise the pass's cache (sources hashed once, here)."""
        root = folder()
        if root is None:
            return None
        return cls(name, options, source_digest(*scripts), root)

    def key(self, input_sha256):
        return hashlib.sha256(json.dumps([FORMAT, self.name, self.options, self.sources, input_sha256],
                                         sort_keys=True).encode()).hexdigest()

    def _paths(self, input_sha256):
        key = self.key(input_sha256)
        base = Path(self.root) / self.name / key[:2]
        return base / (key + '.json'), base / (key + '.bin')

    def load(self, input_sha256):
        """(row, output bytes or None) recorded for this input, or None."""
        meta_path, blob_path = self._paths(input_sha256)
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            if meta.get('format') != FORMAT or meta.get('input_sha256') != input_sha256:
                return None
            output = None
            if meta.get('output_sha256') is not None:
                output = blob_path.read_bytes()
                if hashlib.sha256(output).hexdigest() != meta['output_sha256']:
                    return None
            return meta['row'], output
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def store(self, input_sha256, row, output=None):
        """Record a result (output None: the pass left the map unchanged). Never fails a build."""
        meta_path, blob_path = self._paths(input_sha256)
        try:
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            suffix = f'.{os.getpid()}.tmp'
            if output is not None:
                partial = blob_path.with_name(blob_path.name + suffix)
                partial.write_bytes(output)
                os.replace(partial, blob_path)
            meta = {'format': FORMAT, 'pass': self.name, 'input_sha256': input_sha256,
                    'output_sha256': None if output is None else hashlib.sha256(output).hexdigest(),
                    'row': row}
            partial = meta_path.with_name(meta_path.name + suffix)
            # Key order kept: rows go into receipts exactly as the pass made them.
            partial.write_text(json.dumps(meta) + '\n', encoding='utf-8', newline='\n')
            os.replace(partial, meta_path)
        except (OSError, TypeError, ValueError):
            pass
