/* SPDX-License-Identifier: GPL-2.0-or-later
 * Bounded adapters for audited opening scripts. Each actor retains its own
 * state/timers; speech completion, menus and movement are separate gates. */
#include "quakedef.h"
#include "aw_links.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_activated.h"
#include "aw_hinged_door.h"
#include "aw_msgbox.h"
/* OPENING-TUTORIAL-KEYS-65 (aw_textdef.c sets it): SOURCE's text defines filled in with the bound keys; NULL in fixtures */
int (*aw_opening_defines)(const char *source,char *out,int capacity);
static int route_started,route_failed,route_done;
static int post_retries;static double post_retry;   /* the walk to his post tried again (OPENING-REGRESSION-64) */
/* PIER-GUARD-WALKS-INTO-DOOR-65 (the maintainer's design, 12 November 2026): after the race form the dock guard walks to a
 * fixed point in front of the census office door, then steps aside to the side of the door and faces the sea, the pier
 * and the ship; never a straight line from wherever he met the player (from further down the pier that line ran into the
 * door frame and he pushed against it for half a minute). The points come from the built door table, seyda census
 * 113893 (doors-seyda.txt: box x 308.86..332.61, y -173.38..-149.62, map units): FRONT is the door's middle, 40 units out
 * from its face; POST is a straight step aside from it, left of the door, far enough that a player walking up the door's
 * middle passes him (his half width 16 plus the player's 16). Measured in the emulator 12 November 2026 (v0.0.65-rc3
 * test engine): nearer the wall (276 -191) the step aside stuck at 289 -200 on the wall's corner left of the door.
 * tests/test_pier_guard_route.py keeps these numbers to the door row. */
#define AW_PIER_GUARD_FRONT_X 320.7f
#define AW_PIER_GUARD_FRONT_Y -213.4f
#define AW_PIER_GUARD_POST_X 286.0f
#define AW_PIER_GUARD_POST_Y -214.0f
static int post_leg;   /* 0: to the point in front of the door, 1: aside to the post */
/* the player's use of a placed reference as E gives it (aw_mwhost.c: its script's OnActivate); 1 when taken */
int (*aw_opening_activate)(unsigned reference);
/* CENSUS-INTRO-SCRIPTS-62: Sellus Gravius ("chargen captain") talks through the ordinary dialogue window, as in the
 * original: his Greeting 1 result takes the papers ("player->removeitem chargen statssheet" and his local state -1)
 * and his "duties" answer gives the package, the directions, 87 gold and journal A1_1_FindSpymaster 1. The project's
 * early hand-written box (reading/captain_greeting, captain_duties: "Enter: Duties") is kept only behind this switch,
 * off by default, for an A/B of the old path. */
/* OPENING-REGRESSION-64: the census office's registration is ONE setting, "census type" (aw_census_type, not saved, set
 * before the office loads): 0 amiwind (the default): the original's scripts (the clerk's menus, the papers, the
 * tutorial items, the door guard, the courtyard, Sellus Gravius, the doors) with AmiWind's own registration around
 * them: the clerk turns to the player and starts his talk as the player walks up, the player is held from then until
 * the stat review is done, his lines show in the speech box (aw_mwhost.c host_say), nothing in the office is taken or
 * used before the class and birthsign (aw_scene.c AW_SceneUse); 1 legacy: the project's earlier hand-written
 * registration; 2 original: the original's scripts alone (the v0.0.62-v0.0.64 default). "census legacy 0/1" (the
 * console command aw_census_legacy) stays as an alias: 1 = legacy, 0 = original. */
