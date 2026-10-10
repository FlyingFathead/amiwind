/* SPDX-License-Identifier: GPL-2.0-or-later
 * Actual entity lighting -> alias transform/clip/span -> palette/night fog.
 * The small synthetic actor and grayscale palette contain no game assets. */
#define R_AliasDrawModel CaptureAliasDraw
#define R_AliasCheckBBox AcceptAliasBBox
#include "r_main.c"
#undef R_AliasDrawModel
#undef R_AliasCheckBBox
#include "aw_state.h"
#include "aw_clock.h"
#include <assert.h>
#include <stdarg.h>
/* Light-space night symbols owned by r_light.c / d_sprite.c / d_surf.c. */
int r_daylight=256;unsigned char *r_warm_colormap;const unsigned char *d_nightshade;
void Cvar_Set(char *name,char *value){(void)name;(void)value;}void D_FlushCaches(void){}
void R_AliasDrawModel(alight_t *light);
void R_SetSkyFrame(void);

client_state_t cl;
cvar_t aw_torch_strength={"aw_torch_strength","0.7",true,false,.7f};cvar_t aw_guard_torch_radius={"aw_guard_torch_radius","1",true,false,1};
entity_t cl_entities[MAX_EDICTS],*cl_visedicts[MAX_VISEDICTS],*currententity;
dlight_t cl_dlights[MAX_DLIGHTS];
int cl_numvisedicts;
vec3_t r_entorigin,modelorg;
server_t sv;
viddef_t vid;
double realtime;
byte *host_basepal;
unsigned short d_8to16table[256];
pixel_t *d_viewbuffer;
short *d_pzbuffer,*zspantable[MAXHEIGHT];
unsigned int d_zwidth=320,d_zrowbytes=640;
int d_scantable[MAXHEIGHT];
int errorterm,erroradjustup,erroradjustdown,ubasestep;
static byte palette[768],cmap[16384],fog_table[4096],bank[4096];
static byte pixels[64000],reference[64000];
static short depths[64000];
static model_t actor_model;
static entity_t actor;
static alight_t received;
static int world_light,inside,gallery_active,draws,torch_test_active;
static cvar_t *daynight,*fog_enabled;

entity_t *AW_GuardTorchEntity(entity_t *e){return e;}
/* NPC model levels (aw_npc_lod.c): every actor keeps its own model here. */
void AW_NpcLodFrame(void){}
model_t *AW_NpcLodModel(entity_t *e){return e->model;}
int AW_NpcLodResident(int *bytes){if(bytes)*bytes=0;return 0;}
int AW_HandModelsApply(void){return 1;}
void AW_TorchViewModel(void){assert(0);}
float R_SpriteEntityScale(const entity_t *e){return 1;}
qboolean AcceptAliasBBox(void){currententity->trivial_accept=0;return true;}
void CaptureAliasDraw(alight_t *light){received=*light;draws++;R_AliasDrawModel(light);}
int R_LightPoint(vec3_t p){return world_light;}
/* Maps without an actor light grid: the floor light (r_light.c R_ActorLight). */
int R_ActorLight(entity_t *e,int centre){(void)centre;return R_LightPoint(e->origin);}
int AW_GalleryActive(void){return gallery_active;}
int AW_TorchTestActive(void){return torch_test_active;}
void R_DrawSprite(void){}
void Con_Printf(char *fmt,...){}
void Con_DPrintf(char *fmt,...){}
void Sys_Error(char *fmt,...){va_list ap;va_start(ap,fmt);vfprintf(stderr,fmt,ap);va_end(ap);abort();}
void *Mod_Extradata(model_t *m){assert(m==&actor_model);return bank;}
int AW_AliasBudgetAllows(int v,int t){return v==3 && t==1;}
int AW_Interior(void){return inside;}
int AW_TerrainId(const char *name){return -1;}
void AW_HorizonReport(void){}
void AW_HorizonDraw(byte colour,int distance){assert(0);}
int AW_DayGalleryClock(int actual_ms){return actual_ms;}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);if(!strcmp(c->name,"aw_daynight"))daynight=c;if(!strcmp(c->name,"aw_fog"))fog_enabled=c;}
void Cvar_SetValue(char *name,float value){assert(!strcmp(name,"aw_drawdistance"));aw_drawdistance.value=value;}
void Cmd_AddCommand(char *name,void (*fn)(void)){}
int Cmd_Argc(void){return 1;}
char *Cmd_Argv(int n){return "";}
byte *COM_LoadHunkFile(char *name){assert(!strcmp(name,"gfx/fog.lmp"));return fog_table;}
int COM_FOpenFile(char *path,FILE **file){
    int i;*file=NULL;if(!strcmp(path,AW_NIGHT_SKY_PATH))return -1;
    assert(!strcmp(path,AW_SHARED_SKY_PATH));*file=tmpfile();assert(*file);
    for(i=0;i<AW_SHARED_SKY_BYTES;i++)fputc(i%256<128?0:200,*file);
    rewind(*file);return AW_SHARED_SKY_BYTES;
}

