/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_demowind.c: DemoWind, the effects test kit (docs/DEMOWIND.md; the maintainer, desktop chat 2026-10-28: a
 * fullscreen AGA set of cheap effects, no world, browsed one after another, each with its cost on screen).
 *
 * dbg demowind [on / off / next / prev / dist 0-7 / status]: while on, the world is not drawn; the whole screen is
 * the effect. Keys: Right / N next effect, Left / P previous, Up / Down the distance step, Esc leaves.
 *
 * Effects (both are Quake's own two-layer scrolling sky: a solid back layer and a holed cloud layer at another speed,
 * composed into one 128x128 tile per frame, then one lookup per screen pixel, as r_sky.c R_MakeSky + d_sky.c do):
 *   1 the plain sky: the game's Clear weather colours and cloud speed (Morrowind.ini [Weather Clear]);
 *   2 the Red Mountain sky: a dark blood-red back layer and fast blight/ash clouds, with a palette shift by the
 *     distance to the mountain in eight steps (0 Seyda Neen .. 7 the crater): the colours and cloud speeds of the
 *     game's own data, read from Morrowind.esm and Morrowind.ini in a container on 2026-10-28: the Red Mountain
 *     region's weather is Blight 100 % (REGN WEAT), the Ashlands' Ashstorm 30 %; [Weather Blight] Sky Day 90,35,35,
 *     Sky Night 44,14,14, Fog Day 128,19,19, Sun Day 224,84,84, Cloud Speed 9; [Weather Ashstorm] Sky Day 124,73,58;
 *     [Weather Clear] Sky Day 95,135,203, Fog Day 206,227,255, Sun Day 255,252,238, Cloud Speed 1.25.
 * The textures are our own, made here from seeded value noise (no picture from any game). A step change bakes the
 * palette shift into the two index tiles (32,768 table lookups, once), so the per-frame work of the two effects is
 * the same: the cost shown is measured, never estimated. Nothing is resident until dbg demowind on; off frees it. */
#include "quakedef.h"
#include "aw_tryalloc.h"

byte R_SkyNearest(int r,int g,int b);	/* r_sky.c */

#define DW_SIZE 128
#define DW_TILE (DW_SIZE*DW_SIZE)
#define DW_STEPS 8
#define DW_AVG 32
#define DW_EFFECTS 2

typedef struct {
    byte *noise_back,*noise_cloud;	/* our own texture sources, 0..255 */
    byte *back,*cloud,*tile;		/* palette-index tiles: back layer, cloud layer (0 = hole), the composed sky */
    byte lut_back[64],lut_cloud[64];
    int on,effect,step,baked_effect,baked_step,frames;
    double start,sum,avg[DW_EFFECTS],bake_ms;
    int avg_frames[DW_EFFECTS],logged[DW_EFFECTS][DW_STEPS];
    float speed,coverage;
} dw_t;
static dw_t dw;
static const char *dw_names[DW_EFFECTS]={"PLAIN SKY (CLEAR WEATHER)","RED MOUNTAIN SKY (BLIGHT)"};
static const char *dw_places[DW_STEPS]={"Seyda Neen","Ascadian Isles","Ashlands edge","Ald'ruhn",
    "Ghostfence outside","Ghostfence","inner slopes","the crater"};

/* ---- our own textures: tileable value noise ---- */
static unsigned dw_hash(int x,int y,int seed)
{
    unsigned h=(unsigned)(x*374761393+y*668265263+seed*1442695041);
    h=(h^(h>>13))*1274126177u;
    return (h^(h>>16))&255;
}
static int dw_value(int x,int y,int period,int seed)
{
    int cell=DW_SIZE/period,x0=x/cell,y0=y/cell,fx=(x%cell)*256/cell,fy=(y%cell)*256/cell;
    int x1=(x0+1)%period,y1=(y0+1)%period,a,b,c,d,top,bottom;
    fx=fx*fx*(768-2*fx)/65536;fy=fy*fy*(768-2*fy)/65536;	/* smoothstep */
    a=dw_hash(x0,y0,seed);b=dw_hash(x1,y0,seed);c=dw_hash(x0,y1,seed);d=dw_hash(x1,y1,seed);
    top=a*256+(b-a)*fx;bottom=c*256+(d-c)*fx;
    return (top*256+(bottom-top)*fy)>>16;
}
static void dw_make_noise(void)
{
    int x,y,v;
    for(y=0;y<DW_SIZE;y++)for(x=0;x<DW_SIZE;x++){
        v=(dw_value(x,y,4,7)*2+dw_value(x,y,8,11))/3;
        dw.noise_back[y*DW_SIZE+x]=(byte)v;
        /* billowing ash: four octaves, the fine ones weaker */
        v=(dw_value(x,y,4,3)*8+dw_value(x,y,8,5)*4+dw_value(x,y,16,9)*2+dw_value(x,y,32,13))/15;
        dw.noise_cloud[y*DW_SIZE+x]=(byte)v;
    }
}

