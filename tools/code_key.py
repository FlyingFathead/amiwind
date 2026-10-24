# SPDX-License-Identifier: GPL-3.0-only
"""Exact code keys for the per-unit caches (CHIM build units, NPC gallery models).

A per-unit cache key holds a hash of the code that makes the unit. Hashing whole source files (or everything a
tool's main flow can reach) rekeys every unit when any function in those files changes, also a function the unit
never runs: one collision fix in tools/mesh_geometry.py rebuilt every CHIM terrain unit and every gallery model
(BUILD-CACHE-CLOSURE-WIDE-33, BUILD-NPC-GALLERY-REBUILT-46). A code key covers what the unit's worker can reach:

- ENTRIES: [(repository path, function)], the worker function, and ('path', '<top>') for a module whose classes'
  methods run on objects the worker is handed (the reach analysis cannot follow a method called on an argument; a
  class is part of its module's import-time code). Their reach is
  build_cache.SourceIndex.entry_units (scope 'units'): each reached module's import-time code (top format 2) and
  each reached function or class.
- Each reached unit's text is hashed without comments, blank lines and spacing (normalized_text), so a comment edit
  keeps every key; any change to a token still changes it.
- DATA: repository data files named by the caller (whole-file SHA-256), besides those the reached code names.

Never narrower than what runs: Tracer records every repository function a worker runs (sys.monitoring, each code
object once per process); uncovered() names any that the key's reach does not hold. The callers do not store a unit
whose process ran uncovered code (chim.units.run_units, gallery_cache.convert_cached): a key gap costs reuse, never
a stale unit. Python before 3.12 (no sys.monitoring) records nothing; the callers then say so.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tokenize

ROOT = Path(__file__).resolve().parents[1]
# The form of the code keys: part of every key, so a change of form is a change of key.
CODE_KEY_FORM = 'code key 1'
TOP_FORMAT = 2
# Modules that only key, store or schedule units (never change a unit's result): not followed by the reach (their
# own strings name tool scripts, which the reach would follow as scripts) and left out of the coverage check. This
# module is one of build_cache.INSTRUMENTATION_MODULES (never followed, never in a key).
KEY_NEUTRAL = frozenset({'tools/chim/units.py'})
_INDEX = {}
_KEYS = {}


def normalized_text(text):
    """TEXT as its tokens: comments, blank lines and spacing dropped (a comment edit keeps the hash). Lines that
    start with NUL (build_cache's '\\0defaults' rows of import-time code) are kept as they are. Text that does not
    tokenize is kept whole (a stricter key, never a looser one)."""
    rows, chunk = [], []

    def flush():
        if not chunk:
            return
        source = ''.join(chunk)
        chunk.clear()
        try:
            for token in tokenize.generate_tokens(io.StringIO(source).readline):
                if token.type in (tokenize.COMMENT, tokenize.NL, tokenize.ENCODING, tokenize.ENDMARKER):
                    continue
                if token.type in (tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE):
                    rows.append(tokenize.tok_name[token.type])
                else:
                    rows.append('%s %s' % (tokenize.tok_name[token.type], token.string))
        except (tokenize.TokenError, IndentationError, SyntaxError):
            rows.append('RAW ' + source)
    for line in text.splitlines(keepends=True):
        if line.startswith('\0'):
            flush()
            rows.append('ROW ' + line.rstrip('\n'))
        else:
            chunk.append(line)
    flush()
    return '\x1f'.join(rows)


def source_index(root=ROOT):
    from build_cache import SourceIndex
    root = Path(root).resolve()
    if root not in _INDEX:
        _INDEX[root] = SourceIndex(root, scope='units', top_format=TOP_FORMAT)
    return _INDEX[root]


def reach(entries, root=ROOT):
    """(python files, data files, uncertain, {python file: set of units}) the ENTRIES can reach."""
    index = source_index(root)
    # whole modules by path: listing their units would read them, and a stage that reads a file its fingerprint
    # leaves out is never reused (BUILD-NPC-GALLERY-KEY-NEUTRAL-READ-47)
    stop = frozenset((path, '*') for path in KEY_NEUTRAL)
    python, data, units, uncertain = set(), set(), {}, False
    for path, name in entries:
        if name == '<top>':
            # a module's import-time code, its classes included (a class is part of '<top>' in scope 'units')
            key = 'code-key-top::' + path
            if key not in index._closures:
                found = index._closure_symbols(path, key, entry='<top>', stop=stop)
                index._closures[key] = found
            p, d, unc, _ = index._closures[key]
            u = index._reached.get(key) or {}
        else:
            p, d, unc, u = index.entry_units(Path(root).resolve() / path, name, stop=stop)
        python |= set(p)
        data |= set(d)
        uncertain = uncertain or unc
        for module, names in u.items():
            units.setdefault(module, set()).update(names)
    return python, data, uncertain, units


def unit_hashes(path, units, root=ROOT):
    """{unit: SHA-256 of its normalized text} for UNITS of the module PATH (None: the unit is gone)."""
    from build_cache import SCHEDULING_UNITS, TOP_TEXT
    index = source_index(root)
    texts = index._unit_texts(path, TOP_FORMAT)
    top = {'<top>': TOP_TEXT[TOP_FORMAT]}
    rows = {}
    for unit in sorted(set(units) | {'<top>'}):
        if (path, unit) in SCHEDULING_UNITS:
            continue
        text = texts.get(top.get(unit, unit))
        rows[unit] = None if text is None else hashlib.sha256(
            normalized_text(text).encode('utf-8', 'surrogateescape')).hexdigest()
    return rows


def code_key(entries, data=(), root=ROOT):
    """{'form', 'entries', 'uncertain', 'files': {path: digest}, 'digest'} of ENTRIES' reach and the DATA files.
    Uncertain reach (dynamic code) counts every repository file whole."""
    entries = tuple((str(path), str(name)) for path, name in entries)
    key = (str(Path(root).resolve()), entries, tuple(sorted(data)))
    if key in _KEYS:
        return _KEYS[key]
    index = source_index(root)
    python, found, uncertain, units = reach(entries, root)
    files = {}
    if uncertain:
        files = dict(index.files)
    else:
        for path in sorted(python | found | set(data)):
            if path.endswith('.py') and path in units:
                files[path] = digest(unit_hashes(path, units[path], root))
            elif path in index.files:
                files[path] = index.files[path]
            elif path in data:
                files[path] = None
    result = {'form': CODE_KEY_FORM, 'entries': [list(e) for e in entries], 'uncertain': uncertain,
              'files': files, 'units': {path: sorted(names) for path, names in sorted(units.items())}}
    result['digest'] = digest({k: result[k] for k in ('form', 'entries', 'uncertain', 'files')})
    _KEYS[key] = result
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def uncovered(executed, key, root=ROOT):
    """The (path, function) pairs of EXECUTED (Tracer.take) that KEY's reach does not hold, sorted."""
    if key.get('uncertain'):
        return []
    from build_cache import OUTPUT_NEUTRAL
    index = source_index(root)
    units = key.get('units') or {}
    gaps = set()
    for path, name in executed:
        if path in KEY_NEUTRAL or path in OUTPUT_NEUTRAL or path not in index.files:
            continue
        known = index._module_symbols(path).get('units') or {}
        unit = name if name in known and not name.startswith('<') else '<top>'
        if unit not in units.get(path, ()):
            gaps.add((path, name))
    return sorted(gaps)


class Tracer:
    """The repository functions this process runs between begin() and take() (sys.monitoring PY_START; each code
    object reports once, then its event is switched off, so the cost is one call per function per process). Events
    are on only between begin() and end(): no cost elsewhere. take() returns what ran first since the last take();
    a function that ran before in this process was returned then."""

    TOOL_IDS = (3, 4, 1, 2)

    def __init__(self, root=ROOT):
        self.root = str(Path(root).resolve()).rstrip(os.sep) + os.sep
        self.tool = None
        self.available = None
        self.new = []

    def _register(self):
        monitoring = getattr(sys, 'monitoring', None)
        if monitoring is None:
            self.available = False
            return
        for tool in self.TOOL_IDS:
            if monitoring.get_tool(tool) is None:
                try:
                    monitoring.use_tool_id(tool, 'amiwind-code-key')
                except ValueError:
                    continue
                self.tool = tool
                break
        if self.tool is None:
            self.available = False
            return
        root = self.root
        new = self.new

        def started(code, offset):
            try:
                path = code.co_filename
                if path.startswith(root) and path.endswith('.py'):
                    new.append((path[len(root):].replace(os.sep, '/'), code.co_qualname.split('.', 1)[0]))
            except Exception:  # noqa: BLE001 - tracing never changes a unit
                pass
            return monitoring.DISABLE
        monitoring.register_callback(self.tool, monitoring.events.PY_START, started)
        self.available = True

    def begin(self):
        if self.available is None:
            self._register()
        if self.available:
            sys.monitoring.set_events(self.tool, sys.monitoring.events.PY_START)

    def end(self):
        if self.available:
            sys.monitoring.set_events(self.tool, 0)

    def close(self):
        """Give the monitoring tool back (tests)."""
        if self.available and self.tool is not None:
            sys.monitoring.set_events(self.tool, 0)
            sys.monitoring.register_callback(self.tool, sys.monitoring.events.PY_START, None)
            sys.monitoring.free_tool_id(self.tool)
        self.available, self.tool = None, None

    def take(self):
        """[(path, top-level name)] that ran first since the last take(); None when tracing is not available."""
        if not self.available:
            return None
        found = sorted(set(self.new))
        del self.new[:]
        return found


_TRACER = None


def tracer():
    """This process's Tracer (one per process: a forked worker keeps its parent's record and adds to it)."""
    global _TRACER
    if _TRACER is None:
        _TRACER = Tracer()
    return _TRACER
