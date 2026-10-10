/* SPDX-License-Identifier: GPL-2.0-or-later
 * Character animation kit, engine side: layout parsing, group choice by
 * speed, frame stepping and footstep events (aw_anim.h, docs/ANIMATION.md).
 *
 * Group choice follows the original engine (OpenMW CharacterController):
 * swimming in water, else walk or run; the playback rate is the actor's
 * speed over the group's own speed (the root bone's motion the builder
 * removed), so feet do not slide. Walk or run is chosen by the nearer own
 * speed because the actors here have no run flag (an AmiWind adaptation).
 * The pure part below has no engine dependencies (host-tested).
 */
#include <string.h>
#include "aw_anim.h"
#include "aw_animkit.h"

/* dbg animkit (aw_animkit.c): 0 = movers play their idle frames (the previous method); a playback
 * rate multiplier. Defaults: the kit on, rate x1. */
int aw_anim_kit_enabled=1;
float aw_anim_kit_speed=1;
const char *const aw_anim_group_names[AW_ANIM_GROUPS]={"idle","walk","run","swim","swimidle","hit","knock","death","attack","block","dodgel","dodger"};
static const char *const event_names[AW_ANIM_EVENT_KINDS]={"left","right"};
static const char *const voice_topics[AW_VOICE_TOPICS]={"attack","hit","flee","idle"};
static int hexval(int c) {return c>='0' && c<='9'?c-'0':c>='a' && c<='f'?c-'a'+10:-1;}

/* The previous layouts: 8 idle frames; the 21-frame town actor (walk 13..20). */
void AW_AnimDefault(aw_anim_t *a,int numframes) {
    memset(a,0,sizeof(*a));
    a->g[AW_ANIM_IDLE].count=(unsigned char)(numframes>=8?8:1);a->g[AW_ANIM_IDLE].step=.15f;a->g[AW_ANIM_IDLE].present=1;
    if(numframes==21){
        a->g[AW_ANIM_WALK].base=13;a->g[AW_ANIM_WALK].count=8;a->g[AW_ANIM_WALK].step=.125f;a->g[AW_ANIM_WALK].present=1;
    }
}

static int number(const char **p,float *out) {
    const char *s=*p;long whole=0;float frac=0,scale=.1f;int digits=0,neg=0;
    if(*s=='-'){neg=1;s++;}
    while(*s>='0' && *s<='9'){if(whole<1000000)whole=whole*10+(*s-'0');s++;digits++;}
    if(*s=='.'){s++;while(*s>='0' && *s<='9'){frac+=(*s-'0')*scale;scale*=.1f;s++;digits++;}}
    if(!digits)return 0;
    *out=(float)whole+frac;if(neg)*out=-*out;*p=s;return 1;
}
static int name_of(const char **p,const char *const *names,int count) {
    int i;size_t n;
    for(i=0;i<count;i++){n=strlen(names[i]);if(!strncmp(*p,names[i],n) && (*p)[n]==':'){*p+=n+1;return i;}}
    return -1;
}
static int word_end(const char *p) {return !*p || *p==' ' || *p=='\n' || *p=='\r' || *p=='\t';}

/* 1 = parsed (unknown words are skipped, as the combat reader skips ours);
 * 0 = invalid: *a holds the default layout. */
