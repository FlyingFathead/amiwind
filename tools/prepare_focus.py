#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The focus table (FOCUS-BOX-58): what the framed box shows when you aim at a placed thing in a room.

For every interior cell of the base master (numbered as tools/cell_numbers.py numbers them, the room map's
_aw_cell_int) and every exterior cell (by its grid), each placed item, actor and door: its kind, reference number, position (game units), and for items
the weight, value and whether taking it would be theft (an owner or owning faction on the placement, OpenMW 0.51
mwworld/cellref and mechanicsmanagerimp isAllowedToUse); for doors the destination cell's name, or for a door
leading outside the exterior cell's name, else its region's name. Names are the records'
own display names. The output is private game data: id1/focus.awf, one file with a per-room index.

Format AWF3 (little-endian; AWF1 was the rows without the record id, 64 bytes each; AWF2 the rows below without the
owner list; the engine reads all three):
  "AWF3" u32 rooms
  rooms x { u32 key, u32 first row, u32 rows }   ascending key: a room's cell number, or for an exterior cell
          0x80000000 | (grid x + 2048) << 12 | (grid y + 2048) (exterior_key)
  rows x 96 bytes { u8 kind ('I' item, 'A' actor, 'D' door), u8 owned, u8 action code (STEAL-PROMPT-58: bits 0-1
                    0 none / 1 take / 2 read / 3 talk, bit 2 owned, bit 3 magic scroll; 0 in older files; a container
                    'C': 1 opens (CONTAINER-WINDOW-59), 0 an organic one, flora, harvested), u8 a container's lock
                    level in the data (FLTV 0..100; 0 for everything else and in older files),
                    u32 reference,
                    i32 x, i32 y, i32 z (game units), f32 weight, i32 value, char name[36] (NUL-ended cp1252),
                    char id[32] (an item's record id, folded, NUL-padded; empty for actors; for a door empty, or the
                    rest of a name longer than 35 bytes, up to 31 more: INFO-BOX-TEXT-CUT-62, the engine joins the two
                    when the name field is full) }
  then the owners list (CELL-CHANGES-59 slice 2): "AWO1" u32 n,
  n x { u32 reference, u16 offset of its owner id in the pool, u8 flags (bit 0: a faction owns it), u8 0 }
          ascending reference: every owned item row whose owner id fits (OWNER_ID bytes, printable)
  u32 pool bytes, the pool: each owner id once, folded, NUL-ended
  then the containers' contents (CELL-CHANGES-59 slice 3; an engine of slice 2 stops reading before it):
  "AWC1" u32 n, n x { u32 reference, u32 first item, u16 items, u8 flags (bit 0: an entry restocks, bit 1: a levelled
          list left as the data has it, bit 2: organic), u8 0 }   ascending reference: every placed container ('C' rows, a container
          is owned like an item: its owner in the owners list)
  u32 items, items x { char id[32] (folded, NUL-padded), i32 count }   the record's NPCO list (a restocking entry's
          count made positive); levelled lists (LEVI) are left out (resolved by a later slice)
  then the reference identity table (CELL-CHANGES-59 slice 7; an engine of slice 6 stops reading before it): "AWI1"
          u8 files, files x { u8 index (tools/ref_identity.py), u8 length, the name, u32 references, 8 bytes of the
          file's SHA-256 }, i32 iMonthsToRespawn, f32 fCorpseRespawnDelay, f32 fCorpseClearDelay (the master's GMSTs),
          u32 rows, u32 step, u32 blocks, blocks x u32 the first key of each block of STEP rows,
          rows x { u32 key | flags << 24, u32 record hash }   ascending key: every live placed reference of the master
          by its stable id; flags 1 its record is flagged Respawn (CONT 2, CREA 2, NPC_ 4), 2 a levelled creature list;
          the record hash is FNV-1a over the record id folded to lower case (0 becomes 1; the engine's
          AW_LedgerNameHash). A saved game keeps each changed reference's hash, so a build of other game data can tell
          a reference that is gone or now names another record (engine aw_ledger.h AW_LedgerMigrate), and the respawn
          rules read the flags (OpenMW 0.51 CellStore::respawn).
