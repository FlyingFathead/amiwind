# SPDX-License-Identifier: GPL-3.0-only
"""Item coverage (tools/item_coverage.py, docs/NPC_DEFAULTS.md): every item record of the masters checked against the
shared item table, the inventory catalogue, the image's models and icons, the held models and the placed references,
on a small synthetic data set (no game data in the repo)."""
import hashlib
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import item_coverage  # noqa: E402


def sub(tag, data):
    if isinstance(data, str):
        data = data.encode('cp1252') + b'\0'
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def record(tag, *subs, flags=0):
    payload = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(payload), 0, flags) + payload


def wpdt(kind):
    return sub('WPDT', struct.pack('<fihhffh6Bi', 10.0, 50, kind, 300, 1.0, 1.0, 0, 1, 5, 1, 5, 1, 5, 0))


def lhdt(flags):
    return sub('LHDT', struct.pack('<fiii4BI', 1.0, 5, 100, 128, 255, 200, 100, 0, flags))


def master():
    out = []
    for i in range(27):
        out.append(record('SKIL', sub('INDX', struct.pack('<i', i)), sub('SKDT', struct.pack('<ii4f', i % 8, i % 3, 1, 1, 1, 1))))
    out.append(record('MISC', sub('NAME', 'Gold_001'), sub('MODL', 'm/gold.nif')))
    out.append(record('WEAP', sub('NAME', 'cov_sword'), sub('MODL', 'w/sword.nif'), sub('ITEX', 'w/sword.tga'), wpdt(1)))
    out.append(record('WEAP', sub('NAME', 'cov_bow'), sub('MODL', 'w/bow.nif'), wpdt(9)))
    out.append(record('ARMO', sub('NAME', 'cov_shield'), sub('MODL', 'a/shield.nif'),
                      sub('AODT', struct.pack('<ifiiii', 8, 9.0, 20, 200, 0, 10))))
    out.append(record('ARMO', sub('NAME', 'cov_helm'), sub('MODL', 'a/helm.nif'),
                      sub('AODT', struct.pack('<ifiiii', 0, 3.0, 20, 200, 0, 10))))
    out.append(record('MISC', sub('NAME', 'cov_cup'), sub('MODL', 'm/cup.nif')))
    out.append(record('LIGH', sub('NAME', 'cov_torch'), sub('MODL', 'l/torch.nif'), lhdt(0x2)))
    out.append(record('LIGH', sub('NAME', 'cov_lamp_fixed'), sub('MODL', 'l/lamp.nif'), lhdt(0)))
    out.append(record('MISC', sub('NAME', 'cov_deleted'), sub('DELE', struct.pack('<i', 0))))
    npdt = struct.pack('<h8B27BB3HBBbBi', 5, *range(50, 58), *range(10, 37), 0, 50, 20, 100, 40, 1, 2, 0, 30)
    npco = sub('NPCO', struct.pack('<i', 1) + b'cov_sword'.ljust(32, b'\0'))
    out.append(record('NPC_', sub('NAME', 'cov_npc'), sub('NPDT', npdt), sub('FLAG', struct.pack('<I', 0)), npco))
    out.append(record('CELL', sub('NAME', 'Test Room'), sub('DATA', struct.pack('<Iii', 1, 0, 0)),
                      sub('FRMR', struct.pack('<I', 1)), sub('NAME', 'cov_cup'),
                      sub('FRMR', struct.pack('<I', 2)), sub('NAME', 'cov_sword')))
    return b''.join(out)


def addon():
    # a later master's record replaces the earlier one and may delete one
    return b''.join([record('MISC', sub('NAME', 'cov_cup'), sub('MODL', 'm/cup2.nif')),
                     record('WEAP', sub('NAME', 'cov_bow'), sub('DELE', struct.pack('<i', 0)), flags=0x20)])


def catalogue_row(ident, model, icon, flags):
    row = ident.encode().ljust(64, b'\0') + ident.encode().ljust(96, b'\0')
    row += struct.pack('<iiifII', 7, 0, 1, 1.0, 0, flags)
    row += model.encode().ljust(64, b'\0') + icon.encode().ljust(64, b'\0')
    return row.ljust(item_coverage.CATALOGUE_ROW, b'\0')


class ItemCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-itemcov-'))
        data = cls.tmp / 'data'
        data.mkdir()
        (data / 'Morrowind.esm').write_bytes(master())
        (data / 'Tribunal.esm').write_bytes(addon())
        id1 = cls.tmp / 'id1'
        for d in ('inventory', 'progs/inv', 'gfx/inv', 'items'):
            (id1 / d).mkdir(parents=True)
        (id1 / 'progs/inv/icup.mdl').write_bytes(b'IDPO')
        (id1 / 'gfx/inv/icup.awi').write_bytes(b'AWIC')
        rows = [catalogue_row('cov_cup', 'progs/inv/icup.mdl', 'gfx/inv/icup.awi', 2),
                catalogue_row('cov_sword', 'progs/inv/missing.mdl', '', 1)]
        (id1 / 'inventory/items.awi').write_bytes(b'AWI2' + struct.pack('<I', len(rows)) + b''.join(rows))
        (id1 / 'gfx/icons.awl').write_bytes(b'AWL1\0item:cov_sword\0')
        stem = 'w' + hashlib.sha256('w/sword.nif'.encode()).hexdigest()[:12]
        (id1 / 'items' / (stem + '.mdl')).write_bytes(b'IDPO')
        cls.items, cls.placed = item_coverage.read_masters(data)
        cls.table, cls.carried, cls.source = item_coverage.actor_items(data, id1)
        cls.result = item_coverage.coverage(cls.items, cls.placed, cls.table, cls.carried,
                                            (id1, item_coverage.read_image(id1)))
        cls.data, cls.id1 = data, id1

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def by(self, tag, column):
        return self.result['by_type'][tag][column]

    def test_masters_last_wins_and_deleted(self):
        self.assertNotIn('cov_bow', self.items['WEAP'])          # deleted by the add-on
        self.assertNotIn('cov_deleted', self.items['MISC'])
        self.assertEqual(self.items['MISC']['cov_cup']['model'], 'm/cup2.nif')
        self.assertEqual(self.placed, {'cov_cup': 1, 'cov_sword': 1})

    def test_counts(self):
        self.assertEqual(self.by('WEAP', 'records'), 1)
        self.assertEqual(self.by('WEAP', 'carried'), 1)
        self.assertEqual(self.by('WEAP', 'actor_table'), 1)
        self.assertEqual(self.by('WEAP', 'held_model'), 1)
        self.assertEqual(self.by('WEAP', 'icon'), 1)            # from the icon table
        self.assertEqual(self.by('WEAP', 'ground_model'), 0)    # the named model is not in the image
        self.assertEqual(self.by('WEAP', 'takeable'), 0)        # placed, but not pickable
        self.assertEqual(self.by('ARMO', 'held_model'), 0)      # the shield has no held model
        self.assertEqual(self.result['held_applies']['ARMO'], 1)
        self.assertEqual(self.by('MISC', 'records'), 2)         # the cup and the gold
        self.assertEqual(self.by('MISC', 'takeable'), 1)
        self.assertEqual(self.by('MISC', 'ground_model'), 1)
        self.assertEqual(self.by('MISC', 'icon'), 1)
        self.assertEqual(self.by('LIGH', 'records'), 1)         # the fixed lamp is scenery
        self.assertEqual(self.result['fixed_lights'], 1)
        self.assertEqual(self.result['all']['records'], sum(self.by(t, 'records') for t in item_coverage.TYPES))

    def test_gaps_named(self):
        gaps = self.result['gaps']
        self.assertIn('cov_shield', gaps['ARMO']['held_model'])
        self.assertIn('cov_torch', gaps['LIGH']['catalogue'])
        self.assertIn('cov_sword', gaps['WEAP']['ground_model'])

    def test_cli_json_has_no_ids(self):
        out = self.tmp / 'c.json'
        private = self.tmp / 'p.json'
        self.assertEqual(item_coverage.main(['--data-files', str(self.data), '--id1', str(self.id1),
                                             '--json', str(out), '--private', str(private)]), 0)
        self.assertNotIn('cov_', out.read_text(encoding='utf-8'))
        self.assertIn('cov_shield', private.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
