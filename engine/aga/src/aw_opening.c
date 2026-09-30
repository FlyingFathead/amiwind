/* SPDX-License-Identifier: GPL-2.0-or-later
 * Bounded adapters for audited opening scripts. Each actor retains its own
 * state/timers; speech completion, menus and movement are separate gates. */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"
static int route_started,route_failed;
static float near_actor(int role)
{
    edict_t *actor=AW_IntroRole(role),*player=svs.clients[0].edict;vec3_t delta;
    if(!actor)return 1e30f;
    VectorSubtract(actor->v.origin,player->v.origin,delta);
    /* Source actor positions are at their feet. Native NPC origins are there
     * too, but the player's origin is the middle of the standing hull. Keep
     * the source 3-D radius; comparing mismatched anchors shrinks the trigger. */
    delta[2]+=actor->v.mins[2]-player->v.mins[2];
    return (float)sqrt(DotProduct(delta,delta));
}
static int dock_route(int second)
{
    vec3_t goal;
    goal[0]=((second?-9944.f:-8914.f)+11264)*.25f;
    goal[1]=((second?-72481.f:-73093.f)+71680)*.25f;goal[2]=31.5f;
    route_started=AW_NavStart(AW_IntroRole(5),goal);
    if(!route_started){
        route_failed=1;Con_Printf("Dock route unavailable; story held for inspection.\n");
        AW_UISubtitle("Dock guard","Route unavailable. Please report this checkpoint.",10);
    }
    return route_started;
}
static void hide(edict_t *e)
{
    e->v.modelindex=0;e->v.solid=SOLID_NOT;SV_LinkEdict(e,false);
}
void AW_OpeningSpawn(void)
{
    int i,reference;edict_t *e;eval_t *v;
    route_started=route_failed=0;
    if(aw_story.stage==AW_STAGE_DEMO)return;
    if(!strcmp(sv.name,"census") && aw_story.stage>=AW_STAGE_OFFICE)aw_story.ship_disabled=1;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free)continue;
        v=GetEdictFieldValue(e,"aw_ref");reference=v?(int)v->_float:0;
        v=GetEdictFieldValue(e,"aw_story_hidden");
        if(!strcmp(sv.name,"seyda") && aw_story.ship_disabled && v && v->_float)hide(e);
        if(!strcmp(sv.name,"census")){
            if(reference==172859 && (aw_story.stage<AW_STAGE_PAPERS || AW_Papers() || aw_story.captain))hide(e);
            if(reference==172860 && aw_story.hall_open){e->v.angles[1]=-90;SV_LinkEdict(e,false);}
        }
    }
    if(aw_story.ship_disabled && !strcmp(sv.name,"seyda")){
        if(AW_IntroRole(4))hide(AW_IntroRole(4));
        if(AW_IntroRole(5))hide(AW_IntroRole(5));
    }
}
int AW_OpeningLocked(void)
{
    if(AW_ReaderActive())return 1;
    if(!AW_StoryRestricted())return 0;
    if(!strcmp(sv.name,"seyda"))return aw_story.dock>=20 && aw_story.dock<=50;
    if(!strcmp(sv.name,"census"))return aw_story.census>=10 && aw_story.census<=17;
    return 0;
}
static void show_papers(void)
{
    int i;eval_t *v;edict_t *e;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free)continue;
        v=GetEdictFieldValue(e,"aw_ref");
        if(v && (int)v->_float==172859){e->v.modelindex=SV_ModelIndex(pr_strings+e->v.model);e->v.solid=SOLID_BSP;SV_LinkEdict(e,false);}
    }
}
int AW_OpeningTick(void)
{
    double dt=host_frametime;int result,done;
    if(AW_ReaderActive())return 1;
    if(!AW_StoryRestricted())return 0;
    result=AW_ReaderResult();
    if(result==1 && aw_story.stage==AW_STAGE_PAPERS){
        AW_ItemAdd(&aw_state,"chargen statssheet",1);AW_StoryTransition(AW_STAGE_COURTYARD);AW_OpeningSpawn();
    }else if(result==2 && aw_story.stage==AW_STAGE_CAPTAIN){
        if(AW_Papers()){AW_ItemAdd(&aw_state,"chargen statssheet",-1);aw_story.captain=-1;}
        AW_ReaderOpen("captain_duties",AW_StateGet(&aw_state,AW_JOURNAL,"A1_1_FindSpymaster")==0?3:0);return 1;
    }else if(result==3 && aw_story.stage==AW_STAGE_CAPTAIN && AW_CaptainDuties()){
        AW_UISubtitle("","Package, directions and 87 gold received.",5);
    }
    /* Taking a fixed item is a world event, not permission to skip menus.
     * If it was acquired earlier, let the normal courtyard gate observe it. */
    if(aw_story.stage==AW_STAGE_COURTYARD && AW_Ring())AW_StoryTransition(AW_STAGE_CAPTAIN);
    if(dt>.1)dt=.1;
    done=AW_CharacterDone();
    if(!strcmp(sv.name,"seyda") && !aw_story.ship_disabled && AW_IntroRole(5)){
        if(aw_story.dock==0){if(dock_route(0))aw_story.dock=10;}
        if(aw_story.dock==10){
            if(near_actor(5)<27){
                /* Source AIWander 0 stops travel as soon as the player arrives. */
                AW_NavLoad("seyda");route_started=0;aw_story.dock=20;
            }else if(!route_failed){
                if(!route_started)dock_route(0);
                if(route_started){result=AW_NavStep(dt,0);
                if(result<0){route_failed=1;Con_Printf("Dock approach blocked.\n");}}
            }
        }
        if(aw_story.dock==20 && AW_IntroSpeak(5,"chargendock1"))aw_story.dock=30;
        else if(aw_story.dock==30 && AW_SpeechRemaining()<=0){
            if(AW_CharacterOpen(1)){AW_StoryTransition(AW_STAGE_RACE);aw_story.dock=40;aw_story.dock_timer=0;}
        }else if(aw_story.dock==40){
            if(done==1)AW_StoryTransition(AW_STAGE_OFFICE);
            if(aw_story.stage==AW_STAGE_OFFICE)aw_story.dock_timer+=dt;
            if(aw_story.dock_timer>=1.5 && AW_IntroSpeak(5,"chargendock2")){aw_story.dock=50;aw_story.dock_timer=0;}
        }else if(aw_story.dock==50 && AW_SpeechRemaining()<=0){
            aw_story.dock=-1;route_started=route_failed=0;dock_route(1);IN_AWClearButtons();
        }else if(aw_story.dock==-1){
            if(!route_started && !route_failed)dock_route(1);
            if(route_started && !route_failed){result=AW_NavStep(dt,0);
            if(result)route_failed=1;}
            if(near_actor(5)<37.5 && AW_SpeechRemaining()<=0){
                aw_story.dock_timer+=dt;
                if(aw_story.dock_timer>6 && AW_IntroSpeak(5,"chargendock3"))aw_story.dock_timer=0;
            }
        }
    }
    if(strcmp(sv.name,"census") || aw_story.stage<AW_STAGE_OFFICE)return 0;
    if(!aw_story.captain_hint && near_actor(7)<75){
        aw_story.captain_hint=1;AW_UISubtitle("","E: talk to Sellus Gravius. Ask about your duties.",7);
    }
    if(aw_story.census==0 && near_actor(6)<25 && AW_IntroSpeak(6,"chargen_class1"))aw_story.census=10;
    else if(aw_story.census==10 && AW_SpeechRemaining()<=0){
        if(AW_CharacterOpen(2)){AW_StoryTransition(AW_STAGE_CLASS);aw_story.census=12;aw_story.census_timer=0;}
    }else if(aw_story.census==12){
        if(done==2)AW_StoryTransition(AW_STAGE_BIRTH);
        if(aw_story.stage==AW_STAGE_BIRTH)aw_story.census_timer+=dt;
        if(aw_story.census_timer>1 && AW_IntroSpeak(6,"chargen_birth")){aw_story.census=14;aw_story.census_timer=0;}
    }else if(aw_story.census==14 && AW_SpeechRemaining()<=0){
        if(AW_CharacterOpen(3))aw_story.census=15;
    }else if(aw_story.census==15){
        if(done==3)AW_StoryTransition(AW_STAGE_REVIEW);
        if(aw_story.stage==AW_STAGE_REVIEW)aw_story.census_timer+=dt;
        if(aw_story.census_timer>1 && AW_IntroSpeak(6,"chargen_class2")){aw_story.census=16;aw_story.census_timer=0;}
    }else if(aw_story.census==16 && AW_SpeechRemaining()<=0){
        if(AW_CharacterOpen(4))aw_story.census=17;
    }else if(aw_story.census==17){
        if(done==4)AW_StoryTransition(AW_STAGE_PAPERS);
        if(aw_story.stage==AW_STAGE_PAPERS)aw_story.census_timer+=dt;
        if(aw_story.census_timer>1){aw_story.census=20;aw_story.census_timer=0;IN_AWClearButtons();}
    }else if(aw_story.census==20 && AW_IntroSpeak(6,"chargen_class3")){
        show_papers();aw_story.census=30;
        svs.clients[0].edict->v.health=aw_character.current[0];
    }else if(aw_story.census==30 && AW_SpeechRemaining()<=0){
        aw_story.census_timer+=dt;
        if(aw_story.census_timer>1){AW_UISubtitle("Registration","E: read your papers, then take them to the captain.",8);aw_story.census=-1;aw_story.census_timer=0;}
    }else if(aw_story.census==-1 && !AW_Papers() && !aw_story.captain && near_actor(6)<45 && AW_SpeechRemaining()<=0){
        aw_story.census_timer+=dt;
        if(aw_story.census_timer>5 && AW_IntroSpeak(6,"chargen_class4"))aw_story.census_timer=0;
    }
    if(!aw_story.hall && near_actor(8)<45 && AW_SpeechRemaining()<=0){
        if(AW_Papers()){if(AW_IntroSpeak(8,"chargen_door2"))aw_story.hall=1;}
        else{
            aw_story.hall_timer+=dt;
            if(aw_story.hall_timer>3 && AW_IntroSpeak(8,"chargen_door1"))aw_story.hall_timer=0;
        }
    }
    return 1;
}
/* A pure query shared by the prompt and activation. Hidden, occluded and
 * out-of-reach objects cannot advertise an action. Automatic actor scripts
 * retain their separate proximity triggers above. */
