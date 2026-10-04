/* SPDX-License-Identifier: GPL-2.0-or-later
 * Immutable exterior placements do not occupy QuakeC edicts or signon packets.
 * Rendering and collision use the same complete placement catalogue. Geometry
 * residency is bounded by the current overlapping exterior sub-cell BSP.
 */
#include "quakedef.h"
extern void AW_MergeCollisionTrace(trace_t *,trace_t *,edict_t *);
typedef struct {
    entity_t render;
    vec3_t mins,maxs;
    int modelindex;
} aw_scenery_t;
static aw_scenery_t *placements;
static int count,capacity;

/* Only the validated 64-map Balmora layout shares the alias catalogue.
 * Prefix matching would capture unrelated/scripted map entities silently. */
static int AW_SceneryMapEnabled(const char *name)
{
    if(!strcmp(name,"balmora"))return 1;
    if(strlen(name)!=5 || name[0]!='b' || name[1]!='m' || name[2]!='0' ||
       name[3]<'0' || name[3]>'6' || name[4]<'0' || name[4]>'9')return 0;
    return name[3]!='6' || name[4]<='3';
}

void AW_SceneryClear(void) { placements=NULL;count=capacity=0; }
void AW_SceneryBegin(const char *entities)
{
    const char *p=entities;
    AW_SceneryClear();
    if(!AW_SceneryMapEnabled(sv.name))return;
    while((p=strstr(p,"\"classname\" \"func_wall\""))!=NULL){capacity++;p++;}
    if(capacity>1000)Host_Error("Balmora scenery catalogue exceeds 1000 placements");
    if(capacity)placements=Hunk_AllocName(capacity*sizeof(*placements),"scenery");
}
int AW_SceneryCapture(edict_t *e)
{
    aw_scenery_t *p;model_t *model;vec3_t forward,right,up,corner;float v;int i,j,k;
    if(!AW_SceneryMapEnabled(sv.name) || !e->v.classname ||
       strcmp(pr_strings+e->v.classname,"func_wall"))return 0;
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
    if(!sv.active || !AW_SceneryMapEnabled(sv.name))return;
    if(cl_numvisedicts+count>MAX_VISEDICTS)Host_Error("Balmora visible entity budget exceeded");
    for(i=0;i<count;i++)cl_visedicts[cl_numvisedicts++]=&placements[i].render;
}
void AW_SceneryClip(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,trace_t *best)
{
    int i,k;vec3_t low,high;edict_t solid;trace_t hit;aw_scenery_t *p;
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
