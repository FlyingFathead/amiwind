/* SPDX-License-Identifier: GPL-2.0-or-later */
/* CORPSE-LOOT-60: the body of a dead NPC or creature in reach under the crosshair (the same aim as talking,
 * AW_NPCTarget) reads "E: Search" and E opens the container strip (aw_cstrip.c) with its inventory: the actor record's
 * NPCO list and its levelled entries from the area tables (tools/prepare_focus.py contents list, flag 8; rolled on the
 * first open as a container's, CONTAINER-LEVELLED-CONTENTS-60), the changes kept on the world change list under the
 * actor's reference, so they stay across maps and saves; a respawn drops them (aw_actors.c Respawned). Taking from a
 * body is never theft (OpenMW 0.51 mwmechanics/mechanicsmanagerimp.cpp isAllowedToUse: a dead actor's items are free).
 * Also binds the CHIM actor table's list code for the levelled rolls (aw_inventory.c). Nothing resident: one aim
 * test per frame while the prompt is drawn (the talk aim's own, cached per frame in aw_scene.c), nothing allocated. */
#include "quakedef.h"
#include "aw_inventory.h"
#include "aw_actors.h"
#include "aw_character.h"
#include "chim/chim_actor_table.h"

static int lists_valid(const unsigned char *s,unsigned long bytes,unsigned items){
    return ChimActors_ListsValid(s,bytes,items);
}
static int player_level(void){
    return aw_character.valid && aw_character.level>0?aw_character.level:1;
}
/* the dead actor aimed at and its reference; NULL when none */
static edict_t *corpse_target(unsigned *reference){
    edict_t *p,*e;eval_t *v;
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !(p=svs.clients[0].edict))return NULL;
    /* FOCUS-NPC-OVERRIDES-ITEM-62: an item lying by the body (Tarhiel's journal) is taken, not the body searched */
    if(!(e=AW_ActivateActor(p,p->v.v_angle)) || AW_CombatSlotState(e,NULL)!=2)return NULL;
    if(!(v=GetEdictFieldValue(e,"aw_ref")) || v->_float<1 || v->_float>16777215.0f)return NULL;
    *reference=(unsigned)v->_float;
    return e;
}
static int corpse_prompt(char *line,int size,const char **name){
    unsigned reference;edict_t *e=corpse_target(&reference);
    if(!e || !line || size<2)return 0;
    Q_strcpy_bounded(line,"E: Search",(size_t)size);
    if(name)*name=e->v.netname?pr_strings+e->v.netname:"";
    return 1;
}
static int corpse_use(void){
    unsigned reference;edict_t *e=corpse_target(&reference);
    if(!e || !aw_container_open)return 0;
    return aw_container_open(reference,e->v.netname?pr_strings+e->v.netname:"",0);
}
static void look_at(edict_t *p,const vec3_t mid){
    vec3_t eye,delta;
    VectorAdd(p->v.origin,p->v.view_ofs,eye);VectorSubtract(mid,eye,delta);
    p->v.angles[1]=(float)(atan2(delta[1],delta[0])*180/M_PI);
    p->v.angles[0]=(float)(-atan2(delta[2],sqrt(delta[0]*delta[0]+delta[1]*delta[1]))*180/M_PI);
    p->v.angles[2]=0;VectorCopy(p->v.angles,p->v.v_angle);VectorCopy(p->v.angles,cl.viewangles);
}
void AW_CorpseCommand(void){
    edict_t *p,*e,*best=NULL;float d,nearest=1e30f;vec3_t delta;int i;char line[48];const char *name=NULL;
    double t0;
    if(!sv.active || !svs.clients || !(p=svs.clients[0].edict)){Con_Printf("aw_placed body: no game running.\n");return;}
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free || !e->v.classname || strcmp(pr_strings+e->v.classname,"aw_npc") || AW_CombatSlotState(e,NULL)!=2)continue;
        VectorSubtract(e->v.origin,p->v.origin,delta);d=DotProduct(delta,delta);
        if(d<nearest){nearest=d;best=e;}
    }
    if(!best){Con_Printf("aw_placed body: no dead actor here.\n");return;}
    /* look at its middle from where the player stands (within the activation reach: step up to 48 units from it) */
    {vec3_t mid;float len;
     float dx,dy,t;int k,up;vec3_t spot;trace_t tr;
     VectorCopy(best->v.origin,mid);mid[2]+=8;     /* a body lying: just above its origin (it may be unlinked) */
     VectorSubtract(p->v.origin,mid,delta);delta[2]=0;len=(float)sqrt(DotProduct(delta,delta));
     if(len<1){delta[0]=1;delta[1]=0;len=1;}
     /* a clear standing spot 40 units from it (sixteen directions, the player's side first; the body may lie on
      * another floor than the player stands on), as aw_placed container aim finds one */
     /* the first clear spot from which the aim holds the body (a living resident beside it may stand in the line from
      * one side, as a player would step round him); none: the first clear spot */
     {vec3_t first,start;int found=0,clear=0;VectorCopy(p->v.origin,start);
     dx=delta[0]/len;dy=delta[1]/len;
     for(k=0;k<16 && !found;k++,t=dx*0.92388f-dy*0.38268f,dy=dx*0.38268f+dy*0.92388f,dx=t){
        spot[0]=best->v.origin[0]+dx*40;spot[1]=best->v.origin[1]+dy*40;
        for(up=0;up<=48;up+=4){
            spot[2]=best->v.origin[2]+(float)up;
            /* MOVE_NORMAL: never inside a living actor (CORPSE-INVENTORY-NOT-OPENABLE-59: the old MOVE_NOMONSTERS spot
             * put the eye inside a resident standing there, whose bounds then held the crosshair and E talked to him;
             * the body itself is SOLID_NOT since its death, so it never blocks the spot) */
            tr=SV_Move(spot,p->v.mins,p->v.maxs,spot,MOVE_NORMAL,p);
            if(!tr.startsolid && !tr.allsolid)break;
        }
        if(up>48)continue;
        if(!clear++)VectorCopy(spot,first);
        VectorCopy(spot,p->v.origin);look_at(p,mid);
        found=AW_NPCTarget(p,p->v.v_angle)==best;
     }
     if(!found && clear){VectorCopy(first,p->v.origin);}
     if(!found && !clear){VectorCopy(start,p->v.origin);}
     Con_Printf("aw_placed body: %d clear spots tried, %s\n",clear,found?"the body under the crosshair":"none aims at the body");}
     VectorCopy(vec3_origin,p->v.velocity);look_at(p,mid);
     p->v.fixangle=1;SV_LinkEdict(p,false);}
    Con_Printf("aw_placed body: %s at %d %d %d (model %d), %s\n",best->v.netname?pr_strings+best->v.netname:"?",
               (int)best->v.origin[0],(int)best->v.origin[1],(int)best->v.origin[2],(int)best->v.modelindex,
               corpse_prompt(line,sizeof(line),&name)?line:"not under the crosshair");
    /* what the crosshair holds instead, and where the body is drawn (its frame and pose), for the next look */
    {edict_t *t=AW_NPCTarget(p,p->v.v_angle);
     Con_Printf("aw_placed body: player at %d %d %d, frame %d, yaw %d, solid %d; aim %s%s\n",(int)p->v.origin[0],
                (int)p->v.origin[1],(int)p->v.origin[2],(int)best->v.frame,(int)best->v.angles[1],(int)best->v.solid,
                t?(t->v.netname?pr_strings+t->v.netname:"?"):"nothing",t && t!=best?" (another actor)":"");
     if(t && t!=best){int mi=(int)t->v.modelindex;model_t *tm=mi>0 && mi<MAX_MODELS?sv.models[mi]:NULL;
        Con_Printf("aw_placed body: %s at %d %d %d, frame %d, model %d %s, bounds z %d..%d\n",
                   t->v.netname?pr_strings+t->v.netname:"?",(int)t->v.origin[0],(int)t->v.origin[1],(int)t->v.origin[2],
                   (int)t->v.frame,mi,tm && Cache_Check(&tm->cache)?"resident":"evicted",
                   tm?(int)tm->mins[2]:0,tm?(int)tm->maxs[2]:0);}}
    /* how the body is drawn: its model, frames, skeleton, leaves and effects (CORPSE-LOOT-60: not seen in stills) */
    {int mi=(int)best->v.modelindex;model_t *bm=mi>0 && mi<MAX_MODELS?sv.models[mi]:NULL;aliashdr_t *h;
     h=bm && bm->type==mod_alias?(aliashdr_t *)Cache_Check(&bm->cache):NULL;
     Con_Printf("aw_placed body: drawn as %s, %s, %d frames%s, leaves %d, effects %d, angles %d %d %d, bounds z %d..%d\n",
                bm?bm->name:"no model",h?"resident":"not resident",h?((mdl_t *)((byte *)h+h->model))->numframes:0,
                h && h->aw_skel?" (skeletal)":"",best->num_leafs,(int)best->v.effects,(int)best->v.angles[0],
                (int)best->v.angles[1],(int)best->v.angles[2],bm?(int)bm->mins[2]:0,bm?(int)bm->maxs[2]:0);}
    if(Cmd_Argc()>2 && !strcmp(Cmd_Argv(2),"look"))return;   /* aw_placed body look: stand and aim only (a still) */
    t0=Sys_FloatTime();
    if(corpse_use())Con_Printf("aw_placed body: opened in %d ms\n",(int)((Sys_FloatTime()-t0)*1000));
    else Con_Printf("aw_placed body: E did not open it\n");
}
void AW_CorpseInit(void){
    aw_corpse_prompt=corpse_prompt;aw_corpse_use=corpse_use;
    aw_levelled_valid=lists_valid;aw_levelled_pick=ChimActors_LevelledPick;aw_levelled_level=player_level;
}
