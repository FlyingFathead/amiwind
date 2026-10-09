/* SPDX-License-Identifier: GPL-2.0-or-later
 * One resident BSP, shared exterior coordinates and bounded overlap. */
#include "quakedef.h"
#include "aw_region.h"
#include "aw_section.h"
#include "aw_maps.h"
#include "aw_town.h"
typedef struct {
    aw_region_t regions[AW_REGION_MAX];
    int count,loaded,current,requested,kind,requested_kind;
    float hysteresis;vec3_t arrival,return_point;float arrival_yaw,return_yaw;
} aw_region_area_t;
/* One region directory per town-table row (aw_town.h): file, map prefix,
 * region cap and certified draw distance all come from the table. */
static aw_region_area_t areas[AW_TOWN_COUNT];
static char model_path[40];
/* CHIM: a town whose exterior is a CHIM frame runs in one map with no region
 * loads (chim/chim_world.c sets this only when its data exists; it returns
 * the town's frame map, or NULL to keep the region maps). */
const char *(*aw_chim_town_map)(const char *town);
static const char *chim_map(const char *town){return aw_chim_town_map?aw_chim_town_map(town):NULL;}
/* The running map is the town's CHIM frame map (not its intro regions). */
/* The town's frame map, or (world format 0.5) a frame map of the same
 * frame with its own entities: the intro docks', the enclosed courtyard's.
 * One frame map, no region crossings. */
static int chim_running(void){
    const char *c=chim_map(sv.name),*d;
    if(c && !strcmp(sv.modelname,c))return 1;
    if(!c)return 0;
    if((d=chim_map("intro_docks"))!=NULL && !strcmp(sv.modelname,d))return 1;
    return (d=chim_map("sncourt"))!=NULL && !strcmp(sv.modelname,d);
}
/* An arrival in Seyda Neen's enclosed courtyard (entered only by door links)
 * selects the courtyard's frame map when the town runs on CHIM. */
static int chim_courtyard;
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
/* Predict the first residency change, not the far end of the lookahead.
 * Narrow cores can be skipped by endpoint projection before hysteresis releases
 * the current region, which used to discard the prefix actually needed next. */
