/* SPDX-License-Identifier: GPL-3.0-only
 * CONTAINER-STRIP-TAKE-STALL-59: the real strip (aw_cstrip.c) over the real focus table, item table and world change
 * list, opened both ways: E on the aimed container (AW_InventoryUse) and the console (aw_placed container REF open,
 * AW_ContainerCommand). Both reach the same open with the same container, owner and contents; takes, a put, Take All
 * and Esc then behave the same. The container's data is read once when the strip opens and never again while it is
 * open (before, every take read focus.awf five more times and could hold the frame for seconds on a busy disk); it is
 * released on close. The whole screen is copied out only for a few frames after a change
 * (CONTAINER-STRIP-REDRAW-COST-59). */
#include "quakedef.h"
#include "aw_inventory.h"
#include "aw_ledger.h"
#include "aw_cstrip.h"
#include "aw_icons.h"
#include <assert.h>
#include <stdarg.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
static client_t client;
static edict_t entities[8];
static model_t world,world2;
char *pr_strings;
static char strings[16];
static byte focus_file[8+12+96+28+60+36],item_file[8+2*512];
static const char hud_text[]="iMaxActivateDist 192\nsWeight Weight\nsValue Value\nsTake Take\n";
#define CHEST 500u
static int notices,focus_opens;
/* CONTAINER-STRIP-OPEN-MANY-KINDS-61: the item table with MANY more kinds (misc_k00.. between the inkwell and the
 * quill, in the file's order), served instead of item_file while many_items is set */
#define MANY 40
static byte many_file[8+(MANY+2)*512];static int many_items,item_search_opens,item_pass_opens;
/* the engine pieces the strip and the take reach */
keydest_t key_dest;viddef_t vid;refdef_t r_refdef;int scr_copyeverything;
int (*aw_cstrip_mouse)(int dx,int dy);int (*aw_cstrip_key)(int key);void (*aw_cstrip_draw)(void);int (*aw_cstrip_open_now)(void);
static char console[256];
void Con_Printf(char *format,...){va_list a;va_start(a,format);vsnprintf(console,sizeof(console),format,a);va_end(a);}
void Con_DPrintf(char *format,...){(void)format;}
char *va(char *format,...){static char s[64];va_list a;va_start(a,format);vsnprintf(s,sizeof(s),format,a);va_end(a);return s;}
double Sys_FloatTime(void){return 0;}
void CDAudio_Update(void){}
void S_ExtraUpdate(void){}
edict_t *EDICT_NUM(int i){assert(i>=0 && i<8);return &entities[i];}
eval_t *GetEdictFieldValue(edict_t *e,char *field){(void)e;(void)field;return NULL;}
void *AW_TryMalloc(int size){return calloc(1,size);}
static int serve(const void *data,int size,FILE **file){
    *file=tmpfile();assert(*file);assert(fwrite(data,1,size,*file)==(size_t)size);rewind(*file);return size;
}
/* TRADEHOUSE-LONG-FRAME-59: the binary searches open their file with a small buffer (aw_fopenbuf.c), every other open
 * with the default; the setting never outlives the open */
