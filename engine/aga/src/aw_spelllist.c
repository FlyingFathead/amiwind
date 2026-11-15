/* SPDX-License-Identifier: GPL-2.0-or-later
 * The character windows' spell lists, the engine glue (aw_spelllist.h, CHARGEN-ABILITY-DESCRIPTIONS-65): the race's or
 * the birthsign's spells from the shared stats record (the same rows the player is given, aw_mwhost.c
 * creation_spells), their names, types and effects from the actor table, the effects' names and flags from its magic
 * effect rows, their small icons from gfx/effects.awe, drawn in the console font with a scroll bar when long.
 *
 * Cost (budget sheet, docs/CHARACTER_CREATION.md "Cost"):
 * - resident: the one list (AW_SL_ROWS rows of AW_SL_TEXT + 4 bytes) and at most 32 icons of 144 bytes, static,
 *   about 11 KB; nothing per area;
 * - per event (a race or a sign shown): the spell rows' reads from the actor table (a few seeks each), one open of the
 *   effect file for all the icons; nothing while drawing;
 * - per frame: the rows that fit (a few dozen console glyph rows and the icon blits). */
#include "quakedef.h"
#include "aw_spelllist.h"
#include "aw_fxrow.h"
#include "aw_effects.h"
#include "aw_actorstate.h"
#include "aw_stats.h"
#include "aw_statswin.h"
#include "aw_inventory.h"
#include "aw_character.h"

#define ICONS 32
#define SCROLL_W 11   /* the scroll bar and a pixel */
static aw_sl_list_t list;
static aw_sl_spell_t spells[AW_SL_SPELLS];
static int spell_count,shown_race=-2,shown_birth=-2,shown_w,top;
static short icon_effect[ICONS];
static unsigned char icon_px[ICONS][AW_FX_HUD_ICON*AW_FX_HUD_ICON],icon_ok[ICONS];
static int icon_count;

static void copy_text(char *out,int size,const char *in){int n=0;if(in)while(n<size-1 && in[n]){out[n]=in[n];n++;}out[n]=0;}
/* the spells of race RACE or (RACE < 0) birthsign BIRTH into SPELLS; their count */
static int gather(int race,int birth){
    long tb;const unsigned char *t=AW_AreaStatsShared(&tb);int rows[AW_SL_SPELLS],n=0,i,j,m,k=0,cost,group;
    aw_spell_effect_t e[AW_SL_EFFECTS];aw_mgef_t mg;
    if(!t)return 0;
    if(race>=0 && race<aw_race_count)n=AW_StatRaceSpells(t,tb,AW_StatIdHash(aw_races[race].id),rows,AW_SL_SPELLS);
    else if(birth>=0 && birth<aw_birth_count)n=AW_StatBirthSpells(t,tb,AW_StatIdHash(aw_births[birth].id),rows,AW_SL_SPELLS);
    for(i=0;i<n && k<AW_SL_SPELLS;i++){
        aw_sl_spell_t *s=&spells[k];
        memset(s,0,sizeof(*s));
        if(!AW_ActorSpellInfo(rows[i],&s->type,s->name,sizeof(s->name),&cost))continue;
        m=AW_ActorSpellEffects(rows[i],e,AW_SL_EFFECTS);
        for(j=0;j<m;j++){
            aw_sl_effect_t *x=&s->e[s->n++];
            x->effect=e[j].effect;x->range=e[j].range;x->area=e[j].area;x->duration=e[j].duration;
            x->min=e[j].magnitude_min;x->max=e[j].magnitude_max;
            memset(&mg,0,sizeof(mg));
            if(AW_ActorMagicEffect(e[j].effect,&mg)){x->flags=mg.flags;copy_text(x->name,sizeof(x->name),mg.name);}
            AW_EffectKind(e[j].effect,&group);
            if(group==0 && e[j].attribute>=0)copy_text(x->arg,sizeof(x->arg),AW_StatsAttributeName(e[j].attribute));
            else if(group==4 && e[j].skill>=0)copy_text(x->arg,sizeof(x->arg),AW_StatsSkillName(e[j].skill));
        }
        k++;
    }
    return k;
}
/* the rows for W pixels: the full width first, the scroll bar's room taken off when the list is longer than H */
static void layout(int w,int h){
    int text=w-2;
    AW_SpellListBuild(spells,spell_count,text/AW_SL_CHAR_W,(text-AW_SL_ICON_W)/AW_SL_CHAR_W,&list);
    if(AW_SpellListFit(&list,0,h)<list.rows){
        text-=SCROLL_W;
        AW_SpellListBuild(spells,spell_count,text/AW_SL_CHAR_W,(text-AW_SL_ICON_W)/AW_SL_CHAR_W,&list);
    }
}
static void icons(void){
    int i,j;
    icon_count=0;
    for(i=0;i<list.rows;i++){
        if(list.row[i].kind!=AW_SL_EFFECT)continue;
        for(j=0;j<icon_count && icon_effect[j]!=list.row[i].effect;j++);
        if(j==icon_count && icon_count<ICONS)icon_effect[icon_count++]=list.row[i].effect;
    }
    if(icon_count){AW_FxSmallIcons(icon_effect,icon_count,icon_px,icon_ok);}
}
/* the list of race RACE (BIRTH -1) or birthsign BIRTH (RACE -1) for a panel W x H; its rows, 0 none (the window then
 * shows the names it had before) */
