/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>

refdef_t r_refdef;
float aliasxscale=50, aliasyscale=50, aliasxcenter=50, aliasycenter=50;
static finalvert_t vertices[3];
static auxvert_t auxiliary[3];
static int draws, unique_count, unique_xy[12][2];
void R_AliasProjectFinalVert(finalvert_t *, auxvert_t *);
void R_AliasClipTriangle(mtriangle_t *);

/* Capture the real clipper's rasterizer input. The fixture checks geometry;
 * it does not substitute for target rasterization or visual acceptance. */
void D_PolysetDraw(void) {
    int i,j;
    mtriangle_t *t=r_affinetridesc.ptriangles;
    draws++;
    for(i=0;i<3;i++) {
        finalvert_t *v=&r_affinetridesc.pfinalverts[t->vertindex[i]];
        assert(v->v[0]>=0 && v->v[0]<=100);
        assert(v->v[1]>=0 && v->v[1]<=100);
        assert(v->v[2]>=0 && v->v[2]<=2*65536);
        assert(v->v[3]>=0 && v->v[3]<=2*65536);
        for(j=0;j<unique_count;j++)
            if(unique_xy[j][0]==v->v[0] && unique_xy[j][1]==v->v[1])break;
        if(j==unique_count) {
            assert(unique_count<12);
            unique_xy[j][0]=v->v[0];unique_xy[j][1]=v->v[1];unique_count++;
        }
    }
}

static void check(const float points[3][3],int rotation,int order,int reverse,int expected_draws,int expected_unique) {
    mtriangle_t triangle={1,{0,1,2}};
    int i,j,index;
    draws=unique_count=0;
    memset(vertices,0,sizeof(vertices));memset(auxiliary,0,sizeof(auxiliary));
    pfinalverts=vertices;pauxverts=auxiliary;
    for(i=0;i<3;i++) {
        float x,y,tmp;
        index=(order+(reverse?2-i:i))%3;
        x=points[index][0];y=points[index][1];
        for(j=0;j<rotation;j++){tmp=x;x=-y;y=tmp;}
        auxiliary[i].fv[0]=x;auxiliary[i].fv[1]=y;auxiliary[i].fv[2]=points[index][2];
        vertices[i].v[2]=index*65536;vertices[i].v[3]=index*65536;
        if(points[index][2]<ALIAS_Z_CLIP_PLANE)vertices[i].flags=ALIAS_Z_CLIP;
        else {
            R_AliasProjectFinalVert(&vertices[i],&auxiliary[i]);
            if(vertices[i].v[0]<0)vertices[i].flags|=ALIAS_LEFT_CLIP;
            if(vertices[i].v[0]>100)vertices[i].flags|=ALIAS_RIGHT_CLIP;
            if(vertices[i].v[1]<0)vertices[i].flags|=ALIAS_TOP_CLIP;
            if(vertices[i].v[1]>100)vertices[i].flags|=ALIAS_BOTTOM_CLIP;
        }
    }
    R_AliasClipTriangle(&triangle);
    assert(draws==expected_draws);
    assert(unique_count==expected_unique);
}

int main(void) {
    /* One vertex behind near plane creates a quad. Only its fourth vertex
     * lies beyond the screen edge; clipping must make a pentagon, not merely
     * clamp that vertex's screen coordinate with unchanged texture values. */
    static const float fourth_outside[3][3]={{-2,0,10},{2,8,10},{0,6,1}};
    static const float inside[3][3]={{-2,0,10},{2,2,10},{0,-2,10}};
    static const float two_behind[3][3]={{-1,-1,1},{1,-1,1},{0,1,10}};
    static const float all_behind[3][3]={{-1,-1,1},{1,-1,1},{0,1,1}};
    int edge,order,reverse;
    memset(&r_refdef,0,sizeof(r_refdef));
    r_refdef.aliasvrectright=r_refdef.aliasvrectbottom=100;
    for(edge=0;edge<4;edge++)for(order=0;order<3;order++)for(reverse=0;reverse<2;reverse++) {
        check(fourth_outside,edge,order,reverse,3,5);
        check(inside,edge,order,reverse,1,3);
        check(two_behind,edge,order,reverse,1,3);
        check(all_behind,edge,order,reverse,0,0);
    }
    puts("alias near/screen clipping: all four edges, cyclic order, winding and near rejection passed (96 cases)");
    return 0;
}
