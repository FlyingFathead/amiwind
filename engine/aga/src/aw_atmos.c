/* SPDX-License-Identifier: GPL-2.0-or-later
 * Falling weather and mesh smoke, on the shared effect path (aw_magic.h AW_FxParticles / AW_FxSprite: Quake's
 * particle pool, r_part.c, and temporary sprite entities, cl_tent.c), exteriors only.
 *
 * WEATHER-RAIN (the maintainer, 27 October 2026: "we don't have i.e. rain, but we should have it ... maybe we can do it
 * with sprites"): rain, heavy rain, snow, blizzard and the ash of ash and blight storms fall in a small box around
 * the view while the region weather (aw_weather.c AW_WeatherFalling) has them, fading in and out with its
 * transitions. Sizes from Morrowind.ini as it ships ([Weather Rain] Rain Diameter 600, Rain Height Min 200 / Max
 * 700, [Weather] Precip Gravity 575, Snow Gravity Scale 0.1; original units, a quarter of them here); rules from
 * OpenMW file apps/openmw/mwrender/sky.cpp and mwworld/weather.cpp (read, not copied): the drops fall straight, the
 * ash blows outward from Red Mountain. AmiWind's own budget: at most AW_PRECIP_LIVE drops alive (the original's
 * Max Raindrops 450 / 650 are far past a 68040's particle budget), so the box is filled thinly.
 *
 * MESH-PARTICLE-EMITTERS (the maintainer: "it could be a shit simple sprite thing btw"): every exterior smoke and
 * steam emitter of the placed meshes (world/smoke.aws, tools/particle_emitters.smoke_table: chimneys, campfires,
 * torches, braziers, steam vents) near the view puffs SMOKE_PUFFS sprites of the chimneys' own particle texture
 * (world/smoke.spr) that rise its emitter's rise in its particle lifetime, grow and thin out (the sprite's frames);
 * no particle simulation. At most SMOKE_DRAW emitters, the nearest in front, share the frame's temporary entities
 * with the beams and the magic effects.
 *
 * aw_atmos (saved, dbg atmos): bit 1 the falling weather, bit 2 the smoke; default 2 (smoke on; the falling weather
 * off until its frame cost is measured at 32 MB on the 68040, the TODO's default-off setting first).
 */
#include "quakedef.h"
#include "aw_world.h"
#include "aw_sky.h"
#include "aw_weather.h"
#include "aw_magic.h"

static cvar_t aw_atmos={"aw_atmos","2",true};
#define ATMOS_PRECIP 1
#define ATMOS_SMOKE 2

/* ---- falling weather ---- */
#define AW_PRECIP_LIVE 48            /* drops alive at full strength (heavy rain, blizzard: AW_PRECIP_LIVE_HEAVY) */
#define AW_PRECIP_LIVE_HEAVY 64
#define PRECIP_HALF_WIDTH 75.0f      /* Rain Diameter 600 / 2, a quarter */
#define PRECIP_LOW 50.0f             /* Rain Height Min 200 above the view, a quarter */
#define PRECIP_HIGH 175.0f           /* Rain Height Max 700 */
#define PRECIP_FALL 143.75f          /* Precip Gravity 575 a second, a quarter */
#define PRECIP_AHEAD 40.0f           /* the box's centre ahead of the view: most of it in sight */
static double precip_carry,precip_last=-1;

