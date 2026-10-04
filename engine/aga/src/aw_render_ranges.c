/* GPL-2.0-or-later. Placement render ranges share BSP arrays and preserve the
 * original entity, common model bounds, collision and network identity. */
#ifndef AW_RENDER_RANGES_TEST
#include "quakedef.h"
#endif
#include "aw_render_ranges.h"
#define AW_RANGE_LIMIT 1024
#define AW_RANGE_TEXT 16384
typedef struct aw_range_record_s {
    struct aw_range_record_s *next;
    model_t *model;
    vec3_t origin,angles;
    int count;
    aw_render_range_t ranges[1];
} aw_range_record_t;
static aw_range_record_t *aw_records;
static model_t *aw_pool;
/* This bounded tokenizer avoids COM_Parse's unbounded com_token writes. */
static char *AW_RangeToken(char *p,char *out,int size)
{
    int n=0,quoted;
    for(;;){
        while(*p && *p<=32)p++;
        if(p[0]=='/' && p[1]=='/'){while(*p && *p!='\n')p++;continue;}
        break;
    }
    if(!*p)return NULL;
    if(*p=='{' || *p=='}'){out[0]=*p++;out[1]=0;return p;}
    quoted=*p=='"';if(quoted)p++;
    while(*p && (quoted?*p!='"':*p>32 && *p!='{' && *p!='}')){
        if(n>=size-1)Sys_Error("Render range entity token too long");
        out[n++]=*p++;
    }
    if(quoted){if(*p!='"')Sys_Error("Unclosed render range entity token");p++;}
    out[n]=0;return p;
}
static model_t *AW_RangeModel(const char *name)
{
    int i;
    for(i=1;i<MAX_MODELS;i++)
        if(cl.model_precache[i] && !strcmp(cl.model_precache[i]->name,name))return cl.model_precache[i];
    return NULL;
}
void AW_RenderRangesNewMap(void)
{
    char *p,key[64],value[AW_RANGE_TEXT],classname[64],model[64],pool[64],ranges[AW_RANGE_TEXT];
    vec3_t origin,angles;
    aw_render_range_t parsed[AW_RANGE_LIMIT];
    aw_range_record_t *record,*prior;
    int entity=0,n,k,j,records=0,total_ranges=0,bytes=0;
    float delta;
    aw_records=NULL;aw_pool=NULL;
    if(!cl.worldmodel || !cl.worldmodel->entities)return;
    p=cl.worldmodel->entities;
    while((p=AW_RangeToken(p,key,sizeof(key)))!=NULL){
        if(strcmp(key,"{"))Sys_Error("Invalid render range entity opening");
        classname[0]=model[0]=pool[0]=ranges[0]=0;memset(origin,0,sizeof(origin));memset(angles,0,sizeof(angles));
        for(;;){
            p=AW_RangeToken(p,key,sizeof(key));if(!p)Sys_Error("Truncated render range entity");
            if(!strcmp(key,"}"))break;
            p=AW_RangeToken(p,value,sizeof(value));if(!p)Sys_Error("Truncated render range value");
            if(!strcmp(key,"classname")){strncpy(classname,value,63);classname[63]=0;}
            else if(!strcmp(key,"model")){strncpy(model,value,63);model[63]=0;}
            else if(!strcmp(key,"aw_render_pool")){strncpy(pool,value,63);pool[63]=0;}
            else if(!strcmp(key,"aw_render_ranges"))strcpy(ranges,value);
            else if(!strcmp(key,"origin")){if(sscanf(value,"%f %f %f",&origin[0],&origin[1],&origin[2])!=3)Sys_Error("Invalid range origin");}
            else if(!strcmp(key,"angles")){if(sscanf(value,"%f %f %f",&angles[0],&angles[1],&angles[2])!=3)Sys_Error("Invalid range angles");}
            else if(!strcmp(key,"angle"))angles[1]=atof(value);
        }
        if(entity++==0){
            if(!pool[0])return; /* Ordinary maps allocate nothing and skip per-frame lookup. */
            aw_pool=AW_RangeModel(pool);
            if(!aw_pool || pool[0]!='*' || aw_pool->type!=mod_brush || aw_pool->firstmodelsurface<0 || aw_pool->nummodelsurfaces<0 || aw_pool->firstmodelsurface>aw_pool->numsurfaces || aw_pool->nummodelsurfaces>aw_pool->numsurfaces-aw_pool->firstmodelsurface)Sys_Error("Invalid render pool model");
        }
        if(!ranges[0])continue;
        if(strcmp(classname,"func_wall") || model[0]!='*')Sys_Error("Ranges require an original func_wall");
        n=AW_ParseRenderRanges(ranges,aw_pool->nummodelsurfaces,parsed,AW_RANGE_LIMIT);
        if(n<0)Sys_Error("Invalid render pool ranges");
        if(++records>MAX_EDICTS || n>32768-total_ranges)Sys_Error("Render range registry limit exceeded");
        total_ranges+=n;
        for(k=0;k<3;k++)
            if(!(origin[k]>=-10000000 && origin[k]<=10000000 && angles[k]>=-360000 && angles[k]<=360000))Sys_Error("Nonfinite range transform");
        bytes+=sizeof(*record)+(n-1)*sizeof(parsed[0]);
        record=Hunk_AllocName(sizeof(*record)+(n-1)*sizeof(parsed[0]),"render_ranges");
        record->model=AW_RangeModel(model);
        if(!record->model || record->model==aw_pool || record->model->surfaces!=aw_pool->surfaces)Sys_Error("Invalid range common model");
        VectorCopy(origin,record->origin);VectorCopy(angles,record->angles);record->count=n;
        for(k=0;k<n;k++)record->ranges[k]=parsed[k];
        for(prior=aw_records;prior;prior=prior->next){
            if(prior->model!=record->model)continue;
            for(k=0;k<3;k++){
                if(fabs(prior->origin[k]-origin[k])>.5)break;
                delta=fmod(prior->angles[k]-angles[k],360.0);
                if(delta>180)delta-=360;if(delta< -180)delta+=360;
                if(fabs(delta)>3)break;
            }
            if(k!=3)continue;
            if(prior->count!=n)Sys_Error("Ambiguous render range placement");
            for(j=0;j<n;j++)if(prior->ranges[j].start!=parsed[j].start || prior->ranges[j].count!=parsed[j].count)Sys_Error("Conflicting render range placement");
        }
        record->next=aw_records;aw_records=record;
    }
    Con_Printf("Render ranges: %d placements, %d ranges, %d payload bytes\n",records,total_ranges,bytes);
}
qboolean AW_RenderRangeView(entity_t *entity,int pass,model_t *view)
{
    aw_range_record_t *r;int k;float delta;
    if(!aw_records || pass<0 || !entity || !entity->model || !view)return false;
    for(r=aw_records;r;r=r->next){
        if(r->model!=entity->model)continue;
        for(k=0;k<3;k++){
            if(fabs(r->origin[k]-entity->origin[k])>.25)break;
            delta=fmod(r->angles[k]-entity->angles[k],360.0);
            if(delta>180)delta-=360;if(delta< -180)delta+=360;
            if(fabs(delta)>1.5)break; /* Quake's network angles use 8 bits. */
        }
        if(k!=3)continue;
        if(pass>=r->count)return false;
        *view=*entity->model;
        view->firstmodelsurface=aw_pool->firstmodelsurface+r->ranges[pass].start;
        view->nummodelsurfaces=r->ranges[pass].count;
        return true;
    }
    return false;
}
