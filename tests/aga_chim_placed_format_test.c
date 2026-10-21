/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM world format 0.8 (EXPERIMENTAL): the same synthetic placements in a
 * 0.7 world and a 0.8 world, both written by the CHIM builder
 * (tests/test_chim_placed_format.py), traced the way each world is traced:
 * 0.7: the stored hulls of the placement's own variant (scale and tilt baked)
 * turned by the record's yaw, through world.c SV_ClipMoveToEntity (what
 * chim_chunks.c ClipModel does); 0.8: the untilted model's piece table,
 * placed by the record's three angles (ChimPlaced_AnglesMatrix) and expanded
 * by the world-aligned box (ChimPlaced_TraceTable). A third reference: the
 * builder's exact expansion (prepare_mesh_bsp.standing_planes exact) of the
 * same pieces turned by the full rotation, as a chain at the placement with
 * no turn left (what the 0.7 builder bakes for a tilted variant at yaw 0).
 *
 * argv: CASES OUT. OUT gets one line per case.
 */
#include "quakedef.h"
#include "chim/chim_placed_clip.h"
#include <stdarg.h>
#include <assert.h>

extern trace_t SV_ClipMoveToEntity(edict_t *,vec3_t,vec3_t,vec3_t,vec3_t);
server_t sv;
void Sys_Error(char *fmt,...){va_list ap;va_start(ap,fmt);vfprintf(stderr,fmt,ap);va_end(ap);exit(1);}
void Con_DPrintf(char *fmt,...){}

#define MAXP 4096
static float MINS[3]={-7.32f,-7.12f,-16.625f},MAXS[3]={7.32f,7.12f,16.625f},ZERO[3]={0,0,0};
typedef struct{mplane_t planes[MAXP];dclipnode_t h0[MAXP],h1[MAXP];int root0,n0,root1,n1;}hullset_t;
static hullset_t stored,exact;
static unsigned char table[1<<20];

static void ReadNodes(FILE *f,dclipnode_t *nodes,int *root,int *n){
    int i,p,a,b;assert(fscanf(f,"%d %d",root,n)==2);assert(*n<MAXP);
    for(i=0;i<*n;i++){assert(fscanf(f,"%d %d %d",&p,&a,&b)==3);nodes[i].planenum=p;nodes[i].children[0]=a;nodes[i].children[1]=b;}
}

static void ReadSet(FILE *f,hullset_t *s){
    int np,i;assert(fscanf(f,"%d",&np)==1);assert(np<MAXP);
    for(i=0;i<np;i++){assert(fscanf(f,"%f %f %f %f",&s->planes[i].normal[0],&s->planes[i].normal[1],&s->planes[i].normal[2],&s->planes[i].dist)==4);s->planes[i].type=3;}
    ReadNodes(f,s->h0,&s->root0,&s->n0);ReadNodes(f,s->h1,&s->root1,&s->n1);
}

static trace_t Old(const hullset_t *s,const float origin[3],float yaw,vec3_t a,vec3_t b,int point){
    static model_t model;static edict_t ent;vec3_t lo,hi;
    memset(&model,0,sizeof model);memset(&ent,0,sizeof ent);model.type=mod_brush;
    model.hulls[0].planes=(mplane_t *)s->planes;model.hulls[0].clipnodes=(dclipnode_t *)s->h0;model.hulls[0].firstclipnode=s->root0;model.hulls[0].lastclipnode=s->n0-1;
    model.hulls[1].planes=(mplane_t *)s->planes;model.hulls[1].clipnodes=(dclipnode_t *)s->h1;model.hulls[1].firstclipnode=s->root1;model.hulls[1].lastclipnode=s->n1-1;
    VectorCopy(MINS,model.hulls[1].clip_mins);VectorCopy(MAXS,model.hulls[1].clip_maxs);
    sv.models[1]=&model;ent.v.modelindex=1;ent.v.solid=SOLID_BSP;ent.v.movetype=MOVETYPE_PUSH;
    VectorCopy(origin,ent.v.origin);ent.v.angles[1]=yaw;
    VectorCopy((point?ZERO:MINS),lo);VectorCopy((point?ZERO:MAXS),hi);
    return SV_ClipMoveToEntity(&ent,a,lo,hi,b);
}

