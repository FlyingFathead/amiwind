/* SPDX-License-Identifier: GPL-2.0-or-later
 * The UI icon lookup table (aw_icons.h). Converted pictures are private
 * external game data; a missing table or row leaves the slot empty and the
 * caller draws its documented fallback. */
#include "quakedef.h"
#include "aw_icons.h"
#include "aw_inventory.h"
#include "aw_story.h"
#define ICON_ROW 160
aw_icon_stats_t aw_icon_stats;
static int icon_compare(const char *a,const char *b){
    unsigned x,y;
    do{
        x=(unsigned char)*a++;y=(unsigned char)*b++;
        if(x>='A' && x<='Z')x+='a'-'A';
        if(y>='A' && y<='Z')y+='a'-'A';
        if(x!=y)return x<y?-1:1;
    }while(x);
    return 0;
}
static unsigned long icon_u32(const byte *p){return (unsigned long)p[0]|((unsigned long)p[1]<<8)|((unsigned long)p[2]<<16)|((unsigned long)p[3]<<24);}
/* Binary search of the sorted table: the picture's SHA-256 for key, and where it is: AWL2 rows
 * (key, source, offset, size, SHA-256) point into the pack gfx/icons.awp; AWL1 rows (key, source,
 * SHA-256) name gfx/icon/<sha16>.awi (the first v0.0.42-dev1 layout, still read). */
static int icon_digest(const char *key,byte digest[32],long *offset,int *length){
    FILE *f=NULL;byte head[8],row[ICON_ROW];int size,lo=0,hi,mid,cmp,packed;long base;
    size=COM_FOpenFile("gfx/icons.awl",&f);if(!f)return 0;base=ftell(f);
    if(size<8 || fread(head,1,8,f)!=8 || (memcmp(head,"AWL1",4) && memcmp(head,"AWL2",4)))goto bad;
    packed=head[3]=='2';
    hi=(int)icon_u32(head+4);if(hi<1 || hi>65536 || size!=8+hi*ICON_ROW)goto bad;
    hi--;
    while(lo<=hi){
        mid=lo+(hi-lo)/2;
        if(fseek(f,base+8+(long)mid*ICON_ROW,SEEK_SET) || fread(row,1,ICON_ROW,f)!=ICON_ROW || !memchr(row,0,64))goto bad;
        cmp=icon_compare((char *)row,key);
        if(cmp<0)lo=mid+1;else if(cmp>0)hi=mid-1;else{
            memcpy(digest,row+128,32);
            *offset=packed?(long)icon_u32(row+120):-1;*length=packed?(int)icon_u32(row+124):0;
            fclose(f);return 1;
        }
    }
 bad: fclose(f);return 0;
}
/* One picture into a caller's buffer (at most maxw x maxh); 1 when loaded. */
static int picture_load(const char *key,int *w_out,int *h_out,byte *pixels,int maxw,int maxh){
    static const char hex[]="0123456789abcdef";
    char path[40];byte digest[32],head[8];FILE *f=NULL;int i,size,w,h,ok=0,length;long offset,base;
    aw_icon_stats.lookups++;
    if(!icon_digest(key,digest,&offset,&length)){aw_icon_stats.misses++;return 0;}
    if(offset>=0){
        size=COM_FOpenFile("gfx/icons.awp",&f);if(!f){aw_icon_stats.misses++;return 0;}
        base=ftell(f);
        if(offset<8 || length<8 || offset+(long)length>size || fseek(f,base+offset,SEEK_SET)){fclose(f);aw_icon_stats.misses++;return 0;}
        size=length;
    }else{
        strcpy(path,"gfx/icon/");
        for(i=0;i<8;i++){path[9+i*2]=hex[digest[i]>>4];path[10+i*2]=hex[digest[i]&15];}
        strcpy(path+25,".awi");
        size=COM_FOpenFile(path,&f);if(!f){aw_icon_stats.misses++;return 0;}
    }
    aw_icon_stats.reads++;
    if(size>=8 && fread(head,1,8,f)==8 && !memcmp(head,"AWI1",4)){
        w=head[4]|(head[5]<<8);h=head[6]|(head[7]<<8);
        if(w>0 && h>0 && w<=maxw && h<=maxh && size==8+w*h && fread(pixels,1,w*h,f)==(size_t)(w*h)){*w_out=w;*h_out=h;ok=1;}
    }
    if(!ok)aw_icon_stats.misses++;
    fclose(f);return ok;
}
int AW_StripLoad(aw_strip_t *slot,const char *key){
    if(!slot)return 0;
    if(!key || !*key || strlen(key)>=sizeof(slot->key)){slot->key[0]=0;slot->ok=0;return 0;}
    if(!strcmp(slot->key,key))return slot->ok;
    strcpy(slot->key,key);
    slot->ok=picture_load(key,&slot->w,&slot->h,slot->pixels,AW_STRIP_W,AW_STRIP_H);
    return slot->ok;
}
int AW_IconLoad(aw_icon_t *slot,const char *key){
    if(!slot)return 0;
    if(!key || !*key || strlen(key)>=sizeof(slot->key)){slot->key[0]=0;slot->ok=0;return 0;}
    if(!strcmp(slot->key,key))return slot->ok;
    strcpy(slot->key,key);
    slot->ok=picture_load(key,&slot->w,&slot->h,slot->pixels,AW_ICON_MAX,AW_ICON_MAX);
    return slot->ok;
}
void AW_IconDraw(const aw_icon_t *icon,int x,int y){
    int yy;
    if(!icon || !icon->ok || x<0 || y<0 || x+icon->w>(int)vid.width || y+icon->h>(int)vid.height)return;
    for(yy=0;yy<icon->h;yy++)memcpy(vid.buffer+(y+yy)*vid.rowbytes+x,icon->pixels+yy*icon->w,icon->w);
    aw_icon_stats.draws++;
}

