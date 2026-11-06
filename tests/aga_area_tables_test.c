/* SPDX-License-Identifier: GPL-3.0-only
 * AREA-TABLES-59: the per-area lookup tables (id1/areas.awa, tools/prepare_area_tables.py) against the island-wide
 * files they come from. The fixture (written by tests/test_aga_native_source.py from tools/prepare_area_tables.py's
 * own build over a synthetic focus.awf, items.awi and icon pack) is read from the folder in argv[1], with expect.txt:
 * the answers the fixture was made with. Phase 1 asks before any area is loaded (every answer a file search); phase 2
 * enters each room (its table loaded with it) and asks again: the same answers, no file opened for them, no fallback.
 * Then the load and unload rules: a room left is kept in the cache and taken back without a read; the memory policy's
 * trim empties the cache; a container or an item outside the loaded areas is narrow-loaded through the directory. */
#include "quakedef.h"
#include "aw_inventory.h"
#include "aw_ledger.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
static client_t client;
static edict_t entities[8];
static model_t worlds[8];
char *pr_strings;
static char strings[16];
static const char *folder;
static int file_opens;      /* opens of focus.awf and items.awi */
void Con_Printf(char *format,...){(void)format;}
void CDAudio_Update(void){}
void S_ExtraUpdate(void){}
double Sys_FloatTime(void){return 0;}
edict_t *EDICT_NUM(int i){assert(i>=0 && i<8);return &entities[i];}
eval_t *GetEdictFieldValue(edict_t *e,char *field){(void)e;(void)field;return NULL;}
void *AW_TryMalloc(int size){return calloc(1,size);}
int COM_FOpenFile(char *name,FILE **file){
    char path[512];long size;
    *file=NULL;
    if(!strcmp(name,"focus.awf") || !strcmp(name,"inventory/items.awi"))file_opens++;
    else if(strcmp(name,"areas.awa"))return -1;
    snprintf(path,sizeof(path),"%s/%s",folder,name);
    if(!(*file=fopen(path,"rb")))return -1;
    fseek(*file,0,SEEK_END);size=ftell(*file);rewind(*file);
    return (int)size;
}
int AW_WorldToSource(const char *name,const float *local,float *out){(void)name;(void)local;(void)out;return 0;}
int AW_SourceToWorld(const char *name,const float *in,float *local){(void)name;(void)in;(void)local;return 0;}
void AW_MwscriptRoomShift(float shift[3]){shift[0]=shift[1]=shift[2]=0;}
int AW_ObjectDisabled(unsigned reference){(void)reference;return 0;}
int AW_ObjectTake(unsigned reference,int stolen){(void)reference;(void)stolen;return 1;}
int ChimRoom_Has(unsigned reference){(void)reference;return 1;}
void AW_UIPickupNotice(const char *name,double duration){(void)name;(void)duration;}
void AW_UISubtitle(const char *speaker,const char *text,double duration){(void)speaker;(void)text;(void)duration;}
void AW_CombatEquipmentChanged(void){}
void ED_Free(edict_t *e){(void)e;assert(0);}
edict_t *ED_Alloc(void){assert(0);return NULL;}
char *ED_NewString(char *s){(void)s;assert(0);return NULL;}
void SV_LinkEdict(edict_t *e,qboolean triggers){(void)e;(void)triggers;}
model_t *Mod_ForName(char *name,qboolean crash){(void)name;(void)crash;assert(0);return NULL;}
void *Cache_Check(cache_user_t *c){(void)c;assert(0);return NULL;}
int SV_PointContents(vec3_t p){(void)p;assert(0);return 0;}
trace_t SV_Move(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,int type,edict_t *pass){
    trace_t tr;(void)start;(void)mins;(void)maxs;(void)type;(void)pass;
    memset(&tr,0,sizeof(tr));tr.fraction=1;VectorCopy(end,tr.endpos);return tr;
}
/* expect.txt: "C room ref owner faction n id count ...", "I id name", "P room ref id", "K id w h first-pixel" */
#define MAXC 64
typedef struct {int room;unsigned ref;char owner[40];int faction,n;char id[16][40];int count[16];} cont_t;
static cont_t conts[MAXC];static int nconts;
typedef struct {char id[40],name[100];} item_t;
static item_t items[MAXC];static int nitems;
typedef struct {int room;unsigned ref;char id[40];} placed_t;
static placed_t placed[MAXC];static int nplaced;
typedef struct {char id[40];int w,h,first;} icon_t;
static icon_t icons[MAXC];static int nicons;
static void expectations(void){
    char path[512],kind[4];FILE *f;int i;
    snprintf(path,sizeof(path),"%s/expect.txt",folder);
    assert((f=fopen(path,"r"))!=NULL);
    while(fscanf(f,"%3s",kind)==1){
        if(!strcmp(kind,"C")){cont_t *c=&conts[nconts++];
            assert(fscanf(f,"%d %u %39s %d %d",&c->room,&c->ref,c->owner,&c->faction,&c->n)==5);
            for(i=0;i<c->n;i++)assert(fscanf(f,"%39s %d",c->id[i],&c->count[i])==2);
        }else if(!strcmp(kind,"I")){item_t *t=&items[nitems++];
            assert(fscanf(f,"%39s %99[^\n]",t->id,t->name)==2);
        }else if(!strcmp(kind,"P")){placed_t *p=&placed[nplaced++];
            assert(fscanf(f,"%d %u %39s",&p->room,&p->ref,p->id)==3);
        }else if(!strcmp(kind,"K")){icon_t *k=&icons[nicons++];
            assert(fscanf(f,"%39s %d %d %d",k->id,&k->w,&k->h,&k->first)==4);
        }else assert(0);
    }
    fclose(f);
}
static char entity_text[8][96];
static void enter(int room){
    static int next;model_t *m=&worlds[next];
    memset(&sv,0,sizeof(sv));memset(&svs,0,sizeof(svs));memset(entities,0,sizeof(entities));
    pr_strings=strings;sv.active=1;sv.num_edicts=2;strcpy(sv.name,"room");svs.maxclients=1;svs.clients=&client;
    client.edict=&entities[1];entities[1].v.movetype=MOVETYPE_WALK;
    snprintf(entity_text[next],sizeof(entity_text[next]),"{\n\"classname\" \"worldspawn\"\n\"_aw_cell_int\" \"%d\"\n}\n",room);
    m->entities=entity_text[next];sv.worldmodel=m;next=(next+1)%8;
    AW_PlacedRefresh();            /* the place read: its area tables loaded with it */
}
/* every answer of the fixture; ROOM >= 0: only that room's (the loaded one), and nothing may open a file */
static void ask(int room){
    int i,j,k,opens=file_opens;unsigned long fallbacks=AW_AreaFallbacks();
    for(i=0;i<nconts;i++){
        aw_container_item_t got[AW_CONTAINER_ITEMS];int n;const cont_t *c=&conts[i];
        if(room>=0 && c->room!=room)continue;
        n=AW_ContainerContents(c->ref,got,AW_CONTAINER_ITEMS,NULL);
        assert(n==c->n);
        for(j=0;j<n;j++){
            for(k=0;k<n;k++)if(!Q_strcasecmp(got[j].id,(char *)c->id[k]))break;
            assert(k<n && got[j].count==c->count[k]);
        }
        /* its owning NPC or faction: one taken from it is stolen from them (then put back; the pair stays) */
        if(n>0 && strcmp(c->owner,"-")){
            int before=AW_LedgerStolenCount(&aw_ledger,c->id[0],c->owner,c->faction);
            assert(AW_ContainerChange(c->ref,c->id[0],-1,1)==1);
            assert(AW_LedgerStolenCount(&aw_ledger,c->id[0],c->owner,c->faction)==before+1);
            assert(AW_ContainerChange(c->ref,c->id[0],1,0)==1);
        }
    }
    for(i=0;i<nitems && room<0;i++){
        aw_inventory_item_t item;
        assert(AW_InventoryRead(items[i].id,&item) && !strcmp(item.name,items[i].name));
    }
    if(room>=0){
        for(i=0;i<nconts;i++)if(conts[i].room==room)for(j=0;j<conts[i].n;j++){
            aw_inventory_item_t item;
            assert(AW_InventoryRead(conts[i].id[j],&item));
            for(k=0;k<nitems;k++)if(!Q_strcasecmp(items[k].id,item.id))break;
            assert(k<nitems && !strcmp(item.name,items[k].name));
        }
        for(i=0;i<nplaced;i++){
            char id[64];int owned;
            if(placed[i].room!=room)continue;
            assert(AW_PlacedBook(placed[i].ref,id,&owned) && !Q_strcasecmp(id,placed[i].id));
        }
        for(i=0;i<nicons;i++){
            char key[64];int w,h;byte pixels[32*32];
            for(j=0;j<nconts;j++)if(conts[j].room==room)for(k=0;k<conts[j].n;k++)if(!Q_strcasecmp(conts[j].id[k],icons[i].id))goto here;
            continue;
         here:
            snprintf(key,sizeof(key),"item:%s",icons[i].id);
            assert(AW_AreaIcon(key,&w,&h,pixels,32,32) && w==icons[i].w && h==icons[i].h && pixels[0]==icons[i].first);
        }
        assert(file_opens==opens);                 /* no search of focus.awf or items.awi */
        assert(AW_AreaFallbacks()==fallbacks);
    }
}
/* the icon pack's reader as aw_icons.c gives it: one fixed picture, counted */
static int picture_reads;
static int fake_picture(const char *key,int *w,int *h,unsigned char *pixels,int maxw,int maxh){
    (void)key;assert(maxw>=3 && maxh>=2);picture_reads++;*w=3;*h=2;memset(pixels,77,6);return 1;
}
int main(int argc,char **argv){
    unsigned long s[6],t[6];int rooms[8],nrooms=0,i,j;
    assert(argc==2);folder=argv[1];
    expectations();
    assert(nconts>=3 && nitems>=3 && nplaced>=1 && nicons>=1);
    for(i=0;i<nconts;i++){for(j=0;j<nrooms;j++)if(rooms[j]==conts[i].room)break;if(j==nrooms)rooms[nrooms++]=conts[i].room;}
    assert(nrooms>=3);
    aw_ledger_on=1;AW_LedgerClear(&aw_ledger);AW_StateReset();
    /* phase 1: no area loaded, every answer from the files */
    ask(-1);
    /* phase 2: each room entered, its answers from its table alone */
    for(i=0;i<nrooms;i++){
        AW_AreaStats(s);
        enter(rooms[i]);
        AW_AreaStats(t);
        assert(t[0]==s[0]+1 && t[5]==1);          /* one area read with the room */
        ask(rooms[i]);
    }
    /* load and unload: back into the first room: taken from the cache of areas left, nothing read */
    AW_AreaStats(s);enter(rooms[0]);AW_AreaStats(t);
    assert(t[0]==s[0] && t[2]==s[2]+1 && t[4]==s[4]);
    ask(rooms[0]);
    /* the memory policy trims the cache: the next room is read again */
    assert(AW_AreaCacheTrim(1L<<30)>0);
    AW_AreaStats(s);enter(rooms[1]);AW_AreaStats(t);
    assert(t[0]==s[0]+1);
    ask(rooms[1]);
    /* narrow loads: a container of another room (the cache emptied first), through the directory */
    AW_AreaCacheTrim(1L<<30);
    {int other=-1,opens=file_opens;unsigned long fb=AW_AreaFallbacks();aw_container_item_t got[AW_CONTAINER_ITEMS];
     for(i=0;i<nconts;i++)if(conts[i].room!=rooms[1] && conts[i].n>0){other=i;break;}
     assert(other>=0);
     AW_AreaStats(s);
     assert(AW_ContainerContents(conts[other].ref,got,AW_CONTAINER_ITEMS,NULL)==conts[other].n);
     AW_AreaStats(t);
     assert(t[3]==s[3]+1 && file_opens==opens && AW_AreaFallbacks()==fb);
     /* an item of another room by the item directory (a placed item's record: never asked before, so not in memory) */
     AW_AreaCacheTrim(1L<<30);
     for(i=0;i<nplaced;i++)if(placed[i].room!=rooms[1])break;
     assert(i<nplaced);
     {aw_inventory_item_t item;
      AW_AreaStats(s);
      assert(AW_InventoryRead(placed[i].id,&item));
      AW_AreaStats(t);
      assert(t[3]==s[3]+1 && file_opens==opens && AW_AreaFallbacks()==fb);}
    }
    /* a carried item from another room: its record and picture read while a room loads, then answered from memory */
    {int other=-1,w,h;byte px[32*32];char key[64];unsigned long fb;
     for(i=0;i<nicons;i++)for(j=0;j<nconts;j++)if(conts[j].room!=rooms[2] && conts[j].n && !Q_strcasecmp(conts[j].id[0],icons[i].id))other=i;
     assert(other>=0);
     aw_area_picture_read=fake_picture;
     AW_ItemAdd(&aw_state,icons[other].id,1);
     AW_AreaCacheTrim(1L<<30);
     enter(rooms[2]);
     assert(picture_reads==1);
     AW_AreaCacheTrim(1L<<30);
     AW_AreaStats(s);fb=AW_AreaFallbacks();
     snprintf(key,sizeof(key),"item:%s",icons[other].id);
     assert(AW_AreaIcon(key,&w,&h,px,32,32)==1 && w==3 && h==2 && px[0]==77);
     AW_AreaStats(t);
     assert(t[3]==s[3] && AW_AreaFallbacks()==fb && picture_reads==1);   /* no narrow load, no search */
    }
    AW_LedgerClear(&aw_ledger);
    puts("aga_area_tables_test ok");
    return 0;
}
