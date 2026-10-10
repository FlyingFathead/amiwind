/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "input.h"
#include <assert.h>
#include <math.h>

client_state_t cl;
client_static_t cls;
double host_frametime=.02;
double Q_GammaPow(double x,double g){return pow(x,g);} /* mathlib.c is not linked here */
qboolean noclip_anglehack;
keydest_t key_dest=key_game;
kbutton_t in_mlook, in_strafe;
int mouseX,mouseY;
qboolean mouse_has_moved;
extern cvar_t aw_auto_center,v_centermove,v_centerspeed;
cvar_t cl_forwardspeed={"cl_forwardspeed","200",false,false,200};
extern void V_Init(void);
extern void V_DriftPitch(void);
extern void V_StartPitchDrift(void);
extern void V_CenterView_f(void);
extern qboolean V_ExplicitPitchCentering(void);
cvar_t sensitivity={"sensitivity","1",false,false,1};
cvar_t lookstrafe={"lookstrafe","0",false,false,0};
cvar_t m_side={"m_side","1",false,false,1};
cvar_t m_pitch={"m_pitch","1",false,false,1};
cvar_t m_yaw={"m_yaw","1",false,false,1};
cvar_t m_forward={"m_forward","1",false,false,1};
static int registered_cvar_count,centerview_registered;
void Cvar_RegisterVariable(cvar_t *v){v->value=atof(v->string);if(!strcmp(v->name,"aw_auto_center")){assert(v->archive);registered_cvar_count++;}}
char *Cmd_Argv(int i){return "";}
void Cmd_AddCommand(char *name,void (*fn)(void)){if(!strcmp(name,"centerview")){assert(fn==V_CenterView_f);centerview_registered++;}}
int AW_ReaderActive(void){return 0;}
int AW_CharacterActive(void){return 0;}
int AW_GalleryModal(void){return 0;}
int AW_WorldUIActive(void){return 0;}
void AW_WorldUIMouse(int x,int y){}
void AW_MenuMouse(int x,int y){}
void AW_ReaderMouse(int x,int y){}
void AW_CharacterMouse(int x,int y){}
void AW_GalleryMouse(int x,int y){}
int main(void){
 usercmd_t move;int i;
 memset(&cl,0,sizeof(cl));memset(&cls,0,sizeof(cls));memset(&move,0,sizeof(move));
 cl.onground=true;cl_forwardspeed.value=200;cl.cmd.forwardmove=200;
 V_Init();
 assert(registered_cvar_count==1 && centerview_registered==1);
 aw_auto_center.value=0;
 assert(aw_auto_center.value==0 && aw_auto_center.archive && !strcmp(aw_auto_center.string,"0"));
 v_centermove.value=.15f;v_centerspeed.value=500;
 /* Start with the zeroed local drift fields seen on a fresh client. */
 cl.viewangles[PITCH]=20;cl.idealpitch=0;cl.nodrift=false;cl.pitchvel=0;
 for(i=0;i<80;i++)V_DriftPitch();
 assert(cl.viewangles[PITCH]==20 && cl.nodrift && cl.pitchvel==0 && cl.driftmove==0);
 /* Automatic helper/look-spring start stays off, but explicit centerview works. */
 cl.time=1;in_mlook.state=1;V_StartPitchDrift();assert(cl.nodrift && cl.pitchvel==0);
 mouse_has_moved=false;mouseX=mouseY=0;IN_Move(&move);
 assert(cl.nodrift && cl.pitchvel==0);
 V_CenterView_f();assert(!cl.nodrift && cl.pitchvel==500); /* same-frame explicit command wins */
 IN_Move(&move);assert(!cl.nodrift && cl.pitchvel==500); /* quiet mlook preserves explicit centerview */
 V_DriftPitch();assert(cl.viewangles[PITCH]<20 && cl.viewangles[PITCH]>0);
 for(i=0;i<10;i++)V_DriftPitch();
 assert(cl.viewangles[PITCH]==0);
 /* A real mouse pitch delta still overrides a deliberate centerview. */
 in_mlook.state=1;cl.time=1.5;V_CenterView_f();assert(V_ExplicitPitchCentering());
 IN_AWMouseEvent(0,1);IN_Move(&move);
 assert(!V_ExplicitPitchCentering() && cl.nodrift && cl.pitchvel==0 && cl.viewangles[PITCH]==4);
 in_mlook.state=0;
 /* Opting in restores the legacy forward-movement threshold and drift. */
 aw_auto_center.value=1;cl.time=2;cl.viewangles[PITCH]=20;cl.nodrift=true;cl.pitchvel=0;cl.driftmove=0;
 for(i=0;i<8;i++)V_DriftPitch();
 assert(!cl.nodrift && cl.pitchvel==500);
 V_DriftPitch();assert(cl.viewangles[PITCH]<20);
 /* Disabling legacy mode mid-drift stops it on the next view update. */
 {float before=cl.viewangles[PITCH];aw_auto_center.value=0;V_DriftPitch();
  assert(cl.viewangles[PITCH]==before && cl.nodrift && cl.pitchvel==0);}
 /* Held +mlook cancels drift with no new mouse event and cannot restart it. */
 cl.time=3;cl.viewangles[PITCH]=15;cl.nodrift=false;cl.pitchvel=500;cl.driftmove=.1f;
 cl.cmd.forwardmove=200;in_mlook.state=1;mouse_has_moved=false;mouseX=mouseY=0;
 memset(&move,0,sizeof(move));IN_Move(&move);
 assert(cl.nodrift && cl.pitchvel==0);
 for(i=0;i<40;i++)V_DriftPitch();
 assert(cl.viewangles[PITCH]==15 && cl.nodrift && cl.pitchvel==0 && cl.driftmove==0);
 puts("default-off centering, legacy opt-in, explicit centerview, and quiet-mouse +mlook passed");
 return 0;
}
