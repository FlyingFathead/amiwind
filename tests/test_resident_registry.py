# SPDX-License-Identifier: GPL-3.0-only
"""Ratchet on the engine's resident registries (ENGINE-RESIDENT-REGISTRY-GROWTH-36).

Every console command, console variable and large static name table stays in memory for the whole session.
tools/resident_registry.py counts them in the compiled engine sources with their bytes; this test fails when
any number rises above tests/resident_registry_budget.json, naming the new entries, and asks for the budget to
be lowered when the engine needs less (a ratchet: down freely, up only with a dated, owner-approved reason).
"""
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import resident_registry as registry  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'


def engine(base, files):
    """A synthetic engine tree: a Makefile listing FILES ({name: C text}) and the files."""
    (base / 'src').mkdir(parents=True)
    (base / 'Makefile').write_text('SRCS = \\\n\t' + ' \\\n\t'.join(files) + '\n', encoding='utf-8')
    for name, text in files.items():
        (base / 'src' / name).write_text(text, encoding='utf-8')
    return base


class Sizes(unittest.TestCase):
    def test_sizes_follow_the_engine_structures(self):
        # If one of these structures changes, the byte constants in tools/resident_registry.py must follow.
        cmd = (SRC / 'cmd.c').read_text(encoding='latin-1')
        self.assertRegex(cmd, r'typedef struct cmd_function_s\s*\{\s*struct cmd_function_s\s*\*next;\s*char\s*'
                              r'\*name;\s*xcommand_t\s*function;\s*\}\s*cmd_function_t;')
        self.assertIn('Hunk_Alloc (sizeof(cmd_function_t))', cmd)
        cvar = (SRC / 'cvar.h').read_text(encoding='latin-1')
        fields = re.search(r'typedef struct cvar_s\s*\{(.*?)\}\s*cvar_t;', cvar, re.S).group(1)
        self.assertEqual(len([f for f in fields.split(';') if f.strip()]), 6)
        self.assertIn('Z_Malloc (Q_strlen(variable->string)+1)', (SRC / 'cvar.c').read_text(encoding='latin-1'))
        zone = (SRC / 'zone.c').read_text(encoding='latin-1')
        self.assertRegex(zone, r'int\s+sentinal;\s*int\s+size;[^\n]*\n\s*char\s+name\[8\];\s*\}\s*hunk_t;')
        self.assertIn('size = sizeof(hunk_t) + ((size+15)&~15);', zone)
        self.assertRegex(zone, r'int\s+size;[^\n]*\n\s*int\s+tag;[^\n]*\n\s*int\s+id;[^\n]*\n\s*struct memblock_s\s*'
                               r'\*next, \*prev;\s*int\s+pad;[^\n]*\n\}\s*memblock_t;')
        self.assertIn('size += 4;', zone)
        self.assertIn('size = (size + 7) & ~7;', zone)
        self.assertEqual(registry.command_bytes(), 32)
        self.assertEqual((registry.zone_bytes(''), registry.zone_bytes('1'), registry.zone_bytes('128 4 4')),
                         (32, 32, 40))


