/* SPDX-License-Identifier: GPL-2.0-or-later
 * PLAZA-FABRICANTS-LIVE-AT-START-67: the script host's object state over server spawns, run with aw_mwhost.c's own
 * functions and the real world change list (aw_ledger.c). tests/test_same_map_reload.py cuts the functions out of
 * aw_mwhost.c into mwhost_reload_slice.c (the edicts by reference, the map's attach and ledger_attach, the hide and
 * show of the world change list, Disable and Enable, a save's import, AW_MwscriptServerReset and the tick's map test);
 * this file is the server around them.
 *
 * The fault, by number (v0.0.67 release image, proofs D1, D1b and A2): a server spawn of the map already loaded (a
 * teleport inside the Plaza Brindisi Dorom, frame map mh0005; Seyda Neen spawned again while it is the map in play)
 * gets the same world model slot back by name and keeps its name, so the tick never attached the map again: the
 * edicts the spawn made were drawn although the world change list holds their references disabled, and a script's
 * Disable of a reference disabled already did nothing. The map's actors, as the image's entity text has them
 * (aw_source_id, aw_ref, origin): the Plaza's 7, four of them the fabricants fab_attack_1 / fab_attack_2 disable until
 * An Attack on Mournhold; Seyda Neen's 16, three of them disabled once by the run-once Startup.
 *
 * Every edict of an actor draws a model (modelindex) until a hide takes it off; spawn() makes the map's edicts again,
 * as SV_SpawnServer's ED_LoadFromFile does, then runs the tick's map test as the first tick after the spawn does. */
#include "quakedef.h"
#include "aw_ledger.h"
#include "aw_save.h"
#include "aw_mwcode.h"
#include "aw_tryalloc.h"
#include <assert.h>

server_t sv;char *pr_strings;
#define EDICTS 32
static edict_t edicts[EDICTS];static eval_t refs[EDICTS];
static model_t world;           /* the world model slot: the same one for every spawn of a map (model.c Mod_FindName) */
static char strings[64];
static int links;
edict_t *EDICT_NUM(int n){assert(n>=0 && n<EDICTS);return &edicts[n];}
int NUM_FOR_EDICT(edict_t *e){return (int)(e-edicts);}
void SV_LinkEdict(edict_t *e,qboolean touch){(void)e;(void)touch;links++;}
int SV_ModelIndex(char *name){(void)name;return 9;}
int ChimRoom_Hide(unsigned reference,int hide){(void)reference;(void)hide;return 0;}
/* the host's own file-static helpers the cut functions call, outside this check: no CHIM exterior placements, no
 * fights, no actor spawned by an Enable, no lock data, a frame map (no room number) */
static int exterior_hide(uint32_t ref,int hide){(void)ref;(void)hide;return 0;}
static void disabled_fight_end(edict_t *e){(void)e;}
static void enabled(uint32_t ref){(void)ref;}
static int ledger_data_lock(uint32_t ref){(void)ref;return 0;}
static void ledger_place(aw_ledger_row_t *r){(void)r;}   /* a taken row's place: unknown (read on every map) */
int (*aw_object_drawn)(unsigned reference);               /* no placed item models here */
static long map_cell_number(void){return 0;}
static int AW_MapId(const char *name){return !strcmp(name,"seyda")?1:!strcmp(name,"mh0005")?2:-1;}
#define field_ref(e) (&refs[(e)-edicts])
/* the host's state the cut functions share (aw_mwhost.c declares the same) */
static int leaving_count,attached_map;
static char map_name[64];static void *map_model,*script_model;
static unsigned long server_spawns;
#define EDICT_REFS 1024
static struct {uint32_t ref;int entity;} edict_refs[EDICT_REFS];static int edict_ref_count;
#include "mwhost_reload_slice.c"

