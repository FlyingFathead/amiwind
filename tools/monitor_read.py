#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Read-only access to build run folders for the AmiWind Toolkit Monitor (tools/toolkit_serve.py --builds).

The Monitor shows a running or finished build (tools/build.py run folder): its build-progress.json, a summary of
build-state.json, the stage logs (byte ranges, so a page can follow a log as it grows) and the timeline of
build-profile.json. This module is the one reader: toolkit_serve.py uses it in its own process for a local folder,
or talks to it through a command (for example a read-only container that can see a build volume) with --serve.

Read-only by construction: it opens files for reading only, never runs anything, and every request names a run
and a file that must match a strict name pattern and resolve inside the configured root (no path separators, no
"..", no symlinks). Answers are capped in size.

  monitor_read.py --root builds=DIR --serve      answer JSON requests, one per line on stdin, one per line on stdout
  monitor_read.py --root builds=DIR runs         list the runs (one JSON document)

A request is a JSON object {"op": "runs"} | {"op": "files", "run": R} | {"op": "progress", "run": R} |
{"op": "state", "run": R} | {"op": "timeline", "run": R} | {"op": "log", "run": R, "name": N, "offset": O,
"max": M}; the answer is {"ok": true, ...} or {"ok": false, "error": "..."}.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+-]{0,199}$')
LOG_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+-]{0,120}\.log$')
# a stage's read/write trace (profile/reads/NN-stage.txt): '>path' written, '<path' read, '@file\tfunction' code entered
TRACE_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+-]{0,120}\.txt$')
STAGE_NAME = re.compile(r'^[0-9]{1,3}-[A-Za-z0-9][A-Za-z0-9_+-]{0,100}$')   # NN-stage, as logs/ and profile/ name them
MAX_TRACE = 128 * 1024 * 1024    # a trace larger than this is not parsed for sections
MAX_ANCHORS = 6000               # written files whose times anchor a trace (sampled evenly beyond this)
MAX_SECTIONS = 160
# Trace entries that are not work: loading a module, starting a pool worker, the profiler's own helpers. They never
# name a section (a frame-map step imports the actor check; that import is not the actor check running).
MAX_FILES = 400000             # files of a run folder scanned for their modification times
NOT_WORK = {'<module>', '_pool_worker_init', 'section', '_clock_ticks', '_profile_hook'}
MAX_READ = 256 * 1024          # bytes per log read
MAX_JSON = 8 * 1024 * 1024     # a JSON file larger than this is refused
MAX_RUNS = 60
TIMELINE_POINTS = 600


class Refused(ValueError):
    pass


def check_name(value, pattern=NAME, what='name'):
    if not isinstance(value, str) or not pattern.match(value) or value in ('.', '..') or '..' in value:
        raise Refused('invalid %s' % what)
    return value


