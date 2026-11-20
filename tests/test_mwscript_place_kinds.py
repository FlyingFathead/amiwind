# SPDX-License-Identifier: GPL-3.0-only
"""PlaceItem (and the other Place calls) of a levelled creature list and of a scripted object no map places
(v0.0.67, MWSCRIPT-PLACE-OTHER-KINDS-62): carried out, not "not yet".

The original and OpenMW 0.51 (apps/openmw/mwscript/transformationextensions.cpp OpPlaceItem: a reference made from the
record at x, y, z in the player's cell; mwclass/creaturelevlist.cpp: a placed levelled list gives one creature of it at
the player's level) place both. Tribunal's fab_cent_fight_watch places the levelled list in_dwe_all_tribunal (two
centurions in Bamz-Amschend after the fight) and projectileMine places the activator trapProjectile, whose own script
flies it at the player and casts its spell; a dozen Bloodmoon scripts place effect activators the same way. Until
v0.0.67 the compiler left those calls "not yet": a list is no NPC or creature, and an activator needed a placed
reference of its record as the template of its entity. Now a list's PLAC row is an actor row with the levelled flag
(the engine rolls it from the actor table: aw_actors.c AW_ActorsLevelledText), and a scripted object with no placed
reference a point row (aw_mwhost.c point_spawn: an entity of its own, no model, its script on it). An object with
neither a placed reference nor a script stays "not yet". A script-made reference that SetDelete deletes leaves for good
(aw_mwhost.c placed_gone; OpenMW cellstore.cpp writeReferences keeps no deleted reference that no content file made).
Synthetic data only."""
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):          # src first on the path (TEST-WORKER-SYSPATH-32)
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

SRC = ROOT / 'engine' / 'aga' / 'src'


def sub(tag, data):
    if isinstance(data, str):
        data = data.encode('cp1252') + b'\0'
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def record(tag, *subs):
    payload = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(payload), 0, 0) + payload


def scpt(name, text):
    head = name.encode('cp1252').ljust(32, b'\0') + struct.pack('<5I', 0, 0, 0, 0, 0)
    return record('SCPT', sub('SCHD', head), sub('SCTX', text.encode('cp1252')))


def levc(ident, entries):
    body = [sub('NAME', ident), sub('DATA', struct.pack('<I', 1)), sub('NNAM', bytes([0])),
            sub('INDX', struct.pack('<I', len(entries)))]
    for entry, level in entries:
        body += [sub('CNAM', entry), sub('INTV', struct.pack('<H', level))]
    return record('LEVC', *body)


WATCH = '''Begin fight_watch
short state
if ( state == 0 )
\tPlaceItem "in_dwe_test" 4791 6127 12288 0
\tset state to 1
endif
End fight_watch
'''
MINE = '''Begin proj_mine
float myX
float myY
float myZ
float myRotZ
set myX to GetPos X
set myY to GetPos Y
set myZ to GetPos Z
set myRotZ to GetAngle Z
PlaceItem "trap_proj" myX myY myZ myRotZ
PlaceAtPC "plain_glow" 1 64 0
End proj_mine
'''
PROJ = '''Begin trap_script
short triggered
if ( triggered == 0 )
\tExplodeSpell "proj_spell"
\tset triggered to 1
\tSetDelete 1
endif
End trap_script
'''


def master():
    npdt = bytearray(96)
    struct.pack_into('<i', npdt, 40, 10)
    return b''.join([
        record('TES3', sub('HEDR', b'\0' * 300)),
        record('CREA', sub('NAME', 'centurion_t'), sub('MODL', 'r\\centurion.nif'), sub('FNAM', 'Centurion'),
               sub('NPDT', bytes(npdt)), sub('FLAG', struct.pack('<I', 0x48))),
        levc('in_dwe_test', [('centurion_t', 1)]),
        record('ACTI', sub('NAME', 'trap_proj'), sub('MODL', 'w\\magic_target.nif'), sub('SCRI', 'trap_script')),
        record('ACTI', sub('NAME', 'plain_glow'), sub('MODL', 'w\\glow.nif')),
        scpt('fight_watch', WATCH), scpt('proj_mine', MINE), scpt('trap_script', PROJ)])


