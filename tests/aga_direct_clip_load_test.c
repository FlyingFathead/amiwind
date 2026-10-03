/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <assert.h>
#include <setjmp.h>
#include "../engine/aga/src/model.c"
static byte heap[2*1024*1024];
static int used, allocations, temporary_calls, expect_error;
static jmp_buf failure;
static short same_short(short value){return value;}
static int same_long(int value){return value;}
static short swap_short(short value){unsigned short v=(unsigned short)value;return (v>>8)|(v<<8);}
static int swap_long(int value){unsigned int v=(unsigned int)value;return (v>>24)|((v>>8)&0xff00)|((v<<8)&0xff0000)|(v<<24);}
short (*LittleShort)(short)=same_short;
int (*LittleLong)(int)=same_long;
void *Hunk_AllocName(int size,char *name){
    void *p;int bytes=(size+31)&~15;
    assert(size>=0 && used+bytes<(int)sizeof(heap));p=heap+used;used+=bytes;allocations++;return p;
}
void *Hunk_TempAlloc(int size){temporary_calls++;assert(0);return NULL;}
int Hunk_HighMark(void){assert(0);return 0;}
void Hunk_FreeToHighMark(int mark){assert(0);}
void Sys_Error(char *fmt,...){assert(expect_error);longjmp(failure,1);}
static byte *prefetch_data;
static size_t prefix(const char *name,long offset,byte *target,size_t size){
    memcpy(target,prefetch_data,7);return 7;
}
static size_t bad_prefix(const char *name,long offset,byte *target,size_t size){return size+1;}
static model_t model;
static dmodel_t models[2];
static mplane_t planes[2];
static void setup(dclipnode_t *data,int count){
    int i;memset(&model,0,sizeof(model));memset(models,0,sizeof(models));
    model.numplanes=2;model.planes=planes;model.submodels=models;model.numsubmodels=2;
    for(i=1;i<MAX_MAP_HULLS;i++){models[0].headnode[i]=0;models[1].headnode[i]=count?count-1:-1;}
    if(!count)for(i=1;i<MAX_MAP_HULLS;i++)models[0].headnode[i]=-1;
    loadmodel=&model;used=allocations=temporary_calls=expect_error=0;
    aw_bsp_file=tmpfile();assert(aw_bsp_file);aw_bsp_base=37;aw_bsp_bytes=13+count*8;
    for(i=0;i<aw_bsp_base+13;i++)fputc(0x73,aw_bsp_file);
    assert(fwrite(data,8,count,aw_bsp_file)==(size_t)count);fflush(aw_bsp_file);
    aw_load_prefetch_copy=NULL;prefetch_data=(byte *)data;
}
static void synthetic(void){
    dclipnode_t data[3]={{0,{1,-2}},{1,{2,-1}},{0,{-3,-1}}},swapped;
    dclipnode_t *large;int i;FILE *f;lump_t lump={13,24};
    setup(data,3);aw_load_prefetch_copy=prefix;
    AW_LoadBrushSection(&lump,Mod_LoadClipnodes);
    assert(allocations==1 && !temporary_calls && !memcmp(data,model.clipnodes,24));
    assert(model.numclipnodes==3 && model.hulls[1].clipnodes==model.clipnodes && model.hulls[2].lastclipnode==2);
    assert(model.hulls[1].clip_mins[0]==-7.32f && model.hulls[2].clip_maxs[2]==64);
    fclose(aw_bsp_file);
    /* Endian-fix in place: every input member must be consumed only once. */
    swapped.planenum=0x01000000;swapped.children[0]=(short)0xfeff;swapped.children[1]=(short)0xfdff;
    setup(data,1);LittleLong=swap_long;LittleShort=swap_short;
    AW_DecodeClipnodes(&swapped,&swapped,1);
    assert(swapped.planenum==1 && swapped.children[0]==-2 && swapped.children[1]==-3);
    LittleLong=same_long;LittleShort=same_short;fclose(aw_bsp_file);
    /* Extended positive indices above signed-short range survive unchanged. */
    large=calloc(40001,sizeof(*large));assert(large);
    for(i=0;i<40001;i++){large[i].children[0]=-1;large[i].children[1]=-2;}
    large[0].children[0]=(short)40000;setup(large,40001);lump.filelen=40001*8;
    AW_LoadBrushSection(&lump,Mod_LoadClipnodes);
    assert((unsigned short)model.clipnodes[0].children[0]==40000 && allocations==1 && !temporary_calls);
    fclose(aw_bsp_file);free(large);
    setup(data,3);lump.filelen=23;expect_error=1;
    if(!setjmp(failure)){AW_LoadBrushSection(&lump,Mod_LoadClipnodes);assert(0);}assert(!allocations);
    fclose(aw_bsp_file);
    setup(data,3);lump.filelen=24;aw_load_prefetch_copy=bad_prefix;expect_error=1;
    if(!setjmp(failure)){AW_LoadBrushSection(&lump,Mod_LoadClipnodes);assert(0);}assert(!temporary_calls);
    fclose(aw_bsp_file);
    setup(data,3);fclose(aw_bsp_file);aw_bsp_file=tmpfile();expect_error=1;
    if(!setjmp(failure)){AW_LoadBrushSection(&lump,Mod_LoadClipnodes);assert(0);}assert(!temporary_calls);
    fclose(aw_bsp_file);
    data[0].children[0]=3;setup(data,3);expect_error=1;
    if(!setjmp(failure)){AW_LoadBrushSection(&lump,Mod_LoadClipnodes);assert(0);}fclose(aw_bsp_file);
    data[0].children[0]=-16;setup(data,3);expect_error=1;
    if(!setjmp(failure)){AW_LoadBrushSection(&lump,Mod_LoadClipnodes);assert(0);}fclose(aw_bsp_file);
    data[0].children[0]=1;data[0].planenum=2;setup(data,3);expect_error=1;
    if(!setjmp(failure)){AW_LoadBrushSection(&lump,Mod_LoadClipnodes);assert(0);}fclose(aw_bsp_file);
    data[0].planenum=0;setup(data,3);models[1].headnode[1]=3;expect_error=1;
    if(!setjmp(failure)){AW_LoadBrushSection(&lump,Mod_LoadClipnodes);assert(0);}fclose(aw_bsp_file);
    setup(data,0);lump.filelen=0;AW_LoadBrushSection(&lump,Mod_LoadClipnodes);
    assert(model.numclipnodes==0 && allocations==1 && !temporary_calls);fclose(aw_bsp_file);
}

