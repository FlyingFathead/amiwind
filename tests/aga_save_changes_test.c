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
#include <stdlib.h>
#include <math.h>
#include "aw_story.h"
#include "aw_save.h"
#include "aw_maps.h"
#ifndef PIN_ONLY
#include "aw_mapfog.h"   /* the explored map's own section (MAP-EXPLORED-SAVE-BLOCK-66) */
#endif
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
#ifndef PIN_ONLY
    /* the 48-byte rows of saves before v0.0.66, as the dev line's codec wrote them (SAVE-ACTOR-ROWS-256-66) */
    aw_save_rows_form=1;assert(AW_SaveActorsReserve(&save,2));memset(save.actors,0,2*sizeof(aw_saved_actor_t));
    save.actors[0].fields=save.actors[1].fields=AW_ROW_ALL;
#endif
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
/* MAP-EXPLORED-SAVE-BLOCK-66 and SAVE-ACTOR-ROWS-256-66 (below): every allocation counted to the byte (linked with
 * --wrap for malloc, calloc, realloc and free) */
static long live;
void *__real_malloc(size_t n);void *__real_realloc(void *p,size_t n);void __real_free(void *p);
void *__wrap_malloc(size_t n){size_t *p=(size_t *)__real_malloc(n+16);if(!p)return NULL;p[0]=n;live+=(long)n;return (char *)p+16;}
void __wrap_free(void *q){size_t *p;if(!q)return;p=(size_t *)(void *)((char *)q-16);live-=(long)p[0];__real_free(p);}
void *__wrap_realloc(void *q,size_t n){
    size_t *p,was;
    if(!q)return __wrap_malloc(n);
    p=(size_t *)(void *)((char *)q-16);was=p[0];p=(size_t *)__real_realloc(p,n+16);
    if(!p)return NULL;
    p[0]=n;live+=(long)n-(long)was;return (char *)p+16;
}
void *__wrap_calloc(size_t c,size_t s){void *q=__wrap_malloc(c*s);if(q)memset(q,0,c*s);return q;}
static unsigned char big[AW_SAVE_ACTOR_MAX_BYTES+AW_SAVE_BYTES];
static void block_setting(void)
{
    /* aw_save_block_kb: 64 by default, 32 to 256, whole KB, NaN the default */
    assert(AW_SaveBlockBytes(64)==65536 && AW_SaveBlockBytes(AW_SAVE_BLOCK_KB_DEFAULT)==65536);
    assert(AW_SaveBlockBytes(0)==32768 && AW_SaveBlockBytes(31.9f)==32768 && AW_SaveBlockBytes(-5)==32768);
    assert(AW_SaveBlockBytes(32)==32768 && AW_SaveBlockBytes(100.7f)==102400 && AW_SaveBlockBytes(256)==262144);
    assert(AW_SaveBlockBytes(257)==262144 && AW_SaveBlockBytes(1e9f)==262144);
    assert(AW_SaveBlockBytes(NAN)==65536 && AW_SaveBlockBytes(-INFINITY)==32768 && AW_SaveBlockBytes(INFINITY)==262144);
    fprintf(o,"block setting ok\n");
}
/* a block of BYTES_N through a save and a load that takes it in a buffer of its own size */
static void block_round_trip(int bytes_n)
{
    static unsigned char block[AW_SAVE_ACTOR_MAX_BYTES];int i,n;
    for(i=0;i<bytes_n;i++)block[i]=(unsigned char)(i*7+3);
    list.count=0;list.actors=block;list.actor_bytes=list.actor_capacity=bytes_n;list.explored=0;
    n=AW_SaveEncodeChanges(big,sizeof(big),&save,&list);assert(n>bytes_n);
    memset(&back,0,sizeof(back));back.take=1;
    assert(AW_SaveDecodeChanges(big,n,&decoded,&back) && back.actor_bytes==bytes_n && back.actor_capacity==bytes_n);
    assert(!memcmp(back.actors,block,(size_t)bytes_n));
    AW_SaveChangesFree(&back);assert(!back.actors && !back.actor_bytes);
    AW_SaveRelease(&decoded);
    list.actors=NULL;list.actor_bytes=list.actor_capacity=0;
}
static void block_sizes(void)
{
    /* the 32 KB block of a save before v0.0.66 (its largest), the default 64 KB, the largest setting */
    block_round_trip(AW_SAVE_ACTOR_BYTES);block_round_trip(65536);block_round_trip(AW_SAVE_ACTOR_MAX_BYTES);
    fprintf(o,"blocks ok %d %d %d\n",AW_SAVE_ACTOR_BYTES,65536,AW_SAVE_ACTOR_MAX_BYTES);
}
/* a well explored game: 1,440 land cells walked all over, the 152 around them seen from their edges, 160 crossed once
 * (1,752 cells; the island and Solstheim hold under 1,600 land cells), 300 rooms (half walked through, half seen at
 * one spot) */
