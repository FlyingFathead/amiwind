/* SPDX-License-Identifier: GPL-2.0-or-later
 * Load the real face lump with texinfo indices across the signed-short
 * boundary, and pin the double-precision extents rule. */
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
qboolean aw_loading_music=false; /* referenced by the streamed BSP reader */
void *Hunk_AllocName(int n,char *s){return calloc(1,n);}
void Sys_Error(char *fmt,...){assert(expect_error);longjmp(error,1);}
int Q_strncmp(char *a,char *b,int n){return strncmp(a,b,n);}
int main(void){
 model_t m;dface_t face;lump_t lump;int n,ids[]={0,32767,32768,40000,65535};
 mvertex_t vertices[3];medge_t edges[3];int surfedges[3]={0,1,2};mtexinfo_t *tex;texture_t texture;
 volatile float third=1.0f/3.0f,corner=720.0f;
 memset(&m,0,sizeof(m));memset(&face,0,sizeof(face));memset(vertices,0,sizeof(vertices));memset(&texture,0,sizeof(texture));
 for(n=0;n<3;n++){edges[n].v[0]=n;edges[n].v[1]=(n+1)%3;}
 strcpy(texture.name,"fixture");
 m.numtexinfo=65536;tex=calloc(m.numtexinfo,sizeof(*tex));assert(tex);
 for(n=0;n<m.numtexinfo;n++){tex[n].vecs[0][0]=tex[n].vecs[1][1]=1;tex[n].texture=&texture;}
 m.vertexes=vertices;m.edges=edges;m.surfedges=surfedges;m.texinfo=tex;
 m.numvertexes=3;m.numedges=3;m.numsurfedges=3;
 m.numplanes=1;m.planes=calloc(1,sizeof(mplane_t));assert(m.planes);
 loadmodel=&m;mod_base=(byte *)&face;lump.fileofs=0;lump.filelen=sizeof(face);
 face.numedges=3;face.lightofs=-1;
 vertices[1].position[0]=16;vertices[2].position[1]=16;
 for(n=0;n<5;n++){
  face.texinfo=(short)ids[n];Mod_LoadFaces(&lump);
  assert(m.surfaces[0].texinfo==&tex[ids[n]]);free(m.surfaces);
 }
 /* An index one past the lump stops the load before any pointer is
  * formed, at each boundary (no surface is allocated or written). */
 {int count[]={32767,32768,40000,65535};
  for(n=0;n<4;n++){
   m.numtexinfo=count[n];face.texinfo=(short)count[n];expect_error=1;m.surfaces=NULL;
   if(!setjmp(error)){Mod_LoadFaces(&lump);assert(0);}
   assert(m.surfaces[0].texinfo==NULL);free(m.surfaces);
  }}
 expect_error=0;m.numtexinfo=65536;
 /* 720 * float(1/3) is 240.0000072 exactly but 240.0 in single precision:
  * the engine rule (double after every operation, as ericw light and
  * tools/surface_grid.py) gives 256 on every FPU, never 240. */
 assert((double)corner*(double)third>240.0);
 tex[7].vecs[0][0]=third;tex[7].vecs[1][1]=1;
 vertices[1].position[0]=corner;
 face.texinfo=7;Mod_LoadFaces(&lump);
 assert(m.surfaces[0].texturemins[0]==0);
 assert(m.surfaces[0].extents[0]==256);
 assert(m.surfaces[0].extents[1]==16);
 free(m.surfaces);free(m.planes);free(tex);return 0;
}