/* ---- colours: the game's weather data, mixed by the distance step ---- */
static void dw_mix(const int *a,const int *b,int m,int out[3]) {int k;for(k=0;k<3;k++)out[k]=(a[k]*(256-m)+b[k]*m)/256;}
static void dw_ramp(byte *lut,const int lo[3],const int hi[3],int bands)
{
    int i,k,f,rgb[3];
    for(i=0;i<64;i++){
        f=bands?((i*bands/64)*63/(bands-1>0?bands-1:1)):i;	/* bands: hard-edged steps, the steep contrast */
        if(f>63)f=63;
        for(k=0;k<3;k++)rgb[k]=lo[k]+(hi[k]-lo[k])*f/63;
        lut[i]=R_SkyNearest(rgb[0],rgb[1],rgb[2]);
    }
}
static void dw_bake(void)
{
    static const int clear_sky[3]={95,135,203},clear_fog[3]={206,227,255},clear_sun[3]={255,252,238};
    static const int blight_sky[3]={90,35,35},blight_night[3]={44,14,14},blight_fog[3]={128,19,19};
    static const int blight_sun[3]={224,84,84},ash_sky[3]={124,73,58};
    int back_lo[3],back_hi[3],cloud_lo[3],cloud_hi[3],tmp[3],tmp2[3],m,i,v,thr,k;double t0=Sys_FloatTime();
    m=dw.effect==1?dw.step*256/(DW_STEPS-1):0;
    for(k=0;k<3;k++)tmp[k]=clear_sky[k]*3/4;
    dw_mix(tmp,blight_night,m,back_lo);
    if(dw.effect==1 && dw.step==DW_STEPS-1)for(k=0;k<3;k++)back_lo[k]/=2;	/* the crater: darker still */
    dw_mix(clear_sky,blight_sky,m,back_hi);
    for(k=0;k<3;k++)tmp[k]=clear_fog[k]*3/4,tmp2[k]=ash_sky[k]/2;
    dw_mix(tmp,tmp2,m,cloud_lo);
    dw_mix(clear_sun,m>128?blight_sun:blight_fog,m,cloud_hi);
    dw_ramp(dw.lut_back,back_lo,back_hi,0);
    dw_ramp(dw.lut_cloud,cloud_lo,cloud_hi,dw.effect==1?5:0);
    dw.speed=(float)(1.25+(9.0-1.25)*m/256.0);		/* Cloud Speed, Clear 1.25 .. Blight 9 */
    dw.coverage=(float)(0.55-0.25*m/256.0);			/* more of the sky under ash nearer the mountain */
    thr=(int)(dw.coverage*255);
    for(i=0;i<DW_TILE;i++){
        dw.back[i]=dw.lut_back[dw.noise_back[i]>>2];
        v=dw.noise_cloud[i];
        if(v<thr)dw.cloud[i]=0;
        else{v=(v-thr)*63*3/(255-thr);if(v>63)v=63;dw.cloud[i]=dw.lut_cloud[v];if(!dw.cloud[i])dw.cloud[i]=dw.lut_cloud[63];}
    }
    dw.baked_effect=dw.effect;dw.baked_step=dw.step;
    dw.bake_ms=(Sys_FloatTime()-t0)*1000.0;
}

