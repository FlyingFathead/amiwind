/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Real lightmap/cache/pixel and alias sampling paths, with synthetic assets. */
#include "quakedef.h"
#include "r_local.h"
#include "d_local.h"
#include <assert.h>
client_state_t cl;
dlight_t cl_dlights[MAX_DLIGHTS];
entity_t cl_entities[MAX_EDICTS], *currententity;
refdef_t r_refdef;
viddef_t vid;
int r_framecount=10, r_pixbytes=1, c_surf, d_lightstylevalue[256];
qboolean d_roverwrapped;
#ifndef AW_TEST_REAL_COMMON
qboolean msg_suppress_1=true;
#endif
surfcache_t *d_initial_rover;
cvar_t r_fullbright={"r_fullbright","0"};
static int exterior=1;
int R_SkyExterior(void){return exterior;}
/* The real inline gain policy reads this setting; unkeyed lights stay at one. */
cvar_t aw_torch_strength={"aw_torch_strength","1",true,false,1};cvar_t aw_guard_torch_radius={"aw_guard_torch_radius","1",true,false,1};
void Con_Printf(char *format,...){}
void R_EntityRotate(vec3_t p){assert(0);}
void Sys_Error(char *format,...){fprintf(stderr,"Unexpected renderer error: %s\n",format);abort();}
static byte colourmap[64*256], samples[9], unused_lump[1];
static struct {texture_t header;byte data[32*32+16*16+8*8+4*4];} texture;
static union {double align;byte data[65536];} cache_memory;
static model_t world;
static mnode_t root, leaf;
static mplane_t plane;
static msurface_t surface;
static mtexinfo_t tex;
static byte pixels[2][1024];
static void render(int target,int mip,int missing,int dynamic)
{
    surfcache_t *cache;
    /* A real map change clears caches before the old map allocation is freed. */
    D_FlushCaches();world.lightdata=missing?NULL:unused_lump;
    surface.dlightframe=dynamic?r_framecount:0;surface.dlightbits=dynamic?1:0;
    cache=D_CacheSurface(&surface,mip);
    memcpy(pixels[target],cache->data,1024>>(2*mip));
}
int main(void)
{
    int i,level,offset,mip,ambient,dynamic;
    vec3_t point={8,8,24};
    plane.normal[2]=1;root.plane=&plane;root.numsurfaces=1;leaf.contents=CONTENTS_EMPTY;
    root.children[0]=root.children[1]=&leaf;world.nodes=&root;world.surfaces=&surface;
    world.numsurfaces=world.nummodelsurfaces=1;
    surface.plane=&plane;surface.texinfo=&tex;surface.extents[0]=surface.extents[1]=32;
    memset(surface.styles,255,sizeof surface.styles);
    tex.vecs[0][0]=tex.vecs[1][1]=1;tex.texture=&texture.header;
    texture.header.width=texture.header.height=32;offset=sizeof(texture_t);
    for(i=0;i<4;i++){texture.header.offsets[i]=offset;offset+=1024>>(2*i);}
    memset(texture.data,200,sizeof texture.data);
    for(level=0;level<64;level++)for(i=0;i<256;i++)colourmap[level*256+i]=(i*(63-level))/63;
    for(i=0;i<256;i++)d_lightstylevalue[i]=256;
    vid.colormap=colourmap;cl.worldmodel=&world;currententity=&cl_entities[0];
    cl_dlights[0].origin[2]=25;cl_dlights[0].radius=96;cl_dlights[0].minlight=16;
    D_InitCaches(cache_memory.data,sizeof cache_memory.data);
    for(ambient=0;ambient<=192;ambient+=64)for(dynamic=0;dynamic<2;dynamic++)for(mip=0;mip<4;mip++){
        r_refdef.ambientlight=ambient;render(0,mip,0,dynamic);render(1,mip,1,dynamic);
        assert(!memcmp(pixels[0],pixels[1],1024>>(2*mip)));
        assert(R_LightPoint(point)==ambient);world.lightdata=unused_lump;
        assert(R_LightPoint(point)==ambient);
    }
    /* A local light must still change the final indexed pixels on an empty
     * exterior lump. Equality alone could pass if both maps were fullbright. */
    r_refdef.ambientlight=128;render(0,0,1,0);render(1,0,1,1);
    for(i=0;i<1024;i++)assert(pixels[1][i]>pixels[0][i]);
    /* Preserve legacy/interior missing-lump fallback and the explicit override. */
    exterior=0;render(0,0,1,0);render(1,0,1,1);
    assert(!memcmp(pixels[0],pixels[1],1024));assert(R_LightPoint(point)==255);
    exterior=1;r_fullbright.value=1;render(0,0,0,0);render(1,0,1,1);
    assert(!memcmp(pixels[0],pixels[1],1024));r_fullbright.value=0;
    /* Valid baked samples retain the existing surface and alias calculation. */
    surface.samples=samples;surface.styles[0]=0;memset(samples,200,sizeof samples);
    world.lightdata=samples;assert(R_LightPoint(point)==200);
    render(0,0,0,0);surface.samples=NULL;surface.styles[0]=255;render(1,0,0,0);
    for(i=0;i<1024;i++)assert(pixels[0][i]>pixels[1][i]);
    puts("32 exterior empty/unused-lump final-pixel pairs and alias samples agree; dynamic, baked, legacy and fullbright controls passed");
    return 0;
}
