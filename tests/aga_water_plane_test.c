/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_water.c with world.c (MWSCRIPT-WATER-LEVEL-STATIC-67): a CHIM room's world as tools/chim/interior.py liquid_world
 * writes it (the root node a level plane, the open air in front, a CONTENTS_WATER leaf behind, the two "*water" faces
 * on it), the plane found, moved up and down, clamped into the room's box, its four corners and hull 0 following (the
 * point contents above and below), the CHIM room's relink hook told, and the cases that keep the water as built: lava
 * beside the water, no water face, another map, aw_water_movable 0. */
#include "quakedef.h"
#include <assert.h>
#include <ctype.h>
#include <stdarg.h>
#include "aw_reset.h"
#include "aw_water.h"

server_t sv;
/* the CHIM room loader's hook, defined there (chim/chim_room.c); here the test's own relink counter is set into it */
void (*aw_water_relink)(float old_z,float new_z);
void Sys_Error(char *fmt,...){va_list ap;va_start(ap,fmt);vfprintf(stderr,fmt,ap);va_end(ap);exit(1);}
void Con_DPrintf(char *fmt,...){(void)fmt;}
void Con_Printf(char *fmt,...){va_list ap;va_start(ap,fmt);vprintf(fmt,ap);va_end(ap);}
static cvar_t *water_cvar;
void Cvar_RegisterVariable(cvar_t *v){water_cvar=v;v->value=(float)atof(v->string);}
int Q_strcasecmp(char *a,char *b){while(*a && *b && tolower((unsigned char)*a)==tolower((unsigned char)*b)){a++;b++;}
                                  return tolower((unsigned char)*a)-tolower((unsigned char)*b);}
static aw_reset_fn reset_fn;
int AW_ResetRegister(const char *name,aw_reset_fn reset,aw_reset_digest_fn digest){(void)name;(void)digest;reset_fn=reset;return 1;}

static model_t model;
static mplane_t planes[1];
static mnode_t nodes[1];
static mleaf_t leafs[3];
static mvertex_t vertexes[4];
static medge_t edges[5];
static int surfedges[8];
static msurface_t surfaces[2];
static mtexinfo_t texinfo;
static texture_t texture;
static dclipnode_t clipnodes[1];
static int relinks;static float relink_old,relink_new;
static void relink(float old_z,float new_z){relinks++;relink_old=old_z;relink_new=new_z;}

static void room(float level)
{
    int i;float corner[4][2]={{-90,-90},{90,-90},{90,90},{-90,90}};
    memset(&model,0,sizeof(model));
    planes[0].normal[0]=planes[0].normal[1]=0;planes[0].normal[2]=1;planes[0].dist=level;planes[0].type=PLANE_Z;
    leafs[0].contents=CONTENTS_SOLID;leafs[1].contents=CONTENTS_EMPTY;leafs[2].contents=CONTENTS_WATER;
    leafs[1].minmaxs[2]=(short)level;leafs[1].minmaxs[5]=200;leafs[2].minmaxs[2]=-50;leafs[2].minmaxs[5]=(short)level;
    memset(nodes,0,sizeof(nodes));
    nodes[0].plane=&planes[0];nodes[0].children[0]=(mnode_t *)&leafs[1];nodes[0].children[1]=(mnode_t *)&leafs[2];
    nodes[0].firstsurface=0;nodes[0].numsurfaces=2;
    for(i=0;i<4;i++){vertexes[i].position[0]=corner[i][0];vertexes[i].position[1]=corner[i][1];vertexes[i].position[2]=level;}
    for(i=1;i<5;i++){edges[i].v[0]=(unsigned short)(i-1);edges[i].v[1]=(unsigned short)(i%4);}
    for(i=0;i<4;i++){surfedges[i]=i+1;surfedges[4+i]=-(4-i);}
    strcpy(texture.name,"*water");texinfo.texture=&texture;
    memset(surfaces,0,sizeof(surfaces));
    for(i=0;i<2;i++){surfaces[i].plane=&planes[0];surfaces[i].texinfo=&texinfo;surfaces[i].flags=SURF_DRAWTURB|
                     (i?SURF_PLANEBACK:0);surfaces[i].firstedge=4*i;surfaces[i].numedges=4;}
    clipnodes[0].planenum=0;clipnodes[0].children[0]=CONTENTS_EMPTY;clipnodes[0].children[1]=CONTENTS_WATER;
    model.type=mod_brush;model.numnodes=1;model.nodes=nodes;model.numleafs=3;model.leafs=leafs;
    model.numvertexes=4;model.vertexes=vertexes;model.numedges=5;model.edges=edges;model.numsurfedges=8;
    model.surfedges=surfedges;model.numsurfaces=2;model.surfaces=surfaces;model.numplanes=1;model.planes=planes;
    model.mins[0]=model.mins[1]=-100;model.mins[2]=-50;model.maxs[0]=model.maxs[1]=100;model.maxs[2]=200;
    model.hulls[0].clipnodes=clipnodes;model.hulls[0].planes=planes;model.hulls[0].firstclipnode=0;
    model.hulls[0].lastclipnode=0;
    sv.worldmodel=&model;
}
static int contents_at(float z){vec3_t p;p[0]=10;p[1]=10;p[2]=z;return SV_PointContents(p);}

