# SPDX-License-Identifier: GPL-3.0-only
"""The dialogue table (tools/dialogue_lut.py, AWDL1; DIALOGUE-57, docs/DIALOGUE_DESIGN.md).

Synthetic records only (no game data): topics filtered by race, class, faction and actor, a disposition-gated answer
with the Info Refusal fallback, a Choice answer left for run time, a journal-gated answer, result scripts, topic names
in the answers' texts (hyperlinks), a Persuasion topic and a quest's journal entries. Checked: each NPC row's answers
equal the INFOs the shared filter lets that NPC say, in the original's order, up to the first without a run-time
condition; the condition records use the voice table's opcodes; the links, scripts, journal and size report; the
image step; and the engine's reader and first-match search (engine/aga/src/aw_dial.c with the shared evaluator
aw_glut.c AW_GlutCond) against this module's own answers for every NPC, topic and a spread of run-time states.
"""
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import dialogue_lut as D  # noqa: E402
import greeting_lut as G  # noqa: E402
import mwad.dialogue as dialogue  # noqa: E402
from test_greeting_lut import NPCS, f, info, kinds as voice_kinds  # noqa: E402

CHOICE = ('01500', 1)                          # Choice == 1
CHOICE2 = ('01500', 2)
JOURNAL = ('04JX3A1_Fargoth', 10)              # journal A1_Fargoth >= 10
RANDOM = ('02fX3Random100', 50)
LOCAL = ('03sX0ringfound', 1)                  # the speaker's script local ringfound == 1
SCRIPT = 'begin fargothscript\nfloat mood\nshort ringfound\nend\n'   # ringfound is slot 1


def result(fields, script):
    return fields + [f('BNAM', script)]


def journal_info(identifier, index, line, name=False, finished=False):
    fields = [f('INAM', identifier), ('DATA', struct.pack('<iibbbb', 4, index, -1, -1, -1, 0))]
    fields.append(f('NAME', line))
    if name:
        fields.append(('QSTN', b'\1'))
    if finished:
        fields.append(('QSTF', b'\1'))
    return fields


TOPICS = {
    'background': [info('b0', 'Welcome, guild member.', kind=0, DNAM='Mages Guild'),
                   info('b1', 'I am Fargoth, of Seyda Neen. Ask about my ring.', kind=0, ONAM='fargoth'),
                   info('b2', 'A guild mage. See the Mages Guild.', kind=0, FNAM='Mages Guild', disp=60),
                   info('b3', 'Just a Dunmer, outlander.', kind=0, RNAM='Dark Elf'),
                   info('b4', 'Nothing much.', kind=0)],
    'my ring': [result(info('r1', 'You found it? Thank you!', kind=0, ONAM='fargoth', scvr=[JOURNAL]),
                       'Journal "A1_Fargoth" 20\nModDisposition 10'),
                result(info('r2', 'Will you help me?', kind=0, ONAM='fargoth'),
                       'Choice "Yes" 1 "No" 2')],
    'help': [info('c0', 'You found it!', kind=0, ONAM='fargoth', scvr=[LOCAL]),
             info('c1', 'Good, good.', kind=0, ONAM='fargoth', scvr=[CHOICE]),
             info('c2', 'Hmph.', kind=0, ONAM='fargoth', scvr=[CHOICE2]),
             info('c3', 'Help with what?', kind=0, disp=30),
             result(info('cc', 'Report to the guild.', kind=0, ONAM='chargen captain'),
                    'AddTopic "Background"\nAddTopic "my ring"\nAddTopic "no such topic"')],
    'latest rumors': [info('l1', 'They say the background of things matters.', kind=0, scvr=[RANDOM]),
                      info('l2', 'Nothing new.', kind=0, CNAM='Mage', disp=90)],
    'info refusal': [info('x1', 'I do not want to talk about that.', kind=0)],
    'admire success': [info('p1', 'You flatter me.', kind=3)],
    'a1_fargoth': [journal_info('j0', 0, 'Fargoth\'s Ring', name=True),
                   journal_info('j2', 20, 'I gave the ring back.', finished=True),
                   journal_info('j1', 10, 'I found a ring.')],
    'greeting 0': [info('g1', 'Hello.', kind=2)],
    'hello': [info('h1', 'Hi.', kind=1)],
}
DIALS = {'background': ('Background', 0), 'my ring': ('my ring', 0), 'help': ('Help', 0),
         'latest rumors': ('latest rumors', 0), 'info refusal': ('Info Refusal', 0),
         'admire success': ('Admire Success', 3), 'a1_fargoth': ('A1_Fargoth', 4), 'greeting 0': ('Greeting 0', 2),
         'hello': ('Hello', 1)}