typedef struct {const char *id;uint32_t ref;float x,y,z;int disabled;} actor_t;
/* frame map mh0005, the Plaza's east cell (-3,-30): the image's entity text */
static const actor_t plaza[7]={
    {"guard_highord_attack",4218686,-674.04297f,-404.21094f,12.32150f,0},
    {"fabricant_verm_attack",4218689,-994.16162f,-207.16016f,43.04281f,1},
    {"fabricant_hulkin_attack",4218690,-841.62988f,18.83594f,39.12556f,1},
    {"fabricant_verm_attack",4218692,-824.82031f,126.27344f,43.04281f,1},
    {"fabricant_hulkin_attack",4218693,-983.72656f,182.06641f,39.12557f,1},
    {"guard_helseth_attack",4218697,-865.37305f,-87.98828f,39.12556f,0},
    {"guard_highord_attack",4218700,-777.88623f,218.89062f,43.83478f,0}};
/* seyda-chim.chim, Seyda Neen's 16 map actors */
static const actor_t seyda[16]={
    {"erene llenim",128960,-861.91357f,19.81055f,3.52590f,0},{"indrele rathryon",128961,-221.86353f,29.88867f,22.11302f,0},
    {"vodunius nuccius",128962,21.41455f,247.87305f,59.20172f,0},{"eldafire",128963,-39.39380f,860.58984f,70.00381f,0},
    {"fargoth",128964,188.30493f,115.45898f,42.14743f,0},{"Imperial Guard",128965,-26.33594f,416.61719f,58.33927f,0},
    {"Imperial Guard",128966,-42.72119f,979.89648f,70.63606f,0},{"Imperial Guard",128967,12.84912f,105.87695f,48.16265f,0},
    {"chargen boat guard 1",172848,717.71069f,-427.38477f,46.73180f,0},{"chargen dock guard",172852,366.54297f,-210.68555f,17.93013f,0},
    {"nels llendo",204678,4461.59314f,687.81055f,133.29490f,0},{"teleri helvi",270747,-489.35913f,229.27539f,16.17552f,0},
    {"darvame hleran",270748,664.89697f,368.71875f,205.78392f,0},
    {"Dreamer_Talker04",297837,3198.39868f,1284.20508f,140.84738f,1},
    {"Dreamer_Talker05",297840,-628.53540f,1683.24805f,87.97037f,1},
    {"agronian guy",474443,-1370.84082f,3277.99023f,782.99188f,1}};

/* A server spawn of MAP: SV_SpawnServer resets the host (RESET 0: a spawn the old engine made, no reset), the map's
 * entity text makes its edicts again (edict 1 the player, then the actors in the text's order), the first tick after
 * it runs the map test (AW_MwscriptTick) */
static void spawn(const char *map,const actor_t *a,int n,int reset){
    int i;
    if(reset)AW_MwscriptServerReset();
    memset(edicts,0,sizeof(edicts));memset(refs,0,sizeof(refs));
    memset(&sv,0,sizeof(sv));strcpy(sv.name,map);sv.worldmodel=&world;sv.num_edicts=2+n;
    for(i=0;i<n;i++){
        edict_t *e=&edicts[2+i];
        e->v.modelindex=(float)(3+i);e->v.solid=SOLID_SLIDEBOX;e->v.model=1;
        e->v.origin[0]=a[i].x;e->v.origin[1]=a[i].y;e->v.origin[2]=a[i].z;
        refs[2+i]._float=(float)a[i].ref;
    }
    tick_map();
}
static edict_t *edict_with(uint32_t ref){
    int i;for(i=1;i<sv.num_edicts;i++)if(refs[i]._float==(float)ref)return &edicts[i];
    return NULL;
}
/* every actor of A drawn as its world change list row says: a disabled one with no model and not solid, the rest
 * with the model the spawn gave; the number of disabled ones drawn (0 is right) */
