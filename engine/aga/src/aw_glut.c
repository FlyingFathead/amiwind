/* SPDX-License-Identifier: GPL-2.0-or-later
 * The NPC voice and greeting table, engine side (aw_glut.h; docs/NPC_VOICE_TABLE.md).
 *
 * The rule is the original's (OpenMW mwdialogue/filter.cpp Filter::search, DialogueManager::say and
 * startDialogue): a topic's INFO records in order, the first that passes is said. The builder
 * (tools/greeting_lut.py) decided every test that reads only the speaker's record; what is left are condition
 * records of 8 bytes (opcode, comparison, operand, value) tested here by one switch, no strings parsed and no
 * dialogue record walked. Quake mechanism: the sound goes out like the barks (aw_anim.c AW_VoicePlay, channel 2),
 * the line through the QC hello's centerprint or the dialogue subtitle.
 * The pure part has no engine dependencies (host-tested, tests/aga_glut_test.c).
 */
#include <string.h>
#include "aw_glut.h"

#define NONE16 0xFFFFu
#define NONE32 0xFFFFFFFFul
static unsigned rd16(const unsigned char *p) {return (unsigned)p[0]<<8|p[1];}
static unsigned long rd32(const unsigned char *p) {return (unsigned long)p[0]<<24|(unsigned long)p[1]<<16|(unsigned long)p[2]<<8|p[3];}
static float rdf(const unsigned char *p) {union {unsigned long u;float f;} v;v.u=rd32(p);return v.f;}
static long sx32(unsigned long u) {return u&0x80000000ul?-(long)(0xFFFFFFFFul-u)-1:(long)u;}
static long pad4(long n) {return (n+3)&~3L;}
static int lower(int c) {return c>='A' && c<='Z'?c+32:c;}
static const char *const known_topics[AW_GLUT_TOPICS]={"hello","idle","intruder","thief","hit","attack","flee",
    "alarm","greeting"};

/* The sound events (aw_glut.h; docs/COMBAT.md "Sound events"). Sources: OpenMW 0.51 mwmechanics/combat.cpp (swish,
 * miss, the armour piece struck, Health Damage, critical damage, Hand To Hand Hit, the shield's armour hit on a block),
 * character.cpp (bowPull/bowShoot, crossbowPull/crossbowShoot; a thrown weapon's release plays Weapon Swish; the
 * knockdown and death keys' Body Fall), projectile.cpp (a projectile striking an actor: its hit sounds),
 * spellcasting.cpp (the school's cast, hit and Spell Failure sounds), mwclass/npc.cpp and actors.cpp (the Voice
 * topics; the player's pain = his Hit line), mwclass/creature.cpp getSoundIdFromSndGen (a creature's attack plays the
 * roar key of its attack group). */
const aw_sound_event_t aw_sound_events[AW_SOUND_EVENTS]={
    {"hello",AW_SEK_VOICE,1,0,0,AW_GLUT_HELLO},{"idle",AW_SEK_VOICE,1,0,0,AW_GLUT_IDLE},
    {"intruder",AW_SEK_VOICE,1,0,0,AW_GLUT_INTRUDER},{"thief",AW_SEK_VOICE,1,0,0,AW_GLUT_THIEF},
    {"hit",AW_SEK_VOICE,1,0,0,AW_GLUT_HIT},{"attack",AW_SEK_VOICE,1,0,0,AW_GLUT_ATTACK},
    {"flee",AW_SEK_VOICE,1,0,0,AW_GLUT_FLEE},{"alarm",AW_SEK_VOICE,1,0,0,AW_GLUT_ALARM},
    {"pain",AW_SEK_PLAYER_VOICE,1,0,0,AW_GLUT_HIT},{"taunt",AW_SEK_VOICE,1,0,0,AW_GLUT_ATTACK},
    {"swish",AW_SEK_SLOT,1,0,0,AW_SLOT_WEAPON_SWISH},{"miss",AW_SEK_SLOT,1,0,0,AW_SLOT_MISS},
    {"armorhit",AW_SEK_SLOT,3,1,0,AW_SLOT_LIGHT_ARMOR_HIT},{"damage",AW_SEK_SLOT,1,0,0,AW_SLOT_HEALTH_DAMAGE},
    {"critical",AW_SEK_SLOT,1,0,0,AW_SLOT_CRITICAL_DAMAGE},{"block",AW_SEK_SLOT,3,1,0,AW_SLOT_LIGHT_ARMOR_HIT},
    {"punch",AW_SEK_SLOT,1,0,0,AW_SLOT_HAND_TO_HAND_HIT},{"punch2",AW_SEK_SLOT,1,0,0,AW_SLOT_HAND_TO_HAND_HIT_2},
    {"bowdraw",AW_SEK_SLOT,1,0,0,AW_SLOT_BOW_PULL},{"bowshoot",AW_SEK_SLOT,1,0,0,AW_SLOT_BOW_SHOOT},
    {"crossbowdraw",AW_SEK_SLOT,1,0,0,AW_SLOT_CROSSBOW_PULL},{"crossbowshoot",AW_SEK_SLOT,1,0,0,AW_SLOT_CROSSBOW_SHOOT},
    {"throw",AW_SEK_SLOT,1,0,0,AW_SLOT_WEAPON_SWISH},{"projectilehit",AW_SEK_SLOT,1,0,0,AW_SLOT_HEALTH_DAMAGE},
    {"cast",AW_SEK_SLOT,6,3,2,AW_SLOT_ALTERATION_CAST},{"spellhit",AW_SEK_SLOT,6,3,2,AW_SLOT_ALTERATION_HIT},
    {"spellfail",AW_SEK_SLOT,6,3,2,AW_SLOT_ALTERATION_FAIL},
    {"knockdown",AW_SEK_SLOT,3,1,1,AW_SLOT_BODY_FALL_SMALL},{"death",AW_SEK_SLOT,3,1,1,AW_SLOT_BODY_FALL_SMALL},
    {"creatureattack",AW_SEK_CREATURE,1,0,0,AW_SNDG_ROAR},{"roar",AW_SEK_CREATURE,1,0,0,AW_SNDG_ROAR},
    {"moan",AW_SEK_CREATURE,1,0,0,AW_SNDG_MOAN},{"scream",AW_SEK_CREATURE,1,0,0,AW_SNDG_SCREAM},
    {"land",AW_SEK_CREATURE,1,0,0,AW_SNDG_LAND}};
int AW_SoundEventFind(const char *name) {
    int i,k;
    if(!name)return -1;
    for(i=0;i<AW_SOUND_EVENTS;i++){
        const char *a=aw_sound_events[i].name;
        for(k=0;a[k] && lower((unsigned char)name[k])==a[k];k++);
        if(!a[k] && !name[k])return i;
    }
    return -1;
}
int AW_SoundEventResolve(int event,int arg,int *kind,int *index) {
    const aw_sound_event_t *s;
    if(event<0 || event>=AW_SOUND_EVENTS || !kind || !index)return 0;
    s=&aw_sound_events[event];
    if(arg<0)arg=s->deflt;
    if(arg>=s->args)arg=s->args-1;
    *kind=s->kind;*index=s->base+s->stride*arg;
    return 1;
}

