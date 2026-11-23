/* SPDX-License-Identifier: GPL-2.0-or-later
 * MWSCRIPT-STARTCOMBAT-FOUR-FIGHTERS-68: a script's StartCombat beyond four fighters.
 *
 * Built by tests/test_combat_slots.py the way tests/test_combat.py builds aga_combat_test.c (the same sources, defines
 * and flags), around that fixture's synthetic server (included below with its main renamed), and with the script
 * host's own StartCombat code: to_fighter and host_combat, cut unchanged out of engine/aga/src/aw_mwhost.c into
 * host_combat_slice.c by the test module. This file gives the host's lookups around them (a script object index is the
 * record number here; record_edict names its edict when its actor is loaded).
 *
 * The rule (OpenMW 0.51 aiextensions.cpp OpStartCombat -> mechanicsmanagerimp.cpp startCombat): an AiCombat package is
 * stacked on the actor, with no limit on the actors fighting at once. The game starts six at the player in one script
 * tick three times (two scripts and one greeting) and fifteen actors against each other once (the Skaal village
 * attack). With four fight slots the fifth StartCombat was refused ("Combat: 4 hostile NPCs already."), a third pair of
 * actors never fought, and a dead actor's body could not be laid down while four fought.
 *
 * Slice 2, the kept orders: a StartCombat is an order on the actor's record (AWL_COMBAT and fight_ref: whom it fights),
 * so one past the slots, or on an actor that is not loaded, is taken up once a second when a slot is free and the actor
 * and its target are loaded near the player (aw_mwhost.c fight_order, fight_start, fight_orders, cut into the slice
 * with host_combat; fight_resume, the change list's kept fight, beside them). The actor record's own order calls
 * (aw_actorstate.c) are given here over this file's records; their native test is tests/test_actorstate.py.
 *
 * The functions new with the fixes are weak here, and the slice says whether it holds the orders (AW_SLICE_ORDERS), so
 * this file also builds against the engine before each fix (AMIWIND_RUNTIME_SOURCE) and fails there by its checks,
 * not by its link.
 */
#define main aga_combat_main
#define AW_ItemsShow aga_combat_items_show          /* the base fixture's stub (no item edicts): replaced below */
#include "aga_combat_test.c"
#undef AW_ItemsShow
#undef main
#include "aw_mwvm.h"
#include "aw_actorstate.h"
#include "aw_actors.h"                    /* AW_CombatForget, AW_CombatTestEngage */

int AW_CombatSlotsFree(void) __attribute__((weak));
int AW_CombatItemsRule(int drawn,int spare) __attribute__((weak));

/* every fighter here is armed: a weapon and a shield, each its own edict (aw_items.c AW_ItemsShow) */
static edict_t item_pool[64];static int item_next,armed_shown;
int AW_ItemsShow(edict_t *a,edict_t *o[AW_ITEMS_KINDS]){
    int k;(void)a;
    for(k=0;k<AW_ITEMS_KINDS;k++){o[k]=&item_pool[item_next];item_next=(item_next+1)%64;}
    armed_shown++;return AW_ITEMS_KINDS;
}

