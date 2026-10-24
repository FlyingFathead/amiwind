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
    "greeting"};

long AW_GlutResidentSize(const unsigned char *h,long file_size) {
    long size;unsigned long texts;
    if(memcmp(h,"AWGL",4) || rd16(h+4)!=1)return -1;
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
    if(g->topics<1 || g->topics>64 || g->functions>256)return 0;
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
    TAKE(sound,8L*g->sounds);
    TAKE(global,8L*g->globals);
    TAKE(name,4L*g->names);
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
/* A function's value: the live ones from the engine, the rest the start-of-game fixture; 0 when not known. */
static int value(const aw_glut_t *g,int npc,unsigned fn,const aw_glut_state_t *s,long *out) {
    int rank=(signed char)g->npc[AW_GLUT_NPC_ROW*npc+7];
    switch(fn){
    case AW_GLUT_FN_HEALTH_PERCENT:*out=s->speaker_health_percent;return 1;
    case AW_GLUT_FN_PC_HEALTH_PERCENT:*out=s->player_health_percent;return 1;
    case AW_GLUT_FN_PC_HEALTH:*out=s->player_health;return 1;
    case AW_GLUT_FN_TALKED_TO_PC:*out=s->talked!=0;return 1;
    /* the player holds no rank in any faction yet (no faction system): -1 - the speaker's rank */
    case AW_GLUT_FN_FACTION_RANK_DIFFERENCE:*out=rank<0?0:-1-rank;return 1;
    }
    if((int)fn>=g->functions || !(g->known[fn>>3]>>(fn&7)&1))return 0;
    *out=sx32(rd32(g->fixture+4*fn));
    return 1;
}
static int starts_with(const char *text,const char *prefix) {
    for(;*prefix;text++,prefix++)if(lower((unsigned char)*text)!=lower((unsigned char)*prefix))return 0;
    return 1;
}
int AW_GlutHolds(const aw_glut_t *g,int npc,const unsigned char *c,const aw_glut_state_t *s) {
    unsigned op=c[0],cmp=c[1],operand=rd16(c+2);unsigned long raw=rd32(c+4);long x;
    switch(op){
    case AW_GLUT_OP_FUNC:
        if(!value(g,npc,operand,s,&x))return 0;
        return cmp&0x80?compare_float((float)x,cmp,rdf(c+4)):compare_int(x,cmp,sx32(raw));
    case AW_GLUT_OP_GLOBAL:
        if((long)operand>=g->globals)return 0;
        return compare_float(rdf(g->global+8*operand+4),cmp,cmp&0x80?rdf(c+4):(float)sx32(raw));
    case AW_GLUT_OP_RANDOM100:
        return cmp&0x80?compare_float((float)s->random100,cmp,rdf(c+4)):compare_int(s->random100,cmp,sx32(raw));
    case AW_GLUT_OP_LOCAL:          /* the speaker's script locals: 0 until scripts run (OpenMW: empty locals read 0) */
    case AW_GLUT_OP_JOURNAL:        /* journal indexes: 0 until the journal exists */
    case AW_GLUT_OP_DEAD:           /* dead counts: 0 */
        return cmp&0x80?compare_float(0,cmp,rdf(c+4)):compare_int(0,cmp,sx32(raw));
    case AW_GLUT_OP_NOTLOCAL:
        return !(cmp&0x80?compare_float(0,cmp,rdf(c+4)):compare_int(0,cmp,sx32(raw)));
    case AW_GLUT_OP_ITEM:{          /* the player's items: none counted yet; gold is not known (the builder's rule) */
        const char *item=name_of(g,operand);
        if(!item || !strcmp(item,"gold_001"))return 0;
        return compare_int(0,cmp,sx32(raw));
    }
    case AW_GLUT_OP_CELL:{          /* the NPC row's home cell, a case-insensitive prefix (OpenMW ciStartsWith) */
        const char *cell=name_of(g,rd16(g->npc+AW_GLUT_NPC_ROW*npc+18)),*want=name_of(g,operand);
        int match=cell && want && starts_with(cell,want);
        if(!cell)return 0;
        return raw?match:!match;
    }
    case AW_GLUT_OP_DISP:           /* the NPC's base disposition (no modifiers yet) */
        return compare_int(g->npc[AW_GLUT_NPC_ROW*npc+6],cmp,sx32(raw));
    case AW_GLUT_OP_PCFACTION:      /* the player belongs to no faction yet */
        return 0;
    }
    return 0;
}

int AW_GlutPick(const aw_glut_t *g,int npc,int topic,const aw_glut_state_t *s,int pick_random,int roll) {
    unsigned at[AW_GLUT_MAX_LISTS],end[AW_GLUT_MAX_LISTS];int picks[AW_GLUT_MAX_PICKS];
    unsigned set,ls,n,k;int file_topic,count=0;unsigned long first;
    if(!g->data || npc<0 || npc>=g->npcs || topic<0 || topic>=AW_GLUT_TOPICS || (file_topic=g->topic_of[topic])<0)return -1;
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
        for(c=0;c<nc && ok;c++)ok=AW_GlutHolds(g,npc,g->cond+8*(rd32(row+4)+c),s);
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

int AW_GlutSound(const aw_glut_t *g,int entry,unsigned char hash[8]) {
    unsigned s;
    if(entry<0 || entry>=g->entries || (s=rd16(g->entry+12*entry+8))==NONE16)return 0;
    memcpy(hash,g->sound+8*s,8);
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

#ifndef AW_GLUT_HOST_TEST
#include "quakedef.h"
#include "aw_anim.h"
#include "aw_combat.h"

static cvar_t lut_on={"aw_npc_voice_lut","1",true};   /* 0: the previous method (per-model bark lines only) */
static aw_glut_t table;
static unsigned char *resident;
static int loaded;                /* 0 not tried, 1 usable, -1 unavailable (logged once) */
static short npc_of[MAX_EDICTS];  /* row + 1 per edict, 0 unknown, -1 none; checked against aw_source_id */
static char said[1024];
static const char path[]="npc-voices.lut";

void AW_GlutInit(void) {
    Cvar_RegisterVariable(&lut_on);
    aw_voice_table_row=AW_GlutNpcOf;aw_voice_table_bark=AW_GlutBark;
}
static int load(void) {
    FILE *f=NULL;long size,resident_size;unsigned char header[AW_GLUT_HEADER];
    if(loaded)return loaded>0;
    loaded=-1;
    size=COM_FOpenFile((char *)path,&f);
    if(size<AW_GLUT_HEADER || !f){if(f)fclose(f);Con_DPrintf("Voice table: %s not in this build\n",path);return 0;}
    if(fread(header,1,AW_GLUT_HEADER,f)!=AW_GLUT_HEADER || (resident_size=AW_GlutResidentSize(header,size))<0){
        fclose(f);Con_Printf("Voice table: %s is not AWGL1\n",path);return 0;
    }
    /* once per session, outside the Quake heap (accelerator RAM when there is some) */
    if(!(resident=(unsigned char *)malloc((size_t)resident_size))){fclose(f);Con_Printf("Voice table: no memory for %ld bytes\n",resident_size);return 0;}
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
int AW_GlutNpcOf(edict_t *e) {
    int n,row;const char *id;
    if(!e || e->free || !lut_on.value || !load())return -1;
    n=NUM_FOR_EDICT(e);
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
static void line_of(edict_t *e,int row,int entry,char *out,int capacity) {
    char raw[1024],speaker[1024];
    if(!read_text(entry,raw,sizeof(raw))){out[0]=0;return;}
    AW_GlutExpand(&table,row,pr_strings+e->v.netname,raw,speaker,sizeof(speaker));
    AW_ExpandDialogue(out,capacity,speaker);
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
int AW_GlutBark(edict_t *e,int row,int topic,int pick_random,unsigned char hash[8]) {
    aw_glut_state_t s;int entry;
    state_of(e,0,&s);
    if((entry=AW_GlutPick(&table,row,topic,&s,pick_random,rand()))<0)return -1;
    return AW_GlutSound(&table,entry,hash);
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