static int drawn_disabled(const actor_t *a,int n){
    int i,bad=0;
    for(i=0;i<n;i++){
        edict_t *e=edict_with(a[i].ref);
        assert(e);
        assert(AW_ObjectDisabled(a[i].ref)==a[i].disabled);
        if(a[i].disabled){if(e->v.modelindex){bad++;printf("drawn while disabled: %s (%lu)\n",a[i].id,(unsigned long)a[i].ref);}
                          else assert(e->v.solid==SOLID_NOT);}
        else assert(e->v.modelindex==(float)(3+i) && e->v.solid==SOLID_SLIDEBOX);
    }
    return bad;
}
/* the fabricants' scripts (fab_attack_1, fab_attack_2) on a game that never started the attack: FabAttack 0, so
 * "else disable", every run */
static void fabricant_scripts(void){
    int i;for(i=0;i<7;i++)if(plaza[i].disabled)ledger_object(plaza[i].ref,AWM_DISABLE,0);
}
/* Startup, run once at a new game: its Disable of the three Seyda Neen references */
static void startup_script(void){
    int i;for(i=0;i<16;i++)if(seyda[i].disabled)ledger_object(seyda[i].ref,AWM_DISABLE,0);
}
/* a save loaded in place: the world change list as the save holds it (its rows read back), the save's object import
 * (aw_mwhost.c objects_import), then the server spawn of the place the save names */
static void save_load(const char *map,const actor_t *a,int n){
    aw_ledger_row_t kept[32];int count=aw_ledger.count,i;aw_changes_t none;
    assert(count<=32);memcpy(kept,aw_ledger.row,(size_t)count*sizeof(kept[0]));
    AW_LedgerClear(&aw_ledger);
    for(i=0;i<count;i++){aw_ledger_row_t *r=AW_LedgerPut(&aw_ledger,kept[i].key);assert(r);r->fields=kept[i].fields;}
    memset(&none,0,sizeof(none));
    objects_import(&none);
    spawn(map,a,n,1);
}

/* Every edict of A drawn exactly as its reference's record on the world change list says, whatever put it there:
 * taken or disabled = no model and not solid, else the model and solidity its spawn gave. The edicts that disagree
 * (0 is right). */
static int wrong(const actor_t *a,int n){
    int i,bad=0;
    for(i=0;i<n;i++){
        edict_t *e=edict_with(a[i].ref);aw_ledger_row_t *r=ledger_row(a[i].ref);
        int gone=r && (r->fields&(AW_LEDGER_TAKEN|AW_LEDGER_DISABLED));
        assert(e);
        if(gone && (e->v.modelindex || e->v.solid!=SOLID_NOT)){
            bad++;printf("drawn while disabled or taken: %s (%lu)\n",a[i].id,(unsigned long)a[i].ref);}
        if(!gone && (e->v.modelindex!=(float)(3+i) || e->v.solid!=SOLID_SLIDEBOX)){
            bad++;printf("hidden while enabled: %s (%lu)\n",a[i].id,(unsigned long)a[i].ref);}
    }
    return bad;
}
/* New Game (aw_mwhost.c AW_MwscriptNewGameReset's object state lines, after AW_SaveReset cleared the list) */
static void new_game(void){
    AW_LedgerClear(&aw_ledger);
    object_count=0;hidden_count=0;edict_ref_count=0;leaving_count=0;
    map_model=script_model=NULL;map_name[0]=0;
}

/* THE GENERIC CHECK: every state a reference's record can have, each under every way its script's next run can go,
 * over every kind of load. Record states: never touched, disabled, disabled and enabled again, enabled only (an Enable
 * of a reference never disabled), taken, disabled and taken. Next runs: none (a run-once script), a GetDisabled test
 * only, Disable, Enable. Loads: the same map spawned again, a save loaded in place, a change of place and back, New
 * Game. After the load and after the run, every edict is drawn exactly as its record says (wrong() == 0). The
 * references are made up (no game record has them): the rule is the engine's, for every scripted reference. */
