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
int (*aw_combat_buttons)(int);int (*aw_combat_guard_marker)(void);   /* cl_input.c, aw_ui.c */
void (*aw_defaults_migrate)(int level);                                /* aw_fog.c: the saved configuration's defaults level */
/* aw_items.c (carried weapon/shield entities; its own fixture aga_items_test.c): counted here. */
#include "aw_items.h"
static int items_shown,items_hidden;
/* NPC-NO-SPELLCASTING-65: the fighters' spells (aw_cast.c, aw_magic.c, aw_animkit.c, aw_mwhost.c): no actor record
 * here, so no fighter knows a spell and every fight below stays with weapons and fists (the rules are linked:
 * aw_cast_rules.c, aw_effects.c; their own test is aga_spell_ai_test.c) */
#include "aw_cast.h"
/* NPC-NO-SPELLCASTING-65, the cheaper version: with spell_actor set the fighter has a record that knows two spells;
 * every actor table read of its spells is counted (spell_reads), so the test proves the think reads none after the
 * fight's start */
static int spell_actor;static unsigned long spell_reads;static aw_actor_t spell_record;
/* ACTOR-RANGED-COMBAT-MISSING-66: with ranged_actor set the fighter's record carries ARROWS rounds of AITM row 40 (an
 * arrow, chop 2-6); every round taken off it is counted (removed); the shaft's drawn points are counted; a shot that
 * crosses the player's front (shot_player) hits the player's edict */
static int ranged_actor,arrows,removed,shaft_points;static edict_t *shot_player;
aw_actor_t *AW_MwscriptActorOf(struct edict_s *e,int *row){(void)e;if(row)*row=-1;return spell_actor || ranged_actor?&spell_record:NULL;}
int AW_ActorItems(const aw_actor_t *a,int *items,int *counts,int *equipped,int max){
    (void)a;if(!ranged_actor || max<1 || arrows<=0)return 0;items[0]=40;counts[0]=arrows;equipped[0]=0;return 1;
}
int AW_ActorRemoveItem(aw_actor_t *a,int item,int count){(void)a;assert(item==40 && count==1 && arrows>0);arrows--;removed++;return 1;}
int AW_FxParticles(const float at[3],int count,float spread,const float vel[3],float vel_rand,float life,int r,int g,int b,
                   int gravity){(void)at;(void)spread;(void)vel;(void)vel_rand;(void)life;(void)r;(void)g;(void)b;(void)gravity;
    shaft_points+=count;return count;}
int AW_ActorSpells(const aw_actor_t *a,int *out,int max){
    (void)a;if(!spell_actor || max<2)return 0;spell_reads++;out[0]=5;out[1]=6;return 2;
}
int AW_ActorSpellInfo(int spell,int *type,char *name,int capacity,int *cost){
    (void)spell;if(!spell_actor)return 0;spell_reads++;
    if(type)*type=AW_SPELL_TYPE_SPELL;if(cost)*cost=10;if(name && capacity>0)name[0]=0;return 1;
}
int AW_ActorSpellEffects(int spell,aw_spell_effect_t *out,int max){
    if(!spell_actor || max<1)return 0;spell_reads++;memset(out,0,sizeof(*out));
    out->effect=(int16_t)(spell==5?14:16);out->range=AW_RANGE_TARGET;out->magnitude_min=out->magnitude_max=10;out->duration=1;
    return 1;
}
float AW_PlayerEncumbrance(float *capacity){if(capacity)*capacity=250;return 40;}   /* aw_move.c: the player's load */
int AW_ActorSpellFlags(int spell){(void)spell;if(spell_actor)spell_reads++;return 0;}
int AW_ActorMagicEffect(int index,aw_mgef_t *out){(void)index;if(!spell_actor)return 0;spell_reads++;memset(out,0,sizeof(*out));out->base_cost=5;return 1;}
float AW_ActorStat(const aw_actor_t *a,int stat){(void)a;(void)stat;return 0;}
void AW_ActorModCurrent(aw_actor_t *a,int dynamic,float value){(void)a;(void)dynamic;(void)value;}
float AW_AnimKitCast(edict_t *e,const char *variant){(void)e;(void)variant;return -1;}
unsigned long AW_CastActorCasts(void){return 0;}
int AW_CastActorRelease(edict_t *caster,edict_t *target,int row,float reach){(void)caster;(void)target;(void)row;(void)reach;return -1;}
int AW_CastReady(void){return 0;}
float AW_DialwinEffectCostMult(void){return .5f;}
int AW_MagicCastLookStart(int caster,int mgef,int range,float area){(void)caster;(void)mgef;(void)range;(void)area;return 0;}
void AW_MagicCastLookRelease(int handle,int ok){(void)handle;(void)ok;}
int AW_CompanionPickAim(void){return 0;}      /* aw_companion.c: the right button in pick mode */
/* aw_hand_models.c: the image's hand clip table (FIRST-PERSON-HANDS-IN-C-54): a 0.9 s punch, as the old stamp gave */
float AW_HandDuration(int clip,float fallback){(void)fallback;return clip==3?.9f:fallback;}
int AW_ItemsShow(edict_t *a,edict_t *o[AW_ITEMS_KINDS]){(void)a;o[0]=o[1]=NULL;items_shown++;return 0;}
void AW_ItemsUpdate(edict_t *a,edict_t *i[AW_ITEMS_KINDS]){(void)a;(void)i;}
void AW_ItemsHide(edict_t *i[AW_ITEMS_KINDS]){i[0]=i[1]=NULL;items_hidden++;}
/* aw_levelup.c (its own fixture aga_levelup_rules_test.c): the skill uses the fights report, counted by skill. */
static int skill_uses[27];
int AW_LevelupUse(int skill,int use,float scale){assert(skill>=0 && skill<27 && use==0 && scale==1);skill_uses[skill]++;return 0;}
static char strings[256];static int string_at=1;
static edict_t edicts[16];static client_t client;static dprograms_t program;static model_t model;
static eval_t fields[16][8];
static int walled,steps,sounds,music_on,music_off,music_death,results[2],printed;static edict_t *target;
static char dir[64],last_sound[64];static double clock_now;

