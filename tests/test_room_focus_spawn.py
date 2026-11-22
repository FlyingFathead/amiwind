# SPDX-License-Identifier: GPL-3.0-only
"""Back in a room from an outdoor place, the use key's focus table is the room's (ROOM-AIM-ROWS-OUTDOORS-AFTER-COURTYARD-68).

On the v0.0.68-dev6 image, in the opening journey, the census office's back room answered the use key with the town's
381 outdoor rows after the player went out to the courtyard and back in by its door: the Iron Dagger on the table
(`chargen dagger`, reference 119577) had no focus row. The focus table (aw_inventory.c focus_refresh) told a new map by
the world model's pointer alone; once the session has loaded as many models as the loaded-model table's static base
(model.c Mod_FindName, ENGINE-MODEL-TABLE-58: 256), a world of another name takes an unreferenced slot, here the one the
courtyard's world had just used, so the room was never read and the table stayed outdoors (and with it the place's
keys the per-area tables ask for). Now every server spawn leaves the focus table belonging to no map
(AW_FocusServerReset, called by sv_main.c SV_SpawnServer), so the first frame of every map reads its own.

The behaviour runs natively on the real model table (model.c linked) with the focus table's map test cut out of
aw_inventory.c (file-static functions of an engine file too large to link alone) into a slice that
tests/aga_focus_spawn_test.c includes. On the source before the fix the slice has no reset (an empty stand-in, as
SV_SpawnServer called none) and the check fails back in the room. AMIWIND_RUNTIME_SOURCE selects another engine tree
for that comparison."""
import re
import tempfile
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(native.SOURCE) / 'src'


def function(text, head):
    """The C definition starting at HEAD: to the end of its line when it closes there, else to its brace at column 0."""
    at = text.index(head)
    line = text[at:text.index('\n', at)]
    if line.rstrip().endswith('}') and line.count('{') == line.count('}'):
        return line + '\n'
    return text[at:text.index('\n}\n', at) + 3]


def line(text, head):
    at = text.index('\n' + head) + 1
    return text[at:text.index('\n', at) + 1]


def focus_slice(text):
    """aw_inventory.c's focus table map test, as one C text (definitions before their use)."""
    parts = [
        line(text, 'static model_t *focus_world;'),
        line(text, '#define FOCUS_CELL '),
        line(text, 'static int focus_outdoor,focus_gx,focus_gy;'),
        line(text, '#define AREA_MAX '),
        line(text, 'static unsigned long place_keys[AREA_MAX],place_gen;static int place_n;static model_t *place_world;'),
        function(text, 'int AW_AreaPlaceKeys(unsigned long *keys,int max,unsigned long *generation){'),
    ]
    if 'void AW_FocusServerReset(void){' in text:
        parts.append(function(text, 'void AW_FocusServerReset(void){'))
    else:
        parts.append('void AW_FocusServerReset(void){}   /* the old source: SV_SpawnServer reset nothing here */\n')
    parts.append(function(text, 'static void focus_refresh(const edict_t *p){'))
    return '/* cut from aw_inventory.c by tests/test_room_focus_spawn.py */\n' + ''.join(parts)


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8', errors='replace'), flags=re.S)


class RoomFocusSpawnNativeTests(unittest.TestCase):
    def test_every_spawn_reads_the_new_maps_focus_table_whatever_its_model_slot(self):
        """The back room, the courtyard and back by its door, a save loaded in the room and the courtyard again, with the
        session at the model table's base: the courtyard's world takes the room's slot and the room the courtyard's;
        every first frame reads the focus table once, a room as a room, and the place's keys of the last map never
        answer before the read. A session within the base behaves the same."""
        inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8', errors='replace')
        with tempfile.TemporaryDirectory(prefix='amiwind-focusspawn-') as tmp:
            (Path(tmp) / 'focus_spawn_slice.c').write_text(focus_slice(inventory), encoding='utf-8')
            native.NativeSourceTests().compile_run(
                'aga_focus_spawn_test.c', [SRC / name for name in (*native.SKEL_MODEL, 'mathlib.c')],
                cflags=['-I' + tmp, '-fsanitize=undefined', '-fno-sanitize-recover=all', '-Wl,--wrap=malloc'])


class RoomFocusSpawnWiringTests(unittest.TestCase):
    def test_every_server_spawn_resets_the_focus_table_before_the_new_entities(self):
        server = code('sv_main.c')
        spawn = server[server.index('void SV_SpawnServer (char *server)\n#endif\n{'):]
        spawn = spawn[:spawn.index('\n}\n')]
        reset = spawn.index('AW_FocusServerReset();')
        self.assertLess(spawn.index('memset (&sv, 0, sizeof(sv));'), reset)
        self.assertLess(reset, spawn.index('ED_LoadFromFile (sv.worldmodel->entities);'))
        # declared by its caller, not in a header a world or actor stage keys
        self.assertIn('void AW_FocusServerReset(void);', spawn)
        for header in SRC.glob('*.h'):
            self.assertNotIn('AW_FocusServerReset', header.read_text(encoding='utf-8', errors='replace'), header.name)

    def test_the_reset_leaves_the_table_and_the_place_keys_to_no_map(self):
        inventory = code('aw_inventory.c')
        self.assertIn('void AW_FocusServerReset(void){focus_world=NULL;place_world=NULL;}', inventory)
        refresh = function(inventory, 'static void focus_refresh(const edict_t *p){')
        self.assertIn('if(focus_world!=sv.worldmodel){focus_load();return;}', refresh)
        keys = function(inventory, 'int AW_AreaPlaceKeys(unsigned long *keys,int max,unsigned long *generation){')
        self.assertIn('if(place_world!=sv.worldmodel || !place_world)return -1;', keys)


if __name__ == '__main__':
    unittest.main()