enum {R_UNTOUCHED,R_DISABLED,R_REENABLED,R_ENABLED_ONLY,R_TAKEN,R_DISABLED_TAKEN,R_STATES};
enum {P_NONE,P_GETDISABLED,P_DISABLE,P_ENABLE,P_PATHS};
enum {L_SAME,L_SAVE,L_CHANGE,L_NEWGAME,L_LOADS};
#define GENERIC (R_STATES*P_PATHS)
static actor_t generic[GENERIC];
static const actor_t elsewhere[1]={{"elsewhere_actor",800001,0,0,0,0}};
static void generic_states(void){
    int i;
    for(i=0;i<GENERIC;i++){
        uint32_t ref=generic[i].ref;
        switch(i/P_PATHS){
        case R_DISABLED:ledger_object(ref,AWM_DISABLE,0);break;
        case R_REENABLED:ledger_object(ref,AWM_DISABLE,0);ledger_object(ref,AWM_ENABLE,0);break;
        case R_ENABLED_ONLY:ledger_object(ref,AWM_ENABLE,0);break;
        case R_TAKEN:assert(ledger_take(ref,0));break;
        case R_DISABLED_TAKEN:assert(ledger_take(ref,0));ledger_object(ref,AWM_DISABLE,0);   /* taken, then a Disable */
                              assert(ledger_row(ref)->fields==(AW_LEDGER_TAKEN|AW_LEDGER_DISABLED));break;
        }
    }
}
static void generic_run(void){
    int i;
    for(i=0;i<GENERIC;i++){
        uint32_t ref=generic[i].ref;aw_ledger_row_t *r=ledger_row(ref);
        switch(i%P_PATHS){
        case P_GETDISABLED:assert(ledger_object(ref,AWM_GETDISABLED,0)==(r && (r->fields&AW_LEDGER_DISABLED)?1:0));break;
        case P_DISABLE:ledger_object(ref,AWM_DISABLE,0);break;
        case P_ENABLE:ledger_object(ref,AWM_ENABLE,0);break;
        }
    }
}
static void generic_load(int load){
    switch(load){
    case L_SAME:spawn("gen",generic,GENERIC,1);break;
    case L_SAVE:save_load("gen",generic,GENERIC);break;
    case L_CHANGE:spawn("elsewhere",elsewhere,1,1);spawn("gen",generic,GENERIC,1);break;
    case L_NEWGAME:new_game();spawn("gen",generic,GENERIC,1);break;
    }
}
static void generic_check(void){
    int load,i,round;
    for(i=0;i<GENERIC;i++){
        generic[i].id="generic";generic[i].ref=(uint32_t)(900000+i);
        generic[i].x=(float)(10*i);generic[i].y=generic[i].z=0;generic[i].disabled=0;
    }
    for(load=0;load<L_LOADS;load++){
        new_game();spawn("gen",generic,GENERIC,1);generic_states();
        assert(wrong(generic,GENERIC)==0);
        for(round=0;round<2;round++){          /* the load, the scripts' next run, the same load again */
            generic_load(load);
            if(wrong(generic,GENERIC)){printf("after load %d, round %d\n",load,round);assert(0);}
            generic_run();
            if(wrong(generic,GENERIC)){printf("after the next run, load %d, round %d\n",load,round);assert(0);}
        }
    }
    /* the record states as the scripts left them after the last load (New Game, then one run): only the Disable path
     * left a row (disabled); everything else is drawn */
    for(i=0;i<GENERIC;i++)assert(AW_ObjectDisabled(generic[i].ref)==(i%P_PATHS==P_DISABLE));
}

/* THE CONDITIONS OF THE GAME'S OWN SCRIPTS, BOTH DIRECTIONS (the masters' text):
 *   dreamer_talkerEnable (Dreamer_Talker01..12):  Set test to GetJournalIndex A2_2_6thHouse
 *                                                 if ( GetDisabled == 0 ) Return endif
 *                                                 if ( test == 50 ) Enable Return endif
 *   fallingScript (Tarhiel, "agronian guy"):      if ( fellonce == 0 ) if ( GetDistance Player <= 2000 )
 *                                                 "agronian guy"->enable ... (Startup disabled him)
 *   fab_attack_1 / fab_attack_2 (the fabricants): if ( FabAttack == 1 ) enable ... else disable
 * Hidden before the stage across every load; the stage reached, the script enables them and they are drawn across
 * every load; fab_attack's "else disable" once the global is 0 again hides them again. */