def kinds():
    k = voice_kinds()
    k['DIAL'] = {t: kind for t, (_n, kind) in DIALS.items()}
    k['NPC_'] = dict(k['NPC_'], fargoth=k['NPC_']['fargoth'] + [f('SCRI', 'FargothScript')])
    k['SCPT'] = {'fargothscript': [('SCHD', b'FargothScript'.ljust(52, b'\0')), f('SCTX', SCRIPT)]}
    k['GMST'] = dict(k['GMST'], **{n.casefold(): [f('NAME', n), ('FLTV', struct.pack('<f', v))]
                                   for n, v in DISPOSITION_SETTINGS.items()})
    k['FACT'] = dict(k['FACT'])
    k['FACT']['mages guild'] = k['FACT']['mages guild'] + [f('ANAM', 'Mages Guild'), ('INTV', struct.pack('<i', 3)),
                                                           f('ANAM', 'Fighters Guild'), ('INTV', struct.pack('<i', -2))]
    k['FACT']['fighters guild'] = [f('NAME', 'Fighters Guild'), f('FNAM', 'Fighters Guild'),
                                   f('ANAM', 'Mages Guild'), ('INTV', struct.pack('<i', 1))]
    return k


# the disposition's game settings (test values in the game's range; the table copies whatever the data has)
DISPOSITION_SETTINGS = {'fDispRaceMod': 5.0, 'fDispPersonalityMult': 0.5, 'fDispPersonalityBase': 50.0,
                        'fDispFactionRankMult': 0.5, 'fDispFactionRankBase': 1.0, 'fDispFactionMod': 3.0,
                        'fDispCrimeMod': 0.001, 'fDispDiseaseMod': -10.0, 'fDispWeaponDrawn': -5.0}


def brute_force(k, ident, topic):
    """What the NPC's topic should walk: every INFO the shared filter (with Choice for run time) lets it say, in
    order, up to the first without a run-time condition."""
    context = D.TopicContext(k, ident, G.NO_CELL)
    out = []
    for fields in TOPICS[topic]:
        runtime = context.compile(fields)
        if runtime is None:
            continue
        out.append((dialogue.text(fields, 'NAME'), len(runtime)))
        if not runtime:
            break
    return out