int AW_RegionNextOwner(const aw_region_t *r,int n,const float *point,
    const float *velocity,int previous,float margin,float seconds)
{
    int i,k,id,best=-1,edge,best_edge=1;
    double inverse[2],exit_time=seconds,first=seconds,entry,leave,a,b,t;
    if(!r || !point || !velocity || n<1 || n>AW_REGION_MAX || previous<0 || previous>=n ||
       !isfinite(margin) || margin<0 || !isfinite(seconds) || seconds<=0)return -1;
    for(k=0;k<2;k++)if(!isfinite(point[k]) || !isfinite(velocity[k]))return -1;
    if((double)velocity[0]*velocity[0]+(double)velocity[1]*velocity[1]<16)return -1;
    id=AW_RegionOwner(r,n,point,previous,margin);
    if(id!=previous)return id; /* A crossing is already due this frame. */
    for(k=0;k<2;k++){
        inverse[k]=velocity[k]?1.0/(double)velocity[k]:0;
        if(!velocity[k])continue;
        t=((velocity[k]>0?(double)r[previous].high[k]+margin:
            (double)r[previous].low[k]-margin)-point[k])*inverse[k];
        if(t<exit_time)exit_time=t;
    }
    if(exit_time>=seconds)return -1; /* The inclusive retention box is not left. */
    for(i=0;i<n;i++){
        if(i==previous)continue;
        entry=exit_time;leave=seconds;edge=0;
        for(k=0;k<2;k++){
            if(!velocity[k]){
                if(point[k]<r[i].low[k] || point[k]>r[i].high[k])break;
                if(point[k]==r[i].high[k])edge=1;
            }else{
                a=((double)r[i].low[k]-point[k])*inverse[k];
                b=((double)r[i].high[k]-point[k])*inverse[k];
                if(a>b){t=a;a=b;b=t;}
                if(a>entry)entry=a;
                if(b<leave)leave=b;
            }
            if(entry>=leave)break; /* Corner touches have no travel interval. */
        }
        /* At a shared parallel edge prefer the half-open owner, retaining the
         * inclusive outer-world fallback used by AW_RegionOwner. */
        if(k==2 && entry<leave && (entry<first ||
            (entry==first && edge<best_edge))){best=i;first=entry;best_edge=edge;}
    }
    return best;
}
static int area_id(const char *name){return AW_TownFind(name);}
/* Seyda Neen's intro docks and Census courtyard are sub-scenes of its area. */
static int scenes(int area){return (AW_Town(area)->flags&AW_TOWN_SEYDA_SCENES)!=0;}
static int read_regions(int area)
{
    FILE *f=NULL;char line[256],magic[8],extra,expected[16];int i,k,n,distance;
    aw_region_area_t *a=&areas[area];const aw_town_t *t=AW_Town(area);
    if(a->loaded)return a->count>0;
    a->loaded=1;a->current=a->requested=-1;
    if(COM_FOpenFile((char *)t->regions,&f)<0 || !f)return 0;
    if(!fgets(line,sizeof(line),f) || Q_sscanf(line,"%7s %d %f %d %f %f %f %f %f %f %f %f %c",
        magic,&n,&a->hysteresis,&distance,&a->arrival[0],&a->arrival[1],&a->arrival[2],&a->arrival_yaw,
        &a->return_point[0],&a->return_point[1],&a->return_point[2],&a->return_yaw,&extra)!=12 ||
        strcmp(magic,"AWBR1") || n<1 || n>AW_REGION_MAX || n>t->region_cap ||
        !(a->hysteresis>=0 && a->hysteresis<=128) || distance!=t->draw_distance)goto invalid;
    for(k=0;k<3;k++)if(!(fabs(a->arrival[k])<32768 && fabs(a->return_point[k])<32768))goto invalid;
    if(!(a->arrival_yaw>=0 && a->arrival_yaw<360 && a->return_yaw>=0 && a->return_yaw<360))goto invalid;
    for(i=0;i<n;i++){
        aw_region_t *r=&a->regions[i];
        if(!fgets(line,sizeof(line),f) || Q_sscanf(line,"%7s %f %f %f %f %f %f %f %f %c",r->name,
            &r->low[0],&r->low[1],&r->high[0],&r->high[1],&r->cover_low[0],&r->cover_low[1],
            &r->cover_high[0],&r->cover_high[1],&extra)!=9)goto invalid;
        sprintf(expected,"%.2s%03ld",t->prefix,(long)i);
        if(strcmp(expected,r->name))goto invalid;
        for(k=0;k<2;k++)if(!(r->low[k]<r->high[k] && r->cover_low[k]<=r->low[k] &&
            r->cover_high[k]>=r->high[k] && fabs(r->cover_low[k])<32768 && fabs(r->cover_high[k])<32768))goto invalid;
    }
    if(fgets(line,sizeof(line),f))goto invalid;
    fclose(f);a->count=n;
    if(AW_RegionOwner(a->regions,n,a->arrival,-1,0)<0){a->count=0;return 0;}
    return 1;
invalid:
    fclose(f);Con_Printf("Invalid exterior region directory: %s.\n",t->regions);return 0;
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
    if(area<0)return AW_SectionSelect(name,point);
    if((!intro || !scenes(area)) && chim_map(name)){   /* the frame map covers the town (the intro docks are Seyda Neen's) */
        chim_courtyard=scenes(area) && seyda_kind(point,0,0)==2 && chim_map("sncourt")!=NULL;
        return 1;
    }
    if(intro && scenes(area) && chim_map(name) && chim_map("intro_docks"))return 1;   /* and the intro docks' frame map */
    /* Legacy full single-map payload (Seyda) when its directory is absent. */
    if(!read_regions(area))return (AW_Town(area)->flags&AW_TOWN_LEGACY_PAYLOAD)!=0;
    a=&areas[area];id=AW_RegionOwner(a->regions,a->count,point,-1,0);
    if(id<0)return 0;
    a->requested=id;a->requested_kind=scenes(area)?seyda_kind(point,intro,0):0;return 1;
}
const char *AW_RegionWorldModel(const char *name,int intro)
{
    int area=area_id(name);aw_region_area_t *a;const char *chim;
    if(area>=0 && (!intro || !scenes(area)) && (chim=chim_map(name))!=NULL){
        const char *court=chim_courtyard?chim_map("sncourt"):NULL;
        chim_courtyard=0;
        if(read_regions(area)){areas[area].current=-1;areas[area].kind=0;areas[area].requested=-1;}
        if(court){Con_Printf("%s (courtyard): CHIM frame map %s.\n",AW_Town(area)->title,court);return court;}
        Con_Printf("%s: CHIM frame map %s.\n",AW_Town(area)->title,chim);return chim;
    }
    /* The intro's docks on CHIM: their own frame map over the town's frame
     * (maps/intro_docks-chim.bsp, world format 0.5). */
    if(area>=0 && intro && scenes(area) && chim_map(name) && (chim=chim_map("intro_docks"))!=NULL){
        if(read_regions(area)){areas[area].current=-1;areas[area].kind=0;areas[area].requested=-1;}
        Con_Printf("%s (intro docks): CHIM frame map %s.\n",AW_Town(area)->title,chim);return chim;
    }
    if(area<0 || !read_regions(area))return NULL;
    a=&areas[area];
    if(a->requested<0){a->requested=AW_RegionOwner(a->regions,a->count,a->arrival,-1,0);a->requested_kind=scenes(area)&&intro?1:0;}
    a->current=a->requested;a->kind=a->requested_kind;a->requested=-1;
    if(a->kind==1)return "maps/intro_docks.bsp";
    if(a->kind==2)return "maps/sncourt.bsp";
    sprintf(model_path,"maps/%s.bsp",a->regions[a->current].name);
    Con_Printf("%s: legacy region map %s.\n",AW_Town(area)->title,model_path);return model_path;
}
int AW_RegionCrossing(const float *point,int intro)
{
    int area=area_id(sv.name),id,kind;aw_region_area_t *a;
    if(area<0 || !read_regions(area))return 0;
    if(chim_running())return 0;   /* one frame map: no region crossings */
    a=&areas[area];kind=scenes(area)?seyda_kind(point,intro,a->kind):0;
    if(kind!=a->kind)return 1;
    if(kind)return 0;
    id=AW_RegionOwner(a->regions,a->count,point,a->current,a->hysteresis);
    return id>=0 && id!=a->current;
}
const char *AW_RegionAhead(const float *point,const float *velocity,int intro,float seconds) {
    int area=area_id(sv.name),id;aw_region_area_t *a;static char next[40];
    if(area<0)return AW_SectionAhead(sv.name,point,velocity,seconds);
    if(intro || !read_regions(area) || chim_running())return NULL;
    a=&areas[area];if(a->kind || a->current<0)return NULL;
    id=AW_RegionNextOwner(a->regions,a->count,point,velocity,a->current,a->hysteresis,seconds);
    if(id<0 || id==a->current)return NULL;
    sprintf(next,"maps/%s.bsp",a->regions[id].name);return next;
}
int AW_RegionContains(const float *point)
{
    int area=area_id(sv.name),k;const float *low,*high;aw_region_area_t *a;
    if(area<0)return AW_SectionContains(sv.name,point);
    if(!read_regions(area) || chim_running())return 1;
    a=&areas[area];if(a->current<0 || a->current>=a->count)return 0;
    low=a->kind==1?dock_low:a->kind==2?court_low:a->regions[a->current].cover_low;
    high=a->kind==1?dock_high:a->kind==2?court_high:a->regions[a->current].cover_high;
    for(k=0;k<2;k++)if(point[k]<low[k]+24 || point[k]>high[k]-24)return 0;
    return 1;
}
int AW_RegionGroundCoverage(const float *point) {
    int area=area_id(sv.name);aw_region_area_t *a;
    if(area<0 || chim_running())return 1;
    a=&areas[area];
    if(!read_regions(area) || a->current<0)return 0;
    if(a->kind)return AW_RegionContains(point);
    /* Far render overlap deliberately omits some architectural collision.
     * Audit/correct in the owning core; other copies keep the baked support Z. */
    return AW_RegionOwner(a->regions,a->count,point,-1,0)==a->current;
}
/* CHIM: while a town runs its frame map, the region that owns point (kept
 * with the region hysteresis while current still owns it), with its region
 * map's name in map: per-region data such as the harvest catalogues stays
 * per region. -1: no region owns point; -2: the running map is not a town's
 * CHIM frame map (legacy: the loaded region map is the region). */
