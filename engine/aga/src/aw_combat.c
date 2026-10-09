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
 * Cost per hostile NPC: one slot of about 300 bytes (no allocation), one think per
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
#include "aw_character.h"

#define SLOTS 4                 /* hostile NPCs at a time */
#define SCALE .25f              /* original units -> game units (tools/prepare_quake.py SCALE) */
#define STEP_UP 8.5f
enum {S_CHASE,S_SWING,S_HIT,S_KNOCK,S_DEAD,S_FLEE};
enum {G_IDLE,G_RUN,G_ATTACK,G_HIT,G_KNOCK,G_DEATH,G_COUNT};

typedef struct {
    edict_t *e;
    aw_fighter_t f;
    aw_path_t path;
    short base[G_COUNT];unsigned char count[G_COUNT];float step[G_COUNT];
    float hit_fraction;
    unsigned char state,attack,struck,group,rolled;      /* rolled: no death frames (stand-in) */
    float state_time,next_think,last_think,cooldown,strength,swing_time;
    float decide_at;            /* unreachable player: flee, re-decide at this time */
    func_t think;float nextthink;
} slot_t;

aw_combat_settings_t aw_combat_settings;
static int settings_ok;
static char sound_path[9][32];
static const char *const sound_key[9]={"health","miss","punch","light","medium","heavy","swish","critical","fall"};
enum {SND_HEALTH,SND_MISS,SND_PUNCH,SND_LIGHT,SND_MEDIUM,SND_HEAVY,SND_SWISH,SND_CRITICAL,SND_FALL};

static slot_t slots[SLOTS];
static aw_fighter_t you;        /* the player's sheet while anything is hostile */
static int you_valid,battle,dead_music;
static aw_combat_rng_t rng;
static unsigned long seed_used,encounters;
static float punch_started=-1;static int punch_struck;
static edict_t *enemy;static float enemy_until;
static aw_combat_stats_t totals;
static struct {unsigned long thinks,swings,traces;double seconds,max;} cost;

static cvar_t combat_on={"aw_combat","1"};
static cvar_t readout={"aw_combat_readout","1"};
static cvar_t music={"aw_combat_music","1"};
static cvar_t seed_cvar={"aw_combat_seed","0"};
static cvar_t punch_hit={"aw_combat_punch_hit","0.71"};
static cvar_t think_interval={"aw_combat_think","0.1"};
static cvar_t chase_speed={"aw_combat_speed","200"};

extern unsigned long aw_sv_move_calls;
void (*aw_combat_result)(int won);   /* aw_arena.c: an encounter ended */
static int watching;                 /* the attack button was pressed: follow the punch */

/* ---- data files ---- */
static int read_line(FILE *f,char *line,int size) {
    if(!fgets(line,size,f))return 0;
    line[strcspn(line,"\r\n")]=0;return 1;
}
int AW_CombatSettingsLoad(void) {
    FILE *f=NULL;char line[128],name[64],path[64];float value;int i,n=0;
    if(settings_ok)return 1;
    memset(&aw_combat_settings,0,sizeof(aw_combat_settings));memset(sound_path,0,sizeof(sound_path));
    if(COM_FOpenFile("combat/settings.txt",&f)<0 || !f)return 0;
    if(!read_line(f,line,sizeof(line)) || strcmp(line,"AWCS1")){fclose(f);return 0;}
    while(read_line(f,line,sizeof(line))){
        if(Q_sscanf(line,"sound %63s %63s",name,path)==2){
            for(i=0;i<9;i++)if(!strcmp(name,sound_key[i]) && strlen(path)<sizeof(sound_path[i]) && !strstr(path,".."))strcpy(sound_path[i],path);
            continue;
        }
        if(Q_sscanf(line,"%63s %f",name,&value)==2 && AW_CombatSettingSet(&aw_combat_settings,name,value))n++;
    }
    fclose(f);
    settings_ok=n==AW_COMBAT_SETTING_COUNT;
    if(!settings_ok)Con_Printf("Combat settings incomplete (%ld of %ld); rebuild the image.\n",(long)n,(long)AW_COMBAT_SETTING_COUNT);
    return settings_ok;
}
/* One row of combat/actors.txt (tools/prepare_combat.py write_actors). */
static int parse_actor(char *line,aw_fighter_t *o) {
    char *field[10],*s=line;int i,v[27],n;float a,b,c,d;
    for(i=0;i<10;i++){field[i]=s;s=strchr(s,'\t');if(i<9){if(!s)return 0;*s++=0;}}
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
    return o->health_max>0;
}
static void lower(const char *in,char *out,int size) {
    int i;for(i=0;i<size-1 && in[i];i++)out[i]=(in[i]>='A' && in[i]<='Z')?in[i]+32:in[i];out[i]=0;
}
int AW_CombatActorLoad(const char *id,aw_fighter_t *out) {
    FILE *f=NULL;char line[512],want[32],*tab;long data,offset[27];int total,i,b,cmp;
    lower(id,want,sizeof(want));
    if(!want[0] || COM_FOpenFile("combat/actors.txt",&f)<0 || !f)return 0;
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
    fclose(f);return 0;
}
/* The player: the character sheet and the live health. Hand to hand, no
 * armour worn (all slots unarmoured), no shield. */
