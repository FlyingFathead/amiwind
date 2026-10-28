# SPDX-License-Identifier: GPL-3.0-only
"""NPC Gallery v2.0 (NPC-GALLERY-V2): the catalogue of the actors an image already holds, nothing baked.

Synthetic maps and a synthetic master only (no game data)."""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))

import gallery_v2  # noqa: E402


def bsp(entities):
    """A BSP29 header whose lump 0 is ENTITIES (the only lump the catalogue reads)."""
    text = ''.join('{\n' + ''.join('"%s" "%s"\n' % kv for kv in row.items()) + '}\n' for row in entities).encode()
    header = struct.pack('<i', 29) + struct.pack('<ii', 4 + 15 * 8, len(text)) + bytes(14 * 8)
    return header + text


def sub(tag, data):
    return tag.encode() + struct.pack('<I', len(data)) + data


def record(tag, *subs, flags=0):
    payload = b''.join(subs)
    return tag.encode() + struct.pack('<III', len(payload), 0, flags) + payload


def z(text):
    return text.encode('cp1252') + b'\0'


def master():
    cell_data = struct.pack('<Iii', 1, 0, 0)
    return b''.join([
        record('RACE', sub('NAME', z('Wood Elf')), sub('FNAM', z('Wood Elf'))),
        record('CLAS', sub('NAME', z('Commoner')), sub('FNAM', z('Commoner'))),
        record('NPC_', sub('NAME', z('fargoth')), sub('FNAM', z('Fargoth')), sub('RNAM', z('Wood Elf')),
               sub('CNAM', z('Commoner'))),
        record('NPC_', sub('NAME', z('unplaced')), sub('FNAM', z('Nobody'))),
        record('CREA', sub('NAME', z('mudcrab')), sub('FNAM', z('Mudcrab'))),
        record('CELL', sub('NAME', z('Seyda Neen, Arrille\'s Tradehouse')), sub('DATA', cell_data),
               sub('FRMR', struct.pack('<I', 7)), sub('NAME', z('fargoth'))),
    ])


FARGOTH = {'classname': 'aw_npc', 'aw_ref': '7', 'model': 'progs/a_fargoth.mdl', 'origin': '1 2 3',
           'angles': '0 90 0', 'netname': 'Fargoth', 'aw_source_id': 'fargoth', 'aw_voice': 'npc/a.wav',
           'aw_line': 'Hello\tthere friend','aw_ground_baked': '1 2 3', 'aw_ground_valid': '1'}


