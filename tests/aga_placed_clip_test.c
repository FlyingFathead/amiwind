/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM placed collision experiment (chim/chim_placed_clip.c, AW_EXP_PLACED_CLIP):
 * one stored collision shape placed with rotation and scale at run time,
 * against the same shape baked by the builder at that rotation and scale and
 * traced by the engine's own SV_ClipMoveToEntity (today's method).
 *
 * argv: CASES OUT. CASES is written by tests/test_chim_placed_clip.py from
 * the builder's own functions (prepare_scenery.reference_rotation,
 * prepare_mesh_bsp.standing_planes exact). OUT gets one line per case.
 */
#include "quakedef.h"
#include "chim/chim_placed_clip.h"
#include <stdarg.h>
#include <assert.h>

extern qboolean SV_RecursiveHullCheck(hull_t *,int,float,float,vec3_t,vec3_t,trace_t *);
extern trace_t SV_ClipMoveToEntity(edict_t *,vec3_t,vec3_t,vec3_t,vec3_t);
server_t sv;
void Sys_Error(char *fmt,...){va_list ap;va_start(ap,fmt);vfprintf(stderr,fmt,ap);va_end(ap);exit(1);}
void Con_DPrintf(char *fmt,...){}

#define MAXP 4096
static float MINS[3]={-7.32f,-7.12f,-16.625f},MAXS[3]={7.32f,7.12f,16.625f},ZERO[3]={0,0,0};

typedef struct{int n;mplane_t planes[MAXP];dclipnode_t nodes[MAXP];}chain_t;

/* The builder's piece chain (tools/chim/models.py collider): outside a plane
 * goes on to the next piece, inside every plane of a piece is solid. */
static void ReadChain(FILE *f,chain_t *c){
    int pieces,k,j,np,root=0;assert(fscanf(f,"%d",&pieces)==1);c->n=0;
    for(k=0;k<pieces;k++){
        assert(fscanf(f,"%d",&np)==1);
        for(j=0;j<np;j++){
            mplane_t *p=&c->planes[c->n];dclipnode_t *d=&c->nodes[c->n];
            assert(c->n<MAXP);
            assert(fscanf(f,"%f %f %f %f",&p->normal[0],&p->normal[1],&p->normal[2],&p->dist)==4);
            p->type=3;d->planenum=c->n;
            d->children[1]=j+1<np?c->n+1:CONTENTS_SOLID;
            d->children[0]=-1;	/* fixed below */
            c->n++;
        }
        for(j=root;j<c->n;j++)c->nodes[j].children[0]=k+1<pieces?c->n:CONTENTS_EMPTY;
        root=c->n;
    }
}

static int ReadPieces(FILE *f,chim_piece_t *pieces,float *planes,float *verts,short *edges){
    int n,i,j,np,nv,ne,a,b,v,pl=0,vt=0,ed=0;assert(fscanf(f,"%d",&n)==1);
    for(i=0;i<n;i++){
        assert(fscanf(f,"%d %d %d",&np,&nv,&ne)==3);
        pieces[i].numplanes=np;pieces[i].numverts=nv;pieces[i].numedges=ne;
        pieces[i].planes=planes+4*pl;pieces[i].verts=verts+3*vt;pieces[i].edges=edges+3*ed;
        for(j=0;j<np;j++,pl++)assert(fscanf(f,"%f %f %f %f",planes+4*pl,planes+4*pl+1,planes+4*pl+2,planes+4*pl+3)==4);
        for(j=0;j<nv;j++,vt++)assert(fscanf(f,"%f %f %f",verts+3*vt,verts+3*vt+1,verts+3*vt+2)==3);
        for(j=0;j<ne;j++,ed++){assert(fscanf(f,"%d %d %d",&a,&b,&v)==3);edges[3*ed]=a;edges[3*ed+1]=b;edges[3*ed+2]=v;}
    }
    return n;
}

/* Node visits of SV_RecursiveHullCheck (world.c) on the same input, its
 * branches mirrored, with the point-contents walk it makes at each split:
 * the cost of today's method in plane tests. */
