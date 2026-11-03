"""The focus box (FOCUS-BOX-58): the framed box with an aimed item's name, weight and value, shown only within
the game's activation distance (GMST iMaxActivateDist from the game data, through gfx/hud-settings.txt).

Synthetic settings only; no game data is read here.
"""
import re, struct, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import prepare_icons as icons

SRC = ROOT / 'engine/aga/src'


def body(text, signature):
    start = text.index(signature)
    depth = 0
    for i in range(text.index('{', start), len(text)):
        depth += {'{': 1, '}': -1}.get(text[i], 0)
        if not depth:
            return text[start:i + 1]
    raise ValueError(signature)


class BuilderSettingsTests(unittest.TestCase):
    BASE = {'fmagicitemrechargepersecond': .05}

    def test_activation_distance_and_labels_come_from_the_gmsts(self):
        text, info = icons.hud_settings(dict(self.BASE, imaxactivatedist=192, sweight='Weight', svalue='Value',
                                             stake='Take'))
        lines = text.splitlines()
        self.assertIn('sTake Take', lines)   # STEAL-PROMPT-58
        self.assertIn('iMaxActivateDist 192', lines)
        self.assertIn('sWeight Weight', lines)
        self.assertIn('sValue Value', lines)
        self.assertEqual(info['activate_distance'], 192)

    def test_a_missing_or_odd_setting_writes_no_line(self):
        for odd in ({}, {'imaxactivatedist': 0}, {'imaxactivatedist': 1.5}, {'sweight': 'bad\nline'}):
            text, _ = icons.hud_settings(dict(self.BASE, **odd))
            self.assertNotIn('iMaxActivateDist', text)
            self.assertNotIn('sWeight', text)

    def test_the_inventory_import_keeps_the_label_strings(self):
        source = (ROOT / 'tools/prepare_inventory.py').read_text(encoding='utf-8')
        self.assertRegex(source, r"'sweight'\s*,\s*'svalue'")


def sub(tag, data):
    return tag.encode() + struct.pack('<I', len(data)) + data


def rec(tag, *subs, flags=0):
    body = b''.join(subs)
    return tag.encode() + struct.pack('<III', len(body), 0, flags) + body


def z(text):
    return text.encode('cp1252') + b'\0'


def ref(number, ident, pos, *extra):
    return (sub('FRMR', struct.pack('<I', number)) + sub('NAME', z(ident)) + b''.join(extra) +
            sub('DATA', struct.pack('<6f', *pos, 0, 0, 0)))


