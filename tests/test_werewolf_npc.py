# SPDX-License-Identifier: GPL-3.0-only
"""The NPCs a script turns into werewolves drawn with the player's werewolf set (NPC-WEREWOLF-NO-MODEL-66, v0.0.68).

Rules from OpenMW 0.51 (read, not copied): mwrender/npcanimation.cpp updateNpcBase 469-531 and getBodyParts 1160-1195
(any NPC in werewolf form: the werewolf's skeleton and animation, its skin as the body), mwmechanics/
mechanicsmanagerimp.cpp setWerewolf 1880-1908 (any actor: every item off), aicombataction.cpp prepareNextAction 170-174
and character.cpp updateWeaponState 1283-1288 (a werewolf fights hand to hand). The form holds after death.

Natively, on the real aw_view.c code (tests/aga_werewolf_parts_test.c section (i), cut by tests/test_werewolf_change.py):
the set comes in with the first turned NPC on the map, three share one model and one table, the player's change back
while an NPC is a werewolf keeps the shared body and its table, the last one out releases, 50 changes with the player
turning too leave the model table, the pinned bytes and the tables as before. Here the wiring the native test cannot
reach (the send names the turned NPCs and picks their frames on the werewolf's table, the renderer's swap, the empty
hands, the list sized for every werewolf of the game from the masters' script table) and that run's lines. Each test
fails on the engine before v0.0.68 wolfnpc: a turned NPC was only a mark (16 at most) and kept its own body."""
import json
import os
import re
import shutil
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'


def code(name):
    return (SRC / name).read_text(encoding='utf-8', errors='replace')


def body(text, head):
    at = text.index(head)
    return text[at:text.index('\n}\n', at) + 3]