extern int com_fopen_buffer;
static int focus_small_opens;
int COM_FOpenFile(char *name,FILE **file){
    *file=NULL;
    if(!strcmp(name,"focus.awf")){
        assert(com_fopen_buffer==0 || com_fopen_buffer==256);
        focus_small_opens+=com_fopen_buffer==256;
        focus_opens++;return serve(focus_file,sizeof(focus_file),file);
    }
    /* the searches open it small (512); the one pass over it for many kinds (AW_InventoryCarried) with the default */
    if(!strcmp(name,"inventory/items.awi")){
        assert(com_fopen_buffer==512 || com_fopen_buffer==0);
        if(com_fopen_buffer==512)item_search_opens++;else item_pass_opens++;
        return many_items?serve(many_file,sizeof(many_file),file):serve(item_file,sizeof(item_file),file);
    }
    assert(com_fopen_buffer==0);
    if(!strcmp(name,"gfx/hud-settings.txt"))return serve(hud_text,sizeof(hud_text)-1,file);
    return -1;
}
int AW_WorldToSource(const char *name,const float *local,float *out){(void)name;(void)local;(void)out;return 0;}
int AW_SourceToWorld(const char *name,const float *in,float *local){(void)name;(void)in;(void)local;return 0;}
void AW_MwscriptRoomShift(float shift[3]){shift[0]=shift[1]=shift[2]=0;}
int AW_ObjectDisabled(unsigned reference){(void)reference;return 0;}
int AW_ObjectTake(unsigned reference,int stolen){(void)reference;(void)stolen;assert(0);return 0;}
int AW_ObjectLockLevel(unsigned reference,int original){(void)reference;return original;}
int ChimRoom_Has(unsigned reference){(void)reference;return 0;}
void AW_UIPickupNotice(const char *name,double duration){(void)name;(void)duration;notices++;}
void AW_UISubtitle(const char *speaker,const char *text,double duration){(void)speaker;(void)text;(void)duration;}
void AW_CombatEquipmentChanged(void){}
void IN_AWClearButtons(void){}
int AW_UIColor(int r,int g,int b){return (r+g+b)&255;}
void AW_UIBox(int x,int y,int w,int h){(void)x;(void)y;(void)w;(void)h;}
void AW_UIFill(int x,int y,int w,int h,int c){(void)x;(void)y;(void)w;(void)h;(void)c;}
void AW_UISmallBegin(void){}
void AW_UISmallEnd(void){}
void AW_UIText(int x,int y,const char *s,int c){(void)x;(void)y;(void)s;(void)c;}
void AW_UITextBox(int x,int y,int w,int h,const char *s,int c){(void)x;(void)y;(void)w;(void)h;(void)s;(void)c;}
int AW_UIWidth(const char *s){return (int)strlen(s)*6;}
/* LOOT-WINDOW-LAYOUT-60: the name, properties and key lines in the console font; every character drawn inside the
 * screen (and the strip's frame), none past it */
static int console_chars,console_red;
int AW_ConsoleCharWidth(void){return 8;}
int AW_ConsoleCharHeight(void){return 8;}
void AW_ConsoleCharacter(int x,int y,int c){(void)c;assert(x>=0 && x+8<=(int)vid.width && y>=0 && y+8<=(int)vid.height-4);console_chars++;}
void AW_ConsoleCharacterRed(int x,int y,int c,int red){AW_ConsoleCharacter(x,y,c);(void)red;console_red++;}
int AW_UICursor(int x,int y){(void)x;(void)y;return 1;}
int AW_IconLoad(aw_icon_t *slot,const char *key){(void)slot;(void)key;return 0;}
void AW_IconDraw(const aw_icon_t *icon,int x,int y){(void)icon;(void)x;(void)y;}
int AW_SceneNameLabelsAmiWind(void){return 1;}
void AW_UIButton(int x,int y,int w,int h,const char *text,int lit,int colour){(void)x;(void)y;(void)w;(void)h;(void)text;(void)lit;(void)colour;}
int AW_IconLoadItem(aw_icon_t *slot,const char *id){(void)slot;(void)id;return 0;}
void AW_IconDrawFit(const aw_icon_t *icon,int x,int y,int slot_w,int slot_h,int colour){(void)icon;(void)x;(void)y;(void)slot_w;(void)slot_h;(void)colour;}
void ED_Free(edict_t *e){(void)e;assert(0);}
edict_t *ED_Alloc(void){assert(0);return NULL;}
char *ED_NewString(char *s){(void)s;assert(0);return NULL;}
void SV_LinkEdict(edict_t *e,qboolean triggers){(void)e;(void)triggers;assert(0);}
model_t *Mod_ForName(char *name,qboolean crash){(void)name;(void)crash;assert(0);return NULL;}
void *Cache_Check(cache_user_t *c){(void)c;assert(0);return NULL;}
int SV_PointContents(vec3_t p){(void)p;assert(0);return 0;}
trace_t SV_Move(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,int type,edict_t *pass){
    trace_t tr;(void)start;(void)mins;(void)maxs;(void)type;(void)pass;
    memset(&tr,0,sizeof(tr));tr.fraction=1;VectorCopy(end,tr.endpos);return tr;
}
/* the console's arguments */
static int argc;static char *argv[8];
int Cmd_Argc(void){return argc;}
char *Cmd_Argv(int i){return i<argc?argv[i]:"";}
static void put32(byte *p,unsigned long v){p[0]=(byte)v;p[1]=(byte)(v>>8);p[2]=(byte)(v>>16);p[3]=(byte)(v>>24);}
/* One room (cell 763), one owned container: "Basket" 20 map units ahead of the eye, owner arrille, holding 3 misc_quill
 * and 2 misc_inkwell; the item table knows both. */
