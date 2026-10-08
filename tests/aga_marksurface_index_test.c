/* SPDX-License-Identifier: GPL-2.0-or-later
 * Load real marksurface and leaf lumps across the signed-short boundary. */
#include "quakedef.h"
#include <assert.h>
#include <setjmp.h>
extern model_t *loadmodel;
extern byte *mod_base;
void Mod_LoadMarksurfaces(lump_t *);
void Mod_LoadLeafs(lump_t *);
static jmp_buf error;
static int expect_error;
static short same_short(short x){return x;}
static int same_long(int x){return x;}
short (*LittleShort)(short)=same_short;
int (*LittleLong)(int)=same_long;
qboolean aw_loading_music=false; /* referenced by the streamed BSP reader */
void *Hunk_AllocName(int n,char *s){return calloc(1,n);}
void Sys_Error(char *fmt,...){assert(expect_error);longjmp(error,1);}
int main(void){
 model_t m;lump_t lump;int n,ids[]={0,32767,32768,40000,65535};
 unsigned short marks[5];dleaf_t leaf;
 memset(&m,0,sizeof(m));memset(&leaf,0,sizeof(leaf));
 m.numsurfaces=65536;m.surfaces=calloc(m.numsurfaces,sizeof(msurface_t));assert(m.surfaces);
 loadmodel=&m;
 for(n=0;n<5;n++)marks[n]=(unsigned short)ids[n];
 mod_base=(byte *)marks;lump.fileofs=0;lump.filelen=sizeof(marks);
 Mod_LoadMarksurfaces(&lump);
 assert(m.nummarksurfaces==5);
 for(n=0;n<5;n++)assert(m.marksurfaces[n]==&m.surfaces[ids[n]]);
 free(m.marksurfaces);
 /* A face index one past the face lump stops the load before the mark
  * pointer is formed, at each boundary. */
 {int count[]={32767,32768,40000,65535},bad[]={1,2,3,4};
  for(n=0;n<4;n++){
   m.numsurfaces=count[n];expect_error=1;m.marksurfaces=NULL;
   if(!setjmp(error)){Mod_LoadMarksurfaces(&lump);assert(0);}
   assert(m.marksurfaces[bad[n]]==NULL);free(m.marksurfaces);
  }}
 expect_error=0;
 /* Leaf mark ranges are unsigned and must lie inside the mark list. */
 m.nummarksurfaces=40000;m.marksurfaces=calloc(m.nummarksurfaces,sizeof(msurface_t *));
 assert(m.marksurfaces);
 leaf.contents=-1;leaf.visofs=-1;leaf.firstmarksurface=32768;leaf.nummarksurfaces=7232;
 mod_base=(byte *)&leaf;lump.filelen=sizeof(leaf);
 Mod_LoadLeafs(&lump);
 assert(m.numleafs==1);
 assert(m.leafs[0].firstmarksurface==m.marksurfaces+32768);
 assert(m.leafs[0].nummarksurfaces==7232);
 free(m.leafs);
 /* Unsigned first marks at the boundaries; the last valid mark is 39999. */
 {int first[]={32767,32768,39999},count[]={7233,7232,1};
  for(n=0;n<3;n++){
   leaf.firstmarksurface=(unsigned short)first[n];leaf.nummarksurfaces=(unsigned short)count[n];
   Mod_LoadLeafs(&lump);
   assert(m.leafs[0].firstmarksurface==m.marksurfaces+first[n]);
   assert(m.leafs[0].nummarksurfaces==count[n]);free(m.leafs);
  }}
 /* Ranges past the mark list stop the load before the leaf pointer is set. */
 {int first[]={32767,32768,39999,40000,65535},count[]={7234,7233,2,1,1};
  for(n=0;n<5;n++){
   leaf.firstmarksurface=(unsigned short)first[n];leaf.nummarksurfaces=(unsigned short)count[n];
   expect_error=1;m.leafs=NULL;
   if(!setjmp(error)){Mod_LoadLeafs(&lump);assert(0);}
   assert(m.leafs[0].firstmarksurface==NULL);free(m.leafs);
  }}
 free(m.marksurfaces);free(m.surfaces);return 0;
}
