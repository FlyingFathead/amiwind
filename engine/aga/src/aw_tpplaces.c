/* SPDX-License-Identifier: GPL-2.0-or-later
 * dbg tp with no argument (v0.0.57, TP-PICKER-57): every named settlement of the island in the console-font list
 * box (aw_listbox.c), searchable as you type; choosing one runs the existing coordinate teleport (dbg tp X Y Z).
 * The rows are the builder's table id1/tp-places.lut (tools/tp_places_lut.py): read when the box opens, freed when
 * it closes, so nothing stays resident. Without the table (an older disk) the caller opens the scene picker.
 *
 * v0.0.66 (TP-MENU-CATEGORY-FILTER-66, DBG-TP-TO-NPC-66): the buttons All / Exteriors / Interiors / Beings, and the
 * Beings rows (people and creatures by their own names). A being takes you to a free spot beside it, facing it: where
 * it stands now when its scene is loaded, else where it is placed; a common kind (flag AW_TP_NEAREST) to the nearest
 * one of its placements file (id1/tpk/<name>.tpk, read on choose only).
 * v0.0.67 (TP-BEING-TRIBUNAL-FALLS-THROUGH-67): a row's point is the being's feet; into a room the arrival is that
 * point lifted to a door arrival's height (AW_TpBeingArrival), so the arrival search stands the player on the being's
 * floor even when the being is not in the room to step beside. Outdoors the point stays the feet (dbg tp X Y Z: Z
 * names the floor).
 * Memory (the maintainer, 2026-11-13: no large block that could fragment the heap): while the box is open it holds
 * only the names list id1/tp-names.lut (labels, categories, one offset per row) as ONE block allocated at open and
 * freed at close; the world is paused under the box, so nothing streams meanwhile. When exec's largest free block
 * does not hold it plus LOWMEM_SPARE (the spare the CHIM cache keeps, chim_world.c), only the offsets are held and the
 * labels are read from the file in 4 KB chunks; aw_tp_lowmem 1 forces that path. A chosen row's details (position,
 * map, record id) are read from tp-places.lut into one fixed row buffer.
 */
#include "quakedef.h"
#include "aw_listbox.h"
#include "aw_tryalloc.h"
#include "aw_world.h"
#include "aw_reset.h"
int AW_SceneStarting(void);
#ifdef AMIGA
#include <proto/exec.h>
#include <exec/memory.h>
#endif

#define LOWMEM_SPARE (512L*1024L)
static const char path[]="tp-places.lut",names_path[]="tp-names.lut";
static cvar_t lowmem={"aw_tp_lowmem","0"};
static aw_tp_names_t names;
static FILE *names_file;
static long rows;
static char label_buf[AW_TP_NAME];
static const char *const category_names[AW_TP_CATS]={"All","Exteriors","Interiors","Beings"};