static void tables(void){
    byte *row=focus_file+8+12,*t,*it;
    memset(focus_file,0,sizeof(focus_file));memset(item_file,0,sizeof(item_file));
    memcpy(focus_file,"AWF3",4);put32(focus_file+4,1);
    put32(focus_file+8,763);put32(focus_file+12,0);put32(focus_file+16,1);
    row[0]='C';row[1]=1;row[2]=1|4;row[3]=0;put32(row+4,CHEST);
    put32(row+8,80);put32(row+12,0);put32(row+16,116);memcpy(row+28,"Basket",6);
    t=row+96;memcpy(t,"AWO1",4);put32(t+4,1);put32(t+8,CHEST);put32(t+16,8);memcpy(t+20,"arrille",8);
    t+=28;memcpy(t,"AWC1",4);put32(t+4,1);put32(t+8,CHEST);put32(t+12,0);t[16]=2;t[17]=0;t[18]=t[19]=0;
    put32(t+20,2);memcpy(t+24,"misc_inkwell",12);put32(t+24+32,2);memcpy(t+60,"misc_quill",10);put32(t+60+32,3);
    memcpy(item_file,"AWI2",4);put32(item_file+4,2);
    it=item_file+8;memcpy(it,"misc_inkwell",12);memcpy(it+64,"Inkwell",7);put32(it+160,AW_INV_MISC);put32(it+168,1);
    it+=512;memcpy(it,"misc_quill",10);memcpy(it+64,"Quill Pen",9);put32(it+160,AW_INV_MISC);put32(it+168,1);
}
static void level(void){
    static model_t *next;
    memset(&sv,0,sizeof(sv));memset(&svs,0,sizeof(svs));memset(entities,0,sizeof(entities));
    pr_strings=strings;sv.active=1;sv.num_edicts=2;strcpy(sv.name,"seyda_arrille");svs.maxclients=1;svs.clients=&client;
    client.edict=&entities[1];entities[1].v.movetype=MOVETYPE_WALK;entities[1].v.origin[2]=16;entities[1].v.view_ofs[2]=13;
    next=next==&world?&world2:&world;
    world.entities=world2.entities="{\n\"classname\" \"worldspawn\"\n\"_aw_cell_int\" \"763\"\n}\n";
    sv.worldmodel=next;cls.state=ca_connected;key_dest=key_game;notices=0;
}
static void console_open(void){
    static char a0[]="aw_placed",a1[]="container",a2[]="500",a3[]="open";
    argc=4;argv[0]=a0;argv[1]=a1;argv[2]=a2;argv[3]=a3;
    AW_ContainerCommand();
}
/* One run: open (E or the console), take 2 quills, put 1 back, Take All, Esc. Returns the ledger's stolen quills. */
static void run(int by_console){
    unsigned long reads;int frames;
    AW_LedgerClear(&aw_ledger);AW_StateReset();tables();level();
    vid.width=320;vid.height=200;r_refdef.vrect.width=320;r_refdef.vrect.height=200;
    assert(!AW_CStripActive());
    if(by_console)console_open();else assert(AW_InventoryUse());
    assert(AW_CStripActive());
    assert(aw_cstrip_open_now && aw_cstrip_open_now());
    reads=AW_ContainerFileReads();
    /* LOOT-WINDOW-LAYOUT-60 / -ITEM-PROPERTIES-60: the owned basket's selected entry in red, its properties and the
     * key help in the console font, all inside the screen (the stubs check every character) */
    console_chars=console_red=0;aw_cstrip_draw();assert(console_red>0 && console_chars>console_red);
    /* a take: the selected entry is the first (misc_inkwell); move to the quill, take one, then one more */
    assert(aw_cstrip_key('d') && aw_cstrip_key('e') && aw_cstrip_key('e'));
    assert(AW_StateGet(&aw_state,AW_ITEM,"misc_quill")==2 && AW_ContainerCount(CHEST,"misc_quill")==1);
    assert(AW_LedgerStolenCount(&aw_ledger,"misc_quill","arrille",0)==2 && notices==2);
    /* the other side, put one back: no stolen pair added */
    assert(aw_cstrip_key(K_TAB) && aw_cstrip_key('e'));
    assert(AW_StateGet(&aw_state,AW_ITEM,"misc_quill")==1 && AW_ContainerCount(CHEST,"misc_quill")==2);
    /* back, Take All: both kinds */
    assert(aw_cstrip_key(K_TAB) && aw_cstrip_key('t'));
    assert(AW_StateGet(&aw_state,AW_ITEM,"misc_quill")==3 && AW_StateGet(&aw_state,AW_ITEM,"misc_inkwell")==2);
    assert(AW_ContainerCount(CHEST,"misc_quill")==0 && AW_LedgerStolenCount(&aw_ledger,"misc_inkwell","arrille",0)==2);
    /* none of that read the container's data again */
    assert(AW_ContainerFileReads()==reads);
    /* redraw: a few frames copy the whole screen after a change, then only the view */
    console_chars=console_red=0;
    for(frames=0;frames<10;frames++){scr_copyeverything=0;aw_cstrip_draw();if(!scr_copyeverything)break;}
    assert(console_chars>0);   /* the emptied side's line and the key help, in the console font */
    assert(frames>0 && frames<=3 && !AW_CStripDirty());
    scr_copyeverything=0;aw_cstrip_draw();assert(!scr_copyeverything);
    assert(aw_cstrip_key('a') && AW_CStripDirty());
    /* Esc closes and releases the held data: a count now reads the file again */
    assert(aw_cstrip_key(K_ESCAPE) && !AW_CStripActive());
    reads=AW_ContainerFileReads();
    assert(AW_ContainerCount(CHEST,"misc_quill")==0 && AW_ContainerFileReads()==reads+1);
    /* the contents stay on the world change list: a new map reads the data again with the deltas */
    level();assert(AW_ContainerCount(CHEST,"misc_quill")==0 && AW_ContainerCount(CHEST,"misc_inkwell")==0);
}
/* CONTAINER-STRIP-OPEN-MANY-KINDS-61: with MANY kinds carried the strip names its inventory side from one pass over the
 * item file (as the inventory window does), never one search per kind (415 kinds held a body's open 10.3 s on FS-UAE);
 * a take then names both sides from the open list without any read. The kinds keep the item table's order. */
