/* SPDX-License-Identifier: GPL-2.0-or-later
 * The dialogue table, reader and first-match search (aw_dial.h; docs/DIALOGUE_DESIGN.md).
 *
 * The rule is the original's (OpenMW mwdialogue/filter.cpp Filter::search, learned there, our own code): a topic's
 * responses in the data's order, the first that passes every test is the answer; when one failed only on its
 * disposition test and none passed, the answer comes from the topic "Info Refusal". The builder decided every test
 * that reads only the speaker's record; the run-time ones are the voice table's condition records, tested by
 * AW_GlutCond, so greetings, voice lines and topics share one evaluator.
 * The pure part has no engine dependencies and allocates nothing: the conversation lives in the caller's buffer.
 */
#include <string.h>
#include "aw_dial.h"

static unsigned rd16(const unsigned char *p) {return (unsigned)p[0]<<8|p[1];}
static unsigned long rd32(const unsigned char *p) {return (unsigned long)p[0]<<24|(unsigned long)p[1]<<16|(unsigned long)p[2]<<8|p[3];}
static long pad4(long n) {return (n+3)&~3L;}

/* The header's counts (after the magic, version and functions): */
enum {H_TOPICS=8,H_NPCS=12,H_ROW_BYTES=16,H_LISTSETS=20,H_LISTSET_ITEMS=24,H_LISTS=28,H_LIST_ITEMS=32,H_ENTRIES=36,
      H_CONDS=40,H_GLOBALS=44,H_NAMES=48,H_LINKS=52,H_QUESTS=56,H_JOURNAL=60,H_STRINGS=64,H_TSTRINGS=68,
      H_SCRIPTS=72,H_TEXTS=76,H_ORDER=80,H_INFO_REFUSAL=88,H_STARTS=90,H_FACTIONS=92,H_REACTIONS=94};

static long resident_of(const unsigned char *h) {
    long topics=(long)rd32(h+H_TOPICS),npcs=(long)rd32(h+H_NPCS),functions=(long)rd16(h+6);
    if(topics<0 || topics>0xFFFFL || npcs<0 || npcs>0xFFFFL || functions>256)return -1;
    return AW_DIAL_HEADER+AW_DIAL_TOPIC_ROW*topics+4L*npcs+4L*functions+pad4((functions+7)/8)+
        pad4(2L*rd16(h+H_STARTS))+4L*AW_DIAL_SETTINGS+(long)AW_DIAL_FACTION_ID*rd16(h+H_FACTIONS)+4L*rd16(h+H_REACTIONS);
}

long AW_DialResidentSize(const unsigned char *h,long file_size) {
    long size;
    if(memcmp(h,"AWDL",4) || rd16(h+4)!=AW_DIAL_VERSION)return -1;
    size=resident_of(h);
    return size>AW_DIAL_HEADER && size<=file_size?size:-1;
}

