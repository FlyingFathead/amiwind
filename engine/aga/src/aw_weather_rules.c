/* SPDX-License-Identifier: GPL-2.0-or-later
 * Region weather rules as pure functions (aw_weather.h). No engine state: the
 * host test runs them as they are. */
#include <string.h>
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
/* AWW1 (tools/prepare_world_ui.py region_weather): header, ten 32-byte looks,
 * ten chance bytes per region. Any other shape is refused (clear sky stays). */
int AW_WeatherParse(const unsigned char *raw,long size,aw_weather_table_t *out)
{
    unsigned int weathers,regions,hours;int w,s,k;const unsigned char *row;
    if(!raw || !out || size<20 || memcmp(raw,"AWW1",4))return 0;
    weathers=word(raw+4);regions=word(raw+8);hours=word(raw+12);
    if(weathers!=AW_WEATHERS || regions>AW_WEATHER_REGIONS || hours<1 || hours>240)return 0;
    if(size!=20+32L*(long)weathers+10L*(long)regions)return 0;
    memset(out,0,sizeof *out);
    out->regions=(int)regions;out->hours=(int)hours;
    for(w=0;w<AW_WEATHERS;w++){
        row=raw+20+32*w;
        for(s=0;s<4;s++)for(k=0;k<3;k++){
            out->look[w].sky[s][k]=row[3*s+k];
            out->look[w].fog[s][k]=row[12+3*s+k];
        }
        out->look[w].delta_milli=row[24]|(row[25]<<8);
        out->look[w].glare=row[26]>100?100:row[26];
        if(out->look[w].delta_milli<1)out->look[w].delta_milli=1;
    }
    memcpy(out->chances,raw+20+32*AW_WEATHERS,10*regions);
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
    for(s=0;s<4;s++)for(k=0;k<3;k++){
        out->sky[s][k]=(unsigned char)((a->sky[s][k]*(AW_WEATHER_STEPS-step)+b->sky[s][k]*step+AW_WEATHER_STEPS/2)/AW_WEATHER_STEPS);
        out->fog[s][k]=(unsigned char)((a->fog[s][k]*(AW_WEATHER_STEPS-step)+b->fog[s][k]*step+AW_WEATHER_STEPS/2)/AW_WEATHER_STEPS);
    }
    sa=from==AW_WEATHER_CLEAR?0:AW_WEATHER_STEPS;sb=to==AW_WEATHER_CLEAR?0:AW_WEATHER_STEPS;
    out->strength=(sa*(AW_WEATHER_STEPS-step)+sb*step)/AW_WEATHER_STEPS;
    out->glare=(a->glare*(AW_WEATHER_STEPS-step)+b->glare*step)/AW_WEATHER_STEPS;
}