long AW_GlutResidentSize(const unsigned char *h,long file_size) {
    long size;unsigned long texts;
    if(memcmp(h,"AWGL",4) || rd16(h+4)!=AW_GLUT_VERSION)return -1;
    texts=rd32(h+56);
    if(texts>(unsigned long)file_size)return -1;
    size=(long)(file_size-(long)texts);
    return size>AW_GLUT_HEADER?size:-1;
}

int AW_GlutOpen(aw_glut_t *g,const unsigned char *d,long size,long file_size) {
    long at=AW_GLUT_HEADER,i;int t,k;
    memset(g,0,sizeof(*g));
    if(size<AW_GLUT_HEADER || AW_GlutResidentSize(d,file_size)!=size)return 0;
    g->data=d;g->size=size;g->topics=(int)rd16(d+6);
    g->npcs=(long)rd32(d+8);g->sets=(long)rd32(d+12);g->listsets=(long)rd32(d+16);g->listset_items=(long)rd32(d+20);
    g->lists=(long)rd32(d+24);g->list_items=(long)rd32(d+28);g->entries=(long)rd32(d+32);g->conds=(long)rd32(d+36);
    g->sounds=(long)rd32(d+40);g->globals=(long)rd32(d+44);g->names=(long)rd32(d+48);g->string_bytes=(long)rd32(d+52);
    g->text_bytes=(long)rd32(d+56);g->functions=(int)rd16(d+64);
    g->creatures=(long)rd16(d+68);g->slots=(long)rd16(d+70);g->souns=(long)rd32(d+72);
    if(g->souns>0xFFFFL)return 0;
    if(g->topics<1 || g->topics>64 || g->functions>256 || g->slots<AW_SLOTS)return 0;
    /* each table in file order; every count is checked against the bytes before anything is read */
#define TAKE(field,bytes) do{long n_=(bytes);if(n_<0 || n_>size-at)return 0;g->field=d+at;at+=n_;}while(0)
    TAKE(topic_table,4L*g->topics);
    TAKE(fixture,4L*g->functions);
    TAKE(known,pad4((g->functions+7)/8));
    TAKE(npc,(long)AW_GLUT_NPC_ROW*g->npcs);
    TAKE(set,pad4(2L*g->topics*g->sets));
    TAKE(listset,8L*g->listsets);
    TAKE(listset_item,pad4(2L*g->listset_items));
    TAKE(list,8L*g->lists);
    TAKE(list_item,pad4(2L*g->list_items));
    TAKE(entry,12L*g->entries);
    TAKE(cond,8L*g->conds);
    TAKE(sound,(long)AW_GLUT_SOUND_ROW*g->sounds);
    TAKE(global,8L*g->globals);
    TAKE(name,4L*g->names);
    TAKE(creature,(long)AW_GLUT_CREATURE_ROW*g->creatures);
    TAKE(slot,pad4(2L*g->slots));
    TAKE(soun,(long)AW_GLUT_SOUN_ROW*g->souns);
    TAKE(strings,g->string_bytes);
#undef TAKE
    /* the string block ends in a NUL (its padding is zero), so every string offset below ends inside it */
    if(at!=size || !g->string_bytes || g->strings[g->string_bytes-1]!=0)return 0;
    g->text_base=size;
    /* every string offset and index the walk follows is bounded once here, so a pick never reads past the data */
    for(i=0;i<g->npcs;i++){
        const unsigned char *r=g->npc+AW_GLUT_NPC_ROW*i;
        if(rd32(r)>=(unsigned long)g->string_bytes || (long)rd16(r+8)>=g->sets)return 0;
        for(k=0;k<5;k++)if(rd16(r+10+2*k)!=NONE16 && (long)rd16(r+10+2*k)>=g->names)return 0;
    }
    for(i=0;i<g->sets*g->topics;i++)if(rd16(g->set+2*i)!=NONE16 && (long)rd16(g->set+2*i)>=g->listsets)return 0;
    for(i=0;i<g->listsets;i++){
        unsigned long first=rd32(g->listset+8*i);unsigned n=rd16(g->listset+8*i+4);
        if(!n || n>AW_GLUT_MAX_LISTS || first+n>(unsigned long)g->listset_items)return 0;
    }
    for(i=0;i<g->listset_items;i++)if((long)rd16(g->listset_item+2*i)>=g->lists)return 0;
    for(i=0;i<g->lists;i++){
        unsigned long first=rd32(g->list+8*i);unsigned n=rd16(g->list+8*i+4);
        if(!n || first+n>(unsigned long)g->list_items)return 0;
    }
    for(i=0;i<g->list_items;i++)if((long)rd16(g->list_item+2*i)>=g->entries)return 0;
    for(i=0;i<g->entries;i++){
        const unsigned char *e=g->entry+12*i;
        if(rd32(e)!=NONE32 && rd32(e)>=(unsigned long)g->text_bytes)return 0;
        if(rd32(e+4)+e[10]>(unsigned long)g->conds)return 0;
        if(rd16(e+8)!=NONE16 && (long)rd16(e+8)>=g->sounds)return 0;
    }
    for(i=0;i<g->names;i++)if(rd32(g->name+4*i)>=(unsigned long)g->string_bytes)return 0;
    for(i=0;i<g->creatures;i++){
        const unsigned char *r=g->creature+AW_GLUT_CREATURE_ROW*i;
        if(rd32(r)>=(unsigned long)g->string_bytes)return 0;
        for(k=0;k<AW_SNDG_MOMENTS;k++)if(rd16(r+4+2*k)!=NONE16 && (long)rd16(r+4+2*k)>=g->sounds)return 0;
    }
    for(i=0;i<g->slots;i++)if(rd16(g->slot+2*i)!=NONE16 && (long)rd16(g->slot+2*i)>=g->sounds)return 0;
    for(i=0;i<g->globals;i++)if(rd32(g->global+8*i)>=(unsigned long)g->string_bytes)return 0;
    for(i=0;i<g->topics;i++)if(rd32(g->topic_table+4*i)>=(unsigned long)g->string_bytes)return 0;
    for(t=0;t<AW_GLUT_TOPICS;t++){
        g->topic_of[t]=-1;
        for(k=0;k<g->topics;k++)if(!strcmp((const char *)g->strings+rd32(g->topic_table+4*k),known_topics[t])){g->topic_of[t]=k;break;}
    }
    return 1;
}

const char *AW_GlutId(const aw_glut_t *g,int npc) {
    return npc<0 || npc>=g->npcs?"":(const char *)g->strings+rd32(g->npc+AW_GLUT_NPC_ROW*npc);
}