The record id is what the engine adds to the inventory when the player takes a placed item (PICKUP-PLACED-58); the
owner is whom it is stolen from (the reference's owner ANAM, else its owning faction CNAM; the rule of OpenMW 0.51
mwmechanics/mechanicsmanagerimp.cpp itemTaken), kept by the engine's world change list as (item, owner).
A new stage of its own: no other stage's input or cache key changes.
"""
import argparse, hashlib, json, math, re, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mwad.esm import records, subrecords, string, first
from mwad.paths import resolve_data_files, child_ci
from mwad.masters import master_path
sys.path.insert(0, str(ROOT / 'tools'))
from ref_identity import stable_ref

MASTER = 'Morrowind.esm'   # the content file the lists read (its references' stable ids: tools/ref_identity.py)
ITEM_DATA = {   # record -> (data subrecord, struct of its weight and value, offset)
    'WEAP': ('WPDT', '<fi', 0), 'ARMO': ('AODT', '<xxxxfi', 0), 'CLOT': ('CTDT', '<xxxxfH', 0),
    'ALCH': ('ALDT', '<fi', 0), 'INGR': ('IRDT', '<fi', 0), 'BOOK': ('BKDT', '<fi', 0), 'MISC': ('MCDT', '<fi', 0),
    'LIGH': ('LHDT', '<fi', 0), 'APPA': ('AADT', '<xxxxxxxxfi', 0), 'LOCK': ('LKDT', '<fi', 0),
    'PROB': ('PBDT', '<fi', 0), 'REPA': ('RIDT', '<fi', 0)}
ACTORS = ('NPC_', 'CREA')
ROW = 96
NAME = 36
IDENT = 32
OWNER_ID = 32           # the longest owner id the engine keeps (aw_ledger.h AW_LEDGER_STOLEN_ID)
OWNER_POOL = 65536      # the pool offsets are 16 bits
MAX_ROWS = 1024        # per room or cell (the engine reads a 3 x 3 cell window into FOCUS_ROWS 1536, aw_inventory.c)
WINDOW_ROWS = 1536     # FOCUS-ROWS-WINDOW-OVERFLOW-66: the engine's table, every 3 x 3 exterior window must fit it
PLACED_ITEMS = 1024    # the engine's drawn-item list (aw_placed.c PLACED_MAX): every room's and window's items fit it
LIGHT_CARRY = 2         # LHDT flags: can be carried
CELL = 8192             # game units per exterior cell
GRID_BIAS = 2048        # exterior keys: grid offset into 12 bits
# The action code (STEAL-PROMPT-58), byte 2 of a row: what the activate key does and how the prompt reads.
ACT_NONE, ACT_TAKE, ACT_READ, ACT_TALK = 0, 1, 2, 3      # bits 0-1
ACT_OWNED = 4                                            # bit 2: taking it is theft
ACT_MAGIC_SCROLL = 8                                     # bit 3: a BOOK with an enchantment (taken, never read)

# SIGNPOST-NAMES-MISSING-65, NAMED-ACTIVATOR-FOCUS-66: a named activator ('N' row): every placed activator (ACTI)
# whose record has a name: the road signposts' boards (active_sign_*: each board its own record, named after the place
# it points to), the shop, guild and canton signs, beds, shrines, banners, bells, propylons, switches and the rest.
# The original and OpenMW 0.51 show the name of a named object in focus (mwclass/activator.cpp
# Activator::getToolTipInfo, hasToolTip: a name); the row shows its name, no action. The visible vertex box of every
# such model (model units, node transforms applied, the editor-marker shapes of an MRK model left out), measured once
# from the original data on 13 November 2026 (a one-off read with PyFFI 2.2.3). FOCUS_INVISIBLE: the models with no
# visible geometry (the sound and script markers, named Sound_Cave_Wind00 and the like): never drawn, so never aimed
# at, no row. The row's position is the box's centre in the world and its id field holds the box (half extents, the
# reference's scale applied) and the reference's rotation as a unit quaternion (w, x, y, z), so the engine tests the
# view ray against the object itself.
FOCUS_BOXES = {
    'f\\act_banner_ald_velothi.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\act_banner_gnaar_mok.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\act_banner_hla_oad.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\act_banner_khull.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\act_banner_sadrith_mora.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\act_banner_tel_aruhn.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\act_banner_tel_branora.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\act_banner_tel_fyr.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\act_banner_tel_mora.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\act_banner_tel_vos.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\act_banner_vos.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\active_bubbles00.nif': ((-4.0, -4.0, -31.6), (4.0, 4.0, -23.6)),
    'f\\active_com_bar_door.nif': ((-32.1, -81.2, -2.5), (32.0, 1.2, 2.5)),
    'f\\active_de_bar_door.nif': ((-32.1, -81.2, -2.5), (32.0, 1.2, 2.5)),
    'f\\active_de_bed_01.nif': ((-107.6, -62.3, -30.9), (107.6, 62.3, 30.9)),
    'f\\active_de_bed_02.nif': ((-131.4, -50.7, -39.9), (131.4, 50.7, 39.9)),
    'f\\active_de_bed_03.nif': ((-108.4, -57.7, -63.6), (108.4, 57.7, 63.9)),
    'f\\active_de_bed_04.nif': ((-107.2, -59.8, -31.7), (107.2, 59.6, 31.7)),
    'f\\active_de_bed_05.nif': ((-107.4, -89.0, -32.7), (107.4, 89.1, 32.6)),
    'f\\active_de_bed_06.nif': ((-109.5, -91.2, -30.9), (109.5, 91.2, 30.9)),
    'f\\active_de_bed_07.nif': ((-113.6, -62.3, -45.7), (113.6, 62.7, 45.5)),
    'f\\active_de_bed_08.nif': ((-118.4, -88.8, -45.7), (118.0, 88.8, 45.5)),
    'f\\active_de_bed_09.nif': ((-112.5, -60.2, -67.8), (112.5, 60.2, 67.8)),
    'f\\active_de_bed_10.nif': ((-112.5, -57.6, -31.9), (112.5, 57.6, 31.7)),
    'f\\active_de_bed_11.nif': ((-112.5, -57.6, -31.9), (112.5, 57.6, 31.7)),
    'f\\active_de_bed_12.nif': ((-112.5, -57.6, -31.7), (112.5, 57.6, 31.7)),
    'f\\active_de_bed_13.nif': ((-112.5, -57.6, -31.7), (112.5, 57.6, 31.7)),
    'f\\active_de_bed_14.nif': ((-112.5, -57.6, -31.9), (112.5, 57.6, 31.7)),
    'f\\active_de_bed_15.nif': ((-108.4, -88.2, -32.6), (108.4, 88.2, 32.6)),
    'f\\active_de_bed_16.nif': ((-108.4, -88.9, -32.6), (108.4, 88.9, 32.6)),
    'f\\active_de_bed_17.nif': ((-108.5, -62.3, -30.9), (108.5, 62.3, 30.9)),
    'f\\active_de_bed_18.nif': ((-108.5, -62.4, -30.9), (108.5, 62.3, 30.9)),
    'f\\active_de_bed_19.nif': ((-108.5, -62.7, -30.9), (108.5, 62.4, 30.9)),
    'f\\active_de_bed_20.nif': ((-127.5, -95.0, -30.9), (127.2, 94.4, 30.9)),
    'f\\active_de_bed_21.nif': ((-116.9, -65.6, -45.7), (117.1, 65.6, 45.5)),
    'f\\active_de_bed_22.nif': ((-118.0, -65.6, -45.7), (117.8, 65.6, 45.5)),
    'f\\active_de_bed_23.nif': ((-116.9, -65.6, -45.7), (116.9, 65.6, 45.5)),
    'f\\active_de_bed_24.nif': ((-116.9, -65.6, -45.7), (116.9, 65.6, 45.5)),
    'f\\active_de_bed_25.nif': ((-117.2, -65.6, -45.7), (116.9, 65.6, 45.5)),
    'f\\active_de_bed_26.nif': ((-118.5, -88.8, -45.7), (118.3, 88.8, 45.5)),
    'f\\active_de_bed_27.nif': ((-118.4, -88.8, -45.7), (118.7, 88.8, 45.5)),
    'f\\active_de_bed_28.nif': ((-134.8, -51.1, -41.0), (134.8, 51.1, 40.6)),
    'f\\active_de_bed_29.nif': ((-193.4, -51.1, -34.5), (193.2, 51.1, 41.2)),
    'f\\active_de_bed_30.nif': ((-152.1, -51.1, -49.0), (151.9, 51.1, 28.6)),
    'f\\active_de_bedroll.nif': ((-78.7, -43.3, -12.6), (78.7, 43.5, 13.2)),
    'f\\active_sign_c_arms_01.nif': ((-4.1, -31.2, -90.8), (4.1, 31.3, 3.2)),
    'f\\active_sign_c_clothing_01.nif': ((-5.1, -28.0, -82.5), (5.1, 28.0, 5.3)),
    'f\\active_sign_c_goods_01.nif': ((-5.1, -28.0, -82.5), (5.1, 28.0, 5.0)),
    'f\\active_sign_c_goods_02.nif': ((-6.9, -28.2, -86.8), (6.9, 28.1, 4.1)),
    'f\\active_sign_c_guildf_01.nif': ((-4.1, -31.2, -90.8), (4.1, 31.3, 3.2)),
    'f\\active_sign_c_guildm_01.nif': ((-6.9, -38.4, -101.2), (6.9, 35.9, 4.2)),
    'f\\active_sign_c_inn_02.nif': ((-4.0, -25.7, -77.9), (4.0, 25.0, 3.2)),
    'f\\active_sign_c_pwan_01.nif': ((-6.9, -28.2, -86.8), (6.9, 28.1, 4.1)),
    'f\\active_signpost_01.nif': ((-4.0, -77.6, -16.4), (4.0, 0.1, 16.0)),
    'f\\active_signpost_02.nif': ((-5.7, -88.7, -20.8), (5.7, -0.1, 20.7)),
    'f\\active_triolith_01a.nif': ((-29.6, -28.6, -24.8), (29.8, 28.6, 24.7)),
    'f\\furn_6th_bell1.nif': ((-27.3, -26.0, -32.2), (27.3, 26.0, 32.2)),
    'f\\furn_6th_bell2.nif': ((-23.9, -22.8, -28.3), (23.9, 22.8, 28.3)),
    'f\\furn_6th_bell3.nif': ((-22.0, -20.9, -25.9), (22.0, 20.9, 25.9)),
    'f\\furn_6th_bell4.nif': ((-20.0, -19.0, -23.6), (20.0, 19.0, 23.6)),
    'f\\furn_6th_bell5.nif': ((-18.7, -17.7, -22.0), (18.7, 17.7, 22.0)),
    'f\\furn_6th_bell6.nif': ((-17.1, -16.3, -20.2), (17.1, 16.3, 20.2)),
    'f\\furn_banner_hlaalu_01.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_banner_tavern_01.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_banner_tavern_in.nif': ((-40.0, -0.0, -64.0), (40.0, 0.2, 64.0)),
    'f\\furn_banner_temple_01.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_banner_temple_01_in.nif': ((-40.0, -0.0, -64.0), (40.0, 0.2, 64.0)),
    'f\\furn_banner_temple_02.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_banner_temple_02_in.nif': ((-40.0, -0.0, -64.0), (40.0, 0.2, 64.0)),
    'f\\furn_banner_temple_03.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_banner_temple_03_in.nif': ((-40.0, -0.0, -64.0), (40.0, 0.2, 64.0)),
    'f\\furn_bannerd_alchemy_01.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_bannerd_alchemy_in.nif': ((-40.0, -0.0, -64.0), (40.0, 0.2, 64.0)),
    'f\\furn_bannerd_clothing_01.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_bannerd_clothing_in.nif': ((-40.0, -0.0, -64.0), (40.0, 0.2, 64.0)),
    'f\\furn_bannerd_danger_01.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_bannerd_goods_01.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_bannerd_goods_in.nif': ((-40.0, -0.0, -64.0), (40.0, 0.2, 64.0)),
    'f\\furn_bannerd_wa_shop_01.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_bannerd_wa_shop_in.nif': ((-40.0, -0.0, -64.0), (40.0, 0.2, 64.0)),
    'f\\furn_bannerd_welcome_01.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_cistern_01.nif': ((-41.9, -41.5, -42.5), (41.4, 41.6, 42.5)),
    'f\\furn_com_bed_01.nif': ((-107.1, -56.7, -85.9), (107.1, 56.7, 85.7)),
    'f\\furn_com_bed_02.nif': ((-107.5, -57.0, -31.6), (107.5, 57.0, 31.3)),
    'f\\furn_com_bed_03.nif': ((-107.5, -57.0, -28.8), (107.5, 57.0, 28.8)),
    'f\\furn_com_bed_04.nif': ((-107.5, -57.0, -31.6), (107.5, 57.0, 31.3)),
    'f\\furn_com_bed_05.nif': ((-107.5, -57.0, -28.8), (107.5, 57.0, 28.8)),
    'f\\furn_com_bed_06.nif': ((-107.1, -89.6, -85.7), (107.1, 89.6, 85.7)),
    'f\\furn_com_bed_07.nif': ((-107.5, -100.2, -31.3), (107.5, 100.2, 31.3)),
    'f\\furn_com_bunk_01.nif': ((-105.4, -52.7, -71.2), (105.1, 52.7, 71.1)),
    'f\\furn_com_bunk_02.nif': ((-105.4, -52.7, -71.2), (105.1, 52.7, 71.1)),
    'f\\furn_com_cauldron_01.nif': ((-16.1, -26.4, -44.1), (30.8, 27.0, 52.8)),
    'f\\furn_de_banner_book_01.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_de_banner_book_in.nif': ((-40.0, -0.0, -64.0), (40.0, 0.2, 64.0)),
    'f\\furn_de_banner_pawn_01.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_dwrv_beltdrive00.nif': ((-112.7, -318.1, -123.2), (111.9, 290.0, 168.8)),
    'f\\furn_dwrv_dynamo00.nif': ((-147.2, -585.7, -75.7), (171.5, 22.8, 185.4)),
    'f\\furn_dwrv_fitting40.nif': ((-41.7, -18.4, -1.5), (41.7, 18.5, 71.4)),
    'f\\furn_dwrv_steam_00.nif': ((-105.7, -171.3, -141.4), (86.7, 170.4, 142.8)),
    'f\\furn_dwrv_tranny00.nif': ((-76.0, -408.8, -61.4), (75.1, 24.5, 91.8)),
    'f\\furn_imp_altar_01.nif': ((-79.4, -45.9, -0.2), (79.4, 45.9, 75.2)),
    'f\\furn_lavacave_pool00.nif': ((-117.2, -124.0, -56.1), (117.2, 124.0, 56.1)),
    'f\\furn_redoran_flag_01.nif': ((-40.0, -64.0, 0.0), (40.0, 64.0, 0.2)),
    'f\\furn_redoran_flag_in.nif': ((-40.0, -0.0, -64.0), (40.0, 0.2, 64.0)),
    'f\\furn_shrine_aralor_01.nif': ((-37.5, -41.7, -10.6), (38.7, 36.5, 127.3)),
    'f\\furn_shrine_delyn_01.nif': ((-36.9, -41.7, -10.6), (39.4, 36.5, 127.3)),
    'f\\furn_shrine_felms_01.nif': ((-36.8, -41.7, -10.6), (39.5, 36.5, 127.3)),
    'f\\furn_shrine_llothis_01.nif': ((-37.6, -41.7, -10.6), (38.7, 36.5, 127.3)),
    'f\\furn_shrine_meris_01.nif': ((-37.8, -41.7, -10.6), (38.5, 36.5, 127.3)),
    'f\\furn_shrine_nerevar_01.nif': ((-38.0, -41.7, -10.6), (38.2, 36.5, 127.3)),
    'f\\furn_shrine_olms_01.nif': ((-37.6, -41.7, -10.6), (38.7, 36.5, 127.3)),
    'f\\furn_shrine_rilms_01.nif': ((-37.7, -41.7, -10.6), (38.6, 36.5, 127.3)),
    'f\\furn_shrine_roris_01.nif': ((-37.0, -41.7, -10.6), (39.3, 36.5, 127.3)),
    'f\\furn_shrine_seryn_01.nif': ((-36.9, -41.7, -10.6), (39.4, 36.5, 127.3)),
    'f\\furn_shrine_tribunal_01.nif': ((-37.8, -41.7, -10.6), (38.5, 36.5, 127.3)),
    'f\\furn_shrine_veloth_01.nif': ((-37.5, -41.7, -10.6), (38.7, 36.5, 127.3)),
    'f\\furn_shrine_vivec_01.nif': ((-37.9, -41.7, -10.6), (38.4, 36.5, 127.3)),
    'f\\furn_triolith_01.nif': ((-31.1, -34.6, -144.1), (31.1, 35.3, 144.0)),
    'f\\furn_velothi_altar_01.nif': ((-52.8, -83.1, 0.0), (50.1, 83.3, 76.3)),
    'i\\active_port_andra.nif': ((-19.0, -14.0, -0.1), (5.2, 14.0, 100.6)),
    'i\\active_port_beran.nif': ((-19.0, -14.0, -0.1), (5.2, 14.0, 100.6)),
    'i\\active_port_falag.nif': ((-19.0, -14.0, -0.1), (5.2, 14.0, 100.6)),
    'i\\active_port_falen.nif': ((-19.0, -14.0, -0.1), (5.2, 14.0, 100.6)),
    'i\\active_port_hlor.nif': ((-19.0, -14.0, -0.1), (5.2, 14.0, 100.6)),
    'i\\active_port_indo.nif': ((-19.0, -14.0, -0.1), (5.2, 14.0, 100.6)),
    'i\\active_port_maran.nif': ((-19.0, -14.0, -0.1), (5.2, 14.0, 100.6)),
    'i\\active_port_roth.nif': ((-19.0, -14.0, -0.1), (5.2, 14.0, 100.6)),
    'i\\active_port_telas.nif': ((-19.0, -14.0, -0.1), (5.2, 14.0, 100.6)),
    'i\\active_port_valen.nif': ((-19.0, -14.0, -0.1), (5.2, 14.0, 100.6)),
    'i\\in_akulakhan00.nif': ((-1736.7, -1063.4, 562.6), (1626.2, 1033.5, 8798.5)),
    'i\\in_dagoth_bridge00.nif': ((-159.8, 2.9, -111.6), (170.2, 2260.9, 17.5)),
    'i\\in_dwrv_crank00.nif': ((-24.6, -21.7, -10.6), (24.7, 4.1, 11.3)),
    'i\\in_moldboulder02.nif': ((-150.4, -101.0, -99.3), (148.7, 101.0, 104.3)),
    'm\\misc_skull00.nif': ((-5.7, -9.0, -8.7), (5.7, 8.2, 8.7)),
    'r\\siltstrider.nif': ((-203.7, -694.6, -695.3), (203.7, 585.4, 1385.0)),
    'x\\ex_dae_azura.nif': ((-286.1, -129.7, -0.0), (286.1, 129.7, 772.7)),
    'x\\ex_dae_b_bo_head.nif': ((-114.2, -105.5, -17.1), (116.7, 123.5, 90.0)),
    'x\\ex_dae_boethiah.nif': ((-902.5, -342.3, -10.0), (329.2, 581.6, 778.3)),
    'x\\ex_dae_malacath_attack.nif': ((-264.7, -322.8, -18.8), (237.7, 126.3, 791.3)),
    'x\\ex_dae_mehrunesdagon.nif': ((-312.2, -209.8, -2.0), (312.4, 198.8, 693.2)),
    'x\\ex_dae_molagbal.nif': ((-372.3, -425.0, -264.7), (292.1, 428.7, 551.4)),
    'x\\ex_dae_sheogorath.nif': ((-208.7, -140.7, -19.6), (177.8, 147.7, 769.2)),
    'x\\ex_de_oar.nif': ((-8.3, -87.7, -1.0), (8.3, 87.7, 1.0)),
    'x\\ex_de_rowboat.nif': ((-67.7, -179.4, -36.7), (67.7, 175.7, 36.7)),
    'x\\ex_de_shack_door.nif': ((-54.6, -14.0, -75.8), (54.2, 14.0, 75.8)),
    'x\\ex_de_shack_plank_03.nif': ((-19.3, -123.7, -4.4), (19.3, 123.7, 4.4)),
    'x\\ex_gg_gateswitch_01.nif': ((-13.0, -5.5, -12.5), (13.0, 5.5, 12.5)),
    'x\\ex_gnisis_roadmarker_01.nif': ((-44.8, -44.8, -256.7), (44.8, 44.8, 320.0)),
    'x\\ex_v_sign_arena_01.nif': ((-5.4, -112.9, -137.0), (5.5, 112.9, 137.0)),
    'x\\ex_v_sign_fq_01.nif': ((-5.4, -112.9, -137.0), (5.5, 112.9, 137.0)),
    'x\\ex_v_sign_hallj_01.nif': ((-5.4, -112.9, -137.0), (5.5, 112.9, 137.0)),
    'x\\ex_v_sign_hallw_01.nif': ((-5.4, -112.9, -137.0), (5.5, 112.9, 137.0)),
    'x\\ex_v_sign_hlaalu_01.nif': ((-5.4, -112.9, -137.0), (5.5, 112.9, 137.0)),
    'x\\ex_v_sign_redoran_01.nif': ((-5.4, -112.9, -137.0), (5.5, 112.9, 137.0)),
    'x\\ex_v_sign_stdeyln_01.nif': ((-5.4, -112.9, -137.0), (5.5, 112.9, 137.0)),
    'x\\ex_v_sign_stolms_01.nif': ((-5.4, -112.9, -137.0), (5.5, 112.9, 137.0)),
    'x\\ex_v_sign_telvanni_01.nif': ((-5.4, -112.9, -137.0), (5.5, 112.9, 137.0)),
    'x\\furn_sign_arms_01.nif': ((-4.1, -31.2, -90.8), (4.1, 31.3, 3.2)),
    'x\\furn_sign_inn_01.nif': ((-4.1, -31.2, -90.8), (4.1, 31.3, 3.2)),
    'x\\terrain_lava_vent.nif': ((-22.3, -49.3, -8.6), (47.5, 38.7, 201.5)),
    'x\\terrain_lava_ventlg.nif': ((-72.6, -72.7, -167.5), (84.0, 69.4, 255.0)),
    # EXPANSION-BASE-ONLY-TABLES-66: the models of Tribunal.esm and Bloodmoon.esm (the merged master), measured the
    # same way from Bloodmoon.bsa, Tribunal.bsa and Morrowind.bsa on 13 November 2026
    'd\\ex_de_ship_door.nif': ((-46.7, -5.9, -83.4), (45.6, 2.5, 83.8)),
    'd\\ex_de_ship_trapdoor.nif': ((-48.0, -58.0, -2.1), (48.0, 58.0, 8.3)),
    'f\\act_bm_garden_plot_01.nif': ((-282.2, -315.6, -106.1), (282.2, 315.6, 106.1)),
    'f\\act_bm_pipe_01.nif': ((-46.4, -45.5, -0.4), (46.3, 45.8, 194.0)),
    'f\\act_bm_stone_beast_01.nif': ((-112.5, -56.3, 1.2), (112.5, 56.3, 1215.4)),
    'f\\act_bm_stone_earth_01.nif': ((-113.5, -56.7, -2.3), (112.5, 56.7, 1211.8)),
    'f\\act_bm_stone_sun_01.nif': ((-112.5, -58.4, -0.2), (112.5, 58.4, 1213.9)),
    'f\\act_bm_stone_tree_01.nif': ((-114.4, -56.2, 3.1), (112.5, 56.2, 1217.2)),
    'f\\act_bm_stone_water_01.nif': ((-117.3, -57.0, 3.1), (112.5, 57.0, 1217.2)),
    'f\\act_bm_stone_wind_01.nif': ((-114.9, -56.8, -2.2), (112.5, 56.8, 1211.9)),
    'f\\act_bm_tree_01.nif': ((-184.1, -143.8, -242.5), (159.1, 180.3, 298.2)),
    'f\\act_bm_tree_02.nif': ((-55.3, -50.5, -153.1), (48.7, 66.8, 161.6)),
    'f\\act_bm_tree_03.nif': ((-14.9, -10.6, -69.9), (11.5, 17.5, 75.5)),
    'f\\act_m_sewer_crank_01.nif': ((-25.1, -24.9, -25.2), (25.1, 24.9, 25.2)),
    'f\\bm_forcefield.nif': ((-128.0, -64.0, -128.0), (128.0, 64.0, 128.0)),
    'f\\bm_ice_wall.nif': ((-693.3, -823.5, -215.0), (733.3, 917.9, 933.4)),
    'f\\terrain_rock_bm_74.nif': ((-95.7, -64.9, -293.1), (97.4, 67.0, 290.5)),
    'f\\terrain_rock_bm_75.nif': ((-68.8, -21.3, -256.8), (69.4, 21.4, 256.8)),
    'f\\terrain_rock_bm_78.nif': ((-96.9, -36.8, -229.7), (96.9, 36.8, 231.4)),
    'f\\terrain_rock_bm_79.nif': ((-51.7, -25.2, -232.2), (50.0, 26.7, 232.2)),
    'i\\act_dwe_cavein00.nif': ((-88.9, -60.0, 0.4), (103.0, 59.3, 174.4)),
    'i\\act_dwe_lever00.nif': ((-4.7, -27.5, -10.6), (4.6, 16.1, 79.3)),
    'i\\act_dwe_powerbox00.nif': ((-24.0, -40.0, -0.0), (24.0, 48.0, 128.9)),
    'i\\act_sotha_lever.nif': ((-79.9, -24.0, -1.8), (80.0, 24.1, 112.3)),
    'i\\act_torch_lever.nif': ((-7.8, -4.6, -9.1), (5.6, 4.4, 17.8)),
    'i\\act_werewolf_statue.nif': ((-34.0, -60.5, -64.2), (35.0, 60.5, 64.2)),
    'i\\in_sotha_door_broke.nif': ((-110.6, -51.7, -96.6), (110.6, 66.8, 96.6)),
    'i\\in_sotha_sil00.nif': ((-250.8, -47.9, 23.5), (256.2, 47.9, 464.0)),
    'i\\in_thirsk_archpiece01.nif': ((-61.5, -77.9, -15.8), (61.2, 77.0, 15.8)),
    'i\\in_thirsk_archpiece02.nif': ((-28.8, -41.7, -11.7), (39.7, 50.6, 11.7)),
    'i\\in_thirsk_beampiece01.nif': ((-209.7, -7.7, -11.3), (204.2, 7.4, 11.4)),
    'i\\in_thirsk_beampiece03.nif': ((-162.9, -12.2, -170.2), (187.0, 9.0, 179.8)),
    'i\\in_thirsk_columnpiece01.nif': ((-46.5, -26.0, -26.0), (45.4, 27.8, 26.0)),
    'i\\in_thirsk_columnpiece02.nif': ((-140.8, -23.9, -22.6), (145.0, 23.9, 23.4)),
    'm\\misc_dwrv_artifact00.nif': ((-7.4, -5.7, -14.0), (7.4, 7.2, 13.2)),
    'm\\misc_dwrv_artifact50.nif': ((-15.1, -7.1, -15.3), (15.2, 8.4, 17.4)),
    'w\\w_nord_battleaxe.nif': ((-16.2, -22.9, -2.5), (16.3, 40.8, 2.5)),
    'x\\ex_longboat02.nif': ((-259.8, -768.9, -203.8), (260.3, 785.8, 815.0)),
    'x\\ex_mh_almalexia_whole.nif': ((-316.5, -277.8, 196.9), (355.2, 265.7, 769.8)),
    'x\\ex_mh_palace_gate.nif': ((-314.6, -10.0, -374.4), (314.6, 10.0, 370.6)),
    'x\\furn_tikitorch_out.nif': ((-7.0, -7.0, -104.7), (7.0, 7.0, 12.0)),
}
FOCUS_INVISIBLE = frozenset((
    'editormarker.nif',
))
SIGN_BOARD_BOXES = FOCUS_BOXES   # the older name (the signposts first)

# CONTAINER-WINDOW-59 (OUTDOOR-CONTAINER-AIM-66): the visible vertex box (model units, node transforms applied) of
# every model of a placed, named, non-organic container (CONT) of the base master, measured once from the original data
# on 13 November 2026 (the same one-off read as FOCUS_BOXES, PyFFI 2.2.3; 56 models). An exterior container's row
# carries its box like a named board ('N'): the row sits at the box's centre and the id field holds the half extents and
# the rotation, so the engine tests the view ray against the container itself (outdoors there is no room record whose
# placement box the room ray reads; the near-the-reference-point test missed most sacks, barrels and chests: 987
# exterior containers, none aimable in the v0.0.65 census, tools/container_census.py). A room's container carries it
# too (the engine asks the room ray first; a room map that is not a CHIM room has only this box). A container whose
# model is not here keeps its record id and the near-the-point aim.
CONTAINER_BOXES = {
    'f\\furn_dwrv_cabinet00.nif': ((-70.4, -24.1, -64.1), (96.1, 24.1, 106.3)),
    'i\\in_ci_mummy_01.nif': ((-32.0, -33.3, -41.3), (32.0, 29.6, 41.3)),
    'i\\in_ci_mummy_02.nif': ((-33.0, -39.8, -40.4), (33.0, 39.8, 41.2)),
    'i\\in_ci_mummy_03.nif': ((-30.8, -44.8, -41.8), (30.8, 44.8, 41.4)),
    'i\\in_ci_mummy_04.nif': ((-36.7, -48.2, -39.6), (36.7, 49.8, 37.6)),
    'i\\in_ci_mummy_05.nif': ((-34.6, -48.2, -39.7), (35.2, 55.3, 37.8)),
    'i\\in_ci_mummy_06.nif': ((-33.9, -48.1, -39.7), (34.5, 52.2, 39.4)),
    'm\\misc_com_bottle_05.nif': ((-4.6, -4.4, -16.9), (4.6, 4.4, 16.9)),
    'o\\contain_barrel10.nif': ((-29.3, -30.8, -64.2), (29.3, 30.8, 20.5)),
    'o\\contain_barrel_01.nif': ((-28.4, -28.4, -33.4), (28.4, 28.4, 33.4)),
    'o\\contain_chest10.nif': ((-30.0, -18.3, -16.0), (30.0, 18.3, 17.0)),
    'o\\contain_chest_large_01.nif': ((7.3, -58.1, -0.2), (54.1, 58.1, 62.3)),
    'o\\contain_chest_small_01.nif': ((-21.6, -11.8, -6.3), (21.6, 12.5, 6.3)),
    'o\\contain_chest_small_02.nif': ((-21.6, -11.8, -6.3), (21.6, 12.5, 6.3)),
    'o\\contain_com_basket_01.nif': ((-28.1, -26.7, -35.3), (28.1, 26.7, 35.3)),
    'o\\contain_com_chest_01.nif': ((-40.7, -19.2, -16.7), (40.8, 19.3, 16.7)),
    'o\\contain_com_chest_02.nif': ((-39.8, -18.9, -21.9), (39.8, 19.4, 21.9)),
    'o\\contain_com_closet_01.nif': ((-89.8, -37.3, -82.4), (89.8, 37.3, 82.0)),
    'o\\contain_com_cupboard_01.nif': ((-40.0, -27.4, -27.1), (40.0, 27.4, 27.1)),
    'o\\contain_com_drawers_01.nif': ((-68.7, -25.9, -49.0), (68.7, 25.9, 48.9)),
    'o\\contain_com_hutch_01.nif': ((-65.7, -32.3, -78.6), (65.7, 32.3, 78.7)),
    'o\\contain_com_sack_01.nif': ((-35.2, -19.3, -7.0), (37.8, 19.3, 7.2)),
    'o\\contain_com_sack_02.nif': ((-20.8, -22.7, -26.2), (20.8, 22.7, 26.2)),
    'o\\contain_com_sack_03.nif': ((-11.7, -19.3, -28.3), (11.8, 19.3, 28.3)),
    'o\\contain_corpse00.nif': ((-20.6, -68.7, -9.5), (20.6, 68.7, 9.5)),
    'o\\contain_corpse10.nif': ((-27.9, -47.1, -22.5), (26.2, 49.5, 30.9)),
    'o\\contain_corpse20.nif': ((-29.0, -75.4, -7.9), (29.0, 75.4, 7.9)),
    'o\\contain_couldron10.nif': ((-50.0, -50.0, -32.0), (50.0, 50.0, 38.4)),
    'o\\contain_crate_01.nif': ((-32.0, -32.0, -32.0), (32.0, 32.0, 32.0)),
    'o\\contain_crate_02.nif': ((-32.0, -32.0, -32.0), (32.0, 32.0, 32.0)),
    'o\\contain_de_chest_01.nif': ((-46.9, -22.8, -22.6), (46.9, 22.7, 22.6)),
    'o\\contain_de_chest_02.nif': ((-39.2, -22.7, -17.5), (39.2, 22.7, 17.5)),
    'o\\contain_de_closet_01.nif': ((-105.7, -40.0, -79.8), (105.7, 40.0, 79.9)),
    'o\\contain_de_closet_02.nif': ((-90.9, -36.0, -79.3), (90.9, 36.0, 79.3)),
    'o\\contain_de_crate_logo.nif': ((-32.0, -32.0, -32.0), (32.0, 32.0, 32.0)),
    'o\\contain_de_desk_01.nif': ((-69.9, -32.6, -52.7), (69.9, 32.6, 52.7)),
    'o\\contain_de_drawers_01.nif': ((-73.3, -28.2, -48.7), (73.5, 28.2, 48.7)),
    'o\\contain_de_drawers_02.nif': ((-83.6, -33.2, -49.9), (83.6, 33.2, 49.9)),
    'o\\contain_de_table_01.nif': ((-35.9, -33.8, -30.6), (35.9, 34.0, 30.6)),
    'o\\contain_de_table_02.nif': ((-67.3, -35.6, -35.7), (67.3, 35.6, 35.6)),
    'o\\contain_dwrv_barrel00.nif': ((-30.4, -32.0, -64.2), (30.4, 32.0, 20.5)),
    'o\\contain_dwrv_barrel10.nif': ((-30.6, -32.0, -64.2), (30.3, 32.0, -21.8)),
    'o\\contain_dwrv_chest00.nif': ((-46.1, -28.3, -24.8), (46.1, 28.3, 52.3)),
    'o\\contain_dwrv_chest10.nif': ((-49.6, -5.6, -14.0), (49.1, 41.3, 32.6)),
    'o\\contain_dwrv_closet00.nif': ((-109.9, -43.3, -79.8), (110.6, 46.8, 79.8)),
    'o\\contain_dwrv_desk00.nif': ((-63.3, -32.1, -61.5), (66.0, 33.2, 61.1)),
    'o\\contain_dwrv_drawers00.nif': ((-72.7, -28.2, -47.3), (72.7, 28.2, 43.4)),
    'o\\contain_dwrv_table00.nif': ((-31.1, -31.0, -30.6), (29.7, 31.6, 30.6)),
    'o\\contain_pot_01.nif': ((-13.4, -14.5, -16.9), (13.4, 14.5, 16.9)),
    'o\\contain_tramaroot_06.nif': ((-121.5, -56.3, -72.4), (121.5, 56.3, 72.4)),
    'o\\contain_urn_01.nif': ((-31.9, -26.7, -49.2), (31.9, 26.7, 49.2)),
    'o\\contain_urn_02.nif': ((-29.6, -28.2, -58.3), (29.6, 28.2, 58.3)),
    'o\\contain_urn_03.nif': ((-28.1, -26.7, -41.6), (28.1, 26.7, 41.6)),
    'o\\contain_urn_04.nif': ((-24.9, -23.7, -44.2), (24.9, 23.7, 44.2)),
    'o\\contain_urn_05.nif': ((-28.1, -26.7, -56.7), (28.1, 26.7, 56.7)),
    'o\\flora_bittergreen_pod_01.nif': ((-78.8, -81.7, -83.6), (78.8, 81.7, 83.6)),
    # EXPANSION-BASE-ONLY-TABLES-66: the models of Tribunal.esm and Bloodmoon.esm (the merged master), measured the
    # same way from Bloodmoon.bsa, Tribunal.bsa and Morrowind.bsa on 13 November 2026
    'f\\flora_bm_snowstump_02.nif': ((-44.9, -46.9, -56.6), (44.9, 46.0, 56.7)),
    'i\\bm_ic_icicle_02.nif': ((-24.4, -25.0, -165.9), (23.4, 25.0, 165.9)),
    'i\\bm_ic_rock_05.nif': ((-160.9, -240.0, -233.9), (160.9, 240.0, 233.9)),
    'i\\contain_rock_am_15.nif': ((-134.9, -95.6, -149.1), (127.8, 98.6, 153.8)),
    'i\\contain_rock_am_16.nif': ((-132.5, -96.4, -50.7), (132.5, 98.8, 50.7)),
    'i\\contain_rock_am_17.nif': ((-92.6, -87.9, -109.1), (87.0, 99.5, 124.9)),
    'i\\contain_rock_am_18.nif': ((-92.3, -74.8, -130.8), (86.9, 85.5, 135.4)),
    'i\\contain_rock_am_19.nif': ((-156.5, -129.9, -191.5), (156.5, 125.8, 194.0)),
    'i\\contain_rock_am_20.nif': ((-145.9, -150.1, -112.8), (147.8, 140.8, 115.6)),
    'i\\contain_rock_am_21.nif': ((-200.5, -116.7, -154.7), (200.5, 113.4, 149.1)),
    'i\\contain_rock_apy_10.nif': ((-132.5, -96.4, -50.7), (132.5, 98.8, 50.7)),
    'i\\contain_rock_apy_12.nif': ((-156.5, -129.9, -191.5), (156.5, 125.8, 194.0)),
    'i\\contain_rock_apy_13.nif': ((-200.5, -116.7, -154.7), (200.5, 113.4, 149.1)),
    'i\\contain_rock_apy_14.nif': ((-145.9, -150.1, -112.8), (147.8, 140.8, 115.6)),
    'o\\bm_contain_corpse_01.nif': ((-23.0, -94.1, -9.4), (17.9, 75.5, 8.9)),
    'o\\contain_bm_stalhrim_01.nif': ((-51.8, -87.6, -31.9), (51.8, 85.1, 31.9)),
    'o\\contain_bm_wolfbane_01.nif': ((-5.1, -5.0, -18.2), (6.4, 5.0, 14.9)),
    'o\\contain_rock_ebony_01.nif': ((-132.5, -96.4, -50.7), (132.5, 98.8, 58.4)),
    'o\\contain_rock_ebony_02.nif': ((-92.6, -87.7, -109.1), (87.0, 99.7, 122.8)),
    'o\\contain_rock_ebony_05.nif': ((-156.5, -115.5, -191.5), (156.5, 125.8, 197.8)),
    'o\\contain_rock_ebony_06.nif': ((-145.9, -150.1, -112.8), (147.8, 140.8, 124.7)),
    'o\\contain_rock_ebony_07.nif': ((-200.5, -114.1, -149.1), (200.5, 116.7, 161.3)),
    'o\\flora_bm_holly_06.nif': ((-176.3, -174.1, -204.7), (203.8, 173.3, 241.3)),
}


def missing_boxes(raw):
    """EXPANSION-BASE-ONLY-TABLES-66: the boxes the master RAW (the merged master of the selected layers) needs and
    the tables above lack, as (kind, model, record id) sorted: 'N' every placed, named activator whose model is in
    neither FOCUS_BOXES nor FOCUS_INVISIBLE (the focus stage stops on it), 'C' every placed, named, non-organic
    container whose model is not in CONTAINER_BOXES (it would keep only the near-the-point aim). The build's
    preflight runs it before any stage (tools/build.py focus_box_preflight)."""
    placed = set()
    for _cell, _interior, _grid, _region, refs in cells_of(raw):
        for ref in refs:
            if 'NAME' in ref and 'DELE' not in ref:
                placed.add(string(ref['NAME'], 'NAME', errors='replace').casefold())
    out = set()
    for tag, flags, payload in records(raw):
        if tag not in ('ACTI', 'CONT') or flags & 0x20:
            continue
        fields = list(subrecords(payload))
        if any(k == 'DELE' for k, _ in fields) or not first(fields, 'MODL'):
            continue
        ident = string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()
        if ident not in placed or not string(first(fields, 'FNAM'), 'FNAM', errors='replace').strip():
            continue
        model = string(first(fields, 'MODL'), 'MODL', errors='replace').replace('/', '\\').casefold()
        if tag == 'ACTI':
            if model not in FOCUS_BOXES and model not in FOCUS_INVISIBLE:
                out.add(('N', model, ident))
        else:
            flag = first(fields, 'FLAG')
            organic = len(flag) >= 4 and bool(struct.unpack_from('<I', flag)[0] & CONT_ORGANIC)
            if not organic and model not in CONTAINER_BOXES:
                out.add(('C', model, ident))
    return sorted(out)


def is_sign_board(model):
    """SIGNPOST-NAMES-MISSING-65: True for an activator model that is a sign board (its file name says sign)."""
    return 'sign' in model.replace('/', '\\').casefold().rsplit('\\', 1)[-1]


def reference_rotation(angles):
    """The 3x3 matrix (rows) of a reference's rotation (DATA's three angles, radians): Z then Y then X on column
    vectors, all clockwise, the convention of tools/prepare_scenery.py reference_rotation."""
    x, y, z = (-a for a in angles)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    m = ((cy * cz, -cy * sz, sy), (sz, cz, 0.0), (-sy * cz, sy * sz, cy))      # Ry @ Rz
    return (m[0], tuple(cx * a - sx * b for a, b in zip(m[1], m[2])), tuple(sx * a + cx * b for a, b in zip(m[1], m[2])))


def rotation_quaternion(r):
    """The unit quaternion (w, x, y, z) of the rotation matrix R (rows), w >= 0: the engine turns a board's box with
    it by multiplications only (no sine or cosine in play: those reach 68040-unimplemented instructions)."""
    trace = r[0][0] + r[1][1] + r[2][2]
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        q = (s / 4, (r[2][1] - r[1][2]) / s, (r[0][2] - r[2][0]) / s, (r[1][0] - r[0][1]) / s)
    elif r[0][0] > r[1][1] and r[0][0] > r[2][2]:
        s = math.sqrt(1.0 + r[0][0] - r[1][1] - r[2][2]) * 2
        q = ((r[2][1] - r[1][2]) / s, s / 4, (r[0][1] + r[1][0]) / s, (r[0][2] + r[2][0]) / s)
    elif r[1][1] > r[2][2]:
        s = math.sqrt(1.0 + r[1][1] - r[0][0] - r[2][2]) * 2
        q = ((r[0][2] - r[2][0]) / s, (r[0][1] + r[1][0]) / s, s / 4, (r[1][2] + r[2][1]) / s)
    else:
        s = math.sqrt(1.0 + r[2][2] - r[0][0] - r[1][1]) * 2
        q = ((r[1][0] - r[0][1]) / s, (r[0][2] + r[2][0]) / s, (r[1][2] + r[2][1]) / s, s / 4)
    n = math.sqrt(sum(v * v for v in q))
    q = tuple(v / n for v in q)
    return q if q[0] >= 0 else tuple(-v for v in q)


def quaternion_matrix(q):
    """The rotation matrix (rows) of the unit quaternion Q (w, x, y, z): the engine's focus_board_add, line for line."""
    w, x, y, z = q
    return ((1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)),
            (2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)),
            (2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)))


