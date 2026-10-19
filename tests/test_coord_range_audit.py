# SPDX-License-Identifier: GPL-3.0-only
"""The coordinate range audit (CHIM-FRAME-COORD-RANGE-33): every 4000 / 4096 / 4095 in the engine and in the
builder's frame checks is listed in config/coord-range-audit.json with its class (bound, kept, unrelated), so a
new assumption about Quake's +/-4,096 coordinate range cannot slip in unexamined, and the engine's position
bounds go through AW_COORD_BOUND (engine/aga/src/aw_coord.h), which the wide-coordinate switch raises."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'config/coord-range-audit.json'
PATTERN = re.compile(r'(^|[^0-9.xA-Za-z_])-?(4000|4096|4095)(\.0?f?)?([^0-9]|$)')
SCOPE = ('engine/aga/src', 'tools/town_config.py', 'tools/prepare_world_regions.py', 'tools/chim')
CLASSES = ('bound', 'kept', 'unrelated')


def occurrences():
    out = []
    for scope in SCOPE:
        base = ROOT / scope
        files = [base] if base.is_file() else sorted(p for p in base.rglob('*') if p.suffix in ('.c', '.h', '.py'))
        for path in files:
            for line in path.read_text(encoding='utf-8', errors='replace').split('\n'):
                if PATTERN.search(line):
                    out.append((path.relative_to(ROOT).as_posix(), line.strip()))
    return out


class CoordRangeAuditTests(unittest.TestCase):
    def setUp(self):
        self.entries = json.loads(AUDIT.read_text(encoding='utf-8'))['entries']

    def test_every_occurrence_is_listed_and_every_entry_is_current(self):
        found = occurrences()
        unlisted = [f'{f}: {line}' for f, line in found
                    if not any(e['file'] == f and e['contains'] in line for e in self.entries)]
        self.assertEqual(unlisted, [], 'new 4000/4096 values: classify them in config/coord-range-audit.json')
        stale = [f'{e["file"]}: {e["contains"]}' for e in self.entries
                 if not any(e['file'] == f and e['contains'] in line for f, line in found)]
        self.assertEqual(stale, [], 'audit entries that no longer match the source')

    def test_entries_are_classified_with_a_reason(self):
        for e in self.entries:
            self.assertIn(e['class'], CLASSES, e)
            self.assertTrue(e['note'].strip(), e)

    def test_engine_position_bounds_follow_the_coordinate_bound(self):
        world = (ROOT / 'engine/aga/src/aw_world.c').read_text(encoding='utf-8')
        self.assertEqual(world.count('AW_COORD_BOUND'), 6)   # valid_town (2), region cover (2), two arrival checks
        self.assertNotRegex(world, r'[^0-9]4000[^0-9]')
        spawn = (ROOT / 'engine/aga/src/aw_spawn.c').read_text(encoding='utf-8')
        # map placement x/y (2) and below-point z (1); the search band and AW_MapPlace's start height follow the bound
        # too (CHIM-RED-MOUNTAIN-SOLID-SKY-43: the 3,990 / 4,000 clamps started the search inside Red Mountain)
        self.assertEqual(spawn.count('AW_COORD_BOUND'), 8)
        self.assertNotIn('3990', spawn)
        self.assertNotRegex(spawn, r'[^0-9]4000[^0-9]')
        scene = (ROOT / 'engine/aga/src/aw_scene.c').read_text(encoding='utf-8')
        self.assertIn('fabs(local[2])<AW_COORD_BOUND', scene)
        protocol = (ROOT / 'engine/aga/src/protocol.h').read_text(encoding='utf-8')
        self.assertIn('#define\tPROTOCOL_VERSION\tAW_COORD_PROTOCOL', protocol)
        common = (ROOT / 'engine/aga/src/common.c').read_text(encoding='utf-8')
        self.assertIn('MSG_WriteShort (sb, (int)(f*8));', common)          # the narrow default stays Quake's
        self.assertIn('return MSG_ReadShort() * (1.0/8);', common)


if __name__ == '__main__':
    unittest.main()
