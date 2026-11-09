#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The dialogue choices of the masters, branch by branch (DIALOGUE-CHOICES-62): every result script's Choice call,
and for each of its numbers whether the topic holds an answer that the engine's dialogue runner can pick for it.

The rule is the original's and OpenMW 0.51's (DialogueManager::questionAnswered, Filter::search; our own code): a
pick sets the choice to its number and the same topic is searched again from its first answer; the first answer
whose filters all pass is said. So a branch N of a Choice in topic T is reached by the first answer of T, in the
original's order, that the speaker can say, whose Choice filters (if any) hold for N and whose other filters pass.
An answer without a Choice filter and without any other filter ends the search for every number (it shadows the
answers after it).

A branch is:
  reachable    an answer for it whose every filter the runner reads live or decides when the table is built
  start_value  only answers with a filter the runner reads as its start-of-game value (the fixture)
  unread       only answers with a filter the runner never passes (a function it does not read)
  plain        no answer with a Choice filter for it: an answer without one is said, as in the original (not a
               branch of its own; the runner reads its filters)
  shadowed     its answers come after an answer that always passes
  none         nothing in the topic answers it

Only the numbers and the records' ids are written (docs/dialogue-choices.json); no text of the game.

  python3 tools/dialogue_choices.py measure --data-files DIR    read the masters, write docs/dialogue-choices.json
  python3 tools/dialogue_choices.py check                       the JSON is valid and its counts add up
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):     # src first: tools/mwad.py is the command, src/mwad the package
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

OUT = ROOT / 'docs' / 'dialogue-choices.json'
SCHEMA = 'dialogue-choices 1'
MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
TABLE_MASTER = 'Morrowind.esm'      # the dialogue table the engine reads is built from it (tools/dialogue_lut.py)
STATUSES = ('reachable', 'start_value', 'unread', 'plain', 'shadowed', 'none')
# the SCVR kinds the runner reads (aw_glut.c AW_GlutCond with aw_mwhost.c's live hooks, or decided per speaker when
# the table is built: mwad.dialogue Context.static)
READ_KINDS = {'Global', 'Local', 'NotLocal', 'Journal', 'Item', 'Dead', 'NotId', 'NotFaction', 'NotClass', 'NotRace',
              'NotCell'}
STATIC_FUNCTIONS = {'Level', 'Reputation', 'Hello', 'Fight', 'Flee', 'Alarm'}
CHOICE_LINE = re.compile(r'(?i)^\s*choice\b(.*)$')
PAIR = re.compile(r'"([^"]*)"\s*,?\s*(-?\d+)')
SPEAKER_TAGS = ('ONAM', 'RNAM', 'CNAM', 'FNAM', 'ANAM')


def _strip_comment(line):
    out, quoted = [], False
    for ch in line:
        if ch == '"':
            quoted = not quoted
        elif ch == ';' and not quoted:
            break
        out.append(ch)
    return ''.join(out)


def choice_calls(script):
    """[[(text, number)]] of the Choice calls of a result script, one list per call, in order."""
    out = []
    for line in (script or '').replace('\r', '\n').split('\n'):
        m = CHOICE_LINE.match(_strip_comment(line))
        if m:
            out.append([(t, int(n)) for t, n in PAIR.findall(m.group(1))])
    return out


def classify(function):
    """'read', 'start' or 'never': how the runner reads one SCVR condition (Choice apart)."""
    from dialogue_lut import LIVE_FUNCTIONS
    from mwad.dialogue import FIXTURE
    if function in READ_KINDS or function in LIVE_FUNCTIONS or function in STATIC_FUNCTIONS:
        return 'read'
    if function in FIXTURE or function == 'PcClothingModifier':
        return 'start'
    return 'never'


def _speaker(fields):
    from mwad.esm import text
    return tuple(text(fields, t).casefold() for t in SPEAKER_TAGS)


def _compatible(a, b):
    """Some speaker can say both INFOs (each speaker filter empty in one of them or the same)."""
    return all(not x or not y or x == y for x, y in zip(a, b))


def _covers(answer, offer):
    """ANSWER's speaker filters hold whenever OFFER's do (each empty or the same as OFFER's)."""
    return all(not x or x == y for x, y in zip(answer, offer))


def _parsed(fields):
    from mwad.dialogue import _parsed as parsed
    return parsed(fields)


def _rules(fields):
    p = _parsed(fields)
    return p[10] if p else ()