int AW_RegionAt(const float *point,int current,char *map,int size)
{
    int area=area_id(sv.name),id;aw_region_area_t *a;
    if(area<0 || !chim_running() || !read_regions(area))return -2;
    a=&areas[area];
    if(current>=a->count)current=-1;
    id=AW_RegionOwner(a->regions,a->count,point,current,current>=0?a->hysteresis:0);
    if(id>=0 && map && size>0){strncpy(map,a->regions[id].name,size-1);map[size-1]=0;}
    return id;
}
/* The map file a scene loads from, for every check that a scene exists
 * (arrivals, saves, dbg tp, doors, the scene picker, the town checks): its
 * own maps/<name>.bsp, or, when that is absent and the town runs on CHIM, its
 * frame map (a pure-CHIM image has no legacy town maps). Returns the file's
 * size as COM_FOpenFile does (-1: neither exists) and the path in path. */
int AW_SceneMapSize(const char *name,char *path,int size)
{
    static char found[MAX_QPATH+24];FILE *f=NULL;int n=-1;const char *chim;
    found[0]=0;
    if(name && *name && strlen(name)<=40){
        sprintf(found,"maps/%s.bsp",name);n=COM_FOpenFile(found,&f);
        if(f)fclose(f);
        else if((chim=chim_map(name))!=NULL){
            strcpy(found,chim);f=NULL;n=COM_FOpenFile(found,&f);
            if(f)fclose(f);else n=-1;
        }else n=-1;
    }
    if(path && size>0){strncpy(path,found,size-1);path[size-1]=0;}
    return n;
}
/* dbg tp's named destinations this disk has (the scene's map or the town's
 * CHIM frame map, AW_SceneMapSize), "/"-separated, for its help and error
 * lines: on a pure-CHIM disk only the towns that are there are offered.
 * Returns how many. */
