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
#include "aw_cast.h"
#include "aw_talk.h"
#include "aw_glut.h"
#include "aw_dial.h"
#include "aw_inventory.h"
#include "aw_move.h"
#include "aw_textdef.h"
#include "aw_ledger.h"
#include "aw_jhist.h"
#include "aw_maps.h"
#include "aw_rest.h"
#include "aw_crime.h"
#include "aw_levelup.h"
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
static char map_name[64];static void *map_model,*script_model;   /* the map the objects / the scripts attached to */
static char *topic_names;static int *topic_offsets;static int32_t *topic_values;
/* ambience: the loop is a dungeon ambience (the sound table's flag 2, tools/mwscript/awms.py AMBIENCE_SOUNDS): while one
 * plays the exploration music rests (TOMB-MUSIC-OVER-AMBIENT-60, aw_music.c AW_MusicAmbience) */
typedef struct {int used,instance,looping,sound,channel,entity,ambience;float until,volume;vec3_t origin;} loop_t;
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
/* DIALOGUE-CLOSE-FRAME-FREEZE-59: every read_string opened the file (a directory walk and a 16 KB buffer fill on
 * the Amiga file system, tens of ms in the emulator). A conversation's greeting tests SameRace/SameSex on every
 * candidate INFO (speaker_pair) and the disposition reads the speaker's race, so opening a talk with Fargoth read
 * the same race name hundreds of times and the game stood still for about 14 s. The file's strings never change
 * while it is loaded: the short ones are kept here (STR_CACHE x 64 bytes, round robin), so a name costs one disk
 * read per session. string_reads counts the disk reads (dbg and the dialogue's open-time line). */
#define STR_CACHE 64
static struct {int index;short length;char text[64];} str_cache[STR_CACHE];static int str_cache_next,str_cache_ready;
static unsigned long string_reads;
unsigned long AW_MwscriptStringReads(void){return string_reads;}
/* ARRIVAL-LONG-FRAME-DEV6-59: the file is opened once and kept open while it is loaded (one handle), never once per
 * string read (five opens, about 1 s, in the arrival frame); closed when the scripts load again */
static FILE *str_file;static long str_base;
static void string_cache_clear(void){int i;for(i=0;i<STR_CACHE;i++)str_cache[i].index=-1;str_cache_next=0;str_cache_ready=1;
    if(str_file){fclose(str_file);str_file=NULL;}}
static int read_string(int index,char *out,int capacity){
    FILE *f=NULL;int n=0,i;
    out[0]=0;
    if(capacity<1)return 0;
    if(!str_cache_ready)string_cache_clear();
    for(i=0;i<STR_CACHE;i++)if(str_cache[i].index==index && index>=0){
        n=str_cache[i].length<capacity-1?str_cache[i].length:capacity-1;
        memcpy(out,str_cache[i].text,(size_t)n);out[n]=0;return n;
    }
    if(!str_file){
        extern int com_fopen_buffer;int got;
        com_fopen_buffer=1024;got=COM_FOpenFile(FILE_NAME,&f);com_fopen_buffer=0;   /* small random reads */
        if(got<=0 || !f){if(f)fclose(f);return 0;}
        str_file=f;str_base=ftell(f);
    }
    string_reads++;
    n=read_string_from(str_file,str_base,index,out,capacity);
    if(n>0 && n<(int)sizeof(str_cache[0].text) && n<capacity-1){   /* the whole string (not cut by CAPACITY) is kept */
        i=str_cache_next;str_cache_next=(str_cache_next+1)%STR_CACHE;
        str_cache[i].index=index;str_cache[i].length=(short)n;memcpy(str_cache[i].text,out,(size_t)n+1);
    }
    return n;
}
/* The globals' names for the text defines (aw_textdef.c, BOOK-TEXT-MACROS-58), read ONCE and kept (32 bytes per
 * global, at most 512 globals: 16 KB at most). DIALOGUE-OPEN-STALL-58: the first version opened the compiled
 * scripts' file and seeked to every global's name for every define it did not know, so one conversation line could
 * cost thousands of disk seeks on an Amiga file system and the game stood still for many seconds when a
 * conversation opened. The one load reads two runs of the file in one read each (the string offsets of the globals'
 * names, then the strings between the first and the last of them, 256 KB at most, freed at once): a storm of single
 * seeks also met the emulator's disk stall (CHIM-SEYDA-BALMORA-LOAD-HANG-43). NAMES: NUL-separated; OFFSETS[g] the
 * start of global G's name, -1 none. */