int AW_AnimParse(aw_anim_t *a,const char *p,int numframes) {
    float v[5];int g,k,i,n;
    AW_AnimDefault(a,numframes);
    if(!p)return 0;
    {aw_anim_t t;memset(&t,0,sizeof(t));
    while(*p){
        while(*p==' ' || *p=='\n' || *p=='\r' || *p=='\t')p++;
        if(!*p)break;
        if(*p=='@'){
            p++;
            if((g=name_of(&p,aw_anim_group_names,AW_ANIM_GROUPS))<0 || !number(&p,v) || *p++!=':')goto skip;
            for(k=0;k<AW_ANIM_EVENT_KINDS;k++){size_t n2=strlen(event_names[k]);if(!strncmp(p,event_names[k],n2) && word_end(p+n2)){p+=n2;break;}}
            if(k==AW_ANIM_EVENT_KINDS)goto skip;
            if(t.events<AW_ANIM_EVENTS && v[0]>=0 && v[0]<256){
                t.ev_group[t.events]=(unsigned char)g;t.ev_offset[t.events]=(unsigned char)v[0];t.ev_kind[t.events]=(unsigned char)k;t.events++;
            }
            continue;
        }
        if(*p=='!'){
            aw_voice_line_t line;int k2,h;
            p++;memset(&line,0,sizeof(line));
            if((k=name_of(&p,voice_topics,AW_VOICE_TOPICS))<0)goto skip;
            for(i=0;i<16;i++){if((h=hexval(p[i]))<0)break;if(i&1)line.hash[i>>1]|=(unsigned char)h;else line.hash[i>>1]=(unsigned char)(h<<4);}
            if(i<16)goto skip;
            p+=16;
            for(k2=0;k2<2 && *p==':';k2++){
                p++;
                if((p[0]!='h' && p[0]!='p' && p[0]!='r') || !strchr("=!>g<l",p[1]) || !p[1])goto skip;
                line.kind[k2]=p[0];line.op[k2]=p[1];p+=2;
                if(!number(&p,v))goto skip;
                {int iv=(int)v[0];line.value[k2]=(short)iv;}
            }
            if(!word_end(p))goto skip;
            if(t.voices[k]<AW_VOICE_LINES)t.voice[k][t.voices[k]++]=line;
            continue;
        }
        if(*p=='>'){
            for(p++,n=0;!word_end(p);p++)if(n<AW_ANIM_MOVER_NAME-1)t.mover[n++]=*p;
            t.mover[n]=0;
            if(n<5 || n>=AW_ANIM_MOVER_NAME-1 || strcmp(t.mover+n-4,".mdl"))t.mover[0]=0;
            continue;
        }
        if(*p=='~'){
            p++;
            if((k=name_of(&p,event_names,AW_ANIM_EVENT_KINDS))<0)goto skip;
            for(i=0;i<AW_ANIM_MEDIA;i++){
                for(n=0;*p && *p!=':' && !word_end(p);p++)if(n<AW_ANIM_SOUND_NAME-1)t.sound[k][i][n++]=*p;
                t.sound[k][i][n]=0;
                if(n>=AW_ANIM_SOUND_NAME-1)return 0;
                if(*p==':')p++;else break;
            }
            for(i++;i<AW_ANIM_MEDIA;i++)strcpy(t.sound[k][i],t.sound[k][i-1]);
            continue;
        }
        if((g=name_of(&p,aw_anim_group_names,AW_ANIM_GROUPS))<0)goto skip;
        for(n=0;n<4;n++){
            if(!number(&p,&v[n]))return 0;
            if(*p!=':')break;
            p++;
        }
        n++;
        if(n<3 || !word_end(p))return 0;
        if(v[0]<0 || v[1]<1 || v[0]+v[1]>numframes || !(v[2]>0 && v[2]<5) || v[1]>64)return 0;
        /* Integers first, then one store per field through a pointer: the 68040 build (gcc -O1, FPU)
         * stored every (short) float conversion into group 0 (measured in FS-UAE: idle base 11, hit 0,
         * death 0 for "idle:0 hit:8 death:11"; host builds were right). */
        {aw_anim_group_t *q=&t.g[g];int ib=(int)v[0],ic=(int)v[1];
         q->base=(short)ib;q->count=(unsigned char)ic;q->step=v[2];q->x=n>3?v[3]:0;q->present=1;}
        continue;
    skip:
        while(!word_end(p))p++;
    }
    if(!t.g[AW_ANIM_IDLE].present)return 0;
    for(i=0;i<t.events;i++)
        if(!t.g[t.ev_group[i]].present || t.ev_offset[i]>=t.g[t.ev_group[i]].count)return 0;
    t.from_layout=1;*a=t;}
    return 1;
}

int AW_AnimMoveGroup(const aw_anim_t *a,float speed,int swimming,float *rate) {
    int g;const aw_anim_group_t *w=&a->g[AW_ANIM_WALK],*r=&a->g[AW_ANIM_RUN];
    *rate=1;
    if(!AW_ANIMKIT || !aw_anim_kit_enabled)return AW_ANIM_IDLE;
    if(swimming){
        if(speed<1)return a->g[AW_ANIM_SWIMIDLE].present?AW_ANIM_SWIMIDLE:AW_ANIM_IDLE;
        g=a->g[AW_ANIM_SWIM].present?AW_ANIM_SWIM:w->present?AW_ANIM_WALK:AW_ANIM_IDLE;
    }else{
        if(speed<1 || !w->present)return AW_ANIM_IDLE;
        g=AW_ANIM_WALK;
        /* nearer own speed (OpenMW falls back from run to walk when run is missing) */
        if(r->present && r->x>0 && w->x>0 && speed>(w->x+r->x)*.5f)g=AW_ANIM_RUN;
    }
    if(g!=AW_ANIM_IDLE && a->g[g].x>0){
        *rate=speed/a->g[g].x;
        if(*rate<.25f)*rate=.25f;
        if(*rate>4)*rate=4;
    }
    *rate*=aw_anim_kit_speed;
    return g;
}

