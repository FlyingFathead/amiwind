# SPDX-License-Identifier: GPL-3.0-only
"""The world survey with the expansions on (WORLD-SURVEY-EXPANSIONS-66): it reads the selected masters' archives (a mesh
only an expansion archive holds is measured, not unresolved), it plans the base game's exterior grid and lists the
cells only an expansion adds, and the atlas names every cell it refuses and why. The last test lists the build stages
that still read the merged master with the base archive alone, so a new one fails here before a build."""
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import render_world_survey  # noqa: E402
import survey_vvardenfell as survey  # noqa: E402
from test_layered_archives import write_bsa  # noqa: E402


def sub(tag, data):
    return struct.pack('<4sI', tag.encode(), len(data)) + data


def record(tag, payload):
    return struct.pack('<4sIII', tag.encode(), len(payload), 0, 0) + payload


def cell(x, y, interior=False, name=b'\0'):
    return record('CELL', sub('NAME', name) + sub('DATA', struct.pack('<Iii', 1 if interior else 2, x, y)))


def land(x, y):
    return record('LAND', sub('INTV', struct.pack('<ii', x, y)) + sub('DATA', struct.pack('<I', 0)))


def report_of(*cells):
    return dict(cell_size=8192, cells=list(cells))


def cell_row(x, y, candidate=1, unresolved=0, reasons=None, name=''):
    row = dict(cell=[x, y], name=name, region='', screen=dict(candidate=candidate), unresolved_placements=unresolved)
    if reasons:
        row['unresolved_reasons'] = reasons
    return row


class Atlas(unittest.TestCase):
    def test_a_resolved_cell_passes(self):
        got = render_world_survey.terrain_regions(report_of(cell_row(-2, 3, 2), cell_row(4, 5, 1)))
        self.assertEqual([r['name'] for r in got], ['vf0000', 'vf0001', 'vf0002', 'vf0003', 'vf0004'])

    def test_every_refused_cell_is_named_with_its_reason(self):
        bad = cell_row(7, -3, 1, 2, [dict(reason='meshes/x/gone.nif: KeyError: gone', placements=2)], name='Nowhere')
        with self.assertRaises(ValueError) as caught:
            render_world_survey.terrain_regions(report_of(cell_row(0, 0), bad, cell_row(-25, 19, None)))
        text = str(caught.exception)
        self.assertIn('2 cell(s) refused', text)
        self.assertIn('cell (7, -3) Nowhere: 2 unresolved placement(s): meshes/x/gone.nif: KeyError: gone x2', text)
        self.assertIn('cell (-25, 19) unnamed: subdivision candidate None is not 1, 2, 4 or 8', text)
        self.assertNotIn('cell (0, 0)', text)


class BaseGrid(unittest.TestCase):
    def test_exterior_cells_and_land_of_the_base_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'Morrowind.esm'
            path.write_bytes(record('TES3', sub('HEDR', b'\0' * 300)) + cell(1, 2) + cell(9, 9, True, b'Room\0')
                             + land(1, 3))
            self.assertEqual(survey.base_grid(path), {(1, 2), (1, 3)})


class ExpansionArchive(unittest.TestCase):
    """A placement whose mesh only an expansion archive holds is measured when the expansions are on."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / 'Data Files'
        self.data.mkdir()
        self.cache = Path(self.tmp.name) / 'cache'
        self.cache.mkdir()
        write_bsa(self.data / 'Morrowind.bsa', {'meshes\\x\\base.nif': b'base'})
        write_bsa(self.data / 'Tribunal.bsa', {'meshes\\x\\trib.nif': b'trib'})
        write_bsa(self.data / 'Bloodmoon.bsa', {'meshes\\x\\bm_house.nif': b'blood'})
        geometry = (['geometry'], [], [[0, 0, 0], [1, 1, 1]], [])
        verts = [[0, 0, 0, 0, 0], [1, 0, 0, 0, 0], [0, 1, 0, 0, 0]]
        self.patches = [mock.patch.object(survey, 'model_geometry', return_value=geometry),
                        mock.patch.object(survey, 'unpack_geometry', return_value=(verts, [[0, 1, 2]], None)),
                        mock.patch.object(survey, '_assets', None)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def scan(self, masters):
        with mock.patch.dict(os.environ, {'AMIWIND_MASTERS': masters}):
            survey._assets = None
            return survey.mesh_scan((str(self.data), str(self.cache), 'meshes/x/bm_house.nif'))

    def test_measured_with_the_expansions_on(self):
        self.assertEqual(self.scan('Morrowind.esm,Tribunal.esm,Bloodmoon.esm')['status'], 'measured')

    def test_still_unresolved_on_the_base_game_alone(self):
        got = self.scan('Morrowind.esm')
        self.assertEqual(got['status'], 'unresolved')
        self.assertIn('bm_house', got['error'])


# Build stages that read the merged master (mwad.masters, so the expansions' records when they are on) but open
# Morrowind.bsa alone for meshes and textures: with the expansions on they cannot read a model only an expansion
# archive holds. The world survey and the 24 readers listed in EXPANSION-BASE-ONLY-TABLES-66 now read
# mwad.archives.layered_bsa, so none is known any more; a file with the pattern fails this test, so it is caught here
# and not by a build stage (TODO EXPANSION-DATA-ALL-TABLES-66).
KNOWN_BASE_ARCHIVE_READERS = set()
MERGED = re.compile(r'master_path\(|master_bytes\(')
BASE_ARCHIVE = re.compile(r"BSA\(child_ci\([^)]*'Morrowind\.bsa'\)\)")


class BaseArchiveReaders(unittest.TestCase):
    def test_the_survey_reads_the_layered_archives(self):
        text = (ROOT / 'tools/survey_vvardenfell.py').read_text(encoding='utf-8')
        self.assertIn('layered_bsa(', text)
        self.assertIsNone(BASE_ARCHIVE.search(text))

    def test_no_new_stage_reads_the_merged_master_with_the_base_archive_alone(self):
        found = set()
        for path in sorted((ROOT / 'tools').rglob('*.py')):
            text = path.read_text(encoding='utf-8', errors='replace')
            if MERGED.search(text) and BASE_ARCHIVE.search(text):
                found.add(path.relative_to(ROOT).as_posix())
        self.assertEqual(sorted(found - KNOWN_BASE_ARCHIVE_READERS), [],
                         'reads the merged master but the base archive alone: use mwad.archives.layered_bsa')
        self.assertEqual(sorted(KNOWN_BASE_ARCHIVE_READERS - found), [],
                         'fixed: remove it from KNOWN_BASE_ARCHIVE_READERS')


if __name__ == '__main__':
    unittest.main()
