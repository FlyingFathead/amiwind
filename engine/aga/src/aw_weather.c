/* SPDX-License-Identifier: GPL-2.0-or-later
 * Region weather at the player (aw_weather.h; SKY-REDMOUNTAIN-BLUE-44). The
 * table (world/region-weather.aww, 430 bytes for nine regions) is read once;
 * the region comes from the same per-cell lookup as the HUD's region name, so
 * nothing is read per frame. aw_weather 1 (saved, default): region weather,
 * sky, fog and the land's light; 2: sky and fog only (the land's light before
 * WEATHER-AMBIENT-SUN-UNUSED-51); 0: the clear sky everywhere (the look before v0.0.46). dbg weather NAME
 * forces one weather until dbg weather auto (not saved).
 */
#include "quakedef.h"
#include "aw_weather.h"
#include "aw_world.h"

static cvar_t aw_weather={"aw_weather","1",true};
/* The Red Mountain sky (REDMOUNTAIN-SKY-55, aw_weather.h AW_WeatherMountainPull): 1 (saved, default) pulls the sky,
 * fog and land light toward the Blight weather nearer the mountain; 0 = the region weather alone, as before. */
static cvar_t aw_redmountain={"aw_redmountain","1",true};
static int mountain_pull;
int AW_WeatherMountainLevel(void) {return mountain_pull;}
static aw_weather_table_t table;
static int loaded,attempted,forced=-1;
/* The weather in effect (aw_weather_state_t: current, a running transition, a queued one) and where
 * and when it was last drawn; kept across frame-map crossings, loads and interiors, so only an arrival
 * (AW_WeatherIsArrival) changes it at once. instant: the console changed it. */
static aw_weather_state_t state={AW_WEATHER_CLEAR,AW_WEATHER_NONE,AW_WEATHER_NONE,0.0,-1};
static int instant=1,have_last,last_target=AW_WEATHER_NONE;
static double last_time=-1;
static float last_source[3];
static long last_hour;

