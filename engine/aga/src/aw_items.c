/* Carried items on a hand bone's per-frame tag (aw_items.h; tools/npc_items.py). */
#ifdef AW_ITEMS_HOST_TEST
#include <string.h>
float Q_SinRad(float radians);
float Q_CosRad(float radians);
#else
#include "quakedef.h"
#include "aw_anim.h"
#include "aw_skel.h"
#include "aw_torch.h"
#include "aw_weather.h"
#endif
#include "aw_items.h"
#include "aw_tryalloc.h"

/* A decimal number "-12.345" (the tag writer's %.3f); no library float parsing. */
static int number(const char **p,float *out) {
    const char *s=*p;float v=0,scale=1;int neg=0,digits=0;
    while(*s==' ')s++;
    if(*s=='-'){neg=1;s++;}
    while(*s>='0' && *s<='9'){v=v*10+(float)(*s-'0');s++;digits++;}
    if(*s=='.'){s++;while(*s>='0' && *s<='9'){scale*=.1f;v+=(float)(*s-'0')*scale;s++;digits++;}}
    if(!digits || v>100000.f)return 0;
    *out=neg?-v:v;*p=s;return 1;
}
static const char *line_end(const char *p) {while(*p && *p!='\n')p++;return p;}

/* The "weapon <path|->" and "shield <path|->" lines of both tag forms. */
static int item_paths(const char **pp,char paths[AW_ITEMS_KINDS][AW_ITEMS_PATH]) {
    static const char *const kind[AW_ITEMS_KINDS]={"weapon ","shield "};
    const char *p=*pp,*e;int i,k,n;
    for(k=0;k<AW_ITEMS_KINDS;k++){
        if(strncmp(p,kind[k],7))return 0;
        p+=7;e=line_end(p);n=(int)(e-p);if(n>0 && p[n-1]=='\r')n--;
        if(n<1 || n>=AW_ITEMS_PATH)return 0;
        if(n==1 && *p=='-')paths[k][0]=0;
        else{
            for(i=0;i<n;i++)if(p[i]<=' ' || p[i]>'~' || (p[i]=='.' && p[i+1]=='.'))return 0;
            memcpy(paths[k],p,(size_t)n);paths[k][n]=0;
        }
        p=*e?e+1:e;
    }
    *pp=p;return 1;
}

int AW_ItemsParse(const char *text,int numframes,float *rows,int maxframes,char paths[AW_ITEMS_KINDS][AW_ITEMS_PATH]) {
    const char *p=text;float f;int frames,i,k;
    if(strncmp(p,"AWTG1 ",6))return 0;
    p+=6;if(!number(&p,&f) || f<1 || f>AW_ITEMS_MAX_FRAMES || f>maxframes)return 0;
    frames=(int)f;if(frames!=numframes)return 0;
    p=line_end(p);if(*p)p++;
    if(!item_paths(&p,paths))return 0;
    for(i=0;i<frames;i++){
        for(k=0;k<AW_ITEMS_ROW;k++)if(!number(&p,&rows[i*AW_ITEMS_ROW+k]))return 0;
        while(*p==' ' || *p=='\r')p++;
        if(*p!='\n' && *p)return 0;
        if(*p)p++;
    }
    return frames;
}

int AW_ItemsParseSkel(const char *text,int numframes,char paths[AW_ITEMS_KINDS][AW_ITEMS_PATH],int bones[AW_ITEMS_KINDS],
                      float scale[3],char light[AW_ITEMS_PATH],float emitter[3],int *has_emitter) {
    const char *p=text;float f;int frames,k;
    if(has_emitter)*has_emitter=0;
    if(light)light[0]=0;
    if(strncmp(p,"AWTS1 ",6))return 0;
    p+=6;if(!number(&p,&f) || f<1 || f>AW_ITEMS_MAX_SKEL_FRAMES)return 0;
    frames=(int)f;if(frames!=numframes)return 0;
    p=line_end(p);if(*p)p++;
    if(!item_paths(&p,paths) || strncmp(p,"bones ",6))return 0;
    p+=6;
    for(k=0;k<AW_ITEMS_KINDS;k++){
        if(!number(&p,&f) || f<-1 || f>=AW_ITEMS_MAX_BONES || f!=(float)(int)f)return 0;
        bones[k]=(int)f;
    }
    p=line_end(p);if(*p)p++;
    if(strncmp(p,"scale ",6))return 0;
    p+=6;
    for(k=0;k<3;k++)if(!number(&p,&scale[k]) || !(scale[k]>0))return 0;
    /* optional: a carried light (a guard's torch; SKEL-ITEM-TAGS-52), its model on the shield bone and its flame
     * point in that bone's space; it takes the shield hand while torches are carried (night, or forced) */
    p=line_end(p);if(*p)p++;
    if(!strncmp(p,"light ",6)){
        const char *e;float pt[3];int n,i;
        p+=6;e=line_end(p);n=(int)(e-p);if(n>0 && p[n-1]=='\r')n--;
        if(n<1 || n>=AW_ITEMS_PATH || bones[1]<0)return 0;
        for(i=0;i<n;i++)if(p[i]<=' ' || p[i]>'~' || (p[i]=='.' && p[i+1]=='.'))return 0;
        if(light){memcpy(light,p,(size_t)n);light[n]=0;}
        p=*e?e+1:e;
        if(strncmp(p,"emitter ",8))return 0;
        p+=8;
        for(k=0;k<3;k++)if(!number(&p,&pt[k]))return 0;
        if(emitter)for(k=0;k<3;k++)emitter[k]=pt[k];
        if(has_emitter)*has_emitter=1;
    }
    return frames;
}

/* GUARD-WEAPON-INVISIBLE-65: the frame count a model's tag is read against. NUMFRAMES is the model's when it is
 * known; 0 when it is not: a model registered by name only, as a layout's mover is at spawn (aw_anim.c lazy_index,
 * Mod_FindName: nothing is loaded, and a reused slot still holds the count of the model it held before). Not known:
 * the tag's own declared count, of either form (AWTS1 skeletal, AWTG1 rows), which the engine checks against the
 * model once it is loaded and worn (frames_match), as the row form's movers are read since ANIMKIT-ITEM-TAG-FRAMES-35.
 * 0: no tag, or no valid count. Before, the skeletal form was parsed against the unknown count, so the tag of every
 * skeletal mover was refused and its actor fought with nothing drawn in its hands (the opening's people, whose
 * layouts name an actor-library model as their mover). Declared here and in its fixture, not in aw_items.h: that
 * header is read by the build stages that check the engine's limits (tools/map_engine_limits.py). */
int AW_ItemsTagFrames(const char *text,int numframes);
int AW_ItemsTagFrames(const char *text,int numframes) {
    const char *p=text;float f;int skel;
    if(numframes>0)return numframes;
    if(!p || numframes<0)return 0;
    skel=!strncmp(p,"AWTS1 ",6);
    if(!skel && strncmp(p,"AWTG1 ",6))return 0;
    p+=6;
    if(!number(&p,&f) || f<1 || f>(skel?AW_ITEMS_MAX_SKEL_FRAMES:AW_ITEMS_MAX_FRAMES) || f!=(float)(int)f)return 0;
    return (int)f;
}

