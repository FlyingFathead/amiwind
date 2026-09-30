/* SPDX-License-Identifier: GPL-2.0-or-later
 * One resident BSP, shared exterior coordinates and bounded overlap. */
#include "quakedef.h"
#include "aw_region.h"
typedef struct {
    aw_region_t regions[AW_REGION_MAX];
    int count,loaded,current,requested,kind,requested_kind;
    float hysteresis;vec3_t arrival,return_point;float arrival_yaw,return_yaw;
} aw_region_area_t;
static aw_region_area_t areas[2];
static const char *directories[]={"balmora-regions.txt","seyda-regions.txt"};
static const char *prefixes[]={"bm","sn"};
static char model_path[40];
static const float dock_low[2]={-240,-1100},dock_high[2]={1120,620};
static const float court_low[2]={-128,-384},court_high[2]={512,256};

int AW_RegionOwner(const aw_region_t *r,int n,const float *point,int previous,float margin)
{
    int i,k;
    if(!isfinite(point[0]) || !isfinite(point[1]))return -1;
    if(previous>=0 && previous<n){
        for(k=0;k<2;k++)if(point[k]<r[previous].low[k]-margin || point[k]>r[previous].high[k]+margin)break;
        if(k==2)return previous;
    }
    for(i=0;i<n;i++)if(point[0]>=r[i].low[0] && point[0]<r[i].high[0] &&
                       point[1]>=r[i].low[1] && point[1]<r[i].high[1])return i;
    for(i=0;i<n;i++)if(point[0]>=r[i].low[0] && point[0]<=r[i].high[0] &&
                       point[1]>=r[i].low[1] && point[1]<=r[i].high[1])return i;
    return -1;
}
static int area_id(const char *name){return !strcmp(name,"balmora")?0:!strcmp(name,"seyda")?1:-1;}
static int read_regions(int area)
{
    FILE *f=NULL;char line[256],magic[8],extra,expected[8];int i,k,n,distance;
    aw_region_area_t *a=&areas[area];
    if(a->loaded)return a->count>0;
    a->loaded=1;a->current=a->requested=-1;
    if(COM_FOpenFile((char *)directories[area],&f)<0 || !f)return 0;
    if(!fgets(line,sizeof(line),f) || sscanf(line,"%7s %d %f %d %f %f %f %f %f %f %f %f %c",
        magic,&n,&a->hysteresis,&distance,&a->arrival[0],&a->arrival[1],&a->arrival[2],&a->arrival_yaw,
        &a->return_point[0],&a->return_point[1],&a->return_point[2],&a->return_yaw,&extra)!=12 ||
        strcmp(magic,"AWBR1") || n<1 || n>AW_REGION_MAX || !(a->hysteresis>=0 && a->hysteresis<=128) || distance!=540)goto invalid;
    for(k=0;k<3;k++)if(!(fabs(a->arrival[k])<32768 && fabs(a->return_point[k])<32768))goto invalid;
    if(!(a->arrival_yaw>=0 && a->arrival_yaw<360 && a->return_yaw>=0 && a->return_yaw<360))goto invalid;
    for(i=0;i<n;i++){
        aw_region_t *r=&a->regions[i];
        if(!fgets(line,sizeof(line),f) || sscanf(line,"%7s %f %f %f %f %f %f %f %f %c",r->name,
            &r->low[0],&r->low[1],&r->high[0],&r->high[1],&r->cover_low[0],&r->cover_low[1],
            &r->cover_high[0],&r->cover_high[1],&extra)!=9)goto invalid;
        sprintf(expected,"%s%03ld",prefixes[area],(long)i);
        if(strcmp(expected,r->name))goto invalid;
        for(k=0;k<2;k++)if(!(r->low[k]<r->high[k] && r->cover_low[k]<=r->low[k] &&
            r->cover_high[k]>=r->high[k] && fabs(r->cover_low[k])<32768 && fabs(r->cover_high[k])<32768))goto invalid;
    }
    if(fgets(line,sizeof(line),f))goto invalid;
    fclose(f);a->count=n;
    if(AW_RegionOwner(a->regions,n,a->arrival,-1,0)<0){a->count=0;return 0;}
    return 1;
invalid:
    fclose(f);Con_Printf("Invalid exterior region directory: %s.\n",directories[area]);return 0;
}
static int seyda_kind(const float *point,int intro,int previous)
{
    float margin=previous==2?16:0;
    if(intro)return 1;
    /* This courtyard is enclosed; its only normal entrances are door links.
     * A small tolerance prevents debug/free-roam motion chattering at its edge. */
    if(point[0]+point[1]>=-160-margin && point[0]+point[1]<=130+margin &&
       point[1]-point[0]>=-245-margin && point[1]-point[0]<=-45+margin)return 2;
    return 0;
}
int AW_RegionSelect(const char *name,const float *point,int intro)
{
    int area=area_id(name),id;aw_region_area_t *a;
    if(area<0)return 1;
    if(!read_regions(area))return area==1; /* Legacy full Seyda payload. */
    a=&areas[area];id=AW_RegionOwner(a->regions,a->count,point,-1,0);
    if(id<0)return 0;
    a->requested=id;a->requested_kind=area?seyda_kind(point,intro,0):0;return 1;
}
const char *AW_RegionWorldModel(const char *name,int intro)
{
    int area=area_id(name);aw_region_area_t *a;
    if(area<0 || !read_regions(area))return NULL;
    a=&areas[area];
    if(a->requested<0){a->requested=AW_RegionOwner(a->regions,a->count,a->arrival,-1,0);a->requested_kind=area&&intro?1:0;}
    a->current=a->requested;a->kind=a->requested_kind;a->requested=-1;
    if(a->kind==1)return "maps/intro_docks.bsp";
    if(a->kind==2)return "maps/sncourt.bsp";
    sprintf(model_path,"maps/%s.bsp",a->regions[a->current].name);return model_path;
}
int AW_RegionCrossing(const float *point,int intro)
{
    int area=area_id(sv.name),id,kind;aw_region_area_t *a;
    if(area<0 || !read_regions(area))return 0;
    a=&areas[area];kind=area?seyda_kind(point,intro,a->kind):0;
    if(kind!=a->kind)return 1;
    if(kind)return 0;
    id=AW_RegionOwner(a->regions,a->count,point,a->current,a->hysteresis);
    return id>=0 && id!=a->current;
}
const char *AW_RegionAhead(const float *point,const float *velocity,int intro,float seconds) {
    int area=area_id(sv.name),id,k;float projected[3];aw_region_area_t *a;static char next[40];
    if(area<0 || intro || !read_regions(area))return NULL;
    a=&areas[area];if(a->kind || a->current<0)return NULL;
    if(velocity[0]*velocity[0]+velocity[1]*velocity[1]<16)return NULL;
    for(k=0;k<3;k++)projected[k]=point[k]+velocity[k]*seconds;
    id=AW_RegionOwner(a->regions,a->count,projected,a->current,a->hysteresis);
    if(id<0 || id==a->current)return NULL;
    sprintf(next,"maps/%s.bsp",a->regions[id].name);return next;
}
int AW_RegionContains(const float *point)
{
    int area=area_id(sv.name),k;const float *low,*high;aw_region_area_t *a;
    if(area<0 || !read_regions(area))return 1;
    a=&areas[area];if(a->current<0 || a->current>=a->count)return 0;
    low=a->kind==1?dock_low:a->kind==2?court_low:a->regions[a->current].cover_low;
    high=a->kind==1?dock_high:a->kind==2?court_high:a->regions[a->current].cover_high;
    for(k=0;k<2;k++)if(point[k]<low[k]+24 || point[k]>high[k]-24)return 0;
    return 1;
}
int AW_RegionGroundCoverage(const float *point) {
    int area=area_id(sv.name);aw_region_area_t *a;
    if(area<0)return 1;
    a=&areas[area];
    if(!read_regions(area) || a->current<0)return 0;
    if(a->kind)return AW_RegionContains(point);
    /* Far render overlap deliberately omits some architectural collision.
     * Audit/correct in the owning core; other copies keep the baked support Z. */
    return AW_RegionOwner(a->regions,a->count,point,-1,0)==a->current;
}
int AW_BalmoraArrival(int returning,float *point,float *yaw)
{
    FILE *f=NULL;int id;aw_region_area_t *a=&areas[0];
    if(!read_regions(0))return 0;
    id=AW_RegionOwner(a->regions,a->count,a->arrival,-1,0);
    sprintf(model_path,"maps/%s.bsp",a->regions[id].name);
    if(COM_FOpenFile(returning?"maps/seyda.bsp":model_path,&f)<0 || !f)return 0;
    fclose(f);
    if(returning){VectorCopy(a->return_point,point);*yaw=a->return_yaw;}
    else {VectorCopy(a->arrival,point);*yaw=a->arrival_yaw;a->requested=id;a->requested_kind=0;}
    return 1;
}
int AW_BalmoraSelect(const float *p){return AW_RegionSelect("balmora",p,0);}
const char *AW_BalmoraWorldModel(void){return AW_RegionWorldModel("balmora",0);}
int AW_BalmoraCrossing(const float *p){return !strcmp(sv.name,"balmora") && AW_RegionCrossing(p,0);}
int AW_BalmoraContains(const float *p){return AW_RegionContains(p);}
