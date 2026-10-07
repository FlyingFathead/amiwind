/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include "aw_torch.h"
#include <assert.h>
server_t sv;server_static_t svs;viddef_t vid;refdef_t r_refdef;
cvar_t r_drawviewmodel={"r_drawviewmodel","1"},chase_active;
qboolean r_fov_greater_than_90;keydest_t key_dest;int r_framecount;
byte *host_basepal;
static edict_t player;static client_t client;
static eval_t goal,state,torch;static int gallery,locked,torch_test;
static void (*command)(void);
static cvar_t *radius_setting,*flame_setting;
static int setting_argc=1;static char *setting_value="";
static void (*set_radius)(void),(*set_flame)(void),(*set_strength)(void),(*set_headlamp)(void);
int Cmd_Argc(void){return setting_argc;}
char *Cmd_Argv(int n){return n==1?setting_value:"";}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void *Z_Malloc(int size){void *p=calloc(1,size);assert(p);return p;}
void Z_Free(void *p){free(p);}
int Q_strlen(char *s){return strlen(s);}
void Q_strcpy(char *to,char *from){strcpy(to,from);}
int Q_strcmp(char *a,char *b){return strcmp(a,b);}
float Q_atof(char *s){return atof(s);}
double host_frametime;void AW_EmberSpawn(const vec3_t org,float spread,float rise){(void)org;(void)spread;(void)rise;}
qboolean Cmd_Exists(char *name){return false;}
void SV_BroadcastPrintf(char *format,...){assert(0);}
int AW_UIColor(int r,int g,int b){
    if(r==255 && g==244 && b==214)return 254;
    if(r==255 && g==255 && b==232)return 253;
    if(r==255 && g==232 && b==112)return 252;
    assert(r==248 && g==154 && b==48);return 251;
}