static void actual(const char *path){
    FILE *file;long length;byte *raw;dheader_t *header;dclipnode_t *expected;int count;
    file=fopen(path,"rb");assert(file);assert(!fseek(file,0,SEEK_END));length=ftell(file);
    raw=malloc(length);assert(raw);rewind(file);assert(fread(raw,1,length,file)==(size_t)length);
    header=(dheader_t *)raw;assert(header->version==29);memset(&model,0,sizeof(model));
    model.numplanes=header->lumps[LUMP_PLANES].filelen/sizeof(dplane_t);
    model.planes=calloc(model.numplanes,sizeof(mplane_t));assert(model.planes);
    model.numsubmodels=header->lumps[LUMP_MODELS].filelen/sizeof(dmodel_t);
    model.submodels=(dmodel_t *)(raw+header->lumps[LUMP_MODELS].fileofs);
    loadmodel=&model;mod_base=raw;used=allocations=temporary_calls=expect_error=0;aw_load_prefetch_copy=NULL;
    aw_bsp_file=NULL;Mod_LoadClipnodes(&header->lumps[LUMP_CLIPNODES]);count=model.numclipnodes;
    expected=malloc(count*8);assert(expected);memcpy(expected,model.clipnodes,count*8);
    used=allocations=0;aw_bsp_file=file;aw_bsp_base=0;aw_bsp_bytes=length;
    AW_LoadBrushSection(&header->lumps[LUMP_CLIPNODES],Mod_LoadClipnodes);
    assert(count==model.numclipnodes && !memcmp(expected,model.clipnodes,count*8));
    assert(allocations==1 && !temporary_calls);
    printf("%s: clipnodes=%d bytes_identical=yes raw_temporary=0\n",path,count);
    free(model.planes);free(expected);free(raw);fclose(file);aw_bsp_file=NULL;
}
int main(int argc,char **argv){int i;if(argc==1)synthetic();else for(i=1;i<argc;i++)actual(argv[i]);return 0;}
