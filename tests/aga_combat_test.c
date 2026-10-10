/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_combat.c with a synthetic server: the data files (settings, the
 * bucketed actor sheets), engaging an NPC, the chase with the companion's
 * navigation, the NPC's swing at its hit key, the player's punch at its hit
 * key (watched from the attack button), the enemy health bar's time and
 * fade, battle music on and off, death of either side with its result,
 * a resident hit by the player starting a fight, the player's fatigue
 * return outside fights, the scene change and the cost counters. */
#include "quakedef.h"
#include "aw_anim.h"
#include "aw_combat.h"
#include "aw_character.h"
#include <assert.h>
#include <unistd.h>
#include <sys/stat.h>

server_t sv;server_static_t svs;client_static_t cls;client_state_t cl;keydest_t key_dest;
int host_framecount;double host_frametime=.02;char *pr_strings;dprograms_t *progs;double realtime;
unsigned long aw_sv_move_calls;aw_character_t aw_character;
/* the hooks live beside their callers (aw_ui.c, aw_scene.c) */
int (*aw_combat_enemy_bar)(float *,float *);void (*aw_combat_scene)(void);int (*aw_combat_input_locked)(void);
/* aw_items.c (carried weapon/shield entities; its own fixture aga_items_test.c): counted here. */
#include "aw_items.h"
static int items_shown,items_hidden;
int AW_CompanionPickAim(void){return 0;}      /* aw_companion.c: the right button in pick mode */
int AW_ItemsShow(edict_t *a,edict_t *o[AW_ITEMS_KINDS]){(void)a;o[0]=o[1]=NULL;items_shown++;return 0;}
void AW_ItemsUpdate(edict_t *a,edict_t *i[AW_ITEMS_KINDS]){(void)a;(void)i;}
void AW_ItemsHide(edict_t *i[AW_ITEMS_KINDS]){i[0]=i[1]=NULL;items_hidden++;}
static char strings[256];static int string_at=1;
static edict_t edicts[16];static client_t client;static dprograms_t program;static model_t model;
static eval_t fields[16][8];
static int walled,steps,sounds,music_on,music_off,music_death,results[2],printed;static edict_t *target;
static char dir[64],last_sound[64];static double clock_now;

