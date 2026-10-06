/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>
#include <stdarg.h>
client_state_t cl;
refdef_t r_refdef;
entity_t *currententity;
vec3_t modelorg,vpn={1,0,0},vright={0,-1,0},vup={0,0,1};
float aliasxscale=160,aliasyscale=160,aliasxcenter=160,aliasycenter=100;
qboolean r_recursiveaffinetriangles;
static byte bank[8192],cmap[16384];
static int calls,expected_depth;
void Con_DPrintf(char *f,...){}
void Sys_Error(char *fmt,...){abort();}
void *Mod_Extradata(model_t *m){return bank;}
float R_SpriteEntityScale(const entity_t *e){return 1;}
int AW_AliasBudgetAllows(int v,int t){return v==3 && t==1;}
void D_PolysetUpdateTables(void){assert(0);}
void D_PolysetDrawFinalVerts(finalvert_t *v,int n){assert(0);}
void D_PolysetDraw(void)
{
    static const int xy[3][2]={{180,120},{180,80},{140,120}};
    int i;calls++;
    assert(r_affinetridesc.numtriangles==1);
    for(i=0;i<3;i++){
        finalvert_t *v=&r_affinetridesc.pfinalverts[i];
        assert(v->v[5]==expected_depth);
        assert(v->v[5]>=0 && (v->v[5]>>16)<=32767);
        /* At depth2, no viewmodel placement or perspective change. */
        if(expected_depth==2147418112){assert(v->v[0]==xy[i][0]);assert(v->v[1]==xy[i][1]);}
    }
}
static void check(const char *name,int viewmodel,int frame_count,int x,int draws,int depth,int stale)
{
    aliashdr_t *h=(aliashdr_t *)bank;mdl_t *m;
    maliasskindesc_t *skin;stvert_t *st;mtriangle_t *tri;trivertx_t *v;
    entity_t other;model_t model;alight_t light;vec3_t lv={-1,0,0};int at,i;
    memset(bank,0,sizeof(bank));memset(&other,0,sizeof(other));memset(&model,0,sizeof(model));memset(&cl.viewent,0,sizeof(cl.viewent));
    currententity=viewmodel?&cl.viewent:&other;currententity->model=&model;
    strcpy(model.name,name);model.numframes=frame_count;currententity->colormap=cmap;currententity->trivial_accept=stale;
    at=(sizeof(aliashdr_t)+27*sizeof(maliasframedesc_t)+7)&~7;
    h->model=at;m=(mdl_t *)(bank+at);at+=sizeof(*m);
    m->scale[0]=m->scale[1]=m->scale[2]=.25f;m->scale_origin[1]=m->scale_origin[2]=-.25f;
    m->numskins=1;m->skinwidth=m->skinheight=4;m->numverts=3;m->numtris=1;m->numframes=frame_count;
    h->skindesc=at;skin=(maliasskindesc_t *)(bank+at);at+=sizeof(*skin);skin->skin=at;at+=16;
    h->stverts=at;st=(stvert_t *)(bank+at);at+=3*sizeof(*st);
    h->triangles=at;tri=(mtriangle_t *)(bank+at);at+=sizeof(*tri);tri->facesfront=1;
    for(i=0;i<3;i++)tri->vertindex[i]=i;
    h->frames[0].frame=at;v=(trivertx_t *)(bank+at);
    for(i=0;i<3;i++)v[i].v[0]=x;
    v[1].v[2]=2;v[2].v[1]=2;
    light.ambientlight=128;light.shadelight=64;light.plightvec=lv;
    calls=0;expected_depth=depth;R_AliasDrawModel(&light);assert(calls==draws);
    if(viewmodel && frame_count==28 && !strcmp(name,"progs/hands/nord_m.mdl"))assert(currententity->trivial_accept==0);
}
int main(void)
{
    r_refdef.aliasvrectright=319;r_refdef.aliasvrectbottom=199;
    check("progs/hands/nord_m.mdl",1,28,8,1,2147418112,3);
    check("progs/v_nord.mdl",1,28,8,1,2147418112,0);
    check("progs/hands/nord_m.mdl",1,28,4,0,0,0);
    check("progs/hands/nord_m.mdl",1,28,32,1,805306368,0);
    check("progs/hands/nord_m.mdl",0,28,32,1,268435456,0);
    check("progs/hands/nord_m.mdl",0,28,8,0,0,0);
    check("progs/custom.mdl",1,28,8,0,0,0);
    check("progs/custom.mdl",1,28,32,1,805306368,0);
    check("progs/hands/nord_m_t.mdl",1,8,8,0,0,0);
    check("progs/hands/nord_m_t.mdl",1,8,32,1,805306368,0);
    puts("fist near clipping: perspective, depth saturation/bias, stale metadata and world/custom/torch exclusions passed");
    return 0;
}