#define GLOBAL_NAMES_RUN (256L*1024L)
static char *global_names;static short *global_offsets;static int global_count=-1;
static uint32_t rd_be32(const unsigned char *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static void global_names_load(void){
    FILE *f=NULL;long base;int g,count=AW_MwvmGlobalCount(),index,n,used=0,lo=-1,hi=-1;
    uint32_t offset,rows,bytes,first=0,last=0,at;unsigned char *table=NULL,*text=NULL;long span;
    if(global_count==count)return;
    free(global_names);free(global_offsets);global_names=NULL;global_offsets=NULL;global_count=count;
    if(count<=0)return;
    if(!(global_offsets=(short *)AW_TryMalloc(sizeof(short)*(size_t)count)) ||
       !(global_names=(char *)AW_TryMalloc((size_t)count*32))){
        free(global_offsets);global_offsets=NULL;global_count=0;return;
    }
    for(g=0;g<count;g++){
        global_offsets[g]=-1;
        if((index=AW_MwvmGlobalName(g,NULL))<0)continue;
        if(lo<0 || index<lo)lo=index;
        if(index>hi)hi=index;
    }
    if(lo<0 || !AW_MwvmSection("STRS",&offset,&rows,&bytes) || (uint32_t)hi>=rows)return;
    if(COM_FOpenFile(FILE_NAME,&f)<=0 || !f){if(f)fclose(f);return;}
    base=ftell(f);
    span=4L*(hi-lo+1);   /* 1: the offsets of the globals' names, one read */
    if(span<=GLOBAL_NAMES_RUN && (table=(unsigned char *)AW_TryMalloc((size_t)span))!=NULL &&
       !fseek(f,base+(long)offset+4L*lo,SEEK_SET) && fread(table,1,(size_t)span,f)==(size_t)span){
        int seen=0;
        for(g=0;g<count;g++){
            if((index=AW_MwvmGlobalName(g,NULL))<0)continue;
            at=rd_be32(table+4*(index-lo));
            if(!seen){first=last=at;seen=1;}
            if(at<first)first=at;
            if(at>last)last=at;
        }
        span=(long)(last-first)+64;   /* 2: the strings from the first name to the end of the last, one read */
        if(span<=GLOBAL_NAMES_RUN && (text=(unsigned char *)AW_TryMalloc((size_t)span+1))!=NULL &&
           !fseek(f,base+(long)offset+4L*rows+(long)first,SEEK_SET)){
            span=(long)fread(text,1,(size_t)span,f);text[span]=0;
            for(g=0;g<count;g++){   /* a name over 31 characters is never a define */
                const char *name;
                if((index=AW_MwvmGlobalName(g,NULL))<0)continue;
                at=rd_be32(table+4*(index-lo))-first;
                if((long)at>=span)continue;
                name=(const char *)text+at;
                for(n=0;(long)at+n<span && name[n];n++);
                if(n<=0 || n>31 || (long)at+n>=span || used+n+1>count*32)continue;
                global_offsets[g]=(short)used;memcpy(global_names+used,name,(size_t)n);global_names[used+n]=0;used+=n+1;
            }
        }
    }
    free(table);free(text);
    fclose(f);
}
int AW_MwscriptGlobalPrefix(const char *text,int run,int *length){
    int g,n,k,best=-1;const char *name;
    *length=0;
    if(run<=0)return -1;
    global_names_load();
    if(!global_names || !global_offsets)return -1;
    for(g=0;g<global_count;g++){
        if(global_offsets[g]<0)continue;
        name=global_names+global_offsets[g];n=(int)strlen(name);
        if(n<=*length || n>run)continue;
        for(k=0;k<n && (name[k]|((name[k]>='A' && name[k]<='Z')?32:0))==(text[k]|((text[k]>='A' && text[k]<='Z')?32:0));k++);
        if(k==n){best=g;*length=n;}
    }
    return best;
}
int AW_MwscriptGlobalType(int global){int type=-1;return AW_MwvmGlobalName(global,&type)<0?-1:type;}
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
    loops[slot].ambience=loops[slot].looping && AW_MwvmSoundAmbience(sound);
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
/* the journal-updated notice (aw_dialwin.c sets it at start: the game's sJournalEntry; none in the native tests) */
void (*aw_journal_updated)(void);
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
        {
            unsigned owed=AW_JournalNotices();int dated;
            int32_t days=AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:days"),ms=AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms");
            if(!AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ready"))ms=32400000;
            topic_values[topic]=index;AW_JournalAdd(&aw_state,name,index);   /* the 32-slot copy, for older readers */
            /* the dated history on the world change list (aw_jhist.h): every quest, no 32-slot limit */
            dated=AW_JHistAdd(&aw_jhist,AW_LedgerNameHash(name),index,days,ms);
            if((AW_JournalNotices()!=owed || dated==2) && aw_journal_updated)aw_journal_updated();   /* "Your journal has been updated." */
        }
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
    unsigned char stolen;                               /* PICKUP-PLACED-58: taken by the player from an owner */
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
/* TAKEN-LIGHT-FLAME-61: REF's placements of the CHIM exterior world (no edict; the loaded areas' effect links name
 * them) out (HIDE 1) or back (0); the placements named (0: none outdoors here). */
static int exterior_hide(uint32_t ref,int hide){
    unsigned pids[16];int i,n=AW_AreaEffectPids(ref,pids,16);
    for(i=0;i<n;i++)ChimChunks_GonePid(pids[i],hide);
    return n;
}
static void object_hide(object_t *o){
    int number=entity_of_reference(o->ref);edict_t *e=edict_of(number);
    exterior_hide(o->ref,1);
    ChimRoom_Hide(o->ref,1);           /* its placements in a CHIM room (no edict) leave too */
    if(!e || e->free)return;
    if(o->entity!=number || o->map!=attached_map || e->v.modelindex){
        o->model=e->v.modelindex;o->solid=e->v.solid;o->entity=number;o->map=attached_map;
    }
    e->v.modelindex=0;e->v.solid=SOLID_NOT;SV_LinkEdict(e,false);objects_hidden++;
}
static void object_show(object_t *o){
    edict_t *e=edict_of(o->entity);
    exterior_hide(o->ref,0);
    ChimRoom_Hide(o->ref,0);
    if(!e || e->free || o->map!=attached_map)return;    /* hidden on another map: this one never hid it */
    e->v.modelindex=o->model;e->v.solid=o->solid;SV_LinkEdict(e,false);o->entity=-1;
}
/* --- CELL-CHANGES-59: the object state on the world change list (aw_ledger.h; the default, aw_placed ledger on). One
 * sorted list for the whole world keyed by the stable reference id, every exterior cell, room and CHIM frame alike,
 * kept for the session and written into the save (feature 32). TAKEN (the player took it) and DISABLED (a script's
 * Disable) are separate fields, so Enable never brings back a taken item (SAVE-TAKEN-DISABLED-ONE-FLAG-59); there is no
 * 1,024-object or 2,048-entry ceiling. The fixed table above is the old method, kept selectable (aw_placed ledger off).
 * An edict hidden on this map keeps what it had here, to be shown again by an Enable on the same map. --- */
typedef struct {uint32_t ref;int entity,map;float model,solid;} hidden_t;
#define HIDDEN_BYTES 20
AW_RESIDENT_GROWS("hidden edicts of the loaded map (CELL-CHANGES-59)",MAX_EDICTS,HIDDEN_BYTES);
static hidden_t *hidden;static int hidden_count,hidden_capacity;
static unsigned long ledger_hidden,ledger_refused;
extern int (*aw_object_drawn)(unsigned reference);
static long map_cell_number(void);
static hidden_t *hidden_find(uint32_t ref,int create){
    int i;hidden_t *grown;
    for(i=0;i<hidden_count;i++)if(hidden[i].ref==ref && hidden[i].map==attached_map)return &hidden[i];
    if(!create)return NULL;
    if(hidden_count==hidden_capacity){
        if(hidden_capacity+64>MAX_EDICTS ||
           !(grown=(hidden_t *)AW_TryRealloc(hidden,(unsigned long)(hidden_capacity+64)*sizeof(hidden_t))))return NULL;
        hidden=grown;hidden_capacity+=64;
    }
    memset(&hidden[hidden_count],0,sizeof(hidden_t));
    hidden[hidden_count].ref=ref;hidden[hidden_count].entity=-1;hidden[hidden_count].map=attached_map;
    return &hidden[hidden_count++];
}
/* REF leaves this map: its edict (what it had is kept to show it again) and its CHIM room placements */
static void ledger_hide(uint32_t ref){
    int number=entity_of_reference(ref);edict_t *e=edict_of(number);hidden_t *h;
    exterior_hide(ref,1);
    ChimRoom_Hide(ref,1);
    if(!e || e->free || hidden_find(ref,0))return;
    if(!(h=hidden_find(ref,1))){ledger_refused++;return;}
    h->entity=number;h->model=e->v.modelindex;h->solid=e->v.solid;
    e->v.modelindex=0;e->v.solid=SOLID_NOT;SV_LinkEdict(e,false);ledger_hidden++;
}
static void ledger_show(uint32_t ref){
    hidden_t *h=hidden_find(ref,0);edict_t *e;
    exterior_hide(ref,0);
    ChimRoom_Hide(ref,0);
    if(!h)return;                      /* hidden on another map: this one never hid it */
    e=edict_of(h->entity);
    if(e && !e->free){e->v.modelindex=h->model;e->v.solid=h->solid;SV_LinkEdict(e,false);}
    *h=hidden[--hidden_count];
}
/* The row of REF, NULL when the list has none */
static aw_ledger_row_t *ledger_row(uint32_t ref){
    int i=AW_LedgerFind(&aw_ledger,ref);
    return i<0?NULL:&aw_ledger.row[i];
}
/* the place of a row made here: where the player stands (the cell, the room or the scene; aw_inventory.c) */
static void ledger_place(aw_ledger_row_t *r){
    int at;int32_t where;
    if(sv_player && AW_PlacedWhere(sv_player->v.origin,&at,&where,NULL))AW_LedgerSetPlace(&aw_ledger,r,at,where);
}
/* a reference's own lock level in the game data (a door's; 0 unlocked or not known, at most 100) */
static int ledger_data_lock(uint32_t ref){
    int level=AW_HingedDoorOriginalLock(ref);
    return level<=0?0:level>100?100:level;
}
static int32_t ledger_object(uint32_t ref,int op,int32_t value){
    aw_ledger_row_t *r=ledger_row(ref);
    switch(op){
    case AWM_ENABLE:
        if(r && (r->fields&AW_LEDGER_DISABLED)){
            r->fields&=~AW_LEDGER_DISABLED;
            if(!(r->fields&AW_LEDGER_TAKEN))ledger_show(ref);   /* a taken item stays taken */
            AW_LedgerTidy(&aw_ledger,ref);
        }
        return 0;
    case AWM_DISABLE:
        if(r && (r->fields&AW_LEDGER_DISABLED))return 0;
        if(!(r=AW_LedgerPut(&aw_ledger,ref))){ledger_refused++;return 0;}
        r->fields|=AW_LEDGER_DISABLED;ledger_hide(ref);    /* its place: unknown (read on every map) */
        return 0;
    case AWM_GETDISABLED:
        return r && (r->fields&AW_LEDGER_DISABLED);       /* OpenMW: a taken reference is not "disabled" */
    case AWM_LOCK:
        if(!(r=AW_LedgerPut(&aw_ledger,ref))){ledger_refused++;return 0;}
        /* Lock without a level: the level it had last, else its own level in the game data, else 100 */
        if(value<0)value=r->last_lock?r->last_lock:ledger_data_lock(ref)>0?ledger_data_lock(ref):100;
        if(value>100)value=100;
        r->fields|=AW_LEDGER_LOCK;r->lock=(uint8_t)value;if(value)r->last_lock=(uint8_t)value;
        return 0;
    case AWM_UNLOCK:
        if(!(r=AW_LedgerPut(&aw_ledger,ref))){ledger_refused++;return 0;}
        /* the level is kept for a later Lock (OpenMW 0.51 CellRef::unlock keeps it): the list's, else the game data's */
        if((r->fields&AW_LEDGER_LOCK) && r->lock)r->last_lock=r->lock;
        else if(!(r->fields&AW_LEDGER_LOCK) && ledger_data_lock(ref)>0)r->last_lock=(uint8_t)ledger_data_lock(ref);
        r->fields|=AW_LEDGER_LOCK;r->lock=0;
        return 0;
    }
    return 0;
}
static int ledger_take(uint32_t reference,int stolen){
    int number,room;edict_t *e;aw_ledger_row_t *r=ledger_row(reference);
    if(r && (r->fields&(AW_LEDGER_TAKEN|AW_LEDGER_DISABLED)))return 0;
    number=entity_of_reference(reference);e=edict_of(number);
    room=ChimRoom_Hide(reference,1);
    if(!room)room=exterior_hide(reference,1);      /* TAKEN-LIGHT-FLAME-61: a light of the CHIM exterior world */
    if(!room && (!e || e->free) && !(aw_object_drawn && aw_object_drawn(reference)))return 0;
    if(!(r=AW_LedgerPut(&aw_ledger,reference))){if(room){ChimRoom_Hide(reference,0);exterior_hide(reference,0);}
        ledger_refused++;return 0;}
    r->fields|=AW_LEDGER_TAKEN|(stolen?AW_LEDGER_STOLEN:0);
    ledger_place(r);ledger_hide(reference);
    return 1;
}
/* A new map: what an earlier map hid is that map's; the edicts of this map the list says are gone (taken or
 * disabled) are hidden, and the rows of this room or scene and those of no known place take their room placements
 * (no edict) out. Only this map's rows are read: the edicts by reference, the rows by their place. */
static void ledger_attach(void){
    int i,j,n,first,k;long room=map_cell_number();
    static const int kinds[3]={AW_AT_ROOM,AW_AT_SCENE,AW_AT_ANY};int32_t places[3];
    hidden_count=0;
    if(!aw_ledger.count)return;
    for(i=0;i<edict_ref_count;i++){
        k=AW_LedgerFind(&aw_ledger,edict_refs[i].ref);
        if(k>=0 && (aw_ledger.row[k].fields&(AW_LEDGER_TAKEN|AW_LEDGER_DISABLED)))ledger_hide(edict_refs[i].ref);
    }
    places[0]=(int32_t)room;places[1]=AW_MapId(sv.name);places[2]=0;
    for(j=0;j<3;j++){
        if((j==0 && room<=0) || (j==1 && places[1]<0))continue;
        n=AW_LedgerPlace(&aw_ledger,kinds[j],places[j],&first);
        for(i=0;i<n;i++){
            aw_ledger_row_t *r=AW_LedgerPlaceRow(&aw_ledger,first+i);
            if(r && (r->fields&(AW_LEDGER_TAKEN|AW_LEDGER_DISABLED)))ledger_hide(r->key);
        }
    }
}
/* an older save's object entries (feature 8): their one flag meant taken or disabled; read as DISABLED, what it did
 * then (Enable could bring it back), and only for keys the save's own list does not hold */
static void ledger_import(const aw_changes_t *in){
    int i;aw_ledger_row_t *r;
    for(i=0;i<in->count;i++){
        const aw_change_t *e=&in->entry[i];
        if(!(e->flags&(AW_CHANGE_DISABLED|AW_CHANGE_LOCK)) || (e->key&AW_CHANGE_BUILDER) ||
           AW_LedgerFind(&aw_ledger,e->key)>=0)continue;
        if(!(r=AW_LedgerPut(&aw_ledger,e->key))){ledger_refused++;break;}
        if(e->flags&AW_CHANGE_DISABLED)r->fields|=AW_LEDGER_DISABLED;
        if(e->flags&AW_CHANGE_LOCK){
            r->fields|=AW_LEDGER_LOCK;r->lock=r->last_lock=(uint8_t)((e->flags&AW_CHANGE_LOCK_LEVEL)>>AW_CHANGE_LOCK_SHIFT);
        }
    }
    hidden_count=0;
}
static int topic_rows_now(void);
static void script_import(const aw_ledger_t *l);
static unsigned long locals_kept,locals_dropped,locals_refused;
/* aw_placed ledger and aw_mwscript_status: the world change list's rows by field, its resident bytes */
void AW_MwscriptLedgerStatus(void){
    int i,n[8]={0,0,0,0,0,0,0,0};
    for(i=0;i<aw_ledger.count;i++){
        unsigned f=aw_ledger.row[i].fields;int k;
        for(k=0;k<8;k++)if(f&(1U<<k))n[k]++;
    }
    Con_Printf("world change list %s: %d rows (taken %d, disabled %d, locks %d, stolen %d, moved %d, drops %d, "
               "open doors %d), %d stolen pairs, %lu bytes resident, %lu refused; this map hid %d edicts (%lu in the "
               "session, %lu not kept)\n",
               aw_ledger_on?"on":"off (the fixed tables)",aw_ledger.count,n[0],n[1],n[2],n[3],n[4],n[5],n[7],
               aw_ledger.stolen_count,AW_LedgerResident(&aw_ledger)+(unsigned long)hidden_capacity*sizeof(hidden_t),
               aw_ledger.refused,hidden_count,ledger_hidden,ledger_refused);
    /* slice 4: the script and dialogue tables (the globals, quests and topics as of the last save or load) against the
     * game's own counts, and the named facts */
    Con_Printf("  slice 4: %d globals changed (of %d), %d quest stages (of %d quests), %d topics known (of %d), "
               "%d dispositions, %d named facts\n",aw_ledger.value_count[AW_LEDGER_GLOBALS],AW_MwvmGlobalCount(),
               aw_ledger.value_count[AW_LEDGER_QUESTS],AW_MwvmTopicCount(),aw_ledger.value_count[AW_LEDGER_TOPICS],
               topic_rows_now(),aw_ledger.value_count[AW_LEDGER_DISPOSITIONS],aw_ledger.fact_count);
    /* slice 5: the scripts' locals and the global scripts whose running state changed, as of the last save or load */
    Con_Printf("  slice 5: %d script locals kept, %d global scripts started or stopped (last save: %lu kept, %lu "
               "refused; last load: %lu dropped)\n",aw_ledger.local_count,aw_ledger.script_count,locals_kept,
               locals_refused,locals_dropped);
    /* slice 6: the actors' rows (killed, moved with health, hostile) and the live actor records now */
    {int dead=0,moved=0,fight=0,live,changed=0;
     for(i=0;i<aw_ledger.actor_count;i++){dead+=aw_ledger.actor[i].dead;moved+=aw_ledger.actor[i].moved;fight+=aw_ledger.actor[i].fight;}
     live=AW_ActorStateLive(&changed);
     Con_Printf("  slice 6: %d actor rows (%d dead, %d moved, %d hostile); %d actor records live, %d changed\n",
                aw_ledger.actor_count,dead,moved,fight,live,changed);
     for(i=0;i<aw_ledger.actor_count && i<16;i++){
         const aw_ledger_actor_t *a=&aw_ledger.actor[i];
         Con_Printf("  actor %lu%s%s%s%s health %.0f room %ld died %.1f h\n",(unsigned long)a->key,a->dead?" dead":"",
                    a->moved?" moved":"",a->fight?" hostile":"",a->pick?" levelled roll":"",a->health,(long)a->room,a->died);
     }}
    /* slice 7: respawn and migration */
    {const aw_ledger_events_t *v=&aw_ledger_events;
     Con_Printf("  slice 7: respawn: %lu containers refilled in %lu place loads, %lu actors back; %d places with a refill "
                "time, %d references with a record hash, %d content files; game hours now %.1f\n",v->containers,v->places,
                v->actors,aw_ledger.stamp_count,aw_ledger.ident_count,aw_ledger.file_count,AW_LedgerGameHours());
     if(v->migrations)
         Con_Printf("  slice 7: last load of other game data dropped %lu changes (objects %lu, containers %lu, ranks %lu, "
                    "dispositions %lu, locals %lu, actors %lu, levelled rolls %lu, drops %lu, stolen %lu; content files "
                    "missing %lu; actor records %lu)\n",v->migrated_all,v->migrated.objects,v->migrated.containers,
                    v->migrated.ranks,v->migrated.dispositions,v->migrated.locals,v->migrated.actors,v->migrated.picks,
                    v->migrated.drops,v->migrated.stolen,v->migrated.files,v->records);}
    for(i=0;i<aw_ledger.value_count[AW_LEDGER_DISPOSITIONS] && i<16;i++)
        Con_Printf("  ref %lu disposition %ld\n",(unsigned long)aw_ledger.value[AW_LEDGER_DISPOSITIONS][i].key,
                   (long)aw_ledger.value[AW_LEDGER_DISPOSITIONS][i].value);
    /* slice 2: the locks and open doors of the list, and the stolen pairs (item, owner, count), the first 16 each */
    for(i=0,n[0]=0;i<aw_ledger.count && n[0]<16;i++){
        const aw_ledger_row_t *r=&aw_ledger.row[i];
        if(!(r->fields&(AW_LEDGER_LOCK|AW_LEDGER_OPEN)))continue;
        n[0]++;
        if(r->fields&AW_LEDGER_LOCK)
            Con_Printf("  ref %lu %s lock %d (last %d)%s\n",(unsigned long)r->key,r->lock?"locked":"unlocked",(int)r->lock,
                       (int)r->last_lock,(r->fields&AW_LEDGER_OPEN)?" open":"");
        else Con_Printf("  ref %lu door open\n",(unsigned long)r->key);
    }
    for(i=0;i<aw_ledger.stolen_count && i<16;i++)
        Con_Printf("  stolen %s from %s%s: %ld\n",aw_ledger.stolen[i].item,aw_ledger.stolen[i].faction?"faction ":"",
                   aw_ledger.stolen[i].owner,(long)aw_ledger.stolen[i].count);
}
/* CELL-CHANGES-59 slice 2: a hinged door's pose on the world change list (aw_hinged_door.c through aw_door_open). SET
 * 1: it opens (the use turns it open), 0: it closes (the row goes when nothing else is on it), -1: asks, 1 when the
 * list holds it open. The use's direction is recorded at the use, so a save taken while it turns keeps where it goes
 * (OpenMW 0.51 keeps a door's state on its reference). With the list off (the old method) no door pose is kept: -1. */
static int door_open(unsigned reference,int set){
    aw_ledger_row_t *r;
    if(!aw_ledger_on || !reference || reference>0xFFFFFFu)return -1;
    r=ledger_row(reference);
    if(set<0)return r && (r->fields&AW_LEDGER_OPEN)?1:0;
    if(set){
        if(r && (r->fields&AW_LEDGER_OPEN))return 1;
        if(!(r=AW_LedgerPut(&aw_ledger,reference))){ledger_refused++;return 0;}
        r->fields|=AW_LEDGER_OPEN;ledger_place(r);
        return 1;
    }
    if(r && (r->fields&AW_LEDGER_OPEN)){r->fields&=~AW_LEDGER_OPEN;AW_LedgerTidy(&aw_ledger,reference);}
    return 0;
}
static int32_t object_op(uint32_t ref,int op,int32_t value);
static int32_t host_object(int instance,int target,int op,int32_t value){
    uint32_t ref=target_reference(instance,target);
    if(!ref)return 0;
    return object_op(ref,op,value);
}
/* CELL-CHANGES-59 slice 2: a lock change that is not a script's own line (aw_hinged_door.c through aw_object_lock):
 * the player's key opening a lock (OpenMW 0.51 mwclass/door.cpp and container.cpp: the key unlocks the reference, its
 * level kept for a later Lock), and the console's Lock / Unlock on the door under the crosshair. LOCK 1: Lock LEVEL
 * (-1: the level it had last); 0: Unlock. The same path as a script's, so it is kept and saved the same way. */
int AW_ObjectLock(unsigned reference,int lock,int level){
    if(!reference || reference>0xFFFFFFu)return 0;
    object_op(reference,lock?AWM_LOCK:AWM_UNLOCK,lock?level:0);
    return 1;
}
static int32_t object_op(uint32_t ref,int op,int32_t value){
    object_t *o;
    if(aw_ledger_on && op!=AWM_ACTIVATE && op!=AWM_GETLOCKED)return ledger_object(ref,op,value);
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
/* gone from the world: taken or disabled (not drawn, no aim box, no actor spawned) */
int AW_ObjectDisabled(unsigned int reference){
    object_t *o;
    if(aw_ledger_on){aw_ledger_row_t *r=ledger_row(reference);return r && (r->fields&(AW_LEDGER_TAKEN|AW_LEDGER_DISABLED));}
    o=object_find(reference,0);return o && o->disabled;
}
/* PICKUP-PLACED-58: the player takes a placed item. Like the original and OpenMW 0.51 the reference leaves the world
 * for good: here it is disabled (the object state above, kept in saved games, hidden again at every map) and hidden
 * now, its edict or its CHIM room placements. Refused (0) when nothing of it can be hidden on this map, so the item
 * never sits in the inventory and on the table at once. The owner mark stays for the session (CRIME-59). */
/* WORLD-OBJECT-PLACEMENT-59 (aw_placed.c sets it): the reference is one of the placed items drawn by reference to the
 * shared item models; disabling it is what hides it (it is linked only while not disabled). */
int (*aw_object_drawn)(unsigned reference);
int AW_ObjectTake(unsigned int reference,int stolen){
    object_t *o;int number;edict_t *e;int room;
    if(!reference || reference>0xFFFFFFu || AW_ObjectDisabled(reference))return 0;
    if(aw_ledger_on)return ledger_take(reference,stolen);       /* CELL-CHANGES-59: TAKEN on the world change list */
    number=entity_of_reference(reference);e=edict_of(number);
    room=ChimRoom_Hide(reference,1);
    if(!room)room=exterior_hide(reference,1);
    if(!room && (!e || e->free) && !(aw_object_drawn && aw_object_drawn(reference)))return 0;
    if(!(o=object_find(reference,1))){if(room){ChimRoom_Hide(reference,0);exterior_hide(reference,0);}return 0;}
    o->disabled=1;o->stolen=stolen?1:0;object_hide(o);
    return 1;
}
int AW_ObjectLockLevel(unsigned int reference,int original){
    object_t *o;
    if(aw_ledger_on){aw_ledger_row_t *r=ledger_row(reference);return r && (r->fields&AW_LEDGER_LOCK)?r->lock:original;}
    o=object_find(reference,0);
    return o && o->lock_set?o->level:original;
}
/* Saved games: merged by key into the change list the actors exported. With the world change list on, the objects
 * are its rows (feature 32, aw_save.c) and nothing is added here: the 2,048-entry list holds the actors alone, so it
 * never fills over the objects and refuses the save (SAVE-CHANGES-FULL-REFUSES-SAVE-59). */
static int objects_export(aw_changes_t *out){
    int i,j;uint32_t flags,key;
    if(aw_ledger_on)return out->count;
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
    if(aw_ledger_on){ledger_import(in);map_model=NULL;return;}
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
static int area_stats_source(uint32_t reference,struct aw_stat_block_s *out){
    return AW_AreaActorStats((unsigned)reference,0,out);
}
/* the area load's maker (aw_inventory.c aw_area_actor_make): REFERENCE 0 asks only whether it can make records */
static int area_actor_make(unsigned reference,int actb_row,const unsigned char *section,long bytes,long offset,
                           const unsigned char *shared,long shared_bytes){
    aw_stat_block_t b;
    if(!AW_ActorStatsSwitch(-1) || !AW_MwscriptActors())return -1;
    if(!reference)return 0;
    return AW_StatDecodeAt(section,bytes,offset,shared,shared_bytes,&b) &&
           AW_ActorFromStats((uint32_t)reference,actb_row,&b)!=NULL;
}
extern int (*aw_area_actor_make)(unsigned,int,const unsigned char *,long,long,const unsigned char *,long);
extern int (*aw_area_stat_decode_at)(const unsigned char *,long,long,const unsigned char *,long,aw_stat_block_t *);
extern int (*aw_area_stat_decode)(const unsigned char *,long,uint32_t,const unsigned char *,long,aw_stat_block_t *);
/* combat's sheets read the being's stat block (the combat reader on the one API): the record's level, attributes,
 * skills (a creature's by specialization), health, magicka, fatigue (current at the base), Fight and Flee */
static unsigned long combat_sheets_from_stats;
static void combat_sheet_stats(const char *id,aw_fighter_t *o){
    aw_stat_block_t b;int k;
    if(!AW_ActorStatsSwitch(-1) || !id || !AW_AreaActorStats(0,AW_StatIdHash(id),&b))return;
    o->level=(short)AW_StatRead(&b,AWS_LEVEL);
    for(k=0;k<8;k++){int v=AW_StatRead(&b,AWS_ATTRIBUTE+k);o->attributes[k]=(unsigned char)(v>255?255:v);}
    for(k=0;k<27;k++){int v=AW_StatRead(&b,AWS_SKILL+k);o->skills[k]=(unsigned char)(v>255?255:v);}
    o->health=o->health_max=(float)AW_StatRead(&b,AWS_HEALTH);
    o->magicka=(float)AW_StatRead(&b,AWS_MAGICKA);
    o->fatigue=o->fatigue_max=(float)AW_StatRead(&b,AWS_FATIGUE);
    o->fight=(unsigned char)AW_StatRead(&b,AWS_FIGHT);o->flee=(unsigned char)AW_StatRead(&b,AWS_FLEE);
    combat_sheets_from_stats++;
}
/* ACTOR-STATS-ALL-61: the area tables' hooks into the stat decoder and the actor record */
static void stats_hooks(void){
    aw_area_actor_make=area_actor_make;aw_area_stat_decode_at=AW_StatDecodeAt;aw_area_stat_decode=AW_StatDecode;
    aw_combat_sheet_stats=combat_sheet_stats;
}
int AW_MwscriptActors(void){
    static const aw_actorstate_io_t io={actor_read,NULL};
    unsigned char head[16+16*32];int length,n;
    if(AW_ActorStateReady())return 1;
    if(actors_failed)return 0;
    actors_failed=1;
    if(actor_file){fclose(actor_file);actor_file=NULL;}
    /* ARRIVAL-LONG-FRAME-DEV6-59: the actor rows are read by a binary search on disk (a few small reads per actor):
     * a 1 KB buffer, not 16 KB refilled at every probe (about 1 s of the first play frame in Seyda Neen) */
    {extern int com_fopen_buffer;com_fopen_buffer=1024;
     length=COM_FOpenFile(FILE_NAME,&actor_file);
     com_fopen_buffer=0;}
    if(!actor_file || length<16)return 0;
    actor_base=ftell(actor_file);
    if(fread(head,1,16,actor_file)!=16 || memcmp(head,"AWMS",4))return 0;
    n=(head[6]<<8)|head[7];if(n>32)n=32;
    if(fread(head+16,1,16*n,actor_file)!=(size_t)(16*n) || !AW_ActorStateOpen(head,16+16*n,&io))return 0;
    actors_failed=0;
    aw_actor_stats_source=area_stats_source;     /* ACTOR-STATS-ALL-61: a placed actor's record from its area */
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
/* ACTOR-STATS-ALL-61: the player's spells from character creation (OpenMW 0.51 mechanicsmanagerimp.cpp: the chosen
 * race's powers and abilities, the birthsign's spells; the class gives none of its own). Applied when the race or the
 * birthsign is (re)chosen: what the previous choice gave goes, and the abilities and powers of the default player
 * record (the game's "player" NPC) go the first time; spells bought or added by scripts stay. Since v0.0.61 also the
 * starting spells OpenMW autocalculates from the class's skills (autocalcspell.cpp autoCalcPlayerSpells, start_spells
 * below), chosen again when the class is. */
static int applied_race=-2,applied_birth=-2,applied_class=-2,applied_n;static int applied[AWS_SPELLS];
/* PLAYER-START-SPELLS-NOT-KNOWN-61: the starting spells of the class and the skills (OpenMW 0.51 mechanicsmanagerimp.cpp
 * buildPlayer: autoCalcPlayerSpells over the new character's base skills and attributes, aw_cast_rules.c). Computed
 * from the character as creation builds it (race, sex, class, birthsign at level 1), so a later skill gain or a load
 * never changes the set. RACE: the race's spells (never given twice). Into OUT, how many. */
#define START_SPELLS 32
static int start_spells(const int *race,int nrace,int *out,int max){
    aw_start_spell_t *s;aw_start_settings_t set;aw_character_t c=aw_character;
    int rows[START_SPELLS],count,i,k,type,n;float skills[27],attributes[8];char name[8];
    if(!(count=AW_ActorStartSpells(&set,rows,START_SPELLS)) || !AW_CharacterRebuild(&c))return 0;
    /* about 0.5 KB a spell, only while they are chosen (the masters flag 12) */
    if(!(s=(aw_start_spell_t *)AW_TryMalloc(sizeof(aw_start_spell_t)*(unsigned long)count)))return 0;
    for(i=0;i<8;i++)attributes[i]=c.attributes[i];
    for(i=0;i<27;i++)skills[i]=c.skills[i];
    for(i=0;i<count;i++){
        memset(&s[i],0,sizeof(s[i]));s[i].row=rows[i];
        AW_ActorSpellInfo(rows[i],&type,name,sizeof(name),&s[i].cost);
        s[i].flags=AW_ActorSpellFlags(rows[i]);
        s[i].n=AW_ActorSpellEffects(rows[i],s[i].e,AW_MADE_EFFECTS);
        for(k=0;k<s[i].n;k++)if(!AW_ActorMagicEffect(s[i].e[k].effect,&s[i].m[k]))memset(&s[i].m[k],0,sizeof(s[i].m[k]));
    }
    n=AW_CastStartSpells(s,count,&set,skills,attributes,race,nrace,out,max);
    free(s);
    return n;
}
static int start_chosen[START_SPELLS],start_chosen_n=-1;
static aw_actor_t *player_record(void);
void AW_MwscriptStartSpellsReport(void){
    int i,type,cost;char name[32];
    player_record();   /* a race, class or birthsign changed since: chosen again now */
    if(start_chosen_n<0){Con_Printf("Starting spells: no character made in this session.\n");return;}
    Con_Printf("Starting spells from the class and the skills: %d\n",start_chosen_n);
    for(i=0;i<start_chosen_n;i++){
        AW_ActorSpellInfo(start_chosen[i],&type,name,sizeof(name),&cost);
        Con_Printf(" %d %s (cost %d)\n",start_chosen[i],name,cost);
    }
}
static void creation_spells(aw_actor_t *a){
    int want[AWS_SPELLS],n=0,i,j,held[128],h,type,cost,nrace;long tb;const unsigned char *t;char name[8];
    if(!aw_character.valid || (aw_character.race==applied_race && aw_character.birth==applied_birth &&
                               aw_character.clas==applied_class))return;
    if(!(t=AW_AreaStatsShared(&tb)))return;
    if(aw_character.race>=0 && aw_character.race<aw_race_count)
        n+=AW_StatRaceSpells(t,tb,AW_StatIdHash(aw_races[aw_character.race].id),want+n,AWS_SPELLS-n);
    nrace=n;
    if(aw_character.birth>=0 && aw_character.birth<aw_birth_count)
        n+=AW_StatBirthSpells(t,tb,AW_StatIdHash(aw_births[aw_character.birth].id),want+n,AWS_SPELLS-n);
    {int k=start_spells(want,nrace,want+n,AWS_SPELLS-n<START_SPELLS?AWS_SPELLS-n:START_SPELLS);
     memcpy(start_chosen,want+n,sizeof(int)*(size_t)k);start_chosen_n=k;n+=k;}
    if(applied_race==-2){
        h=AW_ActorSpells(a,held,128);
        for(i=0;i<h;i++){
            for(j=0;j<n && want[j]!=held[i];j++);
            if(j==n && AW_ActorSpellInfo(held[i],&type,name,sizeof(name),&cost) && (type==1 || type==5))
                AW_ActorRemoveSpell(a,held[i]);
        }
    }else for(i=0;i<applied_n;i++){for(j=0;j<n && want[j]!=applied[i];j++);if(j==n)AW_ActorRemoveSpell(a,applied[i]);}
    for(i=0;i<n;i++)if(!AW_ActorHasSpell(a,want[i]))AW_ActorAddSpell(a,want[i]);
    memcpy(applied,want,sizeof(int)*(size_t)n);applied_n=n;applied_race=aw_character.race;applied_birth=aw_character.birth;
    applied_class=aw_character.clas;
    Con_DPrintf("Player spells: %d from the race, the birthsign, the class and the skills (%d starting spells)\n",n,start_chosen_n);
}
static aw_actor_t *player_record(void){
    aw_actor_t *a=AW_ActorPlayer();int i;
    if(!a || !aw_character.valid)return a;
    creation_spells(a);
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
/* PLAYER-CASTING-59 (aw_cast.c): the player's record with the sheet's stats when there is a sheet (else the record's
 * own, as a game started straight on a map has), and its changes back to the sheet and the edict */
aw_actor_t *AW_MwscriptPlayerRecord(void){return player_record();}
void AW_MwscriptPlayerStore(aw_actor_t *a){player_store(a);AW_MwvmStateChanged();}
/* PLAYER-CASTING-59 / SPELL-EFFECTS-57: the actors that carry effects, by reference, and their edicts (found once,
 * checked by their aw_ref each time: no edict scan a frame) */
#define FX_EDICTS 16
static aw_actor_t *disposition_restore(aw_actor_t *a);
static uint32_t fx_edict_ref[FX_EDICTS];static int fx_edict_num[FX_EDICTS];
static uint32_t ref_of_edict(edict_t *e){eval_t *v=e?GetEdictFieldValue(e,"aw_ref"):NULL;return v && v->_float>0?(uint32_t)v->_float:0;}
static void fx_edict_keep(uint32_t ref,edict_t *e){
    int i,k=-1;
    for(i=0;i<FX_EDICTS;i++){if(fx_edict_ref[i]==ref){k=i;break;}if(k<0 && !fx_edict_ref[i])k=i;}
    if(k<0)k=(int)(ref%FX_EDICTS);
    fx_edict_ref[k]=ref;fx_edict_num[k]=NUM_FOR_EDICT(e);
}
static edict_t *fx_edict(uint32_t ref){
    int i;
    for(i=0;i<FX_EDICTS;i++)if(fx_edict_ref[i]==ref){
        edict_t *e;
        if(fx_edict_num[i]<=0 || fx_edict_num[i]>=sv.num_edicts)break;
        e=EDICT_NUM(fx_edict_num[i]);
        if(!e->free && ref_of_edict(e)==ref)return e;
        break;
    }
    return NULL;
}
/* the record of an actor's edict (made from its base when it has none yet), NULL for objects without one */
static aw_actor_t *record_of_edict(edict_t *e){
    uint32_t ref=ref_of_edict(e);int row;
    if(!ref || !AW_MwscriptActors() || (row=row_of_edict(e))==AW_ACTOR_NONE)return NULL;
    return disposition_restore(AW_ActorGet(ref,row,1));
}
/* WEAPON-STRIKE-ENCHANT-NOT-CAST-61 (aw_cast.c): an actor edict's record and its actor table row */
aw_actor_t *AW_MwscriptActorOf(edict_t *e,int *row){
    aw_actor_t *a=record_of_edict(e);
    if(row)*row=a?a->base:AW_ACTOR_NONE;
    return a;
}
/* the effects of RANGE among a spell's N effects (E, their records M) land on TARGET: the player when NULL or
 * sv_player, else the actor whose edict it is (OpenMW spellcasting.cpp inflict): each magnitude rolled once, the
 * cures carried out at once as the scripts' Cast does; a harmful effect on an actor is an attack (AW_CombatSpellHit).
 * How many effects landed; -1 when TARGET has no actor record. */
int AW_MwscriptLand(edict_t *target,const aw_spell_effect_t *e,const aw_mgef_t *m,int n,int range,int source){
    aw_actor_t *a;int i,k=0,harmful=0,on_player=!target || target==sv_player;float health;
    a=on_player?player_record():record_of_edict(target);
    if(!a)return -1;
    if(!on_player){
        if(a->flags&AWL_DEAD)return 0;
        if(AW_CombatSlotState(target,&health)==1)a->dyn_cur[0]=health;   /* the fight's health is the live one */
    }
    health=a->dyn_cur[0];
    for(i=0;i<n;i++){
        float mag;int arg;
        if(e[i].range!=range)continue;
        if((m[i].flags&AW_MGEF_HARMFUL) || AW_EffectHarmful(e[i].effect))harmful=1;
        if(e[i].effect==69 || e[i].effect==70){   /* Cure Common / Blight Disease: those spells go */
            if(AW_ActorRemoveSpellType(a,e[i].effect==69?3:2)>0)k++;
            continue;
        }
        mag=m[i].flags&AW_MGEF_NO_MAGNITUDE?1:AW_CastMagnitude(e[i].magnitude_min,e[i].magnitude_max,(float)(rand()&32767)/32768.0f);
        arg=e[i].attribute>=0?e[i].attribute:e[i].skill>=0?e[i].skill:AW_EFFECT_NO_ARG;
        if(AW_EffectsLand(a,e[i].effect,arg,mag,AW_CastDuration(&e[i],&m[i]),source))k++;
    }
    Con_DPrintf("Spell: %d of %d effects (range %d) landed on %s, health %.1f -> %.1f\n",k,n,range,
                on_player?"you":(target->v.netname?pr_strings+target->v.netname:"an actor"),health,a->dyn_cur[0]);
    if(on_player)player_store(a);
    else{
        fx_edict_keep(a->reference,target);
        if(harmful || a->dyn_cur[0]!=health)AW_CombatSpellHit(target,a->dyn_cur[0],harmful);
        if(a->dyn_cur[0]<=0){AW_EffectsForget(a->reference);if(!(a->flags&AWL_DEAD))AW_ActorKill(a);}
    }
    AW_MwvmStateChanged();
    return k;
}
#ifdef AW_COMBAT_EFFECT_MAGNITUDE
/* RESIST-NORMAL-WEAPONS-61 (aw_combat.h aw_combat_effect_magnitude): the summed magnitude of EFFECT active on the
 * actor of edict E now (the player's or an NPC's by its reference); once per landed blow, no file read */
static float effect_magnitude_of(edict_t *e,int effect){
    uint32_t ref;
    if(!e)return 0;
    if(e==sv_player)return AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,effect,AW_EFFECT_NO_ARG);
    ref=ref_of_edict(e);
    return ref?AW_EffectsMagnitude(ref,effect,AW_EFFECT_NO_ARG):0;
}
#endif
/* the NPCs' and creatures' effects on the game clock: only those whose record is in the pool and whose edict is in
 * the loaded world tick (OpenMW updates the actors of the active cells); their health goes to the fight */
static void npc_effects_tick(float dt){
    uint32_t owners[16];int n=AW_EffectsOwners(owners,16),i;
    for(i=0;i<n;i++){
        edict_t *e=fx_edict(owners[i]);aw_actor_t *a;float before;
        if(!e || !(a=AW_ActorGet(owners[i],AW_ACTOR_NONE,0)))continue;
        before=a->dyn_cur[0];
        if(!AW_EffectsTick(a,dt))continue;
        if(a->dyn_cur[0]!=before)AW_CombatSpellHit(e,a->dyn_cur[0],0);
        if(a->dyn_cur[0]<=0){AW_EffectsForget(owners[i]);if(!(a->flags&AWL_DEAD))AW_ActorKill(a);}
        AW_MwvmStateChanged();
    }
}
/* REST-WAIT-59 (aw_wait.c): the player's spell effects over SECONDS of passing time (a rest or a wait), as the frame's
 * tick does (OpenMW Actors::rest: adjustMagicEffects by the elapsed time) */
void AW_MwscriptEffectsAdvance(float seconds){
    aw_actor_t *p;
    if(!(seconds>0) || !AW_EffectsCount() || !(p=player_record()))return;
    if(AW_EffectsTick(p,seconds)){player_store(p);AW_MwvmStateChanged();}
}
/* CELL-CHANGES-59 slice 4: an NPC's disposition changed by a script (SetDisposition, ModDisposition) or a conversation
 * is kept by its reference on the world change list (OpenMW 0.51 npcstats: the base disposition is the NPC's own
 * saved state), so it outlives the 128-record pool (ACTOR-STATE-POOL-LIMITS-54); back at the data's value it goes. */
static int disposition_key_ok(uint32_t ref){return ref && ref!=AW_ACTOR_PLAYER_REF && !(ref&0x7F000000U);}
static void disposition_keep(aw_actor_t *a){
    aw_actor_base_t b;int now;
    if(!a || !aw_ledger_on || !disposition_key_ok(a->reference) || !AW_ActorBase(a->base,&b) || b.kind!=0)return;
    now=(int)AW_ActorStat(a,AWA_DISPOSITION);
    if(now==(int)b.disposition)AW_LedgerValueDrop(&aw_ledger,AW_LEDGER_DISPOSITIONS,a->reference);
    else AW_LedgerValueSet(&aw_ledger,AW_LEDGER_DISPOSITIONS,a->reference,now);
}
/* a record made again (or kept) takes the list's disposition */
static aw_actor_t *disposition_restore(aw_actor_t *a){
    int32_t d;
    if(a && aw_ledger_on && a->kind==0 && disposition_key_ok(a->reference) &&
       AW_LedgerValue(&aw_ledger,AW_LEDGER_DISPOSITIONS,a->reference,&d) && (int)AW_ActorStat(a,AWA_DISPOSITION)!=d)
        AW_ActorSetStat(a,AWA_DISPOSITION,(float)d);
    return a;
}
/* the disposition of REFERENCE when no live record has it: the list's, else BASE */
static int disposition_kept(unsigned long reference,int base){
    int32_t d;
    return aw_ledger_on && disposition_key_ok((uint32_t)reference) &&
           AW_LedgerValue(&aw_ledger,AW_LEDGER_DISPOSITIONS,(uint32_t)reference,&d)?(int)d:base;
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
    return disposition_restore(AW_ActorGet(ref,row,1));
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
    if(stat==AWA_DISPOSITION)disposition_keep(a);   /* slice 4: on the world change list */
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
/* DIALOGUE-ITEM-NOTICE-MISSING-61 (OpenMW 0.51 containerextensions.cpp OpAddItem / OpRemoveItem): an item a script
 * adds to or removes from the player is told in the conversation while the dialogue window is open (the message box
 * in ShowInDialogueMode_Only: nowhere else), with the game's own lines sNotifyMessage60 (one added), 61 (COUNT added),
 * 62 (one removed), 63 (COUNT removed), the item's name filled in; the game text is read only when one is shown. */
static void item_notice(const char *id,int32_t count,int added){
    static const char *const keys[4]={"sNotifyMessage60","sNotifyMessage61","sNotifyMessage62","sNotifyMessage63"};
    static const char *const fallback[4]={"%s has been added to your inventory.","%d %s has been added to your inventory.",
                                          "%s has been removed from your inventory.","%d %s has been removed from your inventory."};
    char form[160],line[256],number[16];aw_inventory_item_t it;const char *name;int k=(added?0:2)+(count>1),i,o=0;
    if(count<1 || !AW_DialWindowActive())return;
    name=AW_InventoryRead(id,&it) && it.name[0]?it.name:id;
    if(!AW_LevelupGameText(keys[k],form,sizeof(form)) || !form[0])Q_strcpy_bounded(form,fallback[k],sizeof(form));
    Q_snprintf(number,sizeof(number),"%ld",(long)count);
    for(i=0;form[i] && o<(int)sizeof(line)-1;i++){
        const char *put=NULL;
        if(form[i]=='%' && form[i+1]=='s'){put=name;i++;}
        else if(form[i]=='%' && form[i+1]=='d'){put=number;i++;}
        else if(form[i]=='%' && form[i+1]=='%'){i++;}
        if(!put){line[o++]=form[i];continue;}
        while(*put && o<(int)sizeof(line)-1)line[o++]=*put++;
    }
    line[o]=0;
    AW_DialWindowMessage(line);
}
static int32_t host_item(int instance,int target,int verb,int item,int32_t count){
    edict_t *e;aw_actor_t *a=actor_of(instance,target,&e);aw_item_t it;
    actor_calls++;
    if(!a && target>=0 && aw_ledger_on){
        /* CELL-CHANGES-59 slice 3: a placed container (OpenMW 0.51 containerextensions.cpp OpAddItem, OpRemoveItem,
         * OpGetItemCount on a container's store): its data contents with the world change list's deltas; RemoveItem
         * takes up to what it holds; kept and saved. A script's change is never theft. */
        uint32_t ref=AW_MwvmObjectReference(target);char id[64];int have;
        folded_item_id(item,id,sizeof(id));
        if(ref && id[0] && (have=AW_ContainerCount(ref,id))>=0){
            if(count<0)count=(int32_t)(uint16_t)count;
            if(verb==1 || verb==2){
                if(count)AW_ContainerChange(ref,id,verb==1?count:-count,0);
                AW_MwvmStateChanged();have=AW_ContainerCount(ref,id);
            }
            return have<0?0:have;
        }
    }
    if(!a){actor_misses++;return 0;}
    if(verb && (!AW_ActorItem(item,&it) || it.kind==AWK_UNKNOWN))return 0;   /* an id no record has (OpenMW: refused) */
    if(a->reference==AW_ACTOR_PLAYER_REF){
        /* the player's inventory is the game state the engine keeps (aw_state.c AW_ITEM) */
        char id[64];int32_t have;
        folded_item_id(item,id,sizeof(id));
        if(!id[0])return 0;
        have=AW_StateGet(&aw_state,AW_ITEM,id);
        if(count<0)count=(int32_t)(uint16_t)count;
        if(verb==1 && count){AW_StateSet(&aw_state,AW_ITEM,id,have+count);item_notice(id,count,1);}
        else if(verb==2 && count){
            AW_StateSet(&aw_state,AW_ITEM,id,have>count?have-count:0);
            if(have>0)item_notice(id,have>count?count:have,0);   /* only what was removed (numRemoved > 0) */
        }
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
/* The loaded room map's shift (map units = game units / 4 + shift), found when the map attached; the focus box's
 * placed rows use it (aw_inventory.c). 0 outdoors or before the scripts attached this map. */
void AW_MwscriptRoomShift(float shift[3]){int i;for(i=0;i<3;i++)shift[i]=room_shift[i];}
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
static int topic_rows_now(void){return known_topics?topic_rows:0;}
/* The dialogue window learns a topic (a link in an answer or greeting): it joins the saved set (DIALOGUE-COMPLETE-58) */
void AW_MwscriptTopicLearn(int row);
void AW_MwscriptTopicLearn(int row){if(row>=0 && row<topic_rows && known_topics)known_topics[row>>3]|=(unsigned char)(1<<(row&7));}
/* The name hash of every TOPC row (aw_dial.c AW_DialNameHash) into OUT (at most MAX): the rows, 0 without the file's
 * topics; OUT NULL: only the number of rows. One open of the file; for the dialogue window's map from its topics to these rows, made once. */
int AW_MwscriptTopicHashes(unsigned long *out,int max);
/* DIALOGUE-OPEN-STALL-58: this read every topic's name with three seeks of its own (about 12 s for Morrowind.esm's
 * topics on the first conversation of a session, measured in FS-UAE at 32 MB Fast). Now three reads in a row: the
 * rows' string numbers, their string offsets (the slice between the lowest and the highest), the strings between the
 * first and the last of them; TOPIC_RUN bytes at most each, freed at once. Over that: the old row by row read. */
#define TOPIC_RUN (512L*1024L)
static int topic_hashes_bulk(FILE *f,long base,uint32_t off,uint32_t rows,unsigned long *out){
    uint32_t soff,srows,sbytes,r,first=0,last=0,at;unsigned char *ids=NULL,*offs=NULL,*text=NULL;
    int lo=-1,hi=-1,ok=0,s,n;long span;
    if(!AW_MwvmSection("STRS",&soff,&srows,&sbytes) || 2L*(long)rows>TOPIC_RUN ||
       !(ids=(unsigned char *)AW_TryMalloc(2*(size_t)rows)))return 0;
    if(fseek(f,base+(long)off,SEEK_SET) || fread(ids,1,2*(size_t)rows,f)!=2*(size_t)rows)goto done;
    for(r=0;r<rows;r++){s=(ids[2*r]<<8)|ids[2*r+1];if(lo<0 || s<lo)lo=s;if(s>hi)hi=s;}
    if(lo<0 || (uint32_t)hi>=srows || 4L*(hi-lo+1)>TOPIC_RUN || !(offs=(unsigned char *)AW_TryMalloc(4*(size_t)(hi-lo+1))) ||
       fseek(f,base+(long)soff+4L*lo,SEEK_SET) || fread(offs,1,4*(size_t)(hi-lo+1),f)!=4*(size_t)(hi-lo+1))goto done;
    for(r=0;r<rows;r++){
        s=(ids[2*r]<<8)|ids[2*r+1];at=rd_be32(offs+4*(s-lo));
        if(!r){first=last=at;}
        if(at<first)first=at;
        if(at>last)last=at;
    }
    span=(long)(last-first)+256;
    if(span>TOPIC_RUN || !(text=(unsigned char *)AW_TryMalloc((size_t)span+1)) ||
       fseek(f,base+(long)soff+4L*(long)srows+(long)first,SEEK_SET))goto done;
    span=(long)fread(text,1,(size_t)span,f);text[span]=0;
    for(r=0;r<rows;r++){
        const char *name;
        s=(ids[2*r]<<8)|ids[2*r+1];at=rd_be32(offs+4*(s-lo))-first;
        if((long)at>=span)goto done;
        name=(const char *)text+at;
        for(n=0;(long)at+n<span && name[n] && n<255;n++);
        out[r]=AW_DialNameHash(name,n);
    }
    ok=1;
done:
    free(ids);free(offs);free(text);
    return ok;
}
int AW_MwscriptTopicHashes(unsigned long *out,int max){
    FILE *f=NULL;long base;uint32_t off,rows,bytes,r;unsigned char id[2];char name[256];int n;
    if(!out)return known_topics?topic_rows:0;              /* the rows, for the caller's array */
    if(!known_topics || topic_rows<=0 || topic_rows>max || !AW_MwvmSection("TOPC",&off,&rows,&bytes) ||
       (int)rows!=topic_rows)return 0;
    if(COM_FOpenFile(FILE_NAME,&f)<=0 || !f){if(f)fclose(f);return 0;}
    base=ftell(f);
    if(!topic_hashes_bulk(f,base,off,rows,out))
        for(r=0;r<rows;r++){
            if(fseek(f,base+(long)off+2L*(long)r,SEEK_SET) || fread(id,1,2,f)!=2){fclose(f);return 0;}
            n=read_string_from(f,base,(id[0]<<8)|id[1],name,sizeof(name));
            out[r]=AW_DialNameHash(name,n);
        }
    fclose(f);
    return (int)rows;
}
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
/* RaiseRank (RAISE 1) / LowerRank on NPC record A (see AWF_RAISERANK below): the rank now, -1 nothing to change (no
 * NPC, the player, no faction, LowerRank at 0), -2 not kept */
static int npc_rank_change(aw_actor_t *a,int raise){
    aw_actor_base_t b;int now,rank;
    if(!aw_ledger_on || !a || a->reference==AW_ACTOR_PLAYER_REF || !AW_ActorBase(a->base,&b) || b.kind!=0 ||
       b.faction==AW_ACTOR_NONE)return -1;
    now=AW_LedgerRank(&aw_ledger,a->reference);
    if(raise)rank=(now>=0?now:b.rank)+1;
    else if(now==0)return -1;
    else rank=now>0?now-1:(b.rank-1>0?b.rank-1:0);
    if(rank>AW_LEDGER_RANK_TOP)rank=AW_LEDGER_RANK_TOP;
    return AW_LedgerRankSet(&aw_ledger,a->reference,rank)?rank:-2;
}
/* The rank the world change list keeps for the NPC of edict E (RaiseRank / LowerRank), -1 none: the dialogue's speaker
 * rank (aw_glut.c AW_GlutSpeaker) */
int AW_MwscriptNpcRank(edict_t *e);
int AW_MwscriptNpcRank(edict_t *e){
    eval_t *v;
    if(!e || e->free || !aw_ledger_on || !(v=GetEdictFieldValue(e,"aw_ref")) || v->_float<=0)return -1;
    return AW_LedgerRank(&aw_ledger,(uint32_t)v->_float);
}
/* the dialogue window's Choice and Goodbye (aw_dialwin.c sets it while a result script runs): TEXTS NULL = Goodbye */
void (*aw_dial_result_choice)(const char **texts,int ntexts,const aw_mwcell_t *numbers,int count);
void (*aw_dial_result_clear)(void);
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
    case AWF_RAISERANK:case AWF_LOWERRANK:{
        /* RaiseRank / LowerRank on an NPC (OpenMW 0.51 statsextensions.cpp OpRaiseRank, OpLowerRank): the NPC's rank in
         * its own faction; nothing on the player or a factionless NPC; a rank changed before goes on from there, else
         * from its record's; LowerRank stops at 0, RaiseRank has no top (the saved byte has: AW_LEDGER_RANK_TOP). Kept
         * on the world change list by the NPC's reference (CELL-CHANGES-59), saved; the dialogue reads it. */
        edict_t *e;aw_actor_t *a=target==AW_MWVM_PLAYER?NULL:actor_of(instance,target,&e);
        int r=npc_rank_change(a,function==AWF_RAISERANK);
        if(r==-2){Con_DPrintf("MWScript: an NPC rank not kept (list full)\n");return 0;}
        if(r<0){standing_misses++;return 1;}
        standing_calls++;AW_MwvmStateChanged();return 1;}
    case AWF_GETPCFACREP:case AWF_SETPCFACREP:case AWF_MODPCFACREP:
        faction=call_string(strings,nstrings,0);
        if(!faction)faction=actor_faction(instance,target,own,sizeof(own));
        standing_calls++;
        if(function==AWF_GETPCFACREP){result->i=faction?AW_StandingFactionReputation(faction):0;return AW_MWVM_CALL_READ;}
        if(!faction || count<1)return 1;
        AW_StandingSetFactionReputation(faction,function==AWF_SETPCFACREP?value:AW_StandingFactionReputation(faction)+value);
        AW_MwvmStateChanged();return 1;
    case AWF_MODFACTIONREACTION:case AWF_SETFACTIONREACTION:{
        /* ModFactionReaction / SetFactionReaction FACTION1 FACTION2 VALUE: faction 1's reaction toward faction 2 */
        const char *a=call_string(strings,nstrings,0),*b=call_string(strings,nstrings,1);
        if(!a || !b || count<1)return 0;
        if(!AW_DialReactionChange(a,b,numbers[count-1].i,function==AWF_SETFACTIONREACTION)){
            Con_DPrintf("MWScript: faction reaction changes are full (32); %s toward %s not kept\n",a,b);return 0;}
        AW_MwvmStateChanged();return 1;}
    case AWF_CLEARINFOACTOR:
        if(!aw_dial_result_clear)return 0;   /* outside a conversation: nothing */
        aw_dial_result_clear();return 1;
    case AWF_SHOWRESTMENU:
        /* ShowRestMenu on a bed (the bed's script, Bed_Standard): the rest window with that bed (REST-WAIT-59, aw_wait.c;
         * OpenMW OpShowRestMenu with sleepInBed); without a reference, the window as T opens it */
        AW_RestOpen((unsigned long)target_reference(instance,target));return 1;
    case AWF_GETPCSLEEP:result->f=(float)AW_RestSleeping();return AW_MWVM_CALL_READ;
    case AWF_SHOWMAP:{
        /* ShowMap TEXT: the exterior cells whose name holds TEXT become known on the map (OpenMW OpShowMap); kept
         * for the map's place markers (INGAME-MAP-ORIGINAL-57), which do not exist yet */
        const char *text=call_string(strings,nstrings,0);
        if(!text || !*text)return 0;
        if(!AW_RevealedAdd(text)){Con_DPrintf("MWScript: ShowMap %s not kept (128 places at most)\n",text);return 0;}
        AW_MwvmStateChanged();return 1;}
    case AWF_CHOICE:case AWF_GOODBYE:
        /* Choice and Goodbye in a dialogue result script (OpenMW dialogueextensions.cpp OpChoice, OpGoodbye): the
         * dialogue window shows the choices (each text with its number) or ends the conversation with Goodbye alone;
         * outside a conversation they do nothing */
        if(!aw_dial_result_choice)return 0;
        if(function==AWF_GOODBYE){aw_dial_result_choice(NULL,0,NULL,0);return 1;}
        {const char *texts[24];int k,n=0;
         for(k=0;k<nstrings && k<24;k++)texts[n++]=call_string(strings,nstrings,k);
         aw_dial_result_choice(texts,n,numbers,count);}
        return 1;
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
 * RankRequirement reads the factions' rank requirements from the dialogue table (aw_dialwin.c, FACTION-RANK-58). */
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
/* SameSex, SameRace and ShouldAttack (aw_dial.c AW_DialPairFunction): the speaker's record (an NPC) against the
 * player's sheet; ShouldAttack is the speaker's Fight rating toward the player with the condition's disposition (the
 * conversation's derived one), as the world's aggro works it out (aw_ambient.c). 0 when the speaker is not known. */
static int speaker_pair(const aw_glut_cond_t *c,unsigned fn,long *out){
    aw_dial_pair_t p;edict_t *e,*player;eval_t *v,*r;int row;aw_actor_base_t b;aw_actor_t *a;char race[64];
    memset(&p,0,sizeof(p));p.fight_rating=-1;
    if(!aw_character.valid || c->speaker<=0 || c->speaker>=sv.num_edicts || !AW_MwscriptActors())return 0;
    e=EDICT_NUM(c->speaker);
    if(e->free || !(v=GetEdictFieldValue(e,"aw_source_id")) || !v->string || (row=AW_ActorFind(pr_strings+v->string))<0 ||
       !AW_ActorBase(row,&b) || b.kind!=0)return 0;
    p.known=1;p.player_female=aw_character.female!=0;p.speaker_female=(b.flags&AWR_FEMALE)!=0;
    if(aw_character.race>=0 && aw_character.race<aw_race_count)p.player_race=aw_races[aw_character.race].id;
    if(b.race!=AW_ACTOR_NONE && read_string(b.race,race,sizeof(race)))p.speaker_race=race;
    if(fn==AW_DIAL_FN_SHOULD_ATTACK && AW_CombatAiLoaded() && svs.maxclients>0 && (player=svs.clients[0].edict)!=NULL){
        vec3_t d;int fight=b.fight;
        r=GetEdictFieldValue(e,"aw_ref");
        if(r && (a=AW_ActorGet((uint32_t)r->_float,row,0))!=NULL)fight=(int)AW_ActorStat(a,AWA_FIGHT);
        VectorSubtract(e->v.origin,player->v.origin,d);
        p.fight_rating=AW_CombatFightRating(&aw_combat_ai,fight,c->disposition,(float)Length(d)/AW_MOVE_UNIT_SCALE);
    }
    return AW_DialPairFunction(&p,fn,out);
}
/* SCVR function numbers (mwad.dialogue FUNCTIONS): the player's standing and the character's stats */
static int live_function(const aw_glut_cond_t *c,unsigned fn,long *out){
    if(fn==44 || fn==45 || fn==71)return speaker_pair(c,fn,out);        /* SameSex, SameRace, ShouldAttack */
    if(fn==5){*out=AW_StandingReputation();return 1;}                      /* PcReputation */
    if(fn==43){*out=AW_StandingCrime();return 1;}                          /* PcCrimeLevel */
    if(fn==39){*out=c->faction?AW_StandingExpelled(c->faction):0;return 1;} /* PcExpelled (the speaker's faction) */
    if(fn==46){*out=c->faction && AW_StandingRank(c->faction)>=0;return 1;} /* SameFaction */
    if(fn==2){                                                             /* RankRequirement (the speaker's faction) */
        *out=c->faction && aw_character.valid?AW_DialWindowRankRequirement(c->faction,AW_StandingRank(c->faction),
            aw_character.attributes,aw_character.skills,AW_StandingFactionReputation(c->faction)):0;
        return 1;}
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
/* a global by name: the globals' names read once (global_names_load, above). DIALOGUE-GLOBAL-NAMES-CLASH-59: this
 * had its own "static char *global_names" at file scope, which C makes the SAME variable as the one above, with
 * another layout (32 bytes per row against packed names): whichever read first, the other read wrong names. */
static int live_global(const char *name,float *out){
    int g,type=0;
    if(!AW_MwvmLoaded())return 0;
    global_names_load();
    for(g=0;global_names && global_offsets && g<global_count;g++)
        if(global_offsets[g]>=0 && same_id(global_names+global_offsets[g],name)){
            AW_MwvmGlobalName(g,&type);
            *out=type==2?AW_MwvmGlobalFloat(g):(float)AW_MwvmGlobalInt(g);return 1;}
    return 0;
}
/* The disposition's facts of a speaker (aw_dial.h aw_dial_facts_t; DIALOGUE-57): its own disposition from the actor
 * record (the scripts' SetDisposition and ModDisposition included) when the actor table has it, else BASE; same race,
 * the player's Personality, crime level, faction ranks, a disease (a common or a blight one in the player's spells,
 * OpenMW hasCommonDisease / hasBlightDisease) and a drawn weapon (the hands up without a torch: OpenMW's draw state
 * Weapon). Charm: the magnitude of a Charm effect on the NPC; no effect can land on an NPC before player casting
 * (PLAYER-CASTING-59), so it is 0 until then. */
static int standing_rank(const char *faction,int *expelled){*expelled=AW_StandingExpelled(faction);return AW_StandingRank(faction);}
static int player_diseased=-1;   /* the last read (a disk read: never on the engage tick), -1 not read yet */
static int disposition_diseased(int read){
    aw_actor_t *p;
    if(read && AW_MwscriptActors() && (p=AW_ActorPlayer())!=NULL)
        player_diseased=AW_ActorHasSpellType(p,2) || AW_ActorHasSpellType(p,3);
    return player_diseased>0;
}
static int disposition_weapon_drawn(void){
    edict_t *p;eval_t *goal,*torch;
    if(!sv.active || svs.maxclients<1 || !(p=svs.clients[0].edict))return 0;
    goal=GetEdictFieldValue(p,"aw_hand_goal");torch=GetEdictFieldValue(p,"aw_torch");
    return goal && goal->_float==1 && !(torch && torch->_float!=0);
}
static float disposition_charm(unsigned long reference){(void)reference;return 0;}
void AW_MwscriptDispositionFacts(const char *record,unsigned long reference,int base,const char *faction,aw_dial_facts_t *f){
    int row=-1;aw_actor_base_t b;aw_actor_t *a;char race[64];
    memset(f,0,sizeof(*f));
    f->base=base;f->faction=faction;f->rank=standing_rank;f->bounty=AW_StandingCrime();
    f->personality=aw_character.valid?(float)aw_character.attributes[6]:50.0f;
    f->diseased=disposition_diseased(1);f->weapon_drawn=disposition_weapon_drawn();f->charm=disposition_charm(reference);
    if(!AW_MwscriptActors() || !record || (row=AW_ActorFind(record))<0 || !AW_ActorBase(row,&b))return;
    if(reference && (a=AW_ActorGet((uint32_t)reference,row,0))!=NULL)f->base=(int)AW_ActorStat(disposition_restore(a),AWA_DISPOSITION);
    else f->base=disposition_kept(reference,f->base);
    if(aw_character.valid && b.race!=AW_ACTOR_NONE && read_string(b.race,race,sizeof(race)))
        f->same_race=same_id(race,aw_races[aw_character.race].id);
}
/* Persuasion (DIALOGUE-COMPLETE-58): the player's and the speaker's persuasion stats, the speaker's Fight and Flee;
 * the speaker's actor record (made when it has none yet: a persuasion changes it). 1 when the speaker's record is there. */
static aw_actor_t *speaker_actor(const char *record,unsigned long reference){
    int row;
    if(!AW_MwscriptActors() || !record || (row=AW_ActorFind(record))<0)return NULL;
    return disposition_restore(AW_ActorGet((uint32_t)reference,row,1));
}
int AW_MwscriptPersons(const char *record,unsigned long reference,aw_dial_person_t *player,aw_dial_person_t *npc,
                       int *fight,int *flee){
    aw_actor_t *a=speaker_actor(record,reference);aw_actor_base_t b;
    memset(player,0,sizeof(*player));memset(npc,0,sizeof(*npc));player->fatigue=npc->fatigue=1;*fight=*flee=0;
    if(aw_character.valid){
        player->personality=aw_character.attributes[6];player->luck=aw_character.attributes[7];
        player->speechcraft=aw_character.skills[25];player->mercantile=aw_character.skills[24];
        player->level=(float)aw_character.level;player->reputation=(float)AW_StandingReputation();
        player->fatigue=aw_character.maximum[2]>0?aw_character.current[2]/aw_character.maximum[2]:1;
    }
    if(!a || !AW_ActorBase(a->base,&b))return 0;
    npc->personality=AW_ActorStat(a,AWA_ATTRIBUTE+6);npc->luck=AW_ActorStat(a,AWA_ATTRIBUTE+7);
    npc->speechcraft=AW_ActorStat(a,AWA_SKILL+25);npc->mercantile=AW_ActorStat(a,AWA_SKILL+24);
    npc->level=AW_ActorStat(a,AWA_LEVEL);npc->reputation=(float)b.reputation;npc->fatigue=AW_ActorRatio(a,AWA_FATIGUE);
    *fight=(int)AW_ActorStat(a,AWA_FIGHT);*flee=(int)AW_ActorStat(a,AWA_FLEE);
    return 1;
}
/* DIALOGUE-RING-DISPOSITION-CHECK-60: the speaker's own (base) disposition now, from its actor record with the
 * scripts' changes in it (a result's ModDisposition / SetDisposition), else the world change list's, else FALLBACK;
 * and that value set (OpenMW DialogueManager writes it at every persuasion: NpcStats::setBaseDisposition). */
int AW_MwscriptSpeakerDisposition(const char *record,unsigned long reference,int fallback){
    int row;aw_actor_t *a;
    if(!AW_MwscriptActors() || !record || (row=AW_ActorFind(record))<0)return fallback;
    if(reference && (a=AW_ActorGet((uint32_t)reference,row,0))!=NULL)return (int)AW_ActorStat(disposition_restore(a),AWA_DISPOSITION);
    return disposition_kept(reference,fallback);
}
void AW_MwscriptSetSpeakerDisposition(const char *record,unsigned long reference,int disposition){
    aw_actor_t *a=speaker_actor(record,reference);
    if(!a)return;
    AW_ActorSetStat(a,AWA_DISPOSITION,(float)disposition);disposition_keep(a);
    AW_MwvmStateChanged();
}
/* The speaker's own disposition, Fight and Flee set (the actor record, saved with the game). */
void AW_MwscriptSetSpeaker(const char *record,unsigned long reference,int disposition,int fight,int flee){
    aw_actor_t *a=speaker_actor(record,reference);
    if(!a)return;
    if(disposition>=0){AW_ActorSetStat(a,AWA_DISPOSITION,(float)disposition);disposition_keep(a);}
    if(fight>=0)AW_ActorSetStat(a,AWA_FIGHT,(float)fight);
    if(flee>=0)AW_ActorSetStat(a,AWA_FLEE,(float)flee);
    AW_MwvmStateChanged();
}
/* The player's gold (the scripts' item count of gold_001), changed by DELTA first. */
int AW_MwscriptPlayerGold(int delta){
    long gold=AW_StateGet(&aw_state,AW_ITEM,"gold_001");
    if(delta){gold+=delta;if(gold<0)gold=0;AW_StateSet(&aw_state,AW_ITEM,"gold_001",(int32_t)gold);AW_MwvmStateChanged();}
    return (int)gold;
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
    load_failed=1;string_cache_clear();
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
    /* ARRIVAL-LONG-FRAME-DEV6-59: the topics' names from the string section read ONCE into memory (one seek, one
     * read); a name per seek refilled the 16 KB file buffer twice per topic, about 6.9 s of the first play frame */
    {uint32_t off,rows,bytes;unsigned char *strs=NULL;
     if(f && length>0 && AW_MwvmSection("STRS",&off,&rows,&bytes) && bytes>=4*rows && bytes<=(uint32_t)length &&
        (strs=(unsigned char *)AW_TryMalloc(bytes))!=NULL &&
        !fseek(f,base+(long)off,SEEK_SET) && fread(strs,1,bytes,f)==bytes){
         for(i=0;i<n;i++){
             int index=AW_MwvmTopicName(i),k=0;uint32_t at;
             name[0]=0;
             if(index>=0 && (uint32_t)index<rows){
                 const unsigned char *b=strs+4*index;
                 at=4*rows+(((uint32_t)b[0]<<24)|((uint32_t)b[1]<<16)|((uint32_t)b[2]<<8)|b[3]);
                 while(at<bytes && k<(int)sizeof(name)-1 && strs[at])name[k++]=(char)strs[at++];
                 name[k]=0;
             }
             topic_offsets[i]=64*i;topic_values[i]=0;strcpy(topic_names+64*i,name);
         }
         {   /* the first and last names checked against the per-name read (the section's bounds are right) */
             char check[64];int t,bad=0;
             for(t=0;t<n;t+=(n>1?n-1:1)){
                 if(!read_string_from(f,base,AW_MwvmTopicName(t),check,sizeof(check)))check[0]=0;
                 if(strcmp(check,topic_names+64*t))bad=1;
                 if(n<=1)break;
             }
             if(bad)Con_Printf("MWScript: the journal names read at once differ from the file's; read one by one.\n");
             else n=0;      /* done: the loop below has nothing left */
         }
         free(strs);
     }else if(strs)free(strs);}
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
    script_import(&aw_ledger);   /* slice 4: the session's list (a save loaded before the scripts came) */
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
/* A new map, with or without the scripts (PICKUP-E-OWNED-NO-TAKE-58: the taken items are object state too, so this
 * runs while the scripts are off or refused): the edicts by reference, and what was disabled or taken stays hidden. */
static void attach_objects(void){
    int i;edict_t *e;eval_t *v;
    edict_ref_count=0;
    for(i=1;i<sv.num_edicts && edict_ref_count<EDICT_REFS;i++){
        e=EDICT_NUM(i);if(e->free)continue;
        v=GetEdictFieldValue(e,"aw_ref");if(!v || v->_float<=0)continue;
        edict_refs[edict_ref_count].ref=(uint32_t)v->_float;edict_refs[edict_ref_count++].entity=i;
    }
    qsort(edict_refs,edict_ref_count,sizeof(edict_refs[0]),compare_refs);
    /* the object state: what a script disabled or the player took stays hidden on this map too */
    if(aw_ledger_on){ledger_attach();return;}      /* CELL-CHANGES-59: this map's rows of the world change list */
    for(i=0;i<object_count;i++)if(objects[i].disabled){objects[i].entity=-1;object_hide(&objects[i]);}
}
static void attach_map(void){
    FILE *f=NULL;int length,i,k,nroom=0,anchored=0;long base,room;uint32_t offset,rows,bytes,r;unsigned char row[24];
    vec3_t local,shift;float source[3];edict_t *e;int outdoors;
    AW_MwvmBeginMap();
    /* Room or outdoors: outdoors when the shared conversion (aw_world.c) knows this map, a region map or, since
     * CHIM-FRAME-SOURCE-CONVERSION-59, the loaded CHIM frame map (a streamed town counts as outdoors, its placements
     * and GetPCCell by the original's exterior cells); a room map (compiled or a CHIM room) has neither. */
    {float zero[3]={0,0,0};vec3_t at;    /* the player's cell: a room's number (its shift comes with the bindings) */
     map_room=AW_SourceToWorld(sv.name,zero,at)?0:map_cell_number();room_shift[0]=room_shift[1]=room_shift[2]=0;}
    for(i=0;i<LOOPS;i++)if(loops[i].used){S_StopSound(loops[i].entity,loops[i].channel);loops[i].used=0;}
    memset(says,0,sizeof(says));
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
/* TOMB-MUSIC-OVER-AMBIENT-60: a dungeon ambience loop (a tomb's Haunted or spirit voices, a cave's drip or wind) is
 * playing on this map: the exploration music rests (aw_music.c AW_MusicAmbience; battle music still plays). */
static int ambience_playing(void){
    int i;for(i=0;i<LOOPS;i++)if(loops[i].used && loops[i].looping && loops[i].ambience)return 1;
    return 0;
}
void AW_MwscriptTick(float dt){
    int k,n,i;vec3_t player;
    /* no game running (a load, the main menu): a script's message box goes with it */
    if(!sv.active || cls.signon!=SIGNONS || !sv_player){AW_MsgBoxClear();return;}
    if(sv.worldmodel!=map_model || strcmp(sv.name,map_name)){
        map_model=sv.worldmodel;Q_strcpy_bounded(map_name,sv.name,sizeof(map_name));
        attached_map++;attach_objects();script_model=NULL;   /* the count first: what attach hides belongs to this map */
    }
    if(!mwscript.value){AW_MsgBoxClear();AW_MusicAmbience(0);return;}
    {   /* ARRIVAL-LONG-FRAME-DEV6-59: the parts of a first tick that take long are named */
        double t0=Sys_FloatTime(),t1,t2;int was=resident!=NULL;
        if(!load())return;
        t1=Sys_FloatTime();
        if(script_model!=map_model){script_model=map_model;attach_map();}
        t2=Sys_FloatTime();
        if(t2-t0>.3)Con_Printf("MWScript first tick: file %s %.0f ms, map attach %.0f ms.\n",was?"kept":"loaded",
                               (t1-t0)*1000,(t2-t1)*1000);
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
    AW_MusicAmbience(ambience_playing());   /* one look at LOOPS slots a frame; the player acts only on a change */
    VectorCopy(sv_player->v.origin,player);
    player_cell_update();
    actors_from_fights();
    if(AW_EffectsCount()){   /* the player's active spell effects on the game clock (SPELL-EFFECTS-57) */
        aw_actor_t *p=player_record();
        if(p && AW_EffectsTick(p,dt)){player_store(p);AW_MwvmStateChanged();}
        npc_effects_tick(dt);   /* PLAYER-CASTING-59: the actors a spell landed on */
    }
    {double t0=Sys_FloatTime();
     AW_MwvmTick(dt,player);
     if(Sys_FloatTime()-t0>.3)Con_Printf("MWScript tick: %.0f ms (scripts run this frame).\n",(Sys_FloatTime()-t0)*1000);}
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
    AW_MwscriptLedgerStatus();
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
/* ACTOR-STATS-ALL-61: "aw_mwscript_status stats [on|off|ID]" (dbg mwscript stats): the area stats switch, or one
 * being's stats (the actor of record ID, else the one under the crosshair): what its record type holds, every stat by
 * the read rules, its spell rows, and its live record; then where the records came from and the last area load's fill */
static void stats_readout(void){
    char id[64];int argi,k,n=0,sp[AWS_SPELLS];edict_t *e=NULL;eval_t *v;aw_stat_block_t b;unsigned long c[3],m[2];
    int made,blocks;float ms;uint32_t ref=0;char line[1024];
    id[0]=0;
    if(Cmd_Argc()==3 && (!Q_strcasecmp(Cmd_Argv(2),"on") || !Q_strcasecmp(Cmd_Argv(2),"off"))){
        AW_ActorStatsSwitch(!Q_strcasecmp(Cmd_Argv(2),"on"));
        Con_Printf("dbg mwscript stats: area stats %s (new records; off: the actor table's rows)\n",
                   AW_ActorStatsSwitch(-1)?"on":"off");
        return;
    }
    for(argi=2;argi<Cmd_Argc();argi++){if(argi>2)strncat(id," ",sizeof(id)-strlen(id)-1);strncat(id,Cmd_Argv(argi),sizeof(id)-strlen(id)-1);}
    if(id[0]){
        for(argi=1;argi<sv.num_edicts && !e;argi++){
            edict_t *x=EDICT_NUM(argi);
            if(!x->free && (v=GetEdictFieldValue(x,"aw_source_id"))!=NULL && v->string && !Q_strcasecmp(pr_strings+v->string,id))e=x;
        }
    }else if(sv_player)e=AW_NPCTarget(sv_player,sv_player->v.v_angle);
    if(e && (v=GetEdictFieldValue(e,"aw_source_id"))!=NULL && v->string){strncpy(id,pr_strings+v->string,sizeof(id)-1);id[sizeof(id)-1]=0;}
    if(e && (v=GetEdictFieldValue(e,"aw_ref"))!=NULL && v->_float>0)ref=(uint32_t)v->_float;
    if(!id[0]){Con_Printf("dbg mwscript stats ID: no actor of that id here, and none under the crosshair\n");return;}
    if(!AW_AreaActorStats(ref,AW_StatIdHash(id),&b)){
        Con_Printf("dbg mwscript stats %s (ref %lu): not in the loaded areas' stats (the actor table's row is used)\n",
                   id,(unsigned long)ref);
    }else{
        static const char *const kinds[3]={"NPC with stored stats","auto-calculated NPC","creature"};
        Con_Printf("dbg mwscript stats %s (ref %lu): %s, present mask %u, level %d\n",id,(unsigned long)ref,
                   b.kind<3?kinds[b.kind]:"?",b.mask,b.level);
        line[0]=0;
        for(k=0;k<AWS_STATS;k++){
            const char *name=AW_StatName(k);char one[48];
            if(!name[0])continue;
            sprintf(one," %s%s=%d",AW_StatHas(&b,k)?"":"~",name,AW_StatRead(&b,k));
            if(strlen(line)+strlen(one)>=sizeof(line)-1){Con_Printf("  record:%s\n",line);line[0]=0;}
            strcat(line,one);
        }
        if(line[0])Con_Printf("  record:%s\n",line);
        n=AW_StatSpells(&b,sp,AWS_SPELLS);
        line[0]=0;
        for(k=0;k<n && strlen(line)<sizeof(line)-8;k++)sprintf(line+strlen(line)," %d",sp[k]);
        Con_Printf("  spells and abilities (ASPT rows, %d of them the race's):%s\n",b.race_spells,n?line:" none");
    }
    if(ref && AW_MwscriptActors()){
        aw_actor_t *a=AW_ActorGet(ref,AW_ACTOR_NONE,0);
        if(a){
            line[0]=0;
            for(k=0;k<AWA_STATS-2;k++)sprintf(line+strlen(line)," %d",(int)AW_ActorStat(a,k));
            Con_Printf("  live record (attributes, skills, health, magicka, fatigue, level, hello, fight, flee, alarm, "
                       "disposition):%s\n",line);
        }else Con_Printf("  live record: none yet\n");
    }
    AW_AreaActorStatsCounts(c);AW_ActorStatsCounts(m);AW_AreaActorFill(&made,&blocks,&ms);
    Con_Printf("  area stats %s; found direct %lu, by id %lu, not found %lu; records from area stats %lu, from the "
               "actor table %lu; combat sheets from the stats %lu; last area load: %d of %d records, load step %.2f ms, "
               "worst staggered frame %.2f ms\n",AW_ActorStatsSwitch(-1)?"on":"off",c[0],c[1],c[2],m[0],m[1],
               combat_sheets_from_stats,made,blocks,ms,AW_AreaActorFillWorstFrame());
}
static void status(void){
    char *a=Cmd_Argc()>1?Cmd_Argv(1):"";int k,on=-1;
    if(!Q_strcasecmp(a,"on") || !Q_strcasecmp(a,"true") || !Q_strcasecmp(a,"yes") || !strcmp(a,"1"))on=1;
    else if(!Q_strcasecmp(a,"off") || !Q_strcasecmp(a,"false") || !Q_strcasecmp(a,"no") || !strcmp(a,"0"))on=0;
    if(!Q_strcasecmp(a,"stats")){stats_readout();return;}
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
        if(!Q_strcasecmp(f,"journal") || !Q_strcasecmp(f,"setjournalindex")){
            /* "call journal QUEST INDEX": a script's Journal (the dated entry, the notice; a lower index is ignored);
             * "call setjournalindex QUEST INDEX": SetJournalIndex (the index alone, no entry) */
            int advance=!Q_strcasecmp(f,"journal");
            int t,quests=load()?AW_MwvmTopicCount():0,found=-1;
            for(t=0;Cmd_Argc()>3 && t<quests && found<0;t++)if(topic_names && same_id(topic_names+topic_offsets[t],Cmd_Argv(3)))found=t;
            if(found<0){Con_Printf("dbg mwscript call journal QUEST [INDEX]: no such quest (the file must be loaded)\n");return;}
            if(Cmd_Argc()>4){host_journal_set(found,atoi(Cmd_Argv(4)),advance);AW_MwvmStateChanged();}   /* no INDEX: read it */
            Con_Printf("dbg mwscript call journal: %s %ld\n",topic_names+topic_offsets[found],(long)host_journal_get(found));
            return;
        }
        if(!Q_strcasecmp(f,"raiserank") || !Q_strcasecmp(f,"lowerrank")){
            /* the NPC under the crosshair, as a script's RaiseRank / LowerRank on it (DIALOGUE-COMPLETE-58) */
            edict_t *e=sv_player?AW_NPCTarget(sv_player,sv_player->v.v_angle):NULL;eval_t *v;aw_actor_t *npc=NULL;int row,now;
            if(e && AW_MwscriptActors() && (v=GetEdictFieldValue(e,"aw_ref"))!=NULL && v->_float>0 &&
               (row=row_of_edict(e))!=AW_ACTOR_NONE)npc=AW_ActorGet((uint32_t)v->_float,row,1);
            now=npc_rank_change(npc,!Q_strcasecmp(f,"raiserank"));
            if(now>=0)AW_MwvmStateChanged();
            Con_Printf("dbg mwscript call %s: %s, rank %s%d\n",f,e?pr_strings+e->v.netname:"no actor under the crosshair",
                       now>=0?"now ":"unchanged ",now>=0?now:AW_MwscriptNpcRank(e));
            return;
        }
        if(!Q_strcasecmp(f,"setdisposition") || !Q_strcasecmp(f,"moddisposition") || !Q_strcasecmp(f,"getdisposition")){
            /* the NPC under the crosshair, as a script's SetDisposition / ModDisposition N (CELL-CHANGES-59 slice 4) */
            edict_t *e=sv_player?AW_NPCTarget(sv_player,sv_player->v.v_angle):NULL;eval_t *v;aw_actor_t *npc=NULL;int row;
            if(Cmd_Argc()>4){   /* or the actor of that record id after N ("call setdisposition 70 fargoth") */
                char id[64];int argi;id[0]=0;
                for(argi=4;argi<Cmd_Argc();argi++){if(argi>4)strncat(id," ",sizeof(id)-strlen(id)-1);strncat(id,Cmd_Argv(argi),sizeof(id)-strlen(id)-1);}
                e=NULL;
                for(argi=1;argi<sv.num_edicts && !e;argi++){
                    edict_t *x=EDICT_NUM(argi);eval_t *s;
                    if(!x->free && (s=GetEdictFieldValue(x,"aw_source_id"))!=NULL && s->string && !Q_strcasecmp(pr_strings+s->string,id))e=x;
                }
            }
            if(e && AW_MwscriptActors() && (v=GetEdictFieldValue(e,"aw_ref"))!=NULL && v->_float>0 &&
               (row=row_of_edict(e))!=AW_ACTOR_NONE)npc=disposition_restore(AW_ActorGet((uint32_t)v->_float,row,1));
            if(npc && Cmd_Argc()>3 && Q_strcasecmp(f,"getdisposition")){
                if(!Q_strcasecmp(f,"setdisposition"))AW_ActorSetStat(npc,AWA_DISPOSITION,(float)atoi(Cmd_Argv(3)));
                else AW_ActorModStat(npc,AWA_DISPOSITION,(float)atoi(Cmd_Argv(3)));
                disposition_keep(npc);AW_MwvmStateChanged();
            }
            Con_Printf("dbg mwscript call %s: %s (ref %lu), disposition %d\n",f,e?pr_strings+e->v.netname:"no actor under the crosshair",
                       npc?(unsigned long)npc->reference:0ul,npc?(int)AW_ActorStat(npc,AWA_DISPOSITION):-1);
            return;
        }
        if(!Q_strcasecmp(f,"setglobal") || !Q_strcasecmp(f,"getglobal")){
            /* "call setglobal NAME VALUE" / "call getglobal NAME": a global by its id, as a script's Set / Get */
            int g,type=0,found=-1;
            if(load() && Cmd_Argc()>3){
                global_names_load();
                for(g=0;global_names && global_offsets && g<global_count && found<0;g++)
                    if(global_offsets[g]>=0 && same_id(global_names+global_offsets[g],Cmd_Argv(3)))found=g;
            }
            if(found<0){Con_Printf("dbg mwscript call %s NAME [VALUE]: no such global (the file must be loaded)\n",f);return;}
            AW_MwvmGlobalName(found,&type);
            if(!Q_strcasecmp(f,"setglobal") && Cmd_Argc()>4){
                aw_mwcell_t c;
                if(type==2)c.f=(float)Q_atof(Cmd_Argv(4));else c.i=atoi(Cmd_Argv(4));
                AW_MwvmGlobalSetBits(found,(uint32_t)c.i);
            }
            Con_Printf("dbg mwscript call %s: %s = %g (data start %s)\n",f,global_names+global_offsets[found],
                       type==2?(double)AW_MwvmGlobalFloat(found):(double)AW_MwvmGlobalInt(found),
                       AW_MwvmGlobalBits(found)==AW_MwvmGlobalStart(found)?"same":"changed");
            return;
        }
        if(!Q_strcasecmp(f,"setlocal") || !Q_strcasecmp(f,"getlocal")){
            /* CELL-CHANGES-59 slice 5: "call setlocal VALUE [REF]" sets local 0 of REF's script (no REF: the first object
             * attached to this map whose script has a local; remembered), "call getlocal [REF]" reads it, as a
             * script's "set REF.local to VALUE" */
            static uint32_t last_ref;uint32_t ref=0;int argi=!Q_strcasecmp(f,"setlocal")?4:3,script=-1,j;aw_mwcell_t v;
            char name[64];
            if(!load()){Con_Printf("dbg mwscript call %s: the scripts are not loaded\n",f);return;}
            if(Cmd_Argc()>argi)ref=(uint32_t)strtoul(Cmd_Argv(argi),NULL,10);
            else if(argi==3)ref=last_ref;
            for(j=0;!ref && j<AW_MwvmInstanceCount();j++){
                aw_mwvm_instance_t *in=AW_MwvmInstance(j);
                if(in && (in->flags&(AWI_USED|AWI_GLOBAL))==AWI_USED && in->reference && AW_MwvmLocalCount(in->script)>0)
                    ref=in->reference;
            }
            if(!ref || !AW_MwvmLocalGet(ref,0,&script,&v)){
                Con_Printf("dbg mwscript call %s: no script local on reference %lu\n",f,(unsigned long)ref);return;}
            last_ref=ref;
            if(argi==4 && Cmd_Argc()>3){AW_MwvmLocalSet(ref,script,0,(uint32_t)atoi(Cmd_Argv(3)));AW_MwvmLocalGet(ref,0,&script,&v);}
            read_string(AW_MwvmScriptName(script),name,sizeof(name));
            Con_Printf("dbg mwscript call %s: ref %lu script %s (row %d, %d locals), local 0 = %ld (%g)\n",f,
                       (unsigned long)ref,name,script,AW_MwvmLocalCount(script),(long)v.i,(double)v.f);
            return;
        }
        if(!Q_strcasecmp(f,"startscript") || !Q_strcasecmp(f,"stopscript") || !Q_strcasecmp(f,"scriptrunning") ||
           !Q_strcasecmp(f,"globallocal")){
            /* "call startscript ROW" / "stopscript ROW" / "scriptrunning ROW", as a script's StartScript / StopScript /
             * ScriptRunning on the script of that row; "call globallocal ROW [VALUE]": its local 0 */
            int s=Cmd_Argc()>3?atoi(Cmd_Argv(3)):-1;char name[64];
            if(!load() || s<0 || s>=AW_MwvmScriptCount()){Con_Printf("dbg mwscript call %s ROW: no such script row\n",f);return;}
            if(!Q_strcasecmp(f,"startscript") || !Q_strcasecmp(f,"stopscript")){
                AW_MwvmGlobalScriptSet(s,!Q_strcasecmp(f,"startscript"));AW_MwvmStateChanged();}
            if(!Q_strcasecmp(f,"globallocal") && Cmd_Argc()>4)AW_MwvmGlobalScriptLocal(s,0,(uint32_t)atoi(Cmd_Argv(4)));
            read_string(AW_MwvmScriptName(s),name,sizeof(name));
            {int j,local=0;
             for(j=0;j<AW_MwvmInstanceCount();j++){aw_mwvm_instance_t *in=AW_MwvmInstance(j);
                 if(in && (in->flags&AWI_GLOBAL) && !in->reference && in->script==s && AW_MwvmLocalCount(s)>0)local=(int)AW_MwvmLocal(j,0).i;}
             Con_Printf("dbg mwscript call %s: %s (row %d, %d locals, start script %s): %s, local 0 = %d\n",f,name,s,
                        AW_MwvmLocalCount(s),AW_MwvmStartsAtLoad(s)?"yes":"no",AW_MwvmScriptRunning(s)?"running":"not running",local);}
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
/* CELL-CHANGES-59 slice 4: the scripts' globals (only those that differ from the data), every quest's stage and the
 * topics the player knows, written into the world change list's tables before a save and read back after a load
 * (OpenMW 0.51 globals.cpp, journalimp.cpp, dialoguemanagerimp.cpp: kept by record id; our own code). Topics by
 * the name hash of their TOPC row, read from disk on demand (no resident copy), so a rebuilt topic table in another
 * order keeps them. */
static unsigned long script_refused;
static int fact_get(const char *id,int32_t *out){return AW_LedgerFact(&aw_ledger,id,out);}
static int fact_set(const char *id,int32_t value){return AW_LedgerFactSet(&aw_ledger,id,value);}
static uint32_t topic_key(unsigned long h){uint32_t k=(uint32_t)(h&0xFFFFFFFFul);return k?k:1u;}
/* the rows' name hashes, read from disk once per loaded file and kept (4 bytes a row: 2,098 rows = 8.4 KB), so a save
 * or a load does not read the file again (the emulator's disk stall, CHIM-SEYDA-BALMORA-LOAD-HANG-43) */
static uint32_t *topic_hash_cache;static int topic_hash_rows;
static const uint32_t *topic_hash_table(void){
    unsigned long *h;int i;
    if(!known_topics || topic_rows<=0)return NULL;
    if(topic_hash_cache && topic_hash_rows==topic_rows)return topic_hash_cache;
    free(topic_hash_cache);topic_hash_cache=NULL;topic_hash_rows=0;
    if(!(h=(unsigned long *)AW_TryMalloc(sizeof(unsigned long)*(size_t)topic_rows)))return NULL;
    if(AW_MwscriptTopicHashes(h,topic_rows)==topic_rows &&
       (topic_hash_cache=(uint32_t *)AW_TryMalloc(sizeof(uint32_t)*(size_t)topic_rows))!=NULL){
        for(i=0;i<topic_rows;i++)topic_hash_cache[i]=topic_key(h[i]);
        topic_hash_rows=topic_rows;
    }
    free(h);
    return topic_hash_cache;
}
/* CELL-CHANGES-59 slice 5: the scripts' locals and the running global scripts on the list (OpenMW 0.51 livecellref.cpp,
 * locals.cpp, globalscripts.cpp: a reference's locals are part of its saved state; a global script is saved with its
 * running state and locals; our own code). Scripts by the name hash of their id, with their row as a hint: the name of
 * a row is read from disk once per session and kept (SCRIPT_NAMES rows at most, 8 bytes each), so a save or a load reads
 * only the names of the scripts it has not met yet. */
#define SCRIPT_NAMES 2048
AW_RESIDENT_GROWS("script name hashes met (CELL-CHANGES-59)",SCRIPT_NAMES,8);
typedef struct {uint32_t hash;uint16_t script;} script_name_t;
static script_name_t *script_names;static int script_name_count,script_name_capacity;
static FILE *script_names_file;static long script_names_base;
static uint32_t script_hash(int script){
    int lo=0,hi=script_name_count,n;char name[64];uint32_t h;
    if(script<0 || script>=AW_MwvmScriptCount())return 0;
    while(lo<hi){int mid=(lo+hi)/2;if((int)script_names[mid].script<script)lo=mid+1;else hi=mid;}
    if(lo<script_name_count && (int)script_names[lo].script==script)return script_names[lo].hash;
    if(!script_names_file){
        if(COM_FOpenFile(FILE_NAME,&script_names_file)<=0 || !script_names_file){
            if(script_names_file)fclose(script_names_file);
            script_names_file=NULL;return 0;}
        script_names_base=ftell(script_names_file);
    }
    n=read_string_from(script_names_file,script_names_base,AW_MwvmScriptName(script),name,sizeof(name));
    if(n<=0)return 0;
    h=AW_LedgerNameHash(name);
    if(script_name_count==script_name_capacity && script_name_capacity<SCRIPT_NAMES){
        int want=script_name_capacity?script_name_capacity*2:64;script_name_t *grown;
        if(want>SCRIPT_NAMES)want=SCRIPT_NAMES;
        if((grown=(script_name_t *)AW_TryRealloc(script_names,(unsigned long)want*sizeof(script_name_t)))!=NULL){
            script_names=grown;script_name_capacity=want;}
    }
    if(script_name_count<script_name_capacity){
        memmove(&script_names[lo+1],&script_names[lo],(size_t)(script_name_count-lo)*sizeof(script_name_t));
        script_names[lo].hash=h;script_names[lo].script=(uint16_t)script;script_name_count++;
    }
    return h;
}
static void script_names_done(void){if(script_names_file){fclose(script_names_file);script_names_file=NULL;}}
/* one instance's values onto the list (only those that differ from 0, the start) */
static void locals_put(void *user,uint32_t reference,int script,int global,int running,const aw_mwcell_t *cells,int count){
    aw_ledger_t *l=(aw_ledger_t *)user;int i;uint32_t h=0;
    if(global && running!=AW_MwvmStartsAtLoad(script)){
        if(!(h=script_hash(script)) || !AW_LedgerScriptSet(l,h,script,running))locals_refused++;
    }
    for(i=0;i<count;i++){
        if(!cells[i].i)continue;
        if(!h && !(h=script_hash(script))){locals_refused++;return;}
        if(AW_LedgerLocalSet(l,global,global?h:reference,h,script,i,cells[i].i))locals_kept++;else locals_refused++;
    }
}
static void locals_export(aw_ledger_t *l){
    locals_kept=locals_refused=0;
    AW_LedgerLocalsClear(l);
    AW_MwvmLocalsEach(locals_put,l);
    script_names_done();
}
/* the row of a kept script: its hint when that row still has the name, else -1 (a rebuilt file in another order) */
static int script_row(uint32_t hash,int hint){return script_hash(hint)==hash?hint:-1;}
static void locals_import(const aw_ledger_t *l){
    int i,s;
    locals_dropped=0;
    AW_MwvmLocalsReset();      /* a new game's start; then what the list keeps (an older save: nothing) */
    for(i=0;i<l->script_count;i++){
        const aw_ledger_script_t *x=&l->script[i];
        if((s=script_row(x->script,x->hint))<0 || !AW_MwvmGlobalScriptSet(s,x->running))locals_dropped++;
    }
    for(i=0;i<l->local_count;i++){
        const aw_ledger_local_t *x=&l->local[i];
        if((s=script_row(x->script,x->hint))<0 ||
           !(x->global?AW_MwvmGlobalScriptLocal(s,x->slot,(uint32_t)x->value):
                       AW_MwvmLocalSet(x->key,s,x->slot,(uint32_t)x->value)))locals_dropped++;
    }
    script_names_done();
}
/* CELL-CHANGES-59 slice 6 (ACTOR-STATE-POOL-LIMITS-54): the changed actor records go into the world change list as
 * its RECORDS part ("AWAR"), held only until the save is written; the actor block keeps the dead counts. */
static void actor_records_export(aw_ledger_t *l){
    int need=AW_ActorStateReady()?AW_ActorStateExportRecords(NULL,0):0;unsigned char *b;
    AW_LedgerRecordsSet(l,NULL,0);
    if(need<=0)return;
    if(need>AW_LEDGER_RECORDS_MAX || !(b=(unsigned char *)AW_TryMalloc((unsigned long)need)) ){
        Con_Printf("Saved actor records: %d bytes do not fit; changed actors start from the game data at a load.\n",need);
        return;}
    if(AW_ActorStateExportRecords(b,need)!=need || !AW_LedgerRecordsSet(l,b,need))
        Con_Printf("Saved actor records could not be kept; changed actors start from the game data at a load.\n");
    free(b);
}
static void script_export(aw_ledger_t *l){
    int g,i,n;const uint32_t *h;
    actor_records_export(l);
    if(!resident || !AW_MwvmLoaded())return;     /* not loaded: the tables stay as the last load left them */
    locals_export(l);
    AW_LedgerValueClear(l,AW_LEDGER_GLOBALS);AW_LedgerValueClear(l,AW_LEDGER_QUESTS);
    global_names_load();
    for(g=0;g<AW_MwvmGlobalCount();g++){
        uint32_t now=AW_MwvmGlobalBits(g);
        if(now==AW_MwvmGlobalStart(g))continue;
        if(!global_names || !global_offsets || global_offsets[g]<0 ||
           !AW_LedgerValueSet(l,AW_LEDGER_GLOBALS,AW_LedgerNameHash(global_names+global_offsets[g]),(int32_t)now))script_refused++;
    }
    n=AW_MwvmTopicCount();
    for(i=0;topic_values && i<n;i++){
        int32_t v=host_journal_get(i);
        if(v && (!topic_names[topic_offsets[i]] ||
                 !AW_LedgerValueSet(l,AW_LEDGER_QUESTS,AW_LedgerNameHash(topic_names+topic_offsets[i]),v)))script_refused++;
    }
    if((h=topic_hash_table())!=NULL){      /* the file unreadable: the topics as last loaded stay */
        AW_LedgerValueClear(l,AW_LEDGER_TOPICS);
        for(i=0;i<topic_rows;i++)
            if(AW_MwscriptTopicKnown(i) && !AW_LedgerValueSet(l,AW_LEDGER_TOPICS,h[i],1))script_refused++;
    }
}
static void script_import(const aw_ledger_t *l){
    int g,i,n;int32_t v;const uint32_t *h;
    /* slice 6: the changed actor records of the save (after the actor block's dead counts and any records an older
     * save had there), then the bytes go */
    if(l->records_bytes){
        if(AW_MwscriptActors() && !AW_ActorStateImportRecords(l->records,l->records_bytes))
            Con_Printf("Saved actor records unreadable: changed actors start from the game data.\n");
        AW_LedgerRecordsSet((aw_ledger_t *)l,NULL,0);
    }
    if(!resident || !AW_MwvmLoaded())return;     /* load() applies the list when the scripts come */
    global_names_load();
    for(g=0;g<AW_MwvmGlobalCount();g++){
        uint32_t bits=AW_MwvmGlobalStart(g);
        if(global_names && global_offsets && global_offsets[g]>=0 &&
           AW_LedgerValue(l,AW_LEDGER_GLOBALS,AW_LedgerNameHash(global_names+global_offsets[g]),&v))bits=(uint32_t)v;
        AW_MwvmGlobalSetBits(g,bits);
    }
    n=AW_MwvmTopicCount();
    for(i=0;topic_values && i<n;i++){
        int32_t story=AW_StateGet(&aw_state,AW_JOURNAL,topic_names+topic_offsets[i]);
        topic_values[i]=AW_LedgerValue(l,AW_LEDGER_QUESTS,AW_LedgerNameHash(topic_names+topic_offsets[i]),&v)?v:0;
        if(story>topic_values[i])topic_values[i]=story;   /* an older save's 32-slot journal, migrated */
    }
    if(l->value_count[AW_LEDGER_TOPICS] && (h=topic_hash_table())!=NULL){   /* else the actor block's AWKT stands */
        memset(known_topics,0,(size_t)topic_bytes);
        for(i=0;i<topic_rows;i++)if(AW_LedgerValue(l,AW_LEDGER_TOPICS,h[i],NULL))AW_MwscriptTopicLearn(i);
    }
    locals_import(l);
    AW_MwvmStateChanged();
}
static void put_u32(unsigned char *p,unsigned long v){p[0]=(unsigned char)(v>>24);p[1]=(unsigned char)(v>>16);p[2]=(unsigned char)(v>>8);p[3]=(unsigned char)v;}
static int actors_export(unsigned char *out,int capacity){
    /* slice 6: the dead counts only; the changed records are in the world change list (actor_records_export) */
    int n=AW_ActorStateReady()?AW_ActorStateExportCounts(out,capacity):0,s,t;
    if(n<0)return n;
    if((s=AW_StandingExport(out+n,capacity-n))<0)return -1;
    t=6+topic_bytes;
    if(n+s+t+8>capacity)return -1;
    memcpy(out+n+s,"AWKT",4);out[n+s+4]=(unsigned char)(topic_rows>>8);out[n+s+5]=(unsigned char)topic_rows;
    if(topic_bytes)memcpy(out+n+s+6,known_topics,topic_bytes);
    {int f=AW_EffectsExport(out+n+s+t,capacity-n-s-t-8);   /* the active spell effects (SPELL-EFFECTS-57) */
     if(f<0)return -1;
     t+=f;}
    {int k=AW_SoldExport(out+n+s+t,capacity-n-s-t-8);   /* things sold to merchants (AWSL, BARTER-SOLD-ITEM-LOST-58) */
     if(k<0)return -1;
     t+=k;
     k=AW_MadeExport(out+n+s+t,capacity-n-s-t-8);           /* made spells and enchanted items (AWMD, AWEN) */
     if(k<0)return -1;
     t+=k;
     k=AW_GemsExport(out+n+s+t,capacity-n-s-t-8);           /* filled soul gems (AWSG) */
     if(k<0)return -1;
     t+=k;
     k=AW_DialReactionsExport(out+n+s+t,capacity-n-s-t-8);  /* the scripts' faction reaction changes (AWFR) */
     if(k<0)return -1;
     t+=k;
     k=AW_RevealedExport(out+n+s+t,capacity-n-s-t-8);       /* places revealed by ShowMap (AWMP) */
     if(k<0)return -1;
     t+=k;
     k=AW_DialHeardExport(out+n+s+t,capacity-n-s-t-8);       /* the journal's topic pages (AWTP) */
     if(k<0)return -1;
     t+=k;}
    if(aw_mwscript_packages_export){   /* the actors' travel and follow packages (aw_ambient.c, SAVEGAME-COMPLETE-57) */
        int k=aw_mwscript_packages_export(out+n+s+t,capacity-n-s-t-8);
        if(k<0)return -1;
        t+=k;}
    put_u32(out+n+s+t,(unsigned long)(s+t));memcpy(out+n+s+t+4,"AWTR",4);
    return n+s+t+8;
}
static void actors_import(const unsigned char *data,int bytes){
    int actors=bytes;
    AW_StandingReset();AW_EffectsReset();AW_SoldReset();AW_MadeReset();AW_GemsReset();AW_DialReactionsReset();AW_RevealedReset();AW_DialHeardReset();
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
                /* slice 7: a save of other game data keeps its topics by name only (the list's TOPICS), never by row */
                if(aw_save_migrating)Con_Printf("Saved topic bits by row left out: the save is of other game data.\n");
                else if(rows==topic_rows && (unsigned long)(s+6+nb)<=tail && nb==topic_bytes){if(nb)memcpy(known_topics,p+s+6,nb);}
                else Con_Printf("Saved topics belong to other game data: none known.\n");
                rest=(unsigned long)(s+6+nb);
                /* the active spell effects after it (v0.0.57; a save without them: none active), then the actors'
                 * travel and follow packages (AWPK; a save without them: none) */
                if(rest+6<=tail && !memcmp(p+rest,"AWEF",4)){
                    /* SAVE-EFFECTS-BLOCK-SIZE-61: 10 bytes an effect in a version 1 block (v0.0.57), 16 in version 2
                     * (v0.0.61); read as 10, every save with an effect active lost its effects and the blocks after */
                    int fx=AW_EffectsBlockBytes(p+rest,tail-rest);
                    if(fx<0 || !AW_EffectsImport(p+rest,fx))Con_Printf("Saved spell effects unreadable: none active.\n");
                    else rest+=(unsigned long)fx;
                }
                if(rest+6<=tail && !memcmp(p+rest,"AWSL",4)){   /* things sold to merchants (v0.0.58) */
                    int k=AW_SoldImport(p+rest,(int)(tail-rest));
                    if(k<0)Con_Printf("Saved merchants' bought things unreadable: none kept.\n");else rest+=(unsigned long)k;
                }
                if(rest+10<=tail && !memcmp(p+rest,"AWMD",4)){   /* made spells and enchanted items (v0.0.58) */
                    int k=AW_MadeImport(p+rest,(int)(tail-rest));
                    if(k<0)Con_Printf("Saved made spells and enchanted items unreadable: none kept.\n");else rest+=(unsigned long)k;
                }
                if(rest+5<=tail && !memcmp(p+rest,"AWSG",4)){   /* filled soul gems (v0.0.58) */
                    int k=AW_GemsImport(p+rest,(int)(tail-rest));
                    if(k<0)Con_Printf("Saved soul gems unreadable: none filled.\n");else rest+=(unsigned long)k;
                }
                if(rest+5<=tail && !memcmp(p+rest,"AWFR",4)){   /* faction reaction changes (v0.0.58) */
                    int k=AW_DialReactionsImport(p+rest,(int)(tail-rest));
                    if(k<0)Con_Printf("Saved faction reactions unreadable: the game's own.\n");else rest+=(unsigned long)k;
                }
                if(rest+5<=tail && !memcmp(p+rest,"AWMP",4)){   /* places revealed by ShowMap (v0.0.58) */
                    int k=AW_RevealedImport(p+rest,(int)(tail-rest));
                    if(k<0)Con_Printf("Saved revealed places unreadable: none kept.\n");else rest+=(unsigned long)k;
                }
                if(rest+8<=tail && !memcmp(p+rest,"AWTP",4)){   /* the journal's topic pages (v0.0.58) */
                    int k=AW_DialHeardImport(p+rest,(int)(tail-rest));
                    if(k<0)Con_Printf("Saved journal topic pages unreadable: none kept.\n");else rest+=(unsigned long)k;
                }
                if(rest+6<=tail && !memcmp(p+rest,"AWPK",4) && aw_mwscript_packages_import &&
                   !aw_mwscript_packages_import(p+rest,(int)(tail-rest)))Con_Printf("Saved actor packages unreadable: none kept.\n");
            }
        }
    }
    if(!AW_MwscriptActors())return;
    if(!AW_ActorStateImport(data,actors))Con_Printf("Saved actor records unreadable: actors start from the game data.\n");
}
/* CELL-CHANGES-59 slice 7: the save's hooks for respawn and migration (aw_save.h) */
static int save_other_ok(void){return AW_PlacedRefs()!=NULL;}
static void save_ident_refresh(aw_ledger_t *l){AW_PlacedIdentRefresh(l);}
static long save_migrate(aw_ledger_t *l,void *dropped){return AW_PlacedMigrate(l,dropped);}
static int save_drop_actor_records(void){return AW_ActorStateReady()?AW_ActorStateDropAll():0;}
extern uint32_t (*aw_actors_ref_flags)(uint32_t key,aw_ledger_respawn_t *rule);
extern int (*aw_actors_forget)(uint32_t reference);
static void save_notice(const char *line){AW_UISubtitle("",line,8);}
static uint32_t actors_ref_flags(uint32_t key,aw_ledger_respawn_t *rule){
    aw_refs_t *r=AW_PlacedRefs();
    if(r && rule)*rule=r->respawn;
    return AW_PlacedRefFlags(key);
}
static int crime_witness(edict_t *e,aw_crime_witness_t *w);
static int crime_attack(edict_t *e,int fight);
static void crime_thief(aw_crime_thief_t *t);
void AW_MwscriptInit(void){
    Cvar_RegisterVariable(&mwscript);
    stats_hooks();
    aw_actors_ref_flags=actors_ref_flags;aw_actors_forget=AW_ActorForget;aw_save_notice=save_notice;
    aw_save_other_ok=save_other_ok;aw_save_ident_refresh=save_ident_refresh;aw_save_migrate=save_migrate;
    aw_save_drop_actor_records=save_drop_actor_records;
    AW_StandingReset();AW_EffectsReset();
    aw_save_actors_export=actors_export;aw_save_actors_import=actors_import;   /* the actor record (feature 16) */
    aw_save_objects_export=objects_export;aw_save_objects_import=objects_import;
    aw_save_script_export=script_export;aw_save_script_import=script_import;   /* CELL-CHANGES-59 slice 4 */
    aw_state_fact_get=fact_get;aw_state_fact_set=fact_set;   /* named globals past 32: the list's facts (slice 4) */
    aw_object_lock_level=AW_ObjectLockLevel;   /* the doors read a script's Lock and Unlock */
    aw_object_lock=AW_ObjectLock;aw_door_open=door_open;   /* CELL-CHANGES-59 slice 2: the key's unlock, door poses */
    aw_scene_intercept=aw_hinged_intercept=object_intercept;   /* OnActivate takes a door's use */
    aw_actor_disabled=AW_ObjectDisabled;   /* the CHIM window spawns no disabled actor */
    aw_static_flame_gone=AW_ObjectDisabled;   /* a taken candle's flame goes with it (TAKEN-LIGHT-FLAME-STAYS-60) */
    aw_lamp_gone=AW_ObjectDisabled;           /* and outdoors its night lamp light (TAKEN-LIGHT-FLAME-61) */
    aw_inventory_made_item=AW_MadeItemAt;   /* enchanted items (aw_made_N) read through the inventory */
#ifdef AW_COMBAT_EFFECT_MAGNITUDE
    aw_combat_effect_magnitude=effect_magnitude_of;   /* RESIST-NORMAL-WEAPONS-61: the blow's resistance (v0.0.61-weapons) */
#endif
    Cmd_AddCommand("aw_mwscript_status",status);
    /* STEAL-WITNESSED-NO-CRIME-61: the crime rules read the witnesses and the player here */
    aw_crime_witness=crime_witness;aw_crime_attack=crime_attack;aw_crime_thief=crime_thief;
    AW_CrimeInit();
}
/* the speaker of a conversation attacks when its Fight rating with the conversation's disposition reaches 100 */
int AW_MwscriptSpeakerAggro(edict_t *e,int disposition){
    eval_t *v,*r;aw_actor_t *a;aw_fighter_t sheet;int got;
    if(!e || e==sv_player || !(v=GetEdictFieldValue(e,"aw_source_id")) || !v->string)return -1;
    r=GetEdictFieldValue(e,"aw_ref");
    if(!(a=speaker_actor(pr_strings+v->string,r?(unsigned long)r->_float:0)) || (a->flags&AWL_DEAD))return -1;
    if(!AW_CombatActorLoad(pr_strings+v->string,&sheet))return -1;
    to_fighter(a,&sheet);
    if((got=AW_CombatAggro(e,&sheet,NULL,disposition,NULL,NULL))>0){a->flags|=AWL_COMBAT;combat_starts++;}
    return got;
}
/* STEAL-WITNESSED-NO-CRIME-61 (aw_crime.h): what the crime rules read of NPC E and of the player, and a witness's
 * attack; from the actor records in memory (the area's stat blocks), the effects and the player's sheet */
static float fatigue_term_of(float current,float maximum){
    float normalised=maximum<1?1:current/maximum;
    if(normalised<0)normalised=0;
    if(!AW_CombatSettingsLoad())return 1;
    return aw_combat_settings.fFatigueBase-aw_combat_settings.fFatigueMult*(1-normalised);   /* getFatigueTerm */
}
static int crime_witness(edict_t *e,aw_crime_witness_t *w){
    eval_t *v,*r;aw_actor_t *a;aw_actor_base_t b;char clas[32];const aw_fighter_t *f;
    memset(w,0,sizeof(*w));
    if(!e || e==sv_player || !(v=GetEdictFieldValue(e,"aw_source_id")) || !v->string)return 0;
    r=GetEdictFieldValue(e,"aw_ref");
    /* the live record by its reference alone (the area load made it from the area's stat block): no search of the
     * actor table on disk; s12: the first theft's seven searches and class reads took 650 ms. The search only for a
     * record not made yet. */
    a=r && r->_float>0?AW_ActorGet((uint32_t)r->_float,AW_ACTOR_NONE,0):NULL;
    if(!a)a=speaker_actor(pr_strings+v->string,r?(unsigned long)r->_float:0);
    if(!a || a->kind!=0)return 0;   /* NPCs only */
    f=AW_CombatFighter(e);
    w->can_report=!(a->flags&AWL_DEAD) && e->v.health>=0 && !(f && (f->dead || f->knocked));   /* canReportCrime */
    w->alarm=(int)AW_ActorStat(a,AWA_ALARM);w->fight=(int)AW_ActorStat(a,AWA_FIGHT);
    /* isClass(actor, "guard") matters only to a witness with Alarm 100 (an alarmed guard): read only for those */
    w->guard=w->alarm>=100 && AW_ActorBase(a->base,&b) && b.clas!=AW_ACTOR_NONE && read_string(b.clas,clas,sizeof(clas)) &&
             !Q_strcasecmp(clas,"guard");
    w->observer.sneak=AW_ActorStat(a,AWA_SKILL+19);w->observer.agility=AW_ActorStat(a,AWA_ATTRIBUTE+3);
    w->observer.luck=AW_ActorStat(a,AWA_ATTRIBUTE+7);
    w->observer.blind=a->reference?AW_EffectsMagnitude(a->reference,47,AW_EFFECT_NO_ARG):0;   /* Blind */
    w->observer.fatigue_term=fatigue_term_of(a->dyn_cur[2],a->dyn_base[2]);
    return 1;
}
static int crime_attack(edict_t *e,int fight){
    eval_t *v,*r;aw_actor_t *a;aw_fighter_t sheet;
    if(!e || e==sv_player || !sv_player || sv_player->v.health<=0 || !(v=GetEdictFieldValue(e,"aw_source_id")) || !v->string)return 0;
    r=GetEdictFieldValue(e,"aw_ref");
    a=r && r->_float>0?AW_ActorGet((uint32_t)r->_float,AW_ACTOR_NONE,0):NULL;   /* as crime_witness */
    if(!a)a=speaker_actor(pr_strings+v->string,r?(unsigned long)r->_float:0);
    if(!a || (a->flags&AWL_DEAD))return 0;
    AW_ActorSetStat(a,AWA_FIGHT,(float)(fight>100?100:fight));   /* the Fight kept: it fights on after a Calm (OpenMW) */
    if(AW_CombatFighter(e))return 1;                              /* already fighting */
    /* every fight slot taken (aw_combat.c SLOTS 4): no sheet read from disk for a fight that cannot start (s4: two of
     * the six reads of combat/actors.txt at a theft were for such witnesses) */
    if(AW_CombatHostiles()>=4)return 0;
    if(!AW_CombatActorLoad(pr_strings+v->string,&sheet))return 0;
    to_fighter(a,&sheet);sheet.fight=(unsigned char)(fight>100?100:fight);sheet.aware=1;
    if(!AW_CombatEngage(e,&sheet,NULL))return 0;
    a->flags|=AWL_COMBAT;combat_starts++;
    return 1;
}
static void crime_thief(aw_crime_thief_t *t){
    aw_actor_t *p=player_record();aw_inventory_item_t boots;float maximum=0,fatigue=AW_CombatPlayerFatigue(&maximum);
    t->sneaking=AW_MoveSneaking();
    if(p){t->sneak=AW_ActorStat(p,AWA_SKILL+19);t->agility=AW_ActorStat(p,AWA_ATTRIBUTE+3);t->luck=AW_ActorStat(p,AWA_ATTRIBUTE+7);}
    t->boot_weight=sv_player && ((int)sv_player->v.flags&FL_ONGROUND) && AW_InventoryEquippedItem(AW_SLOT_BOOTS,&boots)?
                   boots.weight:0;
    t->fatigue_term=fatigue_term_of(fatigue,maximum);
    t->chameleon=AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,40,AW_EFFECT_NO_ARG);       /* Chameleon */
    t->invisibility=AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,39,AW_EFFECT_NO_ARG);    /* Invisibility */
}
int AW_MwscriptActorRow(const char *record){
    int row;
    return AW_MwscriptActors() && record && (row=AW_ActorFind(record))>=0?row:-1;
}
/* the engage tick's part: memory only (the actor pool, the player's standing) */
void AW_MwscriptDispositionNow(int actor_row,unsigned long reference,int base,aw_dial_facts_t *f){
    aw_actor_t *a;
    f->base=base;f->rank=standing_rank;f->bounty=AW_StandingCrime();
    f->personality=aw_character.valid?(float)aw_character.attributes[6]:50.0f;
    f->diseased=disposition_diseased(0);f->weapon_drawn=disposition_weapon_drawn();f->charm=disposition_charm(reference);
    if(reference && actor_row>=0 && AW_MwscriptActors() && (a=AW_ActorGet((uint32_t)reference,actor_row,0))!=NULL)
        f->base=(int)AW_ActorStat(disposition_restore(a),AWA_DISPOSITION);
    else f->base=disposition_kept(reference,f->base);
}
/* Training (DIALOGUE-COMPLETE-58): the speaker's skills (its actor record), the player's skill (raised by one when
 * RAISE, at most 100) and attribute */
int AW_MwscriptNpcSkills(const char *record,unsigned long reference,float *out){
    aw_actor_t *a=speaker_actor(record,reference);int i;
    for(i=0;i<27;i++)out[i]=a?AW_ActorStat(a,AWA_SKILL+i):0;
    return a!=NULL;
}
int AW_MwscriptPlayerSkill(int which,int raise){
    if(!aw_character.valid || which<0 || which>=27)return 0;
    if(raise && aw_character.skills[which]<100){aw_character.skills[which]++;AW_MwvmStateChanged();}
    return aw_character.skills[which];
}
int AW_MwscriptPlayerAttribute(int attribute){
    return aw_character.valid && attribute>=0 && attribute<8?aw_character.attributes[attribute]:0;
}
/* Spells for sale (DIALOGUE-COMPLETE-58; OpenMW SpellBuyingWindow): the speaker's spells of the plain spell type the
 * player does not know yet, sorted by name (any case); their names and costs; buying one adds it to the player */
int AW_MwscriptSpellsForSale(const char *record,unsigned long reference,int *out,int max,char (*names)[48],int *costs){
    aw_actor_t *a=speaker_actor(record,reference),*p=player_record();int held[64],n,i,j,k=0,type;
    if(!a || !p)return 0;
    n=AW_ActorSpells(a,held,64);
    for(i=0;i<n && k<max;i++){
        char name[48];int cost;
        if(!AW_ActorSpellInfo(held[i],&type,name,sizeof(name),&cost) || type!=0 || AW_ActorHasSpell(p,held[i]))continue;
        for(j=k;j>0 && Q_strcasecmp(names[j-1],name)>0;j--){out[j]=out[j-1];costs[j]=costs[j-1];memcpy(names[j],names[j-1],48);}
        out[j]=held[i];costs[j]=cost;memcpy(names[j],name,48);k++;
    }
    return k;
}
int AW_MwscriptBuySpell(int spell){
    aw_actor_t *p=player_record();
    return p && AW_ActorAddSpell(p,spell);
}
static int ware_of(const char *id,aw_dial_ware_t *w){
    aw_inventory_item_t it;
    if(!AW_InventoryRead(id,&it))return 0;
    Q_snprintf(w->id,sizeof(w->id),"%s",id);Q_snprintf(w->name,sizeof(w->name),"%s",it.name[0]?it.name:id);
    w->value=it.value;w->category=it.category;w->enchanted=it.enchantment[0]!=0;
    return 1;
}
/* the merchant's stock: what its record holds now, equipped things and gold aside (OpenMW trades neither) */
int AW_MwscriptStock(const char *record,unsigned long reference,aw_dial_ware_t *out,int max){
    aw_actor_t *a=speaker_actor(record,reference);int items[64],counts[64],equipped[64],n,i,k=0;char id[40];
    if(!a)return 0;
    n=AW_ActorItems(a,items,counts,equipped,64);
    for(i=0;i<n && k<max;i++){
        if(equipped[i] || !AW_ActorItemId(items[i],id,sizeof(id)) || !ware_of(id,&out[k]))continue;
        out[k].count=counts[i];out[k].row=items[i];k++;
    }
    for(i=0;i<AW_SoldCount() && k<max;i++){   /* what the player sold it (BARTER-SOLD-ITEM-LOST-58) */
        uint32_t ref;int count;
        if(AW_SoldAt(i,&ref,id,sizeof(id),&count) && ref==(uint32_t)reference && ware_of(id,&out[k])){out[k].count=count;out[k].row=-2;k++;}
    }
    return k;
}
/* the player's inventory (aw_state's items), gold and equipped things aside */
int AW_MwscriptPlayerWares(aw_dial_ware_t *out,int max){
    int i,k=0;aw_value_t row;const aw_value_t *v=&row;
    for(i=0;i<AW_ItemCount(&aw_state) && k<max;i++){
        strcpy(row.id,AW_ITEM_ID(&aw_state,i));row.value=AW_ITEM_ROW(&aw_state,i)->value;
        if(v->value<=0 || !Q_strcasecmp((char *)v->id,"gold_001") || AW_InventoryEquipped(&aw_state,v->id) ||
           !ware_of(v->id,&out[k]))continue;
        out[k].count=v->value;out[k].row=-1;k++;
    }
    return k;
}
int AW_MwscriptTrade(const char *record,unsigned long reference,const aw_dial_ware_t *w,int buy,int price){
    aw_actor_t *a=speaker_actor(record,reference);int gold=AW_MwscriptPlayerGold(0);
    if(!a)return 0;
    if(buy){
        if(gold<price)return 0;
        if(w->row==-2){if(!AW_SoldAdd((uint32_t)reference,w->id,-1))return 0;}
        else if(w->row<0 || AW_ActorRemoveItem(a,w->row,1)!=1)return 0;
        AW_ItemAdd(&aw_state,w->id,1);AW_MwscriptPlayerGold(-price);
    }else{
        int row=w->row,items[64],counts[64],equipped[64],n,i;char id[40];
        if(AW_StateGet(&aw_state,AW_ITEM,w->id)<1)return 0;
        if(row<0){   /* the merchant's own row for the thing when it stocks it (no file-wide search on a sale) */
            n=AW_ActorItems(a,items,counts,equipped,64);
            for(i=0;i<n;i++)if(AW_ActorItemId(items[i],id,sizeof(id)) && !Q_strcasecmp(id,(char *)w->id)){row=items[i];break;}
        }
        if(row>=0 && !AW_ActorAddItem(a,row,1))return 0;   /* the record's change list is full (MERCHANT-ITEM-CAP-58) */
        if(row<0 && !AW_SoldAdd((uint32_t)reference,w->id,1)){   /* not stocked: kept as sold to this merchant */
            Con_Printf("Barter: no memory to keep %s at the merchant; it stays with you.\n",w->id);return 0;}
        AW_ItemAdd(&aw_state,w->id,-1);AW_MwscriptPlayerGold(price);
    }
    AW_MwvmStateChanged();
    return 1;
}
/* Repair (OpenMW MerchantRepair): the player's weapons and armour below their full health, equipped ones too, with
 * the record's health and the current points; mending one sets it to full */
int AW_MwscriptRepairables(aw_dial_ware_t *out,int *maximum,int *durability,int max){
    int i,k=0;aw_inventory_item_t it;aw_value_t row;const aw_value_t *v=&row;
    for(i=0;i<AW_ItemCount(&aw_state) && k<max;i++){
        int full,now;
        strcpy(row.id,AW_ITEM_ID(&aw_state,i));row.value=AW_ITEM_ROW(&aw_state,i)->value;
        if(v->value<=0 || !AW_InventoryRead(v->id,&it) || (it.category!=AW_INV_WEAPON && it.category!=AW_INV_ARMOUR))continue;
        full=(int)it.health;now=(int)(AW_InventoryCondition(v->id)*it.health);
        if(full<=0 || now>=full || !ware_of(v->id,&out[k]))continue;
        out[k].count=v->value;out[k].row=-1;maximum[k]=full;durability[k]=now;k++;
    }
    return k;
}
int AW_MwscriptMend(const char *id){return AW_InventorySetCondition(id,1);}
/* Spellmaking (OpenMW SpellCreationDialog / EffectEditorBase::startEditing): the effects the player may use, those of
 * the plain spells he knows and of the spells he made, each effect with its skill or attribute once */
int AW_MwscriptKnownEffects(aw_spell_effect_t *out,int max){
    aw_actor_t *p=player_record();int held[64],n=p?AW_ActorSpells(p,held,64):0,i,j,k=0,m,type;aw_spell_effect_t e[8];
    char name[8];int cost;
    for(i=0;i<n+AW_MadeSpellCount();i++){
        if(i<n){
            if(!AW_ActorSpellInfo(held[i],&type,name,sizeof(name),&cost) || type!=0)continue;
            m=AW_ActorSpellEffects(held[i],e,8);
        }else{
            const aw_made_spell_t *s=AW_MadeSpellAt(i-n);
            m=s?s->effects:0;
            for(j=0;j<m;j++)e[j]=s->effect[j];
        }
        for(j=0;j<m && k<max;j++){
            int q,seen=0;
            for(q=0;q<k;q++)if(out[q].effect==e[j].effect && out[q].skill==e[j].skill && out[q].attribute==e[j].attribute)seen=1;
            if(!seen)out[k++]=e[j];
        }
    }
    return k;
}
/* Enchanting (OpenMW EnchantingDialog): the player's things that can take an enchantment (not enchanted, enchantment
 * points above 0: weapons, armour, clothing, books), with their points and kind */
int AW_MwscriptEnchantables(aw_dial_ware_t *out,int *points,int *kind,int max){
    int i,k=0;aw_inventory_item_t it;aw_value_t row;const aw_value_t *v=&row;
    for(i=0;i<AW_ItemCount(&aw_state) && k<max;i++){
        strcpy(row.id,AW_ITEM_ID(&aw_state,i));row.value=AW_ITEM_ROW(&aw_state,i)->value;
        if(v->value<=0 || !AW_InventoryRead(v->id,&it) || it.enchantment[0] || it.enchant_capacity<=0)continue;
        if(it.category!=AW_INV_WEAPON && it.category!=AW_INV_ARMOUR && it.category!=AW_INV_CLOTHING && it.category!=AW_INV_BOOK)continue;
        if(!ware_of(v->id,&out[k]))continue;
        out[k].count=v->value;out[k].row=-1;points[k]=it.enchant_capacity;
        kind[k]=it.category==AW_INV_WEAPON?AW_DIAL_ENCHANT_WEAPON:it.category==AW_INV_BOOK?AW_DIAL_ENCHANT_BOOK:AW_DIAL_ENCHANT_WORN;
        k++;
    }
    return k;
}
/* the enchanting: the item and the filled gem leave the inventory (Azura's Star stays, emptied), the made item comes;
 * its id aw_made_N. 1 done. */
int AW_MwscriptEnchant(const aw_made_item_t *made,int gem){
    char id[48],gem_id[40];int creature,n;
    if(!made || !AW_GemAt(gem,gem_id,sizeof(gem_id),&creature) || AW_StateGet(&aw_state,AW_ITEM,made->base)<1)return 0;
    if((n=AW_MadeItemAdd(made))<0)return 0;
    Q_snprintf(id,sizeof(id),"%s%d",AW_MADE_ITEM_PREFIX,n);
    AW_ItemAdd(&aw_state,made->base,-1);AW_ItemAdd(&aw_state,id,1);
    AW_GemRemove(gem);
    if(Q_strcasecmp(gem_id,"misc_soulgem_azura"))AW_ItemAdd(&aw_state,gem_id,-1);
    AW_MwvmStateChanged();
    return 1;
}
/* one stat of the speaker's actor record (AWA_*): the enchanter's Enchant and Intelligence for its chance */
float AW_MwscriptSpeakerStat(const char *record,unsigned long reference,int stat){
    aw_actor_t *a=speaker_actor(record,reference);
    return a?AW_ActorStat(a,stat):0;
}
/* --- dialogue result scripts (DIALOGUE-COMPLETE-58) ---
 * The answer's result text is found in the DRSC rows (on disk, sorted by the text's FNV-1a hash, its length, the
 * speaker's script) by its hash and length, so a hash collision with another length never runs another text's
 * script; of the rows for the text, the one compiled with the speaker's own script runs on its instance. */
static unsigned long results_run,results_missing,results_broken;
/* the file's bytes at OFFSET (from its start), for the DRSC rows on disk */
typedef struct {FILE *f;long base;} file_reader_t;
static int read_file_at(void *user,uint32_t offset,void *out,uint32_t bytes){
    file_reader_t *r=(file_reader_t *)user;
    return !fseek(r->f,r->base+(long)offset,SEEK_SET) && fread(out,1,bytes,r->f)==bytes;
}
int AW_MwscriptRunResult(const char *record,unsigned long reference,const char *text,int length){
    int speaker=-1,k,chosen,row_speaker,broken;file_reader_t r;
    if(!text || length<=0)return 0;
    for(k=0;k<AW_MwvmInstanceCount();k++){   /* the speaker's attached script, when it has one */
        aw_mwvm_instance_t *in=AW_MwvmInstance(k);
        if(in && (in->flags&(AWI_USED|AWI_GLOBAL))==AWI_USED && in->reference==(uint32_t)reference){speaker=in->script;break;}
    }
    r.f=NULL;
    if(COM_FOpenFile(FILE_NAME,&r.f)<=0 || !r.f){if(r.f)fclose(r.f);return 0;}
    r.base=ftell(r.f);
    chosen=AW_MwvmFindDialogue(read_file_at,&r,AW_MwvmTextHash(text,length),length,speaker,&row_speaker,&broken);
    fclose(r.f);
    (void)record;
    if(chosen<0){results_missing++;Con_DPrintf("Dialogue: no compiled result script for this answer\n");return 0;}
    if(broken){
        char name[64];read_string(AW_MwvmScriptName(chosen),name,sizeof(name));results_broken++;
        Con_DPrintf("Dialogue: result script %s did not compile; its answer runs without it\n",name);return -1;
    }
    results_run++;
    /* the locals are those the row was compiled with (its speaker script): never another script's layout */
    return AW_MwvmRunDialogue(chosen,(uint32_t)reference,row_speaker);
}