def board_box(box, position, angles, scale):
    """SIGNPOST-NAMES-MISSING-65: (world centre, half extents) of a board's model BOX placed at POSITION with ANGLES
    and SCALE: the centre turned and scaled as drawn, the half extents scaled (the engine turns them by ANGLES)."""
    lo, hi = box
    centre = [(a + b) / 2 * scale for a, b in zip(lo, hi)]
    r = reference_rotation(angles)
    world = tuple(position[i] + sum(r[i][k] * centre[k] for k in range(3)) for i in range(3))
    return world, tuple((b - a) / 2 * scale for a, b in zip(lo, hi))


def book_has_words(text):
    """True when a BOOK's TEXT holds something to read once its markup (<...>, &nbsp;) and blanks are gone, or a
    picture (<IMG ...>: the Bloodmoon stone map) (BLANK-PAPER-READ-60: a text-less paper is taken, not read)."""
    if not text:
        return False
    if re.search(rb'<\s*img\b', text, flags=re.I):
        return True
    plain = re.sub(rb'<[^>]*>', b' ', text.replace(b'\x00', b''))
    plain = re.sub(rb'&nbsp;?', b' ', plain, flags=re.I)
    return bool(plain.strip())
CONT_ORGANIC = 1        # CONT FLAG bit 0: organic (flora: harvested, never opened)
CFLAG_ORGANIC = 4       # the contents list's flag for it (bit 2)


