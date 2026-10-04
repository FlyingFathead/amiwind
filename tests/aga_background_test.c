/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "d_local.h"
#include "aw_sky.h"
#include <assert.h>
int r_backgroundsky,r_skymade;byte *r_skysource;
float d_zistepu,d_zistepv,d_ziorigin;
cvar_t r_clearcolor={"r_clearcolor","2"};
static int sky,depth,make;
static byte pixels[8];static short depths[8];
byte *d_viewbuffer=pixels;short *d_pzbuffer=depths;unsigned int d_zwidth=8;int screenwidth=8;
void R_MakeSky(void){make++;r_skymade=1;}
void D_DrawSkyScans8(espan_t *s){sky++;pixels[s->u]=200;}
void D_DrawZSpans(espan_t *s){depth++;assert(d_zistepu==0 && d_zistepv==0 && d_ziorigin<0);}
vec3_t r_origin={0,0,0},r_pright={1,0,0},r_pup={0,1,0},r_ppn={0,0,1};
float xcenter=1,ycenter=0;
int d_scantable[MAXHEIGHT],d_vrectx,d_vrecty,d_vrectright_particle=7,d_vrectbottom_particle=0;
int d_y_aspect_shift,d_pix_min=1,d_pix_max=1,d_pix_shift=8;
void D_DrawParticle(particle_t *p);
void D_DrawBackground(surf_t *s);
int main(void){
 surf_t s;espan_t span;byte source=1;int i;memset(&s,0,sizeof s);memset(&span,0,sizeof span);span.u=1;span.count=3;s.spans=&span;r_clearcolor.value=2;
 for(i=0;i<8;i++)depths[i]=123;
 D_DrawBackground(&s);assert(pixels[1]==2 && depth==1 && !sky);
 r_backgroundsky=1;r_skysource=&source;D_DrawBackground(&s);assert(sky==1 && make==1 && depth==1 && pixels[1]==200);
 assert(depths[0]==123 && depths[4]==123);for(i=1;i<4;i++)assert(depths[i]==AW_SKY_BACKGROUND_DEPTH);
 D_DrawBackground(&s);assert(sky==2 && make==1 && depth==1);
 r_backgroundsky=0;D_DrawBackground(&s);assert(pixels[1]==2 && sky==2 && depth==2);
 r_backgroundsky=1;r_skysource=NULL;D_DrawBackground(&s);assert(pixels[1]==2 && depth==3);
 {
  particle_t p;memset(&p,0,sizeof p);p.org[2]=256;p.color=42;
  depths[1]=AW_SKY_BACKGROUND_DEPTH;pixels[1]=200;D_DrawParticle(&p);
  assert(depths[1]==128 && pixels[1]==42); /* Opaque particle replaces sky classification. */
  depths[1]=256;pixels[1]=77;D_DrawParticle(&p);assert(depths[1]==256 && pixels[1]==77);
 }
 return 0;
}
