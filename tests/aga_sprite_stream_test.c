/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include <limits.h>
#include <setjmp.h>
#include <stdarg.h>

extern void Mod_LoadSpriteModel(model_t *,void *);
extern int Mod_TryStreamSprite(model_t *);
extern model_t *loadmodel;
extern char loadname[32];

int r_pixbytes=1;
unsigned short d_8to16table[256];
static jmp_buf failure;
static int expect_error;
static byte raw[512];
static void *hunk_blocks[256];
static int hunk_block_count;
static size_t raw_bytes,member_bytes,physical_member_bytes;
static int add_pack_suffix=1;
static const char *container_name="sprite-stream-pack.bin";
static const byte prefix[13]="pack-prefix!";
static const byte suffix[11]="pack-suffix";

static int identity_long(int n){return n;}
static float identity_float(float n){return n;}
int (*LittleLong)(int)=identity_long;
float (*LittleFloat)(float)=identity_float;

/* Hunk allocations live through each comparison/error assertion, then the
 * fixture models its end-of-load cleanup so LeakSanitizer sees no test leaks. */
static void test_hunk_reset(void){
    while(hunk_block_count>0)free(hunk_blocks[--hunk_block_count]);
}
void *Hunk_AllocName(int n,char *name){
    void *block;assert(n>0&&hunk_block_count<(int)(sizeof(hunk_blocks)/sizeof(hunk_blocks[0])));
    block=calloc(1,(size_t)n);assert(block);hunk_blocks[hunk_block_count++]=block;return block;
}
void Q_memset(void *p,int value,int n){memset(p,value,(size_t)n);}
void Q_memcpy(void *p,void *q,int n){memcpy(p,q,(size_t)n);}
void Sys_Error(char *fmt,...){assert(expect_error);longjmp(failure,1);}
int COM_FOpenFile(char *name,FILE **file){
    if(strcmp(name,"progs/test.spr")){*file=NULL;return -1;}
    *file=fopen(container_name,"rb");if(!*file)return -1;
    if(fseek(*file,sizeof(prefix),SEEK_SET)){fclose(*file);*file=NULL;return -1;}
    return (int)member_bytes;
}
void COM_FileBase(char *path,char *out){
    const char *base=strrchr(path,'/');int n;base=base?base+1:path;
    n=(int)strlen(base);if(n>4)n-=4;if(n>31)n=31;memcpy(out,base,(size_t)n);out[n]=0;
}

static void put(byte **p,const void *value,size_t n){memcpy(*p,value,n);*p+=n;}
static size_t make_sprite(void){
    byte *p=raw;dsprite_t header;dspriteframetype_t type;dspriteframe_t frame;
    dspritegroup_t group;dspriteinterval_t interval;byte pixels[4];int i;
    memset(&header,0,sizeof(header));header.ident=IDSPRITEHEADER;header.version=SPRITE_VERSION;
    header.type=SPR_VP_PARALLEL;header.width=3;header.height=2;header.numframes=2;
    header.beamlength=1.25f;header.synctype=ST_SYNC;put(&p,&header,sizeof(header));
    type.type=SPR_SINGLE;put(&p,&type,sizeof(type));
    frame.origin[0]=-2;frame.origin[1]=7;frame.width=2;frame.height=2;put(&p,&frame,sizeof(frame));
    pixels[0]=1;pixels[1]=2;pixels[2]=3;pixels[3]=4;put(&p,pixels,4);
    type.type=SPR_GROUP;put(&p,&type,sizeof(type));group.numframes=2;put(&p,&group,sizeof(group));
    interval.interval=.25f;put(&p,&interval,sizeof(interval));interval.interval=.75f;put(&p,&interval,sizeof(interval));
    frame.origin[0]=3;frame.origin[1]=9;frame.width=4;frame.height=1;put(&p,&frame,sizeof(frame));
    pixels[0]=5;pixels[1]=6;pixels[2]=7;pixels[3]=8;put(&p,pixels,4);
    frame.origin[0]=-4;frame.origin[1]=12;frame.width=2;frame.height=2;put(&p,&frame,sizeof(frame));
    for(i=0;i<4;i++)pixels[i]=(byte)(9+i);put(&p,pixels,4);
    return (size_t)(p-raw);
}

