# SPDX-License-Identifier: GPL-3.0-only
"""Reference closure of an area build (--exclude-unreferenced, tools/content_closure.py).

A synthetic master (no game data): a built interior with two NPCs, a rope
(dressing), a light and a missing record; a far cell with a third NPC; a script
that spawns an NPC into the built cell; dialogue lines with every static
condition. The closure must keep exactly the built NPCs' parts and their whole
dialogue pool, keep the scripted arrival and everything unresolved, keep all
placed content (dressing included) and never touch music.
"""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

import content_closure as cc  # noqa: E402
import build_exclusions as ex  # noqa: E402


def sub(tag, data):
    if isinstance(data, str):
        data = data.encode('cp1252') + b'\0'
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def record(tag, *subs, flags=0):
    body = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(body), 0, flags) + body


def npc(identifier, race, female=False, cls='guard', faction='', head='', hair='', items=(), script=''):
    subs = [sub('NAME', identifier), sub('MODL', ''), sub('RNAM', race), sub('CNAM', cls), sub('ANAM', faction),
            sub('BNAM', head), sub('KNAM', hair), sub('FLAG', struct.pack('<i', 1 if female else 0))]
    subs += [sub('NPCO', struct.pack('<i', 1) + item.encode().ljust(32, b'\0')) for item in items]
    if script:
        subs.append(sub('SCRI', script))
    return record('NPC_', *subs)


def body(identifier, race, female=False, part_type=0, model=''):
    return record('BODY', sub('NAME', identifier), sub('MODL', model or identifier + '.nif'), sub('FNAM', race),
                  sub('BYDT', bytes([0, 0, 1 if female else 0, part_type])))


def cell(name, *refs):
    subs = [sub('NAME', name), sub('DATA', struct.pack('<Iii', 1, 0, 0))]
    for number, ref in enumerate(refs, 1):
        subs += [sub('FRMR', struct.pack('<I', number)), sub('NAME', ref),
                 sub('DATA', struct.pack('<6f', 0, 0, 0, 0, 0, 0))]
    return record('CELL', *subs)


def script(name, source):
    return record('SCPT', sub('SCHD', name.encode().ljust(32, b'\0') + bytes(20)), sub('SCTX', source.encode('cp1252')))


def info(identifier, sound, race='', sex=-1, speaker='', cls='', faction='', cell_name='', conditions=False):
    subs = [sub('INAM', identifier), sub('DATA', struct.pack('<iibbbb', 0, 0, -1, sex, -1, 0))]
    for tag, value in (('ONAM', speaker), ('RNAM', race), ('CNAM', cls), ('FNAM', faction), ('ANAM', cell_name)):
        if value:
            subs.append(sub(tag, value))
    if conditions:
        subs.append(sub('SCVR', '01X1000Random100'))
    subs.append(sub('SNAM', sound))
    return record('INFO', *subs)


def master_bytes():
    return b''.join([
        npc('npc_a', 'Dark Elf', head='b_head_a', hair='b_hair_a', items=['clothes_a'], script='script_a'),
        npc('npc_b', 'Nord', female=True, cls='mage'),
        npc('npc_far', 'Nord'),
        npc('npc_spawned', 'Redguard'),
        body('b_head_a', 'Dark Elf'), body('b_de_m_chest', 'Dark Elf'), body('b_n_f_chest', 'Nord', female=True),
        body('b_n_m_chest', 'Nord'), body('b_r_m_chest', 'Redguard'), body('c_part_m', 'Dark Elf', part_type=1),
        record('CLOT', sub('NAME', 'clothes_a'), sub('MODL', 'c/shirt.nif'), sub('INDX', b'\0'), sub('BNAM', 'c_part_m')),
        record('STAT', sub('NAME', 'dressing_rope'), sub('MODL', 'x\\Rope.nif')),
        record('MISC', sub('NAME', 'gold_001'), sub('MODL', 'm/gold.nif')),
        record('LIGH', sub('NAME', 'light_a'), sub('MODL', 'l/torch.nif'), sub('SNAM', 'fire_sound')),
        record('LIGH', sub('NAME', 'light_far'), sub('MODL', 'l/far.nif'), sub('SNAM', 'far_sound')),
        record('SOUN', sub('NAME', 'fire_sound'), sub('FNAM', 'Fx\\fire.wav')),
        record('SOUN', sub('NAME', 'far_sound'), sub('FNAM', 'Fx\\far.wav')),
        record('SOUN', sub('NAME', 'engine_sound'), sub('FNAM', 'Fx\\ui.wav')),
        script('script_a', 'begin script_a\nAddItem "gold_001" 5\nend'),
        script('spawner', 'begin spawner\nPlaceItemCell "npc_spawned" "Test Cell" 0 0 0 0\nend'),
        script('sayer', 'begin sayer\nSay "Vo\\misc\\Scripted.mp3" "A line"\nend'),
        cell('Test Cell', 'npc_a', 'npc_b', 'dressing_rope', 'light_a', 'missing_thing'),
        cell('Far Cell', 'npc_far', 'light_far'),
        record('DIAL', sub('NAME', 'Greeting 1'), sub('DATA', bytes([2]))),
        info('i1', 'Vo\\d\\m\\Hlo_a.mp3', race='Dark Elf', sex=0),
        info('i2', 'Vo\\n\\m\\Hlo_b.mp3', race='Nord', sex=0),          # only npc_far (not built)
        info('i3', 'Vo\\n\\f\\Hlo_c.mp3', race='Nord', sex=1),
        info('i4', 'Vo\\far.mp3', speaker='npc_far'),
        info('i5', 'Vo\\generic.mp3'),
        info('i6', 'Vo\\d\\m\\random.mp3', race='Dark Elf', conditions=True),  # unresolvable: kept
        info('i7', 'Vo\\d\\m\\vivec.mp3', race='Dark Elf', cell_name='Vivec'),
        info('i8', 'Vo\\guard.mp3', cls='guard'),
        info('i9', 'Vo\\mage_m.mp3', cls='mage', sex=0),                 # npc_b is a female mage
        info('i10', 'Vo\\nofaction.mp3', faction='FFFF'),
        info('i11', 'Vo\\temple.mp3', faction='Temple'),
        info('i12', 'Vo\\spawned.mp3', speaker='npc_spawned'),
    ])