def ref_holds(t, cond, state):
    """The engine's condition test (aw_glut.c AW_GlutCond) for the expectations; None for a disposition test that
    failed (the refusal rule)."""
    op, cmp, operand, value = cond
    compare = [lambda x, v: x == v, lambda x, v: x != v, lambda x, v: x > v, lambda x, v: x >= v,
               lambda x, v: x < v, lambda x, v: x <= v][cmp & 7]
    if op == G.OP_FUNC:
        if operand == dialogue.FUNCTIONS.index('Choice'):
            return compare(state['choice'], value)
        x = t['fixture'].get(operand)
        return x is not None and compare(x, value)
    if op == G.OP_RANDOM100:
        return compare(state['random'], value)
    live = state.get('live')
    if op == G.OP_DISP:
        return compare(state['disposition'], value)
    if op in (G.OP_JOURNAL, G.OP_DEAD):
        kind = 'journal' if op == G.OP_JOURNAL else 'dead'
        return compare((live or {}).get(kind, {}).get(t['names'][operand], 0), value)
    if op in (G.OP_LOCAL, G.OP_NOTLOCAL):
        v = (live or {}).get('local', {}).get(operand & 0x3FFF, 0)
        return compare(v, value) if op == G.OP_LOCAL else not compare(v, value)
    if op == G.OP_GLOBAL:
        name, start = t['globals'][operand]
        return compare((live or {}).get('global', {}).get(name, start), value)
    if op == G.OP_ITEM:
        item = t['names'][operand] if operand < len(t['names']) else None
        if live is not None:
            return compare(live.get('item', {}).get(item, 0), value)
        return item is not None and item != 'gold_001' and compare(0, value)
    if op == G.OP_PCFACTION:
        if live is None:
            return False
        faction = t['names'][operand] if operand != D.NONE16 else state.get('faction')
        rank = live.get('rank', {}).get(faction, -1) if faction else -1
        return rank >= 0 and rank >= value
    if op == G.OP_CELL:
        cell, want = state.get('cell'), t['names'][operand] if operand < len(t['names']) else None
        if not cell:
            return False
        match = bool(want) and cell.casefold().startswith(want.casefold())
        return match if value else not match
    raise AssertionError('no reference for opcode %d' % op)


def ref_pick(t, npc, topic, state):
    """(answer entry or -1, refused) by OpenMW's first-match rule with the disposition test apart."""
    refused = False
    for e in D.candidates(t, npc, topic):
        _text, first, _s, _l, _n, n, _f = t['entries'][e]
        conds = t['conds'][first:first + n]
        other = all(ref_holds(t, c, state) for c in conds if c[0] != G.OP_DISP)
        disp = all(ref_holds(t, c, state) for c in conds if c[0] == G.OP_DISP)
        if other and disp:
            return e, False
        refused = refused or other
    return -1, refused


def pytest_f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


DISPOSITION_CASES = [   # base, same race, personality, bounty, faction, player ranks, diseased, weapon drawn
    (50, 1, 60, 0, 'mages guild', {'mages guild': (2, False)}, 0, 0),
    (50, 0, 50, 0, 'mages guild', {'mages guild': (2, True)}, 0, 0),
    (50, 0, 50, 0, 'mages guild', {'fighters guild': (1, False)}, 0, 0),
    (40, 1, 33, 1200, 'fighters guild', {'mages guild': (0, False), 'fighters guild': (4, False)}, 1, 1),
    (90, 1, 100, 0, None, {}, 0, 0), (3, 0, 10, 99999, None, {}, 1, 1), (61, 0, 47, 7, 'mages guild', {}, 0, 1)]


def ref_list(t, npc, known, state):
    """The window's topic list (OpenMW getAvailableTopics): Topic kind, known, and an answer or a refusal."""
    out = []
    for topic in sorted(t['rows'][npc]):
        if t['topics'][topic][1] != D.KIND_TOPIC or topic not in known:
            continue
        got, refused = ref_pick(t, npc, topic, state)
        if got >= 0 or refused:
            out.append(topic)
    return out


def ref_answer(t, npc, topic, state):
    got, refused = ref_pick(t, npc, topic, state)
    if got < 0 and refused and t['info_refusal'] is not None and topic != t['info_refusal']:
        got, _ = ref_pick(t, npc, t['info_refusal'], state)
    return got


class DialogueTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw, cls.report = D.build(kinds(), TOPICS, DIALS)
        cls.t = D.read(cls.raw)
        cls.order = G.plan_npcs(kinds())[0]
        cls.names = [n for n, _ in cls.t['topics']]

    def answers(self, ident, name):
        return [a[0] for a in D.answers(self.t, self.order.index(ident), self.names.index(name))]

    def test_topics_sorted_by_name_with_kinds(self):
        self.assertEqual(self.t['topics'], [('Admire Success', 3), ('Background', 0), ('Help', 0),
                                            ('Info Refusal', 0), ('latest rumors', 0), ('my ring', 0)])
        self.assertEqual(self.t['info_refusal'], 3)
        self.assertEqual(self.report['npcs'], len(NPCS))

    def test_static_filters(self):
        member = 'Welcome, guild member.'          # the player's faction test is left for run time, for everyone
        self.assertEqual(self.answers('fargoth', 'Background'),
                         [member, 'I am Fargoth, of Seyda Neen. Ask about my ring.'])
        self.assertEqual(self.answers('mage', 'Background'),
                         [member, 'A guild mage. See the Mages Guild.', 'Nothing much.'])
        self.assertEqual(self.answers('dunmer_f', 'Background'), [member, 'Just a Dunmer, outlander.'])
        self.assertEqual(self.answers('breton_m', 'Background'), [member, 'Nothing much.'])
        pc_faction = D.answers(self.t, self.order.index('breton_m'), self.names.index('Background'))[0][3]
        self.assertEqual([(c[0], self.t['names'][c[2]], c[3]) for c in pc_faction], [(G.OP_PCFACTION, 'mages guild', -1)])
        self.assertEqual(self.t['rows'][self.order.index('breton_m')].get(self.names.index('my ring')), None)

    def test_rows_match_the_filter_for_every_npc_and_topic(self):
        k = kinds()
        for ident in NPCS:
            for t, name in enumerate(self.names):
                key = next(x for x in TOPICS if DIALS.get(x, ('',))[0] == name)
                with self.subTest(npc=ident, topic=name):
                    got = [(a[0] or '', len(a[3])) for a in D.answers(self.t, self.order.index(ident), t)]
                    self.assertEqual(got, brute_force(k, ident, key))

    def test_condition_records_scripts_and_links(self):
        npc, ring = self.order.index('fargoth'), self.names.index('my ring')
        found, ask = D.answers(self.t, npc, ring)
        self.assertEqual(found[1], 'Journal "A1_Fargoth" 20\nModDisposition 10')
        self.assertEqual(found[3][0][:2], (G.OP_JOURNAL, 3))
        self.assertEqual(self.t['names'][found[3][0][2]], 'a1_fargoth')
        self.assertEqual(ask[1], 'Choice "Yes" 1 "No" 2')
        choice = D.answers(self.t, npc, self.names.index('Help'))
        # the speaker's script local by its slot in FargothScript (ringfound: slot 1, a short)
        self.assertEqual(choice[0][3], [(G.OP_LOCAL, 0, 1, 1)])
        self.assertEqual(choice[1][3], [(G.OP_FUNC, 0, dialogue.FUNCTIONS.index('Choice'), 1)])
        self.assertEqual(choice[3][3], [(G.OP_DISP, 3, 0, 30)])
        background = D.answers(self.t, npc, self.names.index('Background'))[1]
        self.assertEqual(background[2], [self.names.index('my ring')])         # the topic its text names
        mage = D.answers(self.t, self.order.index('mage'), self.names.index('Background'))[1]
        self.assertEqual(mage[2], [])                                           # "Mages Guild" is no topic
        rumor = D.answers(self.t, npc, self.names.index('latest rumors'))[0]
        self.assertEqual(rumor[2], [self.names.index('Background')])

    def test_local_slots_follow_the_script_compiler(self):
        from mwscript.lexer import tokenize
        from mwscript.parser import declarations
        self.assertEqual(declarations(tokenize(SCRIPT, []))['ringfound'], ('s', 1))
        self.assertEqual(D.with_slots((('Local', 'mood', '0', 1.5),), {'mood': ('f', 0)}),
                         (('Local', 'mood#0f', '0', 1.5),))

    def test_link_rule(self):
        find = D.link_finder(['Background', None, 'my ring', 'ring'])
        self.assertEqual(find('My Ring, the ring, a ringing background.'), [2, 3, 0])
        self.assertEqual(find('backgrounds'), [])

    def test_persuasion_topic_kept_for_every_npc(self):
        for ident in NPCS:
            self.assertEqual(self.answers(ident, 'Admire Success'), ['You flatter me.'])

    def test_disposition_settings_and_factions(self):
        self.assertEqual(self.t['settings'], {k: pytest_f32(v) for k, v in DISPOSITION_SETTINGS.items()})
        self.assertEqual(self.t['factions'], ['fighters guild', 'mages guild'])
        self.assertEqual(sorted(self.t['reactions']), [(0, 1, 1), (1, 0, -2), (1, 1, 3)])
        self.assertEqual(self.report['settings_missing'], [])
        t = self.t
        # base 50, same race +5, personality 60: +5; a member of the Mages Guild at rank 2: (0.5*2+1)*3*3 = 18
        self.assertEqual(D.derived_disposition(t, 50, True, 60, 0, 'mages guild', {'mages guild': (2, False)}), 78)
        # expelled from the NPC's own faction: no faction term
        self.assertEqual(D.derived_disposition(t, 50, False, 50, 0, 'mages guild', {'mages guild': (2, True)}), 50)
        # a Fighters Guild member before a mage: the lowest reaction, -2: (0.5*1+1)*3*-2 = -9
        self.assertEqual(D.derived_disposition(t, 50, False, 50, 0, 'mages guild', {'fighters guild': (1, False)}),
                         41)
        # a bounty of 5000: -5; clamped to 0..100
        self.assertEqual(D.derived_disposition(t, 30, False, 50, 5000, None, {}), 25)
        self.assertEqual(D.derived_disposition(t, 5, False, 0, 0, None, {}), 0)
        self.assertEqual(D.derived_disposition(t, 5, False, 0, 0, None, {}, clamp=False), -20)

    def test_rank_names(self):
        mages = self.t['rank_names'][self.t['factions'].index('mages guild')]
        self.assertEqual(mages[:4], ['Associate', 'Apprentice', 'Journeyman', ''])
        self.assertEqual(len(mages), D.RANKS)

    def test_start_topics_from_the_census_captain(self):
        self.assertEqual([self.names[t] for t in self.t['start']], ['Background', 'my ring'])

    def test_journal(self):
        self.assertEqual(self.t['quests'], [('A1_Fargoth', [(0, D.QUEST_NAME, "Fargoth's Ring"),
                                                            (10, 0, 'I found a ring.'),
                                                            (20, D.QUEST_FINISHED, 'I gave the ring back.')])])

    def test_report_and_budget(self):
        r = self.report
        self.assertEqual(r['bytes'], len(self.raw))
        self.assertEqual(r['resident_bytes'], self.t['resident_bytes'])
        self.assertEqual(r['conversation_bytes'], self.t['conversation_bytes'])
        self.assertEqual(r['resident_bytes'], D.HEADER + 8 * len(self.names) + 4 * len(NPCS) +
                         4 * len(dialogue.FUNCTIONS) + (len(dialogue.FUNCTIONS) + 7) // 8 + 2 + 4 +
                         4 * len(D.SETTINGS) + D.FACTION_ID * 2 + 4 * 3)
        self.assertEqual(sum(r['section_bytes'].values()) + D.HEADER, r['bytes'])
        self.assertLessEqual(r['resident_bytes'], D.RESIDENT_BUDGET)

    def test_first_match_reference(self):
        npc, t = self.order.index('fargoth'), self.t
        helped = self.names.index('Help')
        base = {'choice': -1, 'random': 0, 'disposition': 50}
        self.assertEqual(t['text'](t['entries'][ref_answer(t, npc, helped, dict(base, choice=1))][0]), 'Good, good.')
        self.assertEqual(t['text'](t['entries'][ref_answer(t, npc, helped, base)][0]), 'Help with what?')
        refused = ref_answer(t, npc, helped, dict(base, disposition=10))
        self.assertEqual(t['text'](t['entries'][refused][0]), 'I do not want to talk about that.')