def branch(infos, offer, number):
    """(status, INFO index or -1, [function names not read]) of choice NUMBER of the INFO OFFER of a topic (its
    INFO list INFOS in the original's order)."""
    from mwad.dialogue import _compare
    me = _speaker(infos[offer])
    found = plain = None
    for i, fields in enumerate(infos):
        p = _parsed(fields)
        if p is None or not _compatible(_speaker(fields), me):
            continue
        disposition, _rank, _gender, pcrank, *_rest, rules = p
        choices = [c for c in rules if c[0] == 'Choice']
        if not choices and plain is None and all(classify(c[0]) == 'read' for c in rules):
            plain = i                   # an answer without a Choice filter the runner can pick for any number
        if choices:
            if not all(_compare(number, op, value) for _f, _v, op, value in choices):
                continue
            ways = [classify(c[0]) for c in rules if c[0] != 'Choice']
            if 'never' in ways:
                found = found or ('unread', i, sorted({c[0] for c in rules if classify(c[0]) == 'never'}))
                continue
            if 'start' in ways:
                found = found or ('start_value', i, sorted({c[0] for c in rules if classify(c[0]) == 'start'}))
                continue
            return 'reachable', i, []
        if not rules and disposition <= 0 and pcrank == -1 and not p[8] and _covers(_speaker(fields), me):
            # an answer that always passes for this speaker: the search ends here
            later = any(c[0] == 'Choice' and _compare(number, c[2], c[3]) for f in infos[i + 1:] for c in _rules(f))
            return found or (('shadowed' if later else 'plain'), i, [])
    return found or (('plain', plain, []) if plain is not None else ('none', -1, []))


def audit(topics, master):
    """{'counts': {...}, 'branches': [row]} of a master's topics ({folded name: [INFO fields]})."""
    from mwad.esm import text
    counts = {'infos_with_choice': 0, 'calls': 0, 'branches': 0, 'max_options': 0, 'max_text': 0,
              'status': {s: 0 for s in STATUSES}}
    rows = []
    for name in sorted(topics):
        infos = topics[name]
        for i, fields in enumerate(infos):
            calls = choice_calls(text(fields, 'BNAM'))
            if not calls:
                continue
            counts['infos_with_choice'] += 1
            for call in calls:
                counts['calls'] += 1
                counts['max_options'] = max(counts['max_options'], len(call))
                for words, number in call:
                    counts['max_text'] = max(counts['max_text'], len(words))
                    status, at, why = branch(infos, i, number)
                    counts['branches'] += 1
                    counts['status'][status] += 1
                    rows.append({'master': master, 'topic': name, 'info': text(fields, 'INAM'),
                                 'speaker': text(fields, 'ONAM').casefold(), 'choice': number, 'status': status,
                                 'answer': text(infos[at], 'INAM') if at >= 0 else '', 'why': why})
    return {'counts': counts, 'branches': rows}


def measure(data):
    import greeting_lut as G
    from mwad.paths import child_ci
    doc = {'schema': SCHEMA, 'table_master': TABLE_MASTER, 'masters': {}, 'not_reachable': []}
    for n, master in enumerate(MASTERS, 1):
        try:
            path = child_ci(Path(data), master)
        except (FileNotFoundError, OSError):
            path = None
        if path is None or not Path(path).is_file():
            print('=== PHASE %d/%d: %s: not in the data, skipped ===' % (n, len(MASTERS), master), flush=True)
            continue
        print('=== PHASE %d/%d: %s: reading the dialogue ===' % (n, len(MASTERS), master), flush=True)
        _kinds, topics = G.load(path)
        got = audit(topics, master)
        doc['masters'][master] = dict(got['counts'], in_table=master == TABLE_MASTER)
        doc['not_reachable'] += [r for r in got['branches'] if r['status'] not in ('reachable', 'plain')]
        c = got['counts']
        print('%s: %d INFOs call Choice (%d calls, %d branches): %s' % (
            master, c['infos_with_choice'], c['calls'], c['branches'],
            ', '.join('%s %d' % kv for kv in c['status'].items())), flush=True)
    return doc


def problems(doc):
    out = []
    if doc.get('schema') != SCHEMA:
        out.append('schema must be %r' % SCHEMA)
    listed = {}
    for r in doc.get('not_reachable', []):
        if r.get('status') not in STATUSES or r['status'] in ('reachable', 'plain'):
            out.append('not_reachable: bad status %r' % r.get('status'))
        listed[r.get('master')] = listed.get(r.get('master'), 0) + 1
    for master, c in (doc.get('masters') or {}).items():
        if sum(c.get('status', {}).get(s, 0) for s in STATUSES) != c.get('branches'):
            out.append('%s: the statuses do not add up to the branches' % master)
        want = sum(c['status'].get(s, 0) for s in STATUSES if s not in ('reachable', 'plain'))
        if listed.get(master, 0) != want:
            out.append('%s: %d branches listed as not reachable, the counts say %d' % (master, listed.get(master, 0),
                                                                                      want))
    if not doc.get('masters'):
        out.append('no masters measured')
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('command', choices=('measure', 'check'))
    p.add_argument('--data-files', type=Path)
    p.add_argument('--out', type=Path, default=OUT)
    a = p.parse_args(argv)
    if a.command == 'measure':
        if not a.data_files:
            p.error('measure needs --data-files')
        doc = measure(a.data_files)
        bad = problems(doc)
        if bad:
            print('\n'.join('dialogue choices: ' + b for b in bad))
            return 1
        a.out.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        print('wrote %s' % a.out)
        return 0
    bad = problems(json.loads(a.out.read_text(encoding='utf-8')))
    print('\n'.join('dialogue choices: ' + b for b in bad) if bad else 'dialogue choices ok')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
