/* SPDX-License-Identifier: GPL-2.0-or-later
 * The player's view in the engine (aw_view.h, docs/THIRD_PERSON.md):
 * first/third person on Quake's chase camera, the held Toggle POV orbit, the
 * idle (vanity) orbit, the wheel zoom, the player's body, and the death
 * scene with the original's choices and the AmiWind quick retry.
 *
 * Quake first: chase.c's chase_active makes the client draw the player's own
 * entity (cl_main.c) and R_DrawViewModel skip the hands; Chase_Update's view
 * placement is replaced while this view owns the camera (behind the player at
 * the original's distance, pulled in front of walls by a point trace through
 * the server's world, as chase.c traces its look point). The body is a
 * client-side copy of the view entity with the player's race/sex body model
 * (tools/prepare_player_view.py) and the animation kit's groups (aw_anim.c).
 *
 * Previous methods stay: aw_view_death 0 keeps the first-person death view
 * (Quake's dead roll); aw_player_body 0 draws no body (third person is then
 * refused); chase_active set by hand still runs Chase_Update.
 *
 * Cost: one point trace per frame in third person; the body one frame step
 * per frame; the body model is loaded on first use (Mod_ForName, cache).
 */
#include "quakedef.h"
#include "aw_view.h"
#include "aw_anim.h"
#include "aw_character.h"
#include "aw_save.h"
#include "aw_combat.h"

extern cvar_t chase_active;
/* The hooks (defined beside their callers, NULL in fixtures without this file). */
extern int (*aw_death_input_locked)(void);
extern void (*aw_view_frame)(void);
extern int (*aw_view_camera)(void);
extern entity_t *(*aw_view_body)(entity_t *ent);
extern int (*aw_view_hide_hands)(void);
extern void (*aw_view_input)(int key,int down);
extern int (*aw_view_key)(int key);
extern void (*aw_view_draw)(void);
extern void (*aw_combat_scene)(void);
extern int (*aw_view_fullscreen)(void);
int AW_ArenaActive(void);
void AW_MusicDeath(void);
void IN_AWClearButtons(void);

/* aw_view_third 1 = third person (not saved: the original starts in first person) */
static cvar_t view_cvar={"aw_view_third","0"};
static cvar_t distance_cvar={"aw_view_distance","48",true};
static cvar_t vanity_cvar={"aw_view_vanity","1",true};
/* aw_vanity_fullview 1 (default, saved): the vanity orbit shows the world alone, full screen, no HUD
 * (photo mode's view without its own notices); 0 = the orbit inside the normal HUD. */
static cvar_t fullview_cvar={"aw_vanity_fullview","1",true};
static cvar_t death_cvar={"aw_view_death","1",true};
/* The AmiWind quick retry after a lost fight: a build-config switch (--death-retry on|off,
 * default on); an off build writes aw_death_retry 0 into default-game.cfg. */
static cvar_t retry_cvar={"aw_death_retry","1"};
static cvar_t body_cvar={"aw_player_body","1",true};

static aw_view_rules_t rules;
/* the image's fVanityDelay (dbg vanitycamera delay N changes rules.vanity_delay for a test, not saved) */
static float vanity_delay_setting=30;
/* dbg vanitycamera on: an orbit started by hand runs until any input, also with the automatic orbit off */
static int vanity_forced;
static aw_view_t view;
static aw_death_t death;
static int ready,pov_down,pov_tapped,input_seen,owned,last_view=-1,warned,death_arena,acted;
static vec3_t anchor,last_angles,death_angles;
static char load_text[160]="The most recent Save Game is '%s'. \nWould you like to load it?";
static char yes_text[16]="Yes",no_text[16]="No";
static char save_label[64];
static int save_slot=-1;

