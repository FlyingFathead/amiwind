/* SPDX-License-Identifier: GPL-3.0-only
 * PICKUP-PLACED-58: the activate key's own path on a placed item in a room (AW_InventoryUse, which the scene's use
 * reaches after the opening's story objects): the real focus table (an AWF2 file), the real item table (AWI2), the
 * real aim, reach and take. The take goes to the object state only when the room draws the item (an edict with its
 * reference or a CHIM room placement); a compiled room that leaves the item out shows no box and takes nothing
 * (INTERIOR-PLACED-ITEMS-47, the Census Office). */
#include "quakedef.h"
#include "aw_inventory.h"
#include <assert.h>
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
static client_t client;
static edict_t entities[8];
static model_t world,world2;
char *pr_strings;
static char strings[16];
static int room_draws,taken,take_reference,notices,disabled;
static byte focus_file[8+12+96],item_file[8+512];
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
    if(!strcmp(name,"focus.awf"))return serve(focus_file,sizeof(focus_file),file);
    if(!strcmp(name,"inventory/items.awi"))return serve(item_file,sizeof(item_file),file);
    if(!strcmp(name,"gfx/hud-settings.txt"))return serve(hud_text,sizeof(hud_text)-1,file);
    return -1;
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
    memset(&sv,0,sizeof(sv));memset(&svs,0,sizeof(svs));memset(entities,0,sizeof(entities));memset(&aw_state,0,sizeof(aw_state));
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
    tables();
    /* the room draws the quill: the box, then E takes it once into the inventory */
    level(1);
    assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,"Quill Pen") && owned==1);
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
    puts("Placed pickup through the use key's path: box, take, no second take, no box for an item the room leaves out.");
    return 0;
}
