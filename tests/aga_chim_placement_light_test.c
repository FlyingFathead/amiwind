/* SPDX-License-Identifier: GPL-2.0-or-later */
/* World format 0.12 (docs/chim/INTERIOR_STORE.md): the placement light level in
 * the record flags' high byte, the store folder by name, and the real lightmap
 * and surface cache paths drawing a placement at its own level. */
#include "quakedef.h"
#include "r_local.h"
#include "d_local.h"
#include "chim/chim_format.h"
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
extern int r_daylight,r_lamps;      /* r_light.c */
static int exterior=0;
int R_SkyExterior(void){return exterior;}
cvar_t aw_torch_strength={"aw_torch_strength","1",true,false,1};cvar_t aw_guard_torch_radius={"aw_guard_torch_radius","1",true,false,1};
void Con_Printf(char *format,...){}
void R_EntityRotate(vec3_t p){assert(0);}
void Sys_Error(char *format,...){fprintf(stderr,"Unexpected renderer error: %s\n",format);abort();}
static byte colourmap[64*256], lump[1];
static struct {texture_t header;byte data[32*32+16*16+8*8+4*4];} texture;
static union {double align;byte data[65536];} cache_memory;
static model_t world;
static mnode_t root, leaf;
static mplane_t plane;
static msurface_t surface;
static mtexinfo_t tex;
static entity_t placement;
static surfcache_t *built;
static byte pixels[3][1024];

static void render(int target)
{
    /* d_edge.c sets the level from the entity being drawn before D_CacheSurface */
    r_drawsurf.light=currententity?currententity->aw_light:0;
    built=D_CacheSurface(&surface,0);
    memcpy(pixels[target],built->data,1024);
}

static void records(void)
{
    /* minor 11: the high byte is not read; minor 12: it is the level, the low bits keep their meaning */
    assert(ChimFormat_RecordLight(11,0x8003)==0);
    assert(ChimFormat_RecordLight(12,0x8003)==0x80);
    assert(ChimFormat_RecordLight(12,0x0003)==0);
    assert(ChimFormat_RecordLight(12,0xff00)==255);
    assert(ChimFormat_RecordLight(13,0x0100)==1);
}

static void stores(void)
{
    char out[48];
    assert(ChimFormat_StoreNameValid("chim")&&ChimFormat_StoreNameValid("chimi")&&ChimFormat_StoreNameValid("a_1"));
    assert(ChimFormat_StoreNameValid("abcdefgh"));
    assert(!ChimFormat_StoreNameValid("")&&!ChimFormat_StoreNameValid(NULL)&&!ChimFormat_StoreNameValid("abcdefghi"));
    assert(!ChimFormat_StoreNameValid("Chim")&&!ChimFormat_StoreNameValid("a/b")&&!ChimFormat_StoreNameValid("a.b"));
    assert(!ChimFormat_StoreNameValid("../x")&&!ChimFormat_StoreNameValid("a b"));
    assert(ChimFormat_StorePath(out,sizeof out,"chimi","world.cwi")&&!strcmp(out,"chimi/world.cwi"));
    assert(ChimFormat_StorePath(out,sizeof out,CHIM_STORE_DEFAULT,"s00/s0001.ccs")&&!strcmp(out,"chim/s00/s0001.ccs"));
    assert(!ChimFormat_StorePath(out,15,"chimi","world.cwi"));      /* "chimi/world.cwi" + NUL is 16 */
    assert(ChimFormat_StorePath(out,16,"chimi","world.cwi"));
    assert(!ChimFormat_StorePath(out,sizeof out,"Chimi","world.cwi"));
}

