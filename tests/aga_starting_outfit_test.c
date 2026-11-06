/* SPDX-License-Identifier: GPL-3.0-only
 * CHARGEN-NO-STARTING-CLOTHES-60: the player record's starting outfit (inventory/initial.awi) is carried and worn from
 * the first scene spawn on, once per game, whatever was taken before the inventory was first opened. The real
 * AW_InventorySpawn and AW_InventoryBootstrap over items.awi and initial.awi written by tools/prepare_inventory.py from
 * a synthetic master (tests/test_aga_native_source.py), read from the folder in argv[1]. */
#include "quakedef.h"
#include "aw_inventory.h"
#include "aw_ledger.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
static client_t client;
static edict_t entities[8];
static model_t world;
char *pr_strings;
static char strings[16];
static const char *folder;
static int changed;
int Chim_Active(void){return 0;}
int AW_SceneryCount(void){return 0;}
int AW_StoryRestricted(void){return 1;}
void Con_Printf(char *format,...){(void)format;}
int COM_FOpenFile(char *name,FILE **file){
    char path[512];long size;
    *file=NULL;
    if(strcmp(name,"inventory/items.awi") && strcmp(name,"inventory/initial.awi"))return -1;
    snprintf(path,sizeof(path),"%s/%s",folder,name);
    if(!(*file=fopen(path,"rb")))return -1;
    fseek(*file,0,SEEK_END);size=ftell(*file);rewind(*file);
    return (int)size;
}
void CDAudio_Update(void){}
void S_ExtraUpdate(void){}
edict_t *EDICT_NUM(int i){assert(i>=0 && i<8);return &entities[i];}
edict_t *ED_Alloc(void){assert(0);return NULL;}
void ED_Free(edict_t *e){(void)e;assert(0);}
char *ED_NewString(char *name){(void)name;assert(0);return NULL;}
void SV_LinkEdict(edict_t *e,qboolean triggers){(void)e;(void)triggers;}
model_t *Mod_ForName(char *name,qboolean crash){(void)name;(void)crash;assert(0);return NULL;}
void *Cache_Check(cache_user_t *cache){(void)cache;assert(0);return NULL;}
void AW_UIPickupNotice(const char *name,double duration){(void)name;(void)duration;}
void AW_CombatEquipmentStore(void){}
void AW_CombatEquipmentChanged(void){changed++;}
trace_t SV_Move(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,int type,edict_t *pass){
    trace_t tr;(void)start;(void)mins;(void)maxs;(void)type;(void)pass;
    memset(&tr,0,sizeof(tr));tr.fraction=1;VectorCopy(end,tr.endpos);return tr;
}
int SV_PointContents(vec3_t p){(void)p;return CONTENTS_EMPTY;}
static const char *const outfit[3]={"common_shirt_01","common_pants_01","common_shoes_01"};
static const int slot[3]={AW_SLOT_SHIRT,AW_SLOT_PANTS,AW_SLOT_BOOTS};
static void scene(const char *name){
    memset(&sv,0,sizeof(sv));memset(&svs,0,sizeof(svs));memset(entities,0,sizeof(entities));
    pr_strings=strings;sv.active=1;sv.num_edicts=2;strcpy(sv.name,name);svs.maxclients=1;svs.clients=&client;
    client.edict=&entities[1];entities[1].v.health=100;world.type=mod_brush;sv.worldmodel=&world;
    AW_InventorySpawn();
}
/* every piece carried once and worn in its own slot */
static void dressed(void){
    int i;
    for(i=0;i<3;i++){
        assert(AW_StateGet(&aw_state,AW_ITEM,outfit[i])==1);
        assert(AW_InventoryEquipped(&aw_state,outfit[i])==1 && !strcmp(aw_state.inventory.equipped[slot[i]],outfit[i]));
    }
    assert(AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:inventory:outfit")==1 && aw_state.inventory.initialized);
}
int main(int argc,char **argv){
    int i;
    assert(argc==2);folder=argv[1];aw_ledger_on=0;
    /* the new game: the ship's first spawn dresses the player */
    AW_StateReset();scene("prison");dressed();assert(changed==1);
    /* the reported route: something taken in the Census Office (a take marks the inventory initialized) before the
     * outfit was ever given; the old guard skipped the outfit for good there */
    AW_StateReset();
    assert(AW_ItemAdd(&aw_state,"ingred_bread_01",1));aw_state.inventory.initialized=1;
    scene("census");dressed();assert(AW_StateGet(&aw_state,AW_ITEM,"ingred_bread_01")==1);
    /* once per game: the shirt taken off and sold stays gone through the next scenes and the inventory window */
    assert(AW_InventoryUnequip(&aw_state,"common_shirt_01")==1 && AW_ItemAdd(&aw_state,"common_shirt_01",-1));
    scene("seyda");assert(AW_InventoryBootstrap());
    assert(!AW_StateGet(&aw_state,AW_ITEM,"common_shirt_01") && !aw_state.inventory.equipped[AW_SLOT_SHIRT][0]);
    assert(AW_StateGet(&aw_state,AW_ITEM,"common_pants_01")==1);
    /* a save from before the fix (the outfit flag missing): what it lacks is given and worn, nothing doubled; a
     * piece it already wears in another slot is not worn twice */
    AW_StateReset();aw_state.inventory.initialized=1;
    assert(AW_ItemAdd(&aw_state,"common_shirt_01",1) && AW_ItemAdd(&aw_state,"common_pants_01",1));
    strcpy(aw_state.inventory.equipped[AW_SLOT_SKIRT],"common_pants_01");
    scene("balmora");
    assert(AW_StateGet(&aw_state,AW_ITEM,"common_shirt_01")==1 && AW_StateGet(&aw_state,AW_ITEM,"common_pants_01")==1);
    assert(!strcmp(aw_state.inventory.equipped[AW_SLOT_SHIRT],"common_shirt_01"));
    assert(AW_InventoryEquipped(&aw_state,"common_pants_01")==1 && !aw_state.inventory.equipped[AW_SLOT_PANTS][0]);
    assert(AW_StateGet(&aw_state,AW_ITEM,"common_shoes_01")==1 && AW_InventoryEquipped(&aw_state,"common_shoes_01")==1);
    /* the inventory window opened first (the earlier route) gives the same outfit, once */
    AW_StateReset();assert(AW_InventoryBootstrap());dressed();scene("seyda");dressed();
    /* no outfit file in the image: nothing invented, the scene still spawns, no flag set (the next image tries again) */
    folder="/nonexistent-amiwind-fixture";AW_StateReset();scene("seyda");
    for(i=0;i<3;i++)assert(!AW_StateGet(&aw_state,AW_ITEM,outfit[i]));
    assert(!AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:inventory:outfit"));
    puts("aga_starting_outfit_test ok");
    return 0;
}
