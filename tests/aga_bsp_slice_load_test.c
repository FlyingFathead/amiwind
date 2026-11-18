/* SPDX-License-Identifier: GPL-2.0-or-later
 * Streamed BSP loading against the in-memory file image. Every BSP is loaded
 * through the actual Mod_LoadBrushModel both ways; the decoded low Hunk and
 * every model slot must be byte-identical, and the streamed load may hold at
 * most one slice of temporary input beside the decoded map.
 *
 *   check FILE...      compare image, streamed, prefetched and music-paced loads
 *   dump FILE OUT      streamed load only; write the decoded Hunk and model slots
 *                      (fixed heap address, so two builds can be compared)
 */
#include <assert.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdint.h>
#include <sys/mman.h>
#include "../engine/aga/src/model.c"
/* Diagnostic logs (aw_log.c); without a bound switch they are written live. */
#include "../engine/aga/src/aw_log.c"
#ifndef AW_BSP_SLICE_BYTES
#define AW_BSP_SLICE_BYTES (1<<30) /* dump mode also builds the staged loader */
#define AW_BSP_DIRECTORY_BYTES 0
#endif
/* Largest temporary slice: a texture directory prefix plus one window. */
#define SLICE_LIMIT (AW_BSP_SLICE_BYTES+((AW_BSP_DIRECTORY_BYTES+15)&~15))

qboolean aw_loading_music=false;
static short same_short(short v){return v;}
static int same_long(int v){return v;}
static float same_float(float v){return v;}
short (*LittleShort)(short)=same_short;
int (*LittleLong)(int)=same_long;
float (*LittleFloat)(float)=same_float;
texture_t *r_notexture_mip;

#define HEAP_BYTES (96*1024*1024)
typedef struct { int sentinel, size; char name[8]; } test_hunk_t;
static byte *heap;
static int low, high, peak, temp_active, temp_mark, temp_largest, temp_calls;
static int expect_error, sky_calls;
static jmp_buf failure;

static void track(void){if(low+high>peak)peak=low+high;}
static void *block(byte *p,int size,char *name){
    test_hunk_t *h=(test_hunk_t *)p;memset(p,0,size);
    h->sentinel=0x1df001ed;h->size=size;memcpy(h->name,name,strlen(name)<8?strlen(name):8);return h+1;
}
void *Hunk_AllocName(int size,char *name){
    byte *p;
    assert(size>=0);size=sizeof(test_hunk_t)+((size+15)&~15);
    assert(low+high+size<=HEAP_BYTES);p=heap+low;low+=size;track();
    return block(p,size,name);
}
int Hunk_LowMark(void){return low;}
void Hunk_FreeToLowMark(int mark){assert(mark>=0 && mark<=low);memset(heap+mark,0,low-mark);low=mark;}
void Hunk_FreeToHighMark(int mark){
    if(temp_active){temp_active=0;Hunk_FreeToHighMark(temp_mark);}
    assert(mark>=0 && mark<=high);memset(heap+HEAP_BYTES-high,0,high-mark);high=mark;
}
int Hunk_HighMark(void){
    if(temp_active){temp_active=0;Hunk_FreeToHighMark(temp_mark);}
    return high;
}
static int temp_fail;   /* the next temporary allocation fails, as a full Hunk's does (returns NULL) */
void *Hunk_TempAlloc(int size){
    int bytes;
    assert(size>0);
    if(temp_fail){temp_fail=0;return NULL;}
    if(size>temp_largest)temp_largest=size;
    temp_calls++;size=(size+15)&~15;
    if(temp_active){Hunk_FreeToHighMark(temp_mark);temp_active=0;}
    temp_mark=Hunk_HighMark();bytes=sizeof(test_hunk_t)+size;
    assert(low+high+bytes<=HEAP_BYTES);high+=bytes;track();temp_active=1;
    return block(heap+HEAP_BYTES-high,bytes,"temp");
}
/* SCENE-LOAD-FAIL-FALLBACK-67: an expected error is read as the game's fatal-path hook reads it (model.c AW_MapFailure:
 * the kind, the file, its size, the lump and where it starts, the loader's message), and the loader must then be left
 * as after a finished load (the file closed, the model not present, no decode running). */
