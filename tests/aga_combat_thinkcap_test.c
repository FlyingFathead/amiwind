/* SPDX-License-Identifier: GPL-2.0-or-later
 * MWSCRIPT-STARTCOMBAT-FOUR-FIGHTERS-68, slice 3: the think cap.
 *
 * Built by tests/test_combat_thinkcap.py the way tests/test_combat.py builds aga_combat_test.c (the same sources,
 * defines and flags), around that fixture's synthetic server (included below with its main renamed).
 *
 * Fighters a script starts in one tick share their think time for the rest of the fight: every tenth of a second one
 * frame runs all their thinks. With aw_combat_think_cap N at most N think a frame, in turn; the share grows when a
 * fighter would otherwise wait longer than the original's reaction time (OpenMW 0.51 aitimer.hpp AI_REACTION_TIME,
 * 0.25 s). The cap is off by default: the fights run as before until the comparison in play decides.
 *
 * AW_CombatThinkShare is weak here, so this file also builds against the engine before the change
 * (AMIWIND_RUNTIME_SOURCE) and fails there by its checks, not by its link.
 */
#define main aga_combat_main
#include "aga_combat_test.c"
#undef main
#include "aw_actors.h"                    /* AW_CombatTestEngage */

int AW_CombatThinkShare(int due,int cap,float frametime) __attribute__((weak));
/* AMBIENT-SOUND-READ-IN-FRAME-68 (section E): weak, so the file also links against the engine before the change */
extern int (*aw_combat_sound_warm)(const char *path) __attribute__((weak));
static long warm_lists,warm_player,warm_sounds;static char warm_names[400];
static float warm_effect(edict_t *e,int effect){(void)effect;warm_lists++;if(e==&edicts[1])warm_player++;return 0;}
static int warm_sound(const char *path){warm_sounds++;if(strlen(warm_names)+strlen(path)+2<sizeof(warm_names)){strcat(warm_names," ");strcat(warm_names,path);}return 1;}

static int failures,passes;
#define CHECK(cond,text) do{int ok_=(cond)!=0;printf("%s  %s\n",ok_?"PASS":"FAIL",text);if(ok_)passes++;else failures++;}while(0)
static int share(int due,int cap,float frametime){return AW_CombatThinkShare?AW_CombatThinkShare(due,cap,frametime):-1;}
static double started;
/* the thinks of this encounter so far (dbg combat's count, through AW_CombatCost: thinks a second over the span) */
static long thinks(void){float rate=0;double span=sv.time-started;AW_CombatCost(&rate,NULL,NULL,NULL);return (long)(rate*(span<.001?.001:span)+.5);}
static void start_six(void){
    int k;
    run("aw_combat_cmd calm");started=sv.time;
    for(k=2;k<=7;k++)assert(AW_CombatTestEngage(&edicts[k],0));
    assert(AW_CombatHostiles()==6);
}
/* N frames; the most thinks any one of them ran */
static long frames(int n){long most=0,before,now;int i;for(i=0;i<n;i++){before=thinks();tick(1);now=thinks()-before;if(now>most)most=now;}return most;}

