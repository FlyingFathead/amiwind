/* SPDX-License-Identifier: GPL-2.0-or-later */
/* The same physical floor sample must not lose its torch light merely because
 * the material has denser, mirrored or skewed UVs. Use the real accumulator. */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>
client_state_t cl;
dlight_t cl_dlights[MAX_DLIGHTS];
entity_t cl_entities[MAX_EDICTS], *currententity;
void R_EntityRotate(vec3_t point) { assert(0); }
extern unsigned blocklights[18*18];
void R_AddDynamicLights(void);
static unsigned sample(float sx,float tx,float ty,float normal_component,float x,float y)
{
    msurface_t surface; mplane_t plane; mtexinfo_t tex;
    memset(&surface,0,sizeof surface);memset(&plane,0,sizeof plane);memset(&tex,0,sizeof tex);
    plane.normal[2]=1;surface.plane=&plane;surface.texinfo=&tex;surface.dlightbits=1;
    surface.extents[0]=surface.extents[1]=16;
    tex.vecs[0][0]=sx;tex.vecs[0][2]=normal_component;
    tex.vecs[1][0]=tx;tex.vecs[1][1]=ty;tex.vecs[1][2]=normal_component;
    /* Offset the mapping so the first lightmap sample is the requested world
     * point. Texture minima remain the ordinary multiples of sixteen. */
    tex.vecs[0][3]=-sx*x;tex.vecs[1][3]=-tx*x-ty*y;
    r_drawsurf.surf=&surface;currententity=&cl_entities[0];
    cl_dlights[0].radius=192;cl_dlights[0].minlight=16;cl_dlights[0].origin[2]=25;
    memset(blocklights,0,sizeof blocklights);R_AddDynamicLights();
    return blocklights[0];
}
int main(void)
{
    static const float scales[]={.125f,.5f,1,4,16};
    static const float points[][2]={{0,0},{16,0},{32,16},{128,0},{200,0}};
    int i,j,k;unsigned baseline,actual;
    for(i=0;i<5;i++){
        baseline=sample(1,0,1,0,points[i][0],points[i][1]);
        for(j=0;j<5;j++)for(k=0;k<3;k++){
            actual=sample(scales[j],k?scales[j]*2:0,k==2?-scales[j]:scales[j],0,points[i][0],points[i][1]);
            assert(actual==baseline);
        }
        assert(sample(-1,0,1,0,points[i][0],points[i][1])==baseline);
        assert(sample(1,0,1,2,points[i][0],points[i][1])==baseline);
        printf("world sample (%g,%g), height25 radius192: %u; 17 UV variants agree\n",points[i][0],points[i][1],baseline);
    }
    assert(sample(1,0,1,0,0,0)==167*256);
    assert(sample(16,0,16,0,16,0)==151*256);
    assert(sample(.125f,0,.125f,0,200,0)==0);
    /* Degenerate UVs retain the bounded legacy result instead of dividing by
     * zero. They are not assigned a fabricated invertible surface basis. */
    assert(sample(0,0,0,0,0,0)==167*256);
    assert(sample(1,1,0,0,16,0)==143*256);
    /* Finite source mappings can still invert into enormous distances.
     * UBSan/float-cast-overflow must stay quiet; outside samples add no light. */
    assert(sample(1e-20f,0,1e-20f,0,1e25f,1e25f)==0);
    assert(sample(1,0,1,0,1e30f,0)==0);
    assert(sample(1,0,1,0,0,-1e30f)==0);
    assert(sample(1e20f,0,1e20f,0,16,16)==0);
    assert(sample(1,1,1e-8f,0,1e20f,1e20f)==0);
    puts("near-foot light, material density/skew/mirroring, range and singular controls passed");
    return 0;
}