static void door_point(edict_t *e,vec3_t eye,vec3_t point)
{
    model_t *m;int i,index=(int)e->v.modelindex;vec3_t local,delta,f,r,u;
    m=index>0 && index<MAX_MODELS?sv.models[index]:NULL;
    if(m && m->type==mod_brush){
        AngleVectors(e->v.angles,f,r,u);VectorSubtract(eye,e->v.origin,delta);
        local[0]=DotProduct(delta,f);local[1]=-DotProduct(delta,r);local[2]=DotProduct(delta,u);
        for(i=0;i<3;i++){
            if(local[i]<m->mins[i])local[i]=m->mins[i];
            if(local[i]>m->maxs[i])local[i]=m->maxs[i];
        }
        for(i=0;i<3;i++)point[i]=e->v.origin[i]+local[0]*f[i]-local[1]*r[i]+local[2]*u[i];
    }else for(i=0;i<3;i++){
        point[i]=eye[i];
        if(point[i]<e->v.absmin[i])point[i]=e->v.absmin[i];
        if(point[i]>e->v.absmax[i])point[i]=e->v.absmax[i];
    }
}
static edict_t *opening_target(void)
{
    int i,ref,role;edict_t *p,*e,*target=NULL;eval_t *v;
    vec3_t eye,delta,forward,right,up,point;float distance,best=57;trace_t tr;
    if(!sv.active || !svs.clients)return NULL;
    p=svs.clients[0].edict;if(!p || p->v.movetype!=MOVETYPE_WALK)return NULL;
    VectorAdd(p->v.origin,p->v.view_ofs,eye);AngleVectors(cl.viewangles,forward,right,up);
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);if(e->free || !e->v.modelindex)continue;
        v=GetEdictFieldValue(e,"aw_ref");ref=v?(int)v->_float:0;
        role=e==AW_IntroRole(6)?6:e==AW_IntroRole(7)?7:e==AW_IntroRole(8)?8:0;
        if(role){
            if(!AW_StoryRestricted() || strcmp(sv.name,"census") || near_actor(role)>=48 ||
               (role==6 && aw_story.census!=0) || (role==7 && aw_story.stage!=AW_STAGE_CAPTAIN))continue;
            VectorCopy(e->v.origin,point);point[2]+=27;
        }else{
            if(ref!=172859 && ref!=172860 && ref!=172851)continue;
            if(ref==172860 && aw_story.hall_open)continue;
            VectorAdd(e->v.absmin,e->v.absmax,point);VectorScale(point,.5f,point);
            /* A tall hinged door's centre can be above the player's reach.
             * Aim toward its nearest visible surface at eye height, while
             * retaining facing, distance and occlusion checks. */
            if(ref==172860)door_point(e,eye,point);
        }
        VectorSubtract(point,eye,delta);distance=Length(delta);
        if(distance<.1f || distance>=best || distance>=(ref==172860?56:49) || DotProduct(delta,forward)/distance<.65f)continue;
        tr=SV_Move(eye,vec3_origin,vec3_origin,point,MOVE_NORMAL,p);
        if(tr.startsolid || (tr.fraction<1 && tr.ent!=e))continue;
        best=distance;target=e;
    }
    return target;
}
int AW_OpeningHint(const char **name,const char **action)
{
    edict_t *target=opening_target();eval_t *v;int ref;
    if(!target)return 0;
    if(target==AW_IntroRole(6) || target==AW_IntroRole(7) || target==AW_IntroRole(8)){
        *name=pr_strings+target->v.netname;*action="Talk: E";return 1;
    }
    v=GetEdictFieldValue(target,"aw_ref");ref=(int)v->_float;
    if(ref==172859){*name="Identification papers";*action="Read: E";}
    else if(ref==172860){*name="Hall door";*action=aw_story.hall?"Open: E":"Locked - show papers";}
    else{*name="Barrel";*action=AW_CourtyardRingAvailable()?"Take ring: E":"Empty";}
    return 1;
}
int AW_OpeningUse(void)
{
    edict_t *target=opening_target();eval_t *v;int ref;
    if(!target)return 0;
    if(target==AW_IntroRole(6)){
        if(AW_IntroSpeak(6,"chargen_class1"))aw_story.census=10;
        return 1;
    }
    if(target==AW_IntroRole(7)){
        if(AW_Papers() || aw_story.captain)AW_ReaderOpen("captain_greeting",2);
        else AW_UISubtitle("Sellus Gravius","Bring your identification papers.",4);
        return 1;
    }
    if(target==AW_IntroRole(8)){
        if(AW_IntroSpeak(8,AW_Papers() || aw_story.hall?"chargen_door2":"chargen_door1") && AW_Papers())aw_story.hall=1;
        return 1;
    }
    v=GetEdictFieldValue(target,"aw_ref");ref=(int)v->_float;
    if(ref==172859){AW_ReaderOpen("papers",1);return 1;}
    if(ref==172860){
        if(aw_story.hall){AW_DoorSound(ref,0);target->v.angles[1]=-90;SV_LinkEdict(target,false);aw_story.hall_open=1;}
        else AW_UISubtitle("","The door is locked. Show your papers to the guard.",4);
        return 1;
    }
    if(AW_CourtyardRingAvailable()){
        if(AW_CourtyardTakeRing()){
            if(aw_story.stage==AW_STAGE_COURTYARD)AW_StoryTransition(AW_STAGE_CAPTAIN);
            AW_UISubtitle("Barrel","Engraved Ring of Healing taken.",5);
        }else AW_UISubtitle("Barrel","Could not take the ring. Contents retained.",4);
    }else AW_UISubtitle("Barrel","Empty.",3);
    return 1;
}