void AW_CombatPlayerSheet(aw_fighter_t *o) {
    edict_t *p=sv.active && svs.clients?svs.clients[0].edict:NULL;int i;
    memset(o,0,sizeof(*o));strcpy(o->id,"player");strcpy(o->name,"You");o->aware=1;
    for(i=0;i<8;i++){int v=aw_character.valid?aw_character.attributes[i]:50;o->attributes[i]=(unsigned char)(v<0?0:v>255?255:v);}
    for(i=0;i<27;i++){int v=aw_character.valid?aw_character.skills[i]:30;o->skills[i]=(unsigned char)(v<0?0:v>255?255:v);}
    o->level=(short)(aw_character.valid?aw_character.level:1);
    o->health_max=aw_character.valid && aw_character.maximum[0]>0?aw_character.maximum[0]:100;
    o->health=p?p->v.health:o->health_max;
    o->fatigue_max=aw_character.valid && aw_character.maximum[2]>0?aw_character.maximum[2]:
        (float)(o->attributes[AW_STR]+o->attributes[AW_WIL]+o->attributes[AW_AGI]+o->attributes[AW_END]);
    o->fatigue=aw_character.valid?aw_character.current[2]:o->fatigue_max;
    o->weapon_skill=AW_SK_H2H;
    o->armor=settings_ok?AW_CombatUnarmoredRating(&aw_combat_settings,o):0;
}
static void you_store(edict_t *p) {
    if(p)p->v.health=you.health;
    if(aw_character.valid){aw_character.current[0]=you.health;aw_character.current[2]=you.fatigue;}
}

