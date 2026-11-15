/* SPDX-License-Identifier: GPL-2.0-or-later
 * The active-effect icons (aw_fxrow.h): the HUD grid under the view, the Stats window's row and its V list.
 *
 * Cost (HUD-ACTIVE-EFFECTS-ROW-64 budget sheet, docs/HUD_ACTIVE_EFFECTS.md "Cost"):
 * - resident: the effect file's directory (143 rows, read once) and a picture cache of AW_FX_HUD_MAX 12 x 12 icons,
 *   allocated on the first effect shown; nothing per area;
 * - per frame: one pass of the effect pool (64 entries), the always-active spells' entries kept from the last change of
 *   the player's spell list, a sort of at most AW_FX_ENTRIES, and the blits of the icons shown (144 bytes each);
 * - disk: a new effect's icon is read when it first shows (one open of gfx/effects.awe for every icon missing that
 *   frame, one seek and 144 bytes each); the always-active spells' effects are read again only when the spell list
 *   changes; the V list reads its pictures and descriptions when it opens and frees them when it closes. */
#include "quakedef.h"
#include "aw_fxrow.h"
#include "aw_effects.h"
#include "aw_actorstate.h"
#include "aw_statswin.h"
#include "aw_inventory.h"
#include "aw_reset.h"
#include "aw_tryalloc.h"

/* aw_hud_effects 1 (the default, config/game.cfg): the icons under the view and on the Stats window; 0 none (the V list
 * stays) */
static cvar_t hud_effects={"aw_hud_effects","1",true};
extern int (*aw_title_bar)(int x,int y,int w,const char *title);
extern int aw_worldui_panel_holds_escape;

/* ---- the effect file ---- */
static aw_fx_dir_t dir[AW_FX_EFFECTS];
static int dir_count=-2;           /* -2 not read yet, -1 none or bad */
static int dir_ready(void){
    FILE *f=NULL;unsigned char head[8+AW_FX_EFFECTS*AW_FX_ROW_BYTES];int size,n;
    if(dir_count!=-2)return dir_count>0;
    dir_count=-1;
    size=COM_FOpenFile(AW_FX_FILE,&f);
    if(!f)return 0;
    n=size<(int)sizeof(head)?size:(int)sizeof(head);
    /* AW_FxDirectory checks the header's length itself */
    if(n>0 && (int)fread(head,1,n,f)==n)dir_count=AW_FxDirectory(head,(unsigned long)n,(unsigned long)size,dir,AW_FX_EFFECTS);
    fclose(f);
    if(dir_count<0)Con_DPrintf("Active effects: %s missing or not readable; no effect icons.\n",AW_FX_FILE);
    return dir_count>0;
}
/* N pieces of the effect file, each OFFSET[i] .. +BYTES[i] into OUT[i], in one open; OK[i] 1 for each piece read (OK
 * may be NULL); how many were read */
static int file_read(int n,const unsigned long *offset,const int *bytes,unsigned char **out,unsigned char *ok){
    FILE *f=NULL;int i,got=0,one;long base;
    if(ok)memset(ok,0,(size_t)(n>0?n:0));
    if(n<1)return 0;
    COM_FOpenFile(AW_FX_FILE,&f);
    if(!f)return 0;
    base=ftell(f);
    for(i=0;i<n;i++){
        one=offset[i] && bytes[i]>0 && !fseek(f,base+(long)offset[i],SEEK_SET) && (int)fread(out[i],1,bytes[i],f)==bytes[i];
        if(ok)ok[i]=(unsigned char)one;
        got+=one;
    }
    fclose(f);return got;
}

/* CHARGEN-ABILITY-DESCRIPTIONS-65 (aw_spelllist.c): the small pictures of N EFFECTS into OUT, in one open of the file;
 * OK[i] 1 for each one read; how many were read */
