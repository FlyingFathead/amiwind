/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
extern int r_backgroundsky;
int main(void){
 model_t m;texture_t sky,rock;texture_t *textures[3]={NULL,&rock,&sky};
 memset(&m,0,sizeof m);memset(&sky,0,sizeof sky);memset(&rock,0,sizeof rock);
 strcpy(sky.name,"sky");strcpy(rock.name,"rock");m.textures=textures;m.numtextures=3;
 R_SetSkyBackground(&m);assert(r_backgroundsky);
 m.numtextures=2;R_SetSkyBackground(&m);assert(!r_backgroundsky);
 m.numtextures=3;R_SetSkyBackground(&m);assert(r_backgroundsky);
 R_SetSkyBackground(NULL);assert(!r_backgroundsky);
 return 0;
}