void AW_ItemsPose(const float *tag6,const float origin[3],float yaw,float out_origin[3],float out_angles[3]) {
    float r=yaw*(float)(3.14159265358979323846/180.0),c=Q_CosRad(r),s=Q_SinRad(r);
    out_origin[0]=origin[0]+c*tag6[0]-s*tag6[1];
    out_origin[1]=origin[1]+s*tag6[0]+c*tag6[1];
    out_origin[2]=origin[2]+tag6[2];
    /* r_alias.c R_AliasSetUpTransform negates an alias entity's pitch before AngleVectors,
     * so the entity carries minus the tag's (true AngleVectors) pitch. */
    out_angles[0]=-tag6[3];out_angles[1]=tag6[4]+yaw;out_angles[2]=tag6[5];
}

/* NPC-WEAPON-GRIP-WRONG-69: held items follow the frame the actor is SENT with. The fight, the walk and the idle
 * think pose an actor's items from the frame they set (SV_Physics); just before the send the state pick moves a
 * skeletal actor's frame into the group of its weapon (aw_animkit.c AW_AnimPickPreSend), so the body was drawn at one
 * frame and its weapon posed from another: the weapon hung where the hand of the driver's pose was, up to an arm's
 * length from the drawn hand. The original hangs the weapon on its bone, a child of the bone's node, so it moves with
 * the bone in every frame (rule from OpenMW apps/openmw/mwrender/npcanimation.cpp insertBoundedPart and showWeapons,
 * actoranimation.cpp attachMesh, creatureanimation.cpp updatePart; read, not copied). AW_ItemsStale: 1 when a set
 * posed at POSED_FRAME, POSED (origin x y z, yaw) is not where the actor is now. */
int AW_ItemsStale(int posed_frame,const float posed[4],int frame,const float origin[3],float yaw);
int AW_ItemsStale(int posed_frame,const float posed[4],int frame,const float origin[3],float yaw) {
    return posed_frame!=frame || posed[0]!=origin[0] || posed[1]!=origin[1] || posed[2]!=origin[2] || posed[3]!=yaw;
}
/* 1 for a group played with a weapon or the fists readied (the original's stance suffixes: idle1h, runforward2c,
 * walkback2w, turnlefthh, ...; a view's own prefix "f:" is the caller's to skip). An actor in one never shields its
 * eyes from a storm: the storm pose plays only with no upper-body action (rule from OpenMW
 * apps/openmw/mwmechanics/character.cpp updateIdleStormState, the upper body state test; read, not copied), and the
 * arm layer would lift the weapon hand off its weapon. */
int AW_ItemsStanceGroup(const char *name);
int AW_ItemsStanceGroup(const char *name) {
    static const char *const suffix[]={"1h","2c","2w","hh"};
    int n=name?(int)strlen(name):0,k;
    if(n<3)return 0;
    for(k=0;k<4;k++)if(name[n-2]==suffix[k][0] && name[n-1]==suffix[k][1])return 1;
    return 0;
}

/* HELD-ITEM-TABLE-FULL-69: the entry a new model's tag table takes. USED of SIZE entries hold a table; FLAGS, one per
 * entry in use: AW_ITEMS_SLOT_SKEL its table is the skeletal form (no rows on the level's memory, so the entry can be
 * given to another model), AW_ITEMS_SLOT_BUSY a live actor stands on, wears or may wear its model, or carries its
 * light. A free entry first; in a full table the first skeletal entry nobody uses; -1: every entry is in use. Before,
 * a full table took no new model at all: a CHIM session is one level (the island and every room it joins), so every
 * armed actor met after the level's 64th distinct armed model drew no weapon, shield or torch until the next load. */
#define AW_ITEMS_SLOT_SKEL 1
#define AW_ITEMS_SLOT_BUSY 2
int AW_ItemsTableSlot(int used,int size,const unsigned char *flags);
int AW_ItemsTableSlot(int used,int size,const unsigned char *flags) {
    int k;
    if(used<0 || size<1 || used>size)return -1;
    if(used<size)return used;
    for(k=0;k<used;k++)if((flags[k]&AW_ITEMS_SLOT_SKEL) && !(flags[k]&AW_ITEMS_SLOT_BUSY))return k;
    return -1;
}

unsigned AW_ItemsPathHash(const char *s) {
    unsigned h=2166136261u;
    if(!s)return 0;
    while(*s)h=(h^(unsigned char)*s++)*16777619u;
    return h;
}
/* A held item's model is an item model: its path has an "items/" folder (tools/npc_items.py). */
int AW_ItemsIsItemPath(const char *s) {
    const char *p;
    if(!s)return 0;
    for(p=s;(p=strstr(p,"items/"))!=NULL;p++)if(p==s || p[-1]=='/')return 1;
    return 0;
}

#ifndef AW_ITEMS_HOST_TEST
/* One tag table per actor model in use, reset per level (like aw_anim.c's layouts);
 * rows live on the hunk, which the level owns. */
#define TABLE 64
/* rows: a baked model's tag rows; or skel: a skeletal model's item bones and actor scale (rows NULL). */
typedef struct {model_t *model;int frames;float *rows;int item[AW_ITEMS_KINDS];
               int skel,bone[AW_ITEMS_KINDS];float scale[3];
               float emitter[3];int has_emitter,light_item;   /* a carried light (guard torch) */
               unsigned item_hash[AW_ITEMS_KINDS];   /* the tag's own item paths (HELD-WEAPON-WRONG-MODEL-62) */
               int given,told;                       /* the model's count prep had (0: not known), a mismatch said */
               int unloaded;} aw_items_entry_t;      /* the tag names items that were not loaded (prep LOAD 0) */
static aw_items_entry_t table[TABLE];
static int used;
static int by_own_count,full_spawns;   /* tables read with the tag's own count; spawns that found the table full */
static int reclaims;                   /* entries of models nobody used, given to another model (HELD-ITEM-TABLE-FULL-69) */
static unsigned char slot_flags[TABLE];   /* per entry: skeletal, in use (AW_ItemsTableSlot), as of the last scan */
static double slot_scan_time=-1;          /* the server time of that scan (-1: none this level) */
static int slot_scans;
static model_t *level_world;
/* precache names live through the level. 256: the game data has 235 weapon and shield meshes, and an actor's own
 * items (below) can name any of them in one session; 128 held the tags' item models only */
#define NAMES 256
static char names[NAMES][AW_ITEMS_PATH];
static int named,names_full;
/* ACTOR-HELD-ITEMS-NOT-LIVE-INVENTORY-69: what each actor holds comes from its own record, not from its model. The
 * tag beside a model named ONE weapon and shield for every actor drawn with that model, chosen when the game was
 * built: actors sharing a model could not hold different weapons, a ranged fighter held its melee weapon, and a
 * creature (one model per mesh, many records) held nothing. Now the actor's record says which weapon and shield it
 * has equipped (aw_items_held: the actor table's row, aw_actorstate.c AW_ActorHeldModels) and the tag gives the bones
 * and the scale; the original draws what the inventory's two slots hold (rule from OpenMW
 * apps/openmw/mwrender/npcanimation.cpp showWeapons, showCarriedLeft and creatureanimation.cpp updateParts; read, not
 * copied). own_item: per edict, the precache index of its weapon and its shield (0 none), valid while own_known; an
 * actor whose record cannot say (no actor table, a table without the held models, no row) keeps its tag's items.
 * 5 bytes an edict (3,000 bytes for 600), set at the actor's spawn, cleared with the level. */
