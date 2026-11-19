/* SPDX-License-Identifier: GPL-3.0-only
 * INVENTORY-EQUIP-HINTS-67 (EQUIP-ACTION-REGRESSION-62, SCROLL-CAST-64): which kind of item gets which action in the
 * inventory window, over a catalogue the real builder stage wrote (tools/prepare_inventory.py, from a synthetic master
 * with one record of every item kind and subtype; tests/test_inventory_actions.py), read by the real reader
 * (aw_inventory.c AW_InventoryScan) and judged by the real rule (AW_InventoryItemAction). argv[1]: the id1 folder;
 * argv[2]: the expected table, one line per record "ID<TAB>ACTION" (none, equip, use, cast, read). Every catalogue row
 * must be in the table and every table row in the catalogue, so a new kind without a decided action fails here. */
#include "quakedef.h"
#include "aw_inventory.h"
#include "aw_ledger.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
char *pr_strings;
static const char *folder;
int Chim_Active(void){return 0;}
int AW_SceneryCount(void){return 0;}
int AW_StoryRestricted(void){return 0;}
void Con_Printf(char *format,...){(void)format;}
int COM_FOpenFile(char *name,FILE **file){
    char path[512];long size;
    *file=NULL;
    if(strcmp(name,"inventory/items.awi"))return -1;
    snprintf(path,sizeof(path),"%s/%s",folder,name);
    if(!(*file=fopen(path,"rb")))return -1;
    fseek(*file,0,SEEK_END);size=ftell(*file);rewind(*file);
    return (int)size;
}
void CDAudio_Update(void){}
void S_ExtraUpdate(void){}
edict_t *EDICT_NUM(int i){(void)i;assert(0);return NULL;}
edict_t *ED_Alloc(void){assert(0);return NULL;}
void ED_Free(edict_t *e){(void)e;assert(0);}
char *ED_NewString(char *name){(void)name;assert(0);return NULL;}
void SV_LinkEdict(edict_t *e,qboolean triggers){(void)e;(void)triggers;}
model_t *Mod_ForName(char *name,qboolean crash){(void)name;(void)crash;assert(0);return NULL;}
void *Cache_Check(cache_user_t *cache){(void)cache;assert(0);return NULL;}
void AW_UIPickupNotice(const char *name,double duration){(void)name;(void)duration;}
void AW_CombatEquipmentStore(void){}
void AW_CombatEquipmentChanged(void){}
trace_t SV_Move(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,int type,edict_t *pass){
    trace_t tr;(void)start;(void)mins;(void)maxs;(void)type;(void)pass;
    memset(&tr,0,sizeof(tr));tr.fraction=1;VectorCopy(end,tr.endpos);return tr;
}
int SV_PointContents(vec3_t p){(void)p;return CONTENTS_EMPTY;}

#define ROWS 256
static struct {char id[64],want[16];int seen;} table[ROWS];
static int rows,faults,scanned;
static const char *const names[]={"none","equip","unequip","use","cast","read"};
static void each(void *ctx,const aw_inventory_item_t *it){
    int i,action;(void)ctx;
    scanned++;
    for(i=0;i<rows && strcmp(table[i].id,it->id);i++);
    if(i==rows){printf("FAULT %s (category %d, flags %u): a catalogue row the table has no action for\n",it->id,
                       it->category,(unsigned)it->flags);faults++;return;}
    table[i].seen++;
    action=AW_InventoryItemAction(it,0);
    if(action<0 || action>AW_INV_ACT_READ || strcmp(names[action],table[i].want)){
        printf("FAULT %s: the window offers %s, the table says %s\n",it->id,action>=0 && action<=AW_INV_ACT_READ?
               names[action]:"?",table[i].want);faults++;
    }
    /* worn, an equippable item is taken off; nothing else changes with wearing */
    if(action==AW_INV_ACT_EQUIP && AW_InventoryItemAction(it,1)!=AW_INV_ACT_UNEQUIP){printf("FAULT %s: worn\n",it->id);faults++;}
}
int main(int argc,char **argv){
    FILE *f;char line[160];int i;
    assert(argc==3);folder=argv[1];aw_ledger_on=0;
    assert((f=fopen(argv[2],"r"))!=NULL);
    while(fgets(line,sizeof(line),f)){
        char *tab=strchr(line,'\t'),*end;
        if(!tab)continue;
        *tab=0;end=tab+1+strcspn(tab+1,"\r\n");*end=0;
        assert(rows<ROWS && strlen(line)<64 && strlen(tab+1)<16);
        strcpy(table[rows].id,line);strcpy(table[rows].want,tab+1);rows++;
    }
    fclose(f);
    assert(AW_InventoryScan(each,NULL)==scanned && scanned>0);
    for(i=0;i<rows;i++)if(table[i].seen!=1){printf("FAULT %s: in the table, %d times in the catalogue\n",table[i].id,table[i].seen);faults++;}
    if(faults)return 1;
    printf("inventory actions: %d catalogue rows, every kind's action as the table says\n",scanned);
    return 0;
}
