/* SPDX-License-Identifier: GPL-2.0-or-later
 * WORLD-OBJECT-PLACEMENT-59: the items the original game placed in a room or an exterior cell, drawn by reference
 * to the shared item model table (progs/items/models.awt; the list progs/items/placed.awp is read with the focus
 * rows in aw_inventory.c placed_load, which offers each row the map does not draw itself). Client entities like
 * the harvest proxies (aw_harvest_proxy.c): no edict, no model precache, nothing sent; one loaded model per mesh
 * and level (at most AW_PLACED_MODELS, the room every map keeps: tools/map_engine_limits.py RUNTIME_MODELS), every
 * placement a reference to it with its own position, rotation and scale. A taken or disabled item (the object
 * state, aw_mwhost.c) is not linked, so it stays gone after a save and a load. `aw_placed off` draws none (from the next map).
 */
#include "quakedef.h"
#include "aw_inventory.h"
#include "aw_placed.h"
#include "aw_tryalloc.h"
#include "aw_ledger.h"
#define PLACED_MAX 1024                   /* the focus table's rows (aw_inventory.c FOCUS_ROWS) */
#define PLACED_PATH 40                     /* "progs/items/m" + 16 hex + ".mdl" + NUL = 34 bytes */
#define PLACED_STEP 64                     /* the table grows by this many rows when a room or cell needs more */
#define PLACED_ENTRY 320                   /* bytes per row at most: an entity, its reference and its base position */
typedef char placed_entry_fits[(sizeof(entity_t)+sizeof(unsigned)+3*sizeof(float)<=PLACED_ENTRY)?1:-1];
AW_RESIDENT_GROWS("placed items (WORLD-OBJECT-PLACEMENT-59)",PLACED_MAX,PLACED_ENTRY);
static int placed_on=1;                   /* aw_placed on|off */
static entity_t *ents;
static unsigned *refs;
static float (*base)[3];
static int count,capacity,shift_ok;
static vec3_t shift_now;
static char model_names[AW_PLACED_MODELS][PLACED_PATH];
static model_t *models[AW_PLACED_MODELS];
static int placed_models_used;
static model_t *level_world;
static char level_name[64];
/* A new map (or cell): the drawn set is empty; a new level also gives the model room back. 0: draw nothing. */
static int placed_begin(void){
    count=0;shift_ok=0;
    if(level_world!=sv.worldmodel || strcmp(level_name,sv.name)){
        level_world=sv.worldmodel;Q_strncpy(level_name,sv.name,sizeof(level_name)-1);level_name[sizeof(level_name)-1]=0;
        placed_models_used=0;
    }
    return placed_on && vid.colormap;
}
/* Room for one more row: the three tables grow together by PLACED_STEP rows (they keep what they hold; the visible
 * list is rebuilt every frame, so a moved entity is never left behind in it). 0 when memory or PLACED_MAX says no. */
static int grow(void){
    entity_t *e;unsigned *r;float (*b)[3];int want;
    if(count<capacity)return 1;
    if(capacity>=PLACED_MAX)return 0;
    want=capacity+PLACED_STEP;
    if(!(e=(entity_t *)AW_TryRealloc(ents,(unsigned long)want*sizeof(entity_t))))return 0;
    ents=e;
    if(!(r=(unsigned *)AW_TryRealloc(refs,(unsigned long)want*sizeof(unsigned))))return 0;
    refs=r;
    if(!(b=(float (*)[3])AW_TryRealloc(base,(unsigned long)want*sizeof(*base))))return 0;
    base=b;capacity=want;
    return 1;
}
/* The loaded model of progs/items/m<STEM>.mdl, once per level; NULL when the level's room is used up, the loaded-model
 * table has no free slot, or the file is not an alias model. */
