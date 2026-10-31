/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_sky.h"
server_t sv;client_state_t cl;
float xcenter,ycenter,xscale,yscale;
#include <assert.h>
#include <stdarg.h>
static int inside;
int AW_Interior(void){return inside;}
int AW_DrawDistance(void);
void AW_FogDepths(byte *,int);
static void (*distance_command)(void);
static int argc=1;
static char *argument="";
int Cmd_Argc(void){return argc;}
char *Cmd_Argv(int n){return argument;}
static char said[512];
void Con_Printf(char *fmt,...){va_list a;va_start(a,fmt);vsnprintf(said+strlen(said),sizeof said-strlen(said),fmt,a);va_end(a);}
extern int (*aw_chim_view_reach)(void);
static int chim_reach;
static int view_reach(void){return chim_reach;}
void Cmd_AddCommand(char *name,void (*fn)(void)){if(!strcmp(name,"aw_fog_distance"))distance_command=fn;}
static cvar_t *cvar_list[64];static int cvar_list_count;

cvar_t aw_drawdistance={"aw_drawdistance","700",0,0,700};
void Cvar_SetValue(char *name,float value){
 int i;if(!strcmp(name,"aw_drawdistance")){aw_drawdistance.value=value;return;}
 for(i=0;i<cvar_list_count;i++)if(!strcmp(cvar_list[i]->name,name)){cvar_list[i]->value=value;return;}
 assert(!"unknown cvar");
}
vec3_t vpn={.70710678f,.70710678f,0},r_origin={0,0,0};
vec3_t vright,vup,modelorg;
/* The day/night tables for the fog-exact far test: NULL (off) unless a test sets them;
 * sky_fogged: below the horizon the sky pass returns the full fog colour. */
static byte environment[4096];static int environment_on,sky_fogged;
const unsigned char *R_DayNightFogColours(void){return environment_on?environment:NULL;}
unsigned char R_DayNightSkyPixel(unsigned char c,float x,float y,float z,int fog){return sky_fogged && z<0 && fog?environment[15<<8]:c;}
void Cvar_RegisterVariable(cvar_t *v){v->value=atof(v->string);assert(cvar_list_count<64);cvar_list[cvar_list_count++]=v;}
static byte fog_colours[4096];
viddef_t vid;refdef_t r_refdef;short *d_pzbuffer;unsigned int d_zwidth;
byte *COM_LoadHunkFile(char *p){return fog_colours;}
/* config.cfg for AW_ConfigWithout: NULL = no saved configuration. */
static const char *saved_config;
int COM_FOpenFile(char *name,FILE **f){
 if(!strcmp(name,"world/large-rooms.txt")){           /* FOG-300-DEFAULT-57: one large room, capped at 450 */
  static const char rooms[]="# large rooms\nrie242a8d69e 450\nrimanor\n";
  *f=tmpfile();fputs(rooms,*f);rewind(*f);return (int)strlen(rooms);
 }
 assert(!strcmp(name,"config.cfg"));
 if(!saved_config){*f=NULL;return -1;}
 *f=tmpfile();fputs(saved_config,*f);rewind(*f);return (int)strlen(saved_config);
}
static float cvar_value(const char *name){int i;for(i=cvar_list_count-1;i>=0;i--)if(!strcmp(cvar_list[i]->name,name))return cvar_list[i]->value;assert(!"unregistered");return 0;}
/* Fog-exact far test (aw_cull 2, the default) and the detail options (aw_cull 3-6). */
static int flame_limit_value=32767;
static int flame_limit(void){return flame_limit_value;}
static float box[6];
static int point_far(float x,float y,float z){
 box[0]=box[3]=x;box[1]=box[4]=y;box[2]=box[5]=z;
 return AW_BrushPassFar(box,0,box);
}
/* The fog pass's sky ray z at a projected point, as AW_FogDraw steps it (affine
 * in the screen position, so evaluated at the projected position). */