class Reader:
    """Reads one root folder of build runs (root/<run>/...)."""

    def __init__(self, root):
        self.root = Path(root).resolve()

    def _inside(self, *parts):
        p = self.root.joinpath(*parts)
        for q in [p] + list(p.parents):
            if q == self.root:
                break
            if q.is_symlink():
                raise Refused('symbolic links are not followed')
        real = p.resolve()
        if real != self.root and self.root not in real.parents:
            raise Refused('outside the root')
        return real

    def _run(self, run):
        d = self._inside(check_name(run, what='run'))
        if not d.is_dir():
            raise Refused('no such run')
        return d

    def _json(self, path):
        if not path.is_file():
            return None
        if path.stat().st_size > MAX_JSON:
            raise Refused('%s is too large' % path.name)
        with open(path, 'rb') as f:
            return json.loads(f.read().decode('utf-8'))

    def runs(self):
        out = []
        try:
            entries = list(os.scandir(self.root))
        except FileNotFoundError:
            return {'runs': []}
        for e in entries:
            if not e.is_dir(follow_symlinks=False) or not NAME.match(e.name):
                continue
            d = Path(e.path)
            marker = next((d / n for n in ('build-progress.json', 'build-state.json') if (d / n).is_file()), None)
            if marker is None:
                continue
            out.append({'run': e.name, 'mtime': marker.stat().st_mtime, 'progress': (d / 'build-progress.json').is_file()})
        out.sort(key=lambda r: -r['mtime'])
        return {'runs': out[:MAX_RUNS]}

    def files(self, run):
        d = self._run(run) / 'logs'
        out = []
        if d.is_dir() and not d.is_symlink():
            for e in sorted(os.scandir(d), key=lambda e: e.name):
                if e.is_file(follow_symlinks=False) and LOG_NAME.match(e.name):
                    st = e.stat()
                    out.append({'name': e.name, 'size': st.st_size, 'mtime': st.st_mtime})
        traces = []
        t = self._run(run) / 'profile' / 'reads'
        if t.is_dir() and not t.is_symlink() and not t.parent.is_symlink():
            for e in sorted(os.scandir(t), key=lambda e: e.name):
                if e.is_file(follow_symlinks=False) and TRACE_NAME.match(e.name):
                    st = e.stat()
                    traces.append({'name': e.name, 'size': st.st_size, 'mtime': st.st_mtime})
        return {'run': run, 'logs': out, 'traces': traces}

    def progress(self, run):
        return {'run': run, 'progress': self._json(self._run(run) / 'build-progress.json')}

    def state(self, run):
        """A summary of build-state.json (the full file holds every input hash): status and the steps."""
        s = self._json(self._run(run) / 'build-state.json')
        if s is None:
            return {'run': run, 'state': None}
        steps = []
        for st in s.get('steps') or []:
            if isinstance(st, dict):
                steps.append({k: st.get(k) for k in ('name', 'status', 'jobs', 'started_seconds', 'elapsed_seconds',
                                                     'returncode')})
                if st.get('log'):
                    steps[-1]['log'] = Path(str(st['log'])).name
        keep = ('schema', 'runtime_version', 'status', 'builder', 'chim_version', 'world_format', 'build_started_at',
                'worker_budget', 'jobs_requested')
        return {'run': run, 'state': dict({k: s.get(k) for k in keep}, steps=steps)}

    def timeline(self, run):
        """The Build Timeline data of a finished run (build-profile.json): stage spans and cores over time."""
        p = self._json(self._run(run) / 'build-profile.json')
        if p is None:
            return {'run': run, 'timeline': None}
        stages = [{k: s.get(k) for k in ('name', 'status', 'start', 'end', 'wall', 'jobs', 'cores_avg')}
                  for s in p.get('stages') or [] if isinstance(s, dict)]
        t = p.get('timeline') or {}
        times, cores = t.get('t') or [], t.get('cgroup_cores') or t.get('cores') or []
        step = max(1, len(times) // TIMELINE_POINTS)
        series = [[times[i], cores[i]] for i in range(0, min(len(times), len(cores)), step)]
        return {'run': run, 'timeline': {'status': p.get('status'), 'wall_seconds': p.get('wall_seconds'),
                                         'budget': p.get('budget'), 'host_cpus': p.get('host_cpus'),
                                         'stages': stages, 'cores': series}}

    def log(self, run, name, offset=-1, max_bytes=MAX_READ, trace=False):
        """Bytes [offset, offset + max) of logs/NAME (or, with TRACE, of the stage's read/write trace
        profile/reads/NAME); offset < 0 reads the last max bytes. The text is decoded as UTF-8 with replacement;
        'next' is the offset to ask for next time."""
        if trace:
            f = self._inside(check_name(run, what='run'), 'profile', 'reads', check_name(name, TRACE_NAME, 'trace name'))
        else:
            f = self._inside(check_name(run, what='run'), 'logs', check_name(name, LOG_NAME, 'log name'))
        if not f.is_file():
            raise Refused('no such log')
        max_bytes = max(1, min(int(max_bytes), MAX_READ))
        size = f.stat().st_size
        offset = int(offset)
        start = max(0, size - max_bytes) if offset < 0 else min(offset, size)
        with open(f, 'rb') as fh:
            fh.seek(start)
            data = fh.read(max_bytes)
        return {'run': run, 'name': name, 'size': size, 'offset': start, 'next': start + len(data),
                'text': data.decode('utf-8', 'replace')}

    def _stage_window(self, d, name, profile):
        """(start, end) of stage NAME in seconds from the build's start: build-profile.json, else build-state.json."""
        for st in (profile or {}).get('stages') or []:
            if isinstance(st, dict) and st.get('name') == name and isinstance(st.get('start'), (int, float)):
                return float(st['start']), float(st.get('end') or st['start'])
        state = self._json(d / 'build-state.json') or {}
        for st in state.get('steps') or []:
            if isinstance(st, dict) and st.get('name') == name and isinstance(st.get('started_seconds'), (int, float)):
                start = float(st['started_seconds'])
                return start, start + float(st['elapsed_seconds']) if isinstance(st.get('elapsed_seconds'), (int, float)) else None
        return None, None

    def _build_epoch(self, d, profile):
        """The build's start as a Unix time (build-progress.json, else build-profile.json, else build-state.json)."""
        from datetime import datetime
        progress = self._json(d / 'build-progress.json') or {}
        state = None
        for text in (progress.get('started_at'), (profile or {}).get('started_at')):
            if isinstance(text, str):
                try:
                    return datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp()
                except ValueError:
                    pass
        state = self._json(d / 'build-state.json') or {}
        text = state.get('build_started_at')
        try:
            return datetime.fromisoformat(str(text).replace('Z', '+00:00')).timestamp()
        except ValueError:
            return None

    def sections(self, run, stage):
        """The sections of one stage (NN-stage) on the build's time axis: from the profiler's section timer
        (build-profile.json, source "profile"), or else derived from the stage's read/write trace (source "trace"):
        consecutive code entries of one tool make a section, timed by the modification times of the files the
        stage wrote between them (each written file is a time anchor; entries between two anchors are spread
        evenly). Cores per section come from the profile's per-stage core samples when the run has them."""
        check_name(stage, STAGE_NAME, 'stage')
        d = self._run(run)
        name = stage.split('-', 1)[1]
        profile = self._json(d / 'build-profile.json') if (d / 'build-profile.json').is_file() else None
        start, end = self._stage_window(d, name, profile)
        cores = None
        tl = (profile or {}).get('timeline') or {}
        if isinstance(tl.get('stages'), dict) and isinstance(tl['stages'].get(name), list):
            cores = [(float(t), float(c)) for t, c in tl['stages'][name] if isinstance(t, (int, float)) and isinstance(c, (int, float))]

        self._cores_now = cores

        def mean_cores(a, b):
            if not cores or b is None or b <= a:
                return None
            vals = [c for t, c in cores if a <= t <= b]
            return round(sum(vals) / len(vals), 2) if vals else None
        for st in (profile or {}).get('stages') or []:
            if isinstance(st, dict) and st.get('name') == name and st.get('sections'):
                rows = [x for x in st['sections'] if isinstance(x, dict) and isinstance(x.get('start'), (int, float))]
                out = []
                for x in sorted(rows, key=lambda x: (x['start'], x.get('min_depth') or 0))[:MAX_SECTIONS]:
                    a = float(x['start'])
                    b = a + float(x.get('wall') or 0)
                    out.append({'name': str(x.get('name'))[:80], 'start': round(a, 3), 'end': round(b, 3),
                                'cores': x.get('cores_avg') if x.get('cores_avg') is not None else mean_cores(a, b),
                                'calls': x.get('calls'), 'items': x.get('items'), 'depth': x.get('min_depth') or 0})
                out = mark_low_runs(out)
                # the profiler times only the sections a tool declares; the trace shows what ran in between
                derived = self._trace_sections(d, stage, start, end, mean_cores)
                return {'run': run, 'stage': stage, 'source': 'profile', 'start': start, 'end': end, 'sections': out,
                        'trace': derived.get('sections', []), 'note': derived.get('note')}
        return dict(self._trace_sections(d, stage, start, end, mean_cores), run=run, stage=stage)

    def _file_times(self, d, epoch):
        """Every regular file of a run folder with its modification time in seconds from the build start, sorted:
        what a stage wrote, seen from the files themselves (some writers are not traced, e.g. child processes)."""
        cache = self.__dict__.setdefault('_times_cache', {})
        stamp = (d / 'build-progress.json').stat().st_mtime if (d / 'build-progress.json').is_file() else 0
        key = (str(d), int(stamp // 60))
        if key in cache:
            return cache[key]
        out = []
        for base, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if not os.path.islink(os.path.join(base, x))]
            for name in files:
                f = os.path.join(base, name)
                try:
                    st = os.lstat(f)
                except OSError:
                    continue
                if not os.path.islink(f):
                    out.append((st.st_mtime - epoch, os.path.relpath(f, d).replace(os.sep, '/')))
            if len(out) > MAX_FILES:
                break
        out.sort()
        if len(cache) > 4:
            cache.clear()
        cache[key] = out
        return out

    def _trace_sections(self, d, stage, start, end, mean_cores):
        empty = {'source': 'trace', 'start': start, 'end': end, 'sections': []}
        f = self._inside(d.name, 'profile', 'reads', stage + '.txt')
        if not f.is_file() or start is None:
            return dict(empty, note='no trace or no stage start')
        st = f.stat()
        key = (str(f), st.st_size, st.st_mtime, start, end)
        cache = self.__dict__.setdefault('_section_cache', {})
        if key in cache:
            return cache[key]
        if st.st_size > MAX_TRACE:
            return dict(empty, note='trace too large to parse')
        epoch = self._build_epoch(d, None)
        if epoch is None:
            return dict(empty, note='no build start time')
        entries, writes = [], []
        with open(f, 'rb') as fh:
            for i, raw in enumerate(fh):
                line = raw.decode('utf-8', 'replace').rstrip('\n')
                if line.startswith('@'):
                    tool, _, func = line[1:].partition('\t')
                    entries.append((i, tool, func))
                elif line.startswith('>'):
                    writes.append((i, line[1:]))
        lines = i + 1 if entries or writes else 0
        all_writes = writes
        if len(writes) > MAX_ANCHORS:
            step = len(writes) / MAX_ANCHORS
            writes = [writes[int(k * step)] for k in range(MAX_ANCHORS)]
        stop = end if end is not None else (st.st_mtime - epoch)
        anchors = [(0, start)]
        wrote = []
        for i, path in writes:
            q = Path(path)
            target = q if q.is_absolute() else d / q
            try:
                if target.is_symlink():
                    continue
                real = target.resolve()
                if real != self.root and self.root not in real.parents:
                    continue
                t = target.stat().st_mtime - epoch
            except OSError:
                continue
            if start - 5 <= t <= stop + 5 and t >= anchors[-1][1]:
                anchors.append((i, t))
                wrote.append((t, path))
        anchors.append((max(lines, anchors[-1][0] + 1), stop))
        import bisect
        idx = [a[0] for a in anchors]

        def when(i):
            k = max(0, min(len(anchors) - 2, bisect.bisect_right(idx, i) - 1))
            (i0, t0), (i1, t1) = anchors[k], anchors[k + 1]
            return t0 if i1 <= i0 else t0 + (t1 - t0) * (min(max(i, i0), i1) - i0) / (i1 - i0)
        groups = []
        for i, tool, func in entries:
            if func in NOT_WORK:
                continue
            key = tool.rsplit('/', 1)[-1] + ' · ' + func
            if groups and groups[-1]['tool'] == tool:
                g = groups[-1]
                g['funcs'][key] = g['funcs'].get(key, 0) + 1
                g['n'] += 1
            else:
                groups.append({'tool': tool, 'first': i, 'funcs': {key: 1}, 'n': 1})
        rows = []
        for k, g in enumerate(groups):
            a = when(g['first'])
            b = when(groups[k + 1]['first']) if k + 1 < len(groups) else stop
            rows.append({'tool': g['tool'], 'funcs': g['funcs'], 'n': g['n'], 'start': a, 'end': max(a, b),
                         'i0': g['first'], 'i1': groups[k + 1]['first'] if k + 1 < len(groups) else lines})
        # merge short pieces into their neighbour so the stage reads at a glance
        floor = max(5.0, (stop - start) / 1500.0)
        merged = []
        for r in rows:
            if merged and (r['end'] - r['start'] < floor or merged[-1]['tool'] == r['tool']):
                m = merged[-1]
                m['end'] = r['end']
                m['i1'] = r['i1']
                m['n'] += r['n']
                for fn, c in r['funcs'].items():
                    m['funcs'][fn] = m['funcs'].get(fn, 0) + c
                if m['tool'] != r['tool']:
                    m.setdefault('also', set()).add(r['tool'])
            else:
                merged.append(dict(r, funcs=dict(r['funcs'])))
        while len(merged) > MAX_SECTIONS:
            k = min(range(len(merged) - 1), key=lambda j: merged[j]['end'] - merged[j]['start'] + merged[j + 1]['end'] - merged[j + 1]['start'])
            a, b = merged[k], merged.pop(k + 1)
            a['end'] = b['end']
            a['i1'] = b['i1']
            a['n'] += b['n']
            a.setdefault('also', set()).add(b['tool'])
        import bisect as _b
        widx = [i for i, _ in all_writes]
        times = self._file_times(d, epoch)
        tidx = [t for t, _ in times]
        out = []
        for m in merged:
            # name a section first by what it WROTE (file name pattern and count), then by the code it entered most
            lo, hi = _b.bisect_left(widx, m['i0']), _b.bisect_left(widx, m['i1'])
            made = [Path(p).name for _, p in all_writes[lo:hi]]
            patterns = {}
            for name in made:
                pat = re.sub(r'[0-9]+', '*', name)
                patterns[pat] = patterns.get(pat, 0) + 1
            top = sorted(patterns.items(), key=lambda kv: -kv[1])[:2]
            by_time = {}
            if not top:
                # nothing written by traced code: the files whose modification times fall in the section
                for _, rel in times[_b.bisect_left(tidx, m['start']):_b.bisect_right(tidx, m['end'])]:
                    if rel.startswith(('profile/', 'logs/')) or rel in ('build-progress.json', 'build-state.json', 'build-profile.json'):
                        continue
                    pat = re.sub(r'[0-9]+', '*', rel.rsplit('/', 1)[-1])
                    by_time[pat] = by_time.get(pat, 0) + 1
                top = sorted(by_time.items(), key=lambda kv: -kv[1])[:2]
            ranked = sorted(m['funcs'].items(), key=lambda kv: -kv[1])
            code = ranked[0][0] if ranked else ''
            label = ' + '.join('%s x%d' % kv for kv in top) + (' (file times)' if by_time else '') if top else code
            if top and code:
                label += ' · ' + code
            out.append({'name': label[:90] or m['tool'].rsplit('/', 1)[-1], 'start': round(m['start'], 1),
                        'end': round(m['end'], 1), 'cores': mean_cores(m['start'], m['end']), 'entries': m['n'],
                        'code': [k for k, _ in ranked[:6]], 'files_written': len(made), 'last_written': made[-3:],
                        'writes': ['%s x%d' % kv for kv in sorted(patterns.items(), key=lambda kv: -kv[1])[:5]]})
        out = split_by_cores(out, self.__dict__.get('_cores_now'))
        result = {'source': 'trace', 'start': start, 'end': end, 'sections': out,
                  'note': 'derived from trace (approximate): %d code entries, named by the files written, timed by %d of them'
                          % (len(entries), len(anchors) - 2)}
        if len(cache) > 50:
            cache.clear()
        cache[key] = result
        return result

    def answer(self, request):
        """One request (a dict) to one answer (a dict); never raises."""
        try:
            if not isinstance(request, dict):
                raise Refused('a request is a JSON object')
            op = request.get('op')
            if op == 'runs':
                out = self.runs()
            elif op in ('files', 'progress', 'state', 'timeline'):
                out = getattr(self, op)(request.get('run'))
            elif op == 'sections':
                out = self.sections(request.get('run'), request.get('stage'))
            elif op in ('log', 'trace'):
                out = self.log(request.get('run'), request.get('name'), request.get('offset', -1),
                               request.get('max', MAX_READ), trace=op == 'trace')
            else:
                raise Refused('unknown request')
            return dict(out, ok=True)
        except (Refused, ValueError, TypeError, OSError) as e:
            return {'ok': False, 'error': str(e) if isinstance(e, Refused) else type(e).__name__}


LOW_CORES, LOW_SECONDS = 4.0, 60.0


def split_by_cores(sections, cores, low=LOW_CORES, least=LOW_SECONDS):
    """Split derived sections where the stage's core use changes regime: a stretch of at least LEAST seconds under LOW
    cores becomes its own section ("low-core stretch"), so the timeline shows where a stage left the machine idle even
    when its trace is too sparse to time the code that ran. CORES: [(t, cores)] per-stage samples, or None."""
    if not cores:
        return sections
    out = []
    for sec in sections:
        pts = [(t, c) for t, c in cores if sec['start'] <= t <= sec['end']]
        runs, cur = [], None
        for t, c in pts:
            kind = c < low
            if cur and cur[0] == kind:
                cur[2] = t
                cur[3].append(c)
            else:
                cur = [kind, t, t, [c]]
                runs.append(cur)
        lows = [r for r in runs if r[0] and r[2] - r[1] >= least]
        if not lows:
            out.append(sec)
            continue
        at = sec['start']
        for kind, a, b, cs in lows:
            if a - at > 1:
                out.append(dict(sec, start=round(at, 1), end=round(a, 1), cores=None))
            out.append(dict(sec, name=(sec['name'] + ' (low-core stretch)')[:80], start=round(a, 1), end=round(b, 1),
                            cores=round(sum(cs) / len(cs), 2)))
            at = b
        if sec['end'] - at > 1:
            out.append(dict(sec, start=round(at, 1), end=sec['end'], cores=None))
    # pieces without their own mean get one from the samples
    for sec in out:
        if sec.get('cores') is None:
            vals = [c for t, c in cores if sec['start'] <= t <= sec['end']]
            sec['cores'] = round(sum(vals) / len(vals), 2) if vals else None
    return mark_low_runs(out, low, least)


def mark_low_runs(sections, low=LOW_CORES, least=LOW_SECONDS):
    """Mark 'low_run' on every section of a run of consecutive sections each under LOW cores that together last at
    least LEAST seconds: several short single-core steps in a row are one idle stretch of the machine."""
    k = 0
    while k < len(sections):
        j = k
        while j < len(sections) and sections[j].get('cores') is not None and sections[j]['cores'] < low:
            j += 1
        if j > k and sections[j - 1]['end'] - sections[k]['start'] >= least:
            for sec in sections[k:j]:
                sec['low_run'] = round(sections[j - 1]['end'] - sections[k]['start'], 1)
        k = max(j, k + 1)
    return sections


CONSOLE_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+-]{0,200}\.console\.log$')


def tail_file(root, name, offset=-1, max_bytes=MAX_READ, pattern=CONSOLE_NAME):
    """A byte range of ROOT/NAME (a flat folder of logs, such as the master builder's console logs), with the same
    rules as Reader.log: a strict name, inside the root, no symlinks, capped."""
    root = Path(root).resolve()
    check_name(name, pattern, 'log name')
    f = root / name
    if f.is_symlink() or f.resolve().parent != root or not f.is_file():
        raise Refused('no such log')
    max_bytes = max(1, min(int(max_bytes), MAX_READ))
    size = f.stat().st_size
    offset = int(offset)
    start = max(0, size - max_bytes) if offset < 0 else min(offset, size)
    with open(f, 'rb') as fh:
        fh.seek(start)
        data = fh.read(max_bytes)
    return {'name': name, 'size': size, 'offset': start, 'next': start + len(data), 'text': data.decode('utf-8', 'replace')}


def serve(reader, stdin=sys.stdin, stdout=sys.stdout):
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError:
            request = None
        stdout.write(json.dumps(reader.answer(request), separators=(',', ':')) + '\n')
        stdout.flush()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--root', required=True, help='builds=DIR: the folder holding the build runs')
    p.add_argument('--serve', action='store_true', help='answer JSON requests on stdin, one per line')
    p.add_argument('op', nargs='?', choices=('runs',))
    a = p.parse_args(argv)
    name, _, root = a.root.partition('=')
    if name != 'builds' or not root:
        p.error('--root builds=DIR')
    reader = Reader(root)
    if a.serve:
        serve(reader)
    else:
        print(json.dumps(reader.answer({'op': a.op or 'runs'}), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
