/* SPDX-License-Identifier: GPL-2.0-or-later
 * The player's change of form into the werewolf and back (WEREWOLF-BODY-63, WEREWOLF-TRANSFORM-RULES-PARTIAL-68,
 * v0.0.68), on the game state alone. The one rule the script's BecomeWerewolf and UndoWerewolf, the console's typed lines
 * and dbg werewolf on|off all run (aw_mwhost.c were_player_change). Rules from OpenMW 0.51 (read, not copied):
 * apps/openmw/mwmechanics/mechanicsmanagerimp.cpp setWerewolf 1880-1937, apps/openmw/mwworld/inventorystore.cpp
 * unequipAll 197-206, apps/openmw/mwworld/player.cpp setWerewolfStats / restoreStats, apps/openmw/mwworld/class.cpp
 * showsInInventory 289-295.
 *
 * The change, in the original's order:
 *   no change when the form is already so (1884-1886);
 *   the form set (1894);
 *   into the form: every slot taken off (1900; a worn item's constant effects end with it), the werewolf robe added
 *   and worn in the robe slot (1901-1902); back: the robe slot emptied and one werewolf robe taken away (1906-1907).
 *   The original does not put the earlier items back on: they stay in the inventory, taken off;
 *   the temporary effects end, both ways (1917-1919);
 *   into the form: the player's own attributes and skills kept, the werewolf's set from the game settings; back: his
 *   own given back (1922-1931). Acrobatics stays (SetWerewolfAcrobatics sets it).
 * What the engine adds around it (aw_mwhost.c): the readied spell put away (1890-1892), the inventory and magic windows
 * refused while the form holds (1926-1927, 1932-1933: aw_worldui.c), the body drawn as the werewolf while the robe is
 * worn (aw_view.c, aw_player_parts.h AW_PARTS_WEREWOLF_RACE). Pure C (native tests: tests/test_werewolf_change.py). */
#ifndef AW_WERE_RULES_H
#define AW_WERE_RULES_H
#include <stdint.h>
#include "aw_forced_rules.h"
#include "aw_inventory.h"
#include "aw_actorstate.h"
#include "aw_player_parts.h"

#define AW_WERE_ROBE AW_PARTS_WEREWOLF_ROBE

/* What one change did, for the console and the tests. */
typedef struct {
    int changed;          /* 0: the form was already so */
    int taken_off;        /* slots emptied by the change into the form */
    int robe_added, robe_worn, robe_removed;
    int purged;           /* temporary effects ended */
    int stats;            /* 1 kept and set (into the form), 2 given back (out of it), 0 none (no player record) */
} aw_were_report_t;

/* The change of W (the werewolf state of aw_forced_rules.h) to SET (1 the werewolf, 0 back) on the inventory S, with
 * ROBE the werewolf robe's catalogue row (NULL: not in this game's data: no robe is added) and PLAYER the player's
 * record (NULL: no stats and no effects). NUMBERS (COUNT of them, the compiler's packing, tools/mwscript/codegen.py
 * werewolf_settings): the werewolf's 8 attributes and 27 skills, a byte each, high byte first, 255 where the game data
 * has none (that stat stays). OUT may be NULL. Returns OUT's changed. */
int AW_WereChange(aw_were_t *w,int set,aw_state_t *s,const aw_inventory_item_t *robe,aw_actor_t *player,
                  const int32_t *numbers,int count,aw_were_report_t *out);

/* A list's row for item ID (class.cpp showsInInventory: the original never shows the werewolf robe in a list, nor lets
 * it be taken: the inventory, a container's or a corpse's contents, a trade list). OWN 1: the player's own inventory
 * window. FORM: the player is a werewolf now. 1 = shown. AmiWind's one difference, kept for testing (dbg give
 * werewolfrobe, decided for the project on 22 November 2026): the player's own inventory lists the robe while he is not
 * a werewolf, so a given robe can be worn and taken off there; while the form holds that window does not open at all,
 * as in the original. */
int AW_WereItemShown(const char *id,int own,int form);
/* The same rule for the lists of a container, a corpse and a trade (never shown there) by the id as those lists hold
 * it (the state's and the catalogue's lower-case id), without a call: their native fixtures link no rules file. */
#define AW_WERE_ROBE_ID(id) (!strcmp((const char *)(id),AW_WERE_ROBE))

#endif
