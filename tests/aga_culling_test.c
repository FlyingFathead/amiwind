/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_sky.h"
server_t sv;client_state_t cl;
float xcenter,ycenter,xscale,yscale;
#include <assert.h>
static int inside;
int AW_Interior(void){return inside;}
int AW_DrawDistance(void);
void AW_FogDepths(byte *,int);
static void (*distance_command)(void);
static int argc=1;
static char *argument="";
int Cmd_Argc(void){return argc;}
char *Cmd_Argv(int n){return argument;}
void Con_Printf(char *fmt,...){}
void Cmd_AddCommand(char *name,void (*fn)(void)){if(!strcmp(name,"aw_fog_distance"))distance_command=fn;}

cvar_t aw_drawdistance={"aw_drawdistance","700",0,0,700};
void Cvar_SetValue(char *name,float value){assert(!strcmp(name,"aw_drawdistance"));aw_drawdistance.value=value;}
vec3_t vpn={.70710678f,.70710678f,0},r_origin={0,0,0};
vec3_t vright,vup;
const unsigned char *R_DayNightFogColours(void){return NULL;}
unsigned char R_DayNightSkyPixel(unsigned char c,float x,float y,float z,int fog){return c;}
void Cvar_RegisterVariable(cvar_t *v){v->value=atof(v->string);}
static byte fog_colours[4096];
viddef_t vid;refdef_t r_refdef;short *d_pzbuffer;unsigned int d_zwidth;
byte *COM_LoadHunkFile(char *p){return fog_colours;}
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
 argument="700junk";distance_command();assert(AW_DrawDistance()==400);
 argument="700";distance_command();assert(AW_DrawDistance()==700);
 sv.active=true;strcpy(sv.name,"balmora");assert(AW_DrawDistance()==540);
 assert(aw_drawdistance.value==700);strcpy(sv.name,"seyda");assert(AW_DrawDistance()==540);
 strcpy(sv.name,"prison");assert(AW_DrawDistance()==700);
 puts("forward-depth culling retains visible edge/door and rejects far bounds");return 0;
}
