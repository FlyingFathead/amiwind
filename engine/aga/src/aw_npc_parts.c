/* SPDX-License-Identifier: GPL-2.0-or-later
 * Residents drawn from parts (NPC-PARTS-RUNTIME-59, docs/MODULAR_NPCS.md "Stage: residents from parts"): the player's
 * assembled body (aw_view.c parts_ready, aw_player_parts.c) generalised to any resident. The builder writes each
 * resident's recipe (AWNP1: race, sex, head, hair, the worn items) into the small table of the place it stands in
 * (view/npc_parts/<key>.awnb, one per exterior cell and per room, held only while that place is loaded: see the
 * tables below); the parts library and the body recipe (progs/parts/, view/parts.txt) are the player's. A resident's
 * parts are assembled once, when it is first drawn (several residents per body recipe read), and kept in a small table by its id; per
 * frame only its entity is copied once per part, every part at the resident's own table frame and placement.
 * The resident's fused model stays its server model (collision, items, animation, the head): only its drawing is
 * replaced, and only when the fused model is on the very table the parts name (a female resident's own female table
 * is not the parts' table yet: it keeps its fused model). aw_npc_parts 0 = every resident fused, the previous way. */
#include "quakedef.h"
#include "r_local.h"
#include "aw_skel.h"
#include "aw_player_parts.h"
#include "aw_tryalloc.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define NP_CACHE 96          /* residents' assembled parts kept (by id) */
#define NP_ENTS 384          /* part entities drawn in one frame */
#define NP_PER_FRAME 12      /* assemblies in one frame at most (each reads nothing more: one read per frame) */

typedef struct {
    char id[AW_PARTS_ID];
    int state;               /* 0 unused, 1 parts, -1 none (the fused model draws) */
    int count;
    float weight, height;
    model_t *models[AW_PARTS_MAX];
    char paths[AW_PARTS_MAX][AW_PARTS_PATH];
    const aw_skel_table_t *table;
    unsigned used;
} np_entry_t;

/* off by default (the fused models), not saved; dbg camera npcs on/off (aw_view.c): no cvar or command of its own,
 * the resident registry budget (tests/resident_registry_budget.json) */
static int npc_parts_on=0;
static np_entry_t cache[NP_CACHE];
static unsigned clock_tick;
static entity_t ents[NP_ENTS];
static struct {entity_t *at;entity_t *original;} swapped[NP_ENTS];
static int ent_count,swap_count,ent_list_start;
static int last_actors,last_parts,last_fused,last_skipped,built,refused,no_file;
static double last_ms,build_ms;

/* our entities out of the list again (the guard torch does the same: a paused renderer reuses its list) */
static void restore_list(void)
{
    int i,j,n=0;
    for(j=0;j<swap_count;j++)
        for(i=0;i<cl_numvisedicts;i++)
            if(cl_visedicts[i]==swapped[j].at){cl_visedicts[i]=swapped[j].original;break;}
    for(i=0;i<cl_numvisedicts;i++){
        entity_t *e=cl_visedicts[i];
        if(e>=ents && e<ents+NP_ENTS)continue;
        cl_visedicts[n++]=e;
    }
    cl_numvisedicts=n;swap_count=ent_count=0;(void)ent_list_start;
}

static edict_t *resident_of(entity_t *ent)
{
    uintptr_t ptr=(uintptr_t)ent,base=(uintptr_t)cl_entities,offset;int index;edict_t *e;
    if(ptr<base)return NULL;
    offset=ptr-base;
    if(offset%sizeof(entity_t) || offset/sizeof(entity_t)>=MAX_EDICTS)return NULL;
    index=(int)(offset/sizeof(entity_t));if(index<=0 || index>=sv.num_edicts)return NULL;
    e=EDICT_NUM(index);
    if(e->free || !e->v.classname || strcmp(pr_strings+e->v.classname,"aw_npc"))return NULL;
    return e;
}

static np_entry_t *find(const char *id)
{
    int i;
    for(i=0;i<NP_CACHE;i++)if(cache[i].state && !Q_strcasecmp(cache[i].id,(char *)id))return &cache[i];
    return NULL;
}

static np_entry_t *slot_for(const char *id)
{
    int i,best=0;
    for(i=0;i<NP_CACHE;i++){
        if(!cache[i].state){best=i;break;}
        if(cache[i].used<cache[best].used)best=i;
    }
    memset(&cache[best],0,sizeof(cache[best]));
    Q_strncpy(cache[best].id,(char *)id,AW_PARTS_ID-1);
    return &cache[best];
}