static float sky_ray_z(float x,float y,float z){
 float vx=x*vright[0]+y*vright[1]+z*vright[2],vy=x*vup[0]+y*vup[1]+z*vup[2],vz=x*vpn[0]+y*vpn[1]+z*vpn[2];
 float col=xcenter+xscale*vx/vz,row=ycenter-yscale*vy/vz;
 int extent=r_refdef.vrect.width>r_refdef.vrect.height?r_refdef.vrect.width:r_refdef.vrect.height;
 float step=2.0f/extent,u=(col-((int)vid.width>>1))*step,v=(((int)vid.height>>1)-row)*step;
 return vpn[2]+u*vright[2]+v*vup[2];
}
static void view(float yaw,float pitch){
 float cy=cosf(yaw),sy=sinf(yaw),cp=cosf(pitch),sp=sinf(pitch);
 vpn[0]=cp*cy;vpn[1]=cp*sy;vpn[2]=-sp;
 vright[0]=sy;vright[1]=-cy;vright[2]=0;
 vup[0]=sp*cy;vup[1]=sp*sy;vup[2]=cp;
}
static void fog_exact_tests(void){
 int i,j,full,skipped=0,kept=0;unsigned seed=12345;float x,y,z,depth;
 static byte depths[32768];
 /* Like-for-like with the measurements: the far plane alone unless set. */
 Cvar_SetValue("aw_cull",1);
 /* The last level-15 value of the fog table, for several distances. */
 for(i=100;i<=4096;i+=37){
  AW_FogDepths(depths,i);full=AW_FogFullDepthValue(i);
  for(j=1;j<=full;j++)assert(depths[j]==15);
  assert(full==32767 || depths[full+1]<15);
 }
 assert(AW_FogFullDepthValue(540)==60);
 /* Viewport 320x200, Quake's projection (r_main.c R_ViewChanged). */
 vid.width=320;vid.height=200;r_refdef.vrect.x=r_refdef.vrect.y=0;r_refdef.vrect.width=320;r_refdef.vrect.height=200;
 xcenter=320*.5f-.5f;ycenter=200*.5f-.5f;xscale=160;yscale=160;
 r_origin[0]=r_origin[1]=r_origin[2]=0;view(0,0);
 assert(AW_DrawDistance()==540);
 /* No day/night tables: no test (the far plane alone). */
 environment_on=0;AW_CullBegin();assert(point_far(700,0,-50)==AW_FAR_DRAW);
 /* Tables whose level 15 is one colour, sky below the horizon fogged. */
 for(i=0;i<4096;i++)environment[i]=i>>8==15?9:i&255;
 environment_on=1;sky_fogged=1;
 Cvar_SetValue("aw_skyline_fill",0);
 Cvar_SetValue("aw_cull",1);AW_CullBegin();assert(point_far(700,0,-50)==AW_FAR_DRAW);
 Cvar_SetValue("aw_cull",2);AW_CullBegin();
 assert(point_far(700,0,-50)==AW_FAR_SKIP);   /* beyond full fog, below the horizon */
 assert(point_far(700,0,50)==AW_FAR_DRAW);    /* above the horizon: against the sky */
 assert(point_far(500,0,-50)==AW_FAR_DRAW);   /* nearer than full fog */
 /* A box straddling the full-fog depth below the horizon asks for face tests. */
 box[0]=500;box[1]=-10;box[2]=-60;box[3]=700;box[4]=10;box[5]=-40;
 assert((AW_BrushPassFar(box,0,box)&15)==AW_FAR_FACES);
 /* Level 15 not one colour, sky colours kept below the horizon, the skyline
  * fill marking columns, or an interior: no test. */
 environment[(15<<8)+3]=8;AW_CullBegin();assert(point_far(700,0,-50)==AW_FAR_DRAW);environment[(15<<8)+3]=9;
 sky_fogged=0;AW_CullBegin();assert(point_far(700,0,-50)==AW_FAR_DRAW);sky_fogged=1;
 Cvar_SetValue("aw_skyline_fill",1);AW_CullBegin();assert(point_far(700,0,-50)==AW_FAR_DRAW);Cvar_SetValue("aw_skyline_fill",0);
 inside=1;AW_CullBegin();assert(point_far(700,0,-50)==AW_FAR_DRAW);inside=0;
 /* Large rooms (FOG-300-DEFAULT-57): a listed room draws nothing past the draw distance,
  * at most its cap; an unlisted room, fog off or an exterior keep the 4096 indoor reach. */
 {qboolean was_active=sv.active;char was_name[sizeof sv.name];float was_distance=aw_drawdistance.value;
  memcpy(was_name,sv.name,sizeof was_name);sv.active=1;inside=1;Cvar_SetValue("aw_cull",1);
  strcpy(sv.name,"rie242a8d69e");aw_drawdistance.value=300;AW_CullBegin();
  {vec3_t at={400,0,0},near_at={250,0,0},far_at={3000,0,0};
  assert(AW_LargeRoomDistance()==300 && !AW_ModelVisible(at,10) && AW_ModelVisible(near_at,10));
  aw_drawdistance.value=700;AW_CullBegin();
  at[0]=500;near_at[0]=400;
  assert(AW_LargeRoomDistance()==450 && !AW_ModelVisible(at,10) && AW_ModelVisible(near_at,10));
  strcpy(sv.name,"rimanor");AW_CullBegin();assert(AW_LargeRoomDistance()==700);
  strcpy(sv.name,"rimano");AW_CullBegin();assert(!AW_LargeRoomDistance() && AW_ModelVisible(far_at,10));
  strcpy(sv.name,"rie242a8d69e");Cvar_SetValue("aw_fog",0);AW_CullBegin();
  assert(!AW_LargeRoomDistance() && AW_ModelVisible(far_at,10));Cvar_SetValue("aw_fog",1);}
  inside=0;assert(!AW_LargeRoomDistance());
  sv.active=was_active;memcpy(sv.name,was_name,sizeof was_name);aw_drawdistance.value=was_distance;
  Cvar_SetValue("aw_cull",2);AW_CullBegin();}
 /* A flame farther than full fog moves the test behind it. */
 aw_flame_depth_limit=flame_limit;flame_limit_value=40;AW_CullBegin();
 assert(point_far(700,0,-50)==AW_FAR_DRAW && point_far(900,0,-50)==AW_FAR_SKIP);
 flame_limit_value=32767;
 /* Every point the test leaves out, for random views and eye heights, has a
  * full-fog z-buffer value and lies below the sky ray's horizon. */
 for(j=0;j<200;j++){
  seed=seed*1103515245+12345;view((seed>>8&1023)/1024.0f*6.2831853f,((int)(seed>>18&255)-128)/128.0f*.5f);
  seed=seed*1103515245+12345;r_origin[2]=(int)(seed>>16&255)-128;
  AW_CullBegin();
  for(i=0;i<500;i++){
   float px,py,pz;
   seed=seed*1103515245+12345;depth=520+(seed>>16&127);
   seed=seed*1103515245+12345;x=((int)(seed>>16&1023)-512)/512.0f;
   seed=seed*1103515245+12345;y=((int)(seed>>16&1023)-512)/512.0f*.7f;
   /* a point on the view ray through screen offset (x,y) at view depth depth */
   px=r_origin[0]+depth*(vpn[0]+x*vright[0]+y*vup[0]);
   py=r_origin[1]+depth*(vpn[1]+x*vright[1]+y*vup[1]);
   pz=r_origin[2]+depth*(vpn[2]+x*vright[2]+y*vup[2]);
   if(point_far(px,py,pz)==AW_FAR_SKIP){
    skipped++;
    z=(px-r_origin[0])*vpn[0]+(py-r_origin[1])*vpn[1]+(pz-r_origin[2])*vpn[2];
    assert((int)(32768.0f/z)<=60);
    assert(sky_ray_z(px-r_origin[0],py-r_origin[1],pz-r_origin[2])<0);
   }else kept++;
  }
 }
 assert(skipped>1000 && kept>1000);
 /* The model-space planes after R_RotateBmodel (identity rotation here). */
 view(0,0);r_origin[2]=0;AW_CullBegin();VectorCopy(r_origin,modelorg);
 box[0]=500;box[1]=-10;box[2]=-60;box[3]=700;box[4]=10;box[5]=-40;
 AW_FarPassBegin(AW_BrushPassFar(box,0,box));
 assert(aw_far_faces==1 && aw_far_depth[0]==1 && aw_far_depth[3]>540 && aw_far_depth[3]<560);
 assert(DotProduct(box,aw_far_down)<aw_far_down[3]);
 /* Size-scaled cut-off presets: near side past the share of the distance. */
 assert(AW_SizeCutShare(1,10)==.5f && AW_SizeCutShare(1,100)==.75f && AW_SizeCutShare(1,300)==1);
 assert(AW_SizeCutShare(2,10)==.4f && AW_SizeCutShare(2,100)==.6f && AW_SizeCutShare(2,300)==.85f && AW_SizeCutShare(2,600)==1);
 Cvar_SetValue("aw_cull",3);AW_CullBegin();
 box[0]=box[3]=300;box[1]=box[4]=0;box[2]=box[5]=50;
 assert(AW_BrushPassFar(box,10,box)==AW_FAR_SIZE && AW_BrushPassFar(box,100,box)==AW_FAR_DRAW);
 Cvar_SetValue("aw_cull",2);AW_CullBegin();assert(AW_BrushPassFar(box,10,box)==AW_FAR_DRAW);
 /* Far detail step: far models of radius 32 and more get face tests. */
 Cvar_SetValue("aw_cull",5);AW_CullBegin();
 assert(AW_BrushPassFar(box,40,box)==(AW_FAR_FACES|2<<4) && AW_BrushPassFar(box,10,box)==AW_FAR_DRAW);
 Cvar_SetValue("aw_cull",1);aw_flame_depth_limit=NULL;
}
/* A placement of radius r whose near side (centre depth less r) lies at
 * `near` straight ahead. */
