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

    def test_a_flame_link_must_name_a_frame_map_of_the_image(self):
        # TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61: the engine applies a flame link only on the frame map file it names
        # (its stem's hash); one keyed by the town's server name ("vivec_city" for vivec_city-chim) is never applied
        from prepare_area_tables import name_hash
        world = {'frames': [], 'models': []}
        frame = [{'classname': 'worldspawn', '_chim_frame': '0 -13'}]
        key = L.area_key(lights()[LANTERN])
        good = {key: [(L.KIND_FLAME, 0, name_hash('vivec_city-chim'), LANTERN)]}
        bad = {key: [(L.KIND_FLAME, 0, name_hash('vivec_city'), LANTERN)]}
        with Image({'vivec_city-chim.chim': frame}) as im:
            saved = L.frame_maps
            L.frame_maps = lambda id1: [('vivec_city-chim', frame)]
            try:
                L.check(im.id1, lights(), world, links=good)
                with self.assertRaises(ValueError) as e:
                    L.check(im.id1, lights(), world, links=bad)
            finally:
                L.frame_maps = saved
        self.assertIn('names map hash %#x, which is no frame map of the image' % name_hash('vivec_city'),
                      str(e.exception))


def sub(tag, data):
    data = data.encode('cp1252') + b'\0' if isinstance(data, str) else data
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def record(tag, *subs, flags=0):
    payload = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(payload), 0, flags) + payload


def script(name, text):
    return record('SCPT', sub('SCHD', name.encode('ascii').ljust(32, b'\0') + bytes(20)), sub('SCTX', text.encode('cp1252')))


def cell(x, y, *refs):
    out = [sub('NAME', ''), sub('DATA', struct.pack('<Iii', 0, x, y))]
    for number, ident in refs:
        out += [sub('FRMR', struct.pack('<I', number)), sub('NAME', ident),
                sub('DATA', struct.pack('<6f', x * 8192.0 + 100, y * 8192.0 + 200, 50.0, 0, 0, 0))]
    return record('CELL', *out)