/* ASCII case-insensitive order of the ids' bytes (the builder sorts the case-folded ids by their bytes). */
static int idcmp(const char *a,const char *b) {
    for(;;a++,b++){
        int x=lower((unsigned char)*a),y=lower((unsigned char)*b);
        if(x!=y || !x)return x-y;
    }
}
int AW_GlutFind(const aw_glut_t *g,const char *id) {
    long low=0,high=g->npcs-1;
    if(!g->data || !id || !*id)return -1;
    while(low<=high){
        long mid=(low+high)/2;int c=idcmp(id,AW_GlutId(g,(int)mid));
        if(!c)return (int)mid;
        if(c<0)high=mid-1;else low=mid+1;
    }
    return -1;
}
int AW_GlutHelloDistance(const aw_glut_t *g,int npc) {return npc<0 || npc>=g->npcs?0:(int)rd16(g->npc+AW_GLUT_NPC_ROW*npc+4);}
int AW_GlutResetDistance(const aw_glut_t *g) {return g->data?(int)rd16(g->data+60):0;}
int AW_GlutDuration(const aw_glut_t *g) {return g->data?(int)rd16(g->data+62):0;}

static int compare_int(long x,int c,long v) {
    switch(c&7){
    case 0:return x==v;
    case 1:return x!=v;
    case 2:return x>v;
    case 3:return x>=v;
    case 4:return x<v;
    default:return x<=v;
    }
}
static int compare_float(float x,int c,float v) {
    switch(c&7){
    case 0:return x==v;
    case 1:return x!=v;
    case 2:return x>v;
    case 3:return x>=v;
    case 4:return x<v;
    default:return x<=v;
    }
}
static const char *name_of(const aw_glut_t *g,unsigned index) {
    return index==NONE16 || (long)index>=g->names?NULL:(const char *)g->strings+rd32(g->name+4*index);
}
static const char *cond_name(const aw_glut_cond_t *c,unsigned index) {
    return index==NONE16 || (long)index>=c->names?NULL:(const char *)c->strings+rd32(c->name+4*index);
}
/* A function's value: the live ones from the engine, the rest the start-of-game fixture; 0 when not known. */
static int value(const aw_glut_cond_t *c,unsigned fn,const aw_glut_state_t *s,long *out) {
    switch(fn){
    case AW_GLUT_FN_HEALTH_PERCENT:*out=s->speaker_health_percent;return 1;
    case AW_GLUT_FN_PC_HEALTH_PERCENT:*out=s->player_health_percent;return 1;
    case AW_GLUT_FN_PC_HEALTH:*out=s->player_health;return 1;
    case AW_GLUT_FN_TALKED_TO_PC:*out=s->talked!=0;return 1;
    /* the player's rank in the speaker's faction (-1 not a member, the scripts' PCRaiseRank and friends keep it)
     * minus the speaker's; 0 for a factionless speaker */
    case AW_GLUT_FN_FACTION_RANK_DIFFERENCE:{
        long mine=-1;
        if(c->rank<0){*out=0;return 1;}
        if(c->faction && aw_glut_live && aw_glut_live->pc_rank && !aw_glut_live->pc_rank(c->faction,&mine))mine=-1;
        *out=mine-c->rank;return 1;}
    /* the pick of the open Choice (OpenMW filter.cpp: the dialogue's choice, -1 when none is open) */
    case AW_GLUT_FN_CHOICE:*out=c->choice;return 1;
    }
    if(aw_glut_live && aw_glut_live->function && aw_glut_live->function(c,fn,out))return 1;
    if((int)fn>=c->functions || !(c->known[fn>>3]>>(fn&7)&1))return 0;
    *out=sx32(rd32(c->fixture+4*fn));
    return 1;
}
const aw_glut_live_t *aw_glut_live;
static int starts_with(const char *text,const char *prefix) {
    for(;*prefix;text++,prefix++)if(lower((unsigned char)*text)!=lower((unsigned char)*prefix))return 0;
    return 1;
}
void AW_GlutCondOf(const aw_glut_t *g,int npc,aw_glut_cond_t *c) {
    memset(c,0,sizeof(*c));
    c->global=g->global;c->globals=g->globals;c->name=g->name;c->names=g->names;c->strings=g->strings;
    c->fixture=g->fixture;c->known=g->known;c->functions=g->functions;c->choice=-1;c->rank=-1;c->speaker=-1;
    if(npc<0 || npc>=g->npcs)return;
    c->rank=(signed char)g->npc[AW_GLUT_NPC_ROW*npc+7];
    c->disposition=g->npc[AW_GLUT_NPC_ROW*npc+6];
    c->cell=name_of(g,rd16(g->npc+AW_GLUT_NPC_ROW*npc+18));
}
int AW_GlutHolds(const aw_glut_t *g,int npc,const unsigned char *c,const aw_glut_state_t *s) {
    aw_glut_cond_t ctx;
    AW_GlutCondOf(g,npc,&ctx);
    return AW_GlutCond(&ctx,c,s);
}
int AW_GlutCond(const aw_glut_cond_t *g,const unsigned char *c,const aw_glut_state_t *s) {
    unsigned op=c[0],cmp=c[1],operand=rd16(c+2);unsigned long raw=rd32(c+4);long x;
    switch(op){
    case AW_GLUT_OP_FUNC:
        if(!value(g,operand,s,&x))return 0;
        return cmp&0x80?compare_float((float)x,cmp,rdf(c+4)):compare_int(x,cmp,sx32(raw));
    case AW_GLUT_OP_GLOBAL:{
        float v;
        if((long)operand>=g->globals)return 0;
        v=rdf(g->global+8*operand+4);
        if(aw_glut_live && aw_glut_live->global)aw_glut_live->global((const char *)g->strings+rd32(g->global+8*operand),&v);
        return compare_float(v,cmp,cmp&0x80?rdf(c+4):(float)sx32(raw));}
    case AW_GLUT_OP_RANDOM100:
        return cmp&0x80?compare_float((float)s->random100,cmp,rdf(c+4)):compare_int(s->random100,cmp,sx32(raw));
    case AW_GLUT_OP_JOURNAL:        /* the quest's journal index (the scripts' journal; 0 without it) */
    case AW_GLUT_OP_DEAD:{          /* an actor id's dead count (the actor record; 0 without it) */
        const char *name=cond_name(g,operand);long v=0;
        if(name && aw_glut_live){
            if(op==AW_GLUT_OP_JOURNAL && aw_glut_live->journal)aw_glut_live->journal(name,&v);
            if(op==AW_GLUT_OP_DEAD && aw_glut_live->dead)aw_glut_live->dead(name,&v);
        }
        return cmp&0x80?compare_float((float)v,cmp,rdf(c+4)):compare_int(v,cmp,sx32(raw));}
    case AW_GLUT_OP_LOCAL:          /* the speaker's script local (OpenMW: empty locals read 0) */
    case AW_GLUT_OP_NOTLOCAL:{
        float v=0;int holds;
        if(g->local_slots && aw_glut_live && aw_glut_live->local)
            aw_glut_live->local(g,(int)(operand&~AW_GLUT_LOCAL_FLOAT&0x3FFF),(operand&AW_GLUT_LOCAL_FLOAT)!=0,&v);
        holds=cmp&0x80?compare_float(v,cmp,rdf(c+4)):compare_int((long)v,cmp,sx32(raw));
        return op==AW_GLUT_OP_LOCAL?holds:!holds;}
    case AW_GLUT_OP_ITEM:{          /* the player's items: none counted yet; gold is not known (the builder's rule) */
        const char *item=cond_name(g,operand);long v=0;
        if(item && aw_glut_live && aw_glut_live->item && aw_glut_live->item(item,&v))
            return cmp&0x80?compare_float((float)v,cmp,rdf(c+4)):compare_int(v,cmp,sx32(raw));
        if(!item || !strcmp(item,"gold_001"))return 0;
        return compare_int(0,cmp,sx32(raw));
    }
    case AW_GLUT_OP_CELL:{          /* the NPC's home cell, a case-insensitive prefix (OpenMW ciStartsWith) */
        const char *cell=g->cell,*want=cond_name(g,operand);
        int match=cell && want && starts_with(cell,want);
        if(!cell)return 0;
        return raw?match:!match;
    }
    case AW_GLUT_OP_DISP:           /* the NPC's disposition (the voice table: its base, no modifiers yet) */
        return compare_int(g->disposition,cmp,sx32(raw));
    case AW_GLUT_OP_PCFACTION:{     /* the player's rank in the faction (none named: the speaker's), at least VALUE;
                                     * a member only (OpenMW filter.cpp testPlayer) */
        const char *faction=operand==NONE16?g->faction:cond_name(g,operand);long rank=-1;
        if(!faction || !*faction)faction=g->faction;
        if(!faction || !aw_glut_live || !aw_glut_live->pc_rank || !aw_glut_live->pc_rank(faction,&rank))return 0;
        return rank>=0 && rank>=sx32(raw);}
    }
    return 0;
}

