/* SPDX-License-Identifier: GPL-2.0-or-later
 * Levelling as the original game does it (docs/CHARACTER_CREATION.md "Levelling", LEVEL-UP-58).
 * aw_levelup_rules.c holds the rules as pure functions (host tested); aw_levelup.c runs them on the
 * player: the skill uses the game reports, the messages and sounds, the level-up box, the dbg routes.
 *
 * The rules follow the original as OpenMW 0.51 implements them (reference, own code): skill progress
 * from use files/data-mw/scripts/omw/playerskillhandlers.lua (getSkillProgressRequirement,
 * skillUsedHandler, getSkillLevelUpOptions, skillLevelUpHandler); the level-up apps/openmw/mwgui/
 * levelupdialog.cpp (the coins, the multipliers, the class picture) and mwmechanics/npcstats.cpp
 * (levelUp: the health gain, getLevelupAttributeMultiplier). Every number comes from the game
 * settings and SKIL records of the player's own master file at build time (levelup/settings.txt,
 * tools/prepare_levelup.py).
 */
#ifndef AW_LEVELUP_H
#define AW_LEVELUP_H
#include "aw_character.h"

#define AW_LEVELUP_SKILLS 27
/* The skills the game reports today (SKIL INDX order, as aw_combat.h). */
enum {AW_LU_BLOCK=0,AW_LU_MEDIUM=2,AW_LU_HEAVY=3,AW_LU_ATHLETICS=8,AW_LU_UNARMORED=17,AW_LU_ACROBATICS=20,
      AW_LU_LIGHT=21,AW_LU_MERCANTILE=24,AW_LU_SPEECHCRAFT=25,AW_LU_H2H=26};
/* The use types (OpenMW SkillProgression.SKILL_USE_TYPES): an index into a skill's four use values. */
enum {AW_USE_HIT=0,AW_USE_BLOCK=0,AW_USE_ARMOR=0,AW_USE_JUMP=0,AW_USE_FALL=1,AW_USE_RUN=0,AW_USE_SWIM=1,
      AW_USE_MERCANTILE_SUCCESS=0};
/* Where a skill raise comes from (OpenMW SKILL_INCREASE_SOURCES; jail is not used yet). */
enum {AW_RAISE_USAGE,AW_RAISE_TRAINER,AW_RAISE_BOOK};

typedef struct {
    float major,minor,misc,special;          /* fMajorSkillBonus, fMinorSkillBonus, fMiscSkillBonus, fSpecialSkillBonus */
    float health_end;                        /* fLevelUpHealthEndMult */
    int total;                               /* iLevelupTotal */
    int major_mult,minor_mult;               /* iLevelupMajorMult, iLevelupMinorMult: level progress per raise */
    int major_attribute,minor_attribute,misc_attribute;  /* iLevelupMajorMultAttribute .. iLevelupMiscMultAttriubte */
    int specialization;                      /* iLevelupSpecialization */
    int mult[10];                            /* iLevelUp01Mult .. iLevelUp10Mult */
    unsigned char attribute[AW_LEVELUP_SKILLS],spec[AW_LEVELUP_SKILLS];     /* SKDT governing attribute, specialization */
    float use[AW_LEVELUP_SKILLS][4];         /* SKDT use values */
    unsigned long seen_settings,seen_skills; /* which settings and skill rows were read */
    int loaded;                              /* every setting and skill row was read (AW_LevelupRulesComplete) */
} aw_levelup_rules_t;
#define AW_LEVELUP_SETTING_COUNT 22

/* One "set NAME VALUE" line into the rules; 1 when NAME is a levelling setting. */
int AW_LevelupSettingSet(aw_levelup_rules_t *r,const char *name,float value);
const char *AW_LevelupSettingName(int index);
/* One "skill INDEX ATTRIBUTE SPECIALIZATION USE0 USE1 USE2 USE3" row; 1 when valid. */
int AW_LevelupSkillRow(aw_levelup_rules_t *r,int skill,int attribute,int special,const float *use);
/* 1 when every setting and all 27 skill rows are in. */
int AW_LevelupRulesComplete(const aw_levelup_rules_t *r);
/* 2 major, 1 minor, 0 misc: the skill's place in the class (CLDT pairs: odd major, even minor). */
int AW_LevelupSkillClass(const aw_class_t *k,int skill);
/* The progress a skill needs for its next point: (base + 1) x the major/minor/misc factor, x fSpecialSkillBonus
 * when the skill is of the class's specialization (getSkillProgressRequirement). */