static unsigned long visits;
static int ClipChild(short c){return c<-15?(unsigned short)c:c;}
static int Contents(hull_t *h,int num,vec3_t p){
    while(num>=0){dclipnode_t *n=h->clipnodes+num;mplane_t *pl=h->planes+n->planenum;visits++;
        num=ClipChild(n->children[DotProduct(pl->normal,p)-pl->dist<0]);}
    return num;
}
static int Count(hull_t *h,int num,vec3_t p1,vec3_t p2,int *allsolid){
    float t1,t2,frac;vec3_t mid;int side,i;dclipnode_t *n;mplane_t *pl;
    for(;;){
        if(num<0){if(num!=CONTENTS_SOLID)*allsolid=0;return 1;}
        n=h->clipnodes+num;pl=h->planes+n->planenum;visits++;
        t1=DotProduct(pl->normal,p1)-pl->dist;t2=DotProduct(pl->normal,p2)-pl->dist;
        if(t1>=0&&t2>=0){num=ClipChild(n->children[0]);continue;}
        if(t1<0&&t2<0){num=ClipChild(n->children[1]);continue;}
        break;
    }
    frac=t1/(t1-t2);if(frac<0)frac=0;if(frac>1)frac=1;
    for(i=0;i<3;i++)mid[i]=p1[i]+frac*(p2[i]-p1[i]);
    side=t1<0;
    if(!Count(h,ClipChild(n->children[side]),p1,mid,allsolid))return 0;
    if(*allsolid||Contents(h,ClipChild(n->children[side^1]),mid)!=CONTENTS_SOLID)
        return Count(h,ClipChild(n->children[side^1]),mid,p2,allsolid);
    return 0;
}

static chain_t b0,b1,yc;
static chim_piece_t pieces[64];static float lplanes[4*MAXP],lverts[3*MAXP];static short ledges[3*MAXP];
static chim_wpiece_t wp[64];static float wplanes[4*MAXP];

static trace_t Baked(chain_t *c0,chain_t *c1,const float origin[3],float yaw,vec3_t a,vec3_t b,int point,int count){
    static model_t model;static edict_t ent;vec3_t lo,hi,o;int i,allsolid=1;
    memset(&model,0,sizeof model);memset(&ent,0,sizeof ent);model.type=mod_brush;
    model.hulls[0].planes=c0->planes;model.hulls[0].clipnodes=c0->nodes;model.hulls[0].lastclipnode=c0->n-1;
    model.hulls[1].planes=c1->planes;model.hulls[1].clipnodes=c1->nodes;model.hulls[1].lastclipnode=c1->n-1;
    VectorCopy(MINS,model.hulls[1].clip_mins);VectorCopy(MAXS,model.hulls[1].clip_maxs);
    sv.models[1]=&model;ent.v.modelindex=1;ent.v.solid=SOLID_BSP;ent.v.movetype=MOVETYPE_PUSH;
    VectorCopy(origin,ent.v.origin);ent.v.angles[1]=yaw;
    VectorCopy((point?ZERO:MINS),lo);VectorCopy((point?ZERO:MAXS),hi);
    if(count && !yaw){
        hull_t *h=point?&model.hulls[0]:&model.hulls[1];vec3_t s,e;
        for(i=0;i<3;i++){o[i]=h->clip_mins[i]-lo[i]+origin[i];s[i]=a[i]-o[i];e[i]=b[i]-o[i];}
        Count(h,0,s,e,&allsolid);
    }
    return SV_ClipMoveToEntity(&ent,a,lo,hi,b);
}

static float Dist(const float *a,const float *b){vec3_t d;VectorSubtract(a,b,d);return (float)sqrt(DotProduct(d,d));}