class Scan(unittest.TestCase):
    def test_scan_counts_registrations_and_skips_comments_and_disabled_code(self):
        with tempfile.TemporaryDirectory() as temp:
            base = engine(Path(temp), {
                'a.c': '#include "a.inc"\n#define TINT "128 4 4"\n'
                       'static cvar_t one={"aw_one","1"},tint={"aw_tint",TINT};\n'
                       'void A(void){Cmd_AddCommand("aw_a",f);Cmd_AddCommand ("aw_a",f);'
                       '/* Cmd_AddCommand("aw_c",f); */\n#if 0\nCmd_AddCommand("aw_d",f);\n#endif\n'
                       'Cvar_RegisterVariable(&one);Cvar_RegisterVariable(&tint);Cvar_RegisterVariable(&two);}\n'
                       'static const char *names[]={"' + 'x' * 1100 + '"};\n',
                'b.c': 'void B(void){extern cvar_t three;Cvar_RegisterVariable (&three);}\n'})
            (base / 'src' / 'a.inc').write_text('cvar_t two = {"aw_two","22",true};\n', encoding='utf-8')
            (base / 'src' / 'c.c').write_text('cvar_t three = {"aw_three","333"};\n', encoding='utf-8')
            makefile = base / 'Makefile'
            makefile.write_text(makefile.read_text() + 'MORE_SRCS = c.c\nSRCS += $(MORE_SRCS)\n')
            found = registry.scan(base)
            self.assertEqual(found['problems'], [])
            self.assertEqual([r['name'] for r in found['commands']], ['aw_a'])
            self.assertEqual({r['name']: r['default'] for r in found['cvars']},
                             {'aw_one': '1', 'aw_tint': '128 4 4', 'aw_two': '22', 'aw_three': '333'})
            self.assertEqual([(t['name'], t['bytes']) for t in found['tables']], [('names', 1101)])
            self.assertEqual(registry.totals(found)['cvars'], {'count': 4, 'static_bytes': 96,
                                                               'zone_bytes': 32 + 40 + 32 + 32})

    def test_a_registration_that_cannot_be_read_is_a_problem(self):
        with tempfile.TemporaryDirectory() as temp:
            base = engine(Path(temp), {'a.c': 'void A(void){Cmd_AddCommand(name,f);Cvar_RegisterVariable(&x);}\n'})
            self.assertEqual(len(registry.scan(base)['problems']), 2)

    def test_growth_is_refused_with_the_new_names_and_lowering_needs_no_reason(self):
        with tempfile.TemporaryDirectory() as temp:
            base = engine(Path(temp), {'a.c': 'void A(void){Cmd_AddCommand("aw_a",f);}\n'})
            budget = registry.budget_document(registry.scan(base), ['2026-10-10: first'])
            (base / 'src' / 'a.c').write_text('void A(void){Cmd_AddCommand("aw_a",f);Cmd_AddCommand("aw_b",f);}\n')
            grown = registry.scan(base)
            messages = registry.over_budget(grown, budget)
            self.assertEqual(messages, ['commands count: 2 > budget 1; new: aw_b',
                                        'commands hunk_bytes: 64 > budget 32; new: aw_b'])
            with self.assertRaises(ValueError):
                registry.update_budget(grown, budget)
            raised = registry.update_budget(grown, budget, '2026-10-11: owner OK for aw_b')
            self.assertEqual((raised['totals']['commands']['count'], raised['reasons'][-1]),
                             (2, '2026-10-11: owner OK for aw_b'))
            (base / 'src' / 'a.c').write_text('void A(void){}\n')
            lowered = registry.update_budget(registry.scan(base), raised)
            self.assertEqual(lowered['totals']['commands'], {'count': 0, 'hunk_bytes': 0})


class Budget(unittest.TestCase):
    def test_the_engine_fits_its_resident_registry_budget(self):
        found = registry.scan()
        self.assertEqual(found['problems'], [], 'tools/resident_registry.py cannot read these registrations')
        budget = registry.load_budget()
        messages = registry.over_budget(found, budget)
        self.assertEqual(messages, [], 'resident registries grew above tests/resident_registry_budget.json: '
                         + '; '.join(messages) + '. ' + registry.ADVICE)
        self.assertEqual(registry.totals(found), budget['totals'],
                         'the engine needs less than its budget: ratchet it down with '
                         'python tools/resident_registry.py --lower-budget')
        for reason in budget['reasons']:
            self.assertRegex(reason, r'^\d{4}-\d{2}-\d{2}: ', 'every budget reason starts with its date')

    def test_budget_file_is_lf_json(self):
        raw = registry.BUDGET.read_bytes()
        self.assertNotIn(b'\r', raw)
        self.assertEqual(json.loads(raw)['format'], 'AmiWind resident registry budget 1')


if __name__ == '__main__':
    unittest.main()
