/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"
#include <assert.h>
server_t sv;server_static_t svs;double host_frametime=.1;
aw_character_t aw_character;char *pr_strings;
int pr_edict_size=sizeof(edict_t);client_state_t cl;
static edict_t object,clerk;static eval_t reference;static int occluded,reads;
static int obstructed,door_sounds,links,probes,world_hit;static vec3_t hit_pos;
edict_t *EDICT_NUM(int n){return n==1?&object:&clerk;}
trace_t SV_Move(vec3_t a,vec3_t mi,vec3_t ma,vec3_t b,int type,edict_t *p){
 trace_t t;memset(&t,0,sizeof(t));t.fraction=occluded?.5f:1;
 if(world_hit){t.fraction=.5f;t.ent=sv.edicts;VectorCopy(hit_pos,t.endpos);}  /* a CHIM chunk placement */
 return t;
}
static edict_t guard;static int speech,menu,done,nav_stops,nav_starts,nav_result;
static vec3_t nav_goal;
static char line[32];
edict_t *AW_IntroRole(int role){return role==5?&guard:role==6 && clerk.v.modelindex?&clerk:NULL;}
int AW_NavLoad(const char *s){nav_stops++;return 1;}
int AW_NavStart(edict_t *e,vec3_t goal){nav_starts++;VectorCopy(goal,nav_goal);return 1;}
int AW_NavStep(double dt,int wait){return nav_result;}
int AW_IntroSpeak(int role,const char *s){if(speech)return 0;strcpy(line,s);speech=1;return 1;}
double AW_SpeechRemaining(void){return speech;}
int AW_CharacterDone(void){int d=done;done=0;return d;}
int AW_CharacterOpen(int kind){menu=kind;return 1;}
int AW_ReaderActive(void){return 0;}
int AW_ReaderResult(void){return 0;}
int AW_ReaderOpen(const char *s,int n){reads++;return 1;}
void AW_UISubtitle(const char *a,const char *b,double t){}
void IN_AWClearButtons(void){}
void Con_Printf(char *s,...){}
float AW_DoorSound(unsigned ref,int close){door_sounds++;return 0;}
eval_t *GetEdictFieldValue(edict_t *e,char *s){return e==&object && !strcmp(s,"aw_ref")?&reference:NULL;}
void SV_LinkEdict(edict_t *e,qboolean t){links++;}
trace_t SV_ClipMoveToEntity(edict_t *e,vec3_t a,vec3_t mi,vec3_t ma,vec3_t b){
 trace_t tr;memset(&tr,0,sizeof(tr));assert(e==&object && e->v.angles[1]==-90);
 assert(a==b);probes++;tr.startsolid=tr.allsolid=obstructed;tr.fraction=obstructed?0:1;return tr;
}
int SV_ModelIndex(char *s){return 0;}
int main(void)
{
    edict_t player;client_t client;int i;
    memset(&player,0,sizeof(player));memset(&guard,0,sizeof(guard));
    client.edict=&player;svs.clients=&client;strcpy(sv.name,"seyda");
    player.v.mins[2]=-16.625f;player.v.origin[2]=38.625f;guard.v.origin[2]=22;
    AW_StoryReset(1);assert(AW_StoryTransition(AW_STAGE_DOCK));
    player.v.origin[0]=27;AW_OpeningTick();assert(aw_story.dock==10 && !speech && !AW_OpeningLocked());
    /* Exact 3-D source radius, not horizontal-only and not NPC feet to body centre. */
    player.v.origin[0]=26;player.v.origin[2]+=20;
    AW_OpeningTick();assert(aw_story.dock==10);player.v.origin[2]-=20;
    AW_OpeningTick();assert(aw_story.dock==30 && AW_OpeningLocked());
    assert(nav_stops==1 && !strcmp(line,"chargendock1") && !menu);
    for(i=0;i<20;i++)AW_OpeningTick();assert(!menu && aw_story.dock==30);
    speech=0;AW_OpeningTick();assert(menu==1 && aw_story.dock==40 && AW_OpeningLocked());
    done=1;menu=0;AW_OpeningTick();assert(aw_story.stage==AW_STAGE_OFFICE && AW_OpeningLocked());
    for(i=0;i<16;i++)AW_OpeningTick();assert(aw_story.dock==50 && !strcmp(line,"chargendock2") && AW_OpeningLocked());
    speech=0;AW_OpeningTick();assert(aw_story.dock==-1 && !AW_OpeningLocked() && nav_starts==2);
    assert(nav_goal[0]==299 && nav_goal[1]==-202);
    guard.v.angles[1]=10;nav_result=0;AW_OpeningTick();assert(guard.v.angles[1]==10);
    nav_result=1;AW_OpeningTick();assert(guard.v.angles[1]==225);
    for(i=0;i<5;i++)AW_OpeningTick();assert(nav_starts==2 && guard.v.angles[1]==225);
    assert(AW_StoryRestricted()); /* Race completion must not remove the enclosure. */
    for(i=0;i<70;i++)AW_OpeningTick();assert(!strcmp(line,"chargendock3"));
    /* Prompt and E share aim/range/visibility and the same stateful target. */
    {
        const char *name,*action;model_t door_model;
        sv.active=1;sv.num_edicts=3;strcpy(sv.name,"census");
        player.v.movetype=MOVETYPE_WALK;VectorCopy(vec3_origin,player.v.origin);
        player.v.view_ofs[2]=13;object.v.modelindex=1;
        object.v.absmin[0]=object.v.absmax[0]=30;
        object.v.absmin[2]=object.v.absmax[2]=13;
        reference._float=172859;
        assert(AW_OpeningHint(&name,&action) && !strcmp(action,"Read: E"));
        assert(AW_OpeningUse() && reads==1);
        cl.viewangles[1]=180;assert(!AW_OpeningHint(&name,&action) && !AW_OpeningUse());cl.viewangles[1]=0;
        occluded=1;assert(!AW_OpeningHint(&name,&action) && !AW_OpeningUse());occluded=0;
        object.v.modelindex=0;assert(!AW_OpeningHint(&name,&action));object.v.modelindex=1;
        player.v.origin[0]=-80;assert(!AW_OpeningHint(&name,&action));player.v.origin[0]=0;
        reference._float=172860;object.v.absmax[2]=145;assert(AW_OpeningHint(&name,&action) && strstr(action,"Locked"));
        aw_story.hall=1;assert(AW_OpeningHint(&name,&action) && !strcmp(action,"Open: E"));
        /* A rotated brush's broad-phase radius box can contain the eye even
         * though the actual door is ahead. Use its local bounds for targeting. */
        memset(&door_model,0,sizeof(door_model));door_model.type=mod_brush;
        door_model.mins[0]=-12;door_model.maxs[0]=12;
        door_model.mins[1]=-1;door_model.maxs[1]=1;
        door_model.mins[2]=0;door_model.maxs[2]=140;
        sv.models[1]=&door_model;object.v.origin[0]=30;object.v.angles[1]=90;
        object.v.absmin[0]=-40;object.v.absmax[0]=100;
        object.v.absmin[1]=-70;object.v.absmax[1]=70;
        object.v.absmin[2]=-70;object.v.absmax[2]=145;
        assert(AW_OpeningHint(&name,&action) && !strcmp(action,"Open: E"));
        obstructed=1;links=door_sounds=probes=0;
        assert(AW_OpeningUse() && !aw_story.hall_open && object.v.angles[1]==90);
        assert(!links && !door_sounds && probes==1);
        assert(player.v.origin[0]==0 && player.v.origin[1]==0 && player.v.origin[2]==0);
        assert(AW_OpeningHint(&name,&action) && !strcmp(action,"Open: E"));
        obstructed=0;
        assert(AW_OpeningUse() && aw_story.hall_open && !AW_OpeningHint(&name,&action));
        assert(links==1 && door_sounds==1 && object.v.angles[1]==-90);
        sv.models[1]=NULL;object.v.absmin[0]=object.v.absmax[0]=30;
        object.v.absmin[1]=object.v.absmax[1]=0;object.v.absmin[2]=13;
        reference._float=172851;object.v.absmax[2]=13;AW_StoryReset(0); /* No false empty outside tutorial stage. */
        assert(AW_OpeningHint(&name,&action) && !strcmp(action,"Take ring: E"));
        /* CHIM frame (CHIM-COURT-BARREL-USE-33): the barrel is drawn and collides as a chunk
         * placement (a world hit); its edict is a brush marker without faces. A world hit
         * inside the marker's linked box is the barrel itself; one in front of it occludes. */
        {
            model_t marker;edict_t world_edict;
            memset(&marker,0,sizeof(marker));marker.type=mod_brush;
            memset(&world_edict,0,sizeof(world_edict));sv.edicts=&world_edict;sv.models[1]=&marker;
            object.v.absmin[0]=28;object.v.absmax[0]=32;object.v.absmin[1]=-2;object.v.absmax[1]=2;
            object.v.absmin[2]=11;object.v.absmax[2]=15;
            world_hit=1;hit_pos[0]=28.5f;hit_pos[1]=0;hit_pos[2]=13;
            assert(AW_OpeningHint(&name,&action) && !strcmp(name,"Barrel") && !strcmp(action,"Take ring: E"));
            hit_pos[0]=20;assert(!AW_OpeningHint(&name,&action) && !AW_OpeningUse());
            hit_pos[0]=28.5f;marker.nummodelsurfaces=1;   /* a drawn brush (legacy maps): the plain rule */
            assert(!AW_OpeningHint(&name,&action));
            marker.nummodelsurfaces=0;
            /* Leaving the Census office: the courtyard frame (sncourt-chim) in stage COURTYARD. The
             * courtyard gate (113889) stays shut until the ring is taken; E on the barrel's marker
             * takes it, advances to CAPTAIN and opens the gate. */
            AW_StoryReset(1);aw_story.stage=AW_STAGE_COURTYARD;strcpy(sv.name,"seyda");
            assert(AW_CourtyardRingAvailable() && !AW_StoryDoor(113889));
            assert(AW_OpeningHint(&name,&action) && !strcmp(action,"Take ring: E"));
            assert(AW_OpeningUse() && AW_Ring()==1 && aw_story.stage==AW_STAGE_CAPTAIN);
            assert(AW_StoryDoor(113889) && !AW_CourtyardRingAvailable());
            assert(AW_OpeningHint(&name,&action) && !strcmp(action,"Empty"));
            AW_StoryReset(0);strcpy(sv.name,"census");
            world_hit=0;sv.models[1]=NULL;sv.edicts=NULL;
            object.v.absmin[0]=object.v.absmax[0]=30;object.v.absmin[1]=object.v.absmax[1]=0;
            object.v.absmin[2]=object.v.absmax[2]=13;
        }
        assert(AW_OpeningUse() && AW_Ring()==1);
        aw_story.stage=AW_STAGE_COURTYARD;AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",1);
        AW_OpeningTick();assert(aw_story.stage==AW_STAGE_CAPTAIN);
        assert(AW_ItemAdd(&aw_state,"ring_keley",-1));
        assert(AW_OpeningHint(&name,&action) && !strcmp(action,"Empty"));
        assert(AW_OpeningUse() && !AW_Ring());
        object.v.modelindex=0;clerk.v.modelindex=1;clerk.v.origin[0]=20;
        pr_strings="\0Socucius Ergalla";clerk.v.netname=1;AW_StoryReset(1);aw_story.stage=AW_STAGE_OFFICE;
        assert(AW_OpeningHint(&name,&action) && !strcmp(action,"Talk: E") && !strcmp(name,"Socucius Ergalla"));
        speech=0;assert(AW_OpeningUse() && aw_story.census==10);
        assert(!AW_OpeningHint(&name,&action));
    }
    return 0;
}
