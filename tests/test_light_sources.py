# SPDX-License-Identifier: GPL-3.0-only
"""Light source mapping: class, Quake style, entity text, census per cell."""
import struct, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import light_sources as L


def sub(tag, data): return tag.encode() + struct.pack('<I', len(data)) + data
def record(tag, body): return tag.encode() + struct.pack('<III', len(body), 0, 0) + body
def ligh(identifier, model, radius, colour, flags):
    lhdt = struct.pack('<fiiI', 1.0, 0, 0, radius) + bytes(colour) + b'\0' + struct.pack('<I', flags)
    return record('LIGH', sub('NAME', identifier + b'\0') + sub('MODL', model + b'\0') + sub('LHDT', lhdt))
def cell(name, flags, x, y, refs):
    body = sub('NAME', name + b'\0') + sub('DATA', struct.pack('<Iii', flags, x, y))
    for n, (identifier, pos) in enumerate(refs, 1):
        body += sub('FRMR', struct.pack('<I', n)) + sub('NAME', identifier + b'\0') + sub('DATA', struct.pack('<6f', *pos, 0, 0, 0))
    return record('CELL', body)


class LightSourceTests(unittest.TestCase):
    def test_class_comes_from_the_model_before_the_fire_flag(self):
        self.assertEqual(L.classify('light_com_candle_02_64', 'l\\candle.nif', 0x53), 'candle')
        self.assertEqual(L.classify('light_com_lantern_02', 'l\\lantern.nif', 0x53), 'lamp')
        self.assertEqual(L.classify('light_de_streetlight_01_223', 'l\\streetlight.nif', 1), 'lamp')
        self.assertEqual(L.classify('light_pitfire00', 'l\\pitfire.nif', 0x51), 'fire')
        self.assertEqual(L.classify('torch_128', 'l\\light_torch10.nif', 0x51), 'torch')
        self.assertEqual(L.classify('dark_128', '', 4), 'negative')
        self.assertEqual(L.classify('Flame Light', '', 0), 'fire')
        self.assertEqual(L.classify('light_x', '', 0), 'pure_light')
        self.assertEqual(L.classify('light_dwrv_neon01', 'l\\neon.nif', 0x10), 'fire')
        self.assertEqual(L.classify('light_dwrv_neon01', 'l\\neon.nif', 0x100), 'other')
        self.assertEqual(L.classify('light_com_candle_01_off', 'l\\candle.nif', 0x21), 'off')
        self.assertEqual(L.entity({'class': 'off', 'radius': 64, 'colour': [1, 2, 3], 'flags': 0x21}, (0, 0, 0)), '')

    def test_styles_follow_original_flags_and_outdoor_lamps_switch_at_night(self):
        self.assertEqual(L.quake_style('lamp', 1, True), L.STYLE_NIGHT_LAMPS)
        self.assertEqual(L.quake_style('lamp', 0x41, False), L.STYLE_FLICKER_SOFT)
        self.assertEqual(L.quake_style('fire', 0x8, True), L.STYLE_FLICKER)
        self.assertEqual(L.quake_style('other', 0x80, False), L.STYLE_GENTLE_PULSE)
        self.assertEqual(L.quake_style('other', 0x100, False), L.STYLE_SLOW_PULSE)
        self.assertEqual(L.quake_style('candle', 1, False), L.STYLE_NORMAL)

    def test_entity_text_uses_local_units_colour_and_style(self):
        light = {'class': 'lamp', 'radius': 223, 'colour': [245, 140, 40], 'flags': 1}
        text = L.entity(light, (400, -800, 120), centre=(0, 0), exterior=True)
        self.assertIn('"origin" "100.00 -200.00 30.00"', text)
        self.assertIn('"light" "56"', text); self.assertIn('"delay" "1"', text)
        self.assertIn('"_color" "0.961 0.549 0.157"', text); self.assertIn('"style" "32"', text)
        dark = L.entity({'class': 'negative', 'radius': 128, 'colour': [255, 255, 255], 'flags': 4}, (0, 0, 0))
        self.assertIn('"light" "-32"', dark); self.assertNotIn('"style"', dark)

    def test_lamp_table_lists_exterior_warm_sources_sorted_by_cell(self):
        raw = (ligh(b'light_de_streetlight_01', b'l\\s.nif', 223, (245, 140, 40), 1)
               + ligh(b'light_com_candle_02', b'l\\c.nif', 64, (245, 140, 40), 0x53)
               + ligh(b'light_x', b'', 128, (255, 255, 255), 0)
               + cell(b'Town', 0, -3, -2, [(b'light_de_streetlight_01', (1, 2, 3)), (b'light_x', (9, 9, 9))])
               + cell(b'Other', 0, -4, -2, [(b'light_com_candle_02', (5, 6, 7))])
               + cell(b'Guild', 1, 0, 0, [(b'light_de_streetlight_01', (0, 0, 0))]))
        data = L.lamp_table(raw)
        self.assertEqual(data[:8], b'AWL1' + struct.pack('<I', 2))
        rows = list(L.LAMP_ROW.iter_unpack(data[8:]))
        self.assertEqual([(r[0], r[1], r[5], r[6], r[7]) for r in rows], [(-4, -2, 64, 4, 1), (-3, -2, 223, 1, 1)])
        self.assertEqual(rows[1][2:5], (1.0, 2.0, 3.0))

    def test_census_counts_per_class_and_per_cell(self):
        raw = (ligh(b'light_de_streetlight_01', b'l\\s.nif', 223, (245, 140, 40), 1)
               + ligh(b'light_com_candle_02', b'l\\c.nif', 64, (245, 140, 40), 0x53)
               + ligh(b'light_de_lantern_10', b'l\\l.nif', 128, (0, 166, 255), 1)
               + cell(b'Town', 0, -3, -2, [(b'light_de_streetlight_01', (1, 2, 3))] * 3)
               + cell(b'Guild', 1, 0, 0, [(b'light_com_candle_02', (0, 0, 0)), (b'light_de_lantern_10', (5, 5, 5))]))
        report = L.census(raw)
        self.assertEqual(report['placements'], 5)
        self.assertEqual(report['classes']['lamp'], {'placements': 4, 'interior': 1, 'exterior': 3})
        self.assertEqual(report['classes']['candle']['interior'], 1)
        self.assertEqual(report['colours'], {'warm': 4, 'cool': 1})
        self.assertEqual(report['per_cell']['exterior']['max'], 3)
        self.assertEqual(report['per_cell']['interior']['animated_median'], 1)
        self.assertEqual(report['styles'], {'0': 1, '6': 1, '32': 3})


if __name__ == '__main__':
    unittest.main()
