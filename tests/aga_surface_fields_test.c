/* SPDX-License-Identifier: GPL-2.0-or-later
 * Actual face decoder: disk count limits, field promotion and exact flags. */
#include <assert.h>
#include <setjmp.h>
#include "model.c"
static byte arena[4096];static int used,expect_failure;
static jmp_buf failure;
static int little_long(int n){return n;}
static short little_short(short n){return n;}
static float little_float(float n){return n;}
int (*LittleLong)(int)=little_long;
short (*LittleShort)(short)=little_short;
float (*LittleFloat)(float)=little_float;
void Sys_Error(char *format,...){if(expect_failure)longjmp(failure,1);fprintf(stderr,"%s\n",format);abort();}
void *Hunk_AllocName(int size,char *name){void *p=arena+used;size=(size+15)&~15;assert(used+size<(int)sizeof(arena));used+=size;memset(p,0,size);return p;}
int Q_strncmp(char *a,char *b,int n){return strncmp(a,b,n);}
static model_t model;static dface_t disk;static lump_t lump;
static mplane_t plane;static mtexinfo_t texinfo;static texture_t texture;
static medge_t edges[4];static mvertex_t vertices[3];static int surfedges[32767];
static void setup(int count,const char *name,int side){
    int i;memset(&model,0,sizeof(model));memset(&disk,0,sizeof(disk));
    for(i=0;i<32767;i++)surfedges[i]=1+i%3;
    edges[1].v[0]=0;edges[2].v[0]=1;edges[3].v[0]=2;
    vertices[1].position[0]=16;vertices[2].position[1]=16;
    memset(&texture,0,sizeof(texture));strncpy(texture.name,name,15);texinfo.texture=&texture;
    texinfo.vecs[0][0]=texinfo.vecs[1][1]=1;
    model.planes=&plane;model.numplanes=1;model.texinfo=&texinfo;model.numtexinfo=1;
    model.vertexes=vertices;model.numvertexes=3;model.edges=edges;model.numedges=4;
    model.surfedges=surfedges;model.numsurfedges=32767;
    disk.numedges=count;disk.side=side;disk.lightofs=-1;memset(disk.styles,255,sizeof(disk.styles));
    lump.fileofs=0;lump.filelen=sizeof(disk);loadmodel=&model;mod_base=(byte *)&disk;used=0;
}
int main(void){
    int i,side;const char *names[]={"wall","sky_cloud","*water"};
    int flags[]={0,SURF_DRAWSKY|SURF_DRAWTILED,SURF_DRAWTURB|SURF_DRAWTILED};
    for(i=0;i<3;i++)for(side=0;side<2;side++){
        setup(3,names[i],side);Mod_LoadFaces(&lump);
        assert(model.surfaces[0].numedges==3);
        assert(model.surfaces[0].flags==(flags[i]|(side?SURF_PLANEBACK:0)));
    }
    setup(32767,"wall",0);Mod_LoadFaces(&lump);assert(model.surfaces[0].numedges==32767);
#ifdef AW_SURFACE_FIELDS_16
    assert(sizeof(model.surfaces[0].numedges)==2 && sizeof(model.surfaces[0].flags)==2);
    model.surfaces[0].flags=65535;assert((int)model.surfaces[0].flags==65535);
    expect_failure=1;
    setup(-1,"wall",0);if(!setjmp(failure)){Mod_LoadFaces(&lump);assert(0);}
    setup(-32768,"wall",0);if(!setjmp(failure)){Mod_LoadFaces(&lump);assert(0);}
    setup(3,"wall",0);disk.firstedge=-1;if(!setjmp(failure)){Mod_LoadFaces(&lump);assert(0);}
    setup(3,"wall",0);disk.firstedge=32766;if(!setjmp(failure)){Mod_LoadFaces(&lump);assert(0);}
    expect_failure=0;
#endif
    puts("surface disk counts and generated flags exact");return 0;
}