static void many_kinds(void){
    byte *it;int i,searches,passes;char id[16],name[16];
    memset(many_file,0,sizeof(many_file));memcpy(many_file,"AWI2",4);put32(many_file+4,MANY+2);
    it=many_file+8;memcpy(it,"misc_inkwell",12);memcpy(it+64,"Inkwell",7);put32(it+160,AW_INV_MISC);put32(it+168,1);
    for(i=0;i<MANY;i++){
        it+=512;snprintf(id,sizeof(id),"misc_k%02d",i);snprintf(name,sizeof(name),"Kind %02d",i);
        memcpy(it,id,strlen(id));memcpy(it+64,name,strlen(name));put32(it+160,AW_INV_MISC);put32(it+168,1);
    }
    it+=512;memcpy(it,"misc_quill",10);memcpy(it+64,"Quill Pen",9);put32(it+160,AW_INV_MISC);put32(it+168,1);
    AW_LedgerClear(&aw_ledger);AW_StateReset();tables();level();many_items=1;
    vid.width=320;vid.height=200;r_refdef.vrect.width=320;r_refdef.vrect.height=200;
    /* carried in the reverse of the file's order, so the pass meets them sorted, the strip lists them as carried */
    for(i=MANY-1;i>=0;i--){snprintf(id,sizeof(id),"misc_k%02d",i);assert(AW_ItemAdd(&aw_state,id,i+1));}
    assert(AW_ItemAdd(&aw_state,"misc_ghost",1));   /* no catalogue row: left out of the strip, as before */
    searches=item_search_opens;passes=item_pass_opens;
    assert(AW_InventoryUse() && AW_CStripActive());
    assert(item_pass_opens==passes+1);        /* the one pass */
    assert(item_search_opens<=searches+1);    /* at most one small open, for the kinds the pass did not name */
    assert(aw_cstrip_key(K_TAB));
    for(i=0;i<MANY;i++){
        const aw_cstrip_entry_t *e=AW_CStripSelected(AW_CStripList());
        snprintf(id,sizeof(id),"misc_k%02d",MANY-1-i);snprintf(name,sizeof(name),"Kind %02d",MANY-1-i);
        assert(e && !strcmp(e->id,id) && !strcmp(e->name,name) && e->count==MANY-i);
        assert(aw_cstrip_key('d') || i==MANY-1);
    }
    assert(AW_CStripList()->count[AW_CSTRIP_INVENTORY]==MANY);
    /* a take from the basket: both sides named again from the open list, no second pass (the take's own record read
     * and the uncatalogued kind may search) */
    assert(aw_cstrip_key(K_TAB) && aw_cstrip_key('e'));
    assert(AW_CStripList()->count[AW_CSTRIP_INVENTORY]==MANY+1);
    assert(item_pass_opens==passes+1);
    {const aw_cstrip_list_t *l=AW_CStripList();assert(!strcmp(l->row[AW_CSTRIP_INVENTORY][MANY].name,"Inkwell"));
     assert(!strcmp(l->row[AW_CSTRIP_INVENTORY][0].name,"Kind 39"));}
    assert(aw_cstrip_key(K_ESCAPE) && !AW_CStripActive());
    many_items=0;AW_LedgerClear(&aw_ledger);
}
int main(void){
    aw_ledger_on=1;
    AW_CStripInit();
    run(0);     /* E on the aimed basket */
    run(1);     /* aw_placed container 500 open */
    many_kinds();
    /* TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61: the 'F' effect links name the frame map file's stem with the builder's
     * hash (tools/prepare_area_tables.py name_hash: 0x60c9ec7e for "vivec_city-chim"); the town's server name
     * ("vivec_city", 0x9ae85e08) is another map and must not match */
    assert(AW_AreaMapHash("maps/vivec_city-chim.chim")==0x60c9ec7eUL);
    assert(AW_AreaMapHash("maps/Vivec_City-CHIM.chim")==0x60c9ec7eUL && AW_AreaMapHash("vivec_city-chim")==0x60c9ec7eUL);
    assert(AW_AreaMapHash("maps/seyda-chim.chim")==0x57049ac7UL && AW_AreaMapHash("maps/vivec_city-chim.chim")!=0x9ae85e08UL);
    assert(!AW_AreaMapHash("") && !AW_AreaMapHash(NULL));
    /* the console's open with a strip already open: refused, the open one kept */
    tables();level();assert(AW_InventoryUse() && AW_CStripActive());
    console_open();assert(strstr(console,"does not open here") && AW_CStripActive());
    /* a strip open across a new map is closed by the next frame's draw (its held data released with the place) */
    level();sv.active=0;aw_cstrip_draw();assert(!AW_CStripActive());
    AW_LedgerClear(&aw_ledger);
    assert(focus_small_opens>=2 && com_fopen_buffer==0);   /* the held contents and owner were searched small */
    puts("aga_container_strip_open_test ok");
    return 0;
}
