/* SPDX-License-Identifier: GPL-2.0-or-later
 * Decode a synthetic MDL with the production loader. Freed staging bytes are
 * poisoned so the cache copy cannot accidentally retain a dangling pointer. */
#include "quakedef.h"
#include <assert.h>
void Mod_LoadAliasModel(model_t *,void *);
static byte arena[16384];static int used,cache_size;
int r_pixbytes=1;
unsigned short d_8to16table[256];
static int integer(int v){return v;}static float real(float v){return v;}
int (*LittleLong)(int)=integer;float (*LittleFloat)(float)=real;
int Hunk_LowMark(void){return used;}
void *Hunk_AllocName(int size,char *name){void *p=arena+used;used+=(size+15)&~15;assert(used<sizeof(arena));memset(p,0,(size+15)&~15);return p;}
void Hunk_FreeToLowMark(int mark){memset(arena+mark,0xa5,used-mark);used=mark;}
void *Cache_Alloc(cache_user_t *c,int size,char *name){assert(used==0);cache_size=size;c->data=malloc(size);return c->data;}
void Q_memcpy(void *a,void *b,int n){memcpy(a,b,n);}
void Q_strcpy(char *a,char *b){strcpy(a,b);}
void Sys_Error(char *s,...){assert(0);}
int main(void){
    byte raw[2048],*p;mdl_t *m=(mdl_t *)raw;model_t mod;daliasframe_t *f;dtriangle_t *tri;
    aliashdr_t *h;mdl_t *decoded;maliasskindesc_t *skin;trivertx_t *v;int i;
    memset(raw,0,sizeof(raw));memset(&mod,0,sizeof(mod));
    m->ident=IDPOLYHEADER;m->version=ALIAS_VERSION;m->numskins=1;m->skinwidth=4;m->skinheight=4;
    m->numverts=3;m->numtris=1;m->numframes=1;m->size=1;
    for(i=0;i<3;i++){m->scale[i]=.25;m->scale_origin[i]=-2;}
    p=raw+sizeof(*m)+sizeof(daliasskintype_t);for(i=0;i<16;i++)p[i]=i+1;p+=16;
    p+=3*sizeof(stvert_t);tri=(dtriangle_t *)p;tri->facesfront=1;tri->vertindex[1]=1;tri->vertindex[2]=2;p+=sizeof(*tri);
    p+=sizeof(daliasframetype_t);f=(daliasframe_t *)p;strcpy(f->name,"fixture");v=(trivertx_t *)(f+1);v[0].v[0]=3;v[1].v[1]=17;v[2].v[2]=42;
    Mod_LoadAliasModel(&mod,raw);assert(used==0 && cache_size>16 && mod.type==mod_alias);
    h=mod.cache.data;decoded=(mdl_t *)((byte *)h+h->model);assert(decoded->numframes==1 && decoded->numverts==3);
    skin=(maliasskindesc_t *)((byte *)h+h->skindesc);for(i=0;i<16;i++)assert(*((byte *)h+skin->skin+i)==i+1);
    v=(trivertx_t *)((byte *)h+h->frames[0].frame);assert(v[0].v[0]==3 && v[1].v[1]==17 && v[2].v[2]==42);
    assert(mod.mins[0]==-2 && mod.maxs[0]==61.75 && mod.radius>61.75);free(mod.cache.data);return 0;
}
