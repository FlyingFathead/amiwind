/* SPDX-License-Identifier: GPL-2.0-or-later
 * Synthetic palette/pixels exercise the real composer and viewport fog. */
#include "quakedef.h"
#include "aw_sky.h"
#include "aw_state.h"
#include "aw_clock.h"
#include <assert.h>
extern int r_backgroundsky;
extern float skytime;
void R_SetSkyFrame(void);
void R_GenSkyTile(void *);
void R_GenSkyTile16(void *);
double realtime;
static int gallery_ms=-1;
int AW_DayGalleryClock(int actual_ms){return gallery_ms<0?actual_ms:gallery_ms;}
byte *host_basepal;
unsigned short d_8to16table[256];
static byte palette[768],tile[128*128],night[128*128],baseline_fog[4096];
static unsigned short tile16[128*128];
static int opens,inside,cloud_fixture,particle_seen,night_fixture;
static cvar_t *enabled,*fog_enabled,*type,*sun_enabled,*clouds_enabled,*cloud_speed,*stars_enabled,*night_enabled;
static int nargs=1;static char *argument="";static void (*type_command)(void),(*speed_command)(void);
server_t sv;
client_state_t cl;
cvar_t sv_gravity={"sv_gravity","800",0,0,800};
float xscaleshrink=1,yscaleshrink=1;
extern particle_t *active_particles,*free_particles;
void R_DrawParticles(void);
void D_StartParticles(void){}void D_EndParticles(void){}
void D_DrawParticle(particle_t *p){particle_seen=(int)p->color;}
viddef_t vid;refdef_t r_refdef;short *d_pzbuffer;unsigned int d_zwidth;
vec3_t vpn={1,0,0},vright={0,-1,0},vup={0,0,1},r_origin;
cvar_t aw_drawdistance={"aw_drawdistance","540",0,0,540};
int AW_Interior(void){return inside;}
void Con_Printf(char *fmt,...){}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);if(!strcmp(c->name,"aw_starsky"))stars_enabled=c;if(!strcmp(c->name,"aw_nightsky"))night_enabled=c;if(!strcmp(c->name,"aw_daynight"))enabled=c;if(!strcmp(c->name,"aw_fog"))fog_enabled=c;if(!strcmp(c->name,"aw_sky_type"))type=c;if(!strcmp(c->name,"aw_sun"))sun_enabled=c;if(!strcmp(c->name,"aw_clouds"))clouds_enabled=c;if(!strcmp(c->name,"aw_skyspeed"))cloud_speed=c;}
void Cvar_SetValue(char *name,float value){if(!strcmp(name,"aw_skyspeed")){cloud_speed->value=value;return;}if(!strcmp(name,"aw_sky_type")){type->value=value;return;}assert(!strcmp(name,"aw_drawdistance"));aw_drawdistance.value=value;}
void Cmd_AddCommand(char *name,void (*fn)(void)){if(!strcmp(name,"aw_sky_type_set"))type_command=fn;if(!strcmp(name,"aw_skyspeed_set"))speed_command=fn;}
int Cmd_Argc(void){return nargs;}char *Cmd_Argv(int n){return n?argument:"aw_sky_type_set";}
byte *COM_LoadHunkFile(char *path){assert(!strcmp(path,"gfx/fog.lmp"));return baseline_fog;}
static unsigned int night_hash(const byte *p,int n){unsigned int h=2166136261U;int i;for(i=0;i<n;i++)h=(h^p[i])*16777619U;return h;}
static void night_word(byte *p,unsigned int n){int i;for(i=0;i<4;i++)p[i]=(byte)(n>>(8*i));}
static int night_file(FILE **file){
    byte raw[AW_NIGHT_SKY_BYTES];int i,payload=night_fixture==5?AW_NIGHT_SKY_PAYLOAD:AW_NIGHT_SKY_ART_BYTES;
    *file=NULL;if(!night_fixture)return -1;
    memcpy(raw,night_fixture==5?"AWN2\200\200\030\010":"AWN1\200\200\030\010",8);
    memset(raw+16,200,16384);memset(raw+16+16384,255,AW_NIGHT_SKY_ART_BYTES-16384);
    for(i=0;i<16;i++){raw[16+16384+i*576+12*24+5]=(byte)(i<8?90+i:180+i-8);raw[16+16384+i*576+11*24+5]=(byte)(i<8?90+i:180+i-8);}
    if(night_fixture>=5){
        /* One original-source star at zenith, otherwise black alpha. */
        memset(raw+16,255,16384);memset(raw+16+AW_NIGHT_SKY_ART_BYTES,0,AW_NIGHT_SKY_STAR_MASK_BYTES);
        i=63*128+63;raw[16+i]=200;raw[16+AW_NIGHT_SKY_ART_BYTES+i/8]|=1<<(i&7);
        i=79*128+88;raw[16+i]=200;raw[16+AW_NIGHT_SKY_ART_BYTES+i/8]|=1<<(i&7);
        /* Nonblack owned artwork is a full texel, not a pin-point. */
        raw[16+63*128+68]=64;
    }
    night_word(raw+8,night_hash(palette,768));night_word(raw+12,night_hash(raw+16,payload));
    if(night_fixture==2)raw[20]^=1;
    if(night_fixture==3)raw[8]^=1;
    *file=tmpfile();assert(*file);assert(fwrite(raw,1,16+payload-(night_fixture==4),*file)==16+payload-(night_fixture==4));
    rewind(*file);return 16+payload;
}
int COM_FOpenFile(char *path,FILE **file){
    int i;if(!strcmp(path,AW_NIGHT_SKY_PATH))return night_file(file);assert(!strcmp(path,AW_SHARED_SKY_PATH));opens++;
    *file=tmpfile();assert(*file);
    for(i=0;i<AW_SHARED_SKY_BYTES;i++){
        int c=(i%256)<128?0:200;
        if(cloud_fixture)c=(i%256)>=128?224:(i%4)==0?0:(i%4)==1?64:200;
        if(cloud_fixture==3 && i==1)c=224;
        if(cloud_fixture==4 && i==1)c=95;
        if(cloud_fixture==5 && i%256>=128 && i%8==4)c=2;
        fputc(c,*file);
    }
    rewind(*file);return AW_SHARED_SKY_BYTES;
}
static void capture(int hour,int minute){assert(AW_ClockSetTime(hour,minute));R_SetSkyFrame();R_GenSkyTile(tile);}
static void uniform(int index){int i;for(i=0;i<sizeof(tile);i++)assert(tile[i]==index);}
static void cloud_speed_control(void){
    static char *valid[]={"0","0.001","0.00333333333","0.01","0.0333333333","1","100"};
    static char *invalid[]={"-1","100.1","nan","NaN","inf","-inf","1oops","","1e309"};
    static float raw_invalid[]={-1,101,INFINITY,NAN};
    aw_state_t saved;float sun[3],value;double seconds;int i;
    assert(cloud_speed && cloud_speed->archive && fabs(cloud_speed->value-1.0f/300)<.00000001f && speed_command);
    capture(12,0);saved=aw_state;memcpy(sun,R_DayNightSunDirection(),sizeof sun);
    seconds=(double)AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:days")*86400+43200;
    nargs=2;
    for(i=0;i<7;i++){
        argument=valid[i];speed_command();value=atof(valid[i]);assert(cloud_speed->value==value);
        R_SetSkyFrame();assert(fabs(skytime-fmod(seconds*value,512))<.0001);
        assert(!memcmp(&saved,&aw_state,sizeof saved));
        assert(!memcmp(sun,R_DayNightSunDirection(),sizeof sun));
    }
    value=cloud_speed->value;
    for(i=0;i<9;i++){argument=invalid[i];speed_command();assert(cloud_speed->value==value);}
    nargs=3;argument="0";speed_command();assert(cloud_speed->value==value);
    nargs=1;speed_command();assert(cloud_speed->value==value);nargs=2;
    argument="0";speed_command();R_SetSkyFrame();assert(skytime==0);
    assert(AW_ClockAdvance(30000));R_SetSkyFrame();assert(skytime==0);
    assert(memcmp(sun,R_DayNightSunDirection(),sizeof sun)); /* only clouds freeze */
    aw_state=saved;
    for(i=0;i<4;i++){
        cloud_speed->value=raw_invalid[i];R_SetSkyFrame();
        assert(fabs(skytime-fmod(seconds/300.0,512))<.0001);
    }
    argument="0.00333333333";speed_command();nargs=1;R_SetSkyFrame();
}
static void cloud_scroll(void){
    model_t m;aw_state_t saved=aw_state;float start;double old_realtime=realtime;
    extern float skyspeed;
    /* Thirty game seconds represent one real second at the shipped scale.
     * This catches the prior 240-texel/sec travel without changing the clock. */
    assert(AW_ClockSetTime(12,0));R_SetSkyFrame();start=skytime;
    assert(AW_ClockAdvance(30000));R_SetSkyFrame();
    assert(fabs((skytime-start)*skyspeed-.8f)<.001f);
    assert(AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms")==43230000);
    start=skytime;realtime+=10000;cl.time=0;R_SetSkyFrame();
    assert(skytime==start); /* frozen clock ignores elapsed host/map time */
    gallery_ms=18*3600000;R_SetSkyFrame();assert(skytime==start);
    assert(R_DayNightSunDirection() && R_DayNightSunDirection()[0]<-.8f);
    assert(AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms")==43230000);
    gallery_ms=-1;R_SetSkyFrame();assert(skytime==start);
    assert(R_DayNightSunDirection() && R_DayNightSunDirection()[2]>.9f);
    memset(&m,0,sizeof m);m.entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"interior\"}";
    R_SetSkyBackground(&m);R_SetSkyFrame();assert(skytime==start);
    m.entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"exterior\"}";
    R_SetSkyBackground(&m);R_SetSkyFrame();assert(skytime==start);
    assert(AW_ClockSetTime(23,59));R_SetSkyFrame();start=skytime;
    assert(AW_ClockAdvance(60000));R_SetSkyFrame();
    assert(fabs(skytime-start-.2f)<.0001f); /* no midnight seam */
    cloud_speed->value=.001f;
    AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:days",5);
    AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:ms",79999000);
    R_SetSkyFrame();assert(fabs(skytime-511.999f)<.0001f);
    assert(AW_ClockAdvance(2000));R_SetSkyFrame();assert(fabs(skytime-.001f)<.0001f);
    /* Restore the same saved globals rather than starting another timebase. */
    cloud_speed->value=.00333333333f;
    aw_state=saved;realtime=old_realtime;R_SetSkyFrame();
    start=skytime;assert(AW_ClockAdvance(3600000));R_SetSkyFrame();
    assert(fabs(fmod(skytime-start+512,512)-12)<.0002f);
    aw_state=saved;R_SetSkyFrame();assert(skytime==start);
}
static void fog_projection(void){
    byte storage[19],*pixels=storage+2;short depths[15];int i;byte sky,far;
    const byte *fog;
    vpn[0]=0;vpn[1]=1;vright[0]=-1;vright[1]=0;
    capture(6,0);sky=tile[0];fog=R_DayNightFogColours();assert(fog);far=fog[15*256];
    assert(palette[3*far]>palette[3*far+1]);
    for(i=0;i<256;i++){assert(fog[i]==i);assert(fog[15*256+i]==far);}
    memset(storage,77,sizeof storage);memset(pixels,sky,15);
    for(i=0;i<15;i++)depths[i]=AW_SKY_BACKGROUND_DEPTH;
    vid.buffer=pixels;vid.rowbytes=vid.width=5;vid.height=3;d_pzbuffer=depths;d_zwidth=5;
    r_refdef.vrect.width=5;r_refdef.vrect.height=3;
    pixels[5]=7;depths[5]=32767;pixels[6]=8;depths[6]=0;pixels[8]=9;depths[8]=-1;
    AW_FogDraw();
    assert(storage[0]==77 && storage[1]==77 && storage[17]==77 && storage[18]==77);
    assert(pixels[0]==sky && pixels[5]==7);
    assert(pixels[6]==far && pixels[7]==far && pixels[8]==far && pixels[12]==far);
    for(i=0;i<15;i++)depths[i]=AW_SKY_BACKGROUND_DEPTH;
    memset(pixels,sky,15);vpn[1]=.8660254f;vpn[2]=.5f;vup[1]=-.5f;vup[2]=.8660254f;
    AW_FogDraw();assert(pixels[7]==sky); /* pitch moves the horizon */
    vpn[1]=1;vpn[2]=0;vup[0]=-1;vup[1]=0;vup[2]=0;vright[0]=0;vright[2]=1;
    memset(pixels,sky,15);AW_FogDraw();assert(pixels[5]==far && pixels[9]==sky); /* roll */
    vup[0]=0;vup[2]=1;vright[0]=-1;vright[2]=0;
    memset(pixels,7,15);inside=1;AW_FogDraw();for(i=0;i<15;i++)assert(pixels[i]==7);inside=0;
    fog_enabled->value=0;AW_FogDraw();for(i=0;i<15;i++)assert(pixels[i]==7);fog_enabled->value=1;
    capture(0,0);fog=R_DayNightFogColours();assert(fog[15*256]!=far);
}
static byte sample(int index,float x,float y,float z){return R_DayNightSkyPixel(index,x,y,z,1);}
static int red(byte i){return palette[3*i];}
static int green(byte i){return palette[3*i+1];}
static int blue(byte i){return palette[3*i+2];}
static void type2_and_sun(void){
    const float *sun;float frozen[3],rise[3];byte upper,middle,horizon,cool,hot,gold,low_sun,old[16];
    byte pixels[3];short z[3];int i,band,minute,changed;aw_state_t saved;
    nargs=2;argument="2";type_command();assert(type->value==2);
    argument="V1";type_command();assert(type->value==1);argument="v2";type_command();assert(type->value==2);
    argument="V3";type_command();assert(type->value==3);argument="2";type_command();assert(type->value==2);
    for(i=0;i<4;i++){argument=i==0?"0":i==1?"4":i==2?"NaN":"1.5";type_command();assert(type->value==2);}
    nargs=3;argument="1";type_command();assert(type->value==2);nargs=1;type_command();nargs=1;
    /* No clock resets or new resources when switching palette profiles. */
    capture(18,0);saved=aw_state;uniform(200);
    type->value=1;R_SetSkyFrame();assert(!memcmp(&saved,&aw_state,sizeof saved));
    type->value=2;R_SetSkyFrame();assert(!memcmp(&saved,&aw_state,sizeof saved));
    upper=sample(0,0,1,1);middle=sample(255,0,1,.14f);horizon=sample(255,0,1,0);
    assert(blue(upper)>green(upper));assert(red(middle)>green(middle)+70 && red(middle)>blue(middle));
    assert(horizon==R_DayNightFogColours()[15*256]);
    assert(sample(0,0,1,.14f)!=middle); /* source cloud contrast retained */
    /* An already bright red cloud can quantize to the same entry. Across the
     * source ramp, the sun-facing sector must still be a distinct mapping. */
    changed=0;for(i=0;i<256;i++)if(sample(i,-1,0,.07f)!=sample(i,1,0,.07f))changed++;
    assert(changed>0); /* warm west-facing haze, not a global flat wash */
    hot=middle;capture(20,0);cool=sample(255,0,1,.14f);assert(blue(cool)>red(cool) && red(cool)<red(hot));
    capture(4,30);assert(sample(255,0,1,.14f)==cool);
    capture(6,0);assert(sample(255,0,1,.14f)==hot);assert(!R_DayNightSunDirection());
    capture(7,0);gold=sample(255,0,1,.14f);assert(green(gold)>green(hot));
    capture(17,0);assert(sample(255,0,1,.14f)==gold);
    capture(19,45);assert(sample(255,0,1,.14f)==cool);
    capture(20,30);assert(sample(255,0,1,.14f)==cool);
    cool=R_DayNightFogColours()[255];assert(blue(cool)>red(cool));
    capture(23,0);cool=R_DayNightFogColours()[255];assert(red(cool)<255 && green(cool)<255 && blue(cool)>red(cool));
    type->value=1;R_SetSkyFrame();assert(R_DayNightFogColours()[255]==255);
    type->value=2;capture(12,0);for(i=0;i<256;i++)assert(R_DayNightFogColours()[i]==i);
    assert(sample(200,0,1,-1000)==sample(200,0,1,-1));
    assert(sample(200,0,1,1000)==sample(200,0,1,1));
    assert(sample(200,0,1,NAN)==200);
    /* Stable noon/night RGB and Type1 fallback survive repeated switching. */
    for(i=0;i<2;i++){
        type->value=1;capture(i?23:12,0);
        for(band=0;band<16;band++)old[band]=sample(tile[0],0,1,band*.35f/15);
        type->value=2;R_SetSkyFrame();R_GenSkyTile(tile);uniform(200);
        for(band=0;band<16;band++)assert(sample(tile[0],0,1,band*.35f/15)==old[band]);
    }
    type->value=2;
    /* Exact key points and intervening samples are bounded, not a hue toggle. */
    for(minute=0;minute<1440;minute+=15){
        capture(minute/60,minute%60);
        for(band=0;band<16;band++)(void)sample(band*17,0,1,band*.35f/15);
    }
    capture(6,30);sun=R_DayNightSunDirection();assert(sun && sun[0]>.9f && sun[1]<0 && sun[2]>0);memcpy(rise,sun,sizeof rise);
    low_sun=sample(0,sun[0],sun[1],sun[2]);assert(red(low_sun)>green(low_sun)+50);
    capture(13,0);sun=R_DayNightSunDirection();assert(sun && fabs(sun[0])<.0001f && sun[1]<0 && sun[2]>.98f);
    assert(green(sample(0,sun[0],sun[1],sun[2]))>green(low_sun));
    memcpy(frozen,sun,sizeof frozen);saved=aw_state;R_SetSkyFrame();assert(!memcmp(frozen,R_DayNightSunDirection(),sizeof frozen));assert(!memcmp(&saved,&aw_state,sizeof saved));
    assert(AW_ClockAdvance(3600000));R_SetSkyFrame();sun=R_DayNightSunDirection();assert(sun && sun[0]<0 && sun[2]<frozen[2]);
    capture(19,30);sun=R_DayNightSunDirection();assert(sun && sun[0]<-.9f && fabs(sun[2]-rise[2])<.0001f);
    capture(20,0);assert(!R_DayNightSunDirection());capture(5,59);assert(!R_DayNightSunDirection());
    /* The actual fog pass accepts only the semantic sky depth. Geometry at the
     * same screen point is untouched near the camera, including sprite writes. */
    capture(13,0);sun=R_DayNightSunDirection();for(i=0;i<3;i++)vpn[i]=sun[i];
    vright[0]=1;vright[1]=vright[2]=0;vup[0]=0;vup[1]=1;vup[2]=0;
    vid.buffer=pixels;vid.rowbytes=vid.width=3;vid.height=1;d_pzbuffer=z;d_zwidth=3;
    r_refdef.vrect.x=r_refdef.vrect.y=0;r_refdef.vrect.width=3;r_refdef.vrect.height=1;
    for(i=0;i<3;i++){pixels[i]=200;z[i]=AW_SKY_BACKGROUND_DEPTH;}
    z[0]=32767;AW_FogDraw();assert(pixels[0]==200);assert(pixels[1]==sample(200,sun[0],sun[1],sun[2]));
    assert(pixels[1]!=sample(200,-sun[0],-sun[1],-sun[2]));
    z[1]=32767;pixels[1]=77;AW_FogDraw();assert(pixels[1]==77);
    fog_enabled->value=0;z[1]=AW_SKY_BACKGROUND_DEPTH;pixels[1]=200;AW_FogDraw();assert(pixels[1]==sample(200,sun[0],sun[1],sun[2]));fog_enabled->value=1;
    enabled->value=0;R_SetSkyFrame();assert(!R_DayNightSunDirection());assert(sample(200,1,0,0)==200);enabled->value=1;
    type->value=1;capture(18,0);
}

static void cloud_roles(void){
    static const byte indices[7]={222,133,95,156,140,83,221};
    static const byte safe[7]={223,113,94,158,138,82,223};
    byte clear,dark,bright;int i,nclear=0,ndark=0,nbright=0,ms;particle_t p,before;
    const float *sun;fixed16_t s,t;float initial_sun[3];
    extern float skyspeed;
    void D_Sky_uv_To_st(int,int,fixed16_t *,fixed16_t *);
    type->value=2;capture(18,0);
    for(i=0;i<sizeof tile;i++){
        nclear+=tile[i]==224;ndark+=tile[i]==64;nbright+=tile[i]==200;
    }
    assert(nclear && ndark && nbright); /* masked holes retain the opaque base */
    clear=sample(224,0,1,.14f);dark=sample(64,0,1,.14f);bright=sample(200,0,1,.14f);
    if(cloud_fixture==1 || cloud_fixture==5){
        assert(blue(clear)>red(clear) && blue(clear)>green(clear));
        assert(red(dark)>green(dark)+50 && red(dark)>blue(dark));
        assert(red(bright)>red(dark) && green(bright)>green(dark));
        assert(sample(64,0,1,0)==sample(224,0,1,0)); /* same fog horizon */
        type->value=1;capture(12,0);assert(tile[0]!=224);
    }else{
        /* Missing marker preserves V1; overlapping/output indices reject role decoding. */
        type->value=1;capture(12,0);
        for(i=0;i<sizeof tile;i++)assert(tile[i]==224 || tile[i]==64 || tile[i]==200 || tile[i]==95);
    }
    /* The real sampler changes scale only with validated source roles. */
    vid.width=r_refdef.vrect.width=320;vid.height=r_refdef.vrect.height=200;
    vpn[0]=1;vpn[1]=vpn[2]=0;vright[0]=vright[2]=0;vright[1]=1;
    vup[0]=vup[1]=0;vup[2]=1;
    D_Sky_uv_To_st(160,100,&s,&t);
    assert(r_sky_texture_scale==((cloud_fixture==3 || cloud_fixture==4)?378:128));
    /* Engine normalisation intentionally uses approximate inverse sqrt. */
    assert(fabs(s/65536.0-skytime*skyspeed-r_sky_texture_scale)<1);
    /* Cloud removal retains atmosphere and sun, then restores both source
     * layers without requiring time or scroll to change. V1 also invalidates. */
    for(i=1;i<=3;i++){
        type->value=i;capture(18,0);memcpy(night,tile,sizeof tile);
        clouds_enabled->value=0;R_SetSkyFrame();R_GenSkyTile(tile);uniform(tile[0]);
        if(i>=2)uniform(224);
        assert(R_DayNightSunDirection());
        clouds_enabled->value=1;R_SetSkyFrame();R_GenSkyTile(tile);assert(!memcmp(night,tile,sizeof tile));
    }
    if(cloud_fixture==5){
        type->value=2;capture(18,0);bright=sample(2,0,1,.07f);
        type->value=3;R_SetSkyFrame();dark=sample(2,0,1,.07f);
        assert(red(dark)+green(dark)+blue(dark)<(red(bright)+green(bright)+blue(bright))/2);
        assert(red(sample(200,0,1,.14f))>green(sample(200,0,1,.14f)));
    }
    type->value=2;capture(20,0);
    if(cloud_fixture==1 || cloud_fixture==5){
        assert(sample(224,0,1,.14f)==133);
        assert(R_DayNightFogColours()[15*256]==133);
    }
    capture(18,0);sun=R_DayNightSunDirection();assert(sun);memcpy(initial_sun,sun,sizeof initial_sun);
    if(cloud_fixture==1 || cloud_fixture==5){
        bright=sample(224,sun[0],sun[1],sun[2]);assert(green(bright)>=200);
    }
    ms=AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms");sun_enabled->value=0;
    assert(AW_ClockAdvance(3600000));R_SetSkyFrame();assert(!R_DayNightSunDirection());
    assert(AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms")==ms+3600000);
    sun_enabled->value=1;R_SetSkyFrame();sun=R_DayNightSunDirection();assert(sun && memcmp(initial_sun,sun,sizeof initial_sun));
    for(i=0;i<7;i++){
        assert(R_SkyLegacyColour(indices[i])==(cloud_fixture==2?indices[i]:safe[i]));
        memset(&p,0,sizeof p);p.color=indices[i];p.die=1;p.type=pt_static;before=p;
        active_particles=&p;free_particles=NULL;particle_seen=-1;R_DrawParticles();
        assert(particle_seen==(cloud_fixture==2?indices[i]:safe[i]));
        assert(!memcmp(&p,&before,sizeof p)); /* draw does not poison later ramp updates */
    }
    assert(R_SkyLegacyColour(254)==254 && R_SkyLegacyColour(224)==224);
}
static void point_star_checks(model_t *model){
    static byte pixels[640*400];static short depth[640*400];
    const float *moon;int i,j,w,h,n,count,cx,cy,point,art,other;byte no_stars;
    type->value=3;AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:days",0);capture(23,0);
    clouds_enabled->value=0;fog_enabled->value=0;
    vpn[0]=vpn[1]=0;vpn[2]=1;vright[0]=1;vright[1]=vright[2]=0;vup[1]=1;vup[0]=vup[2]=0;
    for(j=1;j<=2;j++){
        w=320*j;h=200*j;n=w*h;cx=w/2;cy=h/2;point=cy*w+cx;
        vid.buffer=pixels;vid.width=vid.rowbytes=w;vid.height=h;d_pzbuffer=depth;d_zwidth=w;
        r_refdef.vrect.x=r_refdef.vrect.y=0;r_refdef.vrect.width=w;r_refdef.vrect.height=h;
        memset(pixels,224,n);for(i=0;i<n;i++)depth[i]=AW_SKY_BACKGROUND_DEPTH;
        AW_FogDraw();count=0;for(i=0;i<n;i++)if(red(pixels[i])>100 && green(pixels[i])>100 && blue(pixels[i])>100)count++;
        assert(count==1 && red(pixels[point])>100); /* exactly one native pixel at both resolutions */
        art=0;for(i=0;i<n;i++)if(pixels[i]==64)art++;assert(art>1); /* nebula/art extent retained */
        stars_enabled->value=0;no_stars=sample(224,0,0,1);stars_enabled->value=1;
        assert(sample(224,.006f,0,1)==no_stars); /* same coarse cell, outside point */
        clouds_enabled->value=1;assert(red(sample(64,0,0,1))<150);clouds_enabled->value=0;
        memset(pixels,224,n);pixels[point]=77;depth[point]=32767;AW_FogDraw();assert(pixels[point]==77);
        memset(pixels,224,n);pixels[point]=78;depth[point]=123;AW_FogDraw();assert(pixels[point]==78);
        /* A masked foliage hole has semantic sky depth and reveals the point. */
        depth[point]=AW_SKY_BACKGROUND_DEPTH;pixels[point]=224;AW_FogDraw();assert(red(pixels[point])>100);
    }
    /* Every dark/unlit moon interior restores pre-star background. Legacy
     * and AWN2 use the same opaque complete disc test. */
    for(j=0;j<2;j++){
        moon=R_DayNightMoonDirection(j);assert(moon);
        stars_enabled->value=0;no_stars=sample(224,moon[0],moon[1],moon[2]);stars_enabled->value=1;
        assert(sample(224,moon[0],moon[1],moon[2])==no_stars);
    }
    /* A known marked point behind Masser's dark centre is really suppressed,
     * then becomes visible at the identical sky coordinate after its orbit moves. */
    {
        float star[3]={25.0f/63,-16.0f/63,22.0f/63};
        float horizontal;
        VectorCopy(star,vpn);VectorNormalize(vpn);
        horizontal=(float)sqrt(vpn[0]*vpn[0]+vpn[1]*vpn[1]);
        vright[0]=-vpn[1]/horizontal;vright[1]=vpn[0]/horizontal;vright[2]=0;
        vup[0]=-vpn[0]*vpn[2]/horizontal;vup[1]=-vpn[1]*vpn[2]/horizontal;vup[2]=horizontal;
        assert(red(sample(224,star[0],star[1],star[2]))<100);
        AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:days",6);R_SetSkyFrame();
        assert(red(sample(224,star[0],star[1],star[2]))>100);
        AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:days",0);R_SetSkyFrame();
    }
    night_enabled->value=0;R_SetSkyFrame();assert(sample(224,0,0,1)==no_stars || red(sample(224,0,0,1))<150);
    night_enabled->value=1;R_SetSkyFrame();
    model->entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"interior\"}";
    R_SetSkyBackground(model);R_SetSkyFrame();assert(sample(224,0,0,1)==224);
}
static void orbit_preview_checks(void){
    static const int minutes[]={0,1,59,240,1380,1439};
    int day,t,m,i,phase,visible,below=0;float direction[3],negative[3];const float *rendered;
    aw_state_t saved=aw_state,at_preview;
    /* The helper must work before any sky frame at the requested time, not
     * read cached directions from the previous daytime frame. */
    capture(12,0);assert(!R_DayNightMoonDirection(0));
    for(day=0;day<48;day++)for(t=0;t<sizeof(minutes)/sizeof(minutes[0]);t++){
        AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:days",day);
        gallery_ms=minutes[t]*60000;at_preview=aw_state;
        for(m=0;m<2;m++){
            visible=R_NightMoonOrbit(m,gallery_ms,day,direction,&phase);
            assert(phase>=0 && phase<8 && !memcmp(&aw_state,&at_preview,sizeof aw_state));
            if(visible){double norm=0;for(i=0;i<3;i++)norm+=(double)direction[i]*direction[i];assert(fabs(norm-1)<.000001);}
            else{below++;assert(direction[2]<=0);}
            R_SetSkyFrame();rendered=R_DayNightMoonDirection(m);
            assert((rendered!=NULL)==visible);
            if(visible)assert(!memcmp(direction,rendered,sizeof direction));
        }
        assert(!memcmp(&aw_state,&at_preview,sizeof aw_state));
    }
    assert(below>0);gallery_ms=-1;
    assert(R_NightMoonOrbit(0,23*3600000,0,direction,&phase) && phase==0);
    assert(fabs(direction[0]-.68255314f)<.000001 && fabs(direction[1]+.41919028795f)<.000001 && fabs(direction[2]-.59866577418f)<.000001);
    assert(R_NightMoonOrbit(0,23*3600000,-1,negative,NULL) && !memcmp(direction,negative,sizeof direction));
    assert(!R_NightMoonOrbit(-1,0,0,direction,&phase) && direction[2]==-1 && phase==0);
    assert(!R_NightMoonOrbit(2,0,0,direction,NULL));
    assert(!R_NightMoonOrbit(0,-1,0,direction,NULL));
    assert(!R_NightMoonOrbit(0,86400000,0,direction,NULL));
    aw_state=saved;R_SetSkyFrame();
}
static void night_checks(model_t *model){
    const float *moon;float direction[3];byte clear,cloud,disc;int m,i,changed=0;aw_state_t saved;
    type->value=3;AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:days",0);capture(23,0);
    if(night_fixture>1){assert(!R_DayNightMoonDirection(0) && !R_DayNightMoonDirection(1));return;}
    orbit_preview_checks();
    assert(stars_enabled && night_enabled && stars_enabled->archive && night_enabled->archive && stars_enabled->value==1 && night_enabled->value==1);
    assert(R_DayNightMoonDirection(0) && R_DayNightMoonDirection(1));
    clear=sample(224,0,1,1);cloud=sample(64,0,1,1);assert(clear!=cloud);
    clouds_enabled->value=0;assert(sample(64,0,1,1)==clear);clouds_enabled->value=1;
    for(m=0;m<2;m++){
        moon=R_DayNightMoonDirection(m);memcpy(direction,moon,sizeof direction);
        disc=sample(224,moon[0],moon[1],moon[2]);assert(disc!=200);
        /* All phase centres in this fixture are transparent: the full disc
         * must still occlude the bright star field behind its unlit portion. */
        assert(red(disc)<100 && green(disc)<100 && blue(disc)<100);
        assert(sample(64,moon[0],moon[1],moon[2])!=200);
    }
    /* Read an actual lit atlas texel through each billboard projection.
     * The isolated left-of-centre texel identifies both moon and phase. */
    for(i=0;i<2;i++){
        float horizontal,rightx,righty,radius;byte expected;
        if(i)AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:days",3);
        capture(23,0);moon=R_DayNightMoonDirection(0);assert(moon);
        horizontal=(float)sqrt(moon[0]*moon[0]+moon[1]*moon[1]);
        rightx=-moon[1]/horizontal;righty=moon[0]/horizontal;radius=.11f;
        expected=(byte)(90+i);
        assert(sample(224,moon[0]-.54f*radius*rightx,moon[1]-.54f*radius*righty,moon[2])==expected);
    }
    AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:days",0);capture(23,0);
    moon=R_DayNightMoonDirection(1);assert(moon);
    {
        float horizontal=(float)sqrt(moon[0]*moon[0]+moon[1]*moon[1]);
        assert(sample(224,moon[0]+.54f*.04680851f*moon[1]/horizontal,
            moon[1]-.54f*.04680851f*moon[0]/horizontal,moon[2])==180);
    }
    stars_enabled->value=0;clear=sample(224,0,1,1);assert(clear!=200);
    assert(R_DayNightMoonDirection(0));stars_enabled->value=1;
    night_enabled->value=0;R_SetSkyFrame();assert(!R_DayNightMoonDirection(0));
    assert(sample(224,0,1,1)==clear);night_enabled->value=1;R_SetSkyFrame();
    AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:days",12);capture(23,0);
    moon=R_DayNightMoonDirection(0);assert(moon);
    disc=sample(224,moon[0],moon[1],moon[2]);assert(red(disc)<100 && green(disc)<100 && blue(disc)<100);
    AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:days",0);capture(23,0);
    assert(!R_DayNightMoonDirection(-1) && !R_DayNightMoonDirection(2));
    saved=aw_state;clear=sample(224,.15f,.8f,.6f);R_SetSkyFrame();assert(clear==sample(224,.15f,.8f,.6f));
    for(i=0;i<64;i++){
        byte before;float x=(i-32)/40.0f;
        aw_state=saved;R_SetSkyFrame();before=sample(224,x,1,1);
        assert(AW_ClockAdvance(240000));R_SetSkyFrame();changed+=before!=sample(224,x,1,1);
    }
    assert(changed>0 && changed<64);aw_state=saved;R_SetSkyFrame();
    assert(clear==sample(224,.15f,.8f,.6f));
    capture(23,59);moon=R_DayNightMoonDirection(0);assert(moon);memcpy(direction,moon,sizeof direction);
    assert(AW_ClockAdvance(60000));R_SetSkyFrame();moon=R_DayNightMoonDirection(0);assert(moon);
    for(i=0;i<3;i++)assert(fabs(moon[i]-direction[i])<.004f); /* no midnight orbit reset */
    type->value=1;capture(19,0);assert(!R_DayNightMoonDirection(0));
    capture(23,0);assert(R_DayNightMoonDirection(0));night_enabled->value=0;R_SetSkyFrame();R_GenSkyTile(tile);
    assert(!R_DayNightMoonDirection(0));night_enabled->value=1;R_SetSkyFrame();R_GenSkyTile(tile);
    assert(R_DayNightMoonDirection(0));type->value=3;
    AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:days",0);capture(23,0);
    /* Looking below the true world horizon has no celestial overlay. */
    assert(sample(224,0,1,-.5f)==R_DayNightFogColours()[15*256]);
    capture(12,0);assert(!R_DayNightMoonDirection(0));
    assert(sample(224,0,1,1)!=200); /* no original night field in daylight */
    capture(23,0);model->entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"interior\"}";
    R_SetSkyBackground(model);R_SetSkyFrame();assert(!R_DayNightMoonDirection(0));assert(sample(224,0,1,1)==224);
    model->entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"exterior\"}";
    R_SetSkyBackground(model);R_SetSkyFrame();assert(opens==1 && R_DayNightMoonDirection(0));
    /* Opaque world/sprite depth survives even when a moon is behind it. */
    {
        byte pixels[3]={77,224,224};short depth[3]={32767,AW_SKY_BACKGROUND_DEPTH,AW_SKY_BACKGROUND_DEPTH};
        moon=R_DayNightMoonDirection(0);for(i=0;i<3;i++)vpn[i]=moon[i];
        vid.buffer=pixels;vid.rowbytes=vid.width=3;vid.height=1;d_pzbuffer=depth;d_zwidth=3;
        r_refdef.vrect.x=r_refdef.vrect.y=0;r_refdef.vrect.width=3;r_refdef.vrect.height=1;
        fog_enabled->value=0;AW_FogDraw();assert(pixels[0]==77);
    }
}

int main(int argc,char **argv){
    model_t m;int i,warm,dark;float phase;aw_state_t saved;
    for(i=0;i<256;i++){
        palette[3*i]=((i>>5)&7)*255/7;palette[3*i+1]=((i>>2)&7)*255/7;palette[3*i+2]=(i&3)*85;
        d_8to16table[i]=i*7;
    }
    if(argc==2){
        static const byte indices[7]={222,133,95,156,140,83,221};
        static const byte rgb[7][3]={{100,69,138},{52,73,110},{210,50,34},{250,104,45},{255,174,66},{255,232,160},{153,38,79}};
        cloud_fixture=atoi(argv[1]);assert(cloud_fixture>=1 && cloud_fixture<=11);if(cloud_fixture>=6){night_fixture=cloud_fixture-5;cloud_fixture=1;}
        for(i=0;i<7;i++)memcpy(palette+3*indices[i],rgb[i],3);
        palette[3*224]=102;palette[3*224+1]=119;palette[3*224+2]=136;
        for(i=0;i<3;i++){palette[3*64+i]=30;palette[3*200+i]=240;}
        if(cloud_fixture==2)palette[3*indices[0]]++; /* fail exact marker */
    }
    host_basepal=palette;AW_StateReset();AW_FogInit();R_InitDayNight();
    assert(enabled && enabled->value==1 && enabled->archive);
    assert(sun_enabled && sun_enabled->value==1 && sun_enabled->archive);
    assert(clouds_enabled && clouds_enabled->value==1 && clouds_enabled->archive);
    assert(type && type->value==3 && type->archive && type_command);type->value=1;
    memset(&m,0,sizeof m);m.entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"exterior\"}";
    R_SetSkyBackground(&m);assert(r_backgroundsky && opens==1);
    if(night_fixture>=5){point_star_checks(&m);return 0;}
    if(night_fixture){night_checks(&m);return 0;}
    cloud_speed_control();cloud_scroll();
    if(cloud_fixture){cloud_roles();return 0;}
    for(i=0;i<256;i++)assert(R_SkyLegacyColour(i)==i);
    capture(12,0);uniform(200);phase=skytime;
    capture(22,40);dark=tile[0];uniform(dark);assert(dark!=200 && skytime!=phase);
    memcpy(night,tile,sizeof tile);saved=aw_state;
    R_SetSkyFrame();R_GenSkyTile(tile);assert(!memcmp(night,tile,sizeof tile) && !memcmp(&saved,&aw_state,sizeof saved));
    enabled->value=0;R_SetSkyFrame();R_GenSkyTile(tile);uniform(200);assert(!R_DayNightFogColours() && !memcmp(&saved,&aw_state,sizeof saved));
    enabled->value=1;R_SetSkyFrame();R_GenSkyTile(tile);uniform(dark);
    capture(6,0);warm=tile[0];uniform(warm);assert(warm!=dark);
    /* Intermediate phases map uniform source uniformly: old Bayer fails. */
    for(i=300;i<=1200;i+=3){capture(i/60,i%60);uniform(tile[0]);}
    capture(19,0);R_GenSkyTile16(tile16);for(i=0;i<sizeof tile;i++)assert(tile16[i]==d_8to16table[tile[i]]);
    capture(23,59);memcpy(night,tile,sizeof tile);assert(AW_ClockAdvance(60000));R_SetSkyFrame();R_GenSkyTile(tile);assert(!memcmp(night,tile,sizeof tile));
    saved=aw_state;m.entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"interior\"}";
    R_SetSkyBackground(&m);assert(!r_backgroundsky && !R_DayNightFogColours());R_SetSkyFrame();R_GenSkyTile(tile);uniform(200);
    m.entities="{\"classname\" \"worldspawn\" \"_aw_sky_mode\" \"exterior\"}";R_SetSkyBackground(&m);R_SetSkyFrame();R_GenSkyTile(tile);uniform(dark);
    assert(opens==1 && !memcmp(&saved,&aw_state,sizeof saved));
    fog_projection();type2_and_sun();
    m.entities="{\"classname\" \"worldspawn\"}";R_SetSkyBackground(&m);R_SetSkyFrame();R_GenSkyTile(tile);uniform(200);assert(!R_DayNightFogColours());
    return 0;
}
