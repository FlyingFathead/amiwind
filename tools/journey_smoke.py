#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Gameplay journey smoke (GAMEPLAY-JOURNEY-SMOKE-66; docs/GAME_RECORDER.md "Gameplay journeys").

A journey is a play route in the session-script language of tools/engine_smoke.py (cmd / key / xdo / wait / shot /
rec / recstop / state), split into parts that run as separate emulator sessions (a part after the first starts a
fresh engine and loads the save the part before wrote), plus three words of its own:

  step N TITLE            a numbered stage of the journey (its checks are reported under it)
  probe NAME COMMAND...   read one value from the game: the console COMMAND's answer (a getitemcount, a journal
                          read, a control switch, a health read, a kill, the actor list), or with "state KEY" the
                          probe's state-file value (map, screen, local); kept as NAME
  expect NAME OP VALUE    a check: OP is == != > < >= <=; VALUE a number, another probe's NAME, or NAME+N / NAME-N
  expect dead NAME IN LIST   the actor whose reference the probe NAME took (a kill) shows DEAD in the actor list the
                          probe LIST read ("chim actors list"); alive in it fails (it came back), missing from it fails;
                          NAME may also be a reference number (expect dead 262014 in list_end)
  expect alive REF IN LIST   the actor REF (a probe's reference or a number) is in the list and not DEAD
  expect fighting REF IN LIST  the actor REF is in the list and FIGHTING
  expect has NAME TEXT    the probe NAME's answer holds TEXT (case-insensitive)
  expect lacks NAME TEXT  the probe NAME's answer does not hold TEXT (an object that must stay gone)
  expect autosaves from step N   every map change from step N on wrote the game's autosave (ENGINE-REGRESSION-GUARDS-67,
                          SAVE-AUTOSAVE-REGRESSED-67): in the console of step N's part after its marker, and of each
                          later part after its "Game restored" line, each map load ("Scene ready", not a streamed
                          crossing, not a load of a save) is followed by a "Saved Autosave" line before the next load or
                          the part's end; the failure names each map change without one
  expect known ID CHECK   any of the checks above, for a step that cannot pass today: ID is its register entry. Its
                          result is printed as KNOWN (failing as registered) or as a PASS that says the gap closed;
                          it is not counted in the journey's result (ENDGAME-HEART-SESSION-66: the chamber's collapse)
  pick NAME PROBE after|before TEXT   a number read from the answer of an earlier probe: the first number right
                          after (or right before) TEXT (case-sensitive), kept as NAME like a probe's value (the counts of
                          a long status answer: "pick matched_now status before matched")
  part LETTER             a new emulator session from here (the first line of the file is always part A)
  emu KEY=VALUE           an emulator option for the part's session, passed into its script as it stands
                          (tools/engine_smoke.py takes it: emu deterministic=1 serves the remote-console folder on the
                          emulator thread, the way out of the test sessions' stall, CHIM-SEYDA-BALMORA-LOAD-HANG-43)

and the walker's steps of tools/engine_smoke.py (JOURNEY-WALK-DIALOGUE-DESYNC-66), which wait for the game and stop the
session at the first wrong turn instead of running on blind: walkto X Y SECS, waitfor KEY SECS TEXT, boxes, mark,
saw SECS TEXT, topic NAME (a dialogue topic or answer chosen by its name in the window's Find box), face X Y Z, aimed
REF [SECS], lookat REF. A part whose session stopped is reported with the step it stopped in and why; the checks it never reached
say so.

The checks read the game's own state (console answers and the state file), never pictures.

  journey_smoke.py scripts JOURNEY OUTDIR   writes OUTDIR/part-<L>.txt (session scripts) and OUTDIR/journey.json
  journey_smoke.py judge JOURNEY RUNDIR...  (JOURNEY may be a run's own scripts/journey.json, the journey it played)
                                            reads RUNDIR/logs/steps.log and RUNDIR/logs/console.log of each part's
                                            session (in part order), prints one line per check and the last line
                                            "JOURNEY RESULT PASS n/n checks" or "JOURNEY RESULT FAIL ..."; exit 1 on FAIL
  journey_smoke.py check JOURNEY            the file parses and every expect names probes defined before it
  journey_smoke.py walkthrough JOURNEY      the journey as a checklist to play by hand: each step, the console
                                            lines to type and what their answers must show
Standard library only.
"""
import json
import re
import sys
from pathlib import Path

SESSION_WORDS = ('cmd', 'key', 'xdo', 'wait', 'shot', 'rec', 'recstop', 'state', 'emu')
# the walker's steps (tools/engine_smoke.py WALKER-STEPS), each with the form its arguments must have
NUM = r'-?\d+(?:\.\d+)?'
WALKER_WORDS = {
    'walkto': re.compile(r'%s %s \d+' % (NUM, NUM)),
    'waitfor': re.compile(r'[a-z_]+ \d+ \S.*'),
    'boxes': re.compile(r''),
    'mark': re.compile(r''),
    'saw': re.compile(r'\d+ \S.*'),
    'topic': re.compile(r'\S.*'),
    'face': re.compile(r'%s %s %s' % (NUM, NUM, NUM)),
    'aimed': re.compile(r'\d+( \d+)?'),
    'lookat': re.compile(r'\d+'),
}
OPS = ('==', '!=', '>=', '<=', '>', '<')
MARK = 'JOURNEY'
PROBE_WAIT = 2          # seconds of game time after a console probe, for its answer to print


class JourneyError(Exception):
    pass


def parse(text):
    """The journey as {"parts": [{"name": L, "lines": [...]}], "steps": [...], "probes": {...}, "expects": [...]}."""
    parts = [{'name': 'A', 'lines': []}]
    steps, probes, expects, talks = [], {}, [], []
    step = None
    for no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        word, _, rest = line.partition(' ')
        rest = rest.strip()
        where = 'line %d' % no
        if word == 'part':
            if not re.fullmatch(r'[A-Z]', rest):
                raise JourneyError('%s: part takes one capital letter' % where)
            if rest != 'A' or parts[-1]['lines']:
                if any(p['name'] == rest for p in parts):
                    raise JourneyError('%s: part %s twice' % (where, rest))
                parts.append({'name': rest, 'lines': []})
            continue
        part = parts[-1]
        if word == 'step':
            m = re.fullmatch(r'(\d+)\s+(.+)', rest)
            if not m:
                raise JourneyError('%s: step N TITLE' % where)
            step = int(m.group(1))
            steps.append({'step': step, 'title': m.group(2), 'part': part['name']})
            part['lines'].append('cmd echo %s STEP %d' % (MARK, step))
        elif word == 'probe':
            m = re.fullmatch(r'([a-z][a-z0-9_]*)\s+(.+)', rest)
            if not m:
                raise JourneyError('%s: probe NAME COMMAND' % where)
            name, command = m.groups()
            if name in probes:
                raise JourneyError('%s: probe %s twice' % (where, name))
            kind = 'state' if command.startswith('state ') else 'console'
            probes[name] = {'command': command, 'kind': kind, 'part': part['name'], 'step': step}
            part['lines'].append('cmd echo %s PROBE %s' % (MARK, name))
            if kind == 'state':
                part['lines'].append(command)
            else:
                part['lines'] += ['cmd ' + command, 'wait %d' % PROBE_WAIT]
        elif word == 'pick':
            m = re.fullmatch(r'([a-z][a-z0-9_]*)\s+([a-z][a-z0-9_]*)\s+(after|before)\s+(\S.*)', rest)
            if not m:
                raise JourneyError('%s: pick NAME PROBE after|before TEXT' % where)
            name, source, side, needle = m.groups()
            if name in probes:
                raise JourneyError('%s: probe %s twice' % (where, name))
            if source not in probes:
                raise JourneyError('%s: pick reads probe %s before it is defined' % (where, source))
            probes[name] = {'command': '%s "%s" in %s' % (side, needle, source), 'kind': 'pick', 'from': source,
                            'side': side, 'text': needle, 'part': probes[source]['part'], 'step': step}
        elif word == 'expect':
            e = parse_expect(rest, probes, where, step)
            if e['kind'] == 'autosaves' and e['from'] not in [s['step'] for s in steps]:
                raise JourneyError('%s: expect autosaves from step %d: no step %d before it' % (where, e['from'], e['from']))
            expects.append(e)
        elif word in SESSION_WORDS:
            if line.startswith('cmd echo %s ' % MARK):
                raise JourneyError('%s: the %s marker lines are written by the tool' % (where, MARK))
            part['lines'].append(line)
        elif word in WALKER_WORDS:
            if not WALKER_WORDS[word].fullmatch(rest):
                raise JourneyError('%s: %s %r is not the walker step\'s form (tools/engine_smoke.py WALKER-STEPS)'
                                   % (where, word, rest))
            part['lines'].append(line)
            if word == 'topic':
                talks.append({'step': step, 'topic': rest})
        else:
            raise JourneyError('%s: unknown word %r' % (where, word))
    if not expects:
        raise JourneyError('no expect line')
    return {'parts': parts, 'steps': steps, 'probes': probes, 'expects': expects, 'talks': talks}


KNOWN_ID = r'[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+'


def parse_expect(rest, probes, where, step):
    m = re.fullmatch(r'known\s+(%s)\s+(\S.*)' % KNOWN_ID, rest)
    if m:
        if m.group(2).startswith('known '):
            raise JourneyError('%s: expect known takes one register id' % where)
        e = parse_expect(m.group(2), probes, where, step)
        e['known'] = m.group(1)
        return e
    if re.match(r'known\b', rest):
        raise JourneyError('%s: expect known REGISTER-ID CHECK (the register id of the gap, e.g. ENDGAME-CHAMBER-COLLAPSE-63)'
                           % where)
    m = re.fullmatch(r'autosaves\s+from\s+step\s+(\d+)', rest)
    if m:
        return {'kind': 'autosaves', 'from': int(m.group(1)), 'step': step, 'text': rest}
    if re.match(r'autosaves\b', rest):
        raise JourneyError('%s: expect autosaves from step N' % where)
    m = re.fullmatch(r'(dead|alive|fighting)\s+(\w+)\s+in\s+(\w+)', rest)
    if m:
        # the actor: a probe that took a reference (a kill), or the reference number itself
        for n in m.groups()[1:]:
            if n not in probes and not (n == m.group(2) and n.isdigit()):
                raise JourneyError('%s: expect names probe %s before it is defined' % (where, n))
        return {'kind': m.group(1), 'ref': m.group(2), 'list': m.group(3), 'step': step, 'text': rest}
    m = re.fullmatch(r'(has|lacks)\s+(\w+)\s+(.+)', rest)
    if m:
        if m.group(2) not in probes:
            raise JourneyError('%s: expect names probe %s before it is defined' % (where, m.group(2)))
        return {'kind': m.group(1), 'probe': m.group(2), 'needle': m.group(3), 'step': step, 'text': rest}
    m = re.fullmatch(r'(\w+)\s*(==|!=|>=|<=|>|<)\s*(\S+)', rest)
    if not m:
        raise JourneyError('%s: expect NAME OP VALUE, expect dead NAME in LIST or expect has NAME TEXT' % where)
    name, op, value = m.groups()
    if name not in probes:
        raise JourneyError('%s: expect names probe %s before it is defined' % (where, name))
    vm = re.fullmatch(r'(-?\d+(?:\.\d+)?)|([a-z][a-z0-9_]*)(?:([+-])(\d+(?:\.\d+)?))?', value)
    if not vm:
        raise JourneyError('%s: bad value %r' % (where, value))
    # a bare word that is no probe is a text to compare with (== / != only: "expect talk_screen != game")
    if vm.group(2) and vm.group(2) not in probes and (vm.group(3) or op not in ('==', '!=')):
        raise JourneyError('%s: expect names probe %s before it is defined' % (where, vm.group(2)))
    return {'kind': 'compare', 'probe': name, 'op': op, 'value': value, 'step': step, 'text': rest}


def write_scripts(journey_path, outdir):
    j = parse(Path(journey_path).read_text(encoding='utf-8'))
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for p in j['parts']:
        head = ['# generated by tools/journey_smoke.py from %s, part %s; do not edit' % (Path(journey_path).name, p['name'])]
        (out / ('part-%s.txt' % p['name'])).write_text('\n'.join(head + p['lines']) + '\n', encoding='utf-8', newline='\n')
    (out / 'journey.json').write_text(json.dumps(j, indent=1) + '\n', encoding='utf-8', newline='\n')
    return [p['name'] for p in j['parts']]


# --- reading a run ---
def console_answers(text):
    """{probe name: the console lines printed after its marker, up to the next marker}."""
    answers, cur = {}, None
    for line in text.splitlines():
        s = line.strip()
        m = re.fullmatch(MARK + r' (PROBE|STEP) (\S+)', s)
        if m:
            cur = m.group(2) if m.group(1) == 'PROBE' else None
            if cur is not None:
                answers[cur] = []
            continue
        if cur is not None:
            answers[cur].append(s)
    return answers


def state_answers(text):
    """{probe name: value} from steps.log: the first "state KEY: VALUE" line after the probe's marker command."""
    vals, cur = {}, None
    for line in text.splitlines():
        m = re.search(r'cmd echo ' + MARK + r' PROBE (\S+)', line)
        if m:
            cur = m.group(1)
            continue
        m = re.search(r'\bstate (\S+): ?(.*)$', line)
        if m and cur is not None:
            vals[cur] = m.group(2).strip()
            cur = None
    return vals


# value extractors, tried in order on a console answer
NUMBER_FORMS = (
    (re.compile(r'chim actors kill: .*\(ref (\d+)'), 'ref'),
    (re.compile(r'dbg mwscript call journal: \S+ (-?\d+)'), 'journal'),
    (re.compile(r'reads (\d) \((?:off|on)\)'), 'switch'),
    (re.compile(r'dbg mwscript call getglobal: \S+ = (-?[\d.]+)'), 'global'),
    (re.compile(r'(?:get|add|remove)\w* .* -> (-?[\d.]+)\s*$'), 'count'),
    (re.compile(r'^\w+ -> (-?[\d.]+)\s*$'), 'value'),
    (re.compile(r'(\d+) landed'), 'landed'),
)
REFUSALS = re.compile(r'no such (?:item|reference|actor|quest|global)|not possible|no resident|no living actor|'
                      r'unknown command|refused', re.I)


def number_of(lines):
    for rx, _ in NUMBER_FORMS:
        for line in lines:
            m = rx.search(line)
            if m:
                return float(m.group(1))
    return None


def actor_rows(lines):
    """{ref: "DEAD" | "FIGHTING" | "ALIVE"} from a "chim actors list" answer."""
    rows = {}
    for line in lines:
        m = re.match(r'\d+ .* ref (\d+) cell ', line)
        if m:
            rows[int(m.group(1))] = 'DEAD' if ' DEAD' in line else 'FIGHTING' if ' FIGHTING' in line else 'ALIVE'
    return rows


def session_stop(steps_text, start=0):
    """Where a part's session stopped early: (the journey step it was in, 0 = before step 1; the reason) when its
    result is a FAIL (a walker step's wrong turn, a stall, a crash), else None. The first FAIL result line counts (the
    session launcher appends a crash line after the probe's own). START: the step in effect when the part begins (a
    later part goes on in the last step of the part before it until its own first step)."""
    step = start
    for line in steps_text.splitlines():
        m = re.search(r'cmd echo ' + MARK + r' STEP (\d+)', line)
        if m:
            step = int(m.group(1))
            continue
        m = re.search(r'smoke RESULT (FAIL.*)$', line)
        if m:
            return step, m.group(1).replace(WARP_MARK, '').strip()
    return None


# What a session's result line ends with when it ran in the emulator's warp mode (tools/engine_smoke.py WARP_MARK; the
# decision of 17 November 2026: warp is off for every performance and bench test). The journey's checks read the game's
# state and hold in warp; its times never do, and its own result line then says so.
WARP_MARK = ' [warp run: no timing verdict]'


def warp_run(steps_text):
    """True when a session's own result line says it ran in warp."""
    return any('smoke RESULT' in line and line.rstrip().endswith(WARP_MARK) for line in steps_text.splitlines())


def judge(journey, runs):
    """runs: [(steps.log text, console.log text)] in part order. Returns (passed, lines); the result line of a run whose
    sessions ran in warp ends with WARP_MARK."""
    passed, out = judge_checks(journey, runs)
    if any(run is not None and warp_run(run[0]) for run in runs) and out and out[-1].startswith('JOURNEY RESULT'):
        out[-1] += WARP_MARK
    return passed, out


def judge_checks(journey, runs):
    raw, values, missing_parts, stops, consoles = {}, {}, [], {}, {}
    for part, run in zip(journey['parts'], runs):
        if run is None:
            missing_parts.append(part['name'])
            continue
        steps_text, console_text = run
        consoles[part['name']] = console_text
        names = [p['name'] for p in journey['parts']]
        before = [s['step'] for s in journey['steps'] if names.index(s['part']) < names.index(part['name'])]
        stop = session_stop(steps_text, before[-1] if before else 0)
        if stop:
            stops[part['name']] = stop
        con, sta = console_answers(console_text), state_answers(steps_text)
        for name, pr in journey['probes'].items():
            if pr['part'] != part['name']:
                continue
            if pr['kind'] == 'state':
                if name in sta:
                    raw[name] = [sta[name]]
                    try:
                        values[name] = float(sta[name])
                    except ValueError:
                        values[name] = sta[name]
            elif name in con:
                raw[name] = con[name]
                values[name] = number_of(con[name])
    # the picks: numbers read from the answers of probes read above (in file order, so a pick may read a pick)
    for name, pr in journey['probes'].items():
        if pr['kind'] != 'pick' or pr['from'] not in raw:
            continue
        v = pick_number(raw[pr['from']], pr['side'], pr['text'])
        raw[name] = ['%s "%s" in %s: %s' % (pr['side'], pr['text'], pr['from'], 'no number' if v is None else '%g' % v)]
        values[name] = v
    out, fails, total, known_open, known_closed = [], 0, 0, [], []
    titles = {s['step']: s['title'] for s in journey['steps']}
    for e in journey['expects']:
        ok, why = check(e, journey, raw, values, consoles)
        if not ok:
            names = [n for n in (e.get('probe'), e.get('ref'), e.get('list')) if n and not n.isdigit()]
            part = journey['probes'][names[0]]['part'] if names else None
            if names and part in stops and any(n not in raw for n in names):
                why = 'not reached: part %s stopped %s (%s)' % (
                    part, 'in step %d' % stops[part][0] if stops[part][0] else 'before step 1', stops[part][1][:200])
        head = 'step %s (%s): %s' % (e['step'], titles.get(e['step'], '?'), e['text'])
        if e.get('known'):
            # a known gap: reported, never counted in the result; a pass says the gap closed (the register to update)
            if ok:
                known_closed.append(e['known'])
                out.append('PASS %s (known gap %s: passes now, check the register)' % (head, e['known']))
            else:
                known_open.append(e['known'])
                out.append('KNOWN %s: %s [known gap %s]' % (head, why, e['known']))
            continue
        total += 1
        if not ok:
            fails += 1
        out.append('%s %s%s' % ('PASS' if ok else 'FAIL', head, '' if ok else ': ' + why))
    if missing_parts:
        out.append('FAIL parts not run: %s' % ', '.join(missing_parts))
    for name in sorted(stops):
        out.append('STOP part %s %s: %s' % (name, 'in step %d' % stops[name][0] if stops[name][0] else 'before step 1',
                                            stops[name][1]))
    failed_steps = sorted({e['step'] for e, line in zip(journey['expects'], out) if line.startswith('FAIL')},
                          key=lambda s: (s is None, s))
    known = ''
    if known_open or known_closed:
        known = '; known gaps: %d of %d checks still failing%s%s' % (
            len(known_open), len(known_open) + len(known_closed),
            ' (%s)' % ', '.join(sorted(set(known_open))) if known_open else '',
            ', closed now: %s' % ', '.join(sorted(set(known_closed))) if known_closed else '')
    if fails or missing_parts or stops:
        out.append('JOURNEY RESULT FAIL %d of %d checks failed (steps %s)%s%s%s' % (
            fails, total, ', '.join(str(s) for s in failed_steps) or '-', known,
            '; parts not run: ' + ', '.join(missing_parts) if missing_parts else '',
            ''.join('; part %s stopped %s' % (n, 'in step %d' % stops[n][0] if stops[n][0] else 'before step 1')
                    for n in sorted(stops))))
        return False, out
    out.append('JOURNEY RESULT PASS %d/%d checks, %d steps%s' % (total, total, len(journey['steps']), known))
    return True, out


def pick_number(lines, side, text):
    """The first number right after (side "after") or right before ("before") TEXT in the joined answer, else None."""
    joined = ' '.join(lines)
    num = r'(-?\d+(?:\.\d+)?)'
    m = re.search(re.escape(text) + r'\s*' + num if side == 'after' else num + r'\s+' + re.escape(text), joined)
    return float(m.group(1)) if m else None


def resolve(value, values):
    m = re.fullmatch(r'(-?\d+(?:\.\d+)?)', value)
    if m:
        return float(m.group(1)), None
    m = re.fullmatch(r'([a-z][a-z0-9_]*)(?:([+-])(\d+(?:\.\d+)?))?', value)
    base = values.get(m.group(1))
    if not isinstance(base, float):
        return None, 'probe %s has no number' % m.group(1)
    if m.group(2):
        base = base + float(m.group(3)) if m.group(2) == '+' else base - float(m.group(3))
    return base, None


def answer_text(raw, name):
    lines = raw.get(name)
    if lines is None:
        return 'no answer'
    shown = ' | '.join(l for l in lines if l)[:160]
    return shown or 'empty answer'


def autosave_misses(journey, consoles, first):
    """(map changes judged, [the ones without an autosave]) from step FIRST on: in the console of FIRST's part after
    its step marker, and in each later part after its first "Game restored" line (a later part is a fresh engine: its
    own start and the load of the save are no map change of the game). A map change is a "Scene ready" line of a map
    load: a streamed crossing is none (no autosave is asked for it), a "Game restored" line right after it makes it the
    load of a save (none asked either). It needs a "Saved Autosave" line before the next map load or the part's end."""
    names = [p['name'] for p in journey['parts']]
    start = next(s['part'] for s in journey['steps'] if s['step'] == first)
    judged, misses = 0, []
    for name in names[names.index(start):]:
        if name not in consoles:
            continue
        on, pending = False, None
        for line in consoles[name].splitlines():
            s = line.strip()
            if not on:
                on = (re.fullmatch(r'%s STEP %d' % (MARK, first), s) is not None if name == start
                      else s.startswith('Game restored:'))
                continue
            m = re.match(r'Scene ready: (\S+?),', s)
            if m and 'streamed crossing' not in s:
                if pending:
                    misses.append('%s (part %s, the next map loaded first)' % pending)
                pending = (m.group(1), name)
                judged += 1
            elif s.startswith('Game restored:') and pending:
                pending = None
                judged -= 1
            elif s.startswith('Saved Autosave') and pending:
                pending = None
        if pending:
            misses.append('%s (part %s, before the part ended)' % pending)
    return judged, misses


def check(e, journey, raw, values, consoles=None):
    if e['kind'] == 'autosaves':
        consoles = consoles or {}
        start = next(s['part'] for s in journey['steps'] if s['step'] == e['from'])
        if start not in consoles:
            return False, 'no console of part %s' % start
        judged, misses = autosave_misses(journey, consoles, e['from'])
        if not judged:
            return False, 'no map change from step %d on in the console' % e['from']
        if misses:
            return False, '%d of %d map changes wrote no autosave: %s' % (len(misses), judged, '; '.join(misses))
        return True, ''
    if e['kind'] in ('dead', 'alive', 'fighting'):
        ref = float(e['ref']) if e['ref'].isdigit() else values.get(e['ref'])
        if not isinstance(ref, float):
            return False, 'the kill gave no reference (%s)' % answer_text(raw, e['ref'])
        if e['list'] not in raw:
            return False, 'no actor list read'
        rows = actor_rows(raw[e['list']])
        state = rows.get(int(ref))
        if state is None:
            return False, 'reference %d is not in the actor list (%d actors listed)' % (ref, len(rows))
        if e['kind'] == 'alive':
            return state != 'DEAD', 'reference %d is dead' % ref
        if e['kind'] == 'fighting':
            return state == 'FIGHTING', 'reference %d is %s, not fighting' % (ref, state.lower())
        if state == 'DEAD':
            return True, ''
        if not e['ref'].isdigit():
            return False, 'reference %d is %s again: the dead came back' % (ref, state.lower())
        return False, 'reference %d is %s, not dead' % (ref, state.lower())
    if e['kind'] in ('has', 'lacks'):
        if e['probe'] not in raw:
            return False, 'no answer'
        held = e['needle'].lower() in ' '.join(raw[e['probe']]).lower()
        if e['kind'] == 'lacks':
            return not held, 'in the answer (%s)' % answer_text(raw, e['probe'])
        return held, 'not in the answer (%s)' % answer_text(raw, e['probe'])
    have = values.get(e['probe'])
    if e['probe'] not in raw:
        return False, 'probe %s has no answer in the logs' % e['probe']
    if not isinstance(have, float):
        lines = raw[e['probe']]
        refused = next((l for l in lines if REFUSALS.search(l)), None)
        if isinstance(have, str):
            want = e['value']
            if e['op'] in ('==', '!=') and not re.fullmatch(r'-?\d+(?:\.\d+)?', want):
                if want in journey['probes']:
                    if want not in raw:
                        return False, 'probe %s has no answer in the logs' % want
                    want = values.get(want)
                ok = (have == want) == (e['op'] == '==')
                return ok, 'read %r, wanted %s %r' % (have, e['op'], want)
        return False, 'no number in the answer (%s)' % (refused or answer_text(raw, e['probe']))
    want, err = resolve(e['value'], values)
    if err:
        other = re.match(r'[a-z][a-z0-9_]*', e['value']).group(0)
        return False, '%s (%s)' % (err, answer_text(raw, other))
    ok = {'==': have == want, '!=': have != want, '>': have > want, '<': have < want,
          '>=': have >= want, '<=': have <= want}[e['op']]
    return ok, 'read %g, wanted %s %g' % (have, e['op'], want)


def walkthrough(text):
    """The journey as a checklist for a person at the keyboard: each step, the console lines to type (the probes)
    and what each answer must show. The movement and key lines of the script are left out: the player walks."""
    j = parse(text)
    out, step = [], None
    by_step = {}
    for e in j['expects']:
        by_step.setdefault(e['step'], []).append(e)
    for s in j['steps']:
        if s['part'] != (j['steps'][j['steps'].index(s) - 1]['part'] if j['steps'].index(s) else 'A'):
            out.append('')
            out.append('-- quit the game, start it again and load its quicksave (Load game) --')
        out.append('')
        out.append('Step %d: %s' % (s['step'], s['title']))
        for t in j['talks']:
            if t['step'] == s['step']:
                out.append('  talk: choose the topic "%s" in the dialogue window' % t['topic'])
        for name, pr in j['probes'].items():
            if pr['step'] == s['step'] and pr['kind'] == 'pick':
                out.append('  read: the number %s "%s" in the answer of %s   (%s)' % (pr['side'], pr['text'], pr['from'], name))
            elif pr['step'] == s['step']:
                out.append('  type: %s   (%s)' % (pr['command'] if pr['kind'] == 'console' else 'look at the ' + pr['command'][6:], name))
        for e in by_step.get(s['step'], []):
            out.append('  check: %s%s' % (e['text'], ' (known gap %s)' % e['known'] if e.get('known') else ''))
    return '\n'.join(out).lstrip('\n') + '\n'


def read_run(d):
    d = Path(d)
    s, c = d / 'logs' / 'steps.log', d / 'logs' / 'console.log'
    if not s.exists() and not c.exists():
        return None
    return (s.read_text(encoding='utf-8', errors='replace') if s.exists() else '',
            c.read_text(encoding='utf-8', errors='replace') if c.exists() else '')


def main(argv):
    if len(argv) < 2 or argv[0] not in ('scripts', 'judge', 'check', 'walkthrough'):
        print(__doc__)
        return 2
    try:
        if argv[0] == 'walkthrough':
            sys.stdout.write(walkthrough(Path(argv[1]).read_text(encoding='utf-8')))
            return 0
        if argv[0] == 'check':
            j = parse(Path(argv[1]).read_text(encoding='utf-8'))
            print('journey ok: %d parts, %d steps, %d probes, %d checks' % (
                len(j['parts']), len(j['steps']), len(j['probes']), len(j['expects'])))
            return 0
        if argv[0] == 'scripts':
            names = write_scripts(argv[1], argv[2])
            print('journey scripts: parts %s in %s' % (' '.join(names), argv[2]))
            return 0
        # a run's own scripts/journey.json (written by "scripts" before its sessions) judges the run by the journey it
        # played, not by a journey file changed since (the v0.0.66 journeywalk runs: the file changed during a run)
        if argv[1].endswith('.json'):
            j = json.loads(Path(argv[1]).read_text(encoding='utf-8'))
            j.setdefault('talks', [])
        else:
            j = parse(Path(argv[1]).read_text(encoding='utf-8'))
        runs = [read_run(d) for d in argv[2:]]
        runs += [None] * (len(j['parts']) - len(runs))
        ok, lines = judge(j, runs)
        for line in lines:
            print(line)
        return 0 if ok else 1
    except JourneyError as e:
        print('JOURNEY RESULT FAIL the journey file: %s' % e)
        return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