/* The residents' recipes per place (BUILD-NPC-RECIPES-PER-CELL-59): one small table per exterior cell and per room
 * (binary, searched by id hash: the cells' in one pack, view/npc_parts/cells.awnp, whose index is held once read; a
 * room's in view/npc_parts/<map>.awnb), read with one read when the place's actors arrive (aw_actors.c: a cell's frame joining the streamer's
 * window, when its residents are queued; a room on entering it) and freed when the place goes; nothing island-wide is
 * held. The places in now are known even while residents from parts are off (no read then); turning them on reads
 * the tables of the places in now. A new map lets every table go. */
static aw_npc_tables_t tables;
static struct {char key[AW_PARTS_ID];int cell,cx,cy;} places[AW_NPC_TABLES];
static int n_places;
/* the exterior cells' pack (view/npc_parts/cells.awnp): its index read once and held, the file kept open (one seek and
 * one read per cell); state 0 not tried, 1 open, -1 none in this image */
static int pack_state;
static FILE *pack_file;
static long pack_base,pack_index_bytes;
static unsigned char *pack_index;

static int pack_open(void)
{
    unsigned char head[8];long n;
    if(pack_state)return pack_state>0;
    pack_state=-1;
    COM_FOpenFile("view/npc_parts/cells.awnp",&pack_file);
    if(!pack_file)return 0;
    pack_base=ftell(pack_file);
    if(fread(head,1,8,pack_file)!=8 || (n=AW_NpcPackIndexBytes(head))<8 ||
       !(pack_index=(unsigned char *)AW_TryMalloc((unsigned long)n))){fclose(pack_file);pack_file=NULL;return 0;}
    memcpy(pack_index,head,8);
    if(n>8 && fread(pack_index+8,1,(size_t)(n-8),pack_file)!=(size_t)(n-8)){
        free(pack_index);pack_index=NULL;fclose(pack_file);pack_file=NULL;return 0;}
    pack_index_bytes=n;pack_state=1;
    Con_Printf("Residents from parts: cells pack index in (%ld cells, %ld bytes).\n",(n-8)/12,n);
    return 1;
}
static char tables_map[64];
static unsigned long table_loads,table_frees,table_missing,table_read_bytes;
static double table_ms;

/* NPC-RECIPES-PER-AREA-59: the same tables on the shared per-area layout (id1/npc-parts.awa, tools/prepare_area_tables.py
 * build_recipes; the layout of areas.awa and npc-ambient.awa, the same area keys). Its index (12 bytes an area) and its
 * resident directory (8 bytes a resident) are held once read, the file kept open; an area's table costs one seek and
 * one read when the place changes (AW_AreaPlaceKeys: the room, or the 3 x 3 exterior cells, as the container and
 * Wander tables) or when a cell's residents arrive (the streamer's window, AW_NpcPartsCell), never in the middle of
 * play: a resident whose table is not in draws fused and waits for the next place change or arrival, where the
 * directory names its one area (a narrow load, counted). aw_npc_tables_areas 1 (the default, id1/default-game.cfg);
 * 0 = the earlier files (view/npc_parts/cells.awnp, <map>.awnb, dir.awnd), kept for the A/B. */
static cvar_t tables_areas_cvar={"aw_npc_tables_areas","1"};
int AW_AreaPlaceKeys(unsigned long *keys,int max,unsigned long *generation);   /* aw_inventory.c */
static int awr_state;              /* 0 not tried, 1 open, -1 none in this image */
static FILE *awr_file;
static long awr_base,awr_length;
static unsigned char *awr_index,*awr_dir;
static unsigned long awr_areas,awr_dir_n;
static int areas_on;               /* the method the tables held now were read with */
static unsigned long area_now[9],area_gen;static int area_now_n,area_synced;
#define NP_PENDING 16
static char pending[NP_PENDING][AW_PARTS_ID];static int n_pending;
static unsigned long area_loads,area_misses,area_narrow,area_narrow_none;

