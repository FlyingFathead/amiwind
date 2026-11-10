/* SPDX-License-Identifier: GPL-2.0-or-later
 * The expansions' room save IDs (aw_maps.h, aw_layer_table.h): each expansion has its own base of 4096 IDs after
 * the base batch rooms, the shipped (empty) lists and a two-room Tribunal list (AW_LAYER_TEST_TWO, the table given
 * here in place of the generated one) both resolve, and an ID in an expansion's range that the table does not name
 * is titled "needs <expansion>". */
#ifdef AW_LAYER_TEST_TWO
#define AW_LAYER_TABLE_H
#define AW_TRIBUNAL_ROOM_COUNT 2
#define AW_TRIBUNAL_ROOM_NAMES {"ri0123456789","ri89abcdef01"}
#define AW_TRIBUNAL_ROOM_TITLES {"Mournhold, Royal Palace","Mournhold, Temple"}
#define AW_BLOODMOON_ROOM_COUNT 0
#define AW_BLOODMOON_ROOM_NAMES {""}
#define AW_BLOODMOON_ROOM_TITLES {""}
#endif
#include "aw_maps.h"
#include <assert.h>

int main(void)
{
    /* The ranges: base batch rooms, then Tribunal, then Bloodmoon, 4096 each, clear of every base ID. */
    assert(AW_TRIBUNAL_ROOM_BASE==AW_ROOM_BATCH_BASE+4096 && AW_BLOODMOON_ROOM_BASE==AW_TRIBUNAL_ROOM_BASE+4096);
    assert(AW_LAYER_ROOM_END==AW_BLOODMOON_ROOM_BASE+4096 && AW_SCENE_COUNT<=AW_TRIBUNAL_ROOM_BASE);
    assert(!AW_MapLayer(AW_SCENE_COUNT-1) && !AW_MapLayer(AW_TRIBUNAL_ROOM_BASE-1) && !AW_MapLayer(AW_LAYER_ROOM_END));
    assert(!strcmp(AW_MapLayer(AW_TRIBUNAL_ROOM_BASE),"Tribunal") && !strcmp(AW_MapLayer(AW_BLOODMOON_ROOM_BASE-1),"Tribunal"));
    assert(!strcmp(AW_MapLayer(AW_BLOODMOON_ROOM_BASE),"Bloodmoon") && !strcmp(AW_MapLayer(AW_LAYER_ROOM_END-1),"Bloodmoon"));
    /* An ID the table does not name: no map name (a save naming it is refused), titled with the expansion it needs. */
    assert(!AW_MapName(AW_TRIBUNAL_ROOM_BASE+AW_TRIBUNAL_ROOM_COUNT)[0]);
    assert(!strcmp(AW_MapTitle(AW_TRIBUNAL_ROOM_BASE+AW_TRIBUNAL_ROOM_COUNT),"needs Tribunal"));
    assert(!AW_MapName(AW_BLOODMOON_ROOM_BASE)[0] && !strcmp(AW_MapTitle(AW_BLOODMOON_ROOM_BASE),"needs Bloodmoon"));
    assert(!strcmp(AW_MapTitle(AW_LAYER_ROOM_END-1),"needs Bloodmoon") && !strcmp(AW_MapTitle(AW_LAYER_ROOM_END),"Cancel"));
    assert(AW_MapId("ri0000000000")<0);
    {
        int k;
        for(k=0;k<AW_TRIBUNAL_ROOM_COUNT;k++){
            const char *room=AW_TribunalRoomName(k);
            assert(AW_MapId(room)==AW_TRIBUNAL_ROOM_BASE+k && !strcmp(AW_MapName(AW_TRIBUNAL_ROOM_BASE+k),room));
            assert(!strcmp(AW_MapTitle(AW_TRIBUNAL_ROOM_BASE+k),AW_TribunalRoomTitle(k)));
        }
    }
#ifdef AW_LAYER_TEST_TWO
    assert(AW_MapId("ri89abcdef01")==AW_TRIBUNAL_ROOM_BASE+1 && !strcmp(AW_MapTitle(AW_TRIBUNAL_ROOM_BASE+1),"Mournhold, Temple"));
    assert(!strcmp(AW_MapTitle(AW_TRIBUNAL_ROOM_BASE+2),"needs Tribunal"));
#else
    assert(AW_TRIBUNAL_ROOM_COUNT==0 && AW_BLOODMOON_ROOM_COUNT==0);   /* the shipped lists are empty */
#endif
    return 0;
}