/* ---- settings from the image (view/settings.txt, tools/prepare_player_view.py) ---- */
static void unescape(char *s) {
    char *o=s;
    while(*s){if(s[0]=='\\' && s[1]=='n'){*o++='\n';s+=2;}else *o++=*s++;}
    *o=0;
}
static void load_settings(void) {
    FILE *f=NULL;char line[200],*value;float v;
    AW_ViewRulesDefault(&rules);ready=1;
    if(COM_FOpenFile("view/settings.txt",&f)<0 || !f)return;
    if(!fgets(line,sizeof(line),f) || strncmp(line,"AWVS1",5)){fclose(f);return;}
    while(fgets(line,sizeof(line),f)){
        line[strcspn(line,"\r\n")]=0;
        value=strchr(line,' ');if(!value)continue;*value++=0;
        if(!strcmp(line,"fVanityDelay")){v=Q_atof(value);if(v>0 && v<=3600)rules.vanity_delay=vanity_delay_setting=v;}
        else if(!strcmp(line,"sLoadLastSaveMsg") && strlen(value)<sizeof(load_text) && strstr(value,"%s") &&
                !strchr(strstr(value,"%s")+2,'%')){strcpy(load_text,value);unescape(load_text);}
        else if(!strcmp(line,"sYes") && strlen(value)<sizeof(yes_text))strcpy(yes_text,value);
        else if(!strcmp(line,"sNo") && strlen(value)<sizeof(no_text))strcpy(no_text,value);
    }
    fclose(f);
}

static edict_t *local_player(void) {
    if(!sv.active || svs.maxclients!=1 || !svs.clients || cls.state!=ca_connected || cls.signon!=SIGNONS)return NULL;
    return svs.clients[0].edict;
}

/* ---- the body ---- */
#define BODIES 32
static struct {char race[32],path[48];int female;} bodies[BODIES];
static int body_count=-1,body_race=-2,body_female=-1;
static model_t *body_model;
static aw_anim_t body_anim;
static aw_anim_play_t body_play;
static entity_t body;
static void load_bodies(void) {
    byte *raw;int mark=Hunk_LowMark();char *p,*e,race[32],path[48];int female;
    body_count=0;
    raw=COM_LoadHunkFile("view/bodies.txt");
    if(raw && !strncmp((char *)raw,"AWPB1",5)){
        for(p=(char *)raw;p && *p && body_count<BODIES;p=e){
            e=strchr(p,'\n');if(e)*e++=0;
            /* RACE<TAB>0|1<TAB>PATH (no scanf: it pulls in FPU-emulated number parsing) */
            {char *t1=strchr(p,'\t'),*t2=t1?strchr(t1+1,'\t'):NULL;size_t n;
             if(!t1 || !t2 || t2!=t1+2 || (t1[1]!='0' && t1[1]!='1'))continue;
             n=(size_t)(t1-p);if(!n || n>=sizeof(race))continue;memcpy(race,p,n);race[n]=0;
             female=t1[1]-'0';n=strcspn(t2+1,"\r\t ");if(!n || n>=sizeof(path))continue;memcpy(path,t2+1,n);path[n]=0;}
            if(!strncmp(path,"progs/body/",11) && !strstr(path,"..") && strlen(path)>15 && !strcmp(path+strlen(path)-4,".mdl")){
                strcpy(bodies[body_count].race,race);strcpy(bodies[body_count].path,path);bodies[body_count].female=female;body_count++;
            }
        }
    }
    Hunk_FreeToLowMark(mark);
}
/* The body of the character's race and sex (the original's player record, a Dark Elf man,
 * before a character exists). 1 = a body is ready. */