static void precip_update(void)
{
    int kind,strength,live,n,r,g,b;float at[3],vel[3],rand_v,life,dir[2],height;double now=realtime,dt;
    kind=AW_WeatherFalling(&strength);
    dt=precip_last<0?0:now-precip_last;precip_last=now;
    if(!kind || strength<=0 || dt<=0 || dt>0.5){precip_carry=0;return;}
    live=(kind==AW_PRECIP_HEAVY_RAIN || kind==AW_PRECIP_BLIZZARD?AW_PRECIP_LIVE_HEAVY:AW_PRECIP_LIVE)*strength/AW_WEATHER_STEPS;
    height=PRECIP_HIGH-PRECIP_LOW;
    vel[0]=vel[1]=0;
    switch(kind){
    case AW_PRECIP_SNOW:case AW_PRECIP_BLIZZARD:
        vel[2]=-PRECIP_FALL*0.1f;rand_v=6;r=g=b=230;     /* Snow Gravity Scale 0.1 */
        if(kind==AW_PRECIP_BLIZZARD){vel[0]=18;vel[1]=8;}
        break;
    case AW_PRECIP_ASH:
        if(!AW_WeatherStorm(dir)){dir[0]=0;dir[1]=1;}
        vel[0]=dir[0]*60;vel[1]=dir[1]*60;vel[2]=-6;rand_v=10;r=120;g=92;b=74;
        break;
    default:
        vel[2]=-PRECIP_FALL;rand_v=8;r=150;g=160;b=176;
    }
    life=height/(vel[2]<-1?-vel[2]:20);
    if(life>4)life=4;
    precip_carry+=live*dt/life;      /* spawned a second = alive / lifetime */
    n=(int)precip_carry;
    if(n<=0)return;
    if(n>live)n=live;
    precip_carry-=n;
    at[0]=r_refdef.vieworg[0]+vpn[0]*PRECIP_AHEAD;
    at[1]=r_refdef.vieworg[1]+vpn[1]*PRECIP_AHEAD;
    at[2]=r_refdef.vieworg[2]+(PRECIP_LOW+PRECIP_HIGH)*0.5f;
    if(kind==AW_PRECIP_ASH)at[2]=r_refdef.vieworg[2]+16;   /* the ash drifts through the view */
    AW_FxParticles(at,n,PRECIP_HALF_WIDTH,vel,rand_v,life,r,g,b,0);
}