int AW_DialOpen(aw_dial_t *d,const unsigned char *h,long size,long file_size) {
    long at;int i;
    memset(d,0,sizeof(*d));
    d->info_refusal=-1;
    if(size<AW_DIAL_HEADER || AW_DialResidentSize(h,file_size)!=size)return 0;
    d->data=h;d->size=size;d->file_size=file_size;
    d->functions=(long)rd16(h+6);d->topics=(long)rd32(h+H_TOPICS);d->npcs=(long)rd32(h+H_NPCS);
    d->row_bytes=(long)rd32(h+H_ROW_BYTES);d->listsets=(long)rd32(h+H_LISTSETS);
    d->listset_items=(long)rd32(h+H_LISTSET_ITEMS);d->lists=(long)rd32(h+H_LISTS);d->list_items=(long)rd32(h+H_LIST_ITEMS);
    d->entries=(long)rd32(h+H_ENTRIES);d->conds=(long)rd32(h+H_CONDS);d->globals=(long)rd32(h+H_GLOBALS);
    d->names=(long)rd32(h+H_NAMES);d->links=(long)rd32(h+H_LINKS);d->quests=(long)rd32(h+H_QUESTS);
    d->journal=(long)rd32(h+H_JOURNAL);d->string_bytes=(long)rd32(h+H_STRINGS);d->tstring_bytes=(long)rd32(h+H_TSTRINGS);
    d->script_bytes=(long)rd32(h+H_SCRIPTS);d->text_bytes=(long)rd32(h+H_TEXTS);
    /* every count is bounded so the section sums below cannot wrap (the file is a few MB) */
    for(i=H_ROW_BYTES;i<=H_TEXTS;i+=4)if(rd32(h+i)>0x3FFFFFFul)return 0;
    d->topic=h+AW_DIAL_HEADER;
    d->npc_offset=d->topic+AW_DIAL_TOPIC_ROW*d->topics;
    d->fixture=d->npc_offset+4*d->npcs;
    d->known=d->fixture+4*d->functions;
    d->start=d->known+pad4((d->functions+7)/8);d->starts=(int)rd16(h+H_STARTS);
    d->settings=d->start+pad4(2L*d->starts);
    d->faction=d->settings+4*AW_DIAL_SETTINGS;d->factions=(int)rd16(h+H_FACTIONS);
    d->reaction=d->faction+AW_DIAL_FACTION_ID*d->factions;d->reactions=(int)rd16(h+H_REACTIONS);
    at=size;
    d->at_conversation=at;
    d->conversation_bytes=8*d->globals+4*d->names+d->string_bytes;
    at+=d->conversation_bytes;
    d->at_rows=at;at+=d->row_bytes;
    d->at_listsets=at;at+=AW_DIAL_LIST_ROW*d->listsets;
    d->at_listset_items=at;at+=4*d->listset_items;
    d->at_lists=at;at+=AW_DIAL_LIST_ROW*d->lists;
    d->at_list_items=at;at+=4*d->list_items;
    d->at_entries=at;at+=AW_DIAL_ENTRY_ROW*d->entries;
    d->at_conds=at;at+=8*d->conds;
    d->at_links=at;at+=pad4(2*d->links);
    d->at_quests=at;at+=AW_DIAL_QUEST_ROW*d->quests;
    d->at_journal=at;at+=AW_DIAL_JOURNAL_ROW*d->journal;
    d->at_ranks=at;at+=(long)AW_DIAL_FACTION_ID*AW_DIAL_RANKS*rd16(h+H_FACTIONS);
    d->at_tstrings=at;at+=d->tstring_bytes;
    d->at_scripts=at;at+=d->script_bytes;
    d->at_texts=at;at+=d->text_bytes;
    if(at!=file_size || (d->string_bytes&3) || d->string_bytes<1){memset(d,0,sizeof(*d));d->info_refusal=-1;return 0;}
    for(i=0;i<d->topics;i++){
        const unsigned char *r=d->topic+AW_DIAL_TOPIC_ROW*i;
        if(rd32(r)+r[4]>=(unsigned long)d->tstring_bytes){memset(d,0,sizeof(*d));d->info_refusal=-1;return 0;}
    }
    for(i=0;i<d->npcs;i++){
        unsigned long o=rd32(d->npc_offset+4*i);
        if(o!=AW_DIAL_NONE32 && o+4>(unsigned long)d->row_bytes){memset(d,0,sizeof(*d));d->info_refusal=-1;return 0;}
    }
    for(i=0;i<d->starts;i++)if(rd16(d->start+2*i)>=(unsigned)d->topics){memset(d,0,sizeof(*d));d->info_refusal=-1;return 0;}
    for(i=0;i<d->factions;i++)if(d->faction[AW_DIAL_FACTION_ID*i+AW_DIAL_FACTION_ID-1]){memset(d,0,sizeof(*d));d->info_refusal=-1;return 0;}
    for(i=0;i<d->reactions;i++)
        if(d->reaction[4*i]>=d->factions || d->reaction[4*i+1]>=d->factions){memset(d,0,sizeof(*d));d->info_refusal=-1;return 0;}
    if(rd16(h+H_INFO_REFUSAL)<(unsigned)d->topics)d->info_refusal=(int)rd16(h+H_INFO_REFUSAL);
    return 1;
}

