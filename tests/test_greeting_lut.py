# SPDX-License-Identifier: GPL-3.0-only
"""The NPC voice and greeting table (tools/greeting_lut.py, AWGL1; NPC-GREETINGS-LIBRARY-MUTE-48).

Synthetic records only (no game data): Voice topics by race and sex, an id-specific line, a faction-filtered one, a
disposition condition and a Random100 one left for run time, conversation greetings gated by a journal entry and by
TalkedToPc, a speaker define kept for the engine. Checked: the lines each NPC's merged lists give equal the INFOs
the shared filter (mwad.dialogue.Context.compile) lets that NPC say, in the original's order, up to the first one
without a run-time condition; the condition records' opcodes; the build-time evaluation of the town residents'
greeting is unchanged by the compile step; library NPCs (tools/npc_library.py entity texts) find their record; the
image step writes id1/npc-voices.lut from a Data Files folder.
"""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import greeting_lut as G  # noqa: E402
import mwad.dialogue as dialogue  # noqa: E402
from npc_anim import voice_pool_name  # noqa: E402


def f(tag, value):
    return (tag, value.encode('cp1252') + b'\0' if isinstance(value, str) else value)


def info(identifier, line, kind=1, disp=0, rank=-1, gender=-1, sound='', scvr=(), **filters):
    fields = [f('INAM', identifier), ('DATA', struct.pack('<iibbbb', kind, disp, rank, gender, -1, 0))]
    for tag in ('ONAM', 'RNAM', 'CNAM', 'FNAM', 'ANAM', 'DNAM'):
        if tag in filters:
            fields.append(f(tag, filters[tag]))
    for rule, value in scvr:
        fields += [('SCVR', rule.encode('cp1252')), ('INTV', struct.pack('<i', value))]
    fields.append(f('NAME', line))
    if sound:
        fields.append(f('SNAM', sound))
    return fields


def npc(identifier, name, race, cls='Commoner', faction='', female=False, rank=0, disposition=50, hello=30):
    return [f('NAME', identifier), f('FNAM', name), f('RNAM', race), f('CNAM', cls), f('ANAM', faction),
            ('FLAG', struct.pack('<I', 1 if female else 0)),
            ('NPDT', struct.pack('<hBBBBBBi', 5, disposition, 3, rank, 0, 0, 0, 0)),
            ('AIDT', struct.pack('<HBBB3xI', hello, 10, 20, 0, 0))]


NPCS = {'dunmer_m': npc('dunmer_m', 'Dral', 'Dark Elf'),
        'dunmer_f': npc('dunmer_f', 'Dralasa', 'Dark Elf', female=True),
        'breton_m': npc('breton_m', 'Jean', 'Breton'),
        'imperial_m': npc('imperial_m', 'Marcus', 'Imperial', hello=0),
        'fargoth': npc('fargoth', 'Fargoth', 'Wood Elf'),
        'mage': npc('mage', 'Edwinna', 'Breton', cls='Mage', faction='Mages Guild', female=True, rank=2,
                    disposition=70)}
RANDOM = ('02fX3Random100', 50)               # global Random100 >= 50
JOURNAL = ('04JX3A1_Fargoth', 10)             # journal A1_Fargoth >= 10
TALKED = ('01630', 0)                         # TalkedToPc == 0
HURT = ('01044', 50)                          # Health_Percent < 50

TOPICS = {
    'hello': [info('h1', "Fargoth's hello", ONAM='fargoth', sound='vo\\w\\m\\hlo_fargoth.mp3'),
              info('h2', 'Guild hello', FNAM='Mages Guild', sound='vo\\b\\f\\hlo_mg.mp3'),
              info('h3', 'Friendly sera', RNAM='Dark Elf', gender=1, disp=60, sound='vo\\d\\f\\hlo_df_60.mp3'),
              info('h4', 'Hmph.', RNAM='Dark Elf', gender=1, sound='vo\\d\\f\\hlo_df.mp3'),
              info('h5', 'Outlander.', RNAM='Dark Elf', gender=0, sound='vo\\d\\m\\hlo_dm.mp3'),
              info('h6', 'Hello.', RNAM='Breton', sound='vo\\b\\m\\hlo_bm.mp3'),
              info('h7', 'Hm?', scvr=[RANDOM], sound='vo\\i\\m\\hlo_im.mp3')],
    'idle': [info('i1', 'What a day.', RNAM='Dark Elf', scvr=[RANDOM], sound='vo\\d\\m\\idl_dm.mp3'),
             info('i2', '', sound='vo\\misc\\hum.mp3')],
    'hit': [info('t1', 'Ow!', scvr=[HURT], sound='vo\\d\\m\\hit_dm1.mp3'),
            info('t2', 'Ugh.', sound='vo\\d\\m\\hit_dm2.mp3')],
    'attack': [info('a1', 'Die!', sound='vo\\d\\m\\atk_dm.mp3')],
    'flee': [info('f1', 'Mercy!', sound='vo\\d\\m\\fle_dm.mp3')],
    'intruder': [info('n1', 'Get out!', sound='vo\\d\\m\\int_dm.mp3')],
    'thief': [info('s1', 'Thief!', sound='vo\\d\\m\\thf_dm.mp3')],
    'greeting 0': [info('g1', 'About that ring...', kind=2, scvr=[JOURNAL])],
    'greeting 1': [info('g2', 'Hello, %PCName. I am Fargoth.', kind=2, ONAM='fargoth', scvr=[TALKED]),
                   info('g3', 'I am %Name, a %Class of the %Faction.', kind=2, CNAM='Mage')],
    'greeting 9': [info('g4', 'What do you want, %PCRace?', kind=2)],
}