int AW_GlutPick(const aw_glut_t *g,int npc,int topic,const aw_glut_state_t *s,int pick_random,int roll) {
    unsigned at[AW_GLUT_MAX_LISTS],end[AW_GLUT_MAX_LISTS];int picks[AW_GLUT_MAX_PICKS];
    unsigned set,ls,n,k;int file_topic,count=0;unsigned long first;aw_glut_cond_t ctx;
    if(!g->data || npc<0 || npc>=g->npcs || topic<0 || topic>=AW_GLUT_TOPICS || (file_topic=g->topic_of[topic])<0)return -1;
    AW_GlutCondOf(g,npc,&ctx);
    set=rd16(g->npc+AW_GLUT_NPC_ROW*npc+8);
    ls=rd16(g->set+2*((long)set*g->topics+file_topic));
    if(ls==NONE16)return -1;
    first=rd32(g->listset+8*ls);n=rd16(g->listset+8*ls+4);
    for(k=0;k<n;k++){
        unsigned list=rd16(g->listset_item+2*(first+k));
        at[k]=(unsigned)rd32(g->list+8*list);end[k]=at[k]+rd16(g->list+8*list+4);
    }
    for(;;){
        /* the merge: the smallest entry index next (the entries are numbered in the original's order) */
        unsigned best=NONE16,from=0,e;const unsigned char *row;int ok=1;unsigned c,nc;
        for(k=0;k<n;k++)if(at[k]<end[k]){
            e=rd16(g->list_item+2*at[k]);
            if(e<best){best=e;from=k;}
        }
        if(best==NONE16)break;
        at[from]++;                  /* an entry is in one list only (one audience per entry) */
        row=g->entry+12*best;
        nc=row[10];
        for(c=0;c<nc && ok;c++)ok=AW_GlutCond(&ctx,g->cond+8*(rd32(row+4)+c),s);
        if(ok){
            if(!pick_random)return (int)best;
            if(count<AW_GLUT_MAX_PICKS)picks[count++]=(int)best;
        }
        if(row[11]&1)break;          /* no run-time condition: nothing after it can be said */
    }
    if(!count)return -1;
    if(roll<0)roll=-roll;
    return picks[roll%count];
}

int AW_GlutCandidates(const aw_glut_t *g,int npc,int topic,int *out,int max) {
    unsigned at[AW_GLUT_MAX_LISTS],end[AW_GLUT_MAX_LISTS];
    unsigned set,ls,n,k;int file_topic,count=0;unsigned long first;
    if(!g->data || npc<0 || npc>=g->npcs || topic<0 || topic>=AW_GLUT_TOPICS || (file_topic=g->topic_of[topic])<0)return 0;
    set=rd16(g->npc+AW_GLUT_NPC_ROW*npc+8);
    ls=rd16(g->set+2*((long)set*g->topics+file_topic));
    if(ls==NONE16)return 0;
    first=rd32(g->listset+8*ls);n=rd16(g->listset+8*ls+4);
    for(k=0;k<n;k++){
        unsigned list=rd16(g->listset_item+2*(first+k));
        at[k]=(unsigned)rd32(g->list+8*list);end[k]=at[k]+rd16(g->list+8*list+4);
    }
    while(count<max){                /* the same merge as AW_GlutPick, no condition tested */
        unsigned best=NONE16,from=0,e;
        for(k=0;k<n;k++)if(at[k]<end[k]){
            e=rd16(g->list_item+2*at[k]);
            if(e<best){best=e;from=k;}
        }
        if(best==NONE16)break;
        at[from]++;
        out[count++]=(int)best;
    }
    return count;
}
/* letters and digits only, ASCII letters folded: the link marks ('@name#'), pseudo-asterisks and spacing the
 * dialogue table drops from the shown text do not count */
