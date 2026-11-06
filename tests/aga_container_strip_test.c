/* SPDX-License-Identifier: GPL-3.0-only
 * CONTAINER-WINDOW-59: an aimed placed container through the real focus table (AWF3 with its owners and contents
 * lists), the real item table and the world change list: the prompt (Open, Steal in red when owned, Locked), the
 * focus box's lock line, E opening the strip only when unlocked (a script's Unlock through the lock hook), organic
 * containers left to the harvest, take and put through the container deltas (owned: the stolen pair), refusals that
 * change nothing; and the strip's pure rules (selection, scrolling, sides, the mouse's cell). */
#include "quakedef.h"
#include "aw_inventory.h"
#include "aw_ledger.h"
#include "aw_cstrip.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
static client_t client;
static edict_t entities[8];
static model_t world,world2;
char *pr_strings;
static char strings[16];
static byte focus_file[8+12+96+28+60],item_file[8+512];
static const char hud_text[]="iMaxActivateDist 192\nsWeight Weight\nsValue Value\nsTake Take\n";
#define CHEST 500u
static int subtitles,notices;static char last_subtitle[64];
void Con_Printf(char *format,...){(void)format;}
void CDAudio_Update(void){}
void S_ExtraUpdate(void){}
edict_t *EDICT_NUM(int i){assert(i>=0 && i<8);return &entities[i];}
eval_t *GetEdictFieldValue(edict_t *e,char *field){(void)e;(void)field;return NULL;}
void *AW_TryMalloc(int size){return calloc(1,size);}
static int serve(const void *data,int size,FILE **file){
    *file=tmpfile();assert(*file);assert(fwrite(data,1,size,*file)==(size_t)size);rewind(*file);return size;
}
int COM_FOpenFile(char *name,FILE **file){
    *file=NULL;
    if(!strcmp(name,"focus.awf"))return serve(focus_file,sizeof(focus_file),file);
    if(!strcmp(name,"inventory/items.awi"))return serve(item_file,sizeof(item_file),file);
    if(!strcmp(name,"gfx/hud-settings.txt"))return serve(hud_text,sizeof(hud_text)-1,file);
    return -1;
}
int AW_WorldToSource(const char *name,const float *local,float *out){(void)name;(void)local;(void)out;return 0;}
int AW_SourceToWorld(const char *name,const float *in,float *local){(void)name;(void)in;(void)local;return 0;}
void AW_MwscriptRoomShift(float shift[3]){shift[0]=shift[1]=shift[2]=0;}
int AW_ObjectDisabled(unsigned reference){(void)reference;return 0;}
int AW_ObjectTake(unsigned reference,int stolen){(void)reference;(void)stolen;assert(0);return 0;}
int ChimRoom_Has(unsigned reference){(void)reference;return 0;}
void AW_UIPickupNotice(const char *name,double duration){(void)name;(void)duration;notices++;}
void AW_UISubtitle(const char *speaker,const char *text,double duration){
    (void)speaker;(void)duration;subtitles++;Q_strcpy_bounded(last_subtitle,text,sizeof(last_subtitle));}
void AW_CombatEquipmentChanged(void){}
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
static void put32(byte *p,unsigned long v){p[0]=(byte)v;p[1]=(byte)(v>>8);p[2]=(byte)(v>>16);p[3]=(byte)(v>>24);}
/* One room (cell 763), one container row: "Basket" at game units (80,0,116), 20 map units ahead of the eye, owned by
 * arrille, holding 3 misc_quill; the item table knows the quill. OWNED, ACTION (1 opens, 0 organic), LOCK (byte 3). */