static int body_ready(void) {
    const char *race="dark elf";int female=0,i,mark;char anm[64];byte *text;size_t n;
    if(!body_cvar.value)return 0;
    if(body_count<0)load_bodies();
    if(!body_count)return 0;
    if(aw_character.valid && aw_character.race>=0 && aw_character.race<aw_race_count){
        race=aw_races[aw_character.race].id;female=aw_character.female?1:0;
    }
    if(body_model && body_race==(aw_character.valid?aw_character.race:-1) && body_female==female)return 1;
    body_model=NULL;body_race=aw_character.valid?aw_character.race:-1;body_female=female;
    for(i=0;i<body_count;i++)if(bodies[i].female==female && !Q_strcasecmp(bodies[i].race,(char *)race))break;
    if(i==body_count)for(i=0;i<body_count && bodies[i].female!=female;i++);
    if(i==body_count)return 0;
    body_model=Mod_ForName(bodies[i].path,false);
    if(!body_model || body_model->type!=mod_alias){body_model=NULL;return 0;}
    n=strlen(bodies[i].path);memcpy(anm,bodies[i].path,n-4);strcpy(anm+n-4,".anm");
    mark=Hunk_LowMark();text=COM_LoadHunkFile(anm);
    if(!text || !AW_AnimParse(&body_anim,(const char *)text,body_model->numframes))AW_AnimDefault(&body_anim,body_model->numframes);
    Hunk_FreeToLowMark(mark);
    memset(&body_play,0,sizeof(body_play));body_play.group=255;
    return 1;
}
static float death_seconds(void) {
    const aw_anim_group_t *g=&body_anim.g[AW_ANIM_DEATH];
    if(body_model && g->present && g->count>1)return (g->count-1)*g->step;
    return 1.5f;    /* AmiWind: no death animation; the original waits for it to finish */
}
/* The body's height under the player's origin: the player's hull floor (world.qc setsize). */
static float feet(void) {
    edict_t *p=local_player();
    return p && p->v.mins[2]<0?-p->v.mins[2]:16.625f;
}
/* The body's shield block (COMBAT-BLOCKING-36): the block group (base_anim "shield: block start" ..
 * "block stop", hit key "block hit"; OpenMW plays it on a block, character.cpp refreshHitRecoilAnims).
 * While the player guards (aw_combat_block 1, an AmiWind extension) the shield rises to the hit key
 * and stays up; after a blocked blow the rest of the clip plays. -1 = no block frame now. */
static float guard_time;
static int body_block_frame(float dt) {
    const aw_anim_group_t *g=&body_anim.g[AW_ANIM_BLOCK];int hold,i;float left;
    if(!g->present || g->count<1){guard_time=0;return -1;}
    hold=g->x>0 && g->x<1?(int)(g->x*(g->count-1)+.5f):g->count/2;
    if(AW_CombatGuarding()){
        guard_time+=dt;i=(int)(guard_time/g->step);if(i>hold)i=hold;
        return g->base+i;
    }
    guard_time=0;left=AW_CombatBlockShown();
    if(!(left>0))return -1;
    i=g->count-1-(int)(left/g->step);if(i<hold)i=hold;if(i>g->count-1)i=g->count-1;
    return g->base+i;
}
entity_t *AW_ViewBody(entity_t *ent) {
    float speed,rate=1,dt=(float)host_frametime;int group,block=-1;edict_t *p=local_player();
    if(!owned || !body_ready())return NULL;
    if(dt<0)dt=0;
    if(dt>.25f)dt=.25f;
    if(death.stage!=AW_DEATH_NONE)group=AW_ANIM_DEATH;
    else{
        speed=(float)sqrt(cl.velocity[0]*cl.velocity[0]+cl.velocity[1]*cl.velocity[1]);
        group=AW_AnimMoveGroup(&body_anim,speed,p && p->v.waterlevel>=2,&rate);
    }
    body=*ent;body.model=body_model;
    body.frame=AW_AnimAdvance(&body_anim,&body_play,group,dt,rate,NULL);
    if(death.stage==AW_DEATH_NONE && (block=body_block_frame(dt))>=0)body.frame=block;
    if(body.frame<0 || body.frame>=body_model->numframes)body.frame=0;
    /* Converted characters face local +Y; Quake yaw 0 is +X (world.qc aw_npc_idle). */
    body.angles[PITCH]=0;body.angles[ROLL]=0;
    body.angles[YAW]=(death.stage!=AW_DEATH_NONE?death_angles[YAW]:view.mode==AW_VIEW_PREVIEW || view.mode==AW_VIEW_VANITY?anchor[YAW]:cl.viewangles[YAW])-90;
    body.origin[2]=ent->origin[2]-feet();
    body.colormap=vid.colormap;body.skinnum=0;body.efrag=NULL;body.topnode=NULL;body.aw_sprite_scale=1;
    return &body;
}