static int one_shot(int g) {return g==AW_ANIM_HIT || g==AW_ANIM_KNOCK || g==AW_ANIM_DEATH || g==AW_ANIM_ATTACK ||
    g==AW_ANIM_BLOCK || g==AW_ANIM_DODGEL || g==AW_ANIM_DODGER;}

int AW_AnimAdvance(const aw_anim_t *a,aw_anim_play_t *p,int group,float dt,float rate,unsigned long *crossed) {
    const aw_anim_group_t *g;int before,after,count,steps;
    if(group<0 || group>=AW_ANIM_GROUPS || !a->g[group].present)group=AW_ANIM_IDLE;
    g=&a->g[group];count=g->count;
    if(crossed)*crossed=0;
    if(p->group!=group){p->group=(unsigned char)group;p->phase=0;p->index=0;if(crossed)*crossed=1;}
    else{
        before=(int)p->phase;
        if(dt>0 && rate>0)p->phase+=dt*rate/g->step;
        if(one_shot(group) && p->phase>count-1)p->phase=(float)(count-1);
        steps=(int)p->phase-before;          /* frames entered, wraps included */
        while(p->phase>=count)p->phase-=count;
        after=(int)p->phase;
        if(crossed){
            if(steps>=count)*crossed=count>=32?0xffffffffUL:(1UL<<count)-1;
            else while(steps-->0){before=(before+1)%count;*crossed|=1UL<<before;}
        }
        p->index=(unsigned char)after;
    }
    return g->base+p->index;
}

int AW_AnimDone(const aw_anim_t *a,const aw_anim_play_t *p) {
    return one_shot(p->group) && p->index+1>=a->g[p->group].count;
}

static int holds(const aw_voice_line_t *l,int speaker,int player,int r) {
    int k,x,v;
    for(k=0;k<2 && l->kind[k];k++){
        x=l->kind[k]=='h'?speaker:l->kind[k]=='p'?player:r;v=l->value[k];
        switch(l->op[k]){
        case '=':if(!(x==v))return 0;break;
        case '!':if(!(x!=v))return 0;break;
        case '>':if(!(x>v))return 0;break;
        case 'g':if(!(x>=v))return 0;break;
        case '<':if(!(x<v))return 0;break;
        default:if(!(x<=v))return 0;break;
        }
    }
    return 1;
}
int AW_VoicePick(const aw_anim_t *a,int topic,int speaker_health,int player_health,int random100,int pick_random,int roll) {
    int i,n=0,ok[AW_VOICE_LINES];
    if(topic<0 || topic>=AW_VOICE_TOPICS)return -1;
    for(i=0;i<a->voices[topic];i++)
        if(holds(&a->voice[topic][i],speaker_health,player_health,random100)){
            if(!pick_random)return i;
            ok[n++]=i;
        }
    if(!n)return -1;
    if(roll<0)roll=-roll;
    return ok[roll%n];
}

void AW_AnimEvents(const aw_anim_t *a,int group,unsigned long crossed,void (*emit)(void *,int),void *context) {
    int i;
    for(i=0;i<a->events;i++)
        if(a->ev_group[i]==group && a->ev_offset[i]<32 && (crossed>>a->ev_offset[i]&1))emit(context,a->ev_kind[i]);
}

#ifndef AW_ANIM_HOST_TEST
#include "quakedef.h"
#include "aw_combat.h"

/* One parsed layout per model in use (by model index), reset per level. */
#define TABLE 64
static struct {model_t *model;aw_anim_t anim;int needed;} table[TABLE];   /* needed: frames the layout uses */
static int used;
static model_t *level_world;
static char names[TABLE*2][AW_ANIM_SOUND_NAME];    /* precache needs names that live through the level */
static int named;

