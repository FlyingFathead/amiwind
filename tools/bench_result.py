# SPDX-License-Identifier: GPL-3.0-only
"""Read a benchmark result file into a JSON row (docs/HALLOWEEN.md "The benchmark", docs/REAL_HARDWARE.md).

`aw bench halloween` writes, once after its 600 frames, bench/halloween-<build>-<nnn>.txt in the game folder of the
game disk (engine/aga/src/aw_halloween.c bench_write). The file is plain text, one "key values" line each:

    AWBENCH1 halloween
    scene dagoth
    build 0.0.62-dev1
    title AmiWind v0.0.62-dev1 ...
    cpu 68040
    fast_ram_mb 32
    settings screen 320x256 viewsize 100 fov 90 fog 1
    step_s 0.100
    summary HALLOWEEN BENCH dagoth: avg ... (the console line, word for word)
    all frames 600 seconds 121.210 avg 4.95 min 0.40 low1 0.62
    drawing frames 598 seconds 120.000 avg 4.98 min 0.45 low1 0.70
    disk frames 2 ms 812.30 worst_ms 500.40 worst_frame 12 lookups 14 reads 30
    slowest 12 2500.00 500.40          (frame, ms, disk ms; up to five, slowest first)
    times frame ms disk_ms
    1 201.30 0.00                       (every frame)
    ...
    end

"all" counts every frame; "drawing" only the frames that waited on nothing from the disk (the headline frame rate);
"disk" is the disk side on its own. This reader parses the file, checks the figures against the frame times (a
damaged or cut file is refused) and prints one JSON row per file; --append adds the rows to a JSON-lines file once
each (a file already there, by its SHA-256, is not added again).

    python3 tools/bench_result.py halloween-0.0.62-dev1-001.txt --commit abc1234 --machine "Pi 4B, Amiberry"
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

MAGIC = 'AWBENCH1 halloween'
SLOWEST = 5                 # aw_halloween.h AW_HW_BENCH_SLOWEST


def figures(times, keep=None):
    """The engine's figures (aw_halloween_rules.c figures) over the frame times in seconds whose index KEEP allows:
    frames, seconds, average fps, the slowest frame's fps and the 1 % low (the slowest 1 %, at least one, at most 64)."""
    picked = [t for i, t in enumerate(times) if keep is None or keep(i)]
    if not picked:
        return {'frames': 0, 'seconds': 0.0, 'avg': 0.0, 'min': 0.0, 'low1': 0.0}
    total = sum(picked)
    count = min(max(len(picked) // 100, 1), 64)
    slow = sum(sorted(picked, reverse=True)[:count])
    worst = max(picked)
    return {'frames': len(picked), 'seconds': total, 'avg': len(picked) / total if total > 0 else 0.0,
            'min': 1 / worst if worst > 0 else 0.0, 'low1': count / slow if slow > 0 else 0.0}


def _pairs(words, what):
    if len(words) % 2:
        raise ValueError(f'{what}: the line is not "name value" pairs')
    return dict(zip(words[0::2], words[1::2]))


def _number(text, what):
    try:
        return float(text)
    except ValueError:
        raise ValueError(f'{what}: {text!r} is not a number') from None


def parse(text):
    """The result file's TEXT as a dict; ValueError names what is wrong."""
    lines = text.replace('\r\n', '\n').split('\n')
    if not lines or lines[0].strip() != MAGIC:
        raise ValueError(f'not a benchmark result file (the first line is not "{MAGIC}")')
    row = {'benchmark': 'halloween', 'slowest': [], 'times_ms': [], 'disk_ms': []}
    in_times = ended = False
    for number, line in enumerate(lines[1:], 2):
        line = line.strip()
        if not line:
            continue
        if ended:
            raise ValueError(f'line {number}: text after "end"')
        if line == 'end':
            ended = True
            continue
        key, _, rest = line.partition(' ')
        if in_times:
            words = line.split()
            if len(words) != 3 or int(words[0]) != len(row['times_ms']) + 1:
                raise ValueError(f'line {number}: expected frame {len(row["times_ms"]) + 1} with its ms and disk ms')
            row['times_ms'].append(_number(words[1], f'line {number}'))
            row['disk_ms'].append(_number(words[2], f'line {number}'))
            continue
        if key in ('scene', 'build', 'title', 'summary', 'cpu'):
            row[key] = rest
        elif key == 'fast_ram_mb':
            row[key] = int(rest)
        elif key == 'step_s':
            row[key] = _number(rest, key)
        elif key == 'settings':
            row['settings'] = rest
        elif key in ('all', 'drawing'):
            pairs = _pairs(rest.split(), key)
            row[key] = {name: (int(value) if name == 'frames' else _number(value, f'{key} {name}'))
                        for name, value in pairs.items()}
        elif key == 'disk':
            pairs = _pairs(rest.split(), key)
            row['disk'] = {name: (_number(value, f'disk {name}') if name.endswith('ms') else int(value))
                           for name, value in pairs.items()}
        elif key == 'slowest':
            words = rest.split()
            if len(words) != 3:
                raise ValueError(f'line {number}: slowest takes a frame, its ms and its disk ms')
            row['slowest'].append({'frame': int(words[0]), 'ms': _number(words[1], 'slowest'),
                                   'disk_ms': _number(words[2], 'slowest')})
        elif key == 'times':
            in_times = True
        else:
            raise ValueError(f'line {number}: unknown line {key!r}')
    if not ended:
        raise ValueError('the file is cut short (no "end" line)')
    for key in ('scene', 'build', 'summary', 'all', 'drawing', 'disk'):
        if key not in row:
            raise ValueError(f'the file has no {key!r} line')
    check(row)
    return row


def check(row):
    """The figures in the file against its own frame times (to the file's two decimals)."""
    times = [ms / 1000 for ms in row['times_ms']]
    if len(times) != row['all']['frames']:
        raise ValueError(f'{len(times)} frame times for {row["all"]["frames"]} frames')
    waited = [d > 0.0 for d in row['disk_ms']]
    checks = [('all', None)]
    # a frame waited on the disk when its wait was above 0; the file keeps two decimals of a millisecond, so a wait
    # under 0.005 ms reads as 0.00: then the drawing figures cannot be told from the times and the summary stands
    if sum(waited) == row['disk']['frames']:
        checks.append(('drawing', lambda i: not waited[i]))
    for key, keep in checks:
        got = figures(times, keep)
        want = row[key]
        if got['frames'] != want['frames']:
            raise ValueError(f'{key}: {got["frames"]} frames in the times, {want["frames"]} in the summary')
        for name in ('avg', 'min', 'low1'):
            if abs(got[name] - want[name]) > 0.011 + 0.001 * want[name]:
                raise ValueError(f'{key} {name}: {got[name]:.2f} from the times, {want[name]:.2f} in the summary')


def row_of(path, commit=None, machine=None, frames=False):
    raw = Path(path).read_bytes()
    row = parse(raw.decode('latin-1'))
    out = {'file': Path(path).name, 'sha256': hashlib.sha256(raw).hexdigest(), 'build': row['build'],
           'commit': commit, 'machine': machine, 'scene': row['scene'], 'cpu': row.get('cpu'),
           'fast_ram_mb': row.get('fast_ram_mb'), 'settings': row.get('settings'), 'summary': row['summary'],
           'all': row['all'], 'drawing': row['drawing'], 'disk': row['disk'], 'slowest': row['slowest']}
    if frames:
        out['times_ms'] = row['times_ms']
        out['disk_ms'] = row['disk_ms']
    return out


def append(rows, target):
    """Add ROWS to the JSON-lines file TARGET, each once (by the result file's SHA-256); the rows added."""
    target = Path(target)
    known = set()
    if target.exists():
        for line in target.read_text(encoding='utf-8').splitlines():
            if line.strip():
                known.add(json.loads(line).get('sha256'))
    added = [r for r in rows if r['sha256'] not in known]
    if added:
        with target.open('a', encoding='utf-8', newline='\n') as f:
            for r in added:
                f.write(json.dumps(r, sort_keys=True) + '\n')
    return added


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('files', nargs='+', help='bench/halloween-<build>-<nnn>.txt files copied off the game disk')
    p.add_argument('--commit', help='the commit the build was made from, when known')
    p.add_argument('--machine', help='the machine or emulator and its setup, e.g. "Pi 4B, Amiberry, 68040 JIT"')
    p.add_argument('--frames', action='store_true', help='include every frame time and disk wait in the row')
    p.add_argument('--append', metavar='JSONL', help='add the rows to this JSON-lines file, each file once')
    args = p.parse_args(argv)
    rows = []
    for name in args.files:
        try:
            rows.append(row_of(name, args.commit, args.machine, args.frames))
        except (OSError, ValueError) as e:
            print(f'{name}: {e}', file=sys.stderr)
            return 1
    for r in rows:
        print(json.dumps(r, sort_keys=True))
    if args.append:
        added = append(rows, args.append)
        print(f'{len(added)} of {len(rows)} rows added to {args.append}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