/* ---- helpers ---- */
static edict_t *player(void) {
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict)return NULL;
    return svs.clients[0].edict;
}
static void sound(int which) {if(sound_path[which][0])S_LocalSound(sound_path[which]);}
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
static slot_t *slot_of(edict_t *e) {int i;for(i=0;i<SLOTS;i++)if(slots[i].e==e)return &slots[i];return NULL;}
static void print_swing(const char *who,const char *whom,int attack,const aw_swing_t *s) {
    static const char *outcome[]={"miss","BLOCKED","fatigue","HIT"},*type[]={"chop","slash","thrust"};
    if(!readout.value)return;
    if(s->roll<0){Con_Printf("Combat: %s swings at %s (already down)\n",who,whom);return;}
    Con_Printf("Combat: %s -> %s: chance %ld roll %ld %s%s",who,whom,(long)s->chance,(long)s->roll,outcome[s->outcome],
        s->critical?" CRITICAL":"");
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
    for(g=0;g<G_COUNT;g++){s->base[g]=0;s->count[g]=(unsigned char)(n>=8?8:1);s->step[g]=.15f;}
    if(n>=21){s->base[G_RUN]=13;s->count[G_RUN]=8;s->step[G_RUN]=.1f;}   /* town actor layout: walk 13..20 */
    s->hit_fraction=.5f;s->rolled=1;
}
/* "idle:0:4:0.6667 run:4:6:0.1556 attack:10:8:0.1500:0.667 ..." (fighters.txt) */
static int layout_parse(slot_t *s,const char *text) {
    static const char *names[G_COUNT]={"idle","run","attack","hit","knock","death"};
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
    if(got!=(1<<G_COUNT)-1)return 0;
    s->rolled=0;return 1;
}
static void animate(slot_t *s) {
    int g=s->group,i;float t=s->state_time;
    if(s->state==S_DEAD && s->rolled){s->e->v.frame=s->base[G_IDLE];return;}
    i=(int)(t/s->step[g]);
    if(g==G_IDLE || g==G_RUN)i%=s->count[g];
    else if(i>=s->count[g])i=s->count[g]-1;      /* one-shot groups hold the last frame */
    s->e->v.frame=s->base[g]+i;
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
static void release(slot_t *s) {
    if(s->e && !s->e->free && s->state!=S_DEAD){s->e->v.think=s->think;s->e->v.nextthink=s->nextthink>0?(float)sv.time+.1f:0;}
    memset(s,0,sizeof(*s));
}
int AW_CombatHostiles(void) {
    int i,n=0;
    for(i=0;i<SLOTS;i++)if(slots[i].e && !slots[i].e->free && !slots[i].f.dead)n++;
    return n;
}
static void begin_encounter(void) {
    unsigned long seed=(unsigned long)seed_cvar.value;
    /* 24 bits: exact in the float cvar, so a printed seed replays (aw_combat_seed). */
    if(!seed){seed=(0x41c64e6dUL^((encounters+1)*2654435761UL))&0xffffffUL;if(!seed)seed=1;}
    AW_CombatSeed(&rng,seed);seed_used=seed;encounters++;
    memset(&totals,0,sizeof(totals));totals.seed=seed;totals.started=sv.time;
    AW_CombatPlayerSheet(&you);you_valid=1;punch_started=-1;dead_music=0;
}
/* Make an NPC hostile to the player. fighter: its sheet; layout: frame
 * groups (fighters.txt) or NULL for the model's own frames. */
int AW_CombatEngage(edict_t *e,const aw_fighter_t *fighter,const char *layout) {
    slot_t *s=slot_of(e);int i;
    if(!combat_on.value || !e || e->free || !fighter || !AW_CombatSettingsLoad())return 0;
    if(!s){for(i=0;i<SLOTS && slots[i].e;i++);if(i==SLOTS){Con_Printf("Combat: %ld hostile NPCs already.\n",(long)SLOTS);return 0;}s=&slots[i];}
    if(!AW_CombatHostiles())begin_encounter();
    memset(s,0,sizeof(*s));s->e=e;s->f=*fighter;s->f.aware=1;
    s->think=e->v.think;s->nextthink=e->v.nextthink;e->v.nextthink=0;    /* its QuakeC idle stops */
    if(!layout || !layout_parse(s,layout))layout_default(s);
    AW_PathReset(&s->path,(int)floor(e->v.origin[0]),(int)floor(e->v.origin[1]));
    s->next_think=s->last_think=(float)sv.time;s->cooldown=.5f;
    set_state(s,S_CHASE,G_IDLE);
    if(readout.value)Con_Printf("Combat: %s (level %ld) attacks; seed %lu\n",s->f.name,(long)s->f.level,seed_used);
    return 1;
}
void AW_CombatClear(void) {int i;for(i=0;i<SLOTS;i++)if(slots[i].e)release(&slots[i]);enemy=NULL;you_valid=0;}
const aw_combat_stats_t *AW_CombatStats(void) {return &totals;}
unsigned long AW_CombatSeedUsed(void) {return seed_used;}
const aw_fighter_t *AW_CombatPlayer(void) {return you_valid?&you:NULL;}
const aw_fighter_t *AW_CombatFighter(edict_t *e) {slot_t *s=slot_of(e);return s?&s->f:NULL;}

static void ended(int won) {
    totals.ended=sv.time;totals.won=won;
    if(aw_combat_result)aw_combat_result(won);
}
/* The NPC struck at its hit key: resolve against the player. */
static void npc_strike(slot_t *s,edict_t *p) {
    aw_swing_t out;float dz,gap=gap_to(s->e,p,&dz),reach=AW_CombatReach(&aw_combat_settings,&s->f)*SCALE;
    you.health=p->v.health;
    if(gap>reach || dz>reach || dz<-reach || you.dead){
        s->f.fatigue-=aw_combat_settings.fFatigueAttackBase+(s->f.weapon?s->f.weight*s->strength*aw_combat_settings.fWeaponFatigueMult:0);
        totals.npc_swings++;totals.npc_misses++;
        if(readout.value)Con_Printf("Combat: %s swings, out of reach\n",s->f.name);
        return;
    }
    AW_CombatSwing(&aw_combat_settings,&s->f,&you,s->attack,s->strength,bearing(p,s->e,0),
        !(p->v.velocity[0] || p->v.velocity[1]),&rng,&out);
    totals.npc_swings++;cost.swings++;
    if(out.outcome<AW_HIT_FATIGUE){totals.npc_misses++;sound(out.outcome==AW_HIT_BLOCKED?SND_LIGHT:SND_SWISH);}
    else{
        totals.npc_hits++;
        if(out.outcome==AW_HIT_HEALTH){totals.taken_health+=out.damage;flash(out.damage);sound(SND_HEALTH);}
        else{totals.taken_fatigue+=out.damage;sound(SND_PUNCH);}
    }
    print_swing(s->f.name,"you",s->attack,&out);
    if(out.knockdown && you.knocked==1){
        totals.player_down_until=sv.time+2;
        if(readout.value)Con_Printf("Combat: you are knocked down\n");
    }
    you_store(p);
    if(you.dead){
        if(readout.value)Con_Printf("Combat: you have been killed by %s\n",s->f.name);
        sound(SND_FALL);ended(0);
    }
}
/* The player's punch reached its hit key: what is in reach takes it. */
static void player_strike(edict_t *p) {
    edict_t *t;slot_t *s;aw_swing_t out;float reach=AW_CombatReach(&aw_combat_settings,&you)*SCALE,dz;
    char id[32];aw_fighter_t sheet;int attack;
    you.health=p->v.health;
    t=AW_NPCTargetReach(p,p->v.v_angle,reach+16);       /* from the eye: plus the player's own half width */
    if(t && !(s=slot_of(t))){
        /* Any resident: hitting it starts a fight (OpenMW actorAttacked). */
        eval_t *v=GetEdictFieldValue(t,"aw_source_id");
        if(!v || !v->string || !*(pr_strings+v->string)){t=NULL;}
        else{
            strncpy(id,pr_strings+v->string,sizeof(id)-1);id[sizeof(id)-1]=0;
            if(!AW_CombatActorLoad(id,&sheet)){if(readout.value)Con_Printf("Combat: no combat sheet for %s\n",id);t=NULL;}
            else{sheet.aware=0;if(!AW_CombatEngage(t,&sheet,NULL))t=NULL;else if((s=slot_of(t)))s->f.aware=0;}
        }
    }
    s=t?slot_of(t):NULL;
    totals.player_swings++;
    if(!s || s->f.dead || gap_to(p,t,&dz)>reach){
        you.fatigue-=aw_combat_settings.fFatigueAttackBase;totals.player_misses++;you_store(p);
        if(s && !s->f.dead){enemy=t;enemy_until=(float)sv.time+aw_combat_settings.fNPCHealthBarTime;}
        return;
    }
    enemy=t;enemy_until=(float)sv.time+aw_combat_settings.fNPCHealthBarTime;   /* HUD::setEnemy: on every attempt in reach */
    attack=AW_CombatBestAttack(&you,&rng);
    AW_CombatSwing(&aw_combat_settings,&you,&s->f,attack,AW_CombatRoll01(&rng),bearing(t,p,90),!s->f.moving,&rng,&out);
    s->f.aware=1;cost.swings++;
    if(out.outcome<AW_HIT_FATIGUE){totals.player_misses++;sound(out.outcome==AW_HIT_BLOCKED?SND_LIGHT:SND_MISS);}
    else{
        totals.player_hits++;
        if(out.outcome==AW_HIT_HEALTH)totals.dealt_health+=out.damage;else totals.dealt_fatigue+=out.damage;
        sound(out.critical?SND_CRITICAL:out.outcome==AW_HIT_HEALTH?SND_HEALTH:SND_PUNCH);
    }
    print_swing("You",s->f.name,attack,&out);
    you_store(p);
    if(s->f.dead){
        set_state(s,S_DEAD,G_DEATH);s->e->v.solid=SOLID_NOT;SV_LinkEdict(s->e,false);sound(SND_FALL);
        if(s->rolled){s->e->v.angles[2]=90;s->e->v.origin[2]+=2;}           /* stand-in: lie down */
        if(readout.value)Con_Printf("Combat: %s is dead\n",s->f.name);
        if(!AW_CombatHostiles())ended(1);
    }else if(s->f.knocked && s->state!=S_KNOCK){set_state(s,S_KNOCK,G_KNOCK);sound(SND_FALL);}
    else if(out.outcome==AW_HIT_HEALTH && s->state!=S_KNOCK)set_state(s,S_HIT,G_HIT);   /* hit recovery */
}
/* The QuakeC punch (world.qc aw_hands_update state 3): strike once at the
 * hit key, aw_combat_punch_hit of the punch duration (the original
 * HandToHand chop: hit key at 0.67 s of a 0.93 s chop). */
static void watch_punch(edict_t *p) {
    float state=field(p,"aw_hand_state",0),started=field(p,"aw_hand_started",-1),length;
    watching=state==3 || p->v.button0;
    if(state!=3){punch_started=-1;return;}
    if(started!=punch_started){punch_started=started;punch_struck=0;}
    if(punch_struck)return;
    length=field(sv.edicts,"aw_hand_punch",.9f);
    if(sv.time<started+length*punch_hit.value)return;
    punch_struck=1;player_strike(p);
}

/* ---- the think ---- */
static void think(slot_t *s,edict_t *p,float dt) {
    int self[3],goal[3],heading,moved=0,step;float dz,gap,reach;aw_path_io_t io;unsigned long before;
    s->f.moving=0;s->f.attacking=s->state==S_SWING;
    if(AW_CombatRecover(&aw_combat_settings,&s->f,dt))set_state(s,S_CHASE,G_IDLE);
    if(s->state==S_DEAD)return;
    if(s->f.fatigue<0 && !s->f.knocked){s->f.knocked=2;set_state(s,S_KNOCK,G_KNOCK);sound(SND_FALL);}   /* knocked out */
    if(s->state==S_KNOCK){
        if(s->f.knocked==1 && s->state_time>=duration(s,G_KNOCK)+.5f){s->f.knocked=0;set_state(s,S_CHASE,G_IDLE);}
        return;
    }
    if(s->state==S_HIT){if(s->state_time>=duration(s,G_HIT))set_state(s,S_CHASE,G_IDLE);return;}
    if(you.dead){if(s->group!=G_IDLE)set_state(s,S_CHASE,G_IDLE);return;}
    /* Unreachable player (no path): flee, never warp, no combat timeout.
     * OpenMW 0.51 aicombat.cpp 295-339 and 363-467: with no route the actor
     * drops the attack and flees; without a pathgrid it runs directly away
     * for 1.0 s, then stands and watches; the decision is retaken every
     * 3.0 s, so it fights again as soon as the player is reachable. */
    if(s->state==S_FLEE){
        if(s->state_time<1.0f){
            vec3_t away;float len;int moved;
            away[0]=s->e->v.origin[0]-p->v.origin[0];away[1]=s->e->v.origin[1]-p->v.origin[1];away[2]=0;
            len=(float)AW_PathLength((int)away[0],(int)away[1]);if(len<1)len=1;
            VectorScale(away,chase_speed.value*dt/len,away);
            pass_player(1);moved=AW_ActorStep(s->e,away,host_frametime>0?host_frametime:dt);pass_player(0);
            s->e->v.angles[1]=AW_PathHeading((int)-away[0],(int)-away[1])*360.0f/AW_PATH_FAN+90;
            s->f.moving=(unsigned char)moved;s->group=moved?G_RUN:G_IDLE;
            return;
        }
        s->group=G_IDLE;face_player(s->e,p);
        if(sv.time<s->decide_at)return;
        AW_PathReset(&s->path,(int)floor(s->e->v.origin[0]),(int)floor(s->e->v.origin[1]));
        set_state(s,S_CHASE,G_IDLE);
    }
    face_player(s->e,p);
    if(s->state==S_SWING)return;                         /* strike and end: per frame */
    reach=AW_CombatReach(&aw_combat_settings,&s->f)*SCALE;
    gap=gap_to(s->e,p,&dz);
    if(s->cooldown>0)s->cooldown-=dt;
    if(gap<=reach*.8f && dz<reach && dz>-reach){
        if(s->group!=G_IDLE)set_state(s,S_CHASE,G_IDLE);
        AW_PathIdle(&s->path,(int)s->e->v.origin[0],(int)s->e->v.origin[1]);
        if(s->cooldown<=0){
            /* AiCombat: best attack, swing strength, then a cooldown */
            s->attack=(unsigned char)AW_CombatBestAttack(&s->f,&rng);s->strength=AW_CombatRoll01(&rng);
            s->struck=0;s->swing_time=duration(s,G_ATTACK)/(s->f.weapon && s->f.speed>0?s->f.speed:1);
            set_state(s,S_SWING,G_ATTACK);s->f.attacking=1;
        }
        return;
    }
    self[0]=(int)floor(s->e->v.origin[0]);self[1]=(int)floor(s->e->v.origin[1]);self[2]=(int)floor(s->e->v.origin[2]+s->e->v.mins[2]);
    goal[0]=(int)floor(p->v.origin[0]);goal[1]=(int)floor(p->v.origin[1]);goal[2]=(int)floor(p->v.origin[2]+p->v.mins[2]);
    step=(int)(chase_speed.value*dt);if(step>(int)(gap-reach*.6f))step=(int)(gap-reach*.6f);if(step<1)step=1;
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
    if(s->path.mode==AW_PATH_LOST){
        totals.npc_flees++;
        if(readout.value)Con_Printf("Combat: %s cannot reach you and flees\n",s->f.name);
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
    for(i=0;i<SLOTS;i++){
        slot_t *s=&slots[i];
        if(!s->e)continue;
        if(s->e->free){memset(s,0,sizeof(*s));continue;}
        any=1;s->state_time+=dt;
        if(s->state==S_SWING){
            if(!s->struck && s->state_time>=s->swing_time*s->hit_fraction){s->struck=1;if(!you.dead)npc_strike(s,p);}
            if(s->state_time>=s->swing_time){
                s->f.attacking=0;set_state(s,S_CHASE,G_IDLE);
                s->cooldown=aw_combat_settings.fCombatDelayNPC+.01f*AW_CombatRoll100(&rng);
                if(s->cooldown>aw_combat_settings.fCombatDelayNPC+.9f)s->cooldown=aw_combat_settings.fCombatDelayNPC+.9f;
            }
        }
        if(sv.time>=s->next_think){
            interval=think_interval.value<.05f?.05f:think_interval.value>.2f?.2f:think_interval.value;
            dt=(float)(sv.time-s->last_think);if(dt>.3f)dt=.3f;if(dt<0)dt=interval;
            s->last_think=(float)sv.time;s->next_think=(float)sv.time+interval;
            t0=Sys_FloatTime();think(s,p,dt);t0=Sys_FloatTime()-t0;
            cost.thinks++;cost.seconds+=t0;if(t0>cost.max)cost.max=t0;
            dt=(float)host_frametime;
        }
        if(s->state==S_SWING)s->group=G_ATTACK;
        animate(s);
    }
    /* The player: punch, fatigue return, the knockout clock. */
    if((watching || p->v.button0 || any) && !you_valid && AW_CombatSettingsLoad()){AW_CombatPlayerSheet(&you);you_valid=1;}
    if(you_valid){
        you.health=p->v.health;
        if(you.health<=0)you.dead=1;
        if(!you.dead){
            if(you.fatigue<0 && !you.knocked)you.knocked=2;
            if(AW_CombatRecover(&aw_combat_settings,&you,(float)host_frametime) && readout.value)Con_Printf("Combat: you get up\n");
            if(you.knocked==1 && sv.time>=totals.player_down_until)you.knocked=0;
            if(watching || p->v.button0)watch_punch(p);
            if(aw_character.valid)aw_character.current[2]=you.fatigue;
        }
        if(!any && !watching && you.fatigue>=you.fatigue_max)you_valid=0;
    }else if(aw_character.valid && aw_character.current[2]<aw_character.maximum[2] && settings_ok){
        /* No fight: the player's fatigue still returns (Actors::calculateRestoration). */
        aw_fighter_t f;AW_CombatPlayerSheet(&f);AW_CombatRecover(&aw_combat_settings,&f,(float)host_frametime);
        aw_character.current[2]=f.fatigue;
    }
    if(enemy && (enemy->free || sv.time>=enemy_until))enemy=NULL;
    /* Battle music while anyone fights the player (OpenMW music.lua:
     * the battle playlist is active while an actor has combat targets). */
    if(music.value){
        int want=AW_CombatHostiles()>0 && !you.dead;
        if(you_valid && you.dead){if(!dead_music){dead_music=1;AW_MusicDeath();}}
        else if(want!=battle){battle=want;AW_MusicCombat(want);}
    }
}
/* HUD::setEnemy / updateEnemyHealthBar: shown fNPCHealthBarTime seconds
 * after the player's last attempt in reach, fading over the last
 * fNPCHealthBarFade seconds. */
int AW_CombatEnemyBar(float *fraction,float *alpha) {
    slot_t *s;float left;
    if(!enemy || !(s=slot_of(enemy)) || !sv.active)return 0;
    left=enemy_until-(float)sv.time;if(left<0)return 0;
    *fraction=s->f.health_max>0?s->f.health/s->f.health_max:0;
    *alpha=aw_combat_settings.fNPCHealthBarFade>0?left/aw_combat_settings.fNPCHealthBarFade:1;
    if(*alpha>1)*alpha=1;
    return 1;
}
/* aw_scene.c: a new map; the old edicts are gone. */
void AW_CombatSceneSpawn(void) {
    int i;for(i=0;i<SLOTS;i++)memset(&slots[i],0,sizeof(slots[i]));
    enemy=NULL;you_valid=0;
    if(battle){battle=0;AW_MusicCombat(0);}
}

/* ---- dbg combat ---- */
static void report(void) {
    int i;double span=sv.time-totals.started;if(span<.001)span=.001;
    Con_Printf("Combat %s, readout %s, music %s, seed %lu (aw_combat_seed %ld)\n",combat_on.value?"on":"off",
        readout.value?"on":"off",music.value?"on":"off",seed_used,(long)seed_cvar.value);
    for(i=0;i<SLOTS;i++)if(slots[i].e)Con_Printf(" %s: health %ld/%ld fatigue %ld/%ld %s\n",slots[i].f.name,
        (long)slots[i].f.health,(long)slots[i].f.health_max,(long)slots[i].f.fatigue,(long)slots[i].f.fatigue_max,
        slots[i].f.dead?"dead":slots[i].f.knocked?"down":"fighting");
    if(you_valid)Con_Printf(" You: health %ld/%ld fatigue %ld/%ld\n",(long)you.health,(long)you.health_max,(long)you.fatigue,(long)you.fatigue_max);
    Con_Printf("thinks %lu (%.1f/s) swings %lu move traces %lu; ms/think avg %.3f max %.3f\n",cost.thinks,cost.thinks/span,
        cost.swings,cost.traces,cost.thinks?cost.seconds*1000/cost.thinks:0.0,cost.max*1000);
    Con_Printf("bytes: per hostile NPC %ld, all slots %ld, player sheet %ld; no allocation\n",(long)sizeof(slot_t),
        (long)sizeof(slots),(long)sizeof(you));
}
static void command(void) {
    char *a=Cmd_Argv(1);int on;
    if(Cmd_Argc()==1){report();return;}
    if(!Q_strcasecmp(a,"seed") && Cmd_Argc()<=3){
        if(Cmd_Argc()==3)Cvar_SetValue(seed_cvar.name,Q_atof(Cmd_Argv(2)));
        Con_Printf("Combat seed %ld (0: a new seed per encounter); last used %lu\n",(long)seed_cvar.value,seed_used);return;
    }
    if(!Q_strcasecmp(a,"readout") && Cmd_Argc()==3 && (on=AW_CompanionToggleWord(Cmd_Argv(2)))>=0){Cvar_SetValue(readout.name,(float)on);return;}
    if(!Q_strcasecmp(a,"music") && Cmd_Argc()==3 && (on=AW_CompanionToggleWord(Cmd_Argv(2)))>=0){Cvar_SetValue(music.name,(float)on);return;}
    if(!Q_strcasecmp(a,"calm") && Cmd_Argc()==2){AW_CombatClear();if(battle){battle=0;AW_MusicCombat(0);}Con_Printf("Combat: everyone calms down.\n");return;}
    if((on=AW_CompanionToggleWord(a))>=0 && Cmd_Argc()==2){Cvar_SetValue(combat_on.name,(float)on);if(!on)AW_CombatClear();return;}
    Con_Printf("Usage: dbg combat [on/off | seed N | readout on/off | music on/off | calm]\n");
}
void AW_CombatInit(void) {
    Cvar_RegisterVariable(&combat_on);Cvar_RegisterVariable(&readout);Cvar_RegisterVariable(&music);
    Cvar_RegisterVariable(&seed_cvar);Cvar_RegisterVariable(&punch_hit);Cvar_RegisterVariable(&think_interval);
    Cvar_RegisterVariable(&chase_speed);
    Cmd_AddCommand("aw_combat",command);
    aw_combat_enemy_bar=AW_CombatEnemyBar;aw_combat_scene=AW_CombatSceneSpawn;
}
