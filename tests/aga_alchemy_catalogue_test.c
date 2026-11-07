/* SPDX-License-Identifier: GPL-3.0-only
 * ALCHEMY-61: the alchemy block of the item catalogue (aw_inventory.c inv_parse_row) as tools/prepare_inventory.py
 * writes it from a synthetic master (tests/test_alchemy.py), read from the folder in argv[1]: an ingredient's four
 * slots with the attribute or skill only where the effect names one, a potion's effects with duration and magnitude,
 * an apparatus' type and quality; a made potion (a made item of cast type AW_MADE_POTION) read as a potion of its own;
 * the inventory's use offered for the three kinds only; a damaged block refused. */
#include "quakedef.h"
#include "aw_inventory.h"
#include "aw_actorstate.h"
#include "aw_ledger.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
static edict_t entities[8];
char *pr_strings;
static const char *folder;
int Chim_Active(void){return 0;}
int AW_SceneryCount(void){return 0;}
int AW_StoryRestricted(void){return 1;}
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
edict_t *EDICT_NUM(int i){assert(i>=0 && i<8);return &entities[i];}
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
static aw_made_item_t made;
static const aw_made_item_t *made_at(int i){return i==0?&made:NULL;}
static int used;
static int use_stub(const aw_inventory_item_t *it){(void)it;used++;return 1;}
int main(int argc,char **argv){
    aw_inventory_item_t it;
    assert(argc==2);folder=argv[1];aw_ledger_on=0;
    /* the ingredient: Drain Attribute (17) Agility, Restore Fatigue (77, its stray skill dropped), slots 3-4 empty */
    assert(AW_InventoryRead("ingred_test_01",&it));
    assert(it.category==AW_INV_INGREDIENT && (it.flags&AW_INV_ALCHEMY) && it.alchemy_kind==AW_ALCHEMY_INGREDIENT);
    assert(it.alchemy_count==4 && it.alchemy[0].effect==17 && it.alchemy[0].arg==3);
    assert(it.alchemy[1].effect==77 && it.alchemy[1].arg==0xFF && it.alchemy[2].effect==AW_ALCHEMY_NO_EFFECT);
    assert(it.alchemy[3].effect==AW_ALCHEMY_NO_EFFECT && it.weapon==0 && it.weapon_skill==26 && it.health==0);
    assert(it.weight==.5f && it.value==3);
    /* the potion: Restore Health 10 for 1 s and Fortify Skill (83) Alchemy 5 for 30 s */
    assert(AW_InventoryRead("p_test_b",&it));
    assert(it.category==AW_INV_POTION && it.alchemy_kind==AW_ALCHEMY_POTION && it.alchemy_count==2);
    assert(it.alchemy[0].effect==75 && it.alchemy[0].arg==0xFF && it.alchemy[0].magnitude==10 && it.alchemy[0].duration==1);
    assert(it.alchemy[1].effect==83 && it.alchemy[1].arg==16 && it.alchemy[1].magnitude==5 && it.alchemy[1].duration==30);
    /* the apparatus: a calcinator of quality 1.2 (a Misc item, its type the subtype) */
    assert(AW_InventoryRead("apparatus_test_calc",&it));
    assert(it.category==AW_INV_MISC && it.alchemy_kind==AW_ALCHEMY_APPARATUS && it.subtype==2);
    assert(it.apparatus_quality>1.19f && it.apparatus_quality<1.21f && it.alchemy_count==0);
    /* a plain Misc item has no block and no use */
    assert(AW_InventoryRead("misc_test",&it) && !(it.flags&AW_INV_ALCHEMY) && it.alchemy_kind==0);
    assert(!AW_InventoryUsable(&it));
    /* the use is offered only with the hook set */
    assert(AW_InventoryRead("p_test_b",&it) && !AW_InventoryUsable(&it));
    aw_inventory_use=use_stub;
    assert(AW_InventoryUsable(&it) && aw_inventory_use(&it)==1 && used==1);
    /* a made potion: the bottle of p_test_b, its own name, weight, value and effects */
    memset(&made,0,sizeof(made));
    strcpy(made.base,"p_test_b");strcpy(made.name,"Restore Fatigue");made.charge=.75f;made.charge_max=29;
    made.cast_type=AW_MADE_POTION;made.effects=1;
    made.effect[0].effect=77;made.effect[0].skill=-1;made.effect[0].attribute=-1;made.effect[0].duration=29;
    made.effect[0].magnitude_min=made.effect[0].magnitude_max=10;
    aw_inventory_made_item=made_at;
    assert(AW_InventoryRead("aw_made_0",&it));
    assert(!strcmp(it.id,"aw_made_0") && !strcmp(it.name,"Restore Fatigue") && it.category==AW_INV_POTION);
    assert(it.weight==.75f && it.value==29 && it.alchemy_count==1 && it.alchemy[0].effect==77);
    assert(it.alchemy[0].magnitude==10 && it.alchemy[0].duration==29 && it.enchant_kind==0 && !it.enchantment[0]);
    /* a made potion with a bad effect is refused */
    made.effect[0].effect=200;assert(!AW_InventoryRead("aw_made_0",&it));
    puts("aga_alchemy_catalogue_test ok");
    return 0;
}
