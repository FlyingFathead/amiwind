/* SPDX-License-Identifier: GPL-2.0-or-later
 * Location fog (FOG-300-DEFAULT-57): on by default; listed places blend from
 * the day to the night distance as the sky darkens; the name is matched on the
 * HUD title's place, then its region, then the map name (letters and digits,
 * case ignored), so a town inside the CHIM world map is found by its cell; the
 * player's setting stays the bound; unlisted places and interiors are
 * unchanged; the table is read once. */
#include "../src/quakedef.h"
#include <assert.h>
server_t sv;refdef_t r_refdef;int r_daylight=256;static int exterior=1,opens,on_world=1;
static const char *title="Ashlands Region / Ald'ruhn";
int R_SkyExterior(void){return exterior;}
int AW_WorldToSource(const char *name,const float *local,float *world){(void)name;(void)local;world[0]=world[1]=world[2]=0;return on_world;}
const char *AW_RegionNameAt(const float *p){(void)p;return title;}
static cvar_t *var;
void Cvar_RegisterVariable(cvar_t *v){var=v;v->value=(float)atof(v->string);}
int COM_FOpenFile(char *path,FILE **file){
    static const char text[]="# comment\nseyda 400 notanumber\nbalmora 300 250\nAld'ruhn 280 240\n"
                             "Bitter Coast Region 450 350\n";
    FILE *f;assert(!strcmp(path,"world/fog-locations.txt"));opens++;
    f=tmpfile();assert(f);fputs(text,f);rewind(f);*file=f;return (int)strlen(text);
}
int (*aw_fog_location_hook)(int);
void AW_FogLocationInit(void);
int main(void){
    AW_FogLocationInit();assert(aw_fog_location_hook && var && var->value==1 && var->archive);  /* on by default */
    sv.active=1;strcpy(sv.name,"vf1446");
    assert(aw_fog_location_hook(540)==280 && opens==1);             /* the place in the title, CHIM world map */
    r_daylight=128;assert(aw_fog_location_hook(540)==240);          /* night */
    r_daylight=192;assert(aw_fog_location_hook(540)==260);          /* dusk: halfway */
    r_daylight=40;assert(aw_fog_location_hook(540)==240);           /* darker than full night */
    r_daylight=256;
    assert(aw_fog_location_hook(200)==200);                         /* player's shorter setting wins */
    title="Bitter Coast Region / Hla Oad";assert(aw_fog_location_hook(540)==450);  /* unlisted place: its region */
    title="Ascadian Isles Region";assert(aw_fog_location_hook(540)==540);          /* unlisted */
    on_world=0;strcpy(sv.name,"balmora");assert(aw_fog_location_hook(540)==300);   /* map name */
    on_world=1;title="";
    exterior=0;assert(aw_fog_location_hook(540)==540);exterior=1;   /* interiors unchanged */
    var->value=0;assert(aw_fog_location_hook(540)==540);            /* off */
    assert(opens==1);                                               /* read once */
    puts("location fog: on by default, place/region/map match, day/night blend, player bound, interiors");
    return 0;
}