int (*aw_items_held)(edict_t *actor,char weapon[AW_ITEMS_PATH],char shield[AW_ITEMS_PATH]);
static short own_item[MAX_EDICTS][AW_ITEMS_KINDS];
static unsigned char own_known[MAX_EDICTS];
static int own_actors,own_tag_actors;   /* spawns whose items came from their record; from their model's tag */
#define CARRIERS AW_ITEMS_CARRIERS
static struct {edict_t *actor;edict_t *light;int table;} carriers[CARRIERS];
static struct {int frame;float at[4];} carrier_posed[CARRIERS];   /* what each light was posed at (AW_ItemsPreSend) */
static int carrier_count;
static model_t *carrier_world;
/* NPC-WEAPON-GRIP-WRONG-69: the item sets shown now (AW_ItemsShow .. AW_ItemsHide), each with the frame and the place
 * it was posed at, so AW_ItemsPreSend poses again exactly those whose actor is sent otherwise. items: the caller's own
 * array (a fight slot's, a stage actor's), the set's identity. As many as can be shown: the fight's slots and the
 * animation stage's cast. 28 bytes a set. */
#define AW_ITEMS_SHOWN 48
static struct {edict_t *actor;edict_t **items;int frame;float at[4];} shown[AW_ITEMS_SHOWN];
static int shown_count;
static unsigned long presend_sets,presend_lights;   /* posed again at the sent frame since the level began */
static float presend_far;                           /* the largest move of an item by it, units */
static int shown_of(edict_t **items) {
    int i;
    for(i=0;i<shown_count;i++)if(shown[i].items==items)return i;
    return -1;
}
static void shown_drop(edict_t **items) {
    int i=shown_of(items);
    if(i>=0)shown[i]=shown[--shown_count];
}
static int pose_key(edict_t *actor);
static void posed_at(edict_t *actor,int *frame,float at[4]) {
    *frame=pose_key(actor);   /* the frame, and a torso layer's frame in it (ACTOR-DRAW-STOPS-LEGS-69) */
    at[0]=actor->v.origin[0];at[1]=actor->v.origin[1];at[2]=actor->v.origin[2];at[3]=actor->v.angles[1];
}
/* NPC-WEREWOLF-NO-MODEL-66 (v0.0.68): an NPC a script turned into a werewolf holds nothing, its weapon, shield and
 * carried light neither shown nor kept (the original's setWerewolf takes every item off any actor: OpenMW 0.51
 * mwmechanics/mechanicsmanagerimp.cpp 1880-1908, read not copied); it is drawn as the werewolf (aw_view.c). Set by
 * aw_mwhost.c (AW_MwscriptWerewolfNpc); NULL: nobody is turned (the tools' tests). */
int (*aw_items_werewolf)(edict_t *actor);
static int turned(edict_t *actor) {return aw_items_werewolf && aw_items_werewolf(actor);}

/* HELD-WEAPON-WRONG-MODEL-62: the tables hold precache indices of one server. A reload of the same world (the opening
 * skipped with `dbg aw hors 0` reloads Seyda Neen) keeps sv.worldmodel, so the worldmodel test alone kept the opening's
 * indices, which then named other models of the new precache (a guard drew an opening NPC as his weapon). Every new
 * server clears them (SV_SpawnServer, beside AW_AnimSceneReset). */
void AW_ItemsSceneReset(void) {
    used=0;named=0;memset(table,0,sizeof(table));level_world=NULL;by_own_count=full_spawns=0;
    reclaims=slot_scans=0;slot_scan_time=-1;
    memset(own_known,0,sizeof(own_known));own_actors=own_tag_actors=names_full=0;
    carrier_count=0;memset(carriers,0,sizeof(carriers));carrier_world=NULL;
    shown_count=0;memset(shown,0,sizeof(shown));presend_sets=presend_lights=0;presend_far=0;
}

static void level_check(void) {
    R_AliasTorchLayer=AW_ItemsTorchLayer;   /* the renderer poses a torch-holding guard's arm (r_alias.c) */
    R_AliasStormLayer=AW_ItemsStormLayer;   /* and an actor's eye-shielding arm in an ash or blight storm */
    if(level_world!=sv.worldmodel){
        level_world=sv.worldmodel;used=0;named=0;memset(table,0,sizeof(table));by_own_count=full_spawns=0;
        reclaims=slot_scans=0;slot_scan_time=-1;
        memset(own_known,0,sizeof(own_known));own_actors=own_tag_actors=names_full=0;
        shown_count=0;      /* the last world's sets went with its edicts */
    }
}
static model_t *model_of(edict_t *e) {
    int i=(int)e->v.modelindex;
    return i>0 && i<MAX_MODELS?sv.models[i]:NULL;
}
static int entry_of(model_t *m) {
    int i;
    for(i=0;i<used;i++)if(table[i].model==m)return i;
    return -1;
}
/* Carried lights (a guard's torch on a skeletal actor; SKEL-ITEM-TAGS-52): an actor whose tag names a flame point
 * carries its shield-slot item all the time, not only while it fights (the combat slots then draw its weapon only).
 * One entity per carrier, made when first needed and moved with the actor every server frame
 * (AW_ItemsCarriedUpdate); reset per level. */
static void carriers_check(void) {
    if(carrier_world!=sv.worldmodel){carrier_world=sv.worldmodel;carrier_count=0;memset(carriers,0,sizeof(carriers));}
}
static int carries_light(int t) {return t>=0 && table[t].skel && table[t].has_emitter && table[t].light_item;}
/* Precache an item model while the level loads (spawn functions only). */
static int precache(const char *path) {
    int i;model_t *m;
    for(i=1;i<MAX_MODELS && sv.model_precache[i];i++)if(!strcmp(sv.model_precache[i],path))return i;
    if(i>=MAX_MODELS || sv.state!=ss_loading)return 0;
    if(named>=NAMES){       /* said once a level, counted for dbg animkit pick: never a silent empty hand */
        if(!names_full++)Con_Printf("Held item %s: the level's %d item model names are in use, not drawn\n",path,NAMES);
        return 0;
    }
    if(!(m=Mod_ForName((char *)path,false)))return 0;
    strcpy(names[named],path);sv.model_precache[i]=names[named++];sv.models[i]=m;
    return i;
}

/* The refusal, with both counts (GUARD-WEAPON-INVISIBLE-65): the model's frames prep had (0: not known yet) and the
 * tag's own (0: none readable). */
static void refused(const char *path,int model_frames,int tag_frames) {
    Con_Printf("Item tags %s: invalid against %d model frames (the tag has %d), items not drawn\n",path,model_frames,
               tag_frames);
}
/* One model's tag table. numframes 0: a model that is not loaded yet (a mover: aw_anim.c registers it by
 * name only): the tag's own frame count is kept and checked against the model when it is worn
 * (frames_match), for both tag forms (AW_ItemsTagFrames); the builder writes one row per frame of each model
 * (ANIMKIT-ITEM-TAG-FRAMES-35). */
/* HELD-ITEM-TABLE-FULL-69: the entry for a new model's table (AW_ItemsTableSlot): a free one, else, in a full table,
 * a skeletal entry whose model no live actor stands on, wears as its mover, stands on under a worn mover or may wear
 * (its layout names it), and whose light no live actor carries. The scan runs only at a spawn that finds the table
 * full: one pass over the edicts, per alias-model edict one compare an entry, and a name compare an entry for an
 * actor whose layout names a mover. No memory: the entry is used again in place (the indices the carriers hold stay
 * good); a row table is never given back (its rows are on the level's memory). */