static void tables(int owned,int action,int lock){
    byte *row=focus_file+8+12,*t;
    memset(focus_file,0,sizeof(focus_file));memset(item_file,0,sizeof(item_file));
    memcpy(focus_file,"AWF3",4);put32(focus_file+4,1);
    put32(focus_file+8,763);put32(focus_file+12,0);put32(focus_file+16,1);
    row[0]='C';row[1]=(byte)owned;row[2]=(byte)(action|(owned?4:0));row[3]=(byte)lock;put32(row+4,CHEST);
    put32(row+8,80);put32(row+12,0);put32(row+16,116);memcpy(row+28,"Basket",6);
    t=row+96;memcpy(t,"AWO1",4);put32(t+4,1);put32(t+8,CHEST);put32(t+16,8);memcpy(t+20,"arrille",8);
    t+=28;memcpy(t,"AWC1",4);put32(t+4,1);put32(t+8,CHEST);put32(t+12,0);t[16]=1;t[17]=0;t[18]=t[19]=0;
    put32(t+20,1);memcpy(t+24,"misc_quill",10);put32(t+24+32,3);
    memcpy(item_file,"AWI2",4);put32(item_file+4,1);
    memcpy(item_file+8,"misc_quill",10);memcpy(item_file+8+64,"Quill Pen",9);put32(item_file+8+160,AW_INV_MISC);
    put32(item_file+8+168,1);
}
static void level(void){
    static model_t *next;
    memset(&sv,0,sizeof(sv));memset(&svs,0,sizeof(svs));memset(entities,0,sizeof(entities));
    pr_strings=strings;sv.active=1;sv.num_edicts=2;strcpy(sv.name,"seyda_arrille");svs.maxclients=1;svs.clients=&client;
    client.edict=&entities[1];entities[1].v.movetype=MOVETYPE_WALK;entities[1].v.origin[2]=16;entities[1].v.view_ofs[2]=13;
    next=next==&world?&world2:&world;
    world.entities=world2.entities="{\n\"classname\" \"worldspawn\"\n\"_aw_cell_int\" \"763\"\n}\n";
    sv.worldmodel=next;subtitles=notices=0;
}
static unsigned opened;static int opened_owned,script_lock=-1;
static int fake_open(unsigned reference,const char *name,int owned){
    assert(!strcmp(name,"Basket"));opened=reference;opened_owned=owned;return 1;}
