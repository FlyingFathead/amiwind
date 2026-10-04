/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>
server_t sv;server_static_t svs;viddef_t vid;refdef_t r_refdef;
cvar_t r_drawviewmodel={"r_drawviewmodel","1"},chase_active;
qboolean r_fov_greater_than_90;keydest_t key_dest;int r_framecount;
byte *host_basepal;
static edict_t player;static client_t client;
static eval_t goal,state,torch;static int gallery,locked;
static void (*command)(void);
static byte pixels[336*210],pal[768],torch_assets[716];
static model_t torch_model;
int com_filesize;
void AW_GuardTorchInit(void){}
void AW_GuardTorchLoadAssets(const byte *torch){assert(torch);}
void AW_GuardTorchUpdate(void){}
void AW_GuardTorchDraw(void){}
vec3_t vpn,vup,vright;
float aliasxcenter,aliasycenter,aliasxscale,aliasyscale;
byte *COM_LoadHunkFile(char *path){assert(!strcmp(path,"gfx/torch.awt"));com_filesize=sizeof(torch_assets);return torch_assets;}
model_t *Mod_ForName(char *path,qboolean crash){assert(!strcmp(path,"progs/v_torch.mdl"));return &torch_model;}
static void put32(byte *p,unsigned long n){p[0]=n>>24;p[1]=n>>16;p[2]=n>>8;p[3]=n;}