/* ---- the camera ---- */
static void trace(vec3_t from,vec3_t to,vec3_t out,float *fraction) {
    edict_t *p=local_player();
    if(p){
        trace_t t=SV_Move(from,vec3_origin,vec3_origin,to,MOVE_NOMONSTERS,p);
        *fraction=t.allsolid?0:t.fraction;VectorCopy(t.endpos,out);return;
    }
    {extern void TraceLine(vec3_t,vec3_t,vec3_t);vec3_t d;float a,b;
     TraceLine(from,to,out);VectorSubtract(out,from,d);a=Length(d);VectorSubtract(to,from,d);b=Length(d);
     *fraction=b>0?a/b:1;}
}
int AW_ViewCamera(void) {
    vec3_t focal,angles,forward,right,up,end,hit;float fraction,d;entity_t *ent;
    if(!owned)return 0;
    ent=&cl_entities[cl.viewentity];
    /* camera.cpp: the focal point mHeight above the feet (124 x 0.25), not the eye's bob */
    VectorCopy(ent->origin,focal);focal[2]+=rules.height-feet();
    if(death.stage!=AW_DEATH_NONE){VectorCopy(death_angles,angles);}
    else if(view.mode==AW_VIEW_PREVIEW || view.mode==AW_VIEW_VANITY){
        angles[PITCH]=anchor[PITCH]+view.orbit_pitch;angles[YAW]=anchor[YAW]+view.orbit_yaw;angles[ROLL]=0;
    }else{VectorCopy(cl.viewangles,angles);}
    if(angles[PITCH]>80)angles[PITCH]=80;
    if(angles[PITCH]<-80)angles[PITCH]=-80;
    angles[ROLL]=0;
    AngleVectors(angles,forward,right,up);
    VectorMA(focal,-view.distance,forward,end);
    trace(focal,end,hit,&fraction);
    d=AW_ViewObstacle(view.distance,fraction,rules.obstacle);
    VectorMA(focal,-d,forward,r_refdef.vieworg);
    VectorCopy(angles,r_refdef.viewangles);
    return 1;
}
void AW_ViewRoll(void) {if(owned)r_refdef.viewangles[ROLL]=0;}
/* The vanity orbit's full view (screen.c): only while it orbits; any input ends the orbit and brings the HUD back. */
int AW_ViewVanityFullscreen(void) {
    return owned && view.mode==AW_VIEW_VANITY && death.stage==AW_DEATH_NONE && fullview_cvar.value!=0;
}
int AW_ViewThirdPerson(void) {return owned;}

