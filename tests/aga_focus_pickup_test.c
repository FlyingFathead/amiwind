/* SPDX-License-Identifier: GPL-3.0-only
 * PICKUP-PLACED-58: the activate key's own path on a placed item in a room (AW_InventoryUse, which the scene's use
 * reaches after the opening's story objects): the real focus table (an AWF2 file), the real item table (AWI2), the
 * real aim, reach and take. The take goes to the object state only when the room draws the item (an edict with its
 * reference or a CHIM room placement); a compiled room that leaves the item out shows no box and takes nothing
 * (INTERIOR-PLACED-ITEMS-47, the Census Office). */
#include "quakedef.h"
#include "aw_inventory.h"
#include "aw_ledger.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
static client_t client;
static edict_t entities[8];
static model_t world,world2;
char *pr_strings;
static char strings[16];
static int room_draws,taken,take_reference,notices,disabled;
static byte focus_file[8+12+96+28],item_file[8+512],placed_file[8+16+48];
static int placed_size,focus_size=8+12+96;   /* AWF2: the rows alone; AWF3 (CELL-CHANGES-59): the owners list too */
static void put32(byte *p,unsigned long v);
static const char hud_text[]="iMaxActivateDist 192\nsWeight Weight\nsValue Value\nsTake Grab\n";
#define QUILL 406347u
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
    if(!strcmp(name,"focus.awf"))return serve(focus_file,focus_size,file);
    if(!strcmp(name,"inventory/items.awi"))return serve(item_file,sizeof(item_file),file);
    if(!strcmp(name,"gfx/hud-settings.txt"))return serve(hud_text,sizeof(hud_text)-1,file);
    if(!strcmp(name,"progs/items/placed.awp") && placed_size)return serve(placed_file,placed_size,file);
    return -1;
}
/* WORLD-OBJECT-PLACEMENT-59: the placed item list (tools/prepare_item_models.py pack_placed) and the drawing side's
 * hooks (aw_placed.c in the game): what was offered, where and with which model. */
static int admitted,refuse_models;static unsigned admitted_ref;static float admitted_at[3],admitted_scale;static char admitted_stem[17];
static int fake_begin(void){admitted=0;return 1;}
static int fake_admit(unsigned reference,const char *stem,const float local[3],const float angles[3],float scale){
    (void)angles;if(refuse_models)return 0;
    admitted_ref=reference;memcpy(admitted_at,local,sizeof(admitted_at));admitted_scale=scale;strcpy(admitted_stem,stem);
    return ++admitted;
}
static float ray_hit;static int ray_drawn;
static float fake_ray(int drawn,const float *eye,const float *dir){(void)eye;(void)dir;ray_drawn=drawn;return ray_hit;}
static void placed_table(unsigned reference){
    byte *row=placed_file+8+16;float v[6]={80,0,116,0,90,0};int k;unsigned long bits;
    memset(placed_file,0,sizeof(placed_file));memcpy(placed_file,"AWP1",4);put32(placed_file+4,1);
    put32(placed_file+8,763);put32(placed_file+12,0);put32(placed_file+16,1);put32(placed_file+20,1);
    put32(row,reference);row[4]=0;row[5]=0;row[6]=0x00;row[7]=0x18;          /* model row 0, scale 0x1800 = 1.5 */
    for(k=0;k<6;k++){memcpy(&bits,&v[k],4);put32(row+8+4*k,bits);}
    memcpy(row+32,"0123456789abcdef",16);placed_size=sizeof(placed_file);
}
int AW_WorldToSource(const char *name,const float *local,float *out){(void)name;(void)local;(void)out;return 0;}
int AW_SourceToWorld(const char *name,const float *in,float *local){(void)name;(void)in;(void)local;return 0;}
void AW_MwscriptRoomShift(float shift[3]){shift[0]=shift[1]=shift[2]=0;}
int AW_ObjectDisabled(unsigned reference){return disabled && reference==QUILL;}
int AW_ObjectTake(unsigned reference,int stolen){(void)stolen;take_reference=(int)reference;taken++;disabled=1;return 1;}
int ChimRoom_Has(unsigned reference){return room_draws && reference==QUILL;}
void AW_UIPickupNotice(const char *name,double duration){(void)duration;assert(!strcmp(name,"Quill Pen"));notices++;}
void AW_UISubtitle(const char *speaker,const char *text,double duration){(void)speaker;(void)text;(void)duration;assert(0);}
void AW_CombatEquipmentChanged(void){}
void ED_Free(edict_t *e){(void)e;assert(0);}   /* a dropped item's edict: none here */
/* the world change list's drops (CELL-CHANGES-59) are read at every map too: none here, so none is ever shown */
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
/* One room (cell 763), one item row: the Quill Pen at game units (80,0,116), map (20,0,29): 20 units ahead of the
 * eye at (0,0,29), inside the 48-unit reach. */
