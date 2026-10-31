/* SPDX-License-Identifier: GPL-2.0-or-later
 * The player's standing: aw_pcstanding.h. */
#include <string.h>
#include "aw_pcstanding.h"

typedef struct {
    char id[32];
    signed char rank;           /* -1 not a member (known only by a reputation or the expelled mark) */
    unsigned char expelled;
    int reputation;
} faction_t;
static faction_t factions[AW_STANDING_FACTIONS];
static int nfactions,bounty,reputation,full;

void AW_StandingReset(void){memset(factions,0,sizeof(factions));nfactions=bounty=reputation=full=0;}

static int same(const char *a,const char *b){
    for(;*a && *b;a++,b++){
        char x=*a>='A' && *a<='Z'?(char)(*a+32):*a,y=*b>='A' && *b<='Z'?(char)(*b+32):*b;
        if(x!=y)return 0;
    }
    return *a==*b;
}
static faction_t *find(const char *id,int create){
    int i;
    if(!id || !*id || strlen(id)>=sizeof(factions[0].id))return NULL;
    for(i=0;i<nfactions;i++)if(same(factions[i].id,id))return &factions[i];
    if(!create)return NULL;
    if(nfactions>=AW_STANDING_FACTIONS){full=1;return NULL;}
    memset(&factions[nfactions],0,sizeof(factions[0]));
    strcpy(factions[nfactions].id,id);factions[nfactions].rank=-1;
    return &factions[nfactions++];
}

int AW_StandingCrime(void){return bounty;}
void AW_StandingSetCrime(int value){bounty=value;}
void AW_StandingModCrime(int change){bounty+=change;if(bounty<0)bounty=0;}
int AW_StandingReputation(void){return reputation;}
void AW_StandingSetReputation(int value){reputation=value<0?0:value>255?255:value;}

int AW_StandingRank(const char *id){faction_t *f=find(id,0);return f?f->rank:-1;}
void AW_StandingJoin(const char *id){faction_t *f=find(id,1);if(f && f->rank<0)f->rank=0;}
void AW_StandingRaise(const char *id){
    faction_t *f=find(id,1);
    if(!f)return;
    if(f->rank<0)f->rank=0;
    else if(f->rank+1<AW_STANDING_RANKS)f->rank++;
}
void AW_StandingLower(const char *id){
    faction_t *f=find(id,0);
    if(!f || f->rank<0)return;            /* not a member: nothing (OpenMW setFactionRank only changes a member) */
    if(--f->rank<0)f->expelled=0;
}
int AW_StandingExpelled(const char *id){faction_t *f=find(id,0);return f?f->expelled:0;}
void AW_StandingSetExpelled(const char *id,int expelled){
    faction_t *f=find(id,expelled!=0);
    if(f)f->expelled=(unsigned char)(expelled!=0);
}
int AW_StandingFactionReputation(const char *id){faction_t *f=find(id,0);return f?f->reputation:0;}
void AW_StandingSetFactionReputation(const char *id,int value){faction_t *f=find(id,1);if(f)f->reputation=value;}
int AW_StandingFull(void){return full;}

/* Saved games: "AWPS" u8 1 u8 factions i32 bounty u16 reputation, then per faction id[32] s8 rank u8 expelled
 * i32 reputation (big-endian). */
#define FACTION_BYTES 38
static unsigned char *put32(unsigned char *p,long v){
    unsigned long u=(unsigned long)v;p[0]=(unsigned char)(u>>24);p[1]=(unsigned char)(u>>16);p[2]=(unsigned char)(u>>8);
    p[3]=(unsigned char)u;return p+4;}
static long get32(const unsigned char *p){
    unsigned long u=((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)|((unsigned long)p[2]<<8)|p[3];
    return u&0x80000000UL?-(long)((~u&0xFFFFFFFFUL)+1):(long)u;}
int AW_StandingExport(unsigned char *out,int capacity){
    int i,need=12+FACTION_BYTES*nfactions;unsigned char *p=out;
    if(need>capacity)return -1;
    memcpy(p,"AWPS",4);p[4]=1;p[5]=(unsigned char)nfactions;p=put32(p+6,bounty);
    *p++=(unsigned char)(reputation>>8);*p++=(unsigned char)reputation;
    for(i=0;i<nfactions;i++){
        memcpy(p,factions[i].id,32);p+=32;*p++=(unsigned char)factions[i].rank;*p++=factions[i].expelled;
        p=put32(p,factions[i].reputation);
    }
    return need;
}
int AW_StandingImport(const unsigned char *data,int bytes){
    int i,n;
    AW_StandingReset();
    if(bytes<12 || memcmp(data,"AWPS",4) || data[4]!=1)return 0;
    n=data[5];
    if(n>AW_STANDING_FACTIONS || bytes!=12+FACTION_BYTES*n)return 0;
    bounty=(int)get32(data+6);reputation=(data[10]<<8)|data[11];
    for(i=0;i<n;i++){
        const unsigned char *p=data+12+FACTION_BYTES*i;
        memcpy(factions[i].id,p,32);factions[i].id[31]=0;
        factions[i].rank=(signed char)p[32];factions[i].expelled=(unsigned char)(p[33]!=0);
        factions[i].reputation=(int)get32(p+34);
    }
    nfactions=n;
    return 1;
}