/* ---- the death scene ---- */
int AW_DeathLocked(void) {return death.stage!=AW_DEATH_NONE || AW_PlayerDead();}
static void begin_death(void) {
    int retry,saved;
    death_arena=AW_ArenaActive();
    save_slot=AW_SaveProfile()?AW_SaveLatest(AW_SaveProfile(),save_label,sizeof(save_label)):-1;
    saved=save_slot>=0 && !death_arena;
    retry=retry_cvar.value && !death_arena && AW_CombatRetryAvailable();
    VectorCopy(cl.viewangles,death_angles);death_angles[ROLL]=0;   /* the player's own pitch (OpenMW reference frames) */
    body_play.group=255;
    /* character.cpp playRandomDeath -> useDeathCamera: third person for the death animation */
    view.orbit_yaw=view.orbit_pitch=0;
    if(death_cvar.value && body_ready())view.mode=AW_VIEW_DEATH;
    AW_DeathBegin(&death,death_seconds(),retry,saved);acted=0;
    /* the death track (music.lua playerDied); combat plays it for a death in a fight */
    if(!AW_CombatDeathMusicPlayed())AW_MusicDeath();
    IN_AWClearButtons();
    AW_UISubtitle("","",0);      /* no speaker name or line stays on screen */
    Con_Printf("You have died.%s\n",death_arena?" (Arena)":"");
}
static void end_death(void) {
    AW_DeathEnd(&death);
    if(view.mode==AW_VIEW_DEATH)view.mode=view.primary;
}
static void choose(int choice) {
    acted=1;
    if(choice==AW_DEATH_RETRY){
        if(AW_CombatRetry()){Con_Printf("Try again: the fight restarts.\n");end_death();return;}
        Con_Printf("The fight cannot restart; choose again.\n");acted=0;return;
    }
    if(choice==AW_DEATH_LOAD && save_slot>=0){
        if(AW_SaveRead(AW_SaveProfile(),save_slot))return;
        acted=0;return;
    }
    /* No: the main menu (the menu's own "Return to main menu") */
    key_dest=key_game;Cbuf_AddText("disconnect\naw_main_menu\n");
}
int AW_ViewKey(int key) {
    int k=0,c;
    if(death.stage!=AW_DEATH_ASK || acted || key_dest!=key_game)return 0;
    if(key==K_LEFTARROW || key=='a' || key=='A')k=1;
    else if(key==K_RIGHTARROW || key==K_TAB || key=='d' || key=='D')k=2;
    else if(key==K_ENTER || key==K_MOUSE1 || key==K_SPACE || key=='e' || key=='E')k=3;
    else if(key=='y' || key=='Y')k=4;
    else if(key=='n' || key=='N')k=5;
    if(!k)return 0;
    c=AW_DeathKey(&death,k);
    if(c>=0)choose(c);
    return 1;
}
static const char *choice_label(int c) {
    if(death.count==2 && death.choice[0]==AW_DEATH_RETRY)return c==AW_DEATH_RETRY?yes_text:no_text;
    return c==AW_DEATH_LOAD?yes_text:c==AW_DEATH_MENU?no_text:"Retry fight";
}
void AW_ViewDraw(void) {
    char text[240];const char *at;int i,w=280,x=(vid.width-w)/2,y,h=96,bw,gold=AW_UIColor(223,199,144),grey=AW_UIColor(150,130,100);
    extern int scr_copyeverything;
    if(death.stage!=AW_DEATH_ASK || key_dest!=key_game)return;
    scr_copyeverything=1;
    y=(vid.height-h)/2;
    if(death.choice[0]==AW_DEATH_RETRY)strcpy(text,"Try the fight again?");      /* AmiWind: no save to offer */
    else if((at=strstr(load_text,"%s"))!=NULL){
        int n=(int)(at-load_text);
        snprintf(text,sizeof(text),"%.*s%s%s",n,load_text,save_label,at+2);
    }else strcpy(text,load_text);
    AW_UIBox(x,y,w,h);
    AW_UICenteredLines(x+6,y+4,w-12,h-38,text);
    bw=(w-16-(death.count-1)*8)/death.count;
    for(i=0;i<death.count;i++){
        int bx=x+8+i*(bw+8),by=y+h-32;
        AW_UIBox(bx,by,bw,24);
        if(i==death.selection)AW_UIFill(bx+3,by+3,bw-6,18,AW_UIColor(70,52,30));
        AW_UITextBox(bx,by,bw,24,choice_label(death.choice[i]),i==death.selection?gold:grey);
    }
}