static float Dist(const float *a,const float *b){vec3_t d;VectorSubtract(a,b,d);return (float)sqrt(DotProduct(d,d));}

int main(int argc,char **argv){
    FILE *f,*out;char name[128];
    assert(argc==3);f=fopen(argv[1],"r");out=fopen(argv[2],"w");assert(f&&out);
    while(fscanf(f,"%127s",name)==1){
        float yaw,o0[3],o1[3],ang[3],m[3][3],maxd_point=0,maxd_box=0,exact_maxd=0;int i,bytes,n,point,usable;
        unsigned long traces[2]={0,0},match[2]={0,0},solid_diff[2]={0,0},flips[2]={0,0},exact_match=0,exact_solid=0;
        assert(fscanf(f,"%f %f %f %f %f %f %f %f %f %f",&yaw,&o0[0],&o0[1],&o0[2],&o1[0],&o1[1],&o1[2],&ang[0],&ang[1],&ang[2])==10);
        ReadSet(f,&stored);ReadSet(f,&exact);
        assert(fscanf(f,"%d",&bytes)==1);assert(bytes<(int)sizeof table);
        for(i=0;i<bytes;i++){unsigned v;assert(fscanf(f,"%2x",&v)==1);table[i]=(unsigned char)v;}
        usable=ChimPlaced_TableLoad(table,bytes);
        /* a second load of a converted table only checks it */
        assert(ChimPlaced_TableLoad(table,bytes)==usable);
        ChimPlaced_AnglesMatrix(ang,m);
        assert(fscanf(f,"%d",&n)==1);
        for(i=0;i<n;i++){
            vec3_t a,b;trace_t t0,t1,t2;float d;
            assert(fscanf(f,"%d %f %f %f %f %f %f",&point,&a[0],&a[1],&a[2],&b[0],&b[1],&b[2])==7);
            t0=Old(&stored,o0,yaw,a,b,point);
            t2=Old(&exact,o1,0,a,b,point);
            memset(&t1,0,sizeof t1);t1.fraction=1;VectorCopy(b,t1.endpos);
            assert(usable);
            assert(ChimPlaced_TraceTable(table,(const float (*)[3])m,o1,a,point?ZERO:MINS,point?ZERO:MAXS,b,&t1));
            traces[!point]++;
            /* against the exact expansion at the full rotation: every trace */
            if(t2.startsolid!=t1.startsolid||t2.allsolid!=t1.allsolid)exact_solid++;
            else{d=Dist(t2.endpos,t1.endpos);if(d>exact_maxd)exact_maxd=d;
                if(d<0.05f&&(t2.fraction<1)==(t1.fraction<1))exact_match++;
                else fprintf(out,"# %s exact trace %d point %d f %g %g\n",name,i,point,t2.fraction,t1.fraction);}
            if(t0.startsolid!=t1.startsolid||t0.allsolid!=t1.allsolid){solid_diff[!point]++;continue;}
            d=Dist(t0.endpos,t1.endpos);
            if(point){if(d>maxd_point)maxd_point=d;}else if(d>maxd_box)maxd_box=d;
            if((t0.fraction<1)!=(t1.fraction<1))flips[!point]++;
            if(d<0.05f&&(t0.fraction<1)==(t1.fraction<1))match[!point]++;
            else fprintf(out,"# %s trace %d point %d f %g %g end %g %g %g / %g %g %g\n",name,i,point,
                t0.fraction,t1.fraction,t0.endpos[0],t0.endpos[1],t0.endpos[2],t1.endpos[0],t1.endpos[1],t1.endpos[2]);
        }
        fprintf(out,"%s usable %d point %lu point_match %lu point_solid_diff %lu point_maxd %.5f "
            "box %lu box_match %lu box_solid_diff %lu box_flips %lu box_maxd %.5f "
            "exact_match %lu exact_solid_diff %lu exact_maxd %.5f\n",name,usable,traces[0],match[0],
            solid_diff[0],maxd_point,traces[1],match[1],solid_diff[1],flips[1],maxd_box,exact_match,exact_solid,exact_maxd);
    }
    printf("table traces %lu pieces met %lu full %lu\n",chim_placed_stats.table_traces,chim_placed_stats.pieces_met,
        chim_placed_stats.table_full);
    fclose(f);fclose(out);
    return 0;
}