class WerewolfNpcWiring(unittest.TestCase):
    def test_the_send_names_the_turned_npcs_and_picks_on_the_werewolf_table(self):
        kit = code('aw_animkit.c')
        send = body(kit, 'void AW_AnimPickPreSend(void) {')
        # every send begins and ends with the view's list (also when nothing is picked), the turned NPCs on the map
        # named, their table the werewolf's, whatever dbg animkit pick says
        self.assertLess(send.index('AW_ViewWereNpcSend(0,0);'), send.index('for(i=1+svs.maxclients;'))
        self.assertIn('if(!picking && !weres){AW_ViewWereNpcSend(3,0);return;}', send)
        self.assertTrue(send.rstrip().endswith('AW_ViewWereNpcSend(3,0);\n}'))
        self.assertIn('were=weres && AW_MwscriptWerewolfNpc(e);', send)
        self.assertIn('AW_ViewWereNpcSend(1,i);', send)
        self.assertIn('if(!wt && !(wt=AW_ViewWereNpcTable())){weres=were=0;}', send)
        self.assertIn('if(were)t=wt;', send)
        self.assertIn('if(g<0){if(!were)continue;g=AW_ANIM_IDLE;}', send)
        self.assertIn('if(p->table!=t){', send)                  # into or out of the form: the picks start again
        self.assertIn('drive(p,e,t,a,g,storm,were);', send)
        self.assertIn('if(were && p->applied)AW_ViewWereNpcSend(2,i);', send)
        # the own model's cache check and a forced group are for the other actors only
        self.assertLess(send.index('if(were)t=wt;'), send.index('!Cache_Check(&m->cache)'))
        drive = body(kit, 'static void drive(picker_t *p,edict_t *e,const aw_skel_table_t *t,const aw_anim_t *a,int g,'
                          'int storm,int were) {')
        self.assertIn('p->weapon=were?AW_PW_HANDTOHAND:weapon_of(e);', drive)          # its claws
        self.assertIn("s.move=g==AW_ANIM_DODGEL?AW_PM_LEFT:AW_PM_RIGHT;", drive)       # a sidestep walks sideways
        self.assertIn('gi=AW_SkelGroup(t,"idle");', drive)        # never the own frame on the werewolf's body
        for head in ('void AW_AnimPickCast(edict_t *e,int range) {', 'int AW_AnimPickScripted(edict_t *e,const char *group,int count) {'):
            self.assertIn('pick_table(e)', body(kit, head))
        self.assertIn('if(p && p->table && AW_MwscriptWerewolfNpc(e))return p->table;', kit)

    def test_the_renderer_draws_the_werewolf_body_for_the_named_entities(self):
        lod = code('aw_npc_lod.c')
        model = body(lod, 'model_t *AW_NpcLodModel(entity_t *e)\n{')
        self.assertLess(model.index('model_t *were = were_model(e);'), model.index('if (!track_valid'))
        self.assertIn('model_t *(*aw_npc_were_model)(int entity);', lod)
        frame = body(lod, 'void AW_NpcLodFrame(void)\n{')
        self.assertIn('if (aw_npc_were_model && were_model(e))', frame)   # no level of its own model is planned
        # the residents from parts leave a turned NPC to the werewolf's body
        self.assertIn('if(aw_npc_were_model && aw_npc_were_model(index))return NULL;',
                      body(code('aw_npc_parts.c'), 'static edict_t *resident_of(entity_t *ent)\n{'))
        view = code('aw_view.c')
        self.assertIn('aw_npc_were_model=npc_were_model;', body(view, 'void AW_ViewInit(void) {'))
        drawn = body(view, 'static model_t *npc_were_model(int entity) {')
        self.assertIn('npc_were.drawn[entity>>3]&(1<<(entity&7))', drawn)
        # the one count: a model or table the turned NPCs draw is kept by the player's sets' release
        self.assertIn('Cache_Pin(&m->cache,(on || npc_were_holds(m)) && player_cache_cvar.value)', view)
        self.assertIn('|| npc_were_holds(m))return;', body(view, 'static void part_drop(model_t *m) {'))
        self.assertIn('if(npc_were_holds_table(were_tables[k])){were_tables[k][0]=0;continue;}',
                      body(view, 'static void were_tables_release(void) {'))
        # a new map forgets the flushed model (its table is given back by the first send with none on the map)
        self.assertIn('npc_were.model=NULL;npc_were.table=NULL;npc_were.count=0;npc_were.failed=0;',
                      body(view, 'void AW_ViewSceneSpawn(void) {'))
        status = body(view, 'void AW_ViewWerewolfStatus(void) {')
        self.assertIn('turned NPCs on this map: %d, drawn as the werewolf: %d', status)
        self.assertIn("the werewolf's frame %d", status)

    def test_a_turned_npc_holds_nothing(self):
        items = code('aw_items.c')
        self.assertIn('int (*aw_items_werewolf)(edict_t *actor);', items)
        self.assertIn('turned(actor) || !frames_match(', body(items, 'int AW_ItemsShow(edict_t *actor,edict_t *out[AW_ITEMS_KINDS]) {'))
        self.assertIn('turned(actor) || !frames_match(', body(items, 'void AW_ItemsUpdate(edict_t *actor,edict_t *items[AW_ITEMS_KINDS]) {'))
        self.assertIn('|| turned(a)){', body(items, 'void AW_ItemsCarriedUpdate(void) {'))
        self.assertIn('aw_items_werewolf=AW_MwscriptWerewolfNpc;', code('aw_mwhost.c'))

    def test_every_werewolf_of_the_game_fits_the_list(self):
        # the masters' script table (docs/mwscript-features.json): every NPC a script turns, placed, placed by a
        # script or given by a levelled list; the old list held 16 and refused the rest (the maze alone places 31)
        host = code('aw_mwhost.c')
        limit = int(re.search(r'#define WERE_NPCS (\d+)', host).group(1))
        scripts = json.loads((ROOT / 'docs/mwscript-features.json').read_text(encoding='utf-8'))
        rows = scripts['scripts'] if isinstance(scripts, dict) and 'scripts' in scripts else scripts
        total, who = 0, {}
        for row in rows:
            refs = row.get('refs') or {}
            if 'becomewerewolf' not in (row.get('functions') or {}) or not (refs.get('records') or {}).get('NPC_'):
                continue
            placed = sum(int(v.get('NPC_', 0)) for v in (refs.get('placed') or {}).values())
            n = placed + int(refs.get('placed_by_scripts') or 0) + int(refs.get('levelled') or 0)
            who[row['id']] = n
            total += n
        self.assertIn('weremazeScript', who)
        self.assertGreaterEqual(who['weremazeScript'], 31)
        for script in ('skaalwere1Script', 'wereskaalScript', 'wildwereScript', 'Werewolfwilderness', 'werewolf_connor',
                       'wereCeremonyScript'):
            self.assertIn(script, who)                              # the Skaal hunt, the wild hunt, the wilderness
        self.assertGreater(total, 16)
        self.assertLessEqual(total, limit, who)
        self.assertEqual(limit, 255)                                # as many as the saved block holds (one count byte)
        rules = code('aw_forced_rules.c')
        self.assertIn('if(count<0 || count>255 || 79+4*count>capacity)return -1;', rules)
        # packed, in the order turned; a full list lets the oldest go; one bit test for an actor not turned
        setter = body(host, 'static void were_npc_set(uint32_t ref,int set){')
        self.assertIn('memmove(were_npc,were_npc+1,(size_t)(WERE_NPCS-1)*sizeof(were_npc[0]));', setter)
        self.assertIn('were_bloom_build();', setter)
        ask = body(host, 'int AW_MwscriptWerewolfNpc(struct edict_s *e){')
        self.assertLess(ask.index('were_bloom[WERE_BIT(r)>>3]'), ask.index('were_npc_find(r)'))
        self.assertIn('return AW_WerePack(out,capacity,&were,were_npc,were_npc_n);', host)
        self.assertIn('were_npc_n=n;were_bloom_build();', body(host, 'static int were_import(const unsigned char *p,int bytes){'))
        self.assertIn('were_npc_n=0;were_bloom_build();', body(host, 'static void forced_reset(void){'))
        # the form holds after death: only UndoWerewolf takes a reference out
        self.assertEqual(host.count('were_npc_set('), 2)            # its definition and the script's call
        case = host[host.index('case AWF_BECOMEWEREWOLF:case AWF_UNDOWEREWOLF:case AWF_ISWEREWOLF:{'):]
        self.assertIn('were_npc_set(ref,set);', case[:case.index('case AWF_SETWEREWOLFACROBATICS:{')])

    def test_the_tests_and_docs_are_listed(self):
        files = (ROOT / 'tools/release-files.json').read_text(encoding='utf-8')
        self.assertIn('"tests/test_werewolf_npc.py"', files)
        third = (ROOT / 'docs/THIRD_PERSON.md').read_text(encoding='utf-8')
        self.assertIn('NPC-WEREWOLF-NO-MODEL-66', third)
        effects = json.loads((ROOT / 'config/mwscript-effects.json').read_text(encoding='utf-8'))['functions']
        for name in ('becomewerewolf', 'undowerewolf'):
            self.assertNotIn('An NPC only', effects[name]['missing'])


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class WerewolfNpcNative(unittest.TestCase):
    def test_the_view_draws_turned_npcs_with_the_shared_set(self):
        # tests/aga_werewolf_parts_test.c section (i) on the real aw_view.c slice, by number
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import test_werewolf_change as change
        out = change.run_view_slice(self)
        self.assertIn('(i) a turned NPC drawn with the werewolf body (progs/parts/0f/0f0f0f0f03.mdl on '
                      'progs/werewolf.awsk), three sharing it, let go by the last one out', out)
        self.assertIn("(i) the player's change back while an NPC is a werewolf keeps the shared body and its table; "
                      "the NPC's going while he is one keeps his", out)
        self.assertRegex(out, r'\(i\) 50 changes with the player turning too: model table 5 slots in use, 20480 bytes '
                              r'pinned, 20480 bytes in the cache, as before; the NPCs\' set in \d+ times and let go '
                              r'\d+ times, no table kept')
        # WEREWOLF-RACE-SCALE-68 (wolffight): section (j), the werewolf at the size of the race of the one turned
        self.assertIn("(j) the werewolf at the race's size: the player's 0.95 x 1.02 (read once), a Nord man's 1.20 x "
                      "1.06, a dark elf woman's 0.90 x 1.00, no record 1 x 1; a crowd sized 4 a send", out)


if __name__ == '__main__':
    unittest.main()
