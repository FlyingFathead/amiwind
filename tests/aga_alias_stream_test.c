/* SPDX-License-Identifier: GPL-2.0-or-later
 * Production decoder comparison and real hunk/LRU ownership tests. */
#define main old_residency_main
#include "aga_alias_residency_test.c"
#undef main
qboolean aw_loading_music=false;
int Mod_TryStreamAlias(model_t *);
extern void (*aw_load_audio_tick)(void);
static const char *member_path="alias-stream-pack.bin";
static int member_size,ticks,action,cache_allocated_seen;
static model_t *stream_model;
int COM_FOpenFile(char *name,FILE **f){
    if(strcmp(name,"progs/stream.mdl")){*f=NULL;return -1;}
    *f=fopen(member_path,"rb");if(!*f)return -1;
    assert(!fseek(*f,13,SEEK_SET));return member_size;
}
void COM_FileBase(char *name,char *out){strcpy(out,"stream");}
static void tick(void){
    ticks++;
    if(stream_model && stream_model->cache.data){
        cache_allocated_seen++;
        if(action==1){action=0;Cache_Move((cache_system_t *)stream_model->cache.data-1);}
        else if(action==2){action=0;Cache_Free(&stream_model->cache);}
    }
}
static void write_member(int declared,int physical){
    FILE *f=fopen(member_path,"wb");assert(f);
    assert(fwrite("pack-prefix!!",1,13,f)==13);
    assert(fwrite(raw,1,(size_t)physical,f)==(size_t)physical);
    assert(!fclose(f));member_size=declared;
}
static void compare(int bytes,int move){
    model_t old,now;void *expected;int n,low,high;
    memset(&old,0,sizeof(old));memset(&now,0,sizeof(now));reset();
    Mod_LoadAliasModel(&old,raw,bytes);
    n=((cache_system_t *)old.cache.data-1)->size-(int)sizeof(cache_system_t);
    expected=malloc(n);assert(expected);memcpy(expected,old.cache.data,n);
    /* This expected copy is outside the runtime and removed after comparison. */
    Cache_Free(&old.cache);strcpy(now.name,"progs/stream.mdl");
    write_member(bytes,bytes);stream_model=&now;action=move;cache_allocated_seen=0;
    low=hunk_low_used;high=hunk_high_used;fail_malloc=1;
    assert(Mod_TryStreamAlias(&now)==1);fail_malloc=0;
    assert(cache_allocated_seen && hunk_low_used==low && hunk_high_used==high);
    assert(now.cache.data && now.needload==0 && now.type==old.type);
    assert(((cache_system_t *)now.cache.data-1)->size-(int)sizeof(cache_system_t)==n);
    if(memcmp(expected,now.cache.data,n)){
        int at,shown=0;for(at=0;at<n && shown<16;at++)if(((byte *)expected)[at]!=((byte *)now.cache.data)[at]){
            fprintf(stderr,"offset=%d old=%u new=%u total=%d move=%d\n",at,((byte *)expected)[at],((byte *)now.cache.data)[at],n,move);shown++;
        }
        assert(0 && "decoded cache differs");
    }
    assert(now.radius==old.radius && !memcmp(now.mins,old.mins,sizeof(now.mins)) && !memcmp(now.maxs,old.maxs,sizeof(now.maxs)));
    assert(now.flags==old.flags && now.synctype==old.synctype && now.numframes==old.numframes);
    assert(!move || aw_cache_moves>0);free(expected);Cache_Free(&now.cache);stream_model=NULL;
}
static void rejected(int bytes,int physical,int evict){
    model_t m;memset(&m,0,sizeof(m));reset();strcpy(m.name,"progs/stream.mdl");
    write_member(bytes,physical);stream_model=&m;action=evict?2:0;cache_allocated_seen=0;expect_error=1;
    if(!setjmp(failure)){Mod_TryStreamAlias(&m);assert(0 && "invalid stream accepted");}
    expect_error=0;assert(!m.cache.data && !hunk_low_used && !hunk_high_used);
    assert(m.needload==1);if(!evict)assert(!cache_allocated_seen);stream_model=NULL;
}
int main(int argc,char **argv){
    int bytes,i;model_t m;FILE *f;
    aw_load_audio_tick=tick;
    bytes=make_alias(0);compare(bytes,0);compare(bytes,1);
    /* Large aliases preserve the existing generic path and allocation policy. */
    bytes=make_alias(2);memset(&m,0,sizeof(m));strcpy(m.name,"progs/stream.mdl");write_member(bytes,bytes);
    assert(Mod_TryStreamAlias(&m)==0 && !m.cache.data);
    bytes=make_alias(1);memset(&m,0,sizeof(m));strcpy(m.name,"progs/stream.mdl");write_member(bytes,bytes);
    assert(Mod_TryStreamAlias(&m)==0 && !m.cache.data); /* legal groups */
    bytes=make_alias(0);r_pixbytes=2;assert(Mod_TryStreamAlias(&m)==0);r_pixbytes=1;
    bytes=make_alias(0);rejected(bytes,bytes-1,0);
    bytes=make_alias(0);rejected(bytes,bytes,1);
    bytes=make_alias(0);raw[bytes]=0;rejected(bytes+1,bytes+1,0);
    bytes=make_alias(0);((mdl_t *)raw)->numframes=INT_MAX;rejected(bytes,bytes,0);
    bytes=make_alias(0);((mdl_t *)raw)->skinwidth=INT_MAX-3;rejected(bytes,bytes,0);
    bytes=make_alias(0);*(int *)(raw+88+256*256+900*sizeof(stvert_t)+4)=900;rejected(bytes,bytes,0);
    /* Real converter assets supplied by a private read-only input list. */
    for(i=1;i<argc;i++){
        f=fopen(argv[i],"rb");assert(f);bytes=(int)fread(raw,1,sizeof(raw),f);assert(!ferror(f) && feof(f));fclose(f);
        compare(bytes,0);
    }
    aw_load_audio_tick=NULL;remove(member_path);
    printf("alias-stream: exact decoded cache bytes; ordinary multi-frame, groups fallback, relocation, eviction, malformed bounds, malloc failure; real assets=%d ticks=%d\n",argc-1,ticks);
    return 0;
}
