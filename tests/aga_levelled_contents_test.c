/* SPDX-License-Identifier: GPL-3.0-only
 * CONTAINER-LEVELLED-CONTENTS-60 and CORPSE-LOOT-60: a container's levelled entries and an actor's inventory through
 * the per-area tables (id1/areas.awa written by tools/prepare_area_tables.py over a synthetic focus.awf with its AWL1
 * lists; tests/test_aga_native_source.py levelled_fixture), rolled with the CHIM actor table's list code
 * (ChimActors_LevelledPick) on the first open: the player's level picks the entry (highest at or below it), "Each"
 * rolls one per count, a list inside a list, chance none 100 gives nothing; the result stays on the world change list
 * (a second open rolls nothing), a respawn refill drops it and the next open rolls again at the level then; an actor's
 * inventory is its NPCO list plus its rolled entries, and a take from it is no theft. */
#include "quakedef.h"
#include "aw_inventory.h"
#include "aw_ledger.h"
#include "chim/chim_actor_table.h"
#include <assert.h>
#include <stdarg.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
static client_t client;
static edict_t entities[8];
static model_t world;
char *pr_strings;
static char strings[16];
static const char *folder;
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
    if(strcmp(name,"areas.awa") && strcmp(name,"focus.awf") && strcmp(name,"inventory/items.awi"))return -1;
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
static int level=1;
static int player_level(void){return level;}
static int lists_valid(const unsigned char *s,unsigned long bytes,unsigned items){return ChimActors_ListsValid(s,bytes,items);}
static char entity_text[96];
static void enter(int room){
    memset(&sv,0,sizeof(sv));memset(&svs,0,sizeof(svs));memset(entities,0,sizeof(entities));
    pr_strings=strings;sv.active=1;sv.num_edicts=2;strcpy(sv.name,"room");svs.maxclients=1;svs.clients=&client;
    client.edict=&entities[1];entities[1].v.movetype=MOVETYPE_WALK;
    snprintf(entity_text,sizeof(entity_text),"{\n\"classname\" \"worldspawn\"\n\"_aw_cell_int\" \"%d\"\n}\n",room);
    world.entities=entity_text;sv.worldmodel=&world;
    AW_PlacedRefresh();
}
/* the contents of REF are exactly the N (id, count) pairs; no mark among them */
static void expect(unsigned ref,int n,...){
    aw_container_item_t got[AW_CONTAINER_ITEMS];int k=AW_ContainerContents(ref,got,AW_CONTAINER_ITEMS,NULL),i,j;va_list a;
    if(k!=n){for(i=0;i<k;i++)printf("  %u: %s %d\n",ref,got[i].id,got[i].count);}
    assert(k==n);
    for(i=0;i<k;i++)assert(got[i].id[0]!='*');
    va_start(a,n);
    for(i=0;i<n;i++){
        const char *id=va_arg(a,const char *);int count=va_arg(a,int);
        for(j=0;j<k;j++)if(!Q_strcasecmp(got[j].id,(char *)id))break;
        if(j==k || got[j].count!=count)printf("  %u: want %s %d\n",ref,id,count);
        assert(j<k && got[j].count==count);
    }
    va_end(a);
}
int main(int argc,char **argv){
    unsigned long rolls;
    assert(argc==2);folder=argv[1];
    aw_ledger_on=1;AW_LedgerClear(&aw_ledger);memset(&aw_state,0,sizeof(aw_state));
    aw_levelled_valid=lists_valid;aw_levelled_pick=ChimActors_LevelledPick;aw_levelled_level=player_level;aw_levelled_seed=7;
    enter(10);
    /* level 1: the list's level-1 entry; "Each" x 3 one gem each; chance none 100: nothing; the data's own item kept */
    expect(1000,3,"base_item",2,"lev_low",1,"gem",3);
    rolls=aw_levelled_rolls;
    assert(rolls==5);
    expect(1000,3,"base_item",2,"lev_low",1,"gem",3);   /* again: kept, nothing rolled */
    assert(aw_levelled_rolls==rolls);
    /* level 10: the highest entry at or below it; a whole count of one roll; a list inside a list */
    level=10;
    expect(1001,2,"lev_high",2,"gem",1);
    /* CORPSE-LOOT-60: an actor's inventory (its NPCO and its rolled entry); a take from it is no theft */
    expect(1002,2,"npc_shirt",1,"gem",2);
    assert(AW_ContainerChange(1002,"gem",-1,1)==1);
    assert(AW_LedgerStolenCount(&aw_ledger,"gem",NULL,0)==0);
    expect(1002,2,"npc_shirt",1,"gem",1);
    /* a respawn refill: the deltas and the mark go; the next open rolls again, at the level now */
    assert(AW_LedgerContentDrop(&aw_ledger,1000)>0);
    expect(1000,3,"base_item",2,"lev_high",1,"gem",3);
    /* the mark survives as an ordinary content entry (saved with the list), never as an item */
    assert(AW_LedgerContentDelta(&aw_ledger,1000,"*levelled")==1);
    /* a rolled item's record (named by id in the room's pool, held by an item chunk): the item directory's narrow
     * load answers it, never a search of items.awi */
    {aw_inventory_item_t item;unsigned long fb=AW_AreaFallbacks(),s[6],t[6];
     AW_AreaStats(s);
     assert(AW_InventoryRead("lev_high",&item) && !strcmp(item.name,"Lev_High"));
     AW_AreaStats(t);
     assert(AW_AreaFallbacks()==fb && t[3]==s[3]+1);}
    AW_LedgerClear(&aw_ledger);
    puts("aga_levelled_contents_test ok");
    return 0;
}
