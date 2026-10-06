/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real edge projection/clipping/cache code. Same fixture runs old and packed.
 * Digest includes ordered edge/surface output with normalized pointer IDs. */
#include <assert.h>
#include <setjmp.h>
#include "model.c"
static unsigned char heap[32768];static int used;
static jmp_buf failure;static int expecting;
static int service_calls;
static void service(void){service_calls++;}
static int il(int n){return n;}static short is(short n){return n;}static float iff(float n){return n;}
int (*LittleLong)(int)=il;short (*LittleShort)(short)=is;float (*LittleFloat)(float)=iff;
void *Hunk_AllocName(int n,char *name){void *p=heap+used;assert(n>=0 && used+n+16<(int)sizeof(heap));used+=(n+15)&~15;memset(p,0,(n+15)&~15);return p;}
void Sys_Error(char *fmt,...){if(expecting)longjmp(failure,1);fprintf(stderr,"unexpected %s\n",fmt);abort();}
int AW_SeaLevelEnabled(void){return 1;}
entity_t *currententity;vec3_t modelorg;
qboolean insubmodel;int r_framecount,r_outofsurfaces,r_outofedges,r_polycount,r_currentkey;
float xscale,yscale,xcenter,ycenter,xscaleinv,yscaleinv;
refdef_t r_refdef;mvertex_t *r_pcurrentvertbase;
edge_t *r_edges,*edge_p,*edge_max,*newedges[MAXHEIGHT],*removeedges[MAXHEIGHT];
surf_t *surfaces,*surface_p,*surf_max;
void TransformVector(vec3_t in,vec3_t out){memcpy(out,in,sizeof(vec3_t));}
static model_t model;static entity_t entity;static mvertex_t vertices[6];static medge_t edges[10];
static int sequences[]={1,2,3,4,5,6,7,-2,0,8,9};
static msurface_t faces[3];static mplane_t plane;static mtexinfo_t texinfo;static texture_t texture;
static edge_t emitted[128];static surf_t drawn[32];
static unsigned long long hash=1469598103934665603ULL;
static void digest(const void *p,int n){const byte *b=p;int i;for(i=0;i<n;i++){hash^=b[i];hash*=1099511628211ULL;}}
static void number(int n){digest(&n,sizeof(n));}
static int edgeid(edge_t *e){return e?(int)(e-emitted):-1;}
static void output(void){
    int i,n=(int)(edge_p-r_edges),owner;edge_t *e;surf_t *s;
    number(n);number((int)(surface_p-surfaces));
    for(i=0;i<n;i++){
        e=&emitted[i];number(e->u);number(e->u_step);digest(e->surfs,sizeof(e->surfs));digest(&e->nearzi,sizeof(e->nearzi));
        owner=-1;{int j;for(j=0;j<10;j++)if(e->owner==&edges[j])owner=j;}
        number(owner);number(edgeid(e->next));number(edgeid(e->nextremove));
    }
    for(i=0;i<200;i++){number(edgeid(newedges[i]));number(edgeid(removeedges[i]));}
    for(s=surfaces+1;s<surface_p;s++){
        number((msurface_t *)s->data-faces);number(s->flags);number(s->insubmodel);number(s->key);
        digest(&s->nearzi,sizeof(s->nearzi));digest(&s->d_zistepu,sizeof(s->d_zistepu));
        digest(&s->d_zistepv,sizeof(s->d_zistepv));digest(&s->d_ziorigin,sizeof(s->d_ziorigin));
    }
}
static void geometry(void){
    int i;static const float points[6][3]={{-8,-8,32},{0,-8,32},{0,8,32},{-8,8,32},{8,-8,32},{8,8,32}};
    static const unsigned short pairs[10][2]={{2,0},{0,1},{1,2},{2,3},{3,0},{1,4},{4,5},{5,2},{2,4},{4,0}};
    memset(&model,0,sizeof(model));memset(edges,0,sizeof(edges));memset(faces,0,sizeof(faces));
    for(i=0;i<6;i++)memcpy(vertices[i].position,points[i],12);
    for(i=0;i<10;i++)memcpy(edges[i].v,pairs[i],4);
    model.edges=edges;model.numedges=10;model.vertexes=vertices;model.numvertexes=6;model.surfedges=sequences;model.numsurfedges=11;
    model.surfaces=faces;model.numsurfaces=3;entity.model=&model;currententity=&entity;r_pcurrentvertbase=vertices;
    plane.normal[2]=1;plane.dist=32;texinfo.texture=&texture;
    for(i=0;i<3;i++){faces[i].plane=&plane;faces[i].texinfo=&texinfo;faces[i].firstedge=i*4;faces[i].numedges=i==2?3:4;}
#ifdef AW_EDGE_CACHE_SPLIT
    {static dmodel_t sub;memset(&sub,0,sizeof(sub));sub.numfaces=3;model.submodels=&sub;model.numsubmodels=1;used=0;AW_InitEdgeCache(&model);assert(model.edgecache_count==10);}
#endif
}
static void prefix(void){
#ifdef AW_EDGE_CACHE_SPLIT
    static mnode_t node;static msurface_t *mark;
    dmodel_t *sub;geometry();sub=model.submodels;sub->numfaces=1;model.numnodes=0;model.nummarksurfaces=0;used=0;
    AW_InitEdgeCache(&model);assert(model.edgecache_count==5);
    node.firstsurface=2;node.numsurfaces=1;model.nodes=&node;model.numnodes=1;used=0;AW_InitEdgeCache(&model);assert(model.edgecache_count==10);
    model.numnodes=0;mark=&faces[1];model.marksurfaces=&mark;model.nummarksurfaces=1;used=0;AW_InitEdgeCache(&model);assert(model.edgecache_count==8);
    expecting=1;faces[0].firstedge=12;
    if(!setjmp(failure)){AW_InitEdgeCache(&model);assert(0);}faces[0].firstedge=0;
    sequences[0]=INT_MIN;if(!setjmp(failure)){AW_InitEdgeCache(&model);assert(0);}sequences[0]=1;expecting=0;
    /* Many references to one face must still service loading audio at bounded
     * intervals. Entry/exit calls plus 500*(mark+face+4 edges)/256 services. */
    {static msurface_t *marks[500];int i;
        for(i=0;i<500;i++)marks[i]=faces;
        model.marksurfaces=marks;model.nummarksurfaces=500;used=0;
        service_calls=0;aw_load_audio_tick=service;AW_InitEdgeCache(&model);
        assert(service_calls==2+(5+500*6)/256);aw_load_audio_tick=NULL;
    }
#endif
}
int main(void){
    int pass,flags,i;prefix();geometry();xscale=yscale=80;xscaleinv=yscaleinv=1.0f/80;xcenter=160;ycenter=100;
    r_refdef.fvrectright_adj=319;r_refdef.fvrectbottom_adj=199;
    r_refdef.vrectright_adj_shift20=319<<20;r_refdef.vrect_x_adj_shift20=0;
    for(pass=0;pass<4;pass++)for(flags=0;flags<16;flags++){
        r_framecount++;r_currentkey=1;memset(emitted,0,sizeof(emitted));memset(drawn,0,sizeof(drawn));
        memset(newedges,0,sizeof(newedges));memset(removeedges,0,sizeof(removeedges));
        r_edges=edge_p=emitted;edge_max=emitted+128;surfaces=drawn;surface_p=drawn+1;surf_max=drawn+32;
        memset(view_clipplanes,0,sizeof(view_clipplanes));
        view_clipplanes[0].normal[0]=1;view_clipplanes[1].normal[0]=-1;view_clipplanes[2].normal[1]=1;view_clipplanes[3].normal[1]=-1;
        for(i=0;i<4;i++)view_clipplanes[i].dist=pass==0?-12:pass==1?-4:pass==2?100:-7.99f;
        view_clipplanes[0].leftedge=1;view_clipplanes[1].rightedge=1;
        insubmodel=false;R_RenderFace(&faces[0],flags);output();R_RenderFace(&faces[1],flags);output();R_RenderFace(&faces[2],flags);output();
        /* Inline drawing bypasses the cache, including shared world indices. */
        insubmodel=true;R_RenderFace(&faces[0],flags);R_RenderFace(&faces[1],flags);output();
    }
    assert(hash==0x86ab1bc5e1d4e625ULL);
    printf("%016llx edge projection/clipping/cache stream\n",hash);return 0;
}
