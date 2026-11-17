/* SPDX-License-Identifier: GPL-2.0-or-later
 * Melee combat on the server's edicts, for every NPC (docs/COMBAT.md). The
 * rules are aw_combat_rules.c; this file feeds them from the edicts, moves
 * hostile NPCs with the companion's navigation (aw_npcpath.c + AW_ActorStep)
 * and resolves the player's punch at its strike frame.
 *
 * Quake first: a hostile NPC is an edict with a C think on Quake's cadence
 * (0.1 s, from SV_Physics after the companion), like the debug companion.
 * The player's punch stays the QuakeC hand animation (world.qc); this side
 * only watches its state and strikes at the hit key, so the progs CRC does
 * not change. Rolls come from one seeded generator per encounter.
 *
 * Cost per hostile NPC: one slot of about 1.9 KB with its kept spells (no allocation), one think per
 * 0.1 s (at most AW_PATH_TRACES search traces plus the step's own moves),
 * and per frame a pointer test and a frame index. Nothing runs while no NPC
 * is hostile apart from the player's fatigue return.
 *
 * Not saved: a save stores the NPCs' health (as before) but no combat
 * state; after loading, nobody is hostile.
 */
#include "quakedef.h"
#include "aw_npcpath.h"
#include "aw_combat.h"
#include "aw_items.h"
#include "aw_character.h"
#include "aw_levelup.h"
#include "aw_anim.h"
#include "aw_move.h"
#include "aw_hand_models.h"
#include "aw_ambient.h"
#include "aw_effects.h"
#include "aw_cast.h"
#include "aw_animkit.h"

#define SLOTS 4               /* hostile NPCs at a time */
#define SCALE .25f              /* original units -> game units (tools/prepare_quake.py SCALE) */
#define STEP_UP 8.5f
enum {S_CHASE,S_SWING,S_HIT,S_KNOCK,S_DEAD,S_FLEE,S_BLOCK,S_DODGE,S_CAST};
enum {G_IDLE,G_RUN,G_ATTACK,G_HIT,G_KNOCK,G_DEATH,G_BLOCK,G_DODGEL,G_DODGER,G_CAST,G_COUNT};   /* G_CAST: DAGOTH-UR-NO-ANIMATIONS-65 */
#define G_REQUIRED 6            /* the groups a fighters.txt layout must have; block/dodge optional */
/* The dodge (AmiWind extension, docs/COMBAT.md): a quick step aside, 10 game units
 * (40 original) over 0.3 s, a real move through collision. */
#define DODGE_UNITS 10.0f
#define DODGE_SECONDS .3f

typedef struct {
    edict_t *e;
    aw_fighter_t f;
    aw_path_t path;
    short base[G_COUNT];unsigned char count[G_COUNT];float step[G_COUNT];
    float hit_fraction;
    unsigned char state,attack,struck,group,rolled;      /* rolled: no death frames (stand-in) */
    float state_time,next_think,last_think,cooldown,strength,swing_time;
    float decide_at;            /* unreachable player: flee, re-decide at this time */
    signed char dodge_dir;      /* +1 right, -1 left */
    unsigned char has_block,has_dodge;
    float dodged;               /* units stepped of this dodge */
    func_t think;float nextthink;
    edict_t *item[AW_ITEMS_KINDS];  /* carried weapon/shield while fighting (aw_items.c) */
    float run_x;                /* the run group's own speed (layout X, units a second; 0: by time) */
    float step_carry;           /* ACTOR-MECHANICS-USE-STATS-66: the part of a game unit the last step left over */
    float gait;vec3_t gait_at;  /* WALK-CYCLES-57: seconds into the run group by distance, and where it was counted */
    signed char sound_group,sound_frame;   /* the group frame whose sound keys last played (CREATURE-ANIM-SOUND-54) */
    short target_num;           /* COMBAT-ACTOR-VS-ACTOR-62: the actor it fights (edict number), 0 = the player */
    /* NPC-NO-SPELLCASTING-65: the spell it chose (ASPT row, -1 its weapon), that spell's ranges, chance and range (map
     * units), when it decides again, and the cast under way: its release (seconds into S_CAST), end and the look */
    short spell;unsigned char spell_ranges,cast_left;
    float spell_chance,spell_range,spell_at,cast_release,cast_end;
    int cast_look;
    /* its spells read once when the fight starts (the cheaper version: no disk read in the think after that): the
     * castable spells (ASPT row, cost, always-succeeds, their effects in sp_e/sp_m from FIRST, N of them) */
    unsigned char spells_cached,nspells,neffects;
    struct {short row;unsigned short cost;unsigned char first,n,always;} sp[32];
    aw_spell_effect_t sp_e[48];
    struct {uint32_t flags;float base_cost;int school;} sp_m[48];
    /* ACTOR-RANGED-COMBAT-MISSING-66: a bow, crossbow or thrown weapon on its sheet: the ammunition read once from its
     * live record (AITM row, rounds left, its chop), and 1 while the swing under way is a shot */
    unsigned char shooting,ammo_known,ammo_chop[2];
    short ammo_item;int ammo_left;
} slot_t;

aw_combat_settings_t aw_combat_settings;
aw_combat_ai_t aw_combat_ai;
static float were_level,were_flee_mod;     /* iWereWolfLevelToAttack, iWereWolfFleeMod (0: not in the image) */
static int settings_ok,ai_ok,settings_tried;   /* settings_tried: read this load already (COMBAT-SETTINGS-REREAD-63) */
static char sound_path[AW_SND_COUNT][32];
static const char *const sound_key[AW_SND_COUNT]={"health","miss","punch","light","medium","heavy","swish","critical","fall","punch2"};
enum {SND_HEALTH=AW_SND_HEALTH,SND_MISS=AW_SND_MISS,SND_PUNCH=AW_SND_PUNCH,SND_LIGHT=AW_SND_LIGHT,SND_MEDIUM=AW_SND_MEDIUM,
      SND_HEAVY=AW_SND_HEAVY,SND_SWISH=AW_SND_SWISH,SND_CRITICAL=AW_SND_CRITICAL,SND_FALL=AW_SND_FALL};

static slot_t slots[SLOTS];
static aw_fighter_t you;        /* the player's sheet while anything is hostile */
static int you_valid,battle,dead_music;
static aw_combat_rng_t rng;
static unsigned long seed_used,encounters;
static float punch_started=-1;static int punch_struck;
/* PLAYER-ANIM-GROUPS-NOT-PLAYED-66: the last damaging blow on the player (-1 none) and its random hit group; when the
 * player went down (knocked, the state AW_CombatPlayerReaction last saw); cleared with the fight (AW_CombatClear) */
static float you_hit_at=-1,you_down_at;static int you_hit_roll,you_down_seen;
/* The quick retry of a lost fight (an AmiWind extension, aw_view.c, aw_death_retry): where
 * everyone stood and how they were when the fight began. */
static struct {
    int valid;vec3_t origin,angles;aw_fighter_t you;
    struct {edict_t *e;vec3_t origin,angles;aw_fighter_t f;float health;} npc[SLOTS];
} retry;
static edict_t *enemy;static float enemy_until;
static aw_combat_stats_t totals;
static struct {unsigned long thinks,swings,traces;double seconds,max;} cost;

static cvar_t combat_on={"aw_combat","1"};
static cvar_t readout={"aw_combat_readout","1"};
static cvar_t music={"aw_combat_music","1"};
static cvar_t seed_cvar={"aw_combat_seed","0"};
static cvar_t punch_hit={"aw_combat_punch_hit","0.71"};
static cvar_t think_interval={"aw_combat_think","0.1"};
/* ACTOR-MECHANICS-USE-STATS-66: the chase, flee and flight speed. 0 (default) = each fighter's own speed from its Speed
 * and Athletics (AW_MoveActorSpeed: OpenMW 0.51 npc.cpp / creature.cpp getMaxSpeed; an NPC runs, a creature moves at its
 * walk, a flyer by the fly speeds, a swimmer by the swim speed); above 0 = that fixed speed in game units a second for
 * everyone (the earlier rule, 200, kept selectable). */
static cvar_t chase_speed={"aw_combat_speed","0"};
static aw_move_settings_t move_rules;static int move_rules_set;   /* the original's movement settings (as aw_ambient.c) */
static float fighter_speed(const slot_t *s) {
    int medium=AW_MEDIUM_GROUND;
    if(chase_speed.value>0)return chase_speed.value;
    if(!move_rules_set){AW_MoveSettingsDefault(&move_rules);move_rules_set=1;}
    if(AW_AmbientFlags(s->e)&AW_AMBIENT_FLYER)medium=AW_MEDIUM_AIR;
    else if(AW_AmbientFlags(s->e)&AW_AMBIENT_SWIMMER)medium=AW_MEDIUM_WATER;
    /* row 23: its own load (s->f.encumbrance, set when it engages, fighter_load) */
    return AW_MoveActorLoaded(&move_rules,s->f.creature!=0,medium,
                              AW_MoveActorSpeed(&move_rules,s->f.creature!=0,medium,(float)s->f.attributes[AW_SPD],
                                                (float)s->f.skills[8],1),s->f.encumbrance)*SCALE;
}
/* ACTOR-MECHANICS-USE-STATS-66 row 23 (OpenMW 0.51 mwworld/class.cpp getNormalizedEncumbrance, actor.cpp
 * getEncumbrance): a fighter's own load when it engages: what its live record carries (AW_ActorCarriedWeight) plus
 * Burden less Feather on it, over its Strength x fEncumbranceStrMult; its swings, blocks and speed read it. Once per
 * fight (about one read per inventory entry); an actor without a live record keeps 0, as before. */
static void fighter_load(slot_t *s) {
    aw_actor_t *a=AW_MwscriptActorOf(s->e,NULL);float load,cap;
    if(!a)return;
    if(!move_rules_set){AW_MoveSettingsDefault(&move_rules);move_rules_set=1;}
    load=AW_ActorCarriedWeight(a);
    if(aw_combat_effect_magnitude)load+=aw_combat_effect_magnitude(s->e,AW_EFFECT_BURDEN)-aw_combat_effect_magnitude(s->e,AW_EFFECT_FEATHER);
    cap=AW_ActorStat(a,AWA_ATTRIBUTE+0)*move_rules.fEncumbranceStrMult;
    s->f.encumbrance=load<=0?0:cap>0?load/cap:1.000001f;
}
/* one think's step in whole game units; the fraction carries to the next think so a slow actor keeps its speed */
static int fighter_step(slot_t *s,float dt) {
    float x=fighter_speed(s)*dt+s->step_carry;int n=(int)x;
    s->step_carry=x-(float)n;
    return n;
}
/* Options (Controls > Combat style / Dice rolls; saved with the game config):
 * aw_combat_miss 1 = AmiWind style (AmiWind extension: a failed roll shows the
 * defender's dodge or block), 0 = Original Morrowind (the swish/miss sound);
 * aw_combat_dice 1 = the original rolls, 0 = no dice (AmiWind extension);
 * aw_combat_best_attack 1 = "always use best attack", 0 = by movement. Options > Prefs "Always use best attack"
 * (aw_menu.c, the original's Preferences tab); ON by default, an AmiWind default (the original's is off), by decision of
 * the maintainer, 7 November 2026 (BEST-ATTACK-OPTION-62); a saved configuration from before it is switched on once
 * (AW_CombatDefaultsMigrate). */
static cvar_t miss_cvar={"aw_combat_miss","1",true};
static cvar_t dice_cvar={"aw_combat_dice","1",true};
static cvar_t best_cvar={"aw_combat_best_attack","1",true};
static char resist_text[128];        /* sMagicTargetResistsWeapons (combat/settings.txt; RESIST-NORMAL-WEAPONS-61) */
static short normal_resistance(edict_t *t,int test);
static void hit_effects(edict_t *e,aw_fighter_t *f);
static unsigned long god_blows;      /* blows god mode turned away (GODMODE-COMBAT-DAMAGE-61), shown by dbg combat */
/* Blocking (Controls > Blocking; docs/COMBAT.md "Blocking"): aw_combat_block 0 = Original Morrowind
 * (automatic: a shield blocks by skill, no button; UESP Block, OpenMW has no block input), the default
 * by decision of the maintainer, 7 November 2026 (COMBAT-BLOCK-DEFAULT-62); 1 = hold to block (AmiWind
 * extension, an option: the player blocks only while the block button, the right mouse button, is held;
 * each blow is still decided by the original formula and settings). NPCs always block the original way. */
static cvar_t block_cvar={"aw_combat_block","0",true};
/* Flee by the Flee rating (OpenMW aicombataction.cpp makeFleeDecision; docs/COMBAT.md "Combat playground"):
 * 0 (default) = a fighter flees only when it cannot reach the player (the earlier rule); 1 = also when its flee
 * rating beats its best action, and a fleeing fighter runs again whenever the player comes within reach. The
 * combat playground's aggro and group modes switch it on for their session.
 * The swing's sounds as OpenMW plays them (AW_CombatSwingSounds, docs/COMBAT.md "Sounds"): 0 = the earlier
 * sounds (one per outcome), 1 (default since v0.0.58, COMBAT-SOUNDS-RULE-OFF-58) = every swing its swing sound, the armour hit sound of the piece struck, the miss sound
 * for the player's misses only, the two punch sounds. The combat playground's modes switch it on for their session.
 * Both switches are AW_CombatRule's (dbg combat flee|sounds on/off), not console variables. */
/* flee on since v0.0.66 (ACTOR-MECHANICS-USE-STATS-66 row 16: the original's rule, as OpenMW plays it; was off for an
 * A/B), sounds on, contact on, spells on (shipped features default on) */
static int rules[AW_RULE_COUNT]={1,1,1,1};
#define spells_on rules[AW_RULE_SPELLS]
#define flee_on rules[AW_RULE_FLEE]
#define sounds_on rules[AW_RULE_SOUNDS]
#define contact_on rules[AW_RULE_CONTACT]
int AW_CombatRule(int rule,int on) {
    int was;
    if(rule<0 || rule>=AW_RULE_COUNT)return 0;
    was=rules[rule];if(on>=0)rules[rule]=on!=0;
    return was;
}
static unsigned long sound_state=0x9e3779b9UL;     /* the sound picks: not the fight's generator (a seed replays a fight) */
static int guard_key;                /* +aw_alt held outside pick mode */
static float block_shown_until;      /* the body's block clip after a blocked blow */
static float knock_seconds=2.667f,block_seconds=1.333f,block_hit=.25f;   /* settings.txt "anim" lines (base_anim clips) */
/* The player's dodge slide, knockdown view and swing hold. */
static struct {
    float dodge_until,dodge_dir[2],down_since,rise_start,view_base;int view_saved;
    float swing_start,held_until;float move_fwd,move_side;int held;
} pv;

extern unsigned long aw_sv_move_calls;
void (*aw_combat_result)(int won);   /* aw_arena.c: an encounter ended */
/* Combat voices (the animation kit's barks: taunts, pain, flee, death lines): one
 * call per event from this shared layer; NULL = silent. Events: aw_combat.h. */
void (*aw_combat_voice)(edict_t *e,int event);
static void voice(edict_t *e,int event) {if(aw_combat_voice && e)aw_combat_voice(e,event);}
static int watching;                 /* the attack button was pressed: follow the punch */

/* ---- data files ---- */
static int read_line(FILE *f,char *line,int size) {
    if(!fgets(line,size,f))return 0;
    line[strcspn(line,"\r\n")]=0;return 1;
}
int AW_CombatSettingsLoad(void) {
    FILE *f=NULL;char line[128],name[64],path[64];float value;int i,n=0,ai=0;
    if(settings_ok)return 1;
    /* COMBAT-SETTINGS-REREAD-63: an incomplete file was re-read (and its warning printed) on every actor spawn, 16 file
     * opens in one frame after an arrival; it is read once per load (AW_CombatSceneSpawn clears the mark) */
    if(settings_tried)return 0;
    settings_tried=1;
    memset(&aw_combat_settings,0,sizeof(aw_combat_settings));memset(sound_path,0,sizeof(sound_path));
    memset(&aw_combat_ai,0,sizeof(aw_combat_ai));ai_ok=0;were_level=were_flee_mod=0;
    if(COM_FOpenFile("combat/settings.txt",&f)<0 || !f)return 0;
    if(!read_line(f,line,sizeof(line)) || strcmp(line,"AWCS1")){fclose(f);return 0;}
    while(read_line(f,line,sizeof(line))){
        /* "ai NAME VALUE": the aggro and flee ratings' settings (tools/prepare_combat.py AI_SETTINGS) */
        if(Q_sscanf(line,"ai %63s %f",name,&value)==2){if(AW_CombatAiSet(&aw_combat_ai,name,value))ai++;continue;}
        /* "werewolf NAME VALUE" (ACTOR-MECHANICS-USE-STATS-66 row 16; from the expansions' masters, optional) */
        if(Q_sscanf(line,"werewolf %63s %f",name,&value)==2){
            if(!Q_strcasecmp(name,"iWereWolfLevelToAttack"))were_level=value;
            else if(!Q_strcasecmp(name,"iWereWolfFleeMod"))were_flee_mod=value;
            continue;
        }
        {float a=0,b=0;
         if(Q_sscanf(line,"anim %63s %f %f",name,&a,&b)>=2){
            if(!strcmp(name,"knockdown") && a>0 && a<10)knock_seconds=a;
            if(!strcmp(name,"block") && a>0 && a<10){block_seconds=a;if(b>=0 && b<1)block_hit=b;}
            continue;
         }}
        /* "text sMagicTargetResistsWeapons TEXT": the game's own words for a weapon with no effect (RESIST-NORMAL-WEAPONS-61) */
        if(!strncmp(line,"text sMagicTargetResistsWeapons ",32)){
            strncpy(resist_text,line+32,sizeof(resist_text)-1);resist_text[sizeof(resist_text)-1]=0;continue;
        }
        if(Q_sscanf(line,"sound %63s %63s",name,path)==2){
            for(i=0;i<AW_SND_COUNT;i++)if(!strcmp(name,sound_key[i]) && strlen(path)<sizeof(sound_path[i]) && !strstr(path,".."))strcpy(sound_path[i],path);
            continue;
        }
        if(Q_sscanf(line,"%63s %f",name,&value)==2 && AW_CombatSettingSet(&aw_combat_settings,name,value))n++;
    }
    fclose(f);
    ai_ok=ai==AW_COMBAT_AI_COUNT;
    settings_ok=n==AW_COMBAT_SETTING_COUNT;
    if(!settings_ok)Con_Printf("Combat settings incomplete (%ld of %ld); rebuild the image.\n",(long)n,(long)AW_COMBAT_SETTING_COUNT);
    return settings_ok;
}
/* One row of combat/actors.txt (tools/prepare_combat.py write_actors). */
static int parse_actor(char *line,aw_fighter_t *o) {
    char *field[12],*s=line;int i,v[27],n,fields=10;float a,b,c,d;
    for(i=0;i<12;i++){
        field[i]=s;if(i>=10 && !s)break;
        s=s?strchr(s,'\t'):NULL;
        if(i<9){if(!s)return 0;*s++=0;}
        else if(i==9){if(s){*s++=0;fields=11;}else break;}
        else if(i==10){if(s){*s++=0;fields=12;}else break;}
    }
    memset(o,0,sizeof(*o));
    if(strlen(field[0])>=sizeof(o->id) || strlen(field[1])>=sizeof(o->name))return 0;
    strcpy(o->id,field[0]);strcpy(o->name,field[1]);o->level=(short)atoi(field[2]);
    if(Q_sscanf(field[3],"%d %d %d %d %d %d %d %d",v,v+1,v+2,v+3,v+4,v+5,v+6,v+7)!=8)return 0;
    for(i=0;i<8;i++)o->attributes[i]=(unsigned char)(v[i]<0?0:v[i]>255?255:v[i]);
    for(n=0,s=field[4];n<27 && *s;n++){v[n]=(int)strtol(s,&s,10);while(*s==' ')s++;}
    if(n!=27)return 0;
    for(i=0;i<27;i++)o->skills[i]=(unsigned char)(v[i]<0?0:v[i]>255?255:v[i]);
    if(Q_sscanf(field[5],"%f %f %f",&a,&b,&c)!=3)return 0;
    o->health=o->health_max=a;o->magicka=b;o->fatigue=o->fatigue_max=c;
    if(Q_sscanf(field[6],"%d %d",v,v+1)!=2)return 0;
    o->fight=(unsigned char)v[0];o->flee=(unsigned char)v[1];
    if(Q_sscanf(field[7],"%d %d %d %d %d %d %d %d %f %f %f",v,v+1,v+2,v+3,v+4,v+5,v+6,v+7,&a,&b,&c)!=11)return 0;
    o->weapon=(unsigned char)v[0];o->weapon_skill=(unsigned char)(v[1]<27?v[1]:AW_SK_H2H);
    for(i=0;i<6;i++)o->damage[i/2][i%2]=(unsigned char)v[2+i];
    o->reach=a;o->speed=b>0?b:1;o->weight=c;
    if(Q_sscanf(field[8],"%f %d",&d,v)!=2)return 0;
    o->armor=d;o->shield=(unsigned char)(v[0]!=0);o->aware=1;
    /* field 11 (optional): weapon condition, shield condition, shield armour class */
    if(fields==11 && Q_sscanf(field[10],"%f %f %d",&a,&b,v)==3){
        o->weapon_health=o->weapon_health_max=a;o->shield_health=o->shield_health_max=b;
        o->shield_class=(unsigned char)(v[0]>=0 && v[0]<=2?v[0]:0);
    }
    /* field 12 (optional): the armour class of each slot a blow can land on, AW_CombatArmorHitSlot order, one
     * letter each: - none, l light, m medium, h heavy (its hit sound) */
    if(fields==12 && strlen(field[11])==AW_ARMOR_HIT_SLOTS)
        for(i=0;i<AW_ARMOR_HIT_SLOTS;i++)
            o->hit_classes|=(unsigned int)(field[11][i]=='l'?1:field[11][i]=='m'?2:field[11][i]=='h'?3:0)<<(2*i);
    return o->health_max>0;
}
static void lower(const char *in,char *out,int size) {
    int i;for(i=0;i<size-1 && in[i];i++)out[i]=(in[i]>='A' && in[i]<='Z')?in[i]+32:in[i];out[i]=0;
}
/* A creature record has no row in combat/actors.txt (NPC records only): its sheet comes from the actor record
 * (docs/ACTOR_STATE.md, one record for every NPC and creature; aw_mwhost.c opens it), COMBAT-DAEDROTH-NO-HIT-51: a
 * creature without a sheet took no blow. */