float AW_DialSetting(const aw_dial_t *d,int s) {
    union {unsigned long u;float f;} v;
    if(!d->data || s<0 || s>=AW_DIAL_SETTINGS)return 0;
    v.u=rd32(d->settings+4*s);
    return v.f;
}
static int lower_c(int c) {return c>='A' && c<='Z'?c+32:c;}
static int faction_index(const aw_dial_t *d,const char *id) {
    int i,k;
    if(!id || !*id)return -1;
    for(i=0;i<d->factions;i++){
        const char *f=(const char *)d->faction+AW_DIAL_FACTION_ID*i;
        for(k=0;f[k] && lower_c((unsigned char)f[k])==lower_c((unsigned char)id[k]);k++);
        if(!f[k] && !id[k])return i;
    }
    return -1;
}
/* faction A's reaction toward B (0 when A does not list B) */
static int reaction_of(const aw_dial_t *d,int a,int b) {
    int i;
    for(i=0;i<d->reactions;i++)
        if(d->reaction[4*i]==a && d->reaction[4*i+1]==b)return (short)rd16(d->reaction+4*i+2);
    return 0;
}
int AW_DialDisposition(const aw_dial_t *d,const aw_dial_facts_t *f,int clamp) {
    float x=(float)f->base,reaction=0;int rank=0,own=faction_index(d,f->faction),expelled=0,r,i,first=1,v;
    if(f->same_race)x+=AW_DialSetting(d,AW_DIAL_SET_RACE);
    x+=AW_DialSetting(d,AW_DIAL_SET_PERSONALITY_MULT)*(f->personality-AW_DialSetting(d,AW_DIAL_SET_PERSONALITY_BASE));
    if(f->faction && *f->faction && f->rank && (r=f->rank(f->faction,&expelled))>=0){
        /* a member of the NPC's own faction: its reaction toward itself and the player's rank, unless expelled */
        if(!expelled && own>=0){reaction=(float)reaction_of(d,own,own);rank=r;}
    }else if(f->faction && *f->faction && f->rank){
        /* else the lowest reaction of the NPC's faction toward a faction the player belongs to (not expelled) */
        for(i=0;i<d->factions;i++){
            expelled=0;
            if((r=f->rank((const char *)d->faction+AW_DIAL_FACTION_ID*i,&expelled))<0 || expelled)continue;
            v=own>=0?reaction_of(d,own,i):0;
            if(first || v<reaction){reaction=(float)v;rank=r;first=0;}
        }
    }
    x+=(AW_DialSetting(d,AW_DIAL_SET_FACTION_RANK_MULT)*rank+AW_DialSetting(d,AW_DIAL_SET_FACTION_RANK_BASE))*
       AW_DialSetting(d,AW_DIAL_SET_FACTION_MOD)*reaction;
    x-=AW_DialSetting(d,AW_DIAL_SET_CRIME)*f->bounty;
    if(f->diseased)x+=AW_DialSetting(d,AW_DIAL_SET_DISEASE);
    if(f->weapon_drawn)x+=AW_DialSetting(d,AW_DIAL_SET_WEAPON_DRAWN);
    v=(int)x;
    if(clamp)v=v<0?0:v>100?100:v;
    return v;
}

long AW_DialRankAt(const aw_dial_t *d,const char *faction,int rank) {
    int i=faction_index(d,faction);
    if(i<0 || rank<0 || rank>=AW_DIAL_RANKS)return -1;
    return d->at_ranks+(long)AW_DIAL_FACTION_ID*((long)i*AW_DIAL_RANKS+rank);
}
static int starts_ci(const char *p,const char *word) {
    for(;*word;p++,word++)if(lower_c((unsigned char)*p)!=*word)return 0;
    return 1;
}
void AW_DialFillDefines(const char *p,char *out,int capacity,const char *pc_rank,const char *next_rank,
                        const char *cell) {
    static const char *const word[]={"nextpcrank","pcrank","cell"};
    int n=0,k;
    if(capacity<=0)return;
    while(*p && n<capacity-1){
        const char *put=NULL;int skip=0;
        if(*p=='%')for(k=0;k<3;k++)if(starts_ci(p+1,word[k])){
            put=k==0?next_rank:k==1?pc_rank:cell;skip=1+(int)strlen(word[k]);break;}
        if(skip){
            for(put=put?put:"";*put && n<capacity-1;)out[n++]=*put++;
            p+=skip;continue;
        }
        out[n++]=*p++;
    }
    out[n]=0;
}

