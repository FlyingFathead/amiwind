/* SPDX-License-Identifier: GPL-2.0-or-later
 * The game side of the compiled scripts (aw_mwvm.c): the file id1/mwscript.awm, the objects of the loaded map,
 * sounds, voices, music, the journal and the player (docs/MWSCRIPT_BYTECODE.md).
 *
 * On by default since v0.0.57 (aw_mwscript 1; dbg mwscript off switches it off, dbg mwscript tells what it does and
 * what was loaded): the file's resident part (scripts, code and the
 * tables they index) is read once when it is switched on, into one block that stays for the session; nothing is
 * allocated while scripts run. At each map change the objects that carry a script are attached: every edict whose
 * original reference (aw_ref) has a script in the file's bindings, and on an outdoor map every scripted placement
 * inside the map (sound markers and other activators the CHIM frames keep without an edict). The bindings are
 * read from disk at the map change and not kept.
 * Sounds play through Quake's mixer from the media catalogue's converted files (sound/pool/a<hash>.wav), voices
 * the same way on the speaker, music through the soundtrack player's own track numbers. */
#include "quakedef.h"
#include "aw_mwvm.h"
#include "aw_mwcode.h"
#include "aw_state.h"
#include "aw_world.h"
#include "aw_save.h"
#include "aw_hinged_door.h"
#include "aw_actors.h"
#include "aw_msgbox.h"
#include "aw_tryalloc.h"
#include "aw_actorstate.h"
#include "aw_character.h"
#include "aw_combat.h"
#include "aw_animpick.h"
#include "aw_pcstanding.h"
#include "aw_effects.h"
#include "aw_talk.h"
#include "aw_glut.h"
#include "aw_dial.h"
#include <ctype.h>

#define FILE_NAME "mwscript.awm"
#define MAX_RESIDENT (1024*1024)
#define LOOPS 32
#define SAYS 16
#define EDICT_REFS 1024
#define LOOP_ENTITY 30000          /* sound channels of placements without an edict (never a real edict) */
#define CHAN_SCRIPT 5
#define CHAN_SCRIPT_VOICE 2

static cvar_t mwscript={"aw_mwscript","1",true};
static unsigned char *resident;static unsigned long resident_bytes,file_bytes;
static const char *load_why="not read yet";   /* the console answer (dbg mwscript): why the file is not loaded */
static int load_failed,attached_map;
static char map_name[64];static void *map_model;
static char *topic_names;static int *topic_offsets;static int32_t *topic_values;
typedef struct {int used,instance,looping,sound,channel,entity;float until,volume;vec3_t origin;} loop_t;
static loop_t loops[LOOPS];
typedef struct {int entity;float until;} say_t;
static say_t says[SAYS];
static struct {uint32_t ref;int entity;} edict_refs[EDICT_REFS];static int edict_ref_count;
static unsigned long attach_edicts,attach_places,attach_rooms,attach_refused,bindings_read;

/* --- strings from the file on disk (only for logging and the journal names) --- */
static int read_string_from(FILE *f,long base,int index,char *out,int capacity){
    uint32_t offset,rows,bytes;unsigned char b[4];int n=0,c;
    out[0]=0;
    if(index<0 || !AW_MwvmSection("STRS",&offset,&rows,&bytes) || (uint32_t)index>=rows)return 0;
    if(fseek(f,base+(long)offset+4L*index,SEEK_SET) || fread(b,1,4,f)!=4)return 0;
    if(fseek(f,base+(long)offset+4L*rows+(long)(((uint32_t)b[0]<<24)|((uint32_t)b[1]<<16)|((uint32_t)b[2]<<8)|b[3]),
             SEEK_SET))return 0;
    while(n<capacity-1 && (c=fgetc(f))!=EOF && c)out[n++]=(char)c;
    out[n]=0;return n;
}
static int read_string(int index,char *out,int capacity){
    FILE *f=NULL;int n=0;
    out[0]=0;
    if(COM_FOpenFile(FILE_NAME,&f)<=0 || !f){if(f)fclose(f);return 0;}
    n=read_string_from(f,ftell(f),index,out,capacity);
    fclose(f);return n;
}
/* Item ids the player's inventory queries name: kept after the first read (a script asks every frame). */
#define ID_CACHE 16
static struct {int index;char id[64];} id_cache[ID_CACHE];static int id_cache_next;
static const char *cached_id(int index){
    int i;
    for(i=0;i<ID_CACHE;i++)if(id_cache[i].id[0] && id_cache[i].index==index)return id_cache[i].id;
    i=id_cache_next;id_cache_next=(id_cache_next+1)%ID_CACHE;
    id_cache[i].index=index;
    if(!read_string(index,id_cache[i].id,sizeof(id_cache[i].id)))return NULL;
    return id_cache[i].id;
}

/* --- the host table --- */
static edict_t *edict_of(int number){return number>0 && number<sv.num_edicts?EDICT_NUM(number):NULL;}
static int entity_of_reference(uint32_t ref){
    int low=0,high=edict_ref_count-1;
    while(low<=high){
        int mid=(low+high)/2;
        if(edict_refs[mid].ref<ref)low=mid+1;else if(edict_refs[mid].ref>ref)high=mid-1;else return edict_refs[mid].entity;
    }
    return -1;
}
/* Where a target is: an edict number (0: none) and a position. */
static int locate(int instance,int target,vec3_t at){
    aw_mwvm_instance_t *in=AW_MwvmInstance(instance);edict_t *e;int number;
    if(target==AW_MWVM_PLAYER){
        if(!sv_player)return -1;
        VectorCopy(sv_player->v.origin,at);return NUM_FOR_EDICT(sv_player);
    }
    if(target==AW_MWVM_SELF){
        if(!in)return -1;
        VectorCopy(in->origin,at);return in->entity>0?in->entity:0;
    }
    number=entity_of_reference(AW_MwvmObjectReference(target));
    e=edict_of(number);if(!e)return -1;
    VectorCopy(e->v.origin,at);return number;
}
static sfx_t *pool_sound(const unsigned char hash[8]){
    char name[32];int i;
    strcpy(name,"pool/a");
    for(i=0;i<8;i++)sprintf(name+6+2*i,"%02x",hash[i]);
    strcpy(name+22,".wav");
    return S_PrecacheSound(name);
}
/* PlaySound, PlaySoundVP, PlaySound3D(VP), PlayLoopSound3D(VP), StopSound and GetSoundPlaying (rules from OpenMW
 * apps/openmw/mwscript/soundextensions.cpp: the 2D forms on the listener, the 3D forms on the reference, a loop
 * until StopSound; GetSoundPlaying asks about that reference's sound) */
static void host_sound(int instance,int target,int sound,int how,float gain,float pitch){
    unsigned char hash[8];int centis,vol,near_units,far_units,entity,i,slot=-1;vec3_t at;sfx_t *s;float attenuation;
    (void)pitch;   /* Quake's mixer has no pitch; the VP forms keep their volume */
    entity=locate(instance,target,at);
    if(how==AW_MWSND_STOP){
        for(i=0;i<LOOPS;i++)if(loops[i].used && loops[i].instance==instance && loops[i].sound==sound){
            S_StopSound(loops[i].entity,loops[i].channel);loops[i].used=0;}
        return;
    }
    if(entity<0 || !AW_MwvmSound(sound,hash,&centis,&vol,&near_units,&far_units))return;
    if(!(s=pool_sound(hash)))return;
    gain*=vol/255.0f;
    if(gain>1)gain=1;
    if(gain<0)gain=0;
    /* Quake's mixer fades linearly to silence at 1000/attenuation engine units; the record's far distance is
     * in game units (4 per engine unit). The 2D form plays on the listener at full volume. */
    attenuation=how==AW_MWSND_2D || far_units<=0?0:1000.0f/((float)far_units*0.25f);
    if(how==AW_MWSND_2D){entity=cl.viewentity;VectorCopy(r_origin,at);}
    for(i=0;i<LOOPS;i++){
        if(loops[i].used && loops[i].instance==instance && loops[i].sound==sound){
            if(how==AW_MWSND_LOOP && realtime<loops[i].until)return;   /* already looping */
            slot=i;break;
        }
        if(!loops[i].used && slot<0)slot=i;
    }
    if(slot<0)return;
    loops[slot].used=1;loops[slot].instance=instance;loops[slot].sound=sound;
    loops[slot].entity=entity>0?entity:LOOP_ENTITY+slot;loops[slot].channel=CHAN_SCRIPT;
    loops[slot].until=(float)realtime+(centis>0?centis/100.0f:0.5f);VectorCopy(at,loops[slot].origin);
    loops[slot].looping=how==AW_MWSND_LOOP?1:0;loops[slot].volume=gain*255.0f/(vol>0?vol:255);
    S_StartSound(loops[slot].entity,CHAN_SCRIPT,s,at,gain,attenuation);
}
static int host_sound_playing(int instance,int target,int sound){
    int i;(void)target;
    for(i=0;i<LOOPS;i++)if(loops[i].used && loops[i].instance==instance && loops[i].sound==sound &&
                           realtime<loops[i].until)return 1;
    return 0;
}
/* Say (rule from OpenMW apps/openmw/mwscript/soundextensions.cpp OpSay: the voice file on the actor through the
 * sound manager's say, its text shown only as a subtitle; SayDone: OpSayDone, the actor's say finished). The
 * dialogue's own voice lines (greetings, combat taunts, hit and flee lines) go through
 * apps/openmw/mwdialogue/dialoguemanagerimp.cpp DialogueManager::say instead, which also refuses an actor that is
 * already speaking, an NPC under water and a knocked-down actor: the greeting and combat tables carry that rule
 * (docs/NPC_VOICE_TABLE.md), not a script's Say. */
static void host_say(int instance,int target,int voice,int text){
    unsigned char hash[8];int centis,entity,i,slot=0;vec3_t at;sfx_t *s;
    (void)text;
    entity=locate(instance,target,at);
    if(entity<=0 || !AW_MwvmVoice(voice,hash,&centis) || !(s=pool_sound(hash)))return;
    S_StartSound(entity,CHAN_SCRIPT_VOICE,s,at,1.0f,1.0f);
    for(i=0;i<SAYS;i++){if(says[i].entity==entity){slot=i;break;}if(says[i].until<says[slot].until)slot=i;}
    says[slot].entity=entity;says[slot].until=(float)realtime+centis/100.0f;
}
static int host_say_done(int instance,int target){
    int entity,i;vec3_t at;
    entity=locate(instance,target,at);
    for(i=0;i<SAYS;i++)if(says[i].entity==entity && entity>0 && realtime<says[i].until)return 0;
    return 1;
}
static void host_music(int music){int track=AW_MwvmMusic(music);if(track>=0)AW_MusicScriptTrack(track);}
static float host_distance(int instance,int target){
    vec3_t a,b,d;
    if(locate(instance,AW_MWVM_SELF,a)<0 || locate(instance,target,b)<0)return 1.0e9f;
    VectorSubtract(a,b,d);
    return (float)Length(d)*4.0f;   /* game units */
}
static int host_menu_mode(void){return key_dest!=key_game || AW_ModalWorldFrozen();}
static int32_t host_query(int instance,int query,int operand){
    const char *id;(void)instance;
    if(query==AWQ_ITEM_COUNT && (id=cached_id(operand))!=NULL)return AW_StateGet(&aw_state,AW_ITEM,id);
    return 0;   /* the other queries are not available yet (the compiler marks such scripts VOLATILE) */
}
static int32_t host_journal_get(int topic){
    int32_t story;
    if(topic<0 || topic>=AW_MwvmTopicCount() || !topic_values)return 0;
    story=AW_StateGet(&aw_state,AW_JOURNAL,topic_names+topic_offsets[topic]);
    return story>topic_values[topic]?story:topic_values[topic];
}
static void host_journal_set(int topic,int32_t index,int advance){
    const char *name;
    if(topic<0 || topic>=AW_MwvmTopicCount() || !topic_values)return;
    name=topic_names+topic_offsets[topic];
    if(advance){
        if(index<=host_journal_get(topic))return;
        topic_values[topic]=index;AW_JournalAdd(&aw_state,name,index);   /* the journal UI's copy, while it has room */
    }else{
        topic_values[topic]=index;AW_StateSet(&aw_state,AW_JOURNAL,name,index);
    }
}
static void host_notyet(int name,int script){
    char what[48],where[48];
    read_string(name,what,sizeof(what));read_string(script,where,sizeof(where));
    Con_DPrintf("MWScript: %s is not carried out yet (first in %s); logged once.\n",what,where);
}
static void host_warn(const char *what,int script){
    char where[48];
    if(script>=0)read_string(script,where,sizeof(where));else strcpy(where,"-");
    Con_Printf("MWScript: %s (%s).\n",what,where);
}
/* --- object state (v0.0.51): Disable/Enable and Lock/Unlock by the placement's reference, kept in saved games
 * (aw_save.h AW_CHANGE_DISABLED, AW_CHANGE_LOCK). A disabled placement with an edict is hidden (no model) and not
 * solid until Enable; at every map change the new map's edicts are hidden again. Not yet: an actor the CHIM window
 * spawns after the map change, and a CHIM static without an edict (they keep showing). */