int AW_FxSmallIcons(const short *effects,int n,unsigned char (*out)[AW_FX_HUD_ICON*AW_FX_HUD_ICON],unsigned char *ok){
    unsigned long offset[32];int bytes[32],i;unsigned char *to[32];
    if(ok)memset(ok,0,(size_t)(n>0?n:0));
    if(n<1 || !dir_ready())return 0;
    if(n>32)n=32;
    for(i=0;i<n;i++){
        offset[i]=effects[i]>=0 && effects[i]<dir_count?dir[effects[i]].small:0;
        bytes[i]=AW_FX_HUD_ICON*AW_FX_HUD_ICON;to[i]=out[i];
    }
    return file_read(n,offset,bytes,to,ok);
}

/* ---- the HUD pictures: AW_FX_HUD_MAX slots, least recently drawn replaced ---- */
#define PIXELS (AW_FX_HUD_ICON*AW_FX_HUD_ICON)
typedef struct {short effect;unsigned char state;unsigned long used;unsigned char px[PIXELS];} pic_t;   /* state 0 empty, 1 ok, 2 no picture */
static pic_t *pics;
static unsigned long pic_clock,pic_reads,pic_opens;
static pic_t *pic_find(int effect){
    int i;
    if(!pics)return NULL;
    for(i=0;i<AW_FX_HUD_MAX;i++)if(pics[i].state && pics[i].effect==effect)return &pics[i];
    return NULL;
}
/* the pictures of the EFFECTS not held yet, in one open of the file */
static void pic_fill(const short *effects,int n){
    unsigned long offset[AW_FX_HUD_MAX];int bytes[AW_FX_HUD_MAX],i,k,m=0,j;unsigned char *out[AW_FX_HUD_MAX];pic_t *slot[AW_FX_HUD_MAX];
    if(!dir_ready())return;
    if(!pics && !(pics=(pic_t *)AW_TryCalloc(AW_FX_HUD_MAX,sizeof(pic_t))))return;
    pic_clock++;
    for(i=0;i<n;i++){pic_t *p=pic_find(effects[i]);if(p)p->used=pic_clock;}
    for(i=0;i<n && m<AW_FX_HUD_MAX;i++){
        pic_t *best=NULL;
        if(pic_find(effects[i]))continue;
        for(k=0;k<AW_FX_HUD_MAX;k++){   /* an empty slot, else the one drawn longest ago (never one drawn now) */
            pic_t *p=&pics[k];
            if(p->state && p->used==pic_clock)continue;
            for(j=0;j<m && slot[j]!=p;j++);
            if(j<m)continue;
            if(!best || !p->state || (best->state && p->used<best->used))best=p;
            if(!p->state)break;
        }
        if(!best)break;
        best->effect=effects[i];best->state=2;best->used=pic_clock;
        if(effects[i]>=0 && effects[i]<dir_count && dir[effects[i]].small){
            slot[m]=best;offset[m]=dir[effects[i]].small;bytes[m]=PIXELS;out[m]=best->px;m++;
        }
    }
    if(m){
        unsigned char ok[AW_FX_HUD_MAX];
        pic_opens++;
        file_read(m,offset,bytes,out,ok);
        for(i=0;i<m;i++)if(ok[i]){slot[i]->state=1;pic_reads++;}   /* a short read leaves "no picture" */
    }
}
static void pic_draw(const pic_t *p,int x,int y,int frame){
    int yy;
    if(x<0 || y<0 || x+AW_FX_HUD_ICON>(int)vid.width || y+AW_FX_HUD_ICON>(int)vid.height)return;
    if(p && p->state==1){
        for(yy=0;yy<AW_FX_HUD_ICON;yy++)memcpy(vid.buffer+(y+yy)*vid.rowbytes+x,p->px+yy*AW_FX_HUD_ICON,AW_FX_HUD_ICON);
        return;
    }
    AW_UIFill(x,y,AW_FX_HUD_ICON,AW_FX_HUD_ICON,frame);   /* no picture in this build: an empty framed place */
    AW_UIFill(x+1,y+1,AW_FX_HUD_ICON-2,AW_FX_HUD_ICON-2,AW_UIColor(0,0,0));
}

