/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real alias decoder + real hunk/LRU cache. Synthetic data only. */
#include <assert.h>
#include <setjmp.h>
#include <limits.h>
#include "../engine/aga/src/zone.c"
static int fail_malloc;
void *__real_malloc(size_t n);
void *__wrap_malloc(size_t n){return fail_malloc?NULL:__real_malloc(n);}
#ifdef AW_ALIAS_TEST_LEGACY
void Mod_LoadAliasModel(model_t *,void *);
#else
void Mod_LoadAliasModel(model_t *,void *,int);
#endif
static union {long double align;byte bytes[2*1024*1024];} arena;
static byte raw[700000];
static jmp_buf failure;
static int expect_error,loads;
int r_pixbytes=1;
unsigned short d_8to16table[256];
static int integer(int v){return v;}static float real(float v){return v;}
int (*LittleLong)(int)=integer;float (*LittleFloat)(float)=real;
void Q_memset(void *p,int c,int n){memset(p,c,n);}
void Q_memcpy(void *d,void *s,int n){memcpy(d,s,n);}
void Q_strncpy(char *d,char *s,int n){strncpy(d,s,n);}
void Q_strcpy(char *d,char *s){strcpy(d,s);}
void Con_Printf(char *fmt,...){(void)fmt;}
void Cmd_AddCommand(char *name,xcommand_t fn){(void)name;(void)fn;}
void Sys_Error(char *fmt,...){assert(expect_error);longjmp(failure,1);}
static int make_alias(int mode){
    mdl_t *m=(mdl_t *)raw;byte *p;int i,j,grouped=mode==1,skinbytes;dtriangle_t *tri;daliasframe_t *f;
    memset(raw,0,sizeof raw);m->ident=IDPOLYHEADER;m->version=ALIAS_VERSION;
    m->numskins=1;m->skinwidth=mode==2?1024:256;m->skinheight=mode==2?480:256;
    skinbytes=m->skinwidth*m->skinheight;
    m->numverts=900;m->numtris=300;m->numframes=8;m->size=1;
    for(i=0;i<3;i++){m->scale[i]=.25;m->scale_origin[i]=-2;}
    p=raw+sizeof(*m);((daliasskintype_t *)p)->type=grouped?ALIAS_SKIN_GROUP:ALIAS_SKIN_SINGLE;p+=sizeof(daliasskintype_t);
    if(grouped){((daliasskingroup_t *)p)->numskins=2;p+=sizeof(daliasskingroup_t);
        for(i=0;i<2;i++){((daliasskininterval_t *)p)->interval=(i+1)*.2f;p+=sizeof(daliasskininterval_t);}}
    for(j=0;j<(grouped?2:1);j++){for(i=0;i<skinbytes;i++)p[i]=(byte)(i+j);p+=skinbytes;}
    p+=900*sizeof(stvert_t);tri=(dtriangle_t *)p;
    for(i=0;i<300;i++){tri[i].facesfront=1;tri[i].vertindex[0]=i*3;tri[i].vertindex[1]=i*3+1;tri[i].vertindex[2]=i*3+2;}
    p+=300*sizeof(*tri);
    for(j=0;j<8;j++){
        ((daliasframetype_t *)p)->type=grouped?ALIAS_GROUP:ALIAS_SINGLE;p+=sizeof(daliasframetype_t);
        if(grouped){((daliasgroup_t *)p)->numframes=2;p+=sizeof(daliasgroup_t);
            for(i=0;i<2;i++){((daliasinterval_t *)p)->interval=(i+1)*.2f;p+=sizeof(daliasinterval_t);}}
        for(i=0;i<(grouped?2:1);i++){f=(daliasframe_t *)p;strcpy(f->name,"synthetic");p+=sizeof(*f);
            memset(p,17+j+i,900*sizeof(trivertx_t));p+=900*sizeof(trivertx_t);}
    }
    assert(p-raw<sizeof raw);return (int)(p-raw);
}
static void decode(model_t *m,int bytes){
#ifdef AW_ALIAS_TEST_LEGACY
    (void)bytes;Mod_LoadAliasModel(m,raw);
#else
    Mod_LoadAliasModel(m,raw,bytes);
#endif
    loads++;
}
static void reset(void){
    memset(arena.bytes,0,sizeof arena.bytes);hunk_base=arena.bytes;hunk_size=sizeof arena.bytes;
    hunk_low_used=hunk_high_used=0;hunk_tempactive=false;hunk_tempmark=0;mainzone=NULL;
    memset(&cache_head,0,sizeof cache_head);Cache_Init();
    aw_cache_bytes=aw_cache_peak=0;aw_cache_preserve_free=0;AW_HeapAuditBegin();loads=0;
}
static void residency(void){
    model_t actor,body;cache_user_t cold={0},torch={0};int bytes,size,i,initial_loads,initial_evictions;
    memset(&actor,0,sizeof actor);memset(&body,0,sizeof body);reset();bytes=make_alias(0);
    decode(&actor,bytes);size=((cache_system_t *)actor.cache.data-1)->size;
    /* A hot actor at the bottom, old nonvisible data, a warm held torch,
     * and less tail room than a single decoded actor. The hot working set fits. */
    Cache_Alloc(&cold,hunk_size-size-40000-size/2-(int)sizeof(cache_system_t),"cold");
    Cache_Alloc(&torch,30000,"torch");Cache_Check(&actor.cache);Cache_Check(&torch);
    for(i=0;i<20;i++){
        if(!Cache_Check(&body.cache))decode(&body,bytes);
        if(!Cache_Check(&actor.cache))decode(&actor,bytes);
        assert(torch.data);Cache_Check(&torch);
        if(!i){initial_loads=loads;initial_evictions=aw_cache_evictions;}
    }
    printf("loads=%d evictions=%lu moves=%lu actor=%d body=%d held=%d\n",loads,aw_cache_evictions,aw_cache_moves,actor.cache.data!=NULL,body.cache.data!=NULL,torch.data!=NULL);
    fflush(stdout);
    assert(actor.cache.data && body.cache.data && torch.data);
    assert(loads==initial_loads && aw_cache_evictions==initial_evictions && hunk_low_used==0);
    assert(!cold.data);Cache_Flush();
}
static void formats(void){
    model_t m;int bytes,i;aliashdr_t *h;maliasgroup_t *group;maliasskindesc_t *skin;maliasskingroup_t *skins;
    reset();bytes=make_alias(1);memset(&m,0,sizeof m);decode(&m,bytes);
    h=m.cache.data;assert(h && !hunk_low_used);group=(maliasgroup_t *)((byte *)h+h->frames[0].frame);
    assert(group->numframes==2);assert(((trivertx_t *)((byte *)h+group->frames[1].frame))[0].v[0]==18);
    skin=(maliasskindesc_t *)((byte *)h+h->skindesc);skins=(maliasskingroup_t *)((byte *)h+skin->skin);
    assert(skins->numskins==2);for(i=0;i<256;i++)assert(*((byte *)h+skins->skindescs[1].skin+i)==(byte)(i+1));
    Cache_Flush();r_pixbytes=2;for(i=0;i<256;i++)d_8to16table[i]=(unsigned short)(i*257);
    memset(&m,0,sizeof m);decode(&m,bytes);h=m.cache.data;
    skin=(maliasskindesc_t *)((byte *)h+h->skindesc);skins=(maliasskingroup_t *)((byte *)h+skin->skin);
    for(i=0;i<256;i++)assert(((unsigned short *)((byte *)h+skins->skindescs[1].skin))[i]==d_8to16table[(byte)(i+1)]);
    Cache_Flush();r_pixbytes=1;fail_malloc=1;memset(&m,0,sizeof m);decode(&m,bytes);fail_malloc=0;
    assert(m.cache.data && !hunk_low_used);Cache_Flush();
    /* A decoded allocation above the external bound remains supported. */
    bytes=make_alias(2);memset(&m,0,sizeof m);decode(&m,bytes);
    assert(m.cache.data && !hunk_low_used);Cache_Flush();bytes=make_alias(1);
#ifndef AW_ALIAS_TEST_LEGACY
    /* Truncation/count overflow are rejected before staging or cache mutation. */
    expect_error=1;memset(&m,0,sizeof m);
    if(!setjmp(failure)){decode(&m,bytes-1);assert(0);}assert(!m.cache.data && !hunk_low_used);
    ((mdl_t *)raw)->numframes=INT_MAX;
    if(!setjmp(failure)){decode(&m,bytes);assert(0);}assert(!m.cache.data && !hunk_low_used);expect_error=0;
#endif
}
int main(void){residency();formats();return 0;}