/* ---- the frame ---- */
static void set_chase(int on) {
    if(on && !owned){owned=1;Cvar_SetValue("chase_active",1);}
    else if(!on && owned){owned=0;Cvar_SetValue("chase_active",0);}
}
static int playing(void) {
    return key_dest==key_game && !cl.paused && !con_forcedup && !AW_IntroUse();
}
void AW_ViewFrame(void) {
    float dt=(float)host_frametime;int input,dead,mode_before;edict_t *p;
    if(!ready)load_settings();
    if(dt<0)dt=0;
    if(dt>.25f)dt=.25f;
    p=local_player();
    if(!p){if(death.stage!=AW_DEATH_NONE)end_death();set_chase(0);return;}
    if(distance_cvar.value>=rules.min_distance && distance_cvar.value<=rules.max_distance && distance_cvar.value!=view.distance &&
       view.mode!=AW_VIEW_DEATH)view.distance=distance_cvar.value;
    /* aw_view_third set from the console or a config: the primary mode */
    if((int)view_cvar.value!=last_view){
        int want=view_cvar.value?AW_VIEW_THIRD:AW_VIEW_FIRST;
        if(last_view>=0 && view.mode!=AW_VIEW_DEATH){
            if(want==AW_VIEW_THIRD && !body_ready()){
                if(!warned)Con_Printf("No player body in this image (--player-body on builds it): first person only.\n");
                warned=1;want=AW_VIEW_FIRST;
            }
            view.primary=view.mode=want;
        }
        last_view=(int)view_cvar.value;
    }
    dead=p->v.health<=0;
    if(dead && death.stage==AW_DEATH_NONE)begin_death();
    else if(!dead && death.stage!=AW_DEATH_NONE)end_death();
    if(death.stage!=AW_DEATH_NONE){
        VectorCopy(death_angles,cl.viewangles);   /* no turning while dead */
        if(!death_arena && !acted && AW_DeathStep(&death,dt)==AW_DEATH_MAIN_MENU)choose(AW_DEATH_MENU);
    }else if(playing()){
        int turned=cl.viewangles[YAW]!=last_angles[YAW] || cl.viewangles[PITCH]!=last_angles[PITCH];
        mode_before=view.mode;
        if(pov_tapped && !pov_down)AW_ViewPOVTap(&view,&rules);
        else AW_ViewPOV(&view,&rules,pov_down,dt);
        if(view.mode!=AW_VIEW_FIRST && !body_ready()){
            if(!warned)Con_Printf("No player body in this image (--player-body on builds it): first person only.\n");
            warned=1;view.mode=view.primary=AW_VIEW_FIRST;
        }
        if(view.mode==AW_VIEW_PREVIEW || view.mode==AW_VIEW_VANITY){
            if(mode_before!=view.mode)VectorCopy(cl.viewangles,anchor);
            /* the mouse turns the camera, not the player (camera.lua Preview) */
            view.orbit_yaw+=cl.viewangles[YAW]-anchor[YAW];view.orbit_pitch+=cl.viewangles[PITCH]-anchor[PITCH];
            VectorCopy(anchor,cl.viewangles);
        }else if(mode_before==AW_VIEW_PREVIEW){
            /* leaving the orbit: the player turns to the camera's heading (OpenMW turns the
             * character gradually, deferredPreviewRotation; AmiWind turns at once) */
            cl.viewangles[YAW]=anchor[YAW]+view.orbit_yaw;
            view.orbit_yaw=view.orbit_pitch=0;
        }
        input=input_seen || pov_down || pov_tapped || turned || cl.velocity[0] || cl.velocity[1] || cl.velocity[2];
        mode_before=view.mode;
        AW_ViewIdle(&view,&rules,input,(vanity_cvar.value || vanity_forced) && body_ready(),dt);
        if(view.mode!=AW_VIEW_VANITY)vanity_forced=0;
        if(mode_before==AW_VIEW_VANITY && view.mode!=AW_VIEW_VANITY)view.orbit_yaw=view.orbit_pitch=0;
        else if(mode_before!=AW_VIEW_VANITY && view.mode==AW_VIEW_VANITY)VectorCopy(cl.viewangles,anchor);
        if((view.primary==AW_VIEW_THIRD)!=(view_cvar.value!=0)){Cvar_SetValue(view_cvar.name,view.primary==AW_VIEW_THIRD);last_view=(int)view_cvar.value;}
        if(view.distance!=distance_cvar.value)Cvar_SetValue(distance_cvar.name,view.distance);
    }
    input_seen=pov_tapped=0;VectorCopy(cl.viewangles,last_angles);
    set_chase(AW_ViewBehind(&view));
}
void AW_ViewInput(int key,int down) {
    (void)key;
    /* game keys only: the console's own keys (typing a command, closing the console) are not play input */
    if(down && key_dest==key_game)input_seen=1;
}
void AW_ViewSceneSpawn(void) {
    if(death.stage!=AW_DEATH_NONE)end_death();
    body_model=NULL;body_race=-2;
}

/* The vanity orbit now, until any input (dbg vanitycamera on, dbg camera vanity now). */
static void vanity_start(void) {
    if(!ready)load_settings();
    if(!body_ready()){Con_Printf("No player body in this image (--player-body on builds it): no vanity camera.\n");return;}
    if(death.stage!=AW_DEATH_NONE || !local_player()){Con_Printf("Vanity camera: not now.\n");return;}
    view.idle=rules.vanity_delay+1;VectorCopy(cl.viewangles,anchor);
    view.mode=AW_VIEW_VANITY;view.orbit_yaw=view.orbit_pitch=0;vanity_forced=1;
    Con_Printf("Vanity camera: orbiting until any input.\n");
}
/* dbg vanitycamera (alias dbg vanitycam): auto = the original (orbit after fVanityDelay seconds without input,
 * 3 degrees a second; aw_view_vanity 1, the default), off = never (aw_view_vanity 0, saved), on/now = orbit now
 * until any input; delay N = a test delay in seconds (not saved; "delay default" = the game's own setting). */
