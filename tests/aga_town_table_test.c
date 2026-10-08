/* SPDX-License-Identifier: GPL-2.0-or-later
 * Data-driven town table: lookups, save IDs and a generic town's region
 * directory (the Vivec Arena rows from config/vivec_arena.json). */
#include "quakedef.h"
#include "aw_maps.h"
#include "aw_town.h"
#include "aw_region.h"
#include <assert.h>
server_t sv;
static int broken_prefix,wrong_distance,missing_seyda;
void Con_Printf(char *fmt,...) {}
int COM_FOpenFile(char *name,FILE **f) {
    const char *arena="AWBR1 4 96 540 48 431.25 490.625 270 0 0 0 0\n"
        "va000 -1536 -1536 0 0 -1536 -1536 1536 1536\n"
        "va001 0 -1536 1536 0 -1536 -1536 1536 1536\n"
        "va002 -1536 0 0 1536 -1536 -1536 1536 1536\n"
        "va003 0 0 1536 1536 -1536 -1536 1536 1536\n";
    const char *balmora="AWBR1 2 96 540 50 50 30 90 -500 12 20 66\n"
        "bm000 -512 -512 1024 1024 -512 -512 2048 2048\n"
        "bm001 1024 -512 2048 1024 0 -512 2048 2048\n";
    const char *s=NULL;
    *f=NULL;
    if(!strcmp(name,"vivec_arena-regions.txt"))s=broken_prefix?balmora:arena;
    else if(!strcmp(name,"balmora-regions.txt"))s=balmora;
    else if(!strncmp(name,"maps/",5)){
        if(missing_seyda && !strcmp(name,"maps/seyda.bsp"))return -1;
        s="map";
    }
    if(!s)return -1;
    *f=tmpfile();assert(*f);
    if(wrong_distance && s==arena)fputs("AWBR1 4 96 600 48 431.25 490.625 270 0 0 0 0\n",*f);
    else fputs(s,*f);
    rewind(*f);return s[0]=='m'?124:(int)strlen(s);
}
int main(int argc,char **argv) {
    vec3_t p;float yaw;int seyda=AW_TownFind("seyda"),balmora=AW_TownFind("balmora"),arena=AW_TownFind("vivec_arena");
    /* A directory naming another town's regions or another draw distance
     * than the table certifies is rejected as a whole. */
    if(argc==2){
        broken_prefix=!strcmp(argv[1],"prefix");wrong_distance=!strcmp(argv[1],"distance");
        assert(broken_prefix || wrong_distance);
        assert(!AW_TownArrival("vivec_arena",0,p,&yaw) && !AW_RegionWorldModel("vivec_arena",0));
        assert(AW_TownArrival("balmora",0,p,&yaw));
        return 0;
    }
    /* Table rows, in stable save order: appended towns follow the Arena. */
    assert(AW_TOWN_COUNT>=3 && seyda==0 && balmora==1 && arena==2);
    assert(AW_TownFind("bm000")<0 && AW_TownFind("census")<0 && AW_TownFind(NULL)<0);
    assert(!strcmp(AW_Town(seyda)->prefix,"sn") && !strcmp(AW_Town(balmora)->prefix,"bm") && !strcmp(AW_Town(arena)->prefix,"va"));
    assert(!strcmp(AW_Town(balmora)->regions,"balmora-regions.txt") && !strcmp(AW_Town(arena)->regions,"vivec_arena-regions.txt"));
    assert(AW_Town(seyda)->world_slot==0 && AW_Town(balmora)->world_slot==1 && AW_Town(arena)->world_slot==-1);
    assert(AW_Town(arena)->handoff && AW_Town(arena)->origin[0]==9088 && AW_Town(arena)->origin[1]==-21760);
    assert(AW_Town(arena)->core[0]==-1440 && AW_Town(arena)->core[3]==1440);
    assert(AW_Town(seyda)->draw_distance==540 && AW_Town(arena)->draw_distance==540 && AW_Town(arena)->region_cap==64);
    assert(AW_TownFlag("seyda",AW_TOWN_SEYDA_SCENES) && AW_TownFlag("seyda",AW_TOWN_LEGACY_PAYLOAD));
    assert(!AW_TownFlag("seyda",AW_TOWN_OWN_DOORS) && !AW_TownFlag("seyda",AW_TOWN_SCENERY));
    assert(AW_TownFlag("balmora",AW_TOWN_OWN_DOORS) && AW_TownFlag("balmora",AW_TOWN_SCENERY) &&
           AW_TownFlag("balmora",AW_TOWN_TELEPORT) && AW_TownFlag("balmora",AW_TOWN_GROUND_PLACE));
    assert(AW_TownFlag("vivec_arena",AW_TOWN_SCENERY) && !AW_TownFlag("vivec_arena",AW_TOWN_SEYDA_SCENES));
    /* Travel: Seyda's strider goes to Balmora; Balmora's returns. */
    assert(!strcmp(AW_Town(seyda)->travel_npc,"Darvame Hleran") && !strcmp(AW_Town(seyda)->travel_target,"balmora") && !AW_Town(seyda)->travel_return);
    assert(!strcmp(AW_Town(balmora)->travel_npc,"Selvil Sareloth") && !strcmp(AW_Town(balmora)->travel_target,"seyda") && AW_Town(balmora)->travel_return);
    assert(!AW_Town(arena)->travel_npc[0] && !AW_Town(arena)->travel_target[0]);
    /* Region map names: exactly prefix + 3 digits below the town's cap. */
    assert(AW_TownRegionMap("bm000")==balmora && AW_TownRegionMap("bm063")==balmora && AW_TownRegionMap("bm064")<0);
    assert(AW_TownRegionMap("bm100")<0 && AW_TownRegionMap("bm0a1")<0 && AW_TownRegionMap("bm00")<0 && AW_TownRegionMap("bm0000")<0);
    assert(AW_TownRegionMap("va015")==arena && AW_TownRegionMap("sn045")==seyda && AW_TownRegionMap("vf000")<0);
    /* Save IDs: fixed names unchanged, the extra town clear of interiors. */
    assert(AW_MapId("seyda")==1 && AW_MapId("balmora")==16 && AW_MapId("vf0000")==AW_MAP_COUNT);
    assert(AW_MapId("vivec_arena")==AW_TOWN_MAP_BASE && AW_TOWN_MAP_BASE>AW_INTERIOR_MAP_END);
    assert(AW_TOWN_INTERIOR_BASE==AW_TOWN_MAP_BASE+4096 && AW_SCENE_COUNT==AW_TOWN_INTERIOR_BASE+AW_TOWN_INTERIOR_COUNT);
    assert(!strcmp(AW_MapName(AW_TOWN_MAP_BASE),"vivec_arena") && !strcmp(AW_MapTitle(AW_TOWN_MAP_BASE),"Vivec, Arena"));
    assert(!AW_MapName(AW_TOWN_MAP_BASE-1)[0] && !AW_MapName(AW_INTERIOR_MAP_END)[0] && !AW_MapName(AW_SCENE_COUNT)[0]);
    assert(!AW_MapName(AW_TOWN_MAP_BASE+AW_TOWN_EXTRA_COUNT)[0] && !AW_MapName(AW_TOWN_INTERIOR_BASE-1)[0]);
    /* Town interiors: IDs in list order, round trip, interior classification
     * inputs (no town, no terrain) and the town whose bank leads in. */
    {
        int k;
        for(k=0;k<AW_TOWN_INTERIOR_COUNT;k++){
            const char *room=AW_TownInteriorName(k);
            assert(room[0] && AW_MapId(room)==AW_TOWN_INTERIOR_BASE+k && !strcmp(AW_MapName(AW_TOWN_INTERIOR_BASE+k),room));
            assert(AW_MapTitle(AW_TOWN_INTERIOR_BASE+k)[0] && strcmp(AW_MapTitle(AW_TOWN_INTERIOR_BASE+k),"Cancel"));
            assert(AW_TownFind(room)<0 && AW_TerrainId(room)<0 && AW_TownRegionMap(room)<0 && !AW_MapInteriorSection(room));
            assert(AW_TownInteriorTown(k)>=AW_TOWN_FIXED_COUNT && AW_TownInteriorTown(k)<AW_TOWN_COUNT);
            assert(!strncmp(room,AW_Town(AW_TownInteriorTown(k))->prefix,2) && room[2]=='i');
            assert(AW_MapLogicalId(room)==AW_TOWN_INTERIOR_BASE+k);
        }
        assert(!AW_TownInteriorName(AW_TOWN_INTERIOR_COUNT)[0] && AW_TownInteriorTown(AW_TOWN_INTERIOR_COUNT)<0);
        assert(AW_MapId("zzi999")<0 && AW_MapId("")<0);
    }
    assert(AW_MapLogicalId("vivec_arena")==AW_TOWN_MAP_BASE && AW_MapLogicalId("mi5b8154939f7ab")==AW_INTERIOR_MAP_BASE);
    assert(!AW_MapInteriorSection("vivec_arena") && AW_MapInteriorSection("mi5b8154939f7aa") && !AW_MapInteriorSection("seyda"));
    /* A generic town's directory: va regions, explicit arrival, no return. */
    assert(AW_TownArrival("vivec_arena",0,p,&yaw) && p[0]==48 && p[1]==431.25f && p[2]==490.625f && yaw==270);
    assert(!strcmp(AW_RegionWorldModel("vivec_arena",0),"maps/va003.bsp"));
    assert(!AW_TownArrival("vivec_arena",1,p,&yaw));
    strcpy(sv.name,"vivec_arena");p[0]=100;p[1]=-100;p[2]=0;
    assert(AW_RegionCrossing(p,0) && AW_RegionSelect("vivec_arena",p,0));
    assert(!strcmp(AW_RegionWorldModel("vivec_arena",0),"maps/va001.bsp"));
    assert(AW_RegionContains(p) && !AW_RegionCrossing(p,0));
    /* Seyda-only sub-scenes never apply to other towns, even with intro set. */
    assert(AW_RegionSelect("vivec_arena",p,1) && !strcmp(AW_RegionWorldModel("vivec_arena",1),"maps/va001.bsp"));
    /* Balmora returns to its travel target, which must exist. */
    assert(AW_TownArrival("balmora",1,p,&yaw) && p[0]==-500 && yaw==66);
    missing_seyda=1;assert(!AW_TownArrival("balmora",1,p,&yaw) && AW_TownArrival("balmora",0,p,&yaw));missing_seyda=0;
    assert(!AW_TownArrival("census",0,p,&yaw));
    return 0;
}