def load():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'Morrowind.esm').write_bytes(master_bytes())
        return cc.Master.load(Path(tmp))


class Closure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master = load()
        cls.record = cc.closure(cls.master, ['interior:Test Cell'], list(cc.GROUPS))

    def test_exactly_the_built_npcs_and_their_parts(self):
        r = self.record
        self.assertEqual(r['npcs'], ['npc_a', 'npc_b', 'npc_spawned'])
        self.assertNotIn('npc_far', r['npcs'])
        self.assertEqual(r['body_parts'], ['b_de_m_chest', 'b_head_a', 'b_n_f_chest', 'b_r_m_chest', 'c_part_m'])
        self.assertNotIn('b_n_m_chest', r['body_parts'])  # a Nord male part: no Nord male is built

    def test_whole_dialogue_pool_of_the_included_npcs(self):
        self.assertEqual(self.record['voice_files'], sorted([
            'vo/d/m/hlo_a.mp3', 'vo/n/f/hlo_c.mp3', 'vo/generic.mp3', 'vo/d/m/random.mp3', 'vo/guard.mp3',
            'vo/nofaction.mp3', 'vo/spawned.mp3', 'vo/misc/scripted.mp3']))
        counts = self.record['counts']
        self.assertEqual(counts['voice_lines_kept'], 7)
        self.assertEqual(counts['voice_lines_dropped'], 5)  # i2 i4 i7 i9 i11

    def test_scripted_arrivals_and_unresolved_are_kept(self):
        r = self.record
        self.assertIn('npc_spawned', r['kept_by_script'])
        self.assertIn('names a built cell', r['kept_by_script']['npc_spawned'])
        self.assertIn('gold_001', r['kept_by_script'])
        self.assertEqual(sorted(u['id'] for u in r['unresolved_kept']), ['b_hair_a', 'missing_thing'])

    def test_every_placed_object_stays_dressing_included(self):
        models = self.record['models']
        for model in ('x/rope.nif', 'l/torch.nif', 'c/shirt.nif', 'm/gold.nif'):
            self.assertIn(model, models)
        self.assertNotIn('l/far.nif', models)

    def test_sounds_only_left_out_records_name_are_dropped(self):
        self.assertEqual(self.record['sound_files_dropped'], ['fx/far.wav'])  # fire stays, ui (unnamed) stays

    def test_music_is_never_part_of_a_closure(self):
        self.assertEqual(self.record['music'], 'always kept (owner rule)')
        self.assertNotIn('music', cc.GROUPS)
        with self.assertRaises(ValueError) as error:
            cc.parse_groups('voice,music')
        self.assertIn('always kept', str(error.exception))
        import prepare_media_assets as media
        keep, _ = media.closure_filter(self.record)
        self.assertTrue(keep('music/explore/a.mp3'))
        self.assertTrue(keep('sound/vo/d/m/hlo_a.mp3'))
        self.assertFalse(keep('sound/vo/n/m/hlo_b.mp3'))
        self.assertFalse(keep('sound/fx/far.wav'))
        self.assertTrue(keep('sound/fx/ui.wav'))

    def test_groups_choose_what_is_filtered(self):
        self.assertEqual(cc.parse_groups(None), list(cc.GROUPS))
        self.assertEqual(cc.parse_groups('voice'), ['voice'])
        self.assertEqual(cc.parse_groups('sounds,voice,npcs'), ['npcs', 'voice', 'sounds'])
        with self.assertRaises(ValueError):
            cc.parse_groups('trees')
        voice_only = cc.closure(self.master, ['interior:Test Cell'], ['voice'])
        import prepare_media_assets as media
        keep, _ = media.closure_filter(voice_only)
        self.assertTrue(keep('sound/fx/far.wav'))  # sounds not filtered with voice alone
        self.assertFalse(keep('sound/vo/far.mp3'))
        from build_gallery import gallery_filter
        self.assertIsNone(gallery_filter(voice_only))
        self.assertEqual(gallery_filter(self.record), {'npc_a', 'npc_b', 'npc_spawned'})

    def test_unknown_cells_are_rejected(self):
        with self.assertRaises(ValueError) as error:
            cc.closure(self.master, ['interior:Vivec, Arena Pit'], ['voice'])
        self.assertIn('Vivec, Arena Pit', str(error.exception))
        self.assertEqual(cc.cell_key('interior:Vivec, Arena Pit'), ('interior', 'vivec, arena pit'))
        self.assertEqual(cc.cell_key('cell:-3,-2'), ('exterior', -3, -2))

    def test_balmora_area_cells(self):
        cells = cc.area_cells('balmora')
        self.assertIn('cell:-3,-2', cells)
        self.assertEqual(len([c for c in cells if c.startswith('cell:')]), 9)
        self.assertIn("interior:Balmora, Caius Cosades' House", cells)


