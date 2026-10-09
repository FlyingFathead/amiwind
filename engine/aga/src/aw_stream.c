/* SPDX-License-Identifier: GPL-2.0-or-later
 * Method 2 experiment: evictable 128 KiB BSP prefix, 8 KiB read per frame.
 * No second scene, entity construction or collision swap runs in the background.
 */
#include "quakedef.h"
#include "aw_log.h"
#define PREFETCH_STEP 8192
static cvar_t method={"aw_cell_change_method","1",true};
static cvar_t buffer_kib={"aw_cell_prefetch_kib","128",true};
static cvar_t ahead_seconds={"aw_cell_prefetch_seconds","1.5",true};
static cache_user_t cache;
static FILE *input;
static char path[64];
static size_t filled,consumed,capacity;
static int complete,failed;
static double read_seconds;
static double worst_read,transition_started;
static int transition_pending,transition_ready,heap_first_present;
extern size_t (*aw_load_prefetch_copy)(const char *,long,byte *,size_t);
extern double (*aw_load_clock)(void);
extern int (*aw_load_hunk_used)(void);
extern int hunk_low_used,hunk_high_used;
extern long aw_load_disk_bytes,aw_load_disk_calls;
extern double aw_load_disk_seconds,aw_load_decode_seconds;
static void cancel(void) {
    if(input)fclose(input);
    input=NULL;if(cache.data)Cache_Free(&cache);
    path[0]=0;filled=capacity=0;complete=failed=0;read_seconds=worst_read=0;
}
float AW_StreamLookahead(void) {
    if(!(ahead_seconds.value>=.5f && ahead_seconds.value<=4.0f))Cvar_SetValue(ahead_seconds.name,1.5f);
    return ahead_seconds.value;
}
static size_t requested_bytes(void) {
    if(buffer_kib.value!=128 && buffer_kib.value!=256 && buffer_kib.value!=512)Cvar_SetValue(buffer_kib.name,128);
    return (size_t)buffer_kib.value*1024;
}
int AW_CellChangeMethod(void) {
    if(method.value!=1 && method.value!=2){
        Con_Printf("aw_cell_change_method supports 1 (current) or 2 (read-ahead experiment).\n");
        Cvar_SetValue(method.name,1);
    }
    return (int)method.value;
}
int AW_StreamOption(int option,int step) {
    int value,index;
    if(!option){value=AW_CellChangeMethod();if(step)Cvar_SetValue(method.name,value==1?2:1);return AW_CellChangeMethod();}
    value=(int)(requested_bytes()/1024);index=value==128?0:value==256?1:2;
    if(step){index=(index+(step>0?1:2))%3;Cvar_SetValue(buffer_kib.name,index==0?128:index==1?256:512);}
    return (int)buffer_kib.value;
}
void AW_StreamTick(const char *next) {
    byte *data;size_t n,got,wanted;double start,elapsed;FILE *f=NULL;
    if(AW_CellChangeMethod()!=2 || !next){if(path[0])cancel();return;}
    wanted=requested_bytes();
    if(strcmp(path,next) || wanted!=capacity){
        cancel();if(strlen(next)>=sizeof(path))return;strcpy(path,next);
        capacity=wanted;
        /* Reserve room for decoding and active aliases. Allocation may evict
         * cache data but cannot consume the protected low/high hunk arena. */
        if(host_parms.memsize-Hunk_LowMark()-Hunk_HighMark()<capacity+256*1024){failed=1;return;}
        if(COM_FOpenFile((char *)next,&f)<0 || !f){failed=1;return;}
        input=f;Cache_Alloc(&cache,capacity,"next-cell");
    }
    if(failed || complete)return;
    data=Cache_Check(&cache);
    if(!data){if(input)fclose(input);input=NULL;failed=1;return;}
    n=capacity-filled;if(n>PREFETCH_STEP)n=PREFETCH_STEP;
    start=Sys_FloatTime();got=fread(data+filled,1,n,input);elapsed=Sys_FloatTime()-start;read_seconds+=elapsed;
    if(elapsed>worst_read)worst_read=elapsed;
    filled+=got;
    if(got!=n || filled==capacity){
        if(ferror(input)){filled=0;failed=1;}
        fclose(input);input=NULL;complete=1;
    }
}
static size_t copy(const char *name,long offset,byte *out,size_t bytes) {
    byte *data;size_t n;
    if(method.value!=2 || failed || strcmp(name,path) || offset<0 || (size_t)offset>=filled)return 0;
    data=Cache_Check(&cache);if(!data)return 0;
    n=filled-(size_t)offset;if(n>bytes)n=bytes;
    memcpy(out,data+offset,n);consumed+=n;return n;
}
void AW_StreamLoadBegin(const char *name) {
    heap_first_present=1;
    if(input){fclose(input);input=NULL;}
    if(strcmp(name,path) || AW_CellChangeMethod()!=2)cancel();
    consumed=0;aw_load_disk_bytes=aw_load_disk_calls=0;
    aw_load_disk_seconds=aw_load_decode_seconds=0;
}
void AW_StreamLoadEnd(const char *name,double world,double actors,double total) {
    {
        AW_LogPrintf(AW_LOG_CELL_LOAD,"%s\t%d\t%ld\t%ld\t%.6f\t%.6f\t%.6f\t%.6f\t%.6f\t%lu\t%.6f\t%d\t%d\t%lu\t%lu\t%.6f\t%.2f\n",name,
            AW_CellChangeMethod(),aw_load_disk_bytes,aw_load_disk_calls,aw_load_disk_seconds,
            aw_load_decode_seconds,world,actors,total,(unsigned long)consumed,read_seconds,Hunk_LowMark(),Hunk_HighMark(),
            (unsigned long)capacity,(unsigned long)filled,worst_read,(double)AW_StreamLookahead());
    }
    cancel();
}
void AW_StreamTransitionBegin(void) {
    transition_started=Sys_FloatTime();transition_pending=1;transition_ready=0;
}
void AW_StreamTransitionReady(void) {if(transition_pending)transition_ready=1;}
/* Called after video presentation, before selecting the next scene. */
void AW_StreamPresented(void) {
    if(heap_first_present && cls.state==ca_connected && cls.signon==SIGNONS && cl.worldmodel){
        AW_HeapAuditPhase(cl.worldmodel->name,"first-presented");heap_first_present=0;
    }
    if(!transition_pending || !transition_ready || cls.state!=ca_connected || cls.signon!=SIGNONS || !cl.worldmodel)return;
    {AW_LogPrintf(AW_LOG_CELL_VISIBLE,"%s\t%d\t%.6f\t%lu\t%.2f\n",cl.worldmodel->name,AW_CellChangeMethod(),
        Sys_FloatTime()-transition_started,(unsigned long)requested_bytes(),(double)AW_StreamLookahead());}
    transition_pending=transition_ready=0;
}
static int hunk_used(void) {return hunk_low_used+hunk_high_used;}
void AW_StreamInit(void) {
    Cvar_RegisterVariable(&method);Cvar_RegisterVariable(&buffer_kib);Cvar_RegisterVariable(&ahead_seconds);
    aw_load_prefetch_copy=copy;aw_load_clock=Sys_FloatTime;aw_load_hunk_used=hunk_used;
}