extern int AW_MwscriptActors(void);
static int creature_sheet(const char *id,aw_fighter_t *out) {
    int row;aw_actor_base_t b;
    if(!id[0] || !AW_MwscriptActors())return 0;
    row=AW_ActorFind(id);
    if(row==AW_ACTOR_NONE || !AW_ActorBase(row,&b))return 0;
    if(!AW_CombatCreatureSheet(&b,id,out))return 0;
    /* NPC-CREATURE-COMBAT-STYLE-STATS-66: a creature with the weapon flag fights with the weapon its row equips */
    {int item;aw_item_t it;(void)AW_ActorWeaponEnchant(row,&item);
     if(item>=0 && AW_ActorItem(item,&it))(void)AW_CombatCreatureWeapon(out,&it);}
    return 1;
}
/* ESSENTIAL-DEATH-60: an actor whose record carries the essential flag (AWR_ESSENTIAL) dies, in a fight or by dbg kill:
 * the game's own message (GMST sKilledEssential, view/settings.txt by tools/prepare_player_view.py; OpenMW 0.51 shows the
 * same GMST in a message box when an essential actor dies). The player goes on; loading a save is the player's choice.
 * Nothing is shown when the image has no such text (a console line says so). */
extern void AW_MsgBoxShow(const char *text,const char *const *buttons,int count);
int AW_CombatEssentialRecord(const char *id,int *essential) {
    int row;aw_actor_base_t b;char want[32];
    *essential=0;
    if(!id || !id[0] || !AW_MwscriptActors())return 0;
    lower(id,want,sizeof(want));
    row=AW_ActorFind(want);
    if(row==AW_ACTOR_NONE || row<0 || !AW_ActorBase(row,&b))return 0;
    *essential=(b.flags&AWR_ESSENTIAL)?1:0;return 1;
}
/* ESSENTIAL-DEATH-MESSAGE-66: the box once per death of REF (0 unknown): a fight's death and the record's own death
 * (aw_actorstate.c AW_ActorKill, a script's SetHealth 0, a spell or a fall: AW_CombatEssentialKilled) both report it */
static void essential_message(unsigned long ref,const char *name) {
    static unsigned long last_ref;static double last_time=-100;
    FILE *f=NULL;char line[320],*s,*bs;const char *key="sKilledEssential ";size_t n=strlen(key);
    if(ref && ref==last_ref && realtime-last_time<10)return;
    last_ref=ref;last_time=realtime;
    Con_Printf("Essential: %s has died.\n",name?name:"?");
    if(COM_FOpenFile("view/settings.txt",&f)>=0 && f){
        while(fgets(line,sizeof(line),f)){
            line[strcspn(line,"\r\n")]=0;
            if(strncmp(line,key,n) || !line[n])continue;
            fclose(f);s=line+n;
            while((bs=strstr(s,"\\n"))!=NULL){bs[0]=' ';memmove(bs+1,bs+2,strlen(bs+2)+1);}   /* the file writes a newline as \n */
            AW_MsgBoxShow(s,NULL,0);return;
        }
        fclose(f);
    }
    Con_Printf("Essential: this image has no death message (view/settings.txt sKilledEssential).\n");
}
static void essential_death(edict_t *e) {
    eval_t *v,*r;int essential;
    if(!(v=GetEdictFieldValue(e,"aw_source_id")) || !v->string || !AW_CombatEssentialRecord(pr_strings+v->string,&essential) || !essential)return;
    r=GetEdictFieldValue(e,"aw_ref");
    essential_message(r && r->_float>=1 && r->_float<=16777215.0f?(unsigned long)r->_float:0,e->v.netname?pr_strings+e->v.netname:NULL);
}
void AW_CombatEssentialKilled(unsigned long ref,const char *name) {essential_message(ref,name);}
/* ACTOR-STATS-ALL-61: the stats of a fighter's sheet from the being's one stat block (the host, aw_mwhost.c: the loaded
 * areas' block of record ID; NULL or none found: the sheet's own numbers, the previous method). Weapon, armour and the
 * attacks stay the sheet's. */
void (*aw_combat_sheet_stats)(const char *id,aw_fighter_t *out);
static int actor_load(const char *id,aw_fighter_t *out);
int AW_CombatActorLoad(const char *id,aw_fighter_t *out) {
    int ok=actor_load(id,out);
    if(ok && aw_combat_sheet_stats)aw_combat_sheet_stats(id,out);
    return ok;
}
static int actor_load(const char *id,aw_fighter_t *out) {
    FILE *f=NULL;char line[512],want[32],*tab;long data,offset[27];int total,i,b,cmp;
    lower(id,want,sizeof(want));
    if(!want[0] || COM_FOpenFile("combat/actors.txt",&f)<0 || !f)return creature_sheet(want,out);
    if(!read_line(f,line,sizeof(line)) || Q_sscanf(line,"AWCA1 %d",&total)!=1 || total<1)goto bad;
    if(!read_line(f,line,sizeof(line)) || line[0]!='I' || strlen(line)!=1+27*9)goto bad;
    for(i=0;i<27;i++)offset[i]=strtol(line+2+i*9,NULL,10);
    b=want[0]>='a' && want[0]<='z'?want[0]-'a':26;
    /* Rows are sorted: seek to the wanted letter and read only its rows. */
    data=ftell(f);
    if(data<0 || fseek(f,data+offset[b],SEEK_SET))goto bad;
    while(read_line(f,line,sizeof(line))){
        tab=strchr(line,'\t');if(!tab)break;*tab=0;
        cmp=strcmp(line,want);*tab='\t';
        if(cmp>0)break;
        if(!cmp){fclose(f);return parse_actor(line,out);}
    }
bad:
    fclose(f);return creature_sheet(want,out);
}
/* The player: the character sheet and the live health. Hand to hand, no
 * armour worn (all slots unarmoured), no shield. */
/* A loadout of arena/player.txt ("AWAP2", "default NAME", rows "loadout:NAME ...");
 * loadout NULL or "" = the default. chosen (24 bytes) gets the name. */
int AW_CombatLoadout(const char *loadout,aw_fighter_t *out,char *chosen) {
    FILE *f=NULL;char line[512],want[40],def[24];int ok=0;
    if(COM_FOpenFile("arena/player.txt",&f)<0 || !f)return 0;
    if(!read_line(f,line,sizeof(line)) || strcmp(line,"AWAP2") || !read_line(f,line,sizeof(line)) ||
       Q_sscanf(line,"default %23s",def)!=1){fclose(f);return 0;}
    if(!loadout || !*loadout)loadout=def;
    if(strlen(loadout)>=24){fclose(f);return 0;}
    strcpy(want,"loadout:");strcat(want,loadout);
    while(!ok && read_line(f,line,sizeof(line))){
        char *tab=strchr(line,'\t');if(!tab)continue;
        if((int)(tab-line)==(int)strlen(want) && !strncmp(line,want,strlen(want)))ok=parse_actor(line,out);
    }
    fclose(f);
    if(ok && chosen)strcpy(chosen,loadout);
    return ok;
}
/* The arena's set fighter for the player (aw_arena.c), NULL = the character. */
const aw_fighter_t *aw_combat_player_preset;
/* Optional inventory adapter: source-derived equipment on the current sheet. */
void (*aw_combat_equipment)(aw_fighter_t *sheet);
void (*aw_combat_equipment_store)(const aw_fighter_t *sheet);
void AW_CombatPlayerSheet(aw_fighter_t *o) {
    edict_t *p=sv.active && svs.clients?svs.clients[0].edict:NULL;int i;
    if(aw_combat_player_preset){
        *o=*aw_combat_player_preset;strcpy(o->name,"You");o->aware=1;o->knocked=o->dead=0;
        /* PLAYER-HEALTH-OVER-MAX-63 (v0.0.63-dev5 release check: 920/93 after dbg maxstats in the arena): the arena
         * gives the character the set fighter's maxima at the start (aw_arena.c); later changes of the sheet (dbg
         * maxstats, a level) raise the character's, so a higher maximum of the character is taken, and the current
         * values are never above the maxima */
        if(aw_character.valid && aw_character.maximum[0]>o->health_max)o->health_max=aw_character.maximum[0];
        if(aw_character.valid && aw_character.maximum[2]>o->fatigue_max)o->fatigue_max=aw_character.maximum[2];
        o->health=p?p->v.health:o->health_max;
        if(o->health>o->health_max)o->health=o->health_max;
        o->fatigue=aw_character.valid?aw_character.current[2]:o->fatigue_max;
        if(o->fatigue>o->fatigue_max)o->fatigue=o->fatigue_max;
        if(aw_combat_equipment)aw_combat_equipment(o);
        return;
    }
    memset(o,0,sizeof(*o));strcpy(o->id,"player");strcpy(o->name,"You");o->aware=1;
    /* HIT-CHANCE-CHECK-62: the modified attributes (base + fortify - damage), as OpenMW's getModified in every combat
     * formula; the base alone left a Fortify Agility or Luck out of the hit chance */
    for(i=0;i<8;i++){int v=aw_character.valid?aw_character.attributes[i]+aw_character.modifiers[i]-aw_character.damage[i]:50;
                     o->attributes[i]=(unsigned char)(v<0?0:v>255?255:v);}
    for(i=0;i<27;i++){int v=aw_character.valid?aw_character.skills[i]:30;o->skills[i]=(unsigned char)(v<0?0:v>255?255:v);}
    o->level=(short)(aw_character.valid?aw_character.level:1);
    o->health_max=aw_character.valid && aw_character.maximum[0]>0?aw_character.maximum[0]:100;
    o->health=p?p->v.health:o->health_max;
    if(o->health>o->health_max)o->health=o->health_max;   /* PLAYER-HEALTH-OVER-MAX-63: never above the maximum */
    o->fatigue_max=aw_character.valid && aw_character.maximum[2]>0?aw_character.maximum[2]:
        (float)(o->attributes[AW_STR]+o->attributes[AW_WIL]+o->attributes[AW_AGI]+o->attributes[AW_END]);
    o->fatigue=aw_character.valid?aw_character.current[2]:o->fatigue_max;
    o->weapon_skill=AW_SK_H2H;
    o->armor=settings_ok?AW_CombatUnarmoredRating(&aw_combat_settings,o):0;
    if(aw_combat_equipment)aw_combat_equipment(o);
}
/* HAND-TO-HAND-NO-HIT-64: the fight's sheet of the player is taken when the fight starts and kept until it ends; the
 * character's attributes, skills, level and maxima are read into it again every frame, so a change during the fight (dbg
 * maxstats, a level, a potion or spell on the sheet) counts at the next blow, as OpenMW reads the live stats at each hit.
 * The fight's own state (health, fatigue, knocked down, the worn equipment) stays. The arena's set fighter keeps its
 * own numbers (only higher maxima are taken, as AW_CombatPlayerSheet does). */
static void you_refresh(aw_fighter_t *o) {
    int i;
    if(!aw_character.valid || aw_combat_player_preset)return;
    for(i=0;i<8;i++){int v=aw_character.attributes[i]+aw_character.modifiers[i]-aw_character.damage[i];
                     o->attributes[i]=(unsigned char)(v<0?0:v>255?255:v);}
    for(i=0;i<27;i++){int v=aw_character.skills[i];o->skills[i]=(unsigned char)(v<0?0:v>255?255:v);}
    o->level=(short)aw_character.level;
    if(aw_character.maximum[0]>0)o->health_max=aw_character.maximum[0];
    if(aw_character.maximum[2]>0)o->fatigue_max=aw_character.maximum[2];
    {float cap=0,load=AW_PlayerEncumbrance(&cap);o->encumbrance=load<=0?0:cap>0?load/cap:1.000001f;}   /* getNormalizedEncumbrance */
}
/* INVENTORY-NO-ARMOR-RATING-61: the player's armour rating as the inventory window shows it under the picture (OpenMW
 * 0.51 mwgui/inventorywindow.cpp updateArmorRating: the whole number of mwclass/npc.cpp getArmorRating): the worn pieces
 * by slot share, each by its class's skill and its condition, an empty slot by the unarmored skill (the combat sheet,
 * aw_inventory.c inv_combat), plus the magnitude of an active Shield effect. -1 without the game's settings. */
float AW_CombatPlayerArmorRating(void) {
    aw_fighter_t f;edict_t *p=sv.active && svs.clients?svs.clients[0].edict:NULL;float shield;
    if(!settings_ok && !AW_CombatSettingsLoad())return -1;
    AW_CombatPlayerSheet(&f);
    shield=p && aw_combat_effect_magnitude?aw_combat_effect_magnitude(p,AW_EFFECT_SHIELD):0;
    return f.armor+(shield>0?shield:0);
}
/* Inventory transactions store condition before changing slots. Refresh only
 * equipment fields: equipping must never heal or clear an active knockdown. */
void AW_CombatEquipmentStore(void) {
    if(you_valid && aw_combat_equipment_store)aw_combat_equipment_store(&you);
}
void AW_CombatEquipmentChanged(void) {
    aw_fighter_t changed;
    if(!you_valid || !aw_combat_equipment)return;
    changed=you;aw_combat_equipment(&changed);
    you.weapon=changed.weapon;you.weapon_skill=changed.weapon_skill;
    memcpy(you.damage,changed.damage,sizeof(you.damage));
    you.reach=changed.reach;you.speed=changed.speed;you.weight=changed.weight;
    you.armor=changed.armor;you.shield=changed.shield;you.shield_class=changed.shield_class;you.hit_classes=changed.hit_classes;
    you.weapon_health=changed.weapon_health;you.weapon_health_max=changed.weapon_health_max;
    you.shield_health=changed.shield_health;you.shield_health_max=changed.shield_health_max;
}
static void you_store(edict_t *p) {
    AW_CombatEquipmentStore();
    if(p)p->v.health=you.health;
    if(aw_character.valid){aw_character.current[0]=you.health;aw_character.current[2]=you.fatigue;}
}

/* ---- helpers ---- */
static edict_t *player(void) {
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict)return NULL;
    return svs.clients[0].edict;
}
/* beside each other: one blow's sounds (swish, the armour struck, Health Damage, critical: at most 4 of the 8
 * dynamic channels) all play (AUDIO-LOCAL-SOUND-CUTS-58) */
static void sound(int which) {if(which>=0 && which<AW_SND_COUNT && sound_path[which][0])S_LocalSoundBeside(sound_path[which]);}
const char *AW_CombatSoundPath(int key) {
    if(!settings_ok)AW_CombatSettingsLoad();
    return key>=0 && key<AW_SND_COUNT?sound_path[key]:"";
}
int AW_CombatSoundPlay(int key) {if(!*AW_CombatSoundPath(key))return 0;sound(key);return 1;}
/* With the sounds rule on (AW_RULE_SOUNDS): the swing's sounds by AW_CombatSwingSounds (out NULL: a swing that reached nobody). 0 when
 * the switch is off (the caller plays the earlier sounds). */
static int swing_sounds(const aw_swing_t *out,const aw_fighter_t *victim,int by_player) {
    int list[4],n,i;unsigned long x=sound_state;
    if(!sounds_on)return 0;
    x^=(x<<13)&0xffffffffUL;x^=x>>17;x^=(x<<5)&0xffffffffUL;sound_state=x;
    n=AW_CombatSwingSounds(out,victim,by_player,x>>8,list);
    for(i=0;i<n;i++)sound(list[i]);
    return 1;
}
static void shield_sound(const aw_fighter_t *f) {sound(SND_LIGHT+(f->shield_class<=2?f->shield_class:0));}
static float field(edict_t *e,char *name,float fallback) {
    eval_t *v=GetEdictFieldValue(e,name);return v?v->_float:fallback;
}
static float gap_to(edict_t *a,edict_t *b,float *dz) {
    float dx=b->v.origin[0]-a->v.origin[0],dy=b->v.origin[1]-a->v.origin[1];
    float r=(a->v.maxs[0]>8?a->v.maxs[0]:7.32f)+(b->v.maxs[0]>8?b->v.maxs[0]:7.32f);
    *dz=(b->v.origin[2]+b->v.mins[2])-(a->v.origin[2]+a->v.mins[2]);
    return (float)AW_PathLength((int)dx,(int)dy)-r;
}
/* signedAngleRadians(attacker - victim, victim facing, up), degrees. NIF
 * characters face local +Y: facing yaw = angles[1] + 90. */
static float bearing(edict_t *victim,edict_t *attacker,float facing_offset) {
    float yaw=(victim->v.angles[1]+facing_offset)*(float)M_PI/180;
    float fx=Q_CosRad(yaw),fy=Q_SinRad(yaw),ax=attacker->v.origin[0]-victim->v.origin[0],ay=attacker->v.origin[1]-victim->v.origin[1];
    return (float)(Q_atan2(ax*fy-ay*fx,ax*fx+ay*fy)*180/M_PI);
}
/* combat.cpp getAggroDistance for a walking actor: the whole 3D distance of the positions, in original units */
static float original_distance(edict_t *a,edict_t *b) {
    vec3_t d;VectorSubtract(a->v.origin,b->v.origin,d);
    return (float)Length(d)/SCALE;
}
static slot_t *slot_of(edict_t *e) {int i;for(i=0;i<SLOTS;i++)if(slots[i].e==e)return &slots[i];return NULL;}
static void print_swing(const char *who,const char *whom,int attack,const aw_swing_t *s) {
    static const char *outcome[]={"miss","BLOCKED","fatigue","HIT"},*type[]={"chop","slash","thrust"};
    if(!readout.value)return;
    if(s->roll<0 && s->roll!=-2){Con_Printf("Combat: %s swings at %s (already down)\n",who,whom);return;}
    if(s->roll==-2)Con_Printf("Combat: %s -> %s: no dice %s%s",who,whom,outcome[s->outcome],s->critical?" CRITICAL":"");
    else Con_Printf("Combat: %s -> %s: chance %ld roll %ld %s%s",who,whom,(long)s->chance,(long)s->roll,outcome[s->outcome],
        s->critical?" CRITICAL":"");
    if(s->outcome==AW_HIT_MISS && miss_cvar.value)Con_Printf(" (%s)",s->miss_style==2?"blocks":"dodges");
    if(s->weapon_broke)Con_Printf(" WEAPON BROKE");
    if(s->shield_broke)Con_Printf(" SHIELD BROKE");
    if(s->blocked_roll>=0)Con_Printf(" (block %ld/%ld)",(long)s->blocked_roll,(long)s->block_chance);
    if(s->outcome>=AW_HIT_FATIGUE)Con_Printf(" %ld.%ld %s",(long)s->damage,(long)(s->damage*10)%10,s->outcome==AW_HIT_HEALTH?"health":"fatigue");
    Con_Printf("%s (%s, swing %ld%%)\n",s->outcome>=AW_HIT_FATIGUE && s->knockdown?" KNOCKDOWN":"",
        type[attack>=0 && attack<3?attack:0],(long)(s->strength*100));
}
static void flash(float damage) {
    cl.cshifts[CSHIFT_DAMAGE].destcolor[0]=190;cl.cshifts[CSHIFT_DAMAGE].destcolor[1]=20;cl.cshifts[CSHIFT_DAMAGE].destcolor[2]=20;
    cl.cshifts[CSHIFT_DAMAGE].percent+=(int)(3*damage+10);
    if(cl.cshifts[CSHIFT_DAMAGE].percent>150)cl.cshifts[CSHIFT_DAMAGE].percent=150;
}

