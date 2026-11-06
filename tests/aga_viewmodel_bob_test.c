/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>

client_state_t cl;
client_static_t cls;
kbutton_t in_mlook;
server_t sv;
server_static_t svs;
entity_t cl_entities[MAX_EDICTS];
refdef_t r_refdef;
viddef_t vid;
entity_t *currententity;
vec3_t modelorg, vpn, vright, vup;
float aliasxscale, aliasyscale;
double host_frametime=.02;
qboolean noclip_anglehack;
cvar_t cl_forwardspeed={"cl_forwardspeed","200",false,false,200};
cvar_t chase_active={"chase_active","0",false,false,0};
cvar_t scr_viewsize={"viewsize","100",false,false,100};
extern cvar_t aw_torch_depth_bob, cl_rollangle, aw_noclipwobble;
extern mdl_t *pmdl;
static mdl_t synthetic_model;
static int torch_equipped, bob_registered;
int AW_TorchEquipped(void){return torch_equipped;}
int aw_fp_stiff;   /* aw_hands.c's, set by view.c from aw_fp_sway (FP-WEAPON-SWAY-61) */
void Chase_Update(void){assert(0);}
char *Cmd_Argv(int n){return "0";}
void Cmd_AddCommand(char *name,void(*fn)(void)){}
void Cvar_RegisterVariable(cvar_t *c){
 c->value=atof(c->string);
 if(!strcmp(c->name,"aw_torch_depth_bob")){
  assert(c->archive && !strcmp(c->string,"0"));bob_registered++;
 }
}
extern void V_CalcRefdef(void);
extern float V_CalcBob(void);
extern void R_AliasSetUpTransform(int trivial_accept);
extern void R_AliasTransformVector(vec3_t in,vec3_t out);

