/* SPDX-License-Identifier: GPL-2.0-or-later
 * The spell lists of the character windows (CHARGEN-ABILITY-DESCRIPTIONS-65; docs/CHARACTER_CREATION.md): the birthsign
 * window's abilities, powers and spells and the race window's specials, each spell by name under its group heading
 * with every effect on a line of its own under it: the effect's icon, its name (with the attribute or skill it names),
 * the magnitude, and for a power or a spell the duration and the range, in the console font.
 *
 * Rules from OpenMW 0.51 (written independently): the groups and their order (apps/openmw/mwgui/birth.cpp
 * updateSpells: abilities, powers, spells; an ability's effects shown as constant), the effect line
 * (apps/openmw/mwgui/widgets.cpp MWSpellEffect::updateWidgets: name, "min to max" with pt, pts, %, ft, level or
 * x INT, then for a non-constant effect "for N secs", "in N ft area", "on Self/Touch/Target"), the effect's name with
 * its attribute or skill (apps/openmw/mwmechanics/magiceffects.cpp getMagicEffectString), the magnitude kinds
 * (components/esm3/loadmgef.cpp getMagnitudeDisplayType).
 *
 * The rules here are pure (aw_spelllist_rules.c, host-tested: tests/aga_spelllist_test.c); aw_spelllist.c reads the
 * records (the actor table's spell, effect and magic-effect rows, the effect icons of gfx/effects.awe) and draws. */
#ifndef AW_SPELLLIST_H
#define AW_SPELLLIST_H

#define AW_SL_EFFECTS 8       /* effects of one spell at most (the masters have at most 8) */
#define AW_SL_SPELLS 16       /* spells of one race or birthsign at most */
#define AW_SL_ROWS 96         /* rows of one list at most */
#define AW_SL_TEXT 64         /* one row's text */
#define AW_SL_CHAR_W 4        /* the console font's advance */
#define AW_SL_ICON_W 14       /* an effect row's text starts this far right of the icon's left edge */

/* the MGEF flags the line reads (components/esm3/loadmgef.hpp) */
#define AW_SL_NO_DURATION 0x4u
#define AW_SL_NO_MAGNITUDE 0x8u
#define AW_SL_APPLIED_ONCE 0x1000u

/* One effect of a spell: EFFECT 0..142, RANGE 0 self 1 touch 2 target, the record's AREA, DURATION and magnitudes,
 * FLAGS its magic effect's flags, NAME the effect's name ("Fortify Attribute"), ARG the attribute or skill it names
 * ("Agility"; empty none). */
typedef struct {short effect;unsigned char range;unsigned short area,duration,min,max;unsigned long flags;
                char name[32],arg[24];} aw_sl_effect_t;
/* One spell: NAME, TYPE (the SPEL type: 0 spell, 1 ability, 2 blight, 3 disease, 4 curse, 5 power), N effects. */
typedef struct {char name[48];int type,n;aw_sl_effect_t e[AW_SL_EFFECTS];} aw_sl_spell_t;

/* A row: a group heading, a spell's name, an effect's first line (EFFECT its number: the icon is drawn beside it), or
 * a further line of a long name or effect. HEIGHT its pixels. */
enum {AW_SL_HEAD,AW_SL_NAME,AW_SL_EFFECT,AW_SL_MORE};
#define AW_SL_HEAD_H 10
#define AW_SL_NAME_H 9
#define AW_SL_EFFECT_H 13     /* the 12 x 12 icon and a pixel */
#define AW_SL_MORE_H 8
typedef struct {unsigned char kind,height;short effect;char text[AW_SL_TEXT];} aw_sl_row_t;
typedef struct {int rows,spells;aw_sl_row_t row[AW_SL_ROWS];} aw_sl_list_t;

/* The magnitude kind of EFFECT (loadmgef.cpp): */
enum {AW_SL_MAG_NONE,AW_SL_MAG_POINTS,AW_SL_MAG_PERCENT,AW_SL_MAG_FEET,AW_SL_MAG_LEVEL,AW_SL_MAG_TIMES_INT};
int AW_SpellMagnitudeKind(int effect,unsigned long flags);
/* The effect's line into OUT (CAPACITY bytes): CONSTANT 1 for an ability's effect (no duration, area or range);
 * AW_SL_NO_TARGET for a potion's (its duration, no range: widgets.cpp mNoTarget; INVENTORY-ITEM-INFO-67). Its length. */
#define AW_SL_NO_TARGET 2
int AW_SpellEffectText(const aw_sl_effect_t *e,int constant,char *out,int capacity);
/* The rows of the N spells S: the groups Abilities (abilities and the other always-active kinds), Powers and Spells,
 * in that order, each with a heading, its spells by name in their order and every effect's line, names wrapped to
 * NAME_CHARS characters and effect lines to EFFECT_CHARS. The row count (rows past AW_SL_ROWS are dropped). */
int AW_SpellListBuild(const aw_sl_spell_t *s,int n,int name_chars,int effect_chars,aw_sl_list_t *out);
/* How many rows from TOP fit in H pixels (at least one when a row is left). */
int AW_SpellListFit(const aw_sl_list_t *l,int top,int h);
/* The lowest TOP that still fills H to the end of the list. */
int AW_SpellListMaxTop(const aw_sl_list_t *l,int h);

/* ---- engine glue (aw_spelllist.c) ---- */
void AW_SpellListInit(void);
#endif