static int piece_far(float near,float radius){
 float origin[3],mm[6];origin[0]=near+radius;origin[1]=0;origin[2]=0;
 mm[0]=origin[0]-radius;mm[1]=-radius;mm[2]=-radius;mm[3]=origin[0]+radius;mm[4]=radius;mm[5]=radius;
 return AW_BrushPassFar(origin,radius,mm);
}
/* The fog rule (aw_cull + 8, AW_CULL_FOG_RULE; CHIM-BRIDGE-POP-PIECES-44): no cut nearer than
 * the fog's full-opacity depth, the distance itself (AW_FogDepths: level 15
 * from there). Without it the Strong preset (aw_cull 4) cuts a small piece
 * at 40 % of the distance, where the fog is still clear. */
static void fog_rule_tests(void){
 static byte depths[32768];float radii[4]={10,100,300,600},near;int i,z;
 environment_on=0;view(0,0);r_origin[0]=r_origin[1]=r_origin[2]=0;
 assert(AW_DrawDistance()==540);
 /* where the presets cut, the fog is not opaque: level under 15 */
 AW_FogDepths(depths,540);
 z=(int)(32768.0f/(540*.4f));assert(depths[z]<15);z=(int)(32768.0f/(540*.85f));assert(depths[z]<15);
 assert(((int)cvar_value("aw_cull")&~AW_CULL_TEST)==0);   /* switches off: the method before, until the A/B */
 Cvar_SetValue("aw_cull",4);AW_CullBegin();
 assert(piece_far(300,10)==AW_FAR_SIZE);          /* today: a small piece gone at 300 of 540 */
 assert(piece_far(300,100)==AW_FAR_DRAW && piece_far(400,100)==AW_FAR_SIZE);
 assert(piece_far(480,300)==AW_FAR_SIZE);
 for(i=0;i<4;i++){
  int mode;
  for(mode=3;mode<=6;mode++){
   Cvar_SetValue("aw_cull",mode|AW_CULL_FOG_RULE);AW_CullBegin();
   assert(AW_SizeCutDepthShare(radii[i])>=1);
   for(near=0;near<540;near+=9)assert(piece_far(near,radii[i])==AW_FAR_DRAW);   /* no size cut, no detail step */
  }
  Cvar_SetValue("aw_cull",4|AW_CULL_FOG_RULE);AW_CullBegin();
  assert(piece_far(560,radii[i])==AW_FAR_SIZE);   /* past the fog end it still cuts */
 }
 /* the far detail step starts at the fog end, not at half of it */
 Cvar_SetValue("aw_cull",5|AW_CULL_FOG_RULE);AW_CullBegin();assert(piece_far(300,40)==AW_FAR_DRAW);
 Cvar_SetValue("aw_cull",5);AW_CullBegin();assert(piece_far(300,40)==(AW_FAR_FACES|2<<4));
 /* the switch bits leave the far test itself alone: 8 alone is no far test, 9 the far plane */
 {vec3_t far_door={1000,1000,0};
  Cvar_SetValue("aw_cull",AW_CULL_FOG_RULE);AW_CullBegin();assert(AW_ModelVisible(far_door,10) && piece_far(300,10)==AW_FAR_DRAW);
  Cvar_SetValue("aw_cull",1|AW_CULL_FOG_RULE|AW_CULL_GROUPS);AW_CullBegin();assert(!AW_ModelVisible(far_door,10));}
 /* indoors nothing changes */
 Cvar_SetValue("aw_cull",4|AW_CULL_FOG_RULE);inside=1;AW_CullBegin();
 assert(piece_far(300,10)==AW_FAR_DRAW);inside=0;
 Cvar_SetValue("aw_cull",1);
}
/* Whole-structure cuts (aw_cull + 16, AW_CULL_GROUPS): the pieces of one structure are
 * tested on the structure's box, so a walkway keeps its small middle piece
 * and its far end while any of it is within the cut, and loses all of it
 * together. */
