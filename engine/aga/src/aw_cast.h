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

/* ---- engine glue (aw_cast.c; the landing in aw_mwhost.c) ---- */
struct edict_s;
/* The effects of RANGE among N (E, records M) land on TARGET (NULL: the player); how many, -1 no actor record. */
int AW_MwscriptLand(struct edict_s *target,const aw_spell_effect_t *e,const aw_mgef_t *m,int n,int range,int source);
/* The player's record (its stats from the character sheet when there is one) and its changes stored back. */
aw_actor_t *AW_MwscriptPlayerRecord(void);
void AW_MwscriptPlayerStore(aw_actor_t *a);
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
int AW_CastCommand(void);      /* aw_magicfx's casting words (ready, spell, now, casting); 1 when handled */
void AW_CastFrame(void);       /* the server frame: the ready state, the cast key, the release */
int AW_CastReady(void);        /* 1 while the player's magic is readied */
float AW_CastChanceNow(void);  /* the selected spell's chance now, 0..100 */
/* The selected spell: an ASPT row (KIND 0) or a made spell (KIND 1), INDEX; -1 none. */
int AW_CastSelected(int *kind);
void AW_CastSelect(int kind,int index);
#endif
