/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_clock.h"
#include "aw_sky.h"
#include <assert.h>
viddef_t vid;
int AW_ConsoleCharWidth(void){return 8;}int AW_ConsoleCharHeight(void){return 8;}
void AW_ConsoleCharacter(int x,int y,int c){assert(x>=0 && y>=0 && x+8<=320 && y+8<=200);}
char *Key_KeynumToString(int k){return "F1";}int AW_UILogo(int x,int y){return 1;}
client_state_t cl;refdef_t r_refdef;
static model_t world;static vec3_t seen_origin,seen_angles;
void R_RenderView(void){memcpy(seen_origin,r_refdef.vieworg,sizeof seen_origin);memcpy(seen_angles,r_refdef.viewangles,sizeof seen_angles);}
client_static_t cls;server_t sv;server_static_t svs;keydest_t key_dest=key_game;
double host_frametime=1;char *keybindings[256];int scr_copyeverything;
static void (*open_wait)(void),(*help)(void),(*settime)(void),(*setexact)(void),(*gallery)(void),(*nightgallery)(void);static edict_t player;static client_t client;
static int restricted,speech,interior,argc=1;static char *arg="";static cvar_t *scale,*cycle;
int AW_Interior(void){return interior;}
void Con_ToggleConsole_f(void){key_dest=key_game;}
int AW_CharacterActive(void){return 0;}int AW_ReaderActive(void){return 0;}int AW_IntroUse(void){return restricted;}
int AW_StoryRestricted(void){return restricted;}double AW_SpeechRemaining(void){return speech;}
static char subtitle[256];
void IN_AWClearButtons(void){}void AW_UISubtitle(const char *a,const char *b,double d){snprintf(subtitle,sizeof subtitle,"%s",b);}
void Con_Printf(char *s,...){}void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);if(!strcmp(c->name,"aw_timescale"))scale=c;else if(!strcmp(c->name,"aw_daynightcycle"))cycle=c;else assert(0);}
void Cmd_AddCommand(char *n,void(*f)(void)){if(!strcmp(n,"aw_wait"))open_wait=f;else if(!strcmp(n,"aw_quick_help"))help=f;else if(!strcmp(n,"aw_timeofday"))settime=f;else if(!strcmp(n,"aw_set_time"))setexact=f;else if(!strcmp(n,"aw_daycycle_gallery"))gallery=f;else if(!strcmp(n,"aw_nightgallery"))nightgallery=f;}
int Cmd_Argc(void){return argc;}char *Cmd_Argv(int i){return arg;}int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void AW_UIBox(int x,int y,int w,int h){}void AW_UISmallBegin(void){}void AW_UISmallEnd(void){}
void AW_UITextBox(int x,int y,int w,int h,const char *s,int c){assert(x>=0 && y>=0 && x+w<=320 && y+h<=200);}
static void date(int year,int month,int day,int hour,int minute){int y,m,d,h,n;AW_ClockDate(&y,&m,&d,&h,&n);assert(y==year && m==month && d==day && h==hour && n==minute);}
static void tour_camera(void){
    static const float expected[8][3]={{10,135,0},{-5,348,0},{-65,270,0},
        {-10,180,0},{-20,190,0},{-20,190,0},{-10,180,0},{10,135,0}};
    client_state_t original_client;edict_t original_player;aw_state_t original_state;
    refdef_t original_view;int step,i;
    strcpy(sv.name,"seyda");strcpy(world.name,"maps/sn045.bsp");cl.worldmodel=&world;cl.viewheight=17.5f;
    for(i=0;i<3;i++){r_refdef.vieworg[i]=11+i;r_refdef.viewangles[i]=21+i;cl.viewangles[i]=31+i;player.v.origin[i]=41+i;}
    original_client=cl;original_player=player;original_state=aw_state;original_view=r_refdef;
    argc=1;key_dest=key_console;host_frametime=.25;gallery();assert(key_dest==key_game);
    for(step=0;step<8;step++){
        V_RenderCameraView();
        assert(seen_origin[0]==100+1.0f/32 && seen_origin[1]==-180+1.0f/32);
        assert(seen_origin[2]==((step==3 || step==6)?240:180)+cl.viewheight+1.0f/32);
        assert(!memcmp(seen_angles,expected[step],sizeof seen_angles));
        assert(!memcmp(&original_view,&r_refdef,sizeof r_refdef));
        assert(!memcmp(&original_client,&cl,sizeof cl) && !memcmp(&original_player,&player,sizeof player));
        assert(!memcmp(&original_state,&aw_state,sizeof aw_state));
        for(i=0;i<32;i++)AW_WaitTick();
    }
    V_RenderCameraView();assert(!memcmp(seen_origin,original_view.vieworg,sizeof seen_origin) && !memcmp(seen_angles,original_view.viewangles,sizeof seen_angles));
    /* Here mode keeps the exact current camera while previewing sky time. */
    argc=2;arg="here";gallery();V_RenderCameraView();
    assert(AW_DayGalleryClock(99)==330*60000 && !memcmp(seen_origin,original_view.vieworg,sizeof seen_origin) && !memcmp(seen_angles,original_view.viewangles,sizeof seen_angles));
    assert(AW_WaitKey(K_ESCAPE));V_RenderCameraView();assert(!memcmp(&original_view,&r_refdef,sizeof r_refdef));
    /* The same catalogue scene name can switch its actual region BSP. */
    argc=1;gallery();strcpy(world.name,"maps/sn029.bsp");V_RenderCameraView();
    assert(AW_DayGalleryClock(99)==99 && !memcmp(seen_angles,original_view.viewangles,sizeof seen_angles));
    gallery();V_RenderCameraView(); /* another BSP: angles only, no borrowed coordinates */
    assert(!memcmp(seen_origin,original_view.vieworg,sizeof seen_origin));
    assert(!memcmp(seen_angles,expected[0],sizeof seen_angles));
    assert(AW_WaitKey(K_ESCAPE));V_RenderCameraView();
    assert(!memcmp(seen_angles,original_view.viewangles,sizeof seen_angles));
    assert(!memcmp(&original_state,&aw_state,sizeof aw_state));
    strcpy(world.name,"maps/sn045.bsp");strcpy(sv.name,"sn045");
}
static void night_tour_camera(void){
    client_state_t original_client;edict_t original_player;aw_state_t original_state;
    refdef_t original_view;float direction[3],forward[3],pitch,yaw;int day,step,i,visible,hidden=0;
    float original_scale=scale->value,original_cycle=cycle->value;
    assert(nightgallery);strcpy(sv.name,"seyda");strcpy(world.name,"maps/sn045.bsp");
    cl.worldmodel=&world;host_frametime=.25;key_dest=key_game;
    for(i=0;i<3;i++){r_refdef.vieworg[i]=41+i;r_refdef.viewangles[i]=11+i;cl.viewangles[i]=21+i;player.v.origin[i]=31+i;}
    original_client=cl;original_player=player;original_view=r_refdef;
    /* Every source phase/day, including moons below the horizon, without
     * changing eye position even on the day tour's special Seyda map. */
    for(day=0;day<24;day++){
        assert(AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:days",day));original_state=aw_state;
        argc=1;key_dest=key_console;nightgallery();assert(key_dest==key_game);
        for(step=0;step<4;step++){
            assert(AW_DayGalleryClock(99)==1380*60000);V_RenderCameraView();
            assert(!memcmp(seen_origin,original_view.vieworg,sizeof seen_origin));
            if(step==0)assert(!memcmp(seen_angles,original_view.viewangles,sizeof seen_angles));
            else if(step==3)assert(seen_angles[0]==-85 && seen_angles[1]==original_view.viewangles[1] && seen_angles[2]==0);
            else{
                visible=R_NightMoonOrbit(step-1,1380*60000,day,direction,NULL);
                assert(strstr(subtitle,step==1?"Masser":"Secunda"));
                if(!visible){hidden++;assert(strstr(subtitle,"below horizon"));assert(!memcmp(seen_angles,original_view.viewangles,sizeof seen_angles));}
                else{
                    assert(!strstr(subtitle,"below horizon"));pitch=seen_angles[0]*(M_PI/180);yaw=seen_angles[1]*(M_PI/180);
                    forward[0]=cos(pitch)*cos(yaw);forward[1]=cos(pitch)*sin(yaw);forward[2]=-sin(pitch);
                    for(i=0;i<3;i++)assert(fabs(forward[i]-direction[i])<.000001);
                }
            }
            assert(!memcmp(&original_view,&r_refdef,sizeof r_refdef));
            assert(!memcmp(&original_client,&cl,sizeof cl) && !memcmp(&original_player,&player,sizeof player));
            assert(!memcmp(&original_state,&aw_state,sizeof aw_state));
            for(i=0;i<32;i++)AW_WaitTick();
        }
        assert(AW_DayGalleryClock(99)==99);V_RenderCameraView();
        assert(!memcmp(seen_angles,original_view.viewangles,sizeof seen_angles));
    }
    assert(hidden>0 && scale->value==original_scale && cycle->value==original_cycle);
    argc=2;arg="HeRe";nightgallery();
    for(step=0;step<4;step++){
        V_RenderCameraView();assert(!memcmp(seen_origin,original_view.vieworg,sizeof seen_origin) && !memcmp(seen_angles,original_view.viewangles,sizeof seen_angles));
        assert(AW_DayGalleryClock(99)==1380*60000);for(i=0;i<32;i++)AW_WaitTick();
    }
    assert(AW_DayGalleryClock(99)==99);
    argc=1;nightgallery();key_dest=key_console;for(i=0;i<128;i++)AW_WaitTick();
    key_dest=key_game;assert(AW_DayGalleryClock(99)==1380*60000 && strstr(subtitle,"Wide view"));
    assert(AW_WaitKey(K_ESCAPE) && AW_DayGalleryClock(99)==99);
    nightgallery();nightgallery();assert(AW_DayGalleryClock(99)==99);
    nightgallery();argc=2;arg="off";nightgallery();assert(AW_DayGalleryClock(99)==99);
    arg="bad";nightgallery();argc=3;nightgallery();assert(AW_DayGalleryClock(99)==99);
    argc=1;nightgallery();strcpy(world.name,"maps/sn029.bsp");assert(AW_DayGalleryClock(99)==99);
    nightgallery();cls.state=ca_disconnected;assert(AW_DayGalleryClock(99)==99);cls.state=ca_connected;
    interior=1;nightgallery();assert(AW_DayGalleryClock(99)==99);interior=0;
    nightgallery();sv.active=0;AW_WaitTick();sv.active=1;assert(AW_DayGalleryClock(99)==99);
    assert(!memcmp(&original_state,&aw_state,sizeof aw_state));
}
int main(void){
    aw_state_t saved;int i;char exact[5];
    const char *bad[]={"","1","630","00000","2400","2360","0060","-100","+100","12.0","NaN","12:30","0630x"," 630","0630 ","0x10","tomorrow"};
    strcpy(world.name,"maps/sn045.bsp");cl.worldmodel=&world;
    vid.width=320;vid.height=200;sv.active=1;svs.maxclients=1;svs.clients=&client;client.edict=&player;cls.state=ca_connected;
    player.v.health=100;player.v.movetype=MOVETYPE_WALK;player.v.flags=FL_ONGROUND;
    AW_StateReset();AW_WaitInit();assert(open_wait && help && settime && setexact);date(427,8,16,9,0);
    assert(cycle && cycle->value==1 && cycle->archive && scale->value==30 && scale->archive);
    AW_WaitTick();AW_WaitTick();date(427,8,16,9,1);
    cycle->value=0;saved=aw_state;AW_WaitTick();assert(!memcmp(&saved,&aw_state,sizeof saved));
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
    /* Exact command covers every minute, preserving date and resetting seconds. */
    for(i=0;i<1440;i++){sprintf(exact,"%02d%02d",i/60,i%60);arg=exact;setexact();date(427,8,18,i/60,i%60);assert(AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms")==i*60000);}
    saved=aw_state;for(i=0;i<sizeof(bad)/sizeof(bad[0]);i++){arg=(char *)bad[i];setexact();assert(!memcmp(&saved,&aw_state,sizeof saved));}
    arg="0630";argc=1;setexact();argc=3;setexact();argc=2;sv.active=0;setexact();sv.active=1;assert(!memcmp(&saved,&aw_state,sizeof saved));
    arg="DaWn";setexact();date(427,8,18,5,30);arg="dusk";setexact();date(427,8,18,19,0);
    arg="sunset";setexact();date(427,8,18,18,0);arg="night";setexact();date(427,8,18,0,0);
    arg="evening";setexact();date(427,8,18,17,0);arg="morning";setexact();date(427,8,18,9,0);
    arg="midday";setexact();date(427,8,18,12,0);arg="day";setexact();date(427,8,18,14,0);arg="sunrise";setexact();date(427,8,18,6,0);
    arg="dawn";settime();date(427,8,18,5,30);arg="dusk";settime();date(427,8,18,19,0);
    arg="evening";settime();date(427,8,18,18,0);
    saved=aw_state;assert(!AW_ClockSetTime(24,0) && !AW_ClockSetTime(0,60) && !AW_ClockSetTime(-1,0) && !AW_ClockSetTime(0,-1));assert(!memcmp(&saved,&aw_state,sizeof saved));
    /* Explicit set and both 1/24-hour waits above worked while automatic time was off. */
    scale->value=0;cycle->value=1;AW_WaitTick();assert(!memcmp(&saved,&aw_state,sizeof saved));scale->value=30;AW_WaitTick();assert(AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms")==64830000);
    arg="0630";setexact();scale->value=1;host_frametime=.00025;
    for(i=0;i<3;i++)AW_WaitTick();assert(AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms")==23400000);
    cycle->value=0;host_frametime=60;AW_WaitTick();date(427,8,18,6,30);
    cycle->value=1;host_frametime=.00025;AW_WaitTick();assert(AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms")==23400001);
    for(i=0;i<3996;i++)AW_WaitTick();assert(AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms")==23401000);
    saved=aw_state;sv.active=0;AW_WaitTick();sv.active=1;assert(!memcmp(&saved,&aw_state,sizeof saved) && cycle->value==1);
    host_frametime=1;scale->value=30;
    AW_StateReset();assert(AW_ClockEnsure());for(i=0;i<138;i++)assert(AW_ClockAdvance(86400000));date(428,1,1,9,0);
    assert(!AW_ClockAdvance(-1) && !AW_ClockAdvance(86400001));
    saved=aw_state;keybindings[K_F1]="aw_quick_help";assert(AW_WaitKey(K_F1));assert(AW_WaitDraw());
    AW_WaitTick();AW_WaitKey(K_ESCAPE);assert(!memcmp(&saved,&aw_state,sizeof(saved)));
    keybindings[K_F1]="other";assert(!AW_WaitKey(K_F1));
    /* Preview clock is presentation-only: every phase, cancel, invalid input,
     * console pause, map change and disconnection preserve persistent state. */
    saved=aw_state;assert(gallery);strcpy(sv.name,"sn045");argc=1;host_frametime=.25;
    gallery();assert(AW_DayGalleryClock(1234)==330*60000);
    open_wait();assert(key_dest==key_game);
    for(i=0;i<31;i++)AW_WaitTick();assert(AW_DayGalleryClock(1234)==330*60000);
    AW_WaitTick();assert(AW_DayGalleryClock(1234)==390*60000);
    key_dest=key_console;for(i=0;i<64;i++)AW_WaitTick();key_dest=key_game;
    assert(AW_DayGalleryClock(1234)==390*60000);
    for(i=0;i<6*32;i++)AW_WaitTick();assert(AW_DayGalleryClock(1234)==1380*60000);
    for(i=0;i<32;i++)AW_WaitTick();assert(AW_DayGalleryClock(1234)==1234);
    assert(!memcmp(&saved,&aw_state,sizeof saved) && cycle->value==1 && scale->value==30);
    key_dest=key_console;gallery();assert(key_dest==key_game && AW_DayGalleryClock(77)==330*60000);
    assert(AW_WaitKey(K_ESCAPE) && AW_DayGalleryClock(77)==77);
    argc=2;arg="garbage";gallery();assert(AW_DayGalleryClock(77)==77);
    argc=3;gallery();assert(AW_DayGalleryClock(77)==77);
    argc=1;gallery();argc=2;arg="off";gallery();assert(AW_DayGalleryClock(77)==77);
    argc=1;gallery();gallery();assert(AW_DayGalleryClock(77)==77);
    gallery();strcpy(sv.name,"sn012");assert(AW_DayGalleryClock(77)==77);
    gallery();cls.state=ca_disconnected;assert(AW_DayGalleryClock(77)==77);cls.state=ca_connected;
    interior=1;gallery();assert(AW_DayGalleryClock(77)==77);interior=0;
    cycle->value=0;gallery();AW_WaitTick();assert(AW_WaitKey(K_ESCAPE) && cycle->value==0);
    gallery();sv.active=0;AW_WaitTick();sv.active=1;assert(AW_DayGalleryClock(77)==77);
    assert(!memcmp(&saved,&aw_state,sizeof saved));
    tour_camera();night_tour_camera();
    AW_StateReset();for(i=0;i<31;i++){char name[32];sprintf(name,"full%ld",(long)i);AW_StateSet(&aw_state,AW_GLOBAL,name,i);}
    saved=aw_state;assert(!AW_ClockEnsure() && !memcmp(&saved,&aw_state,sizeof(saved)));
    return 0;
}
