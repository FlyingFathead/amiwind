/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>
#include <stdarg.h>

affinetridesc_t r_affinetridesc;
refdef_t r_refdef;
void *acolormap;
finalvert_t *pfinalverts;
auxvert_t *pauxverts;
pixel_t *d_viewbuffer;
short *d_pzbuffer,*zspantable[MAXHEIGHT];
unsigned int d_zwidth=320,d_zrowbytes=640;
int d_scantable[MAXHEIGHT],screenwidth=320;
int errorterm,erroradjustup,erroradjustdown,ubasestep;
static byte pixels[64000],skin[16],colormap[16384];
static short depths[64000];
static finalvert_t vertices[3];
static auxvert_t auxiliary[3];
void R_AliasClipTriangle(mtriangle_t *);
void Sys_Error(char *fmt,...) {abort();}
void R_AliasProjectFinalVert(finalvert_t *v,auxvert_t *a) {
    float inverse=1.0f/a->fv[2];
    v->v[0]=160+a->fv[0]*160*inverse;
    v->v[1]=100+a->fv[1]*160*inverse;
    v->v[5]=inverse*6442450944.0f;
}
static void begin(int occluder) {
    int i;memset(pixels,0,sizeof(pixels));
    for(i=0;i<64000;i++)depths[i]=occluder;
    memset(vertices,0,sizeof(vertices));memset(auxiliary,0,sizeof(auxiliary));
    memset(&r_affinetridesc,0,sizeof(r_affinetridesc));
    r_affinetridesc.pskin=skin;r_affinetridesc.skinwidth=4;r_affinetridesc.skinheight=4;
    r_affinetridesc.numtriangles=1;r_affinetridesc.pfinalverts=vertices;
    pfinalverts=vertices;pauxverts=auxiliary;
}
static void emit(void) {
    assert(fwrite(pixels,1,sizeof(pixels),stdout)==sizeof(pixels));
    assert(fwrite(depths,1,sizeof(depths),stdout)==sizeof(depths));
}
int main(void) {
    static const int shapes[2][3][2]={{{10,10},{20,50},{20,51}},{{10,10},{90,10},{10,90}}};
    static const float clips[3][3][3]={
        {{-2,0,10},{2,8,10},{0,6,1}},
        {{-1,-1,1},{1,-1,1},{0,1,10}},
        {{-1,-1,1},{1,-1,1},{0,1,1}}};
    mtriangle_t triangle={1,{0,1,2}};
    int kind,rotation,order,reverse,occluder,i,j,index,x,y,tmp;
    d_viewbuffer=pixels;d_pzbuffer=depths;acolormap=colormap;
    memset(skin,1,sizeof(skin));memset(colormap,7,sizeof(colormap));
    for(i=0;i<200;i++){d_scantable[i]=i*320;zspantable[i]=depths+i*320;}
    r_refdef.aliasvrectright=319;r_refdef.aliasvrectbottom=199;
    /* Authored synthetic skinny triangles have depth slopes beyond signed32,
     * while every covered pixel's true inverse depth remains representable. */
    for(kind=0;kind<2;kind++)for(rotation=0;rotation<4;rotation++)
    for(order=0;order<3;order++)for(reverse=0;reverse<2;reverse++)
    for(occluder=0;occluder<2;occluder++) {
        begin(occluder*10000);
        for(i=0;i<3;i++) {
            index=(i+order)%3;x=shapes[kind][index][0]-50;y=shapes[kind][index][1]-50;
            for(j=0;j<rotation;j++){tmp=x;x=-y;y=tmp;}
            vertices[i].v[0]=x+160;vertices[i].v[1]=y+100;
            vertices[i].v[5]=((index==1)^reverse)?1200000000:400000000;
        }
        r_affinetridesc.ptriangles=&triangle;D_PolysetDraw();emit();
    }
    /* Actual near/screen clipping reaches the same raster path, in every
     * screen direction and cyclic vertex order, with an occluding surface. */
    for(kind=0;kind<3;kind++)for(rotation=0;rotation<4;rotation++)
    for(order=0;order<3;order++)for(occluder=0;occluder<2;occluder++) {
        begin(occluder*10000);
        for(i=0;i<3;i++) {
            float a,b,t;index=(i+order)%3;a=clips[kind][index][0];b=clips[kind][index][1];
            for(j=0;j<rotation;j++){t=a;a=-b;b=t;}
            auxiliary[i].fv[0]=a;auxiliary[i].fv[1]=b;auxiliary[i].fv[2]=clips[kind][index][2];
            if(auxiliary[i].fv[2]<ALIAS_Z_CLIP_PLANE)vertices[i].flags=ALIAS_Z_CLIP;
            else {
                R_AliasProjectFinalVert(&vertices[i],&auxiliary[i]);
                if(vertices[i].v[0]<0)vertices[i].flags|=ALIAS_LEFT_CLIP;
                if(vertices[i].v[0]>319)vertices[i].flags|=ALIAS_RIGHT_CLIP;
                if(vertices[i].v[1]<0)vertices[i].flags|=ALIAS_TOP_CLIP;
                if(vertices[i].v[1]>199)vertices[i].flags|=ALIAS_BOTTOM_CLIP;
            }
        }
        R_AliasClipTriangle(&triangle);emit();
    }
    return 0;
}
