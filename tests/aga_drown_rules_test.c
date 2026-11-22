/* SPDX-License-Identifier: GPL-2.0-or-later
 * The NPCs' drowning rules (engine/aga/src/aw_drown_rules.c with aw_breath_rules.c; ACTOR-DROWNING-NOT-CARRIED-67):
 * an NPC under water holds its breath for fHoldBreathTime (20 s), then loses fSuffocationDamage (3) health a second;
 * Water Breathing keeps the breath full; out of the water it is full at once and the row can go; the head point is
 * the height over the feet / fSwimHeightScale (0.9, OpenMW World::isSubmerged); which resident NPCs are checked (alive
 * by the combat layer and shown, never by the edict's own health field); the fixed table refuses and counts a 33rd NPC,
 * drops a row in place; the saved fact's id and its exact bits. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "aw_breath.h"
#include "aw_drown.h"

static int near(float a,float b){return fabs(a-b)<1e-4f;}

int main(void)
{
    aw_drown_table_t t;int i,r,k;float loss,total=0;char id[32];
    memset(&t,0,sizeof(t));
    /* a row for a reference, found again, none for 0 */
    r=AW_DrownRow(&t,4212345,1);
    assert(r==0 && t.count==1 && t.row[0].left<0 && AW_DrownRow(&t,4212345,0)==0 && AW_DrownRow(&t,0,1)==-1);
    assert(AW_DrownRow(&t,99,0)==-1 && t.count==1);
    /* 18 s under water: the breath falls, no damage yet (nine steps of 2 s); the step that empties it already takes
     * its 2 s of damage (OpenMW: the time left reaches 0, then the damage of that frame) */
    for(i=0;i<9;i++){assert(AW_DrownStep(&t,r,1,0,20,3,2,&loss));assert(loss==0);}
    assert(near(t.row[r].left,2));
    assert(AW_DrownStep(&t,r,1,0,20,3,2,&loss) && near(t.row[r].left,0) && near(loss,6));
    /* then 3 health a second: 5 s take 15 */
    for(i=0;i<5;i++){assert(AW_DrownStep(&t,r,1,0,20,3,1,&loss));total+=loss;}
    assert(near(total,15));
    /* Water Breathing under water: full at once, the row stays while it is under water */
    assert(AW_DrownStep(&t,r,1,1,20,3,1,&loss) && loss==0 && near(t.row[r].left,20));
    /* under water again for 5 s, then out: full at once and the row can go */
    for(i=0;i<5;i++)AW_DrownStep(&t,r,1,0,20,3,1,&loss);
    assert(near(t.row[r].left,15));
    assert(!AW_DrownStep(&t,r,0,0,20,3,1,&loss) && loss==0 && near(t.row[r].left,20));
    /* the head point: the height / 0.9 over the feet (a 64-unit actor: 71.1) */
    assert(near(AW_DrownHeadHeight(64),64/0.9f));
    /* which resident NPCs are checked (ACTOR-DROWNING-NOT-CARRIED-67 seen again in play, 2026-11-20): one not fighting
     * or fighting and shown is taken, whatever its edict's own health field holds (residents leave it 0); a dead one
     * (the combat layer's state 2) or a hidden one is not */
    assert(AW_DrownTakes(0,1) && AW_DrownTakes(1,1));
    assert(!AW_DrownTakes(2,1) && !AW_DrownTakes(0,0) && !AW_DrownTakes(1,0));
    /* the table: 32 rows, a 33rd refused and counted; a drop moves the last row into its place */
    for(k=1;k<AW_DROWN_ROWS;k++)assert(AW_DrownRow(&t,(uint32_t)(1000+k),1)==k);
    assert(t.count==AW_DROWN_ROWS && AW_DrownRow(&t,5000,1)==-1 && t.full==1);
    AW_DrownDrop(&t,0);
    assert(t.count==AW_DROWN_ROWS-1 && t.row[0].reference==1000+AW_DROWN_ROWS-1 && AW_DrownRow(&t,4212345,0)==-1);
    AW_DrownDrop(&t,99);assert(t.count==AW_DROWN_ROWS-1);
    assert(!AW_DrownStep(&t,-1,1,0,20,3,1,&loss) && loss==0);
    /* ACTOR-KNOCKED-OUT-IN-WATER-DROWNS-68 (OpenMW actors.cpp 1013-1019): knocked out (2) with the feet under water, the
     * breath is gone at once and the same frame takes its damage; a knock-down (1), dry feet or no row change nothing */
    memset(&t,0,sizeof(t));
    r=AW_DrownRow(&t,4212346,1);
    assert(!AW_DrownKnockedOut(&t,r,1,1) && t.row[r].left<0);
    assert(!AW_DrownKnockedOut(&t,r,2,0) && t.row[r].left<0);
    assert(!AW_DrownKnockedOut(&t,5,2,1) && !AW_DrownKnockedOut(NULL,0,2,1));
    assert(AW_DrownKnockedOut(&t,r,2,1) && t.row[r].left==0);
    assert(AW_DrownStep(&t,r,1,0,20,3,0.5f,&loss) && near(loss,1.5f) && t.row[r].left==0);
    /* Water Breathing still keeps a knocked-out NPC breathing (OpenMW: the magnitude check covers both cases) */
    assert(AW_DrownKnockedOut(&t,r,2,1) && AW_DrownStep(&t,r,1,1,20,3,0.5f,&loss) && loss==0 && near(t.row[r].left,20));
    /* ACTOR-DROWN-SOUND-68 (OpenMW actors.cpp 1039-1043): a new row's sound is due at its first damage; then again only
     * once the sample's length has passed; no damage, no sound; a sample under 0.1 s counts as 0.1 s */
    assert(t.row[r].sound==0);
    assert(!AW_DrownSoundDue(&t,r,0,0.5f,1.5f) && t.row[r].sound==0);
    assert(AW_DrownSoundDue(&t,r,3,0.5f,1.5f) && near(t.row[r].sound,1.5f));
    assert(!AW_DrownSoundDue(&t,r,3,0.5f,1.5f) && near(t.row[r].sound,1.0f));
    assert(!AW_DrownSoundDue(&t,r,0,0.5f,1.5f) && near(t.row[r].sound,0.5f));
    assert(AW_DrownSoundDue(&t,r,3,0.5f,1.5f) && near(t.row[r].sound,1.5f));
    t.row[r].sound=0;
    assert(AW_DrownSoundDue(&t,r,3,0.5f,0) && near(t.row[r].sound,0.1f));
    assert(!AW_DrownSoundDue(&t,-1,3,0.5f,1.5f) && !AW_DrownSoundDue(NULL,0,3,0.5f,1.5f));
    /* the saved fact: its id, the breath's exact bits there and back */
    AW_DrownFactId(id,4212345);
    assert(!strcmp(id,"amiwind:breath:4212345"));
    assert(AW_DrownFactLeft(AW_DrownFactValue(7.25f))==7.25f && AW_DrownFactLeft(AW_DrownFactValue(0))==0);
    printf("drown rules ok\n");
    return 0;
}
