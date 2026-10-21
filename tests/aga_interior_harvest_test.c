/* SPDX-License-Identifier: GPL-2.0-or-later
 * HARVEST-INTERIOR-PICK-47: an interior room's catalogue and the world's catalogues are bound to the one global
 * placement index (same digest, same slot count), so their picks are facts of the same saved table: picking in a
 * room never disturbs an outdoor fact, leaving and re-entering keeps both, a save keeps both, the order does not
 * matter, and a catalogue bound to another index fails closed without touching the state. Real harvest and save
 * routines (aw_harvest.c, aw_state.c, aw_save_codec.c). */
#define main legacy_harvest_main
#include "aga_harvest_test.c"
#undef main
#define WORLD_SLOT 5
#define ROOM_SLOT 1500
/* One loaded catalogue at a time, as the runtime holds it: the world map's (an outdoor plant) or the room's. */
static void load(int room)
{
    static aw_state_t kept;kept=state; /* the fixture clears the state: the game's state is not the catalogue's */
    fixture();state=kept;h.slots=2083;memset(h.catalogue,0x47,32);
    h.plant[0].slot=room?ROOM_SLOT:WORLD_SLOT;h.plant[0].reference=room?365588:266995;
    strcpy(HSTR(h.plant[0].key),room?"aw:h:roomroomroomroomroomroomroomroomroomroomroomroomroom":
                                     "aw:h:" "worldworldworldworldworldworldworldworldworldworldwo");
    assert(AW_HarvestValidate(&h));
}
static int picked(int room){load(room);return AW_HarvestHidden(&h,0,&state);}
int main(void)
{
    uint32_t world_fact,room_fact;
    /* Outdoors first: pick the world plant. */
    memset(&state,0,sizeof(state));
    load(0);assert(AW_HarvestPrepare(&h,0,&state,1,11)==1);assert(AW_HarvestTake(&h,0,&state,1,11)==1);
    assert(picked(0) && !picked(1));world_fact=state.harvest.facts[WORLD_SLOT-1];
    /* Into the room: its plant is available and picked into the same table. */
    load(1);assert(AW_HarvestPrepare(&h,0,&state,1,22)==1);assert(AW_HarvestTake(&h,0,&state,1,22)==1);
    room_fact=state.harvest.facts[ROOM_SLOT-1];
    assert(state.harvest.facts[WORLD_SLOT-1]==world_fact && room_fact);
    /* Leave and come back: both stay picked; prepare on a picked plant changes nothing. */
    before=state;assert(picked(0));assert(AW_HarvestPrepare(&h,0,&state,1,33)==0);
    assert(picked(1));assert(AW_HarvestPrepare(&h,0,&state,1,44)==0);assert(!memcmp(&state,&before,sizeof(state)));
    assert(AW_HarvestPickedCount(&state)==2);
    /* Save and load: both facts survive. */
    save_roundtrip();assert(picked(0) && picked(1));
    assert(state.harvest.facts[WORLD_SLOT-1]==world_fact && state.harvest.facts[ROOM_SLOT-1]==room_fact);
    /* Room first, then outdoors: the order does not matter. */
    memset(&state,0,sizeof(state));
    load(1);assert(AW_HarvestTake(&h,0,&state,1,5)==1);
    load(0);assert(AW_HarvestPrepare(&h,0,&state,1,6)==1);assert(AW_HarvestTake(&h,0,&state,1,6)==1);
    assert(picked(0) && picked(1) && AW_HarvestPickedCount(&state)==2);
    /* A room catalogue bound to another index (another digest) fails closed: no pick, no state change. */
    before=state;load(1);h.catalogue[0]^=1;
    assert(AW_HarvestPrepare(&h,0,&state,1,7)==-1 && AW_HarvestTake(&h,0,&state,1,7)==-1);
    assert(!memcmp(&state,&before,sizeof(state)));
    puts("interior and world catalogues share one pick state: pick, leave, return, save, order, foreign index passed");
    return 0;
}
