/* SPDX-License-Identifier: GPL-3.0-only
 * The UI icon table and the HUD weapon/magic boxes (aw_icons.c), with synthetic
 * pictures only: lookup, one load per key change, composition and bars. */
#include "quakedef.h"
#include "aw_icons.h"
#include "aw_inventory.h"
#include "aw_story.h"
#include <assert.h>
viddef_t vid;
aw_state_t aw_state;
int (*aw_hud_item_boxes)(int y,int channels);
static byte screen[200][320];
static int opens,placeholders,armed,selected;
static float condition=.5f,charge=5;
static const char *keys[]={"hud:bar","hud:box","hud:track:magic","hud:track:weapon","item:steel longsword","item:test_ring","skill:26"};
static const int sizes[][3]={{20,4,11},{20,20,12},{18,2,13},{18,2,14},{18,18,15},{18,18,16},{18,18,17}};
#define ROWS 7
static FILE *memory(const byte *p,int n,FILE **out){FILE *f=tmpfile();assert(f);assert(fwrite(p,1,n,f)==(size_t)n);fseek(f,0,SEEK_SET);*out=f;return f;}
int COM_FOpenFile(char *path,FILE **out){
    static byte buf[8+ROWS*160],pic[8+32*32];int i;
    opens++;*out=NULL;
    if(!strcmp(path,"gfx/icons.awl")){
        memset(buf,0,sizeof(buf));memcpy(buf,"AWL1",4);buf[4]=ROWS;
        for(i=0;i<ROWS;i++){strcpy((char *)buf+8+i*160,keys[i]);memset(buf+8+i*160+128,sizes[i][2],32);}
        memory(buf,sizeof(buf),out);return sizeof(buf);
    }
    for(i=0;i<ROWS;i++){
        char want[40];sprintf(want,"gfx/icon/%02x%02x%02x%02x%02x%02x%02x%02x.awi",sizes[i][2],sizes[i][2],sizes[i][2],
            sizes[i][2],sizes[i][2],sizes[i][2],sizes[i][2],sizes[i][2]);
        if(!strcmp(path,want)){
            int n=sizes[i][0]*sizes[i][1];memcpy(pic,"AWI1",4);pic[4]=sizes[i][0];pic[5]=0;pic[6]=sizes[i][1];pic[7]=0;
            memset(pic+8,sizes[i][2],n);memory(pic,8+n,out);return 8+n;
        }
    }
    return -1;
}
double Sys_FloatTime(void){static double t;return t+=.001;}
static cvar_t *icons_cvar;
void Cvar_RegisterVariable(cvar_t *v){v->value=atof(v->string);if(!strcmp(v->name,"aw_hud_icons"))icons_cvar=v;}
static void (*magic_cmd)(void);
void Cmd_AddCommand(char *name,xcommand_t f){if(!strcmp(name,"aw_magic"))magic_cmd=f;}
void Con_Printf(char *fmt,...){(void)fmt;}
int AW_UIColor(int r,int g,int b){return (r+g+b)&255;}
cmd_source_t cmd_source=src_command;server_t sv;server_static_t svs;
static int argc_value;static char *argv_value[4];
int Cmd_Argc(void){return argc_value;}
char *Cmd_Argv(int i){return i<argc_value?argv_value[i]:"";}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
float Q_atof(char *s){return (float)atof(s);}
int AW_InventoryRead(const char *id,aw_inventory_item_t *out){(void)id;(void)out;return 0;}
int AW_MagicSelect(aw_state_t *s,const aw_inventory_item_t *i){(void)s;(void)i;return 0;}
void AW_MagicClear(aw_state_t *s){(void)s;}
int AW_MagicSetCharge(aw_state_t *s,const aw_inventory_item_t *i,float v){(void)s;(void)i;(void)v;return 0;}
void AW_UIHudPlaceholders(int y,int channels){(void)y;(void)channels;placeholders++;}
int AW_InventoryEquippedItem(int slot,aw_inventory_item_t *out){
    if(!armed || slot!=AW_SLOT_RIGHT)return 0;
    memset(out,0,sizeof(*out));strcpy(out->id,"steel longsword");out->category=AW_INV_WEAPON;out->health=900;return 1;
}
float AW_InventoryCondition(const char *id){(void)id;return condition;}
int AW_MagicSelectedItem(aw_inventory_item_t *out){
    if(!selected)return 0;
    memset(out,0,sizeof(*out));strcpy(out->id,"test_ring");out->enchant_kind=AW_ENCH_USED;out->charge_max=20;return 1;
}
float AW_MagicCharge(const aw_state_t *s,const aw_inventory_item_t *item){(void)s;(void)item;return charge;}
static int count(int x,int y,int w,int h,int c){int n=0,i,j;for(j=y;j<y+h;j++)for(i=x;i<x+w;i++)n+=screen[j][i]==c;return n;}
int main(void){
    int y=174,i,reads;
    vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=&screen[0][0];
    AW_IconsInit();assert(aw_hud_item_boxes && magic_cmd);AW_IconStats();
    /* Unarmed, nothing selected: box + bar frames, the hand-to-hand icon, empty bars. */
    assert(aw_hud_item_boxes(y,AW_HUD_ALL));
    assert(count(85,y,20,20,12)==20*20-18*18 && count(86,y+1,18,18,17)==18*18);
    assert(count(85,y+20,20,4,11)==20*4 && count(86,y+21,18,2,14)==0);
    assert(count(107,y,20,20,12)==20*20 && count(107,y+20,20,4,11)==20*4);
    assert(!placeholders);
    /* Armed: the record's icon and condition 0.5 of the 18-pixel track. */
    memset(screen,0,sizeof(screen));armed=1;assert(aw_hud_item_boxes(y,AW_HUD_ALL));
    assert(count(86,y+1,18,18,15)==18*18 && count(86,y+21,18,2,14)==9*2);
    /* Selected magic item: its icon and charge 5/20 (round(4.5) = 5 pixels). */
    memset(screen,0,sizeof(screen));selected=1;assert(aw_hud_item_boxes(y,AW_HUD_ALL));
    assert(count(108,y+1,18,18,16)==18*18 && count(108,y+21,18,2,13)==5*2);
    /* Same state for 32 frames: no further table or picture reads. */
    reads=opens;for(i=0;i<32;i++)assert(aw_hud_item_boxes(y,AW_HUD_ALL));
    assert(opens==reads && aw_icon_stats.misses==0);
    /* A channel the story has not opened is not drawn. */
    memset(screen,0,sizeof(screen));assert(aw_hud_item_boxes(y,AW_HUD_WEAPON));assert(count(107,y,20,24,0)==20*24);
    /* Full charge fills the track; zero leaves it empty. */
    memset(screen,0,sizeof(screen));charge=20;assert(aw_hud_item_boxes(y,AW_HUD_ALL));assert(count(108,y+21,18,2,13)==36);
    memset(screen,0,sizeof(screen));charge=0;assert(aw_hud_item_boxes(y,AW_HUD_ALL));assert(count(108,y+21,18,2,13)==0);
    /* An unknown key fails once and is not looked up again every frame. */
    {aw_icon_t slot;memset(&slot,0,sizeof(slot));assert(!AW_IconLoad(&slot,"item:none"));reads=opens;
     assert(!AW_IconLoad(&slot,"item:none"));assert(opens==reads);}
    /* aw_magic stats reaches the counters; single-player only. */
    argc_value=2;argv_value[0]="aw_magic";argv_value[1]="stats";sv.active=1;svs.maxclients=1;magic_cmd();
    /* aw_hud_icons 0: the interim marks (the old method stays selectable). */
    assert(icons_cvar && icons_cvar->value==1);icons_cvar->value=0;
    assert(aw_hud_item_boxes(y,AW_HUD_ALL) && placeholders==1);
    return 0;
}