static int line_char(const char **p) {
    int c;
    while((c=(unsigned char)**p)!=0){
        (*p)++;
        if((c>='0' && c<='9') || (c>='a' && c<='z') || c>=0x80)return c;
        if(c>='A' && c<='Z')return c+32;
    }
    return 0;
}
int AW_GlutSameLine(const char *voice,const char *shown) {
    int a,b,n=0;
    if(!voice || !shown)return 0;
    do{a=line_char(&voice);b=line_char(&shown);if(a!=b)return 0;n++;}while(a);
    return n>1;                      /* an empty line matches nothing */
}
int AW_GlutSound(const aw_glut_t *g,int entry,unsigned char hash[8]) {
    unsigned s;
    if(entry<0 || entry>=g->entries || (s=rd16(g->entry+12*entry+8))==NONE16)return 0;
    memcpy(hash,g->sound+AW_GLUT_SOUND_ROW*s,8);
    return 1;
}
int AW_GlutCreatureFind(const aw_glut_t *g,const char *id) {
    long low=0,high=g->creatures-1;
    if(!g->data || !id || !*id)return -1;
    while(low<=high){
        long mid=(low+high)/2;
        int c=idcmp(id,(const char *)g->strings+rd32(g->creature+AW_GLUT_CREATURE_ROW*mid));
        if(!c)return (int)mid;
        if(c<0)high=mid-1;else low=mid+1;
    }
    return -1;
}
int AW_GlutCreatureSound(const aw_glut_t *g,int row,int moment) {
    unsigned s;
    if(row<0 || row>=g->creatures || moment<0 || moment>=AW_SNDG_MOMENTS)return -1;
    s=rd16(g->creature+AW_GLUT_CREATURE_ROW*row+4+2*moment);
    return s==NONE16?-1:(int)s;
}
int AW_GlutSlotSound(const aw_glut_t *g,int slot) {
    unsigned s;
    if(!g->data || slot<0 || slot>=g->slots)return -1;
    s=rd16(g->slot+2*slot);
    return s==NONE16?-1:(int)s;
}
int AW_GlutPoolPath(const aw_glut_t *g,int sound,char *out,int capacity) {
    static const char hex[]="0123456789abcdef";
    int i;char *p;
    if(!out || capacity<AW_GLUT_POOL_PATH || sound<0 || sound>=g->sounds)return 0;
    memcpy(out,"sound/pool/a",12);p=out+12;
    for(i=0;i<8;i++){unsigned char b=g->sound[AW_GLUT_SOUND_ROW*sound+i];*p++=hex[b>>4];*p++=hex[b&15];}
    memcpy(p,".wav",5);
    return 1;
}
int AW_GlutSoundLength(const aw_glut_t *g,int sound) {
    return sound<0 || sound>=g->sounds?-1:(int)rd16(g->sound+AW_GLUT_SOUND_ROW*sound+8);
}
int AW_GlutSoundMapped(const aw_glut_t *g,int sound) {
    return sound<0 || sound>=g->sounds?-1:(int)(rd16(g->sound+AW_GLUT_SOUND_ROW*sound+10)&AW_GLUT_MAPPED);
}
int AW_GlutSoun(const aw_glut_t *g,int index,aw_glut_soun_t *out) {
    const unsigned char *r;
    if(!out || index<0 || index>=g->souns)return 0;
    r=g->soun+AW_GLUT_SOUN_ROW*index;
    memcpy(out->hash,r,8);
    out->centis=(unsigned short)rd16(r+8);out->volume=r[10];out->mapped=(unsigned char)(r[11]&AW_GLUT_MAPPED);
    out->near_units=(unsigned short)rd16(r+12);out->far_units=(unsigned short)rd16(r+14);
    return 1;
}
long AW_GlutTextOffset(const aw_glut_t *g,int entry) {
    unsigned long t;
    if(entry<0 || entry>=g->entries || (t=rd32(g->entry+12*entry))==NONE32)return -1;
    return (long)t;
}

void AW_GlutExpand(const aw_glut_t *g,int npc,const char *name,const char *p,char *out,int capacity) {
    static const char *const player[]={"pcname","pcrace","pcclass"};
    static const char *const speaker[]={"faction","class","race","rank","cell","name"};   /* longest first */
    static const int field[]={2,0,1,3,4,-1};                                            /* NPC row define slot */
    int n=0,k;
    if(capacity<=0)return;
    while(*p && n<capacity-1){
        const char *put=NULL;int skip=0;
        if(*p=='%'){
            for(k=0;k<3 && !skip;k++)if(starts_with(p+1,player[k])){skip=-1;}
            if(!skip)for(k=0;k<6;k++)if(starts_with(p+1,speaker[k])){
                put=field[k]<0?name:name_of(g,npc>=0 && npc<g->npcs?rd16(g->npc+AW_GLUT_NPC_ROW*npc+10+2*field[k]):NONE16);
                skip=1+(int)strlen(speaker[k]);
                if(!put)put="";
                break;
            }
        }
        if(skip>0){
            while(*put && n<capacity-1)out[n++]=*put++;
            p+=skip;
            continue;
        }
        out[n++]=*p++;
    }
    out[n]=0;
}

/* The speaker's values for the one getter table (aw_textdef.c; TEXT-MACROS-DIALOGUE-CODES-59): the NPC row's define
 * slots (0 class, 1 race, 2 faction, 3 rank, 4 home cell) and NAME, the same values AW_GlutExpand writes, with no
 * text scanned. V's other fields are left as they are. */
void AW_GlutSpeakerValues(const aw_glut_t *g,int npc,const char *name,aw_textdef_values_t *v) {
    const char *slot[5];int k,ok=npc>=0 && npc<g->npcs;
    for(k=0;k<5;k++)slot[k]=name_of(g,ok?rd16(g->npc+AW_GLUT_NPC_ROW*npc+10+2*k):NONE16);
    v->speaker=1;v->name=name;
    v->clas=slot[0];v->race=slot[1];v->faction=slot[2];v->rank=slot[3];v->cell=slot[4];
}

#ifndef AW_GLUT_HOST_TEST
#include "quakedef.h"
#include "aw_anim.h"
#include "aw_combat.h"
#include "aw_tryalloc.h"
#include "aw_character.h"

static cvar_t lut_on={"aw_npc_voice_lut","1",true};   /* 0: the previous method (per-model bark lines only) */
/* 1: a spoken or shown line's defines filled in one pass through the getter table (TEXT-MACROS-DIALOGUE-CODES-59);
 * 0: the previous chain (AW_GlutExpand, then AW_ExpandDialogue). A compile switch, not a cvar: no resident
 * registration added (tests/resident_registry_budget.json). */
#ifndef AW_TEXT_LUT
#define AW_TEXT_LUT 1
#endif
static aw_glut_t table;
static unsigned char *resident;
static int loaded;                /* 0 not tried, 1 usable, -1 unavailable (logged once) */
static short npc_of[MAX_EDICTS];  /* row + 1 per edict, 0 unknown, -1 none; checked against aw_source_id */
static char said[1024];
static const char path[]="npc-voices.lut";

