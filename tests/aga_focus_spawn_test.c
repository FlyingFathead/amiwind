/* SPDX-License-Identifier: GPL-2.0-or-later
 * ROOM-AIM-ROWS-OUTDOORS-AFTER-COURTYARD-68: the use key's focus table over server spawns, on the real loaded-model
 * table (model.c Mod_FindName and Mod_ClearAll, linked) and the focus table's own map test, cut from aw_inventory.c
 * into focus_spawn_slice.c by tests/test_room_focus_spawn.py (its statics, AW_AreaPlaceKeys, AW_FocusServerReset and
 * focus_refresh). focus_load stands in for the read (its first lines: the map, room or outdoors, the place's keys) and
 * counts the reads. Synthetic model names only.
 *
 * Scenario: the session has loaded as many models as the table's static base (256), as the opening has by its second
 * visit to the courtyard; then the census office's back room, the courtyard and back by its door, a load of a save in
 * the room (the same map again) and the courtyard again. Every spawn must leave the focus table to be read for the new
 * map at its first frame, a room as a room. On the source before the fix the slice has no reset (an empty stand-in, as
 * SV_SpawnServer called none): back in the room from the courtyard nothing is read and the table stays outdoors. */
#define main alias_residency_fixture_main
#include "aga_alias_residency_test.c"
#undef main
extern model_t mod_known[256];extern int mod_numknown;
extern model_t *Mod_FindName(char *);
extern void Mod_ClearAll(void);
server_t sv;
static edict_t player;
static int outdoor_map,reads;
static void stats_drain(void){}
static int focus_to_source(const float *local,float *game){
    (void)local;if(!outdoor_map)return 0;
    game[0]=-10956.0f;game[1]=-72381.0f;game[2]=264.0f;   /* the courtyard door's spot in the game's units */
    return 1;
}
static void focus_load(void);
#include "focus_spawn_slice.c"
/* the first lines of aw_inventory.c focus_load: the map read, outdoors when the player's spot converts */
static void focus_load(void){
    float game[3];
    focus_world=sv.worldmodel;focus_outdoor=0;
    if(focus_to_source(player.v.origin,game)){
        focus_outdoor=1;focus_gx=(int)floor(game[0]/FOCUS_CELL);focus_gy=(int)floor(game[1]/FOCUS_CELL);
    }
    place_n=1;place_keys[0]=focus_outdoor?0x80000000ul:229ul;place_gen++;place_world=sv.worldmodel;
    reads++;
}
/* one model of the map's precache list, loaded (model.c Mod_ForName: found by name or given a slot, then present) */
static model_t *load(const char *name,modtype_t type){
    model_t *m=Mod_FindName((char *)name);
    m->type=type;m->needload=0;
    return m;
}
/* sv_main.c SV_SpawnServer's order: the models unreferenced (Host_ClearMemory), the server cleared, the resets, the
 * world model; the map's other models after it */
static model_t *spawn(const char *name,int outdoor,int aliases_from,int aliases_to){
    int i;char path[64];model_t *world;
    Mod_ClearAll();
    memset(&sv,0,sizeof(sv));
    AW_FocusServerReset();
    Q_strncpy(sv.name,(char *)name,sizeof(sv.name)-1);
    world=sv.worldmodel=load(name,mod_brush);
    for(i=aliases_from;i<aliases_to;i++){sprintf(path,"progs/m%03d.mdl",i);load(path,mod_alias);}
    outdoor_map=outdoor;
    return world;
}
/* the new map's first client frame (aw_placed.c AW_PlacedLink -> AW_PlacedRefresh): one read, of the right kind */
static void first_frame(const char *what,int outdoor,int *failed){
    unsigned long keys[AREA_MAX],gen;int before=reads,before_keys=AW_AreaPlaceKeys(keys,AREA_MAX,&gen);
    focus_refresh(&player);
    focus_refresh(&player);     /* the next frame: nothing more to read */
    if(before_keys>=0){printf("FAIL %s: the place's keys of the last map answered before the read\n",what);*failed=1;}
    if(reads!=before+1){printf("FAIL %s: %d reads of the focus table (one expected)\n",what,reads-before);*failed=1;}
    else if(focus_outdoor!=outdoor){printf("FAIL %s: the focus table is %s\n",what,focus_outdoor?"outdoors":"a room's");*failed=1;}
    else printf("ok %s: read once, %s\n",what,outdoor?"outdoors":"the room's rows");
}
int main(void){
    model_t *room,*court,*back,*again;int failed=0;
    reset();memset(mod_known,0,sizeof(mod_known));mod_numknown=0;
    /* a session within the base: every world keeps a slot of its own (the old behaviour too) */
    spawn("maps/census.bsp",0,0,20);first_frame("small session: the room",0,&failed);
    spawn("maps/sncourt-chim.chim",1,0,10);first_frame("small session: the courtyard",1,&failed);
    spawn("maps/census.bsp",0,0,20);first_frame("small session: back in the room",0,&failed);
    /* the session at the base: the room spawned again (the same map) with 256 models loaded */
    room=spawn("maps/census.bsp",0,0,255);
    if(mod_numknown!=256){printf("FAIL setup: %d models loaded, 256 expected\n",mod_numknown);return 1;}
    first_frame("the back room spawned again, 256 models loaded",0,&failed);
    court=spawn("maps/sncourt-chim.chim",1,0,100);
    printf("the courtyard's world in model slot %d, the room's was in slot %d\n",(int)(court-mod_known),(int)(room-mod_known));
    first_frame("the courtyard",1,&failed);
    back=spawn("maps/census.bsp",0,0,255);
    printf("back in the room: its world in model slot %d (the courtyard's %d)\n",(int)(back-mod_known),(int)(court-mod_known));
    if(back!=court){printf("FAIL setup: the model table gave the room a slot of its own; the case is not made\n");return 1;}
    first_frame("back in the room from the courtyard (its door)",0,&failed);
    again=spawn("maps/census.bsp",0,0,255);
    if(again!=back){printf("FAIL setup: the same map got another slot\n");return 1;}
    first_frame("a save loaded in the room (the same map again)",0,&failed);
    spawn("maps/sncourt-chim.chim",1,0,100);first_frame("the courtyard again",1,&failed);
    if(failed){puts("FAIL: a spawn left the focus table of the last map");return 1;}
    puts("PASS: every spawn reads the new map's focus table at its first frame, a room as a room, whatever its model slot");
    return 0;
}