static void cut_group_tests(void){
 float walkway[6]={200,-20,0,900,20,40},beyond[6]={600,-20,0,900,20,40};
 vec3_t middle={450,0,20},end={800,0,20};
 float mm_mid[6]={440,-10,10,460,10,30},mm_end[6]={700,-100,-80,900,100,120};
 environment_on=0;view(0,0);r_origin[0]=r_origin[1]=r_origin[2]=0;
 Cvar_SetValue("aw_cull",4);AW_CullBegin();
 AW_FarGroup(walkway);                            /* setting off: each piece on its own */
 assert(AW_BrushPassFar(middle,10,mm_mid)==AW_FAR_SIZE);       /* the middle gone at 440 */
 assert(!AW_PassVisible(end,100));                /* the far end past the far plane */
 Cvar_SetValue("aw_cull",4|AW_CULL_GROUPS);AW_CullBegin();
 AW_FarGroup(walkway);
 assert(AW_PassVisible(middle,10) && AW_BrushPassFar(middle,10,mm_mid)==AW_FAR_DRAW);
 assert(AW_PassVisible(end,100) && AW_BrushPassFar(end,100,mm_end)==AW_FAR_DRAW);
 AW_FarGroup(beyond);                             /* the whole structure past the far plane: all of it goes */
 assert(!AW_PassVisible(middle,10) && !AW_PassVisible(end,100));
 AW_FarGroup(NULL);                               /* not a structure piece: its own sphere */
 assert(AW_BrushPassFar(middle,10,mm_mid)==AW_FAR_SIZE && !AW_PassVisible(end,100));
 inside=1;AW_CullBegin();AW_FarGroup(walkway);assert(AW_PassVisible(end,100));inside=0;  /* indoors: no far test */
 /* the structure's size class decides: a 640-unit walkway goes at 85 % of the
  * distance (Strong, no fog rule), all of it, not its small pieces at 40 % */
 AW_CullBegin();AW_FarGroup(walkway);
 {float far_walk[6]={560,-20,0,1200,20,40};vec3_t piece={600,0,20};float mm[6]={590,-10,10,610,10,30};
  AW_FarGroup(far_walk);assert(AW_BrushPassFar(piece,10,mm)==AW_FAR_SIZE);}
 AW_FarGroup(NULL);Cvar_SetValue("aw_cull",1);
}
/* Far detail default (owner 2026-10-17): Strong (4) for a fresh install and in
 * every saved configuration that sets it; a config.cfg saved before aw_cull was
 * saved (up to v0.0.41) keeps Full (1). */