#define OBJECTS 1024
typedef struct {
    uint32_t ref;
    unsigned char disabled,lock_set,level,last_level;   /* level 0 unlocked .. 100 */
    int entity,map;                                     /* the edict hidden, on attach number MAP */
    float model,solid;                                  /* what it had before */
} object_t;
static object_t objects[OBJECTS];static int object_count;
static void object_activate(uint32_t reference);
static unsigned long objects_hidden,objects_full;
static object_t *object_find(uint32_t ref,int create){
    int i;
    for(i=0;i<object_count;i++)if(objects[i].ref==ref)return &objects[i];
    if(!create)return NULL;
    if(object_count==OBJECTS){objects_full++;return NULL;}
    memset(&objects[object_count],0,sizeof(object_t));objects[object_count].ref=ref;objects[object_count].entity=-1;
    return &objects[object_count++];
}
static uint32_t target_reference(int instance,int target){
    aw_mwvm_instance_t *in;
    if(target==AW_MWVM_PLAYER)return 0;      /* the player is never disabled or locked */
    if(target==AW_MWVM_SELF){in=AW_MwvmInstance(instance);return in?in->reference:0;}
    return AW_MwvmObjectReference(target);
}
static void object_hide(object_t *o){
    int number=entity_of_reference(o->ref);edict_t *e=edict_of(number);
    if(!e || e->free)return;
    if(o->entity!=number || o->map!=attached_map || e->v.modelindex){
        o->model=e->v.modelindex;o->solid=e->v.solid;o->entity=number;o->map=attached_map;
    }
    e->v.modelindex=0;e->v.solid=SOLID_NOT;SV_LinkEdict(e,false);objects_hidden++;
}
static void object_show(object_t *o){
    edict_t *e=edict_of(o->entity);
    if(!e || e->free || o->map!=attached_map)return;    /* hidden on another map: this one never hid it */
    e->v.modelindex=o->model;e->v.solid=o->solid;SV_LinkEdict(e,false);o->entity=-1;
}
static int32_t host_object(int instance,int target,int op,int32_t value){
    uint32_t ref=target_reference(instance,target);object_t *o;
    if(!ref)return 0;
    switch(op){
    case AWM_ENABLE:
        if((o=object_find(ref,0))!=NULL && o->disabled){o->disabled=0;object_show(o);}
        return 0;
    case AWM_DISABLE:
        if((o=object_find(ref,1))!=NULL && !o->disabled){o->disabled=1;object_hide(o);}
        return 0;
    case AWM_GETDISABLED:
        return (o=object_find(ref,0))!=NULL && o->disabled;
    case AWM_LOCK:
        if(!(o=object_find(ref,1)))return 0;
        /* Lock without a number: the level it had last (100 when it never had one), as the original */
        if(value<0)value=o->last_level?o->last_level:100;
        if(value>100)value=100;
        o->lock_set=1;o->level=(unsigned char)value;if(value)o->last_level=(unsigned char)value;
        return 0;
    case AWM_UNLOCK:
        if(!(o=object_find(ref,1)))return 0;
        if(o->lock_set && o->level)o->last_level=o->level;
        o->lock_set=1;o->level=0;
        return 0;
    case AWM_ACTIVATE:
        object_activate(ref);
        return 0;
    case AWM_GETLOCKED:{
        /* a door no script has locked: its lock in the game data */
        int original=AW_HingedDoorOriginalLock(ref);
        return AW_ObjectLockLevel(ref,original>0?original:0)>0;}
    }
    return 0;
}
/* Activation (the original's rule): the player's use of an object whose attached script reads OnActivate goes to
 * the script (OnActivate reads 1 on its next run) and the object does nothing until the script's Activate. Off
 * with the scripts off; a script the engine carries by hand (the census office) is never attached. */
static unsigned long intercepted,activated;
static int object_intercept(unsigned reference){
    int k,n;
    if(!mwscript.value || !resident || !reference)return 0;
    n=AW_MwvmInstanceCount();
    for(k=0;k<n;k++){
        aw_mwvm_instance_t *in=AW_MwvmInstance(k);
        if(!in || !(in->flags&AWI_USED) || (in->flags&AWI_GLOBAL) || in->reference!=reference)continue;
        if(!(AW_MwvmScriptFlags(in->script)&AWS_ONACTIVATE))continue;
        in->flags|=AWI_ACTIVATED;in->flags&=~AWI_QUIET;intercepted++;
        return 1;
    }
    return 0;
}
/* E on an object with no NPC under the crosshair (v0.0.57): the scripted placement that reads OnActivate nearest the
 * view's line, within the activation distance (iMaxActivateDist 192 game units, the original's GMST; OpenMW
 * mwworld/worldimp.cpp getMaxActivationDistance) and inside a narrow cone (cos 0.95 against the view). Activators and
 * other placements the CHIM world keeps without an edict are scripts' instances with their positions; the script's
 * OnActivate reads 1 on its next run. 1 when one took the use. */
static void to_game_units(const vec3_t local,float out[3]);
int AW_MwscriptUseInView(const float *eye,const float *forward);
int AW_MwscriptUseInView(const float *eye,const float *forward){
    int k,n,best=-1;float best_cos=0.95f,e[3];
    if(!mwscript.value || !resident)return 0;
    to_game_units(eye,e);
    n=AW_MwvmInstanceCount();
    for(k=0;k<n;k++){
        aw_mwvm_instance_t *in=AW_MwvmInstance(k);float d[3],g[3],len,c;vec3_t l;
        if(!in || !(in->flags&AWI_USED) || (in->flags&AWI_GLOBAL) || !in->reference)continue;
        if(!(AW_MwvmScriptFlags(in->script)&AWS_ONACTIVATE))continue;
        VectorCopy(in->origin,l);to_game_units(l,g);
        d[0]=g[0]-e[0];d[1]=g[1]-e[1];d[2]=g[2]-e[2];
        len=(float)sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]);
        if(len>192.0f || len<1.0f)continue;
        d[0]=in->origin[0]-eye[0];d[1]=in->origin[1]-eye[1];d[2]=in->origin[2]-eye[2];
        len=(float)sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]);
        c=(d[0]*forward[0]+d[1]*forward[1]+d[2]*forward[2])/len;
        if(c>best_cos){best_cos=c;best=k;}
    }
    if(best<0)return 0;
    {aw_mwvm_instance_t *in=AW_MwvmInstance(best);in->flags|=AWI_ACTIVATED;in->flags&=~AWI_QUIET;intercepted++;}
    return 1;
}
static void object_activate(uint32_t reference){
    activated++;
    if(AW_HingedDoorActivate(reference))return;
    AW_SceneActivate(reference);    /* a load door of this map; other objects' own use: not yet */
}
int AW_ObjectDisabled(unsigned int reference){object_t *o=object_find(reference,0);return o && o->disabled;}
int AW_ObjectLockLevel(unsigned int reference,int original){
    object_t *o=object_find(reference,0);
    return o && o->lock_set?o->level:original;
}
/* Saved games: merged by key into the change list the actors exported. */
static int objects_export(aw_changes_t *out){
    int i,j;uint32_t flags,key;
    for(i=0;i<object_count;i++){
        const object_t *o=&objects[i];
        flags=(o->disabled?AW_CHANGE_DISABLED:0)|
              (o->lock_set?AW_CHANGE_LOCK|((uint32_t)o->level<<AW_CHANGE_LOCK_SHIFT):0);
        if(!flags || !o->ref || o->ref>0xFFFFFFu)continue;
        key=AW_SaveChangeKey(o->ref);
        for(j=0;j<out->count;j++)if(out->entry[j].key==key)break;
        if(j==out->count){
            if(out->count==AW_SAVE_CHANGES)return -1;
            memset(&out->entry[j],0,sizeof(aw_change_t));out->entry[j].key=key;out->count++;
        }
        out->entry[j].flags=(out->entry[j].flags&~(AW_CHANGE_DISABLED|AW_CHANGE_LOCK|AW_CHANGE_LOCK_LEVEL))|flags;
    }
    return out->count;
}
static void objects_import(const aw_changes_t *in){
    int i;object_t *o;
    object_count=0;
    for(i=0;i<in->count;i++){
        const aw_change_t *e=&in->entry[i];
        if(!(e->flags&(AW_CHANGE_DISABLED|AW_CHANGE_LOCK)) || (e->key&AW_CHANGE_BUILDER))continue;
        if(!(o=object_find(e->key,1)))break;
        o->disabled=(e->flags&AW_CHANGE_DISABLED)?1:0;
        if(e->flags&AW_CHANGE_LOCK){
            o->lock_set=1;o->level=(unsigned char)((e->flags&AW_CHANGE_LOCK_LEVEL)>>AW_CHANGE_LOCK_SHIFT);
            o->last_level=o->level;
        }
    }
    map_model=NULL;   /* the loaded map attaches again: its disabled edicts are hidden there */
}

/* --- the actor record (v0.0.54; aw_actorstate.c, docs/ACTOR_STATE.md): the actor table's rows are read through one
 * handle on the file kept open for the session; the live records are the actor state's. The scripts' actor calls
 * act on it with OpenMW's rules; the player's stats are the character sheet's (aw_character), read into the
 * player's record before a call and written back after; an NPC in a fight keeps its health, magicka and fatigue
 * in its fighter sheet (aw_combat.c) until combat reads the record itself, so both are kept the same here. --- */
int (*aw_mwscript_combat_end)(struct edict_s *e);
int (*aw_mwscript_wander)(struct edict_s *e,int distance,int duration,int hour,const unsigned char idle[8],int repeat);
/* The ambient tables' current AI package of an actor (aw_ambient.h AW_AmbientAiPackage, assigned in AW_AmbientInit):
 * OpenMW's package number (-1 none, 0 Wander, ...) and *DONE once it has run out; NULL: -1 and 0. The ambient tables
 * move the scripts' state generation when a package starts or ends (AW_MwvmStateChanged). */
