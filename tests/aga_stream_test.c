/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
quakeparms_t host_parms;
size_t (*aw_load_prefetch_copy)(const char *,long,byte *,size_t);
double (*aw_load_clock)(void);
long aw_load_disk_bytes,aw_load_disk_calls;
double aw_load_disk_seconds,aw_load_decode_seconds;
static cvar_t *choice,*buffer,*ahead;static cache_user_t *allocated;static int opened,freed,low;
void Cvar_RegisterVariable(cvar_t *c){
    if(!strcmp(c->name,"aw_cell_change_method"))choice=c;
    else if(!strcmp(c->name,"aw_cell_prefetch_kib"))buffer=c;
    else ahead=c;
    c->value=atof(c->string);
}
void Cvar_SetValue(char *s,float value){
    cvar_t *c=!strcmp(s,choice->name)?choice:!strcmp(s,buffer->name)?buffer:ahead;c->value=value;
}
void Con_Printf(char *s,...){}
double Sys_FloatTime(void){static double t;return t+=.001;}
int Hunk_LowMark(void){return low;}
int Hunk_HighMark(void){return 0;}
void *Cache_Alloc(cache_user_t *c,int size,char *name){assert(size==(int)buffer->value*1024);allocated=c;return c->data=malloc(size);}
void *Cache_Check(cache_user_t *c){return c->data;}
void Cache_Free(cache_user_t *c){assert(c->data);free(c->data);c->data=NULL;freed++;}
int COM_FOpenFile(char *name,FILE **f){
    int i;*f=tmpfile();assert(*f);opened++;
    for(i=0;i<200000;i++)fputc(i%251,*f);rewind(*f);return 200000;
}
int main(void){
    byte out[9000];int i;
    host_parms.memsize=11*1024*1024;AW_StreamInit();
    AW_StreamTick("maps/bm001.bsp");assert(!opened); /* method 1 untouched */
    choice->value=2;AW_StreamTick("maps/bm001.bsp");assert(opened==1);
    assert(aw_load_prefetch_copy("maps/bm001.bsp",0,out,sizeof(out))==8192);
    for(i=0;i<8192;i++)assert(out[i]==i%251);
    assert(!aw_load_prefetch_copy("maps/bm002.bsp",0,out,20));
    assert(!aw_load_prefetch_copy("maps/bm001.bsp",-1,out,20));
    AW_StreamTick("maps/bm001.bsp");
    assert(aw_load_prefetch_copy("maps/bm001.bsp",8000,out,sizeof(out))==8384);
    for(i=0;i<8384;i++)assert(out[i]==(8000+i)%251);
    AW_StreamLoadBegin("maps/bm001.bsp");
    assert(aw_load_prefetch_copy("maps/bm001.bsp",100,out,20)==20);
    AW_StreamTick("maps/bm002.bsp");assert(opened==2 && freed==1);
    assert(!aw_load_prefetch_copy("maps/bm001.bsp",100,out,20));
    Cache_Free(allocated);AW_StreamTick("maps/bm002.bsp");
    assert(!aw_load_prefetch_copy("maps/bm002.bsp",0,out,20));
    low=host_parms.memsize-200000;AW_StreamTick("maps/bm003.bsp");assert(opened==2);
    choice->value=1;AW_StreamTick(NULL);assert(!aw_load_prefetch_copy("maps/bm003.bsp",0,out,20));
    choice->value=99;assert(AW_CellChangeMethod()==1);
    low=0;choice->value=2;buffer->value=512;ahead->value=4;
    assert(AW_StreamLookahead()==4);
    for(i=0;i<30;i++)AW_StreamTick("maps/bm004.bsp");
    assert(aw_load_prefetch_copy("maps/bm004.bsp",195000,out,sizeof(out))==5000);
    for(i=0;i<5000;i++)assert(out[i]==(195000+i)%251);
    buffer->value=256;AW_StreamTick("maps/bm004.bsp");
    assert(!aw_load_prefetch_copy("maps/bm004.bsp",195000,out,20));
    buffer->value=1024;ahead->value=999;AW_StreamTick("maps/bm004.bsp");
    assert(buffer->value==128 && AW_StreamLookahead()==1.5f);
    choice->value=1;AW_StreamTick(NULL);
    return 0;
}
