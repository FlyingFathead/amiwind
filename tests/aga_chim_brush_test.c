/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM brush loading through model.c (included below): the same section
 * decoders write into a CHIM arena instead of the Hunk.
 *
 *   miptex FILE...  Hunk decode (legacy) == arena image decode == arena
 *                   stream decode (one section per step, a legacy load
 *                   between two steps); no edge cache in the arena; the
 *                   decoded-size bound holds.
 *   refs FILE...    CHIM texture references resolved through the arena's
 *                   resolver, image == stream, bound holds.
 *   reject FILE     more than one submodel: refused before decoding.
 *   overflow FILE   an arena below the decoded size stops with an error.
 * Every comparison is of a relocation-independent dump (pointers as indexes).
 */
#include <assert.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdint.h>
#include "../engine/aga/src/model.c"

qboolean aw_loading_music=false;
static short same_short(short v){return v;}
static int same_long(int v){return v;}
static float same_float(float v){return v;}
short (*LittleShort)(short)=same_short;
int (*LittleLong)(int)=same_long;
float (*LittleFloat)(float)=same_float;
static texture_t notexture;
texture_t *r_notexture_mip=&notexture;

#define HEAP_BYTES (32*1024*1024)
static byte *heap;
static int low, high, temp_active, temp_mark, expect_error;
static jmp_buf failure;

void *Hunk_AllocName(int size,char *name){
    byte *p;
    assert(size>=0);size=16+((size+15)&~15);
    assert(low+high+size<=HEAP_BYTES);p=heap+low;low+=size;memset(p,0,size);return p+16;
}
int Hunk_LowMark(void){return low;}
void Hunk_FreeToLowMark(int mark){assert(mark>=0 && mark<=low);memset(heap+mark,0,low-mark);low=mark;}
void Hunk_FreeToHighMark(int mark){
    if(temp_active){temp_active=0;Hunk_FreeToHighMark(temp_mark);}
    assert(mark>=0 && mark<=high);high=mark;
}
int Hunk_HighMark(void){if(temp_active){temp_active=0;Hunk_FreeToHighMark(temp_mark);}return high;}
void *Hunk_TempAlloc(int size){
    size=(size+15)&~15;
    if(temp_active){Hunk_FreeToHighMark(temp_mark);temp_active=0;}
    temp_mark=Hunk_HighMark();high+=size+16;assert(low+high<=HEAP_BYTES);temp_active=1;
    return heap+HEAP_BYTES-high+16;
}
void Sys_Error(char *fmt,...){
    va_list args;
    if(!expect_error){va_start(args,fmt);vfprintf(stderr,fmt,args);va_end(args);fputc('\n',stderr);abort();}
    longjmp(failure,1);
}
void Con_Printf(char *fmt,...){}
void *Cache_Check(cache_user_t *c){return NULL;}
void Cache_Free(cache_user_t *c){abort();}
vec_t Length(vec3_t v){return (vec_t)sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]);}
void R_InitSky(texture_t *tx){}
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

/* ---------------------------------------------------------------- dump */

typedef struct { byte *data; size_t size, used; } dump_t;
static void put(dump_t *d,const void *p,size_t n){
    if(d->used+n>d->size){d->size=(d->used+n)*2+4096;d->data=realloc(d->data,d->size);assert(d->data);}
    memcpy(d->data+d->used,p,n);d->used+=n;
}
static void puti(dump_t *d,long v){put(d,&v,sizeof(v));}
static void putf(dump_t *d,float v){put(d,&v,sizeof(v));}
static long index_of(const void *base,const void *p,size_t unit){return p?(long)(((const byte *)p-(const byte *)base)/(long)unit):-1;}
static long texture_index(const model_t *m,const texture_t *t){
    int i;
    if(!t)return -1;
    if(t==r_notexture_mip)return -2;
    for(i=0;i<m->numtextures;i++)if(m->textures[i]==t)return i;
    return -3;
}
static void dump_texture(dump_t *d,const model_t *m,const texture_t *t,int refs){
    int pixels;
    if(!t){puti(d,-1);return;}
    if(refs){puti(d,(long)(intptr_t)t);return;}  /* shared: identity only */
    put(d,t->name,16);puti(d,t->width);puti(d,t->height);
    puti(d,t->anim_total);puti(d,t->anim_min);puti(d,t->anim_max);
    puti(d,texture_index(m,t->anim_next));puti(d,texture_index(m,t->alternate_anims));
    put(d,t->offsets,sizeof(t->offsets));
    pixels=t->width*t->height/64*85;put(d,t+1,pixels);
}
/* leafs: the decoded leaf count, from the header (AW_BrushFinish replaces
 * model->numleafs with the visible leaf count). */