/* --- the script host around the cut functions (aw_mwhost.c declares the same names) --- */
edict_t *sv_player;
int (*aw_mwscript_combat_end)(struct edict_s *e);
void Con_DPrintf(char *f,...){(void)f;}
static unsigned long actor_calls,actor_misses,combat_starts,combat_stops,combat_between,combat_refused;
#define field_source(e) GetEdictFieldValue((e),"aw_source_id")
#define RECORDS 16
static aw_actor_t records[RECORDS];      /* the live records, by script object index */
static int record_edict[RECORDS];        /* the edict its map made for it, 0 = not loaded */
static aw_actor_t *actor_of(int instance,int target,edict_t **edict){
    (void)instance;*edict=NULL;
    if(target==AW_MWVM_PLAYER){*edict=sv_player;return NULL;}
    if(target<0 || target>=RECORDS || !records[target].reference)return NULL;
    if(record_edict[target]>0 && !edicts[record_edict[target]].free)*edict=&edicts[record_edict[target]];
    return &records[target];
}
static edict_t *edict_of(int number){return number>0 && number<sv.num_edicts?EDICT_NUM(number):NULL;}
static int locate(int instance,int target,vec3_t at){
    (void)instance;
    if(target<0 || target>=RECORDS || record_edict[target]<=0)return -1;
    VectorCopy(edicts[record_edict[target]].v.origin,at);return record_edict[target];
}
static aw_actor_t *record_of_edict(edict_t *e){
    int i;for(i=0;i<RECORDS;i++)if(records[i].reference && record_edict[i]==(int)(e-edicts))return &records[i];
    return NULL;
}
static uint32_t ref_of_edict(edict_t *e){eval_t *v=e?GetEdictFieldValue(e,"aw_ref"):NULL;return v && v->_float>0?(uint32_t)v->_float:0;}
static int edict_of_ref(uint32_t key){
    int i;for(i=1;i<sv.num_edicts;i++)if(!edicts[i].free && ref_of_edict(&edicts[i])==key)return i;
    return 0;
}
aw_actor_t *AW_ActorGet(uint32_t reference,int row,int create){
    int i;(void)row;(void)create;
    for(i=0;i<RECORDS;i++)if(records[i].reference==reference && reference)return &records[i];
    return NULL;
}
void AW_MwvmStateChanged(void){}
float Cvar_VariableValue(char *name){int i;for(i=0;i<cvar_count;i++)if(!strcmp(cvars[i]->name,name))return cvars[i]->value;return 0;}
#ifndef AW_MOVE_UNIT_SCALE
#define AW_MOVE_UNIT_SCALE 0.25f          /* aw_move.h */
#endif
#include "host_combat_slice.c"
#ifdef AW_SLICE_ORDERS
/* the actor record's order calls as aw_actorstate.c has them, over the records here */
void AW_ActorOrder(aw_actor_t *a,uint32_t target){
    if(!a)return;
    if(!target){a->flags&=~AWL_COMBAT;a->fight_ref=0;return;}
    if(a->flags&AWL_DEAD)return;
    a->flags|=AWL_COMBAT|AWL_CHANGED;a->fight_ref=target;
}
int AW_ActorOrders(int *cursor,uint32_t *refs,uint32_t *targets,int max){
    int i=cursor?*cursor:0,n=0;
    if(i<0 || i>=RECORDS)i=0;
    for(;i<RECORDS && n<max;i++){
        if(!records[i].reference || (records[i].flags&(AWL_COMBAT|AWL_DEAD))!=AWL_COMBAT)continue;
        refs[n]=records[i].reference;targets[n]=records[i].fight_ref?records[i].fight_ref:AW_ACTOR_PLAYER_REF;n++;
    }
    if(cursor)*cursor=i>=RECORDS?0:i;
    return n;
}
int AW_ActorOrderCount(void){int i,n=0;for(i=0;i<RECORDS;i++)if((records[i].flags&(AWL_COMBAT|AWL_DEAD))==AWL_COMBAT)n++;return n;}
int AW_ActorOrdersEnd(void){
    int i,n=0;for(i=0;i<RECORDS;i++)if(records[i].flags&AWL_COMBAT){records[i].flags&=~AWL_COMBAT;records[i].fight_ref=0;n++;}
    return n;
}
static int is_actor(const edict_t *e){return e && !e->free && e->v.classname && !strcmp(pr_strings+e->v.classname,"aw_npc");}
extern void (*aw_combat_calmed)(void);
static uint32_t order_target(int rec){return (records[rec].flags&AWL_COMBAT)?records[rec].fight_ref:0;}
static unsigned long kept(void){return orders_kept;}
static unsigned long taken(void){return orders_taken;}
static unsigned long dropped(void){return orders_dropped;}
static void order_from_save(int rec,uint32_t target){AW_ActorOrder(&records[rec],target);orders_live=1;}
#else
/* the engine before the kept orders: none of it exists; the checks below say so */
static void fight_orders(float dt){(void)dt;}
static int fight_resume(edict_t *e){return AW_CombatTestEngage(e,0);}      /* aw_actors.c did this itself */
static uint32_t order_target(int rec){(void)rec;return 0;}
static unsigned long kept(void){return 0;}
static unsigned long taken(void){return 0;}
static unsigned long dropped(void){return 0;}
static void order_from_save(int rec,uint32_t target){(void)target;records[rec].flags|=AWL_COMBAT;}
#endif

