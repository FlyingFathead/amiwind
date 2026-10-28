/* SPDX-License-Identifier: GPL-2.0-or-later
 * Every group of the base game's humanoid animation files (the tables tools/skeletal_actor.py writes), and what in the
 * game reaches it (ANIM-GROUPS-NOT-HOOKED-54, aw_animpick.h). Source data only: tools/anim_coverage.py reads it from
 * this file and the gate's test includes it (tests/aga_animpick_test.c proves every "pick:" row reachable by
 * AW_AnimPick); the engine never compiles it (no 1 KiB name table resident: tests/test_resident_registry.py). */
#define PICK(g,why) {g,"pick: " why}
#define MOVE(g) PICK(g,"moving (refreshMovementAnims)")
#define TURN(g) PICK(g,"turning on the spot (refreshMovementAnims)")
const aw_pick_catalogue_t aw_pick_catalogue[]={
    PICK("idle","standing"),PICK("idle2","wander idle 2"),PICK("idle3","wander idle 3"),PICK("idle4","wander idle 4"),
    PICK("idle5","wander idle 5"),PICK("idle6","wander idle 6"),PICK("idle7","wander idle 7"),PICK("idle8","wander idle 8"),
    PICK("idle9","wander idle 9"),PICK("idlehh","standing, hand-to-hand drawn"),PICK("idle1h","standing, one-handed drawn"),
    PICK("idle2c","standing, two-handed drawn"),PICK("idle2w","standing, two-wide drawn"),PICK("idleswim","standing in water"),
    PICK("idlespell","standing, spell readied"),PICK("idlecrossbow","standing, crossbow drawn"),
    PICK("idlesneak","standing, sneaking"),
    {"idlestorm","layer: the arm facing an ash or blight storm (aw_items.c, character.cpp updateIdleStormState)"},
    {"torch","layer: the left arm while carrying a light (aw_items.c, character.cpp updateWeaponState)"},
    PICK("hit1","hit recovery"),PICK("hit2","hit recovery"),PICK("hit3","hit recovery"),PICK("hit4","hit recovery"),
    PICK("hit5","hit recovery"),PICK("death1","death"),PICK("death2","death"),PICK("death3","death"),PICK("death4","death"),
    PICK("death5","death"),PICK("deathknockdown","death after a knockdown"),PICK("deathknockout","death after a knockout"),
    PICK("knockdown","knocked down"),PICK("knockout","knocked out"),PICK("swimdeath","death in water"),
    PICK("swimknockdown","knocked down in water"),PICK("swimknockout","knocked out in water"),
    PICK("swimdeathknockdown","death in water after a knockdown"),PICK("swimdeathknockout","death in water after a knockout"),
    MOVE("swimwalkforward"),MOVE("swimwalkback"),MOVE("swimwalkleft"),MOVE("swimwalkright"),
    MOVE("swimrunforward"),MOVE("swimrunback"),MOVE("swimrunleft"),MOVE("swimrunright"),TURN("swimturnleft"),TURN("swimturnright"),
    MOVE("walkforward"),MOVE("walkback"),MOVE("walkleft"),MOVE("walkright"),TURN("turnleft"),TURN("turnright"),
    MOVE("runforward"),MOVE("runback"),MOVE("runleft"),MOVE("runright"),
    MOVE("sneakforward"),MOVE("sneakback"),MOVE("sneakleft"),MOVE("sneakright"),PICK("jump","jump"),
    MOVE("walkforwardhh"),MOVE("walkbackhh"),MOVE("walklefthh"),MOVE("walkrighthh"),TURN("turnlefthh"),TURN("turnrighthh"),
    MOVE("runforwardhh"),MOVE("runbackhh"),MOVE("runlefthh"),MOVE("runrighthh"),
    MOVE("sneakforwardhh"),MOVE("sneakbackhh"),MOVE("sneaklefthh"),MOVE("sneakrighthh"),PICK("jumphh","jump, hand-to-hand"),
    MOVE("walkforward1h"),MOVE("walkback1h"),MOVE("walkleft1h"),MOVE("walkright1h"),TURN("turnleft1h"),TURN("turnright1h"),
    MOVE("runforward1h"),MOVE("runback1h"),MOVE("runleft1h"),MOVE("runright1h"),
    MOVE("sneakforward1h"),MOVE("sneakback1h"),MOVE("sneakleft1h"),MOVE("sneakright1h"),PICK("jump1h","jump, one-handed"),
    MOVE("walkforward2c"),MOVE("walkback2c"),MOVE("walkleft2c"),MOVE("walkright2c"),
    MOVE("runforward2c"),MOVE("runback2c"),MOVE("runleft2c"),MOVE("runright2c"),TURN("turnleft2c"),TURN("turnright2c"),
    MOVE("sneakforward2c"),MOVE("sneakback2c"),MOVE("sneakleft2c"),MOVE("sneakright2c"),PICK("jump2c","jump, two-handed"),
    MOVE("walkforward2w"),MOVE("walkback2w"),MOVE("walkleft2w"),MOVE("walkright2w"),TURN("turnleft2w"),TURN("turnright2w"),
    MOVE("runforward2w"),MOVE("runback2w"),MOVE("runleft2w"),MOVE("runright2w"),
    MOVE("sneakforward2w"),MOVE("sneakback2w"),MOVE("sneakleft2w"),MOVE("sneakright2w"),PICK("jump2w","jump, two-wide"),
    PICK("spellcast","casting (self, touch, target); readying and lowering the spell"),
    {"spellcast_2","keys: the beast file's second spellcast place holds its self/touch/target keys (aw_animkit.c key_frame)"},
    TURN("spellturnleft"),TURN("spellturnright"),
    PICK("handtohand","attack and drawing, hand-to-hand"),PICK("crossbow","attack and drawing, crossbow"),
    PICK("bowandarrow","attack and drawing, bow"),PICK("throwweapon","attack and drawing, thrown"),
    PICK("weapononehand","attack and drawing, one-handed"),PICK("weapontwohand","attack and drawing, two-handed"),
    PICK("weapontwowide","attack and drawing, two-wide"),PICK("shield","block"),
    PICK("pickprobe","a lockpick or probe used"),
    PICK("inventoryhandtohand","the inventory picture"),PICK("inventoryweapononehand","the inventory picture"),
    PICK("inventoryweapontwohand","the inventory picture"),PICK("inventoryweapontwowide","the inventory picture"),
    {"f:idle4","view: a woman's own idle4 (base_anim_female) wherever idle4 is picked"},
    {"f:idle5","view: a woman's own idle5 (base_anim_female) wherever idle5 is picked"},
    {"f:walkforward","view: a woman's own walkforward (base_anim_female) wherever walkforward is picked"},
    {"d:idle9","view: an NPC's own file (anim_dancinggirl) wherever idle9 is picked; world.qc aw_idle_base loops it"},
    {"dodgel","combat: the dodge to the left (AmiWind extension, aw_combat.c)"},
    {"dodger","combat: the dodge to the right (AmiWind extension, aw_combat.c)"},
};
const int aw_pick_catalogue_count=(int)(sizeof(aw_pick_catalogue)/sizeof(aw_pick_catalogue[0]));