/* ---- frames ---- */
static void layout_default(slot_t *s) {
    int i=(int)s->e->v.modelindex,n=i>0 && i<MAX_MODELS && sv.models[i]?sv.models[i]->numframes:1,g;
    /* Animation kit models (<model>.anm, aw_anim.c): their own groups; a group they lack plays idle. */
    static const unsigned char kit[G_COUNT]={AW_ANIM_IDLE,AW_ANIM_RUN,AW_ANIM_ATTACK,AW_ANIM_HIT,AW_ANIM_KNOCK,AW_ANIM_DEATH,
        AW_ANIM_BLOCK,AW_ANIM_DODGEL,AW_ANIM_DODGER,AW_ANIM_CAST};
    const aw_anim_t *a=AW_AnimOf(s->e);
    if(a->from_layout){
        for(g=0;g<G_COUNT;g++){
            const aw_anim_group_t *k=&a->g[kit[g]];
            if(!k->present && kit[g]==AW_ANIM_RUN)k=&a->g[AW_ANIM_WALK];     /* run falls back to walk (OpenMW) */
            if(!k->present && (kit[g]==AW_ANIM_DODGEL || kit[g]==AW_ANIM_DODGER))k=&a->g[a->g[AW_ANIM_WALK].present?AW_ANIM_WALK:AW_ANIM_RUN];
            if(!k->present)k=&a->g[AW_ANIM_IDLE];
            s->base[g]=k->base;s->count[g]=k->count;s->step[g]=k->step;
            if(g==G_RUN)s->run_x=k->x;
        }
        s->hit_fraction=a->g[AW_ANIM_ATTACK].present && a->g[AW_ANIM_ATTACK].x>.05f && a->g[AW_ANIM_ATTACK].x<.95f?a->g[AW_ANIM_ATTACK].x:.5f;
        s->rolled=!a->g[AW_ANIM_DEATH].present;
        s->has_block=a->g[AW_ANIM_BLOCK].present;s->has_dodge=a->g[AW_ANIM_DODGEL].present && a->g[AW_ANIM_DODGER].present;
        return;
    }
    for(g=0;g<G_COUNT;g++){s->base[g]=0;s->count[g]=(unsigned char)(n>=8?8:1);s->step[g]=.15f;}
    if(n==21){s->base[G_RUN]=13;s->count[G_RUN]=8;s->step[G_RUN]=.1f;}   /* town actor layout: walk 13..20 */
    s->base[G_DODGEL]=s->base[G_DODGER]=s->base[G_RUN];s->count[G_DODGEL]=s->count[G_DODGER]=s->count[G_RUN];
    s->step[G_DODGEL]=s->step[G_DODGER]=s->step[G_RUN];s->has_block=s->has_dodge=0;
    s->hit_fraction=.5f;s->rolled=1;
}
/* "idle:0:4:0.6667 run:4:6:0.1556 attack:10:8:0.1500:0.667 ..." (fighters.txt) */
static int layout_parse(slot_t *s,const char *text) {
    static const char *names[G_COUNT]={"idle","run","attack","hit","knock","death","block","dodgel","dodger","cast"};
    char word[64];int g,base,count,got=0,n;float step,hit;const char *p=text;
    int frames=s->e->v.modelindex>0 && sv.models[(int)s->e->v.modelindex]?sv.models[(int)s->e->v.modelindex]->numframes:0;
    while(*p){
        while(*p==' ')p++;
        for(n=0;*p && *p!=' ' && n<63;)word[n++]=*p++;
        word[n]=0;
        if(!n)break;
        for(g=0;g<G_COUNT;g++){
            int len=strlen(names[g]);
            if(strncmp(word,names[g],len) || word[len]!=':')continue;
            hit=.5f;
            if(Q_sscanf(word+len+1,"%d:%d:%f:%f",&base,&count,&step,&hit)<3)return 0;
            if(base<0 || count<1 || base+count>frames || !(step>0 && step<5))return 0;
            s->base[g]=(short)base;s->count[g]=(unsigned char)count;s->step[g]=step;
            if(g==G_ATTACK)s->hit_fraction=hit>.05f && hit<.95f?hit:.5f;
            got|=1<<g;
        }
    }
    if((got&((1<<G_REQUIRED)-1))!=(1<<G_REQUIRED)-1)return 0;
    s->has_block=(got>>G_BLOCK)&1;s->has_dodge=((got>>G_DODGEL)&1) && ((got>>G_DODGER)&1);
    if(!s->has_block){s->base[G_BLOCK]=s->base[G_IDLE];s->count[G_BLOCK]=1;s->step[G_BLOCK]=block_seconds;}
    if(!s->has_dodge)for(g=G_DODGEL;g<=G_DODGER;g++){s->base[g]=s->base[G_RUN];s->count[g]=s->count[G_RUN];s->step[g]=s->step[G_RUN];}
    if(!((got>>G_CAST)&1)){s->base[G_CAST]=s->base[G_IDLE];s->count[G_CAST]=s->count[G_IDLE];s->step[G_CAST]=s->step[G_IDLE];}
    s->rolled=0;return 1;
}
static float duration(slot_t *s,int g);
/* The sound keys of the frames the fighter's group has passed since the last call (the animation's own keys: a
 * creature's roar in its attack, scream in its hit, steps in its run; aw_anim.c AW_AnimSounds plays them, a
 * creature's from its voice-table row, CREATURE-ANIM-SOUND-54). Only for a fighter that plays its layout's groups. */
static void group_sounds(slot_t *s,int g,int i) {
    static const int kit[G_COUNT]={AW_ANIM_IDLE,AW_ANIM_RUN,AW_ANIM_ATTACK,AW_ANIM_HIT,AW_ANIM_KNOCK,AW_ANIM_DEATH,
                                   AW_ANIM_BLOCK,AW_ANIM_DODGEL,AW_ANIM_DODGER,AW_ANIM_CAST};
    const aw_anim_t *a=AW_AnimOf(s->e);unsigned long crossed=0;int k,last=s->sound_frame;
    if(i<0 || i>=32)return;
    if(s->sound_group!=g){last=-1;s->sound_group=(signed char)g;}
    else if(i==last)return;
    if(i>last)for(k=last+1;k<=i;k++)crossed|=1UL<<k;
    else{for(k=last+1;k<s->count[g] && k<32;k++)crossed|=1UL<<k;for(k=0;k<=i;k++)crossed|=1UL<<k;}   /* a loop wrapped */
    s->sound_frame=(signed char)i;
    if(a && a->from_layout && a->g[kit[g]].present && a->g[kit[g]].base==s->base[g])
        AW_AnimSounds(s->e,a,kit[g],crossed,AW_AnimMedium(s->e));
}
static void animate(slot_t *s) {
    int g=s->group,i;float t=s->state_time;
    /* A dead resident lies in its standing model: the mover's memory goes back (aw_anim.c). */
    if(s->state==S_DEAD && !s->rolled && t>=duration(s,G_DEATH) && AW_AnimMoving(s->e) && AW_AnimMover(s->e,0)){
        const aw_anim_t *a=AW_AnimOf(s->e);
        if(a->g[AW_ANIM_DEATH].present){s->base[G_DEATH]=a->g[AW_ANIM_DEATH].base;s->count[G_DEATH]=a->g[AW_ANIM_DEATH].count;}
        else{s->base[G_DEATH]=0;s->count[G_DEATH]=1;}
    }
    if(s->state==S_DEAD && s->rolled){s->e->v.frame=s->base[G_IDLE];return;}
    {   /* CREATURE-COMBAT-FRAMES-MISSING-61: the groups were laid out on the model worn at the engage; when another
         * part put a different model on the actor since (a walker's mover taken off), the groups are laid out again
         * on the model it wears now, never a frame past its last */
        int mi=(int)s->e->v.modelindex,n=mi>0 && mi<MAX_MODELS && sv.models[mi]?sv.models[mi]->numframes:0;
        if(n>0 && s->base[g]+s->count[g]>n){
            if(readout.value)Con_Printf("Combat: %s changed model (%d frames): its groups laid out again\n",s->f.name,n);
            layout_default(s);
        }
    }
    if(g==G_RUN && s->run_x>0){
        /* WALK-CYCLES-57: the run's phase by the distance covered over the group's own speed (OpenMW
         * CharacterController: the movement animation's speed scaled to the actor's speed), so the feet do not slide
         * at aw_combat_speed or when a step is cut short; a jump of more than two seconds' run (a teleport) is not counted */
        float dx=s->e->v.origin[0]-s->gait_at[0],dy=s->e->v.origin[1]-s->gait_at[1],d=(float)sqrt(dx*dx+dy*dy);
        float clip=s->count[G_RUN]*s->step[G_RUN];
        if(d<s->run_x*2)s->gait+=d/s->run_x;
        if(clip>0 && s->gait>=clip)s->gait-=clip*(float)(int)(s->gait/clip);
        VectorCopy(s->e->v.origin,s->gait_at);
        t=s->gait;
    }else VectorCopy(s->e->v.origin,s->gait_at);
    i=(int)(t/s->step[g]);
    if(g==G_IDLE || g==G_RUN || g==G_DODGEL || g==G_DODGER)i%=s->count[g];
    else if(i>=s->count[g])i=s->count[g]-1;      /* one-shot groups hold the last frame */
    /* Knocked out: the knockdown clip falls and gets up; hold its lowest (middle) frame until fatigue returns. */
    if(g==G_KNOCK && s->f.knocked==2 && i>s->count[g]/2)i=s->count[g]/2;
    s->e->v.frame=s->base[g]+i;
    group_sounds(s,g,i);
}
static void set_state(slot_t *s,int state,int group) {s->state=(unsigned char)state;s->group=(unsigned char)group;s->state_time=0;}
static float duration(slot_t *s,int g) {return s->count[g]*s->step[g];}

/* ---- traces for aw_npcpath.c (the companion's: player passed through) ---- */
static float player_solid;
static void pass_player(int on) {
    edict_t *p=player();if(!p)return;
    if(on){player_solid=p->v.solid;p->v.solid=SOLID_NOT;}else p->v.solid=player_solid;
}
static int sweep(void *context,int dx,int dy) {
    edict_t *e=context;vec3_t start,end;trace_t tr;
    VectorCopy(e->v.origin,start);start[2]+=STEP_UP;
    VectorCopy(start,end);end[0]+=dx;end[1]+=dy;
    tr=SV_Move(start,e->v.mins,e->v.maxs,end,MOVE_NORMAL,e);
    return !tr.startsolid && !tr.allsolid && tr.fraction==1;
}
static int cell(void *context,int x,int y,int z,int *floor_z) {
    edict_t *e=context;vec3_t start,end;trace_t tr;
    start[0]=end[0]=x;start[1]=end[1]=y;start[2]=z+AW_PATH_STEP;end[2]=z-AW_PATH_STEP;
    tr=SV_Move(start,e->v.mins,e->v.maxs,end,MOVE_NORMAL,e);
    if(tr.startsolid || tr.allsolid || tr.fraction>=1 || tr.plane.normal[2]<AW_WALKABLE_Z)return 0;
    if(floor_z)*floor_z=(int)floor(tr.endpos[2]);
    return 1;
}
static void face_player(edict_t *e,edict_t *p) {
    e->v.angles[1]=AW_PathHeading((int)(p->v.origin[0]-e->v.origin[0]),(int)(p->v.origin[1]-e->v.origin[1]))*360.0f/AW_PATH_FAN-90;
    e->v.angles[0]=e->v.angles[2]=0;
}

/* ---- engagement ---- */
void (*aw_combat_actor_released)(edict_t *e);
void (*aw_combat_actor_died)(edict_t *e);
static void release(slot_t *s) {
    edict_t *alive=s->e && !s->e->free && s->state!=S_DEAD?s->e:NULL;
    AW_ItemsHide(s->item);
    if(s->cast_look)AW_MagicCastLookRelease(s->cast_look,-1);   /* a cast under way ends with the fight */
    if(alive)AW_AnimMover(alive,0);
    if(alive){alive->v.think=s->think;alive->v.nextthink=s->nextthink>0?(float)sv.time+.1f:0;}
    memset(s,0,sizeof(*s));
    if(alive && aw_combat_actor_released)aw_combat_actor_released(alive);
}
int AW_CombatActorState(edict_t *e) {
    slot_t *s=e?slot_of(e):NULL;
    return !s?0:s->f.dead || s->state==S_DEAD?2:1;
}
int AW_CombatActorEnd(edict_t *e) {
    slot_t *s=e?slot_of(e):NULL;
    if(!s)return 0;
    release(s);if(enemy==e)enemy=NULL;
    return 1;
}
int AW_CombatHealthPercent(edict_t *e) {
    slot_t *s=slot_of(e);
    if(!s || !(s->f.health_max>0))return -1;
    return s->f.health<=0?0:(int)(s->f.health*100/s->f.health_max);
}
/* THE "are we in a fight?" check (WAIT-DURING-COMBAT-36): someone fights the player and the player is alive.
 * The battle music plays exactly while it holds (OpenMW music.lua: the battle playlist while an actor has combat
 * targets), and waiting is refused while it holds (aw_wait.c; OpenMW World::canRest Rest_EnemiesAreNearby). The
 * original's rest test is wider (any aggressive actor within 7168 units, docs/WAIT_AND_REST.md); it comes with the
 * wait/rest work. */
int AW_PlayerInCombat(void) {return AW_CombatHostiles()>0 && !you.dead;}
int AW_CombatHostiles(void) {
    int i,n=0;
    /* COMBAT-ACTOR-VS-ACTOR-62: a slot that fights another actor is no hostile of the player (no battle music, no
     * wait refusal, no win) */
    for(i=0;i<SLOTS;i++)if(slots[i].e && !slots[i].e->free && !slots[i].f.dead && !slots[i].target_num)n++;
    return n;
}
/* GAME-RECORDER-FIGHT-SEED-61: while the gameplay recorder records or plays back, the fights draw their seeds from the
 * recording's seed and the recording's own count of fights (recorder_fights), never from this game instance's count
 * (encounters, which differs between the game that recorded and the one that replays) or the clock. At the
 * recording's frame 0 the running generator is set from it too: a fight already on, or begun again by the starting
 * save's load, rolls the same dice in the recording and its replay. 0 = the recorder is off. */
static unsigned long recorder_seed,recorder_fights;
static unsigned long recorder_fight_seed(void) {
    unsigned long s=((recorder_seed^(recorder_fights*2654435761UL))*2246822519UL)&0xffffffUL;
    return s?s:1;
}
void AW_CombatRecorderSeed(unsigned long seed) {
    recorder_seed=seed&0xffffffffUL;recorder_fights=0;
    if(!seed)return;
    seed_used=recorder_fight_seed();AW_CombatSeed(&rng,seed_used);totals.seed=seed_used;
}
static void begin_encounter(void) {
    unsigned long seed=(unsigned long)seed_cvar.value;
    if(recorder_seed){recorder_fights++;seed=recorder_fight_seed();}
    /* 24 bits: exact in the float cvar, so a printed seed replays (aw_combat_seed). */
    if(!seed){seed=(0x41c64e6dUL^((encounters+1)*2654435761UL))&0xffffffUL;if(!seed)seed=1;}
    AW_CombatSeed(&rng,seed);seed_used=seed;encounters++;
    memset(&totals,0,sizeof(totals));totals.seed=seed;totals.started=sv.time;
    memset(&cost,0,sizeof(cost));      /* the thinks per second of dbg combat are this encounter's */
    AW_CombatPlayerSheet(&you);you_valid=1;punch_started=-1;dead_music=0;
    memset(&retry,0,sizeof(retry));
    {edict_t *p=player();
     if(p){retry.valid=1;VectorCopy(p->v.origin,retry.origin);VectorCopy(p->v.v_angle,retry.angles);retry.angles[0]=retry.angles[2]=0;
           retry.you=you;retry.you.health=p->v.health>0?p->v.health:you.health;}}
}
/* Make an NPC hostile to the player. fighter: its sheet; layout: frame
 * groups (fighters.txt) or NULL for the model's own frames. */
/* Set by AW_CombatTestEngage(t,1): the slot is taken only to hold a corpse (a killed actor's saved death applied on
 * a scene load): no encounter starts, no weapon is drawn, no battle cry and no "attacks" line (COMBAT-DEAD-ACTOR-RELOAD-59). */
static int engage_dead;
static int lay_saved;       /* AW_CombatLayCorpse: a saved death laid down again (no essential message) */
int AW_CombatEngage(edict_t *e,const aw_fighter_t *fighter,const char *layout) {
    slot_t *s=slot_of(e);int i;
    if(!combat_on.value || !e || e->free || !fighter || !AW_CombatSettingsLoad())return 0;
    if(!s){
        for(i=0;i<SLOTS && slots[i].e;i++){}
        /* every slot taken: a fallen fighter's slot is reused (a pack of more than SLOTS keeps coming as the first
         * ones die, COMBAT-PACK-SLOTS-57); its death is handed to the actors' change list first, so the corpse stays
         * dead when its cell joins again (aw_actors.c) */
        if(i==SLOTS)for(i=0;i<SLOTS;i++)if(slots[i].e && (slots[i].f.dead || slots[i].state==S_DEAD || slots[i].e->free)){
            if(!slots[i].e->free && aw_combat_actor_died)aw_combat_actor_died(slots[i].e);
            release(&slots[i]);break;
        }
        if(i==SLOTS){Con_Printf("Combat: %ld hostile NPCs already.\n",(long)SLOTS);return 0;}s=&slots[i];}
    if(!engage_dead && !AW_CombatHostiles())begin_encounter();
    AW_ItemsHide(s->item);      /* a re-engaged NPC: its items again from the start */
    memset(s,0,sizeof(*s));s->e=e;s->f=*fighter;s->f.aware=1;
    s->think=e->v.think;s->nextthink=e->v.nextthink;e->v.nextthink=0;    /* its QuakeC idle stops */
    if(!layout){
        /* A resident fights in its full-kit model. Never silently present a
         * declared mover's standing-only poses as run/attack animation. */
        int declared=AW_AnimOf(e)->mover[0]!=0;
        AW_AnimMover(e,1);
        if(declared && !AW_AnimMoving(e))
            Con_Printf("Combat: %s mover unavailable; standing animation fallback\n",s->f.name);
    }
    if(!layout || !layout_parse(s,layout))layout_default(s);
    AW_PathReset(&s->path,(int)floor(e->v.origin[0]),(int)floor(e->v.origin[1]));
    s->next_think=s->last_think=(float)sv.time;s->cooldown=.5f;
    s->spell=-1;s->spell_at=(float)sv.time;   /* the first decision at its first think */
    fighter_load(s);
    set_state(s,S_CHASE,G_IDLE);
    if(retry.valid && retry.npc[s-slots].e!=e){
        retry.npc[s-slots].e=e;VectorCopy(e->v.origin,retry.npc[s-slots].origin);VectorCopy(e->v.angles,retry.npc[s-slots].angles);
        retry.npc[s-slots].f=s->f;retry.npc[s-slots].health=e->v.health;
    }
    if(engage_dead)return 1;    /* a corpse: the caller marks it dead at once */
    AW_ItemsShow(e,s->item);    /* a resident draws its weapon and shield (NPC-WEAPON-MESH-33) */
    if(readout.value)Con_Printf("Combat: %s (level %ld) attacks; seed %lu\n",s->f.name,(long)s->f.level,seed_used);
    voice(e,AW_VOICE_START);
    return 1;
}
static void shots_clear(void);
void AW_CombatClear(void) {
    int i;for(i=0;i<SLOTS;i++)if(slots[i].e)release(&slots[i]);enemy=NULL;you_valid=0;retry.valid=0;
    you_hit_at=-1;you_down_seen=0;shots_clear();
}
int AW_CombatPlayerReaction(float *age,int *roll) {
    if(age)*age=0;
    if(roll)*roll=0;
    if(!you_valid || you.dead){you_down_seen=0;return 0;}
    if(you.knocked!=you_down_seen){you_down_seen=you.knocked;you_down_at=(float)sv.time;}
    if(you.knocked){if(age)*age=(float)sv.time-you_down_at;return you.knocked==2?3:2;}
    if(you_hit_at<0 || sv.time<you_hit_at)return 0;
    if(age)*age=(float)sv.time-you_hit_at;
    if(roll)*roll=you_hit_roll;
    return 1;
}
/* The player died in the current fight and its start is known (aw_view.c offers "Retry fight"). */
int AW_CombatRetryAvailable(void) {return retry.valid && you_valid && you.dead && player()!=NULL;}
/* The death music is combat's (the death in a fight): aw_view.c does not play it again. */
int AW_CombatDeathMusicPlayed(void) {return music.value && you_valid && you.dead;}
/* Retry: everyone back where the fight began, at the health and fatigue they had then; the
 * opponents still hostile. An AmiWind extension (the original offers only the last save). */
int AW_CombatRetry(void) {
    edict_t *p=player();int i;
    if(!p || !AW_CombatRetryAvailable())return 0;
    if(pv.view_saved)p->v.view_ofs[2]=pv.view_base;
    memset(&pv,0,sizeof(pv));
    VectorCopy(retry.origin,p->v.origin);VectorCopy(vec3_origin,p->v.velocity);
    VectorCopy(retry.angles,p->v.angles);VectorCopy(retry.angles,p->v.v_angle);p->v.fixangle=1;
    if(p->v.movetype==MOVETYPE_NONE)p->v.movetype=MOVETYPE_WALK;
    you=retry.you;you.dead=you.knocked=0;you.staggered=0;you_store(p);
    SV_LinkEdict(p,true);
    for(i=0;i<SLOTS;i++){
        slot_t *s=&slots[i];
        if(!s->e || s->e->free || retry.npc[i].e!=s->e)continue;
        s->f=retry.npc[i].f;s->f.aware=1;s->e->v.health=retry.npc[i].health;
        VectorCopy(retry.npc[i].origin,s->e->v.origin);VectorCopy(retry.npc[i].angles,s->e->v.angles);
        if(s->state==S_DEAD)s->e->v.solid=SOLID_SLIDEBOX;
        set_state(s,S_CHASE,G_IDLE);s->cooldown=1;s->struck=0;
        AW_PathReset(&s->path,(int)floor(s->e->v.origin[0]),(int)floor(s->e->v.origin[1]));
        SV_LinkEdict(s->e,false);
    }
    punch_started=-1;dead_music=0;battle=0;enemy=NULL;
    totals.won=0;totals.ended=0;
    if(readout.value)Con_Printf("Combat: the fight restarts (retry, seed %lu)\n",seed_used);
    return 1;
}
const aw_combat_stats_t *AW_CombatStats(void) {return &totals;}
unsigned long AW_CombatSeedUsed(void) {return seed_used;}
const aw_fighter_t *AW_CombatPlayer(void) {return you_valid?&you:NULL;}
const aw_fighter_t *AW_CombatFighter(edict_t *e) {slot_t *s=slot_of(e);return s?&s->f:NULL;}
/* MWSCRIPT-TICK-SHARE-66: the edicts that hold a fight slot now (in slot order), up to MAX; how many */
int AW_CombatFighterEdicts(edict_t **out,int max) {
    int i,n=0;
    for(i=0;i<SLOTS && n<max;i++)if(slots[i].e && !slots[i].e->free)out[n++]=slots[i].e;
    return n;
}
int AW_CombatAttackType(edict_t *e) {slot_t *s=slot_of(e);return s?s->attack:-1;}