int main(void){
    edict_t *p=&edicts[1],*npc=&edicts[2];int k,i;long most,total;
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
    sv.active=1;sv.edicts=edicts;sv.num_edicts=8;sv.models[1]=&model;model.numframes=31;sv.time=1;
    svs.maxclients=1;svs.clients=&client;client.edict=p;client.active=client.spawned=1;cls.state=ca_connected;key_dest=key_game;
    fields[0][2]._float=.9f;
    p->v.origin[2]=16.625f;p->v.mins[2]=-16.625f;p->v.maxs[0]=7.32f;p->v.health=60;
    p->v.flags=(float)FL_GODMODE;                    /* the player lives through every case */
    aw_character.valid=1;for(i=0;i<8;i++)aw_character.attributes[i]=50;for(i=0;i<27;i++)aw_character.skills[i]=30;
    aw_character.current[0]=aw_character.maximum[0]=60;aw_character.current[2]=aw_character.maximum[2]=200;
    npc->v.classname=add_string("aw_npc");npc->v.netname=add_string("Mevil Molor");npc->v.modelindex=1;
    npc->v.solid=SOLID_BBOX;npc->v.nextthink=2;npc->v.think=7;
    npc->v.mins[0]=-7.32f;npc->v.mins[1]=-7.12f;npc->v.maxs[0]=7.32f;npc->v.maxs[1]=7.12f;npc->v.maxs[2]=33.25f;
    fields[2][3].string=add_string("mevil molor");
    AW_CombatInit();aw_combat_result=result;aw_combat_voice=bark;
    run("aw_combat_cmd seed 777");run("aw_combat_cmd readout off");
    /* six fighters around the player, as a script's six StartCombat in one tick leaves them */
    for(k=2;k<=7;k++){
        edict_t *e=&edicts[k];
        if(k>2){*e=edicts[2];fields[k][3].string=fields[2][3].string;}
        e->free=0;e->v.origin[0]=(float)(200+40*(k-2));e->v.origin[1]=(float)(60*(k-2)-150);e->v.origin[2]=0;
        fields[k][4]._float=(float)(1000+k);
    }

    printf("=== R: the rule ===\n");
    CHECK(share(6,0,.02f)==6 && share(16,0,.5f)==16,"R1 cap 0: every due fighter thinks (the behaviour before)");
    CHECK(share(6,2,.02f)==2 && share(16,2,.02f)==2,"R2 cap 2 at a 20 ms frame: two think");
    CHECK(share(2,4,.02f)==2 && share(0,2,.02f)==0,"R3 fewer due than the cap: all of them");
    CHECK(share(16,2,.1f)==7,"R4 sixteen at a 100 ms frame: seven, so nobody waits past 0.25 s");
    CHECK(share(6,2,.2f)==5 && share(16,2,.5f)==16,"R5 the share never passes the fighters due");

    printf("=== A: the cap off (the default): six started in one tick think in one frame ===\n");
    for(i=0,k=0;i<cvar_count;i++)if(!strcmp(cvars[i]->name,"aw_combat_think_cap")){k=1;CHECK(!strcmp(cvars[i]->string,"0"),"A0 the cap is off by default");}
    CHECK(k,"A0b the cap is a setting (aw_combat_think_cap)");
    start_six();
    most=frames(1);
    printf("  thinks in the first frame %ld\n",most);
    CHECK(most==6,"A1 control: all six think in the frame after the start");
    most=frames(49);total=thinks();
    printf("  most thinks in a frame %ld, thinks in the second %ld\n",most,total);
    CHECK(most==6,"A2 control: and in one frame of every five from then on");

    printf("=== B: aw_combat_think_cap 2 ===\n");
    Cvar_SetValue("aw_combat_think_cap",2);
    start_six();
    most=frames(1);
    CHECK(most==2,"B1 two think in the frame after the start");
    frames(2);
    printf("  thinks after three frames %ld\n",thinks());
    CHECK(thinks()==6,"B2 every fighter has thought within three frames");
    most=frames(47);
    printf("  most thinks in a frame %ld, thinks in the second %ld (cap off: %ld)\n",most,thinks(),total);
    CHECK(most<=2,"B3 no frame runs more than two thinks");
    /* (within one round of thinks: a fighter's tenth of a second is five or six 20 ms frames by the clock's rounding) */
    CHECK(thinks()>=total-6 && thinks()<=total+6,"B4 over a second every fighter thinks as often as before");
    CHECK(AW_CombatHostiles()==6,"B5 all six still fight");

    printf("=== C: the cap at a 0.2 s frame (a slow machine) ===\n");
    start_six();
    host_frametime=.2;
    most=frames(1);
    CHECK(most==5,"C1 five of the six think in a frame: the share grows past the cap");
    {long least=6,before,now;for(i=0;i<5;i++){before=thinks();tick(1);now=thinks()-before;if(now<least)least=now;}
     CHECK(least==5,"C2 and in every following frame, in turn");}
    host_frametime=.02;

    printf("=== D: the cap off again ===\n");
    Cvar_SetValue("aw_combat_think_cap",0);
    start_six();
    CHECK(frames(1)==6,"D1 all six think in one frame again");

    /* AMBIENT-SOUND-READ-IN-FRAME-68: what a blow reads from disk (its fighters' ability lists, the fight's own
     * sounds) is asked for at the fight's start, so no blow waits for the disk. The host's two hooks are counted
     * here: the list question (aw_combat_effect_magnitude, the host keeps a whole list per actor) and the sound
     * loader (aw_combat_sound_warm). */
    printf("=== E: what the blows read is read at the fight's start ===\n");
    CHECK(&aw_combat_sound_warm!=NULL,"E0 the fight's sounds have a loader hook");
    if(&aw_combat_sound_warm){
        long lists0,sounds0;
        run("aw_combat_cmd calm");
        aw_combat_effect_magnitude=warm_effect;aw_combat_sound_warm=warm_sound;
        warm_lists=warm_player=warm_sounds=0;warm_names[0]=0;
        started=sv.time;
        for(k=2;k<=7;k++)assert(AW_CombatTestEngage(&edicts[k],0));
        printf("  before any frame: list questions %ld (the player's %ld), sounds asked %ld:%s\n",warm_lists,warm_player,warm_sounds,warm_names);
        CHECK(warm_lists>=12 && warm_player>=6,"E1 every fighter's and the player's ability list is asked at the start, before any blow");
        CHECK(warm_sounds>=2 && strstr(warm_names," combat/health.wav") && strstr(warm_names," combat/miss.wav"),
              "E2 each of the fight's sounds is loaded at the start");
        lists0=warm_lists;sounds0=warm_sounds;
        frames(100);
        printf("  after two seconds of the fight: list questions %ld, sounds asked %ld\n",warm_lists-lists0,warm_sounds-sounds0);
        CHECK(warm_sounds==sounds0,"E3 no sound is loaded by a frame of the fight");
        aw_combat_effect_magnitude=NULL;aw_combat_sound_warm=NULL;
    }else{CHECK(0,"E1 every fighter's and the player's ability list is asked at the start, before any blow");
          CHECK(0,"E2 each of the fight's sounds is loaded at the start");CHECK(0,"E3 no sound is loaded by a frame of the fight");}

    printf("VERDICT: %d passed, %d failed\n",passes,failures);
    return failures!=0;
}