static int table_slot(void) {
    unsigned char *flags=slot_flags;int i,k,base;model_t *m;const aw_anim_t *a;
    if(used<TABLE)return used;
    /* one scan serves every spawn of the same server time (an area's actors join in one frame): within it actors are
     * only added, and a model that takes an entry is marked in use at once (table_taken) */
    if(slot_scan_time==sv.time)return AW_ItemsTableSlot(used,TABLE,flags);
    slot_scan_time=sv.time;slot_scans++;
    for(k=0;k<TABLE;k++)flags[k]=(unsigned char)(table[k].skel && !table[k].rows?AW_ITEMS_SLOT_SKEL:0);
    for(i=1;i<sv.num_edicts;i++){
        edict_t *e=EDICT_NUM(i);
        if(e->free || !(m=model_of(e)) || m==sv.worldmodel)continue;
        for(k=0;k<TABLE;k++)if(table[k].model==m)flags[k]|=AW_ITEMS_SLOT_BUSY;
        if((base=AW_AnimWornBase(e))>0 && base<MAX_MODELS && sv.models[base])
            for(k=0;k<TABLE;k++)if(table[k].model==sv.models[base])flags[k]|=AW_ITEMS_SLOT_BUSY;
        a=AW_AnimOf(e);
        if(a->mover[0])
            for(k=0;k<TABLE;k++)if(!strcmp(table[k].model->name,a->mover))flags[k]|=AW_ITEMS_SLOT_BUSY;
    }
    for(i=0;i<carrier_count;i++)
        if(carriers[i].actor && !carriers[i].actor->free && carriers[i].light && !carriers[i].light->free &&
           carriers[i].table>=0 && carriers[i].table<TABLE)flags[carriers[i].table]|=AW_ITEMS_SLOT_BUSY;
    return AW_ItemsTableSlot(used,TABLE,flags);
}
/* A new model's table put into entry AT: a new entry, or one given up by a model nobody used: then a carrier slot that
 * still names the entry (its actor is gone) is free again. The entry counts as in use for the rest of this scan. */
static void table_taken(int at,const aw_items_entry_t *fresh) {
    int i;
    if(at==used)used++;
    else{
        reclaims++;
        for(i=0;i<carrier_count;i++)if(carriers[i].table==at){
            if(carriers[i].light && !carriers[i].light->free)ED_Free(carriers[i].light);
            carriers[i].actor=NULL;carriers[i].light=NULL;
        }
    }
    table[at]=*fresh;if(!fresh->given)by_own_count++;
    slot_flags[at]=(unsigned char)((fresh->skel && !fresh->rows?AW_ITEMS_SLOT_SKEL:0)|AW_ITEMS_SLOT_BUSY);
}
/* LOAD 0 (ACTOR-HELD-ITEMS-NOT-LIVE-INVENTORY-69): the tag's own item models are not loaded now: the actor's record
 * names what it holds, and the entry is kept for its bones and scale (also a tag that names no item at all, a
 * creature's); tag_items loads them later for an actor whose record cannot say. */
static void prep(model_t *m,const char *name,int numframes,int load) {
    char path[MAX_QPATH+4],items[AW_ITEMS_KINDS][AW_ITEMS_PATH];byte *text;aw_items_entry_t fresh;
    int mark,n,k,frames,any=0,given=numframes,declared,at;float *rows;
    if(!m)return;
    if((k=entry_of(m))>=0){slot_flags[k]|=AW_ITEMS_SLOT_BUSY;return;}   /* in use, also for a scan made just before */
    n=(int)strlen(name);
    if(n<5 || n>=(int)sizeof(path) || strcmp(name+n-4,".mdl") || numframes<0 || numframes>AW_ITEMS_MAX_SKEL_FRAMES)
        return;
    memcpy(path,name,(size_t)(n-4));strcpy(path+n-4,".tag");
    /* The rows stay on the level's hunk; the text is read into temporary memory. */
    mark=Hunk_LowMark();
    text=COM_LoadTempFile(path);
    if(!text){Hunk_FreeToLowMark(mark);return;}
    declared=AW_ItemsTagFrames((const char *)text,0);
    /* a CHIM session is one level (the island and every room it joins), so a full table gives the entry of a model
     * nobody uses any more to the new one (HELD-ITEM-TABLE-FULL-69: table_slot); only when every entry is in use by a
     * live actor does a model with a tag draw no items: said once a level, counted for dbg animkit pick */
    if((at=table_slot())<0){
        if(declared && !full_spawns++)
            Con_Printf("Item tags %s: the level's %d tag tables are in use by live actors, items not drawn\n",path,
                       TABLE);
        Hunk_FreeToLowMark(mark);return;
    }
    numframes=AW_ItemsTagFrames((const char *)text,numframes);   /* not known: the tag's own */
    /* built beside the table and put in only when it holds an item: an entry in use is never written over by a tag
     * that is refused or names nothing */
    memset(&fresh,0,sizeof(fresh));fresh.model=m;fresh.given=given;
    if(!strncmp((const char *)text,"AWTS1 ",6)){
        /* a skeletal model: its items follow the table's bones, posed when drawn (SKEL-ITEM-TAGS-52) */
        int bones[AW_ITEMS_KINDS];float scale[3];char light[AW_ITEMS_PATH];
        frames=numframes?AW_ItemsParseSkel((const char *)text,numframes,items,bones,scale,light,fresh.emitter,
                                           &fresh.has_emitter):0;
        Hunk_FreeToLowMark(mark);
        if(!frames){refused(path,given,declared);return;}
        fresh.frames=frames;fresh.skel=1;
        for(k=0;k<3;k++)fresh.scale[k]=scale[k];
        for(k=0;k<AW_ITEMS_KINDS;k++){
            fresh.bone[k]=bones[k];
            fresh.item[k]=load && items[k][0] && bones[k]>=0?precache(items[k]):0;
            fresh.item_hash[k]=fresh.item[k]?AW_ItemsPathHash(items[k]):0;
            if(fresh.item[k])any=1;
            if(!load && bones[k]>=0){any=1;if(items[k][0])fresh.unloaded=1;}
        }
        fresh.light_item=fresh.has_emitter && light[0]?precache(light):0;
        if(fresh.light_item)any=1;
        if(any)table_taken(at,&fresh);
        return;
    }
    if(numframes>AW_ITEMS_MAX_FRAMES){Hunk_FreeToLowMark(mark);return;}
    if(!numframes){refused(path,given,declared);Hunk_FreeToLowMark(mark);return;}   /* no tag, or no count */
    rows=(float *)Hunk_AllocName(numframes*AW_ITEMS_ROW*(int)sizeof(float),"awtag");
    frames=AW_ItemsParse((const char *)text,numframes,rows,numframes,items);
    if(!frames){
        refused(path,given,declared);
        Hunk_FreeToLowMark(mark);return;
    }
    fresh.frames=frames;fresh.rows=rows;
    for(k=0;k<AW_ITEMS_KINDS;k++){
        fresh.item[k]=load && items[k][0]?precache(items[k]):0;
        fresh.item_hash[k]=fresh.item[k]?AW_ItemsPathHash(items[k]):0;
        if(fresh.item[k])any=1;
        if(!load){any=1;if(items[k][0])fresh.unloaded=1;}
    }
    if(any)table_taken(at,&fresh);else Hunk_FreeToLowMark(mark);
}
/* The item models a table's own tag names, loaded after all (prep with LOAD 0 left them): for an actor whose record
 * cannot say what it holds. The tag is read once more; its frames and bones were checked when the entry was made. */
