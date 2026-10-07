# SPDX-License-Identifier: GPL-3.0-only
"""Night window table: BSP texture provenance, glass/lamp rules, table format."""
import json, struct, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import night_windows as N

AMBER, WOOD, PAPER = (200, 150, 50), (90, 60, 30), (240, 200, 120)
PALETTE = [(0, 0, 0)] * 256
PALETTE[1], PALETTE[2], PALETTE[3] = AMBER, WOOD, PAPER


def bsp(textures, submodels, entities):
    """textures: [(name, palette index)]; submodels: [[texture per face]]."""
    tex = bytearray(); offsets = []
    for name, colour in textures:
        offsets.append(4 + 4 * len(textures) + len(tex))
        tex += struct.pack('<16s6I', name.encode(), 16, 16, 40, 296, 360, 376) + bytes([colour]) * (256 + 64 + 16 + 4)
    lumps = [b''] * 15
    lumps[2] = struct.pack('<i', len(textures)) + struct.pack('<%di' % len(offsets), *offsets) + bytes(tex)
    lumps[6] = b''.join(struct.pack('<8fii', *[0.0] * 8, t, 0) for t in range(len(textures)))
    faces = bytearray(); models = bytearray()
    for faces_of in [[]] + submodels:
        models += struct.pack('<9f7i', *[0.0] * 9, 0, 0, 0, 0, 0, len(faces) // 20, len(faces_of))
        for t in faces_of: faces += struct.pack('<Hhihh4Bi', 0, 0, 0, 3, t, 255, 255, 255, 255, -1)
    lumps[7] = bytes(faces); lumps[14] = bytes(models)
    text = '{\n"classname" "worldspawn"\n}\n' + ''.join(
        '{\n"classname" "func_wall"\n"aw_ref" "%d"\n"model" "*%d"\n}\n' % (ref, model) for ref, model in entities)
    lumps[0] = text.encode() + b'\0'
    header = bytearray(struct.pack('<i', 29) + bytes(120)); data = bytearray()
    for k, lump in enumerate(lumps):
        data += bytes((-len(data)) % 4); struct.pack_into('<ii', header, 4 + 8 * k, 124 + len(data), len(lump)); data += lump
    return bytes(header + data)


def material(texture, ti, emissive=None):
    m = {'texture_source': texture, 'diffuse': [1.0, 1.0, 1.0], 'source_shape': 'Tri ' + texture, 'texture_index': ti}
    if emissive is not None: m['emissive'] = emissive
    return m


INDEX = {
    'textures': [{'source': 'textures/tx_glass_amber_02.dds'}, {'source': 'textures/tx_wood_brown_01.dds'},
                 {'source': 'textures/tx_misc_lantern_paper_02.dds'}, {'source': 'textures/tx_glass_bottle_blue.dds'},
                 {'source': 'textures/tx_window_diamond_01.dds'}],
    'models': [
        {'source': 'meshes/x/ex_hlaalu_win_01.nif',
         'materials': [material('Tx_wood_brown_01.tga', 1), material('tx_glass_amber_02.tga', 0)]},
        {'source': 'meshes/l/light_de_streetlight_01.nif',
         'materials': [material('Tx_wood_brown_01.tga', 1, 0), material('Tx_Misc_lantern_paper_02.tga', 2, 9)]},
        {'source': 'meshes/m/misc_com_bottle_06.nif', 'materials': [material('Tx_glass_bottle_blue.tga', 3)]},
        {'source': 'meshes/x/ex_common_window_01.nif', 'materials': [material('Tx_window_diamond_01.tga', 4)]},
        {'source': 'meshes/x/ex_paper_screen.nif', 'materials': [material('Tx_Misc_lantern_paper_02.tga', 2)]},
    ],
    'references': [{'number': 10, 'model_index': 0, 'type': 'STAT'}, {'number': 11, 'model_index': 1, 'type': 'LIGH'},
                   {'number': 12, 'model_index': 2, 'type': 'MISC'}, {'number': 13, 'model_index': 3, 'type': 'STAT'},
                   {'number': 14, 'model_index': 4, 'type': 'STAT'}]}
COLOURS = {0: AMBER, 1: WOOD, 2: PAPER, 3: (20, 40, 200), 4: AMBER}


def source(index=INDEX, emissive=None):
    return SimpleNamespace(index=index, directory='synthetic',
                           texture_rgb=lambda ti: np.full((8, 8, 3), COLOURS[ti], float),
                           emissive_of=lambda model: emissive(model) if emissive else [None] * len(model['materials']))


class RuleTests(unittest.TestCase):
    def test_window_glass_names(self):
        self.assertTrue(N.is_window_glass('Tx_window_diamond_01.tga', 'meshes/x/anything.nif'))
        self.assertTrue(N.is_window_glass('Tx_win_weather00.tga', 'meshes/x/ex_stronghold_window00.nif'))
        self.assertTrue(N.is_window_glass('tx_glass_amber_02.tga', 'meshes/x/ex_velothi_temple_01.nif'))
        self.assertTrue(N.is_window_glass('tx_glass_amber_02.tga', 'meshes/i/in_redoran_window_01.nif'))
        self.assertFalse(N.is_window_glass('Tx_glass_bottle_blue.tga', 'meshes/x/ex_shelf.nif'))
        self.assertFalse(N.is_window_glass('tx_glass_amber_02.tga', 'meshes/m/misc_de_goblet_03.nif'))
        self.assertFalse(N.is_window_glass('Tx_glass_obsidian.tga', 'meshes/x/ex_dae_ruin.nif'))
        self.assertFalse(N.is_window_glass('Tx_hlaalu_wall2_02.tga', 'meshes/x/ex_hlaalu_win_01.nif'))
        self.assertFalse(N.is_window_glass(None, 'meshes/x/ex_hlaalu_win_01.nif'))

    def test_lamp_needs_light_placement_and_emissive(self):
        model = {'source': 'meshes/l/light_de_streetlight_01.nif'}
        paper = material('Tx_Misc_lantern_paper_02.tga', 2)
        self.assertEqual(N.material_kind(paper, model, {'LIGH'}, 9), 'lamp')
        self.assertIsNone(N.material_kind(paper, model, {'LIGH'}, 0))
        self.assertIsNone(N.material_kind(paper, model, {'STAT'}, 9))


class ProvenanceTests(unittest.TestCase):
    def classify(self, textures, submodels, entities, sources=None, palette=PALETTE):
        return N.classify_map(N.read_bsp(bsp(textures, submodels, entities)), sources or [source()], palette)

    def test_pixels_settle_which_material_a_texture_came_from(self):
        out = self.classify([('surface0', 2), ('surface1', 1), ('surface2', 3)],
                            [[0, 0, 1], [0, 2, 2, 2]], [(10, 1), (11, 2), (11, 2)])
        t = out['textures']
        self.assertEqual((t['surface0']['kind'], t['surface0']['sources']), (None, ['textures/tx_wood_brown_01.dds']))
        self.assertEqual((t['surface1']['kind'], t['surface1']['sources']), ('window', ['textures/tx_glass_amber_02.dds']))
        self.assertEqual((t['surface2']['kind'], t['surface2']['faces'], t['surface2']['drawn_faces']), ('lamp', 3, 6))
        self.assertEqual(N.glowing(out), ['surface1', 'surface2'])
        self.assertLess(t['surface1']['pixel_distance']['textures/tx_glass_amber_02.dds'],
                        t['surface1']['pixel_distance']['textures/tx_wood_brown_01.dds'])

    def test_shared_models_narrow_candidates_without_pixels(self):
        out = self.classify([('surface0', 1), ('surface1', 4)], [[0], [1]], [(10, 1), (13, 2)], palette=None)
        self.assertEqual(out['textures']['surface0']['status'], 'ambiguous')
        self.assertIsNone(out['textures']['surface0']['kind'])
        self.assertEqual(out['textures']['surface1']['kind'], 'window')

    def test_bottles_never_glow_and_mixed_owners_stay_dark(self):
        out = self.classify([('surface0', 3), ('surface1', 3)], [[0], [1], [1]], [(12, 1), (11, 2), (14, 3)])
        self.assertIsNone(out['textures']['surface0']['kind'])
        self.assertEqual(out['textures']['surface1']['status'], 'mixed')
        self.assertEqual(N.glowing(out), [])

    def test_emissive_comes_from_the_original_model_when_the_index_lacks_it(self):
        index = json.loads(json.dumps(INDEX))
        for m in index['models'][1]['materials']: m.pop('emissive')
        read = []
        def emissive(model): read.append(model['source']); return [0, 9]
        out = self.classify([('surface0', 3)], [[0]], [(11, 1)], [source(index, emissive)])
        self.assertEqual(out['textures']['surface0']['kind'], 'lamp')
        self.assertEqual(read, ['meshes/l/light_de_streetlight_01.nif'])
        unknown = self.classify([('surface0', 3)], [[0]], [(11, 1)], [source(index)])
        self.assertEqual(unknown['emissive_unknown'], ['meshes/l/light_de_streetlight_01.nif'])
        self.assertEqual(N.glowing(unknown), [])

    def test_unknown_references_are_reported_with_their_textures(self):
        out = self.classify([('surface0', 1), ('flat5', 1), ('surface9', 1)], [[0], [0, 1, 2]], [(99, 2), (10, 1)])
        self.assertEqual(out['unresolved_refs'], ['99'])
        self.assertEqual(out['untraced_textures'], ['surface9'])

    def test_a_reference_resolves_in_the_first_source_listing_it(self):
        overlay = {'textures': [{'source': 'textures/tx_bark_01.dds'}],
                   'models': [{'source': 'meshes/f/flora_tree_01.nif', 'materials': [material('Tx_bark_01.tga', 0)]}],
                   'references': [{'number': 10, 'model_index': 0, 'type': 'STAT'},
                                  {'number': 50, 'model_index': 0, 'type': 'STAT'}]}
        flora = SimpleNamespace(index=overlay, directory='flora', texture_rgb=lambda ti: None,
                                emissive_of=lambda m: [None])
        out = self.classify([('surface0', 4), ('surface1', 2)], [[0], [1]], [(13, 1), (50, 2)], [source(), flora])
        self.assertEqual(out['textures']['surface0']['kind'], 'window')
        self.assertEqual(out['textures']['surface1']['sources'], ['textures/tx_bark_01.dds'])
        self.assertEqual(out['unresolved_refs'], [])


class TableTests(unittest.TestCase):
    def test_table_is_sorted_lf_and_skips_dark_maps(self):
        text = N.table_text({'sn012': ['surface80'], 'bm019': ['surface81', 'surface105', 'surface43'], 'bm000': []})
        self.assertEqual(text, 'bm019 surface105 surface43 surface81\nsn012 surface80\n')
        self.assertEqual(N.parse_table(text), {'bm019': ['surface105', 'surface43', 'surface81'], 'sn012': ['surface80']})
        with self.assertRaises(ValueError): N.table_text({'bad map': ['surface1']})

    def test_command_line_writes_table_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp); (tmp / 'maps').mkdir(); (tmp / 'scenery').mkdir()
            (tmp / 'scenery' / 'scenery-index.json').write_text(json.dumps(INDEX), encoding='utf-8')
            (tmp / 'maps' / 'bm019.bsp').write_bytes(bsp([('surface7', 1)], [[0]], [(13, 1)]))
            (tmp / 'maps' / 'bm000.bsp').write_bytes(bsp([('surface3', 3)], [[0]], [(12, 1)]))
            (tmp / 'maps' / 'other.bsp').write_bytes(bsp([('surface3', 3)], [[0]], [(14, 1)]))
            out = tmp / 'id1' / 'world' / 'night-windows.txt'
            self.assertEqual(N.main(['--maps', str(tmp / 'maps'), '--scenery', 'bm0*=' + str(tmp / 'scenery'),
                                     '--out', str(out), '--report', str(tmp / 'report.json')]), 0)
            self.assertEqual(out.read_bytes(), b'bm019 surface7\n')
            report = json.loads((tmp / 'report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['other'], {'skipped': 'no scenery source pattern matches'})
            self.assertEqual((report['bm019']['window_textures'], report['bm019']['window_faces']), (['surface7'], 1))
            self.assertEqual(report['bm000']['glowing'], [])


if __name__ == '__main__':
    unittest.main()