int main(int argc,char **argv){
    FILE *f,*out;char name[128];int yawonly,n,i,k,point,np;float scale,origin[3],m[3][3],yaw,ang[3];
    assert(argc==3);f=fopen(argv[1],"r");out=fopen(argv[2],"w");assert(f&&out);
    while(fscanf(f,"%127s",name)==1){
        chim_shape_t shape;chim_xform_t x;chim_wshape_t w0,w1;
        unsigned long hit_match=0,traces=0,normal_diff=0,solid_diff=0,both_hit=0,hits=0,today_bad=0,today_n=0,today_flip=0;float today_both=0;
        unsigned long chain_visits=0,placed_planes=0,prep0,prepf;float maxd=0,today_max=0,mtest[3][3];
        assert(fscanf(f,"%d %f %f %f %f %f %f %f %f",&yawonly,&scale,&origin[0],&origin[1],&origin[2],&ang[0],&ang[1],&ang[2],&yaw)==9);
        for(i=0;i<3;i++)for(k=0;k<3;k++)assert(fscanf(f,"%f",&m[i][k])==1);
        /* the engine builds the builder's matrix from the stored angles */
        ChimPlaced_Matrix(ang[0],ang[1],ang[2],mtest);
        for(i=0;i<3;i++)for(k=0;k<3;k++)assert(fabs(mtest[i][k]-m[i][k])<1e-5);
        shape.numpieces=ReadPieces(f,pieces,lplanes,lverts,ledges);shape.pieces=pieces;
        ReadChain(f,&b0);ReadChain(f,&b1);
        if(yawonly)ReadChain(f,&yc);
        memcpy(x.m,mtest,sizeof x.m);x.scale=scale;VectorCopy(origin,x.origin);
        prep0=chim_placed_stats.prepares;prepf=chim_placed_stats.prepare_flops;
        w0.pieces=wp;w0.cappieces=64;w0.planes=wplanes;w0.capplanes=MAXP/2;
        w1.pieces=wp+32;w1.cappieces=32;w1.planes=wplanes+4*(MAXP/2);w1.capplanes=MAXP/2;
        w0.cappieces=32;
        assert(ChimPlaced_Prepare(&shape,&x,ZERO,ZERO,&w0));
        assert(ChimPlaced_Prepare(&shape,&x,MINS,MAXS,&w1));
        prepf=(chim_placed_stats.prepare_flops-prepf)/2;
        assert(fscanf(f,"%d",&n)==1);
        for(i=0;i<n;i++){
            vec3_t a,b;trace_t t0,t1,ty;unsigned long before=chim_placed_stats.planes_tested;
            assert(fscanf(f,"%d %f %f %f %f %f %f",&point,&a[0],&a[1],&a[2],&b[0],&b[1],&b[2])==7);
            visits=0;
            t0=Baked(&b0,&b1,origin,0,a,b,point,1);
            chain_visits+=visits;
            ChimPlaced_Trace(point?&w0:&w1,a,b,&t1);
            placed_planes+=chim_placed_stats.planes_tested-before;
            traces++;
            if(t0.startsolid!=t1.startsolid||t0.allsolid!=t1.allsolid){solid_diff++;continue;}
            if(t0.fraction<1)hits++;
            {float d=Dist(t0.endpos,t1.endpos);if(d>maxd)maxd=d;
             if(d<0.05f && (t0.fraction<1)==(t1.fraction<1))hit_match++;
             else fprintf(out,"# %s miss trace %d point %d f %g %g end %g %g %g / %g %g %g\n",name,i,point,
                 t0.fraction,t1.fraction,t0.endpos[0],t0.endpos[1],t0.endpos[2],t1.endpos[0],t1.endpos[1],t1.endpos[2]);}
            if(t0.fraction<1&&t1.fraction<1&&!t0.allsolid){both_hit++;if(DotProduct(t0.plane.normal,t1.plane.normal)<0.999f)normal_diff++;}
            if(yawonly&&!point){
                /* today: built at yaw 0, the engine turns the trace (the box turns with the model) */
                float d;ty=Baked(&b0,&yc,origin,yaw,a,b,0,0);today_n++;
                if((t0.fraction<1)!=(ty.fraction<1))today_flip++;
                else if(t0.fraction<1&&!t0.allsolid&&!ty.allsolid&&Dist(t0.endpos,ty.endpos)>today_both)today_both=Dist(t0.endpos,ty.endpos);
                d=Dist(t0.endpos,ty.endpos);if(t0.startsolid!=ty.startsolid)d=1e3f;
                if(d<1e3f&&d>today_max)today_max=d;
                if(d>0.05f)today_bad++;
            }
        }
        np=w1.numplanes;
        fprintf(out,"%s traces %lu match %lu solid_diff %lu hits %lu normal_diff %lu of %lu maxd %.5f "
            "chain_visits %.2f placed_planes %.2f prepare_flops %lu world_planes %d baked_planes %d "
            "today %lu today_bad %lu today_max %.4f today_flip %lu today_both %.4f\n",name,traces,hit_match,solid_diff,hits,normal_diff,both_hit,maxd,
            (double)chain_visits/traces,(double)placed_planes/traces,prepf,np,b1.n,today_n,today_bad,today_max,today_flip,today_both);
        (void)prep0;
    }
    fclose(f);fclose(out);
    return 0;
}