static void tag_items(int t) {
    char path[MAX_QPATH+4],items[AW_ITEMS_KINDS][AW_ITEMS_PATH];const char *p;byte *text;int mark,n,k;
    if(t<0 || !table[t].unloaded)return;
    table[t].unloaded=0;
    n=(int)strlen(table[t].model->name);
    if(n<5 || n>=(int)sizeof(path))return;
    memcpy(path,table[t].model->name,(size_t)(n-4));strcpy(path+n-4,".tag");
    mark=Hunk_LowMark();
    if((text=COM_LoadTempFile(path))!=NULL){
        p=line_end((const char *)text);if(*p)p++;
        if(item_paths(&p,items))for(k=0;k<AW_ITEMS_KINDS;k++){
            table[t].item[k]=items[k][0] && (!table[t].skel || table[t].bone[k]>=0)?precache(items[k]):0;
            table[t].item_hash[k]=table[t].item[k]?AW_ItemsPathHash(items[k]):0;
        }
    }
    Hunk_FreeToLowMark(mark);
}
/* The full-kit model ACTOR's layout names as its mover (aw_anim.c AW_AnimMover; AW_AnimPrep has registered it by
 * name), NULL none or M itself; *NAME its name as the layout writes it. */
static model_t *mover_model(edict_t *actor,model_t *m,const char **name) {
    const aw_anim_t *a=AW_AnimOf(actor);int i;
    *name=a->mover;
    if(!a->mover[0])return NULL;
    for(i=1;i<MAX_MODELS && sv.model_precache[i];i++)
        if(!strcmp(sv.model_precache[i],a->mover))return sv.models[i] && sv.models[i]!=m?sv.models[i]:NULL;
    return NULL;
}

void AW_ItemsPrep(edict_t *actor) {
    model_t *m,*mover;const char *mover_name;int i,n,k,t,tm,held=-1,lazy=aw_items_held!=NULL;
    char own[AW_ITEMS_KINDS][AW_ITEMS_PATH];
    level_check();
    if(!actor)return;
    n=NUM_FOR_EDICT(actor);
    if(n>0 && n<MAX_EDICTS)own_known[n]=0;      /* this edict's last actor's items are not this one's */
    if(!(m=model_of(actor)) || sv.state!=ss_loading)return;
    /* 0: a model known by name only (another layout's mover, registered before this actor spawned, so its precache
     * loaded nothing): read with its tag's own count, as a mover is */
    if(m->numframes<0 || m->numframes>AW_ITEMS_MAX_SKEL_FRAMES)return;
    prep(m,m->name,m->numframes,!lazy);
    /* The full-kit model the actor wears while it moves or fights (aw_anim.c AW_AnimMover) has its own
     * tag table beside it; AW_AnimPrep has registered it by name. GUARD-WEAPON-INVISIBLE-65: never its numframes
     * here (as AW_AnimPrep reads the mover's layout): it is not loaded (0), or its reused slot still holds the count
     * of the model it held before; the tag is read with its own count and checked against the model once it is
     * loaded and worn (frames_match). Passed before, the skeletal tag of every such mover was refused. */
    if((mover=mover_model(actor,m,&mover_name))!=NULL)prep(mover,mover_name,0,!lazy);
    t=entry_of(m);tm=mover?entry_of(mover):-1;
    /* ACTOR-HELD-ITEMS-NOT-LIVE-INVENTORY-69: an actor that has a table (bones to hold with) is asked what its own
     * record has equipped; those models are loaded, the tag's own are not. An actor whose record cannot say keeps
     * the tag's items, loaded now. Asked only for a model with a table: an unarmed model costs no read. */
    if(lazy && (t>=0 || tm>=0)){
        if(n>0 && n<MAX_EDICTS && (held=aw_items_held(actor,own[0],own[1]))>=0){
            for(k=0;k<AW_ITEMS_KINDS;k++)
                own_item[n][k]=(short)((held&(1<<k)) && AW_ItemsIsItemPath(own[k])?precache(own[k]):0);
            own_known[n]=1;own_actors++;
        }else{tag_items(t);tag_items(tm);own_tag_actors++;}
    }
    if(carries_light(t)){          /* a guard's torch: carried all the time (AW_ItemsCarriedUpdate) */
        carriers_check();
        for(i=0;i<carrier_count && carriers[i].actor!=actor;i++);
        /* HELD-ITEM-TABLE-FULL-69: a slot whose actor is gone is used again (a session is one level: the slots
         * were never given back either, so the 33rd torch carrier met carried none) */
        if(i==carrier_count)for(i=0;i<carrier_count && carriers[i].actor && !carriers[i].actor->free;i++);
        if(i<carrier_count || carrier_count<CARRIERS){
            if(i==carrier_count)carrier_count++;
            else if(carriers[i].actor!=actor && carriers[i].light && !carriers[i].light->free)ED_Free(carriers[i].light);
            if(carriers[i].actor!=actor)carriers[i].light=NULL;
            carriers[i].actor=actor;carriers[i].table=t;
        }
    }
}

/* ACTOR's edict number when its items are its own record's (AW_ItemsPrep), else 0. */
static int own_of(edict_t *actor) {
    int n=NUM_FOR_EDICT(actor);
    return n>0 && n<MAX_EDICTS && own_known[n]?n:0;
}
/* A table is used only when its rows match the model's frames (a mover's are checked once it is loaded). */
static int frames_match(model_t *m,int t) {return t>=0 && m && m->numframes==table[t].frames;}

/* HELD-WEAPON-WRONG-MODEL-62: a held item's precache slot must still name the tag's own item model, and an item model
 * at that; anything else is drawn as nothing and said once per server. */
static int held_item_ok(edict_t *actor,int t,int k,int i) {
    static int said_used=-1;
    const char *name=i>0 && i<MAX_MODELS?sv.model_precache[i]:NULL;
    if(name && AW_ItemsPathHash(name)==table[t].item_hash[k] && AW_ItemsIsItemPath(name))return 1;
    if(said_used!=named){
        said_used=named;
        Con_Printf("Held item: slot %d of %s names %s, not its item model; not drawn\n",i,
                   model_of(actor)?model_of(actor)->name:"?",name?name:"nothing");
    }
    return 0;
}

/* GUARD-WEAPON-INVISIBLE-65: a table read with its tag's own count whose model loaded with another (a skeletal model
 * whose animation table did not link stays on its one rest frame) is drawn as nothing; said once a level a table. */
static void mismatch_told(int t) {
    if(t<0 || table[t].told)return;
    table[t].told=1;
    Con_Printf("Item tags of %s: %d frames, the model has %d, items not drawn\n",table[t].model->name,table[t].frames,
               table[t].model->numframes);
}
int AW_ItemsShow(edict_t *actor,edict_t *out[AW_ITEMS_KINDS]) {
    int t=-1,k,n=0,own;edict_t *e;
    level_check();
    for(k=0;k<AW_ITEMS_KINDS;k++)out[k]=NULL;
    if(!actor || actor->free || turned(actor) || !frames_match(model_of(actor),t=entry_of(model_of(actor)))){
        mismatch_told(t);return 0;}
    own=own_of(actor);      /* the actor's own weapon and shield (its record's), else its model's tag's */
    for(k=0;k<AW_ITEMS_KINDS;k++){
        int i=own?own_item[own][k]:table[t].item[k];
        /* while torches are carried the torch has the shield hand (AW_ItemsCarriedUpdate) */
        if(i<=0 || i>=MAX_MODELS || !sv.model_precache[i] || (k==1 && carries_light(t) && AW_GuardTorchWanted()))continue;
        /* HELD-WEAPON-WRONG-MODEL-62: the slot must still name the tag's own item model, and an item model at that;
         * anything else is drawn as nothing and said once per level. An actor's own item: an item model, on a bone
         * the table has */
        if(own?!AW_ItemsIsItemPath(sv.model_precache[i]) || (table[t].skel && table[t].bone[k]<0):
               !held_item_ok(actor,t,k,i))continue;
        e=ED_Alloc();
        e->v.classname=ED_NewString("aw_item")-pr_strings;
        e->v.model=sv.model_precache[i]-pr_strings;e->v.modelindex=i;
        e->v.movetype=MOVETYPE_NONE;e->v.solid=SOLID_NOT;e->v.frame=0;
        out[k]=e;n++;
    }
    /* the set is known from here to its AW_ItemsHide, so the send can pose it at the frame sent (AW_ItemsPreSend) */
    if(n && shown_of(out)<0 && shown_count<AW_ITEMS_SHOWN){
        shown[shown_count].actor=actor;shown[shown_count].items=out;shown[shown_count].frame=-1;shown_count++;
    }
    if(!n)shown_drop(out);
    AW_ItemsUpdate(actor,out);
    return n;
}