static byte pixels[336*210],pal[768],torch_assets[716];
static byte hand_assets[716],legacy_pixels[sizeof(pixels)];
static int hand_size=716,hand_missing,guard_loads;
static model_t torch_model;
int com_filesize;
void AW_GuardTorchInit(void){}
void AW_GuardTorchLoadAssets(const byte *torch){assert(torch==torch_assets);guard_loads++;}
void AW_GuardTorchUpdate(void){}
void AW_LampInit(void){}void AW_LampUpdate(void){}
void AW_GuardTorchDraw(void){}
vec3_t vpn,vup,vright;
float aliasxcenter,aliasycenter,aliasxscale,aliasyscale;
byte *COM_LoadHunkFile(char *path){
    if(!strcmp(path,"gfx/hand-torch.awt")){com_filesize=hand_size;return hand_missing?NULL:hand_assets;}
    assert(!strcmp(path,"gfx/torch.awt"));com_filesize=sizeof(torch_assets);return torch_assets;
}
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
int AW_TorchTestActive(void){return torch_test;}
int AW_IntroImpulse(int impulse){return locked?0:impulse;}
void Cmd_AddCommand(char *name,void (*fn)(void)){
    if(!strcmp(name,"aw_torch_radius_set"))set_radius=fn;
    else if(!strcmp(name,"aw_torch_flame_set"))set_flame=fn;
    else if(!strcmp(name,"aw_torch_strength_set"))set_strength=fn;
    else if(!strcmp(name,"aw_headlamp_set"))set_headlamp=fn;
    else {assert(!strcmp(name,"aw_torch"));command=fn;}
}
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
    AW_TorchInit();AW_TorchLoadAssets();assert(command && set_radius && set_flame && set_strength);
    radius_setting=Cvar_FindVar("aw_torch_radius");flame_setting=Cvar_FindVar("aw_torch_flame_style");
    assert(radius_setting->archive && flame_setting->archive && AW_TorchLightRadius()==192);
    assert(AW_TorchFlameCoreColor()==254 && aw_torch_strength.archive && aw_torch_strength.value==.7f);
    /* Actual cvar storage, archived override and command validation. */
    {
        FILE *f=tmpfile();char saved[512];size_t n;
        assert(f);Cvar_Set("aw_torch_strength","0.3");
        Cvar_WriteVariables(f);rewind(f);n=fread(saved,1,sizeof(saved)-1,f);saved[n]=0;fclose(f);
        assert(strstr(saved,"aw_torch_strength \"0.3\"\n") && aw_torch_strength.value==.3f);
        assert(strstr(saved,"aw_torch_flame_style \"2\"\n") && strstr(saved,"aw_torch_radius \"192\"\n"));
        Cvar_Set("aw_torch_strength","-1");assert(aw_torch_strength.value==0);
        Cvar_Set("aw_torch_strength","2");assert(aw_torch_strength.value==1);
        Cvar_Set("aw_torch_strength","nan");assert(aw_torch_strength.value==0);
        Cvar_Set("aw_torch_strength","inf");assert(aw_torch_strength.value==1);
        setting_argc=2;setting_value="0.7";set_strength();assert(aw_torch_strength.value==.7f);
        setting_value="nan";set_strength();assert(aw_torch_strength.value==.7f);
        setting_value="1.1";set_strength();assert(aw_torch_strength.value==.7f);
        setting_value="0.5junk";set_strength();assert(aw_torch_strength.value==.7f);
    }
    setting_argc=2;setting_value="240";set_radius();assert(AW_TorchLightRadius()==240);
    setting_value="nan";set_radius();assert(AW_TorchLightRadius()==240);
    setting_value="289";set_radius();assert(AW_TorchLightRadius()==240);
    setting_value="31";set_radius();assert(AW_TorchLightRadius()==240);
    radius_setting->value=999;assert(AW_TorchLightRadius()==288);
    radius_setting->value=-1;assert(AW_TorchLightRadius()==32);
    radius_setting->value=NAN;assert(AW_TorchLightRadius()==192);
    setting_value="144";set_radius();assert(AW_TorchLightRadius()==144);
    setting_value="brightbase";set_flame();assert(AW_TorchFlameCoreColor()==254);
    for(i=0;i<256;i++){
        int core=(i%16>=5 && i%16<=10 && i/16>=8);
        assert(AW_TorchFlameColor(7,i*2,0,254)==(core?254:7));
        assert(AW_TorchFlameColor(7,i*2,.5f,254)==7);
        assert(AW_TorchFlameColor(7,i*2,0,-1)==7);
    }
    setting_value="classic";set_flame();assert(AW_TorchFlameCoreColor()==-1);torch_model.type=mod_alias;torch_model.numframes=8;
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
    /* Strength changes real surface accumulation without reallocating light
     * slots, changing the emitter/radius or turning off the held flame. */
    setting_value="0";set_strength();memset(blocklights,0,sizeof(blocklights));R_AddDynamicLights();
    assert(!blocklights[0] && lights()==1 && torch._float);
    setting_value="0.35";set_strength();memset(blocklights,0,sizeof(blocklights));R_AddDynamicLights();
    assert(blocklights[0]>0 && abs((int)(2*blocklights[0])-(int)expected)<=1);
    setting_value="1";set_strength();memset(blocklights,0,sizeof(blocklights));R_AddDynamicLights();
    assert(blocklights[0]>expected && lights()==1);
    setting_value="0.7";set_strength();
    /* Greater reach must increase actual ground-surface light, not just flames. */
    setting_value="192";set_radius();AW_TorchUpdate();
    memset(blocklights,0,sizeof(blocklights));R_AddDynamicLights();assert(blocklights[0]>expected);
    setting_value="144";set_radius();AW_TorchUpdate();
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
    /* Debug headlamp: the torch's eye light without a torch, steady, not saved. */
    assert(set_headlamp && !Cvar_FindVar("aw_headlamp")->archive && !Cvar_FindVar("aw_headlamp")->value);
    setting_argc=2;setting_value="maybe";set_headlamp();AW_TorchUpdate();assert(!lights());
    setting_value="on";set_headlamp();AW_TorchUpdate();assert(lights()==1);
    light=torchlight();assert(light && light->radius==AW_TorchLightRadius());
    cl.time+=.3;AW_TorchUpdate();assert(torchlight()==light && light->radius==AW_TorchLightRadius());
    setting_value="0";set_headlamp();AW_TorchUpdate();assert(!lights());
    setting_value="TRUE";set_headlamp();AW_TorchUpdate();assert(lights()==1);
    setting_value="off";set_headlamp();AW_TorchUpdate();assert(!lights());
    memset(blocklights,0,sizeof(blocklights));R_AddDynamicLights();assert(!blocklights[0]);
    command();assert(torch._float);goal._float=0;AW_TorchUpdate();assert(!lights());
    goal._float=1;AW_TorchUpdate();assert(lights()==1);
    player.v.health=0;AW_TorchUpdate();assert(!lights());player.v.health=100;
    gallery=1;AW_TorchUpdate();assert(!lights());
    torch_test=1;AW_TorchUpdate();assert(lights()==1);torch_test=0;
    AW_TorchUpdate();assert(!lights());gallery=0;
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
    assert(changed>5);memcpy(legacy_pixels,pixels,sizeof(pixels));
    /* Pair-specific duration, anchor and texture selection; legacy restoration
     * reproduces every framebuffer byte and never changes guard light data. */
    memcpy(hand_assets,torch_assets,sizeof(hand_assets));put32(hand_assets+8,1000);
    for(i=0;i<8;i++)put32(hand_assets+16+i*24,0);
    for(i=204;i<716;i+=2)hand_assets[i]=180;
    assert(AW_TorchLoadHandAssets());assert(guard_loads==1);
    AW_TorchUseHandAssets(1);assert(AW_TorchFrame()==(int)(fmod(cl.time,1.0)*8));
    memset(pixels,255,sizeof(pixels));AW_TorchDraw();changed=0;
    for(i=0;i<sizeof(pixels);i++)if(pixels[i]!=255){assert(pixels[i]==180);changed++;}
    assert(changed>5 && memcmp(pixels,legacy_pixels,sizeof(pixels)));
    AW_TorchUseHandAssets(0);memset(pixels,255,sizeof(pixels));AW_TorchDraw();
    assert(!memcmp(pixels,legacy_pixels,sizeof(pixels)));
    AW_TorchUseHandAssets(1);AW_TorchViewModel();assert(cl.viewent.frame==AW_TorchFrame());
    memset(pixels,255,sizeof(pixels));AW_TorchDraw();assert(!memcmp(pixels,legacy_pixels,sizeof(pixels)));
    hand_size=715;assert(!AW_TorchLoadHandAssets());AW_TorchUseHandAssets(1);
    memset(pixels,255,sizeof(pixels));AW_TorchDraw();assert(!memcmp(pixels,legacy_pixels,sizeof(pixels)));
    hand_size=716;hand_assets[0]='X';assert(!AW_TorchLoadHandAssets());
    hand_assets[0]='A';hand_missing=1;assert(!AW_TorchLoadHandAssets());
    assert(guard_loads==1);
    /* Optional sparks use the real framebuffer and obey offset viewport/row
     * padding. Phase is game-time based: repeated frozen draws are identical.
     * Returning to classic restores every original pixel and light setting. */
    {
        byte spark_pixels[sizeof(pixels)];double saved_time=cl.time;
        int spark_colours[3]={0,0,0},step;
        setting_value="sparks";set_flame();assert(flame_setting->value==3);
        for(step=0;step<80;step++){
            cl.time=step*.02;memset(pixels,255,sizeof pixels);AW_TorchDraw();
            memcpy(spark_pixels,pixels,sizeof pixels);AW_TorchDraw();
            assert(!memcmp(spark_pixels,pixels,sizeof pixels));
            for(y=0;y<210;y++)for(x=0;x<336;x++)if(pixels[y*336+x]!=255){
                assert(x>=17 && x<257 && y>=11 && y<156);
                if(pixels[y*336+x]>=251 && pixels[y*336+x]<=253)spark_colours[pixels[y*336+x]-251]++;
            }
        }
        assert(spark_colours[0] && spark_colours[1] && spark_colours[2]);
        cl.time=saved_time;setting_value="classic";set_flame();
        memset(pixels,255,sizeof pixels);AW_TorchDraw();
        assert(!memcmp(pixels,legacy_pixels,sizeof pixels));
        assert(radius_setting->value==144 && guard_loads==1);
    }
    memset(pixels,255,sizeof(pixels));chase_active.value=1;AW_TorchDraw();
    for(i=0;i<sizeof(pixels);i++)assert(pixels[i]==255);
    return 0;
}
