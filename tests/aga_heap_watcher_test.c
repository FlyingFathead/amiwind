/* SPDX-License-Identifier: GPL-2.0-or-later
 * Exercise the real hunk, cache and zone allocator with synthetic data.
 * Host layout validates allocator behavior, not the Amiga target ABI budget.
 */
#include <assert.h>
#include <setjmp.h>
#include <stdarg.h>
#include "../engine/aga/src/zone.c"
/* Diagnostic logs (aw_log.c); without a bound switch they are written live. */
#include "../engine/aga/src/aw_log.c"

static union { long double alignment; byte bytes[6*1024*1024]; } arena;
static union { long double alignment; byte bytes[32768]; } zone_arena;
static jmp_buf failure;
static int expected_failure;
static char error_text[256];
void Q_memset(void *p,int c,int n){memset(p,c,n);}
void Q_memcpy(void *d,void *s,int n){memcpy(d,s,n);}
void Q_strncpy(char *d,char *s,int n){strncpy(d,s,n);}
void Con_Printf(char *fmt,...){(void)fmt;}
void Cmd_AddCommand(char *name,xcommand_t fn){(void)name;(void)fn;}
void Sys_Error(char *fmt,...){
    va_list args;va_start(args,fmt);vsnprintf(error_text,sizeof(error_text),fmt,args);va_end(args);
    assert(expected_failure);longjmp(failure,1);
}
static void reset(void){
    memset(arena.bytes,0,sizeof(arena.bytes));
    hunk_base=arena.bytes;hunk_size=sizeof(arena.bytes);
    mainzone=NULL;aw_cache_bytes=aw_cache_peak=0;aw_cache_preserve_free=0;
    hunk_low_used=hunk_high_used=0;hunk_tempactive=false;hunk_tempmark=0;
    memset(&cache_head,0,sizeof(cache_head));Cache_Init();
    AW_HeapAuditBegin();expected_failure=0;error_text[0]=0;
}
static void load_and_unload_peak(void){
    int permanent,peak,high;
    reset();Hunk_AllocName(512*1024,"base");permanent=Hunk_LowMark();
    AW_HeapAuditBegin();
    high=Hunk_HighMark();assert(Hunk_TempAlloc(1024*1024));
    Hunk_AllocName(768*1024,"map");
    peak=hunk_low_used+hunk_high_used;assert(aw_heap_load_peak==peak);
    Hunk_FreeToHighMark(high);
    assert(aw_heap_load_peak==peak && hunk_low_used+hunk_high_used<peak);
    /* Additional gameplay allocation after the spawn snapshot must be retained. */
    Hunk_AllocName(1536*1024,"late");
    assert(aw_heap_load_peak==hunk_low_used+hunk_high_used);
    peak=aw_heap_load_peak;
    Hunk_FreeToLowMark(permanent);assert(aw_heap_load_peak==peak);
    /* New scene starts its measurement only after outgoing evidence is saved. */
    AW_HeapAuditBegin();assert(aw_heap_load_peak==permanent);
}
static void phase_log_preserves_outgoing_peak(void){
    FILE *f;char text[8192];size_t n;int peak;unsigned long old_id;
    reset();AW_HeapAuditPhase("maps/old.bsp","first-presented");
    Hunk_AllocName(1024*1024,"late-actor");peak=aw_heap_load_peak;old_id=aw_heap_transition;
    AW_HeapAuditPhase("maps/old.bsp","outgoing");
    Hunk_FreeToLowMark(0);AW_HeapAuditBegin();
    AW_HeapAuditPhase("maps/new.bsp","after-unload");
    assert(aw_heap_transition==old_id+1 && aw_heap_load_peak==0 && peak>0);
    f=fopen("heap-audit.log","r");assert(f);n=fread(text,1,sizeof(text)-1,f);text[n]=0;fclose(f);
    assert(strstr(text,"scene=maps/old.bsp phase=outgoing"));
    assert(strstr(text,"scene=maps/new.bsp phase=after-unload"));
    assert(strstr(text,"peak_label=late-actor"));
    assert(strstr(text,"os_metrics=0"));
}
static void cache_move_is_one_logical_allocation(void){
    cache_user_t cache={0};int bytes;byte *p;
    reset();assert(Cache_Alloc(&cache,256*1024,"actor"));bytes=aw_cache_bytes;
    memset(cache.data,0x6b,256*1024);
    Hunk_AllocName(128*1024,"map");
    assert(cache.data && aw_cache_moves==1 && aw_cache_evictions==0);
    assert(aw_cache_bytes==bytes && aw_cache_peak==bytes);
    p=cache.data;assert(p[0]==0x6b && p[256*1024-1]==0x6b);
    Cache_Free(&cache);assert(aw_cache_bytes==0);
}
static void cache_capacity_is_separate(void){
    cache_user_t cache={0};int gap,mark;
    reset();Hunk_AllocName(512*1024,"base");mark=Hunk_LowMark();
    gap=hunk_size-hunk_low_used-hunk_high_used;
    assert(Cache_Alloc(&cache,1024*1024,"actor"));
    assert(aw_cache_bytes>1024*1024 && aw_cache_peak==aw_cache_bytes);
    assert(hunk_size-hunk_low_used-hunk_high_used==gap);
    memset(cache.data,0x5a,1024*1024);
    Hunk_AllocName(5*1024*1024,"world");
    assert(!cache.data);assert(aw_cache_bytes==0 && aw_cache_evictions==1); /* cache is evicted to protect persistent hunk growth */
    Hunk_FreeToLowMark(mark);
    assert(hunk_size-hunk_low_used-hunk_high_used==gap);
    expected_failure=1;
    if(!setjmp(failure)){Cache_Alloc(&cache,hunk_size,"oversize");assert(0);}
    assert(strstr(error_text,"Cache_")!=NULL);
    assert(!strcmp(aw_heap_failed_arena,"cache") && aw_heap_failed_request>hunk_size);expected_failure=0;
}
static void zone_fragmentation_is_separate(void){
    void *blocks[32];memblock_t *b;int n=0,i,free_bytes=0,largest=0,hunk_before;
    reset();hunk_before=hunk_low_used+hunk_high_used;
    mainzone=(memzone_t *)zone_arena.bytes;Z_ClearZone(mainzone,sizeof(zone_arena.bytes));
    while(n<32 && (blocks[n]=Z_TagMalloc(2048,1))!=NULL)n++;
    assert(n>=8);
    for(i=0;i<n;i+=2)Z_Free(blocks[i]);
    for(b=mainzone->blocklist.next;b!=&mainzone->blocklist;b=b->next){
        if(!b->tag){free_bytes+=b->size;if(b->size>largest)largest=b->size;}
    }
    assert(free_bytes>2*largest);
    assert(Z_TagMalloc(free_bytes/2,1)==NULL);
    expected_failure=1;
    if(!setjmp(failure)){Z_Malloc(free_bytes/2);assert(0);}
    assert(!strcmp(aw_heap_failed_arena,"zone"));
    assert(aw_heap_failed_available>0 && aw_heap_failed_available<aw_heap_failed_request);
    expected_failure=0;
    assert(hunk_low_used+hunk_high_used==hunk_before);
    for(i=1;i<n;i+=2)Z_Free(blocks[i]);
    assert(Z_TagMalloc(24000,1)!=NULL); /* merging free neighbors restores capacity */
}
int main(void){load_and_unload_peak();phase_log_preserves_outgoing_peak();cache_move_is_one_logical_allocation();cache_capacity_is_separate();zone_fragmentation_is_separate();return 0;}