int main(void)
{
    int i,offset;
    records();
    stores();
    plane.normal[2]=1;root.plane=&plane;root.numsurfaces=1;leaf.contents=CONTENTS_EMPTY;
    root.children[0]=root.children[1]=&leaf;world.nodes=&root;world.surfaces=&surface;
    world.numsurfaces=world.nummodelsurfaces=1;world.lightdata=lump;
    surface.plane=&plane;surface.texinfo=&tex;surface.extents[0]=surface.extents[1]=32;
    memset(surface.styles,255,sizeof surface.styles);
    tex.vecs[0][0]=tex.vecs[1][1]=1;tex.texture=&texture.header;
    texture.header.width=texture.header.height=32;offset=sizeof(texture_t);
    for(i=0;i<4;i++){texture.header.offsets[i]=offset;offset+=1024>>(2*i);}
    memset(texture.data,200,sizeof texture.data);
    for(i=0;i<64;i++){int j;for(j=0;j<256;j++)colourmap[i*256+j]=(j*(63-i))/63;}
    for(i=0;i<256;i++)d_lightstylevalue[i]=256;
    vid.colormap=colourmap;cl.worldmodel=&world;
    D_InitCaches(cache_memory.data,sizeof cache_memory.data);
    /* Interior (ambient 0 as AW_Interior gives it): an entity without a level draws at the ambient */
    r_refdef.ambientlight=0;currententity=&cl_entities[0];render(0);
    /* A placement at level 64 is brighter than the ambient 0 */
    currententity=&placement;placement.aw_light=64;render(1);
    for(i=0;i<1024;i++)assert(pixels[1][i]>pixels[0][i]);
    /* Its cache is kept while the level is the same, whatever the ambient does */
    { surfcache_t *first=built; r_refdef.ambientlight=200;render(2);
      assert(built==first&&!memcmp(pixels[1],pixels[2],1024)); r_refdef.ambientlight=0; }
    /* Another level rebuilds the same surface's cache: two placements of one model at different levels */
    placement.aw_light=192;render(2);
    for(i=0;i<1024;i++)assert(pixels[2][i]>pixels[1][i]);
    placement.aw_light=64;render(2);assert(!memcmp(pixels[1],pixels[2],1024));
    /* The level is the ambient's units: level 64 draws as the ambient 64 does */
    currententity=&cl_entities[0];r_refdef.ambientlight=64;render(2);assert(!memcmp(pixels[1],pixels[2],1024));
    /* A map with no light lump falls back to fullbright for entities without a level, never for a placement with one */
    D_FlushCaches();world.lightdata=NULL;r_refdef.ambientlight=0;render(0);   /* a map change flushes */
    currententity=&placement;placement.aw_light=64;render(2);
    assert(!memcmp(pixels[1],pixels[2],1024));assert(memcmp(pixels[0],pixels[2],1024));
    /* r_fullbright still wins */
    r_fullbright.value=1;D_FlushCaches();render(2);currententity=&cl_entities[0];render(0);   /* a change of r_fullbright flushes */
    assert(!memcmp(pixels[0],pixels[2],1024));r_fullbright.value=0;
    /* Outdoors (a CHIM exterior world, CHIM-MESHLESS-LIGHTS-33) the level is the light sources' share: added to
     * the daylight-dimmed ambient, never dimmed itself, never past the full-day ambient (the original clamps). */
    exterior=1;world.lightdata=lump;D_FlushCaches();
    /* By day (daylight 256) the ambient is full already: a placement at level 64 draws as one without a level */
    currententity=&cl_entities[0];r_refdef.ambientlight=128;render(0);
    currententity=&placement;placement.aw_light=64;render(2);
    assert(!memcmp(pixels[0],pixels[2],1024));
    /* At night (daylight 64/256) the ambient dims to 32 and the level stays: 32 + 64 draws as ambient 96 by day */
    r_daylight=64;D_FlushCaches();render(2);
    r_daylight=256;D_FlushCaches();currententity=&cl_entities[0];r_refdef.ambientlight=96;render(0);
    assert(!memcmp(pixels[0],pixels[2],1024));
    /* ... and a level past the day ambient stops at it: 32 + 192 draws as the full-day 128 */
    r_daylight=64;r_refdef.ambientlight=128;D_FlushCaches();currententity=&placement;placement.aw_light=192;render(2);
    r_daylight=256;D_FlushCaches();currententity=&cl_entities[0];render(0);
    assert(!memcmp(pixels[0],pixels[2],1024));
    /* r_lamps 0 (the lamp A/B) leaves the dimmed ambient alone: the placement draws as an entity without a level */
    r_lamps=0;r_daylight=64;D_FlushCaches();render(0);
    currententity=&placement;render(2);assert(!memcmp(pixels[0],pixels[2],1024));
    r_lamps=1;r_daylight=256;exterior=0;
    puts("placement light: record levels 11/12, store names and paths, ambient vs level, cache kept per level and rebuilt on a change, fallback and fullbright, outdoors added to the dimmed ambient passed");
    return 0;
}
