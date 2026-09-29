/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_clock.h"
#include <assert.h>
viddef_t vid;
int AW_ConsoleCharWidth(void){return 8;}int AW_ConsoleCharHeight(void){return 8;}
void AW_ConsoleCharacter(int x,int y,int c){assert(x>=0 && y>=0 && x+8<=320 && y+8<=200);}
char *Key_KeynumToString(int k){return "F1";}int AW_UILogo(int x,int y){return 1;}
client_static_t cls;server_t sv;server_static_t svs;keydest_t key_dest=key_game;
double host_frametime=1;char *keybindings[256];int scr_copyeverything;
static void (*open_wait)(void),(*help)(void),(*settime)(void);static edict_t player;static client_t client;
static int restricted,speech,argc=1;static char *arg="";static cvar_t *scale;
int AW_CharacterActive(void){return 0;}int AW_ReaderActive(void){return 0;}int AW_IntroUse(void){return restricted;}
int AW_StoryRestricted(void){return restricted;}double AW_SpeechRemaining(void){return speech;}
void IN_AWClearButtons(void){}void AW_UISubtitle(const char *a,const char *b,double d){}
void Con_Printf(char *s,...){}void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);scale=c;}
void Cmd_AddCommand(char *n,void(*f)(void)){if(!strcmp(n,"aw_wait"))open_wait=f;else if(!strcmp(n,"aw_quick_help"))help=f;else settime=f;}
int Cmd_Argc(void){return argc;}char *Cmd_Argv(int i){return arg;}int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void AW_UIBox(int x,int y,int w,int h){}void AW_UISmallBegin(void){}void AW_UISmallEnd(void){}
void AW_UITextBox(int x,int y,int w,int h,const char *s,int c){assert(x>=0 && y>=0 && x+w<=320 && y+h<=200);}
static void date(int year,int month,int day,int hour,int minute){int y,m,d,h,n;AW_ClockDate(&y,&m,&d,&h,&n);assert(y==year && m==month && d==day && h==hour && n==minute);}
int main(void){
    aw_state_t saved;int i;
    vid.width=320;vid.height=200;sv.active=1;svs.maxclients=1;svs.clients=&client;client.edict=&player;cls.state=ca_connected;
    player.v.health=100;player.v.movetype=MOVETYPE_WALK;player.v.flags=FL_ONGROUND;
    AW_StateReset();AW_WaitInit();assert(open_wait && help && settime);date(427,8,16,9,0);
    AW_WaitTick();AW_WaitTick();date(427,8,16,9,1);
    restricted=1;open_wait();assert(key_dest==key_game);restricted=0;
    speech=1;open_wait();assert(key_dest==key_game);speech=0;
    player.v.waterlevel=2;open_wait();assert(key_dest==key_game);player.v.waterlevel=0;
    open_wait();assert(key_dest==key_menu && AW_WaitDraw());saved=aw_state;
    AW_WaitTick();AW_WaitKey(K_RIGHTARROW);AW_WaitKey(K_ESCAPE);assert(key_dest==key_game && !memcmp(&saved,&aw_state,sizeof(saved)));
    open_wait();for(i=0;i<30;i++)AW_WaitKey(K_RIGHTARROW);AW_WaitKey(K_ENTER);date(427,8,17,9,1);
    open_wait();for(i=0;i<30;i++)AW_WaitKey(K_LEFTARROW);AW_WaitKey(K_ENTER);date(427,8,17,10,1);
    argc=2;arg="sunset";settime();date(427,8,17,19,0);arg="23.5";settime();date(427,8,17,23,30);
    arg="NaN";settime();date(427,8,17,23,30);arg="24";settime();date(427,8,17,23,30);
    assert(AW_ClockAdvance(3600000));date(427,8,18,0,30);
    AW_StateReset();assert(AW_ClockEnsure());for(i=0;i<138;i++)assert(AW_ClockAdvance(86400000));date(428,1,1,9,0);
    assert(!AW_ClockAdvance(-1) && !AW_ClockAdvance(86400001));
    saved=aw_state;keybindings[K_F1]="aw_quick_help";assert(AW_WaitKey(K_F1));assert(AW_WaitDraw());
    AW_WaitTick();AW_WaitKey(K_ESCAPE);assert(!memcmp(&saved,&aw_state,sizeof(saved)));
    keybindings[K_F1]="other";assert(!AW_WaitKey(K_F1));
    AW_StateReset();for(i=0;i<31;i++){char name[32];sprintf(name,"full%ld",(long)i);AW_StateSet(&aw_state,AW_GLOBAL,name,i);}
    saved=aw_state;assert(!AW_ClockEnsure() && !memcmp(&saved,&aw_state,sizeof(saved)));
    return 0;
}
