/* SPDX-License-Identifier: GPL-2.0-or-later
 * Location fog (aw_fog_location 1, the default from v0.0.57; 0 off): places
 * listed in id1/world/fog-locations.txt ("name day night" in local units, one
 * place per line, # comments) shorten the fog and draw distance there, from
 * the day value to the night value as the sky darkens. Short fog is where the
 * frame time goes in a dense town (the maintainer, Balmora: 250 roughly
 * doubles the frame rate; Ald'ruhn at 300: FOG-300-DEFAULT-57), and night
 * hides distance. The name is matched against the place the player stands in
 * (the HUD title's "Region / Place": the place, then the region) and then the
 * map name; letters and digits only, case ignored ("Ald'ruhn" = "aldruhn"),
 * so a town inside the CHIM world map is found by its cell. The player's own
 * setting stays the upper bound; interiors are unchanged. The table is read
 * once; the place is looked up again only when the HUD title changes.
 */
#include "quakedef.h"
#include "aw_remote.h"
#include "aw_sky.h"
#include "aw_world.h"
#define FOG_NIGHT_DAYLIGHT 128
#define FOG_PLACES 48
#define FOG_NAME 40
extern int (*aw_fog_location_hook)(int);
static cvar_t aw_fog_location={"aw_fog_location","1",true};
typedef struct {char name[FOG_NAME];int day,night;} fog_place_t;
static fog_place_t places[FOG_PLACES];
static int place_count,table_read,have,day_distance,night_distance;
static char matched_map[MAX_QPATH],matched_title[132];
/* Letters and digits, lower case: "Ald'ruhn" and "aldruhn" are one name. */
static void squeeze(const char *in,char *out,int size)
{
    int n=0;
    for(;*in && n<size-1;in++){
        char c=*in;
        if(c>='A' && c<='Z')c+='a'-'A';
        if((c>='a' && c<='z') || (c>='0' && c<='9'))out[n++]=c;
    }
    out[n]=0;
}
/* "name words ... day night": the last two numbers are the distances. */
static void read_table(void)
{
    FILE *f=NULL;char line[160],*end,*p;int day,night;
    table_read=1;place_count=0;
    if(COM_FOpenFile("world/fog-locations.txt",&f)<0 || !f)return;
    while(fgets(line,sizeof line,f) && place_count<FOG_PLACES){
        if(line[0]=='#')continue;
        end=line+strlen(line);
        while(end>line && (end[-1]=='\n' || end[-1]=='\r' || end[-1]==' ' || end[-1]=='\t'))*--end=0;
        p=strrchr(line,' ');if(!p)continue;
        night=atoi(p+1);if(p[1]<'0' || p[1]>'9')continue;
        *p=0;p=strrchr(line,' ');if(!p)continue;
        day=atoi(p+1);if(p[1]<'0' || p[1]>'9')continue;
        *p=0;
        if(day<100 || day>1500 || night<100 || night>1500)continue;
        squeeze(line,places[place_count].name,FOG_NAME);
        if(!places[place_count].name[0])continue;
        places[place_count].day=day;places[place_count].night=night;place_count++;
    }
    fclose(f);
}
static const fog_place_t *find(const char *name)
{
    char key[FOG_NAME];int i;
    squeeze(name,key,sizeof key);
    if(!key[0])return NULL;
    for(i=0;i<place_count;i++)if(!strcmp(places[i].name,key))return &places[i];
    return NULL;
}
/* The HUD title of where the view stands ("Region / Place"), or "". */
static const char *title_here(void)
{
    vec3_t source;const char *t;
    if(!AW_WorldToSource(sv.name,r_refdef.vieworg,source))return "";
    t=AW_RegionNameAt(source);
    return t?t:"";
}
static void match(const char *title)
{
    const fog_place_t *p=NULL;const char *slash=strstr(title," / ");char region[132];
    if(slash)p=find(slash+3);
    if(!p){
        snprintf(region,sizeof region,"%s",title);
        if(slash)region[slash-title]=0;
        p=find(region);
    }
    if(!p)p=find(sv.name);
    have=p!=NULL;
    if(p){day_distance=p->day;night_distance=p->night;}
}
static int location(int distance)
{
    int light,value;const char *title;
    if(aw_fog_location.value<=0 || !sv.active || !R_SkyExterior())return distance;
    if(!table_read)read_table();
    if(!place_count)return distance;
    title=title_here();
    if(strcmp(matched_map,sv.name) || strcmp(matched_title,title)){
        snprintf(matched_map,sizeof matched_map,"%s",sv.name);
        snprintf(matched_title,sizeof matched_title,"%s",title);
        match(title);
    }
    if(!have)return distance;
    light=r_daylight>256?256:r_daylight<FOG_NIGHT_DAYLIGHT?FOG_NIGHT_DAYLIGHT:r_daylight;
    value=night_distance+(day_distance-night_distance)*(light-FOG_NIGHT_DAYLIGHT)/(256-FOG_NIGHT_DAYLIGHT);
    return value<distance?value:distance;
}
void AW_FogLocationInit(void)
{
    Cvar_RegisterVariable(&aw_fog_location);aw_fog_location_hook=location;
}
