/* SPDX-License-Identifier: GPL-2.0-or-later
 * Registry lookup through the ACTUAL common.c coordinate/angle protocol. */
#include "quakedef.h"
#include <assert.h>
#include <setjmp.h>
#include <stdarg.h>
#define AW_RENDER_RANGES_TEST
#include "aw_render_ranges.c"

client_state_t cl;
sizebuf_t net_message;
static jmp_buf fatal;
static int expect_fatal;
static char error_text[256];
static void *allocations[8];static int allocation_count;
void Sys_Error(char *fmt,...){va_list ap;va_start(ap,fmt);vsnprintf(error_text,sizeof error_text,fmt,ap);va_end(ap);if(expect_fatal)longjmp(fatal,1);fprintf(stderr,"%s\n",error_text);abort();}
void Con_Printf(char *fmt,...){}
void Con_DPrintf(char *fmt,...){}
void *Hunk_AllocName(int size,char *name){void *p=calloc(1,size);assert(p && allocation_count<8);allocations[allocation_count++]=p;return p;}
static model_t original,pool,world;
static msurface_t surface;
static char entities[4096];
static const float source_origin[3]={-359.80859f,267.83594f,30.06427f};
static void cleanup(void){int i;for(i=0;i<allocation_count;i++)free(allocations[i]);allocation_count=0;aw_records=NULL;aw_pool=NULL;}
static void setup(float *angles,const float *other,int same_ranges){
    int i;cleanup();memset(&cl,0,sizeof cl);memset(&original,0,sizeof original);memset(&pool,0,sizeof pool);memset(&world,0,sizeof world);
    strcpy(original.name,"*72");strcpy(pool.name,"*120");original.type=pool.type=mod_brush;original.surfaces=pool.surfaces=&surface;
    original.firstmodelsurface=16346;original.nummodelsurfaces=733;original.numsurfaces=40000;original.radius=95;
    original.mins[0]=-57.5f;original.maxs[0]=60.5f;original.hulls[0].firstclipnode=31;
    pool.firstmodelsurface=26138;pool.nummodelsurfaces=5000;pool.numsurfaces=40000;
    cl.worldmodel=&world;cl.model_precache[72]=&original;cl.model_precache[120]=&pool;world.entities=entities;
    sprintf(entities,"{\"classname\" \"worldspawn\" \"aw_render_pool\" \"*120\"}\n"
        "{\"classname\" \"func_wall\" \"model\" \"*72\" \"origin\" \"%.9g %.9g %.9g\" \"angles\" \"%.9g %.9g %.9g\" \"aw_render_ranges\" \"4200:140\"}\n",
        source_origin[0],source_origin[1],source_origin[2],angles[0],angles[1],angles[2]);
    if(other)sprintf(entities+strlen(entities),"{\"classname\" \"func_wall\" \"model\" \"*72\" \"origin\" \"%.9g %.9g %.9g\" \"angles\" \"%.9g %.9g %.9g\" \"aw_render_ranges\" \"%d:140\"}\n",
        source_origin[0],source_origin[1],source_origin[2],other[0],other[1],other[2],same_ranges?4200:4400);
    AW_RenderRangesNewMap();
}
static void wire(entity_t *entity,const float *angles){
    byte bytes[64];int k;memset(&net_message,0,sizeof net_message);net_message.data=bytes;net_message.maxsize=sizeof bytes;
    for(k=0;k<3;k++){MSG_WriteCoord(&net_message,source_origin[k]);MSG_WriteAngle(&net_message,angles[k]);}
    memset(entity,0,sizeof *entity);entity->model=&original;MSG_BeginReading();
    for(k=0;k<3;k++){entity->origin[k]=MSG_ReadCoord();entity->angles[k]=MSG_ReadAngle();}
    assert(!msg_badread && msg_readcount==9);
}
static void check(const float *angles,int expected){
    entity_t entity;model_t view,saved;int k,wrap;wire(&entity,angles);saved=original;
    for(wrap=-1;wrap<=1;wrap++){
        for(k=0;k<3;k++)entity.angles[k]+=wrap*360;
        assert(AW_RenderRangeView(&entity,0,&view));
        assert(view.firstmodelsurface==expected && view.nummodelsurfaces==140);
        assert(view.radius==original.radius && view.mins[0]==original.mins[0] && view.maxs[0]==original.maxs[0]);
        assert(view.hulls[0].firstclipnode==31 && view.surfaces==original.surfaces && entity.model==&original);
        assert(!memcmp(&saved,&original,sizeof saved));assert(!AW_RenderRangeView(&entity,1,&view));
        for(k=0;k<3;k++)entity.angles[k]-=wrap*360;
    }
    entity.angles[1]+=17;assert(!AW_RenderRangeView(&entity,0,&view));
}
int main(int argc,char **argv){
    float angles[3]={0,-153.735168f,0},other[3]={0,0,0};entity_t entity;model_t view;
    int code,sign,j,cases=0;float offsets[5]={-.999f,-.001f,0,.001f,.999f};
    setup(angles,NULL,0);wire(&entity,angles);assert(entity.angles[1]==-151.875f);
    check(angles,30338);
    if(argc>1 && !strcmp(argv[1],"indrele")){cleanup();puts("actual wire: Indrele auxiliary walls recovered");return 0;}
    for(sign=-1;sign<=1;sign+=2)for(code=0;code<256;code++)for(j=0;j<5;j++){
        angles[1]=sign*(code*1.40625f+offsets[j]);angles[0]=-angles[1]/3;angles[2]=angles[1]/7;
        setup(angles,NULL,0);check(angles,30338);cases++;
    }
    /* Close original angles with DISTINCT wire values must select their own
     * ranges. A widened2.40625-degree threshold would match both here. */
    angles[0]=angles[2]=0;angles[1]=11.9f;other[1]=14.1f;
    setup(angles,other,0);check(angles,30338);check(other,30538);
    /* Wire collisions straddling zero can exceed the former3-degree load test. */
    angles[1]=1.9f;other[1]=-1.9f;expect_fatal=1;
    if(!setjmp(fatal)){setup(angles,other,0);assert(!"ambiguous wire placement accepted");}
    else assert(strstr(error_text,"render range placement"));expect_fatal=0;
    /* Identical range outputs remain harmless, preserving duplicate entries. */
    setup(angles,other,1);check(angles,30338);check(other,30338);
    /* Runtime guard also rejects a conflict even if a bad registry bypassed
     * normal initialization. Never take whichever list record happens first. */
    assert(aw_records && aw_records->next);aw_records->ranges[0].start=4400;
    wire(&entity,angles);assert(!AW_RenderRangeView(&entity,0,&view));
    setup(angles,NULL,0);wire(&entity,angles);entity.origin[0]=NAN;assert(!AW_RenderRangeView(&entity,0,&view));
    wire(&entity,angles);entity.angles[0]=NAN;assert(!AW_RenderRangeView(&entity,0,&view));
    cleanup();printf("actual MSG writer/reader: %d angle-boundary cases, +/-360 wraps, range identity and ambiguity gates passed\n",cases);return 0;
}
