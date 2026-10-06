/* SPDX-License-Identifier: GPL-2.0-or-later
 * Exercise the real arena allocator/cache lookup. OLD_CACHE also runs the
 * unchanged four-pointer implementation as an output-equivalence control. */
#include <assert.h>
#include <stddef.h>
#include <time.h>
#include "quakedef.h"
#include "d_local.h"
#include "r_local.h"
int r_framecount=1,c_surf,d_lightstylevalue[256];
qboolean msg_suppress_1=true,d_roverwrapped;
surfcache_t *d_initial_rover;
drawsurf_t r_drawsurf;
static texture_t textures[2];
static int animated;
static unsigned random_state=23129,draws;
static unsigned long long digest=1469598103934665603ULL;
static msurface_t *map_surfaces;
static mtexinfo_t texinfo;
static union {double alignment;byte data[32772];} arena;
extern surfcache_t *sc_base;
extern int sc_size;
extern surfcache_t *D_SCAlloc(int width,int size);
void Sys_Error(char *fmt,...){va_list a;va_start(a,fmt);vfprintf(stderr,fmt,a);va_end(a);abort();}
void Con_Printf(char *fmt,...){(void)fmt;}
texture_t *R_TextureAnimation(texture_t *base){(void)base;return &textures[animated];}
static unsigned next_random(void){random_state=random_state*1664525U+1013904223U;return random_state;}
static int cache_mip(surfcache_t *c){
#ifdef OLD_CACHE
    int mip;for(mip=0;mip<MIPLEVELS;mip++)if(c->mipscale==1.0/(1<<mip))return mip;return -1;
#else
    return c->mip;
#endif
}
static byte pixel(msurface_t *s,int mip,int i){return (byte)((s-map_surfaces)*7+mip*17+i*3+animated*47+d_lightstylevalue[s->styles[0]]+(s->dlightframe==r_framecount?91:0));}
void R_DrawSurface(void){int i,n=r_drawsurf.surfwidth*r_drawsurf.surfheight;draws++;for(i=0;i<n;i++)r_drawsurf.surfdat[i]=pixel(r_drawsurf.surf,r_drawsurf.surfmip,i);}
static void validate(void)
{
    int i,mip,mask,count,blocks=0,total=0,owned=0,listed=0;surfcache_t *c;
    for(c=sc_base;c;c=c->next){assert(++blocks<1000);assert((byte *)c>=arena.data && (byte *)c<arena.data+sc_size);assert(c->size>0);total+=c->size;if(c->owner){assert(*c->owner==c);owned++;}}
    assert(total==sc_size);
    for(i=0;i<128;i++){
#ifdef OLD_CACHE
        for(mip=0;mip<MIPLEVELS;mip++){c=map_surfaces[i].cachespots[mip];if(c){assert(c->owner==&map_surfaces[i].cachespots[mip]);assert(cache_mip(c)==mip);listed++;}}
#else
        surfcache_t **owner=&map_surfaces[i].cachehead;mask=0;count=0;
        for(c=map_surfaces[i].cachehead;c;c=c->surface_next){
            assert(++count<=MIPLEVELS);assert(c->owner==owner);assert(*owner==c);
            mip=cache_mip(c);
            assert(mip<MIPLEVELS && !(mask&(1<<mip)));mask|=1<<mip;
            owner=&c->surface_next;listed++;
        }
#endif
    }
    assert(owned==listed);
}
static void sample(int n,int mip)
{
    int i,count=(map_surfaces[n].extents[0]>>mip)*(map_surfaces[n].extents[1]>>mip);surfcache_t *c=D_CacheSurface(&map_surfaces[n],mip);
    assert(cache_mip(c)==mip);assert(c->texture==&textures[animated]);
    for(i=0;i<count;i++){assert(c->data[i]==pixel(&map_surfaces[n],mip,i));digest^=c->data[i];digest*=1099511628211ULL;}
}
static void new_map(void)
{
    int i;D_FlushCaches();if(map_surfaces){validate();free(map_surfaces);}map_surfaces=calloc(128,sizeof(*map_surfaces));assert(map_surfaces);
    for(i=0;i<128;i++){map_surfaces[i].texinfo=&texinfo;map_surfaces[i].extents[0]=map_surfaces[i].extents[1]=32;map_surfaces[i].styles[0]=i%16;map_surfaces[i].styles[1]=map_surfaces[i].styles[2]=map_surfaces[i].styles[3]=255;}
}
int main(int argc,char **argv)
{
    int i,j,n,mip;unsigned before,histogram[5]={0};clock_t start;double elapsed;
    D_InitCaches(arena.data,sizeof(arena.data));new_map();for(i=0;i<256;i++)d_lightstylevalue[i]=256;
    /* All four mip levels coexist, repeated requests are true hits. */
    for(i=0;i<4;i++)sample(0,i);before=draws;for(j=0;j<10;j++)for(i=0;i<4;i++)sample(0,i);assert(draws==before);validate();
    /* Lighting and animated textures reuse the block but invalidate pixels. */
    animated=1;sample(0,2);assert(draws==before+1);d_lightstylevalue[0]++;sample(0,2);assert(draws==before+2);
    map_surfaces[0].dlightframe=r_framecount;sample(0,2);sample(0,2);assert(draws==before+4);r_framecount++;sample(0,2);assert(draws==before+5);sample(0,2);assert(draws==before+5);validate();
    /* Force eviction of middle, head and tail mips and adjacent coalescing. */
    for(i=0;i<4;i++){
        surfcache_t *victim=D_CacheSurface(&map_surfaces[0],i);sc_rover=victim;D_SCAlloc(32,1024);validate();sample(0,i);validate();
    }
    sc_rover=sc_base;D_SCAlloc(0,16384);validate();
    for(i=0;i<24000;i++){
        unsigned r=next_random();n=(r>>8)%128;mip=(r>>20)%4;
        if(i%43==0)animated^=1;
        if(i%67==0)d_lightstylevalue[(r>>16)%16]++;
        if(i%17==0)r_framecount++;
        if(i%13==0)map_surfaces[n].dlightframe=r_framecount;
        sample(n,mip);validate();
        if(i%239==0){D_SCAlloc(0,16384);validate();}
        if(i%997==0){D_FlushCaches();validate();}
        if(i%4001==0)new_map();
    }
    printf("OUTPUT %016llx\n",digest);
    new_map();animated=0;for(i=0;i<4;i++)sample(0,i);before=draws;
    for(i=0;i<4;i++){
        surfcache_t *c;int probes=0;mip=i&3;
#ifdef OLD_CACHE
        probes=1;
#else
        for(c=map_surfaces[0].cachehead;c;c=c->surface_next){probes++;if(cache_mip(c)==mip)break;}
#endif
        histogram[probes]+=1000000;
    }
    start=clock();
    for(i=0;i<4000000;i++){
        surfcache_t *c;mip=i&3;c=D_CacheSurface(&map_surfaces[0],mip);assert(c->data[0]==pixel(&map_surfaces[0],mip,0));
    }
    elapsed=(double)(clock()-start)/CLOCKS_PER_SEC;assert(draws==before);
    printf("LOOKUP host_seconds=%.6f probes=%u,%u,%u,%u,%u calls=4000000\n",elapsed,histogram[0],histogram[1],histogram[2],histogram[3],histogram[4]);
    D_FlushCaches();validate();free(map_surfaces);map_surfaces=NULL;
    /* Flushing an already empty arena after map storage is gone is safe. */
    D_FlushCaches();D_SCAlloc(0,16384);D_FlushCaches();
    puts("PASS four mips, hits, animation, styles, dynamic lights, head/middle/tail eviction, coalescing, wrap, flush and seven map lifetimes");return 0;
}
