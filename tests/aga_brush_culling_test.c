/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>

int r_visframecount=7;
static int draws;
extern float entity_rotation[3][3];
extern int r_currentbkey;
extern mnode_t *r_pefragtopnode;
void R_RecursiveClipBPoly(bedge_t *,mnode_t *,msurface_t *);
void R_SplitEntityOnNode2(mnode_t *);
void Con_Printf(char *fmt,...) {}
void Sys_Error(char *fmt,...) {assert(0);}
int AW_NodeVisible(short *bounds) {return bounds[0]<500;}
void R_RenderBmodelFace(bedge_t *edges,msurface_t *surface) {
    assert(edges && surface && r_currentbkey==123);
    draws++;
}
int main(void) {
    mnode_t root;
    mleaf_t front,back;
    mplane_t plane;
    msurface_t surface;
    mvertex_t vertices[3];
    bedge_t edges[3];
    int i;
    memset(&root,0,sizeof(root));memset(&front,0,sizeof(front));
    memset(&back,0,sizeof(back));memset(&plane,0,sizeof(plane));
    memset(&surface,0,sizeof(surface));memset(vertices,0,sizeof(vertices));
    root.visframe=front.visframe=back.visframe=r_visframecount;
    front.contents=CONTENTS_EMPTY;back.contents=CONTENTS_SOLID;
    front.key=123; /* stale from an earlier traversal: must not be consumed */
    front.minmaxs[0]=1000;plane.normal[0]=1;root.plane=&plane;
    root.children[0]=(mnode_t *)&front;root.children[1]=(mnode_t *)&back;
    for(i=0;i<3;i++)entity_rotation[i][i]=1;
    for(i=0;i<3;i++) {
        vertices[i].position[0]=1;
        vertices[i].position[1]=(i==1);
        vertices[i].position[2]=(i==2);
        edges[i].v[0]=&vertices[i];edges[i].v[1]=&vertices[(i+1)%3];
        edges[i].pnext=i<2?&edges[i+1]:NULL;
    }
    R_RecursiveClipBPoly(edges,&root,&surface);assert(draws==0);
    r_pefragtopnode=NULL;R_SplitEntityOnNode2((mnode_t *)&front);
    assert(!r_pefragtopnode);
    front.minmaxs[0]=100;
    for(i=0;i<3;i++)edges[i].pnext=i<2?&edges[i+1]:NULL;
    R_RecursiveClipBPoly(edges,&root,&surface);assert(draws==1);
    R_SplitEntityOnNode2((mnode_t *)&front);
    assert(r_pefragtopnode==(mnode_t *)&front);
    front.visframe--;
    for(i=0;i<3;i++)edges[i].pnext=i<2?&edges[i+1]:NULL;
    R_RecursiveClipBPoly(edges,&root,&surface);assert(draws==1);
    return 0;
}