static int fake_lock(unsigned reference,int original){assert(reference==CHEST);return script_lock>=0?script_lock:original;}
static void rules(void){
    static aw_cstrip_list_t l;static aw_cstrip_entry_t sides[2][AW_CSTRIP_ROWS];int i;
    memset(&l,0,sizeof(l));l.columns=4;
    l.row[0]=sides[0];l.row[1]=sides[1];l.cap[0]=l.cap[1]=AW_CSTRIP_ROWS;
    for(i=0;i<10;i++){Q_snprintf(l.row[0][i].id,sizeof(l.row[0][i].id),"item%d",i);l.row[0][i].count=i+1;}
    l.count[0]=10;l.count[1]=0;AW_CStripClamp(&l);
    assert(l.side==AW_CSTRIP_CONTAINER && l.selected[0]==0 && l.first[0]==0);
    AW_CStripMove(&l,-1);assert(l.selected[0]==0);                                  /* stops at the first */
    AW_CStripMove(&l,5);assert(l.selected[0]==5 && l.first[0]==2);                 /* scrolled to keep it in view */
    AW_CStripMove(&l,100);assert(l.selected[0]==9 && l.first[0]==6);               /* stops at the last */
    AW_CStripMove(&l,-8);assert(l.selected[0]==1 && l.first[0]==1);
    assert(AW_CStripSelected(&l)==&l.row[0][1]);
    /* the mouse: cells of 36 from x 12, y 100; the second cell in view is entry first+1 */
    assert(AW_CStripCell(&l,12+36+3,110,12,100,36,36)==2);
    assert(AW_CStripCell(&l,11,110,12,100,36,36)==-1 && AW_CStripCell(&l,20,99,12,100,36,36)==-1);
    assert(AW_CStripCell(&l,12+4*36,110,12,100,36,36)==-1);                         /* past the columns */
    /* the other side: empty, nothing selected; back, the selection kept */
    AW_CStripSide(&l,-1);assert(l.side==AW_CSTRIP_INVENTORY && !AW_CStripSelected(&l));
    assert(AW_CStripCell(&l,14,110,12,100,36,36)==-1);
    AW_CStripSide(&l,AW_CSTRIP_CONTAINER);assert(AW_CStripSelected(&l)==&l.row[0][1]);
    /* a take that empties the list's end: the selection and the view follow */
    l.selected[0]=9;AW_CStripClamp(&l);l.count[0]=3;AW_CStripClamp(&l);
    assert(l.selected[0]==2 && l.first[0]==0);
    l.count[0]=0;AW_CStripClamp(&l);assert(!AW_CStripSelected(&l) && l.selected[0]==0);
}
int main(void){
    const char *name,*why;char weight[48],value[48],prompt[48];int owned,steal;
    rules();
    aw_ledger_on=1;AW_LedgerClear(&aw_ledger);AW_StateReset();
    /* unowned, unlocked: "E: Open" in white; the box names it without a lock line; E opens the strip */
    tables(0,1,0);level();
    assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,"Basket") && !owned && !weight[0]);
    assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && !steal && !strcmp(prompt,"E: Open"));
    assert(AW_InventoryUse()==0 && !opened);              /* no strip in this build: E does nothing */
    aw_container_open=fake_open;aw_container_lock=fake_lock;
    assert(AW_InventoryUse() && opened==CHEST && opened_owned==0);
    /* owned: "E: Steal" drawn red; opening is free, the strip knows it is owned */
    tables(1,1,0);level();opened=0;
    assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && steal && !strcmp(prompt,"E: Steal"));
    assert(AW_InventoryUse() && opened==CHEST && opened_owned==1);
    /* locked (level 50): "Locked", the box's lock line, E opens nothing and says so; a script's Unlock opens it */
    tables(1,1,50);level();opened=0;
    assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && steal && !strcmp(prompt,"Locked"));
    assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(weight,"Lock Level: 50"));
    assert(AW_InventoryUse() && !opened && subtitles==1 && !strcmp(last_subtitle,"Locked"));
    script_lock=0;
    assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && !strcmp(prompt,"E: Steal"));
    assert(AW_InventoryUse() && opened==CHEST);
    script_lock=-1;
    /* organic (flora): no prompt, E falls through to the harvest */
    tables(0,0,0);level();opened=0;
    assert(!AW_ItemPrompt(prompt,sizeof(prompt),&steal) && !AW_InventoryUse() && !opened);
    /* take and put through the container deltas: owned, the take is stolen from arrille */
    tables(1,1,0);level();
    assert(AW_ContainerCount(CHEST,"misc_quill")==3);
    assert(AW_ContainerTake(CHEST,"misc_quill",2,1,&why)==2);
    assert(AW_ContainerCount(CHEST,"misc_quill")==1 && AW_StateGet(&aw_state,AW_ITEM,"misc_quill")==2);
    assert(AW_LedgerStolenCount(&aw_ledger,"misc_quill","arrille",0)==2);
    assert(AW_ContainerTake(CHEST,"misc_quill",5,1,&why)==1);                       /* stops at what it holds */
    assert(!AW_ContainerTake(CHEST,"misc_quill",1,1,&why) && !strcmp(why,"none"));
    assert(AW_StateGet(&aw_state,AW_ITEM,"misc_quill")==3 && AW_LedgerStolenCount(&aw_ledger,"misc_quill","arrille",0)==3);
    /* put back: no stolen pair is added; more than carried is refused with nothing changed */
    assert(AW_ContainerPut(CHEST,"misc_quill",1,&why)==1);
    assert(AW_ContainerCount(CHEST,"misc_quill")==1 && AW_StateGet(&aw_state,AW_ITEM,"misc_quill")==2);
    assert(!AW_ContainerPut(CHEST,"misc_quill",5,&why) && !strcmp(why,"carry") && AW_StateGet(&aw_state,AW_ITEM,"misc_quill")==2);
    assert(!AW_ContainerTake(CHEST,"no_such_item",1,0,&why) && !strcmp(why,"item"));
    /* the change is the world change list's: kept across a new map (read again) */
    level();assert(AW_ContainerCount(CHEST,"misc_quill")==1);
    /* an unowned take marks nothing stolen */
    AW_LedgerClear(&aw_ledger);AW_StateReset();tables(0,1,0);level();
    assert(AW_ContainerTake(CHEST,"misc_quill",3,0,&why)==3 && !aw_ledger.stolen_count);
    assert(AW_ContainerCount(CHEST,"misc_quill")==0);
    /* the last one put away is no longer worn: an equipped item put in is unequipped */
    strcpy(aw_state.inventory.equipped[AW_SLOT_RIGHT],"misc_quill");
    assert(AW_ContainerPut(CHEST,"misc_quill",3,&why)==3 && !aw_state.inventory.equipped[AW_SLOT_RIGHT][0]);
    AW_LedgerClear(&aw_ledger);
    puts("aga_container_strip_test ok");
    return 0;
}