static void vanity_command(void) {
    char *a=Cmd_Argv(1);float d;
    if(!ready)load_settings();
    if(Cmd_Argc()==1){
        Con_Printf("Vanity camera: %s; delay %.1f s (game setting fVanityDelay %.1f s)%s; turn %.0f deg/s; idle %.1f s now; orbiting %s; full view %s\n",
            vanity_cvar.value?"auto (the original)":"off",rules.vanity_delay,vanity_delay_setting,
            rules.vanity_delay!=vanity_delay_setting?" [test delay, not saved]":"",rules.vanity_rate,view.idle,
            view.mode==AW_VIEW_VANITY?"yes":"no",fullview_cvar.value?"on":"off");
        return;
    }
    if(Cmd_Argc()==2 && (!Q_strcasecmp(a,"on") || !Q_strcasecmp(a,"now"))){vanity_start();return;}
    if(Cmd_Argc()==2 && !Q_strcasecmp(a,"auto")){Cvar_SetValue(vanity_cvar.name,1);Con_Printf("Vanity camera: auto (the original).\n");return;}
    if(Cmd_Argc()==2 && !Q_strcasecmp(a,"off")){
        Cvar_SetValue(vanity_cvar.name,0);vanity_forced=0;
        if(view.mode==AW_VIEW_VANITY){view.mode=view.primary;view.orbit_yaw=view.orbit_pitch=0;}
        Con_Printf("Vanity camera: off.\n");return;
    }
    if(Cmd_Argc()==3 && !Q_strcasecmp(a,"fullview")){
        int on;
        if(!Q_strcasecmp(Cmd_Argv(2),"on"))on=1;else if(!Q_strcasecmp(Cmd_Argv(2),"off"))on=0;
        else{Con_Printf("Usage: dbg vanitycamera fullview on|off\n");return;}
        Cvar_SetValue(fullview_cvar.name,(float)on);
        Con_Printf("Vanity full view: %s (aw_vanity_fullview %d, saved).\n",on?"on: no HUD, full screen":"off: the orbit inside the HUD",on);
        return;
    }
    if(Cmd_Argc()==3 && !Q_strcasecmp(a,"delay")){
        if(!Q_strcasecmp(Cmd_Argv(2),"default"))d=vanity_delay_setting;else d=Q_atof(Cmd_Argv(2));
        if(d<.5f || d>3600){Con_Printf("Vanity delay: 0.5 to 3600 seconds, or default.\n");return;}
        rules.vanity_delay=d;
        Con_Printf("Vanity delay %.1f s (test value, not saved; the original is the game setting fVanityDelay, %.1f s).\n",d,vanity_delay_setting);
        return;
    }
    Con_Printf("Usage: dbg vanitycamera [auto | off | on (now) | delay N/default | fullview on/off]\n");
}

/* aw_scene.c: a scene spawned; the combat layer's hook first */
static void (*combat_scene)(void);
static void scene_spawn(void) {if(combat_scene)combat_scene();AW_ViewSceneSpawn();}

