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
    {
        /* Transitions (SKY-REDMOUNTAIN-BLUE-44, 46; rules from OpenMW mwworld/weather.cpp). Blight's delta is
         * 0.040 per real second (25 s), cloudy's 0.015 (about 67 s). */
        aw_weather_state_t s={AW_WEATHER_CLEAR,AW_WEATHER_NONE,AW_WEATHER_NONE,0.0,-1};
        table.look[1].delta_milli=15;
        AW_WeatherForce(&s,AW_WEATHER_BLIGHT);
        assert(s.current==AW_WEATHER_BLIGHT && s.next==AW_WEATHER_NONE);
        /* Same weather: nothing starts. */
        AW_WeatherAddTransition(&s,AW_WEATHER_BLIGHT);assert(s.next==AW_WEATHER_NONE);
        /* Walking out of Red Mountain into a cloudy region: a transition at cloudy's delta, not a jump. */
        AW_WeatherAddTransition(&s,1);assert(s.current==AW_WEATHER_BLIGHT && s.next==1 && s.progress==0.0);
        AW_WeatherAdvance(&s,&table,10.0);
        assert(s.current==AW_WEATHER_BLIGHT && s.next==1 && s.progress>0.149 && s.progress<0.151);
        /* Back into Red Mountain mid-transition: queued, the running transition goes on (no snap back). */
        AW_WeatherAddTransition(&s,AW_WEATHER_BLIGHT);
        assert(s.next==1 && s.queued==AW_WEATHER_BLIGHT && s.progress>0.149);
        /* The cloudy transition ends after about 67 s; the time left goes to blight at blight's delta. */
        AW_WeatherAdvance(&s,&table,56.0+2.0/3.0+5.0);
        assert(s.current==1 && s.next==AW_WEATHER_BLIGHT && s.queued==AW_WEATHER_NONE);
        assert(s.progress>0.199 && s.progress<0.201);
        AW_WeatherAdvance(&s,&table,20.5);
        assert(s.current==AW_WEATHER_BLIGHT && s.next==AW_WEATHER_NONE && s.progress==0.0);
        /* A cell without a region keeps the last named region. */
        assert(AW_WeatherRegionKeep(&s,-1)==-1);
        assert(AW_WeatherRegionKeep(&s,1)==1 && AW_WeatherRegionKeep(&s,-1)==1 && AW_WeatherRegionKeep(&s,0)==0);
        /* Arrivals: the first frame, a jump of over half a cell, an hour of game time or time running back.
         * A walked crossing (a few units between frames, however long its load) is not one. */
        assert(AW_WeatherIsArrival(0,0,0,0));
        assert(!AW_WeatherIsArrival(1,300.0,-200.0,0));
        assert(!AW_WeatherIsArrival(1,4096.0,0.0,0) && AW_WeatherIsArrival(1,4097.0,0.0,0));
        assert(AW_WeatherIsArrival(1,0,0,1) && AW_WeatherIsArrival(1,0,0,-1) && AW_WeatherIsArrival(1,0,0,8));
    }
    {
        /* AWW2 (WEATHER-AMBIENT-SUN-UNUSED-51): the ambient and sun stops after the fog stops; the land's tone is the
         * weather's ambient + half its sun against Clear's (rule from OpenMW mwworld/weather.cpp: ambient + sun). */
        static unsigned char v2[20+AW_WEATHER_LOOK_V2*AW_WEATHERS+10*2];
        static const unsigned char amb_clear[3]={137,140,160},sun_clear[3]={255,252,238};
        static const unsigned char amb_blight[3]={79,54,54},sun_blight[3]={224,84,84};
        static aw_weather_table_t t2;aw_weather_blend_t b2;int tone[3],k,w;unsigned char *r;
        memset(v2,0,sizeof v2);memcpy(v2,"AWW2",4);
        put(v2+4,AW_WEATHERS);put(v2+8,2);put(v2+12,20);
        for(w=0;w<AW_WEATHERS;w++){
            r=v2+20+AW_WEATHER_LOOK_V2*w;
            for(k=0;k<12;k++){r[24+k]=amb_clear[k%3];r[36+k]=sun_clear[k%3];}
            r[48]=15;r[50]=w?0:100;
        }
        r=v2+20+AW_WEATHER_LOOK_V2*AW_WEATHER_BLIGHT;
        for(k=0;k<12;k++){r[24+k]=amb_blight[k%3];r[36+k]=sun_blight[k%3];}
        r[48]=40;r[0]=90;r[12]=128;
        v2[20+AW_WEATHER_LOOK_V2*AW_WEATHERS+10+7]=100;   /* region 1: blight */
        assert(!AW_WeatherParse(v2,(long)sizeof v2-1,&t2));
        assert(AW_WeatherParse(v2,(long)sizeof v2,&t2) && t2.light==1 && t2.regions==2);
        assert(t2.look[AW_WEATHER_BLIGHT].delta_milli==40 && t2.look[0].glare==100 && t2.look[AW_WEATHER_BLIGHT].glare==0);
        assert(t2.look[AW_WEATHER_BLIGHT].sky[0][0]==90 && t2.look[AW_WEATHER_BLIGHT].fog[0][0]==128);
        assert(t2.look[AW_WEATHER_BLIGHT].ambient[0][0]==79 && t2.look[AW_WEATHER_BLIGHT].sun[3][2]==84);
        assert(AW_WeatherOfRegion(&t2,1,3,0)==AW_WEATHER_BLIGHT);
        /* Clear: exactly unchanged. */
        AW_WeatherBlend(&t2,0,0,AW_WEATHER_STEPS,&b2);
        AW_WeatherLightTone(&b2,0,0,0,tone);
        assert(tone[0]==256 && tone[1]==256 && tone[2]==256);
        /* Blight by day: darker and red (about 72 %, 36 %, 34 % of clear). */
        AW_WeatherBlend(&t2,AW_WEATHER_BLIGHT,AW_WEATHER_BLIGHT,AW_WEATHER_STEPS,&b2);
        AW_WeatherLightTone(&b2,0,0,0,tone);
        assert(tone[0]>=180 && tone[0]<=190 && tone[1]>=88 && tone[1]<=96 && tone[2]>=84 && tone[2]<=92);
        /* Half way from clear: between the two, mixing stops keeps it in range. */
        AW_WeatherBlend(&t2,0,AW_WEATHER_BLIGHT,AW_WEATHER_STEPS/2,&b2);
        AW_WeatherLightTone(&b2,0,3,16,tone);
        for(k=0;k<3;k++)assert(tone[k]>=AW_WEATHER_TONE_MIN && tone[k]<=AW_WEATHER_TONE_MAX && tone[k]<256);
        /* An AWW1 table carries no light: the tone stays neutral. */
        AW_WeatherBlend(&table,AW_WEATHER_BLIGHT,AW_WEATHER_BLIGHT,AW_WEATHER_STEPS,&b2);
        assert(b2.light==0);
        AW_WeatherLightTone(&b2,0,0,0,tone);
        assert(tone[0]==256 && tone[1]==256 && tone[2]==256);
        AW_WeatherLightTone(NULL,0,0,0,tone);
        assert(tone[0]==256);
    }
    {
        /* Storms (ACTOR-STORM-POSE-51; rules from OpenMW mwworld/weather.cpp, mwmechanics/character.cpp): ash and
         * blight only; the weather left counts until half way; the wind blows outward from Red Mountain; an actor
         * faces into it below -0.5. */
        float dir[2],ald[3]={-16000.0f,50000.0f,0},rm[3]={25000.0f,70000.0f,0};
        assert(AW_WeatherIsStorm(AW_WEATHER_ASH,AW_WEATHER_NONE,0.0) && AW_WeatherIsStorm(AW_WEATHER_BLIGHT,AW_WEATHER_NONE,0.0));
        assert(!AW_WeatherIsStorm(AW_WEATHER_CLEAR,AW_WEATHER_NONE,0.0) && !AW_WeatherIsStorm(4,AW_WEATHER_NONE,0.0));
        assert(!AW_WeatherIsStorm(9,AW_WEATHER_NONE,0.0));                      /* blizzard: no eye pose */
        assert(AW_WeatherIsStorm(AW_WEATHER_ASH,0,0.49) && !AW_WeatherIsStorm(AW_WEATHER_ASH,0,0.5));
        assert(!AW_WeatherIsStorm(0,AW_WEATHER_BLIGHT,0.49) && AW_WeatherIsStorm(0,AW_WEATHER_BLIGHT,0.5));
        /* Ald'ruhn lies west-south-west of Red Mountain: the wind blows toward -x, a little -y */
        assert(AW_WeatherStormDirection(ald,dir) && dir[0]<-0.85f && dir[1]<0 && dir[1]>-0.5f);
        assert(AW_WeatherFacesStorm(0.0f,dir));                                  /* facing east, toward the mountain */
        assert(!AW_WeatherFacesStorm(180.0f,dir));                               /* back to the wind */
        assert(!AW_WeatherFacesStorm(90.0f,dir) && !AW_WeatherFacesStorm(270.0f,dir));
        assert(!AW_WeatherStormDirection(rm,dir) && !AW_WeatherStormDirection(NULL,dir));
    }
    {
        /* Falling weather (WEATHER-RAIN): what falls, and its strength through a transition. */
        int s;
        assert(AW_WeatherPrecipOf(0)==AW_PRECIP_NONE && AW_WeatherPrecipOf(4)==AW_PRECIP_RAIN);
        assert(AW_WeatherPrecipOf(5)==AW_PRECIP_HEAVY_RAIN && AW_WeatherPrecipOf(AW_WEATHER_ASH)==AW_PRECIP_ASH);
        assert(AW_WeatherPrecipOf(AW_WEATHER_BLIGHT)==AW_PRECIP_ASH && AW_WeatherPrecipOf(8)==AW_PRECIP_SNOW);
        assert(AW_WeatherPrecipOf(9)==AW_PRECIP_BLIZZARD && AW_WeatherPrecipOf(2)==AW_PRECIP_NONE);
        assert(AW_WeatherPrecip(4,AW_WEATHER_NONE,0.0,&s)==AW_PRECIP_RAIN && s==AW_WEATHER_STEPS);
        assert(AW_WeatherPrecip(0,AW_WEATHER_NONE,0.0,&s)==AW_PRECIP_NONE && s==0);
        /* clear to rain: nothing in the first half, then growing to full */
        assert(AW_WeatherPrecip(0,4,0.3,&s)==AW_PRECIP_NONE && s==0);
        assert(AW_WeatherPrecip(0,4,0.75,&s)==AW_PRECIP_RAIN && s==AW_WEATHER_STEPS/2);
        assert(AW_WeatherPrecip(0,4,1.0,&s)==AW_PRECIP_RAIN && s==AW_WEATHER_STEPS);
        /* rain to clear: fading over the first half */
        assert(AW_WeatherPrecip(4,0,0.0,&s)==AW_PRECIP_RAIN && s==AW_WEATHER_STEPS);
        assert(AW_WeatherPrecip(4,0,0.25,&s)==AW_PRECIP_RAIN && s==AW_WEATHER_STEPS/2);
        assert(AW_WeatherPrecip(4,0,0.6,&s)==AW_PRECIP_NONE && s==0);
        /* rain to heavy rain: keeps raining */
        assert(AW_WeatherPrecip(4,5,0.6,&s)==AW_PRECIP_HEAVY_RAIN && s>0);
        assert(AW_WeatherPrecip(4,4,0.3,&s)==AW_PRECIP_RAIN && s==AW_WEATHER_STEPS);
    }
    {
        /* The Red Mountain pull (REDMOUNTAIN-SKY-55): none at Seyda Neen or Ald'ruhn (the maintainer: "ald'ruhn is
         * good with the region weather"), rising from outside the Ghostfence, full in the crater; never above
         * AW_WEATHER_STEPS and 0 for a position that is not a number. */
        float seyda[3]={-12000,-70000,0},aldruhn[3]={-12606,54169,0},outside[3]={4000,42000,0},fence[3]={20605,47338,0};
        float crater[3]={25500,69500,0},nan_at[3];aw_weather_blend_t b;int p_al,p_out,p_fence,s,k;
        nan_at[0]=nan_at[1]=nan_at[2]=0.0f/0.0f;
        assert(AW_WeatherParse(file,build(),&table));   /* a fresh AWW1 table: Clear day 95 135 203, Blight 90 35 35 */
        assert(AW_WeatherMountainPull(seyda)==0);
        p_al=AW_WeatherMountainPull(aldruhn);p_out=AW_WeatherMountainPull(outside);p_fence=AW_WeatherMountainPull(fence);
        assert(p_al==0);
        assert(p_out>=1 && p_out<=3);
        assert(p_fence>p_out && p_fence<AW_WEATHER_STEPS);
        assert(AW_WeatherMountainPull(crater)==AW_WEATHER_STEPS);
        assert(AW_WeatherMountainPull(nan_at)==0 && AW_WeatherMountainPull(NULL)==0);
        /* the blend: a clear sky pulled half way toward the Blight weather's own colours, strength raised */
        AW_WeatherBlend(&table,AW_WEATHER_CLEAR,AW_WEATHER_CLEAR,AW_WEATHER_STEPS,&b);
        assert(b.strength==0 && b.sky[0][0]==95);
        AW_WeatherMountainBlend(&table,AW_WEATHER_STEPS/2,&b);
        assert(b.strength==AW_WEATHER_STEPS/2);
        assert(b.sky[0][0]==(95+90+1)/2 && b.sky[0][1]==(135+35+1)/2);
        {   /* the fog at AW_WEATHER_MOUNTAIN_FOG/256 of the pull */
            int f0=table.look[0].fog[0][0],w=(AW_WEATHER_STEPS/2)*AW_WEATHER_MOUNTAIN_FOG/256;
            assert(b.fog[0][0]==(f0*(AW_WEATHER_STEPS-w)+128*w+AW_WEATHER_STEPS/2)/AW_WEATHER_STEPS);
        }
        /* full pull: the Blight sky darkened by AW_WEATHER_MOUNTAIN_DARK/256; the fog half way to Blight's */
        AW_WeatherBlend(&table,AW_WEATHER_CLEAR,AW_WEATHER_CLEAR,AW_WEATHER_STEPS,&b);
        AW_WeatherMountainBlend(&table,AW_WEATHER_STEPS,&b);
        assert(b.strength==AW_WEATHER_STEPS && b.sky[0][0]==90*AW_WEATHER_MOUNTAIN_DARK/256);
        {
            int f0=table.look[0].fog[0][0],w=AW_WEATHER_STEPS*AW_WEATHER_MOUNTAIN_FOG/256;
            assert(b.fog[0][0]==(f0*(AW_WEATHER_STEPS-w)+128*w+AW_WEATHER_STEPS/2)/AW_WEATHER_STEPS);
        }
        /* pull 0 changes nothing */
        AW_WeatherBlend(&table,AW_WEATHER_CLEAR,AW_WEATHER_CLEAR,AW_WEATHER_STEPS,&b);
        AW_WeatherMountainBlend(&table,0,&b);
        for(s=0;s<4;s++)for(k=0;k<3;k++)assert(b.sky[s][k]==table.look[0].sky[s][k]);
    }
    puts("weather rules ok");
    return 0;
}