int (*aw_mwscript_ai_package)(struct edict_s *e,int *done);
int (*aw_mwscript_travel)(struct edict_s *e,const float to[3]);
int (*aw_mwscript_follow)(struct edict_s *e,struct edict_s *target,float hours,const float *final);
int (*aw_mwscript_packages_export)(unsigned char *out,int capacity);
int (*aw_mwscript_packages_import)(const unsigned char *data,int bytes);
static unsigned long travels,travels_refused,follows,follows_refused,positions,positions_refused;
static FILE *actor_file;static long actor_base;static int actors_failed,dagoth_ur_1=-2;
static unsigned long actor_calls,actor_misses,combat_starts,combat_stops,wanders;
static int actor_read(void *context,uint32_t offset,void *out,uint32_t bytes){
    (void)context;
    if(!actor_file || fseek(actor_file,actor_base+(long)offset,SEEK_SET))return 1;
    return fread(out,1,bytes,actor_file)!=bytes;
}
int AW_MwscriptActors(void){
    static const aw_actorstate_io_t io={actor_read,NULL};
    unsigned char head[16+16*32];int length,n;
    if(AW_ActorStateReady())return 1;
    if(actors_failed)return 0;
    actors_failed=1;
    if(actor_file){fclose(actor_file);actor_file=NULL;}
    length=COM_FOpenFile(FILE_NAME,&actor_file);
    if(!actor_file || length<16)return 0;
    actor_base=ftell(actor_file);
    if(fread(head,1,16,actor_file)!=16 || memcmp(head,"AWMS",4))return 0;
    n=(head[6]<<8)|head[7];if(n>32)n=32;
    if(fread(head+16,1,16*n,actor_file)!=(size_t)(16*n) || !AW_ActorStateOpen(head,16+16*n,&io))return 0;
    actors_failed=0;
    Con_DPrintf("Actor record: %d actors, %lu bytes kept.\n",AW_ActorCount(),AW_ActorStateResident());
    return 1;
}
static int row_of_edict(edict_t *e){
    eval_t *v=e?GetEdictFieldValue(e,"aw_source_id"):NULL;
    if(!v || !v->string || !*(pr_strings+v->string))return AW_ACTOR_NONE;
    return AW_ActorFind(pr_strings+v->string);
}
/* each instance's own actor row, found once by its edict's record id */
static int instance_row[AW_MWVM_INSTANCES];static uint32_t instance_row_ref[AW_MWVM_INSTANCES];
static aw_actor_t *player_record(void){
    aw_actor_t *a=AW_ActorPlayer();int i;
    if(!a || !aw_character.valid)return a;
    for(i=0;i<8;i++){a->attr_base[i]=aw_character.attributes[i];a->attr_mod[i]=(short)(aw_character.modifiers[i]-aw_character.damage[i]);}
    for(i=0;i<27;i++){a->skill_base[i]=aw_character.skills[i];a->skill_mod[i]=0;}
    for(i=0;i<3;i++){a->dyn_base[i]=aw_character.maximum[i];a->dyn_cur[i]=aw_character.current[i];}
    if(sv_player)a->dyn_cur[0]=sv_player->v.health;      /* the player's live health is the edict's */
    a->level=(short)aw_character.level;a->kind=0;
    return a;
}
static void player_store(const aw_actor_t *a){
    int i;
    if(!a || !aw_character.valid)return;
    for(i=0;i<8;i++){
        int mod=a->attr_mod[i];
        aw_character.attributes[i]=a->attr_base[i];
        /* the sheet keeps its fortify (race, birthsign) and its damage apart */
        if(mod>=aw_character.modifiers[i])aw_character.damage[i]=0;
        if(mod>aw_character.modifiers[i])aw_character.modifiers[i]=(short)mod;
        else aw_character.damage[i]=(short)(aw_character.modifiers[i]-mod);
    }
    for(i=0;i<27;i++)aw_character.skills[i]=(short)(a->skill_base[i]+a->skill_mod[i]);
    for(i=0;i<3;i++){aw_character.maximum[i]=a->dyn_base[i];aw_character.current[i]=a->dyn_cur[i];}
    aw_character.level=a->level;
    if(sv_player)sv_player->v.health=a->dyn_cur[0];
}
/* The record a script's target names: the player's, its own object's, or another object's (its one placed
 * reference and the OACT table). EDICT: the actor's edict when its map has it loaded. */
static aw_actor_t *actor_of(int instance,int target,edict_t **edict){
    aw_mwvm_instance_t *in=AW_MwvmInstance(instance);int row;uint32_t ref;edict_t *e=NULL;
    *edict=NULL;
    if(!AW_MwscriptActors())return NULL;
    if(target==AW_MWVM_PLAYER){*edict=sv_player;return player_record();}
    if(target==AW_MWVM_SELF){
        if(!in || !in->reference || instance<0 || instance>=AW_MWVM_INSTANCES)return NULL;
        ref=in->reference;e=in->entity>0?edict_of(in->entity):NULL;
        if(instance_row_ref[instance]!=ref){instance_row_ref[instance]=ref;instance_row[instance]=row_of_edict(e);}
        row=instance_row[instance];
    }else{
        /* an id placed more than once (no one reference): not yet (OpenMW changes the record of every copy) */
        ref=AW_MwvmObjectReference(target);row=AW_MwvmObjectActor(target);
        if(!ref)return NULL;
        e=edict_of(entity_of_reference(ref));
    }
    if(row==AW_ACTOR_NONE)return NULL;
    *edict=e && !e->free?e:NULL;
    return AW_ActorGet(ref,row,1);
}
/* an engaged NPC: its fighter sheet holds the live dynamic stats (aw_combat.c) */
static aw_fighter_t *fighter_of(edict_t *e){return e && e!=sv_player?(aw_fighter_t *)AW_CombatFighter(e):NULL;}
static void from_fighter(aw_actor_t *a,const aw_fighter_t *f){
    if(!a || !f)return;
    a->dyn_cur[0]=f->health;if(f->health_max>0)a->dyn_base[0]=f->health_max;
    a->dyn_cur[2]=f->fatigue;if(f->fatigue_max>0)a->dyn_base[2]=f->fatigue_max;
    a->dyn_cur[1]=f->magicka;
    if(f->dead && !(a->flags&AWL_DEAD))AW_ActorKill(a);
}
static void to_fighter(const aw_actor_t *a,aw_fighter_t *f){
    if(!a || !f)return;
    f->health=a->dyn_cur[0];f->health_max=a->dyn_base[0];f->fatigue=a->dyn_cur[2];f->fatigue_max=a->dyn_base[2];
    f->magicka=a->dyn_cur[1];
}
static aw_mwcell_t host_actor(int instance,int target,int verb,int stat,aw_mwcell_t value){
    aw_mwcell_t out;edict_t *e;aw_actor_t *a=actor_of(instance,target,&e);aw_fighter_t *f;
    int whole=stat>=AWA_LEVEL && verb!=AWV_RATIO;float v;
    out.i=0;actor_calls++;
    if(!a){actor_misses++;return out;}
    f=fighter_of(e);from_fighter(a,f);
    if(verb==AWV_GET || verb==AWV_RATIO){
        if(verb==AWV_RATIO)out.f=AW_ActorRatio(a,stat);
        else if(stat==AWA_ONDEATH)out.i=AW_ActorOnDeath(a);
        else if(whole)out.i=(int32_t)AW_ActorStat(a,stat);
        else out.f=AW_ActorStat(a,stat);
        return out;
    }
    /* the original's endgame scripts change dagoth_ur_1 from afar after he is gone: ignored, as OpenMW does
     * (statsextensions.cpp OpModDynamic) */
    if(dagoth_ur_1==-2)dagoth_ur_1=AW_ActorFind("dagoth_ur_1");
    if(target>=0 && !e && a->base==(uint16_t)dagoth_ur_1)return out;
    v=whole?(float)value.i:value.f;
    if(verb==AWV_SET)AW_ActorSetStat(a,stat,v);
    else if(verb==AWV_MOD)AW_ActorModStat(a,stat,v);
    else AW_ActorModCurrent(a,stat,v);
    if(a->dyn_cur[0]<=0 && a->dyn_base[0]>0 && !(a->flags&AWL_DEAD) && a->reference!=AW_ACTOR_PLAYER_REF)AW_ActorKill(a);
    if(a->reference==AW_ACTOR_PLAYER_REF)player_store(a);
    to_fighter(a,f);
    return out;
}
static void folded_item_id(int item,char *out,int capacity){
    aw_item_t it;int i;
    out[0]=0;
    if(!AW_ActorItem(item,&it) || !read_string(it.id,out,capacity))return;
    for(i=0;out[i];i++)if(out[i]>='A' && out[i]<='Z')out[i]=(char)(out[i]+32);
}
static int32_t host_item(int instance,int target,int verb,int item,int32_t count){
    edict_t *e;aw_actor_t *a=actor_of(instance,target,&e);aw_item_t it;
    actor_calls++;
    if(!a){actor_misses++;return 0;}
    if(verb && (!AW_ActorItem(item,&it) || it.kind==AWK_UNKNOWN))return 0;   /* an id no record has (OpenMW: refused) */
    if(a->reference==AW_ACTOR_PLAYER_REF){
        /* the player's inventory is the game state the engine keeps (aw_state.c AW_ITEM) */
        char id[64];int32_t have;
        folded_item_id(item,id,sizeof(id));
        if(!id[0])return 0;
        have=AW_StateGet(&aw_state,AW_ITEM,id);
        if(count<0)count=(int32_t)(uint16_t)count;
        if(verb==1 && count)AW_StateSet(&aw_state,AW_ITEM,id,have+count);
        else if(verb==2 && count)AW_StateSet(&aw_state,AW_ITEM,id,have>count?have-count:0);
        return AW_StateGet(&aw_state,AW_ITEM,id);
    }
    if(verb==1)return AW_ActorAddItem(a,item,count);
    if(verb==2)return AW_ActorRemoveItem(a,item,count);
    return AW_ActorItemCount(a,item);
}
static int32_t host_spell(int instance,int target,int verb,int spell){
    edict_t *e;aw_actor_t *a=actor_of(instance,target,&e);
    actor_calls++;
    if(!a){actor_misses++;return 0;}
    if(verb==1)return AW_ActorAddSpell(a,spell);
    if(verb==2)return AW_ActorRemoveSpell(a,spell);
    if(verb==AWM_SPELL_COMMON_DISEASE)return AW_ActorHasSpellType(a,3);   /* ASPT type 3: a common disease */
    if(verb==AWM_SPELL_BLIGHT_DISEASE)return AW_ActorHasSpellType(a,2);   /* ASPT type 2: a blight disease */
    return AW_ActorHasSpell(a,spell);
}
static void host_combat(int instance,int target,int verb,int other){
    edict_t *e;aw_actor_t *a=actor_of(instance,target,&e);
    actor_calls++;
    if(!a || !e || e==sv_player){actor_misses++;return;}
    if(verb==0){
        /* StartCombat with the player (the one fight the combat layer has): not when either is dead (OpenMW) */
        aw_fighter_t sheet;eval_t *v=GetEdictFieldValue(e,"aw_source_id");
        if(other!=AW_MWVM_PLAYER || (a->flags&AWL_DEAD) || !sv_player || sv_player->v.health<=0)return;
        if(!v || !v->string || !AW_CombatActorLoad(pr_strings+v->string,&sheet))return;
        to_fighter(a,&sheet);
        if(AW_CombatEngage(e,&sheet,NULL)){a->flags|=AWL_COMBAT;combat_starts++;}
        return;
    }
    a->flags&=~AWL_COMBAT;
    if(aw_mwscript_combat_end){aw_mwscript_combat_end(e);combat_stops++;}
    else Con_DPrintf("MWScript: StopCombat waits for the combat layer's per-actor end.\n");
}
static int32_t host_dead_count(int actor){return AW_MwscriptActors()?AW_ActorDeadCount(actor):0;}
/* AIWander's arguments as OpenMW's OpAiWander reads them: range, duration, time; then, if there are more, the
 * first is an idle chance the game never used (dropped), up to eight idle chances (Idle2..Idle9; any given makes the
 * package repeat), and a last explicit repeat flag */
static void host_wander(int instance,int target,const int32_t *values,int count){
    edict_t *e;aw_actor_t *a=actor_of(instance,target,&e);unsigned char idle[8];int i,repeat=0,n;
    actor_calls++;
    if(!e || e==sv_player){actor_misses++;return;}
    (void)a;
    memset(idle,0,sizeof(idle));
    n=count-4;           /* after range, duration, time and the unused chance */
    for(i=0;i<8 && i<n;i++){int32_t c=values[4+i];idle[i]=(unsigned char)(c<0?0:c>100?100:c);repeat=1;}
    if(n>8)repeat=values[12]!=0;
    if(aw_mwscript_wander){aw_mwscript_wander(e,values[0],values[1],values[2],idle,repeat);wanders++;}
    else Con_DPrintf("MWScript: AIWander waits for the ambient tables.\n");
}
/* GetCurrentAIPackage and GetAIPackageDone (rules from OpenMW apps/openmw/mwscript/aiextensions.cpp
 * OpGetCurrentAIPackage, OpGetAiPackageDone): the actor's package by the ambient tables; a dead actor has none
 * (-1); no actor, the player or no ambient tables: -1 and not done */