/* ---- what is active on the player ---- */
/* the spells of the player's list that act always (abilities, diseases, blights, curses): read again when that list
 * changes (OpenMW activespells.cpp keeps them active with no end) */
#define PASSIVE 32
static aw_fx_entry_t passive[PASSIVE];
static int passive_n;
static unsigned long passive_sig,passive_reads;
static unsigned long spell_signature(const aw_actor_t *a){
    unsigned long h=AW_RESET_SEED,epoch=AW_ActorStateEpoch();
    h=AW_ResetHash(h,&epoch,sizeof(epoch));
    if(!a)return h^1UL;
    h=AW_ResetHash(h,&a->base,sizeof(a->base));h=AW_ResetHash(h,&a->nspells,1);
    if(a->spells && a->nspells)h=AW_ResetHash(h,a->spells,sizeof(*a->spells)*a->nspells);
    return h;
}
static void passive_refresh(void){
    aw_actor_t *a=AW_ActorPlayer();int held[64],n,i,k,m,type,group;aw_spell_effect_t e[AW_MADE_EFFECTS];
    unsigned long sig=spell_signature(a);
    if(sig==passive_sig)return;
    passive_sig=sig;passive_n=0;
    if(!a)return;
    passive_reads++;
    n=AW_ActorSpells(a,held,64);
    for(i=0;i<n;i++){
        if(!AW_ActorSpellInfo(held[i],&type,NULL,0,NULL) || type<=0 || type==5)continue;   /* a spell or power: only when cast */
        m=AW_ActorSpellEffects(held[i],e,AW_MADE_EFFECTS);
        for(k=0;k<m && passive_n<PASSIVE;k++){
            aw_fx_entry_t *p=&passive[passive_n++];
            p->effect=e[k].effect;AW_EffectKind(e[k].effect,&group);
            p->arg=group==0?e[k].attribute:group==4?e[k].skill:-1;
            p->source=held[i];p->from=(unsigned char)AW_FxFromSpellType(type);
            p->magnitude=.5f*((float)e[k].magnitude_min+(float)e[k].magnitude_max);p->left=-1;
        }
    }
}
/* the player's entries now, sorted by effect; their count */
static int collect(aw_fx_entry_t *out,int max){
    aw_effect_info_t fx[AW_EFFECTS_PLAYER];int n,i,k=0;
    n=AW_EffectsList(AW_ACTOR_PLAYER_REF,fx,AW_EFFECTS_PLAYER);
    for(i=0;i<n && k<max;i++){
        aw_fx_entry_t *e;
        if(fx[i].source==AW_EFFECT_SOURCE_SCRIPT)continue;   /* a script's base modifier (SetResistFire): no icon */
        e=&out[k++];e->effect=(short)fx[i].effect;e->arg=(short)fx[i].arg;e->magnitude=fx[i].magnitude;
        if(fx[i].source>=AW_EFFECT_SOURCE_CONSTANT){e->from=AW_FX_FROM_WORN;e->source=fx[i].source-AW_EFFECT_SOURCE_CONSTANT;e->left=-1;}
        else{
            e->from=fx[i].source>=AW_EFFECT_SOURCE_ITEM?AW_FX_FROM_ITEM:AW_FX_FROM_SPELL;
            e->source=fx[i].source>=AW_EFFECT_SOURCE_ITEM?-1:fx[i].source;
            e->left=fx[i].left<0?-1:fx[i].left;
        }
    }
    passive_refresh();
    for(i=0;i<passive_n && k<max;i++)out[k++]=passive[i];
    return AW_FxSort(out,k);
}
static aw_fx_entry_t now_e[AW_FX_ENTRIES];
static aw_fx_group_t now_g[AW_FX_ENTRIES];
static int now_groups;
static double now_frame=-1;
static int groups_now(void){
    int n;
    if(now_frame==realtime)return now_groups;
    now_frame=realtime;
    n=cls.state==ca_connected && sv.active?collect(now_e,AW_FX_ENTRIES):0;
    now_groups=AW_FxGroups(now_e,n,now_g,AW_FX_ENTRIES);
    return now_groups;
}
/* draws the icons in WIDTH x HEIGHT at X, the bottom row's top at Y_BOTTOM; rows going up */
static void draw_grid(int x,int y_bottom,int width,int height,int max_rows){
    aw_fx_layout_t l;short want[AW_FX_HUD_MAX];int i,px,py,n=groups_now();char more[8];
    if(!n || !AW_FxLayout(n,width,height,AW_FX_HUD_ICON,AW_FX_HUD_STEP,max_rows,AW_FX_HUD_MAX,&l))return;
    for(i=0;i<l.shown;i++)want[i]=now_g[i].effect;
    pic_fill(want,l.shown);
    for(i=0;i<l.shown;i++){AW_FxPlace(&l,i,x,y_bottom,AW_FX_HUD_STEP,&px,&py);pic_draw(pic_find(want[i]),px,py,AW_UIColor(150,135,104));}
    if(l.more){
        AW_FxPlace(&l,l.shown,x,y_bottom,AW_FX_HUD_STEP,&px,&py);AW_FxMoreText(l.more,more,sizeof(more));
        AW_SmallStringColor(px,py+3,(int)strlen(more)*4,more,AW_UIColor(223,199,144));
    }
    scr_copyeverything=1;
}

