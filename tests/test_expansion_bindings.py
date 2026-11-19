# SPDX-License-Identifier: GPL-3.0-only
"""The scripts of the expansions' own placements are attached (EXPANSION-SCRIPTS-NOT-ATTACHED-66, v0.0.67).

Until v0.0.67 the script stage (tools/prepare_mwscript.py) wrote the bindings without the add-on masters, so no
person, creature or object that Tribunal or Bloodmoon places ran its script, also in the expansion rooms the image
holds (0 of the v0.0.66 release build's 9,095 bindings). The stage now binds the own placements of the build's
selected expansions. The control: with the base game alone the bindings, the whole file and the unit key are exactly
what they were. Synthetic three-master folder only, no game data."""
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):          # src first: tools/mwad.py is a command, src/mwad the package
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

from mwad.masters import MASTERS_ENV  # noqa: E402
import prepare_mwscript  # noqa: E402
from mwscript import awms  # noqa: E402
from mwscript.compiler import bindings, compile_program, BIND_INTERIOR  # noqa: E402
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


def refs(numbered):
    out = []
    for number, ident, pos in numbered:
        out += [sub('FRMR', struct.pack('<I', number)), sub('NAME', ident),
                sub('DATA', struct.pack('<6f', pos[0], pos[1], pos[2], 0, 0, 0))]
    return out


def exterior(x, y, numbered):
    return record('CELL', sub('NAME', ''), sub('DATA', struct.pack('<Iii', 0, x, y)), *refs(numbered))


def interior(name, numbered):
    return record('CELL', sub('NAME', name), sub('DATA', struct.pack('<Iii', 1, 0, 0)), *refs(numbered))


def lamp(ident, script):
    return record('LIGH', sub('NAME', ident), sub('SCRI', script))


def header(*masters):
    return record('TES3', sub('HEDR', b'\0' * 300), *[s for m in masters for s in (sub('MAST', m), sub('DATA', b'\0' * 8))])


TEXT = 'begin %s\nDisable\nend'      # Disable: an effect, so the script is not inert and its placements are bound


def write_masters(folder):
    """Morrowind.esm (placement 301 of its own lamp), Tribunal.esm (its own lamp placed as 77 in a room of its own)
    and Bloodmoon.esm (its own lamp placed as 12 outdoors), each lamp with a script."""
    (folder / 'Morrowind.esm').write_bytes(b''.join([
        header(), scpt('MwLamp', TEXT % 'MwLamp'), lamp('mw_lamp', 'MwLamp'), exterior(1, 2, [(301, 'mw_lamp', (0, 0, 0))])]))
    (folder / 'Tribunal.esm').write_bytes(b''.join([
        header('Morrowind.esm'), scpt('TrLamp', TEXT % 'TrLamp'), lamp('tr_lamp', 'TrLamp'),
        interior('Mournhold, Test Room', [(77, 'tr_lamp', (8, 16, 24))])]))
    (folder / 'Bloodmoon.esm').write_bytes(b''.join([
        header('Morrowind.esm'), scpt('BmLamp', TEXT % 'BmLamp'), lamp('bm_lamp', 'BmLamp'),
        exterior(-22, 16, [(12, 'bm_lamp', (4, 4, 4))])]))


def bind_rows(raw):
    f = awms.read(raw)
    return [struct.unpack_from('>IHH', f['BIND'], 24 * i) for i in range(f['BIND_rows'])]


class ExpansionBindingTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='aw-expbind-'))
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

    def test_bound_addons_follow_the_selection(self):
        self.assertEqual(prepare_mwscript.bound_addons('Morrowind.esm'), ())
        self.assertEqual(prepare_mwscript.bound_addons('Morrowind.esm,Tribunal.esm'), ('Tribunal.esm',))
        self.assertEqual(prepare_mwscript.bound_addons('Morrowind.esm,Tribunal.esm,Bloodmoon.esm'),
                         ('Tribunal.esm', 'Bloodmoon.esm'))
        with mock.patch.dict(os.environ, {MASTERS_ENV: 'Morrowind.esm,Bloodmoon.esm'}):
            self.assertEqual(prepare_mwscript.bound_addons(), ('Bloodmoon.esm',))
        env = {k: v for k, v in os.environ.items() if k != MASTERS_ENV}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(prepare_mwscript.bound_addons(), ())     # no selection: the base game alone

    def test_base_game_alone_binds_writes_and_keys_as_before(self):
        # the control: with the base game alone the stage binds exactly the rows bindings() gave before the change
        # (Morrowind.esm's own placements), the report has no expansion block and the unit key has no new field
        raw, report = self.build((), 'base')
        program, compiled = compile_program(GameData().load(self.dir), None, handwritten=(), rooms={})
        before = [(r['reference'], r['script'], r['flags']) for r in bindings(program, compiled)]
        self.assertEqual(bind_rows(raw), before)
        self.assertEqual([r[0] for r in bind_rows(raw)], [301])
        self.assertNotIn('bound_addons', report)
        keys = prepare_mwscript.unit_inputs(self.dir, self.media, None, prepare_mwscript.CONFIG, rooms={}, addons=())
        self.assertNotIn('bound_addons', keys)
        # the default selection (nothing set) is the base game alone, byte for byte
        env = {k: v for k, v in os.environ.items() if k != MASTERS_ENV}
        with mock.patch.dict(os.environ, env, clear=True):
            again, _ = self.build(None, 'base-default')
        self.assertEqual(again, raw)

    def test_selected_expansions_own_placements_are_bound(self):
        raw, report = self.build(('Tribunal.esm', 'Bloodmoon.esm'), 'both')
        rows = bind_rows(raw)
        # sorted by reference: the base game's, then Tribunal's (master place 1), then Bloodmoon's (place 2)
        self.assertEqual([r[0] for r in rows], [301, 77 + ADDON_KEY_STRIDE, 12 + 2 * ADDON_KEY_STRIDE])
        flags = {r[0]: r[2] for r in rows}
        self.assertTrue(flags[77 + ADDON_KEY_STRIDE] & BIND_INTERIOR)     # Tribunal's room
        self.assertFalse(flags[12 + 2 * ADDON_KEY_STRIDE] & BIND_INTERIOR)  # Solstheim outdoors
        self.assertEqual(report['bound_addons'], {'masters': ['Tribunal.esm', 'Bloodmoon.esm'],
                                                  'rows': {'Tribunal.esm': 1, 'Bloodmoon.esm': 1},
                                                  'held': {'Tribunal.esm': 0, 'Bloodmoon.esm': 0}})
        # one expansion selected: only its own placements
        raw_t, report_t = self.build(('Tribunal.esm',), 'tribunal')
        self.assertEqual([r[0] for r in bind_rows(raw_t)], [301, 77 + ADDON_KEY_STRIDE])
        self.assertEqual(report_t['bound_addons']['rows'], {'Tribunal.esm': 1})
        # the unit key follows the selection, so a base-only build never reuses a unit with the expansions' rows
        base = prepare_mwscript.unit_inputs(self.dir, self.media, None, prepare_mwscript.CONFIG, rooms={}, addons=())
        both = prepare_mwscript.unit_inputs(self.dir, self.media, None, prepare_mwscript.CONFIG, rooms={},
                                            addons=('Tribunal.esm', 'Bloodmoon.esm'))
        self.assertEqual(both.pop('bound_addons'), ['Tribunal.esm', 'Bloodmoon.esm'])
        self.assertEqual(both, base)


if __name__ == '__main__':
    unittest.main()