/* A skeletal model's item rows at one table frame (SKEL-ITEM-TAGS-52): the table posed at the frame and each item
 * bone made into a tag row. The last pose is kept (an armed actor's items follow it every server frame while its
 * table frame changes about 8 times a second). 0 when the model has no table. */
int (*aw_items_player_layer)(const model_t *m,const void *skel_table,int frame,float *layer_frame,int *root);
int AW_ItemsTorchLayer(const model_t *m,const void *skel_table,int frame,float *layer_frame,int *root) {
    const aw_skel_table_t *tab=(const aw_skel_table_t *)skel_table;
    aw_skel_group_t g;int t,i,span;
    if(m && tab && aw_items_player_layer && aw_items_player_layer(m,skel_table,frame,layer_frame,root))return 1;
    if(!m || !tab || !AW_GuardTorchWanted())return 0;
    for(t=0;t<used && table[t].model!=m;t++);
    if(t==used || !carries_light(t))return 0;
    if((*root=AW_SkelLeftArmRoot(tab,table[t].bone[1],table[t].bone[0]))<0 || (i=AW_SkelGroup(tab,"torch"))<0)return 0;
    AW_SkelGroupAt(tab,i,&g);
    span=(int)(g.last-g.first)+1;
    if(span<1)return 0;
    /* the group's frames in turn with the actor's own (the baked guards: its eight phases), so a frame poses alike */
    *layer_frame=(float)(g.first+(unsigned)(frame<0?0:frame)%(unsigned)span);
    return 1;
}

/* ACTOR-STORM-POSE-51: the frames an actor may shield its eyes in. Rule from OpenMW file
 * apps/openmw/mwmechanics/character.cpp (updateIdleStormState, read, not copied): only with no upper-body action
 * (no attack, cast, weapon or hit) and out of the water; here: a frame of the idle groups (idle, idle2..idle9) or of
 * walking, running, turning or sneaking; a view's own prefix ("f:", "d:f:") is skipped. One answer kept. */
static int storm_frame(const aw_skel_table_t *tab,int frame) {
    static const aw_skel_table_t *last_tab;static int last_frame=-1,last_ok;
    aw_skel_group_t g;int i;const char *name,*c;
    if(tab==last_tab && frame==last_frame)return last_ok;
    last_tab=tab;last_frame=frame;last_ok=0;
    for(i=0;i<tab->groups;i++){
        AW_SkelGroupAt(tab,i,&g);
        if(frame<(int)g.first || frame>(int)g.last)continue;
        for(name=c=g.name;*c && c<g.name+AW_SKEL_NAME;c++)if(*c==':')name=c+1;
        {   /* NPC-WEAPON-GRIP-WRONG-69: never in a weapon stance group (the arm layer would lift the hand off its
             * weapon; the original plays the storm pose only with no weapon readied, AW_ItemsStanceGroup) */
            char stance[AW_SKEL_NAME+1];int n=0;
            for(c=name;*c && c<g.name+AW_SKEL_NAME;c++)stance[n++]=*c;
            stance[n]=0;
            if(AW_ItemsStanceGroup(stance))break;
        }
        if(!Q_strncasecmp((char *)name,"idle",4))
            last_ok=!name[4] || (name[4]>='2' && name[4]<='9' && !name[5]);
        else last_ok=!Q_strncasecmp((char *)name,"walk",4) || !Q_strncasecmp((char *)name,"run",3) ||
                     !Q_strncasecmp((char *)name,"turn",4) || !Q_strncasecmp((char *)name,"sneak",5);
        break;
    }
    return last_ok;
}
int AW_ItemsStormLayer(const model_t *m,const void *skel_table,int frame,float yaw,float *layer_frame,int *root) {
    const aw_skel_table_t *tab=(const aw_skel_table_t *)skel_table;
    aw_skel_group_t g;int t,i,span;float dir[2];
    if(!m || !tab || !AW_WeatherStorm(dir) || !AW_WeatherFacesStorm(yaw,dir))return 0;
    for(t=0;t<used && table[t].model!=m;t++);
    if(t==used || !table[t].skel)return 0;
    if((*root=AW_SkelRightArmRoot(tab,table[t].bone[1],table[t].bone[0]))<0 || (i=AW_SkelGroup(tab,"idlestorm"))<0)return 0;
    if(!storm_frame(tab,frame))return 0;
    AW_SkelGroupAt(tab,i,&g);
    span=(int)(g.last-g.first)+1;
    if(span<1)return 0;
    /* the group in turn with the actor's own frames, as the torch layer */
    *layer_frame=(float)(g.first+(unsigned)(frame<0?0:frame)%(unsigned)span);
    return 1;
}

/* ACTOR-DRAW-STOPS-LEGS-69: the torso layer of ACTOR at this send (aw_animkit.c: a draw or put-away played over the
 * walk), NULL in the fixtures: 1 with the draw's table frame and the torso's root bone */
int (*aw_items_torso_layer)(edict_t *actor,float *layer_frame,int *root);
/* The torso's root bone of a skeletal model of an item table (Bip01 Spine2 of the stick figure, tools/skeletal_actor.py
 * STICK_BONES): the parent of the bone both arms' roots hang on (the neck), -1 when the table is not shaped so or the
 * model has no item table. Declared where it is called (aw_animkit.c). */