/* ---- mesh smoke ---- */
#define SMOKE_ROW 26                 /* tools/particle_emitters.py SMOKE_ROW */
#define SMOKE_CACHE 96               /* the 3 x 3 cells around the view; more are dropped (counted) */
#define SMOKE_DRAW 4
#define SMOKE_PUFFS 3
#define SMOKE_RANGE 640.0f           /* local units */
#define SMOKE_PATH "world/smoke.aws"
#define SMOKE_SPRITE "world/smoke.spr"
typedef struct {float origin[3],size,rise,life;} smoke_t;
static smoke_t smokes[SMOKE_CACHE];
static int smoke_count,smoke_dropped,smoke_cell_valid,smoke_cell[2],smoke_sprite_tried;
static model_t *smoke_model,*smoke_world;
static unsigned le32(const byte *p){return (unsigned)p[0]|((unsigned)p[1]<<8)|((unsigned)p[2]<<16)|((unsigned)p[3]<<24);}
static int le16s(const byte *p){return (int)(short)(unsigned short)(p[0]|(p[1]<<8));}
static float lef(const byte *p){unsigned n=le32(p);float f;memcpy(&f,&n,4);return f;}
static void smoke_read_cell(FILE *f,long base,unsigned count,int cx,int cy)
{
    byte row[SMOKE_ROW];int lo=0,hi=(int)count,mid,rx,ry;
    while(lo<hi){
        mid=lo+(hi-lo)/2;
        if(fseek(f,base+8+(long)mid*SMOKE_ROW,SEEK_SET) || fread(row,1,SMOKE_ROW,f)!=SMOKE_ROW)return;
        rx=le16s(row);ry=le16s(row+2);
        if(rx<cx || (rx==cx && ry<cy))lo=mid+1;else hi=mid;
    }
    if(fseek(f,base+8+(long)lo*SMOKE_ROW,SEEK_SET))return;
    for(;lo<(int)count;lo++){
        smoke_t *s;int k;
        if(fread(row,1,SMOKE_ROW,f)!=SMOKE_ROW || le16s(row)!=cx || le16s(row+2)!=cy)return;
        if(smoke_count>=SMOKE_CACHE){smoke_dropped++;continue;}
        s=&smokes[smoke_count];
        for(k=0;k<3;k++)s->origin[k]=lef(row+4+4*k);
        s->size=(float)(row[16]|(row[17]<<8));s->rise=(float)(row[18]|(row[19]<<8));s->life=row[21]/20.0f;
        if(s->life<0.25f)s->life=0.25f;
        if(isfinite(s->origin[0]) && isfinite(s->origin[1]) && isfinite(s->origin[2]))smoke_count++;
    }
}
static void smoke_load(int cx,int cy)
{
    FILE *f=NULL;byte head[8];long base;int size,dx,dy;unsigned count;
    smoke_count=smoke_dropped=0;smoke_cell_valid=1;smoke_cell[0]=cx;smoke_cell[1]=cy;
    size=COM_FOpenFile(SMOKE_PATH,&f);
    if(!f)return;
    base=ftell(f);
    if(base>=0 && size>=8 && fread(head,1,8,f)==8 && !memcmp(head,"AWS1",4)){
        count=le32(head+4);
        if(count<=16384 && (long)size==8+(long)count*SMOKE_ROW)
            for(dx=-1;dx<=1;dx++)for(dy=-1;dy<=1;dy++)smoke_read_cell(f,base,count,cx+dx,cy+dy);
    }
    fclose(f);
}
static void smoke_update(void)
{
    float view[3],global[3],local[3],at[3],d,best_d[SMOKE_DRAW],dx,dy,dz,t,scale;
    int best[SMOKE_DRAW],found=0,i,j,p,cx,cy,frame;
    if(cl.worldmodel!=(model_t *)smoke_world){smoke_world=cl.worldmodel;smoke_model=NULL;smoke_sprite_tried=0;smoke_cell_valid=0;}
    if(!smoke_sprite_tried){
        FILE *f=NULL;
        smoke_sprite_tried=1;
        COM_FOpenFile(SMOKE_SPRITE,&f);     /* no puff without the user's particle texture */
        if(f){fclose(f);smoke_model=Mod_ForName(SMOKE_SPRITE,false);}
    }
    if(!smoke_model)return;
    VectorCopy(r_refdef.vieworg,view);
    if(!AW_WorldToSource(sv.name,view,global))return;
    cx=(int)floor(global[0]/8192.0);cy=(int)floor(global[1]/8192.0);
    if(!smoke_cell_valid || cx!=smoke_cell[0] || cy!=smoke_cell[1])smoke_load(cx,cy);
    for(i=0;i<smoke_count;i++){
        dx=(smokes[i].origin[0]-global[0])*0.25f;dy=(smokes[i].origin[1]-global[1])*0.25f;dz=(smokes[i].origin[2]-global[2])*0.25f;
        if(dx*vpn[0]+dy*vpn[1]+dz*vpn[2]<0)continue;            /* behind the view */
        d=dx*dx+dy*dy+dz*dz;
        if(!(d<SMOKE_RANGE*SMOKE_RANGE))continue;
        for(j=found<SMOKE_DRAW?found++:SMOKE_DRAW;j>0 && best_d[j-1]>d;j--)
            if(j<SMOKE_DRAW){best_d[j]=best_d[j-1];best[j]=best[j-1];}
        if(j<SMOKE_DRAW){best_d[j]=d;best[j]=i;}
    }
    for(j=0;j<found;j++){
        smoke_t *s=&smokes[best[j]];
        if(!AW_SourceToWorld(sv.name,s->origin,local))continue;
        for(p=0;p<SMOKE_PUFFS;p++){
            /* each puff rises the emitter's rise in its lifetime, a third of a life apart, seeded by its place */
            {double u=realtime/s->life+(double)p/SMOKE_PUFFS+(double)(best[j]%7)*0.137;
             t=(float)(u-(double)(long)u);}      /* the fraction, without fmod (68040: library-free) */
            frame=(int)(t*4);if(frame>3)frame=3;
            scale=1.0f+t*1.5f;
            at[0]=local[0];at[1]=local[1];at[2]=local[2]+t*s->rise*0.25f;
            if(!AW_FxSprite(smoke_model,at,s->size*0.25f*scale,frame))return;   /* the frame's entities used up */
        }
    }
}

void AW_AtmosUpdate(void)
{
    int bits=(int)aw_atmos.value;
    if(cls.state!=ca_connected || !sv.active || !cl.worldmodel || !R_SkyExterior()){precip_last=-1;return;}
    if(bits&ATMOS_PRECIP)precip_update();else precip_last=-1;
    if(bits&ATMOS_SMOKE)smoke_update();
}
void AW_AtmosInit(void)
{
    Cvar_RegisterVariable(&aw_atmos);
}
