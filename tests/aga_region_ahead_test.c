/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_region.h"
#include <assert.h>
server_t sv;
void Con_Printf(char *fmt,...) {(void)fmt;}
int COM_FOpenFile(char *name,FILE **f) {
    const char *s="AWBR1 3 96 540 0 500 30 90 0 500 30 90\n"
        "bm000 -100 0 100 260 -1000 -1000 1000 2000\n"
        "bm001 -100 260 100 400 -1000 -1000 1000 2000\n"
        "bm002 -100 400 100 1000 -1000 -1000 1000 2000\n";
    (void)name;*f=tmpfile();assert(*f);fputs(s,*f);rewind(*f);return (int)strlen(s);
}
#ifndef ENDPOINT_CONTROL
static void rectangle(aw_region_t *r,float x0,float y0,float x1,float y1) {
    memset(r,0,sizeof(*r));r->low[0]=x0;r->low[1]=y0;r->high[0]=x1;r->high[1]=y1;
}
static void geometry(void) {
    aw_region_t r[9];float p[3]={0,330,0},v[3]={0,-60,0};int i,x,y;
    rectangle(r,-100,0,100,260);rectangle(r+1,-100,260,100,400);rectangle(r+2,-100,400,100,1000);
    /* Endpoint is in0, while the first residency change is2->1. */
    assert(AW_RegionNextOwner(r,3,p,v,2,96,1.5f)==1);
    p[1]=305;assert(AW_RegionNextOwner(r,3,p,v,2,96,1.5f)==1);
    p[1]=303;assert(AW_RegionNextOwner(r,3,p,v,2,96,1.5f)==1);
    p[1]=450;v[1]=60;assert(AW_RegionNextOwner(r,3,p,v,1,96,1.5f)==2);
    p[1]=406;assert(AW_RegionNextOwner(r,3,p,v,1,96,1.5f)==-1); /* Ends at inclusive496. */
    p[1]=407;assert(AW_RegionNextOwner(r,3,p,v,1,96,1.5f)==2);
    v[1]=0;assert(AW_RegionNextOwner(r,3,p,v,1,96,1.5f)==-1);
    v[1]=3;assert(AW_RegionNextOwner(r,3,p,v,1,96,1.5f)==-1);
    v[1]=60;assert(AW_RegionNextOwner(r,3,p,v,-1,96,1.5f)==-1);
    assert(AW_RegionNextOwner(r,0,p,v,1,96,1.5f)==-1);
    assert(AW_RegionNextOwner(r,3,p,v,3,96,1.5f)==-1);
    assert(AW_RegionNextOwner(r,3,p,v,1,-1,1.5f)==-1);
    assert(AW_RegionNextOwner(r,3,p,v,1,96,0)==-1);
    assert(AW_RegionNextOwner(r,3,p,v,1,96,NAN)==-1);
    assert(AW_RegionNextOwner(r,3,p,v,1,INFINITY,1.5f)==-1);
    p[0]=NAN;assert(AW_RegionNextOwner(r,3,p,v,1,96,1.5f)==-1);p[0]=0;
    v[0]=INFINITY;assert(AW_RegionNextOwner(r,3,p,v,1,96,1.5f)==-1);v[0]=0;
    p[0]=200;assert(AW_RegionNextOwner(r,3,p,v,1,96,1.5f)==-1);
    for(y=0;y<3;y++)for(x=0;x<3;x++)rectangle(r+y*3+x,x*100,y*100,(x+1)*100,(y+1)*100);
    p[0]=p[1]=50;v[0]=v[1]=100;
    assert(AW_RegionNextOwner(r,9,p,v,0,0,2)==4); /* Cross a corner; do not select a touched side. */
    assert(AW_RegionNextOwner(r,9,p,v,0,10,2)==4);
    v[1]=50;assert(AW_RegionNextOwner(r,9,p,v,0,10,2)==1); /* Unequal diagonal. */
    p[0]=p[1]=250;v[0]=v[1]=-100;assert(AW_RegionNextOwner(r,9,p,v,8,10,2)==4);
    p[0]=50;p[1]=150;v[0]=100;v[1]=0;assert(AW_RegionNextOwner(r,9,p,v,3,10,2)==4);
    p[0]=250;v[0]=-100;assert(AW_RegionNextOwner(r,9,p,v,5,10,2)==4);
    p[0]=100;p[1]=50;v[0]=0;v[1]=100;
    assert(AW_RegionNextOwner(r,9,p,v,1,10,2)==4); /* Half-open parallel edge. */
    p[0]=300;assert(AW_RegionNextOwner(r,9,p,v,2,10,2)==5); /* Inclusive outside edge. */
    p[0]=350;assert(AW_RegionNextOwner(r,9,p,v,2,10,2)==-1);
    /* Slow enough dense sampling provides an independent first-owner oracle. */
    for(i=0;i<8;i++){
        int expected=-1,j,got;float q[3];
        static const float velocities[8][2]={{100,0},{-100,0},{0,100},{0,-100},{100,100},{100,-100},{-100,100},{-100,-100}};
        p[0]=p[1]=150;v[0]=velocities[i][0];v[1]=velocities[i][1];
        for(j=1;j<=2000;j++){
            q[0]=p[0]+v[0]*(j*.001f);q[1]=p[1]+v[1]*(j*.001f);q[2]=0;
            got=AW_RegionOwner(r,9,q,4,10);if(got!=4 && got>=0){expected=got;break;}
        }
        assert(AW_RegionNextOwner(r,9,p,v,4,10,2)==expected);
    }
}
#endif
int main(void) {
    float p[3]={0,500,30},v[3]={0,-60,0};const char *next;
#ifndef ENDPOINT_CONTROL
    geometry();
#endif
    strcpy(sv.name,"balmora");assert(AW_RegionSelect("balmora",p,0));
    assert(!strcmp(AW_RegionWorldModel("balmora",0),"maps/bm002.bsp"));
    p[1]=330;next=AW_RegionAhead(p,v,0,1.5f);
    if(!next || strcmp(next,"maps/bm001.bsp"))return 42;
    p[1]=305;assert(!strcmp(AW_RegionAhead(p,v,0,1.5f),"maps/bm001.bsp"));
    assert(!AW_RegionAhead(p,v,1,1.5f));
    strcpy(sv.name,"interior");assert(!AW_RegionAhead(p,v,0,1.5f));
    return 0;
}