/* The original HUD weapon and magic boxes, composed from the imported original
 * art (tools/prepare_icons.py; composition as OpenMW 0.51 lays the original HUD
 * out: openmw_hud.layout WeapBox/SpellBox, hud.cpp, itemwidget.cpp):
 *   hud:box   black interior in the thin menu border, beside the stat bars;
 *   the icon  over the interior: the equipped weapon (enchanted ones on the
 *             magic backdrop, baked in), or the hand-to-hand icon when unarmed;
 *             the selected magic item, or nothing (no spell list exists yet);
 *   hud:bar   the small bar under the box; its track (menu_bar_gray tinted by
 *             Morrowind.ini's fill colour) filled by weapon condition (empty for
 *             fists, OpenMW unsetSelectedWeapon) or the item's charge (empty with
 *             no selection, unsetSelectedSpell).
 * Sizes scale the original's by 24/42 (our three stat bars are 24 pixels tall,
 * the original's 42): box 20x20, bar 20x4. Slots reload only on a key change. */
#define HUD_BOX 20
#define HUD_BAR 4
static cvar_t hud_icons={"aw_hud_icons","1",true};
enum {SLOT_BOX,SLOT_BAR,SLOT_TRACK_WEAPON,SLOT_TRACK_MAGIC,SLOT_WEAPON,SLOT_MAGIC,SLOTS};
static aw_icon_t hud_slot[SLOTS];
static int hud_frame(int x,int y) {
    if(!AW_IconLoad(&hud_slot[SLOT_BOX],"hud:box") || !AW_IconLoad(&hud_slot[SLOT_BAR],"hud:bar") ||
       hud_slot[SLOT_BOX].w!=HUD_BOX || hud_slot[SLOT_BOX].h!=HUD_BOX ||
       hud_slot[SLOT_BAR].w!=HUD_BOX || hud_slot[SLOT_BAR].h!=HUD_BAR)return 0;
    AW_IconDraw(&hud_slot[SLOT_BOX],x,y);AW_IconDraw(&hud_slot[SLOT_BAR],x,y+HUD_BOX);
    return 1;
}
static void hud_track(int slot,const char *key,int x,int y,float fraction) {
    aw_icon_t *t=&hud_slot[slot];int fill,yy;
    if(!(fraction>0) || !AW_IconLoad(t,key) || t->w!=HUD_BOX-2 || t->h!=HUD_BAR-2)return;
    if(fraction>1)fraction=1;
    fill=(int)(t->w*fraction+.5f);if(fill<1)fill=1;
    if(x<0 || y<0 || x+fill>(int)vid.width || y+t->h>(int)vid.height)return;
    for(yy=0;yy<t->h;yy++)memcpy(vid.buffer+(y+yy)*vid.rowbytes+x,t->pixels+yy*t->w,fill);
}
static void hud_icon(int slot,const char *key,int x,int y) {
    aw_icon_t *t=&hud_slot[slot];
    if(AW_IconLoad(t,key) && t->w==HUD_BOX-2 && t->h==HUD_BOX-2)AW_IconDraw(t,x,y);
}
static int hud_original_boxes(int y,int boxes) {
    aw_inventory_item_t item;char key[72];int x;
    if((int)vid.width<140 || y<0 || y+HUD_BOX+HUD_BAR>(int)vid.height)return 1;
    if(boxes&AW_HUD_WEAPON){
        int armed=AW_InventoryEquippedItem(AW_SLOT_RIGHT,&item) && item.category==AW_INV_WEAPON;
        x=85;if(!hud_frame(x,y))return 0;
        if(armed)sprintf(key,"item:%s",item.id);else strcpy(key,"skill:26");
        hud_icon(SLOT_WEAPON,key,x+1,y+1);
        if(armed)hud_track(SLOT_TRACK_WEAPON,"hud:track:weapon",x+1,y+HUD_BOX+1,item.health>0?AW_InventoryCondition(item.id):1);
    }
    if(boxes&AW_HUD_MAGIC){
        x=107;if(!hud_frame(x,y))return 0;
        if(AW_MagicSelectedItem(&item)){
            sprintf(key,"item:%s",item.id);hud_icon(SLOT_MAGIC,key,x+1,y+1);
            hud_track(SLOT_TRACK_MAGIC,"hud:track:magic",x+1,y+HUD_BOX+1,AW_MagicCharge(&aw_state,&item)/item.charge_max);
        }
    }
    return 1;
}
/* Both methods are timed here, so aw_icons reports a same-session A/B of
 * the per-frame cost (aw_hud_icons 1 vs 0). */