def default_plan():
    import build
    args = build.parser().parse_args([])
    args.data_files = Path('/owned/Data Files')
    args.sdk = Path('/sdk')
    tools = {n: '/tools/' + n for n in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
    with patch('build_jobs.auto_jobs', return_value=4):
        return build.commands(args, tools, Path('/private/run'))


class Plan(unittest.TestCase):
    def test_full_builds_refuse_and_area_builds_get_the_closure_stage(self):
        import build
        args = build.parser().parse_args(['--exclude-unreferenced'])
        with self.assertRaises(ValueError) as error:
            ex.resolve(args, '0.0.33-dev1')
        self.assertIn('needs an area build', str(error.exception))
        self.assertEqual(args.unreferenced_groups, list(cc.GROUPS))
        steps = ex.apply(default_plan(), ['unreferenced'], run=Path('/r'), area_cells=['interior:Test Cell'],
                         data_files=Path('/d'), closure_groups=['voice'])
        names = [name for name, _ in steps]
        self.assertEqual(names[0], ex.CLOSURE_STAGE)
        commands = dict(steps)
        self.assertIn('interior:Test Cell', commands[ex.CLOSURE_STAGE])
        self.assertEqual(commands[ex.CLOSURE_STAGE][commands[ex.CLOSURE_STAGE].index('--groups') + 1], 'voice')
        for stage in ('npc-gallery', 'media'):
            self.assertEqual(commands[stage][-2:], ['--reference-closure', str(Path('/r') / ex.CLOSURE_FILE)])
        with self.assertRaises(ValueError):
            ex.apply([('image', ['py'])], ['unreferenced'])

    def test_cache_key_follows_the_closure(self):
        import build_cache
        from build_parallel import stage_dependencies
        base = default_plan()
        run = Path('/private/run')
        one = ex.apply(base, ['unreferenced'], run=run, area_cells=['interior:Test Cell'], data_files=Path('/d'),
                       closure_groups=['voice'])
        two = ex.apply(base, ['unreferenced'], run=run, area_cells=['interior:Far Cell'], data_files=Path('/d'),
                       closure_groups=['voice'])
        self.assertIn(ex.CLOSURE_STAGE, stage_dependencies(one)['media'])
        self.assertNotIn(ex.CLOSURE_STAGE, stage_dependencies(base)['media'])
        metadata = {'tools': {}, 'excluded_content': ex.record(['unreferenced'])}
        index = build_cache.SourceIndex()
        first, parts, _, _ = build_cache.fingerprint_steps(one, run, metadata, index)
        second, _, _, _ = build_cache.fingerprint_steps(two, run, metadata, index)
        for stage in (ex.CLOSURE_STAGE, 'media', 'npc-gallery'):
            self.assertNotEqual(first[stage], second[stage], stage)
        self.assertIn(ex.CLOSURE_STAGE, parts['media']['dependencies'])


class Cli(unittest.TestCase):
    def test_command_line_writes_the_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'Data Files'
            data.mkdir()
            (data / 'Morrowind.esm').write_bytes(master_bytes())
            (data / 'Morrowind.bsa').write_bytes(b'')
            out = Path(tmp) / 'closure.json'
            with patch('sys.stdout'):
                self.assertEqual(cc.main(['--data-files', str(data), '--out', str(out), '--cell',
                                          'interior:Test Cell', '--groups', 'voice,npcs']), 0)
            record = json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(record['format'], cc.FORMAT)
            self.assertEqual(record['groups'], ['npcs', 'voice'])
            self.assertEqual(record['counts']['npcs'], 3)
            self.assertTrue(out.read_bytes().endswith(b'\n') and b'\r' not in out.read_bytes())


if __name__ == '__main__':
    unittest.main()