/* ---- the HUD: right of the weapon and magic boxes and the sneak indicator, under the view ---- */
#define HUD_X 152
#define NAME_LINE 12   /* the strip's top line: the names of what is under the crosshair */
extern int sb_lines;
extern int AW_InspectHudLift(void);
/* The debug HUD fills the strip under the view (its title above the bars, the coordinate rows beside them): then the
 * icons get rows of their own under the name line, which screen.c adds to the strip (AW_FxRowStripLines); the view
 * shrinks by them only while the debug HUD is on and effects are active. */
static int extra_lines;
static int strip_extra(void){return extra_lines;}
extern int (*aw_fx_strip_lines)(void);   /* screen.c */
static void strip_lines(int want){if(want!=extra_lines){extra_lines=want;vid.recalc_refdef=true;}}
static void hud_draw(void){
    int lift=AW_InspectHudLift(),strip_top=(int)vid.height-sb_lines,width=(int)vid.width-6-HUD_X,bottom,n;aw_fx_layout_t l;
    if(!hud_effects.value || key_dest==key_console){strip_lines(0);return;}
    n=groups_now();
    if(AW_DebugOverlaysEnabled()){
        int want=0;
        if(n && AW_FxLayout(n,width,AW_FX_ROWS_MAX*AW_FX_HUD_STEP,AW_FX_HUD_ICON,AW_FX_HUD_STEP,AW_FX_ROWS_MAX,AW_FX_HUD_MAX,&l))
            want=l.rows*AW_FX_HUD_STEP+1;
        strip_lines(want);
        /* rows under the name line; row 0, the lowest, AW_FX_HUD_STEP above the old strip */
        if(extra_lines && sb_lines>=extra_lines+NAME_LINE)
            draw_grid(HUD_X,strip_top+NAME_LINE+extra_lines-1-AW_FX_HUD_STEP,width,extra_lines-1,AW_FX_ROWS_MAX);
        return;
    }
    strip_lines(0);
    bottom=(int)vid.height-2-lift-AW_FX_HUD_ICON;
    if(sb_lines<=0 || bottom<strip_top+2)return;
    draw_grid(HUD_X,bottom,width,bottom-strip_top-2+AW_FX_HUD_ICON,AW_FX_ROWS_MAX);
}