/* ---- commands ---- */
static void pov_press(void) {if(key_dest==key_game)pov_down=pov_tapped=1;}
static void pov_release(void) {pov_down=0;}
static void zoom_command(void) {
    float clicks=Cmd_Argc()>1?Q_atof(Cmd_Argv(1)):0;
    if(key_dest!=key_game || death.stage!=AW_DEATH_NONE)return;
    if(clicks<0 && view.mode==AW_VIEW_FIRST && !body_ready()){
        if(!warned)Con_Printf("No player body in this image (--player-body on builds it): first person only.\n");
        warned=1;return;
    }
    AW_ViewZoom(&view,&rules,clicks*rules.zoom_step);
    input_seen=1;
}
static const char *mode_name(int m) {
    return m==AW_VIEW_THIRD?"third person":m==AW_VIEW_PREVIEW?"orbit (Toggle POV held)":m==AW_VIEW_VANITY?"vanity orbit":
           m==AW_VIEW_DEATH?"death camera":"first person";
}
static void command(void) {
    char *a=Cmd_Argv(1);int on;
    if(!ready)load_settings();
    if(Cmd_Argc()==1){
        Con_Printf("View: %s (primary %s), distance %.1f (%.1f..%.1f), vanity %s after %.0f s idle (%.1f s now), death camera %s, retry %s\n",
            mode_name(view.mode),mode_name(view.primary),view.distance,rules.min_distance,rules.max_distance,
            vanity_cvar.value?"on":"off",rules.vanity_delay,view.idle,death_cvar.value?"on":"off",retry_cvar.value?"on":"off");
        Con_Printf("Body: %s%s\n",body_ready()?body_model->name:"none",body_cvar.value?"":" (aw_player_body 0)");
        return;
    }
    if(!Q_strcasecmp(a,"first")){view.primary=view.mode=AW_VIEW_FIRST;Cvar_SetValue(view_cvar.name,0);last_view=0;return;}
    if(!Q_strcasecmp(a,"third")){Cvar_SetValue(view_cvar.name,1);return;}
    if(!Q_strcasecmp(a,"toggle")){Cvar_SetValue(view_cvar.name,view.primary==AW_VIEW_FIRST);return;}
    if(!Q_strcasecmp(a,"distance") && Cmd_Argc()==3){
        float d=Q_atof(Cmd_Argv(2));
        if(d<rules.min_distance)d=rules.min_distance;
        if(d>rules.max_distance)d=rules.max_distance;
        Cvar_SetValue(distance_cvar.name,d);view.distance=d;return;
    }
    if(!Q_strcasecmp(a,"vanity") && Cmd_Argc()==3 && !Q_strcasecmp(Cmd_Argv(2),"now")){vanity_start();return;}
    if(!Q_strcasecmp(a,"die") && Cmd_Argc()==2){
        /* test the death scene: world damage through the combat layer (as lava, aw_lava.c) */
        if(!AW_CombatHurtPlayer(100000,"dbg camera die"))Con_Printf("Not in a game, or already dead.\n");
        return;
    }
    if(Cmd_Argc()==3 && (on=AW_CompanionToggleWord(Cmd_Argv(2)))>=0){
        if(!Q_strcasecmp(a,"vanity")){Cvar_SetValue(vanity_cvar.name,(float)on);return;}
        if(!Q_strcasecmp(a,"death")){Cvar_SetValue(death_cvar.name,(float)on);return;}
        if(!Q_strcasecmp(a,"retry")){Cvar_SetValue(retry_cvar.name,(float)on);return;}
        if(!Q_strcasecmp(a,"body")){Cvar_SetValue(body_cvar.name,(float)on);body_model=NULL;body_race=-2;return;}
    }
    Con_Printf("Usage: dbg camera [first | third | toggle | distance N | vanity on/off/now | death on/off | retry on/off | body on/off | die]\n");
}
void AW_ViewInit(void) {
    Cvar_RegisterVariable(&view_cvar);Cvar_RegisterVariable(&distance_cvar);Cvar_RegisterVariable(&vanity_cvar);
    Cvar_RegisterVariable(&death_cvar);Cvar_RegisterVariable(&retry_cvar);Cvar_RegisterVariable(&body_cvar);
    Cvar_RegisterVariable(&fullview_cvar);
    AW_ViewRulesDefault(&rules);AW_ViewReset(&view,&rules);
    Cmd_AddCommand("+aw_pov",pov_press);Cmd_AddCommand("-aw_pov",pov_release);
    Cmd_AddCommand("aw_view_zoom",zoom_command);Cmd_AddCommand("aw_camera",command);
    Cmd_AddCommand("aw_vanitycam",vanity_command);
    aw_death_input_locked=AW_DeathLocked;
    aw_view_frame=AW_ViewFrame;aw_view_camera=AW_ViewCamera;aw_view_body=AW_ViewBody;aw_view_hide_hands=AW_ViewThirdPerson;
    aw_view_input=AW_ViewInput;aw_view_key=AW_ViewKey;aw_view_draw=AW_ViewDraw;aw_view_fullscreen=AW_ViewVanityFullscreen;
    combat_scene=aw_combat_scene;aw_combat_scene=scene_spawn;   /* after AW_CombatInit (aw_debug.c) */
}