static void setup(double t,float speed,float pitch,float yaw){
 memset(&cl,0,sizeof(cl));memset(&cls,0,sizeof(cls));
 memset(cl_entities,0,sizeof(cl_entities));memset(&r_refdef,0,sizeof(r_refdef));
 cls.state=ca_connected;cl.viewentity=1;cl.viewheight=12;
 cl.nodrift=true;cl.stats[STAT_HEALTH]=100;
 cl.time=t;cl.oldtime=t-.02;cl.velocity[0]=speed;
 cl.viewangles[PITCH]=pitch;cl.viewangles[YAW]=yaw;
}
static void renderer_point(vec3_t point,vec3_t transformed){
 currententity=&cl.viewent;
 VectorSubtract(r_refdef.vieworg,currententity->origin,modelorg);
 AngleVectors(r_refdef.viewangles,vpn,vright,vup);
 pmdl=&synthetic_model;
 R_AliasSetUpTransform(0);R_AliasTransformVector(point,transformed);
}
int main(void){
 static const double phases[]={.001,.075,.15,.225,.3,.375,.45,.525,.599};
 static const float speeds[]={0,80,160,320};
 static const float pitches[]={-40,0,45};
 static const float yaws[]={0,90,236};
 vec3_t stable_origin,stable_angles,stable_point,legacy_point,fwd,right,up,delta;
 vec3_t point={4.5f,2,-2},world_camera,world_angles;
 float bob;int i,j,k,y,n,legacy_visible=0,legacy_clipped=0;
 V_Init();assert(bob_registered==1);cl_rollangle.value=0;
 synthetic_model.scale[0]=synthetic_model.scale[1]=synthetic_model.scale[2]=1;
 for(i=0;i<9;i++)for(j=0;j<4;j++)for(k=0;k<3;k++)for(y=0;y<3;y++){
  setup(phases[i],speeds[j],pitches[k],yaws[y]);torch_equipped=1;
  aw_torch_depth_bob.value=0;bob=V_CalcBob();V_CalcRefdef();
  VectorCopy(cl.viewent.origin,stable_origin);VectorCopy(cl.viewent.angles,stable_angles);
  VectorCopy(r_refdef.vieworg,world_camera);VectorCopy(r_refdef.viewangles,world_angles);
  renderer_point(point,stable_point);
  aw_torch_depth_bob.value=1;V_CalcRefdef();renderer_point(point,legacy_point);
  AngleVectors(cl.viewangles,fwd,right,up);VectorSubtract(cl.viewent.origin,stable_origin,delta);
  for(n=0;n<3;n++){
   assert(fabs(delta[n]-fwd[n]*bob*.4f)<.0001f);
   assert(fabs(cl.viewent.angles[n]-stable_angles[n])<.0001f);
   assert(fabs(r_refdef.vieworg[n]-world_camera[n])<.0001f);
   assert(fabs(r_refdef.viewangles[n]-world_angles[n])<.0001f);
  }
  /* Actual alias transform: lateral/vertical placement unchanged; only depth varies. */
  assert(fabs(legacy_point[0]-stable_point[0])<.0001f);
  assert(fabs(legacy_point[1]-stable_point[1])<.0001f);
  assert(fabs(legacy_point[2]-stable_point[2]-bob*.4f)<.0001f);
  if(k==1 && y==0){
   assert(stable_point[2]<ALIAS_Z_CLIP_PLANE);
   if(legacy_point[2]<ALIAS_Z_CLIP_PLANE)legacy_clipped++;else legacy_visible++;
  }
  /* Ordinary fists/weapons retain the legacy placement in either setting. */
  torch_equipped=0;aw_torch_depth_bob.value=0;V_CalcRefdef();renderer_point(point,stable_point);
  for(n=0;n<3;n++)assert(fabs(stable_point[n]-legacy_point[n])<.0001f);
 }
 assert(legacy_visible && legacy_clipped);
 /* Invalid/nonfinite values use safe default; only explicit1 selects legacy. */
 setup(.15,320,0,0);torch_equipped=1;aw_torch_depth_bob.value=0;V_CalcRefdef();
 VectorCopy(cl.viewent.origin,stable_origin);
 for(i=0;i<3;i++){
  aw_torch_depth_bob.value=i==0?NAN:(i==1?-1:2);V_CalcRefdef();
  for(n=0;n<3;n++)assert(cl.viewent.origin[n]==stable_origin[n]);
 }
 /* Noclip keeps a steady eye and hand anchor by default, with an opt-in rollback. */
 assert(aw_noclipwobble.archive && aw_noclipwobble.value==0);
 setup(.15,320,0,0);noclip_anglehack=false;bob=V_CalcBob();assert(fabs(bob)>.01);
 noclip_anglehack=true;V_CalcRefdef();assert(V_CalcBob()==0);
 assert(fabs(r_refdef.vieworg[2]-cl.viewheight-1.0/32)<.0001);
 aw_noclipwobble.value=1;assert(fabs(V_CalcBob()-bob)<.0001);
 aw_noclipwobble.value=0;noclip_anglehack=false;assert(fabs(V_CalcBob()-bob)<.0001);
 /* FP-FOREARMS-BELOW-VIEW-61: the original's first-person view (OpenMW 0.51: "first person field of view" 60,
  * vertical; the first-person neck turns the arms by 0.75 of the pitch). The AmiWind view, fov 90 over a view 2.107
  * times as wide as high: the world's half height is tan 0.4746, the model's tan 30 degrees. */
 {
  float half=112,yscale=112/.4746f,k=V_FirstPersonScale(.57735f,half,yscale);
  assert(aw_fp_view.archive && aw_fp_view.value==1);              /* saved, the original's view by default */
  assert(fabs(k-.4746f/.57735f)<.001f && k<1);                    /* drawn smaller: more of the arms in view */
  assert(fabs(half/(yscale*k)-.57735f)<.001f);
  assert(fabs(V_FirstPersonScale(.4746f,half,yscale)-1)<.001f);   /* the same field: the world's projection */
  assert(V_FirstPersonScale(1.2f,half,yscale)<k);
  assert(V_FirstPersonScale(0,half,yscale)==1 && V_FirstPersonScale(NAN,half,yscale)==1);
  assert(V_FirstPersonScale(.57735f,0,yscale)==1 && V_FirstPersonScale(.57735f,half,-1)==1);
  assert(V_FirstPersonScale(.57735f,half,INFINITY)==1);
  assert(fabs(V_FirstPersonPitch(45,V_FP_NECK)-33.75f)<.001f && fabs(V_FirstPersonPitch(-40,V_FP_NECK)+30)<.001f);
  assert(V_FirstPersonPitch(45,1)==45 && V_FirstPersonPitch(45,0)==0 && V_FirstPersonPitch(0,V_FP_NECK)==0);
  assert(fabs(V_FirstPersonPitch(45,NAN)-33.75f)<.001f && fabs(V_FirstPersonPitch(45,2)-33.75f)<.001f);
  /* the whole view: looking 45 down the arms are pitched 33.75 (11.25 up into the view), 45 with aw_fp_view 0; the
   * eye's own angles and place do not change */
  for(i=0;i<3;i++){
   float want[3]={-40*.75f,0,45*.75f};
   setup(.15,0,pitches[i],0);torch_equipped=0;aw_fp_view.value=1;V_CalcRefdef();
   assert(fabs(-cl.viewent.angles[PITCH]-want[i])<.01f);
   VectorCopy(r_refdef.viewangles,world_angles);VectorCopy(r_refdef.vieworg,world_camera);
   aw_fp_view.value=0;V_CalcRefdef();assert(fabs(-cl.viewent.angles[PITCH]-pitches[i])<.01f);
   for(n=0;n<3;n++)assert(r_refdef.viewangles[n]==world_angles[n] && r_refdef.vieworg[n]==world_camera[n]);
  }
  aw_fp_view.value=1;
 }
 puts("torch view depth stable through stride; legacy rollback, camera, anchors and unarmed placement passed");
 return 0;
}