static int awr_ready(void)
{
    unsigned char head[AW_NPC_AREA_HEAD];unsigned long dir_at;
    if(awr_state)return awr_state>0;
    awr_state=-1;
    awr_length=COM_FOpenFile("npc-parts.awa",&awr_file);
    if(!awr_file)return 0;
    awr_base=ftell(awr_file);
    if(fread(head,1,sizeof(head),awr_file)!=sizeof(head) ||
       !AW_NpcAreaHead(head,(unsigned long)awr_length,&awr_areas,&dir_at,&awr_dir_n) ||
       !(awr_index=(unsigned char *)AW_TryMalloc(awr_areas*12+1)) ||
       !(awr_dir=(unsigned char *)AW_TryMalloc(awr_dir_n*8+1)) ||
       fread(awr_index,1,awr_areas*12,awr_file)!=awr_areas*12 ||
       fread(awr_dir,1,awr_dir_n*8,awr_file)!=awr_dir_n*8){
        if(awr_index)free(awr_index);
        if(awr_dir)free(awr_dir);
        awr_index=awr_dir=NULL;fclose(awr_file);awr_file=NULL;
        Con_Printf("Residents from parts: npc-parts.awa is not a pack this engine reads; the earlier files answer.\n");
        return 0;
    }
    awr_state=1;
    Con_Printf("Residents from parts: area pack in (%lu areas, %lu residents; index %lu bytes, directory %lu bytes).\n",
        awr_areas,awr_dir_n,awr_areas*12,awr_dir_n*8);
    return 1;
}

/* area AT/SIZE of the pack into fresh memory (NULL: no read) */
static unsigned char *awr_read(unsigned long at,unsigned long size,int *bytes)
{
    unsigned char *text;
    if(size<12 || at+size>(unsigned long)awr_length || size>1024*1024ul)return NULL;
    if(!(text=(unsigned char *)AW_TryMalloc(size)))return NULL;
    if(fseek(awr_file,awr_base+(long)at,SEEK_SET) || fread(text,1,size,awr_file)!=size){free(text);return NULL;}
    *bytes=(int)size;
    return text;
}

static int areas_wanted(void){return tables_areas_cvar.value!=0 && awr_ready();}

/* the recently left places' tables and the narrow-loaded ones (narrow_find): kept while they fit, the oldest let go
 * first; a fixed small budget for now (NP_ASIDE tables, NP_ASIDE_BYTES), not yet sized from free memory */
#define NP_ASIDE 16
#define NP_ASIDE_BYTES 65536L
static aw_npc_tables_t aside;
static unsigned long table_reuses;

static void table_free_all(void)
{
    unsigned char *text;
    while((text=AW_NpcTablesPop(&tables,NULL))!=NULL){free(text);table_frees++;}
    while((text=AW_NpcTablesPop(&aside,NULL))!=NULL){free(text);table_frees++;}
}

static void place_out(const char *key);

/* a new map: every place of the last one goes */
static void tables_map_check(void)
{
    if(!strncmp(tables_map,sv.name,sizeof(tables_map)-1))return;
    Q_strncpy(tables_map,sv.name,sizeof(tables_map)-1);
    /* the keys name places island-wide (cell grid numbers, room map names): the last map's tables join the recently
     * left ones, so stepping out of a room and back in reads nothing */
    while(n_places)place_out(places[n_places-1].key);
    n_places=0;
}

/* forget the residents that found no recipe (their place's table was not in yet): they are looked up again */
static void forget_unfound(void)
{
    int i;
    for(i=0;i<NP_CACHE;i++)if(cache[i].state<0)memset(&cache[i],0,sizeof(cache[i]));
}

/* one place's table into fresh memory (NULL when the place has none): a cell's from the pack with one seek and one
 * read, a room's from its own file with one read */
static unsigned char *table_read(const char *key,int cell,int cx,int cy,int *bytes)
{
    char path[MAX_QPATH];FILE *f=NULL;unsigned char *text;
    if(cell==2){       /* an area of npc-parts.awa ("a" + its key) */
        unsigned long akey,at,size;
        if(!awr_ready() || !AW_NpcAreaKeyOf(key,&akey) || !AW_NpcAreaFind(awr_index,awr_areas,akey,&at,&size,NULL))
            return NULL;
        return awr_read(at,size,bytes);
    }
    if(cell){
        unsigned long at,size;
        if(!pack_open() || !AW_NpcPackFind(pack_index,pack_index_bytes,cx,cy,&at,&size))return NULL;
        *bytes=(int)size;
        text=size>=12?(unsigned char *)AW_TryMalloc(size):NULL;
        if(!text || fseek(pack_file,pack_base+(long)at,SEEK_SET) || fread(text,1,size,pack_file)!=size){
            if(text)free(text);
            return NULL;
        }
        return text;
    }
    sprintf(path,"view/npc_parts/%.40s.awnb",key);
    *bytes=COM_FOpenFile(path,&f);
    if(!f)return NULL;
    text=*bytes>=12?(unsigned char *)AW_TryMalloc((unsigned long)*bytes):NULL;
    if(!text || fread(text,1,(size_t)*bytes,f)!=(size_t)*bytes){fclose(f);if(text)free(text);return NULL;}
    fclose(f);
    return text;
}

