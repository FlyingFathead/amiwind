/* SPDX-License-Identifier: GPL-2.0-or-later
 * Small native adapter for the original introductory ship scripts. Original
 * voices, subtitles and navigation are supplied only by private conversion.
 */
#include "quakedef.h"
static int active,pending,jiub_state,guard_state,upper_state,prompt,unlocked,failed;
static double elapsed,jiub_timer,guard_timer,upper_timer,deck_timer;
static int deck_state;
static char player_name[32];
static edict_t *roles[9];
static edict_t *player(void){return svs.clients[0].edict;}
static float distance(edict_t *a,edict_t *b){vec3_t d;VectorSubtract(a->v.origin,b->v.origin,d);return Length(d);}
static void face(edict_t *actor){vec3_t d;VectorSubtract(player()->v.origin,actor->v.origin,d);actor->v.angles[1]=atan2(d[1],d[0])*180/M_PI-90;}
static int say(int role,const char *stem) {
    FILE *f=NULL;char path[96],text[2048];int n;sfx_t *sound;edict_t *actor=roles[role];double duration;
    if(!actor || AW_SpeechRemaining()>0)return 0;
    sprintf(path,"intro/%s.txt",stem);n=COM_FOpenFile(path,&f);
    if(!f)return -1;
    if(n<1 || n>sizeof(text) || fread(text,1,n,f)!=n || text[n-1]){fclose(f);return -1;}fclose(f);
    sprintf(path,"intro/%s.wav",stem);sound=S_PrecacheSound(path);if(!sound)return -1;
    face(actor);S_StartSound(NUM_FOR_EDICT(actor),2,sound,actor->v.origin,.9,1);
    duration=AW_SpeechRemaining();if(duration<=0)return -1;
    AW_UISubtitle(pr_strings+actor->v.netname,text,duration);
    Con_Printf("Intro speech: %s (%ld ms)\n",stem,(long)(duration*1000));return 1;
}
static void failure(const char *reason) {
    failed=1;unlocked=1;prompt=0;
    Con_Printf("Intro stopped: %s. Movement unlocked for inspection.\n",reason);
    AW_UISubtitle("Intro checkpoint",reason,12);
}
static int speak(int role,const char *stem) {
    int result=say(role,stem);if(result<0)failure("Required speech asset unavailable");return result>0;
}
static int travel(float x,float y,float z) {
    vec3_t goal;goal[0]=x*.25;goal[1]=y*.25;goal[2]=z*.25;
    if(!AW_NavStart(roles[2],goal)){failure("No connected guard route");return 0;}return 1;
}
void AW_IntroBegin(void) {
    pending=1;active=0;deck_state=0;deck_timer=0;IN_AWClearButtons();key_dest=key_game;
    if(!AW_MusicStartTrack(4))Con_Printf("Selected opening track unavailable.\n");
    Cbuf_AddText("map prison\n");
}
static void new_game(void) {
    FILE *f=NULL;
    if(COM_FOpenFile("intro/chargenname1.txt",&f)<0 || !f){Con_Printf("Convert owned introductory assets before starting a new game.\n");return;}
    fclose(f);active=prompt=pending=0;CL_Disconnect();
    IN_AWClearButtons();key_dest=key_game;
    if(!AW_MovieStart())AW_IntroBegin();
}
void AW_IntroSpawn(void) {
    int i,role;edict_t *e;eval_t *v;vec3_t start={15.25,-33.75,22.875};
    /* Entity pointers belong to the current map. Rebind even after the ship
     * adapter ends; keep the deck guard's local state across door round trips. */
    memset(roles,0,sizeof(roles));
    for(i=1;i<sv.num_edicts;i++){e=EDICT_NUM(i);if(e->free)continue;v=GetEdictFieldValue(e,"aw_intro_role");role=v?(int)v->_float:0;
        if(role>0 && role<9)roles[role]=e;}
    if(!pending){active=prompt=0;return;}
    pending=0;active=1;jiub_state=guard_state=upper_state=prompt=unlocked=failed=0;elapsed=jiub_timer=guard_timer=upper_timer=0;
    player_name[0]=0;
    if(strcmp(sv.name,"prison") || !roles[1] || !roles[2] || !AW_NavLoad("prison")){failure("Required ship actors or path grid unavailable");return;}
    if(!AW_InteriorPlace(player(),start)){failure("Original starting position blocked");return;}
    player()->v.angles[0]=0;player()->v.angles[1]=110;player()->v.angles[2]=0;player()->v.fixangle=1;
    Con_Printf("Ship intro started: original name/escort script adapter.\n");
}
void AW_IntroTick(void) {
    double dt;int result;
    if(!sv.active || sv.paused || key_dest!=key_game)return;
    if(!strcmp(sv.name,"seyda") && roles[4]){
        /* CharGenBoatNPC: timer advances only nearby, after speech ends. */
        if(distance(roles[4],player())<45 && AW_SpeechRemaining()<=0){
            if(!deck_state){if(say(4,"chargenboat1")>0){deck_state=10;deck_timer=0;}}
            else {
                deck_timer+=host_frametime;
                if(deck_timer>6 && say(4,"chargenboat2")>0)deck_timer=0;
            }
        }
        return;
    }
    if(!active || failed || strcmp(sv.name,"prison") || prompt)return;
    dt=host_frametime;if(dt>.1)dt=.1;elapsed+=dt;jiub_timer+=dt;guard_timer+=dt;upper_timer+=dt;
    if(jiub_state==0 && jiub_timer>=1 && speak(1,"chargenname1")){jiub_state=10;jiub_timer=0;}
    else if(jiub_state==10 && AW_SpeechRemaining()<=0){prompt=1;IN_AWClearButtons();}
    else if(jiub_state==20 && jiub_timer>=1 && speak(1,"chargenname2")){jiub_state=40;jiub_timer=0;}
    else if(jiub_state==40 && distance(roles[1],roles[2])<=100 && speak(1,"chargenname3")){jiub_state=50;jiub_timer=5;}
    else if(jiub_state==50 && jiub_timer>14 && distance(roles[1],player())<37.5 && speak(1,"chargenname4"))jiub_timer=0;
    if(guard_state==0 && guard_timer>8 && travel(90,-90,-88)){guard_state=10;guard_timer=0;}
    else if(guard_state==10 || guard_state==50 || guard_state==57){
        result=AW_NavStep(dt,guard_state==50);
        if(result<0){failure("Guard route blocked; inspect collision before continuing");return;}
        if(result>0){if(guard_state==10)guard_state=20;
            else if(guard_state==50){if(travel(185,174,170))guard_state=57;}
            else guard_state=60;}
    }else if(guard_state==20 && jiub_state>=50 && speak(2,"chargenwalk1"))guard_state=30;
    else if(guard_state==30 && AW_SpeechRemaining()<=0){prompt=2;IN_AWClearButtons();}
    else if(guard_state==60 && distance(roles[2],player())<=50 && speak(2,"chargenwalk2")){guard_state=70;guard_timer=0;}
    else if(guard_state==70 && guard_timer>6 && distance(roles[2],player())<37.5 && speak(2,"chargenwalk3"))guard_timer=0;
    if(unlocked && roles[3] && distance(roles[3],player())<45 && (!upper_state || upper_timer>6) &&
       speak(3,upper_state?"chargenwoman2":"chargenwoman1")){upper_state=1;upper_timer=0;}
}
void AW_IntroMove(usercmd_t *cmd) {
    if(active && !failed && !unlocked){cmd->forwardmove=cmd->sidemove=cmd->upmove=0;}
}
int AW_IntroButtons(int bits){return active && !failed?0:bits;}
int AW_IntroImpulse(int impulse){return active && !failed && impulse==202?0:impulse;}
int AW_IntroUse(void){return active && !failed && !unlocked;}
int AW_IntroKey(int key) {
    int n;if(!active || !prompt || key_dest!=key_game)return 0;
    if(key==K_ESCAPE)return 0;
    n=strlen(player_name);
    if(prompt==1){
        if(key==K_BACKSPACE && n)player_name[n-1]=0;
        else if(key>=32 && key<127 && n<31){player_name[n]=key;player_name[n+1]=0;}
        else if(key==K_ENTER && n){prompt=0;jiub_state=20;jiub_timer=0;Con_Printf("Player name accepted.\n");}
    }else if(prompt==2 && key==K_ENTER){prompt=0;unlocked=1;if(travel(195,100,170))guard_state=50;}
    return 1;
}
void AW_IntroDraw(void) {
    int y;char text[40];if(!prompt || key_dest!=key_game)return;
    y=r_refdef.vrect.y+r_refdef.vrect.height;AW_UIBox(0,y,vid.width,vid.height-y);
    if(prompt==1){AW_UIText(10,y+4,"Name (Enter to accept)",-1);sprintf(text,"%s_",player_name);AW_UIText(10,y+22,text,-1);}
    else {AW_UIText(10,y+4,"W A S D: move. E: activate.",-1);AW_UIText(10,y+22,"Enter to follow the guard.",-1);}
}
static void status(void){Con_Printf("Intro active %ld / Jiub %ld / guard %ld / prompt %ld / unlocked %ld / failed %ld\n",
    (long)active,(long)jiub_state,(long)guard_state,(long)prompt,(long)unlocked,(long)failed);
    Con_Printf("Deck guard state %ld / nearby timer %ld ms\n",(long)deck_state,(long)(deck_timer*1000));}
void AW_IntroInit(void){Cmd_AddCommand("aw_new_game",new_game);Cmd_AddCommand("aw_intro_status",status);}