static model_t *placed_model(const char *stem){
    char path[PLACED_PATH];int i;model_t *m;
    for(i=0;i<16;i++)if(!((stem[i]>='0' && stem[i]<='9') || (stem[i]>='a' && stem[i]<='f')))return NULL;
    if(stem[16])return NULL;
    Q_snprintf(path,sizeof(path),"progs/items/m%s.mdl",stem);
    for(i=0;i<placed_models_used;i++)if(!strcmp(model_names[i],path))return models[i];
    if(placed_models_used>=AW_PLACED_MODELS || !Mod_CanFindName(path))return NULL;
    m=Mod_ForName(path,false);
    if(!m || m->type!=mod_alias)return NULL;
    strcpy(model_names[placed_models_used],path);models[placed_models_used++]=m;
    return m;
}
static int placed_admit(unsigned reference,const char *stem,const float local[3],const float angles[3],float scale){
    entity_t *e;model_t *m;
    if(!(m=placed_model(stem)) || !grow())return 0;
    e=&ents[count];memset(e,0,sizeof(*e));
    e->model=m;e->colormap=vid.colormap;
    VectorCopy(angles,e->angles);
    if(scale!=1.0f){e->aw_sprite_scale=scale;e->effects=AW_EF_ALIAS_SCALE;}
    VectorCopy(local,base[count]);VectorCopy(local,e->origin);
    refs[count]=reference;
    return ++count;
}
/* aw_mwhost.c AW_ObjectTake: REFERENCE is drawn here (taking it hides it through the object state). */
static int placed_drawn(unsigned reference){
    int i;
    if(level_world!=sv.worldmodel)return 0;
    for(i=0;i<count;i++)if(refs[i]==reference)return 1;
    return 0;
}
int AW_PlacedCount(void){return level_world==sv.worldmodel?count:0;}
int AW_PlacedModels(void){return level_world==sv.worldmodel?placed_models_used:0;}
/* The drawn rows by distance from the player's eye, nearest first (at most 16): for the two test commands below. */
static int nearest(int *order,int most){
    int i,j,n=0;float d[16],dist;vec3_t eye,delta;edict_t *p;
    if(!sv.active || !svs.clients || !(p=svs.clients[0].edict) || level_world!=sv.worldmodel)return 0;
    VectorCopy(p->v.origin,eye);eye[2]+=p->v.view_ofs[2];
    for(i=0;i<count;i++){
        if(AW_ObjectDisabled(refs[i]))continue;
        VectorSubtract(ents[i].origin,eye,delta);dist=Length(delta);
        for(j=n;j>0 && d[j-1]>dist;j--)if(j<most){d[j]=d[j-1];order[j]=order[j-1];}
        if(j<most){d[j]=dist;order[j]=i;if(n<most)n++;}
    }
    return n;
}
/* aw_placed (status): how many placed items this level draws, the models loaded, the nearest ones (test sessions). */
static void status_command(void){
    int order[16],n=nearest(order,8),i;edict_t *p=svs.clients?svs.clients[0].edict:NULL;vec3_t delta;
    Con_Printf("Placed items: %s, %d drawn, %d of %d item models loaded on this level.\n",placed_on?"on":"off",
               AW_PlacedCount(),AW_PlacedModels(),AW_PLACED_MODELS);
    {int s[6];AW_PlacedReadStats(s);
     Con_Printf("  last read: %d keys (%s), %d rows: %d not in the focus table, %d drawn by the map, %d outside it, %d offered\n",
                s[0]<0?-s[0]:s[0],s[0]<0?"outdoors":"room",s[1],s[2],s[3],s[4],s[5]);}
    for(i=0;i<n && p;i++){
        VectorSubtract(ents[order[i]].origin,p->v.origin,delta);
        Con_Printf("  %d: reference %u, %s, %.0f units\n",i,refs[order[i]],ents[order[i]].model->name,Length(delta));
    }
}
/* aw_placed look [N]: turn the view to the Nth nearest drawn placed item (0 = the nearest), as a test session's aim;
 * aw_placed go [N] first puts the player 24 units from it on its far side from the player, eye 12 units above it
 * (a test session's step into reach: use noclip around it, the spot is not checked for room to stand). */
static void look_command(int go){
    int order[16],n=nearest(order,16),k=Cmd_Argc()>2?atoi(Cmd_Argv(2)):0;edict_t *p;
    vec3_t eye,delta,angles;float flat;
    if(k<0 || k>=n || !svs.clients || !(p=svs.clients[0].edict)){Con_Printf("aw_placed look: %d drawn placed items near here.\n",n);return;}
    if(go){
        VectorSubtract(p->v.origin,ents[order[k]].origin,delta);delta[2]=0;flat=Length(delta);
        if(flat<1){delta[0]=1;delta[1]=0;flat=1;}
        p->v.origin[0]=ents[order[k]].origin[0]+delta[0]/flat*24;p->v.origin[1]=ents[order[k]].origin[1]+delta[1]/flat*24;
        p->v.origin[2]=ents[order[k]].origin[2]+12-p->v.view_ofs[2];
        SV_LinkEdict(p,false);
    }
    VectorCopy(p->v.origin,eye);eye[2]+=p->v.view_ofs[2];
    VectorSubtract(ents[order[k]].origin,eye,delta);
    angles[1]=(float)(atan2(delta[1],delta[0])*180/M_PI);
    angles[0]=(float)(-atan2(delta[2],sqrt(delta[0]*delta[0]+delta[1]*delta[1]))*180/M_PI);   /* Quake: down is +pitch */
    cl.viewangles[0]=angles[0];cl.viewangles[1]=angles[1];cl.viewangles[2]=0;
    Con_Printf("aw_placed look: reference %u at %.0f units.\n",refs[order[k]],Length(delta));
}
/* aw_placed ledger [on|off] (CELL-CHANGES-59): the world change list's counts and resident bytes; on (the default) keeps
 * the object state and the drops on it, off on the old fixed tables (1,024 objects, 32 drops by map name), from the
 * next new game or load. Not saved. */
