/* SPDX-License-Identifier: GPL-2.0-or-later
 * Saved equipment intent. Include after quakedef.h and aw_save.h.
 * Use the transition validator without persisting its animation or VM state. */
#ifndef AW_SAVED_EQUIPMENT_H
#define AW_SAVED_EQUIPMENT_H
#include "aw_hand_state.h"
static int AW_SavedEquipmentCapture(uint32_t *flags,edict_t *p,double now)
{
    aw_hand_snapshot_t hand;uint32_t value=0;
    if(!flags || !p || !AW_HandSnapshotCapture(&hand,p,now))return 0;
    /* Current server rules only own this model; race/sex and torch appearances
     * are chosen locally. Reject unsupported weapons rather than lose them. */
    if(hand.model[0] && strcmp(hand.model,"progs/v_nord.mdl"))return 0;
    if(hand.goal){
        value=AW_EQUIPMENT_DRAWN;
        if(hand.torch)value|=AW_EQUIPMENT_TORCH;
    }
    *flags=value;return 1;
}
static int AW_SavedEquipmentRestore(uint32_t flags,edict_t *p,double now)
{
    aw_hand_snapshot_t hand;
    if(!p || (flags&~AW_EQUIPMENT_MASK) ||
       ((flags&AW_EQUIPMENT_TORCH) && !(flags&AW_EQUIPMENT_DRAWN)))return 0;
    memset(&hand,0,sizeof(hand));hand.valid=1;
    if(flags&AW_EQUIPMENT_DRAWN){
        hand.goal=1;hand.state=2;hand.torch=(flags&AW_EQUIPMENT_TORCH)?1:0;
        strcpy(hand.model,"progs/v_nord.mdl");
    }
    /* Ready/hidden at frame0. Never resume an attack, held input or stale clock.
     * Restore checks the new VM's fields/precache before changing anything. */
    return AW_HandSnapshotRestore(&hand,p,now);
}
#endif