def clean(name):
    name = ''.join(c for c in name if ord(c) >= 32).strip()
    raw = name.encode('cp1252', 'replace')[:NAME - 1]
    return raw


def name_tail(name):
    """INFO-BOX-TEXT-CUT-62: the part of a door's name that does not fit the row's name field (the first NAME - 1 bytes
    are in it), up to IDENT - 1 bytes: it goes in the row's id field, which a door does not use (the engine, when the
    name field is full and the id field is not empty, reads the two as one name). Nothing for a shorter name."""
    name = ''.join(c for c in name if ord(c) >= 32).strip()
    return name.encode('cp1252', 'replace')[NAME - 1:NAME - 1 + IDENT - 1]


def pack_name_and_id(kind, name, ident):
    """The last 68 bytes of a row: the name field (NAME bytes) and the id field (IDENT bytes). An item's or container's
    id as record_id gives it; a door's long name continues there; actors keep an empty field (the area tables mark
    their rows in it)."""
    head = clean(name)
    if isinstance(ident, bytes):   # SIGNPOST-NAMES-MISSING-65, OUTDOOR-CONTAINER-AIM-66: the packed box (placements)
        return head + b'\0' * (NAME - len(head)) + ident
    tail = name_tail(name) if kind == 'D' and len(head) == NAME - 1 else b''
    return head + b'\0' * (NAME - len(head)) + (tail + b'\0' * (IDENT - len(tail)) if tail else record_id(ident))