/* ---- the Stats window: the row under the birthsign, and V ---- */
static void stats_row(int x,int y,int w){if(hud_effects.value)draw_grid(x,y,w,AW_FX_HUD_ICON,1);}

#define BOX_LINES 320
#define BOX_GROUPS AW_FX_ENTRIES
#define BOX_TOP 22
#define BOX_ROW 8
#define BOX_VISIBLE 19
#define BOX_TEXT_X 28
#define BOX_SCROLL_X 304
typedef struct {char text[AW_FX_LINE];short group;unsigned char kind;} box_line_t;   /* kind 0 name, 1 description, 2 source */
typedef struct {
    int lines,groups,top;
    box_line_t line[BOX_LINES];
    short effect[BOX_GROUPS];unsigned char has_icon[BOX_GROUPS];
    unsigned char icon[BOX_GROUPS][AW_FX_LIST_ICON*AW_FX_LIST_ICON];
} box_t;
static box_t *box;
/* the text cut to the field (no strncpy or %s into a smaller field: -O2 warns on the cut) */
static void copy_text(char *out,int size,const char *in){int n=0;if(in)while(n<size-1 && in[n]){out[n]=in[n];n++;}out[n]=0;}
static void box_add(int kind,int group,const char *text){
    box_line_t *l;
    if(box->lines>=BOX_LINES)return;
    l=&box->line[box->lines++];l->kind=(unsigned char)kind;l->group=(short)group;
    copy_text(l->text,(int)sizeof(l->text),text);
}
static void arg_name(int effect,int arg,char *out,int size){
    int group;
    out[0]=0;AW_EffectKind(effect,&group);
    if(arg<0)return;
    if(group==0)copy_text(out,size,AW_StatsAttributeName(arg));
    else if(group==4)copy_text(out,size,AW_StatsSkillName(arg));
}
static void source_name(const aw_fx_entry_t *e,char *out,int size){
    int type=-1,cost;char name[32];
    out[0]=0;
    if(e->from==AW_FX_FROM_WORN){
        aw_inventory_item_t it;
        if(AW_InventoryEquippedItem(e->source,&it))copy_text(out,size,it.name);
        return;
    }
    if(e->source>=0 && AW_ActorSpellInfo(e->source,&type,name,sizeof(name),&cost))copy_text(out,size,name);
}
static int box_build(void){
    int n,g,i,j,k,width=(BOX_SCROLL_X-4-BOX_TEXT_X)/4;
    aw_fx_entry_t *e=now_e;aw_mgef_t mg;
    char text[AW_FX_LINE*2],arg[40],src[48],t[32],wrapped[8][AW_FX_LINE],desc[640];
    FILE *f=NULL;long base=0;
    now_frame=-1;g=groups_now();
    box->groups=g<BOX_GROUPS?g:BOX_GROUPS;
    /* the pictures and descriptions of the effects listed, in one open of the file */
    if(box->groups && dir_ready()){COM_FOpenFile(AW_FX_FILE,&f);if(f)base=ftell(f);}
    if(!box->groups)box_add(1,-1,"No active effects.");
    for(i=0;i<box->groups;i++){
        const aw_fx_group_t *gr=&now_g[i];const aw_fx_dir_t *d=gr->effect<dir_count?&dir[gr->effect]:NULL;
        box->effect[i]=gr->effect;
        if(f && d && d->large && !fseek(f,base+(long)d->large,SEEK_SET) &&
           fread(box->icon[i],1,AW_FX_LIST_ICON*AW_FX_LIST_ICON,f)==AW_FX_LIST_ICON*AW_FX_LIST_ICON)box->has_icon[i]=1;
        memset(&mg,0,sizeof(mg));
        if(!AW_ActorMagicEffect(gr->effect,&mg) || !mg.name[0])snprintf(mg.name,sizeof(mg.name),"Effect %d",gr->effect);
        box_add(0,i,mg.name);
        /* the description (the record's DESC) */
        if(f && d && d->desc){
            int b=d->desc_bytes<(int)sizeof(desc)?d->desc_bytes:(int)sizeof(desc);
            if(!fseek(f,base+(long)d->desc,SEEK_SET) && (int)fread(desc,1,b,f)==b){
                n=AW_FxWrap(desc,b,width,wrapped,8);
                for(j=0;j<n;j++)box_add(1,i,wrapped[j]);
            }
        }
        for(j=gr->first;j<gr->first+gr->count;j++){
            arg_name(e[j].effect,e[j].arg,arg,sizeof(arg));source_name(&e[j],src,sizeof(src));
            AW_FxTimeText(e[j].left,t,sizeof(t));
            snprintf(text,sizeof(text),"%s%s",arg,arg[0]?": ":"");
            if(!(mg.flags&AW_MGEF_FLAG_NO_MAGNITUDE))
                snprintf(text+strlen(text),sizeof(text)-strlen(text),"%ld pts, ",(long)(e[j].magnitude+.5f));
            snprintf(text+strlen(text),sizeof(text)-strlen(text),"%s%s%s%s, %s%s",src,src[0]?" (":"",AW_FxFromName(e[j].from),
                     src[0]?")":"",t,e[j].left>=0?" left":"");
            n=AW_FxWrap(text,(int)strlen(text),width,wrapped,2);
            for(k=0;k<n;k++)box_add(2,i,wrapped[k]);
        }
    }
    if(f)fclose(f);
    return 1;
}
static int box_open(void){
    if(box)return 1;
    if(!(box=(box_t *)AW_TryCalloc(1,sizeof(*box)))){Con_Printf("Active effects: not enough memory for the list.\n");return 0;}
    box_build();return 1;
}
static void box_close(void){free(box);box=NULL;}
static void box_draw(void){
    int gold=AW_UIColor(223,199,144),muted=AW_UIColor(150,135,104),i,y,yy;
    if(!box)return;
    AW_UIFill(0,0,320,200,AW_UIColor(0,0,0));AW_UIBox(2,2,316,196);
    AW_UISmallBegin();
    if(!aw_title_bar || !aw_title_bar(6,6,308,"Active Effects"))AW_UITextCentred(6,6,308,12,"Active Effects",gold);
    AW_UISmallEnd();
    AW_UIBox(4,18,312,160);
    if(box->top>box->lines-BOX_VISIBLE)box->top=box->lines-BOX_VISIBLE;
    if(box->top<0)box->top=0;
    for(i=0;i<BOX_VISIBLE && box->top+i<box->lines;i++){
        const box_line_t *l=&box->line[box->top+i];y=BOX_TOP+i*BOX_ROW;
        AW_SmallStringColor(l->kind==0?BOX_TEXT_X:BOX_TEXT_X+4,y,BOX_SCROLL_X-8-BOX_TEXT_X,l->text,l->kind==1?muted:gold);
        /* the icon beside its name, when the name's row and the next are on the page */
        if(l->kind==0 && l->group>=0 && l->group<box->groups && i+1<BOX_VISIBLE){
            const unsigned char *p=box->icon[l->group];
            if(box->has_icon[l->group])for(yy=0;yy<AW_FX_LIST_ICON;yy++)
                memcpy(vid.buffer+(y+yy)*vid.rowbytes+8,p+yy*AW_FX_LIST_ICON,AW_FX_LIST_ICON);
            else{AW_UIFill(8,y,AW_FX_LIST_ICON,AW_FX_LIST_ICON,muted);AW_UIFill(9,y+1,AW_FX_LIST_ICON-2,AW_FX_LIST_ICON-2,AW_UIColor(0,0,0));}
        }
    }
    if(box->lines>BOX_VISIBLE)AW_UIScrollbar(BOX_SCROLL_X,BOX_TOP,BOX_VISIBLE*BOX_ROW,box->lines,BOX_VISIBLE,box->top);
    AW_UISmallBegin();AW_UITextCentred(4,180,312,14,"Up/Down scroll, V or Esc back",gold);AW_UISmallEnd();
}
static int box_key(int key,int mouse_x,int mouse_y){
    int top;
    if(!box)return 0;
    if(key=='v' || key=='V' || key==K_ESCAPE){box_close();return 0;}
    if(key==K_UPARROW || key=='w' || key==K_MWHEELUP)box->top--;
    if(key==K_DOWNARROW || key=='s' || key==K_MWHEELDOWN)box->top++;
    if(key==K_PGUP)box->top-=BOX_VISIBLE;
    if(key==K_PGDN)box->top+=BOX_VISIBLE;
    if(key==K_HOME)box->top=0;
    if(key==K_END)box->top=box->lines;
    if(key==K_MOUSE1){
        top=AW_UIScrollHit(mouse_x,mouse_y,BOX_SCROLL_X,BOX_TOP,BOX_VISIBLE*BOX_ROW,box->lines,BOX_VISIBLE,box->top);
        if(top>=0)box->top=top;
    }
    if(box->top>box->lines-BOX_VISIBLE)box->top=box->lines-BOX_VISIBLE;
    if(box->top<0)box->top=0;
    return 1;
}