/* ---- reactions: the AmiWind style miss (dodge or block), stagger ---- */
/* A side step of the NPC (+1 right, -1 left of its facing): the side with room. */
static int dodge_side(slot_t *s,edict_t *p) {
    float yaw=(s->e->v.angles[1]+90)*(float)M_PI/180;int k,dir;
    for(k=0;k<2;k++){
        dir=k?-1:1;
        if(sweep(s->e,(int)(Q_SinRad(yaw)*DODGE_UNITS*dir),(int)(-Q_CosRad(yaw)*DODGE_UNITS*dir)))return dir;
    }
    (void)p;return 0;
}
/* The block clip starts at its hit key ("shield: block hit"), so the shield is
 * up at the attacker's contact time, not a third of a second after it. */
static void start_block(slot_t *s) {
    set_state(s,S_BLOCK,G_BLOCK);
    s->state_time=(s->has_block?duration(s,G_BLOCK):block_seconds)*block_hit;
}
/* AmiWind style: the roll was already resolved at the attacker's hit key; this
 * only presents it (no reroll, no shield wear, no block effects). Only a fighter
 * in its ordinary chase state reacts: never mid-swing, staggered, down, fleeing
 * or dead (those keep their state; the miss is just the swish). */
static void npc_react_miss(slot_t *s,edict_t *p,const aw_swing_t *out) {
    if(!miss_cvar.value || s->f.dead || s->f.knocked || s->state!=S_CHASE)return;
    if(out->miss_style==2){start_block(s);shield_sound(&s->f);return;}
    s->dodge_dir=(signed char)dodge_side(s,p);s->dodged=0;
    if(s->dodge_dir)set_state(s,S_DODGE,s->dodge_dir>0?G_DODGER:G_DODGEL);
}
/* The player's side (AmiWind style): a slide of the view, or a block kick. */
static void player_react_miss(edict_t *p,const aw_swing_t *out) {
    vec3_t f,r,u;
    if(!miss_cvar.value || you.dead || you.knocked)return;
    if(out->miss_style==2){shield_sound(&you);p->v.punchangle[0]=-4;p->v.punchangle[2]=3;return;}
    if(punch_started>=0 && !punch_struck)return;      /* mid-swing: no slide, the swish only */
    AngleVectors(p->v.v_angle,f,r,u);
    pv.dodge_dir[0]=r[0];pv.dodge_dir[1]=r[1];pv.dodge_until=(float)sv.time+DODGE_SECONDS;
}
/* One frame of the player's dodge slide: a hull-traced move, right, else left. */
static void player_dodge_step(edict_t *p,float dt) {
    vec3_t end;trace_t tr;int k;float step=DODGE_UNITS*dt/DODGE_SECONDS;
    if(sv.time>=pv.dodge_until)return;
    for(k=0;k<2;k++){
        end[0]=p->v.origin[0]+pv.dodge_dir[0]*step;end[1]=p->v.origin[1]+pv.dodge_dir[1]*step;end[2]=p->v.origin[2];
        tr=SV_Move(p->v.origin,p->v.mins,p->v.maxs,end,MOVE_NORMAL,p);
        if(!tr.startsolid && !tr.allsolid && tr.fraction==1){VectorCopy(end,p->v.origin);SV_LinkEdict(p,true);return;}
        pv.dodge_dir[0]=-pv.dodge_dir[0];pv.dodge_dir[1]=-pv.dodge_dir[1];
    }
    pv.dodge_until=0;
}
static void ended(int won) {
    totals.ended=sv.time;totals.won=won;
    if(aw_combat_result)aw_combat_result(won);
}
/* The NPC struck at its hit key: resolve against the player. */
static void npc_strike(slot_t *s,edict_t *p) {
    aw_swing_t out;float dz,gap=gap_to(s->e,p,&dz),reach=AW_CombatReach(&aw_combat_settings,&s->f)*SCALE;int mapped;
    float dzr=reach+((AW_AmbientFlags(s->e)&AW_AMBIENT_FLYER)?64:0);   /* a flyer strikes from above the eyes (the engage check's allowance) */
    you.health=p->v.health;
    if(gap>reach || dz>dzr || dz<-dzr || you.dead){
        s->f.fatigue-=aw_combat_settings.fFatigueAttackBase+(s->f.weapon?s->f.weight*s->strength*aw_combat_settings.fWeaponFatigueMult:0);
        totals.npc_swings++;totals.npc_misses++;swing_sounds(NULL,NULL,0);
        if(readout.value)Con_Printf("Combat: %s swings, out of reach\n",s->f.name);
        return;
    }
    you.staggered=0;
    you.block_off=(unsigned char)(block_cvar.value && !AW_CombatGuarding());
    /* RESIST-NORMAL-WEAPONS-61: the player's own resistance against an NPC's weapon (the NPC sheets carry no weapon
     * flags yet: a weapon in an NPC's hand counts as ordinary) */
    s->f.weapon_normal=(unsigned char)(s->f.weapon!=0);
    you.resist_normal=s->f.weapon_normal?normal_resistance(p,0):0;
    hit_effects(s->e,&s->f);hit_effects(p,&you);                     /* HIT-CHANCE-CHECK-62 */
    /* fBlockStillBonus while not moving forward (combat.cpp: movement mPosition[1] <= 0) */
    {aw_fighter_t before=you;
     AW_CombatSwing(&aw_combat_settings,&s->f,&you,s->attack,s->strength,bearing(p,s->e,0),
        svs.clients[0].cmd.forwardmove<=0,&rng,&out);
     /* GODMODE-COMBAT-DAMAGE-61: dbg god on (Quake's FL_GODMODE): no damage, no knockdown (OpenMW npc.cpp) */
     if((int)p->v.flags&FL_GODMODE){AW_CombatGodVictim(&you,&before,&out);god_blows++;}}
    you.block_off=0;
    totals.npc_swings++;cost.swings++;
    mapped=swing_sounds(&out,&you,0);
    if(out.outcome==AW_HIT_BLOCKED){
        totals.npc_misses++;totals.player_blocks++;if(!mapped)shield_sound(&you);p->v.punchangle[0]=-4;p->v.punchangle[2]=3;
        block_shown_until=(float)sv.time+block_seconds*(1-block_hit);
        AW_LevelupUse(AW_SK_BLOCK,0,1);       /* LEVEL-UP-58: Block_Success (OpenMW combat.cpp blockMeleeAttack) */
    }
    else if(out.outcome==AW_HIT_MISS){totals.npc_misses++;if(!mapped)sound(SND_SWISH);player_react_miss(p,&out);}
    else{
        totals.npc_hits++;
        if(out.outcome==AW_HIT_HEALTH && out.damage<=0){if(!mapped)sound(SND_HEALTH);}   /* god mode: the blow lands, nothing more */
        else if(out.outcome==AW_HIT_HEALTH){totals.taken_health+=out.damage;flash(out.damage);if(!mapped)sound(SND_HEALTH);
            /* LEVEL-UP-58: Armor_HitByOpponent for the piece the blow lands on, Unarmored for an empty slot (OpenMW
             * files/data-mw/scripts/omw/combat/local.lua applyArmor); the slot by the roll the hit sounds used */
            {int c=AW_HIT_CLASS(&you,AW_CombatArmorHitSlot((int)((sound_state>>8)%100)));
             AW_LevelupUse(c==1?AW_SK_LIGHT:c==2?AW_SK_MEDIUM:c==3?AW_SK_HEAVY:AW_SK_UNARMORED,0,1);}
            /* the player says a Hit line too (OpenMW npc.cpp onHit: the player is an NPC there; iVoiceHitOdds; his race and
             * sex's lines from the voice table, aw_glut.c player row; COMBAT-VOICES-SILENT-33) */
            if(!you.dead)voice(p,AW_VOICE_HIT);}
        else{totals.taken_fatigue+=out.damage;if(!mapped)sound(SND_PUNCH);}
    }
    print_swing(s->f.name,"you",s->attack,&out);
    /* the hit recovery: a blow that did damage and did not knock the player down (not in god mode: no damage) */
    if(out.outcome!=AW_HIT_BLOCKED && out.outcome!=AW_HIT_MISS && out.damage>0 && !out.knockdown && !you.knocked){
        you_hit_at=(float)sv.time;you_hit_roll=(int)((sound_state>>4)&0xFF);
    }
    if(out.knockdown && you.knocked==1){
        totals.player_down_until=sv.time+knock_seconds;   /* the knockdown clip (base_anim) */
        if(readout.value)Con_Printf("Combat: you are knocked down\n");
    }
    you_store(p);
    if(you.dead){
        if(readout.value)Con_Printf("Combat: you have been killed by %s\n",s->f.name);
        voice(p,AW_VOICE_DEATH);    /* Hit, always, when death comes (OpenMW Actors::killDeadActors) */
        sound(SND_FALL);ended(0);
    }
    /* WEAPON-STRIKE-ENCHANT-NOT-CAST-61: the NPC's weapon's Cast When Strikes on the player (a hit or a block) */
    else if(aw_combat_strike_enchant && s->f.weapon && out.outcome!=AW_HIT_MISS)aw_combat_strike_enchant(s->e,p);
    /* MWSCRIPT-INVENTORY-HITONME-62: the weapon's id as the player's last hit object (OpenMW Npc::onHit) */
    if(aw_combat_weapon_hit && s->f.weapon && out.outcome!=AW_HIT_MISS)aw_combat_weapon_hit(s->e,p);
}
/* ---- fights between two actors (v0.0.63, COMBAT-ACTOR-VS-ACTOR-62; rules from OpenMW 0.51 mechanicsmanagerimp.cpp
 * startCombat, aicombat.cpp, combat.cpp, written independently; the design note of 9 November 2026) ---- */
/* the slot S fights (its target's slot), NULL when the target is the player, dead, gone or not in a fight */
static slot_t *actor_target(slot_t *s) {
    edict_t *t;slot_t *v;
    if(!s->target_num || s->target_num>=sv.num_edicts)return NULL;
    t=EDICT_NUM(s->target_num);
    if(t->free || t==s->e || !(v=slot_of(t)) || v->f.dead || v->state==S_DEAD)return NULL;
    return v;
}
/* the outcome of a blow on the actor slot V (as the player's strike applies it): the block, the miss reaction, the
 * death (the change list, the essential rule), the knockdown or the hit recovery; 1 when V died */
static int victim_outcome(slot_t *v,edict_t *attacker,const aw_swing_t *out) {
    if(out->outcome==AW_HIT_BLOCKED){if(v->state!=S_KNOCK && !v->f.dead)start_block(v);}
    else if(out->outcome==AW_HIT_MISS){if(miss_cvar.value)npc_react_miss(v,attacker,out);}
    if(v->f.dead){
        set_state(v,S_DEAD,G_DEATH);v->e->v.solid=SOLID_NOT;SV_LinkEdict(v->e,false);
        if(v->rolled){v->e->v.angles[2]=90;v->e->v.origin[2]+=2;}
        if(aw_combat_actor_died)aw_combat_actor_died(v->e);
        essential_death(v->e);
        if(readout.value)Con_Printf("Combat: %s is dead\n",v->f.name);
        voice(v->e,AW_VOICE_DEATH);
        return 1;
    }
    if(v->f.knocked && v->state!=S_KNOCK)set_state(v,S_KNOCK,G_KNOCK);
    else if(out->outcome>=AW_HIT_FATIGUE && !out->no_effect && v->state!=S_KNOCK)set_state(v,S_HIT,G_HIT);
    if(out->outcome>=AW_HIT_FATIGUE && !out->no_effect)voice(v->e,AW_VOICE_HIT);
    return 0;
}
/* the strike of slot S on the actor slot V: the reach test, the swing between their sheets, its outcome; the swing's
 * sounds only within earshot of the player (the layer's sounds are not placed in the world), no crime */
static unsigned long actor_strikes,actor_hits,actor_deaths;
static void npc_strike_actor(slot_t *s,slot_t *v) {
    aw_swing_t out;float dz,gap=gap_to(s->e,v->e,&dz),reach=AW_CombatReach(&aw_combat_settings,&s->f)*SCALE;
    edict_t *p=player();
    if(v->f.dead)return;
    if(gap>reach || dz>reach || dz<-reach){
        s->f.fatigue-=aw_combat_settings.fFatigueAttackBase+(s->f.weapon?s->f.weight*s->strength*aw_combat_settings.fWeaponFatigueMult:0);
        return;
    }
    s->f.weapon_normal=(unsigned char)(s->f.weapon!=0);
    v->f.resist_normal=s->f.weapon_normal?normal_resistance(v->e,0):0;
    hit_effects(s->e,&s->f);hit_effects(v->e,&v->f);
    AW_CombatSwing(&aw_combat_settings,&s->f,&v->f,s->attack,s->strength,bearing(v->e,s->e,90),!v->f.moving,&rng,&out);
    v->f.aware=1;actor_strikes++;
    if(p && original_distance(s->e,p)<1024)swing_sounds(&out,&v->f,0);
    if(out.outcome!=AW_HIT_MISS && out.outcome!=AW_HIT_BLOCKED)actor_hits++;
    if(readout.value)print_swing(s->f.name,v->f.name,s->attack,&out);
    /* the victim fights back (OpenMW onHit: the attacked actor takes the attacker as its target) unless it fights
     * the player */
    if(!v->f.dead && v->target_num && v->target_num!=(short)NUM_FOR_EDICT(s->e) && !actor_target(v))
        v->target_num=(short)NUM_FOR_EDICT(s->e);
    if(victim_outcome(v,s->e,&out))actor_deaths++;
    if(aw_combat_strike_enchant && s->f.weapon && out.outcome!=AW_HIT_MISS)aw_combat_strike_enchant(s->e,v->e);
    if(aw_combat_weapon_hit && s->f.weapon && out.outcome!=AW_HIT_MISS)aw_combat_weapon_hit(s->e,v->e);
}
/* aw_combat.h: E (sheet A) and V (sheet B) fight each other; an actor already fighting the player keeps the player
 * (only the other one takes it as its target). 1 when at least E fights V. */
int AW_CombatEngageAgainst(edict_t *e,const aw_fighter_t *a,edict_t *v,const aw_fighter_t *b) {
    slot_t *se,*sv_;int was_e,was_v;
    if(!e || !v || e==v || e->free || v->free)return 0;
    was_e=slot_of(e)!=NULL;was_v=slot_of(v)!=NULL;
    if(!was_e && !AW_CombatEngage(e,a,NULL))return 0;
    if(!was_v && b && !AW_CombatEngage(v,b,NULL)){if(!was_e)AW_CombatActorEnd(e);return 0;}
    se=slot_of(e);sv_=slot_of(v);
    if(!se || !sv_)return 0;
    if(!was_e || se->target_num)se->target_num=(short)NUM_FOR_EDICT(v);
    if(!was_v)sv_->target_num=(short)NUM_FOR_EDICT(e);
    return 1;
}
/* aw_combat.h: the actor E fights (NULL: the player or no fight; *player 1 when it fights the player) */
/* The frames a fighter's group NAME plays (fighters.txt names: idle run attack hit knock death block dodgel dodger
 * cast): 1 with *base and *count, 0 when E fights in no slot or NAME is none (DAGOTH-UR-NO-ANIMATIONS-65). */
int AW_CombatGroupFrames(edict_t *e,const char *name,int *base,int *count) {
    static const char *names[G_COUNT]={"idle","run","attack","hit","knock","death","block","dodgel","dodger","cast"};
    slot_t *s=e?slot_of(e):NULL;int g;
    if(!s || !name)return 0;
    for(g=0;g<G_COUNT;g++)if(!strcmp(names[g],name)){*base=s->base[g];*count=s->count[g];return 1;}
    return 0;
}
edict_t *AW_CombatTargetOf(edict_t *e,int *fights_player) {
    slot_t *s=e?slot_of(e):NULL,*v;
    if(fights_player)*fights_player=s && !s->f.dead && !s->target_num;
    if(!s || !s->target_num)return NULL;
    v=actor_target(s);
    return v?v->e:NULL;
}
/* Damage from the world, not from a fighter (lava, aw_lava.c, docs/LAVA.md): the
 * player's live health as combat keeps it; a death ends like a death in combat.
 * GODMODE-LAVA-DEATH-62: every world damage (the lava volume, a lava script's HurtStandingActor, a fall, drowning,
 * dbg camera die) comes through here, so god mode (Quake's FL_GODMODE) is checked here once: no health is lost
 * (OpenMW 0.51: god mode keeps the player's health in every damage path). The held-back damage is counted. */
static unsigned long world_god_held;static float world_god_damage;
unsigned long AW_CombatWorldGodHeld(float *damage) {if(damage)*damage=world_god_damage;return world_god_held;}
int AW_CombatHurtPlayer(float damage,const char *cause) {
    edict_t *p=player();float h;
    if(!p || !(damage>0) || p->v.health<=0)return 0;
    if(AW_CombatGodWorldDamage((int)p->v.flags&FL_GODMODE,damage,&world_god_damage)){world_god_held++;return 0;}
    h=p->v.health-damage;if(h<0)h=0;
    p->v.health=h;
    if(you_valid)you.health=h;
    if(aw_character.valid)aw_character.current[0]=h;
    if(h>0)return 0;
    if(you_valid)you.dead=1;
    if(readout.value)Con_Printf("Combat: you have been killed by %s\n",cause?cause:"the world");
    sound(SND_FALL);ended(0);
    return 1;
}
/* The player's swing strength: the share of the wind-up (start to the hit key)
 * during which the attack button stayed down. The original draws back while the
 * button is held and strikes on release; our QuakeC punch plays at once, so the
 * hold until the hit key stands in for the draw-back. */
static float player_strength(void) {
    float wind=AW_HandDuration(AW_HAND_PUNCH,.9f)*punch_hit.value,held=pv.held_until-pv.swing_start;
    if(!(wind>0))return 1;
    held/=wind;return held<0?0:held>1?1:held;
}
/* The player down (knockdown or knockout): controls locked, the view near the
 * floor, rising over the last 40 % of a knockdown or 0.8 s after a knockout. */
/* A paused combat simulation cannot recover knockdown; it must not lock input. */
static int player_locked(void) {return combat_on.value && you_valid && !you.dead && you.knocked;}
/* The movement rules' view of the player (aw_move.c, docs/PLAYER_MOVEMENT.md): knocked down or
 * out, and the player's one fatigue value (the fight sheet while it is live, else the character
 * sheet). The loss follows OpenMW DynamicStat::setCurrent: never below 0 unless already there. */
int AW_CombatPlayerKnocked(void) {return player_locked();}
float AW_CombatPlayerFatigue(float *maximum) {
    if(you_valid){if(maximum)*maximum=you.fatigue_max;return you.fatigue;}
    if(maximum)*maximum=aw_character.valid?aw_character.maximum[2]:0;
    return aw_character.valid?aw_character.current[2]:0;
}
void AW_CombatPlayerFatigueLoss(float loss) {
    if(loss<=0)return;
    if(you_valid){
        you.fatigue=AW_MoveFatigueAfter(you.fatigue,loss);
        if(aw_character.valid)aw_character.current[2]=you.fatigue;
    }else if(aw_character.valid)aw_character.current[2]=AW_MoveFatigueAfter(aw_character.current[2],loss);
}
/* DBG-SUPERSPEED-62 (aw_combat.h) */
void AW_CombatPlayerFatigueFill(void) {
    if(you_valid && you.fatigue<you.fatigue_max)you.fatigue=you.fatigue_max;
    if(aw_character.valid)aw_character.current[2]=you_valid?you.fatigue:aw_character.maximum[2];
}
static void player_down_view(edict_t *p) {
    float low,base,t,f=1;
    if(!pv.view_saved){
        if(!you.knocked)return;
        pv.view_base=p->v.view_ofs[2];pv.view_saved=1;pv.down_since=(float)sv.time;pv.rise_start=0;
    }
    base=pv.view_base;low=p->v.mins[2]+4;
    if(you.knocked==1){
        float total=(float)(totals.player_down_until-pv.down_since);
        t=(float)(sv.time-pv.down_since);
        if(total>0 && t>total*.6f)f=1-(t-total*.6f)/(total*.4f);
    }else if(you.knocked==0){
        if(!pv.rise_start)pv.rise_start=(float)sv.time;
        f=1-(float)(sv.time-pv.rise_start)/.8f;
    }
    if(f<0)f=0;
    t=(float)(sv.time-pv.down_since);
    if(you.knocked && t<.3f)f*=t/.3f;                     /* the fall: 0.3 s */
    p->v.view_ofs[2]=base+(low-base)*f;
    if(!you.knocked && f<=0){p->v.view_ofs[2]=base;pv.view_saved=0;}
}
/* FIRST-PERSON-WEAPONS-56: 1 while the player's right hand holds a bow, a crossbow or a thrown weapon (aw_inventory.c sets
 * it; NULL in fixtures): such a swing is the shot, which waits for ranged combat, never a melee blow with it. */
int (*aw_combat_player_ranged)(void);
/* RESIST-NORMAL-WEAPONS-61 (aw_combat.h): the effect list's magnitudes (v061-magic fills it), the player's weapon test
 * (aw_inventory.c), and a test override:
 * dbg combat resistnormal N gives every target N % until "off" (not saved), so the rule can be seen before a
 * creature's abilities reach the effect list. */