cvar_t aw_census_type={"aw_census_type","0"};   /* registered in aw_debug.c */
int AW_CensusType(void){int t=(int)aw_census_type.value;return t<0 || t>2?0:t;}
int AW_CensusLegacy(void){return AW_CensusType()==1;}
int AW_CensusAmiwind(void){return AW_CensusType()==0;}
static const char *const census_type_names[]={"amiwind","legacy","original"};
void AW_CensusTypeCommand(void){
    int i;
    if(Cmd_Argc()<2){Con_Printf("census type %d (%s): 0 amiwind, 1 legacy, 2 original\n",AW_CensusType(),
                                census_type_names[AW_CensusType()]);return;}
    for(i=0;i<3;i++)if(!Q_strcasecmp(Cmd_Argv(1),(char *)census_type_names[i]))break;
    if(i==3)i=Q_atoi(Cmd_Argv(1));
    if(i<0 || i>2){Con_Printf("census type: 0 amiwind, 1 legacy, 2 original\n");return;}
    Cvar_SetValue("aw_census_type",(float)i);
}
/* census type amiwind: in the census office nothing is taken or used before the papers' stage (the clerk's class,
 * birthsign and stat review done); aw_inventory.c placed_use asks this through aw_census_take_refused */
int AW_OpeningTakeRefused(void){
    return AW_CensusAmiwind() && AW_StoryRestricted() && sv.active && !strcmp(sv.name,"census") &&
           aw_story.stage<AW_STAGE_PAPERS;
}
void AW_CensusLegacyCommand(void){
    if(Cmd_Argc()<2){Con_Printf("census legacy %d (census type %s)\n",AW_CensusLegacy(),census_type_names[AW_CensusType()]);return;}
    Cvar_SetValue("aw_census_type",Q_atoi(Cmd_Argv(1))?1.f:2.f);
}
/* EnableClassMenu / EnableBirthMenu / EnableStatReviewMenu of the clerk's script (CharGenClassNPC; aw_mwhost.c host
 * call): KIND 2, 3, 4 as AW_CharacterOpen takes them. The class window opening is the office's CLASS stage, as the
 * old path's census step 10 made it; the windows' results move the stages on in AW_OpeningTick. 1 opened. */
int AW_OpeningScriptMenu(int kind)
{
    if(kind<1 || kind>4 || !AW_CharacterOpen(kind))return 0;
    /* EnableRaceMenu (v0.0.63, MWSCRIPT-GAPS-63; CharGenRaceNPC): the race window is the dock's RACE stage, as the
     * hand-written dock step 30 makes it */
    if(kind==1 && (aw_story.stage==AW_STAGE_SHIP || aw_story.stage==AW_STAGE_DOCK))AW_StoryTransition(AW_STAGE_RACE);
    if(kind==2 && aw_story.stage==AW_STAGE_OFFICE)AW_StoryTransition(AW_STAGE_CLASS);
    return 1;
}
/* The captain is an intro role only on the old path; on the new one he is an ordinary speaker (aw_talk.c, world.qc,
 * aw_scene.c read aw_intro_role) bound to role 7 by his record id for the distance rules below. */
static const char *const captain_hint_ok[]={"Ok"};   /* CharGenDialogueMessage's button */
static int captain_papers=-1;   /* the papers carried at the last tick in his reach: the greeting's take is seen */
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
    /* The final post is left of the door when approaching from the pier.
     * Leave the doorway clear and face southeast, out toward the docks. */
    /* CharGenRaceNPC's own two AITravel points (state 0: -8914 -73093, before the plank; state 50: -9944 -72481, next
     * to the door), in the dock map's units; the second was moved left of the door for INTRO-DOCK-GUARD-BLOCKS-DOOR-62
     * and was the script's own in v0.0.63 (the parity check). OPENING-REGRESSION-64: AmiWind's own post is back, as
     * it stood through v0.0.54-v0.0.62 (decided for the project 11 November 2026): 299 -202, left of the door, the
     * doorway clear, facing the dock (yaw 225, set at arrival below) */
    /* PIER-GUARD-WALKS-INTO-DOOR-65: the second walk in two legs, the point in front of the door, then the post */
    goal[0]=second?(post_leg?AW_PIER_GUARD_POST_X:AW_PIER_GUARD_FRONT_X):(-8914.f+11264)*.25f;
    goal[1]=second?(post_leg?AW_PIER_GUARD_POST_Y:AW_PIER_GUARD_FRONT_Y):(-73093.f+71680)*.25f;goal[2]=31.5f;
    /* PIER-GUARD-WALKS-INTO-DOOR-65: the step aside goes straight from the front point to the post (both measured, the
     * line clear of the door); the path grid's nearest point to the post is the door's corner (338 -178), where he
     * stood pushing */
    /* both legs of the second walk go straight (measured, 12 November 2026): on the grid the first leg aimed at the grid
     * point beside the plank (556 -337), where the player stands after the race, and he pushed against the player */
    route_started=second?AW_NavStartDirect(AW_IntroRole(5),goal):AW_NavStart(AW_IntroRole(5),goal);
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
/* The rule for "aw_story_hidden" below, for CHIM placements flagged story
 * hidden (chim/chim_chunks.c, world format 0.5). */