static dump_t dump(const model_t *m,int leafs,int refs){
    dump_t d={0};int i,j;
    puti(&d,m->type);puti(&d,m->numframes);puti(&d,m->flags);
    for(i=0;i<3;i++){putf(&d,m->mins[i]);putf(&d,m->maxs[i]);}
    putf(&d,m->radius);puti(&d,m->firstmodelsurface);puti(&d,m->nummodelsurfaces);puti(&d,m->numleafs);
    puti(&d,m->numsubmodels);put(&d,m->submodels,m->numsubmodels*sizeof(dmodel_t));
    puti(&d,m->numvertexes);put(&d,m->vertexes,m->numvertexes*sizeof(mvertex_t));
    puti(&d,m->numedges);put(&d,m->edges,(m->numedges+1)*sizeof(medge_t));
    puti(&d,m->numsurfedges);put(&d,m->surfedges,m->numsurfedges*sizeof(int));
    puti(&d,m->numplanes);
    for(i=0;i<m->numplanes;i++){put(&d,m->planes[i].normal,12);putf(&d,m->planes[i].dist);puti(&d,m->planes[i].type);puti(&d,m->planes[i].signbits);}
    puti(&d,m->numtextures);
    for(i=0;i<m->numtextures;i++)dump_texture(&d,m,m->textures[i],refs);
    puti(&d,m->numtexinfo);
    for(i=0;i<m->numtexinfo;i++){put(&d,m->texinfo[i].vecs,sizeof(m->texinfo[i].vecs));putf(&d,m->texinfo[i].mipadjust);
        puti(&d,m->texinfo[i].flags);puti(&d,texture_index(m,m->texinfo[i].texture));}
    puti(&d,m->numsurfaces);
    for(i=0;i<m->numsurfaces;i++){const msurface_t *s=&m->surfaces[i];
        puti(&d,index_of(m->planes,s->plane,sizeof(mplane_t)));puti(&d,s->firstedge);puti(&d,s->numedges);puti(&d,s->flags);
        put(&d,s->texturemins,4);put(&d,s->extents,4);puti(&d,index_of(m->texinfo,s->texinfo,sizeof(mtexinfo_t)));
        put(&d,s->styles,MAXLIGHTMAPS);puti(&d,s->samples?(long)(s->samples-m->lightdata):-1);}
    puti(&d,m->nummarksurfaces);
    for(i=0;i<m->nummarksurfaces;i++)puti(&d,index_of(m->surfaces,m->marksurfaces[i],sizeof(msurface_t)));
    for(i=0;i<leafs;i++){const mleaf_t *l=&m->leafs[i];
        puti(&d,l->contents);put(&d,l->minmaxs,12);puti(&d,index_of(m->nodes,l->parent,sizeof(mnode_t)));
        puti(&d,l->compressed_vis?(long)(l->compressed_vis-m->visdata):-1);
        puti(&d,l->firstmarksurface?index_of(m->marksurfaces,l->firstmarksurface,sizeof(msurface_t *)):-1);
        puti(&d,l->nummarksurfaces);put(&d,l->ambient_sound_level,NUM_AMBIENTS);}
    puti(&d,m->numnodes);
    for(i=0;i<m->numnodes;i++){const mnode_t *n=&m->nodes[i];
        puti(&d,n->contents);put(&d,n->minmaxs,12);puti(&d,index_of(m->nodes,n->parent,sizeof(mnode_t)));
        puti(&d,index_of(m->planes,n->plane,sizeof(mplane_t)));
        for(j=0;j<2;j++){const mnode_t *c=n->children[j];
            puti(&d,c->contents<0?-1-index_of(m->leafs,c,sizeof(mleaf_t)):index_of(m->nodes,c,sizeof(mnode_t)));}
        puti(&d,n->firstsurface);puti(&d,n->numsurfaces);}
    puti(&d,m->numclipnodes);put(&d,m->clipnodes,m->numclipnodes*sizeof(dclipnode_t));
    for(i=0;i<MAX_MAP_HULLS;i++){const hull_t *h=&m->hulls[i];
        puti(&d,h->planes==m->planes);puti(&d,h->firstclipnode);puti(&d,h->lastclipnode);
        put(&d,h->clip_mins,12);put(&d,h->clip_maxs,12);
        if(h->clipnodes && h->lastclipnode>=0)put(&d,h->clipnodes,(h->lastclipnode+1)*sizeof(dclipnode_t));}
    puti(&d,m->lightdata!=NULL);puti(&d,m->visdata!=NULL);
    puti(&d,m->entities?(long)strlen(m->entities):-1);if(m->entities)put(&d,m->entities,strlen(m->entities));
    return d;
}
static int same(const dump_t *a,const dump_t *b){return a->used==b->used && !memcmp(a->data,b->data,a->used);}

