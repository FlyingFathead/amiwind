/* SPDX-License-Identifier: GPL-2.0-or-later
 * Stable save IDs. Keep in sync with config/seyda_area.json and balmora_interiors.json; never reorder.
 */
#ifndef AW_MAPS_H
#define AW_MAPS_H
#include <string.h>
#define AW_MAP_COUNT 60
static __inline__ int AW_MapId(const char *name)
{
    static const char *const names[AW_MAP_COUNT] = {"prison","seyda","census","tradehouse","warehouse","draren","eldafire","erene","fargoth","finemouth","foryn","indrele","lighthouse","terurise","vodunius","addamasartus","balmora","bmastius","bmbalyn","bmcaius","bmclagius","bmcouncil","bmbooks","bmdralasa","bmdralcea","bmdralosa","bmdrarayne","bmstorage","bmdura","bmeastguard","bmeightplates","bmeddie","bmfighters","bmmages","bmhecerinde","bmhlaalo","bmhlaalucouncil","bmitan","bmkarlirah","bmluckylockup","bmmeldor","bmmilie","bmmoragtong","bmnalcarya","bmnerano","bmninetoes","bmravirr","bmrarayn","bmrithleen","bmsouthwall","bmtemple","bmrazorhole","bmtsiya","bmtyermaillin","bmtyravel","bmvorar","bmvori","bmwestnorth","bmwestsouth","tharystomb"};
    int i;
    for(i=0;i<AW_MAP_COUNT;i++)if(!strcmp(name,names[i]))return i;
    return -1;
}
static __inline__ const char *AW_MapName(int id)
{
    static const char *const names[AW_MAP_COUNT] = {"prison","seyda","census","tradehouse","warehouse","draren","eldafire","erene","fargoth","finemouth","foryn","indrele","lighthouse","terurise","vodunius","addamasartus","balmora","bmastius","bmbalyn","bmcaius","bmclagius","bmcouncil","bmbooks","bmdralasa","bmdralcea","bmdralosa","bmdrarayne","bmstorage","bmdura","bmeastguard","bmeightplates","bmeddie","bmfighters","bmmages","bmhecerinde","bmhlaalo","bmhlaalucouncil","bmitan","bmkarlirah","bmluckylockup","bmmeldor","bmmilie","bmmoragtong","bmnalcarya","bmnerano","bmninetoes","bmravirr","bmrarayn","bmrithleen","bmsouthwall","bmtemple","bmrazorhole","bmtsiya","bmtyermaillin","bmtyravel","bmvorar","bmvori","bmwestnorth","bmwestsouth","tharystomb"};
    return id>=0 && id<AW_MAP_COUNT ? names[id] : "";
}
static __inline__ const char *AW_MapTitle(int id)
{
    static const char *const titles[AW_MAP_COUNT] = {"Imperial Prison Ship","Seyda Neen","Census and Excise Office","Arrille's Tradehouse","Census and Excise Warehouse","Draren Thiralas' House","Eldafire's House","Erene Llenim's Shack","Fargoth's House","Fine-Mouth's Shack","Foryn Gilnith's Shack","Indrele Rathryon's Shack","Lighthouse","Terurise Girvayne's House","Vodunius Nuccius' House","Addamasartus","Balmora","Astius Hanotepelus' House","Balyn Omarel's House","Caius Cosades' House","Clagius Clanler: Outfitter","Council Club","Dorisa Darvel: Bookseller","Dralasa Nithryon: Pawnbroker","Dralcea Arethi's House","Dralosa Athren's House","Drarayne Thelas' House","Drarayne Thelas' Storage","Dura gra-Bol's House","Eastern Guard Tower","Eight Plates","Fast Eddie's House","Guild of Fighters","Guild of Mages","Hecerinde's House","Hlaalo Manor","Hlaalu Council Manor","Itan's House","Karlirah's House","Lucky Lockup","Meldor: Armorer","Milie Hastien: Fine Clothier","Morag Tong Guild","Nalcarya of White Haven: Fine Alchemist","Nerano Manor","Nine Toes' House","Ra'Virr: Trader","Rarayn Radarys' House","Rithleen's House","South Wall Cornerclub","Temple","The Razor Hole","Tsiya's House","Tyermaillin's House","Tyravel Manor","Vorar Helas' House","Vori's House","Western Guard Tower North","Western Guard Tower South","Tharys Ancestral Tomb"};
    return id>=0 && id<AW_MAP_COUNT ? titles[id] : "Cancel";
}
#endif