/* ---- the frame: Quake's two-layer compose, then one lookup per pixel ---- */
static void dw_compose(double time)
{
    int x,y,fx=(int)(time*dw.speed*4),bx=(int)(time*dw.speed),row,brow;byte c;
    for(y=0;y<DW_SIZE;y++){
        row=((y+fx)&(DW_SIZE-1))*DW_SIZE;brow=((y+bx)&(DW_SIZE-1))*DW_SIZE;
        for(x=0;x<DW_SIZE;x++){
            c=dw.cloud[row+((x+fx)&(DW_SIZE-1))];
            dw.tile[y*DW_SIZE+x]=c?c:dw.back[brow+((x+bx)&(DW_SIZE-1))];
        }
    }
}
static void dw_st(float u,float v,const vec3_t f,const vec3_t r,const vec3_t up,int *s,int *t)
{
    vec3_t e;float scale=(float)(vid.width>vid.height?vid.width:vid.height);
    float wu=8192.0f*(u-vid.width*.5f)/scale,wv=8192.0f*(vid.height*.5f-v)/scale;
    e[0]=4096*f[0]+wu*r[0]+wv*up[0];e[1]=4096*f[1]+wu*r[1]+wv*up[1];e[2]=(4096*f[2]+wu*r[2]+wv*up[2])*3;
    VectorNormalize(e);
    *s=(int)(200.0f*e[0]*65536.0f);*t=(int)(200.0f*e[1]*65536.0f);
}
static void dw_draw_sky(double time)
{
    vec3_t angles,f,r,up;int x,y,n,s,t,s2,t2,ss,ts;byte *dest;
    angles[0]=-25;angles[1]=(float)(time*6.0);angles[2]=0;	/* looking up 25 degrees, a slow 6 deg/s pan */
    AngleVectors(angles,f,r,up);
    for(y=0;y<(int)vid.height;y++){
        dest=vid.buffer+y*vid.rowbytes;
        for(x=0;x<(int)vid.width;x+=16){
            n=(int)vid.width-x;if(n>16)n=16;
            dw_st((float)x,(float)y,f,r,up,&s,&t);dw_st((float)(x+n),(float)y,f,r,up,&s2,&t2);
            ss=(s2-s)/n;ts=(t2-t)/n;
            while(n--){*dest++=dw.tile[((t>>16)&(DW_SIZE-1))*DW_SIZE+((s>>16)&(DW_SIZE-1))];s+=ss;t+=ts;}
        }
    }
}

static unsigned long dw_bytes(void) {return 5UL*DW_TILE+sizeof dw.lut_back+sizeof dw.lut_cloud;}
static void dw_free(void)
{
    free(dw.noise_back);free(dw.noise_cloud);free(dw.back);free(dw.cloud);free(dw.tile);
    dw.noise_back=dw.noise_cloud=dw.back=dw.cloud=dw.tile=NULL;dw.on=0;
}
static int dw_start(void)
{
    if(dw.on)return 1;
    dw.noise_back=AW_TryMalloc(DW_TILE);dw.noise_cloud=AW_TryMalloc(DW_TILE);
    dw.back=AW_TryMalloc(DW_TILE);dw.cloud=AW_TryMalloc(DW_TILE);dw.tile=AW_TryMalloc(DW_TILE);
    if(!dw.noise_back || !dw.noise_cloud || !dw.back || !dw.cloud || !dw.tile){
        dw_free();Con_Printf("DemoWind: not enough memory for %lu bytes.\n",dw_bytes());return 0;
    }
    dw_make_noise();
    dw.on=1;dw.baked_effect=dw.baked_step=-1;dw.start=Sys_FloatTime();dw.frames=0;dw.sum=0;
    memset(dw.logged,0,sizeof dw.logged);
    Con_Printf("DemoWind on: %lu bytes (5 tiles of 128x128, 2 colour tables of 64). Keys: Left/Right effect, Up/Down distance, Esc off.\n",dw_bytes());
    return 1;
}
static void dw_select(int effect,int step)
{
    dw.effect=(effect+DW_EFFECTS)%DW_EFFECTS;
    if(step<0)step=0;
    if(step>DW_STEPS-1)step=DW_STEPS-1;
    dw.step=step;dw.frames=0;dw.sum=0;
}

int AW_DemoWindActive(void) {return dw.on;}