static int fail_kind;static aw_mapfail_t fail;static model_t *fail_model;
void Sys_Error(char *fmt,...){
    va_list args;
    if(!expect_error){va_start(args,fmt);vfprintf(stderr,fmt,args);va_end(args);fputc('\n',stderr);abort();}
    fail_kind=AW_MapFailure(&fail);
    if(fail_kind)assert(!aw_bsp_file && !aw_bsp_lumps && !aw_map_decoding && fail_model->needload==NL_UNREFERENCED);
    longjmp(failure,1);
}
void Con_Printf(char *fmt,...){}
void *Cache_Check(cache_user_t *c){return NULL;}
void Cache_Free(cache_user_t *c){abort();}
vec_t Length(vec3_t v){return (vec_t)sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]);}
void R_InitSky(texture_t *tx){assert(tx && !strncmp(tx->name,"sky",3));sky_calls++;}
int Q_strncmp(char *a,char *b,int n){return strncmp(a,b,n);}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Q_strncpy(char *a,char *b,int n){strncpy(a,b,n);}
void COM_FileBase(char *in,char *out){
    char *slash=strrchr(in,'/'),*dot;const char *s=slash?slash+1:in;
    strncpy(out,s,31);out[31]=0;dot=strrchr(out,'.');if(dot)*dot=0;
}
int COM_FOpenFile(char *name,FILE **file){
    long size;
    *file=fopen(name,"rb");if(!*file)return -1;
    fseek(*file,0,SEEK_END);size=ftell(*file);fseek(*file,0,SEEK_SET);return (int)size;
}

static byte *image;static long image_bytes,prefetch_limit;
/* Like aw_stream.c: the leading prefetch_limit bytes of the file are cached. */
static size_t prefetch(const char *name,long offset,byte *out,size_t bytes){
    size_t n;
    if(offset<0 || offset>=prefetch_limit)return 0;
    n=(size_t)(prefetch_limit-offset);if(n>bytes)n=bytes;
    memcpy(out,image+offset,n);return n;
}

typedef struct { int low; byte *bytes; model_t *models; int known; int peak; } snapshot_t;
static void reset(void){
    memset(heap,0,HEAP_BYTES);low=high=peak=temp_active=temp_largest=temp_calls=0;
    memset(mod_known,0,sizeof(mod_known));mod_numknown=0;loadmodel=NULL;
    aw_load_prefetch_copy=NULL;aw_loading_music=false;sky_calls=0;
}
static void snapshot(snapshot_t *s){
    assert(!temp_active && high==0);
    s->low=low;s->bytes=malloc(low);assert(s->bytes);memcpy(s->bytes,heap,low);
    s->known=mod_numknown;s->models=malloc(mod_numknown*sizeof(model_t)+1);assert(s->models);
    memcpy(s->models,mod_known,mod_numknown*sizeof(model_t));s->peak=peak;
}
static int same(const snapshot_t *a,const snapshot_t *b){
    return a->low==b->low && a->known==b->known && !memcmp(a->bytes,b->bytes,a->low) &&
        !memcmp(a->models,b->models,a->known*sizeof(model_t));
}
static void load_image(char *path,snapshot_t *s){
    model_t *mod;byte *copy=malloc(image_bytes);
    assert(copy);memcpy(copy,image,image_bytes);reset();
    mod=Mod_FindName(path);COM_FileBase(mod->name,loadname);loadmodel=mod;mod->needload=NL_PRESENT;
    Mod_LoadBrushModel(mod,copy);snapshot(s);free(copy);
}
static void load_stream(char *path,snapshot_t *s,long cached,qboolean music){
    model_t *mod;
    reset();aw_loading_music=music;prefetch_limit=cached;
    if(cached)aw_load_prefetch_copy=prefetch;
    mod=Mod_FindName(path);assert(AW_TryStreamBrush(mod));
    aw_load_prefetch_copy=NULL;snapshot(s);
}
static void read_image(const char *path){
    FILE *f=fopen(path,"rb");assert(f);
    fseek(f,0,SEEK_END);image_bytes=ftell(f);fseek(f,0,SEEK_SET);
    free(image);image=malloc(image_bytes);assert(image && fread(image,1,image_bytes,f)==(size_t)image_bytes);fclose(f);
}
static int largest_staged_lump(void){
    /* Every section the old loader staged: all but the four direct ones. */
    dheader_t *h=(dheader_t *)image;int i,largest=0;
    for(i=0;i<HEADER_LUMPS;i++){
        if(i==LUMP_VISIBILITY || i==LUMP_LIGHTING || i==LUMP_ENTITIES || i==LUMP_CLIPNODES)continue;
        if(h->lumps[i].filelen>largest)largest=h->lumps[i].filelen;
    }
    return largest;
}

