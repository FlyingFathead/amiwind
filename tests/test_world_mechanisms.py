# SPDX-License-Identifier: GPL-3.0-only
"""The census of the world mechanisms (tools/world_mechanisms.py, TRAPS-WHEN-OPENED-63, WORLD-BUTTONS-62) on a
synthetic plugin: the activators whose script acts on another object, and the trapped doors and containers."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

import world_mechanisms as wm  # noqa: E402


def sub(tag, data):
    return tag.encode() + struct.pack('<I', len(data)) + data


def record(tag, data, flags=0):
    return tag.encode() + struct.pack('<III', len(data), 0, flags) + data


def z(text):
    return text.encode() + b'\0'


def script(name, text):
    return record('SCPT', sub('SCHD', name.encode().ljust(32, b'\0') + bytes(20)) + sub('SCTX', text.encode()))


def base(tag, identifier, name='', script_name=''):
    data = sub('NAME', z(identifier)) + sub('MODL', z('x\\a.nif')) + (sub('FNAM', z(name)) if name else b'')
    return record(tag, data + (sub('SCRI', z(script_name)) if script_name else b''))


def ref(number, identifier, *extra):
    data = sub('FRMR', struct.pack('<I', number)) + sub('NAME', z(identifier))
    return data + b''.join(sub(t, v) for t, v in extra)


def cell(name, *refs, grid=None):
    flags, gx, gy = (0, grid[0], grid[1]) if grid else (1, 0, 0)
    return record('CELL', sub('NAME', z(name)) + sub('DATA', struct.pack('<Iii', flags, gx, gy)) + b''.join(refs))


def plugin():
    raw = script('GG_OpenGate1', 'begin GG_OpenGate1\nif ( OnActivate == 1 )\n ; "nothing"->Disable\n'
                 '  "ex_gg_portcullis_01"->MoveWorld z 70\nendif\nend')
    raw += script('Valve', 'begin Valve\nif ( OnActivate == 1 )\n  "steam_01"->Disable\n  "door_01"->Unlock\n'
                  '  PlayGroup Idle2\nendif\nend')
    raw += script('SelfOnly', 'begin SelfOnly\nif ( OnActivate == 1 )\n  PlayGroup Idle2\n  Disable\nendif\nend')
    raw += script('Holder', 'begin Holder\n"guard"->Enable\nend')
    raw += script('Anim', 'begin Anim\nif ( OnActivate == 1 )\n "lever_b"->PlayGroup Idle2\nendif\nend')
    raw += base('ACTI', 'ex_gg_gateswitch_01', 'Switch', 'GG_OpenGate1') + base('ACTI', 'valve_01', 'Valve', 'Valve')
    raw += base('ACTI', 'self_lever', 'Lever', 'SelfOnly') + base('ACTI', 'holder', '', 'Holder')
    raw += base('ACTI', 'anim_lever', 'Lever', 'Anim') + base('ACTI', 'ex_gg_portcullis_01')
    raw += base('DOOR', 'door_01', 'Door') + base('CONT', 'chest', 'Chest')
    raw += cell('Ghostgate', ref(1, 'ex_gg_gateswitch_01'), ref(2, 'ex_gg_portcullis_01'), grid=(2, 4))
    raw += cell('Tomb', ref(3, 'valve_01'), ref(4, 'door_01', ('TNAM', z('trap_fire00'))),
                ref(5, 'chest', ('TNAM', z('trap_fire00'))), ref(6, 'chest', ('TNAM', z('trap_frost00'))),
                ref(7, 'chest', ('TNAM', z('trap_frost00')), ('DELE', struct.pack('<i', 0))),
                ref(8, 'door_01', ('DODT', struct.pack('<6f', 0, 0, 0, 0, 0, 0)), ('TNAM', z('poison'))),
                ref(9, 'self_lever'), ref(10, 'holder'))
    return raw


class WorldMechanisms(unittest.TestCase):
    def report(self, states=None):
        return wm.census([('Morrowind.esm', wm.read_master(plugin(), 'Morrowind.esm'))], states)

    def test_activators_acting_on_another_object(self):
        rows = {r['id']: r for r in self.report({'gg_opengate1': 'runs', 'valve': 'not-yet: Unlock'})['mechanisms']}
        # the activator that only acts on itself and the one that only animates another are not mechanisms
        self.assertEqual(sorted(rows), ['ex_gg_gateswitch_01', 'holder', 'valve_01'])
        gate = rows['ex_gg_gateswitch_01']
        self.assertEqual((gate['script'], gate['player'], gate['cells'], gate['acts'], gate['state'], gate['runs']),
                         ('GG_OpenGate1', True, ['Ghostgate (2, 4)'], ['moves ex_gg_portcullis_01'], 'runs', True))
        self.assertEqual(rows['valve_01']['acts'], ['disables steam_01', 'unlocks door_01'])
        self.assertEqual((rows['valve_01']['cells'], rows['valve_01']['runs']), (['Tomb'], False))
        self.assertEqual((rows['holder']['player'], rows['holder']['state']), (False, 'not in the tracker'))

    def test_traps_by_kind_and_spell(self):
        traps = self.report()['traps']
        self.assertEqual(traps['references'], 4)     # the deleted chest is not counted
        self.assertEqual(traps['by_kind'], {'hinged door': 1, 'container': 2, 'load door': 1})
        self.assertEqual(traps['by_spell'], {'trap_fire00': 2, 'trap_frost00': 1, 'poison': 1})

    def test_page_and_command_line(self):
        report = self.report()
        page = wm.markdown(report, '0.0.64', '10 November 2026')
        self.assertTrue(page.startswith('# World mechanisms\n\n_Last updated with AmiWind v0.0.64 (10 November 2026)._'))
        self.assertIn('| ex_gg_gateswitch_01 | Switch | GG_OpenGate1 | yes | Ghostgate (2, 4) | '
                      'ex_gg_portcullis_01 (moves) | not in the tracker |', page)
        self.assertIn('| Morrowind.esm | 3 | 2 | 0 |', page)
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'data'; data.mkdir()
            (data / 'morrowind.esm').write_bytes(plugin())
            features = Path(tmp) / 'features.json'
            features.write_text(json.dumps({'scripts': [{'id': 'Valve', 'state': 'runs'}]}), encoding='utf-8')
            out, md = Path(tmp) / 'out.json', Path(tmp) / 'out.md'
            self.assertEqual(wm.main(['--data-files', str(data), '--features', str(features), '--json', str(out),
                                      '--markdown', str(md)]), 0)
            got = json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(got['summary'], {'Morrowind.esm': {'activators': 3, 'player_worked': 2, 'runs': 1}})
            self.assertIn('## Traps', md.read_text(encoding='utf-8'))

    def test_the_public_page_is_current_in_form(self):
        page = (ROOT / 'docs/WORLD_MECHANISMS.md').read_text(encoding='utf-8')
        self.assertTrue(page.startswith('# World mechanisms\n\n_Last updated with AmiWind v'))
        for part in ('## Summary', '## Traps', '## Morrowind.esm', 'ex_gg_gateswitch_01'):
            self.assertIn(part, page)


if __name__ == '__main__':
    unittest.main()
