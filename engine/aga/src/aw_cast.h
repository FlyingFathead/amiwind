/* SPDX-License-Identifier: GPL-2.0-or-later
 * Player casting (PLAYER-CASTING-59; docs/MAGIC_EFFECTS.md "Casting"): the rules, pure (aw_cast_rules.c,
 * native tests tests/test_mwscript.py CastRuleTests), and the engine glue (aw_cast.c): ready a spell, pay its
 * magicka, roll for success and deliver its effects on Self, Touch or Target through the active effects
 * (aw_effects.h).
 *
 * Rules from OpenMW 0.51, written independently: apps/openmw/mwmechanics/spellutil.cpp (calcSpellBaseSuccessChance,
 * getSpellSuccessChance), mwworld/worldimp.cpp (startSpellCast: the magicka is paid when the cast starts, "not enough
 * magicka" refuses it; castSpell: the touch target by melee hit contact within fCombatDistance),
 * mwmechanics/spellcasting.cpp (CastSpell::cast: the roll 0..99 below the chance succeeds, a failure plays the school's
 * failure sound; inflict: each effect lands with its range; the bolt carries the target effects). */
#ifndef AW_CAST_H
#define AW_CAST_H
#include "aw_actorstate.h"

#define AW_CAST_SCHOOLS 6
enum {AW_RANGE_SELF=0,AW_RANGE_TOUCH=1,AW_RANGE_TARGET=2};
#define AW_MGEF_NO_DURATION 0x4
#define AW_MGEF_NO_MAGNITUDE 0x8
#define AW_MGEF_HARMFUL 0x10
#define AW_SPELL_TYPE_SPELL 0
#define AW_SPELL_TYPE_POWER 5

/* The skill (0..26) of a magic school (the MGEF record's school: 0 Alteration .. 5 Restoration). */
int AW_CastSchoolSkill(int school);
/* The base chance (OpenMW calcSpellBaseSuccessChance): over the spell's N effects (E, and each effect's record M),
 * the effect whose 2 x school skill (SKILL by skill index) minus its cost term is lowest gives the skill; then
 * skill - COST + 0.2 Willpower + 0.1 Luck. *SCHOOL: that effect's school (0 when N is 0). */
float AW_CastBaseChance(const aw_spell_effect_t *e,const aw_mgef_t *m,int n,const float skills[27],float willpower,
                        float luck,int cost,float effect_cost_mult,int *school);
/* The chance (OpenMW getSpellSuccessChance, capped 0..100): a power 100 when READY else 0; silenced 0; any other type
 * but a spell 100; not enough MAGICKA for COST 0 (CHECK_MAGICKA); ALWAYS (the spell's always-succeeds flag) 100; else
 * (BASE - SOUND magnitude) x FATIGUE_TERM. */
float AW_CastChance(float base,int type,int power_ready,int always,float silence,float sound,float fatigue_term,
                    float magicka,int cost,int check_magicka);
/* The fatigue term (OpenMW CreatureStats::getFatigueTerm): BASE - MULT x (1 - current / maximum), 1 at a 0 maximum. */
float AW_CastFatigueTerm(float base,float mult,float current,float maximum);
/* A rolled magnitude between LO and HI for a draw R in [0, 1): LO + floor(R x (HI - LO + 1)), at most HI. */
float AW_CastMagnitude(int lo,int hi,float r);
/* RACE-RESIST-NOT-ON-SPELL-DAMAGE-64: the effects that resist EFFECT (aw_cast_rules.c) and the resistance in percent */
int AW_CastResistEffects(int effect,int *resist,int *weakness,int *shield);
float AW_CastResistance(float attr,float willpower,float luck,float fatigue_term,float cast_chance,float roll,int no_magnitude);
void AW_MwscriptResistReport(void);   /* aw_mwhost.c: the landings' resistance counts (dbg cast spell prints them) */
/* The seconds an effect lasts once landed: its duration, 1 for an effect without one (OpenMW inflict). */
float AW_CastDuration(const aw_spell_effect_t *e,const aw_mgef_t *m);
/* The ranges among the N effects, a bit per AW_RANGE_*. */
int AW_CastRanges(const aw_spell_effect_t *e,int n);
/* Magic items (v0.0.61; OpenMW spellutil.cpp getEffectiveEnchantmentCastCost, spellcasting.cpp CastSpell::cast): the
 * charge one use of a Cast When Used or Cast When Strikes item takes, by the caster's Enchant skill (COST - COST / 100
 * x (skill - 10), at least 1); the charge left after it, -1 when CHARGE is too little (the use is refused). An item's
 * use never rolls for success. */
