/* SPDX-License-Identifier: GPL-2.0-or-later
 * INVENTORY-ITEM-INFO-67: the item information box over the inventory window. The maintainer's design (18 November
 * 2026): an information key (P here: I closes the inventory) opens an overlaid box with the selected item's properties
 * and its written description, a vertical scroll bar when it does not fit, and a button row: OK (back to the
 * inventory) and the item's action (Equip, Unequip, Use, Read). The properties are what the original's tooltip shows
 * for the item's kind (rules from OpenMW 0.53 apps/openmw/mwclass/<kind>.cpp getToolTipInfo and mwgui/widgets.cpp
 * MWSpellEffect, written independently):
 *   weapon      Type: <skill>[, One Handed | Two Handed]; Chop, Slash, Thrust (melee) or Attack (a bow, a crossbow;
 *               a thrown weapon twice its damage); Condition: now/full
 *   armour      Armor Rating; Condition: now/full; Weight: w (Light | Medium | Heavy)
 *   apparatus   Quality
 *   every kind  Weight (armour: with its class), Value
 *   enchanted   the enchantment's kind (Cast Once, Cast When Strikes, Cast When Used, Constant Effect), one line per
 *               effect, Charge: now/full (When Strikes, When Used)
 *   potion      its effects (by the Alchemy skill: an effect the player cannot know yet shows "?")
 *   ingredient  its effects (the same rule)
 *   book, scroll  its text (books.awb), after an empty line
 * The words are the original's English game settings (sType, sChop, sSlash, sThrust, sAttack, sCondition,
 * sArmorRating, sWeight, sValue, sQuality, sCharges, sItemCastOnce ... and the skills' names).
 * The box is laid out by the shared layout helper (aw_layout.c: the frame, the title row, the content, the centred
 * button row its bottom margin above the frame's inner edge) and drawn through aw_ui.c (the frame, the title in the
 * small font, the buttons, the scroll bar) and the console font (the lines, 4 pixels a character, 8 a row), so the
 * layout check measures it (tests/aga_ui_layout_test.c). Budget: nothing resident; while open, the text (its
 * properties and a book's text, at most AW_ITEMINFO_TEXT_MAX bytes) and 5 bytes a wrapped line, freed on close; one
 * read of books.awb when a book's box opens; per frame only the lines in view are drawn. */
#ifndef AW_ITEMINFO_HEADER
#define AW_ITEMINFO_HEADER
#include "aw_inventory.h"
#include "aw_layout.h"

#define AW_ITEMINFO_TEXT_MAX 49152   /* the properties and a book's text (tools/prepare_books.py: 40000 bytes at most) */
#define AW_ITEMINFO_LINES_MAX 2048   /* a 40,000-byte book wraps to under 1,000 lines of 60 characters */
#define AW_ITEMINFO_ROW 8            /* a console-font line: 5 rows of glyph and 3 clear */
#define AW_ITEMINFO_CHAR 4           /* its advance */
#define AW_ITEMINFO_BAR 12           /* the scroll bar (10) and its gap, taken from the text's width when it shows */
/* where the box stands on the 320 x 200 screen, over the inventory window */
#define AW_ITEMINFO_X 26
#define AW_ITEMINFO_Y 10
#define AW_ITEMINFO_W 268
#define AW_ITEMINFO_H 180
#define AW_ITEMINFO_TITLE_H 12

/* What the box shows beyond the item's catalogue row, gathered by the window when it opens (aw_worldui.c) */
typedef struct {
    int condition_known;float condition;    /* the carried copy's condition now, a share (0..1) of its full health */
    int charge_known;float charge;          /* its enchantment's charge now */
    const char *magic;                      /* its enchantment's, a potion's or an ingredient's effect lines, '\n' between */
    const char *body;                       /* its written text (a book's, a scroll's), NULL for none */
} aw_iteminfo_extra_t;

/* The box's text: the properties, one per line, then the enchantment, the effects and the written text, as above.
 * Pure. Its length (cut at SIZE). */
int AW_ItemInfoText(const aw_inventory_item_t *it,const aw_iteminfo_extra_t *x,char *out,int size);

typedef struct {
    char title[96],action[16];   /* the item's name; the action button's word (empty: OK alone) */
    char *text;                  /* the box's text (heap) */
    int *line;unsigned char *len;int lines;   /* each wrapped line's start and length (heap) */
    int chars;                   /* the characters a line holds */
    int top;                     /* the first line in view */
    int drag;                    /* the scroll bar held */
} aw_iteminfo_t;
enum {AW_ITEMINFO_KEEP,AW_ITEMINFO_CLOSE,AW_ITEMINFO_ACTION};
/* Open the box for IT (X its extras, NULL none; ACTION the action button's word, NULL or "" for OK alone): the text
 * composed and wrapped; NULL when there is no memory (nothing kept). */
aw_iteminfo_t *AW_ItemInfoOpen(const aw_inventory_item_t *it,const aw_iteminfo_extra_t *x,const char *action);
void AW_ItemInfoClose(aw_iteminfo_t *b);
/* The box's layout (aw_layout.c), its text area TEXT (x, y, w, h) and how many lines it shows */
void AW_ItemInfoLayout(const aw_iteminfo_t *b,aw_layout_t *l,int text[4],int *visible);
/* Draw it; the pointer at MOUSE_X MOUSE_Y lights the button under it */
void AW_ItemInfoDraw(const aw_iteminfo_t *b,int mouse_x,int mouse_y);
/* A key or a click (the pointer at MOUSE_X MOUSE_Y); USE_KEY 1 when the key is one of the window's use keys, INFO_KEY
 * when it is the information key. Up/Down, Page Up/Down, Home/End and the wheel scroll; the use keys or the action
 * button act (AW_ITEMINFO_ACTION); Esc, the information key or OK close (AW_ITEMINFO_CLOSE; Esc and I are the
 * window's to send); a click on the scroll bar scrolls and holds it. */
int AW_ItemInfoKey(aw_iteminfo_t *b,int key,int mouse_x,int mouse_y,int use_key,int info_key);
/* The pointer moved to MOUSE_Y while the scroll bar is held */
void AW_ItemInfoDrag(aw_iteminfo_t *b,int mouse_y);

/* The window's sources for the extras (aw_worldui.c defines them; NULL in the fixtures: none shown): the carried
 * copy's condition (aw_inventory.c), an enchantment's effect lines (aw_cast.c), a potion's or an ingredient's
 * (aw_alchemy.c), a book's text in a fresh allocation the caller frees (aw_reader.c). The lines' functions return 1
 * when they wrote any. */
extern int (*aw_worldui_condition)(const char *id,float *condition);
extern int (*aw_worldui_enchant_lines)(const aw_inventory_item_t *it,char *out,int size);
extern int (*aw_worldui_alchemy_lines)(const aw_inventory_item_t *it,char *out,int size);
extern char *(*aw_worldui_book_text)(const char *id);
#endif
