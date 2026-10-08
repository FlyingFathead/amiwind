/* SPDX-License-Identifier: GPL-2.0-or-later
 * Stable save IDs. Keep in sync with config/seyda_area.json and balmora_interiors.json; never reorder.
 */
#ifndef AW_MAPS_H
#define AW_MAPS_H
#include <string.h>
#include <stdio.h>
#include "aw_town_table.h"
#define AW_MAP_COUNT 60
#define AW_INTERIOR_MAP_BASE (AW_MAP_COUNT+8192)
#define AW_INTERIOR_MAP_COUNT 2
#define AW_INTERIOR_MAP_END (AW_INTERIOR_MAP_BASE+AW_INTERIOR_MAP_COUNT)
/* Towns after Seyda and Balmora (aw_town_table.h rows AW_TOWN_FIXED_COUNT..)
 * take fixed IDs here, clear of the appendable interior range. */
#define AW_TOWN_MAP_BASE 16384
/* Interiors of the table's towns (aw_town_table.h, append-only lists) take
 * fixed IDs after the extra towns' range. */
#define AW_TOWN_INTERIOR_BASE (AW_TOWN_MAP_BASE+4096)
#define AW_SCENE_COUNT (AW_TOWN_INTERIOR_BASE+AW_TOWN_INTERIOR_COUNT)
typedef char aw_town_extra_range_check[AW_TOWN_EXTRA_COUNT<4096?1:-1];
static __inline__ const char *AW_InteriorMapName(int n)
{
    static const char *const names[AW_INTERIOR_MAP_COUNT]={"mi5b8154939f7aa","mi5b8154939f7ab"};
    return n>=0 && n<AW_INTERIOR_MAP_COUNT?names[n]:"";
}

static __inline__ const char *AW_TownExtraName(int n)
{
    static const char *const names[AW_TOWN_EXTRA_COUNT>0?AW_TOWN_EXTRA_COUNT:1]=AW_TOWN_EXTRA_NAMES;
    return n>=0 && n<AW_TOWN_EXTRA_COUNT?names[n]:"";
}
static __inline__ const char *AW_TownExtraTitle(int n)
{
    static const char *const titles[AW_TOWN_EXTRA_COUNT>0?AW_TOWN_EXTRA_COUNT:1]=AW_TOWN_EXTRA_TITLES;
    return n>=0 && n<AW_TOWN_EXTRA_COUNT?titles[n]:"Cancel";
}

static __inline__ const char *AW_TownInteriorName(int n)
{
    static const char *const names[AW_TOWN_INTERIOR_COUNT>0?AW_TOWN_INTERIOR_COUNT:1]=AW_TOWN_INTERIOR_NAMES;
    return n>=0 && n<AW_TOWN_INTERIOR_COUNT?names[n]:"";
}
static __inline__ const char *AW_TownInteriorTitle(int n)
{
    static const char *const titles[AW_TOWN_INTERIOR_COUNT>0?AW_TOWN_INTERIOR_COUNT:1]=AW_TOWN_INTERIOR_TITLES;
    return n>=0 && n<AW_TOWN_INTERIOR_COUNT?titles[n]:"Cancel";
}
/* Table row of the town whose door bank leads into a town interior, or -1. */
static __inline__ int AW_TownInteriorTown(int n)
{
    static const int towns[AW_TOWN_INTERIOR_COUNT>0?AW_TOWN_INTERIOR_COUNT:1]=AW_TOWN_INTERIOR_TOWNS;
    return n>=0 && n<AW_TOWN_INTERIOR_COUNT?towns[n]:-1;
}