class GalleryV2(unittest.TestCase):
    def image(self, temp):
        id1 = Path(temp) / 'id1'
        (id1 / 'maps').mkdir(parents=True)
        (id1 / 'progs').mkdir()
        for name in ('a_fargoth.mdl', 'c_mudcrab.mdl'):
            (id1 / 'progs' / name).write_bytes(b'IDPO')
        intro = dict(FARGOTH, aw_intro_role='1', aw_source_id='intro guard', model='progs/a_fargoth.mdl')
        (id1 / 'maps/a_room.bsp').write_bytes(bsp([{'classname': 'worldspawn'}, FARGOTH, intro]))
        (id1 / 'maps/b_frame.chim').write_bytes(bsp([
            dict(FARGOTH, model='progs/other.mdl'),              # the same record again: the first row wins
            {'classname': 'aw_npc', 'model': 'progs/c_mudcrab.mdl', 'netname': 'Mudcrab', 'aw_source_id': 'mudcrab',
             'origin': '0 0 0'},
            {'classname': 'aw_npc', 'model': 'progs/gone.mdl', 'netname': 'Gone', 'aw_source_id': 'gone',
             'origin': '0 0 0'},
            {'classname': 'light', 'origin': '0 0 0'}]))
        (Path(temp) / 'Morrowind.esm').write_bytes(master())
        return id1, Path(temp) / 'Morrowind.esm'

    def test_catalogue_lists_the_actors_the_image_holds_and_bakes_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            id1, esm = self.image(temp)
            before = sorted(p.relative_to(id1) for p in id1.rglob('*'))
            report, not_built = gallery_v2.write_catalogue(id1, esm)
            after = sorted(p.relative_to(id1) for p in id1.rglob('*'))
            # one file more, the catalogue: no model, footprint or baked copy
            self.assertEqual(set(after) - set(before), {Path('gallery'), Path('gallery/actors.txt')})
            lines = (id1 / 'gallery/actors.txt').read_text(encoding='cp1252').splitlines()
            self.assertEqual(lines[0], 'AWG2 2')
            rows = [line.split('\t') for line in lines[1:]]
            self.assertEqual([r[3] for r in rows], ['Fargoth', 'Mudcrab'])      # browse order: by name
            fargoth = rows[0]
            self.assertEqual(fargoth[:8], ['2', 'NPC_', 'fargoth', 'Fargoth', 'Wood Elf', 'Commoner',
                                           "Seyda Neen, Arrille's Tradehouse", 'progs/a_fargoth.mdl'])
            self.assertEqual(rows[1][:2], ['1', 'CREA'])                         # numbers: kind, then id
            text = fargoth[8]
            for gone in ('origin', 'angles', 'aw_ref', 'aw_ground_baked', 'aw_ground_valid'):
                self.assertNotIn('"%s"' % gone, text)
            self.assertIn('"aw_line" "Hello there friend"', text)              # no tab inside a value
            self.assertNotIn('{', text)
            self.assertEqual(report['baked_models'], 0)
            self.assertEqual((report['rows'], report['npcs'], report['creatures']), (2, 1, 1))
            self.assertEqual(report['model_missing'], {'gone': 'progs/gone.mdl'})
            self.assertEqual(report['not_built_by_this_image'], {'NPC_': 1, 'CREA': 0})
            self.assertEqual(not_built['NPC_'], ['unplaced'])
            self.assertNotIn('intro guard', (id1 / 'gallery/actors.txt').read_text(encoding='cp1252'))

    def test_a_long_greeting_is_dropped_before_the_row_is_refused(self):
        row = dict(FARGOTH, aw_greeting='x' * 1500)
        text, dropped = gallery_v2.entity_text(row)
        self.assertEqual(dropped, ['aw_greeting'])
        self.assertLessEqual(len(text), gallery_v2.TEXT_LIMIT)
        with self.assertRaises(ValueError):
            gallery_v2.entity_text(dict(FARGOTH, aw_other='y' * 1500))

    def test_method_and_image_option(self):
        run = Path('/run')
        default = SimpleNamespace(no_npc_gallery=False, npc_gallery_method=None, miniwind=False)
        self.assertEqual(gallery_v2.method(default), 'v2')
        self.assertEqual(gallery_v2.image_option(default, run), ['--gallery-v2'])
        baked = SimpleNamespace(no_npc_gallery=False, npc_gallery_method='baked', miniwind=False)
        self.assertEqual(gallery_v2.image_option(baked, run), ['--gallery', run / 'npc-gallery'])
        off = SimpleNamespace(no_npc_gallery=True, npc_gallery_method=None, miniwind=False)
        self.assertEqual(gallery_v2.image_option(off, run), ['--no-npc-gallery'])
        # a MiniWind leaves the gallery out unless the method is named
        mini = SimpleNamespace(no_npc_gallery=False, npc_gallery_method=None, miniwind=True)
        self.assertEqual(gallery_v2.image_option(mini, run), ['--no-npc-gallery'])
        mini.npc_gallery_method = 'v2'
        self.assertEqual(gallery_v2.image_option(mini, run), ['--gallery-v2'])

    def test_engine_and_builder_agree_on_the_limits(self):
        engine = (ROOT / 'engine/aga/src/aw_gallery.c').read_text(encoding='utf-8')
        self.assertIn('#define GALLERY_ROW %d' % (gallery_v2.ROW_LIMIT + 1), engine)
        self.assertIn('#define GALLERY_TEXT %d' % gallery_v2.TEXT_LIMIT, engine)
        self.assertIn('COM_FOpenFile("%s"' % gallery_v2.CATALOGUE, engine)
        self.assertIn('"%s %%d %%c"' % gallery_v2.FORMAT, engine)


if __name__ == '__main__':
    unittest.main()