static const char *precached(const char *name);
/* Mover models: registered by name at spawn (no load), loaded while worn. */
#define MOVERS 16
static char lazy[MOVERS][AW_ANIM_MOVER_NAME];
static int lazies;
static struct {edict_t *e;short base,mover;string_t model;} worn[MOVERS];
static cvar_t movers_on={"aw_npc_movers","1",true};
static void level_check(void) {
    if(level_world!=sv.worldmodel){
        level_world=sv.worldmodel;used=0;named=0;lazies=0;memset(table,0,sizeof(table));memset(worn,0,sizeof(worn));
    }
}
int AW_AnimLazy(const char *name) {
    int i;
    for(i=0;i<lazies;i++)if(!strcmp(lazy[i],name))return 1;
    return 0;
}
static int lazy_index(const char *name) {
    int i;
    for(i=1;i<MAX_MODELS && sv.model_precache[i];i++)if(!strcmp(sv.model_precache[i],name))return i;
    if(i>=MAX_MODELS || sv.state!=ss_loading || lazies>=MOVERS)return 0;
    strcpy(lazy[lazies],name);
    sv.model_precache[i]=lazy[lazies++];
    sv.models[i]=Mod_FindName(sv.model_precache[i]);   /* the name only: nothing is loaded */
    return i;
}
static void prep_layout(model_t *m,const char *path,int numframes) {
    char anm[MAX_QPATH+4];byte *text;int mark,k,i;size_t n=strlen(path);aw_anim_t *a;
    if(used>=TABLE)return;
    a=&table[used].anim;table[used++].model=m;
    if(n<5 || n>=sizeof(anm) || strcmp(path+n-4,".mdl")){AW_AnimDefault(a,numframes);return;}
    memcpy(anm,path,n-4);strcpy(anm+n-4,".anm");
    mark=Hunk_LowMark();
    text=COM_LoadHunkFile(anm);
    if(!text){AW_AnimDefault(a,numframes);Hunk_FreeToLowMark(mark);return;}
    if(!AW_AnimParse(a,(const char *)text,numframes))Con_Printf("Animation layout %s: invalid, idle only\n",anm);
    Hunk_FreeToLowMark(mark);
    {int g,n,k=used-1;table[k].needed=0;
     for(g=0;g<AW_ANIM_GROUPS;g++)if(a->g[g].present){n=(int)a->g[g].base+(int)a->g[g].count;if(n>table[k].needed)table[k].needed=n;}}
    for(k=0;k<AW_ANIM_EVENT_KINDS;k++)for(i=0;i<AW_ANIM_MEDIA;i++)
        if(a->sound[k][i][0] && !precached(a->sound[k][i]))a->sound[k][i][0]=0;
}
static const char *precached(const char *name) {
    int i;
    for(i=0;i<MAX_SOUNDS && sv.sound_precache[i];i++)if(!strcmp(sv.sound_precache[i],name))return sv.sound_precache[i];
    if(i>=MAX_SOUNDS || sv.state!=ss_loading || named>=TABLE*2)return NULL;   /* only spawn functions may precache */
    strcpy(names[named],name);sv.sound_precache[i]=names[named++];
    return sv.sound_precache[i];
}
static model_t *model_of(edict_t *e) {
    int i=(int)e->v.modelindex;
    return i>0 && i<MAX_MODELS?sv.models[i]:NULL;
}
static aw_anim_t *slot(model_t *m) {
    int i;
    for(i=0;i<used;i++)if(table[i].model==m)return &table[i].anim;
    return NULL;
}

void AW_AnimPrep(edict_t *e) {
    model_t *m,*mover;aw_anim_t *a;int i;
    level_check();
    if(!(m=model_of(e)) || slot(m) || used>=TABLE)return;
    prep_layout(m,m->name,m->numframes);
    if(!(a=slot(m)) || !a->mover[0])return;
    /* the mover's layout now (spawn time: its sounds are precached); its frames are checked when it loads */
    if(!(i=lazy_index(a->mover))){a->mover[0]=0;return;}
    mover=sv.models[i];
    if(mover && !slot(mover))prep_layout(mover,a->mover,256);
}

const aw_anim_t *AW_AnimOf(edict_t *e) {
    static aw_anim_t fallback;model_t *m=model_of(e);aw_anim_t *a;int g;
    level_check();
    if(m && (a=slot(m))){
        /* a mover layout was parsed before its model loaded: check it against the frames now */
        for(g=0;g<used;g++)
            if(table[g].model==m && m->numframes>0 && table[g].needed>m->numframes)
                {AW_AnimDefault(&fallback,m->numframes);return &fallback;}
        return a;
    }
    AW_AnimDefault(&fallback,m?m->numframes:1);
    return &fallback;
}