static unsigned long ai_queries;
static int32_t host_ai_package(int instance,int target,int verb){
    edict_t *e;aw_actor_t *a=actor_of(instance,target,&e);int done=0,current;
    ai_queries++;
    if(!e || e==sv_player || !aw_mwscript_ai_package)return verb?0:-1;
    current=aw_mwscript_ai_package(e,&done);
    if(verb)return done?1:0;
    if((a && (a->flags&AWL_DEAD)) || e->v.health<=0)return -1;
    return current;
}
int AW_MwscriptSpeedAttribute(struct edict_s *e){
    int row;aw_actor_t *a;uint32_t ref;eval_t *v;
    if(!e || !AW_MwscriptActors())return -1;
    if(e==sv_player)return (int)AW_ActorStat(player_record(),AWA_ATTRIBUTE+4);
    v=GetEdictFieldValue(e,"aw_ref");ref=v && v->_float>0?(uint32_t)v->_float:0;
    if((row=row_of_edict(e))==AW_ACTOR_NONE)return -1;
    a=ref?AW_ActorGet(ref,row,0):NULL;
    if(a)return (int)AW_ActorStat(a,AWA_ATTRIBUTE+4);
    {aw_actor_base_t b;return AW_ActorBase(row,&b)?b.attributes[4]:-1;}
}
/* The drawn weapon's type for the animation's stance (aw_animpick.h): the record's weapon entry; found once per
 * engagement (the record is a binary search on disk). */
int AW_MwscriptWeaponType(struct edict_s *e){
    int row;
    if(!e || e==sv_player || !AW_MwscriptActors() || (row=row_of_edict(e))==AW_ACTOR_NONE)return -1;
    return AW_ActorWeaponType(row);
}
/* Once a frame while anyone fights: the fighters' health and deaths reach their records (the dead count, OnDeath),
 * and the scripts that read actors wake (AW_MwvmStateChanged). */
static void actors_from_fights(void){
    int i;edict_t *e;const aw_fighter_t *f;
    if(!AW_CombatHostiles() || !AW_ActorStateReady())return;
    for(i=1;i<sv.num_edicts;i++){
        eval_t *v;uint32_t ref;int row;aw_actor_t *a;float before;int dead;
        e=EDICT_NUM(i);if(e->free || !(f=AW_CombatFighter(e)))continue;
        v=GetEdictFieldValue(e,"aw_ref");ref=v && v->_float>0?(uint32_t)v->_float:0;
        if(!ref || (row=row_of_edict(e))==AW_ACTOR_NONE || !(a=AW_ActorGet(ref,row,1)))continue;
        before=a->dyn_cur[0];dead=(a->flags&AWL_DEAD)!=0;
        from_fighter(a,f);
        if(a->dyn_cur[0]!=before || dead!=((a->flags&AWL_DEAD)!=0)){
            if(a->dyn_cur[0]!=a->dyn_base[0])a->flags|=AWL_CHANGED;
            AW_MwvmStateChanged();
        }
    }
}

/* --- MessageBox (aw_msgbox.c shows it): the text and the buttons read from the file's strings --- */
static void host_message(int instance,int text,const float *numbers,int number,const unsigned char *buttons,int count){
    static char format[AW_MSGBOX_TEXT],shown[AW_MSGBOX_TEXT],labels[AW_MSGBOX_BUTTONS][AW_MSGBOX_LABEL];
    const char *list[AW_MSGBOX_BUTTONS];int i;(void)instance;
    if(!read_string(text,format,sizeof(format)))return;
    AW_MsgBoxFormat(shown,sizeof(shown),format,numbers,number);
    if(count>AW_MSGBOX_BUTTONS)count=AW_MSGBOX_BUTTONS;
    for(i=0;i<count;i++){
        if(!read_string((buttons[2*i]<<8)|buttons[2*i+1],labels[i],sizeof(labels[i])))labels[i][0]=0;
        list[i]=labels[i];
    }
    AW_MsgBoxShow(shown,list,count);
}
static int host_button(int instance){(void)instance;return AW_MsgBoxPressed();}

/* --- the world and cell lookups (v0.0.54) --- */
/* The player's cell, worked out once a frame in AW_MwscriptTick: outdoors the grid cell of the player's position in
 * the game's coordinates (8192 game units a cell), in a room its stable number (worldspawn _aw_cell_int). A change
 * moves the state generation, so the quiet scripts that ask GetPCCell run again. */
static int pc_kind,pc_x,pc_y;
static long map_room;                /* the loaded room's stable number, 0 outdoors (attach_map) */
static float room_shift[3];          /* a room map's local position = game position / 4 + this (attach_map) */
static int host_player_cell(int *x,int *y){*x=pc_x;*y=pc_y;return pc_kind;}
static void to_game_units(const vec3_t local,float out[3]){
    int i;
    if(AW_WorldToSource(sv.name,local,out))return;            /* an outdoor map: its own origin */
    for(i=0;i<3;i++)out[i]=(local[i]-room_shift[i])*4.0f;     /* a room map: a quarter scale plus its shift */
}
static void player_cell_update(void){
    int kind=0,x=0,y=0;float at[3];
    if(sv_player){
        if(map_room){kind=2;x=(int)map_room;}
        else if(AW_WorldToSource(sv.name,sv_player->v.origin,at)){
            kind=1;x=(int)floor(at[0]/8192.0f);y=(int)floor(at[1]/8192.0f);
        }
    }
    if(kind!=pc_kind || x!=pc_x || y!=pc_y){pc_kind=kind;pc_x=x;pc_y=y;AW_MwvmStateChanged();}
}
/* GetPos (rule from OpenMW apps/openmw/mwscript/transformationextensions.cpp OpGetPos: the reference's position on
 * the axis, in game units) */
static float host_position(int instance,int target,int axis){
    vec3_t local;float game[3];
    if(axis<0 || axis>2 || locate(instance,target,local)<0)return 0.0f;
    to_game_units(local,game);
    return game[axis];
}
/* PositionCell of the player (rule from OpenMW apps/openmw/mwscript/transformationextensions.cpp OpPositionCell):
 * into a room, its map loaded the way a door loads it with the arrival the builder worked out (aw_scene.c
 * AW_SceneLoadRoom); outdoors (also a cell no interior has, as OpenMW), the coordinate teleport of dbg tp X Y Z
 * (AW_MapTeleportAt: the map that holds the point, the first surface at or below Z; the view keeps its yaw). A room
 * not on this disk, a pending load or the story's hold: nothing happens, counted. */
static unsigned long player_moves,player_moves_refused;
static int host_player_move(int instance,int kind,int map,const float *at,float yaw){
    char name[64];float source[3];int ok=0;(void)instance;
    if(kind==AWM_MOVE_OUTDOORS){source[0]=at[0];source[1]=at[1];source[2]=at[2];ok=AW_MapTeleportAt(source,1);}
    else if(kind==AWM_MOVE_ROOM && read_string(map,name,sizeof(name)))ok=AW_SceneLoadRoom(name,at,yaw);
    if(ok)player_moves++;
    else{player_moves_refused++;Con_DPrintf("MWScript: PositionCell of the player not possible here (kind %d).\n",kind);}
    return ok;
}
/* The import route: each NOTYET call is counted (aw_mwscript_status); a function carried out here by its number
 * needs no new opcode and no change of the file's format; the others are logged once and read 0.
 * v0.0.57: the player's standing (aw_pcstanding.c; rules from OpenMW apps/openmw/mwscript/statsextensions.cpp
 * OpGetPCCrimeLevel, OpSetPCCrimeLevel, OpModPCCrimeLevel, OpPCJoinFaction, OpPCRaiseRank, OpPCLowerRank,
 * OpGetPCRank, OpGetPCFacRep, OpSetPCFacRep, OpModPCFacRep, OpPcExpelled, OpPcExpell, OpPcClearExpelled, OpGetRace;
 * dialogueextensions.cpp OpGetReputation, OpSetReputation, OpModReputation). A faction not named is the target
 * actor's own (the player has none: rank -1). */
static unsigned long standing_calls,standing_misses,anim_plays,anim_misses,topics_added,cures,effects_cast;
static unsigned long greetings,greetings_missed,rotations,rotations_missed;
dfunction_t *ED_FindFunction(char *name);
/* The topics the player knows (AddTopic, v0.0.57): one bit per row of the file's TOPC section (the game's dialogue
 * topics, sorted; the names stay on disk), taken when the file loads; saved with the game. */
