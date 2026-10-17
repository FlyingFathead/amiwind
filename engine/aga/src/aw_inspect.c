/* SPDX-License-Identifier: GPL-2.0-or-later
 * Click-to-pin raw identity. Reuses AmiQuake's point trace, frame bounds and
 * console, plus AW_NPCTargetReach's rotated slab test. No actor mutation,
 * allocation or per-frame entity scan. Rows are a click snapshot, not a retained
 * edict pointer (slots can be reused). A CHIM placement (it collides as the world)
 * is named from its frame's placement record and the index's model name: a few
 * small reads per click, none per frame (INSPECT-CHIM-PLACEMENT-UNNAMED-42).
 * Nothing is drawn over the 3D view: aw_hud.c draws the hint and the snapshot
 * underneath the stat bars, at the bottom of the screen (INSPECT-OVER-VIEWPORT-42); the
 * right mouse button leaves inspect mode (INSPECT-NO-RIGHT-CLICK-EXIT-42).
 */
#include "quakedef.h"
#include "aw_character.h"
#include "aw_inspect.h"
#include "aw_world.h"
#define INSPECT_ROWS 10
#define INSPECT_WIDTH AW_INSPECT_LINE
#define INSPECT_REACH 2048.0f
static int enabled,held,release_attack,rows;
static char pinned[INSPECT_ROWS][INSPECT_WIDTH];
extern int scr_copyeverything,con_notify_quiet;
int (*aw_chim_pick)(const float *start,const float *end,aw_chim_pick_t *out);
static const char hint_text[]="INSPECT: click pin / right exit";

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
    /* A placed model in a CHIM frame collides as the world: ask the frame which
     * placement the same ray hit at the same distance (else terrain/frame world). */
    if(!st && best==sv.edicts && aw_chim_pick){
        aw_chim_pick_t hit;vec3_t far;
        VectorMA(eye,INSPECT_REACH,dir,far);
        if(aw_chim_pick(eye,far,&hit) && fabs(hit.fraction*INSPECT_REACH-limit)<=2.0f){
            snprintf(value,sizeof(value),"CHIM placement %lu / collision pick",(unsigned long)hit.pid);text_field("PINNED",value);
            if(hit.name[0])snprintf(value,sizeof(value),"%s (model %lu)",hit.name,(unsigned long)hit.model);
            else snprintf(value,sizeof(value),"model %lu",(unsigned long)hit.model);
            text_field("mesh",value);
            if(hit.ref)snprintf(value,sizeof(value),"%lu / cell %ld,%ld",(unsigned long)hit.ref,(long)hit.cell_x,(long)hit.cell_y);
            text_field("source ref",hit.ref?value:NULL);
            snprintf(value,sizeof(value),"%.1f %.1f %.1f yaw %.1f",hit.origin[0],hit.origin[1],hit.origin[2],hit.yaw);
            text_field("placement local XYZ",value);
            snprintf(value,sizeof(value),"%s / hit %.1f %.1f %.1f",sv.name,position[0],position[1],position[2]);text_field("scene",value);
            if(AW_WorldToSource(sv.name,position,global)){
                snprintf(value,sizeof(value),"%.1f %.1f %.1f",global[0],global[1],global[2]);text_field("hit global XYZ",value);
            }
            return;
        }
    }
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
    int i;
    /* The lines under the stat bars show the snapshot; the console keeps the full rows
     * without notify lines over the view. */
    con_notify_quiet=1;
    Con_Printf("Inspect snapshot (fixed at click; not live):\n");
    for(i=0;i<rows;i++)Con_Printf("%s\n",pinned[i]);
    con_notify_quiet=0;
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
int AW_InspectEnabled(void) {return enabled;}
static const char *hint(void) {return enabled && interactive()?hint_text:NULL;}
/* The snapshot packed into at most max lines of width characters: rows joined with
 * " | ", a row never split unless it is longer than a line; the last line ends with
 * "..." when rows are left over (the console has them all). */
static int strip(char lines[][AW_INSPECT_LINE],int max,int width) {
    int i,n=0,len,used;const char *s;
    if(!enabled || !interactive() || max<=0 || width<8)return 0;
    if(width>=AW_INSPECT_LINE)width=AW_INSPECT_LINE-1;
    for(i=0;i<rows;i++){
        s=pinned[i];len=(int)strlen(s);
        used=n?(int)strlen(lines[n-1]):0;
        if(n && used+3+len<=width){strcat(lines[n-1]," | ");strcat(lines[n-1],s);continue;}
        if(n==max){
            char *last=lines[n-1];used=(int)strlen(last);
            if(used+4>width)used=width-4;
            strcpy(last+used," ...");return n;
        }
        if(len>width){memcpy(lines[n],s,width);lines[n][width]=0;memcpy(lines[n]+width-3,"...",3);}
        else strcpy(lines[n],s);
        n++;
    }
    return n;
}
static void off(void) {
    enabled=0;rows=0;
    /* Avoid a held inspection click leaking into combat when switched off. */
    if(held)release_attack=1;
    Cvar_SetValue("_aw_debug_all",0);Cvar_SetValue("_aw_debug_coords",0);
    vid.recalc_refdef=true;scr_copyeverything=1;
}
/* keys.c: right (Amiga K_MOUSE3) or middle (K_MOUSE2) button = dbg hud off. */
static int key(int k) {
    if(!enabled || (k!=K_MOUSE3 && k!=K_MOUSE2))return 0;
    off();Con_Printf("Inspect HUD off (right click).\n");return 1;
}
static void hud_command(void) {
    char *s=Cmd_Argv(1);int on;
    if(Cmd_Argc()==1){Con_Printf("dbg hud %s: click pins identity; attack disabled while on.\n",enabled?"on":"off");return;}
    if(Cmd_Argc()!=2 || (Q_strcasecmp(s,"on") && Q_strcasecmp(s,"off") && Q_strcasecmp(s,"true") &&
       Q_strcasecmp(s,"false") && strcmp(s,"1") && strcmp(s,"0"))){Con_Printf("Usage: dbg hud on/off\n");return;}
    on=!Q_strcasecmp(s,"on") || !Q_strcasecmp(s,"true") || !strcmp(s,"1");
    if(!on){off();Con_Printf("Inspect HUD off: normal controls (release any held click).\n");return;}
    enabled=1;rows=0;
    /* Avoid a held inspection click leaking into combat when switched off. */
    if(held)release_attack=1;
    Cvar_SetValue("_aw_debug_all",1);Cvar_SetValue("_aw_debug_coords",1);
    vid.recalc_refdef=true;scr_copyeverything=1;
    Con_Printf("Inspect HUD on: aim and click to pin; attack disabled; right click exits.\n");
}
static void inspect_command(void) {pin_target();print_pin();}
void AW_InspectInit(void) {
    enabled=held=release_attack=rows=0;
    aw_inspect_buttons=buttons;aw_inspect_crosshair=crosshair;aw_inspect_reset=reset;
    aw_inspect_hint=hint;aw_inspect_strip=strip;aw_inspect_key=key;
    Cmd_AddCommand("aw_debug_hud",hud_command);Cmd_AddCommand("aw_inspect",inspect_command);
}