static void key_load(const char *key,int cell,int cx,int cy)
{
    int bytes=0,lines;unsigned char *text;double t0=Sys_FloatTime();
    if(AW_NpcTablesHas(&tables,key))return;
    {   /* a place left a moment ago: its table back from the recently left cache, no read */
        long kept;unsigned char *back=AW_NpcTablesDrop(&aside,key,&kept);
        if(back){
            if(AW_NpcTablesAdd(&tables,key,back,kept)!=1)free(back);
            else{table_reuses++;Con_Printf("Residents from parts: table %s in again from the recently left cache (%ld bytes, no read).\n",key,kept);}
            forget_unfound();return;
        }
    }
    /* no table: no resident of this place from parts, they keep their fused models */
    if(!(text=table_read(key,cell,cx,cy,&bytes))){table_missing++;return;}
    if(AW_NpcTablesAdd(&tables,key,text,bytes)!=1){free(text);table_missing++;return;}
    lines=AW_NpcTableCount(text,bytes);
    table_loads++;table_read_bytes+=bytes;if(cell==2)area_loads++;
    {double ms=(Sys_FloatTime()-t0)*1000;table_ms+=ms;
    Con_Printf("Residents from parts: table %s in (%d residents, %d bytes, %.1f ms); held %d tables, %ld bytes.\n",
        key,lines,bytes,ms,tables.count,tables.bytes);}
    forget_unfound();
}

/* A resident outside the places loaded now (a script moved it, it followed the player): the resident directory
 * (view/npc_parts/dir.awnd, id hash -> place, read once on the first such lookup) names its place, and only that
 * place's table is read, into the small cache of recently left places. Nothing
 * else is read or searched. */
static unsigned char *dir_data;
static long dir_bytes;
static int dir_state;
static unsigned long narrow_loads;

static int dir_open(void)
{
    FILE *f=NULL;int bytes;
    if(dir_state)return dir_state>0;
    dir_state=-1;
    bytes=COM_FOpenFile("view/npc_parts/dir.awnd",&f);
    if(!f)return 0;
    dir_data=bytes>=8?(unsigned char *)AW_TryMalloc((unsigned long)bytes):NULL;
    if(!dir_data || fread(dir_data,1,(size_t)bytes,f)!=(size_t)bytes || !AW_NpcDirCount(dir_data,bytes)){
        fclose(f);if(dir_data)free(dir_data);dir_data=NULL;return 0;}
    fclose(f);dir_bytes=bytes;dir_state=1;
    Con_Printf("Residents from parts: resident directory in (%d residents, %d bytes).\n",AW_NpcDirCount(dir_data,bytes),bytes);
    return 1;
}

static int narrow_find(const char *id,aw_parts_npc_t *out)
{
    char key[AW_PARTS_ID];int cell,cx=0,cy=0,bytes=0;unsigned char *text;double t0;
    if(AW_NpcTablesFind(&aside,id,out))return 1;
    if(!dir_open() || !AW_NpcDirFind(dir_data,dir_bytes,id,key,sizeof(key)) || AW_NpcTablesHas(&tables,key))return 0;
    t0=Sys_FloatTime();
    cell=AW_NpcCellOfKey(key,&cx,&cy);
    if(!(text=table_read(key,cell,cx,cy,&bytes)))return 0;
    while(aside.count && (aside.count>=NP_ASIDE || aside.bytes+bytes>NP_ASIDE_BYTES))
        free(AW_NpcTablesDrop(&aside,aside.t[0].key,NULL));
    if(AW_NpcTablesAdd(&aside,key,text,bytes)!=1){free(text);return 0;}
    narrow_loads++;table_read_bytes+=bytes;
    Con_Printf("Residents from parts: %s is outside the loaded places: table %s narrow-loaded (%d bytes, %.1f ms).\n",
        id,key,bytes,(Sys_FloatTime()-t0)*1000);
    return AW_NpcTablesFind(&aside,id,out);
}

