/* Asset-free range view regression; compile with -Iengine/aga/src -lm. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdarg.h>
#define AW_RENDER_RANGES_TEST
#define MAX_MODELS 256
#define MAX_EDICTS 600
typedef int qboolean;
#define true 1
#define false 0
typedef float vec3_t[3];
typedef struct {char name[64];int type,firstmodelsurface,nummodelsurfaces,numsurfaces;void *surfaces;vec3_t mins,maxs;float radius;int hulls[4];char *entities;} model_t;
typedef struct {model_t *model;vec3_t origin,angles;} entity_t;
enum {mod_brush};
static struct {model_t *worldmodel,*model_precache[MAX_MODELS];} cl;
#define VectorClear(v) memset(v,0,sizeof(vec3_t))
#define VectorCopy(a,b) memcpy(b,a,sizeof(vec3_t))
static void Sys_Error(const char *s){fprintf(stderr,"%s\n",s);abort();}
static void *Hunk_AllocName(int n,const char *s){(void)s;return calloc(1,n);}
static void Con_Printf(const char *s,...){(void)s;}
#include "../engine/aga/src/aw_render_ranges.c"
int main(void)
{
    model_t original,pool,view,saved;entity_t entity;aw_range_record_t record;int dummy;
    memset(&original,0,sizeof(original));memset(&pool,0,sizeof(pool));memset(&entity,0,sizeof(entity));memset(&record,0,sizeof(record));
    original.surfaces=pool.surfaces=&dummy;original.firstmodelsurface=12;original.nummodelsurfaces=9;original.numsurfaces=100;
    original.mins[0]=-4;original.maxs[0]=5;original.radius=7;original.hulls[0]=31;
    pool.firstmodelsurface=70;pool.nummodelsurfaces=20;pool.radius=100000;
    record.model=&original;record.count=1;record.ranges[0].start=3;record.ranges[0].count=4;record.origin[0]=10;record.angles[1]=359.8f;
    entity.model=&original;entity.origin[0]=10.125f;entity.angles[1]=-1.40625f; /* actual MSG_WriteAngle/ReadAngle for359.8 */
    aw_records=&record;aw_pool=&pool;saved=original;
    assert(AW_RenderRangeView(&entity,0,&view));
    assert(view.firstmodelsurface==73 && view.nummodelsurfaces==4);
    assert(view.radius==7 && view.mins[0]==-4 && view.maxs[0]==5 && view.hulls[0]==31);
    assert(view.surfaces==original.surfaces && entity.model==&original && memcmp(&saved,&original,sizeof(saved))==0);
    assert(!AW_RenderRangeView(&entity,1,&view));entity.origin[0]=11;assert(!AW_RenderRangeView(&entity,0,&view));
    cl.worldmodel=NULL;AW_RenderRangesNewMap();assert(!aw_records && !aw_pool);
    return 0;
}