def kinds():
    out = {'NPC_': dict(NPCS), 'CLOT': {}, 'ARMO': {}, 'REGN': {}, 'GLOB': {}, 'SCPT': {},
           'RACE': {r.casefold(): [f('NAME', r), f('FNAM', r)] for r in ('Dark Elf', 'Breton', 'Imperial', 'Wood Elf')},
           'CLAS': {'mage': [f('NAME', 'Mage'), f('FNAM', 'Mage')], 'commoner': [f('NAME', 'Commoner'),
                                                                                 f('FNAM', 'Commoner')]},
           'FACT': {'mages guild': [f('NAME', 'Mages Guild'), f('FNAM', 'Mages Guild'), f('RNAM', 'Associate'),
                                    f('RNAM', 'Apprentice'), f('RNAM', 'Journeyman')]},
           'GMST': {'igreetdistancemultiplier': [f('NAME', 'iGreetDistanceMultiplier'), ('INTV', struct.pack('<i', 6))],
                    'fgreetdistancereset': [f('NAME', 'fGreetDistanceReset'), ('FLTV', struct.pack('<f', 512.))],
                    'igreetduration': [f('NAME', 'iGreetDuration'), ('INTV', struct.pack('<i', 4))]},
           'DIAL': {t: (2 if t.startswith('greeting') else 1) for t in TOPICS}}
    return out


def brute_force(k, ident, topic, home=None):
    """What the NPC's topic should walk: every INFO the shared filter lets it say, in order, up to the first
    without a run-time condition."""
    context = dialogue.Context(k, ident, cell=home or G.NO_CELL)
    out = []
    for fields in G.topic_infos(k, TOPICS, topic):
        runtime = context.compile(fields)
        if runtime is None:
            continue
        out.append((dialogue.text(fields, 'NAME'), dialogue.text(fields, 'SNAM'), len(runtime)))
        if not runtime:
            break
    return out


class VoiceTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw, cls.report = G.build(kinds(), TOPICS)
        cls.t = G.read(cls.raw)

    def hellos(self, ident):
        return [line for line, _, _ in G.lines(self.t, ident, 'hello')]

    def test_topics_and_rows(self):
        self.assertEqual(self.t['topics'], ['hello', 'idle', 'intruder', 'thief', 'hit', 'attack', 'flee', 'greeting'])
        self.assertEqual(sorted(self.t['npcs']), sorted(NPCS))
        self.assertEqual(self.t['npcs']['dunmer_m']['hello'], 45)      # Hello 30 x 6 x 0.25
        self.assertEqual(self.t['npcs']['imperial_m']['hello'], 0)
        self.assertEqual((self.t['reset'], self.t['duration']), (128, 4))
        self.assertEqual(self.t['npcs']['mage']['rank'], 2)
        self.assertEqual(self.t['npcs']['dunmer_m']['rank'], -1)
        self.assertEqual(self.t['npcs']['mage']['defines'],
                         {'class': 'Mage', 'race': 'Breton', 'faction': 'Mages Guild', 'rank': 'Journeyman',
                          'cell': None})
        self.assertEqual(self.report['bytes'], len(self.raw))

    def test_race_sex_id_and_faction_voices(self):
        self.assertEqual(self.hellos('fargoth'), ["Fargoth's hello"])
        self.assertEqual(self.hellos('mage'), ['Guild hello'])
        self.assertEqual(self.hellos('dunmer_f'), ['Friendly sera', 'Hmph.'])
        self.assertEqual(self.hellos('dunmer_m'), ['Outlander.'])
        self.assertEqual(self.hellos('breton_m'), ['Hello.'])
        self.assertEqual(self.hellos('imperial_m'), ['Hm?'])          # only a run-time line: it may stay silent
        _, sound, conds = G.lines(self.t, 'dunmer_m', 'hello')[0]
        self.assertEqual(sound, voice_pool_name('vo\\d\\m\\hlo_dm.mp3')[6:22])
        self.assertEqual(conds, [])

    def test_runtime_conditions_are_condition_records(self):
        _, _, conds = G.lines(self.t, 'dunmer_f', 'hello')[0]
        self.assertEqual(conds, [(G.OP_DISP, 3, 0, 60)])               # disposition >= 60, at greet time
        _, _, conds = G.lines(self.t, 'imperial_m', 'hello')[0]
        self.assertEqual(conds, [(G.OP_RANDOM100, 3, 0, 50)])
        _, _, conds = G.lines(self.t, 'dunmer_m', 'hit')[0]
        self.assertEqual(conds, [(G.OP_FUNC, 4, dialogue.FUNCTIONS.index('Health_Percent'), 50)])
        journal = G.lines(self.t, 'dunmer_m', 'greeting')[0]
        self.assertEqual(journal[0], 'About that ring...')
        self.assertEqual(journal[2][0][:2], (G.OP_JOURNAL, 3))
        self.assertEqual(self.t['names'][journal[2][0][2]], 'a1_fargoth')

    def test_conversation_greeting_lists(self):
        self.assertEqual([x[0] for x in G.lines(self.t, 'fargoth', 'greeting')],
                         ['About that ring...', 'Hello, %PCName. I am Fargoth.', 'What do you want, %PCRace?'])
        talked = G.lines(self.t, 'fargoth', 'greeting')[1][2]
        self.assertEqual(talked, [(G.OP_FUNC, 0, dialogue.FUNCTIONS.index('TalkedToPc'), 0)])
        # the speaker's defines stay in the text: the engine fills them from the NPC row
        self.assertEqual([x[0] for x in G.lines(self.t, 'mage', 'greeting')],
                         ['About that ring...', 'I am %Name, a %Class of the %Faction.'])

    def test_lists_match_the_filter_for_every_npc_and_topic(self):
        k = kinds()
        for ident in NPCS:
            for topic in self.t['topics']:
                with self.subTest(npc=ident, topic=topic):
                    got = [(line or '', '' if sound is None else sound, len(conds))
                           for line, sound, conds in G.lines(self.t, ident, topic)]
                    want = [(line, voice_pool_name(sound)[6:22] if sound else '', n)
                            for line, sound, n in brute_force(k, ident, topic)]
                    self.assertEqual(got, want)

    def test_shared_storage(self):
        # one entry per INFO as its audience sees it; every sound stored once
        self.assertEqual(len(self.t['sounds']), len(set(self.t['sounds'])))
        self.assertLessEqual(self.report['entries'], sum(len(v) for v in TOPICS.values()))

    def test_build_time_greeting_unchanged_by_the_compile_step(self):
        # the town residents' conversation greeting (TalkGreetings) evaluates the compiled conditions with its fixture
        k = kinds()
        for ident in NPCS:
            context = dialogue.Context(k, ident)
            for fields in G.topic_infos(k, TOPICS, 'greeting') + TOPICS['hello']:
                runtime = context.compile(fields)
                verdict = context.info(fields)
                if runtime is None:
                    self.assertIs(verdict, False)
                elif not runtime:
                    self.assertIs(verdict, True)

    def test_non_ascii_ids_are_left_out_with_a_reason(self):
        k = kinds()
        k['NPC_']['atúlg'] = npc('atúlg', 'Atulg', 'Breton')
        _, report = G.build(k, TOPICS)
        self.assertIn('atúlg', report['left_out'])


