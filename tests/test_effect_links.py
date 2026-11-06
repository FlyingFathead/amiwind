"""TAKEN-LIGHT-FLAME-61: a carriable light that gives light takes its effects with it, everywhere in the game.

tools/effect_links.py writes the exterior cells' effect links into their own records of areas.awa and refuses an
image where any carriable light's flame, night lamp row or exterior placement is not tied to it; these tests plant a
miss in each path and check the refusal, and keep the engine's readers of the links in place."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import effect_links as L  # noqa: E402
from light_sources import LAMP_ROW  # noqa: E402

SRC = ROOT / 'engine/aga/src'
CANDLE, LANTERN, FIXED = 119501, 146616, 5000


def lights():
    return {CANDLE: {'id': 'light_com_candle_06', 'master': 'Morrowind.esm', 'interior': True,
                     'cell': 'Seyda Neen, Census and Excise Office', 'position': (1.0, 2.0, 3.0), 'flames': True},
            LANTERN: {'id': 'light_com_lantern_02', 'master': 'Morrowind.esm', 'interior': False, 'cell': (-2, -9),
                      'position': (-12500.5, -71234.25, 310.0), 'flames': True}}


def flame(ref=None, origin='1.00 2.00 3.00'):
    row = {'classname': 'aw_flame', 'origin': origin, 'aw_flame_size': '0.80'}
    if ref is not None:
        row['aw_ref'] = str(ref)
    return row


class Image:
    """A small id1: maps whose entity rows the test names, an optional lamp table."""

    def __init__(self, maps, lamps=()):
        self.tmp = tempfile.TemporaryDirectory()
        self.id1 = Path(self.tmp.name)
        (self.id1 / 'maps').mkdir()
        for name in maps:
            (self.id1 / 'maps' / name).write_bytes(b'')
        self.maps = maps
        if lamps:
            (self.id1 / 'world').mkdir()
            (self.id1 / L.LAMPS).write_bytes(b'AWL1' + struct.pack('<I', len(lamps)) +
                                             b''.join(LAMP_ROW.pack(*r) for r in lamps))

    def __enter__(self):
        self.saved = L.map_entities
        L.map_entities = lambda p: self.maps[Path(p).name]
        return self

    def __exit__(self, *a):
        L.map_entities = self.saved
        self.tmp.cleanup()


def room(*flames, placed=(CANDLE, FIXED)):
    return [{'classname': 'worldspawn'}] + [{'classname': 'func_wall', 'aw_ref': str(r), 'model': '*1'} for r in placed] + \
        list(flames)


class RoomFlames(unittest.TestCase):
    def test_a_room_flame_that_names_its_candle_passes(self):
        with Image({'census.bsp': room(flame(CANDLE), flame(FIXED), flame())}) as im:
            got = L.check(im.id1, lights(), links={})
        self.assertEqual(got['room placements tied'], 1)

    def test_a_planted_miss_is_refused(self):
        # the candle's flame written without its reference: the flame would hang in the air after the take
        with Image({'census.bsp': room(flame(), flame(FIXED))}) as im:
            with self.assertRaises(ValueError) as e:
                L.check(im.id1, lights(), links={})
        self.assertIn('census.bsp: the flame of reference %d (light_com_candle_06) names no placement' % CANDLE,
                      str(e.exception))

    def test_a_fixed_light_needs_no_link(self):
        with Image({'hall.bsp': room(flame(), placed=(FIXED,))}) as im:
            self.assertNotIn('room placements', L.check(im.id1, lights(), links={}))

    def test_past_the_flame_cap_nothing_is_drawn_and_it_is_counted(self):
        rows = room(*[flame(FIXED) for _ in range(L.FLAME_CAP)])
        with Image({'hall.bsp': rows}) as im:
            got = L.check(im.id1, lights(), links={})
        self.assertEqual(got['room placements past the flame cap (no flame drawn)'], 1)


class Outdoors(unittest.TestCase):
    def lamp(self):
        x, y, z = lights()[LANTERN]['position']
        return [(-2, -9, x, y, z, 128, 1, 1), (-2, -9, x + 64, y, z, 128, 1, 1)]

    def test_the_lantern_lamp_row_must_be_linked(self):
        with Image({}, lamps=self.lamp()) as im:
            with self.assertRaises(ValueError) as e:
                L.check(im.id1, lights(), links={})
            self.assertIn('world/lamps.awl row 0 of reference %d' % LANTERN, str(e.exception))
            rows = L.area_rows(im.id1, None, lights())
            self.assertEqual(rows, {L.area_key(lights()[LANTERN]): [(L.KIND_LAMP, 0, 0, LANTERN)]})
            self.assertEqual(L.check(im.id1, lights(), links=rows)['lamp rows'], 1)

    def test_the_lantern_placement_must_be_linked_so_it_can_be_taken(self):
        world = {'frames': [(0, {'cell': (-2, -9)}, [{'owned': [{'pid': 7001, 'ref': LANTERN},
                                                                {'pid': 7002, 'ref': (3 << 24) | LANTERN},
                                                                {'pid': 7003, 'ref': FIXED}]}])], 'models': []}
        with Image({}) as im:
            with self.assertRaises(ValueError) as e:
                L.check(im.id1, lights(), world, links={})
            self.assertIn('CHIM placement 7001 of reference %d' % LANTERN, str(e.exception))
            rows = L.area_rows(im.id1, world, lights())
            self.assertEqual([r[2] for r in rows[L.area_key(lights()[LANTERN])]], [7001, 7002])   # both pieces
            self.assertEqual(L.check(im.id1, lights(), world, links=rows)['exterior placements'], 2)


class Sections(unittest.TestCase):
    def pack(self, records):
        """A small AWA1 pack: no directories, the records in key order."""
        head = b'AWA1' + struct.pack('<IIIII', len(records), 0, 0, 0, 0)
        at, index = 24 + 12 * len(records), b''
        for key, r in records:
            index += struct.pack('<III', key, at, len(r))
            at += len(r)
        return head + index + b''.join(r for _, r in records)

    def test_a_section_goes_last_and_the_other_sections_stay_readable(self):
        levelled = b'AWB1' + bytes(12) + b'AWL1....' + struct.pack('<I', 16) + b'AWL1'
        plain = b'AWB1' + bytes(12)
        key = L.area_key(lights()[LANTERN])
        raw = self.pack([(5, plain), (key, levelled)])
        rows = {key: [(L.KIND_PLACE, 0, 7001, LANTERN), (L.KIND_LAMP, 0, 0, LANTERN)]}
        patched = L.patch_areas(raw, rows)
        _, index, _, records = L.read_areas(patched)
        self.assertEqual(records[5], plain)
        self.assertEqual(L.read_section(records[key]), rows[key])
        start = struct.unpack_from('<I', records[key], len(records[key]) - 8)[0]
        self.assertEqual(records[key][:start], levelled)              # the levelled trailer ends where links start
        self.assertEqual(len(records[key]) - len(levelled), 8 + 12 * 2 + 8)
        self.assertEqual(L.patch_areas(patched, rows), patched)       # written again: replaced, not doubled
        with self.assertRaises(KeyError):
            L.patch_areas(raw, {0x80000001: rows[key]})


class EngineReaders(unittest.TestCase):
    def code(self, name):
        return (SRC / name).read_text(encoding='latin-1')

    def test_the_engine_reads_the_links_with_the_area(self):
        inv = self.code('aw_inventory.c')
        # the links are the record's last section: peeled first, then the stats, then the levelled lists
        self.assertLess(inv.index('!memcmp(b+len-4,"AWE1",4)'), inv.index('!memcmp(b+len-4,"AWS1",4)'))
        self.assertLess(inv.index('!memcmp(b+len-4,"AWS1",4)'), inv.index('!memcmp(b+a->logical-4,"AWL1",4)'))
        self.assertIn('AW_AreaEffectsApply();      /* TAKEN-LIGHT-FLAME-61', inv)
        self.assertNotIn('effect-links.awe', inv + self.code('aw_lamps.c'))   # no world-wide file at run time

    def test_a_taken_exterior_light_leaves_the_chim_world_and_its_effects_go(self):
        chunks = self.code('chim/chim_chunks.c')
        self.assertIn('(gone_count && Gone (p->pid))', chunks)
        self.assertIn('gone_count = 0;', chunks)
        host = self.code('aw_mwhost.c')
        self.assertIn('if(!room)room=exterior_hide(reference,1);', host)
        lamps = self.code('aw_lamps.c')
        self.assertIn('if(lamps[i].ref && aw_lamp_gone && aw_lamp_gone(lamps[i].ref))continue;', lamps)
        self.assertIn('aw_lamp_gone=AW_ObjectDisabled;', host)
        torch = self.code('aw_guard_torch.c')
        self.assertIn('flame_link[ordinal]', torch)

    def test_the_image_step_writes_and_checks_them(self):
        image = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("stage_effect_links(boot/'id1', args.data_files, chim_world_data, out)", image)
        self.assertIn("check_image(boot/'id1', args.data_files, out)", image)
        self.assertLess(image.index('stage_effect_links(boot'), image.index('chim_world_held.clear()'))


if __name__ == '__main__':
    unittest.main()