static int add_string(const char *s){int at=string_at;strcpy(strings+at,s);string_at+=strlen(s)+1;return at;}
edict_t *EDICT_NUM(int n){return &edicts[n];}
int NUM_FOR_EDICT(edict_t *e){return (int)(e-edicts);}   /* COMBAT-ACTOR-VS-ACTOR-62: a slot's target by number */
eval_t *GetEdictFieldValue(edict_t *e,char *name){
    static const char *names[]={"aw_hand_state","aw_hand_started","aw_hand_punch","aw_source_id"};
    int i;for(i=0;i<4;i++)if(!strcmp(name,names[i]))return &fields[e-edicts][i];
    return NULL;
}
void SV_LinkEdict(edict_t *e,qboolean touch){(void)e;(void)touch;}
trace_t SV_Move(vec3_t a,vec3_t mi,vec3_t ma,vec3_t b,int type,edict_t *e){
    trace_t t;(void)ma;(void)e;aw_sv_move_calls++;
    memset(&t,0,sizeof(t));t.fraction=1;VectorCopy(b,t.endpos);
    if(walled){t.startsolid=1;t.fraction=0;return t;}       /* nowhere to go: no path */
    /* a shot (a point trace that hits bodies) crossing the player's front, from the +x side */
    if(shot_player && type==MOVE_NORMAL && mi==vec3_origin && a[0]>shot_player->v.origin[0]+7 &&
       b[0]<=shot_player->v.origin[0]+7){t.fraction=.5f;t.ent=shot_player;return t;}
    if(b[2]<0 && a[2]>=0){t.fraction=a[2]/(a[2]-b[2]);t.endpos[2]=0;t.plane.normal[2]=1;}
    return t;
}
int AW_AmbientFlags(struct edict_s *e){(void)e;return 0;}
static int stationary;   /* HEART-OF-LORKHAN-FOLLOWS-DAGOTH-65: the fighter's record moves by no means */
int AW_ActorStationary(struct edict_s *e){(void)e;return stationary;}
int aw_move_werewolf;   /* the player's werewolf form (aw_move.c): never here */
float AW_ActorCarriedWeight(const aw_actor_t *a){(void)a;return 0;}   /* the fighters here carry nothing */
int AW_AmbientInWater(const float p[3]){(void)p;return 0;}   /* the swimmer chase's water test (never reached here) */   /* every fighter here walks (the flyer chase: test_ambient_lut.py) */
qboolean AW_ActorStep(edict_t *e,vec3_t move,double dt){(void)dt;if(walled)return false;e->v.origin[0]+=move[0];e->v.origin[1]+=move[1];aw_sv_move_calls+=3;steps++;return true;}
edict_t *AW_NPCTargetReach(edict_t *p,vec3_t angles,float reach){(void)p;(void)angles;assert(reach>32 && reach<64);return target;}
void S_LocalSound(char *s){sounds++;strcpy(last_sound,s);}
void S_LocalSoundBeside(char *s){S_LocalSound(s);}   /* one blow's sounds side by side (snd_dma.c) */
/* the fighters' group sound keys (aw_anim.c, not in the host part): counted */
static int group_sound_calls;
int AW_AnimMedium(edict_t *e){(void)e;return 0;}
void AW_AnimSounds(edict_t *e,const aw_anim_t *a,int group,unsigned long crossed,int medium){(void)e;(void)a;(void)group;(void)crossed;(void)medium;group_sound_calls++;}
void AW_MusicCombat(int on){if(on)music_on++;else music_off++;}
void AW_MusicDeath(void){music_death++;}
double Sys_FloatTime(void){return clock_now+=.0001;}
/* aw_anim.c engine glue: test models have no layout file (previous frames). */
static const aw_anim_t *anim_layout;   /* DAGOTH-UR-NO-ANIMATIONS-65: a skeletal fighter's own .anm layout */
const aw_anim_t *AW_AnimOf(edict_t *e){
    static aw_anim_t a;int i=(int)e->v.modelindex;
    if(anim_layout)return anim_layout;
    AW_AnimDefault(&a,i>0 && i<MAX_MODELS && sv.models[i]?sv.models[i]->numframes:1);return &a;
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
/* The actor record (aw_actorstate.c, aw_mwhost.c): one creature, "daedroth" (COMBAT-DAEDROTH-NO-HIT-51). */
static int actor_tables=1;
int AW_MwscriptActors(void){return actor_tables;}
int AW_ActorFind(const char *id){return !strcmp(id,"daedroth")?7:!strcmp(id,"a guard")?9:AW_ACTOR_NONE;}
/* ESSENTIAL-DEATH-60: the resident "a guard" has a record whose flags this test sets; the message box is counted */
static int guard_flags,boxes;static char box_text[320];
void AW_MsgBoxShow(const char *text,const char *const *buttons,int count){assert(!buttons && count==0);boxes++;strcpy(box_text,text);}
int AW_ActorBase(int row,aw_actor_base_t *out){
    int i;
    if(row==9){memset(out,0,sizeof(*out));out->flags=(unsigned char)guard_flags;return 1;}
    if(row!=7)return 0;
    memset(out,0,sizeof(*out));out->kind=1;out->level=16;out->health=180;out->fatigue=400;out->magicka=50;
    for(i=0;i<8;i++)out->attributes[i]=60;
    for(i=0;i<27;i++)out->skills[i]=70;              /* the combat value in every combat skill (getSkill) */
    out->fight=90;out->attack[0]=15;out->attack[1]=35;out->attack[2]=15;out->attack[3]=35;out->attack[4]=15;out->attack[5]=35;
    return 1;
}
/* NPC-CREATURE-COMBAT-STYLE-STATS-66: the daedroth's row equips no weapon (its own attacks stay) */
int AW_ActorWeaponEnchant(int row,int *item){(void)row;if(item)*item=-1;return AW_ACTOR_NONE;}
int AW_ActorItem(int item,aw_item_t *out){
    if(item!=40)return 0;
    memset(out,0,sizeof(*out));out->kind=AWK_WEAPON;out->type=12;out->damage[0]=2;out->damage[1]=6;return 1;
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
static int equipment_stores;
static aw_fighter_t equipment_saved;
static void test_equipment_store(const aw_fighter_t *sheet) {
    equipment_saved=*sheet;equipment_stores++;
}
static void test_equipment_apply(aw_fighter_t *sheet) {
    sheet->weapon=2;sheet->weapon_skill=AW_SK_LONG;
    sheet->shield=1;sheet->shield_class=2;sheet->armor=12;
    sheet->weapon_health=123;sheet->weapon_health_max=900;
    sheet->shield_health=45;sheet->shield_health_max=300;
    /* A bad adapter must not let equipment refresh reset active combat. */
    sheet->health=999;sheet->fatigue=999;sheet->knocked=0;sheet->dead=0;
}
/* INVENTORY-NO-ARMOR-RATING-61: an active Shield of 10 on the player */
static int shield_asked=-1;
static float test_shield(struct edict_s *actor,int effect){(void)actor;shield_asked=effect;return effect==3?10:0;}
int main(void){
    edict_t *p=&edicts[1],*npc=&edicts[2],*resident=&edicts[3];aw_fighter_t f;const aw_fighter_t *sheet;
    float fraction,alpha;int i,before;
    /* MWSCRIPT-INVENTORY-HITONME-62: the last weapon per victim (OpenMW OpHitOnMe: read 1 and cleared on a match, a
     * mismatch keeps it; a victim keeps one row; a new victim past the rows takes the oldest) */
    AW_CombatLastHitReset();assert(AW_CombatLastHitCount()==0 && !AW_CombatLastHitTake(7,0x11));
    AW_CombatLastHitSet(0,0x11);assert(AW_CombatLastHitCount()==0);          /* no reference: nothing kept */
    AW_CombatLastHitSet(7,0x11);AW_CombatLastHitSet(7,0x22);assert(AW_CombatLastHitCount()==1);
    assert(!AW_CombatLastHitTake(7,0x11) && AW_CombatLastHitTake(7,0x22) && !AW_CombatLastHitTake(7,0x22));
    for(i=1;i<=AW_COMBAT_LAST_HITS+1;i++)AW_CombatLastHitSet((unsigned long)i,0x100+(unsigned long)i);
    assert(AW_CombatLastHitCount()==AW_COMBAT_LAST_HITS && !AW_CombatLastHitTake(1,0x101));
    assert(AW_CombatLastHitTake(AW_COMBAT_LAST_HITS+1,0x100+AW_COMBAT_LAST_HITS+1) && AW_CombatLastHitTake(2,0x102));
    AW_CombatLastHitReset();assert(AW_CombatLastHitCount()==0 && !AW_CombatLastHitTake(3,0x103));
    assert(aw_combat_weapon_hit==NULL);
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
        "fCombatAngleXY 60\nfCombatAngleZ 60\nfCombatInvisoMult 0.2\n"
        "anim knockdown 2.667\nanim block 1.333 0.25\n"
        "sound health combat/health.wav\nsound miss combat/miss.wav\nsound ../bad x\n");
    write_actors();
    {char from[160],to[160];sprintf(from,"%s/actors.txt",dir);sprintf(to,"%s/combat/actors.txt",dir);assert(!rename(from,to));}

    pr_strings=strings;progs=&program;program.entityfields=sizeof(entvars_t)/4;
    sv.active=1;sv.edicts=edicts;sv.num_edicts=4;sv.models[1]=&model;model.numframes=31;sv.time=1;
    svs.maxclients=1;svs.clients=&client;client.edict=p;client.active=client.spawned=1;cls.state=ca_connected;key_dest=key_game;
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
    assert(aw_combat_enemy_bar && aw_combat_scene && aw_defaults_migrate==AW_CombatDefaultsMigrate);

    /* data files */
    assert(AW_CombatSettingsLoad() && aw_combat_settings.fNPCHealthBarTime==3);
    assert(AW_CombatActorLoad("Mevil Molor",&f) && !strcmp(f.name,"Mevil Molor") && f.level==9 && f.health_max==94);
    assert(f.weapon==4 && f.weapon_skill==AW_SK_BLUNT && f.damage[0][1]==14 && f.shield && f.attributes[AW_AGI]==63);
    assert(f.skills[AW_SK_H2H]==38 && f.fatigue_max==208 && f.armor>8.8f && f.armor<8.82f);
    assert(AW_CombatActorLoad("weakling",&f) && f.health==3);
    /* a creature: no row in combat/actors.txt, its sheet from the actor record (COMBAT-DAEDROTH-NO-HIT-51) */
    assert(AW_CombatActorLoad("Daedroth",&f) && f.creature==1 && f.health_max==180 && f.fight==90 && f.armor==0);
    assert(f.damage[0][0]==15 && f.damage[2][1]==35 && !f.weapon && f.skills[AW_SK_H2H]==70);
    actor_tables=0;assert(!AW_CombatActorLoad("daedroth",&f));actor_tables=1;
    assert(!AW_CombatActorLoad("nobody at all",&f));
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
    /* INVENTORY-NO-ARMOR-RATING-61: the inventory window's rating (OpenMW npc.cpp getArmorRating): the sheet's, plus
     * the magnitude of an active Shield effect (effect 3) */
    {
        extern float (*aw_worldui_armor_rating)(void);float r=AW_CombatPlayerArmorRating();
        assert(r>5.84f && r<5.86f && aw_worldui_armor_rating==AW_CombatPlayerArmorRating);
        aw_combat_effect_magnitude=test_shield;r=AW_CombatPlayerArmorRating();
        assert(r>15.84f && r<15.86f && shield_asked==3);
        aw_combat_effect_magnitude=NULL;
    }

    /* engage from 300 units: it runs in, then swings */
    assert(AW_CombatActorLoad("mevil molor",&f));
    run("aw_combat_cmd seed 777");
    assert(AW_CombatEngage(npc,&f,"idle:0:4:0.6667 run:4:6:0.1556 attack:10:8:0.1500:0.667 hit:18:3:0.3333 knock:21:4:0.6667 death:25:6:0.3333"));
    assert(items_shown==1);                       /* engage draws the carried items */
    assert(AW_CombatHostiles()==1 && npc->v.nextthink==0 && AW_CombatSeedUsed()==777);
    tick(1);assert(music_on==1 && AW_PlayerInCombat());              /* battle music at once: in a fight */
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
    /* ENEMY-HEALTH-BAR-62: the crosshair's ray meets nobody (a flyer or a small creature beside the crosshair); the
     * swing takes the fighter in the original's hit cone, and the bar shows its health share from that first swing */
    {int contacts=AW_CombatStats()->player_contacts,swings;const aw_fighter_t *foe=AW_CombatFighter(npc);
     target=NULL;p->v.v_angle[1]=npc->v.origin[0]<p->v.origin[0]?180:0;
     p->v.button0=1;tick(1);fields[1][0]._float=3;fields[1][1]._float=(float)sv.time;p->v.button0=0;tick(50);fields[1][0]._float=2;
     assert(AW_CombatStats()->player_contacts==contacts+1);
     assert(aw_combat_enemy_bar(&fraction,&alpha) && alpha==1 && foe && fabsf(fraction-foe->health/foe->health_max)<.001f);
     tick(160);assert(!aw_combat_enemy_bar(&fraction,&alpha));       /* gone after fNPCHealthBarTime */
     /* facing away: no contact, no bar */
     p->v.v_angle[1]+=180;swings=AW_CombatStats()->player_swings;
     p->v.button0=1;tick(1);fields[1][0]._float=3;fields[1][1]._float=(float)sv.time;p->v.button0=0;tick(50);fields[1][0]._float=2;
     assert(AW_CombatStats()->player_swings==swings+1 && AW_CombatStats()->player_contacts==contacts+1 && !aw_combat_enemy_bar(&fraction,&alpha));
     /* dbg combat contact off: the ray alone (the earlier rule) */
     p->v.v_angle[1]-=180;run("aw_combat_cmd contact off");
     p->v.button0=1;tick(1);fields[1][0]._float=3;fields[1][1]._float=(float)sv.time;p->v.button0=0;tick(50);fields[1][0]._float=2;
     assert(AW_CombatStats()->player_contacts==contacts+1 && !aw_combat_enemy_bar(&fraction,&alpha));
     run("aw_combat_cmd contact on");p->v.v_angle[1]=0;target=npc;}
    /* BEST-ATTACK-OPTION-62: on by default; a configuration from before level 2 takes it once */
    {int i,found=0;
     for(i=0;i<cvar_count;i++)if(!strcmp(cvars[i]->name,"aw_combat_best_attack")){found=1;assert(!strcmp(cvars[i]->string,"1"));
         Cvar_SetValue("aw_combat_best_attack",0);AW_CombatDefaultsMigrate(1);assert(cvars[i]->value==1);
         Cvar_SetValue("aw_combat_best_attack",0);AW_CombatDefaultsMigrate(2);assert(cvars[i]->value==0);
         run("aw_combat_cmd bestattack on");assert(cvars[i]->value==1);}
     assert(found);}

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
    assert(AW_CombatHostiles()==0 && !AW_PlayerInCombat());          /* the fight is over: calm */
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
        /* runs away at its own run (ACTOR-MECHANICS-USE-STATS-66: Speed 10, Athletics 5: 110 x 1.80 = 198 original units,
         * 49.5 game units a second: about 22.8 in these 25 ticks; the old fixed 200 went about 92), no warp */
        tick(25);assert(p->v.origin[0]-npc->v.origin[0]>gap0+18 && p->v.origin[0]-npc->v.origin[0]<gap0+28);
        tick(25);x0=npc->v.origin[0];tick(50);assert(npc->v.origin[0]==x0);   /* stands and watches */
        tick(200);assert(p->v.origin[0]-npc->v.origin[0]<gap0);              /* re-decided after 3 s: back in (at its own run) */
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
        assert(AW_CombatHostiles()==1 && !AW_PlayerInCombat());          /* dead: no longer "in a fight" */
        tick(5);assert(music_death==1);
        /* the quick retry (aw_view.c "Retry fight", an AmiWind extension): everyone back where and as the
         * fight began, the opponent still hostile; dying again plays the death track again */
        assert(AW_CombatRetryAvailable() && AW_CombatDeathMusicPlayed() && p->v.health<=0);
        {float start_x=p->v.origin[0]-20;npc->v.origin[0]+=7;p->v.origin[1]+=3;
         assert(AW_CombatRetry());
         assert(p->v.health==.5f && !AW_CombatRetryAvailable() && !AW_CombatDeathMusicPlayed() && AW_CombatHostiles()==1);
         assert(npc->v.origin[0]==start_x && p->v.origin[1]==npc->v.origin[1] && AW_CombatPlayer() && !AW_CombatPlayer()->dead);}
        assert(!AW_CombatRetry());                                   /* only after a death */
        for(i=0;i<600 && results[0]<2;i++)tick(1);
        assert(results[0]==2 && music_death==2 && AW_CombatRetryAvailable());
        AW_CombatClear();assert(!AW_CombatRetryAvailable());
    }

    /* outside fights the player's fatigue returns: 2.5 + 0.02 x 50 = 3.5 per second */
    aw_combat_scene();p->v.health=60;
    aw_character.current[2]=100;tick(50);
    assert(aw_character.current[2]>103 && aw_character.current[2]<104);

    /* Blocking (COMBAT-BLOCKING-36). aw_combat_block 1 (option, AmiWind extension): the player blocks
     * only while the block button (+aw_alt, the right mouse button) is held, and every blow is still
     * decided by the original formula; no swing while guarding. 0 (default): the original automatic block. */
    {
        aw_fighter_t shieldp,brute;char used[24];unsigned long held_blocks,free_blocks,auto_blocks;
        assert(aw_combat_buttons && aw_combat_guard_marker==AW_CombatGuarding);
        {   /* COMBAT-BLOCK-DEFAULT-62: the default is the original automatic block (aw_combat_block 0) */
            int i,found=0;
            for(i=0;i<cvar_count;i++)if(!strcmp(cvars[i]->name,"aw_combat_block")){found=1;assert(!strcmp(cvars[i]->string,"0"));}
            assert(found);
        }
        run("aw_combat_cmd block hold");              /* the held block is the option under test here */
        AW_CombatClear();aw_combat_scene();
        run("+aw_alt");assert(!AW_CombatGuarding() && aw_combat_buttons(1)==1);   /* the character: no shield */
        run("-aw_alt");
        assert(AW_CombatLoadout("sword_shield",&shieldp,used) && shieldp.shield);
        aw_combat_player_preset=&shieldp;
        run("+aw_alt");assert(AW_CombatGuarding() && aw_combat_guard_marker() && aw_combat_buttons(3)==2);  /* attack masked */
        run("-aw_alt");assert(!AW_CombatGuarding() && aw_combat_buttons(3)==3);
        assert(AW_CombatActorLoad("mevil molor",&brute));
        brute.skills[AW_SK_BLUNT]=100;brute.health=brute.health_max=100000;
        p->v.health=100000;p->v.angles[1]=180;                  /* facing the attacker on -X */
        npc->v.solid=SOLID_BBOX;npc->v.origin[0]=p->v.origin[0]-20;npc->v.origin[1]=p->v.origin[1];
        run("aw_combat_cmd seed 4242");
        /* held: blocks happen */
        assert(AW_CombatEngage(npc,&brute,NULL));run("+aw_alt");
        for(i=0;i<20000 && AW_CombatStats()->npc_swings<40;i++)tick(1);
        held_blocks=AW_CombatStats()->player_blocks;assert(AW_CombatStats()->npc_swings>=40 && held_blocks>0);
        assert(AW_CombatStats()->guards==1);
        /* not held: no block at all under the held-block rule */
        run("-aw_alt");AW_CombatClear();p->v.health=100000;
        assert(AW_CombatEngage(npc,&brute,NULL));
        for(i=0;i<20000 && AW_CombatStats()->npc_swings<40;i++)tick(1);
        free_blocks=AW_CombatStats()->player_blocks;assert(AW_CombatStats()->npc_swings>=40 && free_blocks==0);
        /* the original automatic block: blocks without the button */
        run("aw_combat_cmd block auto");AW_CombatClear();p->v.health=100000;
        assert(AW_CombatEngage(npc,&brute,NULL));
        for(i=0;i<20000 && AW_CombatStats()->npc_swings<40;i++)tick(1);
        auto_blocks=AW_CombatStats()->player_blocks;assert(auto_blocks>0);
        run("+aw_alt");assert(!AW_CombatGuarding() && aw_combat_buttons(1)==1);    /* automatic: no guard, attack free */
        run("-aw_alt");run("aw_combat_cmd block hold");
        AW_CombatClear();aw_combat_player_preset=NULL;p->v.health=60;p->v.angles[1]=0;
        printf("blocking ok: held %lu, not held %lu, automatic %lu of 40 blows\n",held_blocks,free_blocks,auto_blocks);
        /* LEVEL-UP-58: every block the player made is one Block use */
        assert(skill_uses[AW_SK_BLOCK]==(int)(held_blocks+auto_blocks));
    }

    /* Actual equipment updates preserve live vital/status state and condition. */
    {
        aw_fighter_t *live;float hp,fp;int hostiles;
        AW_CombatClear();p->v.health=60;
        assert(AW_CombatActorLoad("mevil molor",&f));
        assert(AW_CombatEngage(npc,&f,NULL));
        live=(aw_fighter_t *)AW_CombatPlayer();assert(live);
        live->health=37;live->fatigue=-5;live->knocked=2;
        live->weapon_health=67;live->shield_health=12;
        hp=live->health;fp=live->fatigue;hostiles=AW_CombatHostiles();
        aw_combat_equipment_store=test_equipment_store;
        aw_combat_equipment=test_equipment_apply;
        AW_CombatEquipmentStore();
        assert(equipment_stores==1 && equipment_saved.weapon_health==67 &&
               equipment_saved.shield_health==12);
        AW_CombatEquipmentChanged();
        assert(live->health==hp && live->fatigue==fp && live->knocked==2 &&
               AW_CombatHostiles()==hostiles && aw_combat_input_locked());
        assert(live->weapon==2 && live->shield && live->armor==12 &&
               live->weapon_health==123 && live->shield_health==45);
        /* A disabled combat simulation must not retain its movement lock:
         * recovery is suspended while the raw cvar is off. */
        Cvar_SetValue("aw_combat",0);
        assert(!aw_combat_input_locked());
        Cvar_SetValue("aw_combat",1);
        assert(aw_combat_input_locked());
        aw_combat_equipment_store=NULL;aw_combat_equipment=NULL;
        AW_CombatClear();
    }
    /* COMBAT-DEAD-ACTOR-RELOAD-59: a killed actor's saved death applied on a scene load (aw_actors.c ApplyLoaded,
     * "chim actors kill") takes a combat slot only to hold the corpse: no "attacks" line, no encounter, no weapon
     * drawn, no battle cry, never counted as a hostile. */
    {int was_printed,was_shown,was_start;float h=-1;
     AW_CombatClear();run("aw_combat_cmd readout on");
     was_printed=printed;was_shown=items_shown;was_start=voices[AW_VOICE_START];
     assert(AW_CombatTestEngage(resident,1));
     assert(printed==was_printed && items_shown==was_shown && voices[AW_VOICE_START]==was_start);
     assert(AW_CombatSlotState(resident,&h)==2 && h==0 && AW_CombatHostiles()==0 && !AW_PlayerInCombat());
     AW_CombatClear();
     /* a living engage still announces itself */
     assert(AW_CombatTestEngage(resident,0));
     assert(printed==was_printed+1 && items_shown==was_shown+1 && voices[AW_VOICE_START]==was_start+1);
     assert(AW_CombatSlotState(resident,NULL)==1 && AW_CombatHostiles()==1);
     AW_CombatClear();}
    /* ESSENTIAL-DEATH-60: a death shows the game's own sKilledEssential text (view/settings.txt) only for a record with
     * the essential flag (AWR_ESSENTIAL 2); the record flags come from the actor table, the words from the file */
    {int shown_before;char sub[96];
     sprintf(sub,"%s/view",dir);mkdir(sub,0700);
     write_file("view/settings.txt","AWVS1\nfVanityDelay 30\nsKilledEssential Test essential words\\none line.\n");
     AW_CombatClear();guard_flags=0;shown_before=boxes;
     assert(AW_CombatTestEngage(resident,1));
     assert(boxes==shown_before);                                   /* an ordinary record: no box */
     AW_CombatClear();guard_flags=2;                                /* essential */
     assert(AW_CombatTestEngage(resident,1));
     assert(boxes==shown_before+1 && !strcmp(box_text,"Test essential words one line."));
     /* ESSENTIAL-DEATH-MESSAGE-66: a death of the actor record alone (a script, a spell, a fall) shows it too, once per
      * death: the record's report of the same reference right after is not a second box; another reference's is */
     AW_CombatEssentialKilled(4242,"Caius");assert(boxes==shown_before+2 && !strcmp(box_text,"Test essential words one line."));
     AW_CombatEssentialKilled(4242,"Caius");assert(boxes==shown_before+2);
     AW_CombatEssentialKilled(4243,NULL);assert(boxes==shown_before+3);
     /* OUTDOOR-DEAD-BODY-GONE-66: a saved death laid down again (a room's, the home map's or a joining cell's body) is
      * the same corpse but no new death: no box, even long after the last one */
     AW_CombatClear();guard_flags=2;realtime+=100;
     assert(AW_CombatLayCorpse(resident));
     assert(boxes==shown_before+3 && AW_CombatSlotState(resident,NULL)==2);
     {int essential=0;assert(AW_CombatEssentialRecord("a guard",&essential) && essential);
      guard_flags=0;assert(AW_CombatEssentialRecord("a guard",&essential) && !essential);
      assert(!AW_CombatEssentialRecord("nobody",&essential) && !essential);}
     guard_flags=0;AW_CombatClear();}
    /* MUSIC-DEATH-TRACK-RANDOM-60: an area change mid-fight. The new map's settle frames and the signon frames see the
     * fresh client edict at health 0 and the old map's slots: no death, no death track; play goes on once spawned. */
    {int deaths=music_death;
     AW_CombatClear();p->v.health=60;p->v.button0=0;
     assert(AW_CombatActorLoad("mevil molor",&f) && AW_CombatEngage(npc,&f,NULL));
     tick(2);assert(AW_PlayerInCombat());
     client.spawned=0;p->v.health=0;                             /* settle frames / before Host_Spawn_f */
     tick(3);assert(music_death==deaths && !AW_CombatDeathMusicPlayed() && results[0]==2);
     client.active=0;tick(2);assert(music_death==deaths);       /* before "connect local" */
     aw_combat_scene();client.active=client.spawned=1;p->v.health=60;   /* the scene set-up, the health back */
     tick(3);assert(music_death==deaths && !AW_CombatDeathMusicPlayed());
     AW_CombatClear();}
    /* CREATURE-COMBAT-FRAMES-MISSING-61: a fighter laid out on the model it wore at the engage (the walker's 38-frame
     * mover) and then put back on a smaller model (its 16-frame standing one) plays only frames that model has */
    {static model_t standing;int seen=0,top=-1;
     AW_CombatClear();p->v.health=60;p->v.button0=0;
     npc->v.solid=SOLID_BBOX;npc->v.origin[0]=p->v.origin[0]-200;npc->v.origin[1]=p->v.origin[1];
     assert(AW_CombatActorLoad("mevil molor",&f));
     assert(AW_CombatEngage(npc,&f,"idle:0:4:0.6667 run:4:6:0.1556 attack:10:8:0.1500:0.667 hit:18:3:0.3333 knock:21:4:0.6667 death:25:6:0.3333"));
     tick(2);
     standing.numframes=16;sv.models[2]=&standing;npc->v.modelindex=2;   /* the mover taken off under the fight */
     for(i=0;i<400;i++){tick(1);seen++;if(npc->v.frame>top)top=(int)npc->v.frame;assert(npc->v.frame>=0 && npc->v.frame<16);}
     assert(seen==400 && top>=0);
     npc->v.modelindex=1;sv.models[2]=NULL;AW_CombatClear();}
    /* HEART-OF-LORKHAN-FOLLOWS-DAGOTH-65: a fighter whose creature record can move by no means (the Heart of Lorkhan)
     * stays where it stands 200 units off for 10 s; the same fighter able to walk closes in */
    {float x0;
     AW_CombatClear();p->v.health=60;p->v.button0=0;stationary=1;
     npc->v.solid=SOLID_BBOX;npc->v.origin[0]=p->v.origin[0]-200;npc->v.origin[1]=p->v.origin[1];x0=npc->v.origin[0];
     assert(AW_CombatActorLoad("mevil molor",&f) && AW_CombatEngage(npc,&f,NULL));
     tick(500);assert(npc->v.origin[0]==x0 && npc->v.origin[1]==p->v.origin[1]);
     AW_CombatClear();stationary=0;
     assert(AW_CombatEngage(npc,&f,NULL));tick(100);assert(npc->v.origin[0]>x0+50);
     AW_CombatClear();printf("stationary fighter ok: stayed at %.0f, the walker moved\n",(double)x0);}
    /* DAGOTH-UR-NO-ANIMATIONS-65: a skeletal fighter (Dagoth Ur's table layout from tools/creature_tables.py, with
     * its spellcast group) plays its own run, attack and cast frames, not the idle's; without a cast group the cast
     * stands on the idle */
    {static aw_anim_t a;int base=-1,count=-1;
     static const char dagoth[]="idle:30:8:0.1250 walk:116:9:0.1289:46.59 run:133:8:0.1289:75.75 "
         "attack:96:8:0.1250:0.400 hit:249:5:0.1467 death:320:11:0.1333 cast:141:12:0.1250 @attack:2:roar";
     assert(AW_AnimParse(&a,dagoth,400) && a.from_layout && a.g[AW_ANIM_CAST].present);
     anim_layout=&a;AW_CombatClear();p->v.health=60;p->v.button0=0;
     assert(AW_CombatActorLoad("mevil molor",&f) && AW_CombatEngage(npc,&f,NULL));
     assert(AW_CombatGroupFrames(npc,"run",&base,&count) && base==133 && count==8);
     assert(AW_CombatGroupFrames(npc,"attack",&base,&count) && base==96 && count==8);
     assert(AW_CombatGroupFrames(npc,"cast",&base,&count) && base==141 && count==12);
     assert(AW_CombatGroupFrames(npc,"idle",&base,&count) && base==30 && count==8);
     assert(!AW_CombatGroupFrames(npc,"swim",&base,&count) && !AW_CombatGroupFrames(resident,"run",&base,&count));
     AW_CombatClear();
     assert(AW_AnimParse(&a,"idle:30:8:0.1250 run:133:8:0.1289:75.75 attack:96:8:0.1250:0.400",400));
     assert(AW_CombatEngage(npc,&f,NULL) && AW_CombatGroupFrames(npc,"cast",&base,&count) && base==30 && count==8);
     AW_CombatClear();anim_layout=NULL;printf("skeletal fighter groups ok: run, attack and cast found\n");}
    /* commands and cost */
    run("aw_combat_cmd");run("aw_combat_cmd readout off");run("aw_combat_cmd calm");run("aw_combat_cmd off");
    assert(!AW_CombatEngage(npc,&f,NULL));
    run("aw_combat_cmd on");
    /* LEVEL-UP-58: the player's landed blows report their skill, the blows the player took the armour or Unarmored */
    {int armour=skill_uses[AW_SK_LIGHT]+skill_uses[AW_SK_MEDIUM]+skill_uses[AW_SK_HEAVY]+skill_uses[AW_SK_UNARMORED];
     assert(skill_uses[AW_SK_H2H]>0 && armour>0);
     printf("skill uses ok: hand-to-hand %ld, block %ld, armour or unarmored %ld\n",(long)skill_uses[AW_SK_H2H],
            (long)skill_uses[AW_SK_BLOCK],(long)armour);}
    /* COMBAT-ACTOR-VS-ACTOR-62 (v0.0.63): two actors set against each other fight each other, not the player: each
     * targets the other, no battle music, no hostile of the player; the blows land between them (the guard's health
     * falls); the fight ends when one is dead: the other is released, and a fight with the player is untouched */
    {aw_fighter_t a,b;int fights=0,k;
     AW_CombatClear();p->v.health=60;p->v.button0=0;music_on=0;
     npc->v.solid=resident->v.solid=SOLID_BBOX;npc->v.health=resident->v.health=0;
     npc->v.origin[0]=1000;npc->v.origin[1]=0;resident->v.origin[0]=1020;resident->v.origin[1]=0;
     p->v.origin[0]=300;
     assert(AW_CombatActorLoad("mevil molor",&a) && AW_CombatActorLoad("a guard",&b));
     b.health=b.health_max=8;
     assert(AW_CombatEngageAgainst(npc,&a,resident,&b));
     assert(AW_CombatTargetOf(npc,&fights)==resident && !fights);
     assert(AW_CombatTargetOf(resident,&fights)==npc && !fights);
     assert(AW_CombatHostiles()==0 && !AW_PlayerInCombat());     /* no hostile of the player */
     for(k=0;k<4000 && AW_CombatActorState(resident)==1 && AW_CombatActorState(npc)==1;k++)tick(1);
     assert(AW_CombatActorState(resident)==2 || AW_CombatActorState(npc)==2);   /* one of them died of the other's blows */
     tick(2);
     assert(!AW_CombatTargetOf(npc,&fights) && !AW_CombatTargetOf(resident,&fights));
     assert(AW_CombatActorState(npc)!=1 || AW_CombatActorState(resident)!=1);  /* the survivor was released */
     assert(music_on==0);
     AW_CombatClear();
     printf("actor vs actor ok: %ld ticks\n",(long)k);}
    /* NPC-NO-SPELLCASTING-65, the cheaper version: a fighter that knows two spells reads them (list, row, effects,
     * flags, MGEF: 1 + 4 x 2 reads) once, at its first choice; the next choices (one a second) read nothing */
    {aw_fighter_t a;unsigned long at_start,stats_reads;int k;
     AW_CombatClear();p->v.health=60;p->v.button0=0;npc->v.solid=SOLID_BBOX;npc->v.health=0;
     npc->v.origin[0]=1000;npc->v.origin[1]=0;p->v.origin[0]=300;
     assert(AW_CombatActorLoad("mevil molor",&a));
     spell_actor=1;spell_reads=0;stats_reads=AW_CombatStats()->npc_spell_reads;
     assert(AW_CombatEngage(npc,&a,NULL));
     assert(spell_reads==0);                                   /* nothing read before its first think */
     for(k=0;k<100 && spell_reads==0;k++)tick(1);
     at_start=spell_reads;
     assert(at_start==9 && AW_CombatStats()->npc_spell_reads-stats_reads==9);
     for(k=0;k<600;k++)tick(1);                                /* several more choices */
     assert(spell_reads==at_start && AW_CombatStats()->npc_spell_reads-stats_reads==9);
     AW_CombatClear();
     /* a new fight reads them again (the slot is new) */
     assert(AW_CombatEngage(npc,&a,NULL));
     for(k=0;k<100 && spell_reads==at_start;k++)tick(1);
     assert(spell_reads==2*at_start);
     AW_CombatClear();spell_actor=0;
     printf("spell cache ok: %lu reads at the fight's start, none in the next %ld ticks\n",at_start,(long)600);}
    /* ACTOR-RANGED-COMBAT-MISSING-66: an archer (a bow on its sheet, 3 arrows on its record) 200 units away keeps its
     * place and shoots: each shot takes one arrow off the record, flies (drawn as a shaft) and hits the player (a sure
     * Marksman); a shot that crosses nobody misses; out of arrows it closes in by hand */
    {aw_fighter_t a;int k;float x0,h0;
     AW_CombatClear();p->v.health=1000;p->v.button0=0;npc->v.solid=SOLID_BBOX;npc->v.health=0;
     npc->v.origin[0]=500;npc->v.origin[1]=0;p->v.origin[0]=300;x0=npc->v.origin[0];h0=p->v.health;
     assert(AW_CombatActorLoad("mevil molor",&a));
     a.weapon=10;a.weapon_skill=AW_SK_MARKSMAN;a.skills[AW_SK_MARKSMAN]=200;a.shield=0;
     a.damage[0][0]=5;a.damage[0][1]=20;a.reach=1;a.speed=1;
     ranged_actor=1;arrows=3;removed=0;shaft_points=0;shot_player=p;
     assert(AW_CombatEngage(npc,&a,NULL));
     for(k=0;k<3000 && removed<3;k++)tick(1);
     assert(removed==3 && arrows==0 && npc->v.origin[0]==x0);     /* three shots from where it stood */
     tick(300);                                                   /* the last one lands */
     assert(shaft_points>0 && p->v.health<h0);
     shot_player=NULL;
     for(k=0;k<600 && npc->v.origin[0]==x0;k++)tick(1);
     assert(npc->v.origin[0]<x0);                                 /* out of arrows: it closes in */
     printf("ranged ok: 3 arrows shot from %.0f, health %.0f -> %.0f, shaft points %ld\n",(double)x0,(double)h0,
            (double)p->v.health,(long)shaft_points);
     AW_CombatClear();ranged_actor=0;p->v.health=60;}
    printf("combat ok: %ld steps, %ld sounds\n",(long)steps,(long)sounds);
    AW_CombatClear();assert(items_hidden>=items_shown);   /* every release hides them */
    return 0;
}
