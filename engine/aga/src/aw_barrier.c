/* SPDX-License-Identifier: GPL-2.0-or-later
 * Authored collision-only boxes, including full pitch/roll/yaw. Bounded storage
 * outlives a scene; no scene or hunk pointers are retained. */
#include "quakedef.h"
#include "aw_story.h"
#define AW_BARRIERS 32
typedef struct {vec3_t centre,axis[3],half;} aw_barrier_t;
static aw_barrier_t boxes[AW_BARRIERS];
static int count;

static float read_float(const byte *p)
{
    float f;
    memcpy(&f,p,4);
    return LittleFloat(f);
}

int AW_BarrierDecode(const byte *raw,int size)
{
    int n,i,j,k,at=6;
    aw_barrier_t b;
    count=0;
    if(size<6 || memcmp(raw,"AWB1",4))return 0;
    n=raw[4]+(raw[5]<<8);
    if(n<1 || n>AW_BARRIERS || size!=6+n*60)return 0;
    for(i=0;i<n;i++){
        for(j=0;j<3;j++,at+=4){
            b.centre[j]=read_float(raw+at);
            if(!(fabs(b.centre[j])<32768))return 0;
        }
        for(j=0;j<3;j++)for(k=0;k<3;k++,at+=4){
            b.axis[j][k]=read_float(raw+at);
            if(!(fabs(b.axis[j][k])<=1.001))return 0;
        }
        for(j=0;j<3;j++,at+=4){
            b.half[j]=read_float(raw+at);
            if(!(b.half[j]>.01 && b.half[j]<1024))return 0;
            if(fabs(DotProduct(b.axis[j],b.axis[j])-1)>.001)return 0;
            for(k=0;k<j;k++)if(fabs(DotProduct(b.axis[j],b.axis[k]))>.001)return 0;
        }
        boxes[i]=b;
    }
    count=n;
    return 1;
}

int AW_BarrierLoad(void)
{
    FILE *f=NULL;
    byte raw[6+AW_BARRIERS*60];
    int size;
    count=0;
    size=COM_FOpenFile("intro/barriers.awb",&f);
    if(!f)return 0;
    if(size<6 || size>(int)sizeof(raw) || fread(raw,1,size,f)!=(size_t)size){fclose(f);return 0;}
    fclose(f);
    return AW_BarrierDecode(raw,size);
}

/* Swept separating-axis test for an AABB and an OBB. The 15 axes include the
 * edge cross-products; the six face axes alone miss corner separations. */
static void sweep(aw_barrier_t *b,vec3_t start,vec3_t mins,vec3_t maxs,
                  vec3_t end,trace_t *trace)
{
    vec3_t axes[15],offset,half,velocity,normal;
    float r,p,v,a,z,enter=-1e30f,leave=1e30f,length,hit,closing=1;
    int i,j,k,inside=1,ends_inside=1;
    memset(axes,0,sizeof(axes));VectorCopy(vec3_origin,normal);
    for(i=0;i<3;i++){
        axes[i][i]=1;VectorCopy(b->axis[i],axes[3+i]);
        offset[i]=start[i]+(mins[i]+maxs[i])*.5f-b->centre[i];
        half[i]=(maxs[i]-mins[i])*.5f;velocity[i]=end[i]-start[i];
    }
    for(i=0;i<3;i++)for(j=0;j<3;j++)CrossProduct(axes[i],b->axis[j],axes[6+i*3+j]);
    for(i=0;i<15;i++){
        /* Engine Length uses an approximate reciprocal square root. Collision
         * plane normals must be unit length for sliding response. */
        length=(float)sqrt(DotProduct(axes[i],axes[i]));if(length<.0001f)continue;
        VectorScale(axes[i],1/length,axes[i]);
        r=0;
        for(j=0;j<3;j++)r+=half[j]*fabs(axes[i][j])+b->half[j]*fabs(DotProduct(axes[i],b->axis[j]));
        p=DotProduct(offset,axes[i]);v=DotProduct(velocity,axes[i]);
        if(p<=-r || p>=r)inside=0;
        if(p+v<=-r || p+v>=r)ends_inside=0;
        if(fabs(v)<.000001f){if(p<=-r || p>=r)return;continue;}
        a=(-r-p)/v;z=(r-p)/v;
        if(a>z){hit=a;a=z;z=hit;}
        if(a>enter){
            enter=a;closing=fabs(v);
            for(k=0;k<3;k++)normal[k]=v>0?-axes[i][k]:axes[i][k];
        }
        if(z<leave)leave=z;
        if(enter>leave)return;
    }
    if(inside){
        trace->startsolid=true;
        if(ends_inside){trace->allsolid=true;trace->fraction=0;VectorCopy(start,trace->endpos);trace->ent=sv.edicts;}
        return;
    }
    if(enter<0 || enter>1 || leave<0)return;
    hit=enter-.03125f/closing;if(hit<0)hit=0;
    if(hit>=trace->fraction)return;
    trace->fraction=hit;trace->ent=sv.edicts;
    VectorCopy(normal,trace->plane.normal);
    for(i=0;i<3;i++)trace->endpos[i]=start[i]+hit*velocity[i];
    trace->plane.dist=DotProduct(normal,trace->endpos);
}

void AW_BarrierClip(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,
                    edict_t *entity,trace_t *trace)
{
    int i;
    if(!count || !AW_StoryRestricted() || strcmp(sv.name,"seyda") ||
       !svs.clients || entity!=svs.clients[0].edict ||
       entity->v.movetype!=MOVETYPE_WALK || maxs[2]-mins[2]<1)return;
    for(i=0;i<count;i++)sweep(&boxes[i],start,mins,maxs,end,trace);
}
