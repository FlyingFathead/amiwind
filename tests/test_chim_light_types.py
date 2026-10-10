# SPDX-License-Identifier: GPL-3.0-only
"""CHIM lighting types (--chim-lighting-type, tools/chim/light_types.py): choices, the default, reserved types,
the lamp table each type writes, the builder plumbing and the documentation that must list every type.
Synthetic records only; no game data."""
import argparse
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_font_options as BFO  # noqa: E402
import cell_lighting as CL  # noqa: E402
import light_sources as LS  # noqa: E402
from chim import light_types as LT  # noqa: E402

DOCS = ('docs/chim/LIGHTING.md', 'docs/chim/LIGHTING_ROADMAP.md', 'docs/chim/build_guide/BUILDER_TYPES.md', 'docs/CHANGELOG.md')


def sub(tag, data): return tag.encode() + struct.pack('<I', len(data)) + data
def record(tag, body): return tag.encode() + struct.pack('<III', len(body), 0, 0) + body


def ligh(identifier, model, flags):
    lhdt = struct.pack('<fiiI', 1.0, 0, 0, 128) + bytes((200, 160, 90)) + b'\0' + struct.pack('<I', flags)
    return record('LIGH', sub('NAME', identifier + b'\0') + sub('MODL', model + b'\0') + sub('LHDT', lhdt))


def master():
    refs = [(b'syn_lantern', 1), (b'syn_light_256', 0), (b'syn_shroom_glow', 0), (b'syn_dark', 4)]
    raw = b''.join(ligh(i, b'l\\lantern.nif' if i == b'syn_lantern' else b'', f) for i, f in refs)
    body = sub('NAME', b'Syn\0') + sub('DATA', struct.pack('<Iii', 0, 1, 2))
    for n, (i, _) in enumerate(refs, 1):
        body += sub('FRMR', struct.pack('<I', n)) + sub('NAME', i + b'\0') + sub('DATA', struct.pack('<6f', n, n, n, 0, 0, 0))
    return raw + record('CELL', body)


class LightingTypeTests(unittest.TestCase):
    def test_types_default_and_reserved(self):
        self.assertEqual(LT.DEFAULT, 'hybrid')
        self.assertEqual(LT.IMPLEMENTED, ('none', 'lamps', 'hybrid'))
        self.assertEqual(set(LT.RESERVED), {'baked-e', 'full'})
        for k in LT.IMPLEMENTED:
            self.assertEqual(LT.check(k), k)
        for k in LT.RESERVED:
            with self.assertRaisesRegex(ValueError, 'increased-memory version'):
                LT.check(k)
        with self.assertRaisesRegex(ValueError, 'choose one of none, lamps, hybrid'):
            LT.check('sunny')
        rec = LT.record('hybrid')
        self.assertEqual(rec['parts']['lightstyles'], 'implemented')
        self.assertEqual(rec['parts']['terrain_lightmaps'], 'planned')

    def test_lamp_table_per_type(self):
        raw = master()
        n = {k: struct.unpack_from('<I', LS.lamp_table(raw, classes=LT.lamp_classes(k)), 4)[0] for k in LT.IMPLEMENTED}
        self.assertEqual(n, {'none': 0, 'lamps': 1, 'hybrid': 3})         # darkeners never become dynamic lights
        self.assertEqual(LS.lamp_table(raw), LS.lamp_table(raw, classes=LT.lamp_classes('lamps')))   # legacy default unchanged

    def test_tracker_reach_for_hybrid(self):
        p = CL.light_census_cell([('lamp', True, 0, 32), ('pure_light', False, 0, 32), ('negative', False, 4, 32)])
        self.assertEqual(CL.reach(p, 'hybrid'), {'baked': 0, 'lamp_table': 2, 'none': 1})
        self.assertEqual(CL.reach(p, 'hybrid', baked=3), {'baked': 3, 'lamp_table': 0, 'none': 0})

    def test_builder_option_default_config_and_cli(self):
        defaults = json.loads((ROOT / 'config/build-defaults.json').read_text(encoding='utf-8'))
        self.assertEqual(defaults['chim_lighting_type'], 'hybrid')
        p = argparse.ArgumentParser()
        BFO.add_font_options(p)
        BFO.add_builder_options(p)
        self.assertEqual(BFO.resolve_builder(p.parse_args([]))['chim_lighting_type'], 'hybrid')
        got = BFO.resolve_builder(p.parse_args(['--chim-lighting-type', 'lamps']))
        self.assertEqual((got['chim_lighting_type'], got['chim_lighting_type_selected_by']), ('lamps', 'CLI override'))
        with self.assertRaisesRegex(ValueError, 'increased-memory'):
            BFO.resolve_builder(p.parse_args(['--chim-lighting-type', 'full']))
        with tempfile.TemporaryDirectory() as t:
            cfg = Path(t) / 'b.json'
            cfg.write_text(json.dumps({'chim_lighting_type': 'none'}), encoding='utf-8')
            self.assertEqual(BFO.resolve_builder(p.parse_args(['--build-config', str(cfg)]))['chim_lighting_type'], 'none')
            cfg.write_text(json.dumps({'chim_lighting_type': 'sunny'}), encoding='utf-8')
            with self.assertRaises(ValueError):
                BFO.resolve_builder(p.parse_args(['--build-config', str(cfg)]))
        self.assertIsNone(BFO.resolve_builder(p.parse_args(['--builder', 'legacy']))['chim_lighting_type'])

    def test_help_and_docs_list_every_type_and_the_default(self):
        text = LT.help_text()
        for k in LT.TYPES:
            self.assertIn(k + ' = ', text)
        self.assertIn('default hybrid', text)
        build = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn("'--lighting-type', builder.get('chim_lighting_type')", build)
        self.assertIn("'--chim-lighting-type'", build)
        for rel in DOCS:
            doc = (ROOT / rel).read_text(encoding='utf-8')
            self.assertIn('--chim-lighting-type', doc, rel)
            for k in LT.TYPES:
                self.assertIn('`%s`' % k, doc, '%s does not list %s' % (rel, k))
            self.assertIn('default', doc, rel)


if __name__ == '__main__':
    unittest.main()
