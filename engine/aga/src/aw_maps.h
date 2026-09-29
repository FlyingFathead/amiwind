/* SPDX-License-Identifier: GPL-2.0-or-later
 * Stable save IDs. Keep in sync with config/seyda_area.json; never reorder.
 */
#ifndef AW_MAPS_H
#define AW_MAPS_H
#include <string.h>
#define AW_MAP_COUNT 16
static __inline__ int AW_MapId(const char *name)
{
    static const char *const names[AW_MAP_COUNT] = {"prison","seyda","census","tradehouse","warehouse","draren","eldafire","erene","fargoth","finemouth","foryn","indrele","lighthouse","terurise","vodunius","addamasartus"};
    int i;
    for(i=0;i<AW_MAP_COUNT;i++)if(!strcmp(name,names[i]))return i;
    return -1;
}
static __inline__ const char *AW_MapName(int id)
{
    static const char *const names[AW_MAP_COUNT] = {"prison","seyda","census","tradehouse","warehouse","draren","eldafire","erene","fargoth","finemouth","foryn","indrele","lighthouse","terurise","vodunius","addamasartus"};
    return id>=0 && id<AW_MAP_COUNT ? names[id] : "";
}
static __inline__ const char *AW_MapTitle(int id)
{
    static const char *const titles[AW_MAP_COUNT] = {"Imperial Prison Ship","Seyda Neen","Census and Excise Office","Arrille's Tradehouse","Census and Excise Warehouse","Draren Thiralas' House","Eldafire's House","Erene Llenim's Shack","Fargoth's House","Fine-Mouth's Shack","Foryn Gilnith's Shack","Indrele Rathryon's Shack","Lighthouse","Terurise Girvayne's House","Vodunius Nuccius' House","Addamasartus"};
    return id>=0 && id<AW_MAP_COUNT ? titles[id] : "Cancel";
}
#endif
