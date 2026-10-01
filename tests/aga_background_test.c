/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "d_local.h"
#include <assert.h>
int r_backgroundsky,r_skymade;byte *r_skysource;
float d_zistepu,d_zistepv,d_ziorigin;
cvar_t r_clearcolor={"r_clearcolor","2"};
static int sky,depth,make;
static byte pixels[8];byte *d_viewbuffer=pixels;int screenwidth=8;
void R_MakeSky(void){make++;r_skymade=1;}
void D_DrawSkyScans8(espan_t *s){sky++;pixels[0]=200;}
void D_DrawZSpans(espan_t *s){depth++;assert(d_zistepu==0 && d_zistepv==0 && d_ziorigin<0);}
void D_DrawBackground(surf_t *s);
int main(void){
 surf_t s;espan_t span;byte source=1;memset(&s,0,sizeof s);memset(&span,0,sizeof span);span.count=1;s.spans=&span;r_clearcolor.value=2;
 D_DrawBackground(&s);assert(pixels[0]==2 && depth==1 && !sky);
 r_backgroundsky=1;r_skysource=&source;D_DrawBackground(&s);
 assert(sky==1 && make==1 && depth==2 && pixels[0]==200);
 D_DrawBackground(&s);assert(sky==2 && make==1 && depth==3);
 r_backgroundsky=0;D_DrawBackground(&s);assert(pixels[0]==2 && sky==2);
 r_backgroundsky=1;r_skysource=NULL;D_DrawBackground(&s);assert(pixels[0]==2);
 return 0;
}