static int creature_sound(edict_t *e,int moment,char *out,int size);
static cvar_t player_steps,player_stride,player_step_volume;
static void player_footsteps(void);
static void player_footsteps_cmd(void);
static void sound_event_cmd(void);
void AW_GlutInit(void) {
    Cvar_RegisterVariable(&lut_on);
    Cvar_RegisterVariable(&player_steps);Cvar_RegisterVariable(&player_stride);Cvar_RegisterVariable(&player_step_volume);
    Cmd_AddCommand("aw_player_footsteps_cmd",player_footsteps_cmd);
    Cmd_AddCommand("aw_sound_event",sound_event_cmd);       /* dbg sound: every sound event's trigger, one command */
    aw_voice_table_row=AW_GlutNpcOf;aw_voice_table_bark=AW_GlutBark;
    aw_creature_sound=creature_sound;aw_player_steps=player_footsteps;
}
static int load(void) {
    FILE *f=NULL;long size,resident_size;unsigned char header[AW_GLUT_HEADER];
    if(loaded)return loaded>0;
    loaded=-1;
    size=COM_FOpenFile((char *)path,&f);
    if(size<AW_GLUT_HEADER || !f){if(f)fclose(f);Con_DPrintf("Voice table: %s not in this build\n",path);return 0;}
    if(fread(header,1,AW_GLUT_HEADER,f)!=AW_GLUT_HEADER || (resident_size=AW_GlutResidentSize(header,size))<0){
        fclose(f);Con_Printf("Voice table: %s is not AWGL2\n",path);return 0;
    }
    /* once per session, outside the Quake heap (accelerator RAM when there is some) */
    if(!(resident=(unsigned char *)AW_TryMalloc((size_t)resident_size))){fclose(f);Con_Printf("Voice table: no memory for %ld bytes\n",resident_size);return 0;}
    memcpy(resident,header,AW_GLUT_HEADER);
    if((long)fread(resident+AW_GLUT_HEADER,1,(size_t)(resident_size-AW_GLUT_HEADER),f)!=resident_size-AW_GLUT_HEADER ||
       !AW_GlutOpen(&table,resident,resident_size,size)){
        fclose(f);free(resident);resident=NULL;memset(&table,0,sizeof(table));Con_Printf("Voice table: %s is damaged\n",path);return 0;
    }
    fclose(f);
    Con_DPrintf("Voice table: %ld NPCs, %ld entries, %ld bytes resident\n",table.npcs,table.entries,resident_size);
    loaded=1;
    return 1;
}
static const char *source_id(edict_t *e) {
    eval_t *v=GetEdictFieldValue(e,"aw_source_id");
    return v && v->string?pr_strings+v->string:"";
}
/* The player's voice row (COMBAT-VOICES-SILENT-33): id1/npc-voice-player.txt names, per race and sex, the NPC whose
 * Hit lines are that race and sex's own (tools/greeting_lut.py player_voices); read when the player's race or sex
 * changes, nothing kept but the row. -1 when the build has no file or no line for the player. */
static int player_row(void) {
    static int cached=-2,cached_race=-1,cached_female=-1;
    FILE *f=NULL;char line[160],want[72];int n;
    if(aw_character.race<0 || aw_character.race>=aw_race_count)return -1;
    if(cached!=-2 && cached_race==aw_character.race && cached_female==aw_character.female)return cached;
    cached=-1;cached_race=aw_character.race;cached_female=aw_character.female;
    want[0]=0;strncat(want,aw_races[aw_character.race].id,63);strcat(want,aw_character.female?"\tf\t":"\tm\t");
    for(n=0;want[n];n++)if(want[n]>='A' && want[n]<='Z')want[n]+=32;
    if(COM_FOpenFile("npc-voice-player.txt",&f)<0 || !f)return -1;
    if(!fgets(line,sizeof(line),f) || strncmp(line,"AWPV1",5)){fclose(f);return -1;}
    while(fgets(line,sizeof(line),f)){
        line[strcspn(line,"\r\n")]=0;
        for(n=0;line[n] && line[n]!='\t';n++)if(line[n]>='A' && line[n]<='Z')line[n]+=32;
        if(!strncmp(line,want,strlen(want))){cached=AW_GlutFind(&table,line+strlen(want));break;}
    }
    fclose(f);
    return cached;
}
int AW_GlutNpcOf(edict_t *e) {
    int n,row;const char *id;
    if(!e || e->free || !lut_on.value || !load())return -1;
    n=NUM_FOR_EDICT(e);
    if(n==1)return player_row();        /* the player has no record id of his own: his race and sex's lines */
    if(n<0 || n>=MAX_EDICTS)return -1;
    id=source_id(e);
    row=npc_of[n]-1;
    /* the cache holds while the edict still names that record (a new level reuses edict numbers) */
    if(npc_of[n]>0 && !idcmp(id,AW_GlutId(&table,row)))return row;
    if(npc_of[n]<0 && !*id)return -1;
    row=AW_GlutFind(&table,id);
    npc_of[n]=(short)(row<0?-1:row+1);
    return row;
}
/* A creature's sound generator moment (CREATURE-ANIM-SOUND-54): its row by the record id (aw_source_id), the
 * moment's sound as the pool name the mixer takes ("pool/a<hash>.wav"); 0 when the creature has no row, the moment
 * no sound, or this build lacks the file (a MiniWind keeps only what its actors need). */
static int creature_sound(edict_t *e,int moment,char *out,int size) {
    int row,sound;char pool[AW_GLUT_POOL_PATH];
    if(!e || e->free || !lut_on.value || !load() || size<AW_GLUT_POOL_PATH-6)return 0;
    if((row=AW_GlutCreatureFind(&table,source_id(e)))<0 || (sound=AW_GlutCreatureSound(&table,row,moment))<0)return 0;
    if(!AW_GlutSoundMapped(&table,sound) || !AW_GlutPoolPath(&table,sound,pool,sizeof(pool)))return 0;
    strcpy(out,pool+6);       /* without "sound/" */
    return 1;
}
/* The player's own footsteps (PLAYER-FOOTSTEPS-NONE-58; the maintainer, 31 October 2026: a setting, OFF by default,
 * Options > Audio and dbg footsteps, saved). The original's rule for every actor (docs/ANIMATION.md "Footstep
 * sounds"): the boots' armour class (bare, light, medium, heavy), water, swimming; the sounds are the voice table's
 * named slots. The step itself: one every aw_player_footstep_stride units walked on the ground, left and right in
 * turn (an AmiWind approximation of the original's walk and run sound keys: the player has no third-person
 * animation clock here). */