static const char *label(void *ctx,int row){
    (void)ctx;
    if(!AW_TpNamesGet(&names,row,label_buf,sizeof(label_buf),NULL))return "";
    return label_buf;
}
static int category(void *ctx,int row){
    int c=0;(void)ctx;
    if(!AW_TpNamesGet(&names,row,label_buf,sizeof(label_buf),&c))return 0;
    return c;
}
/* row ROW of tp-places.lut into P: the header and the one row, nothing else read */
static int details(int row,aw_tp_place_t *p){
    FILE *f=NULL;long size,base,count;unsigned char head[AW_TP_HEADER],one[AW_TP_HEADER+AW_TP_ROW3];int rb;
    size=COM_FOpenFile((char *)path,&f);
    if(size<AW_TP_HEADER || !f){if(f)fclose(f);return 0;}
    base=ftell(f);
    if(fread(head,1,AW_TP_HEADER,f)!=AW_TP_HEADER){fclose(f);return 0;}
    rb=head[7];count=(long)((unsigned long)head[8]<<24|(unsigned long)head[9]<<16|(unsigned long)head[10]<<8|head[11]);
    if(rb<AW_TP_ROW || rb>AW_TP_ROW3 || row<0 || row>=count || fseek(f,base+AW_TP_HEADER+(long)row*rb,SEEK_SET) ||
       fread(one+AW_TP_HEADER,1,(size_t)rb,f)!=(size_t)rb){fclose(f);return 0;}
    fclose(f);
    memcpy(one,head,AW_TP_HEADER);one[8]=one[9]=one[10]=0;one[11]=1;   /* a one-row table */
    if(AW_TpPlacesRows(one,AW_TP_HEADER+rb)!=1)return 0;
    AW_TpPlacesRow(one,0,p);
    return 1;
}
static void chosen(void *ctx,int row){
    aw_tp_place_t p;char command[64];(void)ctx;
    if(!details(row,&p)){Con_Printf("Teleport list: %s unreadable.\n",path);return;}
    if(p.flags&AW_TP_BEING){AW_TpBeingGo(&p);return;}
    if(AW_TpPlacesCommand(&p,command,sizeof(command))<0)return;
    Con_Printf("Teleport: %s\n",p.name);
    Cbuf_AddText(command);
}
static void closed(void *ctx){
    (void)ctx;AW_TpNamesClose(&names);rows=0;
    if(names_file)fclose(names_file);
    names_file=NULL;
}
static int whole_fits(long size){
#ifdef AMIGA
    if((long)AvailMem(MEMF_FAST|MEMF_LARGEST)<size+LOWMEM_SPARE)return 0;
#endif
    (void)size;return !lowmem.value;
}
int AW_TpPlacesOpen(void){
    FILE *f=NULL;long size,base;aw_listbox_spec_t s;int whole;
    if(AW_ListBoxActive())return 1;
    size=COM_FOpenFile((char *)names_path,&f);
    if(size<AW_TPN_HEADER || !f){
        if(f)fclose(f);
        Con_DPrintf("Teleport list: %s not on this disk\n",names_path);
        return 0;
    }
    whole=whole_fits(size);
    base=ftell(f);
    if((rows=AW_TpNamesOpen(&names,f,base,size,whole))<1 && whole)
        rows=AW_TpNamesOpen(&names,f,base,size,whole=0);       /* the block did not fit after all: paged */
    if(rows<1){
        fclose(f);Con_Printf("Teleport list: %s is not AWTN or there is not enough memory\n",names_path);return 0;
    }
    if(whole)fclose(f);
    else {names_file=f;Con_Printf("Teleport list: low memory, the names are read from the disk page by page.\n");}
    memset(&s,0,sizeof(s));
    s.title="Teleport to a place, room or being";s.count=(int)rows;s.label=label;s.chosen=chosen;s.closed=closed;
    s.category_names=category_names;s.categories=AW_TP_CATS;s.category=category;
    if(!AW_ListBoxOpen(&s)){closed(NULL);return 0;}
    Con_DPrintf("Teleport list: %ld rows, %ld bytes held while open%s\n",rows,AW_TpNamesHeld(&names),
        whole?"":" (paged)");
    return 1;
}
/* dbg tp TEXT (DBG-TP-EXPANSION-ARRIVALS-66): the list's row TEXT names, read from the names list row by row (nothing
 * held), and chosen as in the box; several rows: how many and the first names, the player stays where he is */
int AW_TpPlacesFind(const char *text){
    FILE *f=NULL;long size,row,matches=0,listed;char list[160];const char *p;
    size=COM_FOpenFile((char *)names_path,&f);
    if(size<AW_TPN_HEADER || !f){if(f)fclose(f);return 0;}
    row=AW_TpNamesFind(f,ftell(f),size,text,&matches,list,sizeof(list));
    fclose(f);
    if(row>=0){chosen(NULL,(int)row);return 1;}
    if(row==-2){
        for(listed=list[0]?1:0,p=list;*p;p++)if(*p==';')listed++;
        Con_Printf("dbg tp: %ld places hold \"%s\": %s%s. Type more of the name, or dbg tp alone for the list.\n",
            matches,text,list,listed<matches?(listed?"; ...":"..."):"");
        return 1;
    }
    return 0;
}
/* ------------------------------------------------------------------------ beings (DBG-TP-TO-NPC-66) */
static struct {
    int active;
    char id[AW_TP_ID],map[AW_TP_MAP],name[AW_TP_NAME];
    float point[3];          /* the being's placed point: room map units, or global units outdoors */
} want;

static const char *edict_id(edict_t *e){
    eval_t *v=GetEdictFieldValue(e,"aw_source_id");
    return v && v->string?pr_strings+v->string:"";
}
static edict_t *player(void){
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict)return NULL;
    return svs.clients[0].edict;
}
/* The live being: an actor of the loaded scene with the record id, the one nearest NEAR (any when NEAR is NULL). */
static edict_t *live_being(const char *id,const float *near){
    int i;edict_t *e,*best=NULL;float d,bd=0;vec3_t delta;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free || e->v.health<=0 || Q_strcasecmp((char *)edict_id(e),(char *)id))continue;
        if(!near)return e;
        VectorSubtract(e->v.origin,near,delta);delta[2]=0;d=DotProduct(delta,delta);
        if(!best || d<bd){best=e;bd=d;}
    }
    return best;
}
/* A spot for the player's hull beside BEING that is free (no wall, table or actor) and has a floor below it. */
typedef struct {edict_t *p,*being;} spot_ctx_t;
/* the player's hull at POINT: free of the map and every actor, the way from the being open (never through a wall),
 * a floor within 64 units below; OUT the standing point */