def record_id(ident):
    """An item's record id as the row keeps it: printable ASCII, NUL-padded to IDENT bytes; empty when it would not
    fit whole (the engine then leaves the item where it is)."""
    raw = ident.encode('ascii', 'replace') if ident else b''
    if len(raw) > IDENT or any(b < 32 or b > 126 for b in raw):
        raw = b''
    return raw + b'\0' * (IDENT - len(raw))


def container_items(fields, items, levelled=()):
    """A CONT, NPC_ or CREA record's NPCO list: [(folded id, count)] of the entries ITEMS (the item records) or
    LEVELLED (the levelled item lists, CONTAINER-LEVELLED-CONTENTS-60: kept by their list id, rolled by the engine on
    the first open) knows, restocking counts made positive; and the flags (1: an entry restocks, 2: an entry naming
    neither was left out)."""
    out, flags = [], 0
    for key, value in fields:
        if key != 'NPCO' or len(value) < 36:
            continue
        count = struct.unpack_from('<i', value)[0]
        ident = value[4:36].split(b'\0', 1)[0].decode('ascii', 'replace').casefold()
        if count < 0:
            flags |= 1; count = -count
        if ident not in items and ident not in levelled:
            flags |= 2 if ident else 0
            continue
        if count and len(ident.encode('ascii', 'replace')) <= IDENT:
            out.append((ident, count))
    return out, flags