static void write_member(const byte *bytes,size_t declared,size_t physical){
    FILE *file=fopen(container_name,"wb");assert(file);
    assert(fwrite(prefix,1,sizeof(prefix),file)==sizeof(prefix));
    assert(fwrite(bytes,1,physical,file)==physical);
    if(add_pack_suffix)assert(fwrite(suffix,1,sizeof(suffix),file)==sizeof(suffix));
    assert(fclose(file)==0);member_bytes=declared;physical_member_bytes=physical;
}

static void compare_frame(const mspriteframe_t *a,const mspriteframe_t *b){
    size_t count=(size_t)a->width*(size_t)a->height*(size_t)r_pixbytes;
    assert(a->width==b->width&&a->height==b->height);
    assert(a->up==b->up&&a->down==b->down&&a->left==b->left&&a->right==b->right);
    assert(!memcmp(a->pixels,b->pixels,count));
}

static void compare_models(model_t *a,model_t *b){
    msprite_t *x=(msprite_t *)a->cache.data,*y=(msprite_t *)b->cache.data;
    int i,j;
    assert(a->type==b->type&&a->synctype==b->synctype&&a->numframes==b->numframes);
    assert(a->radius==b->radius);
    for(i=0;i<3;i++)assert(a->mins[i]==b->mins[i]&&a->maxs[i]==b->maxs[i]);
    assert(x->type==y->type&&x->maxwidth==y->maxwidth&&x->maxheight==y->maxheight);
    assert(x->numframes==y->numframes&&x->beamlength==y->beamlength);
    for(i=0;i<x->numframes;i++){
        assert(x->frames[i].type==y->frames[i].type);
        if(x->frames[i].type==SPR_SINGLE)compare_frame(x->frames[i].frameptr,y->frames[i].frameptr);
        else{
            mspritegroup_t *gx=(mspritegroup_t *)x->frames[i].frameptr;
            mspritegroup_t *gy=(mspritegroup_t *)y->frames[i].frameptr;
            assert(gx->numframes==gy->numframes);
            for(j=0;j<gx->numframes;j++){
                assert(gx->intervals[j]==gy->intervals[j]);
                compare_frame(gx->frames[j],gy->frames[j]);
            }
        }
    }
}

static void expect_stream_error(size_t declared,size_t physical){
    model_t mod;int saved_suffix=add_pack_suffix;
    memset(&mod,0,sizeof(mod));strcpy(mod.name,"progs/test.spr");
    add_pack_suffix=0;write_member(raw,declared,physical);expect_error=1;
    if(!setjmp(failure)){Mod_TryStreamSprite(&mod);assert(0 && "malformed sprite accepted");}
    expect_error=0;add_pack_suffix=saved_suffix;test_hunk_reset();
}

static size_t make_odd_sprite(void){
    byte *p=raw;dsprite_t header;dspriteframetype_t type;dspriteframe_t frame;
    dspritegroup_t group;dspriteinterval_t interval;byte pixels[4]={10,20,30,40};int i;
    memset(&header,0,sizeof(header));header.ident=IDSPRITEHEADER;header.version=SPRITE_VERSION;
    header.type=SPR_VP_PARALLEL;header.width=4;header.height=2;header.numframes=1;
    header.beamlength=.5f;header.synctype=ST_SYNC;put(&p,&header,sizeof(header));
    type.type=SPR_GROUP;put(&p,&type,sizeof(type));group.numframes=2;put(&p,&group,sizeof(group));
    interval.interval=.25f;put(&p,&interval,sizeof(interval));interval.interval=.75f;put(&p,&interval,sizeof(interval));
    frame.origin[0]=-2;frame.origin[1]=3;frame.width=3;frame.height=1;put(&p,&frame,sizeof(frame));
    put(&p,pixels,3);
    frame.origin[0]=1;frame.origin[1]=4;frame.width=2;frame.height=2;put(&p,&frame,sizeof(frame));
    for(i=0;i<4;i++)pixels[i]=(byte)(41+i);put(&p,pixels,4);
    return (size_t)(p-raw);
}