static void load(void)
{
    static unsigned char raw[20+AW_WEATHER_LOOK_V2*AW_WEATHERS+10*AW_WEATHER_REGIONS];
    FILE *f=NULL;int size;
    if(attempted)return;
    attempted=1;
    size=COM_FOpenFile(AW_WEATHER_PATH,&f);
    if(!f)return; /* No table: every region keeps the clear sky. */
    if(size<20 || size>(int)sizeof raw){fclose(f);Con_Printf("Region weather unavailable: %s has %ld bytes.\n",AW_WEATHER_PATH,(long)size);return;}
    if(fread(raw,1,(size_t)size,f)==(size_t)size && AW_WeatherParse(raw,size,&table))loaded=1;
    else Con_Printf("Region weather unavailable: %s is not a valid AWW1/AWW2 table.\n",AW_WEATHER_PATH);
    fclose(f);
}
/* The player's original-world position, or 0 outside an exterior. */
static int player_source(float *source)
{
    if(cls.state!=ca_connected || !sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict)return 0;
    return AW_WorldToSource(sv.name,svs.clients[0].edict->v.origin,source);
}
static int target_weather(int days,int milliseconds,const float *source,int *region)
{
    /* A cell without a region keeps the last region's weather (OpenMW updateWeatherRegion). */
    *region=AW_WeatherRegionKeep(&state,AW_RegionIndexAt(source));
    if(forced>=0)return forced;
    return AW_WeatherOfRegion(&table,*region,days,milliseconds);
}
/* The storm at the player this frame (ACTOR-STORM-POSE-51): set by AW_WeatherFrame. */
static int storm;
static float storm_dir[2];
int AW_WeatherStorm(float dir[2])
{
    if(storm && dir){dir[0]=storm_dir[0];dir[1]=storm_dir[1];}
    return storm;
}
/* What falls at the player (WEATHER-RAIN): set by AW_WeatherFrame with the storm. */
static int falling,falling_strength;
int AW_WeatherFalling(int *strength)
{
    if(strength)*strength=falling?falling_strength:0;
    return falling;
}
int AW_WeatherFrame(int days,int milliseconds,aw_weather_blend_t *out)
{
    float source[3];int target,region,step,key;double now=realtime,seconds;long hour;
    storm=0;falling=AW_PRECIP_NONE;falling_strength=0;mountain_pull=0;
    load();
    if(!loaded || (aw_weather.value<=0 && forced<0)){
        instant=1;have_last=0;last_time=-1;return 0;
    }
    /* Off the exterior (an interior, a load, a crossing's map change) nothing is drawn and nothing is
     * forgotten: the next exterior frame decides from where the player is then. */
    if(!player_source(source)){last_time=-1;return 0;}
    target=target_weather(days,milliseconds,source,&region);
    hour=(long)(days<0?0:days)*24+milliseconds/3600000;
    if(instant || AW_WeatherIsArrival(have_last,source[0]-last_source[0],source[1]-last_source[1],hour-last_hour)){
        AW_WeatherForce(&state,target);
    }else{
        if(target!=last_target)AW_WeatherAddTransition(&state,target);
        /* real seconds since the last exterior frame; a stall (a frame-map load) counts at most 2 s */
        seconds=last_time<0?0.0:now-last_time;
        if(seconds>2.0)seconds=2.0;
        if(seconds>0.0)AW_WeatherAdvance(&state,&table,seconds);
    }
    instant=0;have_last=1;last_time=now;last_target=target;last_hour=hour;
    last_source[0]=source[0];last_source[1]=source[1];last_source[2]=source[2];
    storm=AW_WeatherIsStorm(state.current,state.next,state.progress) && AW_WeatherStormDirection(source,storm_dir);
    falling=AW_WeatherPrecip(state.current,state.next,state.progress,&falling_strength);
    if(state.next==AW_WEATHER_NONE){
        AW_WeatherBlend(&table,state.current,state.current,AW_WEATHER_STEPS,out);
        key=state.current==AW_WEATHER_CLEAR?0:
            1+state.current*AW_WEATHERS*(AW_WEATHER_STEPS+1)+state.current*(AW_WEATHER_STEPS+1)+AW_WEATHER_STEPS;
    }else{
        step=(int)(state.progress*AW_WEATHER_STEPS);
        if(step>AW_WEATHER_STEPS)step=AW_WEATHER_STEPS;
        AW_WeatherBlend(&table,state.current,state.next,step,out);
        key=1+state.current*AW_WEATHERS*(AW_WEATHER_STEPS+1)+state.next*(AW_WEATHER_STEPS+1)+step;
    }
    /* the Red Mountain pull on top (REDMOUNTAIN-SKY-55): one distance a frame; the key changes with the pull, so
     * the sky tables are rebuilt at most AW_WEATHER_STEPS times on the way to the crater */
    if(aw_redmountain.value>0 && forced<0)mountain_pull=AW_WeatherMountainPull(source);
    if(mountain_pull>0)AW_WeatherMountainBlend(&table,mountain_pull,out);
    return key*(AW_WEATHER_STEPS+1)+mountain_pull;
}
int AW_WeatherLightOn(void)
{
    return aw_weather.value<1.5f; /* 2 = sky and fog only (WEATHER-AMBIENT-SUN-UNUSED-51) */
}
static void weather_command(void)
{
    char *s=Cmd_Argv(1);int w;float source[3];const char *now;
    if(Cmd_Argc()==2){
        if(!strcmp(s,"auto"))forced=-1;
        else if(!strcmp(s,"off") || !strcmp(s,"0")){Cvar_SetValue(aw_weather.name,0);forced=-1;}
        else if(!strcmp(s,"on") || !strcmp(s,"1")){Cvar_SetValue(aw_weather.name,1);forced=-1;}
        else if(!strcmp(s,"skyonly") || !strcmp(s,"2")){Cvar_SetValue(aw_weather.name,2);forced=-1;}
        else if((w=AW_WeatherIndex(s))>=0)forced=w;
        else{Con_Printf("Usage: dbg weather [on/off / skyonly / auto / clear cloudy foggy overcast rain thunder ash blight snow blizzard]\n");return;}
        instant=1;
    }else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg weather [on/off / auto / NAME]\n");return;}
    load();
    now=aw_weather_names[state.current<0 || state.current>=AW_WEATHERS?0:state.current];
    Con_Printf("Region weather %s%s: %s",aw_weather.value>0?(AW_WeatherLightOn()?"on":"on, sky only"):"off",forced>=0?", forced":"",now);
    if(loaded && !table.light)Con_Printf(" (AWW1 table: no land light)");
    if(state.next!=AW_WEATHER_NONE)Con_Printf(" changing to %s %ld%%",aw_weather_names[state.next],(long)(state.progress*100));
    if(state.queued!=AW_WEATHER_NONE)Con_Printf(", then %s",aw_weather_names[state.queued]);
    Con_Printf("; Red Mountain pull %d/%d%s",mountain_pull,AW_WEATHER_STEPS,aw_redmountain.value>0?"":" (aw_redmountain 0)");
    Con_Printf(" (table %s",loaded?"loaded":"missing: clear sky");
    if(loaded && player_source(source)){
        int region=AW_RegionIndexAt(source);
        if(region>=0 && region<table.regions)
            Con_Printf("; region %ld: clear %ld cloudy %ld foggy %ld overcast %ld rain %ld thunder %ld ash %ld blight %ld snow %ld blizzard %ld",
                (long)region,(long)table.chances[region][0],(long)table.chances[region][1],(long)table.chances[region][2],
                (long)table.chances[region][3],(long)table.chances[region][4],(long)table.chances[region][5],
                (long)table.chances[region][6],(long)table.chances[region][7],(long)table.chances[region][8],
                (long)table.chances[region][9]);
    }
    Con_Printf(")\n");
}
void AW_WeatherInit(void)
{
    Cvar_RegisterVariable(&aw_weather);
    Cvar_RegisterVariable(&aw_redmountain);
    Cmd_AddCommand("aw_weather_set",weather_command);
}