static void explore(void)
{
    int cx,cy,gx,gy,i;char name[16];static const float mins[2]={0,0},maxs[2]={1600,1600};
    AW_MapFogReset();
    for(cy=-18;cy<18;cy++)for(cx=-20;cx<20;cx++)for(gy=0;gy<8;gy++)for(gx=0;gx<8;gx++)
        AW_MapFogReveal(cx*8192.0f+gx*1024+512,cy*8192.0f+gy*1024+512);
    for(i=0;i<160;i++)AW_MapFogReveal((30+i%20)*8192.0f+4096,(-10+i/20*3)*8192.0f+4096);
    for(i=0;i<300;i++){
        sprintf(name,"ri%010d",i);
        if(i&1){for(gy=0;gy<16;gy++)for(gx=0;gx<16;gx++)AW_MapFogRoomReveal(name,gx*100+50,gy*100+50,mins,maxs);}
        else AW_MapFogRoomReveal(name,800,800,mins,maxs);
    }
}
static void explored_section(void)
{
    static unsigned char block[65536];unsigned char *map;int need,n,i,cells,rooms,left_cells,left_rooms,at;
    aw_save_explored_encode=AW_MapFogExport;
    explore();cells=AW_MapFogCells();rooms=AW_MapFogRooms();
    assert(cells==1752 && rooms==300);
    need=AW_MapFogExport(NULL,0);assert(need==6+1440*5+312*13+6+150*(2+12)+150*(2+12+32));
    /* a full 64 KB actor block (the default) and the explored map beside it: the save is written (before, the map
     * was inside the 32 KB block and a full block refused the whole save) */
    for(i=0;i<65536;i++)block[i]=(unsigned char)(i*13+1);
    list.count=0;list.actors=block;list.actor_bytes=list.actor_capacity=65536;list.explored=1;
    n=AW_SaveEncodeChanges(big,sizeof(big),&save,&list);assert(n>65536+need);
    memset(&back,0,sizeof(back));back.take=1;back.explored=1;
    assert(AW_SaveDecodeChanges(big,n,&decoded,&back) && back.actor_bytes==65536 && back.explored_bytes==need);
    assert((map=(unsigned char *)malloc((size_t)need)) && AW_MapFogExport(map,need)==need && !memcmp(map,back.explored_data,(size_t)need));
    AW_MapFogReset();assert(AW_MapFogImport(back.explored_data,back.explored_bytes)==need);
    assert(AW_MapFogCells()==cells && AW_MapFogRooms()==rooms && AW_MapFogSeen(-20*8192.0f+100,-18*8192.0f+100));
    fprintf(o,"explored %d cells %d rooms: section %d bytes, %lu bytes held; save with a full 64 KB block %d bytes\n",
            cells,rooms,need,AW_MapFogBytes(),n);
    AW_SaveChangesFree(&back);AW_SaveRelease(&decoded);
    /* a reader that does not keep it: checked, not kept */
    memset(&back,0,sizeof(back));back.take=1;
    assert(AW_SaveDecodeChanges(big,n,&decoded,&back) && !back.explored_data && back.actor_bytes==65536);
    AW_SaveChangesFree(&back);AW_SaveRelease(&decoded);
    /* a broken section (its head) refuses the save as any other broken part */
    for(at=12;at<n-4 && memcmp(big+at,"AWFG",4);at++){}
    assert(at<n-4);big[at+3]='X';put(big+8,crc32(big+12,n-12));
    memset(&back,0,sizeof(back));back.take=1;back.explored=1;
    assert(!AW_SaveDecodeChanges(big,n,&decoded,&back) && !back.explored_data && !back.actors);
    /* short of room (never in a save: the section is sized to the need) the land is never cut, only rooms left out
     * and counted (the save contract) */
    i=AW_MapFogExport(map,6+5*1000);AW_MapFogLeftOut(&left_cells,&left_rooms);
    assert(i==0 && left_cells==cells && left_rooms==rooms);
    i=AW_MapFogExport(map,need-46);AW_MapFogLeftOut(&left_cells,&left_rooms);
    assert(i==need-46 && !left_cells && left_rooms==1);
    assert(AW_MapFogExport(map,5)==0);
    i=AW_MapFogExport(map,need);AW_MapFogLeftOut(&left_cells,&left_rooms);assert(i==need && !left_cells && !left_rooms);
    free(map);
    list.actors=NULL;list.actor_bytes=list.actor_capacity=0;list.explored=0;
    fprintf(o,"explored section ok\n");
}
static int scene_ref_order(const void *a,const void *b)
{
    const aw_saved_actor_t *x=(const aw_saved_actor_t *)a,*y=(const aw_saved_actor_t *)b;
    if(x->scene!=y->scene)return x->scene<y->scene?-1:1;
    return x->reference==y->reference?0:x->reference<y->reference?-1:1;
}
/* a long game's rows: NPCS greeted NPCs over 300 places (2,675 NPC records in the base game), ROLES builder roles;
 * creatures have none (their place, health and death are in the change list and the actor records) */