class LibraryAndImageStep(unittest.TestCase):
    def test_library_npc_finds_its_record(self):
        import npc_library
        raw, _ = G.build(kinds(), TOPICS)
        t = G.read(raw)
        text = npc_library.entity_text('Dunmer_M', {'name': 'Dral', 'dead': False, 'key': 'x'},
                                       {'model': 'progs/n_x.mdl', 'step': 0.1})
        fields = dict(line.split('" "', 1) for line in text.strip('\n').strip('"').split('"\n"'))
        self.assertEqual((fields['aw_voice'], fields['aw_hello_distance']), ('', '0'))
        ident = fields['aw_source_id'].casefold()                      # the engine compares without case
        self.assertIn(ident, t['npcs'])
        self.assertEqual([x[0] for x in G.lines(t, ident, 'hello')], ['Outlander.'])
        self.assertGreater(t['npcs'][ident]['hello'], 0)
        self.assertTrue(G.lines(t, ident, 'greeting'))

    def test_image_step_writes_the_table(self):
        def sub(tag, data):
            data = data.encode('cp1252') + b'\0' if isinstance(data, str) else data
            return tag.encode() + struct.pack('<I', len(data)) + data

        def rec(tag, fields):
            body = b''.join(sub(t, d if isinstance(d, (bytes, str)) else d) for t, d in fields)
            return tag.encode() + struct.pack('<III', len(body), 0, 0) + body
        k = kinds()
        raw = b''.join(rec('GMST', v) for v in k['GMST'].values())
        raw += b''.join(rec(tag, v) for tag in ('RACE', 'CLAS', 'FACT') for v in k[tag].values())
        raw += b''.join(rec('NPC_', v) for v in NPCS.values())
        for topic, infos in TOPICS.items():
            raw += rec('DIAL', [('NAME', topic), ('DATA', bytes([k['DIAL'][topic]]))])
            raw += b''.join(rec('INFO', i) for i in infos)
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'Data Files'
            data.mkdir()
            (data / 'Morrowind.esm').write_bytes(raw)
            report = G.image_step(data, Path(tmp) / 'id1', Path(tmp) / 'out')
            table = G.read((Path(tmp) / 'id1' / G.NAME).read_bytes())
            self.assertTrue((Path(tmp) / 'out' / 'npc-voice-table.json').is_file())
        self.assertEqual(sorted(table['npcs']), sorted(NPCS))
        self.assertEqual(report['npcs'], len(NPCS))
        self.assertFalse(report['reused'])
        # no sound sources in this folder: every named voice is listed as missing (the engine stays quiet)
        self.assertIn('vo/d/m/hlo_dm.mp3', report['missing_sources'])


def ref_holds(t, ident, cond, state):
    """The engine's condition test (aw_glut.c AW_GlutHolds), for the expectations."""
    op, cmp, operand, value = cond
    npc = t['npcs'][ident]
    compare = [lambda x, v: x == v, lambda x, v: x != v, lambda x, v: x > v, lambda x, v: x >= v,
               lambda x, v: x < v, lambda x, v: x <= v][cmp & 7]
    if op == G.OP_FUNC:
        number = dialogue.FUNCTIONS.index
        live = {number('Health_Percent'): state['speaker'], number('PcHealthPercent'): state['player'],
                number('PcHealth'): state['player'], number('TalkedToPc'): state['talked'],
                number('FactionRankDifference'): 0 if npc['rank'] < 0 else -1 - npc['rank']}
        x = live.get(operand, t['fixture'].get(operand))
        return x is not None and compare(x, value)
    if op == G.OP_RANDOM100:
        return compare(state['random'], value)
    if op == G.OP_DISP:
        return compare(npc['disposition'], value)
    if op in (G.OP_JOURNAL, G.OP_LOCAL, G.OP_DEAD):
        return compare(0, value)
    if op == G.OP_NOTLOCAL:
        return not compare(0, value)
    raise AssertionError('no reference for opcode %d' % op)


def ref_pick(t, ident, topic, state):
    for e in G.candidates(t, ident, topic):
        _, first, _, n, _ = t['entries'][e]
        if all(ref_holds(t, ident, c, state) for c in t['conds'][first:first + n]):
            return e
    return -1


