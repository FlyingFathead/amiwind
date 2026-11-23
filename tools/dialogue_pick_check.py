#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The dialogue's answer choice, by number: for every NPC record and a set of topics, the answer AmiWind's dialogue table
gives (the table's candidates as the engine walks them, aw_dial.c / aw_glut.c AW_GlutCond) against the answer the
original's rule gives, read straight from the INFO records (DIALOGUE-TEXT-VARIABLES-67, DIALOGUE-PICK-CHECK-67).

The reference is an independent implementation of OpenMW 0.51's dialogue filter (apps/openmw/mwdialogue/filter.cpp:
Filter::list with testActor, testPlayer, testSelectStructs, testDisposition, the Info Refusal fallback; the greeting
from Greeting 0..9 in order without the fallback, DialogueManager::startDialogue), our own code; it does not use the
builder's filter (mwad.dialogue Context). Both sides read one game state (a new character in the NPC's home cell, the
NPC's own disposition, nobody dead, every journal at 0; state()), so a difference is a difference in the answer choice:
the build-time filter, the table's lists and order, or a condition record's meaning.

  python3 tools/dialogue_pick_check.py --data-files DIR [--topics a,b,...] [--jobs N] [--report out.json]

Prints the mismatch count and the first ones; exit 1 when there is any."""
import argparse
import json
import re
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

import dialogue_lut as D  # noqa: E402
import greeting_lut as G  # noqa: E402
import text_defines  # noqa: E402

# the topics checked by default: the first-meeting ones every character knows and the most asked
TOPICS = ('background', 'little advice', 'little secret', 'someone in particular', 'latest rumors', 'my trade',
          'specific place', 'services')
GREETING = 'greeting'                              # the conversation greeting (Greeting 0..9)
# OpenMW's SelectWrapper types (selectwrapper.cpp): compared without the operator (inverted), numeric, boolean
INVERTED = ('NotId', 'NotFaction', 'NotClass', 'NotRace', 'NotCell')
BOOLEAN = ('SameSex', 'SameRace', 'SameFaction', 'PcCommonDisease', 'PcBlightDisease', 'PcCorprus', 'PcExpelled',
           'PcVampire', 'TalkedToPc', 'Alarmed', 'Detected', 'Attacked', 'ShouldAttack', 'Werewolf')
PLAYER = {'race': 'imperial', 'female': False, 'attribute': 40, 'skill': 15}
# the states every speaker is checked in: as met first (its own disposition), unwilling (disposition 0: the refusals),
# and met before at disposition 100 with the other Random100 end
VARIANTS = ({}, {'disposition': 0, 'random': 0}, {'disposition': 100, 'random': 99, 'talked': True},
            # far into the game: every journal at 50, every actor dead once, one of every item, every local at 1, and
            # the player a member of the speaker's faction at rank 3 (the conditions that read them all tested)
            {'disposition': 60, 'random': 25, 'counts': 50, 'dead': 1, 'item': 1, 'local': 1, 'member': 3,
             'common': 1, 'clothing': 300},
            # sick and cursed: a blight disease, Corprus and vampirism, dressed in what is worth 2000 gold, and the
            # speaker attacked before (the conditions the engine reads live since v0.0.67-dev3,
            # DIALOGUE-CONDITIONS-PARTIAL-67)
            {'disposition': 40, 'random': 75, 'blight': 1, 'corprus': 1, 'vampire': 1, 'clothing': 2000, 'attacked': 1})
STATE_FUNCTIONS = (('common', 'PcCommonDisease'), ('blight', 'PcBlightDisease'), ('corprus', 'PcCorprus'),
                   ('vampire', 'PcVampire'), ('clothing', 'PcClothingModifier'), ('attacked', 'Attacked'))


def variant(st, change, npc=None):
    """STATE with a VARIANTS entry applied (NPC: the speaker, for the player's membership of its faction)."""
    st = dict(st, functions=dict(st['functions']), globals=dict(st['globals']), items=dict(st['items']),
              pc_ranks=dict(st['pc_ranks']))
    for key in ('counts', 'dead', 'item', 'local'):
        if key in change:
            st[key] = change[key]
    if 'member' in change and npc is not None and npc['faction']:
        st['pc_ranks'][npc['faction']] = change['member']
        st['functions']['SameFaction'] = 1
        st['functions']['FactionRankDifference'] = change['member'] - npc['rank']
    if 'disposition' in change:
        st['disposition'] = change['disposition']
    if 'random' in change:
        st['random'] = change['random']
        st['globals']['random100'] = float(change['random'])
    if 'talked' in change:
        st['functions']['TalkedToPc'] = int(change['talked'])
    for key, name in STATE_FUNCTIONS:
        if key in change:
            st['functions'][name] = change[key]
    return st


def _compare(x, op, v):
    return {'0': x == v, '1': x != v, '2': x > v, '3': x >= v, '4': x < v, '5': x <= v}[str(op)]


def _f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def state(kinds, npc, home, talked=False):
    """The game state both sides read for one speaker (mwad.dialogue speaker() facts NPC): a new character (no faction,
    level 1, the start values of mwad.dialogue FIXTURE), standing in the NPC's home cell (HOME; '' when it has none),
    the NPC's own disposition, Random100 50, no choice open, every journal, item and death count 0 (gold 100)."""
    from mwad.dialogue import FIXTURE, globals_of, starting_clothing_value
    from mwad.esm import first
    stats = first(kinds['NPC_'][npc['id']], 'NPDT')
    disposition = stats[44] if len(stats) == 52 else stats[2] if len(stats) == 12 else 50
    fn = dict(FIXTURE)
    fn.update({'PcGender': 1 if PLAYER['female'] else 0, 'PcHealth': 100, 'PcMagicka': 50, 'PcFatigue': 100,
               'PcClothingModifier': starting_clothing_value(kinds), 'Weather': 0, 'ShouldAttack': 0,
               'SameSex': int(npc['female'] == PLAYER['female']), 'SameRace': int(npc['race'] == PLAYER['race']),
               'TalkedToPc': int(talked), 'Level': npc['level'], 'Reputation': npc['reputation'],
               'FactionRankDifference': (-1 - npc['rank']) if npc['faction'] else 0,
               'RankRequirement': 0})
    fn.update(npc['ai'])
    for name in ('PcStrength', 'PcIntelligence', 'PcWillpower', 'PcAgility', 'PcSpeed', 'PcEndurance',
                 'PcPersonality', 'PcLuck'):
        fn[name] = PLAYER['attribute']
    from mwad.dialogue import FUNCTIONS
    for name in FUNCTIONS:
        if name.startswith('Pc') and name not in fn:
            fn[name] = PLAYER['skill']
    globals_ = kinds.get('_globals') or globals_of(kinds)
    return {'functions': fn, 'choice': -1, 'random': 50, 'disposition': max(0, min(100, disposition)),
            'cell': home or '', 'globals': dict(globals_, random100=50.0), 'items': {'gold_001': 100},
            'pc_ranks': {}}


# ---- the reference: OpenMW's filter on the INFO records

def _locals_of(kinds, npc):
    from mwad.dialogue import script_locals
    from mwad.esm import text
    if not npc['script']:
        return None
    source = text(kinds.get('SCPT', {}).get(npc['script'], []), 'SCTX')
    return script_locals(source)


def _select(function, variable, op, value, npc, st, locals_):
    """OpenMW Filter::testSelectStruct for one condition."""
    if function == 'Invalid':
        return False                                  # OpenMW drops it when loading; never seen in the masters
    if function == 'Choice' and st['choice'] == -1:
        return False
    if function in INVERTED:
        if function == 'NotCell':
            return not st['cell'].casefold().startswith(variable)
        return npc[{'NotId': 'id', 'NotFaction': 'faction', 'NotClass': 'class', 'NotRace': 'race'}[function]] != variable
    if function == 'Global':
        if variable not in st['globals']:
            return True                               # ignored when the global does not exist
        return _compare(_f32(st['globals'][variable]), op, value)
    if function in ('Local', 'NotLocal'):
        has = locals_ is not None and variable in locals_
        holds = has and _compare(st.get('local', 0), op, value)   # a fresh actor's locals read 0
        return holds if function == 'Local' else not holds
    if function in ('Journal', 'Dead'):
        return _compare(st.get('counts' if function == 'Journal' else 'dead', 0), op, value)
    if function == 'Item':
        return _compare(st['items'].get(variable, st.get('item', 0)), op, value)
    if function == 'Choice':
        return _compare(st['choice'], op, value)
    x = st['functions'].get(function)
    if x is None:
        raise ValueError('no state for function ' + function)
    if function in BOOLEAN:
        x = int(bool(x))
    return _compare(x, op, value)


def ref_passes(fields, npc, st, locals_):
    """(other tests pass, disposition test passes) of one INFO for one NPC speaker (OpenMW Filter::list)."""
    from mwad.dialogue import _parsed
    parsed = _parsed(fields)
    if parsed is None:
        return False, False
    disposition, rank, gender, pcrank, actor, race, cls, faction, pc_faction, cell, rules = parsed
    own_rank = npc['rank'] if npc['faction'] else -1   # getPrimaryFactionRank: -1 without a faction
    # testActor
    if actor and actor != npc['id']:
        return False, False
    if race and race != npc['race']:
        return False, False
    if cls and cls != npc['class']:
        return False, False
    if faction == 'ffff':
        if npc['faction']:
            return False, False
    elif faction:
        if faction != npc['faction'] or own_rank < rank:
            return False, False
    elif rank != -1 and own_rank < rank:
        return False, False
    if gender == (0 if npc['female'] else 1):
        return False, False
    # testPlayer
    if pc_faction:
        if pc_faction not in st['pc_ranks'] or st['pc_ranks'][pc_faction] < pcrank:
            return False, False
    elif pcrank != -1:
        if npc['faction'] not in st['pc_ranks'] or st['pc_ranks'][npc['faction']] < pcrank:
            return False, False
    if cell and not st['cell'].casefold().startswith(cell):
        return False, False
    # testSelectStructs
    for condition in rules:
        if not _select(*condition, npc, st, locals_):
            return False, False
    return True, st['disposition'] >= disposition


def ref_search(infos, npc, st, locals_, refusal_infos=None):
    """The INFO index OpenMW's Filter::search picks in INFOS ([fields]), else ('refusal', index in REFUSAL_INFOS), else
    None."""
    refused = False
    for i, fields in enumerate(infos):
        other, disp = ref_passes(fields, npc, st, locals_)
        if other and disp:
            return i
        refused = refused or other
    if refused and refusal_infos is not None:
        for i, fields in enumerate(refusal_infos):
            other, disp = ref_passes(fields, npc, st, locals_)
            if other and disp:
                return ('refusal', i)
    return None


# ---- AmiWind: the dialogue table as the engine walks it

def _cond_holds(t, cond, npc, st, slots_float):
    """aw_glut.c AW_GlutCond for one condition record (op, cmp, operand, raw value) with the state's values."""
    op, cmp, operand, raw = cond
    value = struct.unpack('>f', struct.pack('>i', raw))[0] if cmp & G.FLOAT else raw
    c = str(cmp & 7)
    if op == G.OP_FUNC:
        from mwad.dialogue import FUNCTIONS
        name = FUNCTIONS[operand]
        if name == 'Choice':
            x = st['choice']
        elif name in D.LIVE_FUNCTIONS or name in ('TalkedToPc', 'FactionRankDifference'):
            x = st['functions'].get(name)
            if name in BOOLEAN and x is not None:
                x = int(bool(x))
        else:
            x = t['fixture'].get(operand)                 # the start-of-game value; none: never passes
        return x is not None and _compare(x, c, value)
    if op == G.OP_RANDOM100:
        return _compare(st['random'], c, value)
    if op == G.OP_GLOBAL:
        name, start = t['globals'][operand]
        return _compare(_f32(st['globals'].get(name, start)), c, value)
    if op in (G.OP_JOURNAL, G.OP_DEAD):
        return _compare(st.get('counts' if op == G.OP_JOURNAL else 'dead', 0), c, value)
    if op in (G.OP_LOCAL, G.OP_NOTLOCAL):
        holds = _compare(st.get('local', 0), c, value)
        return holds if op == G.OP_LOCAL else not holds
    if op == G.OP_ITEM:
        item = t['names'][operand] if operand < len(t['names']) else None
        return item is not None and _compare(st['items'].get(item, st.get('item', 0)), c, value)
    if op == G.OP_CELL:
        want = t['names'][operand] if operand < len(t['names']) else None
        if not st['cell']:
            return False
        match = bool(want) and st['cell'].casefold().startswith(want.casefold())
        return match if raw else not match
    if op == G.OP_DISP:
        return _compare(st['disposition'], c, value)
    if op == G.OP_PCFACTION:
        faction = t['names'][operand] if operand != D.NONE16 else npc['faction']
        faction = faction or npc['faction']
        return bool(faction) and faction in st['pc_ranks'] and st['pc_ranks'][faction] >= value
    raise ValueError('unknown condition opcode %d' % op)


def table_search(t, row, topic, npc, st):
    """(entry, refused) the engine picks for TOPIC on table row ROW (aw_dial.c AW_DialPick: the first candidate whose
    conditions hold; refused when one failed on its disposition test alone)."""
    refused = False
    for e in D.candidates(t, row, topic):
        _text, first, _s, _l, _n, n, _f = t['entries'][e]
        conds = t['conds'][first:first + n]
        other = all(_cond_holds(t, c, npc, st, None) for c in conds if c[0] != G.OP_DISP)
        disp = all(_cond_holds(t, c, npc, st, None) for c in conds if c[0] == G.OP_DISP)
        if other and disp:
            return e, False
        refused = refused or other
    return -1, refused


def table_answer(t, row, topic, npc, st, greeting_topics):
    """The entry the conversation shows: a topic's answer with the Info Refusal fallback; for GREETING the first
    Greeting topic in order with an answer (AW_DialGreeting)."""
    if topic == GREETING:
        for g in greeting_topics:
            e, _ = table_search(t, row, g, npc, st)
            if e >= 0:
                return e
        return -1
    e, refused = table_search(t, row, topic, npc, st)
    if e < 0 and refused and t['info_refusal'] is not None:
        e, _ = table_search(t, row, t['info_refusal'], npc, st)
    return e


# ---- the comparison

def shown_key(finder, fields):
    """(coded text, result script) of an INFO as the table stores it (dialogue_lut.tables: the link markers resolved,
    the defines coded), to name the reference's pick in the table's terms."""
    from mwad.esm import text
    line = text(fields, 'NAME')
    shown, found = finder(line) if line else ('', [])
    coded, _spans, _n = text_defines.encode_spans(shown, found)
    return coded, text(fields, 'BNAM')


def readable(line):
    """A coded table text with its defines written out again (%name), for the report."""
    if line is None:
        return None
    return re.sub(text_defines.CODE + '(.)', lambda m: '%' + text_defines.NAMES[ord(m.group(1)) - 1], line)


def entry_key(t, e):
    if e < 0:
        return None
    text_at, _first, script_at, _l, _n, _c, _f = t['entries'][e]
    return t['text'](text_at) or '', t['script'](script_at) or ''


def check(kinds, topics, dials, raw, order, homes, wanted=TOPICS, limit=20, variants=VARIANTS):
    """{'checked', 'mismatches', 'first': [...], 'by_topic': {topic: n}} for every NPC of ORDER (the table's rows), the
    WANTED topics plus the greeting, in each of the VARIANTS states."""
    from mwad.dialogue import speaker
    t = D.read(raw)
    names = [n.casefold() for n, _k in t['topics']]
    table_names = D.table_topics(dials)
    display = [dials[n][0] if dials[n][1] == D.KIND_TOPIC else None for n in table_names]
    finder = D.span_finder(display)
    greetings = sorted(n for n in table_names if dials[n][1] == D.KIND_GREETING)
    greeting_rows = [names.index(g) for g in greetings]
    refusal = topics.get(D.INFO_REFUSAL)
    out = {'checked': 0, 'mismatches': 0, 'first': [], 'by_topic': {}}
    every = wanted == 'all'
    if every:
        # every Topic kind topic (not the Info Refusal one): per NPC the ones it or the original can answer, from the
        # INFOs for anyone and the ones naming that NPC (the rest have no answer on either side)
        from mwad.esm import text
        wanted = tuple(n for n in table_names if dials[n][1] == D.KIND_TOPIC and n != D.INFO_REFUSAL)
        generic = {n for n in wanted if any(not text(f, 'ONAM') for f in topics.get(n, []))}
        named = {}
        for n in wanted:
            for f in topics.get(n, []):
                actor = text(f, 'ONAM').casefold()
                if actor:
                    named.setdefault(actor, set()).add(n)
    started = time.time()
    for row, ident in enumerate(order):
        if row and row % 250 == 0 and len(order) > 250:
            rate = row / max(0.1, time.time() - started)
            print('Answer choice: %d/%d NPCs, %d checked, %d mismatches (%.0f NPCs/s, ETA %.0f s)' % (
                row, len(order), out['checked'], out['mismatches'], rate, (len(order) - row) / rate), flush=True)
        if G.is_creature(kinds, ident):
            # a creature row (DIALOGUE-CREATURE-SPEAKERS-66): this check's reference search is the NPC rule; the
            # creature rule is tested in tests/test_dialogue_lut.py, its rows are skipped here (counted)
            out['creature_rows_skipped'] = out.get('creature_rows_skipped', 0) + 1
            continue
        npc = speaker(kinds, ident)
        base = state(kinds, npc, homes.get(ident))
        locals_ = _locals_of(kinds, npc)
        if every:
            own = generic | named.get(ident, set()) | {names[k] for k in t['rows'][row]}
            asked = tuple(n for n in wanted if n in own)
        else:
            asked = tuple(w for w in wanted if w in names)
        for change, topic in ((c, w) for c in variants for w in (GREETING,) + asked):
            st = variant(base, change, npc)
            if topic == GREETING:
                want = None
                for g in greetings:
                    i = ref_search(topics.get(g, []), npc, st, locals_)
                    if i is not None:
                        want = shown_key(finder, topics[g][i])
                        break
                got = entry_key(t, table_answer(t, row, GREETING, npc, st, greeting_rows))
            else:
                i = ref_search(topics.get(topic, []), npc, st, locals_, refusal)
                if isinstance(i, tuple):
                    want = shown_key(finder, refusal[i[1]])
                elif i is not None:
                    want = shown_key(finder, topics[topic][i])
                else:
                    want = None
                got = entry_key(t, table_answer(t, row, names.index(topic), npc, st, greeting_rows))
            out['checked'] += 1
            if got != want:
                out['mismatches'] += 1
                out['by_topic'][topic] = out['by_topic'].get(topic, 0) + 1
                if len(out['first']) < limit:
                    out['first'].append({'npc': ident, 'topic': topic, 'state': change,
                                         'amiwind': readable(got[0])[:100] if got else None,
                                         'original': readable(want[0])[:100] if want else None})
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--topics', default=','.join(TOPICS))
    p.add_argument('--jobs', type=int, default=1)
    p.add_argument('--report', type=Path)
    a = p.parse_args(argv)
    from mwad.masters import master_path
    master = master_path(a.data_files)
    t0 = time.time()
    print('=== PHASE 1/2: the dialogue table of %s ===' % master.name, flush=True)
    raw, report = D.build_master(master, a.jobs)
    kinds, topics = G.load(master)
    dials = D.dial_names(master)
    # the table's rows: the NPC records and the creature speakers, in one order (DIALOGUE-CREATURE-SPEAKERS-66)
    creatures = G.creature_speakers(kinds, topics)
    homes = G.home_cells(master, kinds, creatures)
    order = [i for i in G.plan_npcs(kinds, homes, creatures)[0] if i not in report['left_out']]
    wanted = 'all' if a.topics == 'all' else tuple(w.strip().casefold() for w in a.topics.split(',') if w.strip())
    print('=== PHASE 2/2: %d NPCs x %s topics and the greeting, the table against the original\'s rule ===' % (
        len(order), wanted if wanted == 'all' else len(wanted)), flush=True)
    result = check(kinds, topics, dials, raw, order, homes, wanted)
    result['seconds'] = round(time.time() - t0, 1)
    print('Answer choice: %d checked, %d mismatches %s (%.1f s)' % (result['checked'], result['mismatches'],
                                                                   json.dumps(result['by_topic']), result['seconds']))
    for m in result['first']:
        print('  %s | %s | AmiWind: %r | original: %r' % (m['npc'], m['topic'], m['amiwind'], m['original']))
    if a.report:
        a.report.write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    return 1 if result['mismatches'] else 0


if __name__ == '__main__':
    sys.exit(main())