static int open_list(int race,int birth,int w,int h){
    if(race==shown_race && birth==shown_birth && w==shown_w)return list.rows;
    shown_race=race;shown_birth=birth;shown_w=w;top=0;
    spell_count=gather(race,birth);
    if(!spell_count){memset(&list,0,sizeof(list));icon_count=0;return 0;}
    layout(w,h);icons();
    return list.rows;
}
static void draw_list(int x,int y,int w,int h){
    int gold=AW_UIColor(223,199,144),bright=AW_UIColor(255,240,200),muted=AW_UIColor(150,135,104),i,n,yy=y,indent=0,max;
    max=AW_SpellListMaxTop(&list,h);
    if(top>max)top=max;
    if(top<0)top=0;
    n=AW_SpellListFit(&list,top,h);
    for(i=top;i<top+n && i<list.rows;i++){
        const aw_sl_row_t *r=&list.row[i];int text_w=w-2-(n<list.rows?SCROLL_W:0);
        if(r->kind==AW_SL_HEAD){AW_SmallStringColor(x+1,yy+3,text_w,r->text,muted);indent=0;}
        else if(r->kind==AW_SL_NAME){AW_SmallStringColor(x+3,yy+2,text_w-2,r->text,bright);indent=2;}
        else if(r->kind==AW_SL_EFFECT){
            int k,row_px;
            for(k=0;k<icon_count && icon_effect[k]!=r->effect;k++);
            if(k<icon_count && icon_ok[k] && x+3+AW_FX_HUD_ICON<=(int)vid.width && yy+AW_FX_HUD_ICON<=(int)vid.height)
                for(row_px=0;row_px<AW_FX_HUD_ICON;row_px++)
                    memcpy(vid.buffer+(yy+row_px)*vid.rowbytes+x+3,icon_px[k]+row_px*AW_FX_HUD_ICON,AW_FX_HUD_ICON);
            else{AW_UIFill(x+3,yy,AW_FX_HUD_ICON,AW_FX_HUD_ICON,muted);AW_UIFill(x+4,yy+1,AW_FX_HUD_ICON-2,AW_FX_HUD_ICON-2,AW_UIColor(0,0,0));}
            indent=2+AW_SL_ICON_W;
            AW_SmallStringColor(x+1+indent,yy+4,text_w-indent,r->text,gold);
        }else AW_SmallStringColor(x+1+indent,yy+1,text_w-indent,r->text,indent>2?gold:bright);
        yy+=r->height;
    }
    if(n<list.rows)AW_UIScrollbar(x+w-10,y,h,list.rows,n,top);
}
/* DELTA rows up (< 0) or down in a panel H high */
static void scroll_list(int delta,int h){
    int max=AW_SpellListMaxTop(&list,h);
    top+=delta;
    if(top>max)top=max;
    if(top<0)top=0;
}
/* a click at MX, MY on the scroll bar of the panel X, Y, W x H: 1 when it took it */
static int click_list(int mx,int my,int x,int y,int w,int h){
    int n=AW_SpellListFit(&list,top,h),t;
    if(n>=list.rows)return 0;
    t=AW_UIScrollHit(mx,my,x+w-10,y,h,list.rows,n,top);
    if(t<0)return 0;
    top=t;scroll_list(0,h);return 1;
}
static void forget(void){shown_race=shown_birth=-2;shown_w=0;}

extern int (*aw_chargen_spells_open)(int race,int birth,int w,int h);   /* aw_character.c */
extern void (*aw_chargen_spells_draw)(int x,int y,int w,int h);
extern void (*aw_chargen_spells_scroll)(int delta,int h);
extern int (*aw_chargen_spells_click)(int mx,int my,int x,int y,int w,int h);
extern void (*aw_chargen_spells_forget)(void);
void AW_SpellListInit(void){
    aw_chargen_spells_open=open_list;aw_chargen_spells_draw=draw_list;aw_chargen_spells_scroll=scroll_list;
    aw_chargen_spells_click=click_list;aw_chargen_spells_forget=forget;
}