static unsigned char *known_topics;static int topic_rows,topic_bytes;
int AW_MwscriptTopicKnown(int row);   /* the dialogue window's question (DIALOGUE-57): 1 when row ROW is known */
int AW_MwscriptTopicKnown(int row){return row>=0 && row<topic_rows && known_topics && (known_topics[row>>3]>>(row&7)&1);}
/* ForceGreeting's act on actor E (see AWF_FORCEGREETING below); 1 when the greeting was played */
static int force_greeting(edict_t *e){
    dfunction_t *greet;int self,other;
    if(!e || e->free || e==sv_player || !sv_player || strcmp(pr_strings+e->v.classname,"aw_npc") ||
       (aw_can_talk && !aw_can_talk(e)) || !(greet=ED_FindFunction("aw_greet"))){greetings_missed++;return 0;}
    self=pr_global_struct->self;other=pr_global_struct->other;
    pr_global_struct->self=EDICT_TO_PROG(sv_player);
    G_INT(OFS_PARM0)=EDICT_TO_PROG(e);G_INT(OFS_PARM1)=EDICT_TO_PROG(sv_player);G_FLOAT(OFS_PARM2)=0;
    PR_ExecuteProgram(greet-pr_functions);
    pr_global_struct->self=self;pr_global_struct->other=other;
    greetings++;return 1;
}
static const char *call_string(const unsigned char *strings,int nstrings,int i){
    return i<nstrings?cached_id((strings[2*i]<<8)|strings[2*i+1]):NULL;
}
static const char *actor_faction(int instance,int target,char *out,int capacity){
    edict_t *e;aw_actor_t *a;aw_actor_base_t b;
    if(target==AW_MWVM_PLAYER || !(a=actor_of(instance,target,&e)) || a->reference==AW_ACTOR_PLAYER_REF)return NULL;
    if(!AW_ActorBase(a->base,&b) || b.faction==AW_ACTOR_NONE || !read_string(b.faction,out,capacity) || !out[0])return NULL;
    return out;
}
static int same_id(const char *a,const char *b){
    for(;*a && *b;a++,b++)if(tolower((unsigned char)*a)!=tolower((unsigned char)*b))return 0;
    return *a==*b;
}
static int host_call(int instance,int target,int function,const aw_mwcell_t *numbers,int count,
                     const unsigned char *strings,int nstrings,aw_mwcell_t *result){
    char own[64];const char *faction;int value=count>0?numbers[0].i:0;
    switch(function){
    case AWF_GETPCCRIMELEVEL:result->f=(float)AW_StandingCrime();standing_calls++;return AW_MWVM_CALL_READ;
    case AWF_SETPCCRIMELEVEL:case AWF_MODPCCRIMELEVEL:
        if(count<1)return 0;
        if(function==AWF_SETPCCRIMELEVEL)AW_StandingSetCrime((int)numbers[0].f);else AW_StandingModCrime((int)numbers[0].f);
        standing_calls++;AW_MwvmStateChanged();return 1;
    case AWF_GETREPUTATION:case AWF_SETREPUTATION:case AWF_MODREPUTATION:
        if(target!=AW_MWVM_PLAYER){
            edict_t *e;aw_actor_t *a;aw_actor_base_t b;
            /* an NPC's reputation: its record's (changing it is not kept per actor yet: "not yet") */
            if(function!=AWF_GETREPUTATION || !(a=actor_of(instance,target,&e)) || !AW_ActorBase(a->base,&b)){
                standing_misses++;return 0;}
            result->i=b.reputation;standing_calls++;return AW_MWVM_CALL_READ;
        }
        standing_calls++;
        if(function==AWF_GETREPUTATION){result->i=AW_StandingReputation();return AW_MWVM_CALL_READ;}
        AW_StandingSetReputation(function==AWF_SETREPUTATION?value:AW_StandingReputation()+value);
        AW_MwvmStateChanged();return 1;
    case AWF_GETPCRANK:case AWF_PCRAISERANK:case AWF_PCLOWERRANK:case AWF_PCJOINFACTION:
    case AWF_PCEXPELLED:case AWF_PCEXPELL:case AWF_PCCLEAREXPELLED:
        faction=call_string(strings,nstrings,0);
        if(!faction)faction=actor_faction(instance,target,own,sizeof(own));
        standing_calls++;
        if(function==AWF_GETPCRANK){result->i=faction?AW_StandingRank(faction):-1;return AW_MWVM_CALL_READ;}
        if(function==AWF_PCEXPELLED){result->i=faction?AW_StandingExpelled(faction):0;return AW_MWVM_CALL_READ;}
        if(!faction)return 1;              /* a factionless speaker: nothing to change (OpenMW) */
        if(function==AWF_PCRAISERANK)AW_StandingRaise(faction);
        else if(function==AWF_PCLOWERRANK)AW_StandingLower(faction);
        else if(function==AWF_PCJOINFACTION)AW_StandingJoin(faction);
        else AW_StandingSetExpelled(faction,function==AWF_PCEXPELL);
        AW_MwvmStateChanged();return 1;
    case AWF_GETPCFACREP:case AWF_SETPCFACREP:case AWF_MODPCFACREP:
        faction=call_string(strings,nstrings,0);
        if(!faction)faction=actor_faction(instance,target,own,sizeof(own));
        standing_calls++;
        if(function==AWF_GETPCFACREP){result->i=faction?AW_StandingFactionReputation(faction):0;return AW_MWVM_CALL_READ;}
        if(!faction || count<1)return 1;
        AW_StandingSetFactionReputation(faction,function==AWF_SETPCFACREP?value:AW_StandingFactionReputation(faction)+value);
        AW_MwvmStateChanged();return 1;
    case AWF_ADDTOPIC:
        /* AddTopic (OpenMW dialogueextensions.cpp OpAddTopic: the topic joins the player's known list; the dialogue
         * window shows it, DIALOGUE-57): the compiler hands the topic's TOPC row as the number */
        if(count<1 || numbers[0].i<0 || numbers[0].i>=topic_rows || !known_topics)return 0;
        known_topics[numbers[0].i>>3]|=(unsigned char)(1<<(numbers[0].i&7));topics_added++;
        return 1;
    case AWF_FORCEGREETING:{
        /* ForceGreeting (OpenMW dialogueextensions.cpp OpForceGreeting: the actor opens the dialogue with its
         * greeting): the greeting the engine plays when the player talks to the actor (QC aw_greet, the voice table
         * and its hello line), by the same talk rule (aw_talk.c: alive, not hostile, something to say); the dialogue
         * window itself comes with DIALOGUE-57. Nothing happens with no actor, no player or a line still playing. */
        vec3_t at;int n=locate(instance,target,at);
        force_greeting(n>0?edict_of(n):NULL);
        return 1;}
    case AWF_AITRAVEL:{
        /* AITravel X Y Z [repeat] (OpenMW aiextensions.cpp OpAiTravel, aitravel.cpp): the actor walks to the point
         * (the original's coordinates) by the ambient tables' routes (aw_ambient.c AW_AmbientTravel); GetAIPackageDone
         * reads 1 when it arrived. Without the ambient tables in the build, or an actor not loaded: nothing, counted. */
        vec3_t at,local;edict_t *e;int n=locate(instance,target,at);float game[3];
        e=n>0?edict_of(n):NULL;
        if(count<3 || !e || e==sv_player || !aw_mwscript_travel){travels_refused++;return 1;}
        game[0]=numbers[0].f;game[1]=numbers[1].f;game[2]=numbers[2].f;
        if(!AW_SourceToWorld(sv.name,game,local)){   /* a room: a quarter scale plus its shift (as to_game_units) */
            int i;for(i=0;i<3;i++)local[i]=game[i]/4.0f+room_shift[i];
        }
        if(aw_mwscript_travel(e,local))travels++;else travels_refused++;
        return 1;}
    case AWF_AIFOLLOW:{
        /* AIFollow TARGET DURATION X Y Z [reset] (OpenMW aiextensions.cpp OpAiFollow, aifollow.cpp): the actor follows
         * the target (the player, or an actor of this map by its id) by the ambient tables (AW_AmbientFollow) */
        const char *who=call_string(strings,nstrings,0);vec3_t at,local;edict_t *e,*t=NULL;int n=locate(instance,target,at),i;
        float game[3];
        e=n>0?edict_of(n):NULL;
        if(!who || count<4 || !e || e==sv_player || !aw_mwscript_follow){follows_refused++;return 1;}
        if(!Q_strcasecmp((char *)who,"player"))t=sv_player;
        else for(i=1;i<sv.num_edicts && !t;i++){
            edict_t *x=EDICT_NUM(i);eval_t *v;
            if(x->free || !(v=GetEdictFieldValue(x,"aw_source_id")) || !v->string)continue;
            if(!Q_strcasecmp(pr_strings+v->string,(char *)who))t=x;
        }
        game[0]=numbers[1].f;game[1]=numbers[2].f;game[2]=numbers[3].f;
        if(game[0]!=0 || game[1]!=0 || game[2]!=0){
            if(!AW_SourceToWorld(sv.name,game,local))for(i=0;i<3;i++)local[i]=game[i]/4.0f+room_shift[i];
        }else local[0]=local[1]=local[2]=0;
        if(t && aw_mwscript_follow(e,t,numbers[0].f,local))follows++;else follows_refused++;
        return 1;}
    case AWF_POSITION:{
        /* Position X Y Z ZROT (OpenMW transformationextensions.cpp OpPosition): the player goes to the outdoor point
         * (the coordinate teleport, as PositionCell outdoors); any other object with an entity moves within the map it
         * is in. The rotation is not applied yet (the player keeps its view; an object its facing). */
        vec3_t at,local;int n=locate(instance,target,at),i;edict_t *e;float game[3];
        if(count<3){positions_refused++;return 1;}
        game[0]=numbers[0].f;game[1]=numbers[1].f;game[2]=numbers[2].f;
        if(target==AW_MWVM_PLAYER){
            if(AW_MapTeleportAt(game,1))positions++;else positions_refused++;
            return 1;
        }
        e=n>0?edict_of(n):NULL;
        if(!e || e->free || e==sv_player){positions_refused++;return 1;}
        if(!AW_SourceToWorld(sv.name,game,local))for(i=0;i<3;i++)local[i]=game[i]/4.0f+room_shift[i];
        VectorCopy(local,e->v.origin);SV_LinkEdict(e,false);positions++;
        return 1;}
    case AWF_GETSTANDINGPC:{
        /* GetStandingPC (OpenMW miscextensions.cpp OpGetStandingPc, World::getPlayerStandingOn): 1 while the player
         * stands on the object. Here an object with an entity (Quake's ground entity); CHIM scenery without one is
         * part of the world's collision and reads 0 (not yet) */
        vec3_t at;int n=locate(instance,target,at);edict_t *e=n>0?edict_of(n):NULL;
        result->i=e && sv_player && ((int)sv_player->v.flags&FL_ONGROUND) && PROG_TO_EDICT(sv_player->v.groundentity)==e;
        return AW_MWVM_CALL_READ;}
    case AWF_GETTARGET:{
        /* GetTarget ID (OpenMW aiextensions.cpp OpGetTarget: 1 when the actor's combat package targets ID): the
         * combat layer here fights the player only (aw_combat.c), so the answer is 1 for the player while the actor
         * is in a fight and alive, 0 for anyone else */
        const char *id=call_string(strings,nstrings,0);vec3_t at;edict_t *e;int n=locate(instance,target,at);
        const aw_fighter_t *f;
        e=n>0?edict_of(n):NULL;
        result->i=id && !Q_strcasecmp((char *)id,"player") && e && e!=sv_player && (f=AW_CombatFighter(e))!=NULL &&
                  !f->dead;
        return AW_MWVM_CALL_READ;}
    case AWF_ROTATE:{
        /* Rotate AXIS DEGREES-A-SECOND (OpenMW transformationextensions.cpp OpRotate: by that many degrees times the
         * frame's duration; the player only around z): on an object with an entity; the CHIM scenery without one
         * cannot turn yet. Quake's yaw turns the other way round from the original's z. */
        const char *axis=call_string(strings,nstrings,0);vec3_t at;edict_t *e;int n=locate(instance,target,at);
        float step=count>=1?numbers[0].f*(float)host_frametime:0;
        e=n>0?edict_of(n):NULL;
        if(!axis || !e || e->free){rotations_missed++;return 1;}
        if(e==sv_player || tolower((unsigned char)axis[0])=='z')e->v.angles[1]-=step;
        else if(tolower((unsigned char)axis[0])=='x')e->v.angles[0]+=step;
        else if(tolower((unsigned char)axis[0])=='y')e->v.angles[2]+=step;
        rotations++;return 1;}
    case AWF_GETEFFECT:
        /* GetEffect (OpenMW miscextensions.cpp OpGetEffect: an active effect of that kind on the actor): only the
         * player has active effects here (aw_effects.c); an actor's own reads 0, true while no effect lands on it */
        result->i=count>=1 && target==AW_MWVM_PLAYER?AW_EffectsHas(numbers[0].i):0;
        return AW_MWVM_CALL_READ;
    case AWF_CAST:{
        /* Cast SPELL TARGET (OpenMW apps/openmw/mwscript/miscextensions.cpp OpCast; the cures' effects from
         * mwmechanics/spelleffects.cpp CureCommonDisease / CureBlightDisease / CurePoison): v0.0.57 carries out the
         * cures on the player, the caster plays its cast (aw_animkit.c); every other spell waits for the spell
         * effects (SPELL-EFFECTS-57) and stays "not yet". Cure Poison: no poison state exists yet, so it changes
         * nothing (said so in docs/MWSCRIPT_BYTECODE.md). */
        const char *spell=call_string(strings,nstrings,0),*who=call_string(strings,nstrings,1);char s[64];int k,type;
        vec3_t at;edict_t *caster;int n;
        if(count>=1){
            /* SPELL-EFFECTS-57, the first slice: the compiler handed the spell's SPFX row (every effect a Fortify,
             * Drain, Damage or Restore of a stat); each lands on the player with its magnitude rolled once */
            uint32_t off,rows,bytes;int row=numbers[0].i,e;aw_actor_t *p=player_record();
            if(!p || !AW_MwvmSection("SPFX",&off,&rows,&bytes) || row<0 || (uint32_t)row>=rows ||
               off+bytes>resident_bytes)return 0;
            {const unsigned char *h=resident+off+4*row;int first=(h[0]<<8)|h[1],nfx=h[2];
             for(e=0;e<nfx;e++){
                 const unsigned char *x=resident+off+4*rows+8*(first+e);int lo=(x[4]<<8)|x[5],hi=(x[6]<<8)|x[7];
                 float m=(float)(hi>lo?lo+rand()%(hi-lo+1):lo);
                 if(x[0]==4){   /* a cure: the spells of that type go (0: Cure Poison, no poison state yet) */
                     if(x[1])AW_ActorRemoveSpellType(p,x[1]);
                     cures++;continue;
                 }
                 if(AW_EffectsAdd(p,x[0],x[1],m,(float)((x[2]<<8)|x[3])))effects_cast++;
             }}
            player_store(p);AW_MwvmStateChanged();
            n=locate(instance,target,at);caster=n>0?edict_of(n):NULL;
            if(caster && caster!=sv_player)AW_AnimPickCast(caster,AW_PR_TOUCH);
            return 1;
        }
        if(!spell || !who || Q_strcasecmp((char *)who,"player"))return 0;
        for(k=0;spell[k] && k<63;k++)s[k]=(char)tolower((unsigned char)spell[k]);
        s[k]=0;
        if(strstr(s,"cure common disease"))type=3;
        else if(strstr(s,"cure blight disease"))type=2;
        else if(strstr(s,"cure poison"))type=0;
        else return 0;
        if(type){aw_actor_t *p=player_record();if(p && AW_ActorRemoveSpellType(p,type)>0)AW_MwvmStateChanged();}
        n=locate(instance,target,at);caster=n>0?edict_of(n):NULL;
        if(caster && caster!=sv_player)AW_AnimPickCast(caster,AW_PR_TOUCH);
        cures++;return 1;}
    case AWF_PLAYGROUP:case AWF_LOOPGROUP:{
        /* PlayGroup group [flags] / LoopGroup group count [flags] (aw_animkit.c AW_AnimPickScripted, OpenMW's
         * animationextensions.cpp): on a skeletal actor whose map is loaded; else nothing happens, counted */
        const char *group=call_string(strings,nstrings,0);vec3_t at;edict_t *e;int n=locate(instance,target,at);
        e=n>0?edict_of(n):NULL;
        if(group && e && !e->free && e!=sv_player &&
           AW_AnimPickScripted(e,group,function==AWF_LOOPGROUP && count>0?numbers[0].i:0))anim_plays++;
        else anim_misses++;
        return 1;}
    case AWF_GETRACE:{
        const char *race=call_string(strings,nstrings,0);edict_t *e;aw_actor_t *a;aw_actor_base_t b;
        standing_calls++;result->i=0;
        if(!race)return AW_MWVM_CALL_READ;
        if(target==AW_MWVM_PLAYER){
            if(aw_character.valid && aw_character.race>=0 && aw_character.race<aw_race_count)
                result->i=same_id(aw_races[aw_character.race].id,race);
            return AW_MWVM_CALL_READ;
        }
        if((a=actor_of(instance,target,&e)) && AW_ActorBase(a->base,&b) && b.kind==0 && b.race!=AW_ACTOR_NONE &&
           read_string(b.race,own,sizeof(own)))result->i=same_id(own,race);
        return AW_MWVM_CALL_READ;}
    }
    return 0;
}