float (*aw_combat_effect_magnitude)(struct edict_s *actor,int effect);
int (*aw_combat_player_weapon_normal)(void);
void (*aw_combat_strike_enchant)(struct edict_s *attacker,struct edict_s *victim);
void (*aw_combat_weapon_hit)(struct edict_s *attacker,struct edict_s *victim);
/* MWSCRIPT-INVENTORY-HITONME-62 (aw_combat.h): the last weapon per victim, a victim's own row or the oldest */
static struct {unsigned long victim,weapon;} last_hit[AW_COMBAT_LAST_HITS];static int last_hit_next;
void AW_CombatLastHitSet(unsigned long victim,unsigned long weapon){
    int k;
    if(!victim)return;
    for(k=0;k<AW_COMBAT_LAST_HITS && last_hit[k].victim!=victim;k++);
    if(k==AW_COMBAT_LAST_HITS){k=last_hit_next;last_hit_next=(last_hit_next+1)%AW_COMBAT_LAST_HITS;}
    last_hit[k].victim=victim;last_hit[k].weapon=weapon;
}
int AW_CombatLastHitTake(unsigned long victim,unsigned long weapon){
    int k;
    if(!victim)return 0;
    for(k=0;k<AW_COMBAT_LAST_HITS;k++)
        if(last_hit[k].victim==victim){
            if(last_hit[k].weapon!=weapon)return 0;
            last_hit[k].victim=last_hit[k].weapon=0;return 1;
        }
    return 0;
}
void AW_CombatLastHitReset(void){memset(last_hit,0,sizeof(last_hit));last_hit_next=0;}
int AW_CombatLastHitCount(void){int k,n=0;for(k=0;k<AW_COMBAT_LAST_HITS;k++)n+=last_hit[k].victim!=0;return n;}
void (*aw_combat_assault)(struct edict_s *victim);
void (*aw_combat_attacked)(struct edict_s *victim);
void (*aw_combat_player_kill)(struct edict_s *victim);
void (*aw_combat_killed)(struct edict_s *victim);
static float resist_test=-1;
const char *AW_CombatResistText(void){return resist_text;}
/* Resist less Weakness to Normal Weapons in percent, clamped to the sheet's short; TEST: the target of the player's
 * swing (the dbg override applies to those only) */
static short normal_resistance(edict_t *t,int test){
    float r=0,w=0;
    if(test && resist_test>=0)return (short)resist_test;
    if(!aw_combat_effect_magnitude)return 0;
    r=aw_combat_effect_magnitude(t,AW_EFFECT_RESIST_NORMAL_WEAPONS)-aw_combat_effect_magnitude(t,AW_EFFECT_WEAKNESS_NORMAL_WEAPONS);
    if(!(r==r))return 0;
    w=r<-10000?-10000:r>10000?10000:r;
    return (short)(w+(w<0?-.5f:.5f));
}
/* HIT-CHANCE-CHECK-62: the effects the hit chance counts, on fighter F of actor E, before a swing (OpenMW 0.51 combat.cpp
 * getHitChance, creaturestats.cpp getEvasion): about ten effect sums a swing, never per frame */
static short effect_rounded(edict_t *e,int effect){
    float m=aw_combat_effect_magnitude(e,effect);
    if(!(m==m))return 0;
    if(m>10000)m=10000;
    if(m<-10000)m=-10000;
    return (short)(m+(m<0?-.5f:.5f));
}
static void hit_effects(edict_t *e,aw_fighter_t *f){
    short sanctuary;
    f->attack_mod=0;f->sanctuary=f->unseen=0;f->paralyzed=0;
    if(!e || !aw_combat_effect_magnitude)return;
    f->paralyzed=aw_combat_effect_magnitude(e,AW_EFFECT_PARALYZE)>0;   /* ACTOR-MECHANICS-USE-STATS-66 row 4 */
    f->attack_mod=(short)(effect_rounded(e,AW_EFFECT_FORTIFY_ATTACK)-effect_rounded(e,AW_EFFECT_BLIND));
    sanctuary=effect_rounded(e,AW_EFFECT_SANCTUARY);
    f->sanctuary=(unsigned char)(sanctuary<0?0:sanctuary>100?100:sanctuary);   /* getEvasion: at most 100 */
    f->unseen=AW_CombatUnseen(&aw_combat_settings,aw_combat_effect_magnitude(e,AW_EFFECT_CHAMELEON),
                              aw_combat_effect_magnitude(e,AW_EFFECT_INVISIBILITY));
}
/* ENEMY-HEALTH-BAR-62 / HIT-CHANCE-CHECK-62: the player's hit contact when the crosshair's ray met nobody (OpenMW 0.51
 * combat.cpp getHitContact: the player strikes the nearest actor in the cone in front, not only the one under the
 * crosshair). Only the fighters (the slots) are asked: a resident not fighting is still struck by aiming at it. A
 * flyer's feet may be higher by the same allowance its own strike has. Line of sight as World::getLOS. */
static edict_t *contact_target(edict_t *p,float reach){
    int i;edict_t *e,*best=NULL;float best_gap=0,gap,dz,eye,to[3],forward[3],right[3],up[3];vec3_t from,at;trace_t tr;
    AngleVectors(p->v.v_angle,forward,right,up);
    eye=p->v.view_ofs[2]>1?p->v.view_ofs[2]-p->v.mins[2]:22-p->v.mins[2];   /* eye over the feet; 22: Quake's eye */
    for(i=0;i<SLOTS;i++){
        e=slots[i].e;
        if(!e || e->free || slots[i].f.dead || slots[i].state==S_DEAD)continue;
        gap=gap_to(p,e,&dz);
        to[0]=e->v.origin[0]-p->v.origin[0];to[1]=e->v.origin[1]-p->v.origin[1];
        to[2]=(e->v.origin[2]+e->v.mins[2])-(p->v.origin[2]+p->v.mins[2]);
        if(!AW_CombatContact(&aw_combat_settings,to,eye,e->v.maxs[2]-e->v.mins[2],gap,dz,reach,
                             (AW_AmbientFlags(e)&AW_AMBIENT_FLYER)?64:0,forward))continue;
        if(best && gap>=best_gap)continue;
        VectorAdd(p->v.origin,p->v.view_ofs,from);
        VectorCopy(e->v.origin,at);at[2]+=(e->v.mins[2]+e->v.maxs[2])*.5f;
        tr=SV_Move(from,vec3_origin,vec3_origin,at,MOVE_NOMONSTERS,p);
        if(tr.fraction<1 || tr.startsolid || tr.allsolid)continue;
        best=e;best_gap=gap;
    }
    if(best)totals.player_contacts++;
    return best;
}
static void resist_notice(void){
    if(readout.value)Con_Printf("Combat: your weapon has no effect on this target (it resists normal weapons)\n");
    if(resist_text[0])AW_MsgBoxShow(resist_text,NULL,0);   /* OpenMW messageBox: the timed box, no buttons */
}
/* The player's punch reached its hit key: what is in reach takes it. */
static void player_strike(edict_t *p) {
    edict_t *t,*killed=NULL;slot_t *s;aw_swing_t out;float reach=AW_CombatReach(&aw_combat_settings,&you)*SCALE,dz;
    char id[32];aw_fighter_t sheet;int attack,mapped;
    you.health=p->v.health;
    if(aw_combat_player_ranged && aw_combat_player_ranged()){
        static double said;
        if(realtime-said>10){said=realtime;Con_Printf("The shot of a bow, crossbow or thrown weapon is not in this engine yet.\n");}
        return;
    }
    t=AW_NPCTargetReach(p,p->v.v_angle,reach+16);       /* from the eye: plus the player's own half width */
    if(!t && contact_on)t=contact_target(p,reach);      /* the original's hit cone over the fighters (AW_RULE_CONTACT) */
    if(t && !(s=slot_of(t))){
        /* Any resident: hitting it starts a fight (OpenMW actorAttacked). */
        eval_t *v=GetEdictFieldValue(t,"aw_source_id");
        if(!v || !v->string || !*(pr_strings+v->string)){t=NULL;}
        else{
            strncpy(id,pr_strings+v->string,sizeof(id)-1);id[sizeof(id)-1]=0;
            /* CRIME-59: the assault (OpenMW actorAttacked: canCommitCrimeAgainst, commitCrime OT_Assault) before its
             * fight starts; a witness or the victim itself may start fighting there (the crime's reactions) */
            if(aw_combat_assault)aw_combat_assault(t);
            if(aw_combat_attacked)aw_combat_attacked(t);   /* GetAttacked (MWSCRIPT-GAPS-63) */
            if((s=slot_of(t))!=NULL)s->f.aware=0;   /* the crime started its fight: the blow is still unaware's */
            else if(!AW_CombatActorLoad(id,&sheet)){if(readout.value)Con_Printf("Combat: no combat sheet for %s\n",id);t=NULL;}
            else{sheet.aware=0;if(!AW_CombatEngage(t,&sheet,NULL))t=NULL;else if((s=slot_of(t)))s->f.aware=0;}
        }
    }
    s=t?slot_of(t):NULL;
    totals.player_swings++;
    if(!s || s->f.dead || gap_to(p,t,&dz)>reach){
        if(!((int)p->v.flags&FL_GODMODE))you.fatigue-=aw_combat_settings.fFatigueAttackBase;   /* god mode: attacks are free */
        totals.player_misses++;you_store(p);swing_sounds(NULL,NULL,1);
        if(s && !s->f.dead){enemy=t;enemy_until=(float)sv.time+aw_combat_settings.fNPCHealthBarTime;}
        return;
    }
    enemy=t;enemy_until=(float)sv.time+aw_combat_settings.fNPCHealthBarTime;   /* HUD::setEnemy: on every attempt in reach */
    /* The attack type: by the movement at the swing's start, or the best attack
     * (character.cpp); the strength: how long the attack button was held. */
    attack=best_cvar.value?AW_CombatBestAttackPlayer(&you):AW_CombatMovementAttack(pv.move_fwd,pv.move_side);
    s->f.staggered=s->state==S_HIT;
    /* RESIST-NORMAL-WEAPONS-61: the target's resistance to ordinary weapons now (its active effects, abilities
     * included) and whether the player's weapon is ordinary; asked only for an ordinary weapon */
    you.weapon_normal=(unsigned char)(you.weapon && (!aw_combat_player_weapon_normal || aw_combat_player_weapon_normal()));
    s->f.resist_normal=you.weapon_normal?normal_resistance(t,1):0;   /* percent */
    hit_effects(p,&you);hit_effects(t,&s->f);                        /* HIT-CHANCE-CHECK-62 */
    {aw_fighter_t before=you;
     AW_CombatSwing(&aw_combat_settings,&you,&s->f,attack,player_strength(),bearing(t,p,90),!s->f.moving,&rng,&out);
     /* GODMODE-COMBAT-DAMAGE-61: no fatigue, no weapon wear in god mode (OpenMW combat.cpp) */
     if((int)p->v.flags&FL_GODMODE)AW_CombatGodAttacker(&you,&before,&out);}
    s->f.aware=1;cost.swings++;
    if(out.no_effect)resist_notice();
    mapped=swing_sounds(&out,&s->f,1);
    if(out.outcome==AW_HIT_BLOCKED){
        totals.player_misses++;totals.npc_blocks++;if(!mapped)shield_sound(&s->f);
        if(s->state!=S_KNOCK && !s->f.dead)start_block(s);
    }else if(out.outcome==AW_HIT_MISS){
        totals.player_misses++;
        if(miss_cvar.value){if(!mapped)sound(SND_SWISH);npc_react_miss(s,p,&out);}  /* AmiWind style */
        else if(!mapped)sound(SND_MISS);                                       /* original: the miss sound */
    }
    else if(out.no_effect){
        /* the blow lands and does nothing: no hit sound, no skill use, no hit recovery (damage 0) */
        totals.player_hits++;
        if(!mapped)sound(SND_MISS);
    }
    else{
        totals.player_hits++;
        if(out.outcome==AW_HIT_HEALTH)totals.dealt_health+=out.damage;else totals.dealt_fatigue+=out.damage;
        /* LEVEL-UP-58: Weapon_SuccessfulHit for the weapon's skill, Hand-to-hand for fists (OpenMW combat local.lua) */
        AW_LevelupUse(you.weapon?you.weapon_skill:AW_SK_H2H,0,1);
        if(!mapped)sound(out.critical?SND_CRITICAL:out.outcome==AW_HIT_HEALTH?SND_HEALTH:SND_PUNCH);
    }
    print_swing("You",s->f.name,attack,&out);
    you_store(p);
    if(s->f.dead){
        set_state(s,S_DEAD,G_DEATH);s->e->v.solid=SOLID_NOT;SV_LinkEdict(s->e,false);sound(SND_FALL);
        if(s->rolled){s->e->v.angles[2]=90;s->e->v.origin[2]+=2;}           /* stand-in: lie down */
        /* the death onto the change list at once (CORPSE-LOOT-60): a room captures its actors only every half
         * minute, so a body killed just before the player left came back alive and its search was lost */
        if(aw_combat_actor_died)aw_combat_actor_died(s->e);
        essential_death(s->e);
        if(readout.value)Con_Printf("Combat: %s is dead\n",s->f.name);
        voice(s->e,AW_VOICE_DEATH);
        killed=s->e;   /* CRIME-59: the murder, when it is one, after this strike (its witnesses may take slots) */
        if(!AW_CombatHostiles())ended(1);
    }else if(s->f.knocked && s->state!=S_KNOCK){set_state(s,S_KNOCK,G_KNOCK);sound(SND_FALL);}
    else if(out.outcome>=AW_HIT_FATIGUE && !out.no_effect && s->state!=S_KNOCK)set_state(s,S_HIT,G_HIT);   /* hit recovery: every damaging hit */
    if(!s->f.dead && out.outcome>=AW_HIT_FATIGUE && !out.no_effect)voice(s->e,AW_VOICE_HIT);
    /* WEAPON-STRIKE-ENCHANT-NOT-CAST-61: a weapon's Cast When Strikes on a blow that hit or was blocked, the killing
     * blow too (OpenMW npc.cpp hit: the enchantment is cast before the blow's damage; its charge is spent, its effects
     * find a corpse and do nothing) */
    if(aw_combat_strike_enchant && you.weapon && out.outcome!=AW_HIT_MISS)aw_combat_strike_enchant(p,t);
    /* MWSCRIPT-INVENTORY-HITONME-62: the weapon's id as the victim's last hit object (OpenMW Creature/Npc::onHit,
     * successful blows only, the killing one too; HitOnMe reads it) */
    if(aw_combat_weapon_hit && you.weapon && out.outcome!=AW_HIT_MISS)aw_combat_weapon_hit(p,t);
    if(killed && aw_combat_killed)aw_combat_killed(killed);   /* CRIME-59: OpenMW actorKilled */
    if(killed && aw_combat_player_kill)aw_combat_player_kill(killed);   /* GetWerewolfKills (MWSCRIPT-GAPS-63) */
}
/* The player's swing now (0 chop, 1 slash, 2 thrust): the same choice player_strike makes, by the movement at the
 * swing's start or the best attack; the third-person body plays its keys (aw_view.c, WEAPONS-57). */
int AW_CombatPlayerAttackType(void) {
    return best_cvar.value?AW_CombatBestAttackPlayer(&you):AW_CombatMovementAttack(pv.move_fwd,pv.move_side);
}
/* The punch (aw_hand_models.c AW_HandsTick state 3): strike once at the
 * hit key, aw_combat_punch_hit of the punch duration (the original
 * HandToHand chop: hit key at 0.67 s of a 0.93 s chop). */
static void watch_punch(edict_t *p) {
    float state=field(p,"aw_hand_state",0),started=field(p,"aw_hand_started",-1),length;
    watching=state==3 || p->v.button0;
    if(state!=3){punch_started=-1;return;}
    length=AW_HandDuration(AW_HAND_PUNCH,.9f);
    if(started!=punch_started){
        usercmd_t *c=&svs.clients[0].cmd;
        punch_started=started;punch_struck=0;
        /* movement at the swing's start, -1..1 (forward 400 and side 350 = full) */
        pv.move_fwd=c->forwardmove/400.0f;pv.move_side=c->sidemove/350.0f;
        pv.swing_start=started;pv.held=1;pv.held_until=started;
    }
    if(punch_struck)return;
    if(pv.held){if(p->v.button0)pv.held_until=(float)sv.time;else pv.held=0;}
    if(sv.time<started+length*punch_hit.value)return;
    punch_struck=1;player_strike(p);
}

/* ---- NPC-NO-SPELLCASTING-65: the fighter's spells (aw_cast.h AW_SpellAi*, OpenMW aicombataction.cpp) ---- */
#define SPELL_DECIDE 1.0f           /* seconds between two choices of the next action (OpenMW: when an action ends) */
#define SPELL_LIST 32               /* the spells of one fighter weighed */
#define CAST_FALLBACK .5f           /* the release of a fighter without a spellcast group (seconds) */
#define CAST_TAIL .4f               /* the group's rest after the release, before the next action */
typedef struct {aw_actor_t *self;uint32_t enemy_ref;} spell_ctx_t;
static float ai_has(void *ctx,int who,int effect) {
    spell_ctx_t *c=(spell_ctx_t *)ctx;
    return AW_EffectsMagnitude(who?c->enemy_ref:c->self->reference,effect,AW_EFFECT_NO_ARG);
}
static float ai_resist(void *ctx,int effect) {
    spell_ctx_t *c=(spell_ctx_t *)ctx;int resist=-1,weakness=-1,shield=-1;float r=0;
    if(AW_CastResistEffects(effect,&resist,&weakness,&shield)){
        if(resist>=0)r+=AW_EffectsMagnitude(c->enemy_ref,resist,AW_EFFECT_NO_ARG);
        if(weakness>=0)r-=AW_EffectsMagnitude(c->enemy_ref,weakness,AW_EFFECT_NO_ARG);
    }
    return r;
}
static int ai_active(void *ctx,int who,int spell) {
    spell_ctx_t *c=(spell_ctx_t *)ctx;aw_effect_info_t fx[32];int i,n=AW_EffectsList(who?c->enemy_ref:c->self->reference,fx,32);
    for(i=0;i<n;i++)if(fx[i].source==spell)return 1;
    return 0;
}
/* numEffectsToDispel (OpenMW spellpriority.cpp): WHO's active effects lasting over 3 s more, harmful (NEGATIVE) or
 * helpful, of EFFECT, or with EFFECT -1 those of spells (a spell row as the source; the constant entries of
 * abilities, items and scripts never end, so they are left out by the time) */
static int ai_dispel(void *ctx,int who,int effect,int negative) {
    spell_ctx_t *c=(spell_ctx_t *)ctx;aw_effect_info_t fx[32];int i,k=0,n=AW_EffectsList(who?c->enemy_ref:c->self->reference,fx,32);
    for(i=0;i<n;i++){
        if(effect>=0?fx[i].effect!=effect:(fx[i].source<0 || fx[i].source>=AW_EFFECT_SOURCE_ITEM))continue;
        if(!(fx[i].left>3))continue;
        if((AW_EffectHarmful(fx[i].effect)!=0)==(negative!=0))k++;
    }
    return k;
}
static unsigned long spell_ratings;
/* The fighter's castable spells, read from the actor table once per fight (at its first choice): the list, each
 * spell's row, cost and flags, its effects and their MGEF values (about 1 + 3n reads for n spells, then none). A spell
 * whose effects no longer fit the slot's effect store is left out. Powers and abilities are never cast here. */
static void cache_spells(slot_t *s,aw_actor_t *a) {
    int known[SPELL_LIST],n,i,k,type,mcost,ne;char name[32];aw_spell_effect_t e[AW_MADE_EFFECTS];aw_mgef_t m;
    s->spells_cached=1;s->nspells=s->neffects=0;
    n=AW_ActorSpells(a,known,SPELL_LIST);totals.npc_spell_reads++;
    for(i=0;i<n && s->nspells<(int)(sizeof(s->sp)/sizeof(*s->sp));i++){
        totals.npc_spell_reads++;
        if(!AW_ActorSpellInfo(known[i],&type,name,sizeof(name),&mcost) || type!=AW_SPELL_TYPE_SPELL)continue;
        totals.npc_spell_reads++;
        if((ne=AW_ActorSpellEffects(known[i],e,AW_MADE_EFFECTS))<=0)continue;
        if(s->neffects+ne>(int)(sizeof(s->sp_e)/sizeof(*s->sp_e)))continue;
        s->sp[s->nspells].row=(short)known[i];s->sp[s->nspells].cost=(unsigned short)mcost;
        totals.npc_spell_reads++;
        s->sp[s->nspells].always=(AW_ActorSpellFlags(known[i])&AW_SPELL_ALWAYS)!=0;
        s->sp[s->nspells].first=s->neffects;s->sp[s->nspells].n=(unsigned char)ne;
        for(k=0;k<ne;k++){
            totals.npc_spell_reads++;
            if(!AW_ActorMagicEffect(e[k].effect,&m))memset(&m,0,sizeof(m));
            if(AW_EffectHarmful(e[k].effect))m.flags|=AW_MGEF_HARMFUL;   /* the hardcoded flag the data lacks */
            s->sp_e[s->neffects]=e[k];
            s->sp_m[s->neffects].flags=m.flags;s->sp_m[s->neffects].base_cost=m.base_cost;s->sp_m[s->neffects].school=m.school;
            s->neffects++;
        }
        s->nspells++;
    }
}
/* the cached effects of spell I of S as the rules take them (the MGEF name is not used by the rules) */
static int cached_effects(const slot_t *s,int i,aw_spell_effect_t *e,aw_mgef_t *m) {
    int k,ne=s->sp[i].n;
    for(k=0;k<ne;k++){
        e[k]=s->sp_e[s->sp[i].first+k];memset(&m[k],0,sizeof(m[k]));
        m[k].flags=s->sp_m[s->sp[i].first+k].flags;m[k].base_cost=s->sp_m[s->sp[i].first+k].base_cost;
        m[k].school=s->sp_m[s->sp[i].first+k].school;
    }
    return ne;
}
static int cached_index(const slot_t *s,int row) {int i;for(i=0;i<s->nspells;i++)if(s->sp[i].row==row)return i;return -1;}
/* The next action of S against the player P: the best spell when it rates above the weapon (OpenMW prepareNextAction:
 * hand to hand and a creature's own attacks rate 0, so any useful spell wins there); S->spell -1 = the weapon. */