def item_lists(raw):
    """CONTAINER-LEVELLED-CONTENTS-60: {list id (folded): (flags, chance none, [(entry id folded, level)])} of every
    live LEVI record, entries in the record's order (INAM, INTV pairs). Flags as the data has them (OpenMW 0.51
    esm3/loadlevlist.hpp ItemLevList: 1 Each, a new roll for every one of the count; 2 AllLevels, every entry at or
    below the player's level, not only the highest)."""
    out = {}
    for tag, flags, payload in records(raw):
        if tag != 'LEVI' or flags & 0x20:
            continue
        fields = list(subrecords(payload))
        if any(k == 'DELE' for k, _ in fields):
            continue
        ident = string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()
        data, chance = first(fields, 'DATA'), first(fields, 'NNAM')
        entries, pending = [], None
        for key, value in fields:
            if key == 'INAM':
                pending = string(value, 'INAM', errors='replace').casefold()
            elif key == 'INTV' and pending is not None and len(value) >= 2:
                entries.append((pending, struct.unpack_from('<H', value)[0])); pending = None
        if ident:
            out[ident] = (struct.unpack_from('<I', data)[0] if len(data) >= 4 else 0,
                          min(chance[0], 100) if chance else 0, entries)
    return out


ACTOR_INVENTORY = 8     # the contents list's flag (bit 3, CORPSE-LOOT-60): an actor's inventory (a body opens it)


def objects_of(raw, levelled=None):
    """Folded record id -> (kind, name, weight, value, action[, contents, flags]) of every placeable item, actor,
    door and container (kind 'C': its contents and their flags, container_items; kind 'A' with an NPCO list: its
    inventory, flag ACTOR_INVENTORY, CORPSE-LOOT-60). LEVELLED: item_lists (their ids are kept in the contents)."""
    out = {}
    conts = []
    levelled = levelled or {}
    actors = []
    for tag, flags, payload in records(raw):
        if tag not in ITEM_DATA and tag not in ACTORS and tag not in ('DOOR', 'CONT', 'ACTI'):
            continue
        fields = list(subrecords(payload))
        if flags & 0x20 or any(k == 'DELE' for k, _ in fields):
            continue
        ident = string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()
        name = string(first(fields, 'FNAM'), 'FNAM', errors='replace')
        if tag == 'ACTI':
            # SIGNPOST-NAMES-MISSING-65, NAMED-ACTIVATOR-FOCUS-66: a named activator with something drawn; the box
            # comes from FOCUS_BOXES (placements checks that every placed one has its box)
            model = string(first(fields, 'MODL'), 'MODL', errors='replace').replace('/', '\\').casefold()
            if name.strip() and model and model not in FOCUS_INVISIBLE:
                out[ident] = ('N', name, 0.0, 0, ACT_NONE, model)
            continue
        if tag == 'CONT':
            if name:
                flag = first(fields, 'FLAG')
                organic = len(flag) >= 4 and bool(struct.unpack_from('<I', flag)[0] & CONT_ORGANIC)
                conts.append((ident, name, fields, organic))
            continue
        if tag in ITEM_DATA:
            sub, fmt, _ = ITEM_DATA[tag]
            data = first(fields, sub)
            if len(data) < struct.calcsize(fmt):
                continue
            weight, value = struct.unpack_from(fmt, data)
            if tag == 'LIGH' and (len(data) < 24 or not struct.unpack_from('<i', data, 20)[0] & LIGHT_CARRY):
                continue      # a fixed light is not an item
            if not math.isfinite(weight) or weight < 0 or value < 0 or not name:
                continue
            # STEAL-PROMPT-58: a BOOK without an enchantment is read; one with (a magic scroll) is taken like an item.
            # BLANK-PAPER-READ-60: one with no words to read (no TEXT, or only markup: sc_paper plain, the paper under
            # the quill in the Census and Excise Office) is taken like an item too. Decided for the project, 5 November
            # 2026; the original and OpenMW 0.51 (mwclass/book.cpp Book::activate) open an empty page first.
            action = ACT_TAKE
            if tag == 'BOOK':
                if first(fields, 'ENAM'):
                    action = ACT_TAKE | ACT_MAGIC_SCROLL
                elif book_has_words(first(fields, 'TEXT')):
                    action = ACT_READ
            out[ident] = ('I', name, float(weight), int(value), action)
        elif name:
            out[ident] = ('A' if tag in ACTORS else 'D', name, 0.0, 0, ACT_TALK if tag in ACTORS else ACT_NONE)
            if tag in ACTORS:
                actors.append((ident, fields))
    items = {k for k, v in out.items() if v[0] == 'I'}
    for ident, fields in actors:
        contents, cflags = container_items(fields, items, levelled)
        if contents:
            out[ident] = out[ident][:5] + (contents, (cflags & 3) | ACTOR_INVENTORY)
    for ident, name, fields, organic in conts:
        contents, cflags = container_items(fields, items, levelled)
        # CONTAINER-WINDOW-59: a container opens (ACT_TAKE: E opens its strip); an organic one (flora) is harvested,
        # never opened (action none, flag 4)
        model = string(first(fields, 'MODL'), 'MODL', errors='replace').replace('/', '\\').casefold() \
            if first(fields, 'MODL') else ''
        out[ident] = ('C', name, 0.0, 0, ACT_NONE if organic else ACT_TAKE, contents,
                      cflags | (CFLAG_ORGANIC if organic else 0), model)
    return out


def lock_level(ref):
    """CONTAINER-WINDOW-59: a placed container's lock level in the data (FLTV, 0 unlocked, at most 100)."""
    raw = ref.get('FLTV', b'')
    if len(raw) < 4:
        return 0
    return max(0, min(100, struct.unpack_from('<i', raw)[0]))


def contents_list(containers):
    """The contents list after the owners list: CONTAINERS maps reference -> (contents, flags)."""
    index, body = [], []
    for reference in sorted(containers):
        contents, flags = containers[reference]
        index.append(struct.pack('<IIHBB', reference, len(body), len(contents), flags & 15, 0))
        for ident, count in contents:
            body.append(record_id(ident) + struct.pack('<i', count))
    return (b'AWC1' + struct.pack('<I', len(index)) + b''.join(index) + struct.pack('<I', len(body)) + b''.join(body))


RESPAWN_GMSTS = ('iMonthsToRespawn', 'fCorpseRespawnDelay', 'fCorpseClearDelay')
RESPAWN_DEFAULT = (4, 72.0, 72.0)     # Morrowind.esm's own values (OpenMW 0.51 reads the same GMSTs)
RESPAWN_FLAG = {'CONT': 2, 'CREA': 2, 'NPC_': 4}   # the record's Respawn flag (OpenMW esm3 loadcont/loadcrea/loadnpc)
REFS_STEP = 256
REFS_RESPAWN = 1
REFS_LEVELLED = 2
REFS_PERSISTENT = 4   # ACTOR-RESPAWN-CORPSE-RULES-66: an NPC_/CREA record flagged Persistent (header 0x400): body kept
PERSISTENT_FLAG = 0x400


def name_hash(ident):
    """FNV-1a over the id's bytes with A-Z folded to lower case; 0 becomes 1 (engine aw_ledger.c AW_LedgerNameHash)."""
    h = 2166136261
    for c in ident.encode('cp1252', 'replace'):
        if 65 <= c <= 90:
            c += 32
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    return h or 1


def respawn_settings(raw):
    """(iMonthsToRespawn, fCorpseRespawnDelay, fCorpseClearDelay) from the master's GMSTs, the defaults where absent."""
    found = dict(zip(RESPAWN_GMSTS, RESPAWN_DEFAULT))
    for tag, flags, payload in records(raw):
        if tag != 'GMST' or flags & 0x20:
            continue
        fields = list(subrecords(payload))
        name = string(first(fields, 'NAME'), 'NAME', errors='replace')
        if name not in found:
            continue
        for key, value in fields:
            if key == 'INTV' and len(value) >= 4 and name.startswith('i'):
                found[name] = struct.unpack_from('<i', value)[0]
            elif key == 'FLTV' and len(value) >= 4 and name.startswith('f'):
                found[name] = struct.unpack_from('<f', value)[0]
    return tuple(found[n] for n in RESPAWN_GMSTS)


def reference_flags(raw):
    """Folded record id -> table flags (REFS_RESPAWN, REFS_LEVELLED, REFS_PERSISTENT) of the records that have any."""
    out = {}
    for tag, flags, payload in records(raw):
        if tag not in RESPAWN_FLAG and tag != 'LEVC':
            continue
        fields = list(subrecords(payload))
        if flags & 0x20 or any(k == 'DELE' for k, _ in fields):
            continue
        ident = string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()
        if tag == 'LEVC':
            out[ident] = REFS_LEVELLED
            continue
        value = first(fields, 'FLAG')
        bits = 0
        if len(value) >= 4 and struct.unpack_from('<I', value)[0] & RESPAWN_FLAG[tag]:
            bits |= REFS_RESPAWN
        if tag != 'CONT' and flags & PERSISTENT_FLAG:
            bits |= REFS_PERSISTENT   # OpenMW 0.51 Npc/Creature::isPersistent: mRecordFlags & FLAG_Persistent
        if bits:
            out[ident] = bits
    return out