static int hud_item_boxes(int y,int boxes) {
    double t0=Sys_FloatTime();int method=hud_icons.value!=0;
    /* No imported HUD art in this image: the interim marks, never a blank HUD. */
    if(!method || !hud_original_boxes(y,boxes))AW_UIHudPlaceholders(y,boxes);
    aw_icon_stats.seconds[method]+=Sys_FloatTime()-t0;aw_icon_stats.frames[method]++;
    return 1;
}
void AW_IconStats(void) {
    int k;
    Con_Printf("Icons: %u table lookups, %u picture reads, %u missing, %u draws; HUD slots %d bytes resident.\n",
        aw_icon_stats.lookups,aw_icon_stats.reads,aw_icon_stats.misses,aw_icon_stats.draws,(int)sizeof(hud_slot));
    for(k=0;k<2;k++)if(aw_icon_stats.frames[k])
        Con_Printf("HUD boxes, %s: %u frames, %d microseconds per frame.\n",k?"original icons":"placeholders",
            aw_icon_stats.frames[k],(int)(aw_icon_stats.seconds[k]*1e6/aw_icon_stats.frames[k]));
}
/* aw_magic: show the selection; aw_magic select ID | none; DIAGNOSTIC aw_magic charge ID POINTS;
 * aw_magic stats: the HUD icon counters and per-frame cost (aw_icons.c).
 * The original selects magic items in the magic menu, which AmiWind does not have yet. */
void AW_MagicCommand(void){
    aw_inventory_item_t item;
    if(cmd_source!=src_command || !sv.active || svs.maxclients!=1){Con_Printf("aw_magic: single-player game only.\n");return;}
    if(Cmd_Argc()==1){
        if(AW_MagicSelectedItem(&item))
            Con_Printf("Selected magic item: %s (%s), charge %.1f of %.0f.\n",item.name,item.id,AW_MagicCharge(&aw_state,&item),item.charge_max);
        else Con_Printf("No magic item selected (no spell list yet).\n");
        return;
    }
    if(Cmd_Argc()==2 && !Q_strcasecmp(Cmd_Argv(1),"stats")){AW_IconStats();return;}
    if(Cmd_Argc()==2 && !Q_strcasecmp(Cmd_Argv(1),"none")){AW_MagicClear(&aw_state);Con_Printf("Magic selection cleared.\n");return;}
    if(Cmd_Argc()==3 && !Q_strcasecmp(Cmd_Argv(1),"select")){
        if(AW_InventoryRead(Cmd_Argv(2),&item) && AW_MagicSelect(&aw_state,&item))Con_Printf("Selected magic item: %s.\n",item.name);
        else Con_Printf("Cannot select that: not an owned Cast Once / Cast When Used item.\n");
        return;
    }
    if(Cmd_Argc()==4 && !Q_strcasecmp(Cmd_Argv(1),"charge")){
        if(AW_InventoryRead(Cmd_Argv(2),&item) && AW_MagicSetCharge(&aw_state,&item,(float)Q_atof(Cmd_Argv(3))))
            Con_Printf("DIAGNOSTIC magic charge: %s now %.1f of %.0f.\n",item.id,AW_MagicCharge(&aw_state,&item),item.charge_max);
        else Con_Printf("Diagnostic magic charge refused.\n");
        return;
    }
    Con_Printf("aw_magic [select ID | none | charge ID POINTS | stats]\n");
}
/* The original window title bar (UI-WINDOW-TITLE-BAR-42; openmw_windows.skin.xml MW_Caption and
 * HB_ALL, components/widgets/windowcaption.cpp WindowCaption::align): a head block on each side,
 * the title between them on the window's black, the gap = the title's width + 24 (scaled 12/20:
 * + 14). Each block is its left edge, the tiled strip and its right edge. 12 pixels tall. */
