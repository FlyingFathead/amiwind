/* SPDX-License-Identifier: GPL-3.0-only
 * Real drop transaction + real bounded BSP-region queries. Synthetic hull0
 * contents deliberately include obstructions missed by the point-trace stub.
 * Thus thin walls/holes are tested independently of a sampled ray oracle. */
#include "quakedef.h"
#include "aw_inventory.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
static client_t client;
static edict_t entities[MAX_EDICTS];
static model_t world,item_model;
static mplane_t planes[6];
static dclipnode_t nodes[6];
static byte cache_token;
char *pr_strings;
static char strings[64];
static int allocations,links,notices,trace_calls,path_blocked,wet,streamed,scenery,restricted;
int Chim_Active(void){return streamed;}
int AW_SceneryCount(void){return scenery;}
int AW_StoryRestricted(void){return restricted;}
void Con_Printf(char *format,...){(void)format;}
int COM_FOpenFile(char *name,FILE **file){(void)name;*file=NULL;return -1;}
void CDAudio_Update(void){}
void S_ExtraUpdate(void){}
static aw_inventory_item_t item;
edict_t *EDICT_NUM(int i){assert(i>=0 && i<MAX_EDICTS);return &entities[i];}
edict_t *ED_Alloc(void){
    int i;for(i=2;i<sv.num_edicts;i++)if(entities[i].free && (entities[i].freetime<2 || sv.time-entities[i].freetime>.5))break;
    assert(i<MAX_EDICTS);if(i==sv.num_edicts)sv.num_edicts++;
    memset(&entities[i],0,sizeof(entities[i]));allocations++;return &entities[i];
}
void ED_Free(edict_t *e){e->free=1;e->freetime=sv.time;}
char *ED_NewString(char *name){assert(!strcmp(name,"aw_inventory_drop"));return strings+1;}
void SV_LinkEdict(edict_t *e,qboolean triggers){assert(!triggers && !e->free);links++;}
model_t *Mod_ForName(char *name,qboolean crash){assert(!crash);return &item_model;}
void *Cache_Check(cache_user_t *cache){return cache->data;}
void AW_UIPickupNotice(const char *name,double duration){assert(duration==2);notices++;}
void AW_CombatEquipmentStore(void){}
void AW_CombatEquipmentChanged(void){}
trace_t SV_Move(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,int type,edict_t *pass){
    trace_t tr;int k;memset(&tr,0,sizeof(tr));tr.fraction=1;VectorCopy(end,tr.endpos);tr.plane.normal[2]=1;
    for(k=0;k<3;k++)assert(mins[k]==0 && maxs[k]==0);
    assert(type==MOVE_NORMAL && pass==&entities[1]);trace_calls++;
    if(start[2]==end[2]){if(path_blocked)tr.fraction=.5f;}
    else{tr.fraction=.1f;tr.endpos[2]=0;}
    return tr;
}
int SV_PointContents(vec3_t p){return wet?CONTENTS_WATER:CONTENTS_EMPTY;}
static void plane(int i,int axis,float distance){
    planes[i].normal[axis]=1;planes[i].dist=distance;planes[i].type=axis;nodes[i].planenum=i;
}
static void reset(int geometry){
    int i;
    memset(&sv,0,sizeof(sv));memset(&svs,0,sizeof(svs));memset(&aw_state,0,sizeof(aw_state));
    memset(entities,0,sizeof(entities));memset(&world,0,sizeof(world));memset(&item_model,0,sizeof(item_model));
    memset(planes,0,sizeof(planes));memset(nodes,0,sizeof(nodes));memset(&item,0,sizeof(item));
    allocations=links=notices=trace_calls=path_blocked=wet=streamed=scenery=restricted=0;pr_strings=strings;
    sv.active=1;sv.num_edicts=2;sv.time=10;strcpy(sv.name,"seyda");svs.maxclients=1;svs.clients=&client;client.edict=&entities[1];
    entities[1].v.health=100;entities[1].v.movetype=MOVETYPE_WALK;entities[1].v.origin[2]=16;entities[1].v.view_ofs[2]=16;
    world.type=mod_brush;world.numplanes=6;world.hulls[0].planes=planes;world.hulls[0].clipnodes=nodes;
    world.hulls[0].firstclipnode=0;world.hulls[0].lastclipnode=5;sv.worldmodel=&world;
    plane(0,2,0);nodes[0].children[0]=CONTENTS_EMPTY;nodes[0].children[1]=CONTENTS_SOLID;
    if(geometry==1){ /* infinitely thin-abovefloor wall between eye and drop */
        nodes[0].children[0]=1;plane(1,0,10);plane(2,0,10.01f);
        nodes[1].children[0]=2;nodes[1].children[1]=CONTENTS_EMPTY;
        nodes[2].children[0]=CONTENTS_EMPTY;nodes[2].children[1]=CONTENTS_SOLID;
    }
    if(geometry==2){ /* unsupported edge at x25, item spans22..26 */
        nodes[0].children[1]=1;plane(1,0,25);
        nodes[1].children[0]=CONTENTS_EMPTY;nodes[1].children[1]=CONTENTS_SOLID;
    }
    if(geometry==3){ /* 0.01-wide hole inside footprint, not at centre/corners */
        nodes[0].children[1]=1;plane(1,0,24.5f);plane(2,0,24.51f);
        nodes[1].children[0]=2;nodes[1].children[1]=CONTENTS_SOLID;
        nodes[2].children[0]=CONTENTS_SOLID;nodes[2].children[1]=CONTENTS_EMPTY;
    }
    item_model.type=mod_alias;item_model.cache.data=&cache_token;
    item_model.mins[0]=item_model.mins[1]=-2;item_model.maxs[0]=item_model.maxs[1]=2;item_model.maxs[2]=2;
    for(i=2;i<MAX_EDICTS;i++)entities[i].free=0;
    strcpy(item.id,"fixture0");strcpy(item.name,"Fixture");strcpy(item.model,"progs/inv/fixture0.mdl");item.flags=AW_INV_DROP;
    assert(AW_ItemAdd(&aw_state,item.id,2));
    AW_InventorySpawn(); /* clears per-level model state with no saved drops */
}
static void refused(void){
    static aw_state_t before;int allocated=allocations;
    before=aw_state;assert(!AW_InventoryDropHere(&item,1));assert(!memcmp(&before,&aw_state,sizeof(before)));assert(allocations==allocated);
}
int main(void){
    int i;
    reset(0);assert(AW_InventoryDropHere(&item,1));assert(links==1 && notices==1);
    assert(AW_StateGet(&aw_state,AW_ITEM,item.id)==1 && aw_state.inventory.dropped[0].count==1);
    assert(aw_state.inventory.dropped[0].position[2]>.0f);
    reset(1);refused(); /* swept full-box query catches thin wall even when point stub misses it */
    reset(2);refused();
    reset(3);refused();
    reset(0);path_blocked=1;refused();assert(trace_calls==1);
    reset(0);wet=1;refused();
    reset(0);streamed=1;refused();assert(!trace_calls && strstr(AW_InventoryDropReason(),"area"));
    reset(0);scenery=1;refused();assert(!trace_calls);
    reset(0);restricted=1;refused();assert(!trace_calls);
    reset(0);sv.num_edicts=MAX_EDICTS;refused();assert(!trace_calls);
    entities[2].free=1;entities[2].freetime=9.75f;refused(); /* exact ED_Alloc quarantine */
    entities[2].freetime=9;assert(AW_InventoryDropHere(&item,1));
    reset(0);
    for(i=0;i<AW_INVENTORY_DROPS;i++){strcpy(aw_state.inventory.dropped[i].id,"full");aw_state.inventory.dropped[i].count=1;}
    refused();assert(!trace_calls);
    reset(0);
    for(i=0;i<AW_INVENTORY_MODELS;i++){
        sprintf(item.id,"fixture%ld",(long)i);sprintf(item.model,"progs/inv/fixture%ld.mdl",(long)i);
        if(i)assert(AW_ItemAdd(&aw_state,item.id,1));
        assert(AW_InventoryDropHere(&item,1));
    }
    sprintf(item.id,"fixture%ld",(long)i);sprintf(item.model,"progs/inv/fixture%ld.mdl",(long)i);
    assert(AW_ItemAdd(&aw_state,item.id,1));refused();assert(strstr(AW_InventoryDropReason(),"16"));
    /* Existing model slot still works after the distinct-model cap, no duplicate slot. */
    strcpy(item.id,"fixture0");strcpy(item.model,"progs/inv/fixture0.mdl");assert(AW_InventoryDropHere(&item,1));
    reset(2);
    /* Long localY footprint fits edge at yaw0, but yaw90 rotates its long axis over the unsupported edge. */
    item_model.mins[0]=-.25f;item_model.maxs[0]=.25f;item_model.mins[1]=-4;item_model.maxs[1]=4;
    entities[1].v.v_angle[1]=90;entities[1].v.origin[0]=24;entities[1].v.origin[1]=-24;
    refused();
    puts("Real drop: thin wall/hole/edge, forward path, rotated footprint, allocator quarantine,32drop/16model admission and no-loss passed.");
    return 0;
}
