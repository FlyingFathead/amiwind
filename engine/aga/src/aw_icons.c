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
/* Binary search of the sorted table: the picture's SHA-256 for key. */
static int icon_digest(const char *key,byte digest[32]){
    FILE *f=NULL;byte head[8],row[ICON_ROW];int size,lo=0,hi,mid,cmp;long base;
    size=COM_FOpenFile("gfx/icons.awl",&f);if(!f)return 0;base=ftell(f);
    if(size<8 || fread(head,1,8,f)!=8 || memcmp(head,"AWL1",4))goto bad;
    hi=(int)icon_u32(head+4);if(hi<1 || hi>65536 || size!=8+hi*ICON_ROW)goto bad;
    hi--;
    while(lo<=hi){
        mid=lo+(hi-lo)/2;
        if(fseek(f,base+8+(long)mid*ICON_ROW,SEEK_SET) || fread(row,1,ICON_ROW,f)!=ICON_ROW || !memchr(row,0,64))goto bad;
        cmp=icon_compare((char *)row,key);
        if(cmp<0)lo=mid+1;else if(cmp>0)hi=mid-1;else{memcpy(digest,row+128,32);fclose(f);return 1;}
    }
 bad: fclose(f);return 0;
}
int AW_IconLoad(aw_icon_t *slot,const char *key){
    static const char hex[]="0123456789abcdef";
    char path[40];byte digest[32],head[8];FILE *f=NULL;int i,size,w,h;
    if(!slot)return 0;
    if(!key || !*key || strlen(key)>=sizeof(slot->key)){slot->key[0]=0;slot->ok=0;return 0;}
    if(!strcmp(slot->key,key))return slot->ok;
    strcpy(slot->key,key);slot->ok=0;aw_icon_stats.lookups++;
    if(!icon_digest(key,digest)){aw_icon_stats.misses++;return 0;}
    strcpy(path,"gfx/icon/");
    for(i=0;i<8;i++){path[9+i*2]=hex[digest[i]>>4];path[10+i*2]=hex[digest[i]&15];}
    strcpy(path+25,".awi");
    size=COM_FOpenFile(path,&f);if(!f){aw_icon_stats.misses++;return 0;}
    aw_icon_stats.reads++;
    if(size>=8 && fread(head,1,8,f)==8 && !memcmp(head,"AWI1",4)){
        w=head[4]|(head[5]<<8);h=head[6]|(head[7]<<8);
        if(w>0 && h>0 && w<=AW_ICON_MAX && h<=AW_ICON_MAX && size==8+w*h &&
           fread(slot->pixels,1,w*h,f)==(size_t)(w*h)){slot->w=w;slot->h=h;slot->ok=1;}
    }
    if(!slot->ok)aw_icon_stats.misses++;
    fclose(f);return slot->ok;
}
void AW_IconDraw(const aw_icon_t *icon,int x,int y){
    int yy;
    if(!icon || !icon->ok || x<0 || y<0 || x+icon->w>vid.width || y+icon->h>vid.height)return;
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
    if(x<0 || y<0 || x+fill>vid.width || y+t->h>vid.height)return;
    for(yy=0;yy<t->h;yy++)memcpy(vid.buffer+(y+yy)*vid.rowbytes+x,t->pixels+yy*t->w,fill);
}
static void hud_icon(int slot,const char *key,int x,int y) {
    aw_icon_t *t=&hud_slot[slot];
    if(AW_IconLoad(t,key) && t->w==HUD_BOX-2 && t->h==HUD_BOX-2)AW_IconDraw(t,x,y);
}
static int hud_original_boxes(int y,int channels) {
    aw_inventory_item_t item;char key[72];int x;
    if(vid.width<140 || y<0 || y+HUD_BOX+HUD_BAR>vid.height)return 1;
    if(channels&AW_HUD_WEAPON){
        int armed=AW_InventoryEquippedItem(AW_SLOT_RIGHT,&item) && item.category==AW_INV_WEAPON;
        x=85;if(!hud_frame(x,y))return 0;
        if(armed)sprintf(key,"item:%s",item.id);else strcpy(key,"skill:26");
        hud_icon(SLOT_WEAPON,key,x+1,y+1);
        if(armed)hud_track(SLOT_TRACK_WEAPON,"hud:track:weapon",x+1,y+HUD_BOX+1,item.health>0?AW_InventoryCondition(item.id):1);
    }
    if(channels&AW_HUD_MAGIC){
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
static int hud_item_boxes(int y,int channels) {
    double t0=Sys_FloatTime();int method=hud_icons.value!=0;
    /* No imported HUD art in this image: the interim marks, never a blank HUD. */
    if(!method || !hud_original_boxes(y,channels))AW_UIHudPlaceholders(y,channels);
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
void AW_IconsInit(void) {
    Cvar_RegisterVariable(&hud_icons);Cmd_AddCommand("aw_magic",AW_MagicCommand);aw_hud_item_boxes=hud_item_boxes;
}
