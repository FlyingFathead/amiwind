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
#include "aw_state.h"
#include "aw_clock.h"

static cvar_t aw_weather={"aw_weather","1",true};
/* The Red Mountain sky (REDMOUNTAIN-SKY-55, aw_weather.h AW_WeatherMountainPull): 1 (saved, default) pulls the sky,
 * fog and land light toward the Blight weather nearer the mountain; 0 = the region weather alone, as before. */
static cvar_t aw_redmountain={"aw_redmountain","1",true};
/* The weather's own fog depth and cloud speed (aw_weather.h AW_WeatherFogScale, SOL-WEATHER-SKY-SNOW-68): 1 (saved,
 * default) the weather's, 0 one fog and one cloud speed for every weather, as before v0.0.68. */
static cvar_t aw_weather_look={"aw_weather_look","1",true};
/* this frame's weather for the fog and the clouds: set by AW_WeatherFrame only when it draws a weather */
static int look_on,look_current,look_next=AW_WEATHER_NONE,look_step;
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
/* The scripts' changes (ChangeWeather, ModRegion: aw_weather.h AW_WeatherScript*), saved with the scripts' block.
 * mountain_region: the Red Mountain region's catalogue index, read once when a change is first seen (-2 not yet). */
static aw_weather_script_t script;
static int mountain_region=-2;
static int target_weather(int days,int milliseconds,const float *source,int *region)
{
    /* A cell without a region keeps the last region's weather (OpenMW updateWeatherRegion). */
    *region=AW_WeatherRegionKeep(&state,AW_RegionIndexAt(source));
    if(forced>=0)return forced;
    return AW_WeatherScripted(&script,&table,*region,days,milliseconds);
}
/* the weather period of the game clock now (the period AW_WeatherFrame uses) */
static int script_period(void)
{
    int days=0,ms=0;
    if(AW_ClockEnsure()){
        days=AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:days");
        ms=AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms");
    }
    return AW_WeatherPeriod(days,ms,table.hours);
}
int AW_WeatherChangeByScript(int region,int weather)
{
    load();
    if(!loaded || !AW_WeatherScriptChange(&script,&table,region,weather,script_period()))return 0;
    if(mountain_region==-2)mountain_region=-3;   /* read at the next exterior frame */
    return 1;
}
int AW_WeatherModRegionByScript(int region,const int *chances,int n)
{
    load();
    if(!loaded || !AW_WeatherScriptModRegion(&script,&table,region,chances,n,script_period()))return 0;
    if(mountain_region==-2)mountain_region=-3;
    return 1;
}
int AW_WeatherScriptSave(unsigned char *out,int capacity){return AW_WeatherScriptExport(&script,out,capacity);}
int AW_WeatherScriptLoad(const unsigned char *p,int bytes)
{
    int k=AW_WeatherScriptImport(&script,p,bytes);
    if(k>0 && script.count && mountain_region==-2)mountain_region=-3;
    return k;
}
/* New Game and every save load (NEWGAME-STATE-RESET-62): no region changed by a script */
void AW_WeatherScriptClear(void){AW_WeatherScriptReset(&script);}
/* the console's ChangeWeather and ModRegion (v0.0.68, MW-CONSOLE-COMMANDS-62): read only, nothing new kept */
int AW_WeatherForced(void){return forced;}
const unsigned char *AW_WeatherRegionChances(int region){load();return loaded?AW_WeatherChancesOf(&script,&table,region):NULL;}
/* The Red Mountain pull is our stand-in for the mountain's blight (REDMOUNTAIN-SKY-55): once a script gives the Red
 * Mountain region chances with no ash and no blight (the end of the main quest: EndGame's ModRegion), it stops, as
 * the original's sky over the mountain clears then. */
