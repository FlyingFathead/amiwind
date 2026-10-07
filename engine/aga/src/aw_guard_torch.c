/* SPDX-License-Identifier: GPL-2.0-or-later
 * Source-classified guard equipment. Render proxies never change server poses,
 * collision, inventory or the player's carried torch. All storage is bounded.
 */
#include "quakedef.h"
#include "r_local.h"
#include "aw_sky.h"
#include "aw_clock.h"
#include "aw_state.h"
#include "aw_boolean.h"
#include "aw_torch.h"
#include <stdint.h>
#ifdef AMIGA
#include <proto/exec.h>
#include <exec/memory.h>
#endif
extern short *d_pzbuffer;
extern unsigned int d_zwidth;
extern cvar_t r_drawentities;
extern int hunk_size,hunk_low_used,hunk_high_used;
#define GUARD_TYPES 32
#define GUARD_VISIBLE 32
#define GUARD_LIGHTS AW_GUARD_TORCH_LIGHT_COUNT
#define GUARD_LIGHT_KEY AW_GUARD_TORCH_LIGHT_KEY
#define GUARD_LIGHT_RANGE (384.0f*384.0f)
typedef struct {
    char source[64],base[64],body[64],held[64];
    int frames,automatic;
    vec3_t emitter[21];
    model_t *body_model,*held_model;
    int failed,warned;
    double retry_after;
} guard_asset_t;
typedef struct {
    entity_t body,held;
    entity_t *original;
    edict_t *actor;
    vec3_t flame;
    float distance;
    int active,light_test,light_key;
} guard_visible_t;
static guard_asset_t guard_assets[GUARD_TYPES];
static guard_visible_t guards[GUARD_VISIBLE];
static int guard_count,visible_count,override=-1;
static const byte *flame_pixels;
static int last_aliases,last_eligible,last_frames,last_models,last_evicted;
static int last_lights,last_light_range,last_light_contents,last_light_trace,last_light_untested;
static const char *last_gate="not rendered";
static cvar_t guards_torch_cycle={"guards_torch_cycle","1",true};
static unsigned read16(const byte *p){return ((unsigned)p[0]<<8)|p[1];}
static int32_t readfixed(const byte *p){return (int32_t)(((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3]);}
static int field(char *out,const byte *in,int path)
{
    int i,n=0;while(n<64 && in[n])n++;
    if(!n || n==64)return 0;
    for(i=0;i<n;i++)if(in[i]<32 || in[i]>126)return 0;
    for(i=n;i<64;i++)if(in[i])return 0;
    memcpy(out,in,64);
    if(path && (strncmp(out,"progs/",6) || n<11 || strcmp(out+n-4,".mdl") ||
        strstr(out,"..") || strchr(out,'\\') || strchr(out,':')))return 0;
    return 1;
}
static void clear_lights(void)
{
    int i;for(i=0;i<MAX_DLIGHTS;i++)if(cl_dlights[i].key<=GUARD_LIGHT_KEY &&
        cl_dlights[i].key>GUARD_LIGHT_KEY-GUARD_LIGHTS){
        cl_dlights[i].radius=0;cl_dlights[i].die=-1;
    }
}
/* Remove only our prior proxies, even if a paused renderer reuses its list. */
static void restore_list(void)
{
    int i,j,n=0,held;
    for(i=0;i<cl_numvisedicts;i++){
        held=0;
        for(j=0;j<visible_count;j++){
            if(cl_visedicts[i]==&guards[j].held){held=1;break;}
            if(cl_visedicts[i]==&guards[j].body){cl_visedicts[i]=guards[j].original;break;}
        }
        if(!held)cl_visedicts[n++]=cl_visedicts[i];
    }
    cl_numvisedicts=n;visible_count=0;
}
void AW_GuardTorchLoadAssets(const byte *torch)
{
    FILE *file=NULL;byte header[260],p[12];int size,used=8,i,j,k,count,valid=1;
    guard_asset_t *a;
    restore_list();clear_lights();guard_count=0;flame_pixels=(!torch?NULL:torch+204);
    memset(guard_assets,0,sizeof guard_assets);
    size=COM_FOpenFile("gfx/guard-torches.awg",&file);
    if(!file)return;
    if(size<8 || size>8+GUARD_TYPES*(260+21*12) || fread(header,1,8,file)!=8 ||
        memcmp(header,"AWG1",4) || read16(header+6)){fclose(file);goto invalid;}
    count=read16(header+4);if(count>GUARD_TYPES){fclose(file);goto invalid;}
    for(i=0;i<count && valid;i++){
        a=&guard_assets[i];
        if(used+260>size || fread(header,1,260,file)!=260){valid=0;break;}used+=260;
        if(!field(a->source,header,0) || !field(a->base,header+64,1) ||
           !field(a->body,header+128,1) || !field(a->held,header+192,1)){valid=0;break;}
        a->frames=read16(header+256);a->automatic=read16(header+258);
        if((a->frames!=8 && a->frames!=21) || a->automatic>1 ||
            used+a->frames*12>size){valid=0;break;}
        for(j=0;j<i;j++)if(!Q_strcasecmp(a->source,guard_assets[j].source) &&
            !strcmp(a->base,guard_assets[j].base))valid=0;
        for(j=0;j<a->frames && valid;j++){
            if(fread(p,1,12,file)!=12){valid=0;break;}used+=12;
            for(k=0;k<3;k++){
                int32_t value=readfixed(p+k*4);
                if(value < -8388608 || value>8388608)valid=0;
                a->emitter[j][k]=value/65536.0f;
            }
        }
    }
    fclose(file);
    if(!valid || used!=size)goto invalid;
    guard_count=count;return;
invalid:
    Con_Printf("Guard torch registry invalid; guard equipment disabled.\n");
}
static void command(void)
{
    int value,i,active=0,lights=0;
    if(Cmd_Argc()==2){
        value=!Q_strcasecmp(Cmd_Argv(1),"auto")?-1:AW_ParseBoolean(Cmd_Argv(1));
        if(value<0 && Q_strcasecmp(Cmd_Argv(1),"auto")){
            Con_Printf("Usage: dbg guardtorch on/off/auto (true/false, 1/0)\n");return;
        }
        override=value;
    }else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg guardtorch [on/off/auto]\n");return;}
    Con_Printf("Guard torches: %s; cycle %s; %d source records.\n",
        override<0?"auto":override?"on":"off",guards_torch_cycle.value>0?"on":"off",guard_count);
    for(i=0;i<visible_count;i++)if(guards[i].active)active++;
    Con_Printf("Last guard frame: %s; aliases %d, eligible %d, admitted %d, frame skips %d, model skips %d, evicted %d.\n",
        last_gate,last_aliases,last_eligible,active,last_frames,last_models,last_evicted);
    for(i=0;i<MAX_DLIGHTS;i++)if(cl_dlights[i].key<=GUARD_LIGHT_KEY &&
        cl_dlights[i].key>GUARD_LIGHT_KEY-GUARD_LIGHTS && cl_dlights[i].radius>0 && cl_dlights[i].die>=cl.time)lights++;
    Con_Printf("Guard lights: active %d; last selected %d/2, outside range %d, contents rejects %d, trace rejects %d, untested/budget %d.\n",
        lights,last_lights,last_light_range,last_light_contents,last_light_trace,last_light_untested);
}
extern cvar_t aw_static_flames;
void AW_GuardTorchInit(void)
{
    Cvar_RegisterVariable(&aw_static_flames);
    Cvar_RegisterVariable(&guards_torch_cycle);Cmd_AddCommand("aw_guardtorch",command);
}
static int automatic_night(void)
{
    int ms;
    if(guards_torch_cycle.value<=0 || !R_SkyExterior() || !AW_ClockEnsure())return 0;
    ms=AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms");
    return ms>=0 && ms<86400000 && (ms<21600000 || ms>72000000);
}
static guard_asset_t *asset(entity_t *ent,edict_t **actor,int automatic)
{
    uintptr_t ptr=(uintptr_t)ent,base=(uintptr_t)cl_entities,offset;int index,i;
    edict_t *e;eval_t *source;
    if(ptr<base)return NULL;
    offset=ptr-base;
    if(offset%sizeof(entity_t) || offset/sizeof(entity_t)>=MAX_EDICTS)return NULL;
    index=(int)(offset/sizeof(entity_t));if(index<=0 || index>=sv.num_edicts)return NULL;
    e=EDICT_NUM(index);
    if(e->free || !e->v.classname || strcmp(pr_strings+e->v.classname,"aw_npc") ||
        e->v.deadflag || e->v.waterlevel>=2 || (automatic && e->v.enemy))return NULL;
    /* Static scene actors do not run the stock swimming physics update. */
    {vec3_t torso;VectorCopy(e->v.origin,torso);torso[2]+=16;
     if(SV_PointContents(torso)<=CONTENTS_WATER)return NULL;}
    source=GetEdictFieldValue(e,"aw_source_id");if(!source || !source->string)return NULL;
    /* TES record IDs are case-insensitive; model paths remain byte-exact. */
    for(i=0;i<guard_count;i++)if(!Q_strcasecmp(guard_assets[i].source,pr_strings+source->string) &&
        !strcmp(guard_assets[i].base,ent->model->name)){
        if(automatic && !guard_assets[i].automatic)return NULL;
        *actor=e;return &guard_assets[i];
    }
    return NULL;
}
/* Registry pointers outlive map loads; model table slots do not. Verify
 * identity before checking cache, and retain warm companions in the current
 * map via Mod_ForName's allocation-free cached-alias path. Otherwise an
 * unreferenced slot can become an unrelated actor with a plausible frame count. */
static int cached_model(model_t **model,char *name)
{
    if(!*model || strcmp((*model)->name,name)){*model=NULL;return 0;}
    if(!Cache_Check(&(*model)->cache))return 0;
    if((*model)->needload)*model=Mod_ForName(name,false);
    return *model && Cache_Check(&(*model)->cache);
}
static int models(guard_asset_t *a)
{
    void *probe;int body_ready,held_ready;
    if(a->failed)return 0;
    body_ready=cached_model(&a->body_model,a->body);
    held_ready=cached_model(&a->held_model,a->held);
    if(body_ready && held_ready)goto validate;
    if(cl.time<a->retry_after && cl.time>=a->retry_after-3)return 0;
    /* The owned conversion ledger bounds each complete pair below 1 MiB.
     * Keep 2 MiB of hunk clearance for cache/staging and probe 1 MiB of
     * external Fast RAM on the target before the ordinary alias loader is entered.
     * This is optional equipment admission, not a general OOM guarantee. */
    probe=NULL;
    if(hunk_size-hunk_low_used-hunk_high_used>=2*1024*1024){
#ifdef AMIGA
        /* The SDK malloc failure path can trap before returning NULL. */
        probe=AllocMem(1024*1024,MEMF_FAST|MEMF_PUBLIC);
#else
        probe=malloc(1024*1024);
#endif
    }
    if(!probe){
        a->retry_after=cl.time+3;
        if(!a->warned){Con_Printf("Guard torch deferred: low memory; original pose retained.\n");a->warned=1;}
        return 0;
    }
#ifdef AMIGA
    FreeMem(probe,1024*1024);
#else
    free(probe);
#endif
    if(!body_ready)a->body_model=Mod_ForName(a->body,false);
    if(!held_ready)a->held_model=Mod_ForName(a->held,false);
validate:
    if(!a->body_model || !a->held_model || strcmp(a->body_model->name,a->body) ||
        strcmp(a->held_model->name,a->held) || a->body_model->type!=mod_alias ||
        a->held_model->type!=mod_alias || a->body_model->numframes!=a->frames ||
        a->held_model->numframes!=a->frames){
        a->failed=1;Con_Printf("Guard torch model mismatch: %s; retaining original pose.\n",a->source);return 0;
    }
    return Cache_Check(&a->body_model->cache) && Cache_Check(&a->held_model->cache);
}
/* Do not let an optional proxy trigger an unbudgeted lazy cache reload from
 * inside the renderer after a later actor/model load has evicted its pair. */
entity_t *AW_GuardTorchEntity(entity_t *entity)
{
    int i;guard_visible_t *g;
    for(i=0;i<visible_count;i++){
        g=&guards[i];
        if(entity!=&g->body && entity!=&g->held)continue;
        if(!g->active || !Cache_Check(&g->body.model->cache) || !Cache_Check(&g->held.model->cache)){
            int light;
            if(g->active)last_evicted++;
            g->active=0;
            /* A later alias load may evict only this pair. Other admitted
             * guards and the player's independent light remain valid. */
            if(g->light_key)for(light=0;light<MAX_DLIGHTS;light++)
                if(cl_dlights[light].key==g->light_key){
                    cl_dlights[light].radius=0;cl_dlights[light].die=-1;
                }
            g->light_key=0;
            return entity==&g->body?g->original:NULL;
        }
        return entity;
    }
    return entity;
}
void AW_GuardTorchUpdate(void)
{
    int i,j,initial,night,frame,best,chosen[GUARD_LIGHTS]={-1,-1};
    float distance;vec3_t forward,right,up,delta;guard_visible_t *g;guard_asset_t *a;
    edict_t *actor;entity_t *ent;trace_t trace;dlight_t *light;
    restore_list();clear_lights();
    last_aliases=last_eligible=last_frames=last_models=last_evicted=0;
    last_lights=last_light_range=last_light_contents=last_light_trace=last_light_untested=0;
    last_gate="inactive";
    if(!guard_count || !flame_pixels || override==0 || !r_drawentities.value || !sv.active ||
        cls.state!=ca_connected || svs.maxclients!=1 || cl.intermission || AW_GalleryActive())return;
    night=automatic_night();
    last_gate="automatic daytime/disabled";if(override<0 && !night)return;
    last_gate=override>0?"forced on":"automatic night";
    initial=cl_numvisedicts;
    for(i=0;i<initial && visible_count<GUARD_VISIBLE && cl_numvisedicts<MAX_VISEDICTS;i++){
        ent=cl_visedicts[i];if(!ent || !ent->model || ent->model->type!=mod_alias)continue;
        last_aliases++;a=asset(ent,&actor,override<0);if(!a)continue;
        last_eligible++;
        if(ent->frame<0 || ent->frame>=a->frames){last_frames++;continue;}
        if(!models(a)){last_models++;continue;}
        g=&guards[visible_count++];g->original=ent;g->actor=actor;g->active=1;g->light_test=0;g->light_key=0;
        g->body=*ent;g->body.model=a->body_model;g->held=*ent;g->held.model=a->held_model;
        frame=ent->frame;AngleVectors(ent->angles,forward,right,up);
        for(j=0;j<3;j++)g->flame[j]=ent->origin[j]+a->emitter[frame][0]*forward[j]-
            a->emitter[frame][1]*right[j]+a->emitter[frame][2]*up[j];
        VectorSubtract(g->flame,r_refdef.vieworg,delta);g->distance=DotProduct(delta,delta);
        cl_visedicts[i]=&g->body;cl_visedicts[cl_numvisedicts++]=&g->held;
    }
    /* At most two point lights, chosen by distance among clear emitters. */
    for(j=0;j<GUARD_LIGHTS;j++){
        best=-1;distance=GUARD_LIGHT_RANGE;
        for(i=0;i<visible_count;i++){
            if(i==chosen[0] || guards[i].distance>=distance)continue;
            g=&guards[i];
            if(SV_PointContents(g->flame)!=CONTENTS_EMPTY){g->light_test=1;continue;}
            trace=SV_Move(g->flame,vec3_origin,vec3_origin,r_refdef.vieworg,MOVE_NOMONSTERS,g->actor);
            if(trace.startsolid || trace.allsolid || trace.fraction<1){g->light_test=2;continue;}
            g->light_test=3;
            best=i;distance=g->distance;
        }
        if(best<0)break;
        chosen[j]=best;g=&guards[best];light=CL_AllocDlight(GUARD_LIGHT_KEY-j);
        g->light_key=GUARD_LIGHT_KEY-j;
        VectorCopy(g->flame,light->origin);light->radius=AW_TorchLightRadius();light->minlight=16;
        light->die=cl.time+.1;light->decay=0;
        last_lights++;
    }
    for(i=0;i<visible_count;i++){
        g=&guards[i];
        if(g->distance>=GUARD_LIGHT_RANGE)last_light_range++;
        else if(g->light_test==1)last_light_contents++;
        else if(g->light_test==2)last_light_trace++;
        else if(!g->light_test)last_light_untested++;
    }
}
/* One rising flame particle: projected, depth-tested, ordered-dither alpha.
 * Shared by guard torches and static fires; scale 1 is the guard size. */
/* rise: vertical travel scale; opacity: alpha multiplier; solid > 0 replaces the
 * ordered dither with a fixed alpha cut-off (large static flames). Guards: 1, 1, 0. */
static void flame_particle(const vec3_t origin,int k,float scale,int core,int max_pixels,float rise,float opacity,int solid)
{
    static const int threshold[16]={0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5};
    int n,x,y,xx,yy,px,py,j,alpha,z;float age,depth,cx,cy,size;vec3_t delta;
    age=(float)fmod(cl.time*.833333+k/3.0,1.0);if(!isfinite(age) || age<0)age=0;
    VectorSubtract(origin,r_refdef.vieworg,delta);delta[2]+=age*2.7f*rise;
    depth=DotProduct(delta,vpn);if(!(depth>1))return;
    cx=aliasxcenter+DotProduct(delta,vright)*aliasxscale/depth;
    cy=aliasycenter-DotProduct(delta,vup)*aliasyscale/depth;
    size=aliasyscale/depth*1.5f*scale*(1-age*.3f);
    if(!isfinite(cx) || !isfinite(cy) || !isfinite(size) || size<1 ||
        cx<r_refdef.vrect.x-16 || cx>r_refdef.vrect.x+r_refdef.vrect.width+16 ||
        cy<r_refdef.vrect.y-16 || cy>r_refdef.vrect.y+r_refdef.vrect.height+16)return;
    n=size>=max_pixels?max_pixels:(int)size;if(n<2)n=2;x=(int)cx-n/2;y=(int)cy-n/2;z=(int)(32768/depth);
    for(yy=0;yy<n;yy++)for(xx=0;xx<n;xx++){
        px=x+xx;py=y+yy;
        if(px<0 || py<0 || px>=vid.width || py>=vid.height || px<r_refdef.vrect.x ||
            py<r_refdef.vrect.y || px>=r_refdef.vrect.x+r_refdef.vrect.width ||
            py>=r_refdef.vrect.y+r_refdef.vrect.height)continue;
        j=((yy*16/n)*16+xx*16/n)*2;alpha=(int)(flame_pixels[j+1]*(1-age*.6f)*opacity);
        if(alpha>(solid?solid:threshold[(py&3)*4+(px&3)]*16+7) && d_pzbuffer[py*d_zwidth+px]<=z){
            vid.buffer[py*vid.rowbytes+px]=AW_TorchFlameColor(flame_pixels[j],j,age,core);d_pzbuffer[py*d_zwidth+px]=z;
        }
    }
}

void AW_GuardTorchDraw(void)
{
    int i,k,core;
    if(!flame_pixels || !vid.buffer || !d_pzbuffer || d_zwidth<vid.width)return;
    core=AW_TorchFlameCoreColor();
    for(i=0;i<visible_count;i++)for(k=0;k<3;k++){
        if(!guards[i].active)continue;
        flame_particle(guards[i].flame,k,1,core,16,1,1,0);
    }
}

/* Static fires: flames for placed fires, candles, lanterns and braziers.
 * The scene converter writes an "aw_flame" entity (origin, aw_flame_size) for
 * each placed mesh with a particle emitter; their light is already baked into
 * the lightmaps, so only the visible flame is drawn here. The entity text is
 * read once per map into a fixed table; the nearest STATIC_FLAME_DRAW within
 * range are drawn each frame. aw_static_flames 0 turns them off. */
#define STATIC_FLAME_MAX 128
#define STATIC_FLAME_DRAW 12
#define STATIC_FLAME_RANGE (640.0f*640.0f)
cvar_t aw_static_flames={"aw_static_flames","1",true};
static struct {vec3_t origin;float scale;} static_flames[STATIC_FLAME_MAX];
static int static_flame_count;
static model_t *static_flame_world;
static void static_flames_load(model_t *world)
{
    char *data,key[64];int flame;vec3_t origin;float scale;
    static_flame_count=0;static_flame_world=world;
    if(!world || !world->entities)return;
    data=world->entities;
    while((data=COM_Parse(data))!=NULL && com_token[0]=='{'){
        flame=0;origin[0]=origin[1]=origin[2]=0;scale=1;
        while((data=COM_Parse(data))!=NULL && com_token[0]!='}'){
            strncpy(key,com_token,sizeof(key)-1);key[sizeof(key)-1]=0;
            if(!(data=COM_Parse(data)))break;
            if(!strcmp(key,"classname"))flame=!strcmp(com_token,"aw_flame");
            else if(!strcmp(key,"origin"))sscanf(com_token,"%f %f %f",&origin[0],&origin[1],&origin[2]);
            else if(!strcmp(key,"aw_flame_size"))scale=(float)atof(com_token);
        }
        if(flame && static_flame_count<STATIC_FLAME_MAX && isfinite(scale) && scale>0 && scale<=16){
            VectorCopy(origin,static_flames[static_flame_count].origin);
            static_flames[static_flame_count++].scale=scale;
        }
        if(!data)break;
    }
}
void AW_StaticFlamesDraw(void)
{
    int i,j,k,count=0,core,chosen[STATIC_FLAME_DRAW];float dist[STATIC_FLAME_DRAW],d;vec3_t delta;
    if(!aw_static_flames.value || !cl.worldmodel)return;
    if(cl.worldmodel!=static_flame_world)static_flames_load(cl.worldmodel);
    if(!static_flame_count || !flame_pixels || !vid.buffer || !d_pzbuffer || d_zwidth<vid.width)return;
    for(i=0;i<static_flame_count;i++){
        VectorSubtract(static_flames[i].origin,r_refdef.vieworg,delta);d=DotProduct(delta,delta);
        if(d>STATIC_FLAME_RANGE)continue;
        /* keep the STATIC_FLAME_DRAW nearest, sorted by distance */
        if(count<STATIC_FLAME_DRAW)j=count++;
        else if(d>=dist[STATIC_FLAME_DRAW-1])continue;
        else j=STATIC_FLAME_DRAW-1;
        for(;j>0 && dist[j-1]>d;j--){dist[j]=dist[j-1];chosen[j]=chosen[j-1];}
        dist[j]=d;chosen[j]=i;
    }
    core=AW_TorchFlameCoreColor();
    for(i=0;i<count;i++)for(k=0;k<3;k++)
        flame_particle(static_flames[chosen[i]].origin,k,static_flames[chosen[i]].scale,core,48,
                       static_flames[chosen[i]].scale<2.5f?static_flames[chosen[i]].scale:2.5f,2,96);
}