class FocusTableTests(unittest.TestCase):
    """tools/prepare_focus.py on a hand-made master (no game data)."""
    MASTER = b''.join([
        rec('WEAP', sub('NAME', z('test_dagger')), sub('FNAM', z('Test Dagger')),
            sub('WPDT', struct.pack('<fih', 3.0, 10, 0) + b'\0' * 22)),
        rec('MISC', sub('NAME', z('test_cup')), sub('FNAM', z('Cup')), sub('MCDT', struct.pack('<fii', .5, 2, 0))),
        rec('LIGH', sub('NAME', z('wall_lamp')), sub('FNAM', z('Lamp')), sub('LHDT', struct.pack('<fiiiBBBBi', 1, 1, 1, 64, 0, 0, 0, 0, 0))),
        rec('NPC_', sub('NAME', z('clerk')), sub('FNAM', z('A Clerk'))),
        rec('DOOR', sub('NAME', z('door_a')), sub('FNAM', z('Wooden Door'))),
        rec('CELL', sub('NAME', z('Test Office')), sub('DATA', struct.pack('<Iii', 1, 0, 0)),
            ref(10, 'test_dagger', (1, 2, 3)),
            ref(11, 'test_cup', (4, 5, 6), sub('ANAM', z('clerk'))),
            ref(12, 'wall_lamp', (0, 0, 0)),
            ref(13, 'clerk', (7, 8, 9)),
            ref(14, 'door_a', (0, 0, 0), sub('DODT', b'\0' * 24), sub('DNAM', z('Outside Place'))),
            ref(15, 'test_cup', (0, 0, 0), sub('DELE', b'\0\0\0\0')),
            ref(16, 'door_a', (0, 0, 0), sub('DODT', struct.pack('<6f', 9000, 9000, 0, 0, 0, 0))),
            ref(17, 'door_a', (0, 0, 0), sub('DODT', struct.pack('<6f', -100, 9000, 0, 0, 0, 0)))),
        rec('REGN', sub('NAME', z('ascadian isles region')), sub('FNAM', z('Ascadian Isles Region'))),
        rec('CELL', sub('NAME', z('Somewhere')), sub('DATA', struct.pack('<Iii', 0, 1, 1)),
            ref(20, 'test_dagger', (9000, 9000, 0))),
        rec('CELL', sub('NAME', z('')), sub('DATA', struct.pack('<Iii', 0, -1, 1)),
            sub('RGNN', z('Ascadian Isles Region')), ref(21, 'clerk', (-100, 9000, 0))),
    ])

    def test_rows_of_a_room(self):
        import prepare_focus as focus
        rooms = focus.placements(self.MASTER, focus.objects_of(self.MASTER), {'test office': 7})
        rows = {r[2]: r for r in rooms[7]}
        self.assertEqual(sorted(rows), [10, 11, 13, 14, 16, 17])   # the fixed lamp and the deleted cup are left out
        self.assertEqual(rows[10][:2] + rows[10][6:10], ('I', 0, 3.0, 10, 'Test Dagger', 'test_dagger'))
        # STEAL-PROMPT-58: the action code: take (1), +4 when owned; an actor talks (3), a door has none
        self.assertEqual((rows[10][10], rows[11][10], rows[13][10], rows[14][10]), (1, 1 | 4, 3, 0))
        self.assertEqual(rows[13][9], '')                       # only items carry a record id
        self.assertEqual(rows[11][1], 1)                        # an owner on the placement: theft
        self.assertEqual(rows[13][0] + rows[13][8], 'AA Clerk')
        self.assertEqual(rows[14][0] + rows[14][8], 'DOutside Place')   # a door says where it leads
        self.assertEqual(rows[16][8], 'Somewhere')              # outside: the exterior cell's name
        self.assertEqual(rows[17][8], 'Ascadian Isles Region')  # an unnamed cell: its region's name

    def test_exterior_cells_are_keyed_by_grid(self):
        import prepare_focus as focus
        rooms = focus.placements(self.MASTER, focus.objects_of(self.MASTER), {'test office': 7})
        self.assertEqual(sorted(rooms), [7, focus.exterior_key(-1, 1), focus.exterior_key(1, 1)])
        self.assertEqual([r[2] for r in rooms[focus.exterior_key(1, 1)]], [20])
        self.assertEqual([r[2] for r in rooms[focus.exterior_key(-1, 1)]], [21])
        self.assertGreaterEqual(focus.exterior_key(-2047, -2047), 0x80000000)   # above every room number
        self.assertEqual(focus.exterior_key(1, 1), 0x80000000 | 2049 << 12 | 2049)

    def test_engine_uses_the_same_exterior_key(self):
        inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
        key = body(inventory, 'static unsigned long focus_exterior_key(')
        self.assertIn('0x80000000ul', key)
        self.assertIn('<<12', key)
        self.assertRegex(inventory, r'#define FOCUS_GRID_BIAS 2048\b')
        self.assertRegex(inventory, r'#define FOCUS_CELL 8192\.0f')
        load = body(inventory, 'static void focus_load(void)')
        # outdoor rows in this map's own units: the region table, else the loaded CHIM frame
        # (PLACED-ITEMS-OUTDOORS-FIRST-FRAME-59)
        self.assertIn('focus_to_local(', load)
        convert = body(inventory, 'static int focus_to_local(')
        self.assertIn('AW_SourceToWorld(', convert)       # the shared conversion: region table, then the CHIM frame
        self.assertIn('dx<=1', load)                              # the player's cell and its neighbours only

    def test_books_are_read_and_magic_scrolls_are_taken(self):
        """STEAL-PROMPT-58: a BOOK without an enchantment is read (2, +4 owned); one with an enchantment (a magic
        scroll) is taken like any item (1) with the scroll bit (8)."""
        import prepare_focus as focus
        master = b''.join([
            rec('BOOK', sub('NAME', z('bk_note')), sub('FNAM', z('A Note')), sub('BKDT', struct.pack('<fiiii', 1, 5, 1, -1, 0))),
            rec('BOOK', sub('NAME', z('sc_fire')), sub('FNAM', z('Scroll of Fire')),
                sub('BKDT', struct.pack('<fiiii', .2, 80, 1, -1, 0)), sub('ENAM', z('fire_en'))),
            rec('CELL', sub('NAME', z('Library')), sub('DATA', struct.pack('<Iii', 1, 0, 0)),
                ref(30, 'bk_note', (0, 0, 0)), ref(31, 'bk_note', (0, 0, 0), sub('ANAM', z('clerk'))),
                ref(32, 'sc_fire', (0, 0, 0)), ref(33, 'sc_fire', (0, 0, 0), sub('ANAM', z('clerk'))))])
        rows = {r[2]: r[10] for r in focus.placements(master, focus.objects_of(master), {'library': 3})[3]}
        self.assertEqual(rows, {30: focus.ACT_READ, 31: focus.ACT_READ | focus.ACT_OWNED,
                                32: focus.ACT_TAKE | focus.ACT_MAGIC_SCROLL,
                                33: focus.ACT_TAKE | focus.ACT_MAGIC_SCROLL | focus.ACT_OWNED})

    def test_owner_of_an_owned_item(self):
        """CELL-CHANGES-59 slice 2: whom an owned item is stolen from: the placement's owner (ANAM), else its owning
        faction (CNAM); an unowned item or a thing that is no item has none. The list after the rows (AWF3)."""
        import prepare_focus as focus
        rows = {r[2]: r for r in focus.placements(self.MASTER, focus.objects_of(self.MASTER), {'test office': 7})[7]}
        self.assertEqual(rows[11][11], ('clerk', 0))
        self.assertIsNone(rows[10][11])
        self.assertIsNone(rows[13][11])
        self.assertEqual(focus.owner_of({'CNAM': z('Hlaalu')}), ('hlaalu', 1))
        self.assertEqual(focus.owner_of({'ANAM': z('Fargoth'), 'CNAM': z('Hlaalu')}), ('fargoth', 0))
        self.assertIsNone(focus.owner_of({'ANAM': z('x' * 33)}))
        tail = focus.owner_list({20: ('fargoth', 0), 10: ('hlaalu', 1), 30: ('fargoth', 0)})
        self.assertEqual(tail[:8], b'AWO1' + struct.pack('<I', 3))
        entries = [struct.unpack_from('<IHBB', tail, 8 + 8 * i) for i in range(3)]
        self.assertEqual([e[0] for e in entries], [10, 20, 30])                # ascending reference
        self.assertEqual(entries[1][1], entries[2][1])                          # one pool entry per owner
        pool_size = struct.unpack_from('<I', tail, 32)[0]
        pool = tail[36:]
        self.assertEqual(len(pool), pool_size)
        self.assertEqual(pool[entries[0][1]:].split(b'\0')[0], b'hlaalu')
        self.assertEqual(entries[0][2], 1)

    def test_engine_reads_the_owner_list(self):
        import prepare_focus as focus
        inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
        self.assertIn('"AWF3"', inventory)
        owner = body(inventory, 'static int placed_owner(unsigned reference,char *owner,int *faction)')
        self.assertIn('"AWO1"', owner)
        self.assertIn('pool=focus_u32(b))<=%d' % focus.OWNER_POOL, owner)
        self.assertIn("b'AWF3'", (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))
        self.assertEqual(focus.OWNER_ID, 32)
        self.assertRegex((SRC / 'aw_ledger.h').read_text(encoding='utf-8'), r'#define AW_LEDGER_STOLEN_ID 32\b')

    def test_containers_and_their_contents(self):
        """CELL-CHANGES-59 slice 3: a placed container is a 'C' row (owned like an item); its record's NPCO list goes
        into the contents list after the owners list (a restocking count made positive, a levelled list left out)."""
        import prepare_focus as focus

        def npco(count, ident):
            return sub('NPCO', struct.pack('<i', count) + ident.encode('ascii').ljust(32, b'\0'))
        master = self.MASTER + b''.join([
            rec('LEVI', sub('NAME', z('l_loot'))),
            rec('CONT', sub('NAME', z('chest_a')), sub('FNAM', z('Chest')), npco(2, 'test_cup'), npco(-3, 'test_dagger'),
                npco(1, 'l_loot')),
            rec('CELL', sub('NAME', z('Store')), sub('DATA', struct.pack('<Iii', 1, 0, 0)),
                ref(40, 'chest_a', (1, 1, 1), sub('ANAM', z('clerk'))), ref(41, 'chest_a', (2, 2, 2)))])
        objects = focus.objects_of(master)
        self.assertEqual(objects['chest_a'][0], 'C')
        self.assertEqual(objects['chest_a'][5:], ([('test_cup', 2), ('test_dagger', 3)], 3))
        rows = {r[2]: r for r in focus.placements(master, objects, {'store': 9})[9]}
        self.assertEqual((rows[40][0], rows[40][1], rows[40][11]), ('C', 1, ('clerk', 0)))
        self.assertEqual(rows[41][1], 0)
        tail = focus.contents_list({41: rows[41][12], 40: rows[40][12]})
        self.assertEqual(tail[:8], b'AWC1' + struct.pack('<I', 2))
        self.assertEqual(struct.unpack_from('<IIHBB', tail, 8), (40, 0, 2, 3, 0))
        self.assertEqual(struct.unpack_from('<IIHBB', tail, 20), (41, 2, 2, 3, 0))
        self.assertEqual(struct.unpack_from('<I', tail, 32)[0], 4)
        self.assertEqual(tail[36:68].rstrip(b'\0'), b'test_cup')
        self.assertEqual(struct.unpack_from('<i', tail, 68)[0], 2)
        inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
        # CONTAINER-STRIP-TAKE-STALL-59: the file reader is container_base_read (container_base serves a held container)
        self.assertIn('"AWC1"', body(inventory, 'static int container_base_read('))
        self.assertIn("row[0]!='C'", inventory)

    def test_container_opens_or_is_harvested_and_carries_its_lock(self):
        """CONTAINER-WINDOW-59: a container's row action 1 opens it (+4 owned); an organic one (CONT FLAG bit 0,
        flora) has none and flag 4 on its contents; the row's byte 3 is the placement's lock level (FLTV, 0..100)."""
        import prepare_focus as focus
        master = self.MASTER + b''.join([
            rec('CONT', sub('NAME', z('basket_a')), sub('FNAM', z('Basket')), sub('FLAG', struct.pack('<I', 8))),
            rec('CONT', sub('NAME', z('flora_a')), sub('FNAM', z('Wickwheat')), sub('FLAG', struct.pack('<I', 1 | 2))),
            rec('CELL', sub('NAME', z('Store')), sub('DATA', struct.pack('<Iii', 1, 0, 0)),
                ref(50, 'basket_a', (1, 1, 1)), ref(51, 'basket_a', (1, 1, 1), sub('ANAM', z('clerk')),
                                                     sub('FLTV', struct.pack('<i', 50))),
                ref(52, 'flora_a', (1, 1, 1)), ref(53, 'basket_a', (1, 1, 1), sub('FLTV', struct.pack('<i', 400))))])
        objects = focus.objects_of(master)
        self.assertEqual(objects['basket_a'][4], focus.ACT_TAKE)
        self.assertEqual((objects['flora_a'][4], objects['flora_a'][6] & focus.CFLAG_ORGANIC), (focus.ACT_NONE, 4))
        rows = {r[2]: r for r in focus.placements(master, objects, {'store': 9})[9]}
        self.assertEqual([(rows[k][10], rows[k][13]) for k in (50, 51, 52, 53)],
                         [(1, 0), (1 | focus.ACT_OWNED, 50), (0, 0), (1, 100)])
        tail = focus.contents_list({52: rows[52][12]})
        self.assertEqual(struct.unpack_from('<IIHBB', tail, 8)[3], 4)
        inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
        self.assertIn("r->lock=(unsigned char)(row[0]=='C' && row[3]<=100?row[3]:0);", inventory)
        self.assertIn("return container_open(&focus_rows[best]);", body(inventory, 'static int placed_use(void)'))
        self.assertIn('AW_CStripInit();', (SRC / 'aw_placed.c').read_text(encoding='utf-8'))
        strip = (SRC / 'aw_cstrip.c').read_text(encoding='utf-8')
        self.assertIn('AW_TryMalloc(sizeof(strip_t))', strip)        # allocated on open only
        self.assertIn('free(strip)', strip)                          # and freed on close
        self.assertIn('AW_ContainerTake(strip->reference', strip)     # the deltas, never a copy
        self.assertIn('AW_ContainerPut(strip->reference', strip)

    def test_row_layout(self):
        import prepare_focus as focus
        self.assertEqual(struct.calcsize('<BBBBIiiifi') + focus.NAME + focus.IDENT, focus.ROW)
        self.assertEqual(focus.record_id('test_dagger'), b'test_dagger' + b'\0' * 21)
        self.assertEqual(focus.record_id('x' * 33), b'\0' * 32)   # would not fit whole: none
        self.assertEqual(focus.record_id(''), b'\0' * 32)