void AW_DemoWindDraw(void)
{
    char line[96];double t0,ms;int e,y=4;
    if(!dw.on || !vid.buffer)return;
    if(dw.baked_effect!=dw.effect || dw.baked_step!=dw.step)dw_bake();
    t0=Sys_FloatTime();
    dw_compose(t0-dw.start);
    dw_draw_sky(t0-dw.start);
    ms=(Sys_FloatTime()-t0)*1000.0;
    dw.sum+=ms;dw.frames++;
    if(dw.frames==DW_AVG){
        e=dw.effect;dw.avg[e]=dw.sum/DW_AVG;dw.avg_frames[e]=DW_AVG;dw.frames=0;dw.sum=0;
        if(!dw.logged[e][dw.step]){
            dw.logged[e][dw.step]=1;
            Con_Printf("DEMOWIND COST effect %d %s step %d (%s): %.2f ms/frame over %d frames, %lu bytes, bake %.2f ms, %dx%d\n",
                       e+1,dw_names[e],dw.step,dw_places[dw.step],dw.avg[e],DW_AVG,dw_bytes(),dw.bake_ms,vid.width,vid.height);
        }
    }
    sprintf(line,"DEMOWIND %d/%d: %s",dw.effect+1,DW_EFFECTS,dw_names[dw.effect]);Draw_String(4,y,line);y+=10;
    if(dw.effect==1)sprintf(line,"DISTANCE %d/%d: %s",dw.step,DW_STEPS-1,dw_places[dw.step]);
    else strcpy(line,"DISTANCE: none (the plain sky)");
    Draw_String(4,y,line);y+=10;
    sprintf(line,"%.2f MS/FRAME  CLOUD SPEED %.2f",dw.avg_frames[dw.effect]?dw.avg[dw.effect]:ms,dw.speed);Draw_String(4,y,line);y+=10;
    if(dw.avg_frames[0] && dw.avg_frames[1]){sprintf(line,"PLAIN %.2f MS  RED %.2f MS",dw.avg[0],dw.avg[1]);Draw_String(4,y,line);y+=10;}
    sprintf(line,"%lu BYTES  BAKE %.2f MS",dw_bytes(),dw.bake_ms);Draw_String(4,y,line);y+=10;
    Draw_String(4,vid.height-34,"<- -> EFFECT  UP/DOWN DISTANCE  ESC OFF");
    scr_copyeverything=1;
}

int AW_DemoWindKey(int key,int down)
{
    if(!dw.on || key_dest!=key_game)return 0;
    switch(key){
    case K_RIGHTARROW:case 'n':if(down)dw_select(dw.effect+1,dw.step);return 1;
    case K_LEFTARROW:case 'p':if(down)dw_select(dw.effect-1,dw.step);return 1;
    case K_UPARROW:if(down)dw_select(dw.effect,dw.step+1);return 1;
    case K_DOWNARROW:if(down)dw_select(dw.effect,dw.step-1);return 1;
    case K_ESCAPE:if(down){dw_free();Con_Printf("DemoWind off.\n");}return 1;
    default:return 0;
    }
}

static void dw_command(void)
{
    const char *a=Cmd_Argc()>1?Cmd_Argv(1):"on";
    if(!Q_strcasecmp((char *)a,"on") || !Q_strcasecmp((char *)a,"start")){if(dw_start())dw_select(dw.effect,dw.step);return;}
    if(!Q_strcasecmp((char *)a,"off") || !Q_strcasecmp((char *)a,"stop")){dw_free();Con_Printf("DemoWind off.\n");return;}
    if(!Q_strcasecmp((char *)a,"status")){
        Con_Printf("DemoWind %s: effect %d (%s), distance step %d (%s); plain %.2f ms, red %.2f ms (averages of %d frames); %lu bytes; bake %.2f ms\n",
                   dw.on?"on":"off",dw.effect+1,dw_names[dw.effect],dw.step,dw_places[dw.step],dw.avg[0],dw.avg[1],DW_AVG,
                   dw_bytes(),dw.bake_ms);
        return;
    }
    if(!dw.on && !dw_start())return;
    if(!Q_strcasecmp((char *)a,"next"))dw_select(dw.effect+1,dw.step);
    else if(!Q_strcasecmp((char *)a,"prev"))dw_select(dw.effect-1,dw.step);
    else if(!Q_strcasecmp((char *)a,"effect") && Cmd_Argc()==3)dw_select(atoi(Cmd_Argv(2))-1,dw.step);
    else if(!Q_strcasecmp((char *)a,"dist") && Cmd_Argc()==3)dw_select(dw.effect,atoi(Cmd_Argv(2)));
    else Con_Printf("Usage: dbg demowind [on / off / next / prev / effect 1-%d / dist 0-%d / status]\n",DW_EFFECTS,DW_STEPS-1);
}

void AW_DemoWindInit(void) {Cmd_AddCommand("aw_demowind",dw_command);}