float AW_LevelupRequirement(const aw_levelup_rules_t *r,const aw_class_t *k,int skill,int base);
/* A skill used: progress += use value x scale / requirement; at 1 the skill rises (source usage). Returns 1 when it
 * rose, 0 when not, -1 when the skill cannot gain (100 or more, or no rules). c->progress keeps the fraction. */
int AW_LevelupSkillUsed(const aw_levelup_rules_t *r,const aw_class_t *k,aw_character_t *c,int skill,int use,float scale);
/* A skill raised by one (skillLevelUpHandler): the level progress (iLevelupMajorMult / MinorMult), the governing
 * attribute's count (iLevelupMajor/Minor/MiscMultAttribute) and the specialization count; progress back to 0 for a
 * raise by use. 1 when raised, 0 at 100. */
int AW_LevelupSkillRaise(const aw_levelup_rules_t *r,const aw_class_t *k,aw_character_t *c,int skill,int source);
/* The level-up is due: level progress at iLevelupTotal. */
int AW_LevelupDue(const aw_levelup_rules_t *r,const aw_character_t *c);
/* An attribute's multiplier for the box: 1 with no raises, else iLevelUpNNMult for min(10, raises). */
int AW_LevelupMultiplier(const aw_levelup_rules_t *r,const aw_character_t *c,int attribute);
/* The level-up applied (onOkButtonClicked + NpcStats::levelUp): each picked attribute + its multiplier (at most
 * 100), level progress - iLevelupTotal (not below 0), the attribute and specialization counts cleared, the level
 * + 1, health maximum and current + Endurance x fLevelUpHealthEndMult (Endurance after the raise; current at least
 * 1). Returns the new level, 0 when PICKS is not COUNT distinct attributes. */
int AW_LevelupApply(const aw_levelup_rules_t *r,aw_character_t *c,const int *picks,int count);
/* A barter's Mercantile_Success scale (OpenMW mwgui/tradewindow.cpp, "apply skill gain on successful barter"): the
 * share haggled, floor(100 x (merchant offer - price) / merchant offer) when buying below the offer, floor(100 x
 * (price - offer) / price) when selling above it, else 0. A trade at the merchant's own price trains nothing. */
float AW_LevelupMercantileScale(int buying,int final_price,int merchant_offer);
/* The level-up picture (getLevelupClassImage): by the share of raises of each specialization. */
const char *AW_LevelupClassImage(int combat,int magic,int stealth);

/* The level-up box's own state (LevelupDialog): the coins (min(3, attributes under 100)) and the picks. */
typedef struct {int coins,count,picks[3];} aw_levelup_box_t;
void AW_LevelupBoxOpen(const aw_character_t *c,aw_levelup_box_t *b);
/* A click on an attribute (onAttributeClicked): a picked one is taken back; otherwise it is added, or replaces the
 * last pick when every coin is placed. Attributes at 100 cannot be picked. Returns 1 when the picks changed. */
int AW_LevelupBoxClick(const aw_character_t *c,aw_levelup_box_t *b,int attribute);
/* 1 when ATTRIBUTE holds a coin. */
int AW_LevelupBoxPicked(const aw_levelup_box_t *b,int attribute);
/* The value the box shows: base, + the multiplier when picked, at most 100. */
int AW_LevelupBoxValue(const aw_levelup_rules_t *r,const aw_character_t *c,const aw_levelup_box_t *b,int attribute);
/* OK may close the box: every coin placed. */
int AW_LevelupBoxReady(const aw_levelup_box_t *b);

/* aw_levelup.c: the engine side. */
extern aw_levelup_rules_t aw_levelup_rules;
int AW_LevelupLoad(void);
/* The game reports a skill use (combat, movement): the rule above on the player, with the skill-raise message and
 * sound and, at the level threshold, the rest message. Returns 1 when the skill rose. */
int AW_LevelupUse(int skill,int use,float scale);
/* A skill raised by a trainer or a book (the dialogue's training): the skill-raise rule with its message. */
int AW_LevelupRaise(int skill,int source);
/* Seconds of running or swimming on foot (Athletics; OpenMW character.cpp: one use per whole second). */
void AW_LevelupMoveSeconds(int running,int swimming,float seconds);
/* One of the game's own lines from levelup/settings.txt ("text KEY ..."; tools/prepare_levelup.py TEXTS), read from
 * disk on each call (callers keep it); 0 when the image does not have it. */
int AW_LevelupGameText(const char *key,char *out,int size);
/* A rest ended normally: the box opens when the level-up is due. Returns 1 when it opened. */
int AW_LevelupRested(void);
int AW_LevelupBoxActive(void);
void AW_LevelupInit(void);
#endif