static int align8(int n){return (n+7)&~7;}
static void synthetic_actor(void){
    aliashdr_t *h=(aliashdr_t *)bank;mdl_t *m;stvert_t *st;
    mtriangle_t *tri;maliasskindesc_t *skin;trivertx_t *v;int p=align8(sizeof(*h)),i;
    h->model=p;m=(mdl_t *)(bank+p);p=align8(p+sizeof(*m));
    m->numskins=1;m->skinwidth=m->skinheight=4;m->numverts=3;m->numtris=m->numframes=1;
    m->scale[0]=m->scale[1]=m->scale[2]=1;m->scale_origin[1]=m->scale_origin[2]=-24;
    h->skindesc=p;skin=(maliasskindesc_t *)(bank+p);p=align8(p+sizeof(*skin));
    skin->skin=p;memset(bank+p,200,16);p=align8(p+16);
    h->stverts=p;st=(stvert_t *)(bank+p);p=align8(p+3*sizeof(*st));
    for(i=0;i<3;i++)st[i].s=st[i].t=1<<16;
    h->triangles=p;tri=(mtriangle_t *)(bank+p);p=align8(p+sizeof(*tri));
    tri->facesfront=1;tri->vertindex[0]=0;tri->vertindex[1]=1;tri->vertindex[2]=2;
    h->frames[0].frame=p;v=(trivertx_t *)(bank+p);
    v[0].v[1]=0;v[0].v[2]=0;v[1].v[1]=48;v[1].v[2]=0;v[2].v[1]=24;v[2].v[2]=48;
    /* Normal zero faces away from the directional shade term at yaw zero. */
    actor_model.type=mod_alias;actor_model.radius=40;strcpy(actor_model.name,"actors/test.mdl");
    actor.model=&actor_model;actor.origin[0]=128;actor.colormap=cmap;
    cl_visedicts[0]=&actor;cl_numvisedicts=1;cl.time=10;r_drawentities.value=1;
    aliasxscale=aliasyscale=160;aliasxcenter=160;aliasycenter=100;
    vpn[0]=1;vright[1]=-1;vup[2]=1;
    r_refdef.aliasvrectright=319;r_refdef.aliasvrectbottom=199;
    r_refdef.vrect.width=320;r_refdef.vrect.height=200;
    d_viewbuffer=pixels;d_pzbuffer=depths;screenwidth=320;
    vid.buffer=pixels;vid.width=vid.rowbytes=320;vid.height=200;
    for(i=0;i<200;i++){d_scantable[i]=i*320;zspantable[i]=depths+i*320;}
}
static void light(float distance,float radius,double die){
    int i;memset(cl_dlights,0,sizeof cl_dlights);
    for(i=0;i<MAX_DLIGHTS;i++)cl_dlights[i].die=-1;
    cl_dlights[0].origin[0]=actor.origin[0]+distance;
    cl_dlights[0].radius=radius;cl_dlights[0].die=die;
}
static unsigned int hash_pixels(void){int i;unsigned int h=2166136261U;for(i=0;i<64000;i++)h=(h^pixels[i])*16777619U;return h;}
static int render(const char *name,int expected_ambient,int expected_shade){
    int i,count=0,sum=0,raw_sum=0;unsigned int raw_hash;
    memset(pixels,0,sizeof pixels);memset(depths,0,sizeof depths);draws=0;
    AW_CullBegin();R_DrawEntitiesOnList();assert(draws==1);
#ifndef RECORD_CONTROL
    assert(received.ambientlight==expected_ambient && received.shadelight==expected_shade);
#endif
    for(i=0;i<64000;i++)if(depths[i]){count++;raw_sum+=pixels[i];}
    assert(count>100);raw_hash=hash_pixels();AW_FogDraw();
    for(i=0;i<64000;i++)if(depths[i])sum+=pixels[i];
    printf("%s %d %d %d %d %d %08x %08x\n",name,received.ambientlight,received.shadelight,count,raw_sum,sum,raw_hash,hash_pixels());
    return sum;
}
static void time_of_day(int hour){assert(AW_ClockSetTime(hour,0));R_SetSkyFrame();}
static unsigned int viewmodel(int ambient,int shade){
    int i,n=0;memset(pixels,0,sizeof pixels);memset(depths,0,sizeof depths);draws=0;
    cl.viewent=actor;cl.stats[STAT_HEALTH]=100;r_drawviewmodel.value=1;
    R_DrawViewModel();assert(draws==1 && received.ambientlight==ambient && received.shadelight==shade);
    for(i=0;i<64000;i++)if(depths[i])n++;
    assert(n>100);return hash_pixels();
}
int main(void){
    int i,row,j,phase,off,on;char name[64];model_t world;
    for(i=0;i<256;i++)for(j=0;j<3;j++)palette[3*i+j]=(byte)i;
    for(row=0;row<64;row++)for(i=0;i<256;i++)cmap[row*256+i]=(byte)((i*(63-row)+31)/63);
    for(i=0;i<4096;i++)fog_table[i]=(byte)(i&255);
    host_basepal=palette;AW_StateReset();AW_FogInit();R_InitDayNight();assert(daynight && fog_enabled);
    memset(&world,0,sizeof world);world.entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"exterior\"}";
    R_SetSkyBackground(&world);synthetic_actor();aw_drawdistance.value=540;
    /* Every possible no-local-light input retains the exact legacy clamp. */
    for(j=0;j<=255;j++){
        int ambient=j>128?128:j,shade=j;if(ambient+shade>192)shade=192-ambient;
        world_light=j;light(0,0,-1);snprintf(name,sizeof name,"unlit-%03d",j);render(name,ambient,shade);
    }
    for(phase=0;phase<2;phase++){
        time_of_day(phase?0:12);world_light=255;light(0,0,-1);
        snprintf(name,sizeof name,"phase%d-off",phase);off=render(name,128,64);memcpy(reference,pixels,sizeof pixels);
        light(193,192,10.1);snprintf(name,sizeof name,"phase%d-far",phase);assert(render(name,128,64)==off);assert(!memcmp(reference,pixels,sizeof pixels));
        light(100,192,9.9);snprintf(name,sizeof name,"phase%d-expired",phase);assert(render(name,128,64)==off);assert(!memcmp(reference,pixels,sizeof pixels));
        light(100,192,10.1);snprintf(name,sizeof name,"phase%d-near",phase);on=render(name,220,35);
        memcpy(reference,pixels,sizeof pixels);
        /* All admitted torch keys preserve accepted actor pixels at the
         * default 0.7, including the actual night palette/fog pipeline. */
        for(i=0;i<3;i++){
            cl_dlights[0].key=i?AW_GUARD_TORCH_LIGHT_KEY-(i-1):AW_TORCH_LIGHT_KEY;
            aw_torch_strength.value=.7f;assert(render("torch-default",220,35)==on);
            assert(!memcmp(reference,pixels,sizeof pixels));
            aw_torch_strength.value=0;assert(render("torch-zero",128,64)==off);
            aw_torch_strength.value=.35f;render("torch-half",174,64);
            aw_torch_strength.value=1;render("torch-max",255,0);
        }
        aw_torch_strength.value=.7f;
#ifndef RECORD_CONTROL
        assert(on>off);
#endif
        light(0,192,10.1);snprintf(name,sizeof name,"phase%d-close",phase);render(name,255,0);
        world_light=80;light(100,192,10.1);snprintf(name,sizeof name,"phase%d-litbase",phase);render(name,172,80);
        world_light=0;snprintf(name,sizeof name,"phase%d-darkbase",phase);render(name,92,0);
    }
    world_light=255;light(100,192,10.1);cl_dlights[1]=cl_dlights[0];render("two-lights",255,0);
    gallery_active=1;strcpy(actor_model.name,"gallery/test.mdl");render("gallery",200,0);
    torch_test_active=1;world_light=0;light(0,0,-1);render("dark-room-npc-off",0,0);
    light(100,192,10.1);cl_dlights[0].key=AW_TORCH_LIGHT_KEY;render("dark-room-npc-on",92,0);
    torch_test_active=gallery_active=0;world_light=255;strcpy(actor_model.name,"actors/test.mdl");
    inside=1;light(0,0,-1);render("interior-off",128,64);light(100,192,10.1);render("interior-on",220,35);inside=0;
    daynight->value=0;light(0,0,-1);render("daynight-disabled-off",128,64);light(100,192,10.1);render("daynight-disabled-on",220,35);
#ifndef RECORD_CONTROL
    light(0,INFINITY,10.1);render("invalid-infinite",128,64);
    light(0,NAN,10.1);render("invalid-nan",128,64);
    light(0,3.4e38f,10.1);render("finite-cap",255,0);
#endif
    /* Viewmodel uses its existing stricter 128/192 clamp. The default leaves
     * its actual pixels identical to the legacy local-light calculation. */
    {
        unsigned int original;world_light=64;light(170,192,10.1);original=viewmodel(86,64);
        cl_dlights[0].key=AW_TORCH_LIGHT_KEY;assert(viewmodel(86,64)==original);
        aw_torch_strength.value=0;viewmodel(64,64);
        aw_torch_strength.value=.35f;viewmodel(75,64);
        aw_torch_strength.value=1;viewmodel(95,64);
        light(0,192,10.1);cl_dlights[0].key=AW_TORCH_LIGHT_KEY;viewmodel(128,64);
        aw_torch_strength.value=.7f;
    }
    return 0;
}