int AW_DialStartTopic(const aw_dial_t *d,int i) {
    return !d->data || i<0 || i>=d->starts?-1:(int)rd16(d->start+2*i);
}
void AW_DialKnownStart(const aw_dial_t *d,unsigned char *known) {
    int i;
    memset(known,0,(size_t)AW_DialKnownBytes(d));
    for(i=0;i<d->starts;i++)AW_DialKnow(d,known,AW_DialStartTopic(d,i));
}
void AW_DialKnow(const aw_dial_t *d,unsigned char *known,int topic) {
    if(topic>=0 && topic<d->topics)known[topic>>3]|=(unsigned char)(1<<(topic&7));
}
int AW_DialKnows(const aw_dial_t *d,const unsigned char *known,int topic) {
    return topic>=0 && topic<d->topics && (known[topic>>3]>>(topic&7)&1);
}

int AW_DialTopicKind(const aw_dial_t *d,int topic) {
    return !d->data || topic<0 || topic>=d->topics?-1:d->topic[AW_DIAL_TOPIC_ROW*topic+5];
}
long AW_DialTopicName(const aw_dial_t *d,int topic,int *length) {
    const unsigned char *r;
    if(!d->data || topic<0 || topic>=d->topics)return -1;
    r=d->topic+AW_DIAL_TOPIC_ROW*topic;
    if(length)*length=r[4];
    return d->at_tstrings+(long)rd32(r);
}

/* A buffer cut into aligned pieces from the front (the answers: one array) and from the back (their conditions). */
typedef struct {unsigned char *at;long left;} arena_t;
static long pad8(long n) {return (n+7)&~7L;}  /* every piece aligned for its pointers (the buffer's start is) */
static void *take(arena_t *a,long bytes) {
    void *p;
    bytes=pad8(bytes);
    if(bytes<0 || bytes>a->left)return NULL;
    p=a->at;a->at+=bytes;a->left-=bytes;
    return p;
}
static void *take_back(arena_t *a,long bytes) {
    bytes=pad8(bytes);
    if(bytes<0 || bytes>a->left)return NULL;
    a->left-=bytes;
    return a->at+a->left;
}

