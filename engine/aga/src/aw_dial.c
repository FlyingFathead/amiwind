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
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "aw_dial.h"
#include "aw_textdef.h"
#include "aw_tryalloc.h"

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

const char *AW_DialRefusal(const unsigned char *h,long file_size,int *version_out) {
    if(version_out)*version_out=0;
    if(!h || file_size<AW_DIAL_HEADER || memcmp(h,"AWDL",4))return "not a dialogue table";
    if(version_out)*version_out=(int)rd16(h+4);
    if(rd16(h+4)!=AW_DIAL_VERSION)return "another format version";
    if(AW_DialResidentSize(h,file_size)<0)return "a header that does not fit the file";
    return "";
}
long AW_DialResidentSize(const unsigned char *h,long file_size) {
    long size;
    if(!h || file_size<AW_DIAL_HEADER || memcmp(h,"AWDL",4) || rd16(h+4)!=AW_DIAL_VERSION)return -1;
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
    d->at_links=at;at+=pad4(AW_DIAL_LINK_ROW*d->links);
    d->at_quests=at;at+=AW_DIAL_QUEST_ROW*d->quests;
    d->at_journal=at;at+=AW_DIAL_JOURNAL_ROW*d->journal;
    d->at_ranks=at;at+=(long)AW_DIAL_FACTION_ID*AW_DIAL_RANKS*rd16(h+H_FACTIONS);
    d->at_tstrings=at;at+=d->tstring_bytes;
    d->at_scripts=at;at+=d->script_bytes;
    d->at_texts=at;at+=d->text_bytes;
    d->at_services=at;at+=4L*d->npcs;           /* the NPCs' service flags (one 32-bit word each) */
    d->at_skill_attributes=at;at+=pad4(AW_DIAL_SKILLS);   /* the skills' governing attributes */
    d->at_ui_texts=at;at+=(long)AW_DIAL_UI_TEXT*AW_DIAL_TEXTS;   /* the window's words (GMST) */
    d->at_rank_reqs=at;at+=(long)AW_DIAL_RANK_REQ*rd16(h+H_FACTIONS);   /* the factions' rank requirements, last */
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
/* The scripts' changes of faction reactions (ModFactionReaction, SetFactionReaction; OpenMW DialogueManager::
 * modFactionReaction: faction A's reaction toward B, kept for the game and saved): by folded faction ids, bounded */
#define REACTION_CHANGES 32
static struct {char a[AW_DIAL_FACTION_ID],b[AW_DIAL_FACTION_ID];int set,value;} changes[REACTION_CHANGES];
static int nchanges;
static int same_id(const char *x,const char *y){
    while(*x && (*x|32)==(*y|32)){x++;y++;}
    return !*x && !*y;
}
void AW_DialReactionsReset(void){nchanges=0;}
int AW_DialReactionChange(const char *a,const char *b,int value,int set) {
    int i;
    if(!a || !b || strlen(a)>=AW_DIAL_FACTION_ID || strlen(b)>=AW_DIAL_FACTION_ID)return 0;
    for(i=0;i<nchanges;i++)if(same_id(changes[i].a,a) && same_id(changes[i].b,b))break;
    if(i==nchanges){
        if(nchanges==REACTION_CHANGES)return 0;
        strcpy(changes[i].a,a);strcpy(changes[i].b,b);changes[i].set=0;changes[i].value=0;nchanges++;
    }
    if(set){changes[i].set=1;changes[i].value=value;}else changes[i].value+=value;
    return 1;
}
static int reaction_of(const aw_dial_t *d,int a,int b) {
    int i,base=0;const char *na=(const char *)d->faction+AW_DIAL_FACTION_ID*a,*nb=(const char *)d->faction+AW_DIAL_FACTION_ID*b;
    for(i=0;i<d->reactions;i++)
        if(d->reaction[4*i]==a && d->reaction[4*i+1]==b){base=(short)rd16(d->reaction+4*i+2);break;}
    for(i=0;i<nchanges;i++)
        if(same_id(changes[i].a,na) && same_id(changes[i].b,nb))return changes[i].set?changes[i].value:base+changes[i].value;
    return base;
}
/* saved: "AWFR" u8 rows, each u8 a length, a, u8 b length, b, u8 set, i32 value. Bytes written, -1 no room. */
int AW_DialReactionsExport(unsigned char *out,int capacity) {
    int i,at=5,need=5;
    for(i=0;i<nchanges;i++)need+=7+(int)strlen(changes[i].a)+(int)strlen(changes[i].b);
    if(need>capacity)return -1;
    memcpy(out,"AWFR",4);out[4]=(unsigned char)nchanges;
    for(i=0;i<nchanges;i++){
        int la=(int)strlen(changes[i].a),lb=(int)strlen(changes[i].b);uint32_t v=(uint32_t)changes[i].value;
        out[at]=(unsigned char)la;memcpy(out+at+1,changes[i].a,(size_t)la);at+=1+la;
        out[at]=(unsigned char)lb;memcpy(out+at+1,changes[i].b,(size_t)lb);at+=1+lb;
        out[at]=(unsigned char)changes[i].set;out[at+1]=(unsigned char)(v>>24);out[at+2]=(unsigned char)(v>>16);
        out[at+3]=(unsigned char)(v>>8);out[at+4]=(unsigned char)v;at+=5;
    }
    return at;
}
int AW_DialReactionsImport(const unsigned char *p,int bytes) {
    int i,n,at=5;char a[AW_DIAL_FACTION_ID],b[AW_DIAL_FACTION_ID];
    nchanges=0;
    if(!p || bytes<5 || memcmp(p,"AWFR",4))return -1;
    n=p[4];
    for(i=0;i<n;i++){
        int la,lb,set;int32_t v;
        if(at+1>bytes || (la=p[at])>=AW_DIAL_FACTION_ID || at+1+la+1>bytes)goto bad;
        memcpy(a,p+at+1,(size_t)la);a[la]=0;at+=1+la;
        if((lb=p[at])>=AW_DIAL_FACTION_ID || at+1+lb+5>bytes)goto bad;
        memcpy(b,p+at+1,(size_t)lb);b[lb]=0;at+=1+lb;
        set=p[at];v=(int32_t)rd32(p+at+1);at+=5;
        if(!AW_DialReactionChange(a,b,v,set))goto bad;
    }
    return at;
bad:
    nchanges=0;return -1;
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
    x+=f->charm;                   /* Charm's magnitude on the NPC (getDerivedDisposition adds it last) */
    v=(int)x;
    if(clamp)v=v<0?0:v>100?100:v;
    return v;
}
static int same_id_ci(const char *a,const char *b) {
    for(;*a && *b;a++,b++){
        int x=*a>='A' && *a<='Z'?*a+32:*a,y=*b>='A' && *b<='Z'?*b+32:*b;
        if(x!=y)return 0;
    }
    return !*a && !*b;
}
int AW_DialPairFunction(const aw_dial_pair_t *p,unsigned fn,long *out) {
    if(!p || !p->known || !out)return 0;
    switch(fn){
    case AW_DIAL_FN_SAME_SEX:*out=(p->player_female!=0)==(p->speaker_female!=0);return 1;
    case AW_DIAL_FN_SAME_RACE:*out=p->player_race && p->speaker_race && *p->player_race &&
                                   same_id_ci(p->player_race,p->speaker_race);return 1;
    case AW_DIAL_FN_SHOULD_ATTACK:
        if(p->fight_rating<0)return 0;
        *out=p->fight_rating>=100;return 1;
    }
    return 0;
}

long AW_DialRankAt(const aw_dial_t *d,const char *faction,int rank) {
    int i=faction_index(d,faction);
    if(i<0 || rank<0 || rank>=AW_DIAL_RANKS)return -1;
    return d->at_ranks+(long)AW_DIAL_FACTION_ID*((long)i*AW_DIAL_RANKS+rank);
}
/* the section's row: u8 attribute x2, u8 skill x7 (255 none), 3 zeros, then per rank s16 attribute 1, attribute 2,
 * first skill, second skill, faction reputation */
int AW_DialRankRequirement(const aw_dial_t *d,const char *faction,int rank,const short *attributes,const short *skills,
                           int reputation,aw_dial_read_t read,void *user) {
    unsigned char r[AW_DIAL_RANK_REQ];int i=faction_index(d,faction),next=rank<0?0:rank+1,best=-1,second=-1,ok=1,k,s,result=0;
    const unsigned char *q;
    if(i<0 || next>=AW_DIAL_RANKS || !read || !attributes || !skills ||
       !read(user,d->at_rank_reqs+(long)AW_DIAL_RANK_REQ*i,r,AW_DIAL_RANK_REQ))return 0;
    q=r+12+10*next;
    for(k=0;k<2;k++)if(r[k]<8 && attributes[r[k]]<(short)rd16(q+2*k))ok=0;
    for(k=0;k<7;k++){
        if(r[2+k]>=AW_DIAL_SKILLS)continue;
        s=skills[r[2+k]];
        if(s>best){second=best;best=s;}else if(s>second)second=s;
    }
    if(ok && best>=0){                 /* no favoured skill: met */
        if(best<(short)rd16(q+4))ok=0;
        else if(second>=0 && second<(short)rd16(q+6))ok=0;
    }
    if(ok)result|=1;
    if(reputation>=(short)rd16(q+8))result|=2;
    return result;
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

static void ratings(const aw_dial_t *d,const aw_dial_person_t *w,int player,float *r1,float *r2,float *r3) {
    float pm=AW_DialSetting(d,AW_DIAL_SET_PERSONALITY_MOD),lm=AW_DialSetting(d,AW_DIAL_SET_LUCK_MOD);
    float pers=pm!=0?w->personality/pm:0,luck=lm!=0?w->luck/lm:0,rep=w->reputation*AW_DialSetting(d,AW_DIAL_SET_REPUTATION_MOD);
    float rested=w->fatigue>0?w->fatigue:0;
    float fatigue=AW_DialSetting(d,AW_DIAL_SET_FATIGUE_BASE)-AW_DialSetting(d,AW_DIAL_SET_FATIGUE_MULT)*(1-rested);
    float level=w->level*AW_DialSetting(d,AW_DIAL_SET_LEVEL_MOD);
    *r1=(rep+luck+pers+w->speechcraft)*fatigue;
    if(player){*r2=*r1+level;*r3=(w->mercantile+luck+pers)*fatigue;}
    else{*r2=(level+rep+luck+pers+w->speechcraft)*fatigue;*r3=(w->mercantile+rep+luck+pers)*fatigue;}
}
static int clamp100(int v){return v<0?0:v>100?100:v;}
/* OpenMW MechanicsManager::getBarterOffer (our own code): the price an NPC asks (BUYING: the player buys) or gives */
int AW_DialBarterOffer(const aw_dial_t *d,int base,int buying,const aw_dial_person_t *player,const aw_dial_person_t *npc,
                       int disposition) {
    float a,b,c,e,f,g,pc,np,term,pf,nf;int offer;
    if(base==0)return 0;
    pf=AW_DialSetting(d,AW_DIAL_SET_FATIGUE_BASE)-AW_DialSetting(d,AW_DIAL_SET_FATIGUE_MULT)*(1-(player->fatigue>0?player->fatigue:0));
    nf=AW_DialSetting(d,AW_DIAL_SET_FATIGUE_BASE)-AW_DialSetting(d,AW_DIAL_SET_FATIGUE_MULT)*(1-(npc->fatigue>0?npc->fatigue:0));
    a=player->mercantile<100?player->mercantile:100;
    b=0.1f*player->luck;if(b>10)b=10;
    c=0.2f*player->personality;if(c>10)c=10;
    e=npc->mercantile<100?npc->mercantile:100;
    f=0.1f*npc->luck;if(f>10)f=10;
    g=0.2f*npc->personality;if(g>10)g=10;
    pc=((float)(disposition-50)+a+b+c)*pf;
    np=(e+f+g)*nf;
    term=buying?0.01f*(100-0.5f*(pc-np)):0.01f*(50-0.5f*(np-pc));
    offer=(int)((float)base*term);
    return offer>1?offer:1;
}
/* OpenMW TrainingWindow: the NPC's three best skills (by value, ties to the earlier skill) */
int AW_DialTrainingPicks(const float *skills,int count,int *out) {
    int n=0,i,k,j;
    for(i=0;i<count;i++){
        for(k=0;k<n && skills[out[k]]>=skills[i];k++);
        if(k>=3)continue;
        for(j=(n<3?n:2);j>k;j--)out[j]=out[j-1];
        out[k]=i;if(n<3)n++;
    }
    return n;
}
int AW_DialSpellPrice(const aw_dial_t *d,int cost,const aw_dial_person_t *player,const aw_dial_person_t *npc,
                      int disposition) {
    int price=(int)((float)cost*AW_DialSetting(d,AW_DIAL_SET_SPELL_VALUE_MULT));
    return AW_DialBarterOffer(d,price>1?price:1,1,player,npc,disposition);
}
int AW_DialRepairPrice(const aw_dial_t *d,int value,int max,int durability,const aw_dial_person_t *player,
                       const aw_dial_person_t *npc,int disposition) {
    float p=(float)(value>1?value:1),r;int x;
    x=(int)((float)max/p);r=(float)(x>1?x:1);
    x=(int)((float)(max-durability)/r);
    x=(int)(AW_DialSetting(d,AW_DIAL_SET_REPAIR_MULT)*(float)x);
    return AW_DialBarterOffer(d,x>1?x:1,1,player,npc,disposition);
}
float AW_DialEffectCostPlayer(const aw_dial_t *d,const aw_dial_effect_t *e) {
    int lo=e->flags&AW_DIAL_MGEF_NO_MAGNITUDE?1:e->magnitude_min,hi=e->flags&AW_DIAL_MGEF_NO_MAGNITUDE?1:e->magnitude_max;
    int duration=e->flags&AW_DIAL_MGEF_NO_DURATION?1:e->duration,area=e->area>1?e->area:1;
    float x;
    if(lo<1)lo=1;
    if(hi<1)hi=1;
    if(!(e->flags&AW_DIAL_MGEF_APPLIED_ONCE) && duration<1)duration=1;
    x=0.5f*(float)(lo+hi);
    x*=0.1f*e->base_cost;
    x*=(float)(1+duration);                          /* the player-spell method: duration offset 1 */
    x+=0.05f*(float)area*e->base_cost;              /* and an area of at least 1 */
    return x*AW_DialSetting(d,AW_DIAL_SET_EFFECT_COST_MULT);
}
/* OpenMW keeps the running total and multiplies it all by 1.5 at each effect on target (as the original) */
static float spellmaking_total(const aw_dial_t *d,const aw_dial_effect_t *e,int count) {
    float y=0,c;int i;
    for(i=0;i<count;i++){
        c=AW_DialEffectCostPlayer(d,&e[i]);
        y+=c>1?c:1;
        if(e[i].range==AW_DIAL_RANGE_TARGET)y*=1.5f;
    }
    return y;
}
int AW_DialSpellmakingCost(const aw_dial_t *d,const aw_dial_effect_t *e,int count) {return (int)spellmaking_total(d,e,count);}
int AW_DialSpellmakingPrice(const aw_dial_t *d,const aw_dial_effect_t *e,int count,const aw_dial_person_t *player,
                            const aw_dial_person_t *npc,int disposition) {
    int price;
    if(count<=0)return 0;
    price=(int)(spellmaking_total(d,e,count)*AW_DialSetting(d,AW_DIAL_SET_SPELLMAKING_VALUE_MULT));
    return AW_DialBarterOffer(d,price>1?price:1,1,player,npc,disposition);
}
int AW_DialEnchantCosts(const aw_dial_t *d,const aw_dial_effect_t *e,int count,int constant,float *out) {
    float cost=0,duration,mult=AW_DialSetting(d,AW_DIAL_SET_EFFECT_COST_MULT);int i,lo,hi,area;
    for(i=0;i<count;i++){
        lo=e[i].magnitude_min>1?e[i].magnitude_min:1;hi=e[i].magnitude_max>1?e[i].magnitude_max:1;
        area=e[i].area>1?e[i].area:1;
        duration=constant?AW_DialSetting(d,AW_DIAL_SET_ENCHANT_CONSTANT_DURATION_MULT):(float)e[i].duration;
        cost+=((float)(lo+hi)*duration+(float)area)*e[i].base_cost*mult*0.05f;
        if(cost<1)cost=1;
        if(e[i].range==AW_DIAL_RANGE_TARGET)cost*=1.5f;
        if(out)out[i]=cost;
    }
    return count;
}
float AW_DialEnchantPoints(const aw_dial_t *d,const aw_dial_effect_t *e,int count,int constant,int precise) {
    float costs[16],sum=0;int i,n=count<16?count:16;
    AW_DialEnchantCosts(d,e,n,constant,costs);
    for(i=0;i<n;i++)sum+=precise?costs[i]:(float)floor(costs[i]);
    return sum;
}
int AW_DialEnchantCastCost(const aw_dial_t *d,const aw_dial_effect_t *e,int count,int constant,float enchant_skill) {
    float c,r;
    if(constant)return 0;
    c=(float)(int)AW_DialEnchantPoints(d,e,count,constant,0);
    r=c-(c/100)*(enchant_skill-10);
    return (int)(r<1?1:r);
}
int AW_DialEnchantPrice(const aw_dial_t *d,const aw_dial_effect_t *e,int count,int constant,
                        const aw_dial_person_t *player,const aw_dial_person_t *npc,int disposition) {
    float costs[16];int n=count<16?count:16,price;
    if(n<=0)return 1;
    AW_DialEnchantCosts(d,e,n,constant,costs);
    price=AW_DialBarterOffer(d,(int)(costs[n-1]*AW_DialSetting(d,AW_DIAL_SET_ENCHANT_VALUE_MULT)),1,player,npc,disposition);
    return price>1?price:1;                          /* one item, the type multiplier 1 */
}
int AW_DialEnchantChance(const aw_dial_t *d,const aw_dial_effect_t *e,int count,int constant,float enchant_skill,
                         float intelligence,float luck,float fatigue) {
    float term=AW_DialSetting(d,AW_DIAL_SET_FATIGUE_BASE)-AW_DialSetting(d,AW_DIAL_SET_FATIGUE_MULT)*(1-(fatigue>0?fatigue:0));
    float x=(enchant_skill-AW_DialEnchantPoints(d,e,count,constant,1)*AW_DialSetting(d,AW_DIAL_SET_ENCHANT_CHANCE_MULT)
             +0.2f*intelligence+0.1f*luck)*term;
    if(constant)x*=AW_DialSetting(d,AW_DIAL_SET_ENCHANT_CONSTANT_CHANCE_MULT);
    return (int)x;
}
int AW_DialNextCastStyle(int item,int style,int soul,const aw_dial_t *d) {
    int powerful=(float)soul>=AW_DialSetting(d,AW_DIAL_SET_SOUL_FOR_CONSTANT);
    if(item==AW_DIAL_ENCHANT_WORN)return style==2 && powerful?3:2;   /* armour, clothing: when used, constant */
    if(item==AW_DIAL_ENCHANT_WEAPON){                                 /* a melee weapon: strikes, used, constant */
        if(style==1)return 2;
        if(style==2)return powerful?3:1;
        return 1;
    }
    return 0;                                                          /* a book (a scroll): cast once */
}
int AW_DialEnchantCapacity(const aw_dial_t *d,float item_points) {return (int)(item_points*AW_DialSetting(d,AW_DIAL_SET_ENCHANT_MULT));}
/* the price of training a skill of base value SKILL (OpenMW: iTrainingMod x the base, at least 1, then the offer) */
int AW_DialTrainingPrice(const aw_dial_t *d,int skill,const aw_dial_person_t *player,const aw_dial_person_t *npc,
                         int disposition) {
    int price=(int)((float)skill*AW_DialSetting(d,AW_DIAL_SET_TRAINING_MOD));
    return AW_DialBarterOffer(d,price>1?price:1,1,player,npc,disposition);
}
void AW_DialPersuade(const aw_dial_t *d,int kind,const aw_dial_person_t *player,const aw_dial_person_t *npc,
                     int disposition,int roll,int fight,int flee,aw_dial_persuasion_t *out) {
    float p1,p2,p3,n1,n2,n3,dd,t1,t2,t3,bribe,x=0,y=0,c,r,s;
    float min_chance=AW_DialSetting(d,AW_DIAL_SET_PER_MIN_CHANCE),min_change=AW_DialSetting(d,AW_DIAL_SET_PER_MIN_CHANGE);
    float roll_mult=AW_DialSetting(d,AW_DIAL_SET_PER_DIE_ROLL_MULT),temp_mult=AW_DialSetting(d,AW_DIAL_SET_PER_TEMP_MULT);
    int success,temp;
    ratings(d,player,1,&p1,&p2,&p3);ratings(d,npc,0,&n1,&n2,&n3);
    dd=1-0.02f*(float)(disposition>50?disposition-50:50-disposition);
    t1=dd*(p1-n1+50);t2=dd*(p2-n2+50);
    bribe=AW_DialSetting(d,kind==AW_PERSUADE_BRIBE10?AW_DIAL_SET_BRIBE10:kind==AW_PERSUADE_BRIBE100?AW_DIAL_SET_BRIBE100:
                       AW_DIAL_SET_BRIBE1000);
    t3=dd*(p3-n3+50)+bribe;
    if(kind==AW_PERSUADE_ADMIRE){
        if(t1<min_chance)t1=min_chance;
        success=(float)roll<=t1;
        c=(float)floor(roll_mult*(t1-(float)roll));
        x=success && c<min_change?min_change:c;
    }else if(kind==AW_PERSUADE_INTIMIDATE){
        if(t2<min_chance)t2=min_chance;
        success=(float)roll<=t2;
        r=(float)roll!=t2?(float)floor(t2-(float)roll):1;
        if(success){
            s=(float)floor(r*roll_mult*temp_mult);
            flee=clamp100(flee+(int)(s>min_change?s:min_change));
            fight=clamp100(fight+(int)(-s<-min_change?-s:-min_change));
        }
        c=(float)floor(r*roll_mult);if(c>0)c=-c;
        if(success){
            if((c<0?-c:c)<min_change){x=min_change;y=x;}
            else{x=-(float)floor(c*temp_mult);y=c;}
        }else{x=(float)floor(c*temp_mult);y=c;}
    }else if(kind==AW_PERSUADE_TAUNT){
        if(t1<min_chance)t1=min_chance;
        success=(float)roll<=t1;
        c=(float)floor(t1-(float)roll);if(c<0)c=-c;
        if(success){
            int a,b;
            s=c*roll_mult*temp_mult;
            a=-(int)min_change;b=(int)(-s);flee=clamp100(flee+(a<b?a:b));
            a=(int)min_change;b=(int)s;fight=clamp100(fight+(a>b?a:b));
        }
        x=(float)floor(-c*roll_mult);
        if(success && (x<0?-x:x)<min_change)x=-min_change;
    }else{
        if(t3<min_chance)t3=min_chance;
        success=(float)roll<=t3;
        c=(float)floor((t3-(float)roll)*roll_mult);
        x=success && c<min_change?min_change:c;
    }
    temp=kind==AW_PERSUADE_INTIMIDATE?(int)x:(int)(x*temp_mult);
    if(disposition+temp>100)temp=100-disposition;
    else if(disposition+temp<0)temp=-disposition;
    out->success=success;out->temp=temp;out->fight=fight;out->flee=flee;
    if(temp_mult==0)out->perm=0;
    else if(kind==AW_PERSUADE_INTIMIDATE)out->perm=success?-(int)((float)temp/temp_mult):(int)y;
    else out->perm=(int)((float)temp/temp_mult);
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

int AW_DialGreeting(const aw_dial_conv_t *c,const aw_glut_state_t *s,int *topic) {
    int k;
    if(topic)*topic=-1;
    for(k=0;k<c->topics;k++){        /* the row's topics are in the table's order: Greeting 0 before Greeting 1 */
        int t=c->topic[k].topic,got;
        if(AW_DialTopicKind(c->d,t)!=AW_DIAL_KIND_GREETING)continue;
        if((got=AW_DialPick(c,t,s,NULL))>=0){if(topic)*topic=t;return got;}
    }
    return -1;
}

unsigned long AW_DialNameHash(const char *name,int length) {
    unsigned long h=2166136261ul;int i;
    for(i=0;i<length && name[i];i++){
        unsigned char ch=(unsigned char)name[i];
        if(ch>='A' && ch<='Z')ch=(unsigned char)(ch+32);
        h=((h^ch)*16777619ul)&0xFFFFFFFFul;
    }
    return h;
}
/* DIALOGUE-OPEN-STALL-58: the map was made with one disk read per topic and a search through every row per topic
 * (about 3 s for Morrowind.esm on the first conversation, FS-UAE at 32 MB Fast). Now the topic names come in one read
 * (TOPIC_MAP_RUN bytes at most, freed at once; over that, one read per topic as before) and the rows are found by a
 * binary search over their hashes sorted once (2 bytes per row, freed at once). The same row as before: the first
 * row with the hash. */
#define TOPIC_MAP_RUN (512L*1024L)
static const unsigned long *sort_hashes;
static int by_hash(const void *a,const void *b) {
    unsigned short x=*(const unsigned short *)a,y=*(const unsigned short *)b;
    if(sort_hashes[x]!=sort_hashes[y])return sort_hashes[x]<sort_hashes[y]?-1:1;
    return x<y?-1:x>y;
}
int AW_DialTopicMap(const aw_dial_t *d,aw_dial_read_t read,void *user,const unsigned long *hashes,int rows,
                    unsigned short *map) {
    long t,first=-1,end=-1;int r,mapped=0;char name[256];unsigned short *order=NULL;char *names=NULL;
    if(!d->data || !map)return 0;
    if(rows>(int)AW_DIAL_NO_ROW)rows=(int)AW_DIAL_NO_ROW;
    for(t=0;t<d->topics;t++){
        int length;long at;
        if(AW_DialTopicKind(d,(int)t)!=AW_DIAL_KIND_TOPIC || (at=AW_DialTopicName(d,(int)t,&length))<0 || length<1)continue;
        if(first<0 || at<first)first=at;
        if(at+length>end)end=at+length;
    }
    if(first>=0 && end-first<=TOPIC_MAP_RUN && (names=(char *)AW_TryMalloc((size_t)(end-first)))!=NULL &&
       !read(user,first,names,end-first)){free(names);names=NULL;}
    if(rows>0 && (order=(unsigned short *)AW_TryMalloc(sizeof(unsigned short)*(size_t)rows))!=NULL){
        for(r=0;r<rows;r++)order[r]=(unsigned short)r;
        sort_hashes=hashes;qsort(order,(size_t)rows,sizeof(order[0]),by_hash);
    }
    for(t=0;t<d->topics;t++){
        int length;long at;unsigned long h;
        map[t]=AW_DIAL_NO_ROW;
        if(AW_DialTopicKind(d,(int)t)!=AW_DIAL_KIND_TOPIC || (at=AW_DialTopicName(d,(int)t,&length))<0 || length<1)continue;
        if(length>(int)sizeof(name))length=(int)sizeof(name);
        if(names)memcpy(name,names+(at-first),(size_t)length);
        else if(!read(user,at,name,length)){free(order);return -1;}
        h=AW_DialNameHash(name,length);
        if(order){                       /* the first row with the hash: lower bound over (hash, row) */
            int lo=0,hi=rows;
            while(lo<hi){int mid=(lo+hi)/2;if(hashes[order[mid]]<h)lo=mid+1;else hi=mid;}
            if(lo<rows && hashes[order[lo]]==h){map[t]=order[lo];mapped++;}
        }
        else for(r=0;r<rows;r++)if(hashes[r]==h){map[t]=(unsigned short)r;mapped++;break;}
    }
    free(order);free(names);
    return mapped;
}
void AW_DialKnownSync(const aw_dial_t *d,unsigned char *known,const unsigned short *map,int (*knows)(int row)) {
    long t;
    if(!d->data || !map || !knows)return;
    for(t=0;t<d->topics;t++){
        if(map[t]==(unsigned short)AW_DIAL_NO_ROW)continue;       /* a topic the scripts do not know of: its bit stays */
        if(knows(map[t]))known[t>>3]|=(unsigned char)(1<<(t&7));
        else known[t>>3]&=(unsigned char)~(1<<(t&7));
    }
    for(t=0;t<d->starts;t++)AW_DialKnow(d,known,AW_DialStartTopic(d,(int)t));
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

int AW_DialUiTexts(const aw_dial_t *d,aw_dial_read_t read,void *user,char *out) {
    int i;
    if(!d || !read || !out || !read(user,d->at_ui_texts,out,(long)AW_DIAL_UI_TEXT*AW_DIAL_TEXTS))return 0;
    for(i=0;i<AW_DIAL_TEXTS;i++)out[AW_DIAL_UI_TEXT*i+AW_DIAL_UI_TEXT-1]=0;
    return 1;
}
int AW_DialSkillAttribute(const aw_dial_t *d,int skill,aw_dial_read_t read,void *user) {
    unsigned char b[1];
    if(!d || !read || skill<0 || skill>=AW_DIAL_SKILLS || !read(user,d->at_skill_attributes+skill,b,1) || b[0]>7)return -1;
    return b[0];
}
unsigned long AW_DialServices(const aw_dial_t *d,int row,aw_dial_read_t read,void *user) {
    unsigned char b[4];
    if(!d || !read || row<0 || row>=d->npcs || !read(user,d->at_services+4L*row,b,4))return 0;
    return (unsigned long)rd32(b);
}
int AW_DialSpans(const aw_dial_conv_t *c,int answer,aw_dial_read_t read,void *user,aw_dial_span_t *out,int max) {
    unsigned char raw[AW_DIAL_LINK_ROW];int n,k;const aw_dial_answer_t *a;
    if(answer<0 || answer>=c->answers || !read)return 0;
    a=&c->answer[answer];
    if(a->link==AW_DIAL_NONE32)return 0;
    n=a->links<max?a->links:max;
    for(k=0;k<n;k++){
        if(!read(user,c->d->at_links+(long)AW_DIAL_LINK_ROW*(long)(a->link+k),raw,AW_DIAL_LINK_ROW))return k;
        out[k].offset=(unsigned short)rd16(raw);out[k].length=(unsigned short)rd16(raw+2);
        out[k].topic=(unsigned short)rd16(raw+4);
    }
    return n;
}
/* The links of a journal entry, from its entry row (AW_DIAL_ENTRY_ROW: u32 first link at 12, u16 links at 16), the same
 * builder-made spans and rows as a conversation's answer (OpenMW's journal uses the dialogue's keyword search). */
int AW_DialEntrySpans(const aw_dial_t *d,const unsigned char *entry_row,aw_dial_read_t read,void *user,aw_dial_span_t *out,int max) {
    unsigned char raw[AW_DIAL_LINK_ROW];unsigned long link;int n,k;
    if(!d || !entry_row || !read || max<=0)return 0;
    link=((unsigned long)entry_row[12]<<24)|((unsigned long)entry_row[13]<<16)|((unsigned long)entry_row[14]<<8)|entry_row[15];
    if(link==(unsigned long)AW_DIAL_NONE32)return 0;
    n=rd16(entry_row+16);if(n>max)n=max;
    for(k=0;k<n;k++){
        if(!read(user,d->at_links+(long)AW_DIAL_LINK_ROW*(long)(link+(unsigned long)k),raw,AW_DIAL_LINK_ROW))return k;
        out[k].offset=(unsigned short)rd16(raw);out[k].length=(unsigned short)rd16(raw+2);
        out[k].topic=(unsigned short)rd16(raw+4);
    }
    return n;
}
int AW_DialMarkSpans(const char *text,const aw_dial_span_t *spans,int n,char *out,int capacity) {
    int at=0,k=0,o=0;
    if(capacity<=0)return 0;
    for(;text[at] && o<capacity-1;at++){
        int code=AW_TEXTDEF_CODE_BYTES(text+at);
        while(k<n && at==spans[k].offset+spans[k].length && o<capacity-1){out[o++]=AW_DIAL_LINK_CLOSE;k++;}
        if(k<n && at==spans[k].offset && o<capacity-1)out[o++]=AW_DIAL_LINK_OPEN;
        if(code){                    /* a text define's code (aw_textdef.h), whole: its later bytes may equal a mark */
            if(o+code>capacity-1)break;
            memcpy(out+o,text+at,(size_t)code);o+=code;at+=code-1;
            continue;
        }
        if(o<capacity-1 && text[at]!=AW_DIAL_LINK_OPEN && text[at]!=AW_DIAL_LINK_CLOSE)out[o++]=text[at];
    }
    if(k<n && at==spans[k].offset+spans[k].length && o<capacity-1)out[o++]=AW_DIAL_LINK_CLOSE;
    out[o]=0;
    return o;
}
int AW_DialTakeSpans(const char *marked,const aw_dial_span_t *topics,int n,char *out,int capacity,aw_dial_span_t *spans,
                     int *found) {
    int o=0,k=0,open=-1;
    *found=0;
    if(capacity<=0)return 0;
    for(;*marked && o<capacity-1;marked++){
        if(*marked==AW_DIAL_LINK_OPEN){open=o;continue;}
        if(*marked==AW_DIAL_LINK_CLOSE){
            if(open>=0 && k<n && o>open){
                spans[*found].offset=(unsigned short)open;spans[*found].length=(unsigned short)(o-open);
                spans[*found].topic=topics[k].topic;(*found)++;
            }
            if(open>=0)k++;
            open=-1;continue;
        }
        out[o++]=*marked;
    }
    out[o]=0;
    return o;
}

int AW_DialLinks(const aw_dial_conv_t *c,int answer,aw_dial_read_t read,void *user,unsigned short *out,int max) {
    aw_dial_span_t spans[64];int n=AW_DialSpans(c,answer,read,user,spans,64),k,m=0,j,seen;
    for(k=0;k<n && m<max;k++){         /* each topic once, in text order */
        for(seen=0,j=0;j<m;j++)if(out[j]==spans[k].topic)seen=1;
        if(!seen)out[m++]=spans[k].topic;
    }
    return m;
}
/* --- the journal's topic pages (OpenMW Journal::addTopic, Topic::addEntry: one entry per answer heard, the same answer
 * once; removeLastAddedTopicResponse for ClearInfoActor) ---
 * An entry is the answer's table entry, its topic and the speaker's name (a small pool, each name once). Bounded by
 * the data: the three masters hold 16,796 Topic answers, a game hears far fewer; at the bound the oldest entry whose topic
 * has a newer one gives way (every topic keeps its newest) and the caller logs it. Nothing is
 * allocated until the first entry; saved (AWTP). */
#define HEARD_MAX 12000
#define HEARD_NAMES 1024
AW_RESIDENT_GROWS("journal topic entries",HEARD_MAX,6);
AW_RESIDENT_GROWS("journal topic speakers",HEARD_NAMES,AW_DIAL_SPEAKER_NAME);
typedef struct {uint16_t entry,topic,name;} heard_t;
static heard_t *heard;static int nheard,heard_cap;
static char (*heard_names)[AW_DIAL_SPEAKER_NAME];static int nnames;
void AW_DialHeardReset(void){free(heard);heard=NULL;nheard=heard_cap=0;free(heard_names);heard_names=NULL;nnames=0;}
int AW_DialHeardCount(void){return nheard;}
int AW_DialHeardAt(int i,int *entry,int *topic,const char **speaker){
    if(i<0 || i>=nheard)return 0;
    *entry=heard[i].entry;*topic=heard[i].topic;*speaker=heard[i].name<nnames?heard_names[heard[i].name]:"";
    return 1;
}
static int name_index(const char *name){
    int i;
    for(i=0;i<nnames;i++)if(same_id(heard_names[i],name))return i;
    if(nnames>=HEARD_NAMES)return -1;
    if(!heard_names && !(heard_names=(char (*)[AW_DIAL_SPEAKER_NAME])AW_TryMalloc((unsigned long)AW_DIAL_SPEAKER_NAME*HEARD_NAMES)))return -1;
    strncpy(heard_names[nnames],name,AW_DIAL_SPEAKER_NAME-1);heard_names[nnames][AW_DIAL_SPEAKER_NAME-1]=0;
    return nnames++;
}
static void heard_remove(int i){
    memmove(heard+i,heard+i+1,sizeof(heard_t)*(size_t)(nheard-i-1));nheard--;
}
int AW_DialHeardAdd(int entry,int topic,const char *speaker){
    int i,name,dropped=0;
    if(entry<0 || entry>0xFFFF || topic<0 || topic>0xFFFF || !speaker)return 0;
    for(i=0;i<nheard;i++)if(heard[i].entry==entry)return 1;          /* heard already */
    if((name=name_index(speaker))<0)name=0xFFFF;
    if(nheard==HEARD_MAX){   /* the oldest entry whose topic has a newer one gives way: every topic keeps its newest */
        int j,k,best=0;
        for(j=0;j<nheard;j++){
            for(k=j+1;k<nheard && heard[k].topic!=heard[j].topic;k++);
            if(k<nheard){best=j;break;}
        }
        heard_remove(best);dropped=1;
    }
    if(nheard==heard_cap){
        int grow=heard_cap?heard_cap*2:256;heard_t *n;
        if(grow>HEARD_MAX)grow=HEARD_MAX;
        if(!(n=(heard_t *)AW_TryMalloc(sizeof(heard_t)*(unsigned long)grow)))return 0;
        if(heard)memcpy(n,heard,sizeof(heard_t)*(size_t)nheard);
        free(heard);heard=n;heard_cap=grow;
    }
    heard[nheard].entry=(uint16_t)entry;heard[nheard].topic=(uint16_t)topic;heard[nheard].name=(uint16_t)name;nheard++;
    return dropped?2:1;
}
/* the answer ENTRY is on its topic's journal page already (OpenMW: the journal's topic has that info id) */
int AW_DialHeardHas(int entry){
    int i;
    for(i=0;i<nheard;i++)if(heard[i].entry==entry)return 1;
    return 0;
}
int AW_DialHeardRemoveLast(int topic,const char *speaker){
    int i;
    for(i=nheard-1;i>=0;i--)
        if(heard[i].topic==topic && heard[i].name<nnames && same_id(heard_names[heard[i].name],speaker)){heard_remove(i);return 1;}
    return 0;
}
/* "AWTP" u16 names, each u8 length and the name; u16 entries, each u16 entry, topic, name. Bytes, -1 no room. */
int AW_DialHeardExport(unsigned char *out,int capacity){
    int i,at=6,need=8+6*nheard;
    for(i=0;i<nnames;i++)need+=1+(int)strlen(heard_names[i]);
    if(need>capacity)return -1;
    memcpy(out,"AWTP",4);out[4]=(unsigned char)(nnames>>8);out[5]=(unsigned char)nnames;
    for(i=0;i<nnames;i++){int n=(int)strlen(heard_names[i]);out[at]=(unsigned char)n;memcpy(out+at+1,heard_names[i],(size_t)n);at+=1+n;}
    out[at]=(unsigned char)(nheard>>8);out[at+1]=(unsigned char)nheard;at+=2;
    for(i=0;i<nheard;i++){
        out[at]=(unsigned char)(heard[i].entry>>8);out[at+1]=(unsigned char)heard[i].entry;
        out[at+2]=(unsigned char)(heard[i].topic>>8);out[at+3]=(unsigned char)heard[i].topic;
        out[at+4]=(unsigned char)(heard[i].name>>8);out[at+5]=(unsigned char)heard[i].name;at+=6;
    }
    return at;
}
int AW_DialHeardImport(const unsigned char *p,int bytes){
    int i,names,entries,at=6;char name[AW_DIAL_SPEAKER_NAME];
    AW_DialHeardReset();
    if(!p || bytes<8 || memcmp(p,"AWTP",4))return -1;
    names=(p[4]<<8)|p[5];
    if(names>HEARD_NAMES)goto bad;
    for(i=0;i<names;i++){
        int n;
        if(at+1>bytes || (n=p[at])>=AW_DIAL_SPEAKER_NAME || at+1+n>bytes)goto bad;
        memcpy(name,p+at+1,(size_t)n);name[n]=0;at+=1+n;
        if(nnames>=HEARD_NAMES)goto bad;
        if(!heard_names && !(heard_names=(char (*)[AW_DIAL_SPEAKER_NAME])AW_TryMalloc((unsigned long)AW_DIAL_SPEAKER_NAME*HEARD_NAMES)))goto bad;
        strcpy(heard_names[nnames++],name);   /* by position: the entries name them by index */
    }
    if(at+2>bytes)goto bad;
    entries=(p[at]<<8)|p[at+1];at+=2;
    if(entries>HEARD_MAX || at+6*entries>bytes)goto bad;
    for(i=0;i<entries;i++,at+=6){
        int e=(p[at]<<8)|p[at+1],tp=(p[at+2]<<8)|p[at+3],nm=(p[at+4]<<8)|p[at+5];
        if(AW_DialHeardAdd(e,tp,nm<nnames?heard_names[nm]:"")!=1)goto bad;
    }
    return at;
bad:
    AW_DialHeardReset();return -1;
}
