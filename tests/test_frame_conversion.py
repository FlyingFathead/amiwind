# SPDX-License-Identifier: GPL-3.0-only
"""One shared conversion between map units and the original game's coordinates (CHIM-FRAME-SOURCE-CONVERSION-59).

AW_WorldToSource / AW_SourceToWorld / AW_WorldContains (engine/aga/src/aw_world.c) ask the open-world region table
first and the loaded CHIM frame second, so every caller gets a streamed town (a CHIM frame map, which has no region
row) at once. These contracts keep it that way: nothing outside aw_world.c looks up the region table directly or asks
the frame on its own. The behaviour is tested natively: tests/aga_world_regions_test.c (frame_maps: region rows
unchanged, the frame both ways, the script host's map-load decision), tests/aga_chim_world_test.c (ring: the frame's
own half), tests/aga_lamps_test.c and tests/aga_remote_test.c built with AW_FRAME_MAP (callers on a frame map).
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def sources():
    for path in sorted(SRC.rglob('*.c')):
        yield path.relative_to(SRC).as_posix(), path.read_text(encoding='utf-8', errors='replace')


def code_only(text):
    """The text without comments and string literals (a name in a comment is not a call)."""
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r'//[^\n]*', ' ', text)
    return re.sub(r'"(\\.|[^"\\\n])*"', '""', text)


def body(text, head):
    start = text.index(head)
    return text[start:text.index('\n}', start)]


class SharedConversionContract(unittest.TestCase):
    def test_the_region_table_alone_is_asked_only_by_the_shared_conversion(self):
        used = {name for name, text in sources()
                if re.search(r'\bAW_Region(WorldToSource|SourceToWorld)\s*\(', code_only(text))}
        self.assertEqual(used, {'aw_world.c'}, 'a direct region-table lookup outside the shared conversion: '
                         'call AW_WorldToSource / AW_SourceToWorld (aw_world.c), which also know the CHIM frame maps')

    def test_the_frame_half_is_set_by_chim_and_read_only_by_aw_world(self):
        users = {}
        for name, text in sources():
            for hook in re.findall(r'\baw_world_chim_(source|local|contains)\b', code_only(text)):
                users.setdefault(name, set()).add(hook)
        self.assertEqual(set(users), {'aw_world.c', 'chim/chim_world.c'})
        world = (SRC / 'chim/chim_world.c').read_text(encoding='utf-8')
        for line in ('aw_world_chim_source = FrameSource;', 'aw_world_chim_local = FrameLocal;',
                     'aw_world_chim_contains = FrameContains;'):
            self.assertIn(line, body(world, 'void Chim_Init (void)'))
        # the A/B: a compile switch, no console variable (ENGINE-RESIDENT-REGISTRY-GROWTH-36)
        self.assertIn('#if CHIM_FRAME_SOURCE', body(world, 'void Chim_Init (void)'))
        self.assertIn('#define CHIM_FRAME_SOURCE\t1', world)

    def test_no_private_frame_conversion_beside_it(self):
        # aw_inventory.c's own frame hooks (PLACED-ITEMS-OUTDOORS-FIRST-FRAME-59) went into the shared conversion
        for name, text in sources():
            self.assertNotIn('aw_focus_chim', text, name)
        # the debug HUD's older frame readout (HUD-GLOBAL-NO-REGIONS-33) asks the same frame function after the
        # shared conversion; no other file calls the frame's conversion itself
        callers = {name for name, text in sources() if re.search(r'\baw_chim_source\s*\(', code_only(text))}
        self.assertEqual(callers, {'aw_hud.c'})

    def test_region_table_first_then_the_loaded_frame(self):
        world = (SRC / 'aw_world.c').read_text(encoding='utf-8')
        to_source = body(world, 'int AW_WorldToSource(')
        self.assertLess(to_source.index('AW_RegionWorldToSource(name,local,world)'),
                        to_source.index('aw_world_chim_source && aw_world_chim_source(name,local,world)'))
        to_world = body(world, 'int AW_SourceToWorld(')
        self.assertLess(to_world.index('AW_RegionSourceToWorld(name,world,local)'),
                        to_world.index('aw_world_chim_local && aw_world_chim_local(name,world,local)'))
        contains = body(world, 'int AW_WorldContains(')
        self.assertLess(contains.index('if(r)return inside(local,r->cover,-24);'),
                        contains.index('aw_world_chim_contains'))
        # the frame answers for the frame map that is loaded, finite numbers only
        chim = (SRC / 'chim/chim_world.c').read_text(encoding='utf-8')
        frame = body(chim, 'static int FrameMap (')
        self.assertIn("!strcmp (name, frame_map)", frame)
        self.assertIn('isfinite (v[2])', frame)
        self.assertIn('Q_strcpy_bounded (frame_map, MapName (), sizeof(frame_map));', chim)
        self.assertIn('frame_map[0] = 0;', body(chim, 'static void MapEnd (void)'))

    def test_the_script_host_decides_room_or_outdoors_by_the_shared_conversion(self):
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        attach = body(host, 'static void attach_map(void){')
        self.assertIn('map_room=AW_SourceToWorld(sv.name,zero,at)?0:map_cell_number();', attach)
        self.assertIn('outdoors=AW_SourceToWorld(sv.name,source,local);', attach)
        self.assertIn('!AW_WorldContains(sv.name,local)', attach)


if __name__ == '__main__':
    unittest.main()