#ifdef AW_TEST_WRAP_FREAD
/* Linked with --wrap=fread: log every read of a streamed BSP. */
size_t __real_fread(void *,size_t,size_t,FILE *);
static int read_log[65536][2],read_count,read_logging;
__attribute__((externally_visible)) size_t __wrap_fread(void *p,size_t size,size_t n,FILE *f){
    if(read_logging && f==aw_bsp_file){
        assert(read_count<65536);read_log[read_count][0]=(int)ftell(f);read_log[read_count++][1]=(int)(size*n);
    }
    return __real_fread(p,size,n,f);
}
/* The staged loader read the header, then every lump in load order from its
 * start in 16 KiB pieces (AW_LoadRead). A failed node-prefix certification
 * stops part way through the node lump and reads it again from the start. */
static int expect_lump(int k,int lump,int partial){
    dheader_t *h=(dheader_t *)image;int at;
    for(at=0;at<h->lumps[lump].filelen;at+=16384){
        int want=h->lumps[lump].filelen-at<16384?h->lumps[lump].filelen-at:16384;
        if(partial && at && (k>=read_count || read_log[k][0]==h->lumps[lump].fileofs))return k;
        if(k>=read_count || read_log[k][0]!=h->lumps[lump].fileofs+at || read_log[k][1]!=want){
            fprintf(stderr,"read %d differs from the staged loader (lump %d)\n",k,lump);abort();
        }
        k++;
    }
    return k;
}
static void expect_staged_reads(int failed_prefix){
    static const int order[]={LUMP_VERTEXES,LUMP_EDGES,LUMP_SURFEDGES,LUMP_TEXTURES,LUMP_LIGHTING,
        LUMP_PLANES,LUMP_TEXINFO,LUMP_FACES,LUMP_MARKSURFACES,LUMP_VISIBILITY,LUMP_LEAFS,
        LUMP_MODELS,LUMP_NODES,LUMP_CLIPNODES,LUMP_ENTITIES};
    int i,k=1;
    assert(read_count && read_log[0][0]==0 && read_log[0][1]==(int)sizeof(dheader_t));
    for(i=0;i<(int)(sizeof(order)/sizeof(order[0]));i++){
        if(order[i]==LUMP_NODES && failed_prefix)k=expect_lump(k,LUMP_NODES,1);
        k=expect_lump(k,order[i],0);
    }
    assert(k==read_count);
}
#endif

