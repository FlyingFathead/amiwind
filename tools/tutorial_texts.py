#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The tutorial texts' table (OPENING-TUTORIAL-KEYS-65): config/tutorial-texts.json -> engine/aga/src/aw_tutorial_table.inc.

  tutorial_texts.py render   write the .inc from the JSON
  tutorial_texts.py check    fail when the .inc is not the JSON's rendering
  tutorial_texts.py hash TEXT   the row hash of a text (normalized FNV-1a, as aw_tutorial_rules.c AW_TutorialHash)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'config' / 'tutorial-texts.json'
OUT = ROOT / 'engine' / 'aga' / 'src' / 'aw_tutorial_table.inc'
# hide: the box is not shown at all, the box before it already says it in our text (TUTORIAL-BOX-SHOWN-TWICE-65);
# its text is ""
KINDS = ('replace', 'add', 'once', 'hide')
ONCE, HIDE = 1, 2   # aw_tutorial.h AW_TUTORIAL_ONCE, AW_TUTORIAL_HIDE
LINE_MAX = 36       # characters a line, the key counted as 5 (the 320-pixel box, the maintainer's format)


def text_hash(text):
    h = 2166136261
    for b in ' '.join(text.lower().split()).encode('cp1252'):
        h ^= b
        h = (h * 16777619) & 0xffffffff
    return h


def load():
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    if data.get('format') != 'AmiWind tutorial texts 1':
        raise ValueError('unknown format')
    return check_rows(data['rows'])


def check_rows(rows):
    """ROWS checked (ValueError on the first bad one); returns ROWS."""
    seen = set()
    texts = {}
    for row in rows:
        h = int(row['hash'], 16)
        if h in seen or not 0 <= h <= 0xffffffff:
            raise ValueError('bad or repeated hash ' + row['hash'])
        seen.add(h)
        if row['kind'] == 'hide':
            if not row.get('source') or row.get('text', '') != '':
                raise ValueError('a "hide" row has a source and no text: ' + row['hash'])
            continue
        if row['kind'] not in KINDS or not row.get('source') or not row.get('text'):
            raise ValueError('incomplete row ' + row['hash'])
        # TUTORIAL-BOX-SHOWN-TWICE-65: two boxes shown in turn with one text read as the same box twice; only the other
        # branch of the same if/else (never shown with it) may share the text, named by "alternative_of"
        # (an "add" row shows its own original text first, so two of them never read alike)
        if row['kind'] != 'add' and row['text'] in texts and row.get('alternative_of') != texts[row['text']]:
            raise ValueError('rows %s and %s show the same text: hide the second, or name the first in '
                             '"alternative_of" when the script shows only one of them' % (texts[row['text']], row['hash']))
        if row['kind'] != 'add':
            texts.setdefault(row['text'], row['hash'])
        if row['kind'] == 'add' and '{text}' not in row['text']:
            raise ValueError('an "add" row keeps the original text: ' + row['hash'])
        if row['kind'] != 'add' and '{text}' in row['text']:
            raise ValueError('a "replace" row does not show the original text: ' + row['hash'])
        if '{key:' not in row['text'] and '^Action' not in row['text']:
            raise ValueError('a row names no bound key: ' + row['hash'])
        for command in re.findall(r'\{key:([^}]*)\}', row['text']):
            if not re.fullmatch(r'[+a-z_0-9: ]{2,40}', command):
                raise ValueError('bad command %r in %s' % (command, row['hash']))
        for line in row['text'].split('\n'):
            if '{text}' in line:
                continue
            shown = re.sub(r'\{key:[^}]*\}', 'XXXXX', re.sub(r'\^Action\w+', 'X', line)).replace('\t', '  ')
            if len(shown) > LINE_MAX:
                raise ValueError('line over %d characters in %s: %r' % (LINE_MAX, row['hash'], line))
        if any((ord(c) > 126 or c in '"\\') and c not in '\n\t' for c in row['text']):
            raise ValueError('plain ASCII without quotes or backslashes: ' + row['hash'])
    return rows


def render(rows):
    lines = ['/* Generated from config/tutorial-texts.json by tools/tutorial_texts.py render; do not edit. */']
    for row in rows:
        lines.append('/* %s (%s) */' % (row['source'].replace('*/', '* /'), row['kind']))
        flag = ONCE if row['kind'] == 'once' else HIDE if row['kind'] == 'hide' else 0
        lines.append('{%sUL,%d,"%s"},' % (row['hash'].lower(), flag, row['text'].replace('\n', '\\n').replace('\t', '\\t')))
    return '\n'.join(lines) + '\n'


def main(argv):
    if len(argv) >= 2 and argv[1] == 'hash':
        print('0x%08x' % text_hash(' '.join(argv[2:])))
        return 0
    text = render(load())
    if len(argv) == 2 and argv[1] == 'render':
        OUT.write_text(text, encoding='utf-8', newline='\n')
        print('wrote', OUT.relative_to(ROOT))
        return 0
    if len(argv) == 2 and argv[1] == 'check':
        ok = OUT.is_file() and OUT.read_text(encoding='utf-8') == text
        print('tutorial table ok' if ok else 'tutorial table out of date: run tools/tutorial_texts.py render')
        return 0 if ok else 1
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