int AW_TeleportDestinations(char *out,int size)
{
    int i,n=0;const char *name;const aw_town_t *t;
    if(!out || size<1)return 0;
    out[0]=0;
    for(i=-2;i<=AW_TOWN_COUNT;i++){
        if(i==-2)name=AW_SceneMapSize("seyda",NULL,0)>=124?"seydaneen":NULL;
        else if(i==-1)name=AW_SceneMapSize("prison",NULL,0)>=124?"prisonship":NULL;
        else if(i==AW_TOWN_COUNT)   /* the short name while the Arena is the only Vivec town */
            name=AW_TownFind("vivec_arena")>=0 && AW_SceneMapSize("vivec_arena",NULL,0)>=124?"vivec":NULL;
        else{
            t=AW_Town(i);
            name=t && (t->flags&AW_TOWN_TELEPORT) && strcmp(t->name,"seyda") &&
                AW_SceneMapSize(t->name,NULL,0)>=124?t->name:NULL;
        }
        if(!name || (int)(strlen(out)+strlen(name)+2)>size)continue;
        if(n++)strcat(out,"/");
        strcat(out,name);
    }
    return n;
}
/* Arrival into a town's directory point, or (returning) its return travel
 * point inside the town's travel target. The destination map must exist: the
 * arrival region's map, or the town's CHIM frame map when it runs on CHIM. */
int AW_TownArrival(const char *name,int returning,float *point,float *yaw)
{
    FILE *f=NULL;int id,area=area_id(name);aw_region_area_t *a;const aw_town_t *t;
    if(area<0 || !read_regions(area))return 0;
    a=&areas[area];t=AW_Town(area);
    if(returning && !t->travel_target[0])return 0;
    id=AW_RegionOwner(a->regions,a->count,a->arrival,-1,0);
    if(returning){if(AW_SceneMapSize(t->travel_target,NULL,0)<0)return 0;}
    else if(!chim_map(name)){
        sprintf(model_path,"maps/%s.bsp",a->regions[id].name);
        if(COM_FOpenFile(model_path,&f)<0 || !f)return 0;
        fclose(f);
    }
    if(returning){VectorCopy(a->return_point,point);*yaw=a->return_yaw;}
    else {VectorCopy(a->arrival,point);*yaw=a->arrival_yaw;a->requested=id;a->requested_kind=0;}
    return 1;
}
int AW_BalmoraArrival(int returning,float *point,float *yaw){return AW_TownArrival("balmora",returning,point,yaw);}
int AW_BalmoraSelect(const float *p){return AW_RegionSelect("balmora",p,0);}
const char *AW_BalmoraWorldModel(void){return AW_RegionWorldModel("balmora",0);}
int AW_BalmoraCrossing(const float *p){return !strcmp(sv.name,"balmora") && AW_RegionCrossing(p,0);}
int AW_BalmoraContains(const float *p){return AW_RegionContains(p);}