/* ---- the console: the counts for the cost check ---- */
static void status(void){
    int n=groups_now(),i,held=0;
    if(pics)for(i=0;i<AW_FX_HUD_MAX;i++)held+=pics[i].state!=0;
    Con_Printf("Active effects: %d icons (%d entries, %d from always-active spells); HUD icons %s; file %s (%d rows)\n",
               n,n?now_g[n-1].first+now_g[n-1].count:0,passive_n,hud_effects.value?"on":"off",
               dir_count>0?"read":dir_count==-2?"not read yet":"none",dir_count>0?dir_count:0);
    Con_Printf("Pictures: %d of %d held (%ld bytes), %lu read in %lu opens; spell list read %lu times; strip lines %d\n",
               held,AW_FX_HUD_MAX,pics?(long)(AW_FX_HUD_MAX*sizeof(pic_t)):0L,pic_reads,pic_opens,passive_reads,extra_lines);
    for(i=0;i<n;i++){aw_mgef_t mg;AW_ActorMagicEffect(now_g[i].effect,&mg);
        Con_Printf(" %d %s: %d source%s\n",now_g[i].effect,mg.name,now_g[i].count,now_g[i].count==1?"":"s");}
}

/* New Game: what was read for the last game goes (the spell list's signature, the pictures stay valid for any game) */
static void reset_fx(int new_game){(void)new_game;passive_sig=0;passive_n=0;now_frame=-1;now_groups=0;if(box)box_close();}

extern void (*aw_hud_effects_draw)(void);              /* aw_ui.c */
extern void (*aw_stats_effects_row)(int x,int y,int w);   /* aw_statswin.c */
extern int (*aw_stats_effects_open)(void);
extern void (*aw_stats_effects_draw)(void);
extern int (*aw_stats_effects_key)(int key,int mouse_x,int mouse_y);
extern void (*aw_stats_effects_close)(void);
void AW_FxRowInit(void){
    Cvar_RegisterVariable(&hud_effects);
    Cmd_AddCommand("aw_effects_status",status);
    aw_hud_effects_draw=hud_draw;aw_fx_strip_lines=strip_extra;
    aw_stats_effects_row=stats_row;aw_stats_effects_open=box_open;aw_stats_effects_draw=box_draw;
    aw_stats_effects_key=box_key;aw_stats_effects_close=box_close;
    AW_ResetRegister("active-effect icons",reset_fx,NULL);
}
