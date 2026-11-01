#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The class questions (CHARGEN-CENSUS-57 (c)): the ten questions the Census Office asks to pick a class.

The original keeps them in the install's Morrowind.ini, sections [Question 1] .. [Question 10], each with
Question, AnswerOne, AnswerTwo and AnswerThree (a Sound line too, not used here). The first answer of each counts
toward combat, the second toward magic, the third toward stealth; the engine picks the class from the three counts
(aw_character.c, the rule OpenMW 0.51 applies). The output is private game text: character/questions.awq.

Format AWQ1 (little-endian):
  "AWQ1" u8 count (10, or 0 when the ini is missing or incomplete: the game then offers only the class list and
  the custom class)
  count x 4 strings (question, answer one, two, three), each u16 length then that many cp1252 bytes (no NUL)
A stage of its own, depending on nothing: no other stage's input or cache key changes. The ini is named on the
command line (--ini), so the stage key hashes it.
"""
import argparse, hashlib, json, re
from pathlib import Path

QUESTIONS = 10
FIELDS = ('Question', 'AnswerOne', 'AnswerTwo', 'AnswerThree')
MAX_TEXT = 400        # bytes per string (the engine's bound: aw_character.c QUIZ_TEXT)


def ini_sections(text):
    """{section name (folded): {key (folded): value}} of an ini text; later duplicates do not replace earlier."""
    out, current = {}, None
    for line in text.splitlines():
        line = line.strip()
        match = re.fullmatch(r'\[(.+)\]', line)
        if match:
            current = out.setdefault(match.group(1).strip().casefold(), {})
        elif current is not None and '=' in line and not line.startswith(';'):
            key, _, value = line.partition('=')
            current.setdefault(key.strip().casefold(), value.strip())
    return out


def clean(text):
    raw = ''.join(c for c in text if ord(c) >= 32).strip().encode('cp1252', 'replace')
    if not raw or len(raw) > MAX_TEXT:
        raise ValueError('question text empty or too long')
    return raw


def questions(text):
    """The ten questions as [(question, answer one, two, three)] (bytes), or [] when any part is missing."""
    sections = ini_sections(text)
    rows = []
    for n in range(1, QUESTIONS + 1):
        section = sections.get('question %d' % n)
        if not section or any(not section.get(f.casefold()) for f in FIELDS):
            return []
        try:
            rows.append(tuple(clean(section[f.casefold()]) for f in FIELDS))
        except ValueError:
            return []
    return rows


def encode(rows):
    out = bytearray(b'AWQ1' + bytes([len(rows)]))
    for row in rows:
        for part in row:
            out += len(part).to_bytes(2, 'little') + part
    return bytes(out)


def build(ini):
    text = None
    if ini is not None and Path(ini).is_file():
        text = Path(ini).read_bytes().decode('cp1252', 'replace')
    rows = questions(text) if text is not None else []
    payload = encode(rows)
    return payload, {'format': 'AWQ1', 'questions': len(rows), 'bytes': len(payload),
                     'sha256': hashlib.sha256(payload).hexdigest(),
                     'ini': 'found' if text is not None else 'missing'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ini', type=Path, help="The install's Morrowind.ini (left out when the install has none)")
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    payload, report = build(a.ini)
    (a.out / 'id1/character').mkdir(parents=True, exist_ok=True)
    (a.out / 'id1/character/questions.awq').write_bytes(payload)
    (a.out / 'chargen-receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('[chargen] %d class questions (ini %s), %d bytes' % (report['questions'], report['ini'], report['bytes']),
          flush=True)


if __name__ == '__main__':
    main()
