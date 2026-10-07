/* SPDX-License-Identifier: GPL-2.0-or-later
 * Location fog: off by default; when on, listed places blend from the day to
 * the night distance as the sky darkens; the player's setting stays the bound;
 * unlisted places and interiors are unchanged; the table is read once per place. */
#include "../src/quakedef.h"
#include <assert.h>
server_t sv;int r_daylight=256;static int exterior=1,opens;
int R_SkyExterior(void){return exterior;}
static cvar_t *var;
void Cvar_RegisterVariable(cvar_t *v){var=v;v->value=(float)atof(v->string);}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
int COM_FOpenFile(char *path,FILE **file){
    static const char text[]="# comment\nseyda 400 notanumber\nbalmora 300 250\n";
    FILE *f;assert(!strcmp(path,"world/fog-locations.txt"));opens++;
    f=tmpfile();assert(f);fputs(text,f);rewind(f);*file=f;return (int)strlen(text);
}
int (*aw_fog_location_hook)(int);
void AW_FogLocationInit(void);
int main(void){
    AW_FogLocationInit();assert(aw_fog_location_hook && var && var->value==0 && var->archive);
    sv.active=1;strcpy(sv.name,"balmora");
    assert(aw_fog_location_hook(540)==540 && opens==0);             /* off by default */
    var->value=1;
    assert(aw_fog_location_hook(540)==300 && opens==1);             /* full day */
    r_daylight=128;assert(aw_fog_location_hook(540)==250);          /* night */
    r_daylight=192;assert(aw_fog_location_hook(540)==275);          /* dusk: halfway */
    r_daylight=40;assert(aw_fog_location_hook(540)==250);           /* darker than full night */
    assert(aw_fog_location_hook(200)==200);                         /* player's shorter setting wins */
    assert(opens==1);                                               /* read once per place */
    exterior=0;assert(aw_fog_location_hook(540)==540);exterior=1;   /* interiors unchanged */
    strcpy(sv.name,"seyda");assert(aw_fog_location_hook(540)==540 && opens==2); /* unlisted / bad line */
    puts("location fog: off by default, day/night blend, player bound, interiors, per-place read");
    return 0;
}
