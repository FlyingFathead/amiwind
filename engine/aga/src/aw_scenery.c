/* SPDX-License-Identifier: GPL-2.0-or-later
 * Immutable exterior placements do not occupy QuakeC edicts or signon packets.
 * Rendering and collision use the same complete placement catalogue. Geometry
 * residency is bounded by the current overlapping exterior sub-cell BSP.
 */
#include "quakedef.h"
#include "aw_harvest_runtime.h"
#include "aw_town.h"
#include "chim/chim.h"
extern void AW_MergeCollisionTrace(trace_t *,trace_t *,edict_t *);
/* CHIM world streamer (chim/chim_world.c sets these only when its data
 * exists): chunk placements are this catalogue's successor, so they enter
 * and leave with it, link with it and clip with it. */
void (*aw_chim_map_begin)(const char *);
void (*aw_chim_map_end)(void);
void (*aw_chim_link)(void);
void (*aw_chim_clip)(vec3_t,vec3_t,vec3_t,vec3_t,trace_t *);
typedef struct {
    entity_t render;
    vec3_t mins,maxs;
    int modelindex;
} aw_scenery_t;
static aw_scenery_t *placements;
static int count,capacity;

/* Only validated converted town layouts (town table flag AW_TOWN_SCENERY:
 * Balmora's bm000..bm063, the Arena's va000..) share the alias catalogue.
 * Exact names and region numbers below the town's cap, never a loose prefix
 * match, so unrelated/scripted map entities are not captured silently. */
static int AW_SceneryMapEnabled(const char *name)
{
    int town=AW_TownFind(name);
    if(town<0)town=AW_TownRegionMap(name);
    return town>=0 && (AW_Town(town)->flags&AW_TOWN_SCENERY)!=0;
}

void AW_SceneryClear(void) { placements=NULL;count=capacity=0;if(aw_chim_map_end)aw_chim_map_end(); }
void AW_SceneryBegin(const char *entities)
{
    const char *p=entities;
    AW_SceneryClear();AW_HarvestBegin();
    if(aw_chim_map_begin)aw_chim_map_begin(entities);
    if(!AW_SceneryMapEnabled(sv.name))return;
    while((p=strstr(p,"\"classname\" \"func_wall\""))!=NULL){capacity++;p++;}
    if(capacity>AW_SCENERY_MAX_PLACEMENTS)
        Host_Error("Scenery catalogue of %s exceeds %d placements",sv.name,AW_SCENERY_MAX_PLACEMENTS);
    if(capacity)placements=Hunk_AllocName(capacity*sizeof(*placements),"scenery");
}
int AW_SceneryCapture(edict_t *e)
{
    aw_scenery_t *p;model_t *model;vec3_t forward,right,up,corner;float v;int i,j,k;
    if(!AW_SceneryMapEnabled(sv.name) || !e->v.classname ||
       strcmp(pr_strings+e->v.classname,"func_wall"))return 0;
    if(AW_HarvestProtect(e))return 0;
    if(count>=capacity)Host_Error("Balmora scenery catalogue count mismatch");
    p=&placements[count++];p->modelindex=SV_ModelIndex(pr_strings+e->v.model);
    model=sv.models[p->modelindex];
    if(!model || model->type!=mod_brush)Host_Error("Balmora scenery model is not BSP");
    p->render.model=model;VectorCopy(e->v.origin,p->render.origin);VectorCopy(e->v.angles,p->render.angles);
    AngleVectors(e->v.angles,forward,right,up);
    for(i=0;i<3;i++){p->mins[i]=1e20f;p->maxs[i]=-1e20f;}
    for(j=0;j<8;j++){
        for(i=0;i<3;i++)corner[i]=(j&(1<<i))?model->maxs[i]:model->mins[i];
        for(k=0;k<3;k++){
            v=e->v.origin[k]+corner[0]*forward[k]-corner[1]*right[k]+corner[2]*up[k];
            if(v-1<p->mins[k])p->mins[k]=v-1;
            if(v+1>p->maxs[k])p->maxs[k]=v+1;
        }
    }
    return 1;
}
void AW_SceneryLink(void)
{
    int i;
    if(aw_chim_link)aw_chim_link();
    if(!sv.active || !AW_SceneryMapEnabled(sv.name))return;
    if(cl_numvisedicts+count>MAX_VISEDICTS)Host_Error("Balmora visible entity budget exceeded");
    for(i=0;i<count;i++)cl_visedicts[cl_numvisedicts++]=&placements[i].render;
}
void AW_SceneryClip(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,trace_t *best)
{
    int i,k;vec3_t low,high;edict_t solid;trace_t hit;aw_scenery_t *p;
    if(aw_chim_clip){aw_chim_clip(start,mins,maxs,end,best);if(best->allsolid)return;}
    if(!count)return;
    for(k=0;k<3;k++){
        low[k]=(start[k]<end[k]?start[k]:end[k])+mins[k]-1;
        high[k]=(start[k]>end[k]?start[k]:end[k])+maxs[k]+1;
    }
    memset(&solid,0,sizeof(solid));solid.v.solid=SOLID_BSP;solid.v.movetype=MOVETYPE_PUSH;
    for(i=0;i<count;i++){
        p=&placements[i];
        for(k=0;k<3;k++)if(low[k]>p->maxs[k] || high[k]<p->mins[k])break;
        if(k!=3)continue;
        solid.v.modelindex=p->modelindex;
        VectorCopy(p->render.origin,solid.v.origin);VectorCopy(p->render.angles,solid.v.angles);
        hit=SV_ClipMoveToEntity(&solid,start,mins,maxs,end);
        /* Static scenery is world collision, never return the stack proxy. */
        AW_MergeCollisionTrace(best,&hit,sv.edicts);
        if(best->allsolid)return;
    }
}