static aw_strip_t title_strip;
static aw_icon_t title_edge[2];
static void title_block(int x,int y,int w){
    const aw_strip_t *s=&title_strip;int yy,xx,n;byte *row;
    if(w<3)return;
    for(yy=0;yy<s->h;yy++){
        row=vid.buffer+(y+yy)*vid.rowbytes;
        row[x]=title_edge[0].pixels[yy];row[x+w-1]=title_edge[1].pixels[yy];
        for(xx=1;xx<w-1;xx+=n){n=w-1-xx;if(n>s->w)n=s->w;memcpy(row+x+xx,s->pixels+yy*s->w,n);}
    }
}
static int title_bar(int x,int y,int w,const char *title){
    int plaque,side;
    if(!hud_icons.value || !AW_StripLoad(&title_strip,"ui:head:block") || !AW_IconLoad(&title_edge[0],"ui:head:left") ||
       !AW_IconLoad(&title_edge[1],"ui:head:right") || title_strip.h!=12 || title_edge[0].w!=1 || title_edge[1].w!=1 ||
       title_edge[0].h!=12 || title_edge[1].h!=12)return 0;
    if(x<0 || y<0 || x+w>(int)vid.width || y+12>(int)vid.height)return 0;
    plaque=AW_UIWidth(title)+14;if(plaque>w-6)plaque=w-6;
    side=(w-plaque)/2;
    title_block(x,y,side);title_block(x+side+plaque,y,w-side-plaque);
    AW_UIFill(x+side,y,plaque,12,AW_UIColor(0,0,0));
    AW_UITextCentred(x+side,y,plaque,12,title,AW_UIColor(223,199,144));
    return 1;
}
/* GMST sSkillHandtohand from gfx/hud-settings.txt (tools/prepare_icons.py), read once. */
static const char *hand_to_hand_name(void){
    static char name[64];static int loaded;FILE *f=NULL;char text[256],*p;int n,i;
    if(loaded)return name[0]?name:NULL;
    loaded=1;n=COM_FOpenFile("gfx/hud-settings.txt",&f);if(!f)return NULL;
    if(n>0 && n<(int)sizeof(text) && fread(text,1,n,f)==(size_t)n){
        text[n]=0;
        if((p=strstr(text,"sSkillHandtohand "))){
            p+=17;for(i=0;i<63 && p[i] && p[i]!='\n' && p[i]!='\r';i++)name[i]=p[i];
            name[i]=0;
        }
    }
    fclose(f);return name[0]?name:NULL;
}
/* Inventory rows (UI-ICONS-INVENTORY-42): the item's own 16 x 16 icon from the table, on the
 * equipped backdrop when equipped (original item widget Equip state); one slot per visible row,
 * reloaded only when that row's item or state changes. 0 = no picture (the caller's old method). */
static aw_icon_t row_slot[8];
static int inventory_row_icon(int slot,const char *id,int equipped,int x,int y){
    char key[80];aw_icon_t *t;
    if(!hud_icons.value || slot<0 || slot>=8 || !id || strlen(id)>60)return 0;
    t=&row_slot[slot];
    sprintf(key,equipped?"inv:%s:equip":"inv:%s",id);
    if(!AW_IconLoad(t,key) && equipped){sprintf(key,"inv:%s",id);if(!AW_IconLoad(t,key))return 0;}
    else if(!t->ok)return 0;
    if(t->w!=16 || t->h!=16)return 0;
    AW_IconDraw(t,x,y);return 1;
}
void AW_IconsInit(void) {
    Cvar_RegisterVariable(&hud_icons);Cmd_AddCommand("aw_magic",AW_MagicCommand);aw_hud_item_boxes=hud_item_boxes;aw_title_bar=title_bar;aw_hand_to_hand_name=hand_to_hand_name;aw_inventory_row_icon=inventory_row_icon;
}
