/* SPDX-License-Identifier: GPL-2.0-or-later
 * Click-to-pin raw identity. Reuses AmiQuake's point trace, frame bounds and
 * console, plus AW_NPCTargetReach's rotated slab test. No actor mutation,
 * allocation, disk lookup or per-frame entity scan. Rows are a click snapshot,
 * not a retained edict pointer (slots can be reused). Static merged geometry
 * cannot supply a source reference that the resident map does not retain.
 */
#include "quakedef.h"
#include "aw_character.h"
#include "aw_inspect.h"
#include "aw_world.h"
#define INSPECT_ROWS 9
#define INSPECT_WIDTH 128
#define INSPECT_REACH 2048.0f
static int enabled,held,release_attack,rows;
static char pinned[INSPECT_ROWS][INSPECT_WIDTH];
extern int scr_copyeverything;

static int scene_ready(void) {
    return cls.state==ca_connected && !cls.demoplayback && sv.active &&
        svs.maxclients==1 && svs.clients && svs.clients[0].edict && sv.edicts;
}
static int interactive(void) {
    return scene_ready() && key_dest==key_game && !AW_PlayerDead() &&
        !AW_CharacterActive() && !AW_ReaderActive() && !AW_IntroPromptActive();
}
static void text_field(const char *label,const char *value) {
    char *p;
    if(rows>=INSPECT_ROWS)return;
    snprintf(pinned[rows],INSPECT_WIDTH,"%s: %s",label,value && *value?value:"unavailable");
    /* Source strings are data; do not let embedded control characters alter
     * the console or turn one HUD field into multiple rows. */
    for(p=pinned[rows];*p;p++)if((unsigned char)*p<32 || (unsigned char)*p>126)*p='?';
    rows++;
}
static const char *edict_string(edict_t *e,char *field) {
    eval_t *v=GetEdictFieldValue(e,field);
    return v && v->string?pr_strings+v->string:NULL;
}
/* R_AliasCheckBBox's current frame box and R_AliasSetUpTransform's pitch/scale.
 * Whole-model bounds include death poses: they can reach across a foreground
 * actor although the currently drawn standing pose does not. Cache_Check never
 * loads a missing model from disk. This remains a frame-bounds, not triangle,
 * pick; grouped MDL frames use the same group box as the renderer. */
static float model_hit(const float *eye,const float *dir,entity_t *candidate,float limit) {
    aliashdr_t *header;mdl_t *mdl;maliasframedesc_t *frame;
    vec3_t forward,right,up,delta,ray,local,angles,mins,maxs;
    float lo=0,hi=limit,a,b,t,scale;int j,f;
    header=Cache_Check(&candidate->model->cache);if(!header)return -1;
    mdl=(mdl_t *)((byte *)header+header->model);if(mdl->numframes<=0)return -1;
    f=candidate->frame;if(f<0 || f>=mdl->numframes)f=0;
    frame=&header->frames[f];scale=R_SpriteEntityScale(candidate);
    for(j=0;j<3;j++){
        mins[j]=(frame->bboxmin.v[j]*mdl->scale[j]+mdl->scale_origin[j])*scale;
        maxs[j]=(frame->bboxmax.v[j]*mdl->scale[j]+mdl->scale_origin[j])*scale;
    }
    VectorCopy(candidate->angles,angles);angles[PITCH]=-angles[PITCH];
    AngleVectors(angles,forward,right,up);VectorSubtract(eye,candidate->origin,delta);
    local[0]=DotProduct(delta,forward);local[1]=-DotProduct(delta,right);local[2]=DotProduct(delta,up);
    ray[0]=DotProduct(dir,forward);ray[1]=-DotProduct(dir,right);ray[2]=DotProduct(dir,up);
    for(j=0;j<3;j++){
        if(fabs(ray[j])<0.00001f){if(local[j]<mins[j] || local[j]>maxs[j])return -1;}
        else{
            a=(mins[j]-local[j])/ray[j];b=(maxs[j]-local[j])/ray[j];
            if(a>b){t=a;a=b;b=t;}if(a>lo)lo=a;if(b<hi)hi=b;
            if(lo>hi)return -1;
        }
    }
    return lo;
}
/* The thing under the rendered crosshair: an edict (alias model by its drawn frame box, else
 * the collision hit), a client static, or only the world. 0 = no local scene; -1 = the camera
 * is inside collision; 1 = picked (*limit: the distance along the view ray). */
