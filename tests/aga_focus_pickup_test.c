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
static byte focus_file[8+12+96+28],item_file[8+2*512],placed_file[8+16+48];
static int placed_size,focus_size=8+12+96;   /* AWF2: the rows alone; AWF3 (CELL-CHANGES-59): the owners list too */
static void put32(byte *p,unsigned long v);
static const char hud_text[]="iMaxActivateDist 192\nsWeight Weight\nsValue Value\nsTake Grab\n";
#define QUILL 406347u
void Con_Printf(char *format,...){(void)format;}
void CDAudio_Update(void){}
void S_ExtraUpdate(void){}
edict_t *EDICT_NUM(int i){assert(i>=0 && i<8);return &entities[i];}
/* CENSUS-CRAB-PLATE-FOCUS-66: edicts 2 and 3 carry the references in refs[] (the census office's brush items, each an
 * edict of its own with its aw_ref) while ref_edicts is set; every other field lookup finds nothing */
static eval_t refs[8];static int ref_edicts;
eval_t *GetEdictFieldValue(edict_t *e,char *field){
    int n=(int)(e-entities);
    if(ref_edicts && !strcmp(field,"aw_ref") && n>=2 && n<2+ref_edicts)return &refs[n];
    return NULL;
}
void *AW_TryMalloc(int size){return calloc(1,size);}
static int serve(const void *data,int size,FILE **file){
    *file=tmpfile();assert(*file);assert(fwrite(data,1,size,*file)==(size_t)size);rewind(*file);return size;
}
/* CENSUS-CRAB-PLATE-FOCUS-66: a focus table of two item rows (the silver plate and the crab meat on it) */
static byte stacked_file[8+12+2*96];static int stacked;
int COM_FOpenFile(char *name,FILE **file){
    *file=NULL;
    if(!strcmp(name,"focus.awf") && stacked)return serve(stacked_file,sizeof(stacked_file),file);
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
void AW_UIPickupNotice(const char *name,double duration){(void)duration;assert(!strcmp(name,"Quill Pen") || !strcmp(name,"Candle"));notices++;}
static int subtitles;   /* only the locked container's line (DOOR-TRAPS-NOT-SPRUNG-55 check) */
void AW_UISubtitle(const char *speaker,const char *text,double duration){(void)speaker;(void)duration;assert(!strcmp(text,"Locked"));subtitles++;}
void AW_CombatEquipmentChanged(void){}
void ED_Free(edict_t *e){(void)e;assert(0);}   /* a dropped item's edict: none here */
/* the world change list's drops (CELL-CHANGES-59) are read at every map too: none here, so none is ever shown */
edict_t *ED_Alloc(void){assert(0);return NULL;}
char *ED_NewString(char *s){(void)s;assert(0);return NULL;}
void SV_LinkEdict(edict_t *e,qboolean triggers){(void)e;(void)triggers;assert(0);}
model_t *Mod_ForName(char *name,qboolean crash){(void)name;(void)crash;assert(0);return NULL;}
void *Cache_Check(cache_user_t *c){(void)c;assert(0);return NULL;}
int SV_PointContents(vec3_t p){(void)p;assert(0);return 0;}
/* CENSUS-CRAB-PLATE-FOCUS-66: the view trace (the whole reach, 48 map units from the eye) meets edict view_entity at
 * view_fraction when it is set; a sight test to a row's origin (about 20 units) and everything else are clear */
static int view_entity;static float view_fraction;
trace_t SV_Move(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,int type,edict_t *pass){
    trace_t tr;vec3_t d;(void)mins;(void)maxs;(void)type;(void)pass;
    memset(&tr,0,sizeof(tr));tr.fraction=1;VectorCopy(end,tr.endpos);
    VectorSubtract(end,start,d);
    if(view_entity && DotProduct(d,d)>40*40){tr.fraction=view_fraction;tr.ent=&entities[view_entity];}
    return tr;
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
    /* the item table, ids ascending: a carryable light (PRISON-SHIP-ITEMS-TAKEABLE-65: the candle, flagged a light),
     * then the quill */
    memcpy(item_file,"AWI2",4);put32(item_file+4,2);
    memcpy(item_file+8,"light_com_candle_02",19);memcpy(item_file+8+64,"Candle",6);put32(item_file+8+160,AW_INV_MISC);
    put32(item_file+8+168,1);put32(item_file+8+172,bits);put32(item_file+8+180,AW_INV_LIGHT);
    put32(item_file+8+164,128);put32(item_file+8+504,600);     /* its radius and burn time (a light's catalogue row) */
    memcpy(item_file+8+512,"misc_quill",10);memcpy(item_file+8+512+64,"Quill Pen",9);
    put32(item_file+8+512+160,AW_INV_MISC);put32(item_file+8+512+168,1);put32(item_file+8+512+172,bits);
}
/* CENSUS-CRAB-PLATE-FOCUS-66: the census office's back-room table as the table holds it: the owned Silverware Plate
 * (reference PLATE, row 0) and the crab meat lying on it (CRAB, row 1), their centres half a game unit apart (the
 * original data: 580.2 and 580.7); here 20 and 20.5 map units ahead of the eye, one unit under the crosshair line, so
 * the plate's origin is the nearer one. Both rows read "Quill Pen" with the quill's record, so the take path is the
 * quill's own; the reference taken tells them apart. */
#define PLATE 119580u
#define CRAB 454283u
static void stacked_tables(void){
    static const unsigned long refs_of[2]={PLATE,CRAB},x_of[2]={80,82};
    float weight=.1f;unsigned long bits;int k;
    memset(stacked_file,0,sizeof(stacked_file));
    memcpy(stacked_file,"AWF2",4);put32(stacked_file+4,1);
    put32(stacked_file+8,763);put32(stacked_file+12,0);put32(stacked_file+16,2);
    memcpy(&bits,&weight,4);
    for(k=0;k<2;k++){
        byte *row=stacked_file+8+12+96*k;
        row[0]='I';row[1]=1;put32(row+4,refs_of[k]);put32(row+8,x_of[k]);put32(row+12,0);put32(row+16,112);
        put32(row+20,bits);put32(row+24,1);memcpy(row+28,"Quill Pen",9);memcpy(row+64,"misc_quill",10);
    }
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
/* DOOR-TRAPS-NOT-SPRUNG-55: stand-ins for the trap (aw_hinged_door.c) and the strip (aw_cstrip.c) */
extern int (*aw_trap_spring)(unsigned reference);
extern int (*aw_container_open)(unsigned reference,const char *name,int owned);
static int trap_armed,springs,opens;
static int trap_stand_in(unsigned reference){(void)reference;if(!trap_armed)return 0;trap_armed=0;springs++;return 1;}
/* LOCKED-CONTAINERS-NEVER-OPEN-67: a stand-in for the doors' lock rule (aw_hinged_door.c container_lock_pass) */
extern int (*aw_lock_pass)(unsigned reference,const char *key);
static int pass_answer,passes;static unsigned pass_ref;
static int pass_stand_in(unsigned reference,const char *key){(void)key;passes++;pass_ref=reference;return pass_answer;}
static int open_stand_in(unsigned reference,const char *name,int owned){(void)reference;(void)name;(void)owned;opens++;return 1;}
/* CONTAINER-SCRIPT-ACTIVATE-67: a stand-in for the scripts' hold on an object's use (aw_mwhost.c object_intercept) */
static int intercept_answer,intercepts;static unsigned intercept_ref;
static int intercept_stand_in(unsigned reference){intercepts++;intercept_ref=reference;return intercept_answer;}
static int reader_opened;
static int fake_reader(unsigned reference){reader_opened=(int)reference;return 1;}
/* PRISON-SHIP-ITEMS-TAKEABLE-65: the Inventory window not allowed / allowed (aw_story.c AW_StoryInventoryAllowed) */
static int not_allowed(void){return 0;}
static int allowed(void){return 1;}
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
      /* PRISON-SHIP-ITEMS-TAKEABLE-65: a door keeps its name before the papers */
      aw_object_labels=not_allowed;
      assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,doors[d].whole));
      aw_object_labels=NULL;
      /* the same row in a file without the continuation: the name as written */
      memset(row+64,0,32);level(1);
      assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,doors[d].head));
     }
     tables();level(1);
    }
    /* SIGNPOST-NAMES-MISSING-65: a named board ('N' row: the board's centre, its box and angles in the id field,
     * tools/prepare_focus.py) shows its name when the view ray meets its box: a board 76 x 32 game units (map 19 x 8)
     * face on, 20 map units ahead. Turned 20 degrees (7 units off its centre, past the near-the-origin test) it still
     * shows; turned 30 degrees (11 units off, past its half width of 9.5) not. It has no prompt and E takes nothing. */
    {
     byte *row=focus_file+8+12;float box[7]={4,38,16,1,0,0,0};unsigned long bits;int k;char prompt[48];int steal=-1;
     (void)AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned);   /* read on this map: the next map reads again */
     tables();memset(row+20,0,96-20);row[0]='N';row[1]=0;row[2]=0;memcpy(row+28,"Pelagiad (back road)",20);
     for(k=0;k<7;k++){memcpy(&bits,&box[k],4);put32(row+64+4*k,bits);}
     level(1);
     assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,"Pelagiad (back road)") &&
            !weight[0] && !value[0] && !owned);
     assert(!AW_ItemPrompt(prompt,sizeof(prompt),&steal));
     assert(!AW_InventoryUse() && !taken);
     /* PRISON-SHIP-ITEMS-TAKEABLE-65: a named object that is not an item (a board here; the prison ship's hammock,
      * an activator of its own) shows no name before the papers */
     aw_object_labels=not_allowed;assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
     aw_object_labels=allowed;assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));aw_object_labels=NULL;
     entities[1].v.v_angle[1]=20;assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
     entities[1].v.v_angle[1]=30;assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
     entities[1].v.v_angle[1]=180;assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));   /* behind */
     entities[1].v.v_angle[1]=0;
     /* turned a quarter about z (the builder's quaternion w = z = sqrt(1/2)): seen edge on along the view, its 1-unit
      * thickness side on */
     box[3]=box[6]=0.70710678f;for(k=3;k<7;k++){memcpy(&bits,&box[k],4);put32(row+64+4*k,bits);}
     level(1);entities[1].v.v_angle[1]=20;assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
     entities[1].v.v_angle[1]=0;assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
     tables();level(1);
    }
    /* OUTDOOR-CONTAINER-AIM-66: a container whose id field holds its measured box (tools/prepare_focus.py
     * CONTAINER_BOXES: an exterior one) is aimed at by that box: a sack 76 x 32 game units, 20 map units ahead, seen
     * 20 degrees off its centre (7 units, past the near-the-origin test's 6) still shows; 30 degrees off not. The same
     * container with its record id there (a room's, aimed at by the room ray, none here) shows only near its origin. */
    {
     byte *row=focus_file+8+12;float box[7]={4,38,16,1,0,0,0};unsigned long bits;int k;
     (void)AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned);
     tables();memset(row+20,0,96-20);row[0]='C';row[1]=0;row[2]=1;memcpy(row+28,"Sack",4);
     for(k=0;k<7;k++){memcpy(&bits,&box[k],4);put32(row+64+4*k,bits);}
     level(1);
     assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,"Sack"));
     entities[1].v.v_angle[1]=20;assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
     entities[1].v.v_angle[1]=30;assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
     entities[1].v.v_angle[1]=0;
     memset(row+64,0,32);memcpy(row+64,"com_sack_01",11);level(1);
     assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,"Sack"));
     entities[1].v.v_angle[1]=20;assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
     entities[1].v.v_angle[1]=0;
     /* DOOR-TRAPS-NOT-SPRUNG-55 (TRAPS-WHEN-OPENED-63): E on a trapped container springs the trap (its spell on the
      * player, aw_hinged_door.c AW_TrapSpring) and does not open it; the trap is used up, so the next E opens it. A
      * locked one says Locked and springs nothing (the original: the lock first). */
     aw_trap_spring=trap_stand_in;aw_container_open=open_stand_in;trap_armed=1;springs=opens=0;
     assert(AW_InventoryUse() && springs==1 && opens==0 && !trap_armed);
     assert(AW_InventoryUse() && springs==1 && opens==1);
     trap_armed=1;row[3]=50;level(1);
     assert(AW_InventoryUse() && springs==1 && opens==1 && trap_armed && subtitles==1);
     /* LOCKED-CONTAINERS-NEVER-OPEN-67: the doors' way through a lock (aw_hinged_door.c through aw_lock_pass): when
      * it lets the player through (the key carried, god mode, dbg doorlocks off) the locked container opens (its trap
      * first, as unlocked: the key has disarmed it in the engine); when it refuses, Locked as before */
     trap_armed=0;aw_lock_pass=pass_stand_in;pass_answer=0;level(1);
     assert(AW_InventoryUse() && opens==1 && subtitles==2 && passes==1 && pass_ref==QUILL);
     pass_answer=1;level(1);
     assert(AW_InventoryUse() && opens==2 && subtitles==2 && passes==2);
     aw_lock_pass=NULL;row[3]=0;
     /* CONTAINER-BRUSH-ROWS-67: a container drawn as a brush of its own (a compiled room's func_wall with its aw_ref:
      * the Imperial Prison Ship's, the census office's) keeps its row: aimed where the view ray meets that brush, also
      * turned 20 degrees off its origin (where the origin test misses), and E opens it; the courtyard barrel's brush
      * stays the opening's own (no box, E does nothing here) */
     ref_edicts=1;refs[2]._float=(float)QUILL;
     level(1);sv.num_edicts=3;view_entity=2;view_fraction=19.5f/48;
     assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,"Sack"));
     assert(AW_InventoryUse() && opens==3);
     level(1);sv.num_edicts=3;view_entity=2;view_fraction=21.0f/48;entities[1].v.v_angle[1]=20;
     assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,"Sack"));
     entities[1].v.v_angle[1]=0;
     put32(row+4,172851);refs[2]._float=172851.0f;
     level(1);sv.num_edicts=3;view_entity=2;view_fraction=19.5f/48;
     assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !AW_InventoryUse() && opens==3);
     put32(row+4,QUILL);ref_edicts=0;view_entity=0;
     /* CONTAINER-SCRIPT-ACTIVATE-67: a container whose script holds the use (aw_mwhost.c object_intercept, a stand-in
      * here) gives E to the script: nothing opens, no trap springs, no lock is asked. The script's Activate
      * (AW_ContainerActivate) is then the container's own use: the lock first, the trap, then the strip, and nothing
      * while the Inventory window is not allowed; 0 for a reference that is no container here. A script that does
      * not hold the use leaves E to the container, as before. */
     level(1);opens=springs=intercepts=0;trap_armed=0;aw_inventory_intercept=intercept_stand_in;intercept_answer=1;
     assert(AW_InventoryUse() && opens==0 && intercepts==1 && intercept_ref==QUILL);
     assert(AW_ContainerActivate(QUILL) && opens==1);
     assert(!AW_ContainerActivate(QUILL+1) && opens==1);
     trap_armed=1;assert(AW_InventoryUse() && springs==0 && opens==1 && trap_armed);     /* held: the trap waits */
     assert(AW_ContainerActivate(QUILL) && springs==1 && opens==1);                       /* Activate: the trap */
     assert(AW_ContainerActivate(QUILL) && springs==1 && opens==2);                       /* then the strip */
     row[3]=50;level(1);
     {int before=subtitles;
      assert(AW_InventoryUse() && subtitles==before && opens==2);                         /* held: no Locked line */
      assert(AW_ContainerActivate(QUILL) && subtitles==before+1 && opens==2);}            /* Activate: Locked */
     row[3]=0;level(1);
     aw_inventory_allowed=not_allowed;assert(AW_ContainerActivate(QUILL) && opens==2);aw_inventory_allowed=NULL;
     intercept_answer=0;assert(AW_InventoryUse() && opens==3 && intercepts==4);
     aw_trap_spring=NULL;aw_container_open=NULL;
     tables();level(1);
     /* and an item whose script holds the use is not taken by E (MWSCRIPT-MORE-57, the same hook) */
     intercept_answer=1;assert(AW_InventoryUse() && !taken && intercepts==5);
     aw_inventory_intercept=NULL;
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
    /* PRISON-SHIP-ITEMS-TAKEABLE-65: before the Inventory window is allowed (the release papers' EnableInventoryMenu)
     * the use key takes no item and no carryable light and opens no container (spent on nothing: the original's
     * NullAction); a book is read but not taken (its Take refused, as the original's book window hides it). Before
     * the papers (the prison ship's every deck: its bottles, its travel lantern, its crates; the dock, the
     * registration) no text overlay at all: no name and no action line, a book's included. From the papers on, the
     * inventory not yet allowed: the names show, no action line but a book's "E: Read". With the flag set all four
     * work */
    {char prompt[48];int steal=-1;byte *row=focus_file+8+12;
     aw_inventory_allowed=not_allowed;aw_object_labels=not_allowed;level(1);          /* the ship, before the papers */
     assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));                 /* an item: no name */
     assert(!AW_ItemPrompt(prompt,sizeof(prompt),&steal));                            /* nor an action line */
     assert(AW_InventoryUse() && !taken && AW_StateGet(&aw_state,AW_ITEM,"misc_quill")==0);   /* and not taken */
     row[2]=2;aw_book_reader=fake_reader;reader_opened=0;level(1);                      /* a book: read, not taken */
     assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !AW_ItemPrompt(prompt,sizeof(prompt),&steal));
     assert(AW_InventoryUse() && reader_opened==(int)QUILL && !taken);
     assert(!AW_PlacedTake(QUILL) && !taken && AW_StateGet(&aw_state,AW_ITEM,"misc_quill")==0);
     aw_object_labels=allowed;level(1);                       /* the papers laid out, the inventory not yet allowed */
     assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,"Quill Pen"));
     assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && !strcmp(prompt,"E: Read"));
     row[2]=1;level(1);assert(!AW_ItemPrompt(prompt,sizeof(prompt),&steal));             /* an item: its name only */
     aw_object_labels=not_allowed;aw_book_reader=NULL;
     memset(row+28,0,36+32);memcpy(row+28,"Candle",6);memcpy(row+64,"light_com_candle_02",19);level(1);
     assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));                 /* a carryable light (the */
     assert(!AW_ItemPrompt(prompt,sizeof(prompt),&steal));                            /* ship's travel lantern): */
     assert(AW_InventoryUse() && !taken && AW_StateGet(&aw_state,AW_ITEM,"light_com_candle_02")==0);   /* nothing */
     row[0]='C';aw_container_open=open_stand_in;opens=0;level(1);                      /* a container (a crate): */
     assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !AW_ItemPrompt(prompt,sizeof(prompt),&steal));
     assert(AW_InventoryUse() && opens==0);                                          /* no name, stays shut */
     aw_inventory_allowed=allowed;aw_object_labels=allowed;level(1);                 /* the flag set: all four */
     assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned) && !strcmp(name,"Candle"));
     assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && AW_InventoryUse() && opens==1);
     row[0]='I';level(1);
     assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && AW_InventoryUse() && taken==1 &&
            AW_StateGet(&aw_state,AW_ITEM,"light_com_candle_02")==1);
     tables();row[2]=2;level(1);
     assert(AW_PlacedTake(QUILL) && taken==1 && take_reference==(int)QUILL && AW_StateGet(&aw_state,AW_ITEM,"misc_quill")==1);
     tables();level(1);
     assert(AW_ItemPrompt(prompt,sizeof(prompt),&steal) && AW_InventoryUse() && taken==1 &&
            AW_StateGet(&aw_state,AW_ITEM,"misc_quill")==1);
     tables();aw_container_open=NULL;aw_inventory_allowed=NULL;aw_object_labels=NULL;level(1);}
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
    /* CENSUS-CRAB-PLATE-FOCUS-66: the crab meat on the silver plate, both drawn by the room as edicts of their own.
     * The use goes to what the view ray meets first, as in the original; the origin nearer the crosshair line only
     * when the ray meets neither. */
    stacked_tables();stacked=1;ref_edicts=2;refs[2]._float=(float)PLATE;refs[3]._float=(float)CRAB;
    /* the ray meets no edict with a reference: the plate's origin, a hair nearer, as before */
    level(0);sv.num_edicts=4;view_entity=0;
    assert(AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
    assert(AW_InventoryUse() && take_reference==(int)PLATE);
    /* the ray meets the crab meat lying on top first (19.5 units out): E takes the crab meat, not the owned plate */
    level(0);sv.num_edicts=4;view_entity=3;view_fraction=19.5f/48;
    assert(AW_InventoryUse() && take_reference==(int)CRAB);
    /* looking at the plate's rim beside it: the ray meets the plate first, the plate */
    level(0);sv.num_edicts=4;view_entity=2;view_fraction=19.0f/48;
    assert(AW_InventoryUse() && take_reference==(int)PLATE);
    /* the view turned 20 degrees, both origins past the origin test (6.8 units off the line): where the ray meets the
     * crab meat it is still the crab meat (as a drawn item by its model) */
    level(0);sv.num_edicts=4;view_entity=3;view_fraction=21.0f/48;entities[1].v.v_angle[1]=20;
    assert(AW_InventoryUse() && take_reference==(int)CRAB);
    /* turned the same 20 degrees with the ray meeting neither (it passes beside them): no item */
    level(0);sv.num_edicts=4;view_entity=0;entities[1].v.v_angle[1]=20;
    assert(!AW_PlacedFocus(&name,weight,value,sizeof(weight),&owned));
    entities[1].v.v_angle[1]=0;
    /* an edict whose reference no row has (the crab meat's row then has no edict: not drawn): the plate */
    refs[3]._float=(float)(CRAB+1);level(0);sv.num_edicts=4;view_entity=3;view_fraction=19.5f/48;
    assert(AW_InventoryUse() && take_reference==(int)PLATE);
    stacked=0;ref_edicts=0;view_entity=0;
    puts("Placed pickup through the use key's path: box, take, no second take, no box for an item the room leaves out; "
         "the placed list draws the left-out item by reference and it is taken the same way.");
    return 0;
}
