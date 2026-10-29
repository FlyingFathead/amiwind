/* SPDX-License-Identifier: GPL-2.0-or-later
 * Region weather rules as pure functions (aw_weather.h). No engine state: the
 * host test runs them as they are. */
#include <string.h>
#include <math.h>
#include "aw_weather.h"

const char *const aw_weather_names[AW_WEATHERS]={"clear","cloudy","foggy","overcast","rain",
    "thunder","ash","blight","snow","blizzard"};

int AW_WeatherIndex(const char *name)
{
    int i;
    if(!name)return -1;
    for(i=0;i<AW_WEATHERS;i++)if(!strcmp(name,aw_weather_names[i]))return i;
    return -1;
}
/* roll 1..100 against the running sum; a list that never reaches it: Clear. */
int AW_WeatherChoose(const unsigned char *chances,int count,int roll)
{
    int i,sum=0;
    if(!chances || count<=0)return AW_WEATHER_CLEAR;
    if(count>AW_WEATHERS)count=AW_WEATHERS;
    for(i=0;i<count;i++){
        sum+=chances[i];
        if(roll<=sum)return i;
    }
    return AW_WEATHER_CLEAR;
}
/* 1..100, the same for a region and period on every run and machine. */
int AW_WeatherRoll(int region,int period)
{
    unsigned int h=2166136261U^(unsigned int)region;
    h=(h^((unsigned int)period&0xffU))*16777619U;
    h=(h^(((unsigned int)period>>8)&0xffU))*16777619U;
    h=(h^(((unsigned int)period>>16)&0xffU))*16777619U;
    h=(h^((unsigned int)period>>24))*16777619U;
    h^=h>>13;h*=0x5bd1e995U;h^=h>>15;
    return (int)(h%100U)+1;
}
int AW_WeatherPeriod(int days,int milliseconds,int hours)
{
    long hour;
    if(hours<1)hours=1;
    if(days<0)days=0;
    if(milliseconds<0 || milliseconds>=86400000)milliseconds=0;
    hour=(long)days*24+milliseconds/3600000;
    return (int)(hour/hours);
}
static unsigned int word(const unsigned char *p)
{
    return (unsigned int)p[0]|((unsigned int)p[1]<<8)|((unsigned int)p[2]<<16)|((unsigned int)p[3]<<24);
}
/* AWW1 / AWW2 (tools/prepare_world_ui.py region_weather): header, ten 32-byte
 * (AWW1) or 56-byte (AWW2: ambient and sun stops after the fog stops) looks,
 * ten chance bytes per region. Any other shape is refused (clear sky stays). */
int AW_WeatherParse(const unsigned char *raw,long size,aw_weather_table_t *out)
{
    unsigned int weathers,regions,hours;int w,s,k,look,light;const unsigned char *row;
    if(!raw || !out || size<20)return 0;
    if(!memcmp(raw,"AWW1",4)){look=AW_WEATHER_LOOK_V1;light=0;}
    else if(!memcmp(raw,"AWW2",4)){look=AW_WEATHER_LOOK_V2;light=1;}
    else return 0;
    weathers=word(raw+4);regions=word(raw+8);hours=word(raw+12);
    if(weathers!=AW_WEATHERS || regions>AW_WEATHER_REGIONS || hours<1 || hours>240)return 0;
    if(size!=20+(long)look*(long)weathers+10L*(long)regions)return 0;
    memset(out,0,sizeof *out);
    out->regions=(int)regions;out->hours=(int)hours;out->light=light;
    for(w=0;w<AW_WEATHERS;w++){
        row=raw+20+look*w;
        for(s=0;s<4;s++)for(k=0;k<3;k++){
            out->look[w].sky[s][k]=row[3*s+k];
            out->look[w].fog[s][k]=row[12+3*s+k];
            if(light){
                out->look[w].ambient[s][k]=row[24+3*s+k];
                out->look[w].sun[s][k]=row[36+3*s+k];
            }
        }
        row+=light?48:24;
        out->look[w].delta_milli=row[0]|(row[1]<<8);
        out->look[w].glare=row[2]>100?100:row[2];
        if(out->look[w].delta_milli<1)out->look[w].delta_milli=1;
    }
    memcpy(out->chances,raw+20+look*AW_WEATHERS,10*regions);
    return 1;
}
int AW_WeatherOfRegion(const aw_weather_table_t *table,int region,int days,int milliseconds)
{
    if(!table || region<0 || region>=table->regions)return AW_WEATHER_CLEAR;
    return AW_WeatherChoose(table->chances[region],AW_WEATHERS,
        AW_WeatherRoll(region,AW_WeatherPeriod(days,milliseconds,table->hours)));
}
/* Transitions (aw_weather.h; rules from OpenMW mwworld/weather.cpp forceWeather,
 * addWeatherTransition, updateWeatherTransitions, updateWeatherRegion, playerTeleported). */