/* --- the checks --- */
static int failures,passes;
#define CHECK(cond,text) do{int ok_=(cond)!=0;printf("%s  %s\n",ok_?"PASS":"FAIL",text);if(ok_)passes++;else failures++;}while(0)
static int fighting(int edict){return AW_CombatFighter(&edicts[edict])!=NULL;}
static int slots_free(void){return AW_CombatSlotsFree?AW_CombatSlotsFree():-1;}
static int ordered(int rec){return (records[rec].flags&AWL_COMBAT)!=0;}
/* the edict its map makes for record REC (the fighter's model, hull and QuakeC idle as the template below) */
static void load(int k,int rec,float x,float y){
    edict_t *e=&edicts[k];
    *e=edicts[2];
    e->free=0;e->v.origin[0]=x;e->v.origin[1]=y;e->v.origin[2]=0;   /* feet on the stub's floor (z 0) */
    fields[k][3].string=fields[2][3].string;fields[k][4]._float=(float)(1000+rec);
    record_edict[rec]=k;
}
static void unload(int k,int rec){AW_CombatForget(&edicts[k]);edicts[k].free=1;fields[k][4]._float=0;record_edict[rec]=0;}
static void record(int rec){
    memset(&records[rec],0,sizeof(records[rec]));
    records[rec].reference=1000u+(unsigned)rec;records[rec].base=0;records[rec].flags=AWL_USED;
    records[rec].dyn_base[0]=records[rec].dyn_cur[0]=94;records[rec].dyn_base[1]=records[rec].dyn_cur[1]=112;
    records[rec].dyn_base[2]=records[rec].dyn_cur[2]=208;
    record_edict[rec]=0;
}
static void place(int k,int rec,float x,float y){record(rec);load(k,rec,x,y);}
/* the fights and the orders end (the helper clears the marks itself, so the cases stay apart on an engine whose calm
 * leaves them: check H asks the command alone) */
static void calm(void){int k;run("aw_combat_cmd calm");for(k=0;k<RECORDS;k++){records[k].flags&=~AWL_COMBAT;
#ifdef AW_SLICE_ORDERS
    records[k].fight_ref=0;
#endif
    }}
/* N frames of play: the combat layer's frame, then the script host's order pass as AW_MwscriptTick runs it */
static void play(int n){int i;for(i=0;i<n;i++){tick(1);fight_orders((float)host_frametime);}}