int AW_CastItemCost(float cast_cost,float enchant_skill);
float AW_CastItemCharge(float charge,int cost);
/* The starting spells of a new character (OpenMW 0.51 autocalcspell.cpp autoCalcPlayerSpells): over the spells
 * flagged as starting spells, in the masters' order (S, COUNT: each one's ASPT ROW, price COST, SPDT FLAGS and
 * effects), with the character's base SKILLS and ATTRIBUTES: not one of the RACE's spells, the magicka (fPCbaseMagicka
 * Mult x Intelligence) at least the cost, the chance (AW_CastStartChance) at least fAutoPCSpellChance, every skill or
 * attribute an effect names at least iAutoSpellAttSkillMin; at most iAutoPCSpellMax, past it the cheapest gives way.
 * The chosen ASPT rows into OUT; how many. */
typedef struct {int row,cost,flags,n;aw_spell_effect_t e[AW_MADE_EFFECTS];aw_mgef_t m[AW_MADE_EFFECTS];} aw_start_spell_t;
float AW_CastStartChance(const aw_start_spell_t *s,const float skills[27],const float attributes[8],float cost_mult);
int AW_CastStartSpells(const aw_start_spell_t *s,int count,const aw_start_settings_t *set,const float skills[27],
                       const float attributes[8],const int *race,int nrace,int *out,int max);

/* NPC-NO-SPELLCASTING-65: a fighter's choice between its weapon and its spells, rules from OpenMW 0.51
 * mwmechanics/aicombataction.cpp prepareNextAction, spellpriority.cpp rateSpell / rateEffect / rateEffects,
 * weaponpriority.cpp rateWeapon, spellutil.cpp calcEffectCost (written independently). The caster's and its enemy's
 * state the rating reads; HAS: the summed magnitude of an effect now active on the caster (WHO 0) or the enemy (1);
 * RESIST: the enemy's resistance in percent to an effect; ACTIVE: 1 when a spell (ASPT row) is still active on WHO.
 * The game settings: fAIMagicSpellMult, fAIRangeMagicSpellMult (3 and 5 in the masters), fEffectCostMult (0.5),
 * fCombatInvisoMult (0.2). */
