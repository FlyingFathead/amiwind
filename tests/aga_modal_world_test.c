/* SPDX-License-Identifier: GPL-2.0-or-later
 * Actual modal policy and host/client frame routines, with synthetic services.
 * MODAL_CLIENT selects real CL_ReadFromServer; otherwise run _Host_Frame. */
#include "quakedef.h"
#include <assert.h>

server_t sv;server_static_t svs;keydest_t key_dest=key_game;
viddef_t vid;refdef_t r_refdef;int scr_fullupdate,scr_copyeverything;
byte *draw_chars;
static cvar_t *freeze,*black,*mode;
static int character,reader,gallery,movie,clears,extra_audio;
static int physics,network,commands,presentation,audio,music,intro,waits,saves,scenes;
static int scenery,harvest,speech,tempents,packets,parsed;

int AW_CharacterActive(void){return character;}
int AW_ReaderActive(void){return reader;}
int AW_GalleryModal(void){return gallery;}
int AW_MovieActive(void){return movie;}
void IN_AWClearButtons(void){clears++;}
void Con_Printf(char *s,...){}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);if(!strcmp(c->name,"aw_modal_freeze"))freeze=c;else if(!strcmp(c->name,"aw_modal_black"))black=c;else if(!strcmp(c->name,"aw_ui_mode"))mode=c;}
void Cvar_SetValue(char *s,float value){if(freeze && !strcmp(s,freeze->name))freeze->value=value;else{assert(black && !strcmp(s,black->name));black->value=value;}}
void Cmd_AddCommand(char *s,void(*fn)(void)){}
char *Cmd_Argv(int n){return "";}
int Cmd_Argc(void){return 0;}
int COM_FOpenFile(char *s,FILE **f){*f=NULL;return -1;}

#ifdef MODAL_CLIENT
double host_frametime=.02,realtime;byte *host_basepal;
cvar_t chase_active;
void Host_Error(char *s,...){assert(0);}
int CL_GetMessage(void){if(packets){packets--;return 1;}return 0;}
void CL_ParseServerMessage(void){parsed++;cl.mtime[1]=cl.mtime[0];cl.mtime[0]=sv.time;}
void AW_SceneryLink(void){scenery++;}
void AW_HarvestLink(void){harvest++;}
void AW_SpeechRelink(void){speech++;}
void CL_UpdateTEnts(void){tempents++;}
void R_RemoveEfrags(entity_t *e){assert(0);}
void R_EntityParticles(entity_t *e){assert(0);}
void R_RocketTrail(vec3_t a,vec3_t b,int kind){assert(0);}
#else
client_static_t cls;client_state_t cl;
globalvars_t globals,*pr_global_struct=&globals;
vec3_t r_origin,vpn,vright,vup;
void _Host_Frame(float time);
void Sys_SendKeyEvents(void){}
void IN_Commands(void){}
void Cbuf_Execute(void){commands++;}
void Cbuf_AddText(char *s){assert(0);}
char *Sys_ConsoleInput(void){return NULL;}
void NET_Poll(void){network++;}
void CL_SendCmd(void){}
void SV_ClearDatagram(void){}
void SV_CheckForNewClients(void){}
void SV_RunClients(void){}
void SV_SendClientMessages(void){}
void SV_Physics(void){physics++;sv.time+=host_frametime;}
int CL_ReadFromServer(void){return 0;}
void SCR_UpdateScreen(void){presentation++;}
void S_Update(vec3_t a,vec3_t b,vec3_t c,vec3_t d){audio++;}
void S_ExtraUpdate(void){extra_audio++;}
void CDAudio_Update(void){music++;}
void CL_DecayLights(void){}
int AW_MovieDebugActive(void){return 0;}
void AW_MovieUpdate(void){}
void AW_StreamPresented(void){}
void AW_Mark(int n){}
void AW_EndMark(int n){}
void AW_IntroTick(void){intro++;}
void AW_WaitTick(void){waits++;}
void AW_SaveTick(void){saves++;}
void AW_SceneTick(void){scenes++;}
void AW_ProfileFrame(void){}
double Sys_FloatTime(void){return realtime;}
#endif