class PickupTests(unittest.TestCase):
    """PICKUP-PLACED-58: the activate key takes an aimed placed item; it leaves the world through the object state."""
    inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
    host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
    room = (SRC / 'chim/chim_room.c').read_text(encoding='utf-8')

    def test_engine_reads_the_row_layout_the_builder_writes(self):
        import prepare_focus as focus
        self.assertRegex(self.inventory, r'#define FOCUS_ROW2 %d\b' % focus.ROW)
        self.assertRegex(self.inventory, r'#define FOCUS_ID %d\b' % focus.IDENT)
        self.assertIn('"AWF2"', self.inventory)
        self.assertIn('"AWF1"', self.inventory)               # an older table still shows the box

    def test_use_takes_a_placed_item(self):
        use = body(self.inventory, 'int AW_InventoryUse(void)')
        self.assertIn('placed_use()', use)
        use = body(self.inventory, 'static int placed_use(void)')
        self.assertIn("kind!='I'", use)                       # actors and doors are not taken
        self.assertIn('return take_row(row);', use)
        # the take itself, shared with the book reader's Take (BOOK-READER-58)
        take = body(self.inventory, 'static int take_row(focus_row_t *row)')
        self.assertIn('AW_InventoryRead(id,&item)', take)
        self.assertIn('AW_ObjectTake(row->reference,row->owned)', take)
        self.assertIn('AW_ItemAdd(&aw_state,item.id,-1)', take)   # nothing hidden: the item is given back

    def test_room_items_count_only_when_drawn(self):
        # a compiled room that leaves the small items out shows no box for them (INTERIOR-PLACED-ITEMS-47)
        load = body(self.inventory, 'static void focus_load(void)')
        self.assertIn('ChimRoom_Has(focus_rows[j].reference)', load)
        self.assertIn('focus_rows[j].live=1', load)

    def test_taken_state_is_the_saved_object_state(self):
        take = body(self.host, 'int AW_ObjectTake(unsigned int reference,int stolen)')
        self.assertIn('o->disabled=1', take)                  # saved as AW_CHANGE_DISABLED, hidden at every map
        self.assertIn('o->stolen=', take)
        self.assertIn('ChimRoom_Hide(reference,1)', take)
        hide = body(self.host, 'static void object_hide(object_t *o)')
        self.assertIn('ChimRoom_Hide(o->ref,1)', hide)
        show = body(self.host, 'static void object_show(object_t *o)')
        self.assertIn('ChimRoom_Hide(o->ref,0)', show)

    def test_taken_items_stay_taken_with_the_scripts_off(self):
        # PICKUP-E-OWNED-NO-TAKE-58: the take found its edict only through the table the scripts' attach built, so
        # with the scripts off or refused (every dev build since the dialogue result scripts) E took nothing. The
        # edicts by reference and the hiding of taken items now attach on every map before the scripts' switch.
        tick = body(self.host, 'void AW_MwscriptTick(float dt)')
        self.assertLess(tick.index('attach_objects();'), tick.index('if(!mwscript.value)'))
        self.assertLess(tick.index('if(!mwscript.value)'), tick.index('if(!load())return;'))
        self.assertLess(tick.index('if(!load())return;'), tick.index('attach_map();'))
        objects = body(self.host, 'static void attach_objects(void)')
        self.assertIn('"aw_ref"', objects)
        self.assertIn('object_hide(&objects[i])', objects)
        attach = body(self.host, 'static void attach_map(void)')
        self.assertNotIn('object_hide(', attach)               # hidden once per map, never twice
        self.assertNotIn('edict_ref_count=0', attach)

    def test_room_skips_hidden_placements(self):
        link = body(self.room, 'void ChimRoom_Link (void)')
        self.assertIn('.linked)', link)
        clip = body(self.room, 'void ChimRoom_Clip (')
        self.assertIn('if (!p->linked)', clip)
        hide = body(self.room, 'int ChimRoom_Hide (unsigned reference, int hide)')
        self.assertIn('R_RemoveEfrags', hide)
        self.assertIn('ROOM_SOURCE_MASK', hide)               # every cut piece of the reference