static int add_string(const char *s){int at=string_at;strcpy(strings+at,s);string_at+=strlen(s)+1;return at;}
edict_t *EDICT_NUM(int n){return &edicts[n];}
eval_t *GetEdictFieldValue(edict_t *e,char *name){
    static const char *names[]={"aw_hand_state","aw_hand_started","aw_hand_punch","aw_source_id"};
    int i;for(i=0;i<4;i++)if(!strcmp(name,names[i]))return &fields[e-edicts][i];
    return NULL;
}
void SV_LinkEdict(edict_t *e,qboolean touch){(void)e;(void)touch;}
trace_t SV_Move(vec3_t a,vec3_t mi,vec3_t ma,vec3_t b,int type,edict_t *e){
    trace_t t;(void)mi;(void)ma;(void)type;(void)e;aw_sv_move_calls++;
    memset(&t,0,sizeof(t));t.fraction=1;VectorCopy(b,t.endpos);
    if(walled){t.startsolid=1;t.fraction=0;return t;}       /* nowhere to go: no path */
    if(b[2]<0 && a[2]>=0){t.fraction=a[2]/(a[2]-b[2]);t.endpos[2]=0;t.plane.normal[2]=1;}
    return t;
}
qboolean AW_ActorStep(edict_t *e,vec3_t move,double dt){(void)dt;if(walled)return false;e->v.origin[0]+=move[0];e->v.origin[1]+=move[1];aw_sv_move_calls+=3;steps++;return true;}
edict_t *AW_NPCTargetReach(edict_t *p,vec3_t angles,float reach){(void)p;(void)angles;assert(reach>32 && reach<64);return target;}
void S_LocalSound(char *s){sounds++;strcpy(last_sound,s);}
void AW_MusicCombat(int on){if(on)music_on++;else music_off++;}
void AW_MusicDeath(void){music_death++;}
double Sys_FloatTime(void){return clock_now+=.0001;}
/* aw_anim.c engine glue: test models have no layout file (previous frames). */
const aw_anim_t *AW_AnimOf(edict_t *e){
    static aw_anim_t a;int i=(int)e->v.modelindex;AW_AnimDefault(&a,i>0 && i<MAX_MODELS && sv.models[i]?sv.models[i]->numframes:1);return &a;
}
int aw_test_mover_on,aw_test_mover_off;static edict_t *aw_test_worn;
int AW_AnimMover(edict_t *e,int on){if(on){if(aw_test_worn)return 0;aw_test_worn=e;aw_test_mover_on++;return 1;}if(aw_test_worn!=e)return 0;aw_test_worn=NULL;aw_test_mover_off++;return 1;}
int AW_AnimMoving(edict_t *e){return e && aw_test_worn==e;}
void Con_Printf(char *f,...){(void)f;printed++;}
void Sys_Error(char *f,...){(void)f;abort();}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
float Q_atof(char *s){return (float)atof(s);}
int AW_CompanionToggleWord(char *a){
    if(!strcasecmp(a,"on") || !strcmp(a,"1"))return 1;
    if(!strcasecmp(a,"off") || !strcmp(a,"0"))return 0;
    return -1;
}
int COM_FOpenFile(char *name,FILE **file){
    char path[160];long n;sprintf(path,"%s/%s",dir,name);
    *file=fopen(path,"rb");if(!*file)return -1;
    fseek(*file,0,SEEK_END);n=ftell(*file);fseek(*file,0,SEEK_SET);return (int)n;
}
static struct {char *name;xcommand_t f;} commands[8];static int command_count;
static cvar_t *cvars[16];static int cvar_count;
void Cmd_AddCommand(char *name,xcommand_t f){commands[command_count].name=name;commands[command_count++].f=f;}
void Cvar_RegisterVariable(cvar_t *v){v->value=(float)atof(v->string);cvars[cvar_count++]=v;}
void Cvar_SetValue(char *name,float value){int i;for(i=0;i<cvar_count;i++)if(!strcmp(cvars[i]->name,name))cvars[i]->value=value;}
static char *argv[6];static int argc;
int Cmd_Argc(void){return argc;}
char *Cmd_Argv(int i){return i<argc?argv[i]:"";}
static void run(const char *line){
    static char buffer[128];char *p;int i;
    strcpy(buffer,line);argc=0;
    for(p=strtok(buffer," ");p && argc<6;p=strtok(NULL," "))argv[argc++]=p;
    for(i=0;i<command_count;i++)if(!strcmp(commands[i].name,argv[0])){commands[i].f();return;}
    assert(!"command not registered");
}
static void result(int won){results[won!=0]++;}
static int voices[5];static void bark(edict_t *e,int event){assert(e && event>=0 && event<5);voices[event]++;}
static void write_file(const char *name,const char *text){
    char path[160];FILE *f;sprintf(path,"%s/%s",dir,name);
    f=fopen(path,"wb");assert(f);fputs(text,f);fclose(f);
}
/* Sheets as tools/prepare_combat.py writes them, with a correct index. */
static void write_actors(void){
    static const char *rows[]={
        "a guard\tA Guard\t5\t40 30 30 40 40 40 30 40\t10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10\t50 20 150\t30 30\t0 26 0 0 0 0 0 0 0 0 0\t1.000 0\tf",
        "mevil molor\tMevil Molor\t9\t62 56 36 63 78 47 35 40\t47 15 15 15 32 37 32 32 52 6 16 6 6 6 11 6 6 38 6 6 38 11 33 11 19 6 38\t94 112 208\t30 30\t4 4 3 14 3 14 1 2 1.0 1.3 15.0\t8.814 1\tf",
        "mevil zz\tOther\t1\t1 1 1 1 1 1 1 1\t1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1\t5 5 5\t0 0\t0 26 0 0 0 0 0 0 0 0 0\t0 0\ta",
        "weakling\tWeakling\t1\t10 10 10 10 10 10 10 10\t5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5 5\t3 5 10\t30 30\t0 26 0 0 0 0 0 0 0 0 0\t0.1 0\ta"};
    char text[4096],index[300];long offset[27];int i,b,at=0,n=sizeof(rows)/sizeof(*rows);
    for(b=0;b<27;b++)offset[b]=-1;
    for(i=0;i<n;i++){b=rows[i][0]-'a';if(offset[b]<0)offset[b]=at;at+=strlen(rows[i])+1;}
    for(b=26;b>=0;b--)if(offset[b]<0)offset[b]=b<26?offset[b+1]:at;
    strcpy(index,"I");for(b=0;b<27;b++)sprintf(index+strlen(index)," %08ld",offset[b]);
    sprintf(text,"AWCA1 %ld\n%s\n",(long)n,index);
    for(i=0;i<n;i++){strcat(text,rows[i]);strcat(text,"\n");}
    write_file("actors.txt",text);
}
static void tick(int n){
    int i;for(i=0;i<n;i++){sv.time+=host_frametime;realtime=sv.time;host_framecount++;AW_CombatPhysics();}
}
int main(void){
    edict_t *p=&edicts[1],*npc=&edicts[2],*resident=&edicts[3];aw_fighter_t f;const aw_fighter_t *sheet;
    float fraction,alpha;int i,before;
    strcpy(dir,"/tmp/awcombatXXXXXX");assert(mkdtemp(dir));
    {char sub[96];sprintf(sub,"%s/combat",dir);mkdir(sub,0700);}
    write_file("combat/settings.txt","AWCS1\nfFatigueBase 1.25\nfFatigueMult 0.5\nfCombatDistance 128\nfHandToHandReach 1\n"
        "fMinHandToHandMult 0.1\nfMaxHandToHandMult 0.5\nfHandtoHandHealthPer 0.1\nfDamageStrengthBase 0.5\n"
        "fDamageStrengthMult 0.1\nfCombatArmorMinMult 0.25\nfCombatKODamageMult 1.5\nfCombatCriticalStrikeMult 4\n"
        "fKnockDownMult 0.5\niKnockDownOddsBase 50\niKnockDownOddsMult 50\nfFatigueAttackBase 2\nfFatigueAttackMult 0\n"
        "fWeaponFatigueMult 0.25\nfFatigueReturnBase 2.5\nfFatigueReturnMult 0.02\nfUnarmoredBase1 0.1\nfUnarmoredBase2 0.065\n"
        "iBlockMinChance 10\niBlockMaxChance 50\nfSwingBlockBase 1\nfSwingBlockMult 1\nfBlockStillBonus 1.25\n"
        "fFatigueBlockBase 4\nfFatigueBlockMult 0\nfWeaponFatigueBlockMult 1\nfCombatBlockLeftAngle -90\n"
        "fCombatBlockRightAngle 30\nfCombatDelayNPC 0.1\nfNPCHealthBarTime 3\nfNPCHealthBarFade 0.5\nfWeaponDamageMult 0.1\n"
        "anim knockdown 2.667\nanim block 1.333 0.25\n"
        "sound health combat/health.wav\nsound miss combat/miss.wav\nsound ../bad x\n");
    write_actors();
    {char from[160],to[160];sprintf(from,"%s/actors.txt",dir);sprintf(to,"%s/combat/actors.txt",dir);assert(!rename(from,to));}

    pr_strings=strings;progs=&program;program.entityfields=sizeof(entvars_t)/4;
    sv.active=1;sv.edicts=edicts;sv.num_edicts=4;sv.models[1]=&model;model.numframes=31;sv.time=1;
    svs.maxclients=1;svs.clients=&client;client.edict=p;cls.state=ca_connected;key_dest=key_game;
    fields[0][2]._float=.9f;                                         /* worldspawn aw_hand_punch */
    p->v.origin[0]=300;p->v.origin[2]=16.625f;p->v.mins[2]=-16.625f;p->v.maxs[0]=7.32f;p->v.health=60;
    aw_character.valid=1;for(i=0;i<8;i++)aw_character.attributes[i]=50;for(i=0;i<27;i++)aw_character.skills[i]=30;
    aw_character.current[0]=aw_character.maximum[0]=60;aw_character.current[2]=aw_character.maximum[2]=200;
    npc->v.classname=add_string("aw_npc");npc->v.netname=add_string("Mevil Molor");npc->v.modelindex=1;
    npc->v.solid=SOLID_BBOX;npc->v.nextthink=2;npc->v.think=7;
    npc->v.mins[0]=-7.32f;npc->v.mins[1]=-7.12f;npc->v.maxs[0]=7.32f;npc->v.maxs[1]=7.12f;npc->v.maxs[2]=33.25f;
    *resident=*npc;resident->v.origin[1]=500;resident->v.netname=add_string("A Guard");
    fields[3][3].string=add_string("a guard");
    AW_CombatInit();aw_combat_result=result;aw_combat_voice=bark;
    assert(aw_combat_enemy_bar && aw_combat_scene);

    /* data files */
    assert(AW_CombatSettingsLoad() && aw_combat_settings.fNPCHealthBarTime==3);
    assert(AW_CombatActorLoad("Mevil Molor",&f) && !strcmp(f.name,"Mevil Molor") && f.level==9 && f.health_max==94);
    assert(f.weapon==4 && f.weapon_skill==AW_SK_BLUNT && f.damage[0][1]==14 && f.shield && f.attributes[AW_AGI]==63);
    assert(f.skills[AW_SK_H2H]==38 && f.fatigue_max==208 && f.armor>8.8f && f.armor<8.82f);
    assert(AW_CombatActorLoad("weakling",&f) && f.health==3);
    assert(AW_CombatActorLoad("a guard",&f) && f.level==5);
    assert(!AW_CombatActorLoad("mevil",&f) && !AW_CombatActorLoad("nobody",&f) && !AW_CombatActorLoad("",&f));
    /* the arena's set fighter replaces the character's sheet while set */
    {
        aw_fighter_t preset;char sub[96];sprintf(sub,"%s/arena",dir);mkdir(sub,0700);
        char used[24];
        write_file("arena/player.txt","AWAP2\ndefault fists\nloadout:fists\tArena Challenger\t9\t67 36 59 60 66 55 35 40\t"
            "23 6 16 11 33 11 16 11 38 6 6 6 6 6 6 23 6 38 15 47 47 32 15 32 15 15 47\t93.0 72 241\t0 0\t0 26 0 0 0 0 0 0 0 0 0\t8.618 0\tp\t0 0 0\n"
            "loadout:sword_shield\tArena Challenger\t9\t67 36 59 60 66 55 35 40\t"
            "40 6 16 11 33 40 16 11 38 6 6 6 6 6 6 23 6 38 15 47 47 32 15 32 15 15 47\t93.0 72 241\t0 0\t2 5 2 14 1 20 4 18 1.0 1.35 20.0\t9.5 1\tp\t900 300 2\n");
        assert(AW_CombatLoadout("",&preset,used) && !strcmp(used,"fists") && preset.skills[AW_SK_H2H]==47 && preset.health_max==93);
        assert(AW_CombatLoadout("sword_shield",&preset,used) && preset.weapon==2 && preset.shield && preset.weapon_health_max==900 &&
               preset.shield_health_max==300 && preset.shield_class==2);
        assert(!AW_CombatLoadout("claymore",&preset,used) && !AW_CombatLoadout("sword",&preset,used));
        assert(AW_CombatLoadout(NULL,&preset,used));
        aw_combat_player_preset=&preset;AW_CombatPlayerSheet(&f);
        assert(f.skills[AW_SK_H2H]==47 && f.health==60 && f.health_max==93 && !strcmp(f.name,"You") && f.armor>8.6f);
        aw_combat_player_preset=NULL;
    }
    AW_CombatPlayerSheet(&f);
    assert(f.health==60 && f.fatigue_max==200 && f.skills[AW_SK_H2H]==30 && !f.weapon && f.armor>5.84f && f.armor<5.86f);

    /* engage from 300 units: it runs in, then swings */
    assert(AW_CombatActorLoad("mevil molor",&f));
    run("aw_combat seed 777");
    assert(AW_CombatEngage(npc,&f,"idle:0:4:0.6667 run:4:6:0.1556 attack:10:8:0.1500:0.667 hit:18:3:0.3333 knock:21:4:0.6667 death:25:6:0.3333"));
    assert(items_shown==1);                       /* engage draws the carried items */
    assert(AW_CombatHostiles()==1 && npc->v.nextthink==0 && AW_CombatSeedUsed()==777);
    tick(1);assert(music_on==1);                                     /* battle music at once */
    tick(10);assert(steps>0 && npc->v.frame>=4 && npc->v.frame<10);  /* run frames */
    for(i=0;i<400 && AW_CombatStats()->npc_swings==0;i++)tick(1);
    assert(AW_CombatStats()->npc_swings==1);
    assert(p->v.origin[0]-npc->v.origin[0]<40);                      /* in reach when it struck */
    /* every swing is replayable: the readout went to the console */
    assert(printed>0);

    /* the player's punch: watched from the button, strikes at 0.71 of the punch */
    target=npc;p->v.button0=1;tick(1);
    fields[1][0]._float=3;fields[1][1]._float=(float)sv.time;p->v.button0=0;
    before=AW_CombatStats()->player_swings;
    tick(10);assert(AW_CombatStats()->player_swings==before);        /* 0.2 s: not yet */
    tick(30);assert(AW_CombatStats()->player_swings==before+1);      /* at 0.64 s: struck once */
    tick(10);assert(AW_CombatStats()->player_swings==before+1);
    /* the enemy bar: 3 s from the attempt, fading over the last 0.5 s */
    assert(aw_combat_enemy_bar(&fraction,&alpha) && alpha==1 && fraction>0 && fraction<=1);
    fields[1][0]._float=2;
    tick(120);assert(aw_combat_enemy_bar(&fraction,&alpha) && alpha<1 && alpha>0);
    tick(20);assert(!aw_combat_enemy_bar(&fraction,&alpha));

    /* the opponent dies: result won, explore music again */
    sheet=AW_CombatFighter(npc);assert(sheet);
    ((aw_fighter_t *)sheet)->health=.01f;((aw_fighter_t *)sheet)->knocked=1;((aw_fighter_t *)sheet)->shield=0;
    aw_character.skills[AW_SK_H2H]=100;
    for(i=0;i<20 && !results[1];i++){
        p->v.button0=1;tick(1);fields[1][0]._float=3;fields[1][1]._float=(float)sv.time;p->v.button0=0;tick(50);
        fields[1][0]._float=2;tick(1);
    }
    assert(results[1]==1 && sheet->dead && npc->v.solid==SOLID_NOT);
    assert(voices[AW_VOICE_START]==1 && voices[AW_VOICE_SWING]>=1 && voices[AW_VOICE_DEATH]==1);
    assert(AW_CombatHostiles()==0);
    tick(2);assert(music_off==1);
    assert(npc->v.frame>=25 && npc->v.frame<31);                      /* death frames */

    /* a resident struck by the player starts a fight (its record's sheet) */
    target=resident;p->v.origin[0]=0;p->v.origin[1]=480;
    p->v.button0=1;tick(1);fields[1][0]._float=3;fields[1][1]._float=(float)sv.time;p->v.button0=0;tick(50);
    fields[1][0]._float=2;
    assert(AW_CombatFighter(resident) && !strcmp(AW_CombatFighter(resident)->name,"A Guard") && AW_CombatHostiles()==1);
    tick(2);assert(music_on==2);

    /* an unreachable player: the NPC flees (runs away 1 s, never warps), re-decides after 3 s */
    {
        float x0,gap0;aw_fighter_t runner;assert(AW_CombatActorLoad("weakling",&runner));
        aw_combat_scene();npc->v.solid=SOLID_BBOX;npc->v.origin[0]=p->v.origin[0]-200;npc->v.origin[1]=p->v.origin[1];
        assert(AW_CombatEngage(npc,&runner,NULL));
        walled=1;
        for(i=0;i<3000 && !AW_CombatStats()->npc_flees;i++)tick(1);
        assert(AW_CombatStats()->npc_flees>=1 && voices[AW_VOICE_FLEE]>=1);
        walled=0;x0=npc->v.origin[0];gap0=p->v.origin[0]-x0;
        tick(25);assert(p->v.origin[0]-npc->v.origin[0]>gap0+50);           /* runs away, no warp */
        tick(25);x0=npc->v.origin[0];tick(50);assert(npc->v.origin[0]==x0);   /* stands and watches */
        tick(100);assert(p->v.origin[0]-npc->v.origin[0]<gap0);              /* re-decided after 3 s: back in */
    }
    /* the player dies: result lost, the death track, no battle music switching while dead */
    {
        aw_fighter_t killer;assert(AW_CombatActorLoad("mevil molor",&killer));
        killer.skills[AW_SK_BLUNT]=255;
        p->v.health=.5f;
        aw_combat_scene();assert(AW_CombatHostiles()==0 && music_off>=2);
        npc->v.solid=SOLID_BBOX;npc->v.origin[0]=p->v.origin[0]-20;npc->v.origin[1]=p->v.origin[1];
        assert(AW_CombatEngage(npc,&killer,NULL));                   /* the model's own frames */
        for(i=0;i<600 && !results[0];i++)tick(1);
        assert(results[0]==1 && music_death==1);
        tick(5);assert(music_death==1);
    }

    /* outside fights the player's fatigue returns: 2.5 + 0.02 x 50 = 3.5 per second */
    aw_combat_scene();p->v.health=60;
    aw_character.current[2]=100;tick(50);
    assert(aw_character.current[2]>103 && aw_character.current[2]<104);

    /* commands and cost */
    run("aw_combat");run("aw_combat readout off");run("aw_combat calm");run("aw_combat off");
    assert(!AW_CombatEngage(npc,&f,NULL));
    run("aw_combat on");
    printf("combat ok: %ld steps, %ld sounds\n",(long)steps,(long)sounds);
    AW_CombatClear();assert(items_hidden>=items_shown);   /* every release hides them */
    return 0;
}
