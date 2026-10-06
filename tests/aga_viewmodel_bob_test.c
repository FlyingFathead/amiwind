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
extern cvar_t aw_torch_depth_bob, cl_rollangle;
extern mdl_t *pmdl;
static mdl_t synthetic_model;
static int torch_equipped, bob_registered;
int AW_TorchEquipped(void){return torch_equipped;}
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
 puts("torch view depth stable through stride; legacy rollback, camera, anchors and unarmed placement passed");
 return 0;
}