@unittest.skipUnless(__import__('shutil').which('cc'), 'a C compiler is required')
class NativeVoiceTable(unittest.TestCase):
    """engine/aga/src/aw_glut.c on the builder's file (tests/aga_glut_test.c): the lookup and pick against the
    reference above for every NPC, topic and a spread of run-time states; then the engine glue (greet trigger)."""

    @classmethod
    def setUpClass(cls):
        import subprocess
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_aga_native_source import tree_project_version
        cls.raw, _ = G.build(kinds(), TOPICS)
        cls.t = G.read(cls.raw)
        cls.tmp = tempfile.TemporaryDirectory(prefix='amiwind-glut-c-')
        tmp = Path(cls.tmp.name)
        (tmp / G.NAME).write_bytes(cls.raw)
        tree_project_version().generate_native(ROOT / 'VERSION', tmp)
        src = ROOT / 'engine/aga/src'
        common = ['cc', '-std=gnu89', '-O1', '-Wall', '-Wno-unused', '-fsanitize=undefined',
                  '-fno-sanitize-recover=all', '-include', str(ROOT / 'tests/aga_test_files.h'), '-I' + str(tmp),
                  '-I' + str(src), str(ROOT / 'tests/aga_glut_test.c'), str(src / 'aw_glut.c')]
        for name, extra in (('pure', ['-DAW_GLUT_HOST_TEST']), ('glue', [str(src / 'aw_anim.c'), str(src / 'mathlib.c')])):
            result = subprocess.run(common + extra + ['-lm', '-o', str(tmp / name)], capture_output=True, text=True)
            assert result.returncode == 0, result.stderr

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_check(self, *args):
        import subprocess
        result = subprocess.run([str(Path(self.tmp.name) / args[0]), *args], capture_output=True, text=True,
                                cwd=self.tmp.name)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_lookup_and_pick_match_the_reference(self):
        t, lines = self.t, []
        order = sorted(t['npcs'])
        for ident in order:
            lines.append('find\t%s\t%d' % (ident.upper() if ident == 'fargoth' else ident, order.index(ident)))
            lines.append('hello\t%s\t%d' % (ident, t['npcs'][ident]['hello']))
            for topic in t['topics']:
                for talked in (0, 1):
                    for random in (0, 49, 50, 100):
                        for speaker in (100, 20):
                            state = {'talked': talked, 'random': random, 'speaker': speaker, 'player': 100}
                            lines.append('pick\t%s\t%s\t%d\t%d\t%d\t100\t%d' % (
                                ident, topic, talked, random, speaker, ref_pick(t, ident, topic, state)))
        for e, (_, _, sound, _, _) in enumerate(t['entries']):
            lines.append('sound\t%d\t%s' % (e, '-' if sound == G.NONE16 else t['sounds'][sound]))
        lines.append('expand\tmage\tEdwinna\tI am %Name, a %Class of the %Faction (%Rank), %PCName. 10%\t'
                     'I am Edwinna, a Mage of the Mages Guild (Journeyman), %PCName. 10%')
        lines.append('expand\tdunmer_m\tDral\t%name of %CELL in %Faction\tDral of  in ')
        path = Path(self.tmp.name) / 'expect.txt'
        path.write_text('\n'.join(lines) + '\n', encoding='cp1252')
        self.assertIn('%d checks' % len(lines), self.run_check('pure', str(Path(self.tmp.name) / G.NAME), str(path)))

    def test_engine_glue_greet_trigger(self):
        present = [voice_pool_name(s)[6:22] for s in ('vo\\d\\m\\hlo_dm.mp3', 'vo\\b\\m\\hlo_bm.mp3',
                                                      'vo\\d\\m\\atk_dm.mp3')]
        self.assertIn('glue ok', self.run_check('glue', str(Path(self.tmp.name) / G.NAME), ','.join(present)))


class EngineSource(unittest.TestCase):
    def test_wired_and_documented(self):
        src = ROOT / 'engine/aga/src'
        self.assertIn('aw_glut.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))
        self.assertIn('AW_GlutInit();', (src / 'aw_debug.c').read_text(encoding='utf-8'))
        qc = (ROOT / 'engine/aga/qc/world.qc').read_text(encoding='utf-8')
        for line in ('aw_glut_prep = #84', 'aw_glut_say = #85', 'aw_glut_text = #86', 'aw_glut_prep(self);'):
            self.assertIn(line, qc)
        builtins = (src / 'pr_cmds.c').read_text(encoding='latin-1').split('builtin_t pr_builtin[] =', 1)[1]
        for name in ('PF_aw_glut_prep, /* #84', 'PF_aw_glut_say,  /* #85', 'PF_aw_glut_text  /* #86'):
            self.assertIn(name, builtins)
        header = (src / 'aw_glut.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_GLUT_HEADER %d' % G.HEADER, header)
        self.assertIn('#define AW_GLUT_NPC_ROW %d' % G.NPC_ROW_BYTES, header)
        for name in G.LIVE_FUNCTIONS:
            number = dialogue.FUNCTIONS.index(name)
            self.assertRegex(header, r'#define AW_GLUT_FN_\w+ %d\b' % number)
        doc = (ROOT / 'docs/NPC_VOICE_TABLE.md').read_text(encoding='utf-8')
        for code in range(1, 12):
            self.assertIn('| %d |' % code, doc)                      # the opcode table the scripts step reuses
        self.assertIn('greeting_lut', (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