static void choose_spell(slot_t *s,edict_t *p) {
    aw_actor_t *a=AW_MwscriptActorOf(s->e,NULL);aw_spell_ai_t c;spell_ctx_t ctx;
    int n,i,best=-1;float best_rating,cost_mult=AW_DialwinEffectCostMult();
    s->spell=-1;
    if(!a || !p)return;
    if(!s->spells_cached)cache_spells(s,a);
    n=s->nspells;
    if(n<=0)return;
    if(!(cost_mult>0))cost_mult=.5f;   /* the masters' fEffectCostMult */
    memset(&c,0,sizeof(c));ctx.self=a;ctx.enemy_ref=AW_ACTOR_PLAYER_REF;
    c.npc=!s->f.creature;c.beast=0;   /* the beast races' helm and boots rule: the race is not on the sheet yet */
    c.health=s->f.health;c.health_max=s->f.health_max;c.fatigue=s->f.fatigue;c.fatigue_max=s->f.fatigue_max;
    for(i=0;i<27;i++)c.skills[i]=AW_ActorStat(a,AWA_SKILL+i);
    c.underwater=AW_AmbientInWater(s->e->v.origin);
    c.enemy=1;c.enemy_npc=1;c.enemy_down=you.knocked!=0;c.enemy_underwater=AW_AmbientInWater(p->v.origin);
    c.enemy_ready=AW_CastReady()?2:field(p,"aw_hand_goal",0)!=0?1:0;
    c.enemy_armor=you.armor>0;c.enemy_weapon=you.weapon!=0;
    for(i=0;i<8;i++)c.enemy_attributes[i]=you.attributes[i];
    for(i=0;i<27;i++)c.enemy_skills[i]=you.skills[i];
    c.enemy_magicka=you.magicka;
    c.has=ai_has;c.resist=ai_resist;c.active=ai_active;c.dispel=ai_dispel;c.ctx=&ctx;
    /* Restore and Absorb Magicka: the need (getRestoreMagickaPriority) from the kept spells' costs */
    c.magicka=AW_ActorStat(a,AWA_MAGICKA);c.magicka_max=a->dyn_base[1];
    for(i=0;i<n;i++)if((float)s->sp[i].cost>c.magicka && (float)s->sp[i].cost<c.magicka_max){c.magicka_need=2;break;}
    /* Burden on the player by the player's load (AW_PlayerEncumbrance); Feather on itself by the Burden and Feather on
     * it (a character's carried weight is not summed in a fight: 0); no fighter carries arrows here (the bound bow) */
    if(!s->target_num){c.enemy_inventory=1;c.enemy_encumbrance=AW_PlayerEncumbrance(&c.enemy_capacity);}
    c.inventory=c.npc;
    c.encumbrance=ai_has(&ctx,0,AW_EFFECT_BURDEN)-ai_has(&ctx,0,AW_EFFECT_FEATHER);if(c.encumbrance<0)c.encumbrance=0;
    c.capacity=AW_ActorStat(a,AWA_ATTRIBUTE+0)*5;   /* Strength x fEncumbranceStrMult (5 in the masters) */
    c.ammo=0;
    /* the masters' values (Morrowind.esm): fAIMagicSpellMult 3, fAIRangeMagicSpellMult 5, fCombatInvisoMult 0.2 */
    c.spell_mult=3;c.range_spell_mult=5;c.effect_cost_mult=cost_mult;
    c.inviso_mult=aw_combat_settings.fCombatInvisoMult>0?aw_combat_settings.fCombatInvisoMult:.2f;
    /* the weapon's rating (rateWeapon): an NPC's melee weapon; hand to hand and a creature's attacks rate 0 */
    best_rating=0;
    if(s->f.weapon && s->f.creature!=1){
        float strength=aw_combat_settings.fDamageStrengthBase+aw_combat_settings.fDamageStrengthMult*s->f.attributes[AW_STR]*.1f;
        float condition=s->f.weapon_health_max>0?s->f.weapon_health/s->f.weapon_health_max:1;
        best_rating=AW_SpellAiRateWeapon(s->f.damage,strength,condition,(float)AW_CombatHitChance(&aw_combat_settings,&s->f,&you),
                                         s->f.speed>0?s->f.speed:1,s->f.skills[s->f.weapon_skill<27?s->f.weapon_skill:AW_SK_H2H],
                                         aw_combat_ai.fAIMeleeWeaponMult>0?aw_combat_ai.fAIMeleeWeaponMult:2);
    }
    for(i=0;i<n;i++){
        aw_spell_effect_t e[AW_MADE_EFFECTS];aw_mgef_t m[AW_MADE_EFFECTS];int type=AW_SPELL_TYPE_SPELL,mcost=s->sp[i].cost,school,ne,row=s->sp[i].row;
        float chance,base,r;
        ne=cached_effects(s,i,e,m);
        base=AW_CastBaseChance(e,m,ne,c.skills,AW_ActorStat(a,AWA_ATTRIBUTE+2),AW_ActorStat(a,AWA_ATTRIBUTE+7),mcost,cost_mult,&school);
        chance=AW_CastChance(base,type,1,s->sp[i].always,
                             AW_EffectsMagnitude(a->reference,AW_EFFECT_SILENCE,AW_EFFECT_NO_ARG),
                             AW_EffectsMagnitude(a->reference,AW_EFFECT_SOUND,AW_EFFECT_NO_ARG),
                             AW_CastFatigueTerm(1.25f,.5f,s->f.fatigue,s->f.fatigue_max),AW_ActorStat(a,AWA_MAGICKA),mcost,1);
        r=AW_SpellAiRateSpell(&c,row,type,e,m,ne,chance);
        spell_ratings++;
        if(r>best_rating){
            best_rating=r;best=row;s->spell_chance=chance;s->spell_ranges=(unsigned char)AW_CastRanges(e,ne);
        }
    }
    if(best<0)return;
    s->spell=(short)best;totals.npc_spell_choices++;
    /* the range it casts from (suggestCombatRange), in map units */
    s->spell_range=AW_SpellAiCombatRange(s->spell_ranges,aw_combat_settings.fCombatDistance,
                                         aw_combat_settings.fHandToHandReach)*SCALE;
}
/* the start of the chosen cast (OpenMW startSpellCast: the magicka is paid now; CharacterController plays the
 * spellcast group of the first effect's range and casts on its release key) */
static int start_cast(slot_t *s,edict_t *p) {
    static const char *const variant[3]={"self","touch","target"};
    aw_actor_t *a=AW_MwscriptActorOf(s->e,NULL);aw_spell_effect_t e[AW_MADE_EFFECTS];aw_mgef_t m[AW_MADE_EFFECTS];
    int mcost,range,ci=cached_index(s,s->spell);float r;
    (void)p;
    if(!a || s->spell<0 || ci<0 || cached_effects(s,ci,e,m)<=0)return 0;
    mcost=s->sp[ci].cost;
    if(AW_ActorStat(a,AWA_MAGICKA)<(float)mcost)return 0;
    AW_ActorModCurrent(a,AWA_MAGICKA,-(float)mcost);   /* NPC-CAST-MAGICKA-NOT-PAID-66: stat 1 was Intelligence, which ModCurrent ignores */
    range=e[0].range<=AW_RANGE_TARGET?(int)e[0].range:AW_RANGE_TARGET;
    r=AW_AnimKitCast(s->e,variant[range]);
    s->cast_release=r>=0 && r<3?r:CAST_FALLBACK;s->cast_end=s->cast_release+CAST_TAIL;s->cast_left=0;
    /* the look (hand glow, cast sound, the orb or egg) starts with the animation and leaves on the release */
    s->cast_look=AW_MagicCastLookStart(NUM_FOR_EDICT(s->e),e[0].effect,range,0);
    set_state(s,S_CAST,r>=0?G_IDLE:G_CAST);s->f.attacking=1;   /* no kit cast (a skeletal creature): its own cast group */
    voice(s->e,AW_VOICE_SWING);
    if(readout.value){
        char name[32];   /* the readout's name only: one read while the readout is on */
        if(!AW_ActorSpellInfo(s->spell,NULL,name,sizeof(name),NULL))name[0]=0;
        Con_Printf("Combat: %s casts %s (chance %.0f %%)\n",s->f.name,name,s->spell_chance);
    }
    return 1;
}
/* the release of a cast under way: the roll (CastSpell::cast), then the delivery as the player's */
static void cast_release(slot_t *s) {
    int ok=AW_CombatRoll100(&rng)<(int)s->spell_chance || s->spell_chance>=100;
    s->cast_left=1;
    if(ok && AW_CastActorRelease(s->e,NULL,s->spell,AW_CombatReach(&aw_combat_settings,&s->f)*SCALE)>=0)totals.npc_casts++;
    else{ok=0;totals.npc_cast_fails++;}
    if(s->cast_look){AW_MagicCastLookRelease(s->cast_look,ok);s->cast_look=0;}
}

/* ---- the think ---- */
/* ---- ranged fighters (ACTOR-RANGED-COMBAT-MISSING-66; rules from OpenMW 0.51 aicombat.cpp, aicombataction.cpp,
 * projectilemanager.cpp, combat.cpp projectileHit, our own code): an actor whose sheet holds a bow, crossbow or thrown
 * weapon keeps its place while the player is in range and in sight and shoots; the shot is one entry of a 16-entry
 * pool, moved and traced once a frame (one SV_Move each), falling with the original's projectile gravity, drawn as a
 * short shaft of particles; it hits the first body or wall on its path; on the player it is a hit roll and damage as
 * a melee blow with the weapon's and the ammunition's chop, never blocked; one round of ammunition per shot, taken
 * from the actor's live record (so a save keeps it). Out of ammunition: hand to hand. ---- */
#define SHOT_LIFE 5.0f
#define SHOT_GRAVITY (686.0f*.1f*SCALE)   /* projectilemanager.cpp: GravityUnits x 0.1, in game units */
static struct {
    unsigned char used,slot;float strength,born;vec3_t pos,vel;edict_t *from;
} shots[AW_PROJECTILES];
static unsigned long shots_fired,shots_hit,shots_missed;
extern int AW_FxParticles(const float at[3],int count,float spread,const float vel[3],float vel_rand,float life,
                          int r,int g,int b,int gravity);
/* the ammunition of S's ranged weapon, read once: the best round of the needed type its live record carries (a thrown
 * weapon: the held weapon itself) */
static void ammo_read(slot_t *s) {
    aw_actor_t *a;int items[64],counts[64],equipped[64],n,i,need=AW_CombatAmmoType(s->f.weapon),best=-1;aw_item_t it;
    s->ammo_known=1;s->ammo_item=-1;s->ammo_left=0;s->ammo_chop[0]=s->ammo_chop[1]=0;
    if(need<0 || !(a=AW_MwscriptActorOf(s->e,NULL)))return;
    n=AW_ActorItems(a,items,counts,equipped,64);
    for(i=0;i<n;i++){
        if(!AW_ActorItem(items[i],&it) || it.kind!=AWK_WEAPON || counts[i]<=0)continue;
        if(need?it.type+1==need:(it.type==11 && equipped[i])){
            if(best<0 || it.damage[0]+it.damage[1]>best){
                best=it.damage[0]+it.damage[1];s->ammo_item=(short)items[i];s->ammo_left=counts[i];
                s->ammo_chop[0]=it.damage[0];s->ammo_chop[1]=it.damage[1];
            }
        }
    }
    if(!need){s->ammo_chop[0]=s->f.damage[0][0];s->ammo_chop[1]=s->f.damage[0][1];}   /* the weapon is the round */
}
/* out of ammunition: OpenMW rates the bow 0 and the actor fights with what is left; here hand to hand */
static void ammo_out(slot_t *s) {
    if(readout.value)Con_Printf("Combat: %s is out of ammunition\n",s->f.name);
    s->f.weapon=0;s->f.weapon_skill=AW_SK_H2H;memset(s->f.damage,0,sizeof(s->f.damage));s->f.reach=0;s->f.speed=1;
}
static void shot_fire(slot_t *s,edict_t *p) {
    int i;vec3_t from,to,dir;float speed;aw_actor_t *a;
    for(i=0;i<AW_PROJECTILES && shots[i].used;i++);
    if(i==AW_PROJECTILES)return;                      /* the pool is full: no shot this time */
    if(s->ammo_left<=0){ammo_out(s);return;}
    VectorCopy(s->e->v.origin,from);from[2]+=s->e->v.mins[2]+(s->e->v.maxs[2]-s->e->v.mins[2])*.75f;
    VectorCopy(p->v.origin,to);to[2]+=(p->v.view_ofs[2]>1?p->v.view_ofs[2]:22)*.7f;
    speed=AW_CombatShotSpeed(s->strength)*SCALE;
    AW_CombatShotAim(from,to,speed,SHOT_GRAVITY,dir);
    shots[i].used=1;shots[i].slot=(unsigned char)(s-slots);shots[i].strength=s->strength;shots[i].born=(float)sv.time;
    shots[i].from=s->e;VectorCopy(from,shots[i].pos);VectorScale(dir,speed,shots[i].vel);
    s->ammo_left--;shots_fired++;
    if((a=AW_MwscriptActorOf(s->e,NULL)) && s->ammo_item>=0)(void)AW_ActorRemoveItem(a,s->ammo_item,1);
    s->f.fatigue-=aw_combat_settings.fFatigueAttackBase+s->f.weight*s->strength*aw_combat_settings.fWeaponFatigueMult;
    totals.npc_swings++;sound(SND_SWISH);
    if(readout.value)Con_Printf("Combat: %s shoots (%d left)\n",s->f.name,s->ammo_left);
}
/* the shot of slot S reaches the player: OpenMW projectileHit (the hit chance, the weapon's and the round's chop by the
 * draw strength, armour; no block) */