int main(void)
{
    int i;
    AW_WaterInit();
    assert(water_cvar && water_cvar->value==1);
    aw_water_relink=relink;
    /* the Forgotten Sewer's form: the record's level 0 in the map */
    room(0);
    assert(AW_WaterPlaneFind() && AW_WaterPlaneMovable() && AW_WaterPlaneZ()==0);
    assert(contents_at(-10)==CONTENTS_WATER && contents_at(10)==CONTENTS_EMPTY);
    /* up to 100 (the crank's 400 original units at a quarter scale): hull 0, the corners, the leaves' boxes */
    assert(AW_WaterPlaneSet(100) && planes[0].dist==100 && AW_WaterPlaneZ()==100);
    for(i=0;i<4;i++)assert(vertexes[i].position[2]==100);
    assert(contents_at(50)==CONTENTS_WATER && contents_at(150)==CONTENTS_EMPTY);
    assert(leafs[1].minmaxs[2]==-50 && leafs[1].minmaxs[5]==200 && leafs[2].minmaxs[2]==-50 && leafs[2].minmaxs[5]==200);
    assert(relinks==1 && relink_old==0 && relink_new==100);
    /* the same level again: nothing moves, nobody is told */
    assert(AW_WaterPlaneSet(100) && relinks==1);
    /* down past the floor: the box's floor plus one; over the top: the top less one */
    assert(AW_WaterPlaneSet(-375) && AW_WaterPlaneZ()==-49 && contents_at(-40)==CONTENTS_EMPTY);
    assert(AW_WaterPlaneSet(1000) && AW_WaterPlaneZ()==199 && contents_at(190)==CONTENTS_WATER);
    for(i=0;i<4;i++)assert(vertexes[i].position[2]==199);
    /* aw_water_movable 0: the water stays as it is */
    water_cvar->value=0;
    assert(!AW_WaterPlaneMovable() && !AW_WaterPlaneSet(10) && AW_WaterPlaneZ()==199);
    water_cvar->value=1;
    /* another map (a map change): the plane found for the old one is not touched */
    {model_t other;memset(&other,0,sizeof(other));sv.worldmodel=&other;
     assert(!AW_WaterPlaneMovable() && !AW_WaterPlaneSet(10) && planes[0].dist==199);
     sv.worldmodel=&model;}
    /* a map loaded again into the same model slot (a server spawn before the new attach): its memory is new */
    {mvertex_t again[4];mvertex_t *was=model.vertexes;memcpy(again,vertexes,sizeof(again));model.vertexes=again;
     assert(!AW_WaterPlaneMovable() && !AW_WaterPlaneSet(10) && again[0].position[2]==199);
     model.vertexes=was;assert(AW_WaterPlaneMovable());}
    /* lava carved beside the water (the 4 rooms with both): kept as built */
    room(0);leafs[2].contents=CONTENTS_LAVA;
    assert(!AW_WaterPlaneFind() && !AW_WaterPlaneSet(50) && planes[0].dist==0);
    /* no water face on the root (a room map whose water node is something else) */
    room(0);strcpy(texture.name,"*lava");
    assert(!AW_WaterPlaneFind());
    /* a tilted root plane is no water level */
    room(0);planes[0].normal[2]=0.7f;planes[0].normal[0]=0.7f;
    assert(!AW_WaterPlaneFind());
    /* a map with no nodes */
    {model_t empty;memset(&empty,0,sizeof(empty));empty.type=mod_brush;sv.worldmodel=&empty;assert(!AW_WaterPlaneFind());}
    room(0);assert(AW_WaterPlaneFind());
    AW_WaterPlaneStatus();
    assert(reset_fn);reset_fn(1);
    return 0;
}