/* the table key place P's table is held under by the method in use (*CELL: how table_read reads it); 0 = none: a room
 * under the area method (its table comes with the place, areas_sync) */
static int place_table(int p,char *key,int *cell)
{
    if(areas_on){
        if(!places[p].cell)return 0;
        AW_NpcAreaKeyName(AW_NpcAreaCellKey(places[p].cx,places[p].cy),key,AW_PARTS_ID);*cell=2;return 1;
    }
    Q_strncpy(key,places[p].key,AW_PARTS_ID-1);key[AW_PARTS_ID-1]=0;*cell=places[p].cell;
    return 1;
}

/* 1 while a place in now (an arrival, or under the area method the place's areas) still wants table KEY */
static int key_wanted(const char *key)
{
    char k[AW_PARTS_ID];int i,c;
    for(i=0;i<n_places;i++)if(place_table(i,k,&c) && !strcmp(k,key))return 1;
    if(areas_on)for(i=0;i<area_now_n;i++){AW_NpcAreaKeyName(area_now[i],k,sizeof(k));if(!strcmp(k,key))return 1;}
    return 0;
}

static void key_out(const char *key);

/* the residents that found no table under the area method, resolved by the directory: each its one area read into
 * the recently left cache (a narrow load). Called only at a place change or an arrival, never in play. */
static void pending_resolve(void)
{
    int i,bytes=0;char k[AW_PARTS_ID];unsigned char *text;double t0;
    if(!n_pending)return;
    for(i=0;i<n_pending;i++){
        long a=awr_state>0?AW_NpcAreaDirFind(awr_dir,awr_dir_n,pending[i]):-1;
        const unsigned char *e;unsigned long akey,at,size;
        if(a<0 || (unsigned long)a>=awr_areas){area_narrow_none++;continue;}
        e=awr_index+12*a;akey=(unsigned long)e[0]|(unsigned long)e[1]<<8|(unsigned long)e[2]<<16|(unsigned long)e[3]<<24;
        at=(unsigned long)e[4]|(unsigned long)e[5]<<8|(unsigned long)e[6]<<16|(unsigned long)e[7]<<24;
        size=(unsigned long)e[8]|(unsigned long)e[9]<<8|(unsigned long)e[10]<<16|(unsigned long)e[11]<<24;
        AW_NpcAreaKeyName(akey,k,sizeof(k));
        if(AW_NpcTablesHas(&tables,k) || AW_NpcTablesHas(&aside,k))continue;
        t0=Sys_FloatTime();
        if(!(text=awr_read(at,size,&bytes)))continue;
        while(aside.count && (aside.count>=NP_ASIDE || aside.bytes+bytes>NP_ASIDE_BYTES)){
            free(AW_NpcTablesDrop(&aside,aside.t[0].key,NULL));table_frees++;}
        if(AW_NpcTablesAdd(&aside,k,text,bytes)!=1){free(text);continue;}
        area_narrow++;table_read_bytes+=bytes;
        Con_Printf("Residents from parts: %s is outside the loaded areas: area %s narrow-loaded at the place change "
            "(%d bytes, %.1f ms).\n",pending[i],k,bytes,(Sys_FloatTime()-t0)*1000);
    }
    n_pending=0;
    forget_unfound();
}

/* a resident not in the tables held now under the area method: drawn fused, its area looked up at the next place
 * change or arrival (pending_resolve) */
static void pending_add(const char *id)
{
    int i;
    area_misses++;
    for(i=0;i<n_pending;i++)if(!Q_strcasecmp(pending[i],(char *)id))return;
    if(n_pending<NP_PENDING){Q_strncpy(pending[n_pending],(char *)id,AW_PARTS_ID-1);pending[n_pending][AW_PARTS_ID-1]=0;n_pending++;}
}

/* the place's areas (AW_AreaPlaceKeys: the room, or the 3 x 3 exterior cells) in step with the tables under the area
 * method: those that came in read (one seek and one read each, only areas the pack has), those gone let go unless an
 * arrival still wants them; FORCE: read again even when the place has not moved */