static int journal_a2_2_6thhouse,fab_attack,player_near_tarhiel,fellonce;
static void dreamer_scripts(void){
    int i;
    for(i=0;i<16;i++){
        int test=journal_a2_2_6thhouse;uint32_t ref=seyda[i].ref;
        if(strncmp(seyda[i].id,"Dreamer_Talker",14))continue;
        if(ledger_object(ref,AWM_GETDISABLED,0)==0)continue;
        if(test==50){ledger_object(ref,AWM_ENABLE,0);continue;}
    }
}
static void falling_script(void){
    if(fellonce==0 && player_near_tarhiel){ledger_object(474443,AWM_ENABLE,0);fellonce=1;}
}
static void seyda_scripts(void){dreamer_scripts();falling_script();}
static void fab_scripts(void){
    int i;
    for(i=0;i<7;i++)if(!strncmp(plaza[i].id,"fabricant_",10))ledger_object(plaza[i].ref,fab_attack==1?AWM_ENABLE:AWM_DISABLE,0);
}
static void seyda_loads(int dreamers_drawn,int tarhiel_drawn){
    int load;
    for(load=0;load<3;load++){
        if(load==0)spawn("seyda",seyda,16,1);
        else if(load==1)save_load("seyda",seyda,16);
        else{spawn("mh0005",plaza,7,1);spawn("seyda",seyda,16,1);}
        assert(wrong(seyda,16)==0);
        seyda_scripts();
        assert(wrong(seyda,16)==0);
        assert(AW_ObjectDisabled(297837)==!dreamers_drawn && AW_ObjectDisabled(297840)==!dreamers_drawn);
        assert(AW_ObjectDisabled(474443)==!tarhiel_drawn);
    }
}
static void plaza_loads(int drawn){
    int load,i;
    for(load=0;load<3;load++){
        if(load==0)spawn("mh0005",plaza,7,1);
        else if(load==1)save_load("mh0005",plaza,7);
        else{spawn("seyda",seyda,16,1);spawn("mh0005",plaza,7,1);}
        assert(wrong(plaza,7)==0);
        fab_scripts();
        assert(wrong(plaza,7)==0);
        for(i=0;i<7;i++)assert(AW_ObjectDisabled(plaza[i].ref)==(plaza[i].disabled && !drawn));
    }
}
static void conditions_check(void){
    int i;
    new_game();
    spawn("seyda",seyda,16,1);
    startup_script();
    seyda_scripts();
    seyda_loads(0,0);                                   /* journal 0: all three hidden over every load */
    journal_a2_2_6thhouse=40;seyda_loads(0,0);          /* not yet the stage */
    journal_a2_2_6thhouse=50;seyda_scripts();           /* the stage: both Dreamers enable themselves */
    assert(!AW_ObjectDisabled(297837) && !AW_ObjectDisabled(297840) && AW_ObjectDisabled(474443));
    assert(wrong(seyda,16)==0);
    seyda_loads(1,0);
    journal_a2_2_6thhouse=60;seyda_loads(1,0);          /* past the stage: GetDisabled 0, so they stay */
    player_near_tarhiel=1;seyda_scripts();              /* the player within 2000 units: Tarhiel enabled */
    seyda_loads(1,1);
    /* the Plaza: FabAttack 0 hides them over every load; 1 (An Attack on Mournhold begins) enables them over every
     * load; 0 again: their "else disable" hides them again */
    spawn("mh0005",plaza,7,1);fab_attack=0;fab_scripts();
    plaza_loads(0);
    fab_attack=1;fab_scripts();
    for(i=0;i<7;i++)assert(!AW_ObjectDisabled(plaza[i].ref));
    plaza_loads(1);
    fab_attack=0;fab_scripts();
    plaza_loads(0);
}

