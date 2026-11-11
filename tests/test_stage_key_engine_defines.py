# SPDX-License-Identifier: GPL-3.0-only
"""Engine files read only for single defines count in the CHIM world keys as the values read (read only, no build).

BUILD-ENGINE-SOURCE-KEY-BROAD-36, seen again 2026-11-09: tools/map_engine_limits.py reads one define of
engine/aga/src/aw_combat.c (SLOTS). Keyed by its C facts, every declaration of the file whose name is also a word in
a string of the reached builder code (slots, you, retry, cost, music, rules) stayed in the key, so combat edits re-keyed
the CHIM world, the three CHIM towns and the world flora. tools/engine_facts.py version 4 keys such a file as the
values its readers return (define_value), and its #include lines leave the key. A gate test also keeps the engine
files these stages key whole to a reviewed list.
"""
import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache  # noqa: E402
import engine_facts  # noqa: E402
import engine_limits  # noqa: E402
import world_estimate  # noqa: E402

COMBAT = 'engine/aga/src/aw_combat.c'
STAGES = ('chim_build.py', 'chim_town.py', 'prepare_world_flora.py')
# Engine files the CHIM world, town and flora stages may key whole (read whole, parsed, hashed or compiled by name by
# the checks they run). A new whole engine file in these keys means any edit of it re-keys the world: narrow it
# (engine_facts) or add it here with the reason it is read whole.
# The list as found on 9 November 2026 (v0.0.63-dev1); each is named as text by the reached builder code.
WHOLE_ALLOWED = frozenset((
    'engine/aga/qc/world.qc', 'engine/aga/src/progdefs.q1', 'engine/aga/src/progdefs.q2',
    'engine/aga/src/aw_town_table.h', 'engine/aga/src/aw_activated.h', 'engine/aga/src/asm_draw.h',
    'engine/aga/src/aw_harvest.c', 'engine/aga/src/aw_harvest.h', 'engine/aga/src/aw_harvest_proxy.c',
    'engine/aga/src/aw_harvest_runtime.c', 'engine/aga/src/bspfile.h', 'engine/aga/src/chim/chim_chunks.c',
    'engine/aga/src/chim/chim_zone.c', 'engine/aga/src/model.h', 'engine/aga/src/model_alias_stream.inc',
    'engine/aga/src/r_draw.c', 'engine/aga/src/sys_amiga.c'))


def facts_value(value):
    return str(value).startswith(tuple(engine_facts.PREFIXES.values())) or str(value).startswith('policy')


class EngineDefineKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)
        cls.keys = {script: cls.index.selection(ROOT / 'tools' / script)[0] for script in STAGES}

    def key_with(self, text):
        """The three stage keys with aw_combat.c read as TEXT (the stage sees an edited file)."""
        real = engine_facts.read_text

        def read(index, path):
            return text if path == COMBAT else real(index, path)
        engine_facts.read_text = read
        try:
            index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)
            return {script: index.selection(ROOT / 'tools' / script)[0] for script in STAGES}
        finally:
            engine_facts.read_text = real

    def test_combat_counts_as_its_slots_value(self):
        for script, key in self.keys.items():
            with self.subTest(script=script):
                self.assertTrue(str(key[COMBAT]).startswith(engine_facts.PREFIX + engine_facts.DEFINES_TAG))
                self.assertNotIn('engine/aga/src/aw_combat.h', key if script != 'chim_build.py' else ())
        rows = engine_facts.define_rows((ROOT / COMBAT).read_text(encoding='utf-8'), {('SLOTS', 'define')})
        self.assertEqual(int(rows[0][2]), engine_limits.define('aw_combat.c', 'SLOTS'))

    def test_a_combat_edit_outside_slots_keeps_the_keys(self):
        text = (ROOT / COMBAT).read_text(encoding='utf-8')
        edited = text.replace('static aw_fighter_t you;', 'static aw_fighter_t you;\nstatic int you_extra;', 1)
        edited += '\nstatic int AW_CombatProbe(void) { return slots[0].count[0] + rules[0]; }\n'
        self.assertNotEqual(edited, text)
        self.assertEqual(self.key_with(edited), self.keys)

    def test_a_slots_change_rekeys_the_stages(self):
        text = (ROOT / COMBAT).read_text(encoding='utf-8')
        value = engine_limits.define('aw_combat.c', 'SLOTS')
        edited = text.replace('#define SLOTS %d' % value, '#define SLOTS %d' % (value + 1), 1)
        self.assertNotEqual(edited, text)
        after = self.key_with(edited)
        for script in STAGES:
            with self.subTest(script=script):
                self.assertNotEqual(after[script][COMBAT], self.keys[script][COMBAT])

    def test_the_patterns_are_the_readers(self):
        readers = {'define': engine_limits.define, '_define': world_estimate._define,
                   '_mib_define': engine_limits._mib_define, 'cvar_default': engine_limits.cvar_default}
        self.assertEqual(set(readers), set(engine_facts.DEFINE_PATTERNS))
        for name, function in readers.items():
            with self.subTest(reader=name):
                pattern = engine_facts.DEFINE_PATTERNS[name][1]
                head, tail = pattern.split('%s')
                source = inspect.getsource(function)
                self.assertIn(repr(head)[1:-1].replace('\\\\', '\\'), source.replace("r'", "'"))
                self.assertIn(repr(tail)[1:-1].replace('\\\\', '\\'), source.replace("r'", "'"))
                self.assertEqual(engine_facts.DEFINE_PATTERNS[name][0] == 'stripped', 're.sub' in source, name)

    def test_whole_engine_files_are_reviewed(self):
        for script, key in self.keys.items():
            whole = sorted(path for path, value in key.items() if path.startswith('engine/') and not facts_value(value))
            with self.subTest(script=script):
                self.assertEqual([path for path in whole if path not in WHOLE_ALLOWED], [], script)


if __name__ == '__main__':
    unittest.main()