static void areas_sync(int force)
{
    unsigned long keys[9],gen,old[9],at,size;int n,i,j,n_old;char k[AW_PARTS_ID];
    if(!areas_on || !sv.active || (n=AW_AreaPlaceKeys(keys,9,&gen))<0)return;
    if(!force && area_synced && gen==area_gen)return;
    tables_map_check();
    n_old=area_now_n;memcpy(old,area_now,sizeof(old));
    memcpy(area_now,keys,sizeof(unsigned long)*(size_t)n);area_now_n=n;area_gen=gen;area_synced=1;
    if(!npc_parts_on)return;
    for(i=0;i<n_old;i++){
        for(j=0;j<n;j++)if(keys[j]==old[i])break;
        if(j<n)continue;
        AW_NpcAreaKeyName(old[i],k,sizeof(k));
        if(!key_wanted(k))key_out(k);
    }
    for(i=0;i<n;i++)
        if(AW_NpcAreaFind(awr_index,awr_areas,keys[i],&at,&size,NULL)){AW_NpcAreaKeyName(keys[i],k,sizeof(k));key_load(k,2,0,0);}
    pending_resolve();
}

/* every table of the places in now read by the method in use */
static void load_all(void)
{
    int i,c;char k[AW_PARTS_ID];
    for(i=0;i<n_places;i++)if(place_table(i,k,&c))key_load(k,c,places[i].cx,places[i].cy);
    areas_sync(1);
}

/* aw_npc_tables_areas changed (or first seen): the tables held go and the places' tables are read by the other method */
static void method_check(void)
{
    int want=areas_wanted();
    if(want==areas_on)return;
    table_free_all();forget_unfound();
    areas_on=want;area_synced=0;area_now_n=0;n_pending=0;
    Con_Printf("Residents from parts: recipe tables from %s.\n",areas_on?"the area pack (npc-parts.awa)":"the earlier files");
    if(npc_parts_on && sv.active)load_all();
}

static void place_in(const char *key,int cell,int cx,int cy)
{
    int i,c;char k[AW_PARTS_ID];
    if(!sv.active)return;
    tables_map_check();
    for(i=0;i<n_places;i++)if(!strcmp(places[i].key,key))break;
    if(i==n_places){
        if(n_places>=AW_NPC_TABLES)return;
        Q_strncpy(places[i].key,(char *)key,AW_PARTS_ID-1);places[i].cell=cell;places[i].cx=cx;places[i].cy=cy;n_places++;
    }
    if(npc_parts_on && place_table(i,k,&c))key_load(k,c,cx,cy);
    if(npc_parts_on && areas_on)pending_resolve();       /* an arrival: a moment the area method may read */
}

static void place_out(const char *key)
{
    int i,c;char k[AW_PARTS_ID];
    if(!sv.active)return;
    tables_map_check();
    Q_strncpy(k,(char *)key,AW_PARTS_ID-1);k[AW_PARTS_ID-1]=0;
    for(i=0;i<n_places;i++)if(!strcmp(places[i].key,key)){
        if(!place_table(i,k,&c))k[0]=0;
        if(i!=--n_places)places[i]=places[n_places];
        break;
    }
    if(k[0] && !key_wanted(k))key_out(k);
}

static void key_out(const char *key)
{
    long bytes=0;unsigned char *text;
    if((text=AW_NpcTablesDrop(&tables,key,&bytes))!=NULL){
        /* KEEP WHAT YOU CAN AFFORD: the left place's table goes into the small cache of recently left places (and of
         * narrow loads), the oldest let go first; coming back reads nothing */
        while(aside.count && (aside.count>=NP_ASIDE || aside.bytes+bytes>NP_ASIDE_BYTES)){
            free(AW_NpcTablesDrop(&aside,aside.t[0].key,NULL));table_frees++;}
        if(AW_NpcTablesAdd(&aside,key,text,bytes)!=1){free(text);table_frees++;}
        Con_Printf("Residents from parts: table %s out (%ld bytes, kept among %d recently left, %ld bytes); held %d "
            "tables, %ld bytes.\n",key,bytes,aside.count,aside.bytes,tables.count,tables.bytes);
    }
}

/* aw_actors.c: an exterior cell's actors arrive (IN 1) or go (IN 0) */
void AW_NpcPartsCell(int cx,int cy,int in)
{
    char key[AW_PARTS_ID];
    AW_NpcTableCellKey(cx,cy,key,sizeof(key));
    if(in)place_in(key,1,cx,cy);else place_out(key);
}