static int pick(edict_t **best_out,entity_t **st_out,int *slot_out,int *bounds_out,vec3_t eye,vec3_t dir,float *limit_out) {
    edict_t *p,*e,*best=NULL;entity_t *st=NULL;model_t *m;trace_t tr;
    vec3_t right,up,end;float limit,hit;int i,index,slot=-1,bounds=0;
    if(!scene_ready())return 0;
    p=svs.clients[0].edict;
    /* The rendered camera is essential in third person; player eye angles
     * would select a different actor from the one under the visible crosshair. */
    VectorCopy(r_refdef.vieworg,eye);AngleVectors(r_refdef.viewangles,dir,right,up);
    VectorMA(eye,INSPECT_REACH,dir,end);
    tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,p);
    if(tr.startsolid || tr.allsolid)return -1;
    limit=tr.fraction*INSPECT_REACH;
    if(tr.fraction<1)best=tr.ent;
    /* Use the client pose actually drawn, not a newer server position/frame.
     * Walking hulls exclude heads and non-solid props; world/brushes occlude. */
    for(i=1;i<sv.num_edicts && i<cl.num_entities && i<MAX_EDICTS;i++){
        entity_t *candidate=&cl_entities[i];
        e=EDICT_NUM(i);index=(int)e->v.modelindex;
        if(e==p || e->free || index<=0 || index>=MAX_MODELS)continue;
        m=sv.models[index];if(!m || m->type!=mod_alias)continue;
        if(candidate->model!=m || candidate->msgtime!=cl.mtime[0])continue;
        hit=model_hit(eye,dir,candidate,limit);
        if(hit>=0 && hit<limit){limit=hit;best=e;bounds=1;}
    }
    for(i=0;i<cl.num_statics && i<MAX_STATIC_ENTITIES;i++){
        entity_t *candidate=&cl_static_entities[i];m=candidate->model;
        if(!m || m->type!=mod_alias)continue;
        hit=model_hit(eye,dir,candidate,limit);
        if(hit>=0 && hit<limit){limit=hit;best=NULL;st=candidate;slot=i;bounds=1;}
    }
    *best_out=best;*st_out=st;*slot_out=slot;*bounds_out=bounds;*limit_out=limit;
    return 1;
}
/* The centre of an alias entity's drawn frame box in the world (model_hit's box, its local
 * axes turned back); 0 when the model is not in the cache. */
int AW_InspectFrameCentre(entity_t *candidate,float *out) {
    aliashdr_t *header;mdl_t *mdl;maliasframedesc_t *frame;vec3_t forward,right,up,angles,centre;float scale;int j,f;
    if(!candidate->model || candidate->model->type!=mod_alias || !(header=Cache_Check(&candidate->model->cache)))return 0;
    mdl=(mdl_t *)((byte *)header+header->model);if(mdl->numframes<=0)return 0;
    f=candidate->frame;if(f<0 || f>=mdl->numframes)f=0;
    frame=&header->frames[f];scale=R_SpriteEntityScale(candidate);
    for(j=0;j<3;j++)centre[j]=((frame->bboxmin.v[j]+frame->bboxmax.v[j])*.5f*mdl->scale[j]+mdl->scale_origin[j])*scale;
    VectorCopy(candidate->angles,angles);angles[PITCH]=-angles[PITCH];
    AngleVectors(angles,forward,right,up);
    for(j=0;j<3;j++)out[j]=candidate->origin[j]+centre[0]*forward[j]-centre[1]*right[j]+centre[2]*up[j];
    return 1;
}
/* dbg cam orbit (aw_view.c): what the crosshair shows. *edict: its number (0 none), *focal: the
 * centre of its drawn frame box (a static: the same; the world: the point the view ray hits). */
