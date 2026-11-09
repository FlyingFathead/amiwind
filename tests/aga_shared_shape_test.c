/* SPDX-License-Identifier: GPL-2.0-or-later
 * Shared actor shapes (IMAGE-BIGGER-THAN-ORIGINAL-62): a model whose ST and triangle blocks live in
 * progs/shapes/<hex>.aws1 decodes to exactly the cache bytes of the same model with its blocks inline, on the
 * stream loader (both passes) and on the file loader (AW_SharedShapeExpand), also when its skin is shared too; a
 * missing, short or renamed shape file is refused by name. Synthetic data, plus real converted actor models given
 * on the command line (read only). */
#define main old_residency_main
#include "aga_alias_residency_test.c"
#undef main
qboolean aw_loading_music=false;
int Mod_TryStreamAlias(model_t *);
int AW_SharedSkinPixels(const byte *raw,int bytes);
byte *AW_SharedSkinExpand(byte *stored,int *bytes);
int AW_AliasSkinEnd(const byte *raw,int bytes);
int AW_SharedShapeAt(const byte *raw,int bytes);
byte *AW_SharedShapeExpand(byte *stored,int *bytes);
extern cvar_t aw_alias_single_pass;
static const char *member_path="shared-shape-member.bin",*shape_path="shared-shape-blocks.bin",
                  *skin_path="shared-shape-skin.bin";
static char shape_name[64],skin_name[64];
static int member_size,shape_size,skin_size,stream_count,real_count;
static byte shared[900000],work[900000];
int COM_FOpenFile(char *name,FILE **f){
    if(!strcmp(name,"progs/stream.mdl")){*f=fopen(member_path,"rb");return *f?member_size:-1;}
    if(shape_name[0] && !strcmp(name,shape_name)){*f=fopen(shape_path,"rb");return *f?shape_size:-1;}
    if(skin_name[0] && !strcmp(name,skin_name)){*f=fopen(skin_path,"rb");return *f?skin_size:-1;}
    *f=NULL;return -1;
}
void COM_FileBase(char *name,char *out){strcpy(out,"stream");}
static void write_file(const char *path,const byte *data,int bytes){
    FILE *f=fopen(path,"wb");assert(f);assert(fwrite(data,1,(size_t)bytes,f)==(size_t)bytes);assert(!fclose(f));
}
static void le32(byte *p,unsigned int v){p[0]=v&255;p[1]=(v>>8)&255;p[2]=(v>>16)&255;p[3]=(v>>24)&255;}
/* SRC (BYTES long, a single-skin model) with its skin shared when SKIN, into OUT; returns its length. */
static int skin_form(const byte *src,int bytes,int skin,byte *out){
    const mdl_t *m=(const mdl_t *)src;int head=(int)sizeof(mdl_t),pixels=m->skinwidth*m->skinheight,rest;
    if(!skin){memcpy(out,src,bytes);skin_name[0]=0;return bytes;}
    rest=bytes-head-4-pixels;
    memcpy(out,src,head);memcpy(out+head,"AWSK",4);memcpy(out+head+4,"fedcba9876543210",16);le32(out+head+20,pixels);
    memcpy(out+head+24,src+head+4+pixels,rest);
    write_file(skin_path,src+head+4,pixels);skin_size=pixels;strcpy(skin_name,"progs/skins/fedcba9876543210.awk");
    return head+24+rest;
}
/* The stored form tools/payload_share.py writes: everything up to the skin's end, "AWSH", 16 hex digits, the ST
 * and triangle byte counts, the rest. The blocks go to the shape file (BLOCKS_ON_DISK of them). */
static int share(const byte *src,int bytes,const char *hex,int blocks_on_disk){
    const mdl_t *m=(const mdl_t *)src;int at=AW_AliasSkinEnd(src,bytes),st=m->numverts*12,tri=m->numtris*16,rest;
    assert(at>0);rest=bytes-at-st-tri;assert(rest>=0);
    memcpy(shared,src,at);memcpy(shared+at,"AWSH",4);memcpy(shared+at+4,hex,16);le32(shared+at+20,st);le32(shared+at+24,tri);
    memcpy(shared+at+28,src+at+st+tri,rest);
    write_file(member_path,shared,at+28+rest);member_size=at+28+rest;
    write_file(shape_path,src+at,blocks_on_disk);shape_size=blocks_on_disk;
    sprintf(shape_name,"progs/shapes/%.16s.aws1",hex);
    return member_size;
}
static void *generic_cache(int bytes,int *n){
    model_t old;void *copy;memset(&old,0,sizeof(old));reset();
    Mod_LoadAliasModel(&old,raw,bytes);
    *n=((cache_system_t *)old.cache.data-1)->size-(int)sizeof(cache_system_t);
    copy=malloc(*n);assert(copy);memcpy(copy,old.cache.data,*n);Cache_Free(&old.cache);return copy;
}
/* The stream loader over MEMBER: 1 and the cache bytes in *OUT (*N long) when it takes it, else 0. With EXPECTED,
 * the cache must equal it. */