static const aw_mwvm_host_t host={host_sound,host_sound_playing,host_say,host_say_done,host_music,host_distance,
    host_menu_mode,host_query,host_journal_get,host_journal_set,host_notyet,host_warn,host_object,host_message,
    host_button,host_actor,host_item,host_spell,host_combat,host_dead_count,host_wander,host_call,host_player_cell,
    host_position,host_player_move,host_ai_package};

/* The dialogue conditions' live state (aw_glut.h aw_glut_live, DIALOGUE-57): what the scripts keep, read by name.
 * Not yet: script locals, SameRace, SameSex, RankRequirement, globals by name (they keep the start value). */
static int live_journal(const char *quest,long *out){
    int i,n=AW_MwvmTopicCount();long best=AW_StateGet(&aw_state,AW_JOURNAL,(char *)quest);
    for(i=0;topic_values && topic_names && i<n;i++)
        if(topic_values[i]>best && same_id(topic_names+topic_offsets[i],quest))best=topic_values[i];
    *out=best;return 1;
}
static int live_dead(const char *actor,long *out){
    int row;
    if(!AW_MwscriptActors() || (row=AW_ActorFind(actor))<0){*out=0;return 1;}   /* an id no actor has: 0 dead */
    *out=AW_ActorDeadCount(row);return 1;
}
static int live_item(const char *item,long *out){*out=AW_StateGet(&aw_state,AW_ITEM,(char *)item);return 1;}
static int live_rank(const char *faction,long *out){*out=AW_StandingRank(faction);return 1;}
/* SCVR function numbers (mwad.dialogue FUNCTIONS): the player's standing and the character's stats */
static int live_function(const aw_glut_cond_t *c,unsigned fn,long *out){
    if(fn==5){*out=AW_StandingReputation();return 1;}                      /* PcReputation */
    if(fn==43){*out=AW_StandingCrime();return 1;}                          /* PcCrimeLevel */
    if(fn==39){*out=c->faction?AW_StandingExpelled(c->faction):0;return 1;} /* PcExpelled (the speaker's faction) */
    if(fn==46){*out=c->faction && AW_StandingRank(c->faction)>=0;return 1;} /* SameFaction */
    if(!aw_character.valid)return 0;
    if(fn==6){*out=aw_character.level;return 1;}                           /* PcLevel */
    if(fn==38){*out=aw_character.female?1:0;return 1;}                      /* PcGender: 1 female (OpenMW) */
    if(fn==10){*out=aw_character.attributes[0];return 1;}                  /* PcStrength */
    if(fn>=51 && fn<=57){*out=aw_character.attributes[fn-50];return 1;}    /* PcIntelligence .. PcLuck */
    if(fn>=11 && fn<=37){*out=aw_character.skills[fn-11];return 1;}        /* PcBlock .. PcHandToHand */
    return 0;
}
/* the speaker's script local: its attached instance's slot (no instance: 0, OpenMW's empty locals) */
static int live_local(const aw_glut_cond_t *c,int slot,int is_float,float *out){
    int k,n=AW_MwvmInstanceCount();aw_mwvm_instance_t *in;aw_mwcell_t v;
    *out=0;
    for(k=0;c->speaker>0 && k<n;k++)
        if((in=AW_MwvmInstance(k))!=NULL && (in->flags&AWI_USED) && in->entity==c->speaker){
            v=AW_MwvmLocal(k,slot);*out=is_float?v.f:(float)v.i;break;}
    return 1;
}
/* a global by name: the GLOB rows' names read once from the file (32 bytes each, kept for the session) */
static char *global_names;static int global_names_tried;
static int live_global(const char *name,float *out){
    uint32_t off,rows,bytes;int i;
    if(!AW_MwvmLoaded() || !AW_MwvmSection("GLOB",&off,&rows,&bytes) || off+8ul*rows>resident_bytes)return 0;
    if(!global_names && !global_names_tried){
        FILE *f=NULL;long base;
        global_names_tried=1;
        if(COM_FOpenFile(FILE_NAME,&f)>0 && f && (global_names=(char *)AW_TryCalloc(rows?rows:1,32))!=NULL){
            base=ftell(f);
            for(i=0;i<(int)rows;i++)
                if(!read_string_from(f,base,(int)((resident[off+8*i+2]<<8)|resident[off+8*i+3]),global_names+32*i,32))
                    global_names[32*i]=0;
        }
        if(f)fclose(f);
    }
    for(i=0;global_names && i<(int)rows;i++)if(same_id(global_names+32*i,name)){
        *out=resident[off+8*i]==2?AW_MwvmGlobalFloat(i):(float)AW_MwvmGlobalInt(i);return 1;}
    return 0;
}
/* The disposition's facts of a speaker (aw_dial.h aw_dial_facts_t; DIALOGUE-57): its own disposition from the actor
 * record (the scripts' SetDisposition and ModDisposition included) when the actor table has it, else BASE; same race,
 * the player's Personality, crime level, faction ranks. Not yet: disease, a drawn weapon, Charm (0). */
static int standing_rank(const char *faction,int *expelled){*expelled=AW_StandingExpelled(faction);return AW_StandingRank(faction);}
void AW_MwscriptDispositionFacts(const char *record,unsigned long reference,int base,const char *faction,aw_dial_facts_t *f){
    int row=-1;aw_actor_base_t b;aw_actor_t *a;char race[64];
    memset(f,0,sizeof(*f));
    f->base=base;f->faction=faction;f->rank=standing_rank;f->bounty=AW_StandingCrime();
    f->personality=aw_character.valid?(float)aw_character.attributes[6]:50.0f;
    if(!AW_MwscriptActors() || !record || (row=AW_ActorFind(record))<0 || !AW_ActorBase(row,&b))return;
    if(reference && (a=AW_ActorGet((uint32_t)reference,row,0))!=NULL)f->base=(int)AW_ActorStat(a,AWA_DISPOSITION);
    if(aw_character.valid && b.race!=AW_ACTOR_NONE && read_string(b.race,race,sizeof(race)))
        f->same_race=same_id(race,aw_races[aw_character.race].id);
}
/* An NPC record's faction id (the actor table), "" when it has none or the table is not loaded. */
int AW_MwscriptActorFaction(const char *record,char *out,int capacity);
int AW_MwscriptActorFaction(const char *record,char *out,int capacity){
    int row;aw_actor_base_t b;
    out[0]=0;
    if(!AW_MwscriptActors() || !record || (row=AW_ActorFind(record))<0 || !AW_ActorBase(row,&b) ||
       b.faction==AW_ACTOR_NONE || !read_string(b.faction,out,capacity))return 0;
    return out[0]!=0;
}
static const aw_glut_live_t live={live_journal,live_dead,live_item,live_rank,live_global,live_function,live_local};