int AW_DialConverse(aw_dial_conv_t *c,const aw_dial_t *d,int npc,const aw_glut_cond_t *speaker,
                    aw_dial_read_t read,void *user,unsigned char *buffer,long bytes) {
    arena_t a;unsigned char *conv,head[4],*pairs;unsigned long row;int k,count;long i;
    memset(c,0,sizeof(*c));
    c->d=d;c->npc=npc;
    if(!d->data || npc<0 || npc>=d->npcs || !read || !buffer)return 0;
    a.at=buffer;a.left=bytes&~7L;
    /* the table's globals and names: what the condition records of this table name */
    if(!(conv=(unsigned char *)take(&a,d->conversation_bytes)) || !read(user,d->at_conversation,conv,d->conversation_bytes))
        return 0;
    if(conv[d->conversation_bytes-1])return 0;   /* the string block ends in a NUL */
    if(speaker)c->cond=*speaker;else{memset(&c->cond,0,sizeof(c->cond));c->cond.rank=-1;c->cond.speaker=-1;}
    c->cond.global=conv;c->cond.globals=d->globals;
    c->cond.name=conv+8*d->globals;c->cond.names=d->names;
    c->cond.strings=conv+8*d->globals+4*d->names;
    c->cond.fixture=d->fixture;c->cond.known=d->known;c->cond.functions=(int)d->functions;
    c->cond.choice=-1;c->cond.local_slots=1;
    for(i=0;i<d->globals;i++)if(rd32(conv+8*i)>=(unsigned long)d->string_bytes)return 0;
    for(i=0;i<d->names;i++)if(rd32(c->cond.name+4*i)>=(unsigned long)d->string_bytes)return 0;
    row=rd32(d->npc_offset+4*npc);
    if(row==AW_DIAL_NONE32)return 1;               /* an NPC with nothing to talk about */
    if(!read(user,d->at_rows+(long)row,head,4))return 0;
    count=(int)rd16(head);
    if(count>AW_DIAL_MAX_TOPICS || row+4+4ul*count>(unsigned long)d->row_bytes)return 0;
    if(!(pairs=(unsigned char *)take(&a,4L*count)) || !read(user,d->at_rows+(long)row+4,pairs,4L*count))return 0;
    /* the answers are cut from the buffer's top, after the pairs; the pairs are read before they are passed over */
    c->answer=(aw_dial_answer_t *)a.at;
    for(k=0;k<count;k++){
        unsigned topic=rd16(pairs+4*k),ls=rd16(pairs+4*k+2),n,m;unsigned char lsrow[8],items[4*AW_DIAL_MAX_MERGE];
        unsigned long merged[256];int nmerged=0,j;
        if((long)topic>=d->topics || (long)ls>=d->listsets)return 0;
        if(!read(user,d->at_listsets+8L*ls,lsrow,8))return 0;
        n=rd16(lsrow+4);
        if(!n || n>AW_DIAL_MAX_MERGE || rd32(lsrow)+n>(unsigned long)d->listset_items)return 0;
        if(!read(user,d->at_listset_items+4L*(long)rd32(lsrow),items,4L*n))return 0;
        for(m=0;m<n;m++){
            unsigned long list=rd32(items+4*m);unsigned char lrow[8],e[4];unsigned len,q;
            if(list>=(unsigned long)d->lists || !read(user,d->at_lists+8L*(long)list,lrow,8))return 0;
            len=rd16(lrow+4);
            if(!len || rd32(lrow)+len>(unsigned long)d->list_items)return 0;
            for(q=0;q<len;q++){
                unsigned long entry;int at;
                if(!read(user,d->at_list_items+4L*(long)(rd32(lrow)+q),e,4))return 0;
                entry=rd32(e);
                if(entry>=(unsigned long)d->entries)return 0;
                if(nmerged>=(int)(sizeof(merged)/sizeof(merged[0])))return 0;
                /* insertion in the original's order (entries are numbered in it; each is in one list only) */
                for(at=nmerged;at>0 && merged[at-1]>entry;at--)merged[at]=merged[at-1];
                merged[at]=entry;nmerged++;
            }
        }
        c->topic[k].topic=(unsigned short)topic;
        c->topic[k].first=(unsigned short)c->answers;
        for(j=0;j<nmerged;j++){
            unsigned char r[AW_DIAL_ENTRY_ROW];aw_dial_answer_t *ans;unsigned char *cond;
            if(!read(user,d->at_entries+(long)AW_DIAL_ENTRY_ROW*(long)merged[j],r,AW_DIAL_ENTRY_ROW))return 0;
            if(!(ans=(aw_dial_answer_t *)take(&a,sizeof(aw_dial_answer_t))))return 0;
            c->answers++;
            ans->entry=merged[j];ans->text=rd32(r);ans->script=rd32(r+8);ans->link=rd32(r+12);
            ans->links=(unsigned short)rd16(r+16);ans->conditions=r[18];ans->flags=r[19];ans->cond=NULL;
            if(rd32(r+4)+ans->conditions>(unsigned long)d->conds ||
               (ans->text!=AW_DIAL_NONE32 && ans->text>=(unsigned long)d->text_bytes) ||
               (ans->script!=AW_DIAL_NONE32 && ans->script>=(unsigned long)d->script_bytes) ||
               (ans->link!=AW_DIAL_NONE32 && ans->link+ans->links>(unsigned long)d->links))return 0;
            if(ans->conditions){
                /* the answers stay one array at the front; their conditions are cut from the back */
                if(!(cond=(unsigned char *)take_back(&a,8L*ans->conditions)))return 0;
                if(!read(user,d->at_conds+8L*(long)rd32(r+4),cond,8L*ans->conditions))return 0;
                ans->cond=cond;
            }
            if(ans->flags&AW_DIAL_ENTRY_LAST)break;
        }
        c->topic[k].count=(unsigned short)(c->answers-c->topic[k].first);
    }
    c->topics=count;
    return 1;
}

