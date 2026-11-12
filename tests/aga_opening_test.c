/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_activated.h"
#include "aw_hinged_door.h"
#include <assert.h>
server_t sv;server_static_t svs;double host_frametime=.1;
aw_character_t aw_character;char *pr_strings;
int pr_edict_size=sizeof(edict_t);client_state_t cl;
static edict_t object,clerk;static eval_t reference;static int occluded,reads;
static int obstructed,door_sounds,links,probes,world_hit;static vec3_t hit_pos;
static edict_t captain;extern cvar_t aw_census_type;
edict_t *EDICT_NUM(int n){return n==1?&object:n==3?&captain:&clerk;}
trace_t SV_Move(vec3_t a,vec3_t mi,vec3_t ma,vec3_t b,int type,edict_t *p){
 trace_t t;memset(&t,0,sizeof(t));t.fraction=occluded?.5f:1;
 if(world_hit){t.fraction=.5f;t.ent=sv.edicts;VectorCopy(hit_pos,t.endpos);}  /* a CHIM chunk placement */
 return t;
}
static edict_t guard;static int speech,menu,done,nav_stops,nav_starts,nav_result;
static vec3_t nav_goal;
static char line[32];
static int added;static char added_id[64];   /* the OnPCAdd hook's calls (aw_state.c aw_item_added) */
static void count_added(const char *id,int32_t count){(void)count;added++;strcpy(added_id,id);}
static int guard_role8;   /* the captain's edict stands in for the hall door guard */
edict_t *AW_IntroRole(int role){return role==5?&guard:role==6 && clerk.v.modelindex?&clerk:
    role==7 && captain.v.modelindex && !guard_role8?&captain:role==8 && guard_role8?&captain:NULL;}