class EngineTests(unittest.TestCase):
    inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
    scene = (SRC / 'aw_scene.c').read_text(encoding='utf-8')
    ui = (SRC / 'aw_ui.c').read_text(encoding='utf-8')

    def test_reach_is_the_gmst_at_map_scale(self):
        reach = body(self.inventory, 'float AW_ActivateDistance(void)')
        self.assertIn('"iMaxActivateDist"', reach)
        self.assertIn('0.25f', reach)                       # game units to map units (aw_mwhost.c to_game_units)
        target = body(self.inventory, 'static int inv_target(void)')
        self.assertIn('AW_ActivateDistance()', target)
        self.assertNotRegex(target, r'distance=50\b')         # no number of our own
        self.assertIn('DotProduct(delta,delta)>distance*distance', target)   # out of range: no box

    def test_box_has_name_weight_and_value(self):
        focus = body(self.inventory, 'int AW_InventoryFocus(')
        self.assertIn('"sWeight"', focus)
        self.assertIn('"sValue"', focus)
        self.assertIn('item.weight', focus)
        self.assertIn('item.value', focus)
        # the aimed drop of either store: the world change list's (CELL-CHANGES-59) or the old fixed table's
        self.assertIn('drop_aimed()', focus)
        self.assertIn('return aw_ledger_on?ledger_target():inv_target();', self.inventory)

    def test_scene_draws_the_framed_box(self):
        draw = body(self.scene, 'void AW_SceneDraw(void)')
        self.assertIn('AW_InventoryFocus(', draw)
        self.assertIn('AW_PlacedFocus(', draw)                 # placed items and doors
        self.assertIn('AW_UIFocusBox(', draw)
        # FOCUS-BOX-NO-ACTORS-58: no box for a creature or a person (their name shows under the view)
        self.assertEqual(draw.count('AW_UIFocusBox('), 1)
        self.assertIn('if(!driver && !npc_hint() &&', draw)
        self.assertNotIn('person->v.netname', draw)
        placed = body(self.inventory, 'int AW_PlacedFocus(')
        self.assertIn("kind=='A')return 0;", placed)
        box = body(self.ui, 'void AW_UIFocusBox(')
        self.assertIn('AW_UIBox(', box)                      # the shared framed box
        self.assertIn('owned?red', box.replace(' ', ''))     # theft colour on the name

    def test_weight_text_drops_trailing_zeros(self):
        self.assertTrue(re.search(r'static void weight_text\(', self.inventory))


if __name__ == '__main__':
    unittest.main()