/* aw_actors.c: a room entered (its map name; the room's table goes with the map) */
void AW_NpcPartsRoom(const char *map)
{
    place_in(map,0,0,0);
}

/* the parts of the residents in NEEDS (ids), from the tables held now and one read of the body recipe */
static void assemble(const char *const *needs,int n)
{
    int mark=Hunk_LowMark(),i,j,size_body=0;byte *body_text;double t0=Sys_FloatTime();
    body_text=COM_LoadHunkFile("view/parts.txt");size_body=com_filesize;
    if(!body_text)no_file=1;
    for(i=0;i<n;i++){
        np_entry_t *e=slot_for(needs[i]);aw_parts_npc_t npc;aw_parts_body_t body;const char *items[AW_PARTS_ITEMS];
        e->state=-1;e->used=clock_tick;
        if(!body_text)continue;
        if(!AW_NpcTablesFind(&tables,needs[i],&npc)){
            /* the area method reads nothing here, in play: the cache, else the next place change or arrival */
            if(areas_on){if(!AW_NpcTablesFind(&aside,needs[i],&npc)){pending_add(needs[i]);continue;}}
            else if(!narrow_find(needs[i],&npc))continue;
        }
        for(j=0;j<npc.count;j++)items[j]=npc.items[j];
        if(!AW_PartsAssemble((const char *)body_text,size_body,npc.race,npc.female,npc.head,npc.hair,items,npc.count,&body) ||
           !(e->table=AW_SkelTableFor(body.table))){refused++;continue;}
        for(j=0;j<body.count;j++)strcpy(e->paths[j],body.model[j]);
        e->count=body.count;e->weight=body.weight;e->height=body.height;e->state=1;built++;
    }
    Hunk_FreeToLowMark(mark);
    build_ms+=(Sys_FloatTime()-t0)*1000;
}

/* the entry's part models loaded and in the cache (a reload here, outside the renderer, when the cache let one go) */
static int models_ready(np_entry_t *e)
{
    int i;
    for(i=0;i<e->count;i++){
        model_t *m=e->models[i];aliashdr_t *h;
        if(m && !strcmp(m->name,e->paths[i]) && !m->needload && Cache_Check(&m->cache))continue;
        m=Mod_ForName(e->paths[i],false);
        h=m && m->type==mod_alias?(aliashdr_t *)Mod_Extradata(m):NULL;
        if(!h || !h->aw_skel || (const void *)h->aw_skel_table!=(const void *)e->table){
            Con_Printf("Resident %s from parts: part %s not drawn (%s); the fused model draws.\n",e->id,e->paths[i],
                !m?"not in this image":!h?"not a model":"not on the parts' table");
            e->state=-1;refused++;return 0;
        }
        e->models[i]=m;
    }
    return 1;
}

void AW_NpcPartsUpdate(void)
{
    const char *needs[NP_PER_FRAME];int i,k,initial,n_needs=0;double t0;
    restore_list();
    last_actors=last_parts=last_fused=last_skipped=0;
    if(!npc_parts_on || no_file || !sv.active || cls.state!=ca_connected || svs.maxclients!=1)return;
    t0=Sys_FloatTime();clock_tick++;
    method_check();areas_sync(0);      /* NPC-RECIPES-PER-AREA-59: one generation compare a frame; reads only on a place change */
    initial=cl_numvisedicts;
    /* first the residents not met yet: their parts assembled together (one read of each recipe) */
    for(i=0;i<initial && n_needs<NP_PER_FRAME;i++){
        entity_t *ent=cl_visedicts[i];edict_t *a;eval_t *source;
        if(!ent || !ent->model || ent->model->type!=mod_alias || !(a=resident_of(ent)))continue;
        source=GetEdictFieldValue(a,"aw_source_id");
        if(!source || !source->string || !pr_strings[source->string] || find(pr_strings+source->string))continue;
        for(k=0;k<n_needs;k++)if(!Q_strcasecmp((char *)needs[k],pr_strings+source->string))break;
        if(k==n_needs)needs[n_needs++]=pr_strings+source->string;
    }
    if(n_needs)assemble(needs,n_needs);
    for(i=0;i<initial;i++){
        entity_t *ent=cl_visedicts[i];edict_t *a;eval_t *source;np_entry_t *e;aliashdr_t *h;float s;
        if(!ent || !ent->model || ent->model->type!=mod_alias || !(a=resident_of(ent)))continue;
        source=GetEdictFieldValue(a,"aw_source_id");
        if(!source || !source->string || !(e=find(pr_strings+source->string)) || e->state!=1){last_fused++;continue;}
        e->used=clock_tick;
        h=(aliashdr_t *)Mod_Extradata(ent->model);
        /* the fused model's frame is a frame of its table: only the same table may draw the parts at it */
        if(!h || !h->aw_skel || (const void *)h->aw_skel_table!=(const void *)e->table ||
           ent->frame<0 || ent->frame>=e->table->frames){last_fused++;continue;}
        if(ent_count+e->count>NP_ENTS || cl_numvisedicts+e->count-1>MAX_VISEDICTS || !models_ready(e)){last_skipped++;continue;}
        s=ent->effects&AW_EF_ALIAS_SCALE?ent->aw_sprite_scale:1;
        for(k=0;k<e->count;k++){
            entity_t *p=&ents[ent_count++];
            *p=*ent;p->model=e->models[k];
            p->effects|=AW_EF_ALIAS_SCALE;p->aw_sprite_scale=s*e->weight;p->aw_alias_zscale=s*e->height;
            if(!k){swapped[swap_count].at=p;swapped[swap_count++].original=ent;cl_visedicts[i]=p;}
            else cl_visedicts[cl_numvisedicts++]=p;
        }
        last_actors++;last_parts+=e->count;
    }
    last_ms=(Sys_FloatTime()-t0)*1000;
}

