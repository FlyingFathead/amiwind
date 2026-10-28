/* SPDX-License-Identifier: GPL-2.0-or-later
 * Every group of the humanoid animation tables a default build writes (progs/humanoid.awsk and
 * progs/humanoid_kna.awsk, tools/skeletal_actor.py), in table order: the names only, listed from the v0.0.53 final
 * image. The coverage gate (tests/aga_animpick_test.c, tests/test_anim_coverage.py) checks that each one is in the
 * engine catalogue (aw_animpick_rules.inc) and hooked. */
static const char *const table_groups[]={
    "idle","idle2","idle3","idle4","idle5","idle6","idle7","idle8","idle9","idlehh","idle1h","idle2c","idle2w",
    "idleswim","torch","hit1","hit2","hit3","hit4","hit5","death1","death2","death3","death4","death5","knockdown",
    "knockout","swimdeath","swimknockout","swimdeathknockout","swimwalkforward","swimwalkback","swimwalkleft",
    "swimwalkright","swimrunforward","swimrunback","swimrunleft","swimrunright","swimturnleft","swimturnright",
    "walkforward","walkback","walkleft","walkright","turnleft","turnright","runforward","runback","runleft","runright",
    "sneakforward","sneakback","sneakleft","sneakright","jump","walkforwardhh","walkbackhh","walklefthh","walkrighthh",
    "turnlefthh","turnrighthh","runforwardhh","runbackhh","runlefthh","runrighthh","sneakforwardhh","sneakbackhh",
    "sneaklefthh","sneakrighthh","jumphh","walkforward1h","walkback1h","walkleft1h","walkright1h","turnleft1h",
    "turnright1h","runforward1h","runback1h","runleft1h","runright1h","sneakforward1h","sneakback1h","sneakleft1h",
    "sneakright1h","jump1h","walkforward2c","walkback2c","walkleft2c","walkright2c","runforward2c","runback2c",
    "runleft2c","runright2c","turnleft2c","turnright2c","sneakforward2c","sneakback2c","sneakleft2c","sneakright2c",
    "jump2c","walkforward2w","walkback2w","walkleft2w","walkright2w","turnleft2w","turnright2w","runforward2w",
    "runback2w","runleft2w","runright2w","sneakforward2w","sneakback2w","sneakleft2w","sneakright2w","jump2w",
    "spellcast","idlespell","spellturnleft","spellturnright","handtohand","crossbow","bowandarrow","throwweapon",
    "weapononehand","weapontwohand","weapontwowide","shield","pickprobe","deathknockdown","deathknockout",
    "swimknockdown","swimdeathknockdown","idlecrossbow","idlesneak","idlestorm","inventoryhandtohand",
    "inventoryweapononehand","inventoryweapontwohand","inventoryweapontwowide","f:idle4","f:idle5","f:walkforward",
    "d:idle9","dodgel","dodger","spellcast_2",
};