static cvar_t player_steps={"aw_player_footsteps","0",true};
static cvar_t player_stride={"aw_player_footstep_stride","26",true};
static cvar_t player_step_volume={"aw_player_footstep_volume","0.6",true};
static float walked;static vec3_t walked_at;static int walked_foot,walked_ready;
int AW_GlutPlayerStepSlot(int boots_class,int medium,int right) {
    static const int dry[4]={AW_SLOT_FOOT_BARE_LEFT,AW_SLOT_FOOT_LIGHT_LEFT,AW_SLOT_FOOT_MED_LEFT,AW_SLOT_FOOT_HEAVY_LEFT};
    int base=medium==AW_ANIM_SWIMMING?AW_SLOT_SWIM_LEFT:medium==AW_ANIM_WADE?AW_SLOT_FOOT_WATER_LEFT:
        dry[boots_class>=0 && boots_class<=3?boots_class:0];
    return base+(right?1:0);
}
static void player_footsteps(void) {
    edict_t *p;float dx,dy;int boots=0,medium,sound;char pool[AW_GLUT_POOL_PATH];sfx_t *sfx;const aw_fighter_t *me;
    if(!player_steps.value || !sv.active || cls.state!=ca_connected || svs.maxclients<1){walked_ready=0;return;}
    p=EDICT_NUM(1);
    if(p->free || p->v.health<=0){walked_ready=0;return;}
    if(!walked_ready){VectorCopy(p->v.origin,walked_at);walked=0;walked_ready=1;return;}
    dx=p->v.origin[0]-walked_at[0];dy=p->v.origin[1]-walked_at[1];VectorCopy(p->v.origin,walked_at);
    medium=AW_AnimMedium(p);
    if(!((int)p->v.flags&FL_ONGROUND) && medium!=AW_ANIM_SWIMMING)return;   /* in the air: no step */
    {float d=(float)sqrt(dx*dx+dy*dy);if(d>64)return;walked+=d;}            /* a teleport is not a walk */
    if(walked<(player_stride.value>4?player_stride.value:4))return;
    walked=0;walked_foot=!walked_foot;
    if((me=AW_CombatPlayer())!=NULL)boots=AW_HIT_CLASS(me,3);               /* the boots' slot (cuirass, helmet, greaves, boots ...) */
    if(!load() || (sound=AW_GlutSlotSound(&table,AW_GlutPlayerStepSlot(boots,medium,walked_foot)))<0)return;
    if(!AW_GlutSoundMapped(&table,sound) || !AW_GlutPoolPath(&table,sound,pool,sizeof(pool)))return;
    if((sfx=S_PrecacheSound(pool+6))!=NULL)S_StartSound(1,4,sfx,p->v.origin,player_step_volume.value,1);
}
static void player_footsteps_cmd(void) {
    const char *a=Cmd_Argc()>1?Cmd_Argv(1):"";
    if(!Q_strcasecmp((char *)a,"on") || !strcmp(a,"1") || !Q_strcasecmp((char *)a,"true"))Cvar_SetValue("aw_player_footsteps",1);
    else if(!Q_strcasecmp((char *)a,"off") || !strcmp(a,"0") || !Q_strcasecmp((char *)a,"false"))Cvar_SetValue("aw_player_footsteps",0);
    else if(*a){Con_Printf("dbg footsteps: on/off (your own footsteps; default off, saved; also Options > Audio)\n");return;}
    Con_Printf("Your footsteps: %s (NPC and creature footsteps: aw_npc_footsteps)\n",player_steps.value?"on":"off");
}
/* THE SOUND EVENT HOOK (aw_glut.h AW_SoundEvent; VOICE-COVERAGE-58). */
static void said_what(char *what,const char *text) {if(what){what[0]=0;strncat(what,text,63);}}
int AW_SoundEvent(int event,edict_t *e,int arg,char *what) {
    int kind,index,row,sound;unsigned char hash[8];char pool[AW_GLUT_POOL_PATH];sfx_t *sfx;
    edict_t *p=svs.maxclients>0?EDICT_NUM(1):NULL;
    if(!AW_SoundEventResolve(event,arg,&kind,&index)){said_what(what,"no such sound event");return -1;}
    if(!lut_on.value || !load()){said_what(what,"no voice table in this build");return -1;}
    if(cls.state!=ca_connected){said_what(what,"not in a game");return -1;}
    if(kind==AW_SEK_PLAYER_VOICE)e=p;
    if(!e)e=p;
    if(!e || e->free){said_what(what,"no actor");return -1;}
    switch(kind){
    case AW_SEK_VOICE:case AW_SEK_PLAYER_VOICE:
        if((row=AW_GlutNpcOf(e))<0){said_what(what,kind==AW_SEK_VOICE?"not an NPC of the voice table":
                                                  "no voice for the player's race and sex");return -1;}
        if((sound=AW_GlutBark(e,row,index,0,hash))<0){said_what(what,"no line of that topic passes");return 0;}
        if(!sound){said_what(what,"the line has no sound");return 0;}
        if(what){static const char hex[]="0123456789abcdef";int i;strcpy(what,"pool/a");
            for(i=0;i<8;i++){what[6+2*i]=hex[hash[i]>>4];what[7+2*i]=hex[hash[i]&15];}strcpy(what+22,".wav");}
        if(!AW_VoicePlay(e,hash)){if(what)strcat(what," (not played: busy or not in this build)");return 0;}
        return 1;
    case AW_SEK_SLOT:
        if((sound=AW_GlutSlotSound(&table,index))<0){said_what(what,"no sound mapped for it");return 0;}
        break;
    default:
        if((row=AW_GlutCreatureFind(&table,source_id(e)))<0){said_what(what,"not a creature of the voice table");return -1;}
        if((sound=AW_GlutCreatureSound(&table,row,index))<0){said_what(what,"the creature has no such sound");return 0;}
        break;
    }
    if(!AW_GlutSoundMapped(&table,sound) || !AW_GlutPoolPath(&table,sound,pool,sizeof(pool))){
        said_what(what,"its file is not in this build");return 0;
    }
    said_what(what,pool+6);
    if(!(sfx=S_PrecacheSound(pool+6)))return 0;
    /* a creature's moan, roar and scream on the voice channel (as aw_anim.c emit), everything else on the body's */
    S_StartSound(NUM_FOR_EDICT(e),kind==AW_SEK_CREATURE && index!=AW_SNDG_LAND?2:4,sfx,e->v.origin,1,1);
    return 1;
}
/* dbg sound [MOMENT [N] / list]: the event on the actor you aim at (512 units), else on you; no argument or list:
 * every moment and what it plays here. */