static __inline__ int AW_TerrainId(const char *name)
{
    int i,n=0;if(strlen(name)!=6 || name[0]!='v' || name[1]!='f')return -1;
    for(i=2;i<6;i++){if(name[i]<'0' || name[i]>'9')return -1;n=n*10+name[i]-'0';}
    return n<8192?n:-1;
}
static __inline__ int AW_MapId(const char *name)
{
    static const char *const names[AW_MAP_COUNT] = {"prison","seyda","census","tradehouse","warehouse","draren","eldafire","erene","fargoth","finemouth","foryn","indrele","lighthouse","terurise","vodunius","addamasartus","balmora","bmastius","bmbalyn","bmcaius","bmclagius","bmcouncil","bmbooks","bmdralasa","bmdralcea","bmdralosa","bmdrarayne","bmstorage","bmdura","bmeastguard","bmeightplates","bmeddie","bmfighters","bmmages","bmhecerinde","bmhlaalo","bmhlaalucouncil","bmitan","bmkarlirah","bmluckylockup","bmmeldor","bmmilie","bmmoragtong","bmnalcarya","bmnerano","bmninetoes","bmravirr","bmrarayn","bmrithleen","bmsouthwall","bmtemple","bmrazorhole","bmtsiya","bmtyermaillin","bmtyravel","bmvorar","bmvori","bmwestnorth","bmwestsouth","tharystomb"};
    int i;
    for(i=0;i<AW_MAP_COUNT;i++)if(!strcmp(name,names[i]))return i;
    i=AW_TerrainId(name);if(i>=0)return AW_MAP_COUNT+i;
    for(i=0;i<AW_INTERIOR_MAP_COUNT;i++)if(!strcmp(name,AW_InteriorMapName(i)))return AW_INTERIOR_MAP_BASE+i;
    for(i=0;i<AW_TOWN_EXTRA_COUNT;i++)if(!strcmp(name,AW_TownExtraName(i)))return AW_TOWN_MAP_BASE+i;
    for(i=0;i<AW_TOWN_INTERIOR_COUNT;i++)if(!strcmp(name,AW_TownInteriorName(i)))return AW_TOWN_INTERIOR_BASE+i;
    return -1;
}
static __inline__ const char *AW_MapName(int id)
{
    static const char *const names[AW_MAP_COUNT] = {"prison","seyda","census","tradehouse","warehouse","draren","eldafire","erene","fargoth","finemouth","foryn","indrele","lighthouse","terurise","vodunius","addamasartus","balmora","bmastius","bmbalyn","bmcaius","bmclagius","bmcouncil","bmbooks","bmdralasa","bmdralcea","bmdralosa","bmdrarayne","bmstorage","bmdura","bmeastguard","bmeightplates","bmeddie","bmfighters","bmmages","bmhecerinde","bmhlaalo","bmhlaalucouncil","bmitan","bmkarlirah","bmluckylockup","bmmeldor","bmmilie","bmmoragtong","bmnalcarya","bmnerano","bmninetoes","bmravirr","bmrarayn","bmrithleen","bmsouthwall","bmtemple","bmrazorhole","bmtsiya","bmtyermaillin","bmtyravel","bmvorar","bmvori","bmwestnorth","bmwestsouth","tharystomb"};
    static char terrain[8];
    if(id>=AW_MAP_COUNT && id<AW_INTERIOR_MAP_BASE){sprintf(terrain,"vf%04ld",(long)(id-AW_MAP_COUNT));return terrain;}
    if(id>=AW_INTERIOR_MAP_BASE && id<AW_INTERIOR_MAP_END)return AW_InteriorMapName(id-AW_INTERIOR_MAP_BASE);
    if(id>=AW_TOWN_MAP_BASE && id<AW_TOWN_INTERIOR_BASE)return AW_TownExtraName(id-AW_TOWN_MAP_BASE);
    if(id>=AW_TOWN_INTERIOR_BASE && id<AW_SCENE_COUNT)return AW_TownInteriorName(id-AW_TOWN_INTERIOR_BASE);
    return id>=0 && id<AW_MAP_COUNT ? names[id] : "";
}
static __inline__ const char *AW_MapTitle(int id)
{
    static const char *const titles[AW_MAP_COUNT] = {"Imperial Prison Ship","Seyda Neen","Census and Excise Office","Arrille's Tradehouse","Census and Excise Warehouse","Draren Thiralas' House","Eldafire's House","Erene Llenim's Shack","Fargoth's House","Fine-Mouth's Shack","Foryn Gilnith's Shack","Indrele Rathryon's Shack","Lighthouse","Terurise Girvayne's House","Vodunius Nuccius' House","Addamasartus","Balmora","Astius Hanotepelus' House","Balyn Omarel's House","Caius Cosades' House","Clagius Clanler: Outfitter","Council Club","Dorisa Darvel: Bookseller","Dralasa Nithryon: Pawnbroker","Dralcea Arethi's House","Dralosa Athren's House","Drarayne Thelas' House","Drarayne Thelas' Storage","Dura gra-Bol's House","Eastern Guard Tower","Eight Plates","Fast Eddie's House","Guild of Fighters","Guild of Mages","Hecerinde's House","Hlaalo Manor","Hlaalu Council Manor","Itan's House","Karlirah's House","Lucky Lockup","Meldor: Armorer","Milie Hastien: Fine Clothier","Morag Tong Guild","Nalcarya of White Haven: Fine Alchemist","Nerano Manor","Nine Toes' House","Ra'Virr: Trader","Rarayn Radarys' House","Rithleen's House","South Wall Cornerclub","Temple","The Razor Hole","Tsiya's House","Tyermaillin's House","Tyravel Manor","Vorar Helas' House","Vori's House","Western Guard Tower North","Western Guard Tower South","Tharys Ancestral Tomb"};
    if(id>=AW_MAP_COUNT && id<AW_INTERIOR_MAP_BASE)return "Vvardenfell";
    if(id>=AW_INTERIOR_MAP_BASE && id<AW_INTERIOR_MAP_END)return "Abaelun Mine";
    if(id>=AW_TOWN_MAP_BASE && id<AW_TOWN_INTERIOR_BASE)return AW_TownExtraTitle(id-AW_TOWN_MAP_BASE);
    if(id>=AW_TOWN_INTERIOR_BASE && id<AW_SCENE_COUNT)return AW_TownInteriorTitle(id-AW_TOWN_INTERIOR_BASE);
    return id>=0 && id<AW_MAP_COUNT ? titles[id] : "Cancel";
}
/* Actor facts use the original cell; save.scene still names the physical section. */
static __inline__ int AW_MapLogicalId(const char *name)
{
    int id=AW_MapId(name);
    return id>=AW_INTERIOR_MAP_BASE && id<AW_INTERIOR_MAP_END?AW_INTERIOR_MAP_BASE:id;
}
/* Physical sections of one sectioned interior (aw_section.c). */
static __inline__ int AW_MapInteriorSection(const char *name)
{
    int id=AW_MapId(name);
    return id>=AW_INTERIOR_MAP_BASE && id<AW_INTERIOR_MAP_END;
}
#endif