typedef struct {
    int npc,beast;                       /* the caster: an NPC (else a creature), of a beast race */
    float health,health_max,fatigue,fatigue_max;
    float skills[27];
    int underwater;
    int enemy;                           /* 1: there is an enemy (else every Touch or Target effect rates 0) */
    int enemy_npc,enemy_ready,enemy_down,enemy_underwater;   /* ready: 0 nothing, 1 a weapon, 2 magic */
    int enemy_armor,enemy_weapon;        /* the enemy wears armour / holds a weapon */
    float enemy_attributes[8],enemy_skills[27],enemy_magicka;
    float (*has)(void *ctx,int who,int effect);
    float (*resist)(void *ctx,int effect);
    int (*active)(void *ctx,int who,int spell);
    void *ctx;
    float spell_mult,range_spell_mult,effect_cost_mult,inviso_mult;
    /* (v0.0.66) the inputs of the kinds rated since: MAGICKA_NEED getRestoreMagickaPriority (2 when a spell it knows
     * costs more than its magicka now but less than its full magicka, else 0) for Restore Magicka and Absorb Magicka;
     * MAGICKA and MAGICKA_MAX for Restore Magicka; the carried weight and capacity of the caster (Feather) and the
     * enemy (Burden), INVENTORY / ENEMY_INVENTORY 1 when it has one; AMMO 1 when the caster carries arrows (the bound
     * longbow); DISPEL: how many effects on WHO (0 caster, 1 enemy) a Dispel or a cure would remove, of EFFECT (-1: the
     * effects of spells), harmful ones (NEGATIVE 1) or helpful ones (0), lasting over 3 s more (numEffectsToDispel). */
    float magicka_need,magicka,magicka_max;
    float encumbrance,capacity,enemy_encumbrance,enemy_capacity;
    int inventory,enemy_inventory,ammo;
    int (*dispel)(void *ctx,int who,int effect,int negative);
} aw_spell_ai_t;
/* calcEffectCost (the game's spell method): the effect's cost from its magnitudes, duration, area and base cost */
float AW_SpellAiEffectCost(const aw_spell_effect_t *e,const aw_mgef_t *m,float cost_mult);
/* rateEffect: the use of one effect of a spell to the caster in this fight (> 0 worth casting; harmful effects on the
 * enemy and helpful ones on itself rate above 0). M's flags: the data's, with AW_MGEF_HARMFUL set from the game's
 * hardcoded list (AW_EffectHarmful). Effects whose rating needs state this table does not carry rate 0 (see
 * docs/MAGIC_EFFECTS.md "Characters cast too"). */
float AW_SpellAiRateEffect(const aw_spell_ai_t *c,const aw_spell_effect_t *e,const aw_mgef_t *m);
/* rateSpell: 0 for a chance of 0, a type other than a castable spell, or a spell still active on its target; else the
 * effects' ratings (each times fAIRangeMagicSpellMult on Target, fAIMagicSpellMult otherwise) summed, times the chance
 * (0..100) / 100. ROW the spell's ASPT row (the ACTIVE test). */
float AW_SpellAiRateSpell(const aw_spell_ai_t *c,int row,int type,const aw_spell_effect_t *e,const aw_mgef_t *m,int n,
                          float chance);
/* rateWeapon for a melee weapon: DAMAGE chop, slash, thrust (min, max) to (s^2 + t^2 + c^2) / (s + t + c) of their
 * means, times the strength factor (fDamageStrengthBase + fDamageStrengthMult x Strength / 10), the condition share
 * (CONDITION 0..1), the hit chance (percent, clamped to 0.01 .. 1), the weapon's SPEED and fAIMeleeWeaponMult; 0 at a
 * weapon SKILL of 0. Hand to hand rates 0 (OpenMW's default action). */
float AW_SpellAiRateWeapon(const unsigned char damage[3][2],float strength_factor,float condition,float hit_chance,
                           float speed,int skill,float melee_mult);
/* suggestCombatRange: the distance (game units) from which the caster casts a spell of RANGES (AW_CastRanges bits):
 * fCombatDistance for a Touch spell, else 4 x fCombatDistance x max(2, fHandToHandReach) */
float AW_SpellAiCombatRange(int ranges,float combat_distance,float h2h_reach);

/* ---- engine glue (aw_cast.c; the landing in aw_mwhost.c) ---- */
struct edict_s;
/* The effects of RANGE among N (E, records M) land on TARGET (NULL: the player); how many, -1 no actor record. */
int AW_MwscriptLand(struct edict_s *target,const aw_spell_effect_t *e,const aw_mgef_t *m,int n,int range,int source);
/* The player's record (its stats from the character sheet when there is one) and its changes stored back. */
aw_actor_t *AW_MwscriptPlayerRecord(void);
void AW_MwscriptPlayerStore(aw_actor_t *a);
/* GODMODE-LAVA-DEATH-62: how many script or spell losses of the player's health god mode kept back (aw_mwhost.c) */
unsigned long AW_MwscriptGodHealthHeld(void);
/* An actor edict's record (made from its base when it has none yet; NULL for objects without one) and its ACTB row. */
aw_actor_t *AW_MwscriptActorOf(struct edict_s *e,int *row);
/* dbg cast start: the starting spells the class and the skills gave the character made in this session */
void AW_MwscriptStartSpellsReport(void);
/* aw_dialwin.c: the game's fEffectCostMult (0 when the build has no dialogue table) and a made spell's magicka cost by
 * the Spellmaking rule (-1 without the table) */
