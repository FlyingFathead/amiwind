/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "d_local.h"
#include "aw_sky.h"
#include <assert.h>
float d_zistepu,d_zistepv,d_ziorigin;unsigned int d_zwidth=8;short *d_pzbuffer;
int main(void){short depth[8];espan_t span;int i;float origins[]={1.5f,1e30f,0,-.9f,.5f};
 memset(&span,0,sizeof span);span.u=1;span.count=4;d_pzbuffer=depth;
 for(i=0;i<5;i++){int k;memset(depth,0,sizeof depth);depth[0]=depth[5]=77;d_ziorigin=origins[i];d_zistepu=0;D_DrawZSpans(&span);assert(depth[0]==77&&depth[5]==77);for(k=1;k<=4;k++)assert(depth[k]==(i<2?32767:i==4?16384:0));}
 d_ziorigin=1.2f;d_zistepu=-.2f;D_DrawZSpans(&span);for(i=1;i<=4;i++)assert(depth[i]>=0&&depth[i]!=AW_SKY_BACKGROUND_DEPTH);assert(depth[1]>=depth[2]&&depth[2]>=depth[3]&&depth[3]>=depth[4]);
 return 0;}