int AW_OpeningStoryHidden(void)
{
    return sv.active && !strcmp(sv.name,"seyda") && aw_story.ship_disabled;
}
void AW_OpeningSpawn(void)
{
    int i,reference;edict_t *e;eval_t *v;
    route_started=route_failed=route_done=0;captain_papers=-1;post_retries=0;post_retry=0;post_leg=0;
    if(aw_story.stage==AW_STAGE_DEMO)return;
    if(!strcmp(sv.name,"census") && aw_story.stage>=AW_STAGE_OFFICE)aw_story.ship_disabled=1;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free)continue;
        v=GetEdictFieldValue(e,"aw_ref");reference=v?(int)v->_float:0;
        v=GetEdictFieldValue(e,"aw_story_hidden");
        if(!strcmp(sv.name,"seyda") && aw_story.ship_disabled && v && v->_float)hide(e);
        if(!strcmp(sv.name,"census")){
            if(reference==AW_REF_CENSUS_PAPERS && (aw_story.stage<AW_STAGE_PAPERS || AW_Papers() || aw_story.captain))hide(e);
            /* The hall door is a hinged door (aw_hinged_door.c); its pose comes back from hall_open through
             * the story hook below (AW_HINGE_STORY_SPAWN). */
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
        if(v && (int)v->_float==AW_REF_CENSUS_PAPERS){e->v.modelindex=SV_ModelIndex(pr_strings+e->v.model);e->v.solid=SOLID_BSP;SV_LinkEdict(e,false);}
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
            aw_story.dock=-1;route_started=route_failed=route_done=0;post_leg=0;dock_route(1);IN_AWClearButtons();
        }else if(aw_story.dock==-1){
            /* OPENING-REGRESSION-64: a walk to his post held up (the player standing in his way after the race
             * menu: a plain travel does not wait for the player, nav.c) is tried again after a short pause instead
             * of leaving him on the pier for good; the post beside the door is where CharGenRaceNPC's AITravel ends */
            if(route_failed && !route_done && post_retries<30){post_retry+=dt;if(post_retry>2){post_retry=0;post_retries++;route_failed=0;}}
            if(!route_started && !route_failed && !route_done)dock_route(1);
            if(route_started && !route_failed){result=AW_NavStep(dt,0);
                if(result>0 && !post_leg){
                    /* PIER-GUARD-WALKS-INTO-DOOR-65: in front of the door; the next tick starts the step aside */
                    route_started=0;post_leg=1;post_retries=0;
                }else if(result>0){
                    /* at his post he faces the dock (AmiWind's opening through v0.0.62, restored 11 November 2026):
                     * converted actors face local +Y, so native yaw 225 faces the dock at world yaw 315 */
                    edict_t *g=AW_IntroRole(5);
                    route_started=0;route_done=1;
                    if(g){g->v.angles[1]=225;SV_LinkEdict(g,false);}
                }
                else if(result<0 && !post_leg){
                    /* PIER-GUARD-WALKS-INTO-DOOR-65: the front of the door taken (the player stands there): he steps
                     * aside to his post at once instead of pushing toward it */
                    route_started=0;post_leg=1;post_retries=0;Con_Printf("Dock guard: the front of the door is taken; to the post.\n");
                }
                else if(result<0){route_started=0;route_failed=1;Con_Printf("Dock guard post blocked.\n");}}
            if(near_actor(5)<37.5 && AW_SpeechRemaining()<=0){
                aw_story.dock_timer+=dt;
                if(aw_story.dock_timer>6 && AW_IntroSpeak(5,"chargendock3"))aw_story.dock_timer=0;
            }
            /* at his post he stands as the travel left him (the script's AITravel sets no facing; the forced face toward
             * the pier went with the script's own post in v0.0.63) and does not keep following the player */
        }
    }
    if(strcmp(sv.name,"census") || aw_story.stage<AW_STAGE_OFFICE)return 0;
    if(!aw_story.captain_hint && near_actor(7)<75){   /* CharGenDialogueMessage: GetDistance Player < 300 */
        aw_story.captain_hint=1;
        /* CharGenDialogueMessage's own message box with its Ok button (OPENING-CAPTAIN-HINT-SUBTITLE-63) */
        /* OPENING-TUTORIAL-KEYS-65: the bound activate key, not a fixed E (the box fills ^ActionActivate in) */
        AW_MsgBoxShow("Press ^ActionActivate to talk to the Captain. Select topics to ask about them. Don't try persuasion on him. "
                      "If you're not good at it, he will start to dislike you.",captain_hint_ok,1);
    }
    if(!AW_CensusLegacy() && aw_story.stage>=AW_STAGE_CAPTAIN && !aw_story.captain){
        /* his greeting's result took the papers (Greeting 1: removeitem "chargen statssheet", set state to -1) */
        int papers=AW_Papers();
        if(near_actor(7)>=75)captain_papers=-1;
        else{if(captain_papers>0 && papers==0)aw_story.captain=-1;captain_papers=papers;}
    }
    if(AW_CensusAmiwind()){
        /* census type amiwind (OPENING-REGRESSION-64): as AmiWind's registration played, the clerk starts his talk by
         * himself when the player walks up (the hand-written path's 25 units), through his own script's activation
         * (CharGenClassNPC's OnActivate, as E would), turns to the player and holds him there (AW_OpeningLocked:
         * census 10) until the stat review is done (census -1 below) */
        edict_t *clerk=AW_IntroRole(6);
        if(clerk && aw_story.stage==AW_STAGE_OFFICE && aw_story.census==0 && near_actor(6)<25 && aw_opening_activate){
            eval_t *r=GetEdictFieldValue(clerk,"aw_ref");
            if(r && r->_float>0 && aw_opening_activate((unsigned)r->_float))aw_story.census=10;
        }
        /* his own script may start first (CharGenClassNPC's GetDistance Player < 100): the hold and the facing
         * follow it as well, from his class window on until the review is done */
        if(aw_story.census==0 && aw_story.stage>=AW_STAGE_CLASS && aw_story.stage<AW_STAGE_PAPERS)aw_story.census=10;
        if(clerk && aw_story.census==10){
            edict_t *p=svs.clients[0].edict;
            clerk->v.angles[1]=Q_atan2(p->v.origin[1]-clerk->v.origin[1],p->v.origin[0]-clerk->v.origin[0])*180/M_PI-90;
        }
    }
    if(!AW_CensusLegacy()){
        /* the clerk runs his own script (CharGenClassNPC: his lines, EnableClassMenu / -BirthMenu / -StatReviewMenu,
         * the papers shown, the menus and controls turned on). The windows' results move the office's stages on, as
         * the old path's steps did, and the review's end restores the new character's health and shows the papers */
        if(done==2 && aw_story.stage==AW_STAGE_CLASS)AW_StoryTransition(AW_STAGE_BIRTH);
        else if(done==3 && aw_story.stage==AW_STAGE_BIRTH)AW_StoryTransition(AW_STAGE_REVIEW);
        else if(done==4 && aw_story.stage==AW_STAGE_REVIEW && AW_StoryTransition(AW_STAGE_PAPERS)){
            show_papers();aw_story.census=-1;
            svs.clients[0].edict->v.health=aw_character.current[0];
        }
        /* the papers taken (through their own script's Activate): the courtyard stage, as the old reader's Take */
        else if(aw_story.stage==AW_STAGE_PAPERS && AW_Papers())AW_StoryTransition(AW_STAGE_COURTYARD);
    }
    else if(aw_story.census==0 && near_actor(6)<25 && AW_IntroSpeak(6,"chargen_class1"))aw_story.census=10;
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
        if(aw_story.census_timer>1){
            /* OPENING-TUTORIAL-KEYS-65: the bound activate key (the text defines, aw_textdef.c), E only without them */
            static char line[96];const char *say="E: read your papers, then take them to the captain.";
            if(aw_opening_defines && aw_opening_defines("^ActionActivate: read your papers, then take them to the captain.",
                                                        line,sizeof(line)))say=line;
            AW_UISubtitle("Registration",say,8);aw_story.census=-1;aw_story.census_timer=0;
        }
    }else if(aw_story.census==-1 && !AW_Papers() && !aw_story.captain && near_actor(6)<45 && AW_SpeechRemaining()<=0){
        aw_story.census_timer+=dt;
        if(aw_story.census_timer>5 && AW_IntroSpeak(6,"chargen_class4"))aw_story.census_timer=0;
    }
    /* the door guard: his own script (CharGenDoorGuardTalker: his lines, the hall door's Unlock) unless the old path */
    if(AW_CensusLegacy() && !aw_story.hall && near_actor(8)<45 && AW_SpeechRemaining()<=0){
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
 * retain their separate proximity triggers above. The census hall door is not
 * here: it is a hinged door (aw_hinged_door.c) whose lock the story holds
 * (AW_OpeningHingedStory below). */
/* On a CHIM frame the object's drawn shape and collision are a chunk
 * placement; its edict (kept by the frame map for every AW_REF_ in
 * aw_activated.h) is a brush model without faces that only marks where it
 * is. A world hit inside such an edict's linked box is the object itself,
 * not something in front of it. Edicts with drawn faces (legacy maps) keep
 * the plain rule. */
static int own_surface(edict_t *e,trace_t *tr)
{
    int k;model_t *m=sv.models[(int)e->v.modelindex];
    if(!tr->ent || tr->ent!=sv.edicts || !m || m->type!=mod_brush || m->nummodelsurfaces)return 0;
    for(k=0;k<3;k++)if(tr->endpos[k]<e->v.absmin[k] || tr->endpos[k]>e->v.absmax[k])return 0;
    return 1;
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
        /* the census office's people run their own scripts and talk through the dialogue window (role 7 the captain,
         * 8 the door guard; CENSUS-INTRO-SCRIPTS-62) unless the old path */
        if(role && !AW_CensusLegacy())continue;   /* 6 the clerk too */
        if(role){
            if(!AW_StoryRestricted() || strcmp(sv.name,"census") || near_actor(role)>=48 ||
               (role==6 && aw_story.census!=0) || (role==7 && aw_story.stage!=AW_STAGE_CAPTAIN))continue;
            VectorCopy(e->v.origin,point);point[2]+=27;
        }else{
            if(ref!=AW_REF_CENSUS_PAPERS && ref!=AW_REF_COURTYARD_BARREL)continue;
            /* the papers run their own script (CharGenStatsSheet: the use, the reader with Take, OnPCAdd's messages)
             * unless the old path; the courtyard barrel's ring stays the opening's (the ring's own script follows) */
            if(ref==AW_REF_CENSUS_PAPERS && !AW_CensusLegacy())continue;
            VectorAdd(e->v.absmin,e->v.absmax,point);VectorScale(point,.5f,point);
        }
        VectorSubtract(point,eye,delta);distance=Length(delta);
        if(distance<.1f || distance>=best || distance>=49 || DotProduct(delta,forward)/distance<.65f)continue;
        tr=SV_Move(eye,vec3_origin,vec3_origin,point,MOVE_NORMAL,p);
        if(tr.startsolid || (tr.fraction<1 && tr.ent!=e && !own_surface(e,&tr)))continue;
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
    if(ref==AW_REF_CENSUS_PAPERS){*name="Identification papers";*action="Read: E";}
    else{*name="Barrel";*action=AW_CourtyardRingAvailable()?"Take ring: E":"Empty";}
    return 1;
}
/* The census hall door (AW_REF_CENSUS_HALL_DOOR, DOOR "chargen door hall": lock level 100, no
 * key, no script) is an ordinary hinged door (aw_hinged_door.c) whose lock
 * the story holds, as in the original: the door guard's script
 * CharGenDoorGuardTalker unlocks it ("CharGen Door Hall"->Unlock) once the
 * player carries the papers (CharGen StatsSheet) and he has said
 * "chargen_door2"; here that is aw_story.hall (set where he speaks it, below
 * and in the proximity rule above). Until then the use key plays the locked
 * sound and says why; after it the door turns like every hinged door (90
 * degrees in one second, its record's sounds, holding against the player).
 * Whether it stands open is kept in aw_story.hall_open (saved), so a loaded
 * game or a census map loaded again shows it as it was left. */
int AW_OpeningHingedStory(unsigned ref,int event)
{
    if(ref!=AW_REF_CENSUS_HALL_DOOR)return -1;
    switch(event){
    /* the door's own lock (its record: level 100, no key) and the guard script's Unlock, unless the old path */
    case AW_HINGE_STORY_LOCK:return AW_CensusLegacy()?(aw_story.hall?0:1):-1;
    case AW_HINGE_STORY_REFUSED:
        if(!AW_CensusLegacy())return -1;
        AW_UISubtitle("","The door is locked. Show your papers to the guard.",4);
        return 1;
    case AW_HINGE_STORY_OPEN:aw_story.hall_open=1;return 1;
    case AW_HINGE_STORY_CLOSED:aw_story.hall_open=0;return 1;
    case AW_HINGE_STORY_SPAWN:return aw_story.hall_open?1:0;
    }
    return -1;
}
int AW_OpeningUse(void)
{
    edict_t *target=opening_target();eval_t *v;int ref;
    if(!target)return 0;
    if(target==AW_IntroRole(6)){
        if(AW_IntroSpeak(6,"chargen_class1"))aw_story.census=10;
        return 1;
    }
    if(target==AW_IntroRole(7)){   /* only on the old path: opening_target skips him otherwise */
        if(AW_Papers() || aw_story.captain)AW_ReaderOpen("captain_greeting",2);
        else AW_UISubtitle("Sellus Gravius","Bring your identification papers.",4);
        return 1;
    }
    if(target==AW_IntroRole(8)){
        if(AW_IntroSpeak(8,AW_Papers() || aw_story.hall?"chargen_door2":"chargen_door1") && AW_Papers())aw_story.hall=1;
        return 1;
    }
    v=GetEdictFieldValue(target,"aw_ref");ref=(int)v->_float;
    if(ref==AW_REF_CENSUS_PAPERS){
        if(!AW_StoryPapersRead()){
            AW_UISubtitle("","Cannot record registration. Papers retained.",4);return 1;
        }
        AW_ReaderOpen("papers",1);return 1;
    }
    if(AW_CourtyardRingAvailable()){
        if(AW_CourtyardTakeRing()){
            if(aw_story.stage==AW_STAGE_COURTYARD)AW_StoryTransition(AW_STAGE_CAPTAIN);
            AW_UISubtitle("Barrel","Engraved Ring of Healing taken.",5);
        }else AW_UISubtitle("Barrel","Could not take the ring. Contents retained.",4);
    }else AW_UISubtitle("Barrel","Empty.",3);
    return 1;
}