int AW_InspectTarget(int *edict,float *focal) {
    edict_t *best;entity_t *st;int slot,bounds,r;vec3_t eye,dir;float limit;
    *edict=0;
    r=pick(&best,&st,&slot,&bounds,eye,dir,&limit);
    if(r<=0)return r;
    if(st){if(!AW_InspectFrameCentre(st,focal)){VectorCopy(st->origin,focal);}return 1;}
    if(best && best!=sv.edicts && bounds){
        int n=NUM_FOR_EDICT(best);
        *edict=n;
        if(n<cl.num_entities && AW_InspectFrameCentre(&cl_entities[n],focal))return 1;
        VectorAdd(best->v.absmin,best->v.absmax,focal);VectorScale(focal,.5f,focal);return 1;
    }
    /* the world or a brush model: the point the view ray hits */
    if(limit>=INSPECT_REACH)return 0;
    VectorMA(eye,limit,dir,focal);return 1;
}
static void pin_target(void) {
    edict_t *best=NULL;entity_t *st=NULL;model_t *m;
    vec3_t eye,dir,position,global;float limit;int index,slot=-1,bounds=0,r;
    char value[INSPECT_WIDTH];eval_t *ref;
    rows=0;
    r=pick(&best,&st,&slot,&bounds,eye,dir,&limit);
    if(!r){text_field("Inspect","no local scene");return;}
    if(r<0){text_field("Inspect","camera inside collision; move the view");return;}
    if(!best && !st){text_field("Inspect","no target within 2048 local units");return;}
    VectorMA(eye,limit,dir,position);
    if(st){
        snprintf(value,sizeof(value),"static %ld / frame bounds pick",(long)slot);text_field("PINNED",value);
        text_field("class","client static");text_field("source id",NULL);text_field("source ref",NULL);
        text_field("model",st->model->name);
    }else{
        snprintf(value,sizeof(value),"entity %ld / %s",(long)NUM_FOR_EDICT(best),bounds?"frame bounds pick":"collision pick");text_field("PINNED",value);
        snprintf(value,sizeof(value),"%s / %s",best->v.classname?pr_strings+best->v.classname:"world",
                 best->v.netname?pr_strings+best->v.netname:"unnamed");text_field("class/name",value);
        text_field("source id",edict_string(best,"aw_source_id"));
        ref=GetEdictFieldValue(best,"aw_ref");
        if(ref && isfinite(ref->_float) && ref->_float>0 && ref->_float<2147483648.0f){
            snprintf(value,sizeof(value),"%ld",(long)ref->_float);text_field("source ref",value);
        }else text_field("source ref",NULL);
        index=(int)best->v.modelindex;m=index>0 && index<MAX_MODELS?sv.models[index]:NULL;
        text_field("model",m?m->name:best->v.model?pr_strings+best->v.model:NULL);
        snprintf(value,sizeof(value),"frame %ld / skin %ld / health %.1f",(long)best->v.frame,(long)best->v.skin,best->v.health);
        text_field("server runtime",value);
    }
    snprintf(value,sizeof(value),"%s / hit %.1f %.1f %.1f",sv.name,position[0],position[1],position[2]);text_field("scene",value);
    if(best && best!=sv.edicts){VectorCopy(best->v.origin,position);}
    else if(st){VectorCopy(st->origin,position);}
    snprintf(value,sizeof(value),"%.1f %.1f %.1f",position[0],position[1],position[2]);text_field(best && best!=sv.edicts?"server local XYZ":"local XYZ",value);
    if(AW_WorldToSource(sv.name,position,global)){
        snprintf(value,sizeof(value),"%.1f %.1f %.1f",global[0],global[1],global[2]);text_field(best && best!=sv.edicts?"server global XYZ":"global XYZ",value);
    }else text_field("global XYZ",NULL);
}
static void print_pin(void) {
    int i;Con_Printf("Inspect snapshot (fixed at click; not live):\n");
    for(i=0;i<rows;i++)Con_Printf("%s\n",pinned[i]);
}
static void reset(void) {
    /* Keep explicit mode choice through scene loads, discard old identities.
     * Also wait for release so loading with attack held cannot select/attack. */
    rows=0;held=0;release_attack=1;
}
static int buttons(int bits) {
    int down=bits&1;
    if(!down)release_attack=0;
    if(enabled){
        if(down && !held && !release_attack && interactive()){pin_target();print_pin();scr_copyeverything=1;}
        if(down)release_attack=1;
        held=down;return bits&~1;
    }
    held=down;
    return release_attack?bits&~1:bits;
}
static int crosshair(void) {return enabled && interactive();}
static void draw(void) {
    int i,n,y=36,limit;char line[INSPECT_WIDTH];
    if(!enabled || !interactive() || vid.width<20 || vid.height<74)return;
    limit=((int)vid.width-16)/4;
    if(limit>=INSPECT_WIDTH)limit=INSPECT_WIDTH-1;
    for(i=-1;i<rows;i++){
        const char *s=i<0?"INSPECT: click pins / attack disabled / dbg hud off":pinned[i];
        if(y+8>vid.height-30)break;
        n=(int)strlen(s);if(n>limit)n=limit;memcpy(line,s,n);line[n]=0;
        if((int)strlen(s)>limit && n>=3)memcpy(line+n-3,"...",3);
        Draw_Fill(6,y-1,vid.width-12,8,255);AW_SmallString(8,y,line);y+=8;
    }
    scr_copyeverything=1;
}
static void hud_command(void) {
    char *s=Cmd_Argv(1);int on;
    if(Cmd_Argc()==1){Con_Printf("dbg hud %s: click pins identity; attack disabled while on.\n",enabled?"on":"off");return;}
    if(Cmd_Argc()!=2 || (Q_strcasecmp(s,"on") && Q_strcasecmp(s,"off") && Q_strcasecmp(s,"true") &&
       Q_strcasecmp(s,"false") && strcmp(s,"1") && strcmp(s,"0"))){Con_Printf("Usage: dbg hud on/off\n");return;}
    on=!Q_strcasecmp(s,"on") || !Q_strcasecmp(s,"true") || !strcmp(s,"1");
    enabled=on;rows=0;
    /* Avoid a held inspection click leaking into combat when switched off. */
    if(held)release_attack=1;
    Cvar_SetValue("_aw_debug_all",on);Cvar_SetValue("_aw_debug_coords",on);
    vid.recalc_refdef=true;scr_copyeverything=1;
    Con_Printf(on?"Inspect HUD on: aim and click to pin; attack disabled.\n":"Inspect HUD off: normal controls (release any held click).\n");
}
static void inspect_command(void) {pin_target();print_pin();}
void AW_InspectInit(void) {
    enabled=held=release_attack=rows=0;
    aw_inspect_buttons=buttons;aw_inspect_crosshair=crosshair;aw_inspect_draw=draw;aw_inspect_reset=reset;
    Cmd_AddCommand("aw_debug_hud",hud_command);Cmd_AddCommand("aw_inspect",inspect_command);
}