static void tables(void){
    byte *row=focus_file+8+12;float weight=.1f;unsigned long bits;
    memset(focus_file,0,sizeof(focus_file));memset(item_file,0,sizeof(item_file));
    memcpy(focus_file,"AWF2",4);put32(focus_file+4,1);
    put32(focus_file+8,763);put32(focus_file+12,0);put32(focus_file+16,1);
    row[0]='I';row[1]=1;put32(row+4,QUILL);put32(row+8,80);put32(row+12,0);put32(row+16,116);
    memcpy(&bits,&weight,4);put32(row+20,bits);put32(row+24,1);memcpy(row+28,"Quill Pen",9);memcpy(row+64,"misc_quill",10);
    memcpy(item_file,"AWI2",4);put32(item_file+4,1);
    memcpy(item_file+8,"misc_quill",10);memcpy(item_file+8+64,"Quill Pen",9);put32(item_file+8+160,AW_INV_MISC);
    put32(item_file+8+168,1);put32(item_file+8+172,bits);
}
static void level(int draws){
    static model_t *next;
    memset(&sv,0,sizeof(sv));memset(&svs,0,sizeof(svs));memset(entities,0,sizeof(entities));AW_StateReset();
    pr_strings=strings;sv.active=1;sv.num_edicts=2;strcpy(sv.name,"census");svs.maxclients=1;svs.clients=&client;
    client.edict=&entities[1];entities[1].v.movetype=MOVETYPE_WALK;entities[1].v.origin[2]=16;entities[1].v.view_ofs[2]=13;
    /* a new map each time: the focus table is read again */
    next=next==&world?&world2:&world;
    world.entities=world2.entities="{\n\"classname\" \"worldspawn\"\n\"_aw_cell_int\" \"763\"\n}\n";
    sv.worldmodel=next;room_draws=draws;taken=take_reference=notices=disabled=0;
}
static int reader_opened;
static int fake_reader(unsigned reference){reader_opened=(int)reference;return 1;}
int main(void){
    const char *name;char weight[48],value[48];int owned;
    /* PLACED-PIT-AXE-NO-FOCUS-61: the ray against a placed model's box (mathlib.c AW_RayAliasBox): an axe 20 units long
     * along its model x, turned 90 degrees (lying along world y), the margin 1; looked at from straight above */
    {float origin[3]={100,0,0},angles[3]={0,90,0},mins[3]={0,-1,-1},maxs[3]={20,1,1},down[3]={0,0,-1};
     float above[3]={100,10,10},beside[3]={100,-10,10},far_end[3]={100,30,10},side[3]={110,10,0},along[3]={-1,0,0};float t;
     t=AW_RayAliasBox(origin,angles,1,mins,maxs,1,above,down);assert(t>7.99f && t<8.01f);        /* its middle: hit */
     assert(AW_RayAliasBox(origin,angles,1,mins,maxs,1,beside,down)<0);                           /* behind its end */
     assert(AW_RayAliasBox(origin,angles,1,mins,maxs,1,far_end,down)<0);                          /* past its tip */
     t=AW_RayAliasBox(origin,angles,2,mins,maxs,1,far_end,down);assert(t>6.99f && t<7.01f);       /* scaled 2: hit */
     t=AW_RayAliasBox(origin,angles,1,mins,maxs,1,side,along);assert(t>7.99f && t<8.01f);         /* from the side */
     assert(AW_RayAliasBox(origin,angles,1,mins,maxs,1,origin,down)==0);}                         /* the eye inside */
    tables();
    /* the room draws the quill: the box, then E takes it once into the inventory */
    level(1);
    assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,"Quill Pen") && owned==1);
    /* INFO-BOX-TEXT-CUT-62: a door's name longer than the 35-byte name field goes on in the row's id field: the maintainer's
     * two doors, whole ("...Excise Offic" and "...: Apoth" were the cut ones); an older file (empty id field) reads as written */
    {
     static const struct {const char *head,*tail,*whole;} doors[]={
      {"Seyda Neen, Census and Excise Offic","e","Seyda Neen, Census and Excise Office"},
      {"Suran, Ibarnadad Assimarari: Apothe","cary","Suran, Ibarnadad Assimarari: Apothecary"},
      {"Short Door","","Short Door"}};
     int d;
     for(d=0;d<3;d++){
      byte *row=focus_file+8+12;
      tables();memset(row+28,0,36+32);row[0]='D';row[1]=0;memcpy(row+28,doors[d].head,strlen(doors[d].head));
      memcpy(row+64,doors[d].tail,strlen(doors[d].tail));
      level(1);
      if(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned))fprintf(stderr,"door %d: no focus row\n",d),assert(0);
      if(strcmp(name,doors[d].whole))fprintf(stderr,"door %d: name '%s'\n",d,name),assert(0);
      /* the same row in a file without the continuation: the name as written */
      memset(row+64,0,32);level(1);
      assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,doors[d].head));
     }
     tables();level(1);
    }
    /* STEAL-PROMPT-58: the owned quill reads "E: Steal" (drawn red); unowned it reads the GMST's "E: Take" */
    {char prompt[48];int steal=-1;
     assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && steal==1 && !strcmp(prompt,"E: Steal"));
     focus_file[8+12+1]=0;level(1);
     assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && steal==0 && !strcmp(prompt,"E: Grab"));
     /* the builder's action code: an owned readable book reads "E: Read" (red) once the reader exists, else E
      * takes it and the prompt says so; a magic scroll (take + scroll bit) is taken like any item */
     focus_file[8+12+1]=1;focus_file[8+12+2]=2|4;level(1);
     assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && steal==1 && !strcmp(prompt,"E: Steal"));
     aw_book_reader=fake_reader;
     assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && steal==1 && !strcmp(prompt,"E: Read"));
     focus_file[8+12+1]=0;focus_file[8+12+2]=2;level(1);
     assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && steal==0 && !strcmp(prompt,"E: Read"));
     focus_file[8+12+2]=1|8;level(1);
     assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && steal==0 && !strcmp(prompt,"E: Grab"));
     /* BOOK-READER-58: E on a readable book opens the reader and takes nothing; the reader asks for its id and owner,
      * and its Take goes through the same take as E on an item (once) */
     {char id[33];int book_owned=-1;
      focus_file[8+12+1]=1;focus_file[8+12+2]=2|4;level(1);reader_opened=0;
      assert(AW_InventoryUse() && reader_opened==(int)QUILL && !taken);
      assert(AW_PlacedBook(QUILL,id,&book_owned) && !strcmp(id,"misc_quill") && book_owned==1);
      assert(!AW_PlacedBook(QUILL+1,id,&book_owned) && !id[0]);
      assert(AW_PlacedTake(QUILL) && taken==1 && take_reference==(int)QUILL && notices==1);
      assert(!AW_PlacedTake(QUILL) && taken==1);}
     aw_book_reader=NULL;focus_file[8+12+1]=1;focus_file[8+12+2]=0;level(1);}
    assert(AW_InventoryUse());
    assert(taken==1 && take_reference==(int)QUILL && notices==1);
    assert(AW_StateGet(&aw_state,AW_ITEM,"misc_quill")==1);
    assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));   /* taken: no box */
    assert(!AW_InventoryUse() && taken==1);                                 /* and nothing taken twice */
    /* a compiled room without the item (the Census Office's small items): no box, E falls through */
    level(0);
    assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
    assert(!AW_InventoryUse() && !taken && AW_StateGet(&aw_state,AW_ITEM,"misc_quill")==0);
    /* FOCUS-BOX-NO-ACTORS-58: an aimed actor row (a creature or a person) gets no box; E takes nothing from it */
    focus_file[8+12]='A';level(1);
    assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
    assert(!AW_InventoryUse() && !taken);
    focus_file[8+12]='I';
    /* WORLD-OBJECT-PLACEMENT-59: the room leaves the quill out, the placed list draws it by reference to the shared
     * model: offered once at its map position (a quarter of the game units), its model and scale; then the box and
     * E work on it as on a drawn item */
    placed_table(QUILL);aw_placed_begin=fake_begin;aw_placed_admit=fake_admit;
    level(0);
    assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,"Quill Pen"));
    assert(admitted==1 && admitted_ref==QUILL && !strcmp(admitted_stem,"0123456789abcdef"));
    assert(admitted_at[0]==20 && admitted_at[1]==0 && admitted_at[2]==29 && admitted_scale==1.5f);
    assert(AW_InventoryUse() && taken==1 && take_reference==(int)QUILL);
    assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));     /* taken: disabled, no box */
    /* PLACED-PIT-AXE-NO-FOCUS-61: the aim meets a drawn item's own model (aw_placed.c placed_ray): the view turned 20
     * degrees off its origin (6.8 units off the crosshair line, past the origin test's 4) finds it where the ray meets
     * the model, at the distance of that point (beyond the reach: none); a miss falls back to the origin test */
    aw_placed_ray=fake_ray;ray_hit=15;level(0);entities[1].v.v_angle[1]=20;
    assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,"Quill Pen") && ray_drawn==1);
    ray_hit=-1;assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
    ray_hit=60;assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
    entities[1].v.v_angle[1]=0;ray_hit=-1;assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
    aw_placed_ray=NULL;
    /* a room that draws the item itself: nothing offered (no second copy) */
    level(1);assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && admitted==0);
    /* the level's model room used up: the row is not drawn, so no box over an empty table */
    refuse_models=1;level(0);
    assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && admitted==0);
    /* another reference in the list than in the room: nothing */
    refuse_models=0;placed_table(QUILL+1);level(0);
    assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && admitted==0);
    aw_placed_begin=NULL;aw_placed_admit=NULL;
    /* CELL-CHANGES-59 slice 2: AWF3, the owners list after the rows: the owned quill taken is stolen from its owner,
     * the pair (misc_quill, fargoth) on the world change list; a faction owner is a pair of its own; an unowned take,
     * an AWF2 table (no owner list) and the old method (aw_placed ledger off) add none */
    {byte *t;
     tables();memcpy(focus_file,"AWF3",4);
     t=focus_file+8+12+96;memcpy(t,"AWO1",4);put32(t+4,1);put32(t+8,QUILL);t[12]=t[13]=t[14]=t[15]=0;
     put32(t+16,8);memcpy(t+20,"fargoth",8);focus_size=8+12+96+28;
     AW_LedgerClear(&aw_ledger);level(1);
     assert(AW_InventoryUse() && taken==1);
     assert(aw_ledger.stolen_count==1 && AW_LedgerStolenCount(&aw_ledger,"misc_quill","fargoth",0)==1);
     t[14]=1;AW_LedgerClear(&aw_ledger);level(1);
     assert(AW_InventoryUse() && AW_LedgerStolenCount(&aw_ledger,"misc_quill","fargoth",1)==1 &&
            !AW_LedgerStolenCount(&aw_ledger,"misc_quill","fargoth",0));
     focus_file[8+12+1]=0;AW_LedgerClear(&aw_ledger);level(1);
     assert(AW_InventoryUse() && taken==1 && !aw_ledger.stolen_count);
     focus_file[8+12+1]=1;memcpy(focus_file,"AWF2",4);AW_LedgerClear(&aw_ledger);level(1);
     assert(AW_InventoryUse() && taken==1 && !aw_ledger.stolen_count);
     memcpy(focus_file,"AWF3",4);aw_ledger_on=0;AW_LedgerClear(&aw_ledger);level(1);
     assert(AW_InventoryUse() && taken==1 && !aw_ledger.stolen_count);aw_ledger_on=1;
     /* a list that names another reference: no owner, no pair */
     put32(t+8,QUILL+1);AW_LedgerClear(&aw_ledger);level(1);
     assert(AW_InventoryUse() && taken==1 && !aw_ledger.stolen_count);
     AW_LedgerClear(&aw_ledger);focus_size=8+12+96;}
    puts("Placed pickup through the use key's path: box, take, no second take, no box for an item the room leaves out; "
         "the placed list draws the left-out item by reference and it is taken the same way.");
    return 0;
}