int AW_NavLoad(const char *s){nav_stops++;return 1;}
int AW_NavStart(edict_t *e,vec3_t goal){nav_starts++;VectorCopy(goal,nav_goal);return 1;}
/* PIER-GUARD-WALKS-INTO-DOOR-65: the dock guard's two measured legs go straight, without the path grid */
int AW_NavStartDirect(edict_t *e,vec3_t goal){nav_starts++;VectorCopy(goal,nav_goal);return 1;}
int AW_NavStep(double dt,int wait){return nav_result;}
int AW_IntroSpeak(int role,const char *s){if(speech)return 0;strcpy(line,s);speech=1;return 1;}
double AW_SpeechRemaining(void){return speech;}
int AW_CharacterDone(void){int d=done;done=0;return d;}
int AW_CharacterOpen(int kind){menu=kind;return 1;}
int AW_ReaderActive(void){return 0;}
int AW_ReaderResult(void){return 0;}
int AW_ReaderOpen(const char *s,int n){reads++;return 1;}
void AW_UISubtitle(const char *a,const char *b,double t){}
/* OPENING-CAPTAIN-HINT-SUBTITLE-63: the captain hint is CharGenDialogueMessage's box with its Ok button */
static char box_text[256];static int box_buttons=-1;
void AW_MsgBoxShow(const char *text,const char *const *buttons,int count){
    strncpy(box_text,text,sizeof(box_text)-1);box_buttons=count && buttons && !strcmp(buttons[0],"Ok")?count:-1;}
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
    /* the old hand-written path (census type legacy) for the checks written for it; the census office's own
     * scripts (the default, 0) where a block says so (CENSUS-INTRO-SCRIPTS-62) */
    aw_census_type.value=1;
    /* Original camera unlock is after the papers instruction, not race
     * selection, office entry, or merely making the papers visible. */
    AW_StoryReset(1);
    for(i=AW_STAGE_SHIP;i<=AW_STAGE_PAPERS;i++){
        aw_story.stage=i;aw_story.census=30;
        assert(!AW_StoryViewAllowed());
    }
    aw_story.census=-1;assert(AW_StoryViewAllowed());
    aw_story.stage=AW_STAGE_COURTYARD;aw_story.census=0;
    assert(AW_StoryViewAllowed()); /* restore a later-stage save */
    AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1);
    aw_story.stage=AW_STAGE_RELEASED;assert(AW_StoryViewAllowed());
    AW_StoryReset(0);assert(AW_StoryViewAllowed()); /* diagnostic start */
    AW_StoryReset(1);assert(!AW_StoryViewAllowed()); /* new game relocks */
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
    /* PIER-GUARD-WALKS-INTO-DOOR-65 (the maintainer's design, 12 November 2026): after the race form he walks to a fixed
     * point in front of the census office door (320.7 -213.4), then steps aside to his post beside the door (286 -214),
     * both straight and measured from the door table; on arrival he faces the sea, the pier and the ship (native yaw
     * 225) and keeps it; while walking his facing is the travel's. Before (v0.0.54-v0.0.62 and rc2): one walk on the
     * path grid to 299 -202, whose nearest grid point is the door's corner, where he pushed against the door */
    assert(nav_goal[0]==320.7f && nav_goal[1]==-213.4f);
    guard.v.angles[1]=10;nav_result=0;AW_OpeningTick();assert(guard.v.angles[1]==10);
    nav_result=1;AW_OpeningTick();assert(nav_starts==2 && guard.v.angles[1]==10);   /* in front of the door */
    AW_OpeningTick();assert(nav_starts==3 && nav_goal[0]==286.f && nav_goal[1]==-214.f && guard.v.angles[1]==225);
    for(i=0;i<5;i++)AW_OpeningTick();assert(nav_starts==3 && guard.v.angles[1]==225);
    /* INTRO-DOCK-GUARD-BLOCKS-DOOR-62, by numbers: his box at the post (half widths 7.32 x 7.12, as the converted
     * actors') and the office door's box of the shipped door table (doors-seyda.txt 113893: 308.86..332.61,
     * -173.38..-149.62) do not overlap, and the space between them is wider than the player's box (2 x 7.32): the
     * player passes between him and the door */
    {float guard_top=nav_goal[1]+7.12f,door_bottom=-173.37754f,gap=door_bottom-guard_top;
     assert(gap>0 && gap>2*7.32f);}
    assert(AW_StoryRestricted()); /* Race completion must not remove the enclosure. */
    for(i=0;i<70;i++)AW_OpeningTick();assert(!strcmp(line,"chargendock3"));
    /* Prompt and E share aim/range/visibility and the same stateful target. */
    {
        const char *name,*action;
        sv.active=1;sv.num_edicts=3;strcpy(sv.name,"census");
        player.v.movetype=MOVETYPE_WALK;VectorCopy(vec3_origin,player.v.origin);
        player.v.view_ofs[2]=13;object.v.modelindex=1;
        object.v.absmin[0]=object.v.absmax[0]=30;
        object.v.absmin[2]=object.v.absmax[2]=13;
        reference._float=172859;aw_story.stage=AW_STAGE_PAPERS;
        assert(AW_StoryHudChannels()==AW_HUD_STATS);
        assert(AW_OpeningHint(&name,&action) && !strcmp(action,"Read: E"));
        assert(AW_OpeningUse() && reads==1);
        assert(!AW_Papers() && !AW_StoryFighting());
        assert(AW_StoryHudChannels()==(AW_HUD_STATS|AW_HUD_WEAPON));
        cl.viewangles[1]=180;assert(!AW_OpeningHint(&name,&action) && !AW_OpeningUse());cl.viewangles[1]=0;
        occluded=1;assert(!AW_OpeningHint(&name,&action) && !AW_OpeningUse());occluded=0;
        object.v.modelindex=0;assert(!AW_OpeningHint(&name,&action));object.v.modelindex=1;
        player.v.origin[0]=-80;assert(!AW_OpeningHint(&name,&action));player.v.origin[0]=0;
        /* The census hall door is a hinged door (aw_hinged_door.c, AW-20260928-12): the opening no longer aims
         * at it or uses it; its story hook holds the lock until the guard has unlocked it (aw_story.hall, the
         * original's CharGenDoorGuardTalker) and keeps whether it stands open (aw_story.hall_open, saved). */
        reference._float=AW_REF_CENSUS_HALL_DOOR;object.v.absmax[2]=145;
        aw_story.hall=0;assert(!AW_OpeningHint(&name,&action) && !AW_OpeningUse());
        assert(AW_OpeningHingedStory(AW_REF_CENSUS_HALL_DOOR,AW_HINGE_STORY_LOCK)==1);
        aw_story.hall=1;assert(!AW_OpeningHint(&name,&action) && !AW_OpeningUse());
        assert(AW_OpeningHingedStory(AW_REF_CENSUS_HALL_DOOR,AW_HINGE_STORY_LOCK)==0);
        assert(AW_OpeningHingedStory(397586,AW_HINGE_STORY_LOCK)==-1);	/* an ordinary door: no story rule */
        aw_story.hall_open=0;
        assert(AW_OpeningHingedStory(AW_REF_CENSUS_HALL_DOOR,AW_HINGE_STORY_OPEN)==1 && aw_story.hall_open);
        assert(AW_OpeningHingedStory(AW_REF_CENSUS_HALL_DOOR,AW_HINGE_STORY_SPAWN)==1);
        assert(AW_OpeningHingedStory(AW_REF_CENSUS_HALL_DOOR,AW_HINGE_STORY_CLOSED)==1 && !aw_story.hall_open);
        assert(AW_OpeningHingedStory(AW_REF_CENSUS_HALL_DOOR,AW_HINGE_STORY_SPAWN)==0);
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
        /* CENSUS-INTRO-SCRIPTS-62: Sellus Gravius talks through the dialogue window (his Greeting 1 and "duties"
         * answers with their result scripts), not the old hand-written box; the box only behind
         * census type legacy. The greeting's take of the papers, seen in his reach, records his state -1. */
        {
            int before=reads;
            aw_census_type.value=2;
            clerk.v.modelindex=0;sv.num_edicts=4;captain.v.modelindex=1;captain.v.netname=1;
            captain.v.origin[0]=20;captain.v.origin[2]=-14;
            /* OPENING-CAPTAIN-HINT-SUBTITLE-63: within 75 map units (300 original) the hint is CharGenDialogueMessage's
             * message box with its Ok button, once */
            AW_StoryReset(1);aw_story.stage=AW_STAGE_CAPTAIN;aw_story.census=-1;aw_story.captain_hint=0;box_buttons=-1;
            AW_OpeningTick();
            assert(aw_story.captain_hint==1 && box_buttons==1 && strstr(box_text,"talk to the Captain"));
            box_buttons=-1;AW_OpeningTick();assert(box_buttons==-1);
            AW_StoryReset(1);aw_story.stage=AW_STAGE_CAPTAIN;aw_story.census=-1;aw_story.captain_hint=1;
            assert(AW_ItemAdd(&aw_state,"chargen statssheet",1) && AW_Papers()==1);
            assert(!AW_CensusLegacy());
            assert(!AW_OpeningHint(&name,&action));
            assert(!AW_OpeningUse() && reads==before);
            aw_census_type.value=1;
            assert(AW_OpeningHint(&name,&action) && !strcmp(action,"Talk: E"));
            assert(AW_OpeningUse() && reads==before+1);
            aw_census_type.value=2;
            AW_OpeningTick();assert(aw_story.captain==0);              /* he has not taken them yet */
            assert(AW_ItemAdd(&aw_state,"chargen statssheet",-1));
            AW_OpeningTick();assert(aw_story.captain==-1);             /* Greeting 1: removeitem, state -1 */
            /* papers dropped away from him are not his greeting */
            AW_StoryReset(1);aw_story.stage=AW_STAGE_CAPTAIN;aw_story.census=-1;aw_story.captain_hint=1;
            captain.v.origin[0]=400;
            assert(AW_ItemAdd(&aw_state,"chargen statssheet",1));AW_OpeningTick();
            assert(AW_ItemAdd(&aw_state,"chargen statssheet",-1));AW_OpeningTick();
            assert(aw_story.captain==0);
            captain.v.modelindex=0;sv.num_edicts=3;
            /* the door guard (role 8) runs CharGenDoorGuardTalker: the opening says nothing for him and no longer
             * holds the hall door's lock (the door's own lock and his script's Unlock); on the old path it does */
            assert(AW_OpeningHingedStory(AW_REF_CENSUS_HALL_DOOR,AW_HINGE_STORY_LOCK)==-1);
            assert(AW_OpeningHingedStory(AW_REF_CENSUS_HALL_DOOR,AW_HINGE_STORY_REFUSED)==-1);
            AW_StoryReset(1);aw_story.stage=AW_STAGE_COURTYARD;speech=0;line[0]=0;
            captain.v.modelindex=1;captain.v.origin[0]=20;    /* standing in for him: AW_IntroRole(8) below */
            guard_role8=1;
            assert(AW_ItemAdd(&aw_state,"chargen statssheet",1));
            for(i=0;i<40;i++)AW_OpeningTick();
            assert(!aw_story.hall && !line[0]);
            aw_census_type.value=1;
            for(i=0;i<40 && !aw_story.hall;i++)AW_OpeningTick();
            assert(aw_story.hall && !strcmp(line,"chargen_door2"));
            assert(AW_OpeningHingedStory(AW_REF_CENSUS_HALL_DOOR,AW_HINGE_STORY_LOCK)==0);
            guard_role8=0;captain.v.modelindex=0;
        }
    }
    /* CENSUS-INTRO-SCRIPTS-62: the scripts' EnableInventoryMenu / EnableStatsMenu (one saved named fact, one row for
     * every menu, no row for a repeat; New Game clears it) add to the opening's rule; the clerk's script opens the
     * class window (the office's CLASS stage), the birth and review windows (no stage of their own) */
    {
        int rows;
        AW_StoryReset(1);aw_story.stage=AW_STAGE_OFFICE;
        assert(!AW_StoryInventoryAllowed() && !(AW_StoryHudChannels()&AW_HUD_STATS) && !AW_StoryMenus());
        rows=aw_state.count[AW_GLOBAL];
        assert(AW_StoryMenuEnable(AW_MENU_INVENTORY|AW_MENU_STATS) && aw_state.count[AW_GLOBAL]==rows+1);
        assert(AW_StoryMenuEnable(AW_MENU_STATS) && aw_state.count[AW_GLOBAL]==rows+1);
        assert(AW_StoryMenus()==(AW_MENU_INVENTORY|AW_MENU_STATS));
        assert(AW_StoryInventoryAllowed() && (AW_StoryHudChannels()&AW_HUD_STATS) && !(AW_StoryHudChannels()&AW_HUD_MAGIC));
        assert(AW_StoryMenuEnable(AW_MENU_MAGIC) && (AW_StoryHudChannels()&AW_HUD_MAGIC));
        /* EnableRest (v0.0.63, MWSCRIPT-GAPS-63): its own bit, kept with the others, cleared by New Game */
        assert(AW_StoryMenuEnable(AW_MENU_REST) && (AW_StoryMenus()&AW_MENU_REST) && AW_StoryRestricted());
        AW_StoryReset(1);assert(!AW_StoryMenus());
        menu=0;aw_story.stage=AW_STAGE_OFFICE;
        assert(AW_OpeningScriptMenu(2) && menu==2 && aw_story.stage==AW_STAGE_CLASS);
        assert(AW_OpeningScriptMenu(3) && menu==3 && aw_story.stage==AW_STAGE_CLASS);
        assert(AW_OpeningScriptMenu(4) && menu==4 && !AW_OpeningScriptMenu(5) && menu==4);
        /* EnableRaceMenu (v0.0.63, MWSCRIPT-GAPS-63): the race window opens; only on the ship or the dock does it make
         * the RACE stage (in the office the stage stays) */
        assert(AW_OpeningScriptMenu(1) && menu==1 && aw_story.stage==AW_STAGE_CLASS);
        menu=0;aw_story.stage=AW_STAGE_DOCK;
        assert(AW_OpeningScriptMenu(1) && menu==1 && aw_story.stage==AW_STAGE_RACE);
    }
    /* CENSUS-INTRO-SCRIPTS-62: the clerk runs CharGenClassNPC. The opening says nothing for him, does not lock the
     * player and does not aim at him; his script's windows move the stages on: class -> birth -> review -> papers,
     * the review's end restoring the new character's health and allowing the view. On the old path he speaks. */
    {
        const char *name,*action;
        aw_census_type.value=2;
        strcpy(sv.name,"census");sv.active=1;sv.num_edicts=3;object.v.modelindex=0;
        clerk.v.modelindex=1;clerk.v.origin[0]=15;clerk.v.origin[1]=0;clerk.v.origin[2]=0;
        player.v.origin[0]=player.v.origin[1]=0;player.v.origin[2]=0;player.v.movetype=MOVETYPE_WALK;
        AW_StoryReset(1);aw_story.stage=AW_STAGE_OFFICE;speech=0;line[0]=0;menu=0;
        for(i=0;i<10;i++)AW_OpeningTick();
        assert(aw_story.census==0 && !line[0] && !menu && !AW_OpeningLocked());
        assert(!AW_OpeningHint(&name,&action) && !AW_OpeningUse());
        assert(AW_OpeningScriptMenu(2) && aw_story.stage==AW_STAGE_CLASS);
        done=3;AW_OpeningTick();assert(aw_story.stage==AW_STAGE_CLASS);     /* not this window's result */
        done=2;AW_OpeningTick();assert(aw_story.stage==AW_STAGE_BIRTH);
        done=3;AW_OpeningTick();assert(aw_story.stage==AW_STAGE_REVIEW && !AW_StoryViewAllowed());
        aw_character.current[0]=55;player.v.health=1;
        done=4;AW_OpeningTick();
        assert(aw_story.stage==AW_STAGE_PAPERS && aw_story.census==-1 && player.v.health==55 && AW_StoryViewAllowed());
        assert(!line[0] && menu==2);   /* only the window his script opened; nothing said for him */
        /* the papers run CharGenStatsSheet: the opening does not aim at them; carried, they are the courtyard stage;
         * every gain of the player's inventory reaches the OnPCAdd hook, a copy's does not */
        clerk.v.modelindex=0;object.v.modelindex=1;reference._float=AW_REF_CENSUS_PAPERS;
        object.v.absmin[0]=object.v.absmax[0]=30;object.v.absmin[1]=object.v.absmax[1]=0;
        object.v.absmin[2]=object.v.absmax[2]=13;player.v.view_ofs[2]=13;cl.viewangles[1]=0;
        assert(!AW_OpeningHint(&name,&action) && !AW_OpeningUse());
        aw_item_added=count_added;added=0;
        {aw_state_t copy=aw_state;assert(AW_ItemAdd(&copy,"chargen statssheet",1) && added==0);}
        assert(AW_ItemAdd(&aw_state,"chargen statssheet",1) && added==1 && !strcmp(added_id,"chargen statssheet"));
        assert(AW_ItemAdd(&aw_state,"chargen statssheet",-1) && added==1);
        assert(AW_ItemAdd(&aw_state,"Chargen StatsSheet",1) && added==2 && !strcmp(added_id,"chargen statssheet"));
        aw_item_added=NULL;
        AW_OpeningTick();assert(aw_story.stage==AW_STAGE_COURTYARD);
        aw_census_type.value=1;
        assert(AW_ItemAdd(&aw_state,"chargen statssheet",-1));
        AW_StoryReset(1);aw_story.stage=AW_STAGE_PAPERS;
        assert(AW_OpeningHint(&name,&action) && !strcmp(action,"Read: E"));
        aw_census_type.value=2;object.v.modelindex=0;clerk.v.modelindex=1;
        AW_StoryReset(1);aw_story.stage=AW_STAGE_OFFICE;
        aw_census_type.value=1;
        AW_StoryReset(1);aw_story.stage=AW_STAGE_OFFICE;speech=0;
        AW_OpeningTick();assert(aw_story.census==10 && !strcmp(line,"chargen_class1"));
        clerk.v.modelindex=0;speech=0;
    }
    /* An old full global table cannot silently lose the activation permission.
     * Refuse recording, retain all state, and do not admit an earlier stage. */
    {
        aw_state_t prior;char key[32];
        AW_StoryReset(1);assert(!AW_StoryPapersRead());
        aw_story.stage=AW_STAGE_PAPERS;
        for(i=aw_state.count[AW_GLOBAL];i<AW_STATE_VALUES;i++){
            sprintf(key,"full%d",i);assert(AW_StateSet(&aw_state,AW_GLOBAL,key,1));
        }
        prior=aw_state;assert(!AW_StoryPapersRead());assert(!memcmp(&prior,&aw_state,sizeof(prior)));
        assert(AW_StoryHudChannels()==AW_HUD_STATS);
        object.v.modelindex=1;clerk.v.modelindex=0;reference._float=172859;
        {int before_reads=reads;assert(AW_OpeningUse());assert(reads==before_reads);}
        assert(!memcmp(&prior,&aw_state,sizeof(prior)));
        AW_StoryReset(0);assert(AW_StoryPapersRead() && AW_StoryHudChannels()==AW_HUD_ALL);
    }
    return 0;
}
