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

    def test_a_long_door_name_continues_in_the_id_field(self):
        # INFO-BOX-TEXT-CUT-62: "Suran, Ibarnadad Assimarari: Apothecary" and "Seyda Neen, Census and Excise Office"
        # filled the 36-byte name field and were cut ("...Apoth", "...Offic"); a door's name goes on in its row's id field
        import prepare_focus as focus
        for name in ('Suran, Ibarnadad Assimarari: Apothecary', 'Seyda Neen, Census and Excise Office',
                     'A' * 66, 'B' * 35, 'Vivec, Hall of Wisdom'):
            packed = focus.pack_name_and_id('D', name, '')
            self.assertEqual(len(packed), focus.NAME + focus.IDENT)
            head = packed[:focus.NAME].split(b'\0', 1)[0]
            tail = packed[focus.NAME:].split(b'\0', 1)[0]
            self.assertEqual((head + tail).decode('cp1252'), name)         # the engine's join gives the whole name
            self.assertLessEqual(len(head), focus.NAME - 1)
            if len(name) <= focus.NAME - 1:
                self.assertEqual(tail, b'')                                  # a short name leaves the id field empty
        # more than the two fields hold is cut at 66 bytes, never past the row
        self.assertEqual(len(focus.pack_name_and_id('D', 'C' * 90, '')), focus.NAME + focus.IDENT)
        self.assertEqual((focus.pack_name_and_id('D', 'C' * 90, '')[:focus.NAME].rstrip(b'\0') +
                          focus.pack_name_and_id('D', 'C' * 90, '')[focus.NAME:].rstrip(b'\0')), b'C' * 66)
        # items, containers and actors keep the old fields: a long item name is cut at 35, its id stays in the id field
        packed = focus.pack_name_and_id('I', 'I' * 50, 'misc_cup')
        self.assertEqual(packed[:focus.NAME].rstrip(b'\0'), b'I' * 35)
        self.assertEqual(packed[focus.NAME:].rstrip(b'\0'), b'misc_cup')
        self.assertEqual(focus.pack_name_and_id('A', 'N' * 50, '')[focus.NAME:], b'\0' * focus.IDENT)
        # the engine joins them, and an old file (no tail) reads as before
        inventory = (ROOT/'engine/aga/src/aw_inventory.c').read_text(encoding='utf-8')
        self.assertIn("row[0]=='D' && strlen(r->name)==FOCUS_NAME_FIELD-1 && row[FOCUS_ROW]", inventory)
        self.assertIn('#define FOCUS_NAME_LONG (FOCUS_NAME_FIELD-1+FOCUS_ID-1)', inventory)

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
        scroll) is taken like any item (1) with the scroll bit (8). BLANK-PAPER-READ-60: a BOOK with no words (no
        TEXT, as sc_paper plain, or only markup) is taken like any item (1), never read."""
        import prepare_focus as focus
        master = b''.join([
            rec('BOOK', sub('NAME', z('bk_note')), sub('FNAM', z('A Note')), sub('BKDT', struct.pack('<fiiii', 1, 5, 1, -1, 0)),
                sub('TEXT', b'<DIV ALIGN="LEFT">Keep out.<BR>')),
            rec('BOOK', sub('NAME', z('sc_fire')), sub('FNAM', z('Scroll of Fire')),
                sub('BKDT', struct.pack('<fiiii', .2, 80, 1, -1, 0)), sub('ENAM', z('fire_en'))),
            rec('BOOK', sub('NAME', z('sc_paper plain')), sub('FNAM', z('paper')), sub('BKDT', struct.pack('<fiiii', 1, 3, 1, -1, 50))),
            rec('BOOK', sub('NAME', z('bk_markup')), sub('FNAM', z('Empty Page')), sub('BKDT', struct.pack('<fiiii', 1, 3, 0, -1, 0)),
                sub('TEXT', b'<DIV ALIGN="CENTER"><BR>\r\n&nbsp;<BR>\x00')),
            rec('CELL', sub('NAME', z('Library')), sub('DATA', struct.pack('<Iii', 1, 0, 0)),
                ref(30, 'bk_note', (0, 0, 0)), ref(31, 'bk_note', (0, 0, 0), sub('ANAM', z('clerk'))),
                ref(32, 'sc_fire', (0, 0, 0)), ref(33, 'sc_fire', (0, 0, 0), sub('ANAM', z('clerk'))),
                ref(34, 'sc_paper plain', (0, 0, 0)), ref(35, 'sc_paper plain', (0, 0, 0), sub('ANAM', z('clerk'))),
                ref(36, 'bk_markup', (0, 0, 0)))])
        rows = {r[2]: r[10] for r in focus.placements(master, focus.objects_of(master), {'library': 3})[3]}
        self.assertEqual(rows, {30: focus.ACT_READ, 31: focus.ACT_READ | focus.ACT_OWNED,
                                32: focus.ACT_TAKE | focus.ACT_MAGIC_SCROLL,
                                33: focus.ACT_TAKE | focus.ACT_MAGIC_SCROLL | focus.ACT_OWNED,
                                34: focus.ACT_TAKE, 35: focus.ACT_TAKE | focus.ACT_OWNED, 36: focus.ACT_TAKE})
        self.assertFalse(focus.book_has_words(b'') or focus.book_has_words(None))
        self.assertTrue(focus.book_has_words(b'<BR>A<BR>'))
        self.assertTrue(focus.book_has_words(b'<DIV><IMG SRC="bm_stonemap.tga" WIDTH="256"><BR>'))   # a picture page

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
        self.assertEqual(objects['chest_a'][5:7], ([('test_cup', 2), ('test_dagger', 3)], 3))
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
        """CONTAINER-WINDOW-59: a container's row action 1 opens it (+4 owned); an organic one (CONT FLAG bit 0) keeps
        flag 4 on its contents and is picked in the world (no action) only when its model is a harvest kind (the small
        mushrooms, the bracket fungi); FARGOTH-STASH-STUMP-69: every other organic container opens its window, as in
        the original and OpenMW (a wickwheat plant, Fargoth's hollow treestump; before, none opened); the row's byte 3
        is the placement's lock level (FLTV, 0..100)."""
        import prepare_focus as focus
        master = self.MASTER + b''.join([
            rec('CONT', sub('NAME', z('basket_a')), sub('FNAM', z('Basket')), sub('FLAG', struct.pack('<I', 8))),
            rec('CONT', sub('NAME', z('flora_a')), sub('FNAM', z('Wickwheat')), sub('MODL', z('o\\flora_wickwheat_01.nif')),
                sub('FLAG', struct.pack('<I', 1 | 2))),
            rec('CONT', sub('NAME', z('flora_treestump_unique')), sub('FNAM', z('Hollow Treestump')),
                sub('MODL', z('f\\flora_treestump_wg_01.nif')), sub('FLAG', struct.pack('<I', 1))),
            rec('CONT', sub('NAME', z('flora_bc_mushroom_a')), sub('FNAM', z('Luminous Russula')),
                sub('MODL', z('f\\flora_bc_mushroom_01.nif')), sub('FLAG', struct.pack('<I', 1 | 2))),
            rec('CELL', sub('NAME', z('Store')), sub('DATA', struct.pack('<Iii', 1, 0, 0)),
                ref(50, 'basket_a', (1, 1, 1)), ref(51, 'basket_a', (1, 1, 1), sub('ANAM', z('clerk')),
                                                     sub('FLTV', struct.pack('<i', 50))),
                ref(52, 'flora_a', (1, 1, 1)), ref(53, 'basket_a', (1, 1, 1), sub('FLTV', struct.pack('<i', 400))),
                ref(54, 'flora_bc_mushroom_a', (1, 1, 1)), ref(55, 'flora_treestump_unique', (1, 1, 1)))])
        objects = focus.objects_of(master)
        self.assertEqual(objects['basket_a'][4], focus.ACT_TAKE)
        # PLANT-PICK-DIRECT-DEFAULT-69: the plant opens (its window under the Original value) and carries the AmiWind
        # pick's bit; Fargoth's treestump, a stash, opens and has none
        self.assertEqual((objects['flora_a'][4], objects['flora_a'][6] & focus.CFLAG_ORGANIC),
                         (focus.ACT_TAKE | focus.PLANT_PICK['pick'], 4))
        self.assertEqual(objects['flora_treestump_unique'][4], focus.ACT_TAKE)
        self.assertEqual((objects['flora_bc_mushroom_a'][4], objects['flora_bc_mushroom_a'][6] & focus.CFLAG_ORGANIC),
                         (focus.ACT_NONE, 4))
        self.assertTrue(focus.harvest_picked('f\\flora_bc_shelffungus_01.nif'))
        self.assertFalse(focus.harvest_picked('o\\flora_comberry_01.nif'))
        rows = {r[2]: r for r in focus.placements(master, objects, {'store': 9})[9]}
        self.assertEqual([(rows[k][10], rows[k][13]) for k in (50, 51, 52, 53, 54, 55)],
                         [(1, 0), (1 | focus.ACT_OWNED, 50), (1 | focus.PLANT_PICK['pick'], 0), (1, 100), (0, 0), (1, 0)])
        tail = focus.contents_list({52: rows[52][12]})
        self.assertEqual(struct.unpack_from('<IIHBB', tail, 8)[3], 4)
        inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
        self.assertIn("r->lock=(unsigned char)(row[0]=='C' && row[3]<=100?row[3]:0);", inventory)
        # PRISON-SHIP-ITEMS-TAKEABLE-65: once the Inventory window is allowed (tests/test_activate.py)
        self.assertIn("return inventory_allowed()?container_open(&focus_rows[best]):1;",
                      body(inventory, 'static int placed_use(void)'))
        self.assertIn('AW_CStripInit();', (SRC / 'aw_placed.c').read_text(encoding='utf-8'))
        strip = (SRC / 'aw_cstrip.c').read_text(encoding='utf-8')
        self.assertIn('AW_TryMalloc(sizeof(strip_t))', strip)        # allocated on open only
        self.assertIn('free(strip)', strip)                          # and freed on close
        self.assertIn('AW_ContainerTake(strip->reference', strip)     # the deltas, never a copy
        self.assertIn('AW_ContainerPut(strip->reference', strip)

    # PLANT-PICK-DIRECT-DEFAULT-69: every organic container of the three masters without the respawn flag (32 records),
    # and the two that respawn but are supply chests, with what the AmiWind pick does with it: 'pick' (one press, shown
    # picked), 'keep' (one press, stays drawn: the ore and gem rocks) or 'window' (a stash or supply barrel or chest: its
    # window under both values). The respawn flag alone does not tell them apart: the egg sacks, rocks, kollops and the
    # Horn Lily do not respawn, the guild supply chests do. Counted on the masters' CONT records and placements,
    # 27 November 2026: 140 organic records, 12 the harvest's (the small mushrooms and bracket fungi, 2,945
    # placements), 101 picked (22,502), 22 picked and kept drawn (234), 5 windows (14).
    ORGANIC_NOT_RESPAWNING = dict({
        'barrel_01_ahnassi_drink': ('o\\contain_barrel_01.nif', 'window'),
        'barrel_01_ahnassi_food': ('o\\contain_barrel_01.nif', 'window'),
        'cavern_spore00': ('o\\contain_cavern_spore00.nif', 'pick'),
        'egg_kwama00': ('o\\contain_egg_kwama00.nif', 'pick'),
        'flora_bc_fern_04_chuck': ('f\\flora_bc_fern_04.nif', 'pick'),
        'flora_plant_01': ('o\\flora_plant_01.nif', 'pick'),
        'flora_treestump_unique': ('f\\flora_treestump_wg_01.nif', 'window'),
        'kollop_01': ('f\\furn_shell00.nif', 'pick'),
        'kollop_02': ('f\\furn_shell10.nif', 'pick'),
        'kollop_03': ('f\\furn_shell20.nif', 'pick'),
        'rock_adam_py09': ('i\\contain_rock_apy_09.nif', 'keep')},
        **{'rock_%s_%02d' % (kind, n): ('o\\contain_rock_%s_%02d.nif' % (kind, n), 'keep')
           for kind in ('diamond', 'ebony', 'glass') for n in range(1, 8)})
    ORGANIC_RESPAWNING_STASHES = {'com_chest_02_fg_supply': ('o\\contain_com_chest_02.nif', 'window'),
                                  'com_chest_02_mg_supply': ('o\\contain_com_chest_02.nif', 'window')}

    def test_plants_are_picked_and_stashes_keep_their_window(self):
        """PLANT-PICK-DIRECT-DEFAULT-69 (the maintainer, 27 November 2026): the AmiWind pick is the default, the window an
        option. The builder marks every organic container that is a plant, egg sack, kollop, spore pod or ore or gem
        rock (PLANT_PICK 'pick', +'keep' for a rock) by config/harvest-flora.json's groups; the harvest's mushrooms keep no
        action; the masters' non-respawning organic containers are listed here by name so none is picked by mistake."""
        import prepare_focus as focus
        pick, keep = focus.PLANT_PICK['pick'], focus.PLANT_PICK['keep']
        self.assertEqual((pick, keep), (16, 32))      # the row's bits 4 and 5, above the owned and scroll bits
        self.assertEqual(len(self.ORGANIC_NOT_RESPAWNING), 32)
        verdicts = {0: 'window', pick: 'pick', pick | keep: 'keep'}
        for ident, (model, want) in {**self.ORGANIC_NOT_RESPAWNING, **self.ORGANIC_RESPAWNING_STASHES}.items():
            self.assertFalse(focus.harvest_picked(model), ident)
            self.assertEqual(verdicts[focus.pick_bits(ident, model)], want, ident)
        # respawning plants: picked; the harvest's kinds are the harvest's (no action, aw_harvest_runtime.c)
        for ident, model in (('flora_comberry_01', 'f\\flora_comberry_01.nif'), ('flora_wickwheat_01', 'o\\flora_wickwheat_01.nif'),
                             ('flora_marshmerrow_01', 'o\\flora_marshmerrow_01.nif'), ('contain_trama_shrub_01', 'o\\contain_trama_shrub_01.nif'),
                             ('flora_bm_holly_04', 'o\\flora_bm_holly_04.nif')):
            self.assertEqual(focus.pick_bits(ident, model), pick, ident)
        self.assertTrue(focus.harvest_picked('f\\flora_bc_mushroom_01.nif'))
        # the row carries the bits (action_code keeps them) and the engine reads the same ones
        self.assertEqual(focus.action_code(focus.ACT_TAKE | pick | keep, 1), focus.ACT_TAKE | pick | keep | focus.ACT_OWNED)
        inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
        self.assertIn('#define FOCUS_ACT_PICK %d\n' % pick, inventory)
        self.assertIn('#define FOCUS_ACT_PICK_KEEP %d\n' % keep, inventory)
        self.assertIn('if(plant_row(row))return plant_pick(row);', body(inventory, 'static int container_open(focus_row_t *row){'))
        self.assertIn('if(row->hidden || (row->picked && plant_row(row)))continue;', body(inventory, 'static int placed_target(void){'))
        # the plant's action line is the mushrooms' own, drawn by the scene (no new fixed key text in aw_inventory.c)
        self.assertIn('if(plant_row(row) && container_lock(row)<=0)return 0;', body(inventory, 'static int container_prompt('))
        self.assertNotIn('"E: Pick"', inventory)
        scene = (SRC / 'aw_scene.c').read_text(encoding='utf-8')
        self.assertIn('(name=AW_PlacedPlantHint(&steal))!=NULL', scene)
        self.assertEqual(scene.count('"E: Pick"'), 1)
        # the one saved value, AmiWind by default (the Options row, the console and dbg plantpick are views of it), and
        # the pick sound is the mushrooms' own
        strip = (SRC / 'aw_cstrip.c').read_text(encoding='utf-8')
        self.assertIn('static cvar_t plant_pick={"aw_plant_pick","1",true};', strip)
        self.assertIn('aw_plant_hide=ChimRoom_Hide;', body(strip, 'void AW_CStripInit(void){'))
        sound = re.search(r'#define PICKUP_SOUND "([^"]+)"', (SRC / 'aw_harvest_runtime.c').read_text(encoding='utf-8')).group(1)
        self.assertIn('#define PLANT_PICK_SOUND "%s"' % sound, strip)
        menu = (SRC / 'aw_menu.c').read_text(encoding='utf-8')
        self.assertIn('case ROW_PLANTS:Cvar_SetValue("aw_plant_pick",Cvar_VariableValue("aw_plant_pick")?0:1);break;', menu)
        self.assertIn('"Plant and mushroom picking: AmiWind"', menu)
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('\nPLAYTESTING|plantpick|aw_plant_pick|', catalogue)

    def test_exterior_container_carries_its_measured_box(self):
        """OUTDOOR-CONTAINER-AIM-66: an exterior container of a measured model (CONTAINER_BOXES) sits at its box's
        centre with the box and rotation in its id field, as a named board; a room's carries it too, the room ray first (the room
        ray), and so does an exterior one of an unmeasured model. The engine reads the box for 'C' rows."""
        import prepare_focus as focus
        model = 'o\\contain_com_sack_01.nif'
        self.assertIn(model, focus.CONTAINER_BOXES)
        master = self.MASTER + b''.join([
            rec('CONT', sub('NAME', z('sack_a')), sub('FNAM', z('Sack')), sub('MODL', z('o/Contain_Com_Sack_01.nif')),
                sub('FLAG', struct.pack('<I', 8))),
            rec('CONT', sub('NAME', z('odd_a')), sub('FNAM', z('Odd')), sub('MODL', z('o\\not_measured.nif')),
                sub('FLAG', struct.pack('<I', 8))),
            rec('CELL', sub('NAME', z('Store')), sub('DATA', struct.pack('<Iii', 1, 0, 0)), ref(60, 'sack_a', (1, 1, 1))),
            rec('CELL', sub('NAME', z('')), sub('DATA', struct.pack('<Iii', 0, 3, 3)),
                ref(61, 'sack_a', (24600, 24600, 100)), ref(62, 'odd_a', (24600, 24600, 100)))])
        objects = focus.objects_of(master)
        self.assertEqual(objects['sack_a'][7], model)
        rooms = focus.placements(master, objects, {'store': 9})
        inside = {r[2]: r for r in rooms[9]}
        outside = {r[2]: r for r in rooms[focus.exterior_key(3, 3)]}
        self.assertIsInstance(inside[60][9], bytes)      # a room's container too (a room map without a CHIM room)
        self.assertEqual(outside[62][9], 'odd_a')
        packed = outside[61][9]
        self.assertIsInstance(packed, bytes)
        self.assertEqual(len(focus.pack_name_and_id('C', 'Sack', packed)), focus.NAME + focus.IDENT)
        halves = struct.unpack_from('<3f', packed)
        quat = struct.unpack_from('<4f', packed, 12)
        lo, hi = focus.CONTAINER_BOXES[model]
        self.assertEqual([round(h, 2) for h in halves], [round((b - a) / 2, 2) for a, b in zip(lo, hi)])
        self.assertAlmostEqual(sum(q * q for q in quat), 1.0, places=5)
        centre = [24600 + (a + b) / 2 for a, b in zip(lo[:2], hi[:2])]
        self.assertAlmostEqual(outside[61][3], centre[0], places=3)
        self.assertAlmostEqual(outside[61][4], centre[1], places=3)
        inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
        self.assertIn("r->box=(short)(r->kind=='C'?focus_board_add(row+FOCUS_ROW):-1);", inventory)
        self.assertIn("focus_board_ray(focus_board_axis[row->box],at,eye,f)", body(inventory, 'static int placed_target(void){'))

    def test_a_plant_that_opens_carries_its_measured_box(self):
        """PLANT-BOX-AIM-69: an organic container that opens (FARGOTH-STASH-STUMP-69: no harvest kind covers its model)
        carries its measured box outdoors as any container that opens (before: the near-the-point aim only, 19,879
        placements of the three masters); a harvest kind (a mushroom) keeps its record id; the build's preflight asks for
        the box of every one that opens and none of a harvest kind."""
        import prepare_focus as focus
        stump = 'f\\flora_treestump_wg_01.nif'
        for model in (stump, 'o\\flora_wickwheat_01.nif', 'f\\flora_comberry_01.nif', 'o\\contain_trama_shrub_01.nif',
                      'o\\flora_bm_holly_04.nif'):
            self.assertIn(model, focus.CONTAINER_BOXES)
            self.assertFalse(focus.harvest_picked(model))
        self.assertNotIn('f\\flora_bc_mushroom_01.nif', focus.CONTAINER_BOXES)
        # flora_bm_holly_04 measured with the repo's NIF reader reads exactly as flora_bm_holly_06 measured with PyFFI
        self.assertEqual(focus.CONTAINER_BOXES['o\\flora_bm_holly_04.nif'], focus.CONTAINER_BOXES['o\\flora_bm_holly_06.nif'])
        master = self.MASTER + b''.join([
            rec('CONT', sub('NAME', z('flora_treestump_unique')), sub('FNAM', z('Hollow Treestump')),
                sub('MODL', z('f\\Flora_TreeStump_WG_01.nif')), sub('FLAG', struct.pack('<I', 1))),
            rec('CONT', sub('NAME', z('flora_bc_mushroom_a')), sub('FNAM', z('Luminous Russula')),
                sub('MODL', z('f\\flora_bc_mushroom_01.nif')), sub('FLAG', struct.pack('<I', 1 | 2))),
            rec('CONT', sub('NAME', z('flora_new_a')), sub('FNAM', z('New Plant')),
                sub('MODL', z('o\\flora_not_measured_01.nif')), sub('FLAG', struct.pack('<I', 1))),
            rec('CELL', sub('NAME', z('')), sub('DATA', struct.pack('<Iii', 0, -2, -9)),
                ref(70, 'flora_treestump_unique', (-14000, -71000, 300)), ref(71, 'flora_bc_mushroom_a', (-14100, -71000, 300)),
                ref(72, 'flora_new_a', (-14200, -71000, 300)))])
        rows = {r[2]: r for r in focus.placements(master, focus.objects_of(master), {})[focus.exterior_key(-2, -9)]}
        self.assertIsInstance(rows[70][9], bytes)
        self.assertAlmostEqual(struct.unpack_from('<3f', rows[70][9])[0], (546.9 + 530.8) / 2, places=3)
        self.assertEqual(rows[71][9], 'flora_bc_mushroom_a')
        self.assertEqual(rows[72][9], 'flora_new_a')
        self.assertEqual(focus.boxed_rows(list(rows.values())), 1)
        # the preflight: the unmeasured plant that opens is asked for (before: no organic one ever was), the mushroom not
        missing = focus.missing_boxes(master)
        self.assertIn(('C', 'o\\flora_not_measured_01.nif', 'flora_new_a'), missing)
        self.assertFalse([m for m in missing if m[2] in ('flora_bc_mushroom_a', 'flora_treestump_unique')])

    def test_every_place_fits_the_engines_box_table(self):
        """PLANT-BOX-AIM-69: the named boards and the boxed containers of a place share the engine's box table
        (aw_inventory.c FOCUS_BOARDS: a room alone, outdoors the 3 x 3 cells); a board past it is not kept at all. With
        the plants' boxes the most in one window of the three masters is 1,183: at the 256 of before 182 places were
        over and 379 signposts left the focus. The box table now holds as many as the row table, and the focus stage
        refuses a place past it, as it does for the rows. The table is allocated with the rows (55,296 bytes)."""
        import prepare_focus as focus
        self.assertEqual(focus.WINDOW_BOXES, focus.WINDOW_ROWS)
        inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
        self.assertRegex(inventory, r'#define FOCUS_BOARDS %d\b' % focus.WINDOW_BOXES)
        self.assertRegex(inventory, r'#define FOCUS_ROWS %d\b' % focus.WINDOW_ROWS)
        self.assertIn('if(!focus_board_axis || focus_boards>=FOCUS_BOARDS)return -1;',
                      body(inventory, 'static int focus_board_add('))
        # allocated with the rows at the first place read, not in the BSS: the engine's static size comes off the Fast
        # RAM before the heap and the automatic CHIM cache bank is sized from the rest in whole MiB
        self.assertIn('static float (*focus_board_axis)[3][3];', inventory)
        self.assertNotIn('static float focus_board_axis[', inventory)
        load = body(inventory, 'static void focus_load(void)')
        self.assertLess(load.index('focus_rows=(focus_row_t *)AW_TryMalloc(FOCUS_ROWS*sizeof(focus_row_t))'),
                        load.index('focus_board_axis=(float (*)[3][3])AW_TryMalloc(FOCUS_BOARDS*sizeof(*focus_board_axis))'))
        # a window like the busiest of the masters: 9 cells of 131 boxes (1,179) is past the old 256 and fits now; a
        # room counts alone
        counts = {focus.exterior_key(x, y): 131 for x in (-1, 0, 1) for y in (-1, 0, 1)}
        counts[7] = 300
        most, key = focus.window_boxes(counts)
        self.assertEqual((most, key), (1179, focus.exterior_key(0, 0)))
        self.assertGreater(most, 256)
        self.assertLessEqual(most, focus.WINDOW_BOXES)
        self.assertEqual(focus.window_boxes({7: 300, 8: 12}), (300, 7))
        self.assertEqual(focus.window_boxes({}), (0, 0))
        # the focus stage checks it beside the rows and says it in its receipt
        build = (ROOT / 'tools/prepare_focus.py').read_text(encoding='utf-8')
        start = build.index('def build(data_files, presented=None):')
        build = build[start:build.index('\ndef main():', start)]
        self.assertIn('boxes[number] = boxed_rows(rows)', build)
        self.assertIn('box_window, box_key = window_boxes(boxes)', build)
        self.assertIn('if box_window > WINDOW_BOXES:', build)
        self.assertIn("'most_place_boxes': box_window, 'box_limit': WINDOW_BOXES", build)

    def test_an_item_without_a_name_is_taken(self):
        """ITEM-NAMELESS-NOT-TAKEN-69: OpenMW 0.51 takes the faced object when its class hasToolTip; for a light that is
        its carry flag (mwclass/light.cpp Light::hasToolTip = showsInInventory), every other item class keeps
        Class::hasToolTip's true. The ten burned-out torches of Old Mournhold's Temple Sewers West
        (light_com_torch_burnedout_UNI: no FNAM, carry flag) had no row and could not be aimed at; a fixed light without a
        name is still no item, and an activator or container without a name still has no row."""
        import prepare_focus as focus
        master = self.MASTER + b''.join([
            rec('LIGH', sub('NAME', z('light_com_torch_burnedout_UNI')), sub('MODL', z('l\\Light_Com_Torch_01.NIF')),
                sub('LHDT', struct.pack('<fiiiBBBBi', 0, 1, 0, 16, 0, 0, 0, 0, 0x22))),
            rec('LIGH', sub('NAME', z('light_com_torch_01_UNI')), sub('MODL', z('l\\Light_Com_Torch_01.NIF')),
                sub('LHDT', struct.pack('<fiiiBBBBi', 0, 5, -1, 256, 0, 0, 0, 0, 0x19))),
            rec('MISC', sub('NAME', z('misc_nameless')), sub('MCDT', struct.pack('<fii', .5, 2, 0))),
            rec('CELL', sub('NAME', z('Sewers')), sub('DATA', struct.pack('<Iii', 1, 0, 0)),
                ref(80, 'light_com_torch_burnedout_UNI', (1, 1, 1)), ref(81, 'light_com_torch_01_UNI', (1, 1, 1)),
                ref(82, 'misc_nameless', (2, 2, 2)))])
        objects = focus.objects_of(master)
        self.assertEqual(objects['light_com_torch_burnedout_uni'][:5], ('I', '', 0.0, 1, focus.ACT_TAKE))
        self.assertEqual(objects['misc_nameless'][:2], ('I', ''))
        self.assertNotIn('light_com_torch_01_uni', objects)          # not carried: a fixed light, no item
        rows = {r[2]: r for r in focus.placements(master, objects, {'sewers': 4})[4]}
        self.assertEqual(sorted(k for k in rows if k >= 80), [80, 82])
        packed = focus.pack_name_and_id('I', rows[80][8], rows[80][9])
        self.assertEqual(packed[:focus.NAME], bytes(focus.NAME))       # an empty name field
        self.assertEqual(packed[focus.NAME:].rstrip(b'\0'), b'light_com_torch_burnedout_uni')
        inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
        add = body(inventory, 'static void focus_add_row(const byte *row){')
        self.assertIn("if((!r->name[0] && r->kind!='I') || !(r->weight>=0 && r->weight<1000000))return;", add)
        take = body(inventory, 'static int take_row(focus_row_t *row){')
        self.assertIn('if(row->name[0])AW_UIPickupTaken(row->name,1,3);', take)

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
        self.assertIn('field_ref(e)', objects)     # aw_ref, found once per game code (MWSCRIPT-TICK-SHARE-66)
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
        # every cut piece of the reference, in either id form (REF-IDENTITY-MERGED-MASTER-66: RoomRefIs masks the
        # piece bits off and reads a merged number as its stable id too)
        self.assertIn('RoomRefIs (i, reference)', hide)
        self.assertIn('& ROOM_SOURCE_MASK', body(self.room, 'static int RoomRefIs (int i, unsigned reference)'))


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
        # INFO-BOX-TEXT-CUT-62: in the Morrowind name-label style the box is the only label, for every target: with the
        # focus row's weight and value lines, or the title alone
        self.assertEqual(draw.count('AW_UIFocusBox('), 2)
        self.assertIn('if(!driver && !npc_hint() &&', draw)
        self.assertNotIn('person->v.netname', draw)
        placed = body(self.inventory, 'int AW_PlacedFocus(')
        self.assertIn("kind=='A')return 0;", placed)
        box = body(self.ui, 'void AW_UIFocusBox(')
        self.assertIn('AW_UIBox(', box)                      # the shared framed box
        self.assertIn('owned?red', box.replace(' ', ''))     # theft colour on the name

    def test_name_labels_switch_defaults_to_the_amiwind_style(self):
        # INFO-BOX-TEXT-CUT-62: aw_name_labels 1 = AmiWind (title and action only below the view, no box over it,
        # the default), 0 = Morrowind (the framed box too, sized from its measured text and wrapped, never cut)
        self.assertIn('static cvar_t name_labels={"aw_name_labels","1",true};', self.scene)
        self.assertIn('Cmd_AddCommand("aw_name_labels_set",name_labels_command)', self.scene)
        draw = body(self.scene, 'void AW_SceneDraw(void)')
        self.assertIn('ami=AW_SceneNameLabelsAmiWind()', draw)
        self.assertIn('if(!ami){', draw)                  # Morrowind: the box only, then return before any title or action
        # AmiWind only: the aimed name below the view (HUD-TEXTS-OVERLAP-67: the one title, through focus_title_draw)
        self.assertIn('who=ami?AW_SceneTargetName():NULL;', draw)
        self.assertIn('if(title && *title && (!AW_UISpeakerAtRight() || style!=2))AW_UIObjectName(title,style);',
                      body(self.scene, 'static void focus_title_draw('))
        keymaps = (ROOT/'config/keymaps.cfg').read_text(encoding='utf-8')
        self.assertIn('\naw_name_labels 1\n', keymaps)               # Reset to defaults
        commands = (ROOT/'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('ui namelabels|aw_name_labels_set|', commands)
        listing = (ROOT/'docs/AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertIn('ui namelabels', listing)
        menu = (ROOT/'engine/aga/src/aw_menu.c').read_text(encoding='utf-8')
        self.assertIn('"Name labels: AmiWind":"Name labels: Morrowind"', menu)
        # the box measures its rows in the small font and wraps at the screen width (AW_UILine): nothing is cut
        box = body(self.ui, 'static int focus_layout(')
        self.assertIn('AW_UILine(', box)
        self.assertIn('AW_UIWidth(rows[i])', box)

    def test_weight_text_drops_trailing_zeros(self):
        self.assertTrue(re.search(r'static void weight_text\(', self.inventory))


if __name__ == '__main__':
    unittest.main()
