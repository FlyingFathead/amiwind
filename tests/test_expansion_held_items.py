# SPDX-License-Identifier: GPL-3.0-only
"""The scripted items the expansions' own holders carry are bound (EXPANSION-HELD-ITEMS-66, v0.0.67).

The items a placed container, NPC or creature holds run their scripts while the holder's area is loaded (BIND_HELD,
MWSCRIPT-INVENTORY-HITONME-62); until v0.0.67 only Morrowind.esm's holders were read (gamedata holder_refs), so a
holder an expansion places (Barilzar's lich with the Mazed Band, the Mournhold guards' armour) carried its items
without their scripts. The script stage now binds them for the selected expansions, as it binds their placements
(EXPANSION-SCRIPTS-NOT-ATTACHED-66); with the base game alone the bindings are what they were. Synthetic masters only."""
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):          # src first: tools/mwad.py is a command, src/mwad the package
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

import prepare_mwscript  # noqa: E402
from mwscript import awms  # noqa: E402
from mwscript.compiler import bindings, compile_program, held_key, BIND_HELD, BIND_INTERIOR, BIND_EDICT  # noqa: E402
from mwscript.gamedata import GameData, ADDON_KEY_STRIDE  # noqa: E402


def sub(tag, data):
    if isinstance(data, str):
        data = data.encode('cp1252') + b'\0'
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def record(tag, *subs):
    payload = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(payload), 0, 0) + payload


def scpt(name, text):
    head = name.encode('cp1252').ljust(32, b'\0') + struct.pack('<5I', 0, 0, 0, 0, 0)
    return record('SCPT', sub('SCHD', head), sub('SCTX', text.encode('cp1252')))


def header(*masters):
    return record('TES3', sub('HEDR', b'\0' * 300), *[s for m in masters for s in (sub('MAST', m), sub('DATA', b'\0' * 8))])


def item(ident, script):
    return record('MISC', sub('NAME', ident), sub('SCRI', script))


def chest(ident, *items):
    return record('CONT', sub('NAME', ident), *[sub('NPCO', struct.pack('<i', 1) + i.encode('cp1252').ljust(32, b'\0'))
                                                for i in items])


def room(name, numbered):
    parts = [sub('NAME', name), sub('DATA', struct.pack('<Iii', 1, 0, 0))]
    for number, ident in numbered:
        parts += [sub('FRMR', struct.pack('<I', number)), sub('NAME', ident),
                  sub('DATA', struct.pack('<6f', 1, 2, 3, 0, 0, 0))]
    return record('CELL', *parts)


TEXT = 'begin %s\nDisable\nend'      # an effect: not inert, so its holders' rows are written


def write_masters(folder):
    """Morrowind.esm: a chest (301) holding its scripted key; Tribunal.esm: its own chest (77, in a room of its own)
    holding its own scripted key, and the base chest's record changed to hold Tribunal's key too (an override)."""
    (folder / 'Morrowind.esm').write_bytes(b''.join([
        header(), scpt('MwKey', TEXT % 'MwKey'), item('mw_key', 'MwKey'), chest('mw_chest', 'mw_key'),
        room('Test Room', [(301, 'mw_chest')])]))
    (folder / 'Tribunal.esm').write_bytes(b''.join([
        header('Morrowind.esm'), scpt('TrKey', TEXT % 'TrKey'), item('tr_key', 'TrKey'), chest('tr_chest', 'tr_key'),
        chest('mw_chest', 'mw_key', 'tr_key'), room('Mournhold, Test Vault', [(77, 'tr_chest')])]))


def bind_rows(raw):
    f = awms.read(raw)
    return [struct.unpack_from('>IHH', f['BIND'], 24 * i) for i in range(f['BIND_rows'])]


class ExpansionHeldItemTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='aw-expheld-'))
        write_masters(self.dir)
        self.media = self.dir / 'media'
        self.media.mkdir()
        (self.media / 'media-coverage.json').write_text(json.dumps({'format': 'AWMEDIA1', 'excluded': [], 'entries': []}))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def build(self, addons, name):
        out = self.dir / name
        report = prepare_mwscript.build(self.dir, self.media, None, out, addons=addons)
        return (out / 'id1' / prepare_mwscript.NAME).read_bytes(), report

    def test_the_holder_refs_of_each_master(self):
        data = GameData().load(self.dir)
        self.assertEqual([r['reference'] for r in data.holder_refs], [301])
        self.assertEqual([(r['reference'], r['id'], r['master']) for r in data.addon_holder_refs],
                         [(77 + ADDON_KEY_STRIDE, 'tr_chest', 'Tribunal.esm')])
        # the base chest holds what the last master's record gives it (Tribunal's override)
        self.assertEqual(data.holdings['mw_chest'], ['mw_key', 'tr_key'])

    def test_base_game_alone_binds_as_before(self):
        raw, report = self.build((), 'base')
        program, compiled = compile_program(GameData().load(self.dir), None, handwritten=(), rooms={})
        self.assertEqual(bind_rows(raw), [(r['reference'], r['script'], r['flags']) for r in bindings(program, compiled)])
        held = [r[0] for r in bind_rows(raw) if r[2] & BIND_HELD]
        self.assertEqual(held, [held_key(301, 0), held_key(301, 1)])     # the base chest's two keys only
        self.assertNotIn('bound_addons', report)

    def test_a_tribunal_holders_items_are_bound(self):
        raw, report = self.build(('Tribunal.esm',), 'tribunal')
        rows = {r[0]: r for r in bind_rows(raw)}
        key = held_key(77 + ADDON_KEY_STRIDE, 0)
        self.assertIn(key, rows)
        self.assertEqual(rows[key][2], BIND_HELD | BIND_INTERIOR | BIND_EDICT)
        self.assertEqual(report['bound_addons']['rows'], {'Tribunal.esm': 1})
        self.assertEqual(report['bound_addons']['held'], {'Tribunal.esm': 1})
        # the base chest's rows are the same with or without the expansion selected
        base, _ = self.build((), 'base')
        self.assertEqual([r for r in bind_rows(raw) if r[0] != key], bind_rows(base))


if __name__ == '__main__':
    unittest.main()