static int hull_free(void *ctx,const float *point,float *out){
    spot_ctx_t *c=(spot_ctx_t *)ctx;edict_t *p=c->p;vec3_t cand,down,centre;trace_t t;
    VectorCopy(c->being->v.origin,centre);VectorCopy(point,cand);
    cand[2]=centre[2]+(p->v.mins[2]-c->being->v.mins[2])+1;
    /* the player's own box (tests/test_engine_hulls.py: an entity's own box, named as one) */
    t=SV_Move(cand,p->v.mins,p->v.maxs,cand,MOVE_NORMAL,p);
    if(t.startsolid || t.allsolid)return 0;
    t=SV_Move(centre,vec3_origin,vec3_origin,cand,MOVE_NOMONSTERS,c->being);
    if(t.fraction<1)return 0;
    VectorCopy(cand,down);down[2]-=64;
    t=SV_Move(cand,p->v.mins,p->v.maxs,down,MOVE_NORMAL,p);
    if(t.allsolid || t.fraction>=1)return 0;
    VectorCopy(t.endpos,out);
    return 1;
}
static int free_spot(edict_t *p,edict_t *being,vec3_t out){
    spot_ctx_t c;float radius;
    c.p=p;c.being=being;
    radius=(being->v.maxs[0]>being->v.maxs[1]?being->v.maxs[0]:being->v.maxs[1])+p->v.maxs[0]+8;
    if(radius<40)radius=40;
    return AW_TpPickSpot(being->v.origin,p->v.origin,radius,hull_free,&c,out)>0;
}
static int place_beside(edict_t *p,edict_t *being){
    vec3_t spot;
    if(!free_spot(p,being,spot)){
        Con_Printf("Teleport: no free spot beside %s; you stand where the teleport put you.\n",want.name);
        return 0;
    }
    VectorCopy(spot,p->v.origin);VectorCopy(spot,p->v.oldorigin);VectorCopy(vec3_origin,p->v.velocity);
    p->v.angles[0]=0;p->v.angles[1]=AW_TpFacingYaw(spot,being->v.origin);p->v.angles[2]=0;
    VectorCopy(p->v.angles,p->v.v_angle);p->v.fixangle=1;
    SV_LinkEdict(p,false);
    Con_Printf("Teleport: beside %s (%ld %ld %ld)\n",want.name,(long)spot[0],(long)spot[1],(long)spot[2]);
    return 1;
}
void AW_TpBeingArrive(void){
    edict_t *p=player(),*being;
    if(!want.active || !p)return;
    if(AW_SceneStarting())return;           /* the load is still on: the spawn calls again */
    want.active=0;
    being=live_being(want.id,p->v.origin);
    if(!being){Con_Printf("Teleport: %s is not in this scene now; you stand at its place.\n",want.name);return;}
    place_beside(p,being);
}
static void arrive_command(void){AW_TpBeingArrive();}
/* the nearest placement of a common kind: in the loaded room first, then outdoors nearest the player (in a room:
 * the first outdoor one) */