def reference_table(raw, digest=None, name=MASTER, hashes=None):
    """The AWI1 section: every live placed reference of the master by its stable id, with its record hash and flags.
    The file list names every content file the references belong to (EXPANSION-DATA-ALL-TABLES-66): with the merged
    master of the selected layers a reference's stable id names its owning master (tools/ref_identity.py), and each
    file gets its own entry (fixed index, name, its references, the first 8 bytes of its SHA-256 from HASHES
    {name: hex}); the base game alone writes the one entry it always wrote (DIGEST)."""
    from ref_identity import NUMBER_BITS, CONTENT_FILES, RefIdentityError, file_index
    flags = reference_flags(raw)
    rows = {}
    for _cell, _interior, _grid, _region, refs in cells_of(raw):
        for ref in refs:
            if 'DELE' in ref or 'NAME' not in ref:
                continue
            try:
                key = stable_ref(name, ref['number'])
            except RefIdentityError:
                continue
            ident = string(ref['NAME'], 'NAME', errors='replace').casefold()
            rows.setdefault(key, (name_hash(ident), flags.get(ident, 0)))
    keys = sorted(rows)
    months, respawn_delay, clear_delay = respawn_settings(raw)
    owners = sorted({k >> NUMBER_BITS for k in keys} | {file_index(name)})
    hashes = dict(hashes or {})
    if digest:
        hashes.setdefault(name, digest)
    entries = []
    for index in owners:
        owner = CONTENT_FILES[index] if index != file_index(name) else name
        raw_name = owner.encode('ascii')
        own = sum(1 for k in keys if k >> NUMBER_BITS == index)
        mark = hashes.get(owner)
        entries.append(struct.pack('<BB', index, len(raw_name)) + raw_name + struct.pack('<I', own) +
                       (bytes.fromhex(mark)[:8] if mark else bytes(8)))
    files = struct.pack('<B', len(entries)) + b''.join(entries)
    blocks = [keys[i] for i in range(0, len(keys), REFS_STEP)]
    body = b''.join(struct.pack('<II', k | rows[k][1] << 24, rows[k][0]) for k in keys)
    return (b'AWI1' + files + struct.pack('<iffIII', months, respawn_delay, clear_delay, len(keys), REFS_STEP,
                                          len(blocks)) +
            b''.join(struct.pack('<I', k) for k in blocks) + body), len(keys), (months, respawn_delay, clear_delay)


def levelled_section(lists):
    """CONTAINER-LEVELLED-CONTENTS-60: the AWL1 section after AWI1, for the per-area tables only (the engine never
    reads it; tools/prepare_area_tables.py writes each area's lists): "AWL1" u32 lists, lists x { char id[32],
    u8 flags, u8 chance none, u16 entries, entries x { char id[32], u16 level } }, ascending id; an id that does not
    fit 32 printable bytes is left out."""
    out = [b'AWL1', b'']
    n = 0
    for ident in sorted(lists):
        flags, chance, entries = lists[ident]
        raw = record_id(ident)
        if not raw.strip(b'\0'):
            continue
        kept = [(record_id(e), lv) for e, lv in entries if record_id(e).strip(b'\0')]
        out.append(raw + struct.pack('<BBH', flags & 0xFF, chance, len(kept)) +
                   b''.join(e + struct.pack('<H', lv) for e, lv in kept))
        n += 1
    out[1] = struct.pack('<I', n)
    return b''.join(out)


def action_code(kind_action, owned):
    """The row's action code (byte 2): the kind in bits 0-1, owned in bit 2, a magic scroll in bit 3. The engine
    indexes its prompt table by it (aw_inventory.c AW_ItemPrompt); nothing is looked up per frame."""
    return (kind_action & (3 | ACT_MAGIC_SCROLL)) | (ACT_OWNED if owned else 0)


def owner_of(ref):
    """Whom taking the placed thing REF steals from (OpenMW 0.51 itemTaken): (owner id, 0) for its owner (ANAM), else
    (faction id, 1) for its owning faction (CNAM); None when neither is set or the id does not fit the engine's list
    (printable, at most OWNER_ID bytes)."""
    for key, faction in (('ANAM', 0), ('CNAM', 1)):
        if ref.get(key):
            ident = string(ref[key], key, errors='replace').strip().casefold()
            raw = ident.encode('ascii', 'replace')
            if not raw or len(raw) > OWNER_ID or any(b < 32 or b > 126 for b in raw):
                return None
            return ident, faction
    return None


def owner_list(owners):
    """The owners list after the rows: OWNERS maps reference -> (owner id, faction flag)."""
    pool, offsets, entries = bytearray(), {}, []
    for reference in sorted(owners):
        ident, faction = owners[reference]
        if ident not in offsets:
            offsets[ident] = len(pool)
            pool += ident.encode('ascii') + b'\0'
            if len(pool) > OWNER_POOL:
                raise SystemExit('[focus] the pool of owner ids is over %d bytes' % OWNER_POOL)
        entries.append(struct.pack('<IHBB', reference, offsets[ident], faction & 1, 0))
    return b'AWO1' + struct.pack('<I', len(entries)) + b''.join(entries) + struct.pack('<I', len(pool)) + bytes(pool)


def exterior_key(gx, gy):
    """The table key of an exterior cell: the top bit set (room numbers stay below it), then the grid x and y,
    each offset by 2048 into 12 bits. The engine computes the same from a game position (aw_inventory.c)."""
    return 0x80000000 | ((gx + GRID_BIAS) & 0xFFF) << 12 | ((gy + GRID_BIAS) & 0xFFF)


def cells_of(raw):
    """Every live CELL record: (name, interior, grid x, grid y, region id, its references)."""
    for tag, flags, payload in records(raw):
        if tag != 'CELL' or flags & 0x20:
            continue
        cell = None; interior = False; grid = (0, 0); region = ''; current = None; refs = []
        for key, value in subrecords(payload):
            if current is None and key == 'NAME' and cell is None:
                cell = string(value, 'NAME', errors='replace')
            elif current is None and key == 'DATA' and len(value) == 12:
                interior = bool(struct.unpack('<I', value[:4])[0] & 1)
                grid = struct.unpack_from('<ii', value, 4)
            elif current is None and key == 'RGNN':
                region = string(value, 'RGNN', errors='replace').casefold()
            elif key == 'FRMR':
                current = {'number': struct.unpack('<I', value)[0]}; refs.append(current)
            elif current is not None:
                current.setdefault(key, value)
        yield cell or '', interior, grid, region, refs


def cells_presented(raw, places=None):
    """cells_of(RAW) as the presented world has it (MOURNHOLD-EXTERIOR-CELLS-66): an interior cell that PLACES names
    (tools/presented_exterior.py build_places: the districts this build converts whole, each an exterior cell block
    of its own) is yielded as the exterior cells of its block, in the block's order, each with the references whose
    moved position falls in it. The move is presented_exterior.moved_position, the one the presented master gets (x
    and y plus the cell's offset, the height kept), so a table row and the world's own placement cannot drift; a
    reference without a position stays with the block's first cell. A moved reference is a copy: RAW's own are not
    changed. Without PLACES every cell is cells_of's own, in its order: the base game alone reads exactly what it
    read before. The readers that key their rows by area take their cells from here (placements, the levelled
    creature areas of tools/actor_stats.py, the placed item list of tools/prepare_item_models.py)."""
    if not places:
        yield from cells_of(raw)
        return
    from presented_exterior import moved_position
    for cell, interior, grid, region, refs in cells_of(raw):
        place = places.get(cell.casefold()) if interior and cell else None
        if place is None:
            yield cell, interior, grid, region, refs
            continue
        block, size = place['block'], place['size']
        per = {(block[0] + dx, block[1] + dy): [] for dx in range(size[0]) for dy in range(size[1])}
        for ref in refs:
            spot = (block[0], block[1])
            if len(ref.get('DATA', b'')) == 24:
                v = list(struct.unpack('<6f', ref['DATA']))
                spot, v[:3] = moved_position(place['offset'], v[0], v[1], v[2])
                ref = dict(ref, DATA=struct.pack('<6f', *v))
            if spot not in per:
                raise ValueError('A placement of %s (reference %d) falls outside its presented block'
                                 % (cell, ref['number']))
            per[spot].append(ref)
        for spot, moved in per.items():
            yield cell, False, spot, region, moved


def presented_counts(rooms, numbers, places):
    """{district name: {'rows', 'kinds': {kind: rows}, 'cells': {"x,y": rows}, 'left_in_room': rows}} of placements()'
    result ROOMS for the presented cells PLACES: what each district's block holds, and the rows still under its room
    number (none, when the readers took the places)."""
    out = {}
    for key, place in sorted(places.items()):
        kinds, cells = {}, {}
        for dx in range(place['size'][0]):
            for dy in range(place['size'][1]):
                gx, gy = place['block'][0] + dx, place['block'][1] + dy
                rows = rooms.get(exterior_key(gx, gy), ())
                cells['%d,%d' % (gx, gy)] = len(rows)
                for row in rows:
                    kinds[row[0]] = kinds.get(row[0], 0) + 1
        out[place['cell']] = {'rows': sum(cells.values()), 'kinds': dict(sorted(kinds.items())), 'cells': cells,
                              'left_in_room': len(rooms.get(numbers.get(key), ())) if key in numbers else 0}
    return out


def place_names(raw):
    """Exterior grid -> the name the original shows for a door leading there: the cell's own name (a town, a
    ruin), else its region's name."""
    regions = {}
    for tag, flags, payload in records(raw):
        if tag == 'REGN' and not flags & 0x20:
            fields = list(subrecords(payload))
            regions[string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()] = \
                string(first(fields, 'FNAM'), 'FNAM', errors='replace')
    out = {}
    for cell, interior, grid, region, _ in cells_of(raw):
        if not interior:
            out[grid] = cell.strip() or regions.get(region, '')
    return out


