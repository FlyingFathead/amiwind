/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_weather_rules.c alone (SKY-REDMOUNTAIN-BLUE-44): the chance roll, the
 * period, the AWW1 table and the blend toward a weather's colours. */
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "aw_weather.h"

static unsigned char file[20+32*AW_WEATHERS+10*3];
static void put(unsigned char *p,unsigned int v){p[0]=v;p[1]=v>>8;p[2]=v>>16;p[3]=v>>24;}
static long build(void)
{
    /* Regions in catalogue order: 0 West Gash, 1 Red Mountain, 2 an all-zero list. */
    static const unsigned char chances[3][10]={{15,30,15,20,10,10,0,0,0,0},{0,0,0,0,0,0,0,100,0,0},{0}};
    int w,s,k;unsigned char *row;
    memset(file,0,sizeof file);memcpy(file,"AWW1",4);
    put(file+4,AW_WEATHERS);put(file+8,3);put(file+12,20);
    for(w=0;w<AW_WEATHERS;w++){
        row=file+20+32*w;
        for(s=0;s<4;s++)for(k=0;k<3;k++){row[3*s+k]=(unsigned char)(w*20+s);row[12+3*s+k]=(unsigned char)(w*20+s+1);}
        row[24]=15;row[26]=w?0:100;
    }
    /* Clear: the engine's clear sky day; Blight: Morrowind.ini's blight day. */
    file[20+0]=95;file[21]=135;file[22]=203;
    row=file+20+32*AW_WEATHER_BLIGHT;row[0]=90;row[1]=35;row[2]=35;row[12]=128;row[13]=19;row[14]=19;row[24]=40;
    memcpy(file+20+32*AW_WEATHERS,chances,sizeof chances);
    return (long)sizeof file;
}
int main(void)
{
    static aw_weather_table_t table;aw_weather_blend_t blend;
    static const unsigned char red[10]={0,0,0,0,0,0,0,100,0,0},gash[10]={15,30,15,20,10,10,0,0,0,0};
    int roll,period,count[AW_WEATHERS],seen[101],i;long size=build();
    /* The roll against the running sum (rule from OpenMW mwworld/weather.cpp). */
    for(roll=1;roll<=100;roll++)assert(AW_WeatherChoose(red,AW_WEATHERS,roll)==AW_WEATHER_BLIGHT);
    assert(AW_WeatherChoose(gash,AW_WEATHERS,1)==0 && AW_WeatherChoose(gash,AW_WEATHERS,15)==0);
    assert(AW_WeatherChoose(gash,AW_WEATHERS,16)==1 && AW_WeatherChoose(gash,AW_WEATHERS,45)==1);
    assert(AW_WeatherChoose(gash,AW_WEATHERS,100)==5);
    assert(AW_WeatherChoose((const unsigned char *)"\0\0\0\0\0\0\0\0\0\0",AW_WEATHERS,50)==AW_WEATHER_CLEAR);
    /* Rolls 1..100, deterministic, every value reached. */
    memset(seen,0,sizeof seen);
    for(i=0;i<20000;i++){roll=AW_WeatherRoll(i%9,i/9);assert(roll>=1 && roll<=100);seen[roll]=1;
        assert(roll==AW_WeatherRoll(i%9,i/9));}
    for(roll=1;roll<=100;roll++)assert(seen[roll]);
    /* A new weather every 20 game hours. */
    assert(AW_WeatherPeriod(0,0,20)==0 && AW_WeatherPeriod(0,19*3600000+3599999,20)==0);
    assert(AW_WeatherPeriod(0,20*3600000,20)==1 && AW_WeatherPeriod(5,0,20)==6);
    /* The table: shape checked, wrong sizes refused. */
    assert(!AW_WeatherParse(file,size-1,&table));
    assert(!AW_WeatherParse(file,size+1,&table));
    file[4]=9;assert(!AW_WeatherParse(file,size,&table));file[4]=AW_WEATHERS;
    assert(AW_WeatherParse(file,size,&table) && table.regions==3 && table.hours==20);
    assert(table.look[AW_WEATHER_BLIGHT].delta_milli==40 && table.look[0].glare==100);
    /* Red Mountain is blight in every period; a region outside the table is clear. */
    for(period=0;period<500;period++)assert(AW_WeatherOfRegion(&table,1,period,0)==AW_WEATHER_BLIGHT);
    assert(AW_WeatherOfRegion(&table,3,0,0)==AW_WEATHER_CLEAR && AW_WeatherOfRegion(&table,-1,0,0)==AW_WEATHER_CLEAR);
    assert(AW_WeatherOfRegion(&table,2,7,0)==AW_WEATHER_CLEAR);
    /* West Gash over 4,000 periods follows its chances within a few percent. */
    memset(count,0,sizeof count);
    for(i=0;i<4000;i++)count[AW_WeatherOfRegion(&table,0,i*20/24,(i*20%24)*3600000)]++;
    for(i=0;i<AW_WEATHERS;i++){int expect=gash[i]*40;assert(count[i]>=expect-120 && count[i]<=expect+120);}
    /* Blend: clear stays clear (strength 0, clear stops); blight is full strength. */
    AW_WeatherBlend(&table,0,0,AW_WEATHER_STEPS,&blend);
    assert(blend.strength==0 && blend.glare==100 && blend.sky[0][0]==95 && blend.sky[0][2]==203);
    AW_WeatherBlend(&table,AW_WEATHER_BLIGHT,AW_WEATHER_BLIGHT,AW_WEATHER_STEPS,&blend);
    assert(blend.strength==AW_WEATHER_STEPS && blend.glare==0);
    assert(blend.sky[0][0]==90 && blend.sky[0][1]==35 && blend.fog[0][0]==128 && blend.fog[0][1]==19);
    AW_WeatherBlend(&table,0,AW_WEATHER_BLIGHT,AW_WEATHER_STEPS/2,&blend);
    assert(blend.strength==AW_WEATHER_STEPS/2 && blend.glare==50);
    assert(blend.sky[0][2]==(203+35+1)/2);
    assert(AW_WeatherIndex("blight")==AW_WEATHER_BLIGHT && AW_WeatherIndex("clear")==0 && AW_WeatherIndex("x")<0);
    puts("weather rules ok");
    return 0;
}
