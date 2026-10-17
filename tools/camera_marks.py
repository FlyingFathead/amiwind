#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Named camera marks (dbg cam mark / recall / list): the marks file format, checked the way the engine reads it.

docs/CAMERA_MARKS.md describes the file. The public marks are config/camera-marks.txt (copied onto the boot disk
as id1/camera-marks.txt by tools/build_aga.py); private marks are saves/camera-marks.txt in the game folder,
written by dbg cam mark. The engine's reader is engine/aga/src/aw_cam_rules.c; both refuse the same lines.

  python3 tools/camera_marks.py check [FILE ...]     validate (default: config/camera-marks.txt)
  python3 tools/camera_marks.py show NAME [FILE]     one mark as JSON
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'config' / 'camera-marks.txt'
MAGIC = 'AWCM1'
LINE_LIMIT = 383            # characters per line without the line end (AW_CAM_LINE 384)
FILE_LIMIT = 16384          # bytes per file (AW_CAM_FILE_BYTES)
NOTE_LIMIT = 159
NAME = re.compile(r'[A-Za-z0-9_.-]{1,31}\Z')
MAP = re.compile(r'[a-z0-9_]{1,15}\Z')
NUMBER = re.compile(r'[0-9+.-]{1,23}\Z')
GLOBAL_BOUND = 2000000.0
LOCAL_BOUND = 32768.0
FIELDS = ('name', 'place', 'position', 'view', 'time', 'headlamp', 'fog', 'note')


class MarkError(ValueError):
    pass


def _numbers(text, most, bound, what):
    if not text or '  ' in text or text.startswith(' ') or text.endswith(' '):
        raise MarkError(f'{what}: numbers separated by single spaces: {text!r}')
    values = []
    for token in text.split(' '):
        if not NUMBER.match(token):
            raise MarkError(f'{what}: not a number: {token!r}')
        try:
            value = float(token)
        except ValueError:
            raise MarkError(f'{what}: not a number: {token!r}') from None
        if not -bound <= value <= bound:
            raise MarkError(f'{what}: {token} outside +-{bound:g}')
        values.append(value)
    if len(values) > most:
        raise MarkError(f'{what}: at most {most} numbers: {text!r}')
    return values


def parse_line(line):
    """A mark as a dict, None for a comment or an empty line; MarkError names the field and value."""
    if not line or line.startswith('#'):
        return None
    if len(line) > LINE_LIMIT:
        raise MarkError(f'line longer than {LINE_LIMIT} characters')
    if any(not 32 <= ord(c) <= 126 for c in line):
        raise MarkError('only printable ASCII')
    fields = line.split('|')
    if len(fields) != len(FIELDS):
        raise MarkError(f'{len(fields)} fields, expected {len(FIELDS)} ({"|".join(FIELDS)})')
    name, place, position, view, time, headlamp, fog, note = fields
    if not NAME.match(name):
        raise MarkError(f'name: {name!r} (1..31 of A-Z a-z 0-9 _ - .)')
    mark = {'name': name}
    if place == 'global':
        point = _numbers(position, 3, GLOBAL_BOUND, 'position')
        if len(point) < 2:
            raise MarkError(f'position: X Y [Z] for a global mark: {position!r}')
        mark.update(place='global', point=point)
    else:
        if not MAP.match(place):
            raise MarkError(f'place: "global" or a map name (a-z 0-9 _, 1..15): {place!r}')
        point = _numbers(position, 3, LOCAL_BOUND, 'position')
        if len(point) != 3:
            raise MarkError(f'position: X Y Z for a map mark: {position!r}')
        mark.update(place=place, point=point)
    angles = _numbers(view, 2, 360, 'view')
    if len(angles) != 2 or not 0 <= angles[0] < 360 or not -80 <= angles[1] <= 80:
        raise MarkError(f'view: YAW 0..<360 PITCH -80..80: {view!r}')
    mark.update(yaw=angles[0], pitch=angles[1])
    if time == '-':
        mark['time'] = None
    elif re.fullmatch(r'[0-9]{4}', time) and int(time[:2]) <= 23 and int(time[2:]) <= 59:
        mark['time'] = time
    else:
        raise MarkError(f'time: HHMM 0000..2359 or -: {time!r}')
    if headlamp not in ('on', 'off', '-'):
        raise MarkError(f'headlamp: on/off/-: {headlamp!r}')
    mark['headlamp'] = None if headlamp == '-' else headlamp == 'on'
    if fog == '-':
        mark['fog'] = None
    elif re.fullmatch(r'[0-9]{3,4}', fog) and 100 <= int(fog) <= 4096:
        mark['fog'] = int(fog)
    else:
        raise MarkError(f'fog: 100..4096 or -: {fog!r}')
    if len(note) > NOTE_LIMIT:
        raise MarkError(f'note longer than {NOTE_LIMIT} characters')
    mark['note'] = note
    return mark


def parse(raw, label='camera marks'):
    """The marks of a file's bytes, in order; MarkError names the line."""
    if len(raw) > FILE_LIMIT:
        raise MarkError(f'{label}: {len(raw)} bytes > {FILE_LIMIT}')
    if b'\r' in raw:
        raise MarkError(f'{label}: CR bytes (LF line ends only)')
    try:
        text = raw.decode('ascii')
    except UnicodeDecodeError:
        raise MarkError(f'{label}: not ASCII') from None
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    if not lines or lines[0] != MAGIC:
        raise MarkError(f'{label}: first line must be {MAGIC}')
    marks, seen = [], {}
    for number, line in enumerate(lines[1:], start=2):
        try:
            mark = parse_line(line)
        except MarkError as error:
            raise MarkError(f'{label} line {number}: {error}') from None
        if mark is None:
            continue
        key = mark['name'].lower()
        if key in seen:
            raise MarkError(f'{label} line {number}: name {mark["name"]!r} again (first on line {seen[key]})')
        seen[key] = number
        marks.append(mark)
    return marks


def load(path=PUBLIC):
    path = Path(path)
    return parse(path.read_bytes(), str(path.name))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('check')
    check.add_argument('files', nargs='*', type=Path)
    show = sub.add_parser('show')
    show.add_argument('name')
    show.add_argument('file', nargs='?', type=Path, default=PUBLIC)
    args = parser.parse_args(argv)
    try:
        if args.command == 'check':
            for path in args.files or [PUBLIC]:
                marks = load(path)
                print(f'{path}: {len(marks)} marks OK')
            return 0
        for mark in load(args.file):
            if mark['name'].lower() == args.name.lower():
                print(json.dumps(mark, indent=1))
                return 0
        print(f'no mark {args.name!r} in {args.file}', file=sys.stderr)
        return 1
    except (MarkError, OSError) as error:
        print(f'camera marks: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