/* ---------------------------------------------------------------- loads */

static byte *image;static long image_bytes;
static void read_image(const char *path){
    FILE *f=fopen(path,"rb");assert(f);
    fseek(f,0,SEEK_END);image_bytes=ftell(f);fseek(f,0,SEEK_SET);
    free(image);image=malloc(image_bytes);assert(image && fread(image,1,image_bytes,f)==(size_t)image_bytes);fclose(f);
}
static int header_leafs(void){dheader_t h;assert(AW_BrushHeader(&h,image,image_bytes));return h.lumps[LUMP_LEAFS].filelen/sizeof(dleaf_t);}

static texture_t shared[8];
static int resolved;
static texture_t *resolve(void *context,int id){
    assert(context==(void *)shared);
    assert(id>=0 && id<8);resolved++;return &shared[id];
}

static byte slice[AW_BRUSH_SLICE_BYTES];
static void arena_init(aw_brush_arena_t *a,int size,int refs){
    memset(a,0,sizeof(*a));a->base=calloc(1,size?size:1);a->size=size;
    a->slice=slice;a->slice_bytes=sizeof(slice);
    if(refs){a->texture=resolve;a->context=shared;}
}
static dump_t load_hunk(void){
    byte *copy=malloc(image_bytes);model_t *mod;dump_t d;
    memcpy(copy,image,image_bytes);low=high=0;memset(mod_known,0,sizeof(mod_known));mod_numknown=0;
    mod=Mod_FindName("hunk.bsp");COM_FileBase(mod->name,loadname);loadmodel=mod;mod->needload=NL_PRESENT;
    Mod_LoadBrushModel(mod,copy);
    assert(mod->edgecache || !mod->numedges);
    d=dump(mod,header_leafs(),0);free(copy);return d;
}
static dump_t load_image(int refs,int *used){
    aw_brush_arena_t a;model_t mod;dheader_t h;byte *copy=malloc(image_bytes);dump_t d;int bound;
    memcpy(copy,image,image_bytes);assert(AW_BrushHeader(&h,copy,image_bytes));
    bound=AW_BrushBound(&h,refs);assert(bound>0);arena_init(&a,bound,refs);
    memset(&mod,0,sizeof(mod));strcpy(mod.name,"chim:image");resolved=0;
    assert(AW_BrushImage(&mod,copy,image_bytes,&a));
    assert(!mod.edgecache && !mod.edgecache_count && mod.type==mod_brush && mod.needload==NL_PRESENT);
    assert(a.used<=a.size);*used=a.used;
    printf("bound=%d used=%d ",bound,a.used);
    d=dump(&mod,header_leafs(),refs);free(copy);/* arena kept: dump copied */
    return d;
}
static dump_t load_stream(const char *path,int refs,int interleave){
    aw_brush_arena_t a;aw_brush_stream_t s;model_t mod;dheader_t h;FILE *f;dump_t d;int steps=0,bound;
    byte *before;
    assert(AW_BrushHeader(&h,image,image_bytes));bound=AW_BrushBound(&h,refs);arena_init(&a,bound,refs);
    memset(&mod,0,sizeof(mod));strcpy(mod.name,"chim:stream");
    /* The image sits 1000 bytes into a larger "pack" file. */
    f=fopen("pack.bin","w+b");assert(f);
    before=calloc(1,1000);fwrite(before,1,1000,f);fwrite(image,1,image_bytes,f);fwrite(before,1,1000,f);free(before);
    assert(AW_BrushStreamBegin(&s,&mod,f,1000,image_bytes,&a));
    while(!AW_BrushStreamStep(&s)){
        steps++;
        /* A legacy Hunk load between two steps must not disturb the stream. */
        if(interleave && steps==7){dump_t x=load_hunk();free(x.data);}
        /* Other reads of the same file between steps move its position. */
        fseek(f,0,SEEK_SET);
    }
    assert(steps==AW_BRUSH_SECTIONS-1 && AW_BrushStreamStep(&s));
    assert(!aw_brush_arena && !aw_bsp_file && loadmodel!=&mod);
    assert(!mod.edgecache && a.used<=a.size);
    d=dump(&mod,header_leafs(),refs);fclose(f);return d;
}

