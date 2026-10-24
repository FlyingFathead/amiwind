/* SPDX-License-Identifier: GPL-2.0-or-later
 * BUILD-LEGACY-ENGINE-PATHS-48: aw_region.c built with AW_LEGACY_TOWN_REGIONS 0 (the legacy town region streaming
 * left out) runs every CHIM town as before, and a town without its CHIM frame map no longer falls back to region
 * maps: it has no exterior (select 0, no world model, no arrival, no crossings). Compiled with
 * -DAW_LEGACY_TOWN_REGIONS=0 by tests/test_aga_native_source.py. */
#include "quakedef.h"
#include "aw_region.h"
#include "aw_town.h"
#include <assert.h>
#if AW_LEGACY_TOWN_REGIONS
#error "build this test with -DAW_LEGACY_TOWN_REGIONS=0"
#endif
server_t sv;
void Con_Printf(char *fmt,...) {}
int COM_FOpenFile(char *name,FILE **f) {
    const char *s="AWBR1 4 96 540 50 50 30 90 -500 12 20 66\n"
        "bm000 -512 -512 1024 1024 -512 -512 2048 2048\n"
        "bm001 1024 0 2048 1024 0 0 2048 2048\n"
        "bm002 0 1024 1024 2048 0 0 2048 2048\n"
        "bm003 1024 1024 2048 2048 0 0 2048 2048\n";
    *f=tmpfile();assert(*f);fputs(s,*f);
    if(!strcmp(name,"seyda-regions.txt")){long pos;int c;rewind(*f);while((c=fgetc(*f))!=EOF){if(c=='b'){pos=ftell(*f);fseek(*f,pos-1,SEEK_SET);fputc('s',*f);fputc('n',*f);fflush(*f);}}}
    rewind(*f);return strlen(s);
}
extern const char *(*aw_chim_town_map)(const char *);
static const char *town_map(const char *town)
{
    if(!strcmp(town,"balmora"))return "maps/balmora-chim.chim";
    if(!strcmp(town,"seyda"))return "maps/seyda-chim.chim";
    if(!strcmp(town,"intro_docks"))return "maps/intro_docks-chim.chim";
    if(!strcmp(town,"sncourt"))return "maps/sncourt-chim.chim";
    return NULL;
}
int main(void) {
    vec3_t p={5000,5000,0},v={100,0,0};float yaw;char map[16];
    aw_chim_town_map=town_map;
    /* CHIM towns: the frame map, no crossings, the region table still answers (harvest, saves) */
    assert(AW_RegionSelect("balmora",p,0));
    assert(!strcmp(AW_RegionWorldModel("balmora",0),"maps/balmora-chim.chim"));
    strcpy(sv.name,"balmora");strcpy(sv.modelname,"maps/balmora-chim.chim");
    p[0]=p[1]=50;
    assert(!AW_RegionCrossing(p,0) && !AW_RegionAhead(p,v,0,2) && AW_RegionContains(p));
    assert(AW_RegionAt(p,-1,map,sizeof(map))==0 && !strcmp(map,"bm000"));
    assert(AW_TownArrival("balmora",0,p,&yaw) && p[0]==50 && yaw==90);
    /* Seyda Neen: the intro docks' and the courtyard's own frame maps, the town's elsewhere */
    p[0]=695;p[1]=50;assert(AW_RegionSelect("seyda",p,1));
    assert(!strcmp(AW_RegionWorldModel("seyda",1),"maps/intro_docks-chim.chim"));
    p[0]=52;p[1]=-152;assert(AW_RegionSelect("seyda",p,0));
    assert(!strcmp(AW_RegionWorldModel("seyda",0),"maps/sncourt-chim.chim"));
    p[0]=p[1]=50;assert(AW_RegionSelect("seyda",p,0));
    assert(!strcmp(AW_RegionWorldModel("seyda",0),"maps/seyda-chim.chim"));
    /* No frame map (or chim_towns 0): no legacy fallback in this engine */
    aw_chim_town_map=NULL;strcpy(sv.name,"balmora");strcpy(sv.modelname,"maps/bm000.bsp");
    p[0]=p[1]=50;
    assert(!AW_RegionSelect("balmora",p,0));
    assert(AW_RegionWorldModel("balmora",0)==NULL);
    assert(!AW_TownArrival("balmora",0,p,&yaw));
    p[0]=1121;assert(!AW_RegionCrossing(p,0) && !AW_RegionAhead(p,v,0,2));
    return 0;
}
