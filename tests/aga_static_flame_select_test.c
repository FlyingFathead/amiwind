/* SPDX-License-Identifier: GPL-2.0-or-later
 * Static flame budget (FLAME-RANGE-NEAREST-32): a hearth in view is drawn even
 * when more than STATIC_FLAME_DRAW candles are nearer, most of them behind the
 * camera (the Census and Excise Office case). The earlier nearest-first rule
 * stays selectable (aw_static_flames_nearest 1) and keeps its behaviour. */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>
refdef_t r_refdef;vec3_t vpn,vup,vright;float aliasxcenter,aliasycenter,aliasxscale,aliasyscale;
void Con_Printf(char *fmt,...) {}
void Sys_Error(char *fmt,...) {assert(0);}
#define DRAW 12
static aw_static_flame_t flames[64];static int count;
static void candle(float x,float y,float z){aw_static_flame_t *f=&flames[count++];memset(f,0,sizeof *f);
    f->origin[0]=x;f->origin[1]=y;f->origin[2]=z;f->scale=.8f;f->shape[0]=.62f;f->shape[1]=.88f;f->shape[2]=.09f;}
static void view(float x,float y,float z,float pitch,float yaw){vec3_t a;a[0]=pitch;a[1]=yaw;a[2]=0;
    r_refdef.vieworg[0]=x;r_refdef.vieworg[1]=y;r_refdef.vieworg[2]=z;AngleVectors(a,vpn,vright,vup);}
static int has(const int *chosen,int n,int index){int i;for(i=0;i<n;i++)if(chosen[i]==index)return 1;return 0;}
static int front(int index){vec3_t d;VectorSubtract(flames[index].origin,r_refdef.vieworg,d);return DotProduct(d,vpn)>0;}
int main(void)
{
    int i,j,n,hearth,chosen[DRAW];float d[64];
    r_refdef.vrect.x=0;r_refdef.vrect.y=0;r_refdef.vrect.width=320;r_refdef.vrect.height=200;
    aliasxcenter=160;aliasycenter=100;aliasxscale=aliasyscale=160;
    /* Two chandeliers behind the camera, one in front, one wall candle in
     * front and a hearth about 100 units ahead (owner pose, facing south). */
    for(i=0;i<4;i++){candle(-11.6f-8.8f*(i&1),11+8.8f*(i>>1),95.5f);candle(43.6f+8.8f*(i&1),12+8.8f*(i>>1),95.5f);}
    for(i=0;i<4;i++)candle(-11.6f-8.8f*(i&1),-53.1f+8.8f*(i>>1),95.8f);
    candle(-39.6f,52.7f,71);candle(58.6f,-42.5f,76.1f);
    hearth=count;candle(-10,-117.9f,50.9f);flames[hearth].scale=8;
    flames[hearth].shape[0]=10.5f;flames[hearth].shape[1]=13.5f;flames[hearth].shape[2]=3.87f;
    for(i=0;i<20;i++)candle(300+i,300,90); /* far away, beyond the budget */
    view(-25,-20,86,10,277);
    /* Earlier rule: the twelve nearest in any direction; the hearth is 15th. */
    n=AW_StaticFlamesPick(flames,count,1,chosen);assert(n==DRAW && !has(chosen,n,hearth));
    for(i=0;i<count;i++){vec3_t v;VectorSubtract(flames[i].origin,r_refdef.vieworg,v);d[i]=DotProduct(v,v);}
    for(i=0;i<count;i++)if(!has(chosen,n,i))for(j=0;j<n;j++)assert(d[chosen[j]]<=d[i]);
    for(j=1;j<n;j++)assert(d[chosen[j-1]]<=d[chosen[j]]);
    /* Default rule: only flames that can reach the screen; the hearth first. */
    n=AW_StaticFlamesPick(flames,count,0,chosen);
    assert(n>0 && n<=DRAW && chosen[0]==hearth);
    for(j=0;j<n;j++)assert(front(chosen[j]));
    /* Turned around: the hearth is behind and gives its slot away. */
    view(-25,-20,86,10,97);n=AW_StaticFlamesPick(flames,count,0,chosen);assert(n>0 && !has(chosen,n,hearth));
    for(j=0;j<n;j++)assert(front(chosen[j]));
    /* Budget: never more than STATIC_FLAME_DRAW, also with many in view. */
    count=0;for(i=0;i<40;i++)candle(100+i*2,(i%5)*4-8,60);view(0,0,60,0,0);
    n=AW_StaticFlamesPick(flames,count,0,chosen);assert(n==DRAW);
    for(j=0;j<n;j++)assert(flames[chosen[j]].origin[0]<100+2*16); /* the nearest of equal size */
    /* Beyond the range, nothing. */
    view(-2000,0,60,0,0);assert(AW_StaticFlamesPick(flames,count,0,chosen)==0 && AW_StaticFlamesPick(flames,count,1,chosen)==0);
    puts("static flames: on-screen, size-ranked budget keeps the hearth; nearest-first rule kept and selectable");
    return 0;
}
