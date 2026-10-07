/* SPDX-License-Identifier: GPL-2.0-or-later
 * Waiting advances the persistent clock; NPC scheduling/rest recovery and sky
 * rendering are separate systems. The modal uses the existing single-player
 * menu pause, leaving the music service running.
 */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_clock.h"
#include "aw_sky.h"
static int modal,hours=1,help_page;
static const char *help_commands[]={"+forward","+back","+moveleft","+moveright","+attack","+aw_use","impulse 202","aw_torch","aw_wait","aw_quicksave","aw_quickload","toggleconsole","aw_quick_help","togglemenu","aw_worldmap","aw_journal"};
static const char *help_actions[]={"Move forward","Move back","Move left","Move right","Attack","Activate","Ready hands","Toggle torch","Wait","Quicksave","Quickload","Console","Quick help","Pause menu","World map","Journal"};
#define HELP_COUNT 16
#define HELP_ROWS 7
static void help_text(int x,int y,const char *s) {
    int w=AW_ConsoleCharWidth();
    for(;*s && x+w<=vid.width-12;s++,x+=w)AW_ConsoleCharacter(x,y,(unsigned char)*s);
}
static int help_pages(void) {
    int k,n=0;for(k=0;k<256;k++)if(keybindings[k] && *keybindings[k])n++;
    return n?(n+HELP_ROWS-1)/HELP_ROWS:1;
}
static keydest_t return_dest;
static cvar_t timescale={"aw_timescale","30",true};
static cvar_t daynightcycle={"aw_daynightcycle","1",true};
/* Fraction of one clock millisecond, not a second game-time state. */
static double clock_fraction;
/* A bounded presentation preview, never a second saved world clock. */
static int gallery_active,gallery_step,gallery_here,gallery_night;
static double gallery_elapsed;
static char gallery_map[MAX_QPATH],gallery_world[MAX_QPATH];
static const int gallery_minutes[]={330,390,780,1020,1080,1140,1215,1380};
static const char *gallery_names[]={"Dawn 05:30","Sunrise 06:30","Midday 13:00",
    "Golden hour 17:00","Red sunset 18:00","Dusk 19:00","Blue hour 20:15","Night 23:00"};
/* Source-tested sn045 eye directions. Other maps keep their current eye
 * position and only preview these angles; no map load or player teleport. */
static const float gallery_angles[8][3]={{10,135,0},{-5,348,0},{-65,270,0},
    {-10,180,0},{-20,190,0},{-20,190,0},{-10,180,0},{10,135,0}};
static const float gallery_height[8]={180,180,180,240,180,180,240,180};
static void gallery_stop(void) {
    gallery_active=0;gallery_elapsed=0;
}
/* dbg 24hrcycle [seconds]: steps the real clock one game hour at a time and
 * shows each hour for the given seconds (default 1, so 24 s in all), ending at
 * the same hour the next day. One step per hour keeps the sky and light
 * updates to 24, not one per frame. Esc, a map change or a new game stops it. */
static double cycle_hold,cycle_elapsed;static int cycle_steps;
/* dbg lightgallery: lighting switches at the current spot, listed in a strip
 * below the view. Up/Down: choose, Left/Right: change, Esc: done. Time is a
 * preview through the gallery clock (the saved clock is untouched); the other
 * switches are the normal settings and stay as chosen. */
