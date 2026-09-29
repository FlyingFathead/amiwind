/* SPDX-License-Identifier: GPL-2.0-or-later
 * Waiting advances the persistent clock; NPC scheduling/rest recovery and sky
 * rendering are separate systems. The modal uses the existing single-player
 * menu pause, leaving the music service running.
 */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_clock.h"
static int modal,hours=1,help_page;
static const char *help_commands[]={"+forward","+back","+moveleft","+moveright","+attack","+aw_use","impulse 202","aw_wait","aw_quicksave","aw_quickload","toggleconsole","aw_quick_help","togglemenu"};
static const char *help_actions[]={"Move forward","Move back","Move left","Move right","Attack","Activate","Ready hands","Wait","Quicksave","Quickload","Console","Quick help","Pause menu"};
#define HELP_COUNT 13
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
    if(modal || key_dest!=key_game)return;
    if(!allowed()){AW_UISubtitle("","Wait after registration, on dry ground, when no one is speaking.",5);return;}
    if(!AW_ClockEnsure()){Con_Printf("Clock state unavailable.\n");return;}
    hours=1;open_modal(1);
}
static void quick_help(void){if(!modal && key_dest==key_game){help_page=0;open_modal(2);}}
static void timeofday(void) {
    static const char *names[]={"morning","night","midday","day","evening","sunset","sunrise"};
    static const int values[]={9,0,12,14,18,19,6};
    char *s=Cmd_Argv(1),*end;double hour;int i,y,m,d,h,n;
    if(!sv.active){Con_Printf("Start the local game first.\n");return;}
    if(Cmd_Argc()==2){
        for(i=0;i<7;i++)if(!Q_strcasecmp(s,(char *)names[i]))break;
        if(i<7)hour=values[i];else{hour=strtod(s,&end);if(!*s || *end)hour=-1;}
        if(!AW_ClockSetHour(hour)){Con_Printf("dbg timeofday 0..23.999 / morning night midday day evening sunset sunrise\n");return;}
    }else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg timeofday [hour or named time]\n");return;}
    AW_ClockDate(&y,&m,&d,&h,&n);
    Con_Printf("Time %02ld:%02ld, %02ld/%02ld/%ld (day/month/year)\n",(long)h,(long)n,(long)d,(long)m,(long)y);
}
void AW_WaitInit(void){
    Cvar_RegisterVariable(&timescale);Cmd_AddCommand("aw_wait",wait_open);
    Cmd_AddCommand("aw_quick_help",quick_help);Cmd_AddCommand("aw_timeofday",timeofday);
}
void AW_WaitTick(void) {
    double delta;
    if(!sv.active){modal=0;return;}
    if(modal || sv.paused || key_dest!=key_game || cls.state!=ca_connected ||
       AW_IntroUse() || AW_ReaderActive())return;
    delta=host_frametime*timescale.value*1000;
    if(delta>0 && delta<=86400000)AW_ClockAdvance((int)delta);
}
int AW_WaitKey(int key) {
    char line[80];int y,m,d,h,n;
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
        help_text(12,165,"Mouse: look. Console: bind key command");
        help_text(12,180,"Arrows: page  Enter/Esc: return");
        scr_copyeverything=1;return 1;
    }
    AW_UISmallEnd();scr_copyeverything=1;return 1;
}