static int stream_member(const byte *member,int bytes,int single_pass,const void *expected,int n,void **out,int *outn){
    model_t now;int streams,size;
    write_file(member_path,member,bytes);member_size=bytes;
    memset(&now,0,sizeof(now));reset();strcpy(now.name,"progs/stream.mdl");aw_alias_single_pass.value=single_pass;
    streams=Mod_TryStreamAlias(&now);
    if(streams){
        size=((cache_system_t *)now.cache.data-1)->size-(int)sizeof(cache_system_t);
        if(expected)assert(size==n && !memcmp(expected,now.cache.data,n));
        if(out){*out=malloc(size);assert(*out);memcpy(*out,now.cache.data,size);*outn=size;}
    }
    if(now.cache.data)Cache_Free(&now.cache);
    aw_alias_single_pass.value=1;return streams;
}
static void same_as_inline(int bytes,int single_pass,int skin,int synthetic){
    void *expected=NULL,*generic=NULL;int n=0,g,stored,inline_bytes,full,streams;byte *copy;
    /* The form with the blocks inline (its skin shared or not) decides whether the stream loader takes it; its
     * cache bytes are what the shared form must decode to. */
    inline_bytes=skin_form(raw,bytes,skin,work);shape_name[0]=0;
    streams=stream_member(work,inline_bytes,single_pass,NULL,0,&expected,&n);
    if(synthetic){                      /* the synthetic model: the stream equals the generic loader too */
        generic=generic_cache(bytes,&g);assert(streams && g==n && !memcmp(generic,expected,n));free(generic);
    }
    stored=share(work,inline_bytes,"0123456789abcdef",((mdl_t *)raw)->numverts*12+((mdl_t *)raw)->numtris*16);
    assert(AW_SharedShapeAt(shared,stored)>0 && AW_SharedShapeAt(work,inline_bytes)<0);
    assert((AW_SharedSkinPixels(shared,stored)>=0)==skin);
    /* The stream loader, the pass given. */
    assert(stream_member(shared,stored,single_pass,expected,n,NULL,NULL)==streams);
    stream_count+=streams;
    /* The file loader's rebuild (model.c AW_AliasFile: the shape, then the skin) is the original, byte for byte. */
    copy=malloc(stored);assert(copy);memcpy(copy,shared,stored);full=stored;
    copy=AW_SharedShapeExpand(copy,&full);assert(copy && full==inline_bytes && !memcmp(copy,work,inline_bytes));
    if(skin){copy=AW_SharedSkinExpand(copy,&full);assert(copy);}
    assert(full==bytes && !memcmp(copy,raw,bytes));free(copy);
    free(expected);
}
static void refused(int bytes,const char *hex,int blocks_on_disk,int drop_shape){
    model_t m;int stored;byte *copy;
    skin_name[0]=0;stored=share(raw,bytes,hex,blocks_on_disk);if(drop_shape)shape_name[0]=0;
    copy=malloc(stored);assert(copy);memcpy(copy,shared,stored);
    assert(!AW_SharedShapeExpand(copy,&stored));        /* frees its input either way */
    memset(&m,0,sizeof(m));reset();strcpy(m.name,"progs/stream.mdl");expect_error=1;
    if(!setjmp(failure)){Mod_TryStreamAlias(&m);assert(0 && "bad shared shape accepted");}
    expect_error=0;assert(!m.cache.data && m.needload==1);
}
int main(int argc,char **argv){
    int bytes,i,blocks;FILE *f;
    bytes=make_alias(0);
    for(i=0;i<4;i++)same_as_inline(bytes,i&1,i>>1,1);
    assert(stream_count==4);stream_count=0;
    blocks=((mdl_t *)raw)->numverts*12+((mdl_t *)raw)->numtris*16;
    refused(bytes,"0123456789abcdef",blocks-1,0);   /* short shape file */
    refused(bytes,"0123456789abcdef",blocks,1);     /* missing shape file */
    refused(bytes,"0123456789ABCDEF",blocks,0);     /* not a lowercase hex name */
    for(i=1;i<argc;i++){
        fprintf(stderr,"%s\n",argv[i]);         /* the last name before a failure is the model that failed */
        f=fopen(argv[i],"rb");assert(f);bytes=(int)fread(raw,1,sizeof(raw),f);assert(!ferror(f) && feof(f));fclose(f);
        if(AW_AliasSkinEnd(raw,bytes)<0 || AW_SharedSkinPixels(raw,bytes)>=0){printf("skipped (no single inline skin): %s\n",argv[i]);continue;}
        same_as_inline(bytes,1,0,0);real_count++;
        if(i%16==1){same_as_inline(bytes,0,0,0);same_as_inline(bytes,1,1,0);}
    }
    remove(member_path);remove(shape_path);remove(skin_path);
    assert(stream_count*2>=real_count);     /* most real actor models go through the stream loader */
    printf("shared-shape: stream (both passes) and file loader decode the inline cache bytes, with and without a shared skin; refusals named; real assets=%d (stream loader %d)\n",real_count,stream_count);
    return 0;
}
