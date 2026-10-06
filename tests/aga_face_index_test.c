/* SPDX-License-Identifier: GPL-2.0-or-later
 * Load the real face lump across the signed-short boundary. */
#include "quakedef.h"
#include <assert.h>
#include <setjmp.h>
extern model_t *loadmodel;
extern byte *mod_base;
void Mod_LoadFaces(lump_t *);
static jmp_buf error;
static int expect_error;
static short same_short(short x){return x;}
static int same_long(int x){return x;}
short (*LittleShort)(short)=same_short;
int (*LittleLong)(int)=same_long;
void *Hunk_AllocName(int n,char *s){return calloc(1,n);}
void Sys_Error(char *fmt,...){assert(expect_error);longjmp(error,1);}
int Q_strncmp(char *a,char *b,int n){return strncmp(a,b,n);}
int main(void){
 model_t m;dface_t face;lump_t lump;int n,ids[]={32767,32768,34642,65535};
 mvertex_t vertices[3];medge_t edges[3];int surfedges[3]={0,1,2};mtexinfo_t tex;texture_t texture;
 memset(&m,0,sizeof(m));memset(&face,0,sizeof(face));memset(vertices,0,sizeof(vertices));memset(&tex,0,sizeof(tex));memset(&texture,0,sizeof(texture));
 vertices[1].position[0]=16;vertices[2].position[1]=16;
 for(n=0;n<3;n++){edges[n].v[0]=n;edges[n].v[1]=(n+1)%3;}
 tex.vecs[0][0]=tex.vecs[1][1]=1;tex.texture=&texture;strcpy(texture.name,"fixture");
 m.vertexes=vertices;m.edges=edges;m.surfedges=surfedges;m.texinfo=&tex;
 m.numvertexes=3;m.numedges=3;m.numsurfedges=3;m.numtexinfo=1;
 m.numplanes=65536;m.planes=calloc(m.numplanes,sizeof(mplane_t));assert(m.planes);
 loadmodel=&m;mod_base=(byte *)&face;lump.fileofs=0;lump.filelen=sizeof(face);
 face.numedges=3;face.lightofs=-1;
 for(n=0;n<4;n++){
  face.planenum=(short)ids[n];Mod_LoadFaces(&lump);
  assert(m.surfaces[0].plane==&m.planes[ids[n]]);free(m.surfaces);
 }
 m.numplanes=34642;face.planenum=(short)34642;expect_error=1;
 if(!setjmp(error)){Mod_LoadFaces(&lump);assert(0);}
 free(m.surfaces);free(m.planes);return 0;
}
