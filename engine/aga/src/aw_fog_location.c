/* SPDX-License-Identifier: GPL-2.0-or-later
 * Location fog (aw_fog_location 1; off by default, a backup the owner keeps
 * for frame rate): places listed in id1/world/fog-locations.txt ("name day
 * night" in local units, one place per line, # comments) shorten the fog and
 * draw distance there, from the day value to the night value as the sky
 * darkens. Short fog is where the frame time goes in a dense town (owner,
 * Balmora: 250 roughly doubles the frame rate), and night hides distance. The
 * player's own setting stays the upper bound; interiors are unchanged. The
 * table is read once per area.
 */
#include "quakedef.h"
#include "aw_sky.h"
#define FOG_NIGHT_DAYLIGHT 128
extern int (*aw_fog_location_hook)(int);
static cvar_t aw_fog_location={"aw_fog_location","0",true};
static char loaded[MAX_QPATH];
static int have,day_distance,night_distance;
static void load(void)
{
    FILE *f=NULL;char line[128],name[64];int day,night;
    snprintf(loaded,sizeof loaded,"%s",sv.name);have=0;
    if(COM_FOpenFile("world/fog-locations.txt",&f)<0 || !f)return;
    while(fgets(line,sizeof line,f)){
        if(line[0]=='#' || Q_sscanf(line,"%63s %d %d",name,&day,&night)!=3)continue;
        if(Q_strcasecmp(name,sv.name))continue;
        if(day>=100 && day<=1500 && night>=100 && night<=1500){have=1;day_distance=day;night_distance=night;}
        break;
    }
    fclose(f);
}
static int location(int distance)
{
    int light,value;
    if(aw_fog_location.value<=0 || !sv.active || !R_SkyExterior())return distance;
    if(strcmp(loaded,sv.name))load();
    if(!have)return distance;
    light=r_daylight>256?256:r_daylight<FOG_NIGHT_DAYLIGHT?FOG_NIGHT_DAYLIGHT:r_daylight;
    value=night_distance+(day_distance-night_distance)*(light-FOG_NIGHT_DAYLIGHT)/(256-FOG_NIGHT_DAYLIGHT);
    return value<distance?value:distance;
}
void AW_FogLocationInit(void)
{
    Cvar_RegisterVariable(&aw_fog_location);aw_fog_location_hook=location;
}
