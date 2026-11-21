/* SPDX-License-Identifier: GPL-2.0-or-later
 * NPCs drown: the engine side of aw_drown.h (ACTOR-DROWNING-NOT-CARRIED-67, v0.0.68). Every server frame, after the
 * player's breath (aw_breath.c AW_BreathPhysics): in a room whose cell has the water flag, each living NPC edict's head
 * point is tested against hull 0 (SV_PointContents); one under water gets a row of the fixed table, its breath falls,
 * and once it is gone the NPC loses the suffocation damage through its own record (aw_mwhost.c AW_MwscriptActorHurt:
 * the death by the scripts' death path). The breath left is kept as a named fact of the world change list, so a save
 * made under water loads with it. Fixed state only (the table: 32 rows of 8 bytes), no allocation; nothing runs in a dry
 * room or outdoors. */
#include "quakedef.h"
#include "aw_breath.h"
#include "aw_drown.h"
#include "aw_actors.h"
#include "aw_combat.h"
#include "aw_effects.h"
#include "aw_ledger.h"
#include "aw_reset.h"

static aw_drown_table_t table;
static void *table_map;                  /* the map the rows' edicts belong to */
static unsigned long frames,checked,submerged_seen,restored,deaths,hurt_misses;
static float damage;

/* a resident NPC that is alive by the combat layer and shown (aw_drown.h AW_DrownTakes); its health lives in its actor
 * record and fight sheet, never in the edict's own health field (resident NPCs leave it 0: the first check read it and
 * took no NPC in play, ACTOR-DROWNING-NOT-CARRIED-67 seen again 2026-11-20) */
static int npc(edict_t *e)
{
    return e && !e->free && e->v.classname && !strcmp(pr_strings+e->v.classname,"aw_npc") &&
           AW_DrownTakes(AW_CombatSlotState(e,NULL),e->v.modelindex!=0);
}

static int under_water(const edict_t *e)
{
    vec3_t p;int c;
    VectorCopy(e->v.origin,p);
    p[2]+=e->v.mins[2]+AW_DrownHeadHeight(e->v.maxs[2]-e->v.mins[2]);
    c=SV_PointContents(p);
    return c==CONTENTS_WATER || c==CONTENTS_SLIME;
}

static int water_breathing(edict_t *e)
{
    return aw_combat_effect_magnitude && aw_combat_effect_magnitude(e,AW_EFFECT_WATER_BREATHING)>0;
}

void AW_DrownPhysics(void)
{
    aw_breath_settings_t s;int i,row;float dt=(float)host_frametime,loss;char id[32];int32_t kept;
    if(table_map!=(void *)sv.worldmodel){table_map=(void *)sv.worldmodel;table.count=0;}
    if(!sv.active || !(dt>0) || !AW_MwscriptRoomWater())return;
    AW_BreathSettingsGet(&s);
    frames++;
    for(i=1;i<sv.num_edicts;i++){
        edict_t *e=EDICT_NUM(i);uint32_t ref;int under;
        if(!npc(e))continue;
        checked++;
        under=under_water(e);
        ref=AW_MwscriptNpcReference(e);
        row=AW_DrownRow(&table,ref,0);
        if(row<0){
            if(!under)continue;
            if((row=AW_DrownRow(&table,ref,1))<0)continue;     /* the table full: counted in table.full */
            AW_DrownFactId(id,ref);
            if(AW_LedgerFact(&aw_ledger,id,&kept) && AW_DrownFactLeft((long)kept)>=0 && AW_DrownFactLeft((long)kept)<s.hold){
                table.row[row].left=AW_DrownFactLeft((long)kept);restored++;
            }
        }
        if(under)submerged_seen++;
        if(!AW_DrownStep(&table,row,under,under && water_breathing(e),s.hold,s.suffocation,dt,&loss)){
            AW_DrownFactId(id,ref);
            AW_LedgerFactSet(&aw_ledger,id,(int32_t)AW_DrownFactValue(s.hold));   /* full again */
            AW_DrownDrop(&table,row);
            continue;
        }
        AW_DrownFactId(id,ref);
        AW_LedgerFactSet(&aw_ledger,id,(int32_t)AW_DrownFactValue(table.row[row].left));
        if(loss>0){
            int r=AW_MwscriptActorHurt(e,loss);
            if(r<0){hurt_misses++;continue;}
            damage+=loss;
            if(r>0){deaths++;AW_DrownDrop(&table,row);}
        }
    }
}

void AW_DrownStatus(void)
{
    int i;
    Con_Printf(" NPCs: %s; %ld under water now (%d rows, %lu not kept: the table full); %lu frames, %lu NPC checks, "
               "%lu submerged, %lu breaths read back from the saved changes, %.1f health taken, %lu drowned, %lu without "
               "a record\n",AW_MwscriptRoomWater()?"checked in this room":"not checked here (outdoors or a dry room)",
               (long)table.count,AW_DROWN_ROWS,table.full,frames,checked,submerged_seen,restored,damage,deaths,hurt_misses);
    for(i=0;i<table.count;i++)
        Con_Printf("  reference %lu: %.1f s of breath left\n",(unsigned long)table.row[i].reference,table.row[i].left);
}

/* New Game: no row, nothing counted (the facts go with the world change list) */
static void reset_drown(int new_game)
{
    (void)new_game;
    memset(&table,0,sizeof(table));table_map=NULL;
    frames=checked=submerged_seen=restored=deaths=hurt_misses=0;damage=0;
}
static unsigned long digest_drown(void)
{
    return AW_ResetHash(AW_RESET_SEED,&table.count,sizeof(table.count));
}

void AW_DrownInit(void)
{
    AW_ResetRegister("breath of NPCs (drowning)",reset_drown,digest_drown);
}