def placements(raw, objects, numbers, extras=None, presented=None):
    """Table key -> rows: interior cells of this master by their room number, exterior cells by exterior_key.
    EXTRAS (a dict, optional; AREA-TABLES-59): reference -> (trapped, key item id) of every placed container and door
    that has a trap (TNAM) or a key (KNAM), for the per-area tables (tools/prepare_area_tables.py).
    PRESENTED (cells_presented's places, optional): the districts this build presents as exterior cells have their
    rows under their block's exterior keys at the moved positions, where the game asks for them outdoors; a sign
    board's and a container's box is made from the moved position."""
    rooms = {}
    places = place_names(raw)
    for cell, interior, grid, region, refs in cells_presented(raw, presented):
        if interior:
            if not cell or cell.casefold() not in numbers:
                continue
            key = numbers[cell.casefold()]
        elif not all(abs(g) < GRID_BIAS for g in grid) or not refs:
            continue
        else:
            key = exterior_key(*grid)
        rows = rooms.setdefault(key, [])
        for ref in refs:
            if 'DELE' in ref or 'NAME' not in ref or len(ref.get('DATA', b'')) != 24:
                continue
            ident = string(ref['NAME'], 'NAME', errors='replace').casefold()
            record = objects.get(ident)
            if not record:
                continue
            kind, name, weight, value, action = record[:5]
            x, y, z = struct.unpack_from('<fff', ref['DATA'])
            board = None
            if kind == 'N':
                # SIGNPOST-NAMES-MISSING-65: the row sits at the board's centre; its id field holds the box
                if record[5] not in FOCUS_BOXES:
                    raise SystemExit('[focus] named activator %s (%s) has no measured box in FOCUS_BOXES'
                                     % (ident, record[5]))
                angles = struct.unpack_from('<fff', ref['DATA'], 12)
                scale = struct.unpack('<f', ref['XSCL'][:4])[0] if len(ref.get('XSCL', b'')) >= 4 else 1.0
                if not all(math.isfinite(v) for v in (x, y, z, scale, *angles)) or scale <= 0:
                    continue
                (x, y, z), halves = board_box(FOCUS_BOXES[record[5]], (x, y, z), angles, scale)
                board = struct.pack('<7f', *halves, *rotation_quaternion(reference_rotation(angles))) + bytes(IDENT - 28)
            elif kind == 'C' and len(record) > 7 and record[7] in CONTAINER_BOXES:
                # OUTDOOR-CONTAINER-AIM-66: a container carries its box as a board does (CONTAINER_BOXES); in a CHIM
                # room the engine asks the room record's placement box first, and a room map that is not a CHIM room
                # (the opening's Imperial Prison Ship and Census and Excise Office: 58 containers) uses this box
                angles = struct.unpack_from('<fff', ref['DATA'], 12)
                scale = struct.unpack('<f', ref['XSCL'][:4])[0] if len(ref.get('XSCL', b'')) >= 4 else 1.0
                if all(math.isfinite(v) for v in (x, y, z, scale, *angles)) and scale > 0:
                    (x, y, z), halves = board_box(CONTAINER_BOXES[record[7]], (x, y, z), angles, scale)
                    board = struct.pack('<7f', *halves, *rotation_quaternion(reference_rotation(angles))) + \
                        bytes(IDENT - 28)
            owned = int(kind in ('I', 'C') and bool(ref.get('ANAM') or ref.get('CNAM')))
            if kind == 'D':
                if 'DNAM' in ref:
                    name = string(ref['DNAM'], 'DNAM', errors='replace')
                elif len(ref.get('DODT', b'')) >= 8:
                    # leads outside: the place there, as the original names it (cell name, else region)
                    dx, dy = struct.unpack_from('<ff', ref['DODT'])
                    if math.isfinite(dx) and math.isfinite(dy):
                        name = places.get((math.floor(dx / CELL), math.floor(dy / CELL))) or name
                else:
                    continue          # a door that only opens: the hinged doors say their own name
            # the stable reference id (tools/ref_identity.py, CELL-CHANGES-59): the merged master's numbers name their
            # owning master (the base game's own numbers are their ids)
            if extras is not None and kind in ('C', 'D') and (ref.get('TNAM') or ref.get('KNAM')):
                key_id = string(ref['KNAM'], 'KNAM', errors='replace').strip().casefold() if ref.get('KNAM') else ''
                extras[stable_ref(MASTER, ref['number'])] = (bool(ref.get('TNAM')), key_id)
            rows.append((kind, owned, stable_ref(MASTER, ref['number']), x, y, z, weight, value, name,
                         board if board is not None else ident if kind in ('I', 'C') else '',
                         action_code(action, owned), owner_of(ref) if owned else None,
                         record[5:7] if kind in ('C', 'A') and len(record) > 5 else None,
                         lock_level(ref) if kind == 'C' else 0))
    return rooms


def window_rows(counts):
    """FOCUS-ROWS-WINDOW-OVERFLOW-66: (most rows, its centre key) of the 3 x 3 exterior windows the engine reads at
    once (aw_inventory.c focus_load: the player's cell and its eight neighbours); COUNTS {table key: rows}. Rooms are
    read alone (their key, MAX_ROWS)."""
    best, at = 0, 0
    for key in counts:
        if key < 0x80000000:
            continue
        gx, gy = (key >> 12) & 0xFFF, key & 0xFFF
        n = sum(counts.get(0x80000000 | ((gx + dx) & 0xFFF) << 12 | ((gy + dy) & 0xFFF), 0)
                for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        if n > best:
            best, at = n, key
    return best, at


def presented_places(receipt, cells):
    """MOURNHOLD-EXTERIOR-CELLS-66: the districts this build presents as exterior cells and converts whole, from the
    presented data stage's receipt RECEIPT (a path) and the build's module cells CELLS ("x,y:k ..."), as the image
    step and the scripts read them (tools/presented_exterior.py build_places); {} without a receipt."""
    if not receipt:
        return {}
    import presented_exterior
    return presented_exterior.build_places(json.loads(Path(receipt).read_text(encoding='utf-8')),
                                           presented_exterior.cells_of_text(cells or ''))[0]


def build(data_files, presented=None):
    from cell_numbers import load_table, room_numbers
    data = resolve_data_files(Path(data_files))
    raw = master_path(data).read_bytes()
    table, hashes = load_table(data)
    numbers = room_numbers(table)   # EXPANSION-BASE-ONLY-TABLES-66: every selected master's rooms
    extras = {}
    levelled = item_lists(raw)
    rooms = placements(raw, objects_of(raw, levelled), numbers, extras, presented)
    index, body, held, owners, containers = [], [], {}, {}, {}
    for number in sorted(rooms):
        rows = sorted(rooms[number], key=lambda r: r[2])
        if len(rows) > MAX_ROWS:
            held[number] = len(rows) - MAX_ROWS; rows = rows[:MAX_ROWS]
        index.append(struct.pack('<III', number, len(body), len(rows)))
        for kind, owned, reference, x, y, z, weight, value, name, ident, action, owner, contents, lock in rows:
            if contents is not None:
                containers[reference] = contents
            body.append(struct.pack('<BBBBIiiifi', ord(kind), owned, action, lock, reference, int(round(x)), int(round(y)),
                                    int(round(z)), weight, value) + pack_name_and_id(kind, name, ident))
            if owner:
                owners[reference] = owner
    window, window_key = window_rows({number: count for number, _, count in
                                      (struct.unpack('<III', head) for head in index)})
    if window > WINDOW_ROWS:
        raise SystemExit('[focus] %d rows in the 3 x 3 cells around key %#x: over the engine\'s %d (FOCUS_ROWS)'
                         % (window, window_key, WINDOW_ROWS))
    items = {number: sum(1 for r in rooms[number] if r[0] == 'I') for number in rooms}
    most_items = max([window_rows(items)[0]] + [n for k, n in items.items() if k < 0x80000000] + [0])
    if most_items > PLACED_ITEMS:
        raise SystemExit('[focus] %d placed items in one place: over the engine\'s %d (PLACED_MAX)'
                         % (most_items, PLACED_ITEMS))
    identities, references, respawn = reference_table(raw, hashes.get('Morrowind.esm'), hashes=hashes)
    payload = (b'AWF3' + struct.pack('<I', len(index)) + b''.join(index) + b''.join(body) + owner_list(owners) +
               contents_list(containers) + identities + levelled_section(levelled))
    assert all(len(r) == ROW for r in body)
    report = {'format': 'AWF3', 'rooms': len(index), 'rows': len(body), 'owners': len(owners),
              'containers': len(containers), 'references': references, 'levelled_item_lists': len(levelled),
              'actor_inventories': sum(1 for c in containers.values() if c[1] & ACTOR_INVENTORY),
              'respawn': dict(zip(RESPAWN_GMSTS, respawn)), 'bytes': len(payload),
              'sha256': hashlib.sha256(payload).hexdigest(), 'master_sha256': hashes.get('Morrowind.esm'),
              'held_rows': held, 'most_window_rows': window, 'window_limit': WINDOW_ROWS,
              'most_place_items': most_items, 'placed_limit': PLACED_ITEMS}
    # AREA-TABLES-59: traps and keys of placed containers and doors (not in focus.awf; read by
    # tools/prepare_area_tables.py from the stage's focus-extras.json)
    report['extras'] = {str(k): [int(t), key] for k, (t, key) in sorted(extras.items())}
    if presented:
        # only with presented districts, so the base game's receipt is the one before
        report['presented'] = presented_counts(rooms, numbers, presented)
        left = {name: row['left_in_room'] for name, row in report['presented'].items() if row['left_in_room']}
        if left:
            raise SystemExit('[focus] rows of presented districts left under their room numbers: %s' % left)
    return payload, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--presented-receipt', type=Path,
                   help='the presented data stage\'s receipt (tools/build.py gives it only with the module '
                        'tribunal-mournhold; MOURNHOLD-EXTERIOR-CELLS-66): the placed things of a district the build '
                        'converts are keyed outdoors, at their moved places')
    p.add_argument('--presented-cells', default='', help='the module\'s cells, with --presented-receipt')
    a = p.parse_args()
    presented = presented_places(a.presented_receipt, a.presented_cells)
    payload, report = build(a.data_files, presented)
    for name, row in (report.get('presented') or {}).items():
        print('[focus] presented district %s: %d placed things outdoors %s in cells %s' % (
            name, row['rows'], row['kinds'], row['cells']), flush=True)
    (a.out / 'id1').mkdir(parents=True, exist_ok=True)
    (a.out / 'id1/focus.awf').write_bytes(payload)
    extras = report.pop('extras')
    (a.out / 'focus-extras.json').write_text(json.dumps(extras, indent=0) + '\n', encoding='utf-8', newline='\n')
    (a.out / 'focus-receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    # ACTOR-STATS-ALL-61: every NPC and creature record's stat subrecords of the masters, for the areas' stat
    # sections the image step writes (tools/prepare_area_tables.py stats_section)
    import actor_stats
    recs, gmst = actor_stats.master_records(a.data_files)
    from cell_numbers import load_table, room_numbers
    data = resolve_data_files(Path(a.data_files))
    numbers = room_numbers(load_table(data)[0])
    # EXPANSION-BASE-ONLY-TABLES-66: the merged master (the base file's own bytes when it is alone)
    vocabulary = actor_stats.write_vocabulary(recs, gmst, actor_stats.levelled_by_area(
        master_path(data).read_bytes(), numbers, presented))
    (a.out / actor_stats.FILE_NAME).write_bytes(vocabulary)
    print('[focus] actor stats: %d NPC and %d creature records, %d bytes' % (len(recs['NPC_']), len(recs['CREA']),
                                                                             len(vocabulary)), flush=True)
    print('[focus] %d rooms, %d placed things, %d owned things with their owner, %d containers with contents, '
          '%d references in the identity table, %d bytes'
          % (report['rooms'], report['rows'], report['owners'], report['containers'], report['references'],
             report['bytes']), flush=True)


if __name__ == '__main__':
    main()
