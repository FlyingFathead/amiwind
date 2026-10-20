/* SPDX-License-Identifier: GPL-2.0-or-later
 * Region weather at the player (aw_weather.h; SKY-REDMOUNTAIN-BLUE-44). The
 * table (world/region-weather.aww, 430 bytes for nine regions) is read once;
 * the region comes from the same per-cell lookup as the HUD's region name, so
 * nothing is read per frame. aw_weather 1 (saved, default): region weather;
 * 0: the clear sky everywhere (the look before v0.0.46). dbg weather NAME
 * forces one weather until dbg weather auto (not saved).
 */
#include "quakedef.h"
#include "aw_weather.h"
#include "aw_world.h"

static cvar_t aw_weather={"aw_weather","1",true};
static aw_weather_table_t table;
static int loaded,attempted,forced=-1;
static int from=AW_WEATHER_CLEAR,to=AW_WEATHER_CLEAR,instant=1;
static double progress=1.0,last_time=-1;
static float last_source[3];
static char last_map[MAX_QPATH];

static void load(void)
{
    static unsigned char raw[20+32*AW_WEATHERS+10*AW_WEATHER_REGIONS];
    FILE *f=NULL;int size;
    if(attempted)return;
    attempted=1;
    size=COM_FOpenFile(AW_WEATHER_PATH,&f);
    if(!f)return; /* No table: every region keeps the clear sky. */
    if(size<20 || size>(int)sizeof raw){fclose(f);Con_Printf("Region weather unavailable: %s has %ld bytes.\n",AW_WEATHER_PATH,(long)size);return;}
    if(fread(raw,1,(size_t)size,f)==(size_t)size && AW_WeatherParse(raw,size,&table))loaded=1;
    else Con_Printf("Region weather unavailable: %s is not a valid AWW1 table.\n",AW_WEATHER_PATH);
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
    *region=AW_RegionIndexAt(source);
    if(forced>=0)return forced;
    return AW_WeatherOfRegion(&table,*region,days,milliseconds);
}
int AW_WeatherFrame(int days,int milliseconds,aw_weather_blend_t *out)
{
    float source[3];int target,region,step,teleport;double now=realtime,dx,dy;
    load();
    if(!loaded || (aw_weather.value<=0 && forced<0) || !player_source(source)){
        instant=1;last_time=-1;return 0;
    }
    target=target_weather(days,milliseconds,source,&region);
    /* A load, a map change, a long pause or a jump of over half a cell is an
     * arrival: the new weather is there at once (OpenMW playerTeleported). */
    dx=source[0]-last_source[0];dy=source[1]-last_source[1];
    teleport=instant || last_time<0 || now-last_time>2.0 || strcmp(last_map,sv.name) || dx*dx+dy*dy>4096.0*4096.0;
    if(teleport){from=to=target;progress=1.0;}
    else if(target!=to){
        /* A new weather mid-transition starts from the nearer end. */
        if(progress<.5)to=from;
        from=to;to=target;progress=0.0;
    }else if(progress<1.0){
        progress+=(now-last_time)*table.look[to].delta_milli/1000.0;
        if(progress>1.0)progress=1.0;
    }
    instant=0;last_time=now;
    last_source[0]=source[0];last_source[1]=source[1];last_source[2]=source[2];
    snprintf(last_map,sizeof last_map,"%s",sv.name);
    step=(int)(progress*AW_WEATHER_STEPS);
    if(from==to)step=AW_WEATHER_STEPS;
    AW_WeatherBlend(&table,from,to,step,out);
    if(from==AW_WEATHER_CLEAR && to==AW_WEATHER_CLEAR)return 0;
    return 1+from*AW_WEATHERS*(AW_WEATHER_STEPS+1)+to*(AW_WEATHER_STEPS+1)+step;
}
static void weather_command(void)
{
    char *s=Cmd_Argv(1);int w;float source[3];const char *now;
    if(Cmd_Argc()==2){
        if(!strcmp(s,"auto"))forced=-1;
        else if(!strcmp(s,"off") || !strcmp(s,"0")){Cvar_SetValue(aw_weather.name,0);forced=-1;}
        else if(!strcmp(s,"on") || !strcmp(s,"1")){Cvar_SetValue(aw_weather.name,1);forced=-1;}
        else if((w=AW_WeatherIndex(s))>=0)forced=w;
        else{Con_Printf("Usage: dbg weather [on/off / auto / clear cloudy foggy overcast rain thunder ash blight snow blizzard]\n");return;}
        instant=1;
    }else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg weather [on/off / auto / NAME]\n");return;}
    load();
    now=aw_weather_names[to<0 || to>=AW_WEATHERS?0:to];
    Con_Printf("Region weather %s%s: %s%s (table %s",aw_weather.value>0?"on":"off",forced>=0?", forced":"",now,
        from!=to?" (changing)":"",loaded?"loaded":"missing: clear sky");
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
    Cmd_AddCommand("aw_weather_set",weather_command);
}