static int nearest_kind(const char *kind,aw_tp_place_t *out){
    FILE *f=NULL;long size,n,i;unsigned char *data;aw_tp_place_t r;char name[MAX_QPATH];edict_t *p=player();
    float here[3],d,bd=0;int found=0,have_here,best_room=0;
    Q_snprintf(name,sizeof(name),"tpk/%s.tpk",kind);
    size=COM_FOpenFile(name,&f);
    if(size<AW_TPK_HEADER || size>65536L*AW_TPK_ROW || !f){if(f)fclose(f);return 0;}
    if(!(data=(unsigned char *)AW_TryMalloc((unsigned long)size))){fclose(f);return 0;}
    n=(long)fread(data,1,(size_t)size,f)==size?AW_TpKindRows(data,size):-1;
    fclose(f);
    have_here=p && AW_WorldToSource(sv.name,p->v.origin,here);
    for(i=0;i<n;i++){
        AW_TpKindRow(data,i,&r);
        if(r.map[0]){
            if(p && !strcmp(r.map,sv.name)){
                d=(r.x-p->v.origin[0])*(r.x-p->v.origin[0])+(r.y-p->v.origin[1])*(r.y-p->v.origin[1]);
                if(!best_room || d<bd){*out=r;bd=d;best_room=found=1;}
            }
            continue;
        }
        if(best_room)continue;
        d=have_here?((float)r.x-here[0])*((float)r.x-here[0])+((float)r.y-here[1])*((float)r.y-here[1]):0;
        if(!found || d<bd){*out=r;bd=d;found=1;}
    }
    if(!found && n>0)AW_TpKindRow(data,0,out);   /* only rooms elsewhere: the first */
    free(data);
    return found || n>0;
}
void AW_TpBeingGo(const aw_tp_place_t *row){
    aw_tp_place_t r=*row;edict_t *p=player(),*being;float point[3],here[3],local[3];
    if(!p){Con_Printf("dbg tp: start a game first.\n");return;}
    if(r.flags&AW_TP_NEAREST){
        if(!nearest_kind(r.map,&r)){Con_Printf("Teleport: no %s on this disk.\n",row->name);return;}
    }
    memset(&want,0,sizeof(want));
    /* the same sizes as the row's, which always end in a NUL (AW_TpPlacesRow, AW_TpKindRow) */
    memcpy(want.id,r.id,sizeof(want.id));memcpy(want.map,r.map,sizeof(want.map));
    memcpy(want.name,row->name,sizeof(want.name));
    point[0]=(float)r.x;point[1]=(float)r.y;point[2]=(float)r.z;VectorCopy(point,want.point);
    Con_Printf("Teleport: %s\n",row->name);
    /* loaded already: where it stands now (a walker), no load */
    if(r.map[0] && !strcmp(r.map,sv.name) && (being=live_being(r.id,point))!=NULL){place_beside(p,being);return;}
    if(!r.map[0] && AW_WorldToSource(sv.name,p->v.origin,here)){
        int i;edict_t *e;
        for(i=1;i<sv.num_edicts;i++){
            e=EDICT_NUM(i);
            if(e->free || e->v.health<=0 || Q_strcasecmp((char *)edict_id(e),r.id) ||
               !AW_WorldToSource(sv.name,e->v.origin,local))continue;
            if(fabs(local[0]-point[0])<2048 && fabs(local[1]-point[1])<2048){place_beside(p,e);return;}
        }
    }
    want.active=1;
    if(r.map[0]){
        /* the room is loaded the way a door loads it, so the arrival is a door's: the player's origin over the
         * being's floor, never its feet (TP-BEING-TRIBUNAL-FALLS-THROUGH-67) */
        float arrival[3];
        AW_TpBeingArrival(point,p->v.mins[2],arrival);
        if(!AW_SceneLoadRoom(r.map,arrival,0)){
            want.active=0;Con_Printf("Teleport: %s's room is not on this disk.\n",row->name);
        }
        return;
    }
    if(!AW_MapTeleportAt(point,1)){
        want.active=0;Con_Printf("Teleport: no map on this disk holds %s.\n",row->name);return;
    }
    Cbuf_AddText("aw_tp_being_arrive\n");   /* a teleport inside the loaded map: no spawn follows */
}
/* DBG-TP-LORDVIVEC-69 (dbg tp lordvivec): a named place that is a being. Its row of tp-places.lut is found by the
 * record id, row by row (aw_listbox_rules.c AW_TpPlacesBeingRow: one row's bytes on the stack, nothing allocated, the
 * file closed before the teleport), and taken as the list's Beings row is: beside it, facing it. */
int AW_TpBeingByIdGo(const char *id){
    FILE *f=NULL;long size,row;aw_tp_place_t p;
    size=COM_FOpenFile((char *)path,&f);
    if(size<AW_TP_HEADER || !f){if(f)fclose(f);return 0;}
    row=AW_TpPlacesBeingRow(f,ftell(f),size,id,&p);
    fclose(f);
    if(row<0)return 0;
    AW_TpBeingGo(&p);
    return 1;
}
static void reset_being(int new_game){(void)new_game;memset(&want,0,sizeof(want));}
void AW_TpPlacesInit(void){
    Cvar_RegisterVariable(&lowmem);
    AW_ResetRegister("dbg tp being arrival",reset_being,NULL);
    {extern void (*aw_tp_being_arrive)(void);aw_tp_being_arrive=AW_TpBeingArrive;}
    Cmd_AddCommand("aw_tp_being_arrive",arrive_command);
}