float AW_DialwinEffectCostMult(void);
int AW_DialwinMadeSpellCost(const aw_spell_effect_t *e,int count);
float AW_DialwinMadeItemCost(const aw_spell_effect_t *e,int count,int constant);
/* aw_magic.c: the look and sounds of a cast of effect MGEF on RANGE (FAIL: the failure's sound only); 0 when the
 * look is off (aw_magic_fx 0) or the effect has none */
int AW_MagicCastLook(int mgef,int range,int fail,float area);
/* CAST-EGG-SYNC-62: the look of a cast that plays the cast animation: started on the animation's frame by CASTER (0 the
 * player, else an actor's edict casting at the player), the hand glow, the cast sound and the shell with it; it waits
 * for AW_MagicCastLookRelease on the frame the spell leaves (OK 1), fails (0, the failure sound) or is dropped (-1).
 * Handle 0: no look (off, or no effect). */
int AW_MagicCastLookStart(int caster,int mgef,int range,float area);
void AW_MagicCastLookRelease(int handle,int ok);
int AW_CastCommand(void);      /* aw_magicfx's casting words (ready, spell, now, casting); 1 when handled */
void AW_CastFrame(void);       /* the server frame: the ready state, the cast key, the release */
int AW_CastReady(void);        /* 1 while the player's magic is readied */
float AW_CastChanceNow(void);  /* the selected spell's chance now, 0..100 */
/* The selected spell: an ASPT row (KIND 0) or a made spell (KIND 1), INDEX; -1 none. */
int AW_CastSelected(int *kind);
void AW_CastSelect(int kind,int index);
/* ExplodeSpell (v0.0.63, MWSCRIPT-GAPS-63; OpenMW miscextensions.cpp OpExplodeSpell, spellcasting.cpp inflict,
 * worldimp.cpp explodeSpell): the object casts the ASPT spell SPELL on itself, always succeeding; an object is no
 * actor, so its Self and Touch effects land only through their area: on every actor within each effect's area (feet)
 * of AT (map units), the player included. How many actors it reached; -1 when the spell has no effects here. */
int AW_CastExplode(const float at[3],int spell);
/* Cast SPELL TARGET of a script whose caster is not the player (v0.0.64, MWSCRIPT-GAPS-63; OpenMW 0.53
 * miscextensions.cpp OpCast, spellcasting.cpp CastSpell::cast, always succeeding): the ASPT spell's Self effects on
 * CASTER when it is an actor (the player's edict included), its Touch and Target effects on TARGET (NULL: the player),
 * at once. How many ranges landed; -1 when the spell has no effects here. */
int AW_CastOn(struct edict_s *caster,struct edict_s *target,int spell);
/* NPC-NO-SPELLCASTING-65: CASTER (an actor's edict) casts the ASPT spell ROW at TARGET (NULL: the player) as the
 * player's casts go: its Self effects on itself, its Touch effects on the target when it is within REACH (map units)
 * at the release, its Target effects as a bolt from its eye that lands on the target when it reaches it (the world
 * stops it first). Called on the spellcast group's release. How many ranges went out; -1 when the spell has no
 * effects here. */
int AW_CastActorRelease(struct edict_s *caster,struct edict_s *target,int row,float reach);
unsigned long AW_CastActorCasts(void);   /* how many actor casts went out this session (dbg combat) */
#endif
