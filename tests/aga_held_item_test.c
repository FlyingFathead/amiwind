/* SPDX-License-Identifier: GPL-2.0-or-later */
/* FP-TORCH-HAND-REGRESSION-67 (aw_hand_models.c AW_HandItemPlace, built with -DAW_BLOCK_HOST_TEST): a held item's grip
 * sits on its hand's bone in first person, whatever the view and the pose. The grip is the item point the item's own
 * carried place (a light's .hld offset) puts on the bone's origin: in item units it is fixed by that offset alone, so
 * placed on the arms it must land on the bone's placed origin, never beside it. Before, the held light was also moved
 * 4 units forward along the view (cd67bdcf, v0.0.61): this check then reads 4.00 units. The bone tags are the first-
 * person table's own of the v0.0.67-dev2 image (a Nord man, the light stance's frames 196 and 200; the weapon bone at
 * frame 196), the carried place the debug torch's (the glass lantern and the candles have the same). */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "aw_hand_models.h"

/* where the alias renderer draws model point P of an entity at ORIGIN, ANGLES (AW_BlockCompose of a point tag) */
static void place(const float origin[3],const float angles[3],const float p[3],float out[3]) {
    float tag[6],a[3];
    tag[0]=p[0];tag[1]=p[1];tag[2]=p[2];tag[3]=tag[4]=tag[5]=0;
    AW_BlockCompose(origin,angles,tag,out,a);
}
static float dist(const float a[3],const float b[3]) {
    float x=a[0]-b[0],y=a[1]-b[1],z=a[2]-b[2];return (float)sqrt(x*x+y*y+z*z);
}
/* the model point that an entity at ORIGIN, ANGLES draws at TARGET (its axes read back from three unit points) */
static void model_point(const float origin[3],const float angles[3],const float target[3],float out[3]) {
    int k,j;float e[3],axis[3];
    for(k=0;k<3;k++){
        e[0]=e[1]=e[2]=0;e[k]=1;place(origin,angles,e,axis);
        for(out[k]=0,j=0;j<3;j++)out[k]+=(target[j]-origin[j])*(axis[j]-origin[j]);
    }
}
int main(void) {
    static const float tags[3][6]={
        {2.8523f,7.3995f,-3.4792f,-11.3371f,155.9804f,84.4612f},      /* shield bone, light stance frame 196 */
        {2.9746f,7.5128f,-3.4742f,-11.6799f,157.5357f,84.0992f},      /* shield bone, frame 200 */
        {7.3451f,-2.8602f,-2.5617f,-14.3151f,-0.9381f,92.0853f}};     /* weapon bone, frame 196 */
    static const float views[4][6]={{0,0,0,0,0,0},{-120.5f,310.25f,64,25,90,0},{40,-80,22,-30,215,5},{0,0,22,70,10,0}};
    static const float carried[6]={0,.749f,-.121f,0,0,-90};          /* the debug torch's .hld offset */
    static const float none[6]={0,0,0,0,0,0};
    float zero[3]={0,0,0},bo[3],ba[3],grip[3],o[3],a[3],bone[3],at[3],drawn[3],worst=0;int t,v,k;
    /* the grip in item units: the item point the carried place puts on the bone's origin (in the bone's own frame) */
    AW_HandItemPlace(zero,zero,none,carried,bo,ba);
    model_point(bo,ba,zero,grip);
    assert(fabs(grip[0])<1e-3f && fabs(grip[1]+.121f)<1e-3f && fabs(grip[2]+.749f)<1e-3f);   /* the probe's grip */
    for(t=0;t<3;t++)for(v=0;v<4;v++){
        const float *view=views[v];
        /* the hand's bone as the arms are drawn: the view model's place, then the bone tag */
        AW_HandItemPlace(view,view+3,tags[t],NULL,bone,at);
        AW_BlockCompose(view,view+3,tags[t],o,a);
        for(k=0;k<3;k++)assert(fabs(bone[k]-o[k])<1e-4f && fabs(at[k]-a[k])<1e-3f);   /* no carried place: the bone */
        /* the item on it with its carried place: its grip point is drawn on the bone */
        AW_HandItemPlace(view,view+3,tags[t],carried,o,a);
        place(o,a,grip,drawn);
        if(dist(drawn,bone)>worst)worst=dist(drawn,bone);
        assert(dist(drawn,bone)<.01f);
    }
    printf("Held item grip on its hand's bone: worst %.4f units over %d poses and %d views (the old 4-unit forward push "
           "read 4.00).\n",worst,3,4);
    return 0;
}