class ScriptedPlacements(unittest.TestCase):
    """OUTDOOR-DISABLE-NOT-HIDDEN-68: an outdoor placement a script can Disable or Enable gets 'P' rows, as a taken
    light does, so the CHIM world hides it. The masters' own forms: a stronghold stage's bare Disable in the script its
    pieces run (strong2_construct), "ex_gg_particles_01"->Disable (the Ghostfence's end), a dialogue result's
    "wolfgiver"->disable on an actor (left out: an actor's edict is hidden), DisablePlayerControls and GetDisabled
    (no switch of an object)."""

    def master(self):
        return b''.join([
            record('TES3', sub('HEDR', bytes(300))),
            record('ACTI', sub('NAME', 'strong_wall_02'), sub('SCRI', 'strong2_construct')),
            record('ACTI', sub('NAME', 'ex_gg_particles_01')),
            record('STAT', sub('NAME', 'plain_rock')),
            record('NPC_', sub('NAME', 'wolfgiver'), sub('SCRI', 'wolfscript')),
            script('strong2_construct', 'Begin strong2_construct\nif ( GetJournalIndex HH_Stronghold < 200 )\n'
                                        '    Disable\nelse\n    Enable\nendif\nEnd\n'),
            script('ghostfencescript', 'Begin ghostfencescript\n"ex_gg_particles_01"->Disable\n'
                                       'DisablePlayerControls\nif ( GetDisabled == 1 )\nendif\nEnd\n'),
            record('INFO', sub('INAM', '1'), sub('BNAM', '"wolfgiver"->disable')),
            cell(-5, -5, (101, 'strong_wall_02'), (102, 'plain_rock'), (103, 'ex_gg_particles_01'),
                 (104, 'wolfgiver'))])

    def test_the_script_tables_name_the_switched_placements(self):
        ids, scripts, kinds, scripted = L.script_targets({'Morrowind.esm': self.master()})
        self.assertEqual(ids, {'ex_gg_particles_01', 'wolfgiver'})
        self.assertEqual(scripts, {'strong2_construct'})               # ghostfencescript: no bare Disable of its own
        self.assertEqual((kinds['wolfgiver'], scripted['strong_wall_02']), ('NPC_', 'strong2_construct'))
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Morrowind.esm').write_bytes(self.master())
            got = L.scripted_placements(tmp)
        from ref_identity import stable_ref
        self.assertEqual(sorted(got), [stable_ref('Morrowind.esm', 101), stable_ref('Morrowind.esm', 103)])
        self.assertEqual(got[stable_ref('Morrowind.esm', 101)]['cell'], (-5, -5))

    def test_a_scripted_piece_gets_its_row_and_the_check_holds_it(self):
        strong, ghost = 101, 103
        scripted = {strong: {'id': 'strong_wall_02', 'master': 'Morrowind.esm', 'interior': False, 'cell': (-5, -5),
                             'position': (0.0, 0.0, 0.0), 'flames': False},
                    ghost: {'id': 'ex_gg_particles_01', 'master': 'Morrowind.esm', 'interior': False, 'cell': (-5, -5),
                            'position': (0.0, 0.0, 0.0), 'flames': False}}
        world = {'frames': [(0, {'cell': (-5, -5)}, [{'owned': [{'pid': 9001, 'ref': strong},
                                                                {'pid': 9002, 'ref': (2 << 24) | strong}]}])],
                 'models': []}
        # the particles: an entity of a frame map (one with no flames of this world's frame)
        frame = [{'classname': 'worldspawn', '_chim_frame': '-6 -5'},
                 {'classname': 'func_wall', 'aw_ref': str(ghost), 'model': '*1'}]
        with Image({'vf0001.chim': frame}) as im:
            rows = L.area_rows(im.id1, world, {}, scripted)
            key = L.area_key(scripted[strong])
            self.assertEqual(rows[key], [(L.KIND_PLACE, 0, 9001, strong), (L.KIND_PLACE, 0, 9002, strong)])
            got = L.check(im.id1, {}, world, links=rows, scripted=scripted)
            self.assertEqual(got['scripted exterior placements'], 2)
            self.assertEqual(got['scripted placements drawn as entities (hidden by their edict)'], 1)
            self.assertEqual(got['scripted targets with no CHIM piece and no entity'], [])
            with self.assertRaises(ValueError) as e:
                L.check(im.id1, {}, world, links={}, scripted=scripted)
            self.assertIn('CHIM placement 9001 of reference %d (strong_wall_02) has no effect link in its cell, so it '
                          'cannot be switched off' % strong, str(e.exception))
            # a target with no piece and no entity is named, a finding
            lone = dict(scripted)
            lone[105] = dict(scripted[ghost], id='lone_piece')
            got = L.check(im.id1, {}, world, links=rows, scripted=lone)
            self.assertEqual(got['scripted targets with no CHIM piece and no entity'], ['105 lone_piece (-5, -5)'])

    def test_an_expansion_piece_of_a_store_of_frames_gets_its_row_under_its_stable_id(self):
        # EXPANSION-STORE-DISABLE-NOT-HIDDEN-68: Solstheim's store of frames numbers Bloodmoon's ice cover in front of
        # Stahlman's Gorge (act_bm_snowdoor4, its own number 33009) as the merged master does, 2 x 2**22 + 33009; the
        # scripted placements key it by its stable id, 2 x 2**20 + 33009. Before, the two were compared as they are and
        # no piece of an expansion's store ever got a row, so its script's Disable hid nothing.
        from ref_identity import stable_ref
        ice = stable_ref('Bloodmoon.esm', 33009)
        merged = (2 << 22) + 33009
        self.assertEqual((ice, merged), (2130161, 8421617))
        scripted = {ice: {'id': 'act_bm_snowdoor4', 'master': 'Bloodmoon.esm', 'interior': False, 'cell': (-27, 26),
                          'position': (-219465.0, 217321.0, -1917.0), 'flames': False}}
        layer = {'frames': [(0, {'cell': (-27, 26)}, [{'owned': [{'pid': 77, 'ref': merged},
                                                                 {'pid': 78, 'ref': (1 << 24) | merged}]}])],
                 'models': []}
        self.assertEqual(L.place_links(layer, scripted), [(77, ice), (78, ice)])
        self.assertEqual(L.placement_ref(merged), ice)
        self.assertEqual(L.placement_ref(225480), 225480)               # a base game number: both forms
        with Image({}) as im:
            rows = L.area_rows(im.id1, None, {}, scripted, layers=[layer])
            self.assertEqual(rows, {L.area_key(scripted[ice]): [(L.KIND_PLACE, 0, 77, ice),
                                                                (L.KIND_PLACE, 0, 78, ice)]})
            got = L.check(im.id1, {}, None, links=rows, scripted=scripted, layers=[layer])
        self.assertEqual(got['scripted exterior placements'], 2)
        self.assertEqual(got['scripted targets with no CHIM piece and no entity'], [])

    def test_the_engine_hides_a_row_by_a_reference_in_either_form(self):
        # EXPANSION-STORE-DISABLE-NOT-HIDDEN-68: the row holds the stable id; a script's Disable names the reference by
        # the merged number (its instance's binding), a take by the stable id: the engine's match and the area-load
        # apply take both, by the same conversion as chim_room.c RoomRefIs and tools/ref_identity.py
        inv = (SRC / 'aw_inventory.c').read_text(encoding='latin-1')
        self.assertIn('static unsigned ref_stable(unsigned r){return r>=(1u<<22) && r<(3u<<22)?((r>>22)<<20)|'
                      '(r&0x3FFFFFu):r;}', inv)
        self.assertIn('static unsigned ref_merged(unsigned r){return r>=(1u<<20) && r<(3u<<20)?((r>>20)<<22)|'
                      '(r&0xFFFFFu):r;}', inv)
        self.assertIn("if(r[0]=='P' && ref_stable((unsigned)focus_u32(r+8))==stable)", inv)
        self.assertIn('if(AW_ObjectDisabled(ref) || (ref_merged(ref)!=ref && AW_ObjectDisabled(ref_merged(ref))))', inv)
        from ref_identity import stable_ref

        def c_stable(r):
            return ((r >> 22) << 20) | (r & 0x3FFFFF) if (1 << 22) <= r < (3 << 22) else r

        def c_merged(r):
            return ((r >> 20) << 22) | (r & 0xFFFFF) if (1 << 20) <= r < (3 << 20) else r
        for master, number in (('Morrowind.esm', 225480), ('Tribunal.esm', 2001), ('Bloodmoon.esm', 33009),
                               ('Bloodmoon.esm', 33635)):
            stable = stable_ref(master, number)
            merged = (['Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'].index(master) << 22) + number
            self.assertEqual((c_stable(merged), c_stable(stable), c_merged(stable)), (stable, stable, merged))

    def test_a_district_piece_goes_into_its_presented_cell(self):
        # Mournhold's districts (MOURNHOLD-EXTERIOR-CELLS-66): an interior cell the build presents outdoors; its pieces
        # are in the store of frames (a layer world) and their rows in the area of the presented block's cell
        import presented_exterior as P
        places = P.receipt_places({'cells': [{'cell': 'Mournhold, Temple Courtyard', 'block': [4, -30], 'size': [2, 2],
                                              'offset': [40000.0, -245000.0]}]})
        tree = 2001
        scripted = {tree: {'id': 'flora_tree_mh_01', 'master': 'Tribunal.esm', 'interior': True,
                           'cell': 'Mournhold, Temple Courtyard', 'position': (100.0, 300.0, 20.0), 'flames': False}}
        layer = {'frames': [(0, {'cell': (4, -30)}, [{'owned': [{'pid': 12, 'ref': tree}]}])], 'models': []}
        with Image({}) as im:
            rows = L.area_rows(im.id1, None, {}, scripted, layers=[layer], places=places)
        grid, _ = P.present_position(places, 'Mournhold, Temple Courtyard', (100.0, 300.0, 20.0))
        self.assertEqual(rows, {L.area_key({'cell': grid}): [(L.KIND_PLACE, 0, 12, tree)]})
        self.assertEqual(grid, (4, -30))
        self.assertEqual(L.placed_outdoors(scripted), {})                # without the presented cells: a room


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
        # TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61: the 'F' links are matched against the loaded frame map file (the
        # world model's stem, the same hash as name_hash; tests/aga_container_strip_open_test.c holds the numbers),
        # never the town's server name, which matched no link in any town
        self.assertIn('AW_AreaMapHash(sv.worldmodel->name)', inv)
        from prepare_area_tables import name_hash
        self.assertEqual(name_hash('vivec_city-chim'), 0x60c9ec7e)
        self.assertNotEqual(name_hash('vivec_city-chim'), name_hash('vivec_city'))
        self.assertNotIn('effect-links.awe', inv + self.code('aw_lamps.c'))   # no world-wide file at run time

    def test_a_taken_exterior_light_leaves_the_chim_world_and_its_effects_go(self):
        chunks = self.code('chim/chim_chunks.c')
        # CHIM-GONE-LIST-64-CAP-68: a bit per placement of the loaded frame, the block's third row (no list, no cap)
        self.assertIn('Hidden (p) || Gone (p->pid) ||', chunks)
        self.assertIn('size = n*sizeof(chim_entry_t) + cells*sizeof(short) + 3*bits;', chunks)
        self.assertNotIn('CHIM_GONE_PIDS', chunks)
        host = self.code('aw_mwhost.c')
        self.assertIn('if(!room)room=exterior_hide(reference,1);', host)
        # every piece of the reference, as its rows name it: no array of pieces (pids[16] before)
        self.assertIn('return AW_AreaEffectHide(ref,hide);', host)
        self.assertNotIn('pids[16]', host)
        lamps = self.code('aw_lamps.c')
        self.assertIn('if(lamps[i].ref && aw_lamp_gone && aw_lamp_gone(lamps[i].ref))continue;', lamps)
        self.assertIn('aw_lamp_gone=AW_ObjectDisabled;', host)
        torch = self.code('aw_guard_torch.c')
        self.assertIn('flame_link[ordinal]', torch)

    def test_the_image_step_writes_and_checks_them(self):
        image = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("stage_effect_links(boot/'id1', args.data_files, chim_world_data, out, layers=effect_link_layers(args),",
                      image)
        # OUTDOOR-DISABLE-NOT-HIDDEN-68: every store of frames the image installs (Solstheim's, Mournhold's districts)
        # gives its rows in the same call, and the districts by their presented cells
        self.assertIn("places=presented_places(args)[0])", image)
        self.assertIn("out += [str(world) for store, world in parse(values) if kinds.get(store) == 'frames']", image)
        self.assertIn("out.append(str(args.chim_sol_world))", image)
        self.assertIn("check_image(boot/'id1', args.data_files, out)", image)
        self.assertLess(image.index('stage_effect_links(boot'), image.index('chim_world_held.clear()'))


if __name__ == '__main__':
    unittest.main()