/* dbg camera npcs: the counters */
void AW_NpcPartsStatus(void)
{
    int i,kept=0,none=0;
    for(i=0;i<NP_CACHE;i++){if(cache[i].state==1)kept++;else if(cache[i].state<0)none++;}
    Con_Printf("Residents from parts: %s; last frame %d residents from %d parts, %d fused, %d skipped (%.2f ms).\n",
        npc_parts_on?"on":"off (fused models)",last_actors,last_parts,last_fused,last_skipped,last_ms);
    Con_Printf("Assembled %d, refused %d, kept %d with parts and %d fused; assembly %.1f ms in all%s.\n",
        built,refused,kept,none,build_ms,no_file?"; no view/parts.txt in this image":"");
    Con_Printf("Recipe tables: %d places in, %d tables held (%ld bytes); %lu read (%lu bytes, %.1f ms), %lu freed, "
        "%lu places without one; cells pack index %ld bytes.\n",n_places,tables.count,tables.bytes,table_loads,
        table_read_bytes,table_ms,table_frees,table_missing,pack_index_bytes);
    Con_Printf("Recently left and narrow-loaded tables kept: %d (%ld bytes); back without a read %lu; narrow loads %lu; "
        "resident directory %ld bytes.\n",aside.count,aside.bytes,table_reuses,narrow_loads,dir_bytes);
    Con_Printf("Area method (aw_npc_tables_areas %d): %s; pack %lu areas, index %lu bytes, directory %lu bytes; %d place "
        "areas; %lu area reads; not in the held tables %lu (waiting %d); narrow loads at a place change %lu, none in "
        "the directory %lu.\n",(int)tables_areas_cvar.value,areas_on?"on":"off (the earlier files)",awr_areas,
        awr_areas*12,awr_dir_n*8,area_now_n,area_loads,area_misses,n_pending,area_narrow,area_narrow_none);
}

/* the console variable (aw_debug.c, with the other modules' settings, before the game config is read) */
void AW_NpcPartsInit(void)
{
    Cvar_RegisterVariable(&tables_areas_cvar);      /* NPC-RECIPES-PER-AREA-59 */
}

/* a new map or dbg camera npcs: the assembled residents go (the recipe tables follow their places) */
void AW_NpcPartsReset(void)
{
    restore_list();memset(cache,0,sizeof(cache));no_file=0;
}

/* dbg camera npcs on/off: on reads the tables of the places in now, off lets them go */
void AW_NpcPartsSet(int on)
{
    int i;
    AW_NpcPartsReset();npc_parts_on=on!=0;
    if(!sv.active)return;
    tables_map_check();
    if(!npc_parts_on){table_free_all();return;}
    (void)i;
    if(areas_wanted()!=areas_on){table_free_all();areas_on=!areas_on;}
    area_synced=0;n_pending=0;
    load_all();
}