/* --- loading and the map's objects --- */
static int load(void){
    FILE *f=NULL;int length,i,n;unsigned char head[16];uint32_t wanted;char name[64];long base;
    if(resident || load_failed)return resident!=NULL;
    load_failed=1;
    length=COM_FOpenFile(FILE_NAME,&f);
    if(!f){load_why="no id1/mwscript.awm in this image";Con_Printf("MWScript: no %s in this image.\n",FILE_NAME);return 0;}
    file_bytes=length>0?(unsigned long)length:0;
    if(length<16 || fread(head,1,16,f)!=16 || memcmp(head,"AWMS",4)){
        fclose(f);load_why="the file is not AWMS";Con_Printf("MWScript: bad file.\n");return 0;}
    wanted=((uint32_t)head[12]<<24)|((uint32_t)head[13]<<16)|((uint32_t)head[14]<<8)|head[15];
    if(wanted<16 || wanted>MAX_RESIDENT || wanted>(uint32_t)length || !(resident=(unsigned char *)AW_TryMalloc(wanted))){
        fclose(f);load_why="no memory for its resident part";Con_Printf("MWScript: cannot keep %lu bytes.\n",(unsigned long)wanted);return 0;}
    memcpy(resident,head,16);
    if(fread(resident+16,1,wanted-16,f)!=wanted-16){fclose(f);free(resident);resident=NULL;load_why="read error";return 0;}
    fclose(f);resident_bytes=wanted;
    if(!AW_MwvmLoad(resident,resident_bytes,&host)){
        free(resident);resident=NULL;load_why="the interpreter refused it (format or version)";Con_Printf("MWScript: refused.\n");return 0;}
    n=AW_MwvmTopicCount();
    topic_offsets=(int *)AW_TryMalloc(sizeof(int)*(n+1));topic_values=(int32_t *)AW_TryMalloc(sizeof(int32_t)*(n+1));
    topic_names=(char *)AW_TryMalloc(64*(n+1));
    if(!topic_offsets || !topic_values || !topic_names){
        load_why="no memory for the journal names";Con_Printf("MWScript: no memory for the journal names.\n");return 0;}
    f=NULL;length=COM_FOpenFile(FILE_NAME,&f);
    base=f?ftell(f):0;     /* the file's start (inside a PAK it is not 0) */
    for(i=0;i<n;i++){
        topic_offsets[i]=64*i;topic_values[i]=0;
        if(!f || length<=0 || !read_string_from(f,base,AW_MwvmTopicName(i),name,sizeof(name)))name[0]=0;
        strcpy(topic_names+64*i,name);
    }
    if(f)fclose(f);
    {uint32_t off,rows,b;      /* the known topics: one bit per TOPC row */
     if(AW_MwvmSection("TOPC",&off,&rows,&b) && rows>0 && rows<0x10000 &&
        (known_topics=(unsigned char *)AW_TryMalloc((rows+7)/8))!=NULL){
         topic_rows=(int)rows;topic_bytes=(int)((rows+7)/8);memset(known_topics,0,topic_bytes);}}
    load_failed=0;load_why="loaded";
    aw_glut_live=&live;     /* the dialogue conditions read the scripts' state from now on */
    Con_Printf("MWScript: %d scripts, %lu bytes kept.\n",AW_MwvmScriptCount(),resident_bytes);
    return 1;
}
/* The loaded room's stable interior number: worldspawn _aw_cell_int (tools/cell_numbers.py); 0 outdoors. */
static long map_cell_number(void){
    const char *p=sv.worldmodel?sv.worldmodel->entities:NULL,*key;long n=0;
    if(!p)return 0;
    key=strstr(p,"\"_aw_cell_int\"");
    if(!key || key>strchr(p,'}'))return 0;      /* worldspawn only: the first entity */
    key+=14;
    while(*key==' ' || *key=='\t')key++;
    if(*key!='"')return 0;
    for(key++;*key>='0' && *key<='9' && n<100000;key++)n=n*10+(*key-'0');
    return *key=='"'?n:0;
}
#define ROOM_ROWS 256
static unsigned char room_rows[ROOM_ROWS][24];
static int compare_refs(const void *a,const void *b){
    uint32_t x=*(const uint32_t *)a,y=*(const uint32_t *)b;return x<y?-1:x>y;
}
static void attach_map(void){
    FILE *f=NULL;int length,i,k,nroom=0,anchored=0;long base,room;uint32_t offset,rows,bytes,r;unsigned char row[24];
    vec3_t local,shift;float source[3];edict_t *e;eval_t *v;int outdoors;
    AW_MwvmBeginMap();
    {float zero[3]={0,0,0};vec3_t at;    /* the player's cell: a room's number (its shift comes with the bindings) */
     map_room=AW_SourceToWorld(sv.name,zero,at)?0:map_cell_number();room_shift[0]=room_shift[1]=room_shift[2]=0;}
    for(i=0;i<LOOPS;i++)if(loops[i].used){S_StopSound(loops[i].entity,loops[i].channel);loops[i].used=0;}
    memset(says,0,sizeof(says));
    edict_ref_count=0;
    for(i=1;i<sv.num_edicts && edict_ref_count<EDICT_REFS;i++){
        e=EDICT_NUM(i);if(e->free)continue;
        v=GetEdictFieldValue(e,"aw_ref");if(!v || v->_float<=0)continue;
        edict_refs[edict_ref_count].ref=(uint32_t)v->_float;edict_refs[edict_ref_count++].entity=i;
    }
    qsort(edict_refs,edict_ref_count,sizeof(edict_refs[0]),compare_refs);
    /* the object state: what a script disabled stays hidden on this map too */
    for(i=0;i<object_count;i++)if(objects[i].disabled){objects[i].entity=-1;object_hide(&objects[i]);}
    if(!AW_MwvmSection("BIND",&offset,&rows,&bytes))return;
    length=COM_FOpenFile(FILE_NAME,&f);if(!f)return;
    base=ftell(f);
    if(length<=0 || fseek(f,base+(long)offset,SEEK_SET)){fclose(f);return;}
    source[0]=source[1]=source[2]=0;
    outdoors=AW_SourceToWorld(sv.name,source,local);
    room=outdoors?0:map_cell_number();
    shift[0]=shift[1]=shift[2]=0;
    for(r=0;r<rows;r++){
        uint32_t ref;int script,flags,entity;
        if(fread(row,1,24,f)!=24)break;
        bindings_read++;
        ref=((uint32_t)row[0]<<24)|((uint32_t)row[1]<<16)|((uint32_t)row[2]<<8)|row[3];
        script=(row[4]<<8)|row[5];flags=(row[6]<<8)|row[7];
        for(i=0;i<3;i++){
            const unsigned char *p=row+12+4*i;
            source[i]=(float)(int32_t)(((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3]);
        }
        entity=entity_of_reference(ref);
        if(entity>0){
            e=EDICT_NUM(entity);
            k=AW_MwvmAttach(ref,script,flags|AWB_INTERIOR*(!outdoors),entity,e->v.origin);
            if(k>=0)attach_edicts++;else attach_refused++;
            /* a room placed with a shift (recentred rooms): an edict of this room tells it */
            if(room && (flags&AWB_INTERIOR) && ((row[8]<<8)|row[9])==room && !anchored){
                for(i=0;i<3;i++)shift[i]=e->v.origin[i]-source[i]*0.25f;
                anchored=1;
            }
            continue;
        }
        if(room && (flags&AWB_INTERIOR) && ((row[8]<<8)|row[9])==room){
            /* a placement in the loaded room with no edict (a sound marker, an activator): placed at its spot
             * once every row of the room has been read (an edict anchor may come later) */
            if(nroom<ROOM_ROWS)memcpy(room_rows[nroom++],row,24);else attach_refused++;
            continue;
        }
        if(!outdoors || (flags&AWB_INTERIOR))continue;
        if(!AW_SourceToWorld(sv.name,source,local) || !AW_WorldContains(sv.name,local))continue;
        k=AW_MwvmAttach(ref,script,flags,-1,local);
        if(k>=0)attach_places++;else attach_refused++;
    }
    fclose(f);
    VectorCopy(shift,room_shift);
    /* room maps are the source positions at a quarter scale (tools/prepare_quake.py SCALE), plus a room's shift */
    for(r=0;r<(uint32_t)nroom;r++){
        const unsigned char *p=room_rows[r];uint32_t ref=((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];
        for(i=0;i<3;i++){
            const unsigned char *q=p+12+4*i;
            local[i]=(float)(int32_t)(((uint32_t)q[0]<<24)|((uint32_t)q[1]<<16)|((uint32_t)q[2]<<8)|q[3])*0.25f+shift[i];
        }
        k=AW_MwvmAttach(ref,(p[4]<<8)|p[5],(p[6]<<8)|p[7],-1,local);
        if(k>=0)attach_rooms++;else attach_refused++;
    }
}
void AW_MwscriptTick(float dt){
    int k,n,i;vec3_t player;
    /* no game running (a load, the main menu): a script's message box goes with it */
    if(!mwscript.value || !sv.active || cls.signon!=SIGNONS || !sv_player){AW_MsgBoxClear();return;}
    if(!load())return;
    if(sv.worldmodel!=map_model || strcmp(sv.name,map_name)){
        map_model=sv.worldmodel;Q_strcpy_bounded(map_name,sv.name,sizeof(map_name));
        attached_map++;attach_map();   /* the count first: what attach hides belongs to this map */
    }
    n=AW_MwvmInstanceCount();
    for(k=0;k<n;k++){
        aw_mwvm_instance_t *in=AW_MwvmInstance(k);edict_t *e;
        if(!in || !(in->flags&AWI_USED) || in->entity<=0)continue;
        e=edict_of(in->entity);if(e && !e->free)AW_MwvmSetOrigin(k,e->v.origin);
    }
    /* loops end with their object's activation (OpenMW's LoopRemoveAtDistance); a live loop starts again when its
     * sample ends */
    for(i=0;i<LOOPS;i++){
        aw_mwvm_instance_t *in;
        if(loops[i].used && !loops[i].looping && realtime>=loops[i].until){
            /* a one-shot sound ended: GetSoundPlaying of its script reads 0 now, so the script runs again (a script
             * that only asks CellChanged and GetSoundPlaying is not run every frame: codegen.py) */
            loops[i].used=0;AW_MwvmWake(loops[i].instance);continue;
        }
        if(!loops[i].used || !loops[i].looping)continue;
        in=AW_MwvmInstance(loops[i].instance);
        if(!in || !(in->flags&AWI_USED) || !(in->flags&AWI_ACTIVE)){
            S_StopSound(loops[i].entity,loops[i].channel);loops[i].used=0;continue;
        }
        if(realtime>=loops[i].until){
            int instance=loops[i].instance,sound=loops[i].sound;float gain=loops[i].volume;
            loops[i].until=0;host_sound(instance,AW_MWVM_SELF,sound,AW_MWSND_LOOP,gain,1.0f);
        }
    }
    VectorCopy(sv_player->v.origin,player);
    player_cell_update();
    actors_from_fights();
    if(AW_EffectsCount()){   /* the player's active spell effects on the game clock (SPELL-EFFECTS-57) */
        aw_actor_t *p=player_record();
        if(p && AW_EffectsTick(p,dt)){player_store(p);AW_MwvmStateChanged();}
    }
    AW_MwvmTick(dt,player);
}
static void status_counts(void){
    const aw_mwvm_stats_t *s=AW_MwvmStats();int k,n=AW_MwvmInstanceCount(),attached=0,global=0,active=0,looping=0;
    if(!resident){Con_Printf("MWScript %s; file not loaded (%s).\n",mwscript.value?"on":"off",load_why);return;}
    for(k=0;k<n;k++){aw_mwvm_instance_t *in=AW_MwvmInstance(k);if(!in || !(in->flags&AWI_USED))continue;
        if(in->flags&AWI_GLOBAL)global++;else attached++;if(in->flags&AWI_ACTIVE)active++;}
    for(k=0;k<LOOPS;k++)looping+=loops[k].used;
    Con_Printf("MWScript %s: %d scripts, %lu bytes kept; map %s: %d objects (session: %lu by edict, %lu outdoor "
               "places, %lu room places, %lu not attached), %d global scripts, %d active, %d sounds\n",
               mwscript.value?"on":"off",AW_MwvmScriptCount(),resident_bytes,map_name,attached,attach_edicts,
               attach_places,attach_rooms,attach_refused,global,active,looping);
    Con_Printf("frames %lu runs %lu quiet-skips %lu far %lu deferred %lu ops %lu (max %lu a frame) aborted %lu not-yet calls %lu\n",
               s->frames,s->runs,s->skipped_quiet,s->skipped_far,s->deferred,s->ops,s->max_ops_frame,s->aborted,s->notyet_calls);
    {/* the import route: the not-yet functions this session called most (by function number) */
     int top[8],ntop=0,f,i,j;char name[32];
     for(f=0;f<AWM_FUNCTIONS;f++){
         unsigned long c=AW_MwvmFunctionCalls(f);
         if(!c)continue;
         for(i=0;i<ntop && AW_MwvmFunctionCalls(top[i])>=c;i++);
         if(i==8)continue;
         if(ntop<8)ntop++;
         for(j=ntop-1;j>i;j--)top[j]=top[j-1];
         top[i]=f;
     }
     Con_Printf("not yet, most called:");
     for(i=0;i<ntop;i++){
         if(!read_string(AW_MwvmFunctionName(top[i]),name,sizeof(name)))strcpy(name,"?");
         Con_Printf(" %s %lu",name,AW_MwvmFunctionCalls(top[i]));
     }
     Con_Printf("%s; player cell %d %d %d; player moves %lu (%lu not possible); AI package queries %lu%s\n",
                ntop?"":" none",pc_kind,pc_x,pc_y,player_moves,player_moves_refused,ai_queries,
                aw_mwscript_ai_package?"":" (no ambient tables)");}
    {int i,disabled=0,locks=0;
     for(i=0;i<object_count;i++){disabled+=objects[i].disabled;locks+=objects[i].lock_set;}
     Con_Printf("object state: %d disabled, %d locks set (%d of %d kept; %lu hidden, %lu over the table); uses taken by "
                "OnActivate %lu, Activate %lu\n",disabled,locks,object_count,OBJECTS,objects_hidden,objects_full,
                intercepted,activated);}
    {const aw_actorstate_stats_t *a=AW_ActorStateStats();
     Con_Printf("actor record: %d actors, %lu bytes kept; calls %lu (%lu with no actor), records made %lu, changed %lu, "
                "dropped %lu, full %lu, disk reads %lu; combat started %lu stopped %lu; wanders %lu\n",AW_ActorCount(),
                AW_ActorStateResident(),actor_calls,actor_misses,a->created,a->changed,a->evicted,a->full,a->reads,
                combat_starts,combat_stops,wanders);}
    Con_Printf("player standing: crime level %d, reputation %d; calls %lu (%lu not carried out)%s; PlayGroup %lu "
               "(%lu with no skeletal actor or group); topics added %lu (of %d, %d bytes kept); cures cast %lu; spell effects "
               "landed %lu, active %d, refused %lu; ForceGreeting %lu (%lu not possible); Rotate %lu (%lu with no entity); AITravel %lu (%lu not possible); AIFollow %lu (%lu not possible); Position %lu (%lu not possible)\n",
               AW_StandingCrime(),AW_StandingReputation(),standing_calls,standing_misses,
               AW_StandingFull()?"; faction table full":"",anim_plays,anim_misses,topics_added,topic_rows,topic_bytes,cures,
               effects_cast,AW_EffectsCount(),AW_EffectsRefused(),greetings,greetings_missed,rotations,rotations_missed,travels,travels_refused,follows,follows_refused,positions,positions_refused);
}
/* "aw_mwscript_status [on|off|about]" (dbg mwscript [on|off], dbg mwscript status; DBG-MWSCRIPT-SILENT-56): the
 * switch answers in the console what it does, whether id1/mwscript.awm was loaded (scripts, bytes, its format) and
 * the counts. Switching on reads the file at once (no map needed), so the answer is never "nothing happened". */
/* the debug call's helpers: a string's index in the file (a scan of STRS on disk, without case), the known topics */
static int find_string(char *text){
    FILE *f=NULL;uint32_t off,rows,bytes,i;long base;char s[64];int found=-1;
    if(!AW_MwvmSection("STRS",&off,&rows,&bytes) || COM_FOpenFile(FILE_NAME,&f)<=0 || !f){if(f)fclose(f);return -1;}
    base=ftell(f);
    for(i=0;i<rows && found<0;i++)if(read_string_from(f,base,(int)i,s,sizeof(s)) && !Q_strcasecmp(s,text))found=(int)i;
    fclose(f);return found;
}
static int topics_known(void){int i,n=0;for(i=0;i<topic_rows;i++)n+=AW_MwscriptTopicKnown(i);return n;}
static void status(void){
    char *a=Cmd_Argc()>1?Cmd_Argv(1):"";int k,on=-1;
    if(!Q_strcasecmp(a,"on") || !Q_strcasecmp(a,"true") || !Q_strcasecmp(a,"yes") || !strcmp(a,"1"))on=1;
    else if(!Q_strcasecmp(a,"off") || !Q_strcasecmp(a,"false") || !Q_strcasecmp(a,"no") || !strcmp(a,"0"))on=0;
    if(!Q_strcasecmp(a,"call")){
        /* "aw_mwscript_status call FUNCTION [number] [faction]" (dbg mwscript call): one of the player's standing or
         * AddTopic calls through the same host route a script takes, on the player (a test and evidence route) */
        static struct {char *name;int fn;} calls[]={{"getpccrimelevel",AWF_GETPCCRIMELEVEL},
            {"setpccrimelevel",AWF_SETPCCRIMELEVEL},{"modpccrimelevel",AWF_MODPCCRIMELEVEL},
            {"modreputation",AWF_MODREPUTATION},{"getpcrank",AWF_GETPCRANK},{"pcraiserank",AWF_PCRAISERANK},
            {"pcjoinfaction",AWF_PCJOINFACTION},{"pcexpell",AWF_PCEXPELL},{"addtopic",AWF_ADDTOPIC}};
        aw_mwcell_t num[1],r;unsigned char str[2];int i,n=0,ns=0,fn=-1,done;char *f=Cmd_Argc()>2?Cmd_Argv(2):"";
        if(!Q_strcasecmp(f,"aifollow")){   /* the actor under the crosshair follows the player, as a script's AIFollow */
            edict_t *e=sv_player?AW_NPCTarget(sv_player,sv_player->v.v_angle):NULL;
            if(Cmd_Argc()>3){   /* or the actor of that record id ("aw_mwscript_status call aifollow indrele rathryon") */
                char id[64];int argi;id[0]=0;
                for(argi=3;argi<Cmd_Argc();argi++){if(argi>3)strncat(id," ",sizeof(id)-strlen(id)-1);strncat(id,Cmd_Argv(argi),sizeof(id)-strlen(id)-1);}
                e=NULL;
                for(argi=1;argi<sv.num_edicts && !e;argi++){
                    edict_t *x=EDICT_NUM(argi);eval_t *v;
                    if(!x->free && (v=GetEdictFieldValue(x,"aw_source_id"))!=NULL && v->string && !Q_strcasecmp(pr_strings+v->string,id))e=x;
                }
            }
            Con_Printf("dbg mwscript call aifollow: %s (%s)\n",
                       e && aw_mwscript_follow && aw_mwscript_follow(e,sv_player,0,NULL)?"following the player":"not possible",
                       e?pr_strings+e->v.netname:"no actor under the crosshair");
            return;
        }
        if(!Q_strcasecmp(f,"journal")){   /* "call journal QUEST INDEX": the quest's index set, as a script's Journal */
            int t,quests=load()?AW_MwvmTopicCount():0,found=-1;
            for(t=0;Cmd_Argc()>4 && t<quests && found<0;t++)if(topic_names && same_id(topic_names+topic_offsets[t],Cmd_Argv(3)))found=t;
            if(found<0){Con_Printf("dbg mwscript call journal QUEST INDEX: no such quest (the file must be loaded)\n");return;}
            host_journal_set(found,atoi(Cmd_Argv(4)),0);AW_MwvmStateChanged();
            Con_Printf("dbg mwscript call journal: %s %ld\n",topic_names+topic_offsets[found],(long)host_journal_get(found));
            return;
        }
        if(!Q_strcasecmp(f,"forcegreeting")){   /* the actor under the crosshair greets, as a script's ForceGreeting */
            edict_t *e=sv_player?AW_NPCTarget(sv_player,sv_player->v.v_angle):NULL;
            Con_Printf("dbg mwscript call forcegreeting: %s (%s)\n",force_greeting(e)?"greeting played":"not possible",
                       e?pr_strings+e->v.netname:"no actor under the crosshair");
            return;
        }
        for(i=0;i<(int)(sizeof(calls)/sizeof(calls[0]));i++)if(!Q_strcasecmp(f,calls[i].name))fn=calls[i].fn;
        if(fn<0 || !load()){Con_Printf("dbg mwscript call: getpccrimelevel, setpccrimelevel N, modpccrimelevel N, "
                                       "modreputation N, getpcrank FACTION, pcraiserank FACTION, pcjoinfaction FACTION, "
                                       "pcexpell FACTION, addtopic ROW, journal QUEST INDEX (the file must be loaded)\n");return;}
        for(i=3;i<Cmd_Argc();i++){
            char *s=Cmd_Argv(i);
            if((s[0]>='0' && s[0]<='9') || s[0]=='-'){
                num[0].i=atoi(s);if(fn==AWF_SETPCCRIMELEVEL || fn==AWF_MODPCCRIMELEVEL)num[0].f=(float)Q_atof(s);n=1;}
            else{   /* a faction: its string index is not known here, so the call goes by name below */
                int at=find_string(s);
                if(at>=0){str[0]=(unsigned char)(at>>8);str[1]=(unsigned char)at;ns=1;}
                else{Con_Printf("dbg mwscript call: no string %s in the file\n",s);return;}
            }
        }
        r.i=0;done=host_call(-1,AW_MWVM_PLAYER,fn,num,n,str,ns,&r);
        Con_Printf("dbg mwscript call %s: %s, answer %d (%.1f); crime level %d, reputation %d, topics known %d\n",f,
                   done?"carried out":"not carried out",(int)r.i,r.f,AW_StandingCrime(),AW_StandingReputation(),topics_known());
        return;
    }
    if(on<0 && Q_strcasecmp(a,"about")){status_counts();return;}
    if(on>=0)Cvar_SetValue(mwscript.name,(float)on);
    if(!mwscript.value)   /* off: the scripts' sounds stop with it (the tick no longer runs them) */
        for(k=0;k<LOOPS;k++)if(loops[k].used){S_StopSound(loops[k].entity,loops[k].channel);loops[k].used=0;}
    Con_Printf("MWScript %s (aw_mwscript %d, default 1, saved): %s\n",mwscript.value?"ON":"OFF",(int)mwscript.value,
               mwscript.value?"the game's compiled scripts run: ambient and activator sounds, NPC voice lines, music "
               "cues, journal and globals, object state (Disable, Lock), actor records and AIWander (with the Wander "
               "packages, chim actors ambient). Functions not carried out yet are counted and logged once.":
               "no compiled script runs; the scripts' sounds stopped. dbg mwscript on runs them again.");
    if(mwscript.value)load();
    if(resident)Con_Printf("file id1/%s: format AWMS %d, %lu bytes on disk, %d scripts, %lu bytes kept (one block, "
                           "outside the Quake heap); bindings read per map\n",FILE_NAME,(resident[4]<<8)|resident[5],
                           file_bytes,AW_MwvmScriptCount(),resident_bytes);
    else Con_Printf("file id1/%s: not loaded (%s)\n",FILE_NAME,load_why);
    status_counts();
}
/* The actor block of a saved game (feature 16), with the player's standing and known topics after it (v0.0.57,
 * MWSCRIPT-STANDING-NOT-SAVED-57): [actor records][AWPS standing]["AWKT" u16 rows u16 bytes, the known-topic bits]
 * [u32 bytes of the two]["AWTR"]. A save of an earlier version has no trailer: its block is the actor records. */
static void put_u32(unsigned char *p,unsigned long v){p[0]=(unsigned char)(v>>24);p[1]=(unsigned char)(v>>16);p[2]=(unsigned char)(v>>8);p[3]=(unsigned char)v;}
static int actors_export(unsigned char *out,int capacity){
    int n=AW_ActorStateReady()?AW_ActorStateExport(out,capacity):0,s,t;
    if(n<0)return n;
    if((s=AW_StandingExport(out+n,capacity-n))<0)return -1;
    t=6+topic_bytes;
    if(n+s+t+8>capacity)return -1;
    memcpy(out+n+s,"AWKT",4);out[n+s+4]=(unsigned char)(topic_rows>>8);out[n+s+5]=(unsigned char)topic_rows;
    if(topic_bytes)memcpy(out+n+s+6,known_topics,topic_bytes);
    {int f=AW_EffectsExport(out+n+s+t,capacity-n-s-t-8);   /* the active spell effects (SPELL-EFFECTS-57) */
     if(f<0)return -1;
     t+=f;}
    if(aw_mwscript_packages_export){   /* the actors' travel and follow packages (aw_ambient.c, SAVEGAME-COMPLETE-57) */
        int k=aw_mwscript_packages_export(out+n+s+t,capacity-n-s-t-8);
        if(k<0)return -1;
        t+=k;}
    put_u32(out+n+s+t,(unsigned long)(s+t));memcpy(out+n+s+t+4,"AWTR",4);
    return n+s+t+8;
}
static void actors_import(const unsigned char *data,int bytes){
    int actors=bytes;
    AW_StandingReset();AW_EffectsReset();
    if(aw_mwscript_packages_import)aw_mwscript_packages_import(NULL,0);   /* none until the save's block says */
    if(topic_bytes)memset(known_topics,0,topic_bytes);
    if(data && bytes>=8 && !memcmp(data+bytes-4,"AWTR",4)){
        unsigned long tail=((unsigned long)data[bytes-8]<<24)|((unsigned long)data[bytes-7]<<16)|
                           ((unsigned long)data[bytes-6]<<8)|data[bytes-5];
        if(tail<=(unsigned long)(bytes-8)){
            const unsigned char *p=data+bytes-8-tail;int s;
            actors=(int)(bytes-8-tail);
            s=p[0]=='A' && tail>=12?12+38*p[5]:0;
            if(s<=0 || (unsigned long)s>tail || !AW_StandingImport(p,s))Con_Printf("Saved standing unreadable: it starts empty.\n");
            else if(tail-s>=6 && !memcmp(p+s,"AWKT",4)){
                int rows=(p[s+4]<<8)|p[s+5],nb=(rows+7)/8;unsigned long rest;
                if(rows==topic_rows && (unsigned long)(s+6+nb)<=tail && nb==topic_bytes){if(nb)memcpy(known_topics,p+s+6,nb);}
                else Con_Printf("Saved topics belong to other game data: none known.\n");
                rest=(unsigned long)(s+6+nb);
                /* the active spell effects after it (v0.0.57; a save without them: none active), then the actors'
                 * travel and follow packages (AWPK; a save without them: none) */
                if(rest+6<=tail && !memcmp(p+rest,"AWEF",4)){
                    unsigned long fx=6+10UL*p[rest+5];
                    if(rest+fx>tail || !AW_EffectsImport(p+rest,(int)fx))Con_Printf("Saved spell effects unreadable: none active.\n");
                    else rest+=fx;
                }
                if(rest+6<=tail && !memcmp(p+rest,"AWPK",4) && aw_mwscript_packages_import &&
                   !aw_mwscript_packages_import(p+rest,(int)(tail-rest)))Con_Printf("Saved actor packages unreadable: none kept.\n");
            }
        }
    }
    if(!AW_MwscriptActors())return;
    if(!AW_ActorStateImport(data,actors))Con_Printf("Saved actor records unreadable: actors start from the game data.\n");
}
void AW_MwscriptInit(void){
    Cvar_RegisterVariable(&mwscript);
    AW_StandingReset();AW_EffectsReset();
    aw_save_actors_export=actors_export;aw_save_actors_import=actors_import;   /* the actor record (feature 16) */
    aw_save_objects_export=objects_export;aw_save_objects_import=objects_import;
    aw_object_lock_level=AW_ObjectLockLevel;   /* the doors read a script's Lock and Unlock */
    aw_scene_intercept=aw_hinged_intercept=object_intercept;   /* OnActivate takes a door's use */
    aw_actor_disabled=AW_ObjectDisabled;   /* the CHIM window spawns no disabled actor */
    Cmd_AddCommand("aw_mwscript_status",status);
}