static void check_streamed_odd_sprite(void){
    int bpp,i;size_t length=make_odd_sprite();
    for(bpp=1;bpp<=2;bpp++){
        model_t mod;msprite_t *sprite;mspritegroup_t *group;mspriteframe_t *frame;
        memset(&mod,0,sizeof(mod));strcpy(mod.name,"progs/test.spr");r_pixbytes=bpp;
        write_member(raw,length,length);assert(Mod_TryStreamSprite(&mod)==1);
        sprite=(msprite_t *)mod.cache.data;group=(mspritegroup_t *)sprite->frames[0].frameptr;
        assert(mod.type==mod_sprite&&mod.numframes==1&&sprite->numframes==1);
        assert(sprite->frames[0].type==SPR_GROUP&&group->numframes==2);
        assert(group->intervals[0]==.25f&&group->intervals[1]==.75f);
        frame=group->frames[0];assert(frame->width==3&&frame->height==1);
        assert(frame->up==3&&frame->down==2&&frame->left==-2&&frame->right==1);
        for(i=0;i<3;i++){
            if(bpp==1)assert(frame->pixels[i]==(byte)(10+10*i));
            else {unsigned short actual;memcpy(&actual,frame->pixels+i*sizeof(actual),sizeof(actual));
                assert(actual==d_8to16table[10+10*i]);}
        }
        frame=group->frames[1];assert(frame->width==2&&frame->height==2);
        assert(frame->up==4&&frame->down==2&&frame->left==1&&frame->right==3);
        for(i=0;i<4;i++){
            if(bpp==1)assert(frame->pixels[i]==(byte)(41+i));
            else {unsigned short actual;memcpy(&actual,frame->pixels+i*sizeof(actual),sizeof(actual));
                assert(actual==d_8to16table[41+i]);}
        }
        test_hunk_reset();
    }
}

int main(void){
    size_t length;int i;model_t generic,streamed;byte malformed[512];
    length=make_sprite();raw_bytes=length;
    for(i=0;i<256;i++)d_8to16table[i]=(unsigned short)(i*257U);
    write_member(raw,length,length);
    for(r_pixbytes=1;r_pixbytes<=2;r_pixbytes++){
        memset(&generic,0,sizeof(generic));memset(&streamed,0,sizeof(streamed));
        strcpy(generic.name,"progs/test.spr");strcpy(streamed.name,"progs/test.spr");
        strcpy(loadname,"test");loadmodel=&generic;Mod_LoadSpriteModel(&generic,raw);
        write_member(raw,length,length);assert(Mod_TryStreamSprite(&streamed)==1);
        assert(streamed.needload==0);compare_models(&generic,&streamed);
        test_hunk_reset();
    }
    /* The member starts after a prefix and ends before unrelated PAK bytes. */
    assert(physical_member_bytes==raw_bytes);
    /* Odd pixels inside a group are stream-tested separately; the generic
     * equivalence input stays word-aligned for its legacy cursor. */
    check_streamed_odd_sprite();
    length=make_sprite();raw_bytes=length;r_pixbytes=1;
    /* A non-IDSP keeps the generic fallback available. */
    memcpy(malformed,raw,length);memcpy(malformed,"NOPE",4);write_member(malformed,length,length);
    memset(&streamed,0,sizeof(streamed));strcpy(streamed.name,"progs/test.spr");
    assert(Mod_TryStreamSprite(&streamed)==0);
    /* Physical short read, declared trailing byte, and arithmetic overflow fail closed. */
    expect_stream_error(length,length-1);
    memcpy(malformed,raw,length);malformed[length]=0;write_member(malformed,length+1,length+1);
    memset(&streamed,0,sizeof(streamed));strcpy(streamed.name,"progs/test.spr");expect_error=1;
    if(!setjmp(failure)){Mod_TryStreamSprite(&streamed);assert(0 && "trailing byte accepted");}
    expect_error=0;test_hunk_reset();
    memcpy(malformed,raw,length);*(int *)(malformed+48)=INT_MAX;*(int *)(malformed+52)=2;
    memcpy(raw,malformed,length);expect_stream_error(length,length);
    length=make_sprite();*(int *)(raw+64)=INT_MAX;expect_stream_error(length,length);
    length=make_sprite();*(int *)(raw+44)=INT_MIN;expect_stream_error(length,length);
    length=make_sprite();*(int *)(raw+40)=INT_MAX;expect_stream_error(length,length);
    length=make_sprite();*(unsigned int *)(raw+28)=0x7fc00000U;expect_stream_error(length,length);
    length=make_sprite();*(unsigned int *)(raw+12)=0x7f800000U;expect_stream_error(length,length);
    assert(hunk_block_count==0);
    remove(container_name);
    return 0;
}