int main(void){
    setvbuf(stdout,NULL,_IONBF,0);   /* the lines before a failed check reach the test's message */
    pr_strings=strings;strcpy(strings+1,"progs/actor.mdl");
    aw_ledger_on=1;

    /* 1. the Plaza on a new game: the first spawn of mh0005; the fabricants' scripts' first run hides them */
    spawn("mh0005",plaza,7,1);
    assert(attached_map==1);
    fabricant_scripts();
    assert(drawn_disabled(plaza,7)==0);
    assert(ledger_hidden==4 && hidden_count==4);

    /* 2. a teleport inside the Plaza: mh0005 spawned again (the same world model slot, the same name). The map's
     * attach hides the four before any script runs; their scripts' next Disable changes nothing. */
    spawn("mh0005",plaza,7,1);
    printf("second spawn of mh0005: map attached %d times\n",attached_map);
    assert(drawn_disabled(plaza,7)==0);          /* the old engine: four fabricants drawn, nothing hidden */
    assert(attached_map==2 && server_spawns==2 && hidden_count==4 && ledger_hidden==8);
    fabricant_scripts();
    assert(drawn_disabled(plaza,7)==0 && ledger_rehidden==0);

    /* 3. the second line of defence: the map's edicts made again with no attach (the old engine's spawn): drawn; the
     * fabricants' scripts' next Disable hides each drawn one (the entry of the old edict goes, the new one's model is
     * kept), so Enable would show the right model */
    spawn("mh0005",plaza,7,0);
    assert(attached_map==2);
    assert(drawn_disabled(plaza,7)==4);
    fabricant_scripts();
    assert(drawn_disabled(plaza,7)==0 && ledger_rehidden==4 && hidden_count==4);
    fabricant_scripts();
    assert(ledger_rehidden==4);                   /* once: hidden now */

    /* 4. Seyda Neen, the base game: a new game's Startup disables its three references once; Seyda Neen spawned again
     * while it is the map in play (a teleport inside it, the level command's reload) keeps them hidden although
     * Startup never runs again */
    spawn("seyda",seyda,16,1);
    startup_script();
    assert(drawn_disabled(seyda,16)==0);
    spawn("seyda",seyda,16,1);
    assert(drawn_disabled(seyda,16)==0);          /* the old engine: Dreamer_Talker04, Dreamer_Talker05, agronian guy */
    spawn("seyda",seyda,16,1);
    assert(drawn_disabled(seyda,16)==0);

    /* 5. a save made in Seyda Neen loaded there, then a map change and back: hidden every time */
    save_load("seyda",seyda,16);
    assert(drawn_disabled(seyda,16)==0);
    spawn("mh0005",plaza,7,1);
    assert(drawn_disabled(plaza,7)==0);
    spawn("seyda",seyda,16,1);
    assert(drawn_disabled(seyda,16)==0);

    /* 6. Enable after a same-map spawn: Dreamer_Talker04's own script (journal A2_2_6thHouse 50) shows the edict of
     * this spawn with its own model, solid again */
    spawn("seyda",seyda,16,1);
    ledger_object(297837,AWM_ENABLE,0);
    {edict_t *e=edict_with(297837);assert(e->v.modelindex==(float)(3+13) && e->v.solid==SOLID_SLIDEBOX);}
    assert(!AW_ObjectDisabled(297837));

    /* 7. every record state under every next run over every load, then the game's own conditions both ways */
    generic_check();
    printf("generic: %d references, %d record states x %d next runs, %d kinds of load: drawn as recorded\n",
           GENERIC,R_STATES,P_PATHS,L_LOADS);
    conditions_check();
    printf("conditions: the Dreamers (A2_2_6thHouse 50), Tarhiel (2000 units) and the fabricants (FabAttack 1) hidden "
           "before and drawn after, over the same map, a save and a change of place\n");

    AW_LedgerClear(&aw_ledger);free(hidden);
    printf("PASS: %d map attaches over %lu server spawns, %lu edicts hidden, %lu hidden again by a Disable\n",
           attached_map,server_spawns,ledger_hidden,ledger_rehidden);
    return 0;
}
