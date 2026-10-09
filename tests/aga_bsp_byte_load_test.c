/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <assert.h>
#include <setjmp.h>
#include "../engine/aga/src/model.c"
/* Diagnostic logs (aw_log.c); without a bound switch they are written live. */
#include "../engine/aga/src/aw_log.c"
qboolean aw_loading_music=false;
static byte heap[3*1024*1024];
static int used,temporary_calls,failed;
static jmp_buf failure;
/* Streaming dispatch also references the in-place clipnode decoder. */
static short same_short(short value){return value;}
static int same_long(int value){return value;}
short (*LittleShort)(short)=same_short;
int (*LittleLong)(int)=same_long;
/* The section dispatcher names the texture decoder. */
int Q_strncmp(char *a,char *b,int n){return strncmp(a,b,n);}
void R_InitSky(texture_t *tx){assert(0);}
void *Hunk_AllocName(int size,char *name) {
    void *p;int bytes=(size+31)&~15;
    assert(used+bytes<sizeof(heap));p=heap+used;used+=bytes;return p;
}
void *Hunk_TempAlloc(int size){temporary_calls++;assert(0);return NULL;}
int Hunk_HighMark(void){return 0;}
void Hunk_FreeToHighMark(int mark){assert(0);}
void Sys_Error(char *fmt,...){failed=1;longjmp(failure,1);}
static size_t prefix(const char *name,long offset,byte *target,size_t size){
    assert(offset==7);memset(target,0x5a,17);return 17;
}
int main(void) {
    model_t model;lump_t l;int i;byte *p;
    memset(&model,0,sizeof(model));strcpy(model.name,"sn012");loadmodel=&model;
    l.fileofs=7;l.filelen=2767103;aw_bsp_bytes=l.fileofs+l.filelen;
    aw_bsp_file=tmpfile();assert(aw_bsp_file);
    for(i=0;i<aw_bsp_bytes;i++)fputc(0x5a,aw_bsp_file);fflush(aw_bsp_file);
    aw_bsp_base=0;aw_load_prefetch_copy=prefix;
    AW_LoadBrushSection(&l,Mod_LoadVisibility);p=model.visdata;
    assert(p && used<3*1024*1024 && temporary_calls==0);
    for(i=0;i<l.filelen;i++)assert(p[i]==0x5a);
    /* Simulate a BSP member beginning at a nonzero pack-file offset. */
    used=0;aw_bsp_base=19;l.filelen=40;aw_bsp_bytes=100;
    aw_load_prefetch_copy=NULL;
    fseek(aw_bsp_file,aw_bsp_base+l.fileofs,SEEK_SET);
    for(i=0;i<40;i++)fputc(0x3c,aw_bsp_file);fflush(aw_bsp_file);
    AW_LoadBrushSection(&l,Mod_LoadVisibility);
    for(i=0;i<40;i++)assert(model.visdata[i]==0x3c);
    aw_bsp_base=0;aw_load_prefetch_copy=prefix;
    used=0;l.filelen=40;AW_LoadBrushSection(&l,Mod_LoadLighting);
    assert(model.lightdata);for(i=0;i<17;i++)assert(model.lightdata[i]==0x5a);
    used=0;AW_LoadBrushSection(&l,Mod_LoadEntities);assert(model.entities);
    l.filelen=0;AW_LoadBrushSection(&l,Mod_LoadVisibility);assert(!model.visdata);
    l.fileofs=-1;
    if(!setjmp(failure)){AW_LoadBrushSection(&l,Mod_LoadVisibility);assert(0);}
    assert(failed);
    failed=0;used=0;l.fileofs=7;l.filelen=40;aw_bsp_bytes=100;
    fclose(aw_bsp_file);aw_bsp_file=tmpfile();assert(aw_bsp_file);
    aw_load_prefetch_copy=NULL;
    if(!setjmp(failure)){AW_LoadBrushSection(&l,Mod_LoadVisibility);assert(0);}
    assert(failed && temporary_calls==0);
    fclose(aw_bsp_file);return 0;
}