static void shot_hit(slot_t *s,edict_t *p,float strength) {
    aw_swing_t out;aw_fighter_t shooter,before;
    you.health=p->v.health;
    if(you.dead)return;
    AW_CombatShotSheet(&s->f,s->ammo_chop,&shooter);
    you.staggered=0;you.block_off=1;                  /* a shot is never blocked */
    shooter.weapon_normal=1;you.resist_normal=normal_resistance(p,0);
    hit_effects(s->e,&shooter);hit_effects(p,&you);
    before=you;
    AW_CombatSwing(&aw_combat_settings,&shooter,&you,0,strength,0,1,&rng,&out);
    if((int)p->v.flags&FL_GODMODE){AW_CombatGodVictim(&you,&before,&out);god_blows++;}
    you.block_off=0;
    s->f.weapon_health=shooter.weapon_health;
    if(out.outcome==AW_HIT_MISS || out.outcome==AW_HIT_BLOCKED){totals.npc_misses++;shots_missed++;}
    else{
        totals.npc_hits++;shots_hit++;
        if(out.outcome==AW_HIT_HEALTH && out.damage>0){totals.taken_health+=out.damage;flash(out.damage);sound(SND_HEALTH);
            if(!you.dead)voice(p,AW_VOICE_HIT);}
        else if(out.outcome==AW_HIT_FATIGUE)totals.taken_fatigue+=out.damage;
    }
    print_swing(s->f.name,"you",0,&out);
    if(out.knockdown && you.knocked==1)totals.player_down_until=sv.time+knock_seconds;
    you_store(p);
    if(you.dead){
        if(readout.value)Con_Printf("Combat: you have been killed by %s\n",s->f.name);
        voice(p,AW_VOICE_DEATH);sound(SND_FALL);ended(0);
    }
}
/* every shot in flight, once a frame: the move, one trace, the shaft */
static void shots_update(edict_t *p,float dt) {
    int i,k;vec3_t next,back;trace_t tr;
    for(i=0;i<AW_PROJECTILES;i++){
        if(!shots[i].used)continue;
        if(shots[i].from->free || sv.time-shots[i].born>SHOT_LIFE){shots[i].used=0;continue;}
        AW_CombatShotStep(shots[i].pos,shots[i].vel,SHOT_GRAVITY,dt,next);
        tr=SV_Move(shots[i].pos,vec3_origin,vec3_origin,next,MOVE_NORMAL,shots[i].from);
        cost.traces++;
        if(tr.fraction<1 || tr.startsolid){
            slot_t *s=&slots[shots[i].slot];
            if(tr.ent==p && s->e==shots[i].from)shot_hit(s,p,shots[i].strength);
            else shots_missed++;                      /* a wall, the ground or another body: it stops there */
            shots[i].used=0;continue;
        }
        VectorCopy(next,shots[i].pos);
        /* the shaft: four points behind the head, along the flight, for one frame */
        {float len=(float)Length(shots[i].vel);if(len<1)len=1;
         for(k=0;k<4;k++){VectorMA(shots[i].pos,-2.5f*k/len,shots[i].vel,back);
                          (void)AW_FxParticles(back,1,0,NULL,0,.05f,k?110:200,k?80:200,k?50:200,0);}}
    }
}
static void shots_clear(void) {memset(shots,0,sizeof(shots));}
static void think(slot_t *s,edict_t *p,float dt) {
    int self[3],goal[3],heading,moved=0,step;float dz,gap,reach;aw_path_io_t io;unsigned long before;
    s->f.moving=0;s->f.attacking=s->state==S_SWING;
    if(AW_CombatRecover(&aw_combat_settings,&s->f,dt))set_state(s,S_CHASE,G_IDLE);
    if(s->state==S_DEAD)return;
    if(s->f.fatigue<0 && !s->f.knocked){s->f.knocked=2;set_state(s,S_KNOCK,G_KNOCK);sound(SND_FALL);}   /* knocked out */
    if(s->state==S_KNOCK){
        /* the knockdown lasts its clip (character.cpp: the hit state ends with the group) */
        if(s->f.knocked==1 && s->state_time>=duration(s,G_KNOCK)){s->f.knocked=0;set_state(s,S_CHASE,G_IDLE);}
        return;
    }
    s->f.staggered=s->state==S_HIT;
    if(s->state==S_HIT){if(s->state_time>=duration(s,G_HIT))set_state(s,S_CHASE,G_IDLE);s->f.staggered=s->state==S_HIT;return;}
    if(s->state==S_BLOCK){if(s->state_time>=(s->has_block?duration(s,G_BLOCK):block_seconds))set_state(s,S_CHASE,G_IDLE);return;}
    if(s->state==S_DODGE){
        if(s->dodged<DODGE_UNITS && !AW_ActorStationary(s->e)){
            float yaw=(s->e->v.angles[1]+90)*(float)M_PI/180,dstep=DODGE_UNITS*dt/DODGE_SECONDS;vec3_t move;
            if(dstep>DODGE_UNITS-s->dodged)dstep=DODGE_UNITS-s->dodged;
            move[0]=Q_SinRad(yaw)*dstep*s->dodge_dir;move[1]=-Q_CosRad(yaw)*dstep*s->dodge_dir;move[2]=0;
            pass_player(1);if(!AW_ActorStep(s->e,move,host_frametime>0?host_frametime:dt))s->dodged=DODGE_UNITS;pass_player(0);
            s->dodged+=dstep;
        }
        if(s->state_time>=DODGE_SECONDS+.1f)set_state(s,S_CHASE,G_IDLE);
        return;
    }
    /* P is the slot's target: the player, or since v0.0.63 another actor (COMBAT-ACTOR-VS-ACTOR-62; the player's own
     * states below apply only to the player) */
    if(!s->target_num && you.dead){if(s->group!=G_IDLE)set_state(s,S_CHASE,G_IDLE);return;}
    /* Quake notarget (the camera orbit detaches the player, dbg cam orbit): no chase, no attack */
    if(!s->target_num && ((int)p->v.flags&FL_NOTARGET)){if(s->group!=G_IDLE)set_state(s,S_CHASE,G_IDLE);return;}
    /* Unreachable player (no path): flee, never warp, no combat timeout.
     * OpenMW 0.51 aicombat.cpp 295-339 and 363-467: with no route the actor
     * drops the attack and flees; without a pathgrid it runs directly away
     * for 1.0 s, then stands and watches; the decision is retaken every
     * 3.0 s, so it fights again as soon as the player is reachable. */
    if(s->state==S_FLEE){
        if(s->state_time<1.0f && !AW_ActorStationary(s->e)){
            vec3_t away;float len;int fled;
            away[0]=s->e->v.origin[0]-p->v.origin[0];away[1]=s->e->v.origin[1]-p->v.origin[1];away[2]=0;
            len=(float)AW_PathLength((int)away[0],(int)away[1]);if(len<1)len=1;
            VectorScale(away,fighter_speed(s)*dt/len,away);
            pass_player(1);fled=AW_ActorStep(s->e,away,host_frametime>0?host_frametime:dt);pass_player(0);
            s->e->v.angles[1]=AW_PathHeading((int)-away[0],(int)-away[1])*360.0f/AW_PATH_FAN+90;
            s->f.moving=(unsigned char)fled;s->group=fled?G_RUN:G_IDLE;
            return;
        }
        s->group=G_IDLE;face_player(s->e,p);
        /* the flee rule on: the player caught up: run again (aicombat.cpp updateFleeing, FleeState_Idle -> RunBlindly
         * when the target is within its attack distance) */
        if(flee_on){
            reach=AW_CombatReach(&aw_combat_settings,&s->f)*SCALE;gap=gap_to(s->e,p,&dz);
            if(gap<=reach && sv.time<s->decide_at){s->state_time=0;return;}
        }
        if(sv.time<s->decide_at)return;
        AW_PathReset(&s->path,(int)floor(s->e->v.origin[0]),(int)floor(s->e->v.origin[1]));
        set_state(s,S_CHASE,G_IDLE);
    }
    face_player(s->e,p);
    if(s->state==S_CAST)return;                          /* the cast and its release: per frame */
    /* A flyer near the player holds its striking place in the air (COMBAT-FLYER-FLEES-57 reopened: it fought from
     * inside the player, drawn at the player's feet): in front of the player, at 70 % of its striking gap from the
     * player's hull, a little above the player's eyes (Quake's 22 when view_ofs is unset), moving there at the chase speed
     * against the world only (touching the player's hull must not pin it), every think, swings included. */
    if((AW_AmbientFlags(s->e)&AW_AMBIENT_FLYER) && gap_to(s->e,p,&dz)<=AW_CombatReach(&aw_combat_settings,&s->f)*SCALE*1.5f){
        edict_t *fe=s->e;vec3_t hold,dv,end;trace_t tr;
        float r=AW_CombatReach(&aw_combat_settings,&s->f)*SCALE,hx=fe->v.origin[0]-p->v.origin[0],hy=fe->v.origin[1]-p->v.origin[1];
        float hl=(float)sqrt(hx*hx+hy*hy),stand=r*.7f+(fe->v.maxs[0]>8?fe->v.maxs[0]:7.32f)+(p->v.maxs[0]>8?p->v.maxs[0]:7.32f),len,mv;
        if(hl<1){hx=1;hy=0;hl=1;}
        hold[0]=p->v.origin[0]+hx/hl*stand;hold[1]=p->v.origin[1]+hy/hl*stand;
        /* above the eyes: a player standing in water has the eyes at the surface, and a flyer at that height is
         * hidden under the drawn water (seen in game, 30 October 2026) */
        hold[2]=p->v.origin[2]+(p->v.view_ofs[2]>1?p->v.view_ofs[2]:22)+16;
        VectorSubtract(hold,fe->v.origin,dv);len=(float)Length(dv);mv=fighter_speed(s)*dt;
        if(len>2){
            if(mv>len)mv=len;
            VectorMA(fe->v.origin,mv/len,dv,end);
            tr=SV_Move(fe->v.origin,fe->v.mins,fe->v.maxs,end,MOVE_NOMONSTERS,fe);
            if(readout.value>=2)Con_Printf("flyer %s: at %.0f %.0f %.0f hold %.0f %.0f %.0f frac %.2f solid %d\n",s->f.name,fe->v.origin[0],
                                           fe->v.origin[1],fe->v.origin[2],hold[0],hold[1],hold[2],tr.fraction,(int)tr.startsolid);
            if(!tr.startsolid && !tr.allsolid && tr.fraction>0){VectorCopy(tr.endpos,fe->v.origin);SV_LinkEdict(fe,false);}
        }
    }    if(s->state==S_SWING)return;                         /* strike and end: per frame */
    reach=AW_CombatReach(&aw_combat_settings,&s->f)*SCALE;
    gap=gap_to(s->e,p,&dz);
    /* the flee rule on: the flee decision of every next action (aicombat.cpp: prepareNextAction whenever the actor is
     * ready; a melee action has no cooldown, ActionFlee 3 s) */
    if(flee_on && ai_ok && s->state==S_CHASE){
        float d=original_distance(s->e,p);
        /* ACTOR-MECHANICS-USE-STATS-66 row 16: the werewolf case, and a spell that is the best action rates against
         * fleeing by its own success chance (prepareNextAction: the masters' fAIMagicSpellMult 3, fAIRangeMagicSpellMult 5) */
        float were=AW_CombatWerewolfFleeMod(&s->f,aw_move_werewolf,were_level,were_flee_mod);
        float anti=spells_on && s->spell>=0?AW_CombatSpellAntiFlee(s->spell_chance,s->spell_ranges,3,5,AW_AmbientInWater(p->v.origin)):
                   AW_CombatAntiFleeRating(&aw_combat_ai,&s->f);
        if(AW_CombatFleeDecisionVs(&aw_combat_ai,&s->f,d,were,anti)){
            totals.npc_flees++;
            if(readout.value)Con_Printf("Combat: %s flees (health %ld/%ld, Flee %ld, rating %ld over %ld)\n",s->f.name,
                (long)s->f.health,(long)s->f.health_max,(long)s->f.flee,(long)AW_CombatFleeRatingVs(&aw_combat_ai,&s->f,d,were),
                (long)anti);
            voice(s->e,AW_VOICE_FLEE);
            set_state(s,S_FLEE,G_RUN);s->decide_at=(float)sv.time+3.0f;return;
        }
    }
    if(s->cooldown>0)s->cooldown-=dt;
    /* NPC-NO-SPELLCASTING-65: the next action, weighed each SPELL_DECIDE seconds against the player: a spell that rates
     * above the weapon is cast once the player is within its range and in sight (OpenMW AiCombat: the action's combat
     * range, then the attack); otherwise the chase and the swing below */
    if(spells_on && !s->target_num && s->cooldown<=0 && sv.time>=s->spell_at && !you.dead){
        s->spell_at=(float)sv.time+SPELL_DECIDE;
        choose_spell(s,p);
    }
    if(spells_on && s->spell>=0 && !s->target_num && s->cooldown<=0 && gap<=s->spell_range && !you.dead){
        trace_t tr;vec3_t from,to;
        VectorCopy(s->e->v.origin,from);from[2]+=s->e->v.mins[2]+(s->e->v.maxs[2]-s->e->v.mins[2])*.75f;
        VectorCopy(p->v.origin,to);to[2]+=p->v.view_ofs[2]>1?p->v.view_ofs[2]:22;
        tr=SV_Move(from,vec3_origin,vec3_origin,to,MOVE_NOMONSTERS,s->e);
        if(tr.fraction>=1 && !tr.startsolid){
            AW_PathIdle(&s->path,(int)s->e->v.origin[0],(int)s->e->v.origin[1]);
            if(start_cast(s,p))return;
            s->spell=-1;   /* not enough magicka now: the weapon until the next choice */
        }
    }
    /* ACTOR-RANGED-COMBAT-MISSING-66: a bow, crossbow or thrown weapon against the player: the actor keeps its place
     * and shoots while the player is within the weapon's combat range (fProjectileMaxSpeed) and in sight; otherwise
     * it closes in as below (OpenMW aicombat.cpp: a ranged action does not chase once in range and in view) */
    if(AW_COMBAT_RANGED(s->f.weapon) && !s->target_num && !you.dead){
        if(!s->ammo_known)ammo_read(s);
        if(s->ammo_left<=0)ammo_out(s);
        else{
            trace_t tr;vec3_t from,to;
            VectorCopy(s->e->v.origin,from);from[2]+=s->e->v.mins[2]+(s->e->v.maxs[2]-s->e->v.mins[2])*.75f;
            VectorCopy(p->v.origin,to);to[2]+=p->v.view_ofs[2]>1?p->v.view_ofs[2]:22;
            tr=SV_Move(from,vec3_origin,vec3_origin,to,MOVE_NOMONSTERS,s->e);
            if(AW_CombatShootNow(&s->f,s->ammo_left,gap/SCALE,tr.fraction>=1 && !tr.startsolid)){
                if(s->group!=G_IDLE)set_state(s,S_CHASE,G_IDLE);
                AW_PathIdle(&s->path,(int)s->e->v.origin[0],(int)s->e->v.origin[1]);
                if(s->cooldown<=0){
                    /* the draw: the actor's attack strength in OpenMW, min(1, 0.1 + a roll) */
                    float x=.1f+AW_CombatRoll01(&rng);
                    s->attack=0;s->strength=x>1?1:x;s->struck=0;s->shooting=1;
                    s->swing_time=duration(s,G_ATTACK)/(s->f.speed>0?s->f.speed:1);
                    set_state(s,S_SWING,G_ATTACK);s->f.attacking=1;
                }
                return;
            }
        }
    }
    /* a flyer strikes from its place above the player's eyes, so its height gap may be larger by that much */
    if(gap<=reach*.8f && dz<reach+((AW_AmbientFlags(s->e)&AW_AMBIENT_FLYER)?64:0) &&
       dz>-reach-((AW_AmbientFlags(s->e)&AW_AMBIENT_FLYER)?64:0)){
        if(s->group!=G_IDLE)set_state(s,S_CHASE,G_IDLE);
        AW_PathIdle(&s->path,(int)s->e->v.origin[0],(int)s->e->v.origin[1]);
        if(s->cooldown<=0){
            /* AiCombat: best attack, swing strength, then a cooldown */
            s->attack=(unsigned char)AW_CombatBestAttack(&s->f,&rng);s->strength=AW_CombatRoll01(&rng);
            s->struck=0;s->shooting=0;s->swing_time=duration(s,G_ATTACK)/(s->f.weapon && s->f.speed>0?s->f.speed:1);
            voice(s->e,AW_VOICE_SWING);
            set_state(s,S_SWING,G_ATTACK);s->f.attacking=1;
        }
        return;
    }
    /* HEART-OF-LORKHAN-FOLLOWS-DAGOTH-65: a creature that can move by no means strikes only within its reach */
    if(AW_ActorStationary(s->e)){if(s->group!=G_IDLE)set_state(s,S_CHASE,G_IDLE);return;}
    /* A flying fighter (COMBAT-FLYER-FLEES-57): OpenMW 0.51 aipackage.cpp pathTo lets an actor that can move by the
     * Z axis shortcut straight to its target while it is in line of sight (shortcutPath, UpdateFlag_CanMoveByZ),
     * never the walkers' ground route. Here: the standing hull swept straight toward the player's height in three
     * dimensions (no floor test, no gravity); a blocked sweep keeps it where it is (no flee: the target is reachable
     * through the air). Walkers keep the ground chase below. Our own code. */
    if(AW_AmbientFlags(s->e)&(AW_AMBIENT_FLYER|AW_AMBIENT_SWIMMER)){
        vec3_t d,end;trace_t tr;float len;edict_t *fe=s->e;
        step=fighter_step(s,dt);if(step>(int)(gap-reach*.6f))step=(int)(gap-reach*.6f);if(step<1)step=1;
        /* the goal is not the player's centre (it flew into the player and fought from inside, drawn out of sight:
         * COMBAT-FLYER-FLEES-57 reopened) but a point in front of the player at striking distance, a flyer at the
         * player's eye height (a swimmer at the player's own height); the player stays solid to the sweep */
        {
            float hx=s->e->v.origin[0]-p->v.origin[0],hy=s->e->v.origin[1]-p->v.origin[1],hl=(float)sqrt(hx*hx+hy*hy),stand=reach*.7f+(fe->v.maxs[0]>8?fe->v.maxs[0]:7.32f)+(p->v.maxs[0]>8?p->v.maxs[0]:7.32f);   /* centre distance at 70 % of the striking gap (gap_to), so it is seen in front, not inside the view */
            vec3_t goal3;
            if(hl<1){hx=1;hy=0;hl=1;}
            goal3[0]=p->v.origin[0]+hx/hl*stand;goal3[1]=p->v.origin[1]+hy/hl*stand;
            goal3[2]=p->v.origin[2]+((AW_AmbientFlags(fe)&AW_AMBIENT_FLYER)?(p->v.view_ofs[2]>1?p->v.view_ofs[2]:22):0);   /* 22: Quake's eye height when view_ofs is not set */
            VectorSubtract(goal3,s->e->v.origin,d);
        }
        len=(float)Length(d);
        if(len>1){
            if((float)step>len)step=(int)len;
            VectorMA(s->e->v.origin,(float)step/len,d,end);
            tr=SV_Move(fe->v.origin,fe->v.mins,fe->v.maxs,end,MOVE_NORMAL,fe);
            /* a swimmer chases the same straight way but never leaves the water (OpenMW: a pure water creature's path
             * stays in water); at the shore it waits there */
            /* blocked on the way (a rock, a roof): a flyer climbs over it first (OpenMW's flyers leave the straight
             * shortcut when it is not clear; here the cheapest way round is up) */
            if((tr.startsolid || tr.allsolid || tr.fraction<1) && (AW_AmbientFlags(fe)&AW_AMBIENT_FLYER)){
                VectorCopy(fe->v.origin,end);end[2]+=step;
                tr=SV_Move(fe->v.origin,fe->v.mins,fe->v.maxs,end,MOVE_NORMAL,fe);
            }
            if(!tr.startsolid && !tr.allsolid && tr.fraction>0 &&
               (!(AW_AmbientFlags(fe)&AW_AMBIENT_SWIMMER) || AW_AmbientInWater(tr.endpos))){VectorCopy(tr.endpos,s->e->v.origin);SV_LinkEdict(s->e,false);moved=1;}
        }
        s->f.moving=(unsigned char)moved;
        if(moved && s->group!=G_RUN)set_state(s,S_CHASE,G_RUN);
        else if(!moved && s->group!=G_IDLE)set_state(s,S_CHASE,G_IDLE);
        face_player(s->e,p);
        return;
    }
    self[0]=(int)floor(s->e->v.origin[0]);self[1]=(int)floor(s->e->v.origin[1]);self[2]=(int)floor(s->e->v.origin[2]+s->e->v.mins[2]);
    goal[0]=(int)floor(p->v.origin[0]);goal[1]=(int)floor(p->v.origin[1]);goal[2]=(int)floor(p->v.origin[2]+p->v.mins[2]);
    step=fighter_step(s,dt);if(step>(int)(gap-reach*.6f))step=(int)(gap-reach*.6f);if(step<1)step=1;
    io.context=s->e;io.sweep=sweep;io.cell=cell;
    pass_player(1);
    if(AW_PathThink(&s->path,&io,self,goal,step,&heading)){
        vec3_t move;
        move[0]=aw_path_fan[heading][0]*step/(float)AW_PATH_FAN_RADIUS;
        move[1]=aw_path_fan[heading][1]*step/(float)AW_PATH_FAN_RADIUS;move[2]=0;
        before=aw_sv_move_calls;
        moved=AW_ActorStep(s->e,move,host_frametime>0?host_frametime:dt);
        cost.traces+=aw_sv_move_calls-before;
    }
    pass_player(0);
    s->f.moving=(unsigned char)moved;
    /* PROTOTYPE diagnostics (branch v0.0.46-type1-stateful, COMBAT-CHASE-CHIM-STUCK-46): "aw_combat_cmd readout 2"
     * is not a toggle word, so the cvar is set directly: aw_combat_readout 2 prints every chase think. */
    if(readout.value>=2){
        trace_t t;vec3_t end;edict_t *se=s->e;
        VectorCopy(se->v.origin,end);end[2]-=8.75f;
        t=SV_Move(se->v.origin,se->v.mins,se->v.maxs,end,MOVE_NORMAL,se);
        Con_Printf("chase %s: mode %d step %d moved %d at %ld %ld %ld goal %ld %ld %ld onground %d hull %ld..%ld below frac %ld/100 solid %d/%d normz %ld/100 hit %d\n",
            s->f.name,(int)s->path.mode,step,moved,(long)s->e->v.origin[0],(long)s->e->v.origin[1],(long)s->e->v.origin[2],
            (long)goal[0],(long)goal[1],(long)goal[2],((int)s->e->v.flags&FL_ONGROUND)!=0,(long)s->e->v.mins[2],(long)s->e->v.maxs[2],
            (long)(t.fraction*100),(int)t.startsolid,(int)t.allsolid,(long)(t.plane.normal[2]*100),t.ent!=NULL);
    }
    if(s->path.mode==AW_PATH_LOST){
        totals.npc_flees++;
        if(readout.value)Con_Printf("Combat: %s cannot reach you and flees\n",s->f.name);
        voice(s->e,AW_VOICE_FLEE);
        set_state(s,S_FLEE,G_RUN);s->decide_at=(float)sv.time+3.0f;return;
    }
    if(moved && s->group!=G_RUN)set_state(s,S_CHASE,G_RUN);
    else if(!moved && s->group!=G_IDLE)set_state(s,S_CHASE,G_IDLE);
    face_player(s->e,p);
}
/* SV_Physics, after the entities and the companion. */
void AW_CombatPhysics(void) {
    edict_t *p;int i,any=0;float dt=(float)host_frametime,interval;double t0;
    if(!combat_on.value || !(p=player()))return;
    /* Only for a spawned player (MUSIC-DEATH-TRACK-RANDOM-60): a new map's settle frames (sv_main.c SV_SpawnServer runs
     * SV_Physics twice) and the signon frames after "connect local" see the fresh client edict at health 0 before
     * Host_Spawn_f gives it back (aw_scene.c), and the old map's slots before AW_CombatSceneSpawn empties them: that
     * read as the player's death and played the death track on an area change. */
    if(!svs.clients[0].active || !svs.clients[0].spawned)return;
    aw_combat_dice=dice_cvar.value!=0;
    for(i=0;i<SLOTS;i++){
        slot_t *s=&slots[i];
        if(!s->e)continue;
        if(s->e->free){AW_ItemsHide(s->item);memset(s,0,sizeof(*s));continue;}
        /* COMBAT-ACTOR-VS-ACTOR-62: a fight against another actor ends when that actor is dead or gone (OpenMW
         * aicombat.cpp: the package ends with its target); the slot is released, the actor calms down */
        if(s->target_num && s->state!=S_DEAD && !s->f.dead && !actor_target(s)){release(s);continue;}
        any=any || !s->target_num;s->state_time+=dt;
        if(s->state==S_SWING){
            if(!s->struck && s->state_time>=s->swing_time*s->hit_fraction){
                s->struck=1;
                if(s->shooting){if(!you.dead && !((int)p->v.flags&FL_NOTARGET))shot_fire(s,p);}   /* the release */
                else if(s->target_num){slot_t *v=actor_target(s);if(v)npc_strike_actor(s,v);}
                else if(!you.dead && !((int)p->v.flags&FL_NOTARGET))npc_strike(s,p);
            }
            if(s->state_time>=s->swing_time){
                s->f.attacking=0;s->shooting=0;set_state(s,S_CHASE,G_IDLE);
                s->cooldown=aw_combat_settings.fCombatDelayNPC+.01f*AW_CombatRoll100(&rng);
                if(s->cooldown>aw_combat_settings.fCombatDelayNPC+.9f)s->cooldown=aw_combat_settings.fCombatDelayNPC+.9f;
            }
        }
        /* NPC-NO-SPELLCASTING-65: a cast leaves on its release key, then the group's rest, then the next action */
        if(s->state==S_CAST){
            if(!s->cast_left && s->state_time>=s->cast_release){if(!you.dead)cast_release(s);else s->cast_left=1;}
            if(s->state_time>=s->cast_end){
                s->f.attacking=0;set_state(s,S_CHASE,G_IDLE);s->spell_at=(float)sv.time;
                s->cooldown=aw_combat_settings.fCombatDelayNPC+.01f*AW_CombatRoll100(&rng);
                if(s->cooldown>aw_combat_settings.fCombatDelayNPC+.9f)s->cooldown=aw_combat_settings.fCombatDelayNPC+.9f;
            }
        }else if(s->cast_look){AW_MagicCastLookRelease(s->cast_look,-1);s->cast_look=0;}   /* interrupted (a hit) */
        if(sv.time>=s->next_think){
            interval=think_interval.value<.05f?.05f:think_interval.value>.2f?.2f:think_interval.value;
            dt=(float)(sv.time-s->last_think);if(dt>.3f)dt=.3f;if(dt<0)dt=interval;
            s->last_think=(float)sv.time;s->next_think=(float)sv.time+interval;
            t0=Sys_FloatTime();
            {slot_t *v=s->target_num?actor_target(s):NULL;if(!s->target_num || v)think(s,v?v->e:p,dt);}
            t0=Sys_FloatTime()-t0;
            cost.thinks++;cost.seconds+=t0;if(t0>cost.max)cost.max=t0;
            dt=(float)host_frametime;
        }
        if(s->state==S_SWING)s->group=G_ATTACK;
        animate(s);
        AW_ItemsUpdate(s->e,s->item);
    }
    shots_update(p,(float)host_frametime);            /* ACTOR-RANGED-COMBAT-MISSING-66: the shots in flight */
    /* The player: punch, fatigue return, the knockout clock. */
    if((watching || p->v.button0 || any) && !you_valid && AW_CombatSettingsLoad()){AW_CombatPlayerSheet(&you);you_valid=1;}
    if(you_valid){
        you_refresh(&you);   /* HAND-TO-HAND-NO-HIT-64: the live attributes and skills, not the fight's start */
        you.health=p->v.health;
        if(you.health<=0)you.dead=1;
        if(!you.dead){
            if(you.fatigue<0 && !you.knocked)you.knocked=2;
            if(AW_CombatRecover(&aw_combat_settings,&you,(float)host_frametime) && readout.value)Con_Printf("Combat: you get up\n");
            if(you.knocked==1 && sv.time>=totals.player_down_until){you.knocked=0;if(readout.value)Con_Printf("Combat: you get up\n");}
            if(!you.knocked && (watching || p->v.button0))watch_punch(p);
            player_dodge_step(p,(float)host_frametime);
            if(aw_character.valid)aw_character.current[2]=you.fatigue;
        }
        player_down_view(p);
        if(!any && !watching && !pv.view_saved && you.fatigue>=you.fatigue_max)you_valid=0;
    }else if(aw_character.valid && aw_character.current[2]<aw_character.maximum[2] && settings_ok){
        /* No fight: the player's fatigue still returns (Actors::calculateRestoration). */
        aw_fighter_t f;AW_CombatPlayerSheet(&f);AW_CombatRecover(&aw_combat_settings,&f,(float)host_frametime);
        aw_character.current[2]=f.fatigue;
    }
    if(enemy && (enemy->free || sv.time>=enemy_until))enemy=NULL;
    /* Battle music while anyone fights the player (OpenMW music.lua:
     * the battle playlist is active while an actor has combat targets). */
    if(music.value){
        int want=AW_PlayerInCombat();
        if(you_valid && you.dead){if(!dead_music){dead_music=1;AW_MusicDeath();}}
        else if(want!=battle){battle=want;AW_MusicCombat(want);}
    }
}
/* HUD::setEnemy / updateEnemyHealthBar: shown fNPCHealthBarTime seconds
 * after the player's last attempt in reach, fading over the last
 * fNPCHealthBarFade seconds. */
int AW_CombatEnemyBar(float *fraction,float *alpha) {
    slot_t *s;float left;
    if(!enemy || !(s=slot_of(enemy)) || !sv.active || AW_PlayerDead())return 0;
    left=enemy_until-(float)sv.time;if(left<0)return 0;
    *fraction=s->f.health_max>0?s->f.health/s->f.health_max:0;
    *alpha=aw_combat_settings.fNPCHealthBarFade>0?left/aw_combat_settings.fNPCHealthBarFade:1;
    if(*alpha>1)*alpha=1;
    return 1;
}
int AW_CombatAiLoaded(void) {return AW_CombatSettingsLoad() && ai_ok;}
/* Aggro on sight (aw_combat.h): OpenMW Actors::engageCombat's check against the player, run by the caller on the
 * engage timer (actor.hpp mEngageCombat: every 1 s, deviating by 0.25 s). */