static void check(char *path){
    snapshot_t a,b,c,d;int slice;
    read_image(path);
    load_image(path,&a);
#ifdef AW_TEST_WRAP_FREAD
    read_count=0;read_logging=1;
#endif
    load_stream(path,&b,0,false);
    slice=temp_largest;
#ifdef AW_TEST_WRAP_FREAD
    read_logging=0;
    loadmodel=&mod_known[0];
    expect_staged_reads(!aw_direct_hull0 &&
        AW_PredictRenderPrefix(((dheader_t *)image)->lumps[LUMP_NODES].filelen/(int)sizeof(dnode_t)));
#endif
    load_stream(path,&c,image_bytes/3+7,false);
    load_stream(path,&d,0,true);
    if(!same(&a,&b) || !same(&a,&c) || !same(&a,&d)){fprintf(stderr,"%s: decoded Hunk differs\n",path);abort();}
    /* Temporary input is one bounded slice, never a whole staged lump. */
    assert(slice<=SLICE_LIMIT);
    assert(b.peak<=b.low+(int)sizeof(test_hunk_t)+slice);
    printf("%s low=%d stream_peak=%d slice=%d largest_staged_lump=%d direct_hull0=%d sky=%d\n",
        path,b.low,b.peak,slice,largest_staged_lump(),(int)aw_direct_hull0,sky_calls);
    free(a.bytes);free(b.bytes);free(c.bytes);free(d.bytes);
    free(a.models);free(b.models);free(c.models);free(d.models);
}

static void dump(char *path,const char *out){
    snapshot_t s;FILE *f;
    read_image(path);load_stream(path,&s,0,false);
    f=fopen(out,"wb");assert(f);
    assert(fwrite(&s.low,sizeof(s.low),1,f)==1 && fwrite(s.bytes,1,s.low,f)==(size_t)s.low);
    assert(fwrite(&s.known,sizeof(s.known),1,f)==1 && fwrite(s.models,sizeof(model_t),s.known,f)==(size_t)s.known);
    fclose(f);
    printf("%s low=%d stream_peak=%d temp_largest=%d temp_calls=%d direct_hull0=%d\n",
        path,s.low,s.peak,temp_largest,temp_calls,(int)aw_direct_hull0);
    free(s.bytes);free(s.models);
}

