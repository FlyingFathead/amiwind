/* SPDX-License-Identifier: GPL-2.0-or-later
 * MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66: the death rule of every path (OpenMW 0.51 creaturestats.cpp setDynamic: a
 * current health under 1 is death, whatever the base), through the real actor record (aw_actorstate.c, on an actor
 * table the builder's own writer made: tests/test_actor_death_native.py) and the real blow rule (aw_combat_rules.c).
 * A script's health call runs as aw_mwhost.c host_actor runs it: the record before the call, the call, then
 * AW_ActorHealthDeath. Covered: SetHealth 0 on a living actor kills it once (OnDeath once, the dead count, the death
 * report once); an actor taken to 0.5 by SetHealth, ModHealth or ModCurrentHealth dies; one left at exactly 1 lives;
 * a dead actor's SetHealth 0 is no second death; a body the data places with no health dies no second time; a blow
 * that leaves 0.5 kills, one that leaves 1 does not. Every result printed; the Python side checks them.
 *
 * Usage: aga_actor_death_test FILE.awm */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_actorstate.h"
#include "aw_combat.h"

static unsigned char *file;
static long size;
static int rd(void *c, uint32_t off, void *out, uint32_t n) {
    (void)c;
    if (off + n > (uint32_t)size) return 1;
    memcpy(out, file + off, n);return 0;
}
static int reports;     /* the death report (aw_actor_killed: the essential box in the engine), once per death */
static void killed(const aw_actor_t *a) { (void)a;reports++; }

/* a script's health call on A as host_actor makes it: VERB 1 SetHealth, 2 ModHealth, 3 ModCurrentHealth */
static int script_health(aw_actor_t *a, int verb, float value) {
    int was_dead = (a->flags & AWL_DEAD) != 0;float before = a->dyn_cur[0];
    if (verb == 1) AW_ActorSetStat(a, AWA_HEALTH, value);
    else if (verb == 2) AW_ActorModStat(a, AWA_HEALTH, value);
    else AW_ActorModCurrent(a, AWA_HEALTH, value);
    return AW_ActorHealthDeath(a, was_dead, before);
}
static void show(const char *what, aw_actor_t *a, int killed_now) {
    int first = AW_ActorOnDeath(a), second = AW_ActorOnDeath(a);
    printf("%s killed %d dead %.0f health %.2f base %.2f ondeath %d %d reports %d\n", what, killed_now,
           AW_ActorStat(a, AWA_DEAD), a->dyn_cur[0], a->dyn_base[0], first, second, reports);
}
int main(int argc, char **argv) {
    FILE *f;aw_actorstate_io_t io = {rd, NULL};aw_actor_t *a;int npc, rat, k;
    if (argc < 2 || !(f = fopen(argv[1], "rb"))) {printf("no file\n");return 2;}
    fseek(f, 0, SEEK_END);size = ftell(f);fseek(f, 0, SEEK_SET);
    file = malloc((size_t)size);
    if (!file || fread(file, 1, (size_t)size, f) != (size_t)size) return 2;
    fclose(f);
    if (!AW_ActorStateOpen(file, (uint32_t)size, &io)) {printf("open failed\n");return 1;}
    aw_actor_killed = killed;
    npc = AW_ActorFind("fixed_npc");rat = AW_ActorFind("test_rat");

    /* the rule itself: under 1 is death, 1 is not; a fall from 1 or more to under 1 */
    printf("rule %d %d %d %d fell %d %d %d\n", AW_ACTOR_HEALTH_DEAD(0.0f), AW_ACTOR_HEALTH_DEAD(0.5f),
           AW_ACTOR_HEALTH_DEAD(1.0f), AW_ACTOR_HEALTH_DEAD(-3.0f), AW_ACTOR_HEALTH_FELL(1.0f, 0.99f),
           AW_ACTOR_HEALTH_FELL(0.5f, 0.0f), AW_ACTOR_HEALTH_FELL(30.0f, 1.0f));

    /* SetHealth 0 on a living actor (the base goes to 0 as well, OpenMW OpSetDynamic): dead, once */
    a = AW_ActorGet(77, rat, 1);
    printf("rat health %.2f base %.2f\n", a->dyn_cur[0], a->dyn_base[0]);
    k = script_health(a, 1, 0);show("sethealth0", a, k);
    /* again on the dead actor: no second death (the count, OnDeath and the report as they were) */
    k = script_health(a, 1, 0);show("again", a, k);
    printf("rat count %d\n", AW_ActorDeadCount(rat));

    /* taken to 0.5: ModCurrentHealth (the record's own death inside the call: still this change's), SetHealth, ModHealth */
    a = AW_ActorGet(1234, npc, 1);k = script_health(a, 3, -(a->dyn_cur[0] - 0.5f));show("modcurrent-half", a, k);
    a = AW_ActorGet(1235, npc, 1);k = script_health(a, 1, 0.5f);show("sethealth-half", a, k);
    a = AW_ActorGet(1236, npc, 1);k = script_health(a, 2, -(a->dyn_cur[0] - 0.5f));show("modhealth-half", a, k);
    /* left at exactly 1: alive */
    a = AW_ActorGet(1237, npc, 1);k = script_health(a, 1, 1);show("sethealth-one", a, k);
    a = AW_ActorGet(1238, npc, 1);k = script_health(a, 3, -(a->dyn_cur[0] - 1));show("modcurrent-one", a, k);
    /* a body the data places with no health (health and base 0, not marked dead): SetHealth 0 is no new death */
    a = AW_ActorGet(1239, npc, 1);a->dyn_cur[0] = a->dyn_base[0] = 0;
    k = script_health(a, 1, 0);show("body", a, k);
    printf("npc count %d reports %d\n", AW_ActorDeadCount(npc), reports);

    /* the blow rule (aw_combat_rules.c AW_CombatSwing), no dice: a creature's 1-point attack on an unarmoured victim */
    {
        aw_combat_settings_t s;aw_fighter_t at, v;aw_swing_t out;aw_combat_rng_t r;
        memset(&s, 0, sizeof(s));
        AW_CombatSettingSet(&s, "fCombatArmorMinMult", .25f);AW_CombatSettingSet(&s, "fKnockDownMult", .5f);
        aw_combat_dice = 0;AW_CombatSeed(&r, 1);
        memset(&at, 0, sizeof(at));at.creature = 1;at.damage[0][0] = at.damage[0][1] = 1;
        at.health = at.health_max = 50;at.fatigue = at.fatigue_max = 100;
        memset(&v, 0, sizeof(v));v.aware = 1;v.armor = 0;v.attributes[AW_AGI] = 100;
        v.fatigue = v.fatigue_max = 100;v.health_max = 50;
        v.health = 1.5f;AW_CombatSwing(&s, &at, &v, AW_ATTACK_CHOP, 1, 0, 1, &r, &out);
        printf("blow-half damage %.2f dead %d health %.2f\n", out.damage, v.dead, v.health);
        v.dead = 0;v.health = 2;AW_CombatSwing(&s, &at, &v, AW_ATTACK_CHOP, 1, 0, 1, &r, &out);
        printf("blow-one damage %.2f dead %d health %.2f\n", out.damage, v.dead, v.health);
    }
    return 0;
}