void AW_WeatherForce(aw_weather_state_t *s,int weather)
{
    s->current=weather;s->next=s->queued=AW_WEATHER_NONE;s->progress=0.0;
}
void AW_WeatherAddTransition(aw_weather_state_t *s,int weather)
{
    if(s->next==AW_WEATHER_NONE){
        if(weather!=s->current){s->next=weather;s->progress=0.0;}
    }else if(weather!=s->next)s->queued=weather;
}
/* seconds of real time at the delta (Transition Delta, per real second) of the weather being moved to;
 * time left over when one ends goes to the queued one at its own delta. */
void AW_WeatherAdvance(aw_weather_state_t *s,const aw_weather_table_t *table,double seconds)
{
    double delta,left;
    while(s->next!=AW_WEATHER_NONE && seconds>0.0){
        delta=table->look[s->next].delta_milli/1000.0;
        if(delta<=0.0)delta=0.001;
        s->progress+=seconds*delta;
        if(s->progress<1.0)return;
        left=(s->progress-1.0)/delta;
        s->current=s->next;s->next=s->queued;s->queued=AW_WEATHER_NONE;s->progress=0.0;
        seconds=left;
    }
}
/* The region to use: a named region is remembered; none (-1) keeps the last named one. */
int AW_WeatherRegionKeep(aw_weather_state_t *s,int region)
{
    if(region>=0)s->region=region;
    return s->region;
}
int AW_WeatherIsArrival(int have_last,double dx,double dy,long hours_passed)
{
    if(!have_last)return 1;
    if(dx*dx+dy*dy>AW_WEATHER_ARRIVAL_UNITS*AW_WEATHER_ARRIVAL_UNITS)return 1;
    return hours_passed>=AW_WEATHER_ARRIVAL_HOURS || hours_passed<0;
}
/* step 0 = all from, AW_WEATHER_STEPS = all to. */
void AW_WeatherBlend(const aw_weather_table_t *table,int from,int to,int step,aw_weather_blend_t *out)
{
    const aw_weather_look_t *a,*b;int s,k,sa,sb;
    if(from<0 || from>=AW_WEATHERS)from=AW_WEATHER_CLEAR;
    if(to<0 || to>=AW_WEATHERS)to=AW_WEATHER_CLEAR;
    if(step<0)step=0;
    if(step>AW_WEATHER_STEPS)step=AW_WEATHER_STEPS;
    a=&table->look[from];b=&table->look[to];
#define MIX(field) (unsigned char)((a->field[s][k]*(AW_WEATHER_STEPS-step)+b->field[s][k]*step+AW_WEATHER_STEPS/2)/AW_WEATHER_STEPS)
    for(s=0;s<4;s++)for(k=0;k<3;k++){
        out->sky[s][k]=MIX(sky);
        out->fog[s][k]=MIX(fog);
        out->ambient[s][k]=MIX(ambient);
        out->sun[s][k]=MIX(sun);
        out->clear_ambient[s][k]=table->look[AW_WEATHER_CLEAR].ambient[s][k];
        out->clear_sun[s][k]=table->look[AW_WEATHER_CLEAR].sun[s][k];
    }
#undef MIX
    out->light=table->light;
    sa=from==AW_WEATHER_CLEAR?0:AW_WEATHER_STEPS;sb=to==AW_WEATHER_CLEAR?0:AW_WEATHER_STEPS;
    out->strength=(sa*(AW_WEATHER_STEPS-step)+sb*step)/AW_WEATHER_STEPS;
    out->glare=(a->glare*(AW_WEATHER_STEPS-step)+b->glare*step)/AW_WEATHER_STEPS;
}
int AW_WeatherMountainPull(const float *source)
{
    double dx,dy,d,t;int pull;
    if(!source)return 0;
    dx=source[0]-AW_WEATHER_RED_MOUNTAIN_X;dy=source[1]-AW_WEATHER_RED_MOUNTAIN_Y;d=sqrt(dx*dx+dy*dy);
    if(!(d<AW_WEATHER_MOUNTAIN_REACH))return 0;   /* also a NaN position */
    if(d<=AW_WEATHER_MOUNTAIN_CRATER)return AW_WEATHER_STEPS;
    t=(AW_WEATHER_MOUNTAIN_REACH-d)/(AW_WEATHER_MOUNTAIN_REACH-AW_WEATHER_MOUNTAIN_CRATER);
    pull=(int)(t*AW_WEATHER_STEPS+0.5);
    return pull<0?0:pull>AW_WEATHER_STEPS?AW_WEATHER_STEPS:pull;
}
void AW_WeatherMountainBlend(const aw_weather_table_t *table,int pull,aw_weather_blend_t *out)
{
    const aw_weather_look_t *b;int s,k,strength;
    if(!table || !out || pull<=0)return;
    if(pull>AW_WEATHER_STEPS)pull=AW_WEATHER_STEPS;
    b=&table->look[AW_WEATHER_BLIGHT];
#define PULL(field,w) out->field[s][k]=(unsigned char)((out->field[s][k]*(AW_WEATHER_STEPS-(w))+b->field[s][k]*(w)+AW_WEATHER_STEPS/2)/AW_WEATHER_STEPS)
    for(s=0;s<4;s++)for(k=0;k<3;k++){
        /* the fog at AW_WEATHER_MOUNTAIN_FOG/256 of the pull: the far land, fully fogged, takes the fog colour flat,
         * and Blight's own fog (128 19 19) at full turned distant rock into flat orange-red shapes (shots of
         * 2026-10-29 outside the Ghostfence); the red belongs in the sky, as in DemoWind */
        PULL(sky,pull);PULL(fog,pull*AW_WEATHER_MOUNTAIN_FOG/256);
        if(table->light){PULL(ambient,pull);PULL(sun,pull);}
        if(pull==AW_WEATHER_STEPS)out->sky[s][k]=(unsigned char)(out->sky[s][k]*AW_WEATHER_MOUNTAIN_DARK/256);
    }
#undef PULL
    strength=out->strength>pull?out->strength:pull;
    out->strength=strength;
    out->glare=(out->glare*(AW_WEATHER_STEPS-pull)+b->glare*pull)/AW_WEATHER_STEPS;
}
int AW_WeatherIsStorm(int current,int next,double progress)
{
    int w=next!=AW_WEATHER_NONE && progress>=0.5?next:current;
    return w==AW_WEATHER_ASH || w==AW_WEATHER_BLIGHT;
}
int AW_WeatherPrecipOf(int weather)
{
    switch(weather){
    case 4:return AW_PRECIP_RAIN;
    case 5:return AW_PRECIP_HEAVY_RAIN;
    case AW_WEATHER_ASH:case AW_WEATHER_BLIGHT:return AW_PRECIP_ASH;
    case 8:return AW_PRECIP_SNOW;
    case 9:return AW_PRECIP_BLIZZARD;
    default:return AW_PRECIP_NONE;
    }
}
int AW_WeatherPrecip(int current,int next,double progress,int *strength)
{
    int a=AW_WeatherPrecipOf(current),b=next==AW_WEATHER_NONE?a:AW_WeatherPrecipOf(next),s;
    if(next==AW_WEATHER_NONE || a==b){if(strength)*strength=a?AW_WEATHER_STEPS:0;return a;}
    if(progress<0.5){
        s=(int)((0.5-progress)*2*AW_WEATHER_STEPS+0.5);
        if(strength)*strength=a?s:0;
        return a;
    }
    s=(int)((progress-0.5)*2*AW_WEATHER_STEPS+0.5);
    if(s>AW_WEATHER_STEPS)s=AW_WEATHER_STEPS;
    if(strength)*strength=b?s:0;
    return b;
}
int AW_WeatherStormDirection(const float *source,float dir[2])
{
    float x,y,length;
    dir[0]=0;dir[1]=1;
    if(!source)return 0;
    x=source[0]-AW_WEATHER_RED_MOUNTAIN_X;y=source[1]-AW_WEATHER_RED_MOUNTAIN_Y;
    length=(float)sqrt((double)(x*x+y*y));
    if(!(length>1.0f))return 0;
    dir[0]=x/length;dir[1]=y/length;
    return 1;
}
/* sine of an angle in degrees by Bhaskara's rational form (error under 0.002): no library sin or cos, whose argument
 * reduction reaches instructions the 68040 does not implement (the gate's engine check) */
