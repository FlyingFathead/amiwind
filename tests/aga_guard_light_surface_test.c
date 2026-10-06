/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Reuse the registry/actor/LOS stubs; this fixture adds the actual surface
 * marking, cache invalidation, lightmap and final indexed-pixel pipeline. */
#define main guard_registry_fixture_main
#include "aga_guard_torch_test.c"
#undef main
#include "d_local.h"
int r_framecount, r_pixbytes=1, c_surf, d_lightstylevalue[256];
qboolean msg_suppress_1=true, d_roverwrapped;
surfcache_t *d_initial_rover;
cvar_t r_fullbright={"r_fullbright","0"};
static byte colourmap[64*256], samples[9];
static struct {texture_t header;byte data[32*32+16*16+8*8+4*4];} texture;
static union {double align;byte data[65536];} cache_memory;
static model_t world;
static mnode_t root, leaf;
static mplane_t plane;
static msurface_t surface;
static mtexinfo_t tex;
static int mip;
static byte off_pixels[1024], on_pixels[1024], restored_pixels[1024];
void Sys_Error(char *format,...){fprintf(stderr,"Unexpected renderer error: %s\n",format);abort();}
static void render(byte *output,entity_t *brush)
{
    surfcache_t *cache;
    AW_GuardTorchUpdate();
    currententity=&cl_entities[0];
    R_PushDlights();
    r_framecount++; /* R_SetupFrame advances after R_PushDlights. */
    if(brush){currententity=brush;R_MarkBrushLights(&world);}
    cache=D_CacheSurface(&surface,mip);
    memcpy(output,cache->data,1024>>(2*mip));
}
static int difference(const byte *a,const byte *b)
{
    int i,n=0;for(i=0;i<(1024>>(2*mip));i++)if(a[i]!=b[i])n++;return n;
}
static void pair(int ambient,int baked,entity_t *brush)
{
    int i,n;
    D_FlushCaches();r_refdef.ambientlight=ambient;memset(samples,baked,sizeof samples);
    set_command("off");render(off_pixels,brush);assert(lights()==0);
    set_command("on");render(on_pixels,brush);assert(lights()==1);
    n=difference(off_pixels,on_pixels);assert(n==(1024>>(2*mip)));
    for(i=0;i<(1024>>(2*mip));i++)assert(on_pixels[i]>off_pixels[i]);
    set_command("off");render(restored_pixels,brush);
    assert(!difference(off_pixels,restored_pixels));
    printf("ambient=%d static=%d brush=%d mip=%d: %d final pixels brighter; extinguishing restored all pixels\n",ambient,baked,brush!=NULL,mip,n);
}
int main(void)
{
    int level,i,offset;entity_t brush;
    strcpy(base.name,"progs/original.mdl");base.type=body.type=held.type=mod_alias;
    base.numframes=body.numframes=held.numframes=8;
    sv.active=1;sv.num_edicts=40;svs.maxclients=1;cls.state=ca_connected;cl.time=1;
    make_registry(8);AW_GuardTorchInit();AW_GuardTorchLoadAssets(torch);
    npc(1,(int)(strstr(strings+18,"guard_a")-strings),16);scene(1);
    cl_entities[1].origin[1]=16;clock_ms=82800000;
    plane.normal[2]=1;root.plane=&plane;root.numsurfaces=1;leaf.contents=CONTENTS_EMPTY;
    root.children[0]=root.children[1]=&leaf;world.nodes=&root;world.surfaces=&surface;
    world.numsurfaces=world.nummodelsurfaces=1;world.lightdata=samples;
    world.mins[0]=world.mins[1]=world.mins[2]=-32;
    world.maxs[0]=world.maxs[1]=world.maxs[2]=32;
    surface.plane=&plane;surface.texinfo=&tex;surface.extents[0]=surface.extents[1]=32;
    surface.samples=samples;surface.styles[0]=0;
    surface.styles[1]=surface.styles[2]=surface.styles[3]=255;
    tex.vecs[0][0]=tex.vecs[1][1]=1;tex.texture=&texture.header;
    texture.header.width=texture.header.height=32;offset=sizeof(texture_t);
    for(i=0;i<4;i++){texture.header.offsets[i]=offset;offset+=1024>>(2*i);}
    memset(texture.data,200,sizeof texture.data);
    for(level=0;level<64;level++)for(i=0;i<256;i++)colourmap[level*256+i]=(i*(63-level))/63;
    for(i=0;i<256;i++)d_lightstylevalue[i]=256;
    vid.colormap=colourmap;cl.worldmodel=&world;r_framecount=10;
    D_InitCaches(cache_memory.data,sizeof cache_memory.data);
    for(mip=0;mip<4;mip++){pair(0,12,NULL);pair(128,12,NULL);pair(128,50,NULL);}
    /* The shared scalar reaches the actual indexed surface output and cache,
     * including immediate zero/restoration; neither guard count nor reach changes. */
    for(mip=0;mip<4;mip++){
        D_FlushCaches();r_refdef.ambientlight=0;memset(samples,12,sizeof samples);
        set_command("off");render(off_pixels,NULL);
        set_command("on");aw_torch_strength.value=0;render(on_pixels,NULL);
        assert(lights()==1 && !difference(off_pixels,on_pixels));
        aw_torch_strength.value=.35f;render(on_pixels,NULL);
        assert(difference(off_pixels,on_pixels)>0);
        aw_torch_strength.value=.7f;render(restored_pixels,NULL);
        assert(difference(on_pixels,restored_pixels)>0);
        for(i=0;i<(1024>>(2*mip));i++)assert(restored_pixels[i]>=on_pixels[i]);
        assert(universal_radius==192 && lights()==1);
    }
    /* A translated and yaw-rotated brush must match the world surface. */
    memset(&brush,0,sizeof brush);brush.origin[0]=100;brush.origin[1]=100;
    brush.angles[1]=90;entity_rotation[0][1]=1;entity_rotation[1][0]=-1;entity_rotation[2][2]=1;
    cl_entities[1].origin[0]=84;cl_entities[1].origin[1]=116;
    for(mip=0;mip<4;mip++)pair(128,50,&brush);mip=0;
    /* Legacy missing lightdata and fullbright intentionally bypass illumination;
     * high baked light saturates. These controls prevent false conclusions. */
    cl_entities[1].origin[0]=cl_entities[1].origin[1]=16;currententity=&cl_entities[0];
    exterior=0;D_FlushCaches();world.lightdata=NULL;set_command("off");render(off_pixels,NULL);
    set_command("on");render(on_pixels,NULL);assert(!difference(off_pixels,on_pixels));
    exterior=1;world.lightdata=samples;D_FlushCaches();r_fullbright.value=1;
    set_command("off");render(off_pixels,NULL);set_command("on");render(on_pixels,NULL);
    assert(!difference(off_pixels,on_pixels));r_fullbright.value=0;
    D_FlushCaches();r_refdef.ambientlight=128;memset(samples,255,sizeof samples);
    set_command("off");render(off_pixels,NULL);set_command("on");render(on_pixels,NULL);
    assert(!difference(off_pixels,on_pixels));
    puts("missing-lightdata, fullbright and saturation controls reproduced; no universal surface-light failure");
    return 0;
}