int AW_AnimMedium(edict_t *e) {
    vec3_t p;
    VectorCopy(e->v.origin,p);p[2]+=e->v.maxs[2]>0?e->v.maxs[2]*.6f:20;
    if(SV_PointContents(p)<=CONTENTS_WATER)return AW_ANIM_SWIMMING;
    VectorCopy(e->v.origin,p);p[2]+=2;
    return SV_PointContents(p)<=CONTENTS_WATER?AW_ANIM_WADE:AW_ANIM_DRY;
}

static cvar_t footsteps={"aw_npc_footsteps","1",true};
static cvar_t footstep_volume={"aw_npc_footstep_volume","0.6",true};
static struct {edict_t *e;const aw_anim_t *a;int medium;} emitting;
static void emit(void *context,int kind) {
    const char *name=emitting.a->sound[kind][emitting.medium];(void)context;
    /* channel 4: the body; the voice keeps channel 2 (aw_greet) */
    if(name[0])SV_StartSound(emitting.e,4,(char *)name,(int)(footstep_volume.value*255),2);
}
/* ---- voice barks ---- */
static cvar_t voices_on={"aw_npc_voices","1",true};
static cvar_t voice_pick={"aw_npc_voice_pick","0",true};     /* 0 first match (OpenMW), 1 random among matches (AmiWind option) */
#define SPEAKERS 32
static struct {edict_t *e;double until;} speaking[SPEAKERS];
static int health_percent(edict_t *e) {
    int h=AW_CombatHealthPercent(e);                          /* -1: not fighting, so unhurt */
    return h<0?100:h;
}
static int pool_has(const char *name) {
    FILE *f=NULL;int bytes=COM_FOpenFile((char *)name,&f);
    if(f)fclose(f);
    return bytes>=44;
}
static int voice_file(const aw_voice_line_t *l,char *out) {
    static const char hex[]="0123456789abcdef";int i;
    strcpy(out,"pool/a");
    for(i=0;i<8;i++){out[6+2*i]=hex[l->hash[i]>>4];out[7+2*i]=hex[l->hash[i]&15];}
    strcpy(out+22,".wav");
    return 1;
}
int AW_VoiceSay(edict_t *e,int topic,int odds) {
    const aw_anim_t *a;int k,free_slot=-1,line,player;char name[32];sfx_t *sfx;sfxcache_t *sc;double now=realtime;
    edict_t *p=svs.maxclients>0?EDICT_NUM(1):NULL;
    if(!e || e->free || !voices_on.value || cls.state!=ca_connected)return 0;
    if(odds<10000 && (rand()%10000)>=odds)return 0;
    if(topic==AW_VOICE_IDLE_LINE){                             /* OpenMW Actors::playIdleDialogue */
        vec3_t from,to,d;trace_t tr;
        if(!p || p->free)return 0;
        VectorSubtract(p->v.origin,e->v.origin,d);
        if(DotProduct(d,d)>750.0f*750.0f)return 0;
        VectorCopy(e->v.origin,from);from[2]+=27;VectorAdd(p->v.origin,p->v.view_ofs,to);
        tr=SV_Move(from,vec3_origin,vec3_origin,to,MOVE_NOMONSTERS,e);
        if(tr.fraction<1)return 0;
    }
    for(k=0;k<SPEAKERS;k++)if(speaking[k].e==e){
        if(speaking[k].until>now)return 0;                                   /* already speaking */
        free_slot=k;
    }
    for(k=0;free_slot<0 && k<SPEAKERS;k++)if(!speaking[k].e || speaking[k].until<=now)free_slot=k;
    if(free_slot<0)return 0;
    {model_t *m=model_of(e);if(m && !slot(m))AW_AnimPrep(e);}   /* spawned after the load (Arena fighters) */
    a=AW_AnimOf(e);
    player=p && !p->free && p->v.max_health>0?(int)(p->v.health*100/p->v.max_health):100;
    if((line=AW_VoicePick(a,topic,health_percent(e),player,rand()%101,voice_pick.value!=0,rand()))<0)return 0;
    voice_file(&a->voice[topic][line],name);
    {char path[40];strcpy(path,"sound/");strcat(path,name);
     if(!pool_has(path))return 0;}                      /* left out of this build's voice pool: silent */
    if(!(sfx=S_PrecacheSound(name)) || !(sc=S_LoadSound(sfx)))return 0;
    S_StartSound(NUM_FOR_EDICT(e),2,sfx,e->v.origin,1,1);    /* the voice channel (aw_greet uses 2 too) */
    speaking[free_slot].e=e;speaking[free_slot].until=now+(sc->speed>0?(double)sc->length/sc->speed:2);
    return 1;
}
/* aw_combat.c's hook: the original's rules (OpenMW): the fight starts = Attack, always
 * (MechanicsManager::startCombat); every new swing 10 % (iVoiceAttackOdds, AiCombat startAttackIfReady);
 * a health hit 30 % (iVoiceHitOdds, Npc::onHit); flight = Flee, always (AiCombat); death = Hit, always
 * (Actors::killDeadActors). */