int AW_ItemsTorsoRoot(const model_t *m,const void *skel_table);
int AW_ItemsTorsoRoot(const model_t *m,const void *skel_table) {
    const aw_skel_table_t *tab=(const aw_skel_table_t *)skel_table;int t,l,r,neck;
    if(!m || !tab)return -1;
    for(t=0;t<used && table[t].model!=m;t++);
    if(t==used || !table[t].skel)return -1;
    l=AW_SkelLeftArmRoot(tab,table[t].bone[1],table[t].bone[0]);r=AW_SkelRightArmRoot(tab,table[t].bone[1],table[t].bone[0]);
    if(l<0 || r<0 || (neck=tab->parent[l])<0 || neck!=tab->parent[r] || tab->parent[neck]<=0)return -1;
    return tab->parent[neck];
}
/* the frame an actor's set is posed at, the torso layer's frame in it (AW_ItemsStale compares it whole) */
static int pose_key(edict_t *actor) {
    float lf;int root;
    if(actor && aw_items_torso_layer && aw_items_torso_layer(actor,&lf,&root))   /* unsigned: wraps, never overflows */
        return (int)((unsigned)(int)actor->v.frame+(unsigned)(1+(int)lf)*(unsigned)(AW_ITEMS_MAX_SKEL_FRAMES+1));
    return (int)actor->v.frame;
}
static int skel_rows(int t,int f,edict_t *actor,float rows[AW_ITEMS_ROW]) {
    static const aw_skel_table_t *last_table;static int last_frame=-1,last_layered,last_roots[2];static float last_layers[2];
    static float world[AW_SKEL_MAX_BONES][3][4];
    const aliashdr_t *hdr=(const aliashdr_t *)Mod_Extradata(table[t].model);
    const aw_skel_table_t *tab=hdr && hdr->aw_skel?(const aw_skel_table_t *)hdr->aw_skel_table:NULL;
    int k,root=-1,layered,roots[2];float layer=0,layers[2];
    if(!tab)return 0;
    /* a guard holding his torch has his left arm on the torch group, as he is drawn (AW_ItemsTorchLayer); a fighter
     * drawing while it moves has its torso on the draw (ACTOR-DRAW-STOPS-LEGS-69), as r_alias.c draws it */
    layered=AW_ItemsTorchLayer(table[t].model,tab,f,&layer,&root);
    layers[0]=layer;roots[0]=layered?root:-1;layers[1]=0;roots[1]=-1;
    if(actor && aw_items_torso_layer && !aw_items_torso_layer(actor,&layers[1],&roots[1])){layers[1]=0;roots[1]=-1;}
    if(tab!=last_table || f!=last_frame || layered!=last_layered || memcmp(roots,last_roots,sizeof(roots)) ||
       memcmp(layers,last_layers,sizeof(layers))){
        AW_SkelPoseLayers(tab,(float)f,2,layers,roots,world);last_table=tab;last_frame=f;last_layered=layered;
        memcpy(last_roots,roots,sizeof(roots));memcpy(last_layers,layers,sizeof(layers));
    }
    for(k=0;k<AW_ITEMS_KINDS;k++){
        int b=table[t].bone[k];
        if(b>=0 && b<tab->bones)AW_SkelBoneTag((const float (*)[4])world[b],table[t].scale,&rows[k*6]);
        else memset(&rows[k*6],0,6*sizeof(float));
    }
    return 1;
}

void AW_ItemsUpdate(edict_t *actor,edict_t *items[AW_ITEMS_KINDS]) {
    int t,k,f;float skel[AW_ITEMS_ROW];const float *row;
    if(!actor || actor->free || turned(actor) || !frames_match(model_of(actor),t=entry_of(model_of(actor)))){
        AW_ItemsHide(items);return;}   /* NPC-WEREWOLF-NO-MODEL-66: a werewolf holds nothing (turned in the fight too) */
    f=(int)actor->v.frame;if(f<0 || f>=table[t].frames)f=0;
    if(table[t].skel){
        if(!skel_rows(t,f,actor,skel)){AW_ItemsHide(items);return;}
        row=skel;
    }else row=&table[t].rows[f*AW_ITEMS_ROW];
    for(k=0;k<AW_ITEMS_KINDS;k++){
        edict_t *e=items[k];
        if(!e || e->free)continue;
        AW_ItemsPose(&row[k*6],actor->v.origin,actor->v.angles[1],e->v.origin,e->v.angles);
        SV_LinkEdict(e,false);
    }
    if((k=shown_of(items))>=0){shown[k].actor=actor;posed_at(actor,&shown[k].frame,shown[k].at);}
}

/* One carrier's light on its hand at the actor's frame now; what it was posed at is kept (AW_ItemsPreSend). */
static void carried_pose(int i) {
    float rows[AW_ITEMS_ROW];edict_t *a=carriers[i].actor,*e=carriers[i].light;int t=carriers[i].table;
    if(!skel_rows(t,(int)a->v.frame<0 || (int)a->v.frame>=table[t].frames?0:(int)a->v.frame,a,rows))return;
    AW_ItemsPose(&rows[6],a->v.origin,a->v.angles[1],e->v.origin,e->v.angles);
    SV_LinkEdict(e,false);
    posed_at(a,&carrier_posed[i].frame,carrier_posed[i].at);
}

/* NPC-WEAPON-GRIP-WRONG-69: just before the server sends the entities, after the state pick has put every skeletal
 * actor on the frame it is drawn at (sv_main.c SV_SendClientMessages, between aw_animkit.c AW_AnimPickPreSend and
 * AW_AnimPickPostSend): every item set shown and every carried light whose actor is sent on another frame, or at
 * another place, than its items were posed at is posed again, so the weapon, the shield and the torch are on the hand
 * of the pose that is drawn. Cost: per set and per light five compares; one pose of the table's bones (no vertices)
 * for each actor the pick moved. Declared where it is called, not in aw_items.h (a build stage reads that header's
 * limits: tools/map_engine_limits.py). */
void AW_ItemsPreSend(void);
void AW_ItemsPreSend(void) {
    int i,k;float was[AW_ITEMS_KINDS][3],d,m;
    if(sv.state!=ss_active)return;
    level_check();
    for(i=shown_count-1;i>=0;i--){      /* backwards: a set that cannot be posed is hidden and leaves the list */
        edict_t *a=shown[i].actor,**items=shown[i].items;
        if(!a || a->free){AW_ItemsHide(items);continue;}
        if(!AW_ItemsStale(shown[i].frame,shown[i].at,pose_key(a),a->v.origin,a->v.angles[1]))continue;
        for(k=0;k<AW_ITEMS_KINDS;k++)if(items[k] && !items[k]->free)VectorCopy(items[k]->v.origin,was[k]);
        AW_ItemsUpdate(a,items);
        if(shown_of(items)!=i)continue;                 /* hidden by the update */
        presend_sets++;
        for(k=0;k<AW_ITEMS_KINDS;k++)if(items[k] && !items[k]->free){
            d=(items[k]->v.origin[0]-was[k][0])*(items[k]->v.origin[0]-was[k][0])+
              (items[k]->v.origin[1]-was[k][1])*(items[k]->v.origin[1]-was[k][1])+
              (items[k]->v.origin[2]-was[k][2])*(items[k]->v.origin[2]-was[k][2]);
            m=d>0?(float)sqrt(d):0;
            if(m>presend_far)presend_far=m;
        }
    }
    carriers_check();
    for(i=0;i<carrier_count;i++){
        edict_t *a=carriers[i].actor,*e=carriers[i].light;
        if(!a || a->free || !e || e->free || model_of(a)!=table[carriers[i].table].model)continue;
        if(!AW_ItemsStale(carrier_posed[i].frame,carrier_posed[i].at,pose_key(a),a->v.origin,a->v.angles[1]))continue;
        carried_pose(i);presend_lights++;
    }
}
/* dbg animkit pick (aw_animkit.c): how many item sets and carried lights the send posed again since the level began,
 * and the largest move of an item by it (how far the weapon was from the drawn hand before the send's pose). */
void AW_ItemsPreSendCount(unsigned long *sets,unsigned long *lights,float *far_units,int *shown_now);
void AW_ItemsPreSendCount(unsigned long *sets,unsigned long *lights,float *far_units,int *shown_now) {
    *sets=presend_sets;*lights=presend_lights;*far_units=presend_far;*shown_now=shown_count;
}
/* dbg animkit pick (GUARD-WEAPON-INVISIBLE-65): the level's tag tables: counts[0] in use, [1] the table's size, [2]
 * read with the tag's own frame count (a model not loaded at spawn, a mover), [3] spawns of a tagged model that found
 * the table full of entries in use, [4] entries of models nobody used given to another model, [5] the scans of the
 * edicts made for that (HELD-ITEM-TABLE-FULL-69), [6] spawns whose held items came from the actor's own record, [7]
 * from its model's tag (the record could not say), [8] item model names in use, [9] of so many, [10] items not loaded
 * because the names were used up (ACTOR-HELD-ITEMS-NOT-LIVE-INVENTORY-69). For ACTOR (NULL: none), the table of its
 * model, else of its layout's mover: its model's name, the tag's frames, the model's frames now and the count prep
 * had (0: not known). 1 when ACTOR has one. */