static void ledger_command(void){
    const char *b=Cmd_Argc()>2?Cmd_Argv(2):"";
    if(!strcmp(b,"on") || !strcmp(b,"off")){
        aw_ledger_on=!strcmp(b,"on");
        Con_Printf("World change list %s from the next new game or load.\n",aw_ledger_on?"on":"off (the fixed tables)");
    }
    AW_MwscriptLedgerStatus();
}
/* aw_placed pass HOURS (CELL-CHANGES-59 slice 7, a check command): the game clock goes on HOURS game hours (at most
 * 100,000), as waiting and resting move it (aw_clock.c AW_ClockAdvance, a day at a time), for the respawn checks;
 * nothing else of a rest happens (no healing, no recharge). */
int AW_ClockAdvance(int milliseconds);
static void pass_command(void){
    double h=Cmd_Argc()>2?Q_atof(Cmd_Argv(2)):0,left;
    if(!(h>0 && h<=100000)){Con_Printf("aw_placed pass HOURS: 1 to 100000 game hours.\n");return;}
    for(left=h;left>0;left-=24)
        if(!AW_ClockAdvance(left>=24?86400000:(int)(left*3600000.0))){Con_Printf("aw_placed pass: the clock stops here.\n");break;}
    Con_Printf("aw_placed pass: %.1f game hours passed; now %.1f.\n",h,AW_LedgerGameHours());
}
/* One console command (the resident registry counts each): aw_placed [status | look [N] | go [N] | on | off |
 * ledger [on|off] | container ... | pass HOURS]. Off draws no placed item from the next map or cell on (an A/B of their
 * cost); not saved. */
static void placed_command(void){
    const char *a=Cmd_Argc()>1?Cmd_Argv(1):"status";
    if(!strcmp(a,"ledger")){ledger_command();return;}
    if(!strcmp(a,"pass")){pass_command();return;}
    if(!strcmp(a,"container")){AW_ContainerCommand();return;}   /* CELL-CHANGES-59 slice 3 */
    if(!strcmp(a,"areas")){AW_AreaStatus();return;}             /* AREA-TABLES-59 */
    if(!strcmp(a,"look") || !strcmp(a,"go"))look_command(!strcmp(a,"go"));
    else if(!strcmp(a,"on") || !strcmp(a,"off")){placed_on=!strcmp(a,"on");Con_Printf("Placed items %s from the next map.\n",a);}
    else status_command();
}
void AW_PlacedInit(void){
    Cmd_AddCommand("aw_placed",placed_command);
    aw_placed_begin=placed_begin;aw_placed_admit=placed_admit;aw_object_drawn=placed_drawn;aw_placed_link=AW_PlacedLink;
    AW_CStripInit();     /* CONTAINER-WINDOW-59: E on a container opens its strip */
}
void AW_PlacedLink(void){
    int i,outdoor;vec3_t shift;
    if(!sv.active || svs.maxclients!=1 || cls.state!=ca_connected)return;
    outdoor=AW_PlacedRefresh();
    if(!count || level_world!=sv.worldmodel || !placed_on)return;
    /* a room's rows are a quarter scale; its shift (the scripts' placements use the same) is added here */
    if(outdoor)shift[0]=shift[1]=shift[2]=0;else AW_MwscriptRoomShift(shift);
    if(!shift_ok || !VectorCompare(shift,shift_now)){
        for(i=0;i<count;i++)VectorAdd(base[i],shift,ents[i].origin);
        VectorCopy(shift,shift_now);shift_ok=1;
    }
    for(i=0;i<count && cl_numvisedicts<MAX_VISEDICTS;i++)
        if(!AW_ObjectDisabled(refs[i]))cl_visedicts[cl_numvisedicts++]=&ents[i];
}
