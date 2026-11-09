/* SPDX-License-Identifier: GPL-2.0-or-later
 * Actor skin tiles (IMAGE-BIGGER-THAN-ORIGINAL-62, method B): a model whose skin is a table of tile numbers into
 * progs/tiles/<hex>-<chunk>.awtp is rebuilt by AW_TiledSkinExpand into exactly the model with its pixels inline,
 * also when its shape is shared too (either expansion first); the stream loader leaves it to the file loader; a
 * missing or short chunk and a bad name are refused. Synthetic data, plus (optional) a real tiled payload:
 *   aga_tiled_skin_test TILED_ID1 ORIGINAL_ID1 LIST
 * LIST names id1-relative models (one a line) stored tiled under TILED_ID1 and whole under ORIGINAL_ID1. Each is
 * rebuilt and compared byte for byte, and the time of reading the whole original file is set against reading the
 * stored model and rebuilding it (this machine's file cache: a host measure of the reader, not an Amiga one). */
#define main old_residency_main
#include "aga_alias_residency_test.c"
#undef main
#include <time.h>
qboolean aw_loading_music=false;
int Mod_TryStreamAlias(model_t *);
int AW_AliasSkinEnd(const byte *raw,int bytes);
int AW_SharedShapeAt(const byte *raw,int bytes);
byte *AW_SharedShapeExpand(byte *stored,int *bytes);
int AW_TiledSkinTiles(const byte *raw,int bytes);
byte *AW_TiledSkinExpand(byte *stored,int *bytes);
static const char *member_path="tiled-skin-member.bin",*chunk_path[2]={"tiled-skin-chunk0.bin","tiled-skin-chunk1.bin"},
                  *shape_path="tiled-skin-shape.bin";
static const char *tiled_root;
static int member_size,chunk_size[2],shape_size,chunks_on=2;
static char shape_name[64];
static byte stored[900000],tiles[300000];
int COM_FOpenFile(char *name,FILE **f){
    char path[1024];
    if(!strcmp(name,"progs/stream.mdl")){*f=fopen(member_path,"rb");return *f?member_size:-1;}
    if(tiled_root && !strncmp(name,"progs/tiles/",12)){
        snprintf(path,sizeof path,"%s/%s",tiled_root,name);*f=fopen(path,"rb");
        if(!*f)return -1;fseek(*f,0,SEEK_END);{long n=ftell(*f);fseek(*f,0,SEEK_SET);return (int)n;}
    }
    if(!strcmp(name,"progs/tiles/0123456789abcdef-00.awtp") && chunks_on>0){*f=fopen(chunk_path[0],"rb");return *f?chunk_size[0]:-1;}
    if(!strcmp(name,"progs/tiles/0123456789abcdef-01.awtp") && chunks_on>1){*f=fopen(chunk_path[1],"rb");return *f?chunk_size[1]:-1;}
    if(shape_name[0] && !strcmp(name,shape_name)){*f=fopen(shape_path,"rb");return *f?shape_size:-1;}
    *f=NULL;return -1;
}
void COM_FileBase(char *name,char *out){strcpy(out,"stream");}
static void write_file(const char *path,const byte *data,int bytes){
    FILE *f=fopen(path,"wb");assert(f);assert(fwrite(data,1,(size_t)bytes,f)==(size_t)bytes);assert(!fclose(f));
}
static void le32(byte *p,unsigned int v){p[0]=v&255;p[1]=(v>>8)&255;p[2]=(v>>16)&255;p[3]=(v>>24)&255;}
/* The stored form tools/payload_share.py writes for SRC: its distinct tiles in chunk 0 (and the same again in chunk
 * 1, which every odd tile slot uses), "AWTL", the hex name, the pixel and tile counts, the u32 numbers. */