static void sound_event_cmd(void) {
    const char *a=Cmd_Argc()>1?Cmd_Argv(1):"";int event,arg=-1,r,i,kind,index;char what[96];
    edict_t *p=svs.maxclients>0 && sv.active?EDICT_NUM(1):NULL,*e=NULL;
    if(!*a || !Q_strcasecmp((char *)a,"list")){
        Con_Printf("Sound events (dbg sound MOMENT [N] on the actor you aim at, else on you):\n");
        for(i=0;i<AW_SOUND_EVENTS;i++){
            static const char *const kinds[]={"voice","your voice","sound","creature"};
            int s=-1;AW_SoundEventResolve(i,-1,&kind,&index);
            if(kind==AW_SEK_SLOT && load())s=AW_GlutSlotSound(&table,index);
            Con_Printf(" %-14s %s%s%s\n",aw_sound_events[i].name,kinds[kind],aw_sound_events[i].args>1?" [N]":"",
                       kind!=AW_SEK_SLOT?"":s<0?": none mapped":AW_GlutSoundMapped(&table,s)>0?"":": not in this build");
        }
        return;
    }
    if((event=AW_SoundEventFind(a))<0){Con_Printf("dbg sound: no moment '%s' (dbg sound list)\n",a);return;}
    if(Cmd_Argc()>2)arg=Q_atoi(Cmd_Argv(2));
    if(p && !p->free){vec3_t angles;VectorCopy(cl.viewangles,angles);e=AW_NPCTargetReach(p,angles,512);}
    r=AW_SoundEvent(event,e,arg,what);
    Con_Printf("Sound event %s on %s: %s %s\n",aw_sound_events[event].name,
               e && aw_sound_events[event].kind!=AW_SEK_PLAYER_VOICE?"the actor aimed at":"you",
               r>0?"played":r==0?"silent,":"cannot run,",what);
}
static void set_float(edict_t *e,char *field,float value) {
    eval_t *v=GetEdictFieldValue(e,field);
    if(v)v->_float=value;
}
int AW_GlutPrep(edict_t *e) {
    int row=AW_GlutNpcOf(e);eval_t *voice,*hello;
    if(row<0)return 0;
    voice=GetEdictFieldValue(e,"aw_voice");hello=GetEdictFieldValue(e,"aw_hello_distance");
    if((!voice || !voice->string || !pr_strings[voice->string]) && (!hello || hello->_float<=0)){
        set_float(e,"aw_hello_distance",(float)AW_GlutHelloDistance(&table,row));
        set_float(e,"aw_hello_reset",(float)AW_GlutResetDistance(&table));
        set_float(e,"aw_greet_duration",(float)AW_GlutDuration(&table));
    }
    return 1;
}
static void state_of(edict_t *e,int talked,aw_glut_state_t *s) {
    edict_t *p=svs.maxclients>0?EDICT_NUM(1):NULL;int h=AW_CombatHealthPercent(e);
    s->speaker_health_percent=h<0?100:h;
    s->player_health=p && !p->free?(int)p->v.health:100;
    s->player_health_percent=p && !p->free && p->v.max_health>0?(int)(p->v.health*100/p->v.max_health):100;
    s->talked=talked;
    s->random100=rand()%101;
}
static int read_text(int entry,char *out,int capacity) {
    FILE *f=NULL;long offset=AW_GlutTextOffset(&table,entry),start;int n;
    out[0]=0;
    if(offset<0 || capacity<2)return 0;
    if(COM_FOpenFile((char *)path,&f)<0 || !f)return 0;
    start=ftell(f);
    if(fseek(f,start+table.text_base+offset,SEEK_SET)){fclose(f);return 0;}
    n=(int)fread(out,1,(size_t)(capacity-1),f);
    fclose(f);
    if(n<0)n=0;
    out[n]=0;
    return (int)strlen(out);
}
int AW_GlutDefineValues(edict_t *e,int row,aw_textdef_values_t *v) {
    if(!AW_TEXT_LUT)return 0;
    AW_TextDefinesPlayer(v);
    AW_GlutSpeakerValues(&table,row,pr_strings+e->v.netname,v);
    return 1;
}
static void line_of(edict_t *e,int row,int entry,char *out,int capacity) {
    char raw[1024];
    if(!read_text(entry,raw,sizeof(raw))){out[0]=0;return;}
    AW_GlutFill(e,row,raw,out,capacity);
}
int AW_GlutSay(edict_t *e,int topic,int talked) {
    int row=AW_GlutNpcOf(e),entry;aw_glut_state_t s;unsigned char hash[8];
    said[0]=0;
    if(row<0 || AW_PlayerDead())return 0;
    state_of(e,talked,&s);
    if((entry=AW_GlutPick(&table,row,topic,&s,0,0))<0)return 0;
    line_of(e,row,entry,said,sizeof(said));
    if(AW_GlutSound(&table,entry,hash))AW_VoicePlay(e,hash);      /* missing from the voice pool: quiet */
    return 1;
}
const char *AW_GlutText(void) {return said;}
/* The conversation greeting's voice (VOICE-COVERAGE-58; OpenMW DialogueManager::startDialogue says the picked INFO's
 * sound): the voice table's Greeting entry of this speaker whose line is the one shown (AW_GlutSameLine; both tables
 * hold the same INFO records), its voice played; that INFO without a voice: silent, as in the original. No entry
 * with that line: the voice table's own greeting pick, the previous method. One file open, the candidates' texts
 * read until the match; nothing kept. 1 when a voice was started. */
int AW_GlutGreetVoice(edict_t *e,const char *shown) {
    static int list[AW_GLUT_MAX_PICKS*4];
    int row=AW_GlutNpcOf(e),n,k,entry=-1;aw_glut_state_t s;unsigned char hash[8];FILE *f=NULL;long start;
    static char text[1024];
    if(row<0 || !shown || AW_PlayerDead())return 0;
    n=AW_GlutCandidates(&table,row,AW_GLUT_GREETING,list,(int)(sizeof(list)/sizeof(list[0])));
    if(n>0 && COM_FOpenFile((char *)path,&f)>=0 && f){
        start=ftell(f);
        for(k=0;k<n && entry<0;k++){
            long offset=AW_GlutTextOffset(&table,list[k]);int got;
            if(offset<0 || fseek(f,start+table.text_base+offset,SEEK_SET))continue;
            got=(int)fread(text,1,sizeof(text)-1,f);text[got<0?0:got]=0;
            if(AW_GlutSameLine(text,shown))entry=list[k];
        }
        fclose(f);
    }else if(f)fclose(f);
    if(entry<0){                     /* no entry with the shown line: the voice table's pick */
        state_of(e,0,&s);
        if((entry=AW_GlutPick(&table,row,AW_GLUT_GREETING,&s,0,0))<0)return 0;
    }
    return AW_GlutSound(&table,entry,hash) && AW_VoicePlay(e,hash)>0;
}
int AW_GlutBark(edict_t *e,int row,int topic,int pick_random,unsigned char hash[8]) {
    aw_glut_state_t s;int entry;
    state_of(e,0,&s);
    if((entry=AW_GlutPick(&table,row,topic,&s,pick_random,rand()))<0)return -1;
    return AW_GlutSound(&table,entry,hash);
}
int AW_MwscriptActorFaction(const char *record,char *out,int capacity);   /* aw_mwhost.c */
int AW_MwscriptNpcRank(edict_t *e);                                         /* aw_mwhost.c */
int AW_GlutSpeaker(edict_t *e,int talked,aw_glut_cond_t *c,aw_glut_state_t *s) {
    static char faction[64];int row=AW_GlutNpcOf(e),kept;
    if(row<0)return -1;
    AW_GlutCondOf(&table,row,c);
    /* a script's RaiseRank / LowerRank on this NPC (CELL-CHANGES-59, saved) over its record's rank */
    if(c->rank>=0 && (kept=AW_MwscriptNpcRank(e))>=0)c->rank=kept;
    state_of(e,talked,s);
    c->speaker=NUM_FOR_EDICT(e);
    c->faction=AW_MwscriptActorFaction(source_id(e),faction,sizeof(faction))?faction:NULL;
    return row;
}
void AW_GlutFill(edict_t *e,int row,const char *raw,char *out,int capacity) {
    char speaker[1024];aw_textdef_values_t v;
    if(AW_GlutDefineValues(e,row,&v)){AW_TextDefines(out,capacity,raw,&v);return;}   /* one pass */
    AW_GlutExpand(&table,row,pr_strings+e->v.netname,raw,speaker,sizeof(speaker));
    AW_ExpandDialogue(out,capacity,speaker);
}
int AW_GlutConverse(edict_t *e,int again,char *out,int capacity) {
    int row=AW_GlutNpcOf(e),entry;aw_glut_state_t s;
    if(row<0)return 0;
    state_of(e,again,&s);
    if((entry=AW_GlutPick(&table,row,AW_GLUT_GREETING,&s,0,0))<0)return 0;
    line_of(e,row,entry,out,capacity);
    return out[0]!=0;
}
#endif