static void policy(void){
    int f,b;
    AW_UIInit();assert(freeze && freeze->archive && freeze->value==1);
    assert(black && black->archive && black->value==1);
    assert(mode && mode->archive && AW_UIMode()==2);
    mode->value=1;assert(AW_UIMode()==1);mode->value=0;assert(AW_UIMode()==2);mode->value=2;
    sv.active=true;svs.maxclients=1;cls.state=ca_connected;cls.signon=SIGNONS;
    assert(!AW_ModalWorldFrozen() && !AW_ModalWorldHidden());
    character=1;assert(AW_ModalWorldFrozen() && AW_ModalWorldHidden());
    scr_fullupdate=7;AW_ModalFrame();assert(clears && !scr_fullupdate);
    sv.paused=true;key_dest=key_menu;AW_ModalFrame();assert(sv.paused);
    key_dest=key_console;assert(AW_ModalWorldFrozen());
    key_dest=key_game;character=0;reader=1;assert(AW_ModalWorldFrozen());
    reader=0;gallery=1;assert(AW_ModalWorldFrozen());
    gallery=0;key_dest=key_menu;assert(AW_ModalWorldFrozen());
    /* Map, journal, wait/help, travel and save all use key_menu ownership. */
    for(f=0;f<=1;f++)for(b=0;b<=1;b++){
        Cvar_SetValue(freeze->name,f);Cvar_SetValue(black->name,b);
        assert(AW_ModalWorldFrozen()==f && AW_ModalWorldHidden()==b);
    }
    /* Black-only changes still force a whole redraw on switchback. */
    AW_ModalFrame();scr_fullupdate=7;black->value=0;AW_ModalFrame();
    assert(!scr_fullupdate && AW_ModalWorldFrozen());black->value=1;
    Cvar_SetValue(freeze->name,1);svs.maxclients=2;assert(!AW_ModalWorldFrozen());
    svs.maxclients=1;sv.active=false;assert(!AW_ModalWorldFrozen());
    sv.active=true;cls.signon=3;assert(!AW_ModalWorldFrozen());
    cls.signon=SIGNONS;cls.demoplayback=true;assert(!AW_ModalWorldFrozen());
    cls.demoplayback=false;movie=1;assert(!AW_ModalWorldFrozen());movie=0;
    cls.state=ca_disconnected;assert(!AW_ModalWorldFrozen());cls.state=ca_connected;
    key_dest=key_game;scr_fullupdate=7;AW_ModalFrame();assert(!scr_fullupdate && sv.paused);
    assert(!AW_ModalWorldFrozen());sv.paused=false;
}
void AW_RemotePoll(void){}
int main(void){
    int i,f,b;double before;
    policy();character=1;sv.time=7;cl.time=7;
#ifdef MODAL_CLIENT
    cl.mtime[0]=7;cl.mtime[1]=6.98;
    for(i=0;i<200;i++){black->value=i&1;realtime+=host_frametime;packets=1;CL_ReadFromServer();}
    assert(cl.time==7 && cl.oldtime==7 && parsed==200);
    assert(!scenery && !harvest && !speech && !tempents);
    /* Resume uses one frame, never the four elapsed seconds spent in UI. */
    character=0;sv.time=7.02;packets=1;CL_ReadFromServer();
    assert(fabs(cl.time-7.02)<.00001 && cl.oldtime==7 && parsed==201);
    assert(scenery==1 && harvest==1 && speech==1 && tempents==1);
    character=1;freeze->value=0;sv.time=7.04;packets=1;CL_ReadFromServer();
    assert(fabs(cl.time-7.04)<.00001 && scenery==2 && harvest==2);
#else
    for(i=0;i<200;i++)_Host_Frame(.02f);
    assert(!physics && sv.time==7 && !intro && !waits && !scenes);
    assert(presentation==200 && audio==200 && extra_audio==200 && music==400 && saves==200);
    assert(commands==200 && network==200 && realtime>3.99);
    character=0;before=sv.time;_Host_Frame(.02f);
    assert(physics==1 && fabs(sv.time-before-.02)<.00001);
    assert(intro==1 && waits==1 && scenes==1 && presentation==201);
    character=1;sv.paused=true;_Host_Frame(.02f);character=0;_Host_Frame(.02f);
    assert(sv.paused && physics==1);sv.paused=false;
    character=1;freeze->value=0;_Host_Frame(.02f);assert(physics==2);
    /* Disabling the new policy preserves the old menu pause rule. */
    key_dest=key_menu;_Host_Frame(.02f);assert(physics==2);
    /* Execute the real host path in all four combinations. UI, soundtrack,
     * mixer and network service counts must not depend on either setting. */
    key_dest=key_game;character=1;
    for(f=0;f<=1;f++)for(b=0;b<=1;b++){
        int a=audio,m=music,e=extra_audio,p=presentation,n=network,s=physics;
        freeze->value=f;black->value=b;
        for(i=0;i<40;i++)_Host_Frame(.02f);
        assert(audio-a==40 && music-m==80 && extra_audio-e==40);
        assert(presentation-p==40 && network-n==40 && physics-s==(f?0:40));
    }
#endif
    return 0;
}