int AW_DialFind(const aw_dial_conv_t *c,int topic) {
    int low=0,high=c->topics-1;
    while(low<=high){                /* the row lists its topics in the table's order */
        int mid=(low+high)/2;
        if(c->topic[mid].topic==topic)return mid;
        if(c->topic[mid].topic<topic)low=mid+1;else high=mid-1;
    }
    return -1;
}

int AW_DialPick(const aw_dial_conv_t *c,int topic,const aw_glut_state_t *s,int *refused) {
    int k=AW_DialFind(c,topic),i;
    if(refused)*refused=0;
    if(k<0)return -1;
    for(i=c->topic[k].first;i<c->topic[k].first+c->topic[k].count;i++){
        const aw_dial_answer_t *a=&c->answer[i];int n,other=1,disposition=1;
        /* every test, the disposition one apart (OpenMW Filter::search: an answer that failed only on it sends
         * the player to Info Refusal) */
        for(n=0;n<a->conditions && other;n++){
            const unsigned char *r=a->cond+8*n;
            if(r[0]==AW_GLUT_OP_DISP)disposition=AW_GlutCond(&c->cond,r,s);
            else other=AW_GlutCond(&c->cond,r,s);
        }
        if(other && disposition)return i;
        if(other && refused)*refused=1;
    }
    return -1;
}

int AW_DialTopicList(const aw_dial_conv_t *c,const unsigned char *known,const aw_glut_state_t *s,int *out,int max) {
    int k,n=0,refused;
    for(k=0;k<c->topics && n<max;k++){
        int topic=c->topic[k].topic;
        if(AW_DialTopicKind(c->d,topic)!=AW_DIAL_KIND_TOPIC || !AW_DialKnows(c->d,known,topic))continue;
        if(AW_DialPick(c,topic,s,&refused)>=0 || refused)out[n++]=topic;
    }
    return n;
}

int AW_DialAnswer(const aw_dial_conv_t *c,int topic,const aw_glut_state_t *s) {
    int refused,got=AW_DialPick(c,topic,s,&refused);
    if(got>=0 || !refused || c->d->info_refusal<0 || topic==c->d->info_refusal)return got;
    return AW_DialPick(c,c->d->info_refusal,s,NULL);
}

long AW_DialTextAt(const aw_dial_conv_t *c,int answer) {
    if(answer<0 || answer>=c->answers || c->answer[answer].text==AW_DIAL_NONE32)return -1;
    return c->d->at_texts+(long)c->answer[answer].text;
}
long AW_DialScriptAt(const aw_dial_conv_t *c,int answer) {
    if(answer<0 || answer>=c->answers || c->answer[answer].script==AW_DIAL_NONE32)return -1;
    return c->d->at_scripts+(long)c->answer[answer].script;
}
int AW_DialWrapNext(const char **text,int cols,char *out,int capacity) {
    const char *p=*text;int n=0,cut=-1;
    if(!p || !*p || cols<1 || capacity<=cols)return 0;
    while(p[n] && p[n]!='\n' && n<cols){if(p[n]==' ')cut=n;n++;}
    if(p[n] && p[n]!='\n' && p[n]!=' ' && cut>0)n=cut;     /* the word does not fit: break at the last space */
    memcpy(out,p,(size_t)n);out[n]=0;
    p+=n;
    if(*p=='\n' || *p==' ')p++;                           /* the line end or the space it broke at */
    *text=p;
    return 1;
}

int AW_DialLinks(const aw_dial_conv_t *c,int answer,aw_dial_read_t read,void *user,unsigned short *out,int max) {
    unsigned char raw[2];int n,k;const aw_dial_answer_t *a;
    if(answer<0 || answer>=c->answers || !read)return 0;
    a=&c->answer[answer];
    if(a->link==AW_DIAL_NONE32)return 0;
    n=a->links<max?a->links:max;
    for(k=0;k<n;k++){
        if(!read(user,c->d->at_links+2L*(long)(a->link+k),raw,2))return k;
        out[k]=(unsigned short)rd16(raw);
    }
    return n;
}