static void combat_voice(edict_t *e,int event) {
    switch(event){
    case AW_VOICE_START:AW_VoiceSay(e,AW_VOICE_ATTACK_LINE,10000);break;
    case AW_VOICE_SWING:AW_VoiceSay(e,AW_VOICE_ATTACK_LINE,1000);break;
    case AW_VOICE_HIT:AW_VoiceSay(e,AW_VOICE_HIT_LINE,3000);break;
    case AW_VOICE_FLEE:AW_VoiceSay(e,AW_VOICE_FLEE_LINE,10000);break;
    case AW_VOICE_DEATH:{int k;for(k=0;k<SPEAKERS;k++)if(speaking[k].e==e)speaking[k].until=0;}
        AW_VoiceSay(e,AW_VOICE_HIT_LINE,10000);break;
    }
}
void AW_AnimInit(void) {
    Cvar_RegisterVariable(&footsteps);Cvar_RegisterVariable(&footstep_volume);Cvar_RegisterVariable(&movers_on);
    Cvar_RegisterVariable(&voices_on);Cvar_RegisterVariable(&voice_pick);
    aw_combat_voice=combat_voice;
}

static int worn_slot(edict_t *e) {int i;for(i=0;i<MOVERS;i++)if(worn[i].e==e)return i;return -1;}
int AW_AnimMoving(edict_t *e) {level_check();return e && worn_slot(e)>=0;}
int AW_AnimMover(edict_t *e,int on) {
    int i,k,index;const aw_anim_t *a;model_t *m;
    if(!e)return 0;
    level_check();
    k=worn_slot(e);
    if(on){
        if(k>=0 || !movers_on.value || e->free)return 0;
        a=AW_AnimOf(e);
        if(!a->mover[0])return 0;
        for(index=1;index<MAX_MODELS && sv.model_precache[index];index++)if(!strcmp(sv.model_precache[index],a->mover))break;
        if(index>=MAX_MODELS || !sv.model_precache[index]){Con_Printf("Mover %s: not registered\n",a->mover);return 0;}
        for(k=0;k<MOVERS && worn[k].e;k++);
        if(k==MOVERS){Con_Printf("Mover %s: %ld movers worn already\n",a->mover,(long)MOVERS);return 0;}
        m=Mod_ForName(sv.model_precache[index],false);       /* loads into the Cache (Mod_Extradata reloads it later if evicted) */
        if(!m || m->type!=mod_alias){Con_Printf("Mover %s: not loaded\n",a->mover);return 0;}
        sv.models[index]=m;
        worn[k].e=e;worn[k].base=(short)e->v.modelindex;worn[k].mover=(short)index;worn[k].model=e->v.model;
        e->v.modelindex=index;e->v.model=sv.model_precache[index]-pr_strings;
        return 1;
    }
    if(k<0)return 0;
    index=worn[k].mover;
    if(!e->free){e->v.modelindex=worn[k].base;e->v.model=worn[k].model;}
    memset(&worn[k],0,sizeof(worn[k]));
    for(i=0;i<MOVERS;i++)if(worn[i].e && worn[i].mover==index)return 1;
    m=sv.models[index];
    if(m && m->type==mod_alias && Cache_Check(&m->cache))Cache_Free(&m->cache);   /* the memory comes back at once */
    return 1;
}
void AW_AnimSaveSwap(int begin) {
    int k;short x;string_t s;
    for(k=0;k<MOVERS;k++){
        edict_t *e=worn[k].e;
        if(!e || e->free)continue;
        x=(short)e->v.modelindex;e->v.modelindex=worn[k].base;worn[k].base=x;
        s=e->v.model;e->v.model=worn[k].model;worn[k].model=s;
    }
    (void)begin;
}
void AW_AnimSounds(edict_t *e,const aw_anim_t *a,int group,unsigned long crossed,int medium) {
    if(!crossed || !footsteps.value || !a->events)return;
    emitting.e=e;emitting.a=a;emitting.medium=medium;
    AW_AnimEvents(a,group,crossed,emit,NULL);
}
#endif