static void long_game(aw_save_t *s,int npcs,int roles)
{
    int i;aw_saved_actor_t *a;
    memcpy(s,&save,sizeof(*s));memset(&s->state.items,0,sizeof(s->state.items));
    s->actors=NULL;s->actor_count=s->actor_capacity=0;
    assert(AW_SaveActorsReserve(s,npcs+roles));memset(s->actors,0,sizeof(aw_saved_actor_t)*(size_t)(npcs+roles));
    for(i=0;i<npcs;i++){
        a=&s->actors[s->actor_count++];a->reference=1000+(uint32_t)i;a->scene=(unsigned short)(AW_MAP_COUNT+i%300);
        a->fields=AW_ROW_GREET;a->hello_count=1+i%3;a->hello_done=i&1;a->manual_count=i%5?0:2;
    }
    for(i=0;i<roles;i++){
        a=&s->actors[s->actor_count++];a->reference=0x800000U+(uint32_t)i+1;a->scene=(unsigned short)AW_MapLogicalId("seyda");
        a->fields=AW_ROW_ALL;a->position[0]=100.4f+i;a->position[1]=-50;a->position[2]=8;a->angles[1]=90;
        a->health=i&1?37.5f:40;a->hello_count=i%2;
    }
    qsort(s->actors,(size_t)s->actor_count,sizeof(aw_saved_actor_t),scene_ref_order);
}
static void packed_rows(void)
{
    static aw_save_t s,back_rows,again;int n,n_base,n2,i,j,greeted=0;aw_saved_actor_t *a,*b;
    aw_save_rows_form=0;
    long_game(&s,2700,20);
    {aw_save_t none=s;none.actor_count=0;n_base=AW_SaveEncode(big,sizeof(big),&none);assert(n_base>0);}
    n=AW_SaveEncode(big,sizeof(big),&s);assert(n>n_base && n-n_base==AW_SaveActorRowsBytes(&s));
    assert(AW_SaveDecode(big,n,&back_rows) && back_rows.actor_count==2720);
    for(i=0;i<2720;i++){
        a=&s.actors[i];b=&back_rows.actors[i];
        assert(a->reference==b->reference && a->scene==b->scene && a->hello_count==b->hello_count &&
               a->manual_count==b->manual_count && a->hello_done==b->hello_done);
        if(a->fields==AW_ROW_ALL){
            /* greetings all 0 write nothing (the game data's own), so such a row comes back with its place and health */
            assert((b->fields&(AW_ROW_PLACE|AW_ROW_HEALTH))==(AW_ROW_PLACE|AW_ROW_HEALTH) &&
                   !(b->fields&AW_ROW_GREET)==!(a->hello_count || a->manual_count || a->hello_done) &&
                   b->position[0]==floorf(a->position[0]+.5f) && b->position[1]==-50 &&
                   b->position[2]==8 && b->angles[1]==90 && b->health==a->health);
        }else{assert(b->fields==AW_ROW_GREET);greeted++;}
    }
    /* save, load, save: the same bytes */
    memcpy(other,big,(size_t)n);n2=AW_SaveEncode(big,sizeof(big),&back_rows);assert(n2==n && !memcmp(big,other,(size_t)n));
    /* the old form holds 256 at most: refused, never cut */
    aw_save_rows_form=1;assert(!AW_SaveEncode(big,sizeof(big),&s));
    {aw_save_t first=s;first.actor_count=AW_SAVE_ACTORS;n2=AW_SaveEncode(big,sizeof(big),&first);assert(n2>0);
     assert(AW_SaveDecode(big,n2,&again) && again.actor_count==AW_SAVE_ACTORS && again.actors[255].reference==s.actors[255].reference);
     AW_SaveRelease(&again);}
    /* SAVE-ACTOR-ROWS-EXPANSION-ROOMS-66: an expansion room's row (its save ID past the base rooms' range) refused
     * the old form, so the whole save; the packed form keeps it */
    {aw_save_t one=s;aw_saved_actor_t r=s.actors[0];one.actors=&r;one.actor_count=1;r.scene=AW_TRIBUNAL_ROOM_BASE+5;
     assert(!AW_SaveEncode(big,sizeof(big),&one));
     aw_save_rows_form=0;n2=AW_SaveEncode(big,sizeof(big),&one);assert(n2>0);
     assert(AW_SaveDecode(big,n2,&again) && again.actor_count==1 && again.actors[0].scene==AW_TRIBUNAL_ROOM_BASE+5);
     AW_SaveRelease(&again);
     r.scene=AW_SCENE_COUNT;assert(!AW_SaveEncode(big,sizeof(big),&one));   /* an ID no place has: refused */
     r.scene=AW_LAYER_ROOM_END;assert(!AW_SaveEncode(big,sizeof(big),&one));}
    /* rows out of order or twice are refused (a capture keeps them sorted) */
    {aw_saved_actor_t t=s.actors[0];s.actors[0]=s.actors[1];s.actors[1]=t;assert(!AW_SaveEncode(big,sizeof(big),&s));
     s.actors[1]=s.actors[0];assert(!AW_SaveEncode(big,sizeof(big),&s));s.actors[0]=t;
     qsort(s.actors,(size_t)s.actor_count,sizeof(aw_saved_actor_t),scene_ref_order);}
    /* the most one row takes: a place, a tilt, a health that is not whole, both counts at their largest, done */
    {aw_save_t one=s;aw_saved_actor_t r;memset(&r,0,sizeof(r));r.reference=0xffffff;r.scene=1;r.fields=AW_ROW_ALL;
     r.position[0]=-32767;r.angles[0]=10;r.health=0.25f;r.hello_count=r.manual_count=10000000;r.hello_done=1;
     one.actors=&r;one.actor_count=1;j=AW_SaveActorRowsBytes(&one)-4-3-4;assert(j==25);
     n2=AW_SaveEncode(big,sizeof(big),&one);assert(n2>0 && AW_SaveDecode(big,n2,&again));
     assert(again.actors[0].hello_count==10000000 && again.actors[0].health==0.25f && again.actors[0].position[0]==-32767);
     AW_SaveRelease(&again);}
    fprintf(o,"packed rows %d (%d greeted NPCs, 20 builder roles): %d bytes, %.2f a row; the old form %d bytes "
            "(and at most %d rows); worst row 25 bytes\n",s.actor_count,greeted,n-n_base,(double)(n-n_base)/s.actor_count,
            s.actor_count*48,AW_SAVE_ACTORS);
    fprintf(o,"fresh save %d bytes\n",n_base);
    AW_SaveRelease(&back_rows);AW_SaveActorsFree(&s);
}
/* save, load, save, load: the bytes held stay the same to the byte (rows, the explored map, the load's buffers) */
static void heap_cycles(void)
{
    static aw_save_t s,d;static unsigned char block[65536];long held=0;int c,n;
    aw_save_rows_form=0;aw_save_explored_encode=AW_MapFogExport;
    explore();long_game(&s,2700,20);
    for(c=0;c<6;c++){
        list.count=0;list.actors=block;list.actor_bytes=list.actor_capacity=40000;list.explored=1;
        n=AW_SaveEncodeChanges(big,sizeof(big),&s,&list);assert(n>0);
        memset(&back,0,sizeof(back));back.take=1;back.explored=1;
        assert(AW_SaveDecodeChanges(big,n,&d,&back) && d.actor_count==2720 && back.actor_bytes==40000);
        assert(AW_MapFogImport(back.explored_data,back.explored_bytes)==back.explored_bytes);
        AW_SaveChangesFree(&back);
        AW_SaveRelease(&s);s=d;memset(&d,0,sizeof(d));   /* the loaded save becomes the game's */
        if(c==1)held=live;
        else if(c>1)assert(live==held);
    }
    fprintf(o,"heap %ld bytes held after each of 5 save and load cycles\n",held);
    AW_SaveRelease(&s);AW_MapFogReset();
    list.actors=NULL;list.actor_bytes=list.actor_capacity=0;list.explored=0;aw_save_explored_encode=NULL;
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
    /* a room's actor (v0.0.57, SAVEGAME-COMPLETE-57): WHERE is the room's stable number, the position room-local;
     * a room entry with no room number, or with a scene too, is refused */
    {aw_changes_t rooms;aw_changes_t read;int k;
     rooms.count=0;
     rooms.entry[rooms.count]=entry(7001,AW_CHANGE_MOVED|AW_CHANGE_ROOM,0,0,0,112.5f,30);rooms.entry[rooms.count++].where=203;
     k=AW_SaveEncodeChanges(other,sizeof(other),&save,&rooms);assert(k>0);
     assert(AW_SaveDecodeChanges(other,k,&decoded,&read) && read.count==1);
     assert(read.entry[0].flags==(AW_CHANGE_MOVED|AW_CHANGE_ROOM) && read.entry[0].where==203 &&
            read.entry[0].position[0]==112.5f && read.entry[0].health==30);
     rooms.entry[0].where=0;assert(!AW_SaveEncodeChanges(other,sizeof(other),&save,&rooms));
     rooms.entry[0].where=203;rooms.entry[0].flags|=AW_CHANGE_SCENE;assert(!AW_SaveEncodeChanges(other,sizeof(other),&save,&rooms));}
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
    list.entry[1]=entry(10,0x10000,0,0,0,0,0);assert(!AW_SaveEncodeChanges(other,sizeof(other),&save,&list));
    list.entry[1]=entry(10,AW_CHANGE_ROOM,0,0,0,0,0);assert(!AW_SaveEncodeChanges(other,sizeof(other),&save,&list));   /* room 0 */
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
    other[n-AW_CHANGE_ENTRY_BYTES+5]|=0x80;                  /* the second entry's packed word: a stray bit */
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
     /* MAP-EXPLORED-SAVE-BLOCK-66: past the largest block the setting gives (256 KB) it is refused */
     {static unsigned char huge[AW_SAVE_ACTOR_MAX_BYTES+1];
      list.actors=huge;list.actor_bytes=AW_SAVE_ACTOR_MAX_BYTES+1;list.actor_capacity=AW_SAVE_ACTOR_MAX_BYTES+1;
      assert(!AW_SaveEncodeChanges(big,sizeof(big),&save,&list));}
     list.actors=NULL;list.actor_bytes=list.actor_capacity=0;}
    fprintf(o,"refusals ok\n");
    AW_SaveRelease(&decoded);
    block_setting();
    block_sizes();
    explored_section();
    packed_rows();
    heap_cycles();
#endif
    if(o!=stdout)fclose(o);
    return 0;
}