class PlaceKindsCompile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from mwscript.gamedata import GameData
        from mwscript.compiler import compile_program
        tmp = Path(tempfile.mkdtemp(prefix='aw-place-kinds-'))
        try:
            (tmp / 'Morrowind.esm').write_bytes(master())
            cls.data = GameData().load(tmp)
            cls.prog, compiled = compile_program(cls.data, None)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        cls.names = {c.name.casefold(): c for c in compiled}

    def test_placeitem_of_a_list_and_of_a_scripted_object_is_carried_out(self):
        # before v0.0.67 both read ['placeitem'] here (MWSCRIPT-PLACE-OTHER-KINDS-62)
        self.assertEqual(self.names['fight_watch'].notyet, [])
        self.assertEqual(self.names['proj_mine'].notyet, ['placeatpc'])   # the unscripted, unplaced glow stays
        self.assertIn('trap_script', self.names)

    def test_the_place_rows_say_how_the_engine_makes_them(self):
        from mwscript.codegen import PLACE_KINDS
        from mwscript.opcodes import NONE
        from mwscript import awms
        from mwscript.compiler import bindings
        rows = {r['key']: r for r in self.prog.place_rows()}
        lev, proj, glow = rows['in_dwe_test'], rows['trap_proj'], rows['plain_glow']
        self.assertEqual((lev['kind'], lev['carried'], lev['levelled'], lev['point']), (PLACE_KINDS['actor'], True, True, False))
        self.assertEqual((proj['kind'], proj['carried'], proj['point'], proj['template']),
                         (PLACE_KINDS['other'], True, True, 0))
        self.assertEqual(proj['script'], self.prog.scripts.index['trap_script'])
        self.assertEqual((glow['carried'], glow['point']), (False, False))
        f = awms.read(awms.write(self.prog, list(self.names.values()), bindings(self.prog))[0])
        flags = {}
        order = self.prog.place_rows()
        for k in range(f['PLAC_rows']):
            flags[order[k]['key']] = struct.unpack_from('>HHIHBB', f['PLAC'], 12 * k)[5]
        self.assertEqual(flags, {'in_dwe_test': 1 | 4, 'plain_glow': 0, 'trap_proj': 1 | 2})
        self.assertNotEqual(proj['script'], NONE)


class PlaceKindsEngine(unittest.TestCase):
    """The engine side, read from its source (the parts run natively elsewhere: the list roll in
    tests/test_aw_actors_native.py, the host's place call through the same place_here as before)."""

    @staticmethod
    def code(name):
        return (SRC / name).read_text(encoding='utf-8')

    def test_the_row_flags_reach_the_spawn(self):
        host = self.code('aw_mwhost.c')
        self.assertIn('out->point=(r[11]&2)!=0;out->levelled=(r[11]&4)!=0;', host)
        spawn = host[host.index('static int placed_spawn(unsigned key){'):]
        spawn = spawn[:spawn.index('\n}\n')]
        self.assertIn('if(r.point)e=r.kind==PLACE_ACTOR?NULL:point_spawn(key);', spawn)
        self.assertIn('AW_MwvmLevelledScript(picked,&script)', spawn)
        text = host[host.index('static char *placed_text('):]
        self.assertIn('text=own=AW_ActorsLevelledText(id,key,&n,picked);', text[:text.index('\n}\n')])
        point = host[host.index('static edict_t *point_spawn(uint32_t key){'):]
        point = point[:point.index('\n}\n')]
        self.assertIn('e->v.solid=SOLID_NOT;', point)
        self.assertIn('v->_float=(float)key;', point)
        self.assertNotIn('setmodel', point.lower())

    def test_a_deleted_script_made_reference_leaves_for_good(self):
        host = self.code('aw_mwhost.c')
        flush = host[host.index('static void deleted_flush(void){'):]
        flush = flush[:flush.index('\n}\n')]
        self.assertLess(flush.index('deleted_script(deleted_pending[i]);'), flush.index('placed_gone(deleted_pending[i]);'))
        gone = host[host.index('static void placed_gone(uint32_t ref){'):]
        gone = gone[:gone.index('\n}\n')]
        self.assertIn('AW_ActorsPlacedForget(ref);', gone)
        self.assertIn('r->fields=0;AW_LedgerTidy(&aw_ledger,ref);', gone)
        self.assertIn('ref<AW_ACTORS_PLACED || ref>(AW_ACTORS_PLACED|0xFFFFF)', gone)


if __name__ == '__main__':
    unittest.main()