extern unsigned blocklights[18*18];
extern float entity_rotation[3][3];
void R_AddDynamicLights(void);
eval_t *GetEdictFieldValue(edict_t *e,char *name){
    assert(e==&player);
    if(!strcmp(name,"aw_hand_goal"))return &goal;
    if(!strcmp(name,"aw_hand_state"))return &state;
    if(!strcmp(name,"aw_torch"))return &torch;
    return NULL;
}
int AW_GalleryActive(void){return gallery;}
int AW_IntroImpulse(int impulse){return locked?0:impulse;}
void Cmd_AddCommand(char *name,void (*fn)(void)){assert(!strcmp(name,"aw_torch"));command=fn;}
void Con_Printf(char *format,...){}
static int lights(void){int i,n=0;for(i=0;i<MAX_DLIGHTS;i++)if(cl_dlights[i].radius>0)n++;return n;}
static dlight_t *torchlight(void){int i;for(i=0;i<MAX_DLIGHTS;i++)if(cl_dlights[i].key< -1)return &cl_dlights[i];return NULL;}
int main(void)
{
    int i,x,y,changed=0;dlight_t *light,local;unsigned expected;entity_t brush;
    model_t model;mnode_t root,leaf;msurface_t surface;mplane_t plane;mtexinfo_t tex;
    memset(&model,0,sizeof(model));memset(&root,0,sizeof(root));memset(&leaf,0,sizeof(leaf));
    memset(&surface,0,sizeof(surface));memset(&plane,0,sizeof(plane));memset(&tex,0,sizeof(tex));
    client.edict=&player;svs.clients=&client;svs.maxclients=1;sv.active=true;
    cls.state=ca_connected;key_dest=key_game;cl.time=1;player.v.health=100;
    memcpy(torch_assets,"AWT1",4);torch_assets[5]=8;torch_assets[7]=16;put32(torch_assets+8,2667);
    for(i=0;i<8;i++){put32(torch_assets+12+i*24,12*65536);put32(torch_assets+16+i*24,3*65536);}
    for(i=204;i<716;i+=2){torch_assets[i]=220;torch_assets[i+1]=255;}
    assert(AW_TorchAssetsValidate(torch_assets,716));assert(!AW_TorchAssetsValidate(torch_assets,715));
    torch_assets[5]=9;assert(!AW_TorchAssetsValidate(torch_assets,716));torch_assets[5]=8;
    put32(torch_assets+8,0);assert(!AW_TorchAssetsValidate(torch_assets,716));put32(torch_assets+8,2667);
    put32(torch_assets+12,129*65536);assert(!AW_TorchAssetsValidate(torch_assets,716));put32(torch_assets+12,12*65536);
    AW_TorchInit();AW_TorchLoadAssets();assert(command);torch_model.type=mod_alias;torch_model.numframes=8;
    command();assert(!torch._float); /* V alone cannot raise hands. */
    goal._float=1;state._float=1;command();assert(torch._float==1);
    AW_TorchUpdate();assert(!lights()); /* Wait for the drawn pose. */
    state._float=2;r_refdef.vieworg[2]=24;AW_TorchUpdate();assert(lights()==1);
    light=torchlight();assert(light && light->radius>=141 && light->radius<=148);
    assert(light->origin[2]==24 && light->minlight==16 && light->die>cl.time && light->decay==0);
    AW_TorchViewModel();assert(cl.viewent.model==&torch_model && cl.viewent.frame==AW_TorchFrame());
    for(i=0;i<10000;i++){cl.time=i*.007;assert(AW_TorchFrame()>=0 && AW_TorchFrame()<8);}
    cl.time=1;
    /* Refresh reuses one keyed light and does not alter an unrelated light. */
    cl_dlights[4].key=123;cl_dlights[4].radius=30;cl_dlights[4].die=5;
    for(i=0;i<100;i++){cl.time+=.013;r_refdef.vieworg[0]=i;AW_TorchUpdate();}
    assert(lights()==2 && torchlight()==light && light->origin[0]==99 && cl_dlights[4].radius==30);
    cl_dlights[4].radius=0;r_refdef.vieworg[0]=0;AW_TorchUpdate();
    /* Exercise actual BSP marking and actual surface light accumulation. */
    plane.normal[2]=1;root.plane=&plane;root.numsurfaces=1;leaf.contents=-1;
    root.children[0]=root.children[1]=&leaf;model.nodes=&root;model.surfaces=&surface;
    surface.plane=&plane;surface.texinfo=&tex;surface.extents[0]=surface.extents[1]=16;
    tex.vecs[0][0]=tex.vecs[1][1]=1;cl.worldmodel=&model;r_framecount=10;
    R_PushDlights();assert(surface.dlightframe==11 && surface.dlightbits);
    r_drawsurf.surf=&surface;memset(blocklights,0,sizeof(blocklights));R_AddDynamicLights();
    assert(blocklights[0]>0 && blocklights[3]>0);
    expected=blocklights[0];
    /* Same light/face relationship after moving and yaw-rotating an instance.
     * The world light stays unchanged; translated cave pieces receive light. */
    memset(&brush,0,sizeof(brush));brush.origin[0]=1000;brush.origin[1]=2000;brush.origin[2]=3000;
    brush.angles[1]=90;currententity=&brush;
    entity_rotation[0][1]=1;entity_rotation[1][0]=-1;entity_rotation[2][2]=1;
    light->origin[0]=1000;light->origin[1]=2000;light->origin[2]=3024;
    local=*light;R_DlightOrigin(light,local.origin);
    assert(local.origin[0]==0 && local.origin[1]==0 && local.origin[2]==24);
    surface.dlightbits=0;R_MarkLights(&local,1<<(light-cl_dlights),&root);
    assert(surface.dlightbits);memset(blocklights,0,sizeof(blocklights));R_AddDynamicLights();
    assert(blocklights[0]==expected && light->origin[2]==3024);
    light->origin[0]=990;light->origin[1]=2020;R_DlightOrigin(light,local.origin);
    assert(local.origin[0]==20 && local.origin[1]==10 && local.origin[2]==24);
    currententity=&cl_entities[0];
    command();assert(!torch._float && !lights());
    memset(blocklights,0,sizeof(blocklights));R_AddDynamicLights();assert(!blocklights[0]);
    command();assert(torch._float);goal._float=0;AW_TorchUpdate();assert(!lights());
    goal._float=1;AW_TorchUpdate();assert(lights()==1);
    player.v.health=0;AW_TorchUpdate();assert(!lights());player.v.health=100;
    gallery=1;AW_TorchUpdate();assert(!lights());gallery=0;
    cl.intermission=1;AW_TorchUpdate();assert(!lights());cl.intermission=0;
    locked=1;command();assert(torch._float);locked=0;
    sv.paused=1;command();assert(torch._float);sv.paused=0;
    cls.state=ca_disconnected;AW_TorchUpdate();assert(!lights());cls.state=ca_connected;
    /* Draw into an offset viewport with padded rows; all writes stay inside. */
    for(i=0;i<256;i++)pal[i*3]=pal[i*3+1]=pal[i*3+2]=i;
    host_basepal=pal;vid.buffer=pixels;vid.width=320;vid.height=200;vid.rowbytes=336;
    r_refdef.vrect.x=17;r_refdef.vrect.y=11;r_refdef.vrect.width=240;r_refdef.vrect.height=145;
    r_drawviewmodel.value=1;vpn[0]=1;vright[1]=-1;vup[2]=1;
    memset(r_refdef.vieworg,0,sizeof(vec3_t));memset(cl.viewent.origin,0,sizeof(vec3_t));memset(cl.viewent.angles,0,sizeof(vec3_t));
    aliasxcenter=137;aliasycenter=90;aliasxscale=aliasyscale=120;
    memset(pixels,255,sizeof(pixels));AW_TorchDraw();
    for(y=0;y<210;y++)for(x=0;x<336;x++)if(pixels[y*336+x]!=255){
        assert(x>=17 && x<257 && y>=11 && y<156);changed++;
    }
    assert(changed>5);
    memset(pixels,255,sizeof(pixels));chase_active.value=1;AW_TorchDraw();
    for(i=0;i<sizeof(pixels);i++)assert(pixels[i]==255);
    return 0;
}
