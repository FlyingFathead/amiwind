/* SPDX-License-Identifier: GPL-2.0-or-later
 * Shared actor skins (IMAGE-ACTOR-SKIN-REPEATS-46): a model whose skin pixels live in progs/skins/<hex>.awk
 * decodes to exactly the cache bytes of the same model with its pixels inline, on the stream loader (both
 * passes) and on the file loader (AW_SharedSkinExpand); a missing, short or renamed skin is refused by name.
 * Synthetic data, plus real converted actor models given on the command line (read only). */
#define main old_residency_main
#include "aga_alias_residency_test.c"
#undef main
qboolean aw_loading_music=false;
int Mod_TryStreamAlias(model_t *);
int AW_SharedSkinPixels(const byte *raw,int bytes);
byte *AW_SharedSkinExpand(byte *stored,int *bytes);
extern cvar_t aw_alias_single_pass;
static const char *member_path="shared-skin-member.bin",*skin_path="shared-skin-pixels.bin";
static char skin_name[64];
static int member_size,skin_size,stream_count;
static byte shared[700000];
int COM_FOpenFile(char *name,FILE **f){
    if(!strcmp(name,"progs/stream.mdl")){*f=fopen(member_path,"rb");return *f?member_size:-1;}
    if(skin_name[0] && !strcmp(name,skin_name)){*f=fopen(skin_path,"rb");return *f?skin_size:-1;}
    *f=NULL;return -1;
}
void COM_FileBase(char *name,char *out){strcpy(out,"stream");}
static void write_file(const char *path,const byte *data,int bytes){
    FILE *f=fopen(path,"wb");assert(f);assert(fwrite(data,1,(size_t)bytes,f)==(size_t)bytes);assert(!fclose(f));
}
/* The stored form tools/payload_share.py writes: header, "AWSK", 16 hex digits, pixel count, the rest. */
static int share(int bytes,const char *hex,int pixels_on_disk){
    mdl_t *m=(mdl_t *)raw;int pixels=m->skinwidth*m->skinheight,head=(int)sizeof(mdl_t),rest=bytes-head-4-pixels;
    memcpy(shared,raw,head);memcpy(shared+head,"AWSK",4);memcpy(shared+head+4,hex,16);
    shared[head+20]=pixels&255;shared[head+21]=(pixels>>8)&255;shared[head+22]=(pixels>>16)&255;shared[head+23]=(pixels>>24)&255;
    memcpy(shared+head+24,raw+head+4+pixels,rest);
    write_file(member_path,shared,head+24+rest);member_size=head+24+rest;
    write_file(skin_path,raw+head+4,pixels_on_disk);skin_size=pixels_on_disk;
    sprintf(skin_name,"progs/skins/%.16s.awk",hex);
    return member_size;
}
static void *expected_cache(int bytes,int *n){
    model_t old;void *copy;memset(&old,0,sizeof(old));reset();
    Mod_LoadAliasModel(&old,raw,bytes);
    *n=((cache_system_t *)old.cache.data-1)->size-(int)sizeof(cache_system_t);
    copy=malloc(*n);assert(copy);memcpy(copy,old.cache.data,*n);Cache_Free(&old.cache);return copy;
}
static void same_as_inline(int bytes,int single_pass){
    model_t now;void *expected;int n,stored,full;byte *copy;
    int streams;
    expected=expected_cache(bytes,&n);
    /* Does the stream loader take the model with its pixels inline? The shared form must decide the same. */
    write_file(member_path,raw,bytes);member_size=bytes;skin_name[0]=0;
    memset(&now,0,sizeof(now));reset();strcpy(now.name,"progs/stream.mdl");aw_alias_single_pass.value=single_pass;
    streams=Mod_TryStreamAlias(&now);if(now.cache.data)Cache_Free(&now.cache);
    stored=share(bytes,"0123456789abcdef",((mdl_t *)raw)->skinwidth*((mdl_t *)raw)->skinheight);
    assert(AW_SharedSkinPixels(shared,stored)==((mdl_t *)raw)->skinwidth*((mdl_t *)raw)->skinheight);
    assert(AW_SharedSkinPixels(raw,bytes)<0);
    /* The stream loader, both passes. */
    memset(&now,0,sizeof(now));reset();strcpy(now.name,"progs/stream.mdl");
    assert(Mod_TryStreamAlias(&now)==streams);
    if(streams){
        assert(((cache_system_t *)now.cache.data-1)->size-(int)sizeof(cache_system_t)==n);
        assert(!memcmp(expected,now.cache.data,n));Cache_Free(&now.cache);
    }
    aw_alias_single_pass.value=1;stream_count+=streams;
    /* The file loader's rebuild is the inline model, byte for byte. */
    copy=malloc(stored);assert(copy);memcpy(copy,shared,stored);full=stored;
    copy=AW_SharedSkinExpand(copy,&full);assert(copy && full==bytes && !memcmp(copy,raw,bytes));free(copy);
    free(expected);
}
static void refused(int bytes,const char *hex,int pixels_on_disk,int drop_skin){
    model_t m;int stored;byte *copy;
    stored=share(bytes,hex,pixels_on_disk);if(drop_skin)skin_name[0]=0;
    copy=malloc(stored);assert(copy);memcpy(copy,shared,stored);
    assert(!AW_SharedSkinExpand(copy,&stored));        /* frees its input either way */
    memset(&m,0,sizeof(m));reset();strcpy(m.name,"progs/stream.mdl");expect_error=1;
    if(!setjmp(failure)){Mod_TryStreamAlias(&m);assert(0 && "bad shared skin accepted");}
    expect_error=0;assert(!m.cache.data && m.needload==1);
}
int main(int argc,char **argv){
    int bytes,i,pixels;FILE *f;
    bytes=make_alias(0);same_as_inline(bytes,1);same_as_inline(bytes,0);assert(stream_count==2);stream_count=0;
    pixels=((mdl_t *)raw)->skinwidth*((mdl_t *)raw)->skinheight;
    refused(bytes,"0123456789abcdef",pixels-1,0);   /* short skin file */
    refused(bytes,"0123456789abcdef",pixels,1);     /* missing skin file */
    refused(bytes,"0123456789ABCDEF",pixels,0);     /* not a lowercase hex name */
    for(i=1;i<argc;i++){
        f=fopen(argv[i],"rb");assert(f);bytes=(int)fread(raw,1,sizeof(raw),f);assert(!ferror(f) && feof(f));fclose(f);
        same_as_inline(bytes,1);
    }
    remove(member_path);remove(skin_path);
    printf("shared-skin: stream (both passes) and file loader decode the inline cache bytes; refusals named; real assets=%d (stream loader %d)\n",argc-1,stream_count);
    return 0;
}