static int light_active,light_row,light_time;
static const char *const light_rows[]={"Night","Tint","Lamps","Glow","Headlamp","Veil","Hue","Time"};
#define LIGHT_ROWS 8
static const char *const light_hues[]={"255 210 140","255 170 80","255 235 200","200 220 255"};
static const char *const light_hue_names[]={"warm","lamp","soft","cool"};
#define LIGHT_HUES 4
static const short light_minutes[]={-1,330,390,780,1080,1140,1320,0};
static const char *const light_times[]={"real","05:30","06:30","13:00","18:00","19:00","22:00","00:00"};
#define LIGHT_TIMES 8
static float light_cvar(const char *name){cvar_t *v=Cvar_FindVar((char *)name);return v?v->value:0;}
static void light_value(int row,char *out,int size) {
    switch(row){
    case 0:snprintf(out,size,"%s",light_cvar("aw_night_light")>0?"light":"remap");break;
    case 1:snprintf(out,size,"%ld%%",(long)light_cvar("aw_night_tint"));break;
    case 2:snprintf(out,size,"%s",r_lamps?"on":"off");break;
    case 3:snprintf(out,size,"%s",light_cvar("aw_emissive")?"on":"off");break;
    case 4:snprintf(out,size,"%s",light_cvar("aw_headlamp")?"on":"off");break;
    case 5:snprintf(out,size,"%ld",(long)light_cvar("aw_horizon_veil"));break;
    case 6:{cvar_t *h=Cvar_FindVar("aw_light_hue");int i;const char *name="custom";
        for(i=0;h && i<LIGHT_HUES;i++)if(!strcmp(h->string,light_hues[i]))name=light_hue_names[i];
        snprintf(out,size,"%s",name);break;}
    default:snprintf(out,size,"%s",light_times[light_time]);
    }
}
static void light_change(int step) {
    float tint;
    switch(light_row){
    case 0:Cvar_SetValue("aw_night_light",light_cvar("aw_night_light")>0?0:1);break;
    case 1:tint=light_cvar("aw_night_tint")+step*25;if(tint<0)tint=100;if(tint>100)tint=0;
        Cvar_SetValue("aw_night_tint",tint);break;
    case 2:r_lamps=!r_lamps;D_FlushCaches();break;
    case 3:Cvar_SetValue("aw_emissive",light_cvar("aw_emissive")?0:1);D_FlushCaches();break;
    case 4:Cvar_SetValue("aw_headlamp",light_cvar("aw_headlamp")?0:1);break;
    case 5:tint=light_cvar("aw_horizon_veil")+step*2;if(tint<0)tint=8;if(tint>8)tint=0;
        Cvar_SetValue("aw_horizon_veil",tint);break;
    case 6:{cvar_t *h=Cvar_FindVar("aw_light_hue");int i,at=-1;
        for(i=0;h && i<LIGHT_HUES;i++)if(!strcmp(h->string,light_hues[i]))at=i;
        at=(at+step+LIGHT_HUES)%LIGHT_HUES;Cvar_Set("aw_light_hue",(char *)light_hues[at]);break;}
    default:light_time=(light_time+step+LIGHT_TIMES)%LIGHT_TIMES;
    }
}
int AW_LightGalleryDraw(void) {
    char line[160],value[16];int i,used=0,n;
    if(!light_active || key_dest!=key_game)return 0;
    AW_UIFill(0,vid.height-28,vid.width,28,AW_UIColor(0,0,0));
    line[0]=0;
    for(i=0;i<LIGHT_ROWS && used<(int)sizeof(line)-1;i++){
        light_value(i,value,sizeof value);
        n=snprintf(line+used,sizeof(line)-used,i==light_row?"[%s:%s] ":"%s:%s ",light_rows[i],value);
        if(n<0)break;
        used+=n;
    }
    AW_SmallString(4,vid.height-24,line);
    AW_SmallString(4,vid.height-14,"Up/Down: choose  Left/Right: change  Esc: done");
    return 1;
}
static void light_gallery_command(void) {
    if(Cmd_Argc()==2 && !Q_strcasecmp(Cmd_Argv(1),"off")){
        if(light_active){light_active=0;Con_Printf("Light gallery off; real time shown.\n");}
        return;
    }
    if(Cmd_Argc()>1){Con_Printf("Usage: dbg lightgallery [off]\n");return;}
    if(!sv.active || cls.state!=ca_connected || svs.maxclients!=1 || gallery_active || cycle_steps || modal ||
       AW_IntroUse() || AW_CharacterActive() || AW_ReaderActive()){
        Con_Printf("Start the light gallery in a local game (not during the intro, another gallery or the 24 h cycle).\n");return;
    }
    light_active=1;light_row=0;light_time=0;
    if(key_dest==key_console)Con_ToggleConsole_f();
    IN_AWClearButtons();
}
static void cycle_stop(const char *why) {
    if(!cycle_steps)return;
    cycle_steps=0;if(why)AW_UISubtitle("",why,4);
}
static void cycle_label(void) {
    int y,m,d,h,n;char line[96];AW_ClockDate(&y,&m,&d,&h,&n);
    snprintf(line,sizeof line,"24 h cycle: %02ld:%02ld (%ld/24). Esc: stop.",(long)h,(long)n,(long)(24-cycle_steps));
    AW_UISubtitle("",line,cycle_hold<1?1:(float)cycle_hold);
}
static void cycle_command(void) {
    char *s=Cmd_Argv(1),*end;double hold=1;
    if(Cmd_Argc()>2)goto usage;
    if(Cmd_Argc()==2){
        if(!Q_strcasecmp(s,"off")){
            if(cycle_steps){cycle_stop(NULL);Con_Printf("24 h cycle stopped.\n");}
            else Con_Printf("24 h cycle is not running.\n");
            return;
        }
        hold=strtod(s,&end);if(!*s || *end || !(hold>=.25 && hold<=60))goto usage;
    }
    if(!sv.active || cls.state!=ca_connected || svs.maxclients!=1 || gallery_active || modal ||
       AW_IntroUse() || AW_CharacterActive() || AW_ReaderActive() || !AW_ClockEnsure()){
        Con_Printf("Start the 24 h cycle in a local game (not during the intro or a gallery).\n");return;
    }
    cycle_hold=hold;cycle_elapsed=0;cycle_steps=24;clock_fraction=0;
    Con_Printf("24 h cycle: each hour shown %ld.%02ld s, %ld s in all. Esc stops.\n",
        (long)hold,(long)(hold*100+.5)%100,(long)(24*hold+.5));
    if(key_dest==key_console)Con_ToggleConsole_f();
    IN_AWClearButtons();cycle_label();return;
usage:
    Con_Printf("Usage: dbg 24hrcycle [off or seconds per hour 0.25..60, default 1]\n");
}
int AW_DayGalleryClock(int actual_ms) {
    if(light_active && light_time>0 && sv.active)return light_minutes[light_time]*60000;
    if(gallery_active && (!sv.active || cls.state!=ca_connected ||
       strcmp(gallery_map,sv.name) || !cl.worldmodel ||
       strcmp(gallery_world,cl.worldmodel->name) || AW_Interior()))gallery_stop();
    return gallery_active?(gallery_night?1380:gallery_minutes[gallery_step])*60000:actual_ms;
}
int AW_DayGalleryView(float *origin,float *angles) {
    int i;float direction[3];double horizontal;
    (void)AW_DayGalleryClock(0);
    if(!gallery_active || gallery_here)return 0;
    if(gallery_night){
        /* Keep the current eye in every map. Never borrow another scene's
         * coordinates or use last frame's cached, possibly daytime moon. */
        if(gallery_step==0)return 0;
        if(gallery_step==3){angles[0]=-85;angles[2]=0;return 1;}
        if(!R_NightMoonOrbit(gallery_step-1,1380*60000,
            AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:days"),direction,NULL))return 0;
        horizontal=sqrt((double)direction[0]*direction[0]+(double)direction[1]*direction[1]);
        angles[0]=(float)(-atan2(direction[2],horizontal)*180/M_PI);
        angles[1]=(float)(atan2(direction[1],direction[0])*180/M_PI);
        if(angles[1]<0)angles[1]+=360;
        angles[2]=0;return 1;
    }
    for(i=0;i<3;i++)angles[i]=gallery_angles[gallery_step][i];
    /* Only the exact loaded BSP establishes the known coordinate basis.
     * sv.name may remain "seyda" while the catalogue changes region BSPs. */
    if((!strcmp(sv.name,"seyda") || !strcmp(sv.name,"sn045")) &&
       !strcmp(gallery_world,"maps/sn045.bsp")){
        origin[0]=100+1.0f/32;origin[1]=-180+1.0f/32;
        origin[2]=gallery_height[gallery_step]+cl.viewheight+1.0f/32;
    }
    return 1;
}
static void gallery_label(void) {
    static const char *night_names[]={"Wide view","Masser","Secunda","Overhead stars"};
    char line[128];float direction[3];int hidden=0;
    if(gallery_night){
        if(gallery_step==1 || gallery_step==2)
            hidden=!R_NightMoonOrbit(gallery_step-1,1380*60000,
                AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:days"),direction,NULL);
        snprintf(line,sizeof line,"Night %s 23:00: %s%s. Esc: return.",
            gallery_here?"here":"tour",night_names[gallery_step],hidden?" below horizon; current view":"");
    }else snprintf(line,sizeof line,"%s: %s. Esc: return.",gallery_here?"Sky here":"Sky tour",gallery_names[gallery_step]);
    AW_UISubtitle("",line,7.5);
}
static void gallery_command(int night) {
    char *arg=Cmd_Argv(1);int here=Cmd_Argc()==2 && !Q_strcasecmp(arg,"here");
    if(Cmd_Argc()>2 || (Cmd_Argc()==2 && !here && Q_strcasecmp(arg,"off"))){
        Con_Printf("Usage: dbg %s [here/off]\n",night?"nightgallery":"daycycle gallery");return;
    }
    if((Cmd_Argc()==2 && !here) || (Cmd_Argc()==1 && gallery_active)){
        gallery_stop();Con_Printf("Sky gallery off; real game time restored.\n");return;
    }
    if(!sv.active || cls.state!=ca_connected || !cl.worldmodel || svs.maxclients!=1 || AW_Interior() ||
       AW_IntroUse() || AW_CharacterActive() || AW_ReaderActive() || modal ||
       (key_dest!=key_console && key_dest!=key_game)){
        Con_Printf("Start the %s gallery in a local outdoor game.\n",night?"night":"daycycle");return;
    }
    gallery_active=1;gallery_step=0;gallery_elapsed=0;gallery_here=here;gallery_night=night;
    snprintf(gallery_map,sizeof gallery_map,"%s",sv.name);
    snprintf(gallery_world,sizeof gallery_world,"%s",cl.worldmodel->name);
    if(key_dest==key_console)Con_ToggleConsole_f();
    IN_AWClearButtons();gallery_label();
}
static void daycycle_gallery(void){gallery_command(0);}
static void night_gallery(void){gallery_command(1);}
extern char *keybindings[256];
extern int scr_copyeverything;
static int allowed(void) {
    edict_t *p;
    if(!sv.active || svs.maxclients!=1 || !svs.clients || cls.state!=ca_connected ||
       AW_StoryRestricted() || AW_CharacterActive() || AW_ReaderActive() ||
       AW_SpeechRemaining()>0)return 0;
    p=svs.clients[0].edict;
    return p && p->v.health>0 && p->v.movetype==MOVETYPE_WALK &&
        ((int)p->v.flags&FL_ONGROUND) && p->v.waterlevel<2 && !sv.paused;
}
static void close_modal(void){modal=0;key_dest=return_dest;IN_AWClearButtons();}
static void open_modal(int kind){return_dest=key_dest;modal=kind;key_dest=key_menu;IN_AWClearButtons();}
static void wait_open(void) {
    if(modal || gallery_active || key_dest!=key_game)return;
    if(!allowed()){AW_UISubtitle("","Wait after registration, on dry ground, when no one is speaking.",5);return;}
    if(!AW_ClockEnsure()){Con_Printf("Clock state unavailable.\n");return;}
    hours=1;open_modal(1);
}
static void quick_help(void){if(!modal && key_dest==key_game){help_page=0;open_modal(2);}}
static int named_minutes(char *s) {
    static const char *names[]={"morning","night","midday","day","evening","sunset","sunrise","dusk","dawn"};
    /* Convenient distinct snapshots, not nine original game rules. Sunrise/sunset
     * are source anchors; dawn is the sky pre-sunrise start (05:30). */
    static const int values[]={540,0,720,840,1020,1080,360,1140,330};
    int i;for(i=0;i<9;i++)if(!Q_strcasecmp(s,(char *)names[i]))return values[i];
    return -1;
}
static void report_time(void) {
    int y,m,d,h,n;AW_ClockDate(&y,&m,&d,&h,&n);
    Con_Printf("Time %02ld:%02ld, %02ld/%02ld/%ld (day/month/year)\n",(long)h,(long)n,(long)d,(long)m,(long)y);
}
/* Exact debug input: four decimal digits, HH 00..23 and MM 00..59.
 * Invalid input never touches state; legacy evening/sunset hour aliases stay compatible. */
static void set_time(void) {
    char *s=Cmd_Argv(1);int hour,minute=0,i,named;
    if(!sv.active){Con_Printf("Start the local game first.\n");return;}
    if(Cmd_Argc()==1){report_time();return;} /* dbg time: what time is it */
    if(Cmd_Argc()!=2)goto invalid;
    named=named_minutes(s);
    if(named>=0){hour=named/60;minute=named%60;}
    else{
        if(strlen(s)!=4)goto invalid;
        for(i=0;i<4;i++)if(s[i]<'0' || s[i]>'9')goto invalid;
        hour=(s[0]-'0')*10+s[1]-'0';minute=(s[2]-'0')*10+s[3]-'0';
        if(hour>23 || minute>59)goto invalid;
    }
    if(!AW_ClockSetTime(hour,minute)){Con_Printf("Clock state unavailable.\n");return;}
    clock_fraction=0;report_time();return;
invalid:
    Con_Printf("Usage: dbg time [HHMM 0000..2359 or a named time]\n");
}
static void timeofday(void) {
    char *s=Cmd_Argv(1),*end;double hour;
    if(!sv.active){Con_Printf("Start the local game first.\n");return;}
    if(Cmd_Argc()==2){
        hour=named_minutes(s)/60.0;
        if(!Q_strcasecmp(s,"evening"))hour=18; /* legacy debug aliases */
        else if(!Q_strcasecmp(s,"sunset"))hour=19;
        else if(hour<0){hour=strtod(s,&end);if(!*s || *end)hour=-1;}
        if(!AW_ClockSetHour(hour)){Con_Printf("dbg timeofday 0..23.999 / morning night midday day evening sunset sunrise dusk dawn\n");return;}
        clock_fraction=0;
    }else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg timeofday [hour or named time]\n");return;}
    report_time();
}
void AW_WaitInit(void){
    Cvar_RegisterVariable(&timescale);Cvar_RegisterVariable(&daynightcycle);Cmd_AddCommand("aw_wait",wait_open);
    Cmd_AddCommand("aw_quick_help",quick_help);Cmd_AddCommand("aw_timeofday",timeofday);
    Cmd_AddCommand("aw_set_time",set_time);
    Cmd_AddCommand("aw_daycycle_gallery",daycycle_gallery);
    Cmd_AddCommand("aw_nightgallery",night_gallery);
    Cmd_AddCommand("aw_24hrcycle",cycle_command);
    Cmd_AddCommand("aw_lightgallery",light_gallery_command);
}
void AW_WaitTick(void) {
    double delta;int whole;
    if(!sv.active){modal=0;clock_fraction=0;gallery_stop();cycle_steps=0;light_active=0;return;}
    (void)AW_DayGalleryClock(0);
    if(cycle_steps){
        if(cls.state!=ca_connected || AW_IntroUse()){cycle_stop(NULL);return;}
        if(modal || sv.paused || key_dest!=key_game)return;
        if(host_frametime>0 && host_frametime<1)cycle_elapsed+=host_frametime;
        if(cycle_elapsed>=cycle_hold){
            cycle_elapsed-=cycle_hold;
            if(!AW_ClockAdvance(3600000)){cycle_stop("24 h cycle stopped: clock unavailable.");return;}
            if(--cycle_steps)cycle_label();
            else {cycle_steps=1;cycle_stop("24 h cycle finished.");}
        }
        return;
    }
    if(gallery_active){
        if(sv.paused || key_dest!=key_game || modal)return;
        if(host_frametime>0 && host_frametime<1)gallery_elapsed+=host_frametime;
        if(gallery_elapsed>=8){
            gallery_elapsed-=8;
            if(++gallery_step>=(gallery_night?4:8)){gallery_stop();AW_UISubtitle("","Sky gallery finished; real game time restored.",4);}
            else gallery_label();
        }
        return;
    }
    if(modal || sv.paused || key_dest!=key_game || cls.state!=ca_connected ||
       AW_IntroUse() || AW_ReaderActive() || !(daynightcycle.value>0))return;
    delta=host_frametime*timescale.value*1000;
    if(delta>0 && delta<=86400000){
        delta+=clock_fraction;whole=(int)delta;
        if(AW_ClockAdvance(whole))clock_fraction=delta-whole;
    }
}
int AW_WaitKey(int key) {
    char line[80];int y,m,d,h,n;
    if(cycle_steps && key_dest==key_game && key==K_ESCAPE){cycle_stop("24 h cycle stopped.");return 1;}
    if(light_active && key_dest==key_game){
        if(key==K_ESCAPE){light_active=0;AW_UISubtitle("","Light gallery closed; real time shown.",3);return 1;}
        if(key==K_UPARROW){light_row=(light_row+LIGHT_ROWS-1)%LIGHT_ROWS;return 1;}
        if(key==K_DOWNARROW){light_row=(light_row+1)%LIGHT_ROWS;return 1;}
        if(key==K_LEFTARROW || key==K_RIGHTARROW){light_change(key==K_RIGHTARROW?1:-1);return 1;}
    }
    if(gallery_active && key_dest==key_game && key==K_ESCAPE){
        gallery_stop();AW_UISubtitle("","Sky gallery off; real game time restored.",4);return 1;
    }
    if(!modal){
        /* Help remains reachable during text entry without stealing printable
         * name characters or hard-wiring a key that the player has rebound. */
        if(key_dest==key_game && key>=128 && key<256 && keybindings[key] &&
           !strcmp(keybindings[key],"aw_quick_help")){quick_help();return 1;}
        return 0;
    }
    if(key_dest!=key_menu){modal=0;return 0;}
    if(key==K_ESCAPE || (modal==2 && (key==K_ENTER || key==K_F1))){close_modal();return 1;}
    if(modal==2){
        if(key==K_LEFTARROW || key==K_RIGHTARROW || key==K_PGDN || key==K_PGUP || key==K_TAB)help_page=(help_page+(key==K_LEFTARROW || key==K_PGUP?-1:1)+help_pages())%help_pages();
        return 1;
    }
    if(key==K_LEFTARROW || key==K_DOWNARROW || key=='a' || key=='s'){if(hours>1)hours--;}
    if(key==K_RIGHTARROW || key==K_UPARROW || key=='d' || key=='w'){if(hours<24)hours++;}
    if(key==K_ENTER){
        if(!allowed()){close_modal();return 1;}
        if(!AW_ClockAdvance(hours*3600000)){close_modal();AW_UISubtitle("","Could not advance the clock.",4);return 1;}
        clock_fraction=0;
        AW_ClockDate(&y,&m,&d,&h,&n);close_modal();
        sprintf(line,"Waited %ld hour%s. %02ld:%02ld, %02ld/%02ld/%ld",(long)hours,hours==1?"":"s",(long)h,(long)n,(long)d,(long)m,(long)y);
        AW_UISubtitle("",line,5);
    }
    return 1;
}
int AW_WaitDraw(void) {
    int y,m,d,h,n;char line[96];
    if(!modal || key_dest!=key_menu)return 0;
    AW_UIBox(18,24,284,152);AW_UISmallBegin();
    if(modal==1){
        AW_ClockDate(&y,&m,&d,&h,&n);
        AW_UITextBox(26,32,268,20,"Wait",-1);
        sprintf(line,"%02ld:%02ld  %02ld/%02ld/%ld",(long)h,(long)n,(long)d,(long)m,(long)y);
        AW_UITextBox(26,57,268,20,line,-1);
        sprintf(line,"Wait for %ld hour%s",(long)hours,hours==1?"":"s");AW_UITextBox(26,85,268,22,line,-1);
        AW_UITextBox(26,116,268,20,"Arrows / A D: 1 to 24 hours",-1);
        AW_UITextBox(26,143,268,20,"Enter: wait   Esc: cancel",-1);
    }else{
        int i,k,row=0,skip=help_page*HELP_ROWS,ch=AW_ConsoleCharHeight();const char *action;
        AW_UISmallEnd();AW_UIBox(2,2,316,196);
        if(!AW_UILogo(60,6))AW_UITextBox(10,6,300,36,"AmiWind",-1);
        sprintf(line,"Current keys - page %ld/%ld",(long)help_page+1,(long)help_pages());help_text(12,48,line);
        for(k=0;k<256 && row<HELP_ROWS;k++)if(keybindings[k] && *keybindings[k]){
            if(skip){skip--;continue;}
            action=keybindings[k];
            for(i=0;i<HELP_COUNT;i++)if(!strcmp(action,help_commands[i])){action=help_actions[i];break;}
            snprintf(line,sizeof(line),"%s: %s",Key_KeynumToString(k),action);
            help_text(12,66+row*(ch+3),line);row++;
        }
        help_text(12,165,"F10: console half / full / closed");
        help_text(12,180,"Arrows: page  Enter/Esc: return");
        scr_copyeverything=1;return 1;
    }
    AW_UISmallEnd();scr_copyeverything=1;return 1;
}