int AW_CombatAggro(edict_t *e,const aw_fighter_t *sheet,const char *layout,int disposition,int *rating,float *distance) {
    edict_t *p=player();float d;int r;vec3_t from,to;trace_t tr;aw_fighter_t f;
    if(rating)*rating=0;
    if(distance)*distance=0;
    if(!e || e->free || !sheet || !p)return -1;
    if(slot_of(e))return 1;
    if(!combat_on.value || !AW_CombatAiLoaded() || p->v.health<=0)return -1;
    d=original_distance(e,p);r=AW_CombatFightRating(&aw_combat_ai,sheet->fight,disposition,d);
    if(rating)*rating=r;
    if(distance)*distance=d;
    if(r<100 || sheet->dead)return 0;
    if((int)p->v.flags&FL_NOTARGET)return 0;
    /* World::getLOS: eye to eye, the world only (actors do not block) */
    VectorCopy(e->v.origin,from);from[2]+=e->v.maxs[2]*.9f;
    VectorCopy(p->v.origin,to);to[2]+=p->v.view_ofs[2];
    tr=SV_Move(from,vec3_origin,vec3_origin,to,MOVE_NOMONSTERS,e);
    if(tr.fraction<1 || tr.startsolid || tr.allsolid)return 0;
    f=*sheet;f.aware=1;
    if(!AW_CombatEngage(e,&f,layout))return -1;
    if(readout.value)Con_Printf("Combat: %s attacks on sight (Fight %ld, rating %ld at %ld)\n",f.name,(long)f.fight,(long)r,(long)d);
    return 1;
}
int AW_CombatActorFleeing(edict_t *e) {slot_t *s=e?slot_of(e):NULL;return s && s->state==S_FLEE && !s->f.dead;}
void AW_CombatCost(float *per_second,float *ms_mean,float *ms_max,int *fighters) {
    double span=sv.time-totals.started;
    if(span<.001)span=.001;
    if(per_second)*per_second=(float)(cost.thinks/span);
    if(ms_mean)*ms_mean=(float)(cost.thinks?cost.seconds*1000/cost.thinks:0);
    if(ms_max)*ms_max=(float)(cost.max*1000);
    if(fighters)*fighters=AW_CombatHostiles();
}
/* aw_scene.c: a new map; the old edicts are gone. */
void AW_CombatSceneSpawn(void) {
    int i;for(i=0;i<SLOTS;i++)memset(&slots[i],0,sizeof(slots[i]));
    memset(&pv,0,sizeof(pv));block_shown_until=0;settings_tried=0;
    enemy=NULL;you_valid=0;memset(&retry,0,sizeof(retry));shots_clear();
    if(battle){battle=0;AW_MusicCombat(0);}
}

/* ---- dbg combat ---- */
static void report(void) {
    int i;double span=sv.time-totals.started;if(span<.001)span=.001;
    AW_CombatSettingsLoad();             /* before any fight the settings are not read yet: say what the image holds */
    Con_Printf("Combat %s, readout %s, music %s, seed %lu (aw_combat_seed %ld)\n",combat_on.value?"on":"off",
        readout.value?"on":"off",music.value?"on":"off",seed_used,(long)seed_cvar.value);
    Con_Printf("Blocking: %s%s; blocks: you %lu, NPCs %lu; guards %lu\n",block_cvar.value?"hold to block (AmiWind)":"automatic (original)",
        AW_CombatGuarding()?", guarding":"",totals.player_blocks,totals.npc_blocks,totals.guards);
    Con_Printf("Flee by rating: %s; aggro and flee settings %s; flees %ld\n",flee_on?"on":"off",
        ai_ok?"loaded":"missing (rebuild the image)",(long)totals.npc_flees);
    Con_Printf("Sounds: %s\n",sounds_on?"as OpenMW (dbg combat sounds on)":"one per outcome (dbg combat sounds off)");
    Con_Printf("Best attack: %s; hit contact: %s (swings found by the cone %ld)\n",best_cvar.value?"on":"off",
        contact_on?"cone when the crosshair misses":"crosshair only",(long)totals.player_contacts);
    Con_Printf("Spells: %s; spell choices %lu, casts %lu, failed %lu (ratings %lu; all actors' casts %lu; spell reads %lu, at the fight's start only)\n",
        spells_on?"fighters cast the spells they know (dbg combat spells off: weapons only)":"weapons only",
        totals.npc_spell_choices,totals.npc_casts,totals.npc_cast_fails,spell_ratings,AW_CastActorCasts(),totals.npc_spell_reads);
    for(i=0;i<SLOTS;i++)if(slots[i].e)Con_Printf(" %s: health %ld/%ld fatigue %ld/%ld %s\n",slots[i].f.name,
        (long)slots[i].f.health,(long)slots[i].f.health_max,(long)slots[i].f.fatigue,(long)slots[i].f.fatigue_max,
        slots[i].f.dead?"dead":slots[i].f.knocked?"down":"fighting");
    if(you_valid)Con_Printf(" You: health %ld/%ld fatigue %ld/%ld\n",(long)you.health,(long)you.health_max,(long)you.fatigue,(long)you.fatigue_max);
    Con_Printf("thinks %lu (%.1f/s) swings %lu move traces %lu; ms/think avg %.3f max %.3f\n",cost.thinks,cost.thinks/span,
        cost.swings,cost.traces,cost.thinks?cost.seconds*1000/cost.thinks:0.0,cost.max*1000);
    {int n=0;for(i=0;i<AW_PROJECTILES;i++)n+=shots[i].used;
     Con_Printf("Shots: fired %lu, hit you %lu, missed %lu; in flight %d of %d (%ld bytes)\n",shots_fired,shots_hit,
        shots_missed,n,AW_PROJECTILES,(long)sizeof(shots));}
    if(god_blows)Con_Printf("god mode turned away %lu blows (no damage, no knockdown)\n",god_blows);
    Con_Printf("bytes: per hostile NPC %ld, all slots %ld, player sheet %ld; no allocation\n",(long)sizeof(slot_t),
        (long)sizeof(slots),(long)sizeof(you));
}
/* +aw_alt (the Amiga right mouse button, keymaps.cfg): one context action. Pick mode
 * (dbg companion pick): pick the companion under the crosshair (the left button picks
 * too). Otherwise the block button (COMBAT-BLOCKING-36): with aw_combat_block 1 (the
 * option; the default 0 is automatic) the player guards while it is held. */
static int shield_ready(void) {
    aw_fighter_t f;const aw_fighter_t *o=&f;
    if(you_valid)o=&you;else{if(!settings_ok && !AW_CombatSettingsLoad())return 0;AW_CombatPlayerSheet(&f);}
    return o->shield && !AW_TWO_HANDED(o->weapon) && !o->dead && !o->knocked;
}
int AW_CombatGuarding(void) {
    return guard_key && block_cvar.value && combat_on.value && player()!=NULL && !AW_PlayerDead() && shield_ready();
}
float AW_CombatBlockShown(void) {
    float left=block_shown_until-(float)sv.time;
    return sv.active && left>0 && left<10?left:0;
}
static void alt_down(void) {
    if(AW_PlayerDead())return;
    if(AW_CompanionPickAim())return;
    guard_key=1;
    if(!block_cvar.value || !player())return;
    if(!shield_ready()){if(readout.value)Con_Printf("Combat: no shield to block with (a shield and a one-handed weapon or none)\n");}
    else{totals.guards++;if(readout.value && AW_CombatHostiles())Con_Printf("Combat: you raise your shield\n");}
}
static void alt_up(void) {guard_key=0;}
/* No swing while guarding (release the block button to attack). */
static int guard_buttons(int bits) {return AW_CombatGuarding()?bits&~1:bits;}
/* dbg combat loadout NAME: a test loadout of arena/player.txt for fights in the
 * world (the arena sets its own); "off" = the character again. */
static aw_fighter_t world_loadout;
static void loadout_command(char *name) {
    char used[24];
    if(!Q_strcasecmp(name,"off")){
        if(aw_combat_player_preset==&world_loadout)aw_combat_player_preset=NULL;
        you_valid=0;Con_Printf("Combat loadout off: you fight as your character.\n");return;
    }
    if(!AW_CombatLoadout(name,&world_loadout,used)){Con_Printf("No loadout %s in arena/player.txt (config/arena_player.json).\n",name);return;}
    aw_combat_player_preset=&world_loadout;you_valid=0;
    Con_Printf("Combat loadout %s: %s, level %ld (test sheet; \"dbg combat loadout off\" ends it).\n",used,world_loadout.name,(long)world_loadout.level);
}
static void command(void) {
    char *a=Cmd_Argv(1);int on;
    if(Cmd_Argc()==1){report();return;}
    if(!Q_strcasecmp(a,"loadout") && Cmd_Argc()==3){loadout_command(Cmd_Argv(2));return;}
    /* dbg combat resistnormal N|off (RESIST-NORMAL-WEAPONS-61, test only, not saved): every target resists normal
     * weapons by N % (0..1000); off = the targets' own effects again */
    if(!Q_strcasecmp(a,"resistnormal") && Cmd_Argc()<=3){
        if(Cmd_Argc()==3)resist_test=!Q_strcasecmp(Cmd_Argv(2),"off")?-1:Q_atof(Cmd_Argv(2));
        if(resist_test<0)resist_test=-1;
        if(resist_test>1000)resist_test=1000;
        if(resist_test>=0)Con_Printf("Resist normal weapons: every target %.0f %% (test only)",resist_test);
        else Con_Printf("Resist normal weapons: the targets' own effects");
        Con_Printf("; effect list %s; text %s\n",aw_combat_effect_magnitude?"connected":"not connected",
                   resist_text[0]?resist_text:"(none in this image)");
        return;
    }
    if(!Q_strcasecmp(a,"seed") && Cmd_Argc()<=3){
        if(Cmd_Argc()==3)Cvar_SetValue(seed_cvar.name,Q_atof(Cmd_Argv(2)));
        Con_Printf("Combat seed %ld (0: a new seed per encounter); last used %lu\n",(long)seed_cvar.value,seed_used);return;
    }
    if(!Q_strcasecmp(a,"readout") && Cmd_Argc()==3 && (on=AW_CompanionToggleWord(Cmd_Argv(2)))>=0){Cvar_SetValue(readout.name,(float)on);return;}
    if(!Q_strcasecmp(a,"music") && Cmd_Argc()==3 && (on=AW_CompanionToggleWord(Cmd_Argv(2)))>=0){Cvar_SetValue(music.name,(float)on);return;}
    if(Cmd_Argc()==3 && !Q_strcasecmp(a,"dice") && (on=AW_CompanionToggleWord(Cmd_Argv(2)))>=0){Cvar_SetValue(dice_cvar.name,(float)on);
        Con_Printf("Dice rolls %s.\n",on?"on (the original rolls)":"off (AmiWind extension: every swing in reach hits)");return;}
    if(Cmd_Argc()==3 && !Q_strcasecmp(a,"style")){
        if(!Q_strcasecmp(Cmd_Argv(2),"amiwind"))on=1;else if(!Q_strcasecmp(Cmd_Argv(2),"original"))on=0;else on=-1;
        if(on>=0){Cvar_SetValue(miss_cvar.name,(float)on);
            Con_Printf("Combat style: %s.\n",on?"AmiWind (a missed blow is dodged or blocked; AmiWind extension)":"Original Morrowind (the swish)");return;}
    }
    if(Cmd_Argc()==3 && !Q_strcasecmp(a,"block")){
        if(!Q_strcasecmp(Cmd_Argv(2),"hold"))on=1;else if(!Q_strcasecmp(Cmd_Argv(2),"auto") || !Q_strcasecmp(Cmd_Argv(2),"original"))on=0;else on=-1;
        if(on>=0){Cvar_SetValue(block_cvar.name,(float)on);
            Con_Printf("Blocking: %s.\n",on?"hold the block button (AmiWind extension; the original formula decides each blow)":"automatic (Original Morrowind)");return;}
    }
    if(Cmd_Argc()==3 && !Q_strcasecmp(a,"flee") && (on=AW_CompanionToggleWord(Cmd_Argv(2)))>=0){AW_CombatRule(AW_RULE_FLEE,on);
        Con_Printf("Flee by the Flee rating %s.\n",on?"on (OpenMW makeFleeDecision)":"off (only an unreachable player makes a fighter flee)");return;}
    if(Cmd_Argc()==3 && !Q_strcasecmp(a,"sounds") && (on=AW_CompanionToggleWord(Cmd_Argv(2)))>=0){AW_CombatRule(AW_RULE_SOUNDS,on);
        Con_Printf("Combat sounds: %s.\n",on?"as OpenMW plays them (swing, armour hit, miss for your swings, two punches)":"one sound per outcome (the earlier set)");return;}
    if(Cmd_Argc()==3 && !Q_strcasecmp(a,"bestattack") && (on=AW_CompanionToggleWord(Cmd_Argv(2)))>=0){Cvar_SetValue(best_cvar.name,(float)on);
        Con_Printf("Always use best attack: %s (Options > Prefs shows the same setting).\n",on?"on (the weapon's strongest attack)":"off (the attack follows your movement)");return;}
    if(Cmd_Argc()==3 && !Q_strcasecmp(a,"contact") && (on=AW_CompanionToggleWord(Cmd_Argv(2)))>=0){AW_CombatRule(AW_RULE_CONTACT,on);
        Con_Printf("Hit contact: %s.\n",on?"the original's hit cone when the crosshair misses (OpenMW getHitContact)":"the crosshair's ray only (the earlier rule)");return;}
    if(Cmd_Argc()==3 && !Q_strcasecmp(a,"spells") && (on=AW_CompanionToggleWord(Cmd_Argv(2)))>=0){AW_CombatRule(AW_RULE_SPELLS,on);
        Con_Printf("Fighters' spells: %s.\n",on?"each fighter weighs its spells against its weapon and casts the best (OpenMW prepareNextAction)":"weapons and fists only (the earlier rule)");return;}
    if(!Q_strcasecmp(a,"calm") && Cmd_Argc()==2){AW_CombatClear();if(battle){battle=0;AW_MusicCombat(0);}Con_Printf("Combat: everyone calms down.\n");return;}
    if((on=AW_CompanionToggleWord(a))>=0 && Cmd_Argc()==2){Cvar_SetValue(combat_on.name,(float)on);if(!on)AW_CombatClear();return;}
    Con_Printf("Usage: dbg combat [on/off | seed N | readout on/off | music on/off | dice on/off | style amiwind/original | block hold/auto | flee on/off | sounds on/off | bestattack on/off | contact on/off | spells on/off | loadout NAME/off | calm]\n");
}
void AW_CombatInit(void) {
    Cvar_RegisterVariable(&combat_on);Cvar_RegisterVariable(&readout);Cvar_RegisterVariable(&music);
    Cvar_RegisterVariable(&seed_cvar);Cvar_RegisterVariable(&punch_hit);Cvar_RegisterVariable(&think_interval);
    Cvar_RegisterVariable(&chase_speed);
    Cvar_RegisterVariable(&miss_cvar);Cvar_RegisterVariable(&dice_cvar);Cvar_RegisterVariable(&best_cvar);
    Cvar_RegisterVariable(&block_cvar);aw_combat_buttons=guard_buttons;aw_combat_guard_marker=AW_CombatGuarding;
    aw_combat_input_locked=player_locked;
    Cmd_AddCommand("aw_combat_cmd",command);   /* not "aw_combat": the cvar of that name would shadow it (CONSOLE-COMMAND-SHADOWED-BY-CVAR-36) */
    Cmd_AddCommand("+aw_alt",alt_down);Cmd_AddCommand("-aw_alt",alt_up);
    aw_combat_enemy_bar=AW_CombatEnemyBar;aw_combat_scene=AW_CombatSceneSpawn;
    {extern float (*aw_worldui_armor_rating)(void);aw_worldui_armor_rating=AW_CombatPlayerArmorRating;}
    {extern void (*aw_defaults_migrate)(int level);aw_defaults_migrate=AW_CombatDefaultsMigrate;}
}
/* BEST-ATTACK-OPTION-62: run once for a saved configuration of defaults level LEVEL (aw_fog.c horizon_migrate, after
 * config.cfg): before level 2 the configuration holds "Always use best attack" at the old default 0, which no menu
 * offered, so it takes the new default 1; a choice made after that stays. */
void AW_CombatDefaultsMigrate(int level) {
    if(level<2)Cvar_SetValue(best_cvar.name,1);
}

#include "aw_actors.h"
/* PROTOTYPE (branch v0.0.46-type1-stateful, aw_actors.c): the window's
 * stateful actors ask a resident's combat state, start a fight with the
 * nearest one for a test, and let a dead one's slot go before it is freed. */
int AW_CombatSlotState(edict_t *e,float *health) {
    slot_t *s=slot_of(e);
    if(!s)return 0;
    if(health)*health=s->f.health;
    return s->f.dead?2:1;
}
int AW_CombatTestEngage(edict_t *t,int dead) {
    slot_t *s=slot_of(t);char id[32];aw_fighter_t sheet;eval_t *v;
    if(!s){
        v=GetEdictFieldValue(t,"aw_source_id");
        if(!v || !v->string || !*(pr_strings+v->string))return 0;
        strncpy(id,pr_strings+v->string,sizeof(id)-1);id[sizeof(id)-1]=0;
        {int ok;engage_dead=dead?1:0;ok=AW_CombatActorLoad(id,&sheet) && AW_CombatEngage(t,&sheet,NULL);engage_dead=0;
         if(!ok)return 0;}
        s=slot_of(t);if(!s)return 0;
    }
    /* a corpse as the fight leaves one (combat_hit: not solid; the aim test finds it by its model's bounds) */
    if(dead){s->f.dead=1;s->f.health=0;set_state(s,S_DEAD,G_DEATH);s->e->v.solid=SOLID_NOT;
        if(s->rolled && s->e->v.angles[2]!=90){s->e->v.angles[2]=90;s->e->v.origin[2]+=2;}   /* stand-in: lie down */
        SV_LinkEdict(s->e,false);
        if(aw_combat_actor_died)aw_combat_actor_died(s->e);   /* on the change list at once, as a fight's death */
        if(!lay_saved)essential_death(s->e);   /* a saved death laid down again is not a new death */
    }
    return 1;
}
/* OUTDOOR-DEAD-BODY-GONE-66: a saved death laid down again (a room's, the home map's or a joining cell's body, aw_actors.c):
 * the corpse as AW_CombatTestEngage(t,1) leaves one, without the essential message a new death shows */
int AW_CombatLayCorpse(edict_t *t) {
    int ok;lay_saved=1;ok=AW_CombatTestEngage(t,1);lay_saved=0;return ok;
}
/* PLAYER-CASTING-59 (aw_mwhost.c AW_MwscriptLand): a spell's effects changed an actor's health to HEALTH. A harmful
 * spell is an attack: an actor not yet fighting joins the fight with the player (OpenMW spellcasting.cpp inflict,
 * the player's harmful spell on a living actor shows its health bar and counts as an attack). Under 1 it dies as by a
 * blow (AW_ACTOR_HEALTH_DEAD, MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66). 1 when the actor has a fight slot. */
int AW_CombatSpellHit(edict_t *e,float health,int harmful) {
    slot_t *s;int dead=AW_ACTOR_HEALTH_DEAD(health);
    if(!e || e->free)return 0;
    s=slot_of(e);
    if(!s){
        eval_t *v=GetEdictFieldValue(e,"aw_source_id");aw_fighter_t sheet;
        if(!harmful || !v || !v->string || !*(pr_strings+v->string))return 0;
        if(aw_combat_assault)aw_combat_assault(e);   /* CRIME-59: the player's harmful spell is an attack too */
        if(aw_combat_attacked)aw_combat_attacked(e);  /* GetAttacked (MWSCRIPT-GAPS-63) */
        if(!(s=slot_of(e)) && (!AW_CombatActorLoad(pr_strings+v->string,&sheet) || !AW_CombatEngage(e,&sheet,NULL) ||
                               !(s=slot_of(e))))return 0;
    }
    if(s->f.dead)return 1;
    if(harmful){enemy=e;enemy_until=(float)sv.time+aw_combat_settings.fNPCHealthBarTime;}
    s->f.health=!dead && health>0?health:0;
    if(dead){
        s->f.dead=1;
        set_state(s,S_DEAD,G_DEATH);s->e->v.solid=SOLID_NOT;SV_LinkEdict(s->e,false);sound(SND_FALL);
        if(s->rolled){s->e->v.angles[2]=90;s->e->v.origin[2]+=2;}           /* stand-in: lie down */
        if(aw_combat_actor_died)aw_combat_actor_died(s->e);
        essential_death(s->e);
        if(readout.value)Con_Printf("Combat: %s is dead\n",s->f.name);
        voice(s->e,AW_VOICE_DEATH);
        if(harmful && aw_combat_killed)aw_combat_killed(s->e);   /* CRIME-59: the player's spell killed it */
        if(harmful && aw_combat_player_kill)aw_combat_player_kill(s->e);   /* GetWerewolfKills (MWSCRIPT-GAPS-63) */
        if(!AW_CombatHostiles())ended(1);
    }
    return 1;
}
/* aw_actors.c: a resumed fight keeps the health the save or the change list held. */
int AW_CombatSetHealth(edict_t *e,float health) {slot_t *s=slot_of(e);if(!s || !(health>0))return 0;s->f.health=health;return 1;}
void AW_CombatForget(edict_t *e) {slot_t *s=slot_of(e);if(s)release(s);if(enemy==e)enemy=NULL;}
