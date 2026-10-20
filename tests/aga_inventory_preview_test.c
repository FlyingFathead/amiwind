/* SPDX-License-Identifier: GPL-3.0-only
 * Real alias preview, source-independent synthetic meshes and padded framebuffer. */
#include "quakedef.h"
#include <assert.h>
viddef_t vid;
static model_t body,gear,torch;
static union {double align;byte bytes[4096];} body_data,gear_data,torch_data;
static byte framebuffer[324*200+4];
static int show_gear,show_torch;
void *Mod_Extradata(model_t *model){
    return model==&body?body_data.bytes:model==&torch?torch_data.bytes:gear_data.bytes;
}
int AW_ViewInventoryEquipment(model_t *models[2],float origins[2][3],float angles[2][3]){
    if(!show_gear)return 0;
    models[0]=&gear;origins[0][0]=20;origins[0][1]=0;origins[0][2]=35;
    angles[0][0]=angles[0][1]=angles[0][2]=0;return 1;
}
/* PLAYER-TORCH-THIRDPERSON-38: the torch pose's held torch, at the body's frame and place
 * (taller than the body here, so its top shows above it). */
int AW_ViewInventoryHeld(model_t **model,int *frame){
    if(!show_torch)return 0;
    *model=&torch;*frame=0;return 1;
}
static void alias(model_t *model,byte *raw,int tall,byte color){
    aliashdr_t *h=(aliashdr_t *)raw;mdl_t *m;trivertx_t *v;stvert_t *st;mtriangle_t *tri;maliasskindesc_t *skin;
    int offset=sizeof(*h),i;model->type=mod_alias;model->numframes=1;
    h->model=offset;m=(mdl_t *)(raw+offset);offset+=sizeof(*m);
    m->numverts=4;m->numtris=2;m->numframes=1;m->skinwidth=m->skinheight=2;
    m->scale[0]=m->scale[1]=m->scale[2]=1;
    h->frames[0].frame=offset;v=(trivertx_t *)(raw+offset);offset+=4*sizeof(*v);
    v[0].v[0]=v[2].v[0]=0;v[1].v[0]=v[3].v[0]=10;v[2].v[2]=v[3].v[2]=tall;
    h->stverts=offset;st=(stvert_t *)(raw+offset);offset+=4*sizeof(*st);
    st[1].s=st[3].s=65536;st[2].t=st[3].t=65536;
    h->triangles=offset;tri=(mtriangle_t *)(raw+offset);offset+=2*sizeof(*tri);
    tri[0].vertindex[0]=0;tri[0].vertindex[1]=1;tri[0].vertindex[2]=2;
    tri[1].vertindex[0]=1;tri[1].vertindex[1]=3;tri[1].vertindex[2]=2;
    offset=(offset+7)&~7;h->skindesc=offset;skin=(maliasskindesc_t *)(raw+offset);offset+=sizeof(*skin);skin->skin=offset;
    for(i=0;i<4;i++)raw[offset+i]=color;
}
static int colored(int color){
    int x,y,n=0,min=200,max=-1;
    for(y=0;y<200;y++)for(x=0;x<324;x++){
        byte value=vid.buffer[y*324+x];
        if(x>=320){assert(value==137);continue;}
        if(value!=137){assert(x>=7 && x<123 && y>=20 && y<182);}
        if(value==color){n++;if(y<min)min=y;if(y>max)max=y;}
    }
    if(color==70 && n){assert(min>=24 && max<=177 && max-min>=145);}
    assert(framebuffer[0]==137 && framebuffer[sizeof(framebuffer)-1]==137);
    return n;
}
int main(void){
    int body_pixels,gear_pixels;
    vid.width=320;vid.height=200;vid.rowbytes=324;vid.buffer=framebuffer+2;
    alias(&body,body_data.bytes,64,70);alias(&gear,gear_data.bytes,12,100);
    memset(framebuffer,137,sizeof(framebuffer));
    assert(AW_InventoryPreviewDraw(&body,0,7,20,116,162,0));body_pixels=colored(70);assert(body_pixels>100);
    memset(framebuffer,137,sizeof(framebuffer));show_gear=1;
    assert(AW_InventoryPreviewDraw(&body,0,7,20,116,162,0));gear_pixels=colored(100);
    assert(gear_pixels>0 && colored(70)>0);
    assert(!AW_InventoryPreviewDraw(&body,0,7,20,123,162,0));
    /* PLAYER-TORCH-THIRDPERSON-38: the carried torch is drawn with the torch pose. */
    alias(&torch,torch_data.bytes,80,110);show_gear=0;show_torch=1;
    memset(framebuffer,137,sizeof(framebuffer));
    assert(AW_InventoryPreviewDraw(&body,0,7,20,116,162,0));assert(colored(110)>0);
    show_torch=0;
    AW_InventoryPreviewClear();AW_InventoryPreviewClear();return 0;
}
