/* SPDX-License-Identifier: GPL-3.0-only
 * The world-state change list in saves (AWS4 feature bit 8; aw_save.h, aw_save_codec.c; tests/test_save_changes.py).
 * Writes (to argv[1]) "base SHA" and "rows SHA" lines (a save without changes and one with actor rows: their bytes are pinned
 * against the dev line's codec by the Python test; built with -DPIN_ONLY for the dev line, which has no change list
 * API), then checks: no change list = the same bytes; a round trip keeps every entry (sorted, same hash); old actor
 * rows fold into "moved + health" entries with the intro roles under bit 31; a full list fits and one more does
 * not; duplicate keys, cut-piece bits, unknown flags and a corrupt entry are refused.
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_story.h"
#include "aw_save.h"
#include "aw_maps.h"
aw_race_t aw_races[16];aw_class_t aw_classes[32];aw_birth_t aw_births[16];aw_part_t aw_parts[384];
int aw_race_count=1,aw_class_count=1,aw_birth_count=1,aw_part_count=2;
static aw_save_t save,decoded;
static unsigned char bytes[AW_SAVE_BYTES],other[AW_SAVE_BYTES];
static FILE *o;

/* SHA-256 (FIPS 180-4), for the pin lines only */
static unsigned int K[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,
0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,
0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,
0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,
0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
#define R(x,n) (((x)>>(n))|((x)<<(32-(n))))
static void sha(const unsigned char *m,unsigned long n,char *hex)
{
    unsigned int h[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19},w[64];
    unsigned long total=((n+9+63)/64)*64,i,j;static unsigned char buf[AW_SAVE_BYTES+128];
    memset(buf,0,total);memcpy(buf,m,n);buf[n]=0x80;
    for(i=0;i<8;i++)buf[total-1-i]=(unsigned char)(((unsigned long long)n*8)>>(8*i));
    for(i=0;i<total;i+=64){
        unsigned int a,b,c,d,e,f,g,k,t1,t2;
        for(j=0;j<16;j++)w[j]=(buf[i+4*j]<<24)|(buf[i+4*j+1]<<16)|(buf[i+4*j+2]<<8)|buf[i+4*j+3];
        for(j=16;j<64;j++)w[j]=(R(w[j-2],17)^R(w[j-2],19)^(w[j-2]>>10))+w[j-7]+(R(w[j-15],7)^R(w[j-15],18)^(w[j-15]>>3))+w[j-16];
        a=h[0];b=h[1];c=h[2];d=h[3];e=h[4];f=h[5];g=h[6];k=h[7];
        for(j=0;j<64;j++){
            t1=k+(R(e,6)^R(e,11)^R(e,25))+((e&f)^(~e&g))+K[j]+w[j];t2=(R(a,2)^R(a,13)^R(a,22))+((a&b)^(a&c)^(b&c));
            k=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
        }
        h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=k;
    }
    for(i=0;i<8;i++)sprintf(hex+8*i,"%08x",h[i]);
}
static void base(void)
{
    strcpy(aw_races[0].id,"race");strcpy(aw_classes[0].id,"class");strcpy(aw_births[0].id,"birth");
    strcpy(aw_parts[0].id,"head");strcpy(aw_parts[1].id,"hair");aw_parts[1].kind=1;
    memset(&save,0,sizeof(save));
    save.sequence=save.profile=1;strcpy(save.scene,"seyda");strcpy(save.story.name,"Player");
    save.story.stage=AW_STAGE_RELEASED;save.story.ship_disabled=1;save.story.captain=-1;
    save.character.valid=1;save.character.level=1;save.character.hair=1;
    assert(AW_StateSet(&save.state,AW_GLOBAL,"CharGenState",-1));
}
static void rows(void)
{
    save.actor_count=2;
    save.actors[0].reference=1234;save.actors[0].scene=AW_MapLogicalId("seyda");
    save.actors[0].position[0]=100;save.actors[0].angles[1]=90;save.actors[0].health=40;
    save.actors[1].reference=0x800003;save.actors[1].scene=AW_MapLogicalId("seyda");
    save.actors[1].health=100;
}
#ifndef PIN_ONLY
static unsigned int crc32(const unsigned char *p,int n)
{
    unsigned int crc=0xffffffffU;int i;
    while(n--){crc^=*p++;for(i=0;i<8;i++)crc=(crc>>1)^((crc&1)?0xedb88320U:0);}
    return crc^0xffffffffU;
}
static void put(unsigned char *p,unsigned int v){p[0]=v;p[1]=v>>8;p[2]=v>>16;p[3]=v>>24;}
static unsigned int fnv(const aw_changes_t *c)
{
    unsigned int h=2166136261u;const unsigned char *p=(const unsigned char *)c->entry;
    unsigned long i;for(i=0;i<sizeof(aw_change_t)*c->count;i++)h=(h^p[i])*16777619u;return h;
}
static aw_changes_t list,back,folded;
static aw_change_t entry(unsigned int key,unsigned int flags,unsigned int pick,int cx,int cy,float x,float health)
{
    aw_change_t e;memset(&e,0,sizeof(e));e.key=key;e.flags=flags;e.pick=pick;
    e.where=(int)(((unsigned int)(cx&0xffff)<<16)|(unsigned int)(cy&0xffff));
    e.position[0]=x;e.position[1]=-x;e.position[2]=8;e.yaw=45;e.health=health;e.hours=12.5f;return e;
}
#endif
int main(int argc,char **argv)
{
    int n0,n1,n,i;char hex[65];
    o=argc>1?fopen(argv[1],"w"):stdout;assert(o);
    base();
    n0=AW_SaveEncode(bytes,sizeof(bytes),&save);assert(n0>0);sha(bytes,n0,hex);fprintf(o,"base %s %d\n",hex,n0);
    rows();
    n1=AW_SaveEncode(bytes,sizeof(bytes),&save);assert(n1>0);sha(bytes,n1,hex);fprintf(o,"rows %s %d\n",hex,n1);
#ifndef PIN_ONLY
    /* no change list: the very same bytes */
    list.count=0;
    n=AW_SaveEncodeChanges(other,sizeof(other),&save,&list);assert(n==n1 && !memcmp(bytes,other,n));
    n=AW_SaveEncodeChanges(other,sizeof(other),&save,NULL);assert(n==n1 && !memcmp(bytes,other,n));
    /* an old save: its rows fold into moved + health entries, the intro role under bit 31 */
    assert(AW_SaveDecodeChanges(bytes,n1,&decoded,&back) && back.count==0 && decoded.actor_count==2);
    folded.count=0;assert(AW_SaveFoldActors(&decoded,&folded)==2);
    assert(folded.entry[0].key==1234 && folded.entry[0].flags==(AW_CHANGE_MOVED|AW_CHANGE_SCENE) &&
           folded.entry[0].health==40 && folded.entry[0].yaw==90 && folded.entry[0].position[0]==100);
    assert(folded.entry[1].key==(AW_CHANGE_BUILDER|3));
    assert(AW_SaveFoldActors(&decoded,&folded)==0);           /* a key already there is not added twice */
    assert(AW_SaveChangeKey(484475)==484475 && AW_SaveChangeKey(0x800000)==AW_CHANGE_BUILDER);
    /* a round trip: sorted by key, every field, the same hash */
    list.count=0;
    list.entry[list.count++]=entry(500,AW_CHANGE_DEAD|AW_CHANGE_MOVED,0,1,-7,4000,0);
    list.entry[list.count++]=entry(77,AW_CHANGE_MOVED|AW_CHANGE_FIGHT,0,2,-6,4500.5f,67);
    list.entry[list.count++]=entry(355130,AW_CHANGE_PICK,5,8,14,0,0);
    list.entry[list.count++]=entry(AW_CHANGE_BUILDER|2,AW_CHANGE_MOVED|AW_CHANGE_SCENE,0,0,0,10,90);
    list.entry[3].where=AW_MapLogicalId("seyda");
    n=AW_SaveEncodeChanges(other,sizeof(other),&save,&list);
    assert(n==n1+4+4*AW_CHANGE_ENTRY_BYTES);
    assert(AW_SaveDecodeChanges(other,n,&decoded,&back) && back.count==4);
    assert(back.entry[0].key==77 && back.entry[1].key==500 && back.entry[2].key==355130 &&
           back.entry[3].key==(AW_CHANGE_BUILDER|2));
    {aw_changes_t sorted=list;aw_change_t t;
     t=sorted.entry[0];sorted.entry[0]=sorted.entry[1];sorted.entry[1]=t;
     assert(fnv(&sorted)==fnv(&back));}
    assert(AW_SaveDecode(other,n,&decoded));               /* checked, not kept */
    fprintf(o,"roundtrip %08x %d\n",fnv(&back),n);
    /* object state (v0.0.51): a disabled placement and a door the scripts locked at 50 and another unlocked (0) */
    {aw_changes_t objects;aw_changes_t read;int k;
     objects.count=0;
     objects.entry[objects.count++]=entry(6001,AW_CHANGE_DISABLED,0,0,0,0,0);
     objects.entry[objects.count++]=entry(6002,AW_CHANGE_LOCK|(50U<<AW_CHANGE_LOCK_SHIFT),0,0,0,0,0);
     objects.entry[objects.count++]=entry(6003,AW_CHANGE_LOCK|AW_CHANGE_DISABLED,0,0,0,0,0);
     k=AW_SaveEncodeChanges(other,sizeof(other),&save,&objects);assert(k>0);
     assert(AW_SaveDecodeChanges(other,k,&decoded,&read) && read.count==3);
     assert(read.entry[0].flags==AW_CHANGE_DISABLED);
     assert(read.entry[1].flags==(AW_CHANGE_LOCK|(50U<<AW_CHANGE_LOCK_SHIFT)));
     assert(read.entry[2].flags==(AW_CHANGE_LOCK|AW_CHANGE_DISABLED));}
    /* a full list fits the cap; one more entry does not */
    list.count=0;
    for(i=0;i<AW_SAVE_CHANGES;i++)list.entry[list.count++]=entry(1000+i,AW_CHANGE_DEAD,0,0,0,0,0);
    n=AW_SaveEncodeChanges(other,sizeof(other),&save,&list);assert(n>0 && n<AW_SAVE_BYTES);
    assert(AW_SaveDecodeChanges(other,n,&decoded,&back) && back.count==AW_SAVE_CHANGES);
    fprintf(o,"full %d\n",n);
    list.count=AW_SAVE_CHANGES+1;list.entry[AW_SAVE_CHANGES-1].key=999999;
    assert(!AW_SaveEncodeChanges(other,sizeof(other),&save,&list));
    /* refused: a key twice, a cut-piece key, an unknown flag, no flag, a pick without its flag */
    list.count=2;list.entry[0]=entry(9,AW_CHANGE_DEAD,0,0,0,0,0);list.entry[1]=entry(9,AW_CHANGE_DEAD,0,0,0,0,0);
    assert(!AW_SaveEncodeChanges(other,sizeof(other),&save,&list));
    list.entry[1]=entry(0x01000009,AW_CHANGE_DEAD,0,0,0,0,0);assert(!AW_SaveEncodeChanges(other,sizeof(other),&save,&list));
    list.entry[1]=entry(10,0x8000,0,0,0,0,0);assert(!AW_SaveEncodeChanges(other,sizeof(other),&save,&list));
    /* object state (v0.0.51): a lock level needs its flag and stays within 100 */
    list.entry[1]=entry(10,AW_CHANGE_DISABLED|(5U<<AW_CHANGE_LOCK_SHIFT),0,0,0,0,0);
    assert(!AW_SaveEncodeChanges(other,sizeof(other),&save,&list));
    list.entry[1]=entry(10,AW_CHANGE_LOCK|(101U<<AW_CHANGE_LOCK_SHIFT),0,0,0,0,0);
    assert(!AW_SaveEncodeChanges(other,sizeof(other),&save,&list));
    list.entry[1]=entry(10,0,0,0,0,0,0);assert(!AW_SaveEncodeChanges(other,sizeof(other),&save,&list));
    list.entry[1]=entry(10,AW_CHANGE_DEAD,3,0,0,0,0);assert(!AW_SaveEncodeChanges(other,sizeof(other),&save,&list));
    /* a corrupt entry with a good CRC is refused field by field; a bad CRC too */
    list.entry[1]=entry(10,AW_CHANGE_DEAD,0,0,0,0,0);
    n=AW_SaveEncodeChanges(other,sizeof(other),&save,&list);assert(n>0);
    other[n-AW_CHANGE_ENTRY_BYTES+5]|=0x80;                  /* the second entry's flags: an unknown bit (15) */
    put(other+8,crc32(other+12,n-12));assert(!AW_SaveDecodeChanges(other,n,&decoded,&back));
    other[n-1]^=1;assert(!AW_SaveDecodeChanges(other,n,&decoded,&back));
    /* the actor record's block (v0.0.54, feature 16): read back into the caller's buffer, with no change list too;
     * a reader without a buffer skips it; a block over the cap is refused */
    {static unsigned char block[64],got[64];int k2;
     list.count=0;list.actors=block;list.actor_bytes=10;list.actor_capacity=64;memcpy(block,"AWAS\1\0\0\0\0\0",10);
     k2=AW_SaveEncodeChanges(other,sizeof(other),&save,&list);assert(k2>0);
     back.actors=got;back.actor_capacity=64;back.actor_bytes=0;
     assert(AW_SaveDecodeChanges(other,k2,&decoded,&back) && back.actor_bytes==10 && !memcmp(got,block,10) && back.count==0);
     back.actors=NULL;back.actor_capacity=0;
     assert(AW_SaveDecodeChanges(other,k2,&decoded,&back) && back.actor_bytes==0);
     list.actor_bytes=AW_SAVE_ACTOR_BYTES+1;list.actor_capacity=AW_SAVE_ACTOR_BYTES+1;
     assert(!AW_SaveEncodeChanges(other,sizeof(other),&save,&list));
     list.actors=NULL;list.actor_bytes=list.actor_capacity=0;}
    fprintf(o,"refusals ok\n");
#endif
    if(o!=stdout)fclose(o);
    return 0;
}