int main(void){
    edict_t *p=&edicts[1],*npc=&edicts[2];int k,i;
    setvbuf(stdout,NULL,_IONBF,0);
    /* the base fixture's data files (aga_combat_test.c main), in the folder the test module runs this in */
    strcpy(dir,"data");mkdir(dir,0700);
    {char sub[96];sprintf(sub,"%s/combat",dir);mkdir(sub,0700);}
    write_file("combat/settings.txt","AWCS1\nfFatigueBase 1.25\nfFatigueMult 0.5\nfCombatDistance 128\nfHandToHandReach 1\n"
        "fMinHandToHandMult 0.1\nfMaxHandToHandMult 0.5\nfHandtoHandHealthPer 0.1\nfDamageStrengthBase 0.5\n"
        "fDamageStrengthMult 0.1\nfCombatArmorMinMult 0.25\nfCombatKODamageMult 1.5\nfCombatCriticalStrikeMult 4\n"
        "fKnockDownMult 0.5\niKnockDownOddsBase 50\niKnockDownOddsMult 50\nfFatigueAttackBase 2\nfFatigueAttackMult 0\n"
        "fWeaponFatigueMult 0.25\nfFatigueReturnBase 2.5\nfFatigueReturnMult 0.02\nfUnarmoredBase1 0.1\nfUnarmoredBase2 0.065\n"
        "iBlockMinChance 10\niBlockMaxChance 50\nfSwingBlockBase 1\nfSwingBlockMult 1\nfBlockStillBonus 1.25\n"
        "fFatigueBlockBase 4\nfFatigueBlockMult 0\nfWeaponFatigueBlockMult 1\nfCombatBlockLeftAngle -90\n"
        "fCombatBlockRightAngle 30\nfCombatDelayNPC 0.1\nfNPCHealthBarTime 3\nfNPCHealthBarFade 0.5\nfWeaponDamageMult 0.1\n"
        "fCombatAngleXY 60\nfCombatAngleZ 60\nfCombatInvisoMult 0.2\n"
        "anim knockdown 2.667\nanim block 1.333 0.25\n"
        "sound health combat/health.wav\nsound miss combat/miss.wav\n");
    write_actors();
    {char from[160],to[160];sprintf(from,"%s/actors.txt",dir);sprintf(to,"%s/combat/actors.txt",dir);assert(!rename(from,to));}
    pr_strings=strings;progs=&program;program.entityfields=sizeof(entvars_t)/4;
    sv.active=1;sv.edicts=edicts;sv.num_edicts=12;sv.models[1]=&model;model.numframes=31;sv.time=1;
    for(k=8;k<12;k++)edicts[k].free=1;               /* edicts for the actors that load later (C) */
    svs.maxclients=1;svs.clients=&client;client.edict=p;client.active=client.spawned=1;cls.state=ca_connected;key_dest=key_game;
    fields[0][2]._float=.9f;
    p->v.origin[2]=16.625f;p->v.mins[2]=-16.625f;p->v.maxs[0]=7.32f;p->v.health=60;sv_player=p;
    /* god mode (GODMODE-COMBAT-DAMAGE-61: the blows take no health): the player lives through every case, so a refusal
     * below is the slots', never host_combat's "the player is dead" */
    p->v.flags=(float)FL_GODMODE;
    aw_character.valid=1;for(i=0;i<8;i++)aw_character.attributes[i]=50;for(i=0;i<27;i++)aw_character.skills[i]=30;
    aw_character.current[0]=aw_character.maximum[0]=60;aw_character.current[2]=aw_character.maximum[2]=200;
    npc->v.classname=add_string("aw_npc");npc->v.netname=add_string("Mevil Molor");npc->v.modelindex=1;
    npc->v.solid=SOLID_BBOX;npc->v.nextthink=2;npc->v.think=7;
    npc->v.mins[0]=-7.32f;npc->v.mins[1]=-7.12f;npc->v.maxs[0]=7.32f;npc->v.maxs[1]=7.12f;npc->v.maxs[2]=33.25f;
    fields[2][3].string=add_string("mevil molor");
    AW_CombatInit();aw_combat_result=result;aw_combat_voice=bark;
    aw_mwscript_combat_end=AW_CombatActorEnd;        /* aw_mwhost.c AW_MwscriptInit: StopCombat ends a fight */
#ifdef AW_SLICE_ORDERS
    aw_combat_calmed=orders_calmed;                  /* and the calm ends the orders */
#endif
    run("aw_combat_cmd seed 777");run("aw_combat_cmd readout off");
    for(k=2;k<=7;k++)place(k,k,(float)(200+40*(k-2)),(float)(60*(k-2)-150));

    printf("=== A: six StartCombat Player in one script tick ===\n");
    armed_shown=0;
    for(k=2;k<=7;k++)host_combat(0,k,0,AW_MWVM_PLAYER);
    printf("  hostiles %d, slots free %d, starts %lu, held items shown for %d fighters\n",AW_CombatHostiles(),slots_free(),
           combat_starts,armed_shown);
    CHECK(fighting(2) && fighting(3) && fighting(4) && fighting(5),"A1 control: the first four hold a fight");
    CHECK(fighting(6),"A2 the fifth StartCombat holds a fight");
    CHECK(fighting(6) && fighting(7) && AW_CombatHostiles()==6,"A3 all six fight the player at once");
    CHECK((records[6].flags&AWL_COMBAT) && (records[7].flags&AWL_COMBAT),"A4 the fifth and sixth records are marked as fighting");
    CHECK(slots_free()==10,"A5 ten of sixteen fight slots are free");
    CHECK(armed_shown==6,"A6 all six draw their weapon and shield (this map has edicts to spare)");
    tick(50);                                        /* one second of the fight: every think runs */
    CHECK(AW_CombatHostiles()==6,"A7 all six still fight after a second");

    printf("=== D: three actor-against-actor StartCombats (the shape of the Skaal village attack) ===\n");
    calm();
    host_combat(0,2,0,3);host_combat(0,4,0,5);host_combat(0,6,0,7);
    printf("  between %lu, refused %lu, slots free %d\n",combat_between,combat_refused,slots_free());
    CHECK(fighting(2) && fighting(3) && fighting(4) && fighting(5),"D0 control: two pairs fight (two slots each)");
    CHECK(fighting(6) && fighting(7),"D1 the third pair fights too");
    CHECK(AW_CombatHostiles()==0,"D2 none of the six is a hostile of the player");

    printf("=== E: a dead body laid down while four living fighters fight ===\n");
    calm();
    for(k=2;k<=5;k++)host_combat(0,k,0,AW_MWVM_PLAYER);
    CHECK(AW_CombatLayCorpse(&edicts[6]),"E1 a dead body is laid down while four fight");
    CHECK(AW_CombatHostiles()==4,"E2 the body is no hostile");

    printf("=== F: aw_combat_slots 4, the cap before v0.0.68, for a comparison ===\n");
    calm();run("aw_combat_cmd slots 4");
    for(k=2;k<=7;k++)host_combat(0,k,0,AW_MWVM_PLAYER);
    CHECK(fighting(5) && !fighting(6) && !fighting(7) && AW_CombatHostiles()==4,"F1 with four slots the fifth and sixth are refused");
    CHECK(slots_free()==0,"F2 no slot is free");
    host_combat(0,2,1,AW_MWVM_PLAYER);               /* StopCombat on the first */
    CHECK(!fighting(2) && slots_free()==1,"F3 StopCombat frees one slot");
    host_combat(0,6,0,AW_MWVM_PLAYER);
    CHECK(fighting(6) && slots_free()==0,"F4 the next StartCombat takes the freed slot");
    run("aw_combat_cmd slots 16");
    CHECK(slots_free()==12,"F5 back at sixteen slots twelve are free");
    host_combat(0,7,0,AW_MWVM_PLAYER);host_combat(0,2,0,AW_MWVM_PLAYER);
    CHECK(AW_CombatHostiles()==6,"F6 and all six fight");
    run("aw_combat_cmd slots 99");
    CHECK(slots_free()==10,"F7 a value past sixteen counts as sixteen");
    run("aw_combat_cmd slots 16");

    printf("=== G: the held items of a fighter past the four the maps keep edicts for ===\n");
    /* tools/map_engine_limits.py runtime_edicts keeps 2 + 4 x 2 + 32 + 32 = 74 edicts free on every map for the
     * engine's own (four fighters' held items among them); a fifth armed fighter takes its two only from edicts
     * beyond those 74 */
    CHECK(AW_CombatItemsRule && AW_CombatItemsRule(0,0) && AW_CombatItemsRule(3,0),"G1 the first four armed fighters always draw their items");
    CHECK(AW_CombatItemsRule && !AW_CombatItemsRule(4,0) && !AW_CombatItemsRule(4,75) && !AW_CombatItemsRule(15,75),
          "G2 a fifth draws none while fewer than 76 edicts are spare");
    CHECK(AW_CombatItemsRule && AW_CombatItemsRule(4,76) && AW_CombatItemsRule(15,76),"G3 and draws them with 76 or more spare");

    printf("=== B: the orders past the slots are kept and taken up (aw_combat_slots 4 for the comparison) ===\n");
    calm();run("aw_combat_cmd slots 4");
    {unsigned long k0=kept(),t0=taken();
     for(k=2;k<=7;k++)host_combat(0,k,0,AW_MWVM_PLAYER);
     CHECK(AW_CombatHostiles()==4 && !fighting(6) && !fighting(7),"B0 control: four fight, the fifth and sixth do not");
     CHECK(ordered(6) && ordered(7) && order_target(6)==AW_ACTOR_PLAYER_REF && order_target(7)==AW_ACTOR_PLAYER_REF &&
           kept()-k0==2,"B1 the fifth and sixth keep their order against the player on their records");
     play(100);                                      /* two seconds: two order passes */
     CHECK(!fighting(6) && !fighting(7) && AW_CombatHostiles()==4,"B2 while no slot is free the orders wait");
     host_combat(0,2,1,AW_MWVM_PLAYER);              /* StopCombat on the first */
     CHECK(!ordered(2),"B3 StopCombat ends the first one's order");
     play(100);
     CHECK(fighting(6) && !fighting(7) && taken()-t0==1,"B4 the nearer waiting order is taken up once a slot frees");
     CHECK(!fighting(2),"B5 the stopped one does not start again");
     run("aw_combat_cmd slots 16");play(100);
     CHECK(fighting(7) && AW_CombatHostiles()==5 && taken()-t0==2,"B6 with slots free again the last order is taken up");}

    printf("=== C: an order on an actor that is not loaded, and one out of range ===\n");
    calm();
    record(8);                                       /* a record of the game data; its map has made no edict for it */
    {unsigned long m0=actor_misses,t0=taken();
     host_combat(0,8,0,AW_MWVM_PLAYER);
     CHECK(ordered(8) && order_target(8)==AW_ACTOR_PLAYER_REF && actor_misses==m0,
           "C1 a StartCombat on an actor that is not loaded is kept on its record");
     play(100);
     CHECK(AW_CombatHostiles()==0,"C2 nothing fights while it is not loaded");
     load(8,8,300,0);play(100);
     CHECK(fighting(8) && taken()-t0==1,"C3 it fights within a second of loading near the player");}
    calm();unload(8,8);
    record(9);load(9,9,2400,0);                      /* 9,600 original units away; the processing range is 7,168 */
    order_from_save(9,AW_ACTOR_PLAYER_REF);play(100);
    CHECK(!fighting(9) && ordered(9),"C4 an order waits while its actor is beyond the actors' processing range");
    edicts[9].v.origin[0]=300;play(100);
    CHECK(fighting(9),"C5 and is taken up once the actor is within it");
    host_combat(0,8,0,AW_MWVM_PLAYER);host_combat(0,8,1,AW_MWVM_PLAYER);
    CHECK(!ordered(8),"C6 StopCombat ends the order of an actor that is not loaded");

    printf("=== R: a kept fight between two actors starts again against the same actor ===\n");
    calm();unload(9,9);
    host_combat(0,2,0,3);
    CHECK(fighting(2) && fighting(3) && order_target(2)==1003 && order_target(3)==1002,
          "R1 each of the pair holds its order against the other");
    AW_CombatClear();                                /* the map left and loaded again: the slots empty, the orders stay */
    {int pl=-1;
     CHECK(fight_resume(&edicts[2]) && AW_CombatTargetOf(&edicts[2],&pl)==&edicts[3] && !pl && AW_CombatHostiles()==0,
           "R2 the change list's kept fight starts again against the other actor, not the player");}
    AW_CombatClear();unload(3,3);
    CHECK(!fight_resume(&edicts[2]) && !fighting(2),"R3 with its target not loaded it does not turn on the player");
    load(3,3,240,-90);play(100);
    CHECK(fighting(2) && fighting(3) && AW_CombatHostiles()==0,"R4 and the pair fights again once the target is loaded");
    AW_CombatClear();records[3].flags|=AWL_DEAD;records[3].flags&=~AWL_COMBAT;   /* as AW_ActorKill leaves a record */
    {unsigned long d0=dropped();
     play(100);
     CHECK(!fighting(2) && !ordered(2) && dropped()-d0==1,"R5 an order whose target died ends");}
    records[3].flags&=~AWL_DEAD;
    calm();order_from_save(4,AW_ACTOR_PLAYER_REF);
    CHECK(fight_resume(&edicts[4]) && AW_CombatHostiles()==1,"R6 a kept fight against the player starts again against the player");

    printf("=== H: dbg combat calm ends the orders too ===\n");
    calm();
    for(k=2;k<=4;k++)host_combat(0,k,0,AW_MWVM_PLAYER);
    run("aw_combat_cmd calm");                       /* the command alone, not this file's helper */
    CHECK(AW_CombatHostiles()==0 && !ordered(2) && !ordered(3) && !ordered(4),"H1 after the calm nobody is marked as fighting");
    play(100);
    CHECK(AW_CombatHostiles()==0,"H2 and no fight starts again");

    printf("VERDICT: %d passed, %d failed\n",passes,failures);
    return failures?1:0;
}