static int tile_form(const byte *src,int bytes,const char *hex){
    const mdl_t *m=(const mdl_t *)src;int head=(int)sizeof(mdl_t),w=m->skinwidth,h=m->skinheight,n=(w/16)*(h/16),
        distinct=0,i,j,r,rest=bytes-head-4-w*h;byte cut[256];
    memcpy(stored,src,head);memcpy(stored+head,"AWTL",4);memcpy(stored+head+4,hex,16);le32(stored+head+20,w*h);le32(stored+head+24,n);
    for(i=0;i<n;i++){
        for(r=0;r<16;r++)memcpy(cut+r*16,src+head+4+((i/(w/16))*16+r)*w+(i%(w/16))*16,16);
        for(j=0;j<distinct && memcmp(tiles+j*256,cut,256);j++);
        if(j==distinct)memcpy(tiles+(distinct++)*256,cut,256);
        le32(stored+head+28+4*i,(i&1)?65536u+j:(unsigned int)j);
    }
    memcpy(stored+head+28+4*n,src+head+4+w*h,rest);
    write_file(chunk_path[0],tiles,distinct*256);chunk_size[0]=distinct*256;
    write_file(chunk_path[1],tiles,distinct*256);chunk_size[1]=distinct*256;
    return head+28+4*n+rest;
}
static byte *copy_of(const byte *src,int n){byte *c=malloc(n);assert(c);memcpy(c,src,n);return c;}
static void synthetic(void){
    int bytes=make_alias(0),n,full;byte *c;model_t m;const mdl_t *h=(const mdl_t *)raw;
    n=tile_form(raw,bytes,"0123456789abcdef");
    assert(n<bytes && AW_TiledSkinTiles(stored,n)==(h->skinwidth/16)*(h->skinheight/16) && AW_TiledSkinTiles(raw,bytes)<0);
    assert(AW_AliasSkinEnd(stored,n)==(int)sizeof(mdl_t)+4+24+4*AW_TiledSkinTiles(stored,n));
    full=n;c=AW_TiledSkinExpand(copy_of(stored,n),&full);
    assert(c && full==bytes && !memcmp(c,raw,bytes));free(c);
    /* the stream loader leaves a tiled skin to the file loader */
    write_file(member_path,stored,n);member_size=n;
    memset(&m,0,sizeof m);reset();strcpy(m.name,"progs/stream.mdl");
    assert(!Mod_TryStreamAlias(&m) && !m.cache.data);
    /* with its shape shared as well: the shape reference follows the table; both orders rebuild the model */
    {
        int at=AW_AliasSkinEnd(stored,n),st=h->numverts*12,tri=h->numtris*16,rest=n-at-st-tri,s;byte *both=malloc(n);
        assert(both && rest>=0);
        memcpy(both,stored,at);memcpy(both+at,"AWSH",4);memcpy(both+at+4,"fedcba9876543210",16);le32(both+at+20,st);le32(both+at+24,tri);
        memcpy(both+at+28,stored+at+st+tri,rest);s=at+28+rest;
        write_file(shape_path,stored+at,st+tri);shape_size=st+tri;strcpy(shape_name,"progs/shapes/fedcba9876543210.aws1");
        assert(AW_SharedShapeAt(both,s)==at);
        full=s;c=AW_SharedShapeExpand(copy_of(both,s),&full);assert(c);c=AW_TiledSkinExpand(c,&full);
        assert(c && full==bytes && !memcmp(c,raw,bytes));free(c);
        full=s;c=AW_TiledSkinExpand(copy_of(both,s),&full);assert(c);c=AW_SharedShapeExpand(c,&full);
        assert(c && full==bytes && !memcmp(c,raw,bytes));free(c);free(both);shape_name[0]=0;
    }
    /* refusals: a missing chunk, a short chunk, a name that is not lowercase hex */
    chunks_on=1;full=n;assert(!AW_TiledSkinExpand(copy_of(stored,n),&full));chunks_on=2;
    write_file(chunk_path[1],tiles,256);full=n;assert(!AW_TiledSkinExpand(copy_of(stored,n),&full));
    n=tile_form(raw,bytes,"0123456789ABCDEF");full=n;assert(!AW_TiledSkinExpand(copy_of(stored,n),&full));
    remove(member_path);remove(chunk_path[0]);remove(chunk_path[1]);remove(shape_path);
}
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
static int read_all(const char *path,byte *out,int cap){
    FILE *f=fopen(path,"rb");int n;assert(f);n=(int)fread(out,1,cap,f);assert(!ferror(f) && feof(f));fclose(f);return n;
}
static void real_payload(const char *tiled,const char *original,const char *list){
    char name[512],path[1024];FILE *l=fopen(list,"r");int count=0,n,o,full;double whole=0,rebuilt=0,t,worst=0;byte *c;
    static byte orig[900000];
    assert(l);tiled_root=tiled;
    while(fscanf(l,"%511s",name)==1){
        snprintf(path,sizeof path,"%s/%s",original,name);
        t=now();o=read_all(path,orig,sizeof orig);whole+=now()-t;
        snprintf(path,sizeof path,"%s/%s",tiled,name);
        t=now();n=read_all(path,stored,sizeof stored);
        if(AW_TiledSkinTiles(stored,n)<0){fprintf(stderr,"not tiled: %s\n",name);assert(0);}
        full=n;c=AW_TiledSkinExpand(copy_of(stored,n),&full);t=now()-t;rebuilt+=t;if(t>worst)worst=t;
        if(!c || full!=o || memcmp(c,orig,o)){fprintf(stderr,"differs: %s\n",name);assert(0);}
        free(c);count++;
    }
    fclose(l);
    printf("tiled-skin real: %d models byte-identical; whole file %.3f ms a model, stored + tiles %.3f ms a model "
           "(worst %.3f ms); 20 actors %.1f ms against %.1f ms (%+.1f %%)\n",count,whole*1e3/count,rebuilt*1e3/count,
           worst*1e3,20*whole*1e3/count,20*rebuilt*1e3/count,100*(rebuilt-whole)/whole);
}
int main(int argc,char **argv){
    synthetic();
    if(argc==4)real_payload(argv[1],argv[2],argv[3]);
    printf("tiled-skin: file loader rebuild byte-identical (with and without a shared shape), stream loader defers, refusals named\n");
    return 0;
}