int AW_ItemsTables(edict_t *actor,int counts[11],const char **model,int info[3]);
int AW_ItemsTables(edict_t *actor,int counts[11],const char **model,int info[3]) {
    int t=-1,i;const aw_anim_t *a;
    level_check();
    counts[0]=used;counts[1]=TABLE;counts[2]=by_own_count;counts[3]=full_spawns;counts[4]=reclaims;counts[5]=slot_scans;
    counts[6]=own_actors;counts[7]=own_tag_actors;counts[8]=named;counts[9]=NAMES;counts[10]=names_full;
    if(!actor || actor->free || !model_of(actor))return 0;
    if((t=entry_of(model_of(actor)))<0 && (a=AW_AnimOf(actor))->mover[0])
        for(i=1;i<MAX_MODELS && sv.model_precache[i];i++)
            if(!strcmp(sv.model_precache[i],a->mover)){t=sv.models[i]?entry_of(sv.models[i]):-1;break;}
    if(t<0)return 0;
    *model=table[t].model->name;info[0]=table[t].frames;info[1]=table[t].model->numframes;info[2]=table[t].given;
    return 1;
}

/* The shield-slot item's flame point of a carried light model (the torch item's own model space), 1 if it is one.
 * The tag states it in the shield bone's units (tools/prepare_guard_torches.py torch_item); the item model is that
 * bone space at the items' own scale, 0.25 (tools/npc_items.py: an item keeps its size, it is not scaled with the
 * actor), so the point is taken at that scale: unscaled it sat about three torch lengths out, the flame and its light
 * away from the torch (SKEL-ITEM-TAGS-52). */
#define AW_ITEMS_ITEM_SCALE 0.25f
int AW_ItemsLightEmitter(const model_t *item,float out[3]) {
    int t,k;
    if(!item)return 0;
    for(t=0;t<used;t++){
        int i=table[t].light_item;
        if(!carries_light(t) || sv.models[i]!=item)continue;
        for(k=0;k<3;k++)out[k]=table[t].emitter[k]*AW_ITEMS_ITEM_SCALE;
        return 1;
    }
    return 0;
}

void AW_ItemsCarriedUpdate(void) {
    int i,t,wanted;
    carriers_check();
    wanted=AW_GuardTorchWanted();       /* as the baked guard torches: at night, or forced (aw_guard_torch.c) */
    for(i=0;i<carrier_count;i++){
        edict_t *a=carriers[i].actor,*e=carriers[i].light;
        t=carriers[i].table;
        if(!wanted || !a || a->free || model_of(a)!=table[t].model || turned(a)){   /* a werewolf carries no light */
            if(e && !e->free)ED_Free(e);
            carriers[i].light=NULL;continue;
        }
        if(!e || e->free){
            int m=table[t].light_item;
            e=carriers[i].light=ED_Alloc();
            e->v.classname=ED_NewString("aw_item")-pr_strings;
            e->v.model=sv.model_precache[m]-pr_strings;e->v.modelindex=m;
            e->v.movetype=MOVETYPE_NONE;e->v.solid=SOLID_NOT;e->v.frame=0;
        }
        carried_pose(i);
    }
}

void AW_ItemsHide(edict_t *items[AW_ITEMS_KINDS]) {
    int k;
    for(k=0;k<AW_ITEMS_KINDS;k++){if(items[k] && !items[k]->free)ED_Free(items[k]);items[k]=NULL;}
    shown_drop(items);
}
/* ACTOR-WEAPON-SHOWN-BEFORE-DRAW-69: a shown set handed from one holder to another (a fight slot's to the sheathe
 * list of aw_combat.c while its put-away plays): the entities and the send's pose of them follow (AW_ItemsPreSend);
 * FROM is left empty. Declared where it is called (aw_combat.c), not in aw_items.h (a build stage reads that header). */
void AW_ItemsMoveSet(edict_t *from[AW_ITEMS_KINDS],edict_t *to[AW_ITEMS_KINDS]);
void AW_ItemsMoveSet(edict_t *from[AW_ITEMS_KINDS],edict_t *to[AW_ITEMS_KINDS]) {
    int k,i=shown_of(from);
    for(k=0;k<AW_ITEMS_KINDS;k++){to[k]=from[k];from[k]=NULL;}
    if(i>=0)shown[i].items=to;
}

int AW_ItemsKinds(edict_t *actor) {
    int t,k,kinds=0,own;
    level_check();
    if(!actor || actor->free || (t=entry_of(model_of(actor)))<0)return 0;
    own=own_of(actor);
    for(k=0;k<AW_ITEMS_KINDS;k++)if(own?own_item[own][k]>0:table[t].item[k])kinds|=1<<k;
    if(carries_light(t))kinds|=AW_ITEMS_LIGHT;
    return kinds;
}
/* A single active player alias: optional per-frame tags use the same parser
 * and bounds as NPC attachments. Storage is released on model/scene change. */
static model_t *player_tag_model;
static float *player_tag_rows;
static int player_tag_frames,player_tag_failed;
void AW_ItemsAliasClear(void){
    free(player_tag_rows);player_tag_rows=NULL;player_tag_model=NULL;
    player_tag_frames=player_tag_failed=0;
}
int AW_ItemsAliasTag(model_t *model,int frame,int kind,float tag[6]){
    FILE *f=NULL;int size,n;char path[96],paths[AW_ITEMS_KINDS][AW_ITEMS_PATH],*text;
    if(!model || model->type!=mod_alias || kind<0 || kind>=AW_ITEMS_KINDS)return 0;
    if(player_tag_model!=model){AW_ItemsAliasClear();player_tag_model=model;}
    if(player_tag_failed)return 0;
    if(!player_tag_rows){
        n=(int)strlen(model->name);
        if(n<5 || n>80 || model->numframes<1 || model->numframes>AW_ITEMS_MAX_FRAMES)goto unavailable;
        strcpy(path,model->name);strcpy(path+n-4,".tag");
        size=COM_FOpenFile(path,&f);
        if(!f || size<20 || size>AW_ITEMS_MAX_FRAMES*AW_ITEMS_ROW*16+256)goto unavailable;
        text=(char *)AW_TryMalloc(size+1);if(!text)goto unavailable;
        if(fread(text,1,size,f)!=(size_t)size){free(text);goto unavailable;}
        fclose(f);f=NULL;text[size]=0;
        player_tag_rows=(float *)AW_TryMalloc(model->numframes*AW_ITEMS_ROW*sizeof(float));
        if(!player_tag_rows){free(text);goto unavailable;}
        player_tag_frames=AW_ItemsParse(text,model->numframes,player_tag_rows,model->numframes,paths);
        free(text);
        if(player_tag_frames!=model->numframes){free(player_tag_rows);player_tag_rows=NULL;goto unavailable;}
    }
    if(frame<0)return 1;
    if(frame>=player_tag_frames || !tag)return 0;
    memcpy(tag,player_tag_rows+frame*AW_ITEMS_ROW+kind*6,6*sizeof(float));return 1;
 unavailable:
    if(f)fclose(f);
    player_tag_failed=1;
    Con_Printf("Player equipment tags unavailable for %s; item pose not substituted.\n",model->name);return 0;
}
#endif