class ImageStep(unittest.TestCase):
    def test_image_step_writes_the_table_beside_the_voice_table(self):
        from test_greeting_lut import esm
        k = kinds()
        records = [('GMST', v) for v in k['GMST'].values()]
        records += [(tag, v) for tag in ('RACE', 'CLAS', 'FACT') for v in k[tag].values()]
        records += [('NPC_', v) for v in NPCS.values()]
        raw = esm(records)
        for topic, infos in TOPICS.items():
            name = DIALS.get(topic, (topic, 0))
            raw += esm([('DIAL', [('NAME', name[0]), ('DATA', bytes([name[1]]))])] + [('INFO', i) for i in infos])
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'Data Files'
            data.mkdir()
            (data / 'Morrowind.esm').write_bytes(raw)
            G.image_step(data, Path(tmp) / 'id1', Path(tmp) / 'out')
            report = D.image_step(data, Path(tmp) / 'id1', Path(tmp) / 'out')
            table = D.read((Path(tmp) / 'id1' / D.NAME).read_bytes())
            self.assertTrue((Path(tmp) / 'out' / 'dialogue-table.json').is_file())
            # the NPC rows are the voice table's: checked by the step against id1/npc-voices.lut
            voices = list(G.read((Path(tmp) / 'id1' / G.NAME).read_bytes())['npcs'])
            self.assertEqual(len(table['rows']), len(voices))
            # a voice table of other NPCs is refused
            (Path(tmp) / 'id1' / G.NAME).write_bytes(G.build(dict(k, NPC_={'fargoth': NPCS['fargoth']}),
                                                             TOPICS)[0])
            with self.assertRaises(ValueError):
                D.image_step(data, Path(tmp) / 'id1', None)
        self.assertEqual(report['npcs'], len(NPCS))
        self.assertFalse(report['reused'])
        self.assertIn(D.INFO_REFUSAL, [n.casefold() for n, _ in table['topics']])

    def test_wired_into_the_image(self):
        self.assertIn('dialogue_lut', (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))

    def test_contract_matches_the_engine_header(self):
        header = (ROOT / 'engine/aga/src/aw_dial.h').read_text(encoding='utf-8')
        for define, value in (('VERSION', D.VERSION), ('HEADER', D.HEADER),
                              ('TOPIC_ROW', struct.calcsize(D.TOPIC_ROW)), ('ENTRY_ROW', struct.calcsize(D.ENTRY_ROW)),
                              ('LIST_ROW', struct.calcsize(D.LIST_ROW)), ('QUEST_ROW', struct.calcsize(D.QUEST_ROW)),
                              ('JOURNAL_ROW', struct.calcsize(D.JOURNAL_ROW)), ('ENTRY_LAST', D.ENTRY_LAST),
                              ('KIND_TOPIC', D.KIND_TOPIC), ('KIND_PERSUASION', D.KIND_PERSUASION),
                              ('BUFFER', D.BUFFER_BUDGET)):
            self.assertRegex(header, r'#define AW_DIAL_%s %d\b' % (define, value))
        self.assertEqual(struct.calcsize(D.HEADER_FORMAT) + 4, D.HEADER)
        import re
        block = re.search(r'enum \{(AW_DIAL_SET_[^}]*)\}', header).group(1)
        names = [n for n in re.findall(r'AW_DIAL_SET_(\w+)', block)]
        self.assertEqual(len(names), len(D.SETTINGS))
        self.assertIn('AW_DIAL_SETTINGS}', block.replace(' ', '').replace('\n', '') + '}')
        self.assertRegex(header, r'#define AW_DIAL_FACTION_ID %d\b' % D.FACTION_ID)
        glut = (ROOT / 'engine/aga/src/aw_glut.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_GLUT_FN_CHOICE %d' % dialogue.FUNCTIONS.index('Choice'), glut)
        self.assertIn('aw_dial.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))


@unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
class NativeDialogue(unittest.TestCase):
    """engine/aga/src/aw_dial.c (+ aw_glut.c's shared evaluator) on the builder's files (tests/aga_dial_test.c): the
    rows, the first match with the refusal rule, the texts, scripts and links against this module's answers."""

    @classmethod
    def setUpClass(cls):
        cls.raw, _ = D.build(kinds(), TOPICS, DIALS)
        cls.voices, _ = G.build(kinds(), TOPICS)
        cls.t = D.read(cls.raw)
        cls.tmp = tempfile.TemporaryDirectory(prefix='amiwind-dial-c-')
        tmp = Path(cls.tmp.name)
        (tmp / D.NAME).write_bytes(cls.raw)
        (tmp / G.NAME).write_bytes(cls.voices)
        src = ROOT / 'engine/aga/src'
        result = subprocess.run(['cc', '-std=gnu89', '-O1', '-Wall', '-Wno-unused', '-fsanitize=undefined,address',
                                 '-fno-sanitize-recover=all', '-DAW_GLUT_HOST_TEST', '-I' + str(src),
                                 str(ROOT / 'tests/aga_dial_test.c'), str(src / 'aw_dial.c'), str(src / 'aw_glut.c'),
                                 '-lm', '-o', str(tmp / 'dial')], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_reader_and_first_match_match_the_tool(self):
        t, lines = self.t, []
        order = list(G.read(self.voices)['npcs'])
        names = [n for n, _ in t['topics']]
        for npc, ident in enumerate(order):
            lines.append('row\t%s\t%d\t%s' % (ident, npc, ','.join(str(x) for x in sorted(t['rows'][npc])) or '-'))
            for topic in range(len(names)):
                for disposition in (0, 30, 60, 100):
                    for choice in (-1, 1, 2):
                        for random in (0, 50, 100):
                            state = {'choice': choice, 'random': random, 'disposition': disposition}
                            got = ref_answer(t, npc, topic, state)
                            text = '-' if got < 0 or t['entries'][got][0] == D.NONE32 else \
                                t['text'](t['entries'][got][0])
                            script = '-' if got < 0 or t['entries'][got][2] == D.NONE32 else \
                                t['script'](t['entries'][got][2]).replace('\n', '|')
                            links = ','.join(str(x) for x in (D.answers(t, npc, topic)[
                                D.candidates(t, npc, topic).index(got)][2] if got >= 0 and got in
                                D.candidates(t, npc, topic) else [])) or '-'
                            lines.append('answer\t%s\t%d\t%d\t%d\t%d\t%d\t%s\t%s\t%s' % (
                                ident, topic, disposition, choice, random, got, text, script, links))
            for disposition in (0, 50, 100):
                for which, known in (('all', set(range(len(names)))), ('start', set(t['start']))):
                    state = {'choice': -1, 'random': 50, 'disposition': disposition}
                    lines.append('list\t%s\t%d\t%s\t%s' % (ident, disposition, which,
                                                          ','.join(map(str, ref_list(t, npc, known, state))) or '-'))
        # the live state (aw_glut_live: the scripts' journal, locals, dead counts, items, the player's ranks)
        live = {'journal': {'a1_fargoth': 10}, 'local': {1: 1}, 'rank': {'mages guild': 0},
                'item': {'gold_001': 100}, 'dead': {}, 'global': {}}
        lines.append('live')
        for kind in ('journal', 'item', 'rank'):
            for name, value in live[kind].items():
                lines.append('set\t%s\t%s\t%d' % (kind, name, value))
        for slot, value in live['local'].items():
            lines.append('set\tlocal\t%d\t%d' % (slot, value))
        for npc, ident in enumerate(order):
            lines.append('row\t%s\t%d\t%s' % (ident, npc, ','.join(str(x) for x in sorted(t['rows'][npc])) or '-'))
            faction = dialogue.text(NPCS[ident], 'ANAM').casefold() or None
            lines.append('faction\t%s' % (faction or '-'))
            for topic in range(len(names)):
                for disposition in (0, 60):
                    for choice in (-1, 1):
                        state = {'choice': choice, 'random': 50, 'disposition': disposition, 'live': live,
                                 'faction': faction}
                        got = ref_answer(t, npc, topic, state)
                        text = '-' if got < 0 or t['entries'][got][0] == D.NONE32 else t['text'](t['entries'][got][0])
                        script = '-' if got < 0 or t['entries'][got][2] == D.NONE32 else \
                            t['script'](t['entries'][got][2]).replace('\n', '|')
                        e = t['entries'][got] if got >= 0 else None
                        links = ','.join(str(x) for x in t['links'][e[3]:e[3] + e[4]]) if e and e[3] != D.NONE32 \
                            else '-'
                        lines.append('answer\t%s\t%d\t%d\t%d\t50\t%d\t%s\t%s\t%s' % (
                            ident, topic, disposition, choice, got, text, script, links or '-'))
        self.live_answers = sum(1 for line in lines if line.startswith('answer') and 'You found it!' in line)
        self.assertGreater(self.live_answers, 0)                  # the local made an answer reachable
        for base, race, personality, bounty, faction, ranks, diseased, weapon in DISPOSITION_CASES:
            for clamp in (1, 0):
                want = D.derived_disposition(t, base, race, personality, bounty, faction, ranks, diseased, weapon,
                                             clamp=bool(clamp))
                lines.append('disp\t%d\t%d\t%d\t%d\t%s\t%s\t%d\t%d\t%d\t%d' % (
                    base, race, personality, bounty, faction or '-',
                    ','.join('%s:%d:%d' % (k, r, e) for k, (r, e) in sorted(ranks.items())) or '-', diseased,
                    weapon, clamp, want))
        for faction, names in zip(t['factions'], t['rank_names']):
            for rank, name in enumerate(names):
                lines.append('rank\t%s\t%d\t%s' % (faction.upper() if rank == 1 else faction, rank, name or '-'))
        lines.append('rank\tno such faction\t0\t-')
        for text, pc, nxt, cell, want in (
                ('You are %PCRank; next %NextPCRank. In %Cell, %PCName.', 'Associate', 'Apprentice', 'Seyda Neen',
                 'You are Associate; next Apprentice. In Seyda Neen, %PCName.'),
                ('%pcrank %NEXTPCRANK %cell %PCRace %Name', '%', '%', 'Balmora', '% % Balmora %PCRace %Name'),
                ('100% sure', 'x', 'y', 'z', '100% sure')):
            lines.append('defines\t%s\t%s\t%s\t%s\t%s' % (text, pc, nxt, cell, want))
        lines.append('start\t%s' % (','.join(map(str, t['start'])) or '-'))
        for cols, text, want in ((10, 'Hello there outlander', 'Hello|there|outlander'),
                                 (5, 'abcdefgh ij', 'abcde|fgh|ij'), (11, 'one two\nthree', 'one two|three'),
                                 (8, 'a\n\nb', 'a|~|b'), (24, 'short', 'short')):
            lines.append('wrap\t%d\t%s\t%s' % (cols, text.replace('\n', '\\n'), want))
        path = Path(self.tmp.name) / 'expect.txt'
        path.write_text('\n'.join(lines) + '\n', encoding='cp1252')
        result = subprocess.run([str(Path(self.tmp.name) / 'dial'), str(Path(self.tmp.name) / D.NAME),
                                 str(Path(self.tmp.name) / G.NAME), str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('%d checks' % len(lines), result.stdout)


if __name__ == '__main__':
    unittest.main()