static double sin_degrees(double x)
{
    double s=1.0,p;
    if(!(x>-1e6 && x<1e6))return 0.0;
    x-=(double)(long)(x/360.0)*360.0;   /* no fmod either */
    if(x<0)x+=360.0;
    if(x>180.0){x-=180.0;s=-1.0;}
    p=x*(180.0-x);
    return s*4.0*p/(40500.0-p);
}
int AW_WeatherFacesStorm(float yaw,const float dir[2])
{
    return sin_degrees((double)yaw+90.0)*dir[0]+sin_degrees((double)yaw)*dir[1]<-0.5;
}
/* stops a and b (0..3, r_sky.c order) mixed by mix/32; tone in 1/256 per channel (aw_weather.h). */
void AW_WeatherLightTone(const aw_weather_blend_t *blend,int a,int b,int mix,int *tone)
{
    int k;long weather,clear;
    if(a<0 || a>3)a=0;
    if(b<0 || b>3)b=0;
    if(mix<0)mix=0;
    if(mix>32)mix=32;
    for(k=0;k<3;k++){
        tone[k]=256;
        if(!blend || !blend->light)continue;
        weather=((long)blend->ambient[a][k]*256+(long)blend->sun[a][k]*AW_WEATHER_SUN_SHARE)*(32-mix)+
                ((long)blend->ambient[b][k]*256+(long)blend->sun[b][k]*AW_WEATHER_SUN_SHARE)*mix;
        clear=((long)blend->clear_ambient[a][k]*256+(long)blend->clear_sun[a][k]*AW_WEATHER_SUN_SHARE)*(32-mix)+
              ((long)blend->clear_ambient[b][k]*256+(long)blend->clear_sun[b][k]*AW_WEATHER_SUN_SHARE)*mix;
        if(clear<=0)continue;
        /* weather*256 stays below 2^31: at most (255*256+255*128)*32*256, about 8.0e8 */
        tone[k]=(int)(weather*256/clear);
        if(tone[k]<AW_WEATHER_TONE_MIN)tone[k]=AW_WEATHER_TONE_MIN;
        if(tone[k]>AW_WEATHER_TONE_MAX)tone[k]=AW_WEATHER_TONE_MAX;
    }
}
