#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Read cost model for CHIM files on an Amiga FFS disk, from `awbench seek` reports.

FFS keeps a file's block list in extension blocks of 72 entries (36 KiB of
data with 512-byte blocks). A Seek forward walks the chain from the current
position, a Seek backward from the file header, so a seek costs about one
extension block step per 36 KiB travelled, while a forward skip of up to
64 KiB costs no more than reading on (docs/bugs/STREAM-FFS-SEEK-32.md,
docs/chim/WORLD_FORMAT.md). The model:

    crossing ms = open_ms x files opened
                + ext_ms x extension blocks walked (from the file start to the
                  last range read, reading every file in ascending order)
                + seq_ms_per_kib x KiB read
                + request_ms x read runs

`python3 tools/chim/readcost.py REPORT.txt ... --out COST.json` fits the
constants from awbench seek reports (several file sizes; 16 KiB requests, so
its per-KiB cost includes each request's overhead and overstates long runs);
`readcost.py REPLAY.txt --replay-estimates EST.json` compares an `awbench
replay` of the validator's walk with the estimates and fits the constants to
the replayed crossings (the built-in default). The validator uses a model for
its crossing estimates (--read-cost). Emulator reports give relative numbers
only until a hardware report exists.
"""
import argparse
import json
import re
import statistics
import sys
from pathlib import Path

EXT_BYTES = 72 * 512
SKIP_FREE_LIMIT = 1.5     # a forward skip is "free" while it costs at most this times a plain request

# Fitted to the replayed Balmora walk (validate.py --replay-dir, awbench replay; 210 crossings,
# R^2 0.82): FS-UAE cycle-approximate 68040 (cycle-exact, multiplier 7), the CHIM files on an FFS
# partition made by the builder, 8 October 2026. Relative numbers: the emulator's hard disk moves
# bytes almost for free (about 90 MB/s), a real IDE drive does not.
DEFAULT = {'source': 'awbench replay of the Balmora walk, FS-UAE cycle-approximate 68040, FFS partition '
                     'made by the builder, 8 October 2026',
           'seq_ms_per_kib': 0.01129, 'ext_ms': 0.09204, 'open_ms': 1.2542, 'request_ms': 0.97902,
           'skip_free_bytes': 65536}


def parse(text):
    """AWBENCH seek lines of one report: [{pattern, gap, file_bytes, requests, us_per_request, open_us}]."""
    rows = []
    for line in text.splitlines():
        if not line.startswith('AWBENCH seek '):
            continue
        kv = dict(re.findall(r'(\w+)=(\S+)', line))
        rows.append({'pattern': kv['pattern'], 'gap': int(kv['gap']), 'file_bytes': int(kv['file_bytes']),
                     'requests': int(kv['requests']), 'request': int(kv['request']),
                     'us_per_request': int(kv['us_per_request']), 'open_us': int(kv['open_us'])})
    return rows


def fit(rows):
    """Constants of the cost model from parsed seek rows (one or more reports)."""
    if not rows:
        raise ValueError('No AWBENCH seek lines')
    by_file = {}
    for r in rows:
        by_file.setdefault(r['file_bytes'], []).append(r)
    seq, ext, free = [], [], []
    for size, rs in by_file.items():
        base = [r for r in rs if r['pattern'] == 'skip' and r['gap'] == 0]
        if not base:
            continue
        b = base[0]['us_per_request']
        seq.append(b / (base[0]['request'] / 1024) / 1000)
        for r in rs:
            if r['pattern'] == 'random':
                blocks = size / 2 / EXT_BYTES
            elif r['pattern'] == 'skip' and r['gap'] >= 4 * EXT_BYTES:
                blocks = r['gap'] / EXT_BYTES
            else:
                blocks = 0
            if blocks and r['us_per_request'] > b:
                ext.append((r['us_per_request'] - b) / blocks / 1000)
        gaps = sorted(r['gap'] for r in rs if r['pattern'] == 'skip' and r['gap']
                      and r['us_per_request'] <= SKIP_FREE_LIMIT * b)
        cheap = 0
        for gap in sorted(r['gap'] for r in rs if r['pattern'] == 'skip' and r['gap']):
            if gap not in gaps:
                break
            cheap = gap
        free.append(cheap)
    if not seq or not ext:
        raise ValueError('Seek report lacks the sequential or far-seek patterns')
    return {'seq_ms_per_kib': round(statistics.median(seq), 5), 'ext_ms': round(statistics.median(ext), 4),
            'open_ms': round(statistics.median(r['open_us'] for r in rows) / 1000, 3), 'request_ms': 0.0,
            'skip_free_bytes': min(free) if free else 0, 'reports_rows': len(rows),
            'file_sizes': sorted(by_file)}


def crossing_ms(runs, cost):
    """runs: [(file, first byte, end byte, requests)] read in one crossing (ascending per file)."""
    files = {}
    for f, a, b, n in runs:
        files.setdefault(f, []).append((a, b, n))
    ms = 0.0
    for f, rs in files.items():
        rs.sort()
        ms += cost['open_ms'] + cost['ext_ms'] * (rs[-1][0] // EXT_BYTES)
        ms += sum((b - a) / 1024 * cost['seq_ms_per_kib'] + cost['request_ms'] for a, b, n in rs)
    return ms


def merge_runs(ranges, skip_free):
    """Ranges (file, start, end) to read runs: forward gaps up to skip_free cost nothing extra."""
    runs = []
    for f, a, b in sorted(ranges):
        if runs and runs[-1][0] == f and 0 <= a - runs[-1][2] <= skip_free:
            runs[-1][2] = max(runs[-1][2], b)
            runs[-1][3] += 1
        else:
            runs.append([f, a, b, 1])
    return runs


def features(runs):
    """What a crossing does, in the cost model's terms: KiB read, extension blocks walked, files, runs."""
    files = {}
    for f, a, b, n in runs:
        files.setdefault(f, []).append(a)
    return {'kib': round(sum(b - a for _, a, b, _ in runs) / 1024, 3), 'ext_blocks': sum(max(v) // EXT_BYTES
                                                                                        for v in files.values()),
            'files': len(files), 'runs': len(runs), 'bytes': sum(b - a for _, a, b, _ in runs)}


def fit_replay(measured_us, rows):
    """Cost model constants fitted to replayed crossings (least squares, no negative constants).

    rows: replay estimates with features (validate.py --replay-dir)."""
    import numpy as np
    use = [r for r in rows if r['crossing'] in measured_us and r['bytes']]
    names = ['seq_ms_per_kib', 'ext_ms', 'open_ms', 'request_ms']
    X = np.array([[r['kib'], r['ext_blocks'], r['files'], r['runs']] for r in use], float)
    y = np.array([measured_us[r['crossing']] / 1000 for r in use], float)
    keep = list(range(4))
    while True:
        coef, *_ = np.linalg.lstsq(X[:, keep], y, rcond=None)
        if (coef >= 0).all() or len(keep) == 1:
            break
        keep.pop(int(np.argmin(coef)))
    out = dict.fromkeys(names, 0.0)
    for k, c in zip(keep, coef):
        out[names[k]] = round(float(max(c, 0.0)), 5)
    pred = X[:, keep] @ np.maximum(coef, 0)
    out['crossings'] = len(use)
    out['residual_ms_p90'] = round(float(np.percentile(np.abs(pred - y), 90)), 2)
    out['r2'] = round(float(1 - ((pred - y) ** 2).sum() / ((y - y.mean()) ** 2).sum()), 3) if len(y) > 1 else None
    return out


def parse_replay(text):
    """{crossing: microseconds} of an `awbench replay` report (incomplete crossings left out)."""
    out = {}
    for line in text.splitlines():
        if line.startswith('AWBENCH replay crossing=') and 'incomplete=' not in line:
            kv = dict(re.findall(r'(\w+)=(\S+)', line))
            out[int(kv['crossing'])] = int(kv['us'])
    return out


def compare_replay(measured_us, estimates):
    """Measured against estimated time per crossing: ratios and a least-squares scale factor.

    estimates: [{crossing, estimated_ms, runs, bytes, files}] (validate.py --replay-dir)."""
    rows = [dict(e, measured_ms=measured_us[e['crossing']] / 1000) for e in estimates if e['crossing'] in measured_us]
    moving = [r for r in rows if r['crossing'] > 0 and r['bytes']]
    if not moving:
        raise ValueError('No replayed crossing matches the estimates')
    ratio = sorted(r['measured_ms'] / r['estimated_ms'] for r in moving if r['estimated_ms'])
    est = [r['estimated_ms'] for r in moving]
    mea = [r['measured_ms'] for r in moving]
    scale = sum(x * y for x, y in zip(est, mea)) / sum(x * x for x in est)
    mean_e, mean_m = statistics.mean(est), statistics.mean(mea)
    cov = sum((x - mean_e) * (y - mean_m) for x, y in zip(est, mea))
    var_e = sum((x - mean_e) ** 2 for x in est)
    var_m = sum((y - mean_m) ** 2 for y in mea)
    return {'crossings': len(moving), 'measured_ms_p50': round(statistics.median(mea), 2),
            'measured_ms_max': round(max(mea), 2), 'measured_ms_total': round(sum(mea), 1),
            'estimated_ms_p50': round(statistics.median(est), 2), 'estimated_ms_max': round(max(est), 2),
            'estimated_ms_total': round(sum(est), 1),
            'ratio_p10': round(ratio[len(ratio) // 10], 3), 'ratio_p50': round(ratio[len(ratio) // 2], 3),
            'ratio_p90': round(ratio[9 * len(ratio) // 10], 3), 'scale': round(scale, 3),
            'correlation': round(cov / (var_e * var_m) ** 0.5, 3) if var_e and var_m else None,
            'cold': next(({'measured_ms': r['measured_ms'], 'estimated_ms': r['estimated_ms']}
                          for r in rows if r['crossing'] == 0), None)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('reports', nargs='+', type=Path, help='awbench seek reports (or one replay report)')
    ap.add_argument('--source', default='', help='where the reports come from (machine, profile, disk)')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--replay-estimates', type=Path,
                    help='compare an `awbench replay` report with these estimates (validate.py --replay-dir)')
    a = ap.parse_args(argv)
    if a.replay_estimates:
        measured = parse_replay(a.reports[0].read_text(encoding='utf-8', errors='replace'))
        rows = json.loads(a.replay_estimates.read_text(encoding='utf-8'))
        result = compare_replay(measured, rows)
        if all('kib' in r for r in rows):
            result['fitted'] = fit_replay(measured, rows)
        text = json.dumps(dict(result, source=a.source), indent=1, sort_keys=True) + '\n'
        if a.out:
            a.out.write_bytes(text.encode('utf-8'))
        sys.stdout.write(text)
        return 0
    rows = [r for p in a.reports for r in parse(p.read_text(encoding='utf-8', errors='replace'))]
    cost = dict(fit(rows), source=a.source)
    text = json.dumps(cost, indent=1, sort_keys=True) + '\n'
    if a.out:
        a.out.write_bytes(text.encode('utf-8'))
    sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