static int mountain_cleared(void)
{
    const unsigned char *c;
    if(!script.count)return 0;
    if(mountain_region==-3){
        float crater[3]={AW_WEATHER_RED_MOUNTAIN_X,AW_WEATHER_RED_MOUNTAIN_Y,0};
        mountain_region=AW_RegionIndexAt(crater);   /* one catalogue read; the player's cell is read again next */
        if(mountain_region<0)mountain_region=-1;
    }
    if(mountain_region<0)return 0;
    {int i;for(i=0;i<script.count;i++)if(script.row[i].region==mountain_region && script.row[i].has_chances)break;
     if(i==script.count)return 0;}
    c=AW_WeatherChancesOf(&script,&table,mountain_region);
    return c && !c[AW_WEATHER_ASH] && !c[AW_WEATHER_BLIGHT];
}
/* GetCurrentWeather (MWSCRIPT-SMALL-FUNCTIONS-62): the weather in effect */
int AW_WeatherCurrent(void)
{
    return state.current<0 || state.current>=AW_WEATHERS?0:state.current;
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
    storm=0;falling=AW_PRECIP_NONE;falling_strength=0;mountain_pull=0;look_on=0;
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
    /* the storm's own wind (v0.0.68: a blizzard blows north, SOL-WEATHER-SKY-SNOW-68) */
    storm=AW_WeatherStormDirectionOf(AW_WeatherStormOf(state.current,state.next,state.progress),source,storm_dir);
    falling=AW_WeatherPrecip(state.current,state.next,state.progress,&falling_strength);
    if(state.next==AW_WEATHER_NONE){
        AW_WeatherBlend(&table,state.current,state.current,AW_WEATHER_STEPS,out);
        key=state.current==AW_WEATHER_CLEAR?0:
            1+state.current*AW_WEATHERS*(AW_WEATHER_STEPS+1)+state.current*(AW_WEATHER_STEPS+1)+AW_WEATHER_STEPS;
        step=0;
    }else{
        step=(int)(state.progress*AW_WEATHER_STEPS);
        if(step>AW_WEATHER_STEPS)step=AW_WEATHER_STEPS;
        AW_WeatherBlend(&table,state.current,state.next,step,out);
        key=1+state.current*AW_WEATHERS*(AW_WEATHER_STEPS+1)+state.next*(AW_WEATHER_STEPS+1)+step;
    }
    look_on=aw_weather_look.value>0;look_current=state.current;look_next=state.next;look_step=step;
    /* the Red Mountain pull on top (REDMOUNTAIN-SKY-55): one distance a frame; the key changes with the pull, so
     * the sky tables are rebuilt at most AW_WEATHER_STEPS times on the way to the crater */
    if(aw_redmountain.value>0 && forced<0 && !mountain_cleared())mountain_pull=AW_WeatherMountainPull(source);
    if(mountain_pull>0)AW_WeatherMountainBlend(&table,mountain_pull,out);
    return key*(AW_WEATHER_STEPS+1)+mountain_pull;
}
int AW_WeatherLightOn(void)
{
    return aw_weather.value<1.5f; /* 2 = sky and fog only (WEATHER-AMBIENT-SUN-UNUSED-51) */
}
/* The weather's fog depth and cloud speed this frame (SOL-WEATHER-SKY-SNOW-68): Clear's outside a drawn weather. */
int AW_WeatherFogScaleAt(int a,int b,int mix)
{
    return look_on?AW_WeatherFogScale(look_current,look_next,look_step,a,b,mix):AW_WEATHER_FOG_CLEAR;
}
int AW_WeatherCloudPercentNow(void)
{
    return look_on?AW_WeatherCloudPercent(look_current,look_next,look_step):100;
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
        else{Con_Printf("Usage: dbg weather [on/off / skyonly / auto / clear cloudy foggy overcast rain thunder ash blight snow blizzard / look on/off]\n");return;}
        instant=1;
    }else if(Cmd_Argc()==3 && !strcmp(s,"look") && (!strcmp(Cmd_Argv(2),"on") || !strcmp(Cmd_Argv(2),"off"))){
        Cvar_SetValue(aw_weather_look.name,!strcmp(Cmd_Argv(2),"on"));   /* the weather's fog depth and cloud speed */
    }else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg weather [on/off / auto / NAME / look on/off]\n");return;}
    load();
    now=aw_weather_names[state.current<0 || state.current>=AW_WEATHERS?0:state.current];
    Con_Printf("Region weather %s%s: %s",aw_weather.value>0?(AW_WeatherLightOn()?"on":"on, sky only"):"off",forced>=0?", forced":"",now);
    if(loaded && !table.light)Con_Printf(" (AWW1 table: no land light)");
    if(state.next!=AW_WEATHER_NONE)Con_Printf(" changing to %s %ld%%",aw_weather_names[state.next],(long)(state.progress*100));
    if(state.queued!=AW_WEATHER_NONE)Con_Printf(", then %s",aw_weather_names[state.queued]);
    Con_Printf("; Red Mountain pull %d/%d%s",mountain_pull,AW_WEATHER_STEPS,aw_redmountain.value>0?"":" (aw_redmountain 0)");
    /* the weather's look (SOL-WEATHER-SKY-SNOW-68): fog span against Clear's at day and night, clouds, the storm */
    Con_Printf("; look %s: fog x%ld/256 day x%ld/256 night, clouds %ld%%",aw_weather_look.value>0?"on":"off",
        (long)AW_WeatherFogScaleAt(0,0,0),(long)AW_WeatherFogScaleAt(3,3,0),(long)AW_WeatherCloudPercentNow());
    if(storm)Con_Printf("; storm, wind %ld %ld /100",(long)(storm_dir[0]*100),(long)(storm_dir[1]*100));
    /* the land's light of this weather against Clear's by day and by night, per channel in 1/256 (AW_WeatherLightTone) */
    if(loaded && table.light){
        aw_weather_blend_t b;int day[3],night[3],cur=state.current<0 || state.current>=AW_WEATHERS?0:state.current;
        AW_WeatherBlend(&table,cur,state.next==AW_WEATHER_NONE?cur:state.next,
                        state.next==AW_WEATHER_NONE?AW_WEATHER_STEPS:(int)(state.progress*AW_WEATHER_STEPS),&b);
        AW_WeatherLightTone(&b,0,0,0,day);AW_WeatherLightTone(&b,3,3,0,night);
        Con_Printf("; light day %ld %ld %ld night %ld %ld %ld /256",(long)day[0],(long)day[1],(long)day[2],
                   (long)night[0],(long)night[1],(long)night[2]);
    }
    Con_Printf(" (table %s",loaded?"loaded":"missing: clear sky");
    if(loaded && player_source(source)){
        int region=AW_RegionIndexAt(source);const unsigned char *c=AW_WeatherChancesOf(&script,&table,region);
        char id[64];
        /* the chances in effect: a script's ModRegion's when it changed them (MWSCRIPT-COMPLETE-LANDMARK); v0.0.68: the
         * region's id as ChangeWeather and ModRegion take it on the console (the compiled scripts' region table) */
        if(c){
            if(AW_MwscriptRegionId(region,id,(int)sizeof id))Con_Printf("; region %ld \"%s\"",(long)region,id);
            else Con_Printf("; region %ld",(long)region);
            Con_Printf(": clear %ld cloudy %ld foggy %ld overcast %ld rain %ld thunder %ld ash %ld blight %ld snow %ld blizzard %ld",
                (long)c[0],(long)c[1],(long)c[2],(long)c[3],(long)c[4],(long)c[5],(long)c[6],(long)c[7],
                (long)c[8],(long)c[9]);
        }
    }
    if(script.count)Con_Printf("; %ld regions changed by scripts%s",(long)script.count,mountain_cleared()?
                               ", Red Mountain cleared":"");
    Con_Printf(")\n");
}
void AW_WeatherInit(void)
{
    Cvar_RegisterVariable(&aw_weather);
    Cvar_RegisterVariable(&aw_redmountain);
    Cvar_RegisterVariable(&aw_weather_look);
    Cmd_AddCommand("aw_weather_set",weather_command);
}