static void far_detail_default_tests(void){
 saved_config=NULL;assert(!AW_ConfigWithout("aw_cull"));
 saved_config="bind w +forward\naw_drawdistance \"540\"\nvolume \"0.7\"\n";assert(AW_ConfigWithout("aw_cull"));
 saved_config="bind w +forward\naw_cull \"6\"\n";assert(!AW_ConfigWithout("aw_cull"));
 saved_config="aw_cull \"1\"\n";assert(!AW_ConfigWithout("aw_cull"));
 saved_config="say aw_cull 3\naw_culling \"1\"\n";assert(AW_ConfigWithout("aw_cull"));
 saved_config="";assert(AW_ConfigWithout("aw_cull"));
 AW_FarDetailSavedBefore(0);AW_FogInit();assert(cvar_value("aw_cull")==4);
 AW_FarDetailSavedBefore(1);AW_FogInit();assert(cvar_value("aw_cull")==1);
}
int main(void) {
 int distances[6]={128,400,540,700,1400,4096},i,j,expected;byte fog[32770];
 short edge_visible[6]={790,-110,-10,810,-90,10};
 short distant[6]={1000,1000,-10,1020,1020,10};
 short crosses_far[6]={490,490,-10,530,530,10};
 vec3_t door={800,-100,0},far_door={1000,1000,0};
 {
  byte pixels[5]={7,7,7,7,7};short z[5]={AW_SKY_BACKGROUND_DEPTH,-1,0,32767,128};
  for(i=0;i<4096;i++)fog_colours[i]=i>>8;
  vid.buffer=pixels;vid.rowbytes=5;d_pzbuffer=z;d_zwidth=5;r_refdef.vrect.width=5;r_refdef.vrect.height=1;
  AW_FogInit();AW_FogDraw();
  assert(pixels[0]==7);assert(pixels[1]==15 && pixels[2]==15);assert(pixels[3]==0);assert(pixels[4]!=7);
  inside=1;memset(pixels,7,sizeof pixels);AW_FogDraw();for(i=0;i<5;i++)assert(pixels[i]==7);inside=0;
 }
 assert(cvar_value("aw_cull")==4); /* Strong, the default from v0.0.42 */
 AW_CullBegin();
 assert(AW_NodeVisible(edge_visible)); /* old radius-aligned cube dropped this */
 assert(!AW_NodeVisible(distant));
 assert(AW_NodeVisible(crosses_far));
 assert(AW_ModelVisible(door,10));assert(!AW_ModelVisible(far_door,10));
 for(j=0;j<6;j++){
  memset(fog,123,sizeof(fog));AW_FogDepths(fog+1,distances[j]);
  assert(fog[0]==123 && fog[32769]==123 && fog[1]==15);
  for(i=1;i<32768;i++){
   expected=(int)floor((32768.0/i-distances[j]*.4)*25/distances[j]+1e-9);
   if(expected<0)expected=0;if(expected>15)expected=15;
   assert(fog[i+1]==expected);
  }
 }
 assert(distance_command);argc=2;argument="400";distance_command();assert(AW_DrawDistance()==400);
 AW_CullBegin();assert(!AW_NodeVisible(edge_visible));assert(!AW_ModelVisible(door,10));
 inside=1;AW_CullBegin();assert(AW_ModelVisible(far_door,10));inside=0;
 argument="0";distance_command();assert(AW_DrawDistance()==400);
 argument="999999999999999999999";distance_command();assert(AW_DrawDistance()==400);
 argument="4097";distance_command();assert(AW_DrawDistance()==400);
 argument="700junk";distance_command();assert(AW_DrawDistance()==400);
 argument="700";distance_command();assert(AW_DrawDistance()==700);
 sv.active=true;strcpy(sv.name,"balmora");assert(AW_DrawDistance()==540);
 assert(aw_drawdistance.value==700);strcpy(sv.name,"seyda");assert(AW_DrawDistance()==540);
 strcpy(sv.name,"prison");assert(AW_DrawDistance()==700);
 /* No artificial clamps: beyond the old 1500 the setting holds where nothing
  * else limits it; a CHIM map follows it up to its own world's data, and the
  * command says what limits it. */
 argument="2000";said[0]=0;distance_command();assert(AW_DrawDistance()==2000 && !strstr(said,"Here:"));
 aw_chim_view_reach=view_reach;chim_reach=0;assert(AW_DrawDistance()==2000);
 strcpy(sv.name,"balmora");assert(AW_DrawDistance()==540);
 said[0]=0;argc=1;distance_command();assert(strstr(said,"Here: 540") && strstr(said,"region maps"));argc=2;
 chim_reach=636;said[0]=0;distance_command();
 assert(AW_DrawDistance()==636 && strstr(said,"Here: 636") && strstr(said,"CHIM world's visibility data"));
 argument="600";said[0]=0;distance_command();assert(AW_DrawDistance()==600 && !strstr(said,"Here:"));
 chim_reach=1200;argument="1100";distance_command();assert(AW_DrawDistance()==1100);
 aw_chim_view_reach=NULL;assert(AW_DrawDistance()==540);
 fog_exact_tests();
 fog_rule_tests();
 cut_group_tests();
 far_detail_default_tests();
 puts("forward-depth culling retains visible edge/door and rejects far bounds; the fog-exact far test leaves out only full-fog geometry below the horizon");return 0;
}