int main(int argc,char **argv){
    int i,used;
    heap=calloc(1,HEAP_BYTES);assert(heap);
    if(argc<3)return 2;
    for(i=2;i<argc;i++){
        read_image(argv[i]);
        if(!strcmp(argv[1],"miptex")){
            dump_t h=load_hunk(),a=load_image(0,&used),s=load_stream(argv[i],0,1);
            assert(same(&h,&a));assert(same(&a,&s));
            printf("%s ok\n",argv[i]);
        }else if(!strcmp(argv[1],"refs")){
            dump_t a=load_image(1,&used),s;
            assert(resolved>0);
            s=load_stream(argv[i],1,0);
            assert(same(&a,&s));
            printf("%s ok\n",argv[i]);
        }else if(!strcmp(argv[1],"reject")){
            dheader_t h;aw_brush_arena_t a;model_t mod;
            assert(!AW_BrushHeader(&h,image,image_bytes));
            arena_init(&a,1<<20,0);memset(&mod,0,sizeof(mod));
            assert(!AW_BrushImage(&mod,image,image_bytes,&a) && !a.used);
            /* A header shorter than its lumps is refused too. */
            assert(!AW_BrushHeader(&h,image,image_bytes/2));
            printf("%s rejected\n",argv[i]);
        }else if(!strcmp(argv[1],"dag")){
            /* A placed model's point hull with 40 chained pieces: decoded
             * into hull 0 only, in time linear in its nodes (Mod_SetParent
             * would visit 6^40 paths; the first real Balmora run hung so). */
            dheader_t h;aw_brush_arena_t a;model_t mod;int k,n,inside;
            assert(AW_BrushHeader(&h,image,image_bytes));
            arena_init(&a,AW_BrushBound(&h,1),1);a.point_hull_only=1;
            memset(&mod,0,sizeof(mod));strcpy(mod.name,"chim:chain");
            assert(AW_BrushImage(&mod,image,image_bytes,&a));
            assert(!mod.nodes && !mod.numnodes && mod.hulls[0].clipnodes && mod.hulls[0].lastclipnode==239);
            for(k=0;k<80;k++){
                vec3_t p;hull_t *hu=&mod.hulls[0];
                p[0]=(float)(k%40)*100+(k<40?24:70);p[1]=24;p[2]=24;
                n=0;while(n>=0){
                    dclipnode_t *c=&hu->clipnodes[n];mplane_t *pl=&hu->planes[c->planenum];
                    n=c->children[DotProduct(p,pl->normal)-pl->dist<0];
                }
                inside=k<40;
                assert(n==(inside?CONTENTS_SOLID:CONTENTS_EMPTY));
            }
            printf("%s chain decoded\n",argv[i]);
        }else if(!strcmp(argv[1],"overflow")){
            dheader_t h;aw_brush_arena_t a;model_t mod;
            assert(AW_BrushHeader(&h,image,image_bytes));
            arena_init(&a,AW_BrushBound(&h,0)/2,0);memset(&mod,0,sizeof(mod));strcpy(mod.name,"chim:small");
            expect_error=1;
            if(!setjmp(failure)){AW_BrushImage(&mod,image,image_bytes,&a);abort();}
            expect_error=0;aw_brush_arena=NULL;
            assert(a.used<=a.size);
            printf("%s overflow stopped\n",argv[i]);
        }else return 2;
    }
    return 0;
}