/* SCENE-LOAD-FAIL-FALLBACK-67: the report a failed streamed load leaves for the failed-load box (see Sys_Error above). */
static int test_hunk_used(void){return low+high+1;}   /* as aw_stream.c's: marks each section's end (never 0) */
static size_t bad_prefetch(const char *name,long offset,byte *out,size_t bytes){   /* dbg loadfail N lump's aid */
    (void)name;(void)offset;(void)out;return bytes+1;
}
static void expect_fail(const char *name,int kind,int lump,long bytes){
    if(fail_kind!=kind || fail.lump!=lump || fail.bytes!=bytes || strcmp(fail.file,name) || !fail.why[0] ||
       (lump>=0 && fail.offset!=((dheader_t *)image)->lumps[lump].fileofs) || (lump<0 && fail.offset!=-1)){
        fprintf(stderr,"failed load report: kind %d lump %d bytes %ld offset %ld file %s why %s; wanted kind %d lump %d "
            "bytes %ld\n",fail_kind,fail.lump,fail.bytes,fail.offset,fail.file,fail.why,kind,lump,bytes);abort();
    }
    fail_kind=-1;
}
/* As Mod_LoadModel streams a map: the decode marked as running (AW_MapDecode), then the streamed load. */
static void stream_fails(char *name,size_t (*copy)(const char *,long,byte *,size_t)){
    reset();expect_error=1;fail_kind=-1;aw_load_hunk_used=test_hunk_used;aw_load_prefetch_copy=copy;
    if(!setjmp(failure)){fail_model=Mod_FindName(name);AW_MapDecode(fail_model);AW_TryStreamBrush(fail_model);assert(0);}
    expect_error=0;aw_load_prefetch_copy=NULL;aw_load_hunk_used=NULL;
    if(aw_bsp_file){fclose(aw_bsp_file);aw_bsp_file=NULL;}
}
/* Malformed streamed input must stop before any pointer is made from it. */
static void malformed(char *path){
    static const int fields[]={LUMP_TEXTURES,LUMP_FACES,LUMP_NODES,LUMP_MARKSURFACES};
    char name[]="malformed.bsp";dheader_t *h;FILE *f;int i,ofs;
    read_image(path);
    for(i=0;i<(int)(sizeof(fields)/sizeof(fields[0]));i++){
        byte *copy=malloc(image_bytes);assert(copy);memcpy(copy,image,image_bytes);
        h=(dheader_t *)copy;ofs=h->lumps[fields[i]].fileofs;
        if(fields[i]==LUMP_TEXTURES)((int *)(copy+ofs))[1]=h->lumps[fields[i]].filelen;  /* miptex past lump */
        else if(fields[i]==LUMP_FACES)((dface_t *)(copy+ofs))->texinfo=(short)0xffff;  /* texinfo 65535 */
        else if(fields[i]==LUMP_NODES)((dnode_t *)(copy+ofs))[1].planenum=1<<30;       /* plane outside */
        else ((short *)(copy+ofs))[0]=(short)0xffff;                                   /* face 65535 */
        f=fopen(name,"wb");assert(f && fwrite(copy,1,image_bytes,f)==(size_t)image_bytes);fclose(f);
        stream_fails(name,NULL);
        expect_fail(name,AW_MAPFAIL_LUMP,fields[i],image_bytes);   /* bad lump N: the lump being decoded */
        free(copy);
    }
    /* a truncated file: a lump past the cut is a short read, named with where it starts */
    f=fopen(name,"wb");assert(f && fwrite(image,1,image_bytes/2,f)==(size_t)(image_bytes/2));fclose(f);
    stream_fails(name,NULL);
    assert(fail_kind==AW_MAPFAIL_SHORT && fail.lump>=0);
    expect_fail(name,AW_MAPFAIL_SHORT,fail.lump,image_bytes/2);
    /* an intact file whose first section read gets bad data (the aid of dbg loadfail N lump): bad lump, the first one
     * the decode reads (the vertexes) */
    f=fopen(name,"wb");assert(f && fwrite(image,1,image_bytes,f)==(size_t)image_bytes);fclose(f);
    stream_fails(name,bad_prefetch);
    expect_fail(name,AW_MAPFAIL_LUMP,LUMP_VERTEXES,image_bytes);
    /* a section's temporary memory not had: not enough memory, with the bytes it needed */
    temp_fail=1;stream_fails(name,NULL);
    assert(fail_kind==AW_MAPFAIL_MEMORY && fail.need>0 && fail.lump>=0 && !temp_fail);
    expect_fail(name,AW_MAPFAIL_MEMORY,fail.lump,image_bytes);
    /* another version, decoded from a file image: a bad header, no lump, the size not known on this path */
    {byte *copy=malloc(image_bytes);model_t *mod;assert(copy);memcpy(copy,image,image_bytes);((int *)copy)[0]=30;
     reset();expect_error=1;fail_kind=-1;
     if(!setjmp(failure)){mod=fail_model=Mod_FindName(name);COM_FileBase(mod->name,loadname);loadmodel=mod;
         mod->needload=NL_PRESENT;AW_MapDecode(mod);Mod_LoadBrushModel(mod,copy);assert(0);}
     expect_error=0;free(copy);
     expect_fail(name,AW_MAPFAIL_HEADER,-1,-1);}
    /* a fatal error with no map decode running is not a map's: nothing named, the loader untouched; a decode that
     * finished is not running either */
    {aw_mapfail_t other;
     assert(!AW_MapFailure(&other) && !other.file[0] && !other.why[0] && other.lump==-1);
     AW_MapDecode(&mod_known[0]);AW_MapDecode(NULL);assert(!AW_MapFailure(&other));}
    remove(name);
}

int main(int argc,char **argv){
    int i;void *want=(void *)(uintptr_t)0x200000000ULL;
#ifdef MAP_FIXED_NOREPLACE
    heap=mmap(want,HEAP_BYTES+4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
    if(heap==MAP_FAILED)
#endif
    heap=mmap(NULL,HEAP_BYTES+4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    assert(heap!=MAP_FAILED);
    r_notexture_mip=(texture_t *)(heap+HEAP_BYTES);
    if(argc>=4 && !strcmp(argv[1],"dump")){if(heap!=want)return 2;dump(argv[2],argv[3]);return 0;}
    assert(argc>=3 && !strcmp(argv[1],"check"));
    for(i=2;i<argc;i++)check(argv[i]);
    malformed(argv[2]);
    return 0;
}
