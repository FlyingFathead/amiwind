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
#include "aw_mappath.h"
#include "aw_npcpath.h"
#include "aw_ambient.h"   /* AW_AmbientLeaderOf: the fights' sides (COMBAT-ACTOR-VS-ACTOR-62) */   /* aw_path_fan: the followers' arrival spots (v0.0.62) */
#include "aw_story.h"     /* the player's control switches (v0.0.62, MWSCRIPT-PLAYER-CONTROL-62) */
#include "aw_weather.h"   /* GetCurrentWeather (v0.0.62, MWSCRIPT-SMALL-FUNCTIONS-62) */
#include "aw_forced_rules.h"   /* the AWFS save block (v0.0.62, MWSCRIPT-GAP-FUNCTIONS-62) */
#include "aw_lava.h"           /* HurtStandingActor holds the lava volume's own damage back */
#include "aw_mwconsole.h"      /* the original's console commands (v0.0.63, MW-CONSOLE-COMMANDS-62) */
#include "aw_listbox.h"        /* the console target finder */
#include "aw_clock.h"          /* GetCurrentTime, the moons' phases (v0.0.63, MWSCRIPT-GAPS-63) */
#include "aw_sky.h"
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
static void mw_target(void);       /* the console target finder (MW-CONSOLE-COMMANDS-62), below */
static void results_close(void);   /* the result scripts' handle (MWSCRIPT-RESULT-LONG-FRAME-62), closed at a load */
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
/* SCRIPTED-EVENTS-FALLING-MAGE-62: the session's Say calls, started and not (no actor in the world, no voice row, no
 * sample in the pool), and the entity and length of the last one started (aw_mwscript_status) */
static unsigned long says_started,says_missed;static int say_last_entity;static float say_last_seconds;
static void host_say(int instance,int target,int voice,int text){
    unsigned char hash[8];int centis,entity,i,slot=0;vec3_t at;sfx_t *s;
    (void)text;
    entity=locate(instance,target,at);
    if(entity<=0 || !AW_MwvmVoice(voice,hash,&centis) || !(s=pool_sound(hash))){says_missed++;return;}
    S_StartSound(entity,CHAN_SCRIPT_VOICE,s,at,1.0f,1.0f);
    says_started++;say_last_entity=entity;say_last_seconds=centis/100.0f;
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
/* GetDistance (OpenMW 0.51 apps/openmw/mwscript/miscextensions.cpp OpGetDistance: the 3D distance between the script's
 * own reference and the target, in game units). SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62: the earlier rule that fired a
 * far event just inside the draw distance is withdrawn (decided for the project 7 November 2026): the falling mage's
 * fallingScript runs on his journal on the ground and fires at the original's 2000 units from it, as the original. The
 * SCRP row's far trigger field stays in the file (awms.py) but is no longer read here. */
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
/* SCRIPTED-EVENT-FALLING-MAGE-61 (a): an actor a script enables in an area that is loaded already (the CHIM window
 * held it back while disabled) spawns at once, not at its cell's next join (aw_actors.c sets it; NULL: none). The
 * edict an earlier Disable hid on this map is shown again by ledger_show / object_show as before. */
extern void (*aw_actor_enabled)(unsigned reference);
void AW_FallTick(float dt);void AW_FallStatus(void);void AW_FallInit(void);
static unsigned long actors_enabled;
static void enabled(uint32_t ref){if(aw_actor_enabled){aw_actor_enabled(ref);actors_enabled++;}}
static int32_t ledger_object(uint32_t ref,int op,int32_t value){
    aw_ledger_row_t *r=ledger_row(ref);
    switch(op){
    case AWM_ENABLE:
        if(r && (r->fields&AW_LEDGER_DISABLED)){
            r->fields&=~AW_LEDGER_DISABLED;
            if(!(r->fields&AW_LEDGER_TAKEN))ledger_show(ref);   /* a taken item stays taken */
            if(!(r->fields&AW_LEDGER_TAKEN))enabled(ref);       /* an actor of a loaded area spawns at once */
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
        if((o=object_find(ref,0))!=NULL && o->disabled){o->disabled=0;object_show(o);enabled(ref);}
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
    if(AW_SceneActivate(reference))return;    /* a load door of this map */
    if(AW_PlacedActivate(reference))return;   /* a placed item: its reader with Take, or taken (the census papers) */
    {   /* an NPC: its conversation, as E opens it (OpenMW: Activate on an actor is its default use, the dialogue; the
         * census clerk's CharGenClassNPC passes his use on this way; CENSUS-INTRO-SCRIPTS-62). Other objects' own
         * use: not yet */
        int n=entity_of_reference(reference);edict_t *e=edict_of(n);
        if(e && !e->free && !strcmp(pr_strings+e->v.classname,"aw_npc"))AW_DialWindowTalkTo(e);
    }
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
/* OnPCAdd (CENSUS-INTRO-SCRIPTS-62; OpenMW 0.51: an item's script reads OnPCAdd 1 once the item is in the player's
 * inventory): every gain of the player's inventory (aw_state.c aw_item_added) is queued (8 a frame) and, before the
 * scripts run, set on the item's script: the placement just taken keeps its own instance, a carried item without one
 * gets the carried instance (aw_mwvm.c AW_MwvmPcAdd). Cost: one hash per gain, a binary search of the PADD rows. */
#define PCADD_QUEUE 8
static uint32_t pcadd_queue[PCADD_QUEUE],last_taken;static int npcadd;static unsigned long pcadd_placed,pcadd_carried;
static void item_added(const char *id,int32_t count){
    (void)count;
    if(!mwscript.value || !resident || npcadd>=PCADD_QUEUE)return;
    pcadd_queue[npcadd++]=AW_MwvmTextHash(id,(int)strlen(id));
}
static int census_script(int script);
static void held_recheck(int script);
static void pcadd_flush(void){
    int i,script,slot,r;
    for(i=0;i<npcadd;i++){
        if(!AW_MwvmPcAddRow(pcadd_queue[i],&script,&slot))continue;
        held_recheck(script);   /* taken from a container or a body: its held instance there stops */
        if(census_script(script))AW_MwvmScriptHold(script,AW_CensusLegacy());   /* the ring on the old path */
        if((r=AW_MwvmPcAdd(last_taken,script,slot))!=0){
            if(r==1)pcadd_placed++;else pcadd_carried++;}
    }
    npcadd=0;last_taken=0;
}
/* MWSCRIPT-UNPLACED-ATTACH-62 (OpenMW 0.51 runs the script of every item in the player's inventory, and an item's
 * script ends with the item there): the last of an item leaving the inventory is queued (8 a frame, as the gains) and
 * its carried instance stops unless another carried item names the same script; at every map change (a load comes
 * with one) each carried kind's script runs (carried_sync: one hash and one binary search per kind carried, never a
 * file read). A placement the player took that runs its own instance on this map is not doubled. */
#define CARRIED_QUEUE 8
static uint32_t removed_queue[CARRIED_QUEUE];static int nremoved;
static unsigned long carried_started,carried_stopped,carried_syncs;
static void item_removed(const char *id){
    if(!mwscript.value || !resident || nremoved>=CARRIED_QUEUE)return;
    removed_queue[nremoved++]=AW_MwvmTextHash(id,(int)strlen(id));
}
/* 1 when an item of the inventory other than HASH names SCRIPT */
static int carried_other(int script,uint32_t hash){
    int i,s,slot;
    for(i=0;i<aw_state.items.count;i++){
        const char *id;uint32_t h;
        if(AW_ITEM_ROW(&aw_state,i)->value<=0)continue;
        id=AW_ITEM_ID(&aw_state,i);h=AW_MwvmTextHash(id,(int)strlen(id));
        if(h!=hash && AW_MwvmPcAddRow(h,&s,&slot) && s==script)return 1;
    }
    return 0;
}
static void removed_flush(void){
    int i,script,slot;
    for(i=0;i<nremoved;i++)
        if(AW_MwvmPcAddRow(removed_queue[i],&script,&slot) && !carried_other(script,removed_queue[i]) &&
           AW_MwvmCarriedStop(script))carried_stopped++;
    nremoved=0;
}
static void carried_sync(void){
    int i,script,slot;
    carried_syncs++;
    for(i=0;i<aw_state.items.count;i++){
        const char *id;
        if(AW_ITEM_ROW(&aw_state,i)->value<=0)continue;
        id=AW_ITEM_ID(&aw_state,i);
        if(!AW_MwvmPcAddRow(AW_MwvmTextHash(id,(int)strlen(id)),&script,&slot) || AW_MwvmScriptAttached(script))continue;
        if(census_script(script))AW_MwvmScriptHold(script,AW_CensusLegacy());
        if(AW_MwvmPcAdd(0,script,AW_MWVM_NO_SLOT)==2)carried_started++;
    }
}
int AW_ObjectTake(unsigned int reference,int stolen){
    object_t *o;int number;edict_t *e;int room;
    if(!reference || reference>0xFFFFFFu || AW_ObjectDisabled(reference))return 0;
    last_taken=reference;   /* the placement whose item the queued OnPCAdd belongs to (pcadd_flush) */
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
static unsigned long combat_between,combat_refused;   /* COMBAT-ACTOR-VS-ACTOR-62: fights between two actors started, refused */
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
/* UNDERWATER-BREATH-62: counts every change of the player's race, birthsign or class spells, so the kept always-active
 * magnitudes (passive_of) are read again: a race swap removes and adds as many spells, the list size alone stays */
static unsigned long creation_generation;
static unsigned long applied_epoch;   /* AW_ActorStateEpoch when applied: a load or New Game empties the record */
static void creation_spells(aw_actor_t *a){
    int want[AWS_SPELLS],n=0,i,j,held[128],h,type,cost,nrace;long tb;const unsigned char *t;char name[8];
    /* UNDERWATER-BREATH-62 (v0.0.63-dev5 release check: an Argonian read Water Breathing 0): the player's record was
     * emptied since the spells were applied (a loaded game, a New Game), so it holds only its base list again:
     * apply from the start, as the first time */
    if(applied_epoch!=AW_ActorStateEpoch()){applied_race=applied_birth=applied_class=-2;applied_n=0;}
    if(!aw_character.valid ||(aw_character.race==applied_race && aw_character.birth==applied_birth &&
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
    applied_class=aw_character.clas;creation_generation++;applied_epoch=AW_ActorStateEpoch();
    Con_DPrintf("Player spells: %d from the race, the birthsign, the class and the skills (%d starting spells)\n",n,start_chosen_n);
}
static unsigned long god_health_held;   /* GODMODE-LAVA-DEATH-62: script or spell health losses god mode kept back */
unsigned long AW_MwscriptGodHealthHeld(void){return god_health_held;}
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
    int i;float old_max;
    if(!a || !aw_character.valid)return;
    old_max=aw_character.maximum[0];
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
    /* GODMODE-LAVA-DEATH-62: every script and spell change of the player's health comes back here (SetHealth,
     * ModCurrentHealth, Damage Health, poison, the elements, a drain of the maximum): in god mode it never falls below
     * the edict's live health (a heal still lands); the maximum caps it only when the change drained the maximum itself
     * (v0.0.63-dev3: a health above an unchanged maximum, 100 of 40, let ModCurrentHealth -50 land) */
    if(sv_player){
        float h=AW_CombatGodHealth(((int)sv_player->v.flags&FL_GODMODE)!=0,sv_player->v.health,a->dyn_cur[0],
                                   a->dyn_base[0]<old_max?a->dyn_base[0]:0);
        if(h!=a->dyn_cur[0]){god_health_held++;aw_character.current[0]=h;}
        sv_player->v.health=h;
    }
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
/* RESIST-NORMAL-WEAPONS-61 (aw_combat.h aw_combat_effect_magnitude): the summed magnitude of EFFECT on the actor of
 * edict E now (the player's or an NPC's or creature's by its reference): its active effects (cast spells, worn items)
 * plus, since v0.0.62, the always-active spells of its list (AW_ActorPassiveMagnitude: the "immune to normal weapons"
 * ability of 68 creatures and 1 NPC of the masters, the vampires' 50 %, Almalexia's shield). The list part reads the
 * actor's spells from disk, so it is kept: PASSIVE_MEMO answers by reference, effect, list size and record, refreshed
 * when the list changes or a game loads; once per landed blow, no file read when kept. */
#define PASSIVE_MEMO 8
static struct {uint32_t ref;int effect,nspells;uint16_t base;unsigned long generation;float value;} passive_memo[PASSIVE_MEMO];
static int passive_next;
static unsigned long passive_reads,passive_kept;
static float passive_of(const aw_actor_t *a,uint32_t ref,int effect){
    int i;unsigned long g=AW_EffectsGeneration()+creation_generation;   /* either changes: read again */
    if(!a)return 0;
    for(i=0;i<PASSIVE_MEMO;i++)
        if(passive_memo[i].ref==ref && passive_memo[i].effect==effect && passive_memo[i].nspells==a->nspells &&
           passive_memo[i].base==a->base && passive_memo[i].generation==g){passive_kept++;return passive_memo[i].value;}
    i=passive_next;passive_next=(passive_next+1)%PASSIVE_MEMO;
    passive_memo[i].ref=ref;passive_memo[i].effect=effect;passive_memo[i].nspells=a->nspells;passive_memo[i].base=a->base;
    passive_memo[i].generation=g;passive_memo[i].value=AW_ActorPassiveMagnitude(a,effect);
    passive_reads++;
    return passive_memo[i].value;
}
static float effect_magnitude_of(edict_t *e,int effect){
    uint32_t ref;
    if(!e)return 0;
    if(e==sv_player)
        return AW_EffectsMagnitude(AW_ACTOR_PLAYER_REF,effect,AW_EFFECT_NO_ARG)+passive_of(player_record(),AW_ACTOR_PLAYER_REF,effect);
    ref=ref_of_edict(e);
    if(!ref)return 0;
    return AW_EffectsMagnitude(ref,effect,AW_EFFECT_NO_ARG)+passive_of(record_of_edict(e),ref,effect);
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
/* CRIME-59 (GUARD-RESIST-ARREST-NOTHING-61): the loaded edict of placed reference REF, NULL none. A dialogue
 * result's instance carries the speaker's reference but no entity, so its StartCombat ("Resist Arrest.") found no
 * actor and the guard did nothing. One walk of the edicts, only for such a call. */
static edict_t *speaker_edict(uint32_t ref){
    int i;eval_t *v;
    if(!ref || !sv.active)return NULL;
    for(i=1;i<sv.num_edicts;i++){
        edict_t *x=EDICT_NUM(i);
        if(!x->free && (v=GetEdictFieldValue(x,"aw_ref"))!=NULL && v->_float>0 && (uint32_t)v->_float==ref)return x;
    }
    return NULL;
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
        if(!e)e=speaker_edict(ref);   /* a dialogue result's run has no entity of its own: the speaker by its reference */
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
        if((a->flags&AWL_DEAD))return;
        if(other!=AW_MWVM_PLAYER){
            /* COMBAT-ACTOR-VS-ACTOR-62 (v0.0.63): StartCombat on another actor (OpenMW mechanicsmanagerimp.cpp
             * startCombat): both fight each other, each with its own sheet; the other one only when it has an entity
             * here and is alive */
            vec3_t at;int n=locate(instance,other,at);edict_t *o=n>0?edict_of(n):NULL;aw_actor_t *b;eval_t *w;
            aw_fighter_t other_sheet;
            if(!o || o==e || o==sv_player || !(b=record_of_edict(o)) || (b->flags&AWL_DEAD)){combat_refused++;return;}
            w=GetEdictFieldValue(o,"aw_source_id");
            if(!v || !v->string || !AW_CombatActorLoad(pr_strings+v->string,&sheet) ||
               !w || !w->string || !AW_CombatActorLoad(pr_strings+w->string,&other_sheet)){combat_refused++;return;}
            to_fighter(a,&sheet);to_fighter(b,&other_sheet);
            if(AW_CombatEngageAgainst(e,&sheet,o,&other_sheet)){a->flags|=AWL_COMBAT;b->flags|=AWL_COMBAT;combat_starts++;
                                                                combat_between++;}
            return;
        }
        if(!sv_player || sv_player->v.health<=0)return;
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
static unsigned long binks,binks_missed;   /* PlayBink: started, and absent from the build (MWSCRIPT-UNPLACED-ATTACH-62) */
static unsigned long weather_calls,weather_refused;   /* ChangeWeather and ModRegion (MWSCRIPT-COMPLETE-LANDMARK) */
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
/* MW-CONSOLE-COMMANDS-62: a console line's own words (an axis, a target id) given to a host call as the string
 * indexes CONSOLE_STRING+k, never a row of the file's strings (whose count stays far below it) */
#define CONSOLE_STRING 0xFFF0
static const char *console_texts[4];
static const char *call_string(const unsigned char *strings,int nstrings,int i){
    int k;
    if(i>=nstrings)return NULL;
    k=(strings[2*i]<<8)|strings[2*i+1];
    if(k>=CONSOLE_STRING && k<CONSOLE_STRING+4)return console_texts[k-CONSOLE_STRING];
    return cached_id(k);
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

/* --- PositionCell of anything but the player (v0.0.62, MWSCRIPT-POSITIONCELL-ACTORS-62; the rules of OpenMW 0.51
 * apps/openmw/mwscript/transformationextensions.cpp OpPositionCell, our own code). The compiler hands x, y, z, yaw,
 * the kind (AWM_MOVE_OUTDOORS: the original's units; AWM_MOVE_ROOM: the room map's own units) and the room's stable
 * number. Into the place loaded now: the actor is put there (or, not loaded here, spawned there from its entity). Into
 * another place: its row of the world change list says where it is now (aw_actors.c AW_ActorsMoveTo); a loaded actor
 * leaves this map at the end of the frame (its script parked, its edict freed; after a conversation closes), and its
 * entity block is kept for this session. A room spawns its arrivals when it loads (room_visitors: the VISI rows, the
 * entity read from the actor's home room map, one open and two reads). Not carried yet: an actor arriving outdoors
 * while its home frame is not in the window (it stands there once its home frame joins), and an object that is no
 * actor moved across places (counted). */
static unsigned long poscells,poscells_refused,poscells_away,visitors_spawned,visitors_no_text;
static int compare_refs(const void *a,const void *b);
#define CARRIED 8
static struct {uint32_t ref;char *text;unsigned long length;} carried_text[CARRIED];static int carried_next;
#define LEAVING 16
static struct {uint32_t ref;int entity;} leaving[LEAVING];static int leaving_count;
static void edict_refs_refresh(void){
    int i;edict_t *e;eval_t *v;
    edict_ref_count=0;
    for(i=1;i<sv.num_edicts && edict_ref_count<EDICT_REFS;i++){
        e=EDICT_NUM(i);if(e->free)continue;
        v=GetEdictFieldValue(e,"aw_ref");if(!v || v->_float<=0)continue;
        edict_refs[edict_ref_count].ref=(uint32_t)v->_float;edict_refs[edict_ref_count++].entity=i;
    }
    qsort(edict_refs,edict_ref_count,sizeof(edict_refs[0]),compare_refs);
}
/* an actor's entity block kept when it leaves a map this session (its home's text, or a joined frame's) */
static void carry_copy(uint32_t ref,const char *block,unsigned long length){
    int i,slot=-1;char *copy;
    if(!block || length<2 || length>16384)return;
    for(i=0;i<CARRIED;i++)if(carried_text[i].text && carried_text[i].ref==ref)slot=i;
    if(slot<0){slot=carried_next;carried_next=(carried_next+1)%CARRIED;}
    if(!(copy=(char *)AW_TryMalloc(length+1)))return;
    memcpy(copy,block,length);copy[length]=0;
    free(carried_text[slot].text);carried_text[slot].text=copy;carried_text[slot].ref=ref;carried_text[slot].length=length;
}
/* from the loaded map's entity text (a room's, a town map's) */
static void carry_text(uint32_t ref){
    const char *text=sv.worldmodel?sv.worldmodel->entities:NULL,*block;unsigned long length=0;
    if(text && (block=AW_MwvmEntityBlock(text,(unsigned long)strlen(text),ref,&length))!=NULL)carry_copy(ref,block,length);
}
static const char *carried_of(uint32_t ref,unsigned long *length){
    int i;for(i=0;i<CARRIED;i++)if(carried_text[i].text && carried_text[i].ref==ref){*length=carried_text[i].length;return carried_text[i].text;}
    return NULL;
}
/* REF's entity block from its home room map MAP (a copy, freed by the caller; NULL none): the map's header, then its
 * entity lump in one read (BSP29 and CHIM room maps alike: lump 0) */
static char *home_text(const char *map,uint32_t ref,unsigned long *length){
    char path[AW_MAP_PATH_SIZE];unsigned char head[12];FILE *f=NULL;int bytes;long at,k,n;char *lump,*copy=NULL;
    const char *block;
    AW_MapPath(map,path,sizeof(path));
    if((bytes=COM_FOpenFile(path,&f))<=0 || !f){if(f)fclose(f);return NULL;}
    at=ftell(f);
    if(fread(head,1,sizeof(head),f)!=sizeof(head)){fclose(f);return NULL;}
    k=(long)(head[4]|(head[5]<<8)|(head[6]<<16)|((unsigned long)head[7]<<24));
    n=(long)(head[8]|(head[9]<<8)|(head[10]<<16)|((unsigned long)head[11]<<24));
    if(k<0 || n<=0 || n>4L*1024L*1024L || k+n>bytes || !(lump=(char *)AW_TryMalloc((size_t)n+1))){fclose(f);return NULL;}
    if(fseek(f,at+k,SEEK_SET) || fread(lump,1,(size_t)n,f)!=(size_t)n)n=0;
    fclose(f);lump[n]=0;
    if((block=AW_MwvmEntityBlock(lump,(unsigned long)n,ref,length))!=NULL && (copy=(char *)AW_TryMalloc(*length+1))!=NULL){
        memcpy(copy,block,*length);copy[*length]=0;}
    free(lump);
    return copy;
}
/* CENSUS-INTRO-SCRIPTS-62: the census office's scripts the compiled file runs (taken off config/mwscript.json's
 * hand-written list one by one). With aw_census_legacy 1 the old hand-written opening carries them instead,
 * so they are held (AW_MwvmScriptHold): not attached, nothing happens twice. The answer per script number is kept
 * (64 rows, 512 bytes: one name read per script that is attached, from the string cache; never a scan of the file's
 * names). */
static const char *const census_scripts[]={"chargendoorentercaptain","chargendoorexit","chargendoorexitcaptain",
    "chargenfatiguebarrel","chargendoorguardtalker","chargenclassnpc","chargenstatssheet","chargen_ring_keley",NULL};
#define CENSUS_SEEN 64
static int census_seen[CENSUS_SEEN],census_is[CENSUS_SEEN],ncensus_seen;static const unsigned char *census_for;
static int census_script(int script){
    char name[40];int i;
    if(census_for!=resident){census_for=resident;ncensus_seen=0;}
    for(i=0;i<ncensus_seen;i++)if(census_seen[i]==script)return census_is[i];
    read_string(AW_MwvmScriptName(script),name,sizeof(name));
    for(i=0;census_scripts[i] && Q_strcasecmp(name,(char *)census_scripts[i]);i++);
    if(ncensus_seen<CENSUS_SEEN){census_seen[ncensus_seen]=script;census_is[ncensus_seen++]=census_scripts[i]!=NULL;}
    return census_scripts[i]!=NULL;
}
static int attach_script(uint32_t ref,int script,int flags,int entity,const float origin[3]){
    if(script>=0 && census_script(script))AW_MwvmScriptHold(script,AW_CensusLegacy());
    return AW_MwvmAttach(ref,script,flags,entity,origin);
}
/* an arrived actor's own script, as attach_map binds this map's (the BIND rows are sorted by reference: a binary
 * search on disk, a few small reads) */
static void attach_visitor(uint32_t ref,int entity,const edict_t *e){
    FILE *f=NULL;uint32_t offset,rows,bytes;long base,low=0,high;unsigned char row[24];
    if(!AW_MwvmSection("BIND",&offset,&rows,&bytes) || !rows || COM_FOpenFile(FILE_NAME,&f)<=0 || !f){if(f)fclose(f);return;}
    base=ftell(f);high=(long)rows-1;
    while(low<=high){
        long mid=(low+high)/2;uint32_t r;
        if(fseek(f,base+(long)offset+24L*mid,SEEK_SET) || fread(row,1,24,f)!=24)break;
        r=((uint32_t)row[0]<<24)|((uint32_t)row[1]<<16)|((uint32_t)row[2]<<8)|row[3];
        if(r<ref)low=mid+1;else if(r>ref)high=mid-1;
        else{
            int k=attach_script(ref,(row[4]<<8)|row[5],((row[6]<<8)|row[7])|(map_room?AWB_INTERIOR:0),entity,e->v.origin);
            if(k>=0)attach_edicts++;else attach_refused++;
            break;
        }
    }
    fclose(f);
}
/* REF arrives here (its row says so): its entity from this session's copy, else from its home room map HOME (a string
 * index, AWM_NONE: none known); spawned, indexed and its script attached. NULL when it cannot be. */
static edict_t *visitor_arrives(uint32_t ref,int home){
    unsigned long length=0;const char *text=carried_of(ref,&length);char *read=NULL,map[64];edict_t *e;
    if(!text && home!=AWM_NONE && read_string(home,map,sizeof(map)))text=read=home_text(map,ref,&length);
    if(!text){visitors_no_text++;Con_DPrintf("PositionCell: actor %lu arrives with no entity to spawn.\n",(unsigned long)ref);
        return NULL;}
    e=AW_ActorsSpawnVisitor(text,length);
    free(read);
    if(!e)return NULL;
    edict_refs_refresh();
    attach_visitor(ref,NUM_FOR_EDICT(e),e);
    visitors_spawned++;
    return e;
}
/* aw_actors.c, when a room's actors take their rows: the VISI rows of ROOM (resident, sorted by room) */
static void room_visitors(long room){
    uint32_t off,rows,bytes,i;long moved;
    if(!resident || !room || !AW_MwvmSection("VISI",&off,&rows,&bytes) || off+bytes>resident_bytes || 12ul*rows>bytes)return;
    for(i=0;i<rows;i++){
        const unsigned char *r=resident+off+12*i;uint32_t where=rd_be32(r),ref=rd_be32(r+4);
        /* 0xFFFFFFFF: a follower of the player, in whatever room its row puts it (v0.0.62) */
        if(where!=0xFFFFFFFFu && (long)where!=room)continue;
        if(AW_ActorsMovedPlace(ref,&moved) && moved==room)visitor_arrives(ref,(r[8]<<8)|r[9]);
    }
}
/* the VISI row of (ROOM, REF): its home map, AWM_NONE none */
static int visitor_home(long room,uint32_t ref){
    uint32_t off,rows,bytes,i;
    if(!resident || !AW_MwvmSection("VISI",&off,&rows,&bytes) || off+bytes>resident_bytes || 12ul*rows>bytes)return AWM_NONE;
    for(i=0;i<rows;i++){
        const unsigned char *r=resident+off+12*i;
        if((long)rd_be32(r)==room && rd_be32(r+4)==ref)return (r[8]<<8)|r[9];
    }
    return AWM_NONE;
}
/* the actors that left this map this frame go at its end (a script that moved itself goes on to its end first), and
 * not while a conversation or a menu is open */
static void leave_now(void){
    int i,left=0;
    if(!leaving_count || host_menu_mode())return;
    for(i=0;i<leaving_count;i++){
        edict_t *e=edict_of(leaving[i].entity);eval_t *v;
        AW_MwvmDetach(leaving[i].ref);
        if(!e || e->free || !(v=GetEdictFieldValue(e,"aw_ref")) || (uint32_t)v->_float!=leaving[i].ref)continue;
        AW_ActorsRemove(e);left++;
    }
    leaving_count=0;
    if(left)edict_refs_refresh();
}
static int is_actor(const edict_t *e){
    const char *c;
    if(!e || e->free || !e->v.classname)return 0;
    c=pr_strings+e->v.classname;
    return !strcmp(c,"aw_npc") || !strcmp(c,"aw_creature");
}
static int position_cell(int instance,int target,const aw_mwcell_t *numbers,int count){
    vec3_t at,local;int n,kind,i,here;long where;edict_t *e;uint32_t ref;float pos[3],yaw,island[3];
    if(count<6)return 0;                       /* not the compiler's carried form: stays "not yet" */
    for(i=0;i<3;i++)pos[i]=numbers[i].f;
    yaw=numbers[3].f;kind=numbers[4].i;where=numbers[5].i;
    if(target==AW_MWVM_PLAYER){                /* the compiler keeps the player's own as PLAYERMOVE */
        if(kind==AWM_MOVE_OUTDOORS && AW_MapTeleportAt(pos,1))poscells++;else poscells_refused++;
        return 1;
    }
    n=locate(instance,target,at);e=n>0?edict_of(n):NULL;
    if(e && (e->free || e==sv_player))e=NULL;
    ref=target_reference(instance,target);
    if(kind==AWM_MOVE_ROOM){here=map_room && where==map_room;for(i=0;i<3;i++)local[i]=pos[i];}
    else here=!map_room && AW_SourceToWorld(sv.name,pos,local);
    if(e && !is_actor(e)){
        /* an object that is no actor: moved within this place as Position does; across places not yet */
        if(!here){poscells_refused++;return 1;}
        VectorCopy(local,e->v.origin);e->v.angles[1]=yaw;SV_LinkEdict(e,false);poscells++;return 1;
    }
    if(here && e){
        VectorCopy(local,e->v.origin);e->v.angles[0]=e->v.angles[2]=0;e->v.angles[1]=yaw;
        e->v.velocity[0]=e->v.velocity[1]=e->v.velocity[2]=0;SV_LinkEdict(e,false);
        /* its row: where it stands now (outdoors the actor module's own island conversion) */
        if(ref && map_room)AW_ActorsMoveTo(ref,map_room,local,yaw);
        else if(ref)AW_ActorsCapture(e);
        poscells++;return 1;
    }
    if(!ref){poscells_refused++;return 1;}     /* no reference: nothing to keep it by */
    for(i=0;i<3;i++)island[i]=pos[i]*0.25f;    /* outdoors: the island's units (game units / 4) */
    if(!AW_ActorsMoveTo(ref,kind==AWM_MOVE_ROOM?where:0,kind==AWM_MOVE_ROOM?pos:island,yaw)){poscells_refused++;return 1;}
    AW_MwvmStateChanged();
    if(here){
        /* not loaded here: it arrives now (a room: its entity from its home map) */
        if(kind!=AWM_MOVE_ROOM || !visitor_arrives(ref,visitor_home(where,ref)))poscells_refused++;
        else poscells++;
        return 1;
    }
    if(e && leaving_count<LEAVING){
        carry_text(ref);
        leaving[leaving_count].ref=ref;leaving[leaving_count].entity=NUM_FOR_EDICT(e);leaving_count++;
    }
    poscells_away++;
    return 1;
}

/* --- the placing family (v0.0.62, MWSCRIPT-PLACE-OBJECTS-62; the rules of OpenMW 0.51
 * apps/openmw/mwscript/transformationextensions.cpp OpPlaceAt, OpPlaceItem, OpPlaceItemCell and mwworld/worldimp.cpp
 * safePlaceObject, our own code). The compiler hands the object's PLAC row (the id, its kind, a template reference of
 * the same record and that reference's home room map, the record's script) as the last number. PlaceAtPC / PlaceAtMe:
 * COUNT copies at DISTANCE game units in DIRECTION (0 front, 1 back, 2 left, 3 right) of the player or the reference,
 * facing as it faces; an actor takes the next direction when the way back to the reference is blocked (OpenMW: a ray
 * from the spot 30 units up to the reference 20 units up), and stands on the ground under the spot. PlaceItem: x, y,
 * z in the player's cell (game units), the rotation in degrees. PlaceItemCell: the place worked out by the compiler.
 * An NPC or creature is a new reference (aw_actors.h AW_ACTORS_PLACED + its row << 12 + a serial) spawned from its
 * template's entity (the loaded map's text, this session's copy, the home room map's, else the actor table's base of
 * the record), its own script attached; its row of the world change list keeps it (AW_ActorsPlacedTick spawns it again
 * where the row says). A carried item is a drop row of the list (AW_InventoryPlace), taken as any drop. */
#define PLACE_ACTOR 0
#define PLACE_ITEM 1
#define PLACE_OTHER 2            /* v0.0.62: an activator, a static, a container: from its template's entity */
#define PLACE_COPIES 16          /* the most copies one call makes (the game's calls ask for 1) */
typedef struct {int id,home,script,kind,carried;uint32_t template_ref;} place_row_t;
static unsigned long places,places_refused,places_away,placed_spawned,placed_no_text;
static int place_row(int row,place_row_t *out){
    uint32_t off,rows,bytes;const unsigned char *r;
    if(!resident || row<0 || !AW_MwvmSection("PLAC",&off,&rows,&bytes) || off+bytes>resident_bytes || 12ul*rows>bytes ||
       (uint32_t)row>=rows)return 0;
    r=resident+off+12*row;
    out->id=(r[0]<<8)|r[1];out->home=(r[2]<<8)|r[3];out->template_ref=rd_be32(r+4);out->script=(r[8]<<8)|r[9];
    out->kind=r[10];out->carried=r[11]&1;
    return out->carried;
}
/* a free key for a new placement of PLAC row ROW: 0 when the row's 4,095 are used */
static uint32_t placed_key(int row){
    uint32_t n,key;
    if(row<0 || row>255)return 0;
    for(n=1;n<=0xFFF;n++){key=AW_ACTORS_PLACED|((uint32_t)row<<12)|n;if(AW_ActorsPlacedFree(key))return key;}
    return 0;
}
/* the entity text a placed actor of row R spawns from, with its own reference KEY ("{" .. "}", to free; NULL none) */
static char *placed_text(const place_row_t *r,uint32_t key,unsigned long *length){
    unsigned long n=0;const char *text=NULL,*block;char *own=NULL,*out,id[64],map[64],tail[40];int t;
    if(r->template_ref){
        const char *ents=sv.worldmodel?sv.worldmodel->entities:NULL;
        if(ents && (block=AW_MwvmEntityBlock(ents,(unsigned long)strlen(ents),r->template_ref,&n))!=NULL)text=block;
        else if((block=carried_of(r->template_ref,&n))!=NULL)text=block;
        else if(r->home!=AWM_NONE && read_string(r->home,map,sizeof(map)))text=own=home_text(map,r->template_ref,&n);
    }
    if(!text && read_string(r->id,id,sizeof(id)))text=own=AW_ActorsBaseText(id,&n);
    if(!text || n<2 || text[n-1]!='}' || n>16384){free(own);return NULL;}
    /* the template's own "aw_ref" stays in the text; a later key wins in ED_ParseEdict */
    t=sprintf(tail,"\n\"aw_ref\" \"%lu\"\n}",(unsigned long)key);
    if((out=(char *)AW_TryMalloc(n+(unsigned long)t+1))!=NULL){
        memcpy(out,text,n-1);memcpy(out+n-1,tail,(size_t)t+1);*length=n-1+(unsigned long)t;
    }
    free(own);
    return out;
}
/* the placed actor KEY spawned where its row puts it (here), its script attached; 1 spawned. AW_ActorsPlacedTick's
 * spawner too (a return to its place, a load). */
/* v0.0.62 (MWSCRIPT-GAP-FUNCTIONS-62): a placed object that is not an actor (an activator, a static, a container) from
 * its template's entity TEXT ("{" .. "}") where its row KEY puts it: the entity parsed, placed, its spawn function run
 * as a map load runs it (precaching allowed), linked. NULL when the text or its spawn function is missing. */
static unsigned long placed_objects;
static int edict_of_ref(uint32_t key){
    int i;
    for(i=1;i<sv.num_edicts;i++){edict_t *x=EDICT_NUM(i);if(!x->free && ref_of_edict(x)==key)return i;}
    return 0;
}
/* a free edict without growing into the map's reserve (the Halloween scene's rule, aw_halloween.c): a placed object
 * takes no reserved slot, so a full map leaves it out (refused, counted) */
static int object_edict_free(void){
    int i;edict_t *e;
    for(i=svs.maxclients+1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free && (e->freetime<2 || sv.time-e->freetime>.5))return 1;
    }
    return sv.num_edicts<MAX_EDICTS-8;
}
static edict_t *object_spawn(const char *text,unsigned long n,uint32_t key){
    char *copy;edict_t *e;dfunction_t *func;server_state_t was=sv.state;float origin[3],angles[3];
    if(!sv.active || n<2 || !object_edict_free() || !AW_ActorsRowPlace(key,origin,angles) ||
       !(copy=(char *)AW_TryMalloc(n+1)))return NULL;
    memcpy(copy,text+1,n-1);copy[n-1]=0;
    e=ED_Alloc();
    if(!ED_ParseEdict(copy,e) || !(func=ED_FindFunction(pr_strings+e->v.classname))){free(copy);ED_Free(e);return NULL;}
    free(copy);
    VectorCopy(origin,e->v.origin);VectorCopy(angles,e->v.angles);
    pr_global_struct->self=EDICT_TO_PROG(e);
    sv.state=ss_loading;PR_ExecuteProgram(func-pr_functions);sv.state=was;
    if(e->free)return NULL;
    VectorCopy(origin,e->v.origin);SV_LinkEdict(e,false);placed_objects++;
    return e;
}
static int placed_spawn(unsigned key){
    place_row_t r;unsigned long n=0;char *text;edict_t *e;
    if(key<AW_ACTORS_PLACED || !place_row((int)((key>>12)&0xFF),&r) || r.kind==PLACE_ITEM)return 0;
    if(r.kind!=PLACE_ACTOR && edict_of_ref(key))return 1;   /* an object already here (AliveWithRef sees actors only) */
    if(!(text=placed_text(&r,key,&n))){placed_no_text++;return 0;}
    e=r.kind==PLACE_ACTOR?AW_ActorsSpawnVisitor(text,n):object_spawn(text,n,key);
    free(text);
    if(!e)return 0;
    edict_refs_refresh();
    if(r.script!=AWM_NONE){
        int k;
        AW_MwvmDetach(key);       /* spawned again (a return, a load): its values parked, then on the new edict */
        k=attach_script(key,r.script,map_room?AWB_INTERIOR:0,NUM_FOR_EDICT(e),e->v.origin);
        if(k>=0)attach_edicts++;else attach_refused++;
    }
    placed_spawned++;
    return 1;
}
/* LOCAL dropped onto the ground under it (a short trace down; unchanged over nothing) */
static void place_ground(vec3_t local){
    vec3_t start,end;trace_t tr;
    VectorCopy(local,start);start[2]+=8;VectorCopy(local,end);end[2]-=256;
    tr=SV_Move(start,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,sv_player);
    if(!tr.startsolid && !tr.allsolid && tr.fraction<1)local[2]=tr.endpos[2];
}
/* OpenMW safePlaceObject: the spot DISTANCE (map units) in DIRECTION of BASE (the reference's feet) facing YAW; an actor
 * falls back to the next direction while the way from the spot to the reference is blocked */
static void place_spot(const vec3_t base,float yaw,float distance,int direction,int actor,vec3_t out){
    static const int order[4][4]={{0,3,2,1},{1,0,3,2},{2,1,0,3},{3,2,1,0}};
    vec3_t angles,forward,right,up,back;int i,k,d;trace_t tr;
    angles[0]=angles[2]=0;angles[1]=yaw;AngleVectors(angles,forward,right,up);
    if(direction<0 || direction>3)direction=0;
    for(i=0;i<4;i++){
        d=order[direction][i];
        for(k=0;k<3;k++){
            float v=d==0?forward[k]:d==1?-forward[k]:d==2?-right[k]:right[k];
            out[k]=base[k]+v*distance;
        }
        if(!actor)break;
        out[2]+=30*0.25f;                       /* 30 game units up for slopes, snapped down below */
        VectorCopy(base,back);back[2]+=20*0.25f;
        tr=SV_Move(out,vec3_origin,vec3_origin,back,MOVE_NOMONSTERS,sv_player);
        if(!(tr.fraction<1) && !tr.startsolid)break;   /* every way blocked: the last one stays, as OpenMW */
    }
    if(actor)place_ground(out);
}

/* --- summoned creatures (v0.0.62, SUMMONED-CREATURES-62; the rules of OpenMW 0.51 apps/openmw/mwmechanics/
 * summoning.cpp and actors.cpp, our own code). While a summoning effect (aw_effects.h AW_EffectSummon) is active on
 * the player, the creature its game setting names (maps/chim-summons.txt, tools/chim/actors.py summons_text) stands
 * by the player: it appears 120 game units in front of the caster (safePlaceObject, as PlaceAtPC places), follows
 * the player (AIFollow), comes back beside the player after a door or a load while the effect lasts, and goes when
 * the effect ends; when it dies its effect ends and its body goes a moment later. Its key is AW_ACTORS_SUMMONED | slot
 * (aw_actors.h); its entity is the actor table's base of the record. Appearing and going show Quake's teleport flash
 * (the original's summon start and end effects are not converted yet). Not yet: it does not fight the player's foes
 * (the fight has no actor-against-actor side: COMBAT-SUMMON-ALLY-62), and an NPC's summoning effect calls up nothing
 * (NPCs do not cast yet). Cost: a look over the 64 effect entries a frame while an effect is active; a spawn reads one
 * base from the actor table. */
#define SUMMONS 8                /* summoned creatures at once (the original has no limit; a spell has one or two) */
#define SUMMON_IDS 24            /* lines of maps/chim-summons.txt kept (the masters name 16, the expansions 6 more) */
#define SUMMON_DISTANCE (120*0.25f)   /* safePlaceObject's 120 game units, in map units */
#define SUMMON_BODY_SECONDS 3.0  /* a dead summoned creature's body stays this long (its death animation) */
typedef struct {unsigned char used,effect;int entity;uint32_t key;double dead_at,retry_at;} summon_t;
static summon_t summons[SUMMONS];
static struct {unsigned char effect;char id[32];} summon_ids[SUMMON_IDS];
static int summon_id_count=-1;   /* -1: the file not read yet */
static unsigned long summons_made,summons_ended,summons_died,summons_back,summons_no_creature;
static const char *summon_creature(int effect){
    int i;
    if(summon_id_count<0){
        static char text[1024];FILE *f=NULL;int n;char *p;
        summon_id_count=0;
        n=COM_FOpenFile("maps/chim-summons.txt",&f);
        if(!f)return NULL;
        if(n<=0 || n>=(int)sizeof(text) || fread(text,1,(size_t)n,f)!=(size_t)n)n=0;
        fclose(f);text[n]=0;
        for(p=text;*p && summon_id_count<SUMMON_IDS;){
            int number=0,k=0;
            while(*p>='0' && *p<='9' && number<1000){number=number*10+(*p-'0');p++;}
            if(*p==' ')p++;
            while(*p && *p!='\n' && *p!='\r'){if(k<31)summon_ids[summon_id_count].id[k++]=*p;p++;}
            summon_ids[summon_id_count].id[k]=0;
            if(k>0 && number<AW_EFFECT_COUNT && AW_EffectSummon(number))
                summon_ids[summon_id_count++].effect=(unsigned char)number;
            while(*p=='\n' || *p=='\r')p++;
        }
    }
    for(i=0;i<summon_id_count;i++)if(summon_ids[i].effect==effect)return summon_ids[i].id;
    return NULL;
}
static edict_t *summon_edict(const summon_t *s){
    edict_t *e;
    if(s->entity<=0 || s->entity>=sv.num_edicts)return NULL;
    e=EDICT_NUM(s->entity);
    return !e->free && ref_of_edict(e)==s->key?e:NULL;
}
static void summon_flash(const vec3_t at){
    MSG_WriteByte(&sv.datagram,svc_temp_entity);MSG_WriteByte(&sv.datagram,TE_TELEPORT);
    MSG_WriteCoord(&sv.datagram,at[0]);MSG_WriteCoord(&sv.datagram,at[1]);MSG_WriteCoord(&sv.datagram,at[2]);
}
/* the creature of S's effect by the player now (a new summon, or one back after a door or a load); 1 spawned */
static int summon_spawn(summon_t *s){
    const char *id=summon_creature(s->effect);unsigned long n=0;char *text,*out,tail[40];vec3_t base,local;float yaw;
    edict_t *e;int t;
    s->entity=0;
    if(!id || !sv_player || !(text=AW_ActorsBaseText(id,&n))){summons_no_creature++;return 0;}
    VectorCopy(sv_player->v.origin,base);base[2]+=sv_player->v.mins[2];yaw=sv_player->v.v_angle[1];
    place_spot(base,yaw,SUMMON_DISTANCE,0,1,local);
    t=sprintf(tail,"\n\"aw_ref\" \"%lu\"\n}",(unsigned long)s->key);
    out=n>=2 && text[n-1]=='}'?(char *)AW_TryMalloc(n+(unsigned long)t+1):NULL;
    if(out){memcpy(out,text,n-1);memcpy(out+n-1,tail,(size_t)t+1);}
    free(text);
    if(!out){summons_no_creature++;return 0;}
    e=AW_ActorsPlaceRow(s->key,local,yaw)?AW_ActorsSpawnVisitor(out,n-1+(unsigned long)t):NULL;
    free(out);
    if(!e){AW_ActorsPlacedForget(s->key);summons_no_creature++;return 0;}
    edict_refs_refresh();
    s->entity=NUM_FOR_EDICT(e);
    if(aw_mwscript_follow)aw_mwscript_follow(e,sv_player,0,NULL);
    summon_flash(e->v.origin);
    Con_DPrintf("Summon: %s (effect %d) by you.\n",id,s->effect);
    return 1;
}
static void summon_end(summon_t *s,int flash){
    edict_t *e=summon_edict(s);
    if(e){if(flash)summon_flash(e->v.origin);AW_ActorsRemove(e);edict_refs_refresh();}
    AW_ActorsPlacedForget(s->key);
    s->used=0;s->entity=0;
}
static void summons_tick(void){
    int i,k;aw_effect_info_t fx;
    if(!sv_player || !sv.active)return;
    for(i=0;i<SUMMONS;i++){
        summon_t *s=&summons[i];edict_t *e;float health=1;
        if(!s->used)continue;
        e=summon_edict(s);
        if(s->dead_at>0){if(realtime>=s->dead_at)summon_end(s,1);continue;}
        if(!AW_EffectsHasOn(AW_ACTOR_PLAYER_REF,s->effect)){summon_end(s,1);summons_ended++;continue;}
        if(e && (AW_CombatSlotState(e,&health)==2 || (e->v.health<=0 && e->v.deadflag))){
            /* it died: its effect ends (OpenMW Actors: a dead summon's effect is removed), the body goes soon */
            AW_EffectsEnd(NULL,AW_ACTOR_PLAYER_REF,s->effect);
            s->dead_at=realtime+SUMMON_BODY_SECONDS;summons_died++;continue;
        }
        if(!e && realtime>=s->retry_at){   /* gone with a door or a load: back by the player */
            if(summon_spawn(s))summons_back++;else s->retry_at=realtime+2;
        }
    }
    for(k=0;AW_EffectsAt(k,&fx);k++){
        int free_slot=-1;
        if(fx.owner!=AW_ACTOR_PLAYER_REF || !AW_EffectSummon(fx.effect))continue;
        for(i=0;i<SUMMONS;i++){
            if(summons[i].used && summons[i].effect==fx.effect)break;
            if(!summons[i].used && free_slot<0)free_slot=i;
        }
        if(i<SUMMONS || free_slot<0)continue;
        memset(&summons[free_slot],0,sizeof(summon_t));
        summons[free_slot].used=1;summons[free_slot].effect=(unsigned char)fx.effect;
        summons[free_slot].key=AW_ACTORS_SUMMONED|(uint32_t)free_slot;
        if(summon_spawn(&summons[free_slot]))summons_made++;
        else summons[free_slot].retry_at=realtime+2;
    }
}
/* one copy of row R (number ROW) at LOCAL on this map facing YAW: 1 made */
static int place_here(int row,const place_row_t *r,const vec3_t local,float yaw){
    if(r->kind==PLACE_ITEM){
        int at;int32_t where;float game[3];char id[64];
        if(!read_string(r->id,id,sizeof(id)) || !AW_PlacedWhere(local,&at,&where,game))return 0;
        return AW_InventoryPlace(id,at,where,game,yaw);
    }
    {uint32_t key=placed_key(row);
     if(!key || !AW_ActorsPlaceRow(key,local,yaw))return 0;
     if(!placed_spawn(key)){AW_ActorsPlacedForget(key);return 0;}
     return 1;}
}
static int place_call(int instance,int target,int function,const aw_mwcell_t *numbers,int count){
    place_row_t r;vec3_t base,local;float yaw=0;int i,row,copies=1,made=0;
    if(function==AWF_PLACEATPC || function==AWF_PLACEATME){
        edict_t *e=NULL;int n;
        if(count<4)return 0;                   /* not the compiler's carried form: stays "not yet" */
        row=numbers[3].i;copies=numbers[0].i;
        if(!place_row(row,&r)){places_refused++;return 1;}
        if(copies<1)return 1;                  /* OpenMW: none (a negative count is its script error) */
        if(copies>PLACE_COPIES)copies=PLACE_COPIES;
        if(function==AWF_PLACEATPC){
            if(!sv_player){places_refused++;return 1;}
            e=sv_player;VectorCopy(e->v.origin,base);base[2]+=e->v.mins[2];yaw=e->v.v_angle[1];
        }else{
            if((n=locate(instance,target,base))<0){places_refused++;return 1;}
            if(n>0 && (e=edict_of(n))!=NULL && !e->free){
                if(e->v.solid!=SOLID_BSP)base[2]+=e->v.mins[2];
                yaw=e==sv_player?e->v.v_angle[1]:e->v.angles[1];
            }
        }
        place_spot(base,yaw,numbers[1].f*0.25f,numbers[2].i,r.kind==PLACE_ACTOR,local);
        for(i=0;i<copies;i++)made+=place_here(row,&r,local,yaw);
    }else if(function==AWF_PLACEITEM){
        float game[3];
        if(count<5)return 0;
        row=numbers[4].i;
        if(!place_row(row,&r)){places_refused++;return 1;}
        for(i=0;i<3;i++)game[i]=numbers[i].f;
        yaw=-numbers[3].f;                     /* the original's degrees clockwise; Quake's yaw turns the other way */
        if(!AW_SourceToWorld(sv.name,game,local))for(i=0;i<3;i++)local[i]=game[i]/4.0f+room_shift[i];
        if(r.kind==PLACE_ACTOR)place_ground(local);
        made=place_here(row,&r,local,yaw);
    }else{                                     /* AWF_PLACEITEMCELL */
        float pos[3];int kind,here;long where;
        if(count<7)return 0;
        row=numbers[6].i;
        if(!place_row(row,&r)){places_refused++;return 1;}
        for(i=0;i<3;i++)pos[i]=numbers[i].f;
        yaw=numbers[3].f;kind=numbers[4].i;where=numbers[5].i;
        if(kind==AWM_MOVE_ROOM){
            here=map_room && where==map_room;
            /* an actor: the room map's units; an item: room-local game units */
            for(i=0;i<3;i++)local[i]=r.kind!=PLACE_ITEM?pos[i]:pos[i]/4.0f+room_shift[i];   /* an object as an actor */
        }else here=!map_room && AW_SourceToWorld(sv.name,pos,local);
        if(here){
            if(r.kind==PLACE_ACTOR)place_ground(local);
            made=place_here(row,&r,local,yaw);
        }else if(r.kind==PLACE_ITEM){
            /* the row lies in that place until it loads (a room: its number; outdoors: the exterior cell) */
            char id[64];int32_t w=kind==AWM_MOVE_ROOM?(int32_t)where:
                (int32_t)(((uint32_t)(int16_t)floor(pos[0]/8192.0f)<<16)|((uint32_t)(int)floor(pos[1]/8192.0f)&0xffffU));
            made=read_string(r.id,id,sizeof(id)) && aw_ledger_on &&
                 AW_LedgerPlaceItem(&aw_state,&aw_ledger,id,1,kind==AWM_MOVE_ROOM?AW_AT_ROOM:AW_AT_CELL,w,pos,yaw)!=0;
            if(made)places_away++;
        }else{
            /* an actor's row puts it there (a room: its map units; outdoors the island's: game units / 4) */
            uint32_t key=placed_key(row);float island[3];
            for(i=0;i<3;i++)island[i]=pos[i]*0.25f;
            made=key && AW_ActorsMoveTo(key,kind==AWM_MOVE_ROOM?where:0,kind==AWM_MOVE_ROOM?pos:island,yaw);
            if(made)places_away++;
        }
        copies=1;
    }
    places+=(unsigned long)made;places_refused+=(unsigned long)(copies-made);
    if(made)AW_MwvmStateChanged();
    return 1;
}
/* --- AIFollowCell, AIEscort, AIEscortCell and the followers through a door (v0.0.62, MWSCRIPT-POSITIONCELL-ACTORS-62;
 * the rules of OpenMW 0.51 aiextensions.cpp OpAiFollowCell / OpAiEscort / OpAiEscortCell, aifollow.cpp, aiescort.cpp
 * and actionteleport.cpp getFollowers, our own code). The packages run on the ambient tables (aw_ambient.c
 * AW_AmbientPackage). When a door, a travel or a region map's load takes the player away, each follower of the player
 * within 800 original units goes along: its package is kept to be applied where it arrives, its entity block kept for
 * the session (from the loaded map's entities, or for an outdoor actor from the CHIM frame map it was joined from), and
 * once the player stands in the new place it is spawned beside the player there, its row of the world change list
 * saying so (aw_actors.c AW_ActorsArriveHere), its own script attached again. A follower's VISI row of any room
 * (compiled for every AIFollow / AIFollowCell of the player) spawns it again in a room it was left in or saved in. */
static unsigned long escorts,escorts_refused,cell_follows,cell_follows_refused,crossed,crossed_lost;
#define CROSSING 8
static uint32_t crossing[CROSSING];static int crossing_count;
int (*aw_mwscript_package)(struct edict_s *e,struct edict_s *target,int kind,float hours,const float *point,long place);
int (*aw_mwscript_followers)(struct edict_s *player,struct edict_s **out,int max);
/* an actor of this map by its id (the player: "player"), as AIFollow names its target */
static edict_t *named_actor(const char *who){
    int i;
    if(!who)return NULL;
    if(!Q_strcasecmp((char *)who,"player"))return sv_player;
    for(i=1;i<sv.num_edicts;i++){
        edict_t *x=EDICT_NUM(i);eval_t *v;
        if(x->free || !(v=GetEdictFieldValue(x,"aw_source_id")) || !v->string)continue;
        if(!Q_strcasecmp(pr_strings+v->string,(char *)who))return x;
    }
    return NULL;
}
static int ai_package(int instance,int target,int function,const aw_mwcell_t *numbers,int count,
                      const unsigned char *strings,int nstrings){
    vec3_t at,point;edict_t *e,*t;int n=locate(instance,target,at),i,cell=function!=AWF_AIESCORT;
    int follow=function==AWF_AIFOLLOWCELL;long place=0;
    unsigned long *ok=follow?&cell_follows:&escorts,*refused=follow?&cell_follows_refused:&escorts_refused;
    e=n>0?edict_of(n):NULL;
    if(count<(cell?6:4) || !e || e->free || e==sv_player || !is_actor(e) || !aw_mwscript_package ||
       !(t=named_actor(call_string(strings,nstrings,0)))){(*refused)++;return 1;}
    if(cell){
        /* the compiler's carried form: duration, x y z (a room: its map's own units), kind, the room's number */
        place=numbers[4].i==AWM_MOVE_ROOM && numbers[5].i>0?(long)numbers[5].i:-1;
        for(i=0;i<3;i++)point[i]=numbers[1+i].f;
        if(place<0 && !follow){
            /* AIEscortCell outdoors: the original's units, converted for the map it is in */
            float game[3];for(i=0;i<3;i++)game[i]=point[i];
            if(!AW_SourceToWorld(sv.name,game,point))for(i=0;i<3;i++)point[i]=game[i]/4.0f+room_shift[i];
        }
    }else{
        /* AIEscort TARGET DURATION X Y Z: the original's units, converted for the map it is in (as AIFollow's) */
        float game[3];for(i=0;i<3;i++)game[i]=numbers[1+i].f;
        if(!AW_SourceToWorld(sv.name,game,point))for(i=0;i<3;i++)point[i]=game[i]/4.0f+room_shift[i];
    }
    if(aw_mwscript_package(e,t,follow?3:2,numbers[0].f,point,place))(*ok)++;else (*refused)++;
    return 1;
}
/* aw_scene.c: LEAVE 1 the next map loads (the followers' entities and packages kept), 0 the player stands there (they
 * arrive), -1 another map loaded (none come) */
static void followers(edict_t *p,int leave){
    int i,n;
    if(leave<0){crossing_count=0;return;}
    if(leave>0){
        edict_t *list[CROSSING];
        crossing_count=0;
        if(!p || !aw_mwscript_followers || !sv.worldmodel)return;
        n=aw_mwscript_followers(p,list,CROSSING);
        for(i=0;i<n;i++){
            eval_t *v=GetEdictFieldValue(list[i],"aw_ref");uint32_t ref=v && v->_float>0?(uint32_t)v->_float:0;
            unsigned long length;char map[64];
            if(!ref)continue;
            carry_text(ref);
            if(!carried_of(ref,&length) && AW_ActorsFrameMap(list[i],map,sizeof(map))){
                /* an outdoor actor: its entity from the frame map it was joined from */
                char *text=home_text(map,ref,&length);
                if(text){carry_copy(ref,text,length);free(text);}
            }
            if(carried_of(ref,&length))crossing[crossing_count++]=ref;else crossed_lost++;
        }
        return;
    }
    for(i=0;i<crossing_count;i++){
        uint32_t ref=crossing[i];unsigned long length=0;const char *text=carried_of(ref,&length);edict_t *e;vec3_t spot;
        float yaw=p->v.angles[1];int h;
        if(!text){crossed_lost++;continue;}
        /* behind the player, side by side when several (OpenMW puts them on the player's own spot); the heading table,
         * no sin or cos (the 68040 lacks them in hardware) */
        h=((int)((yaw+180.0f)*AW_PATH_FAN/360.0f+0.5f)+(i*2-(crossing_count-1))*2)%AW_PATH_FAN;if(h<0)h+=AW_PATH_FAN;
        spot[0]=p->v.origin[0]+aw_path_fan[h][0]*40.0f/AW_PATH_FAN_RADIUS;
        spot[1]=p->v.origin[1]+aw_path_fan[h][1]*40.0f/AW_PATH_FAN_RADIUS;spot[2]=p->v.origin[2];
        if(!AW_ActorsArriveHere(ref,spot,yaw)){crossed_lost++;continue;}
        AW_MwvmStateChanged();
        if(!(e=AW_ActorsSpawnVisitor(text,length))){crossed_lost++;continue;}
        if(SV_TestEntityPosition(e)){VectorCopy(p->v.origin,e->v.origin);SV_LinkEdict(e,false);}   /* no room: the player's spot */
        edict_refs_refresh();
        attach_visitor(ref,NUM_FOR_EDICT(e),e);
        crossed++;
    }
    crossing_count=0;
}
/* The player's control switches (v0.0.62, MWSCRIPT-PLAYER-CONTROL-62; OpenMW 0.51 controlextensions.cpp OpSetControl
 * and OpGetDisabled, miscextensions.cpp OpEnableTeleporting and OpEnableLevitation): the function's switch bit, set
 * on, off, or read; 0 for any other function. A reference before the call (player->DisablePlayerControls) changes
 * nothing: the switches are the player's. Kept in saved games (aw_story.c, the "amiwind:controls" named fact). */
static unsigned long control_calls,control_refused;
static int control_function(int function,int *verb){
    static const struct {short fn;short verb;short bit;} rows[]={
        {AWF_DISABLEPLAYERCONTROLS,0,AW_CONTROL_PLAYER},{AWF_ENABLEPLAYERCONTROLS,1,AW_CONTROL_PLAYER},
        {AWF_GETPLAYERCONTROLSDISABLED,2,AW_CONTROL_PLAYER},
        {AWF_DISABLEPLAYERFIGHTING,0,AW_CONTROL_FIGHTING},{AWF_ENABLEPLAYERFIGHTING,1,AW_CONTROL_FIGHTING},
        {AWF_GETPLAYERFIGHTINGDISABLED,2,AW_CONTROL_FIGHTING},
        {AWF_DISABLEPLAYERJUMPING,0,AW_CONTROL_JUMPING},{AWF_ENABLEPLAYERJUMPING,1,AW_CONTROL_JUMPING},
        {AWF_GETPLAYERJUMPINGDISABLED,2,AW_CONTROL_JUMPING},
        {AWF_DISABLEPLAYERLOOKING,0,AW_CONTROL_LOOKING},{AWF_ENABLEPLAYERLOOKING,1,AW_CONTROL_LOOKING},
        {AWF_GETPLAYERLOOKINGDISABLED,2,AW_CONTROL_LOOKING},
        {AWF_DISABLEPLAYERMAGIC,0,AW_CONTROL_MAGIC},{AWF_ENABLEPLAYERMAGIC,1,AW_CONTROL_MAGIC},
        {AWF_GETPLAYERMAGICDISABLED,2,AW_CONTROL_MAGIC},
        {AWF_DISABLEPLAYERVIEWSWITCH,0,AW_CONTROL_VIEWSWITCH},{AWF_ENABLEPLAYERVIEWSWITCH,1,AW_CONTROL_VIEWSWITCH},
        {AWF_GETPLAYERVIEWSWITCHDISABLED,2,AW_CONTROL_VIEWSWITCH},
        {AWF_DISABLEVANITYMODE,0,AW_CONTROL_VANITY},{AWF_ENABLEVANITYMODE,1,AW_CONTROL_VANITY},
        {AWF_GETVANITYMODEDISABLED,2,AW_CONTROL_VANITY},
        {AWF_DISABLETELEPORTING,0,AW_CONTROL_TELEPORTING},{AWF_ENABLETELEPORTING,1,AW_CONTROL_TELEPORTING},
        {AWF_DISABLELEVITATION,0,AW_CONTROL_LEVITATION},{AWF_ENABLELEVITATION,1,AW_CONTROL_LEVITATION}};
    int i;
    for(i=0;i<(int)(sizeof(rows)/sizeof(rows[0]));i++)if(rows[i].fn==function){*verb=rows[i].verb;return rows[i].bit;}
    return 0;
}
/* --- the small functions (v0.0.62, MWSCRIPT-SMALL-FUNCTIONS-62; the rules of OpenMW 0.51 named at each, our own code).
 * Angles and moves act on an object with an entity (an NPC, a creature, a door or an object the map keeps as an edict);
 * CHIM scenery without one cannot turn or move yet (counted, as Rotate). Cost: per call a few comparisons and at most
 * one link of the entity; GetDetected and GetLOS one world trace each; nothing resident but the tables below (32
 * starting places of 36 bytes, 16 knockdowns of 16; aw_crime.c 16 awareness rolls of 16: 1,664 bytes). */
static unsigned long transforms,transforms_missed,detections,detections_yes,sightings,knockouts,wakeups;
static void crime_thief(aw_crime_thief_t *t);
static int crime_witness(edict_t *e,aw_crime_witness_t *w);
static float fatigue_term_of(float current,float maximum);
static int disposition_weapon_drawn(void);
/* the object a transform call names: its entity, or NULL (counted as missed) */
static edict_t *transform_entity(int instance,int target){
    vec3_t at;int n=locate(instance,target,at);edict_t *e=n>0?edict_of(n):NULL;
    return !e || e->free?NULL:e;
}
static edict_t *transform_target(int instance,int target){
    edict_t *e=transform_entity(instance,target);
    if(!e)transforms_missed++;
    return e;
}
/* WORLD-BUTTONS-62: the reference a transform call names (the call's own object, or the named one), 0 for the
 * player or none; a CHIM placement without an entity moves through the movers table (aw_hinged_door.c) */
static unsigned long mover_moves;
static uint32_t transform_reference(int instance,int target){
    aw_mwvm_instance_t *in;
    if(target==AW_MWVM_PLAYER)return 0;
    if(target==AW_MWVM_SELF){in=AW_MwvmInstance(instance);return in?in->reference:0;}
    return AW_MwvmObjectReference(target);
}
/* SetAtStart (OpenMW transformationextensions.cpp OpSetAtStart: the reference back at its placed position and
 * rotation): a script's first change of an object's place or angles keeps where the map put it, until the next map */
#define STARTS 32
static struct {uint32_t ref;int entity,map;vec3_t origin,angles;} starts[STARTS];static int start_next;
static int start_find(edict_t *e){
    int i,n=NUM_FOR_EDICT(e);
    for(i=0;i<STARTS;i++)if(starts[i].map==attached_map && starts[i].entity==n && starts[i].ref)return i;
    return -1;
}
static void start_keep(edict_t *e){
    eval_t *v;int i;
    if(e==sv_player || start_find(e)>=0 || !(v=GetEdictFieldValue(e,"aw_ref")) || v->_float<=0)return;
    i=start_next;start_next=(start_next+1)%STARTS;
    starts[i].ref=(uint32_t)v->_float;starts[i].entity=NUM_FOR_EDICT(e);starts[i].map=attached_map;
    VectorCopy(e->v.origin,starts[i].origin);VectorCopy(e->v.angles,starts[i].angles);
}
/* the player standing on E goes with it (OpenMW moveStandingActors: elevators) */
static void move_by(edict_t *e,const vec3_t diff){
    start_keep(e);
    if(sv_player && e!=sv_player && ((int)sv_player->v.flags&FL_ONGROUND) && PROG_TO_EDICT(sv_player->v.groundentity)==e){
        VectorAdd(sv_player->v.origin,diff,sv_player->v.origin);SV_LinkEdict(sv_player,false);
    }
    VectorAdd(e->v.origin,diff,e->v.origin);SV_LinkEdict(e,false);transforms++;
}
static int actor_like(const edict_t *e){return e==sv_player || is_actor(e);}
/* ForceSneak / ClearForceSneak / GetForceSneak (v0.0.62, MWSCRIPT-GAP-FUNCTIONS-62; OpenMW controlextensions.cpp
 * OpSetMovementFlag, OpClearMovementFlag, OpGetForceSneak; creaturestats.cpp getStance: the forced flag makes the
 * actor sneak): the player's flag is aw_move.c's (the stance itself), an NPC's a reference in this short list, read by
 * the detection as the NPC sneaking. Not kept in saved games yet (OpenMW keeps the movement flags): a load clears them. */
#define FORCED 32
static uint32_t forced_sneak[FORCED];
static unsigned long forced_calls,forced_refused;
static unsigned long moon_calls,equipped_calls,equipped_missed;   /* v0.0.63, MWSCRIPT-GAPS-63 */
/* ForceRun / ClearForceRun / GetForceRun (v0.0.63, MWSCRIPT-GAPS-63; OpenMW controlextensions.cpp OpSetMovementFlag,
 * OpClearMovementFlag, OpGetForceRun): the player's flag is aw_move.c's (the player runs), an NPC's a reference in the
 * same kind of short list, read by the ambient tables' walk as the NPC running (AW_MwscriptForcedRun); kept in saved
 * games (the AWRN block) */
static uint32_t forced_run[FORCED];
/* GetAttacked (v0.0.63, MWSCRIPT-GAPS-63; OpenMW statsextensions.cpp OpGetAttacked, CreatureStats::getAttacked, set by
 * actorAttacked): the actors the player attacked (aw_combat.c aw_combat_attacked), a short list by reference; an entry
 * holds while the actor's fight goes on and goes when it ends (the combat layer fights the player only, so no other
 * actor attacks one). Not saved: a load ends every fight. */
#define ATTACKED 16
static uint32_t attacked[ATTACKED];static int attacked_next;
/* The werewolf set (v0.0.63, MWSCRIPT-GAPS-63; OpenMW 0.51 statsextensions.cpp OpSetWerewolf, OpIsWerewolf,
 * OpSetWerewolfAcrobatics, OpGetWerewolfKills; mechanicsmanagerimp.cpp setWerewolf, applyWerewolfAcrobatics;
 * player.cpp setWerewolfStats / restoreStats): the player's form with his own attributes and skills kept while the
 * werewolf's (the game settings fWerewolf*, handed by the compiler) stand, every item taken off; the NPCs a script
 * turned (a short list by reference); the werewolf kills. Kept in saved games (the AWWF block). The beast's body is
 * not drawn yet: the player keeps his own model (said in docs/MWSCRIPT_BYTECODE.md). */
#define WERE_NPCS 16
static aw_were_t were;static uint32_t were_npc[WERE_NPCS];
static unsigned long were_calls;
static void forced_reset(void){
    memset(&were,0,sizeof(were));memset(were_npc,0,sizeof(were_npc));aw_move_werewolf=0;
    memset(attacked,0,sizeof(attacked));attacked_next=0;
    memset(forced_sneak,0,sizeof(forced_sneak));aw_move_force_sneak=0;
    memset(forced_run,0,sizeof(forced_run));aw_move_force_run=0;
}
static int forced_find(uint32_t ref){int i;for(i=0;ref && i<FORCED;i++)if(forced_sneak[i]==ref)return i;return -1;}
static int forced_run_find(uint32_t ref){int i;for(i=0;ref && i<FORCED;i++)if(forced_run[i]==ref)return i;return -1;}
static int forced_run_export(unsigned char *out,int capacity){   /* aw_forced_rules.c */
    uint32_t refs[FORCED];int i,n=0;
    for(i=0;i<FORCED;i++)if(forced_run[i])refs[n++]=forced_run[i];
    return AW_ForcedRunPack(out,capacity,aw_move_force_run,refs,n);
}
static int forced_run_import(const unsigned char *p,int bytes){
    int player,n,k;
    memset(forced_run,0,sizeof(forced_run));aw_move_force_run=0;
    if((k=AW_ForcedRunUnpack(p,bytes,&player,forced_run,FORCED,&n))<0){memset(forced_run,0,sizeof(forced_run));return -1;}
    aw_move_force_run=player;
    return k;
}
/* the ambient tables' walk (aw_ambient.c walk_speed): 1 when a script forced E to run */
int AW_MwscriptForcedRun(struct edict_s *e){return forced_run_find(ref_of_edict(e))>=0;}
static void were_kill_hook(edict_t *e){
    /* OpenMW actors.cpp: the player kills an NPC while he is a werewolf: one more werewolf kill */
    if(were.player && e && !strcmp(pr_strings+e->v.classname,"aw_npc") && were.kills<0xFFFF){were.kills++;AW_MwvmStateChanged();}
}
static int were_export(unsigned char *out,int capacity){
    uint32_t refs[WERE_NPCS];int i,n=0;
    for(i=0;i<WERE_NPCS;i++)if(were_npc[i])refs[n++]=were_npc[i];
    return AW_WerePack(out,capacity,&were,refs,n);
}
static int were_import(const unsigned char *p,int bytes){
    int n,k;
    memset(&were,0,sizeof(were));memset(were_npc,0,sizeof(were_npc));
    if((k=AW_WereUnpack(p,bytes,&were,were_npc,WERE_NPCS,&n))<0){memset(&were,0,sizeof(were));memset(were_npc,0,sizeof(were_npc));return -1;}
    aw_move_werewolf=were.player;
    return k;
}
static int were_npc_find(uint32_t ref){int i;for(i=0;ref && i<WERE_NPCS;i++)if(were_npc[i]==ref)return i;return -1;}
static void attacked_hook(edict_t *e){
    uint32_t ref=ref_of_edict(e);int i;
    if(!ref)return;
    for(i=0;i<ATTACKED;i++)if(attacked[i]==ref)return;
    attacked[attacked_next]=ref;attacked_next=(attacked_next+1)%ATTACKED;
}
static int attacked_now(edict_t *e){
    uint32_t ref=ref_of_edict(e);int i;const aw_fighter_t *f;
    for(i=0;ref && i<ATTACKED;i++)if(attacked[i]==ref){
        if((f=AW_CombatFighter(e))!=NULL && !f->dead)return 1;
        if(!f){attacked[i]=0;return 0;}   /* the fight ended: the flag goes */
        return 1;                         /* dead: still the one that was attacked */
    }
    return 0;
}
/* Saved games (v0.0.62): "AWFS" u8 1 u8 the player forced u8 count, count x u32 NPC reference, f32 the screen's black
 * the fade goes to (big-endian); 11 + 4 x count bytes. OpenMW keeps the movement flags with the actors; the fade is
 * kept too, so a game saved dark loads dark until its script's FadeIn. */
static int forced_export(unsigned char *out,int capacity){   /* aw_forced_rules.c */
    uint32_t refs[FORCED];int i,n=0;
    for(i=0;i<FORCED;i++)if(forced_sneak[i])refs[n++]=forced_sneak[i];
    return AW_ForcedPack(out,capacity,aw_move_force_sneak,refs,n,V_ScreenFadeTarget());
}
static int forced_import(const unsigned char *p,int bytes){
    int player,n,k;float f;
    forced_reset();
    if((k=AW_ForcedUnpack(p,bytes,&player,forced_sneak,FORCED,&n,&f))<0){forced_reset();return -1;}
    aw_move_force_sneak=player;V_ScreenFade(f,0);
    return k;
}
/* GetDetected's two sides: ACTOR as the one noticed (the player's sheet, else an actor that does not sneak: OpenMW sets
 * the sneak stance of an NPC only by ForceSneak, not carried; its Chameleon and Invisibility), an NPC as the observer */
static void detect_thief(edict_t *a,aw_crime_thief_t *t){
    eval_t *r;uint32_t ref;aw_actor_t *x;
    memset(t,0,sizeof(*t));t->fatigue_term=1;
    if(a==sv_player){crime_thief(t);return;}
    r=GetEdictFieldValue(a,"aw_ref");ref=r && r->_float>0?(uint32_t)r->_float:0;
    if(!ref)return;
    t->sneaking=forced_find(ref)>=0;   /* a ForceSneak on the NPC (v0.0.62) */
    if((x=AW_ActorGet(ref,AW_ACTOR_NONE,0))!=NULL){
        t->fatigue_term=fatigue_term_of(x->dyn_cur[2],x->dyn_base[2]);
        if(x->reference)ref=x->reference;   /* the key the effects keep (as crime_witness reads Blind) */
    }
    t->chameleon=AW_EffectsMagnitude(ref,40,AW_EFFECT_NO_ARG);
    t->invisibility=AW_EffectsMagnitude(ref,39,AW_EFFECT_NO_ARG);
}
static int detect_observer(edict_t *o,aw_crime_witness_t *w){
    const aw_fighter_t *f;
    if(!o || o==sv_player || !crime_witness(o,w))return 0;    /* an NPC only */
    f=AW_CombatFighter(o);
    return w->can_report || (f && f->knocked && !f->dead);   /* awarenessCheck: alive (a knocked-down one still looks) */
}
/* OpenMW actors.cpp isActorDetected: an NPC observer, its own check; any other (a creature, no object): whether any NPC
 * within the actors' processing range (7168 original units) sees and notices ACTOR (creatures are not asked here) */
static int detected(edict_t *observer,edict_t *actor){
    aw_crime_thief_t t;aw_crime_witness_t w;int i;
    if(!actor || actor->free || !actor_like(actor))return 0;
    detect_thief(actor,&t);
    if(detect_observer(observer,&w))return AW_CrimeDetects(observer,&w.observer,actor,&t);
    for(i=1;i<sv.num_edicts;i++){
        edict_t *x=EDICT_NUM(i);vec3_t d;
        if(x==actor || x->free || strcmp(pr_strings+x->v.classname,"aw_npc"))continue;
        VectorSubtract(x->v.origin,actor->v.origin,d);
        if(Length(d)>7168*AW_MOVE_UNIT_SCALE || !detect_observer(x,&w))continue;
        if(AW_CrimeDetects(x,&w.observer,actor,&t))return 1;
    }
    return 0;
}
/* OnKnockout (OpenMW statsextensions.cpp OpOnKnockout, actors.cpp: the knocked-down flag holds for exactly one frame
 * when the knockdown starts): 1 in the frame a script first sees the actor's knockdown (a hit's or fatigue's) */
#define KNOCKS 16
static struct {int entity,map,knocked,frame;} knocks[KNOCKS];
static int knocked_now(edict_t *e){
    const aw_fighter_t *f=e?AW_CombatFighter(e):NULL;int i,n,slot=-1,down=f && f->knocked && !f->dead;
    if(!e)return 0;
    n=NUM_FOR_EDICT(e);
    for(i=0;i<KNOCKS;i++){
        if(knocks[i].entity==n && knocks[i].map==attached_map){slot=i;break;}
        if(slot<0 && (!knocks[i].knocked || knocks[i].map!=attached_map))slot=i;
    }
    if(!down){if(slot>=0 && knocks[slot].entity==n)knocks[slot].knocked=0;return 0;}
    if(slot<0)return 0;
    if(knocks[slot].entity!=n || knocks[slot].map!=attached_map || !knocks[slot].knocked){
        knocks[slot].entity=n;knocks[slot].map=attached_map;knocks[slot].knocked=1;knocks[slot].frame=host_framecount;
        knockouts++;
    }
    return knocks[slot].frame==host_framecount;
}
/* a point of the original's world (x y z) in this map's units, as Position converts it */
static void map_point(const float game[3],vec3_t local){
    int i;
    if(!AW_SourceToWorld(sv.name,(float *)game,local))for(i=0;i<3;i++)local[i]=game[i]/4.0f+room_shift[i];
}
static int small_call(int instance,int target,int function,const aw_mwcell_t *numbers,int count,
                      const unsigned char *strings,int nstrings,aw_mwcell_t *result){
    const char *axis=call_string(strings,nstrings,0);edict_t *e;
    switch(function){
    case AWF_GETANGLE:
        /* GetAngle AXIS (OpenMW OpGetAngle): the reference's rotation on the axis in degrees (aw_move_rules.c) */
        result->f=0;
        if(!axis || !(e=transform_target(instance,target)))return AW_MWVM_CALL_READ;
        result->f=AW_MoveScriptAngle(e==sv_player?sv_player->v.v_angle:e->v.angles,(unsigned char)axis[0],actor_like(e));
        return AW_MWVM_CALL_READ;
    case AWF_SETANGLE:{
        /* SetAngle AXIS DEGREES (OpenMW OpSetAngle, rotateObject): the reference turned to it; the player's view too */
        float q;int k;
        if(!axis || count<1)return 1;
        if(!(e=transform_entity(instance,target))){
            /* a scripted mover placement (WORLD-BUTTONS-62 part 2): its angle set, as an object's (not an actor's) */
            if((k=AW_MoveScriptAngleSet((unsigned char)axis[0],numbers[0].f,0,&q))>=0 &&
               AW_MoverSetAngle(transform_reference(instance,target),k,q)){mover_moves++;transforms++;}
            else transforms_missed++;
            return 1;
        }
        if((k=AW_MoveScriptAngleSet((unsigned char)axis[0],numbers[0].f,actor_like(e),&q))<0){transforms_missed++;return 1;}
        start_keep(e);
        if(e==sv_player){sv_player->v.v_angle[k]=q;VectorCopy(sv_player->v.v_angle,sv_player->v.angles);sv_player->v.fixangle=1;}
        else{e->v.angles[k]=q;SV_LinkEdict(e,false);}
        transforms++;return 1;}
    case AWF_MOVE:case AWF_MOVEWORLD:{
        /* Move / MoveWorld AXIS UNITS-A-SECOND (OpenMW OpMove: along the object's own axes; OpMoveWorld: the world's;
         * times the frame's duration; the actors standing on it go along) */
        vec3_t diff,f,r,u;float step=count>=1?numbers[0].f*(float)host_frametime*AW_MOVE_UNIT_SCALE:0;
        if(!axis)return 1;
        if(!(e=transform_entity(instance,target))){
            /* no entity: a scripted mover the CHIM world draws as a placement (the Ghostgate portcullises) moves
             * along the world's axes; Move along its own axes needs its angles: not yet (counted as missed) */
            int k=tolower((unsigned char)axis[0])-'x';
            diff[0]=diff[1]=diff[2]=0;
            if(function==AWF_MOVEWORLD && k>=0 && k<=2){
                diff[k]=step;
                if(AW_MoverShift(transform_reference(instance,target),diff)){mover_moves++;transforms++;return 1;}
            }
            transforms_missed++;return 1;
        }
        if(function==AWF_MOVE){
            AngleVectors(e->v.angles,f,r,u);
            if(!AW_MoveScriptLocal(f,r,u,(unsigned char)axis[0],step,diff)){transforms_missed++;return 1;}
        }else{
            int k=tolower((unsigned char)axis[0])-'x';
            if(k<0 || k>2){transforms_missed++;return 1;}
            diff[0]=diff[1]=diff[2]=0;diff[k]=step;
        }
        move_by(e,diff);return 1;}
    case AWF_SETPOS:{
        /* SetPos AXIS VALUE (OpenMW OpSetPos): the reference's position on the axis, the original's units */
        float game[3];vec3_t local;int k;
        if(!axis || count<1 || !(e=transform_target(instance,target)))return 1;
        k=tolower((unsigned char)axis[0])-'x';
        if(k<0 || k>2){transforms_missed++;return 1;}
        start_keep(e);
        to_game_units(e->v.origin,game);game[k]=numbers[0].f;map_point(game,local);
        VectorSubtract(local,e->v.origin,local);local[(k+1)%3]=local[(k+2)%3]=0;   /* only that axis moves */
        VectorAdd(e->v.origin,local,e->v.origin);SV_LinkEdict(e,false);transforms++;
        return 1;}
    case AWF_SETATSTART:{
        int i;
        if(!(e=transform_entity(instance,target))){
            /* a scripted mover placement back where the game data put it (WORLD-BUTTONS-62) */
            if(AW_MoverAtStart(transform_reference(instance,target))){mover_moves++;transforms++;}
            else transforms_missed++;
            return 1;
        }
        if((i=start_find(e))>=0){
            VectorCopy(starts[i].origin,e->v.origin);VectorCopy(starts[i].angles,e->v.angles);SV_LinkEdict(e,false);
        }   /* never moved by a script on this map: it stands where it started */
        transforms++;return 1;}
    case AWF_FACE:{
        /* Face X Y (OpenMW aiextensions.cpp OpFace, aiface.cpp: an actor, not the player, turns to face the point; the
         * original turns it at its turning speed, here at once); Q_atan2: no atan the 68040 lacks */
        float game[3];vec3_t local;
        if(count<2 || !(e=transform_target(instance,target)))return 1;
        if(e==sv_player || !is_actor(e)){transforms_missed++;return 1;}
        to_game_units(e->v.origin,game);game[0]=numbers[0].f;game[1]=numbers[1].f;map_point(game,local);
        if(local[0]!=e->v.origin[0] || local[1]!=e->v.origin[1])
            e->v.angles[1]=(float)(Q_atan2(local[1]-e->v.origin[1],local[0]-e->v.origin[0])*180/M_PI);
        transforms++;return 1;}
    case AWF_GETDETECTED:{
        /* GetDetected ACTOR (OpenMW aiextensions.cpp OpGetDetected): see detected() above */
        vec3_t at;int n=locate(instance,target,at);
        result->i=detected(n>0?edict_of(n):NULL,named_actor(axis));
        detections++;if(result->i)detections_yes++;
        return AW_MWVM_CALL_READ;}
    case AWF_GETLOS:case AWF_GETLINEOFSIGHT:{
        /* GetLOS ACTOR (OpenMW OpGetLineOfSight, World::getLOS): both actors, enabled, eye to eye through the world */
        vec3_t at;int n=locate(instance,target,at);edict_t *t=named_actor(axis);
        e=n>0?edict_of(n):NULL;
        result->i=e && t && actor_like(e) && actor_like(t) && AW_CrimeSight(e,t);
        sightings++;return AW_MWVM_CALL_READ;}
    case AWF_GETINTERIOR:
        /* GetInterior (OpenMW cellextensions.cpp OpGetInterior): 1 while the player is in an interior (a room map) */
        result->i=map_room!=0;return AW_MWVM_CALL_READ;
    case AWF_GETCURRENTWEATHER:
        result->i=AW_WeatherCurrent();return AW_MWVM_CALL_READ;
    case AWF_CHANGEWEATHER:
        /* ChangeWeather REGION WEATHER (OpenMW skyextensions.cpp OpChangeWeather, weather.cpp changeWeather): the
         * compiler hands the region's catalogue index first; aw_weather.c keeps it until the region's next change */
        if(count<2 || !AW_WeatherChangeByScript(numbers[0].i,numbers[1].i)){weather_refused++;return 1;}
        weather_calls++;AW_MwvmStateChanged();return 1;
    case AWF_MODREGION:{
        /* ModRegion REGION CHANCES... (OpenMW OpModRegion, weather.cpp modRegion: the first chances replaced, kept for
         * the game and saved) */
        int chances[AW_WEATHERS],k,n=count-1;
        if(n>AW_WEATHERS)n=AW_WEATHERS;
        for(k=0;k<n;k++)chances[k]=numbers[1+k].i;
        if(count<1 || !AW_WeatherModRegionByScript(numbers[0].i,chances,n<0?0:n)){weather_refused++;return 1;}
        weather_calls++;AW_MwvmStateChanged();return 1;}
    case AWF_ONKNOCKOUT:{
        vec3_t at;int n=locate(instance,target,at);e=n>0?edict_of(n):NULL;
        result->i=e && e!=sv_player && knocked_now(e);return AW_MWVM_CALL_READ;}
    case AWF_WAKEUPPC:
        if(AW_RestWake()){wakeups++;AW_MwvmStateChanged();}
        return 1;
    case AWF_ROTATEWORLD:{
        /* RotateWorld AXIS DEGREES-A-SECOND (OpenMW OpRotateWorld: about the world's axis, times the frame's duration;
         * an actor only about z). About z that is Rotate's turn; about x and y it is taken as Quake's pitch and roll,
         * exact for an object standing upright (the game's one use turns a door about z) */
        float step=count>=1?numbers[0].f*(float)host_frametime:0;int k;
        if(!axis)return 1;
        if(!(e=transform_entity(instance,target))){
            /* a scripted mover placement (the Shishi skull, RotateWorld z): as an upright entity turns */
            float d[3]={0,0,0};
            k=tolower((unsigned char)axis[0]);
            if(k=='z')d[1]=-step;else if(k=='x')d[0]=step;else if(k=='y')d[2]=step;
            if(k>='x' && k<='z' && AW_MoverTurn(transform_reference(instance,target),d)){mover_moves++;transforms++;}
            else transforms_missed++;
            return 1;
        }
        k=tolower((unsigned char)axis[0]);
        if(k!='z' && ((k!='x' && k!='y') || actor_like(e))){transforms_missed++;return 1;}
        start_keep(e);
        if(k=='z')e->v.angles[1]-=step;else if(k=='x')e->v.angles[0]+=step;else e->v.angles[2]+=step;
        SV_LinkEdict(e,false);transforms++;return 1;}
    case AWF_GETPCSNEAKING:
        /* GetPCSneaking (OpenMW controlextensions.cpp OpGetPcSneaking, isSneaking): the player sneaks (aw_move.c) */
        result->i=AW_MoveSneaking();return AW_MWVM_CALL_READ;
    case AWF_GETWEAPONDRAWN:{
        /* GetWeaponDrawn (OpenMW miscextensions.cpp OpGetWeaponDrawn: the draw state is the weapon and it shows): the
         * player's readied hands without a torch (the disposition's rule); an actor while it fights (the combat layer
         * readies its weapon for the fight) */
        vec3_t at;int n=locate(instance,target,at);const aw_fighter_t *f;
        e=n>0?edict_of(n):NULL;
        if(e==sv_player || target==AW_MWVM_PLAYER)result->i=disposition_weapon_drawn();
        else result->i=e && (f=AW_CombatFighter(e))!=NULL && !f->dead;
        return AW_MWVM_CALL_READ;}
    case AWF_SETDELETE:
        /* SetDelete 1 / 0 (OpenMW miscextensions.cpp OpSetDelete: the reference deleted from the world, or back): here
         * the object state's Disable and Enable, kept in saved games; any other number does nothing (OpenMW: an
         * error) */
        if(count<1 || (numbers[0].i!=0 && numbers[0].i!=1))return 1;
        host_object(instance,target,numbers[0].i?AWM_DISABLE:AWM_ENABLE,0);AW_MwvmStateChanged();transforms++;
        return 1;
    }
    return 0;
}
/* GetResist* / SetResist* / ModResist* (v0.0.62, MWSCRIPT-GAP-FUNCTIONS-62; OpenMW 0.51 statsextensions.cpp
 * OpGetMagicEffect, OpSetMagicEffect, OpModMagicEffect): the value is the resistance's magnitude less its weakness's,
 * the elemental shield added for fire, frost and shock; Set moves the actor's base modifier by the difference to the
 * new value, Mod by the number (aw_effects.c AW_EffectsBaseModify, kept in saved games with the effects) */
static const struct {int get,set,mod,effect,weakness,shield;} resists[]={
    {AWF_GETRESISTFIRE,AWF_SETRESISTFIRE,AWF_MODRESISTFIRE,90,28,4},
    {AWF_GETRESISTFROST,AWF_SETRESISTFROST,AWF_MODRESISTFROST,91,29,6},
    {AWF_GETRESISTSHOCK,AWF_SETRESISTSHOCK,AWF_MODRESISTSHOCK,92,30,5},
    {AWF_GETRESISTMAGICKA,AWF_SETRESISTMAGICKA,AWF_MODRESISTMAGICKA,93,31,-1},
    {AWF_GETRESISTDISEASE,AWF_SETRESISTDISEASE,AWF_MODRESISTDISEASE,94,32,-1},
    {AWF_GETRESISTBLIGHT,AWF_SETRESISTBLIGHT,AWF_MODRESISTBLIGHT,95,33,-1},
    {AWF_GETRESISTCORPRUS,AWF_SETRESISTCORPRUS,AWF_MODRESISTCORPRUS,96,34,-1},
    {AWF_GETRESISTPOISON,AWF_SETRESISTPOISON,AWF_MODRESISTPOISON,97,35,-1},
    {AWF_GETRESISTNORMALWEAPONS,AWF_SETRESISTNORMALWEAPONS,AWF_MODRESISTNORMALWEAPONS,98,36,-1},
    {AWF_GETRESISTPARALYSIS,AWF_SETRESISTPARALYSIS,AWF_MODRESISTPARALYSIS,99,-1,-1},
    /* v0.0.63 (UNDERWATER-BREATH-62): Get/Set/ModWaterBreathing, the same calls on Water Breathing; the read also
     * counts the always-active spells of the actor's list (the Argonians' ability), as OpenMW's magic effects do */
    {AWF_GETWATERBREATHING,AWF_SETWATERBREATHING,AWF_MODWATERBREATHING,AW_EFFECT_WATER_BREATHING,-1,-1},
    /* v0.0.63 (MWSCRIPT-GAPS-63, the functions no game script calls: the console's): the other magic effects of the
     * script family, by OpenMW 0.51 statsextensions.cpp's table (OpGetMagicEffect / OpSetMagicEffect /
     * OpModMagicEffect): Chameleon, Water Walking, Swift Swim (SwimSpeed), Jump (SuperJump), Levitate (Flying), Shield
     * (ArmorBonus), Sound (CastPenalty), Silence, Blind, Paralyze, Invisibility, Fortify Attack (AttackBonus),
     * Sanctuary (DefendBonus); no weakness, no shield; the read counts the always-active spells as Water Breathing's */
    {AWF_GETCHAMELEON,AWF_SETCHAMELEON,AWF_MODCHAMELEON,40,-1,-1},
    {AWF_GETWATERWALKING,AWF_SETWATERWALKING,AWF_MODWATERWALKING,2,-1,-1},
    {AWF_GETSWIMSPEED,AWF_SETSWIMSPEED,AWF_MODSWIMSPEED,1,-1,-1},
    {AWF_GETSUPERJUMP,AWF_SETSUPERJUMP,AWF_MODSUPERJUMP,9,-1,-1},
    {AWF_GETFLYING,AWF_SETFLYING,AWF_MODFLYING,10,-1,-1},
    {AWF_GETARMORBONUS,AWF_SETARMORBONUS,AWF_MODARMORBONUS,3,-1,-1},
    {AWF_GETCASTPENALTY,AWF_SETCASTPENALTY,AWF_MODCASTPENALTY,48,-1,-1},
    {AWF_GETSILENCE,AWF_SETSILENCE,AWF_MODSILENCE,46,-1,-1},
    {AWF_GETBLINDNESS,AWF_SETBLINDNESS,AWF_MODBLINDNESS,AW_EFFECT_BLIND,-1,-1},
    {AWF_GETPARALYSIS,AWF_SETPARALYSIS,AWF_MODPARALYSIS,45,-1,-1},
    {AWF_GETINVISIBLE,AWF_SETINVISIBLE,AWF_MODINVISIBLE,39,-1,-1},
    {AWF_GETATTACKBONUS,AWF_SETATTACKBONUS,AWF_MODATTACKBONUS,AW_EFFECT_FORTIFY_ATTACK,-1,-1},
    {AWF_GETDEFENDBONUS,AWF_SETDEFENDBONUS,AWF_MODDEFENDBONUS,AW_EFFECT_SANCTUARY,-1,-1}};
#define RESIST_PASSIVE_FIRST 10   /* Water Breathing's row and the rows after it count the always-active spells */
static unsigned long resist_calls,resist_refused,fades;
static float resist_value(uint32_t owner,int k){
    float v=AW_EffectsMagnitude(owner,resists[k].effect,AW_EFFECT_NO_ARG);
    if(resists[k].weakness>=0)v-=AW_EffectsMagnitude(owner,resists[k].weakness,AW_EFFECT_NO_ARG);
    if(resists[k].shield>=0)v+=AW_EffectsMagnitude(owner,resists[k].shield,AW_EFFECT_NO_ARG);
    return v;
}
/* HasSoulGem / RemoveSoulGem CREATURE [COUNT] (v0.0.62; OpenMW 0.51 miscextensions.cpp OpHasSoulGem, OpRemoveSoulGem):
 * the player's filled soul gems whose soul is that creature (aw_actorstate.c AW_Gem*: the soul as its ACTB row); Remove
 * takes COUNT of them (1 when not given), each gem item leaving the inventory with its soul, as OpenMW removes the
 * item (Azura's Star too). Another actor carries no filled gems here: 0, nothing. */
static unsigned long gem_calls,hurts,drops;
static int soul_gems(int function,int target,const char *creature,int count){
    int row,i,n=0;char gem[40];int soul;
    if(target!=AW_MWVM_PLAYER || !creature || !AW_MwscriptActors() || (row=AW_ActorFind(creature))<0)return 0;
    gem_calls++;
    for(i=AW_GemCount()-1;i>=0;i--){
        if(!AW_GemAt(i,gem,sizeof(gem),&soul) || soul!=row)continue;
        if(function==AWF_HASSOULGEM){n++;continue;}
        if(n>=count)break;
        AW_GemRemove(i);AW_ItemAdd(&aw_state,gem,-1);n++;
    }
    if(function==AWF_REMOVESOULGEM && n)AW_MwvmStateChanged();
    return n;
}
/* --- OnPCEquip and PCSkipEquip (v0.0.62, MWSCRIPT-GAP-FUNCTIONS-62; OpenMW 0.51 mwgui/inventorywindow.cpp useItem).
 * The compiler's EQUP rows name the carried items whose script declares OnPCEquip or PCSkipEquip, with the slots of
 * those locals. When the player equips one (the inventory window, aw_worldui.c): its script's PCSkipEquip 1 = the
 * script takes the equipping: OnPCEquip is set to 1 and nothing is worn; else OnPCEquip 0, the item is worn, then
 * OnPCEquip 1. The item's script then runs while the item is carried (OpenMW runs the scripts of the player's items),
 * as an instance of its own key (CARRIED_KEY and the item id's hash) that follows the player, its values parked on a
 * map change and saved with every object's; it reads OnPCEquip, shows its message box (with its buttons; the choice
 * read by GetButtonPressed) and resets it, as in the original. Not kept: which carried items run (after a load an
 * item's script runs again from its next equipping). */
#define CARRIED_ITEMS 16
#define CARRIED_KEY 0xFE000000u
typedef struct {int script,on,skip;} equip_row_t;
static struct {uint32_t key;char id[64];int script;} carried_items[CARRIED_ITEMS];
static unsigned long equip_reactions,equip_skipped,carried_refused;
static uint32_t carried_key(const char *id){
    uint32_t h=2166136261u;
    for(;*id;id++)h=(h^(uint32_t)(unsigned char)tolower((unsigned char)*id))*16777619u;
    return CARRIED_KEY|(h&0xFFFFFFu);
}
static int equip_row(const char *id,equip_row_t *out){
    uint32_t off,rows,bytes,i;char name[64];
    if(!resident || !id || !AW_MwvmSection("EQUP",&off,&rows,&bytes) || off+bytes>resident_bytes || 8ul*rows>bytes)
        return 0;
    for(i=0;i<rows;i++){
        const unsigned char *r=resident+off+8*i;
        if(!read_string((r[0]<<8)|r[1],name,sizeof(name)) || !same_id(name,id))continue;
        out->script=(r[2]<<8)|r[3];out->on=r[4]==0xFF?-1:r[4];out->skip=r[5]==0xFF?-1:r[5];
        return 1;
    }
    return 0;
}
static int instance_of_reference(uint32_t key){
    int i;
    for(i=0;i<AW_MWVM_INSTANCES;i++){
        aw_mwvm_instance_t *in=AW_MwvmInstance(i);
        if(in && (in->flags&AWI_USED) && in->reference==key)return i;
    }
    return -1;
}
static void carried_add(const char *id,int script){
    uint32_t key=carried_key(id);int i,slot=-1;
    for(i=0;i<CARRIED_ITEMS;i++){
        if(carried_items[i].key==key)return;
        if(slot<0 && !carried_items[i].key)slot=i;
    }
    if(slot<0){carried_refused++;return;}
    carried_items[slot].key=key;carried_items[slot].script=script;
    Q_snprintf(carried_items[slot].id,sizeof(carried_items[slot].id),"%s",id);
}
/* every frame before the scripts run: each carried item's script attached (again after a map change) at the
 * player; one no longer carried leaves (its values parked) */
static void carried_tick(const float player[3]){
    int i,k;
    for(i=0;i<CARRIED_ITEMS;i++){
        if(!carried_items[i].key)continue;
        if(AW_StateGet(&aw_state,AW_ITEM,carried_items[i].id)<=0){AW_MwvmDetach(carried_items[i].key);carried_items[i].key=0;continue;}
        if((k=instance_of_reference(carried_items[i].key))<0 &&
           (k=AW_MwvmAttach(carried_items[i].key,carried_items[i].script,0,-1,player))<0){carried_refused++;continue;}
        AW_MwvmSetOrigin(k,player);
    }
}
static void carried_reset(void){memset(carried_items,0,sizeof(carried_items));}
/* the inventory window's Equip: PHASE 0 before (1: the script takes it, nothing is worn), 1 after it was worn */
static int equip_script(const aw_inventory_item_t *it,int phase){
    equip_row_t r;uint32_t key;
    if(!it || !it->script[0] || !equip_row(it->id,&r))return 0;
    key=carried_key(it->id);carried_add(it->id,r.script);
    /* PHASE 2, taken off (OpenMW 0.51 InventoryStore::unequipSlot): OnPCEquip 0, so a script that acts while its
     * item is worn (ouch_sunder, MWSCRIPT-UNPLACED-RECORD-SCRIPTS-61) stops acting */
    if(phase==2){if(r.on>=0){AW_MwvmLocalSet(key,r.script,r.on,0);AW_MwvmStateChanged();}return 0;}
    if(phase==0){
        aw_mwcell_t v;int s;
        if(r.skip>=0 && AW_MwvmLocalGet(key,r.skip,&s,&v) && s==r.script && v.i==1){
            if(r.on>=0)AW_MwvmLocalSet(key,r.script,r.on,1);
            equip_skipped++;AW_MwvmStateChanged();return 1;
        }
        if(r.on>=0)AW_MwvmLocalSet(key,r.script,r.on,0);
        return 0;
    }
    if(r.on>=0){AW_MwvmLocalSet(key,r.script,r.on,1);equip_reactions++;AW_MwvmStateChanged();}
    return 0;
}
/* Resurrect (v0.0.62; OpenMW 0.51 statsextensions.cpp OpResurrect: an actor other than the player is reset to its game
 * data, "as per original engine behavior": alive, its stats, inventory and place the data's). Its change row, live
 * record and body contents go (aw_actors.c AW_ActorsReset), the entity is spawned again from its map's entity block
 * (its data place), or, outdoors where the actor table spawns it, from its record's base text where it stands, its
 * script kept with its values. The player is not resurrected here (his death has its own screen): nothing. */
static unsigned long resurrections,resurrect_refused;
static int resurrect(int instance,int target){
    vec3_t at,origin;int n=locate(instance,target,at),i,script=-1;edict_t *e=n>0?edict_of(n):NULL,*x;uint32_t ref;
    const char *ents,*block=NULL;char *own=NULL,*text=NULL,id[64],tail[40];unsigned long len=0;float yaw;eval_t *v;
    if(target==AW_MWVM_PLAYER || !e || e->free || e==sv_player || !is_actor(e) || !(ref=ref_of_edict(e))){
        resurrect_refused++;return 1;}
    VectorCopy(e->v.origin,origin);yaw=e->v.angles[1];id[0]=0;
    if((v=GetEdictFieldValue(e,"aw_source_id"))!=NULL && v->string){
        strncpy(id,pr_strings+v->string,sizeof(id)-1);id[sizeof(id)-1]=0;}
    ents=sv.worldmodel?sv.worldmodel->entities:NULL;
    if(ents)block=AW_MwvmEntityBlock(ents,(unsigned long)strlen(ents),ref,&len);
    if(!block && id[0] && (own=AW_ActorsBaseText(id,&len))!=NULL && len>=2 && own[len-1]=='}'){
        int t=sprintf(tail,"\n\"aw_ref\" \"%lu\"\n}",(unsigned long)ref);
        if((text=(char *)AW_TryMalloc(len+(unsigned long)t+1))!=NULL){
            memcpy(text,own,len-1);memcpy(text+len-1,tail,(size_t)t+1);len=len-1+(unsigned long)t;block=text;}
    }
    if(!block){free(own);resurrect_refused++;return 1;}
    for(i=0;i<AW_MWVM_INSTANCES;i++){
        aw_mwvm_instance_t *in=AW_MwvmInstance(i);
        if(in && in->reference==ref){script=in->script;break;}
    }
    AW_ActorsReset(ref);
    if(text)AW_ActorsArriveHere(ref,origin,yaw);      /* outdoors from the base text: where it lay */
    AW_ActorsRemove(e);
    x=AW_ActorsSpawnVisitor(block,len);
    free(own);free(text);
    edict_refs_refresh();
    if(x && script>=0){
        AW_MwvmDetach(ref);
        if(AW_MwvmAttach(ref,script,map_room?AWB_INTERIOR:0,NUM_FOR_EDICT(x),x->v.origin)>=0)attach_edicts++;
        else attach_refused++;
    }
    if(x)resurrections++;else resurrect_refused++;
    AW_MwvmStateChanged();
    return 1;
}
/* HitOnMe WEAPON (MWSCRIPT-INVENTORY-HITONME-62; OpenMW 0.51 miscextensions.cpp OpHitOnMe: 1 when the actor's last hit
 * object is that weapon id, and then it is cleared; Creature/Npc::onHit keeps the weapon of every successful blow, the
 * heart's LorkhanHeart waits for Keening and Sunder). The player's right-hand weapon id is kept per victim reference by
 * the combat's hook (aw_combat.c AW_CombatLastHit*, 8 rows); an NPC's or a creature's weapon has no record id in
 * its sheet yet, so a blow on the player is counted, not kept. */
static unsigned long hits_kept,hits_npc,hits_read,hits_matched;
static unsigned long id_hash(const char *s){
    unsigned long h=2166136261UL;
    for(;s && *s;s++)h=((h^(unsigned long)(unsigned char)tolower((unsigned char)*s))*16777619UL)&0xffffffffUL;
    return h;
}
static void weapon_hit(edict_t *attacker,edict_t *victim){
    const char *id;uint32_t ref;
    if(!attacker || !victim)return;
    if(attacker!=sv_player){hits_npc++;return;}
    id=aw_state.inventory.equipped[AW_SLOT_RIGHT];
    if(!id[0] || !(ref=ref_of_edict(victim)))return;
    AW_CombatLastHitSet(ref,id_hash(id));hits_kept++;
}
static int hit_on_me(int instance,int target,const char *weapon){
    vec3_t at;int n;uint32_t ref;
    hits_read++;
    if(!weapon || !*weapon || target==AW_MWVM_PLAYER)return 0;
    n=locate(instance,target,at);
    ref=n>0?ref_of_edict(edict_of(n)):0;
    if(!ref)ref=target_reference(instance,target);
    if(!AW_CombatLastHitTake(ref,id_hash(weapon)))return 0;
    hits_matched++;return 1;
}
/* v0.0.63 (MWSCRIPT-GAPS-63): functions no game script of the three masters calls, carried out for the console and
 * for add-on content. Every one is a read or a view switch; nothing resident is added (a few counters). */
static unsigned long uncalled_calls,uncalled_refused;
static int actor_touches(const edict_t *x,const edict_t *e,int standing){
    int i;
    if(!x || x->free || x==e || (x!=sv_player && !is_actor(x)) || x->v.health<=0)return 0;
    if(standing)return ((int)x->v.flags&FL_ONGROUND) && PROG_TO_EDICT(x->v.groundentity)==e;
    for(i=0;i<3;i++)if(x->v.absmin[i]>e->v.absmax[i]+1 || x->v.absmax[i]<e->v.absmin[i]-1)return 0;
    return 1;
}
static int uncalled_call(int instance,int target,int function,const aw_mwcell_t *numbers,int count,
                         const unsigned char *strings,int nstrings,aw_mwcell_t *result){
    edict_t *e;
    switch(function){
    /* --- batch 2 (v0.0.63, MWSCRIPT-GAPS-63) --- */
    case AWF_GETPCRUNNING:
        /* GetPCRunning (controlextensions.cpp OpGetPcRunning: running and moving): the player's last move (aw_move.c) */
        result->i=AW_MovePlayerRunning();return AW_MWVM_CALL_READ;
    case AWF_FORCEJUMP:case AWF_CLEARFORCEJUMP:case AWF_FORCEMOVEJUMP:case AWF_CLEARFORCEMOVEJUMP:
        /* ForceJump / ForceMoveJump and their Clear (controlextensions.cpp OpSetMovementFlag, OpClearMovementFlag:
         * Flag_ForceJump jumps, Flag_ForceMoveJump jumps while moving): the player's jump button held by the flag
         * (aw_move.c); another actor has no jump here: nothing */
        if(target!=AW_MWVM_PLAYER){uncalled_refused++;return 1;}
        if(function==AWF_FORCEJUMP || function==AWF_CLEARFORCEJUMP)aw_move_force_jump=function==AWF_FORCEJUMP;
        else aw_move_force_move_jump=function==AWF_FORCEMOVEJUMP;
        uncalled_calls++;return 1;
    case AWF_GETFORCEJUMP:result->i=target==AW_MWVM_PLAYER && aw_move_force_jump;return AW_MWVM_CALL_READ;
    case AWF_GETFORCEMOVEJUMP:result->i=target==AW_MWVM_PLAYER && aw_move_force_move_jump;return AW_MWVM_CALL_READ;
    case AWF_GETARMORTYPE:{
        /* GetArmorType SLOT (containerextensions.cpp OpGetArmorType: the armour in that equipment slot by its weight
         * class, 0 light, 1 medium, 2 heavy; -1 none or not armour): the player's slot (the slots are the original's
         * order, aw_inventory.h); an NPC's worn armour has no weight class in the actor table yet: -1 */
        aw_inventory_item_t it;int slot=count>=1?numbers[0].i:-1;
        result->i=-1;
        if(target==AW_MWVM_PLAYER && slot>=0 && slot<=AW_SLOT_AMMUNITION && AW_InventoryEquippedItem(slot,&it) &&
           it.category==AW_INV_ARMOUR && it.shield_class>=0 && it.shield_class<=2)result->i=it.shield_class;
        return AW_MWVM_CALL_READ;}
    case AWF_SAMEFACTION:{
        /* SameFaction (statsextensions.cpp OpSameFaction: the player is in the actor's faction) */
        char own[64];const char *f=actor_faction(instance,target,own,sizeof(own));
        result->i=f && AW_StandingRank(f)>=0;return AW_MWVM_CALL_READ;}
    case AWF_GETFACTIONREACTION:{
        /* GetFactionReaction FACTION1 FACTION2 (dialogueextensions.cpp OpGetFactionReaction): 1's reaction toward 2,
         * the dialogue table's with the scripts' changes (aw_dial.c) */
        const char *a=call_string(strings,nstrings,0),*b=call_string(strings,nstrings,1);
        result->i=a && b?AW_DialWindowReaction(a,b):0;return AW_MWVM_CALL_READ;}
    case AWF_REMOVEEFFECTS:case AWF_REMOVESPELLEFFECTS:{
        /* RemoveEffects EFFECT / RemoveSpellEffects SPELL (miscextensions.cpp OpRemoveEffects,
         * OpRemoveSpellEffects): the actor's active effects of that number / of that spell (the compiler's ASPT row)
         * end, each undone as at its end (aw_effects.c) */
        aw_actor_t *a;uint32_t owner;int n;
        if(count<1)return 1;
        if(target==AW_MWVM_PLAYER){a=player_record();owner=AW_ACTOR_PLAYER_REF;}
        else if((a=actor_of(instance,target,&e))!=NULL)owner=a->reference;
        else{uncalled_refused++;return 1;}
        n=function==AWF_REMOVEEFFECTS?AW_EffectsEnd(a,owner,numbers[0].i):a?AW_EffectsRemoveSource(a,numbers[0].i):0;
        if(n){if(target==AW_MWVM_PLAYER && a)player_store(a);AW_MwvmStateChanged();}
        uncalled_calls++;return 1;}
    case AWF_ADDSOULGEM:case AWF_DROPSOULGEM:{
        /* AddSoulGem CREATURE GEM (miscextensions.cpp OpAddSoulGem: a gem of that kind filled with the creature's
         * soul into the inventory) and DropSoulGem CREATURE (OpDropSoulGem: the first gem holding that soul leaves
         * the inventory; OpenMW lays it on the ground, here it is not laid down yet): the player's filled gems
         * (aw_actorstate.c AW_Gem*) */
        const char *creature=call_string(strings,nstrings,0),*gem=call_string(strings,nstrings,1);int row,i,soul;char id[40];
        if(target!=AW_MWVM_PLAYER || !creature || !AW_MwscriptActors() || (row=AW_ActorFind(creature))<0){
            uncalled_refused++;return 1;}
        if(function==AWF_ADDSOULGEM){
            if(!gem || !AW_GemAdd(gem,row)){uncalled_refused++;return 1;}
            AW_ItemAdd(&aw_state,gem,1);
        }else{
            for(i=0;i<AW_GemCount();i++)if(AW_GemAt(i,id,sizeof(id),&soul) && soul==row)break;
            if(i==AW_GemCount())return 1;
            AW_GemRemove(i);AW_ItemAdd(&aw_state,id,-1);
        }
        AW_MwvmStateChanged();uncalled_calls++;return 1;}
    case AWF_ENABLELEVELUPMENU:
        /* EnableLevelupMenu (guiextensions.cpp: the level-up window): opened when a level is due (aw_levelup.c, the
         * rest's own box); nothing when none is */
        AW_LevelupRested();uncalled_calls++;return 1;
    case AWF_GETCURRENTTIME:{
        /* GetCurrentTime (OpenMW 0.51 miscextensions.cpp OpGetCurrentTime: the GameHour global): the saved clock's
         * hour of the day (aw_clock.c, the global amiwind:clock:ms) */
        result->f=AW_ClockEnsure()?(float)AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms")/3600000.0f:0;
        uncalled_calls++;return AW_MWVM_CALL_READ;}
    case AWF_GETMASSERPHASE:case AWF_GETSECUNDAPHASE:{
        /* GetMasserPhase / GetSecundaPhase (skyextensions.cpp; weather.cpp MoonModel: the day of the 24-day cycle in
         * steps of three, 0 full): the sky's own orbit of that moon on the saved clock (r_sky.c R_NightMoonOrbit) */
        float dir[3];int phase=0,ms=0,days=0;
        if(AW_ClockEnsure()){ms=AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms");days=AW_ClockDays();}
        R_NightMoonOrbit(function==AWF_GETSECUNDAPHASE,ms,days,dir,&phase);
        result->i=phase;uncalled_calls++;return AW_MWVM_CALL_READ;}
    case AWF_GETSTARTINGPOS:case AWF_GETSTARTINGANGLE:{
        /* GetStartingPos / GetStartingAngle AXIS (transformationextensions.cpp OpGetStartingPos, OpGetStartingAngle: the
         * reference's placed position and rotation): where a script's first move found it (SetAtStart's record), else
         * where it is now (never moved by a script on this map); the player: where he is */
        const char *axis=call_string(strings,nstrings,0);float game[3];int a,i;
        result->f=0;
        if(!axis || !(e=transform_target(instance,target)))return AW_MWVM_CALL_READ;
        a=tolower((unsigned char)axis[0]);i=e==sv_player?-1:start_find(e);
        if(function==AWF_GETSTARTINGANGLE){
            result->f=AW_MoveScriptAngle(i>=0?starts[i].angles:e==sv_player?sv_player->v.v_angle:e->v.angles,
                                         (unsigned char)a,actor_like(e));
        }else if(a>='x' && a<='z'){
            to_game_units(i>=0?starts[i].origin:e->v.origin,game);result->f=game[a-'x'];
        }
        uncalled_calls++;return AW_MWVM_CALL_READ;}
    case AWF_PCGET3RDPERSON:result->i=chase_active.value!=0;return AW_MWVM_CALL_READ;
    case AWF_PCFORCE1STPERSON:case AWF_PCFORCE3RDPERSON:
        /* PCForce1stPerson / PCForce3rdPerson (controlextensions.cpp OpPCForce1stPerson, OpPCForce3rdPerson): the
         * player's view switched as his own key does (the chase camera, aw_view.c) */
        Cvar_SetValue("chase_active",function==AWF_PCFORCE3RDPERSON);uncalled_calls++;return 1;
    case AWF_GETPCJUMPING:
        /* GetPCJumping (statsextensions.cpp OpGetPCJumping, Player::getJumping: from the jump until the landing): the
         * player off the ground and not swimming (a fall from a ledge counts too here) */
        result->i=sv_player && !((int)sv_player->v.flags&FL_ONGROUND) && sv_player->v.waterlevel<2 &&
                  !((int)sv_player->v.flags&FL_FLY);
        return AW_MWVM_CALL_READ;
    case AWF_GETSPELLREADIED:
        /* GetSpellReadied (miscextensions.cpp OpGetSpellReadied: the draw state is the spell): the player's readied
         * magic (aw_cast.c); another actor readies no spell outside its cast here: 0 */
        result->i=target==AW_MWVM_PLAYER?AW_CastReady()!=0:0;return AW_MWVM_CALL_READ;
    case AWF_GETSTANDINGACTOR:case AWF_GETCOLLIDINGACTOR:{
        /* GetStandingActor / GetCollidingActor (miscextensions.cpp; World::getActorStandingOn, getActorCollidingWith):
         * any actor, the player included, standing on the object's entity or touching its box (a unit apart) */
        vec3_t at;int n=locate(instance,target,at),i,hit=0;
        e=n>0?edict_of(n):NULL;
        if(e && !e->free){
            hit=actor_touches(sv_player,e,function==AWF_GETSTANDINGACTOR);
            for(i=1;!hit && i<sv.num_edicts;i++)hit=actor_touches(EDICT_NUM(i),e,function==AWF_GETSTANDINGACTOR);
        }
        result->i=hit;uncalled_calls++;return AW_MWVM_CALL_READ;}
    }
    return 0;
}
/* v0.0.63 (MWSCRIPT-GAPS-63 batch 3): the console group as script functions too (OpenMW 0.51 compiles them in any
 * script: miscextensions.cpp, consoleextensions, aiextensions.cpp OpToggleAI, transformationextensions.cpp
 * OpResetActors, userextensions.cpp). The original's console aliases run the same AmiWind line (aw_mwconsole.c);
 * the rest print to the console. Nothing resident (one counter). */
static void console_exec(const char *text);
static unsigned long console_group_calls;
static void show_global(int g){
    int type=0;const char *name=global_names+global_offsets[g];
    AW_MwvmGlobalName(g,&type);
    if(type==2)Con_Printf("%s = %g\n",name,(double)AW_MwvmGlobalFloat(g));
    else Con_Printf("%s = %ld\n",name,(long)AW_MwvmGlobalInt(g));
}
/* the instance of the object a call names (its own script's locals), -1 none */
static int object_instance(int instance,int target,edict_t **out){
    int k,n=AW_MwvmInstanceCount(),num;aw_mwvm_instance_t *in;edict_t *e=transform_entity(instance,target);
    *out=e;
    if(target==AW_MWVM_SELF)return instance;
    if(!e || e==sv_player)return -1;
    num=NUM_FOR_EDICT(e);
    for(k=0;k<n;k++)if((in=AW_MwvmInstance(k))!=NULL && (in->flags&AWI_USED) && !(in->flags&AWI_GLOBAL) && in->entity==num)
        return k;
    return -1;
}
static int console_group_call(int instance,int target,int function,const aw_mwcell_t *numbers,int count,
                              const unsigned char *strings,int nstrings,aw_mwcell_t *result){
    const char *s=call_string(strings,nstrings,0);char line[128];int g,k;edict_t *e;aw_mwvm_instance_t *in;
    (void)result;
    switch(function){
    case AWF_SHOW:{
        /* Show NAME (OpenMW OpShow: the variable's value on the console): a global by its name; a script local's name
         * is not kept in the engine (the compiler makes it a slot): ShowVars prints the locals by slot */
        if(!s)return 1;
        global_names_load();
        for(g=0;global_names && global_offsets && g<global_count;g++)
            if(global_offsets[g]>=0 && same_id(global_names+global_offsets[g],s)){show_global(g);break;}
        if(!global_names || !global_offsets || g>=global_count)
            Con_Printf("Show: %s is no global (a local's name is not kept: ShowVars lists the locals by slot)\n",s);
        console_group_calls++;return 1;}
    case AWF_SHOWVARS:case AWF_SV:
        /* ShowVars (OpenMW OpShowVars: the reference's local variables, else the globals): the object's script's
         * locals by slot (each shown as a whole number and as a fraction: the slot's type is the compiler's), the
         * player or no object: every global */
        if(target!=AW_MWVM_PLAYER && (k=object_instance(instance,target,&e))>=0 && (in=AW_MwvmInstance(k))!=NULL){
            int n=AW_MwvmLocalCount(in->script),i;aw_mwcell_t v;
            Con_Printf("ShowVars: script %d, %d locals\n",(int)in->script,n);
            for(i=0;i<n;i++){v=AW_MwvmLocal(k,i);Con_Printf("  local %d = %ld / %g\n",i,(long)v.i,(double)v.f);}
        }else if(target!=AW_MWVM_PLAYER && target!=AW_MWVM_SELF){
            Con_Printf("ShowVars: the object has no script here\n");
        }else{
            global_names_load();
            for(g=0;global_names && global_offsets && g<global_count;g++)if(global_offsets[g]>=0)show_global(g);
        }
        console_group_calls++;return 1;
    case AWF_TOGGLESCRIPTS:
        /* ToggleScripts (OpenMW OpToggleScripts): the compiled scripts off and on, the dbg mwscript switch */
        Cvar_SetValue(mwscript.name,mwscript.value?0.0f:1.0f);
        Con_Printf("Scripts %s\n",mwscript.value?"on":"off");console_group_calls++;return 1;
    case AWF_TOGGLEAI:case AWF_TAI:
        /* ToggleAI (OpenMW OpToggleAI: the actors' AI processing off and on): the walking packages ("chim actors
         * ambient off" keeps every actor standing); the combat layer is its own */
        console_exec(AW_AmbientEnabled()?"chim actors ambient off":"chim actors ambient on");
        console_group_calls++;return 1;
    case AWF_RESETACTORS:case AWF_RA:{
        /* ResetActors (OpenMW World::resetActors): the actors a script moved back where the map put them (SetAtStart's
         * record), then every walker of the map at its spawn spot, choosing again (aw_ambient.c) */
        int i,n=0;
        for(i=0;i<STARTS;i++)if(starts[i].ref && starts[i].map==attached_map && starts[i].entity>0 &&
                                 starts[i].entity<sv.num_edicts){
            e=EDICT_NUM(starts[i].entity);
            if(e->free || !is_actor(e))continue;
            VectorCopy(starts[i].origin,e->v.origin);VectorCopy(starts[i].angles,e->v.angles);SV_LinkEdict(e,false);n++;
        }
        n+=AW_AmbientResetActors();
        Con_Printf("ResetActors: %d actors back at their start\n",n);console_group_calls++;return 1;}
    case AWF_OUTPUTREFINFO:case AWF_ORI:{
        /* OutputRefInfo (OpenMW OpOutputRefInfo... the reference's id, number, place and script on the console) */
        float game[3];eval_t *v,*scale;uint32_t ref=transform_reference(instance,target);
        k=target==AW_MWVM_PLAYER?-1:object_instance(instance,target,&e);
        if(target==AW_MWVM_PLAYER)e=sv_player;
        if(!e){Con_Printf("OutputRefInfo: no such reference here\n");return 1;}
        v=GetEdictFieldValue(e,"aw_source_id");scale=GetEdictFieldValue(e,"aw_scale");
        to_game_units(e->v.origin,game);
        Con_Printf("RefID: %s\nRefNum: %lu\nPosition: %g %g %g\nAngle Z: %g\nScale: %g\nScript: %d\n",
                   e==sv_player?"player":v && v->string?pr_strings+v->string:"(none)",(unsigned long)ref,
                   (double)game[0],(double)game[1],(double)game[2],(double)e->v.angles[1],
                   (double)(scale && scale->_float>0?scale->_float:1.0f),
                   k>=0 && (in=AW_MwvmInstance(k))!=NULL?(int)in->script:-1);
        console_group_calls++;return 1;}
    case AWF_USER1:case AWF_USER2:case AWF_USER3:case AWF_USER4:
        /* User1..User4 (OpenMW userextensions.cpp: the developers' test hooks, no game effect): the name on the console */
        Con_Printf("User%d\n",function-AWF_USER1+1);console_group_calls++;return 1;
    /* the original's console aliases (aw_mwconsole.c aliases[]): the same AmiWind line from a script */
    case AWF_TOGGLECOLLISION:case AWF_TCL:console_exec("noclip");console_group_calls++;return 1;
    case AWF_TOGGLEGODMODE:case AWF_TGM:console_exec("dbg god");console_group_calls++;return 1;
    case AWF_TOGGLEMENUS:case AWF_TM:console_exec("dbg killhud");console_group_calls++;return 1;
    case AWF_TOGGLEVANITYMODE:case AWF_TVM:console_exec("dbg vanitycam on");console_group_calls++;return 1;
    case AWF_FIXME:console_exec("dbg unstuck");console_group_calls++;return 1;
    case AWF_CENTERONCELL:case AWF_COC:
        if(!s)return 1;
        Q_snprintf(line,sizeof(line),"dbg tp \"%s\"",s);console_exec(line);console_group_calls++;return 1;
    case AWF_CENTERONEXTERIOR:case AWF_COE:
        /* an exterior cell's grid X, Y: its centre (as the console's coe) */
        if(count<2)return 1;
        Q_snprintf(line,sizeof(line),"dbg tp %ld %ld",(long)numbers[0].i*8192L+4096L,(long)numbers[1].i*8192L+4096L);
        console_exec(line);console_group_calls++;return 1;
    }
    return 0;
}
static int gap_call(int instance,int target,int function,const aw_mwcell_t *numbers,int count,
                    const unsigned char *strings,int nstrings,aw_mwcell_t *result){
    int k;
    if(function==AWF_RESURRECT)return resurrect(instance,target);
    if(function==AWF_HITONME){result->i=hit_on_me(instance,target,call_string(strings,nstrings,0));
                              return AW_MWVM_CALL_READ;}
    if(function==AWF_DROP){
        /* Drop ITEM COUNT (OpenMW 0.51 miscextensions.cpp OpDrop: the actor's COUNT of the item leave its inventory,
         * World::dropObjectOnGround lays them at its feet): what the actor had of it, at most COUNT, goes; each piece
         * is made on the ground at the actor's feet as PlaceAtMe makes a carried item (place_here, kept on the world
         * change list), at most PLACE_COPIES; the compiler hands the AITM and PLAC rows */
        vec3_t base,local;place_row_t r;int n,had,left,made=0;edict_t *e;float yaw=0;
        if(count<3 || numbers[0].i<1 || !place_row(numbers[2].i,&r)){places_refused++;return 1;}
        if((n=locate(instance,target,base))<0){places_refused++;return 1;}
        e=n>0?edict_of(n):NULL;
        if(e && !e->free){base[2]+=e->v.mins[2];yaw=e==sv_player?e->v.v_angle[1]:e->v.angles[1];}
        had=host_item(instance,target,0,numbers[1].i,0);
        left=host_item(instance,target,2,numbers[1].i,numbers[0].i);
        n=had-left;if(n>PLACE_COPIES)n=PLACE_COPIES;
        place_spot(base,yaw,0,0,0,local);
        for(k=0;k<n;k++)made+=place_here(numbers[2].i,&r,local,yaw);
        places+=(unsigned long)made;drops++;
        AW_MwvmStateChanged();return 1;
    }
    if(function==AWF_HURTSTANDINGACTOR){
        /* HurtStandingActor HEALTH-A-SECOND (OpenMW 0.51 miscextensions.cpp OpHurtStandingActor, World::
         * hurtStandingActors: every actor standing on the object loses that health times the frame's duration, not in
         * menus, not the player in god mode): the player standing on the object's entity; the lava volume's own damage
         * holds back meanwhile (aw_lava.c). CHIM scenery without an entity sees no one standing on it. */
        vec3_t at;int n=locate(instance,target,at);edict_t *e=n>0?edict_of(n):NULL;float hurt;
        if(!e || e->free || !sv_player || host_menu_mode() || !((int)sv_player->v.flags&FL_ONGROUND) ||
           PROG_TO_EDICT(sv_player->v.groundentity)!=e || sv_player->v.health<=0 ||
           ((int)sv_player->v.flags&FL_GODMODE) || count<1)return 1;
        hurt=numbers[0].f*(float)host_frametime;
        if(hurt>0){AW_CombatHurtPlayer(hurt,"lava");aw_lava_script_hurt=realtime;hurts++;}
        return 1;
    }
    if(function==AWF_HURTCOLLIDINGACTOR || function==AWF_GETCOLLIDINGPC){
        /* GetCollidingPC / HurtCollidingActor HEALTH-A-SECOND (OpenMW 0.51 miscextensions.cpp OpGetCollidingPc,
         * OpHurtCollidingActor; World::getPlayerCollidingWith, hurtCollidingActors): the player's box touching the
         * object's (a unit apart at most), as HurtStandingActor's rule above (not in menus, not in god mode) */
        vec3_t at;int n=locate(instance,target,at),i,touch;edict_t *e=n>0?edict_of(n):NULL;float hurt;
        touch=e && !e->free && sv_player && e!=sv_player;
        for(i=0;i<3 && touch;i++)
            if(sv_player->v.absmin[i]>e->v.absmax[i]+1 || sv_player->v.absmax[i]<e->v.absmin[i]-1)touch=0;
        if(function==AWF_GETCOLLIDINGPC){result->i=touch;return AW_MWVM_CALL_READ;}
        if(!touch || host_menu_mode() || sv_player->v.health<=0 || ((int)sv_player->v.flags&FL_GODMODE) || count<1)return 1;
        hurt=numbers[0].f*(float)host_frametime;
        if(hurt>0){AW_CombatHurtPlayer(hurt,"lava");hurts++;}
        return 1;
    }
    if((k=uncalled_call(instance,target,function,numbers,count,strings,nstrings,result))!=0)return k;   /* v0.0.63, MWSCRIPT-GAPS-63 */
    if((k=console_group_call(instance,target,function,numbers,count,strings,nstrings,result))!=0)return k;   /* batch 3 */
    if(function==AWF_GETSTAT){result->i=0;return AW_MWVM_CALL_READ;}   /* OpenMW OpGetStat: a dummy, 0 */
    if(function==AWF_GETWEAPONTYPE){
        /* GetWeaponType (containerextensions.cpp OpGetWeaponType): the right hand's weapon type, -1 none: the player's
         * equipped weapon (aw_inventory.c), an NPC's record weapon (aw_actorstate.c AW_ActorWeaponType) */
        edict_t *e;aw_actor_t *a;
        if(target==AW_MWVM_PLAYER){result->i=AW_InventoryEquippedWeaponType();return AW_MWVM_CALL_READ;}
        a=actor_of(instance,target,&e);
        result->i=!a?-1:a->reference==AW_ACTOR_PLAYER_REF?AW_InventoryEquippedWeaponType():AW_ActorWeaponType(a->base);
        return AW_MWVM_CALL_READ;
    }
    if(function==AWF_GETWATERLEVEL){
        /* GetWaterLevel (cellextensions.cpp OpGetWaterLevel): 0 outdoors (the original's oddity); in a room the water
         * surface in the original's units: the top of the water in the player's column, found from the room map's
         * contents (the room's own water is baked into it); 0 when the column has no water */
        int x,y;vec3_t p;float game[3];int k2,in;
        result->f=0;
        if(!sv.active || !sv_player || host_player_cell(&x,&y)!=2)return AW_MWVM_CALL_READ;
        VectorCopy(sv_player->v.origin,p);
        in=SV_PointContents(p)<=CONTENTS_WATER && SV_PointContents(p)>=CONTENTS_LAVA;
        for(k2=0;k2<1024;k2++){   /* two units a step: down to the water, or up out of it */
            int c=SV_PointContents(p),w=c<=CONTENTS_WATER && c>=CONTENTS_LAVA;
            if(in?!w:w)break;
            p[2]+=in?2:-2;
        }
        if(k2>=1024)return AW_MWVM_CALL_READ;
        to_game_units(p,game);result->f=game[2];
        return AW_MWVM_CALL_READ;
    }
    if(function==AWF_HASSOULGEM){result->i=soul_gems(function,target,call_string(strings,nstrings,0),0);
                                 return AW_MWVM_CALL_READ;}
    if(function==AWF_REMOVESOULGEM){
        soul_gems(function,target,call_string(strings,nstrings,0),count>=1 && numbers[0].i>0?numbers[0].i:1);return 1;}
    for(k=0;k<(int)(sizeof(resists)/sizeof(resists[0]));k++){
        edict_t *e;aw_actor_t *a=NULL;uint32_t owner;
        if(function!=resists[k].get && function!=resists[k].set && function!=resists[k].mod)continue;
        result->i=0;
        if(target==AW_MWVM_PLAYER)owner=AW_ACTOR_PLAYER_REF;
        else if((a=actor_of(instance,target,&e))!=NULL)owner=a->reference;
        else{resist_refused++;return function==resists[k].get?AW_MWVM_CALL_READ:1;}
        if(function==resists[k].get){
            float v=resist_value(owner,k);
#ifdef AW_COMBAT_EFFECT_MAGNITUDE
            if(k>=RESIST_PASSIVE_FIRST)
                v+=passive_of(target==AW_MWVM_PLAYER?player_record():a,owner,resists[k].effect);
#endif
            result->i=(int)v;resist_calls++;return AW_MWVM_CALL_READ;}
        if(count<1)return 1;
        if(!AW_EffectsBaseModify(owner,resists[k].effect,(float)(function==resists[k].mod?numbers[0].i:
                                                                  numbers[0].i-(int)resist_value(owner,k)))){
            resist_refused++;Con_DPrintf("MWScript: a resistance change not kept (effects full)\n");return 1;}
        resist_calls++;AW_MwvmStateChanged();return 1;
    }
    switch(function){
    case AWF_FADEIN:case AWF_FADEOUT:
        /* FadeIn / FadeOut SECONDS (OpenMW OpFadeIn, OpFadeOut): to none / to black from the fade of the moment */
        V_ScreenFade(function==AWF_FADEOUT?1.0f:0.0f,count>=1?numbers[0].f:0);fades++;return 1;
    case AWF_FADETO:
        /* FadeTo PERCENT SECONDS (OpenMW OpFadeTo: the percent of black, the whole number of it) */
        if(count<2)return 1;
        V_ScreenFade((float)(int)numbers[0].f/100.0f,numbers[1].f);fades++;return 1;
    case AWF_FORCESNEAK:case AWF_CLEARFORCESNEAK:case AWF_GETFORCESNEAK:{
        vec3_t at;int n,i,set=function==AWF_FORCESNEAK;uint32_t ref;
        if(target==AW_MWVM_PLAYER){
            if(function==AWF_GETFORCESNEAK){result->i=aw_move_force_sneak!=0;return AW_MWVM_CALL_READ;}
            if(aw_move_force_sneak!=set){aw_move_force_sneak=set;AW_MwvmStateChanged();}
            forced_calls++;return 1;
        }
        n=locate(instance,target,at);
        ref=n>0?ref_of_edict(edict_of(n)):0;
        if(!ref)ref=target_reference(instance,target);
        i=forced_find(ref);
        if(function==AWF_GETFORCESNEAK){result->i=i>=0;return AW_MWVM_CALL_READ;}
        if(!ref){forced_refused++;return 1;}
        if(set && i<0){
            for(i=0;i<FORCED && forced_sneak[i];i++);
            if(i==FORCED){forced_refused++;Con_DPrintf("MWScript: a ForceSneak not kept (32 at most)\n");return 1;}
            forced_sneak[i]=ref;AW_MwvmStateChanged();
        }else if(!set && i>=0){forced_sneak[i]=0;AW_MwvmStateChanged();}
        forced_calls++;return 1;}
    case AWF_FORCERUN:case AWF_CLEARFORCERUN:case AWF_GETFORCERUN:{
        /* v0.0.63 (MWSCRIPT-GAPS-63): as the sneak above, the run flag (OpenMW OpSetMovementFlag Flag_ForceRun) */
        vec3_t at;int n,i,set=function==AWF_FORCERUN;uint32_t ref;
        if(target==AW_MWVM_PLAYER){
            if(function==AWF_GETFORCERUN){result->i=aw_move_force_run!=0;return AW_MWVM_CALL_READ;}
            if(aw_move_force_run!=set){aw_move_force_run=set;AW_MwvmStateChanged();}
            forced_calls++;return 1;
        }
        n=locate(instance,target,at);
        ref=n>0?ref_of_edict(edict_of(n)):0;
        if(!ref)ref=target_reference(instance,target);
        i=forced_run_find(ref);
        if(function==AWF_GETFORCERUN){result->i=i>=0;return AW_MWVM_CALL_READ;}
        if(!ref){forced_refused++;return 1;}
        if(set && i<0){
            for(i=0;i<FORCED && forced_run[i];i++);
            if(i==FORCED){forced_refused++;Con_DPrintf("MWScript: a ForceRun not kept (32 at most)\n");return 1;}
            forced_run[i]=ref;AW_MwvmStateChanged();
        }else if(!set && i>=0){forced_run[i]=0;AW_MwvmStateChanged();}
        forced_calls++;return 1;}
    case AWF_TURNMOONRED:case AWF_TURNMOONWHITE:
        /* v0.0.63 (MWSCRIPT-GAPS-63; OpenMW skyextensions.cpp OpTurnMoonRed / OpTurnMoonWhite, sky.cpp setMoonColour):
         * Secunda in the script colour or white, kept in the saved named facts (aw_story.c) */
        if(AW_MoonRed()!=(function==AWF_TURNMOONRED)){
            if(!AW_MoonRedSet(function==AWF_TURNMOONRED)){Con_DPrintf("MWScript: the moon colour not kept (named facts full)\n");return 1;}
            AW_MwvmStateChanged();
        }
        moon_calls++;return 1;
    case AWF_HASITEMEQUIPPED:{
        /* v0.0.63 (MWSCRIPT-GAPS-63; OpenMW containerextensions.cpp OpHasItemEquipped: 1 when any equipment slot holds
         * the item, compared without case): the player's slots (aw_inventory.c); an NPC's worn or held entries of its
         * record's list, by the item's AITM row the compiler hands (aw_actorstate.c AW_ActorWearsItem) */
        const char *id=call_string(strings,nstrings,0);int slot;
        result->i=0;
        if(!id)return AW_MWVM_CALL_READ;
        if(target!=AW_MWVM_PLAYER){
            edict_t *e;aw_actor_t *a=actor_of(instance,target,&e);
            if(!a || count<1){equipped_missed++;return AW_MWVM_CALL_READ;}
            result->i=AW_ActorWearsItem(a,numbers[0].i);equipped_calls++;return AW_MWVM_CALL_READ;
        }
        for(slot=0;slot<AW_INVENTORY_SLOTS;slot++)if(aw_state.inventory.equipped[slot][0] &&
                                            !Q_strcasecmp(aw_state.inventory.equipped[slot],(char *)id)){result->i=1;break;}
        equipped_calls++;return AW_MWVM_CALL_READ;}
    }
    return 0;
}
/* SPELL-EFFECTS-57: the compiler's SPFX row ROW (every effect a Fortify, Drain, Damage or Restore of a stat, a cure,
 * or a passive effect by its number) lands on the player, each magnitude rolled once; 0 when the row is not there.
 * Cast and ExplodeSpell share it (v0.0.63). */
static unsigned long explodes,explodes_missed;   /* v0.0.63, MWSCRIPT-GAPS-63 */
/* OPENING-WEATHER-NOT-CLOUDY-63: the NGWE rows (awms.py: u16 region catalogue index, u8 weather, u8 0), the weather
 * a carried new-game script sets (CharGen: Bitter Coast Region cloudy), set as its ChangeWeather would (aw_weather.c) */
static void new_game_weather(void){
    uint32_t off,rows,bytes,i;
    if(!resident || !AW_MwvmSection("NGWE",&off,&rows,&bytes) || off+bytes>resident_bytes || 4ul*rows>bytes)return;
    for(i=0;i<rows;i++){
        const unsigned char *r=resident+off+4*i;
        if(AW_WeatherChangeByScript((r[0]<<8)|r[1],r[2]))weather_calls++;else weather_refused++;
    }
}
static int land_spfx(int row){
    uint32_t off,rows,bytes;int e;aw_actor_t *p=player_record();
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
         if(x[0]==5){   /* MWSCRIPT-UNPLACED-ATTACH-62: an effect with no attribute or skill, by its number
                         * (Shield, a resistance, Levitate, Fortify Attack: the shrines' blessings) */
             if(AW_EffectsLand(p,x[1],AW_EFFECT_NO_ARG,m,(float)((x[2]<<8)|x[3]),AW_EFFECT_NO_SOURCE))effects_cast++;
             continue;
         }
         if(AW_EffectsAdd(p,x[0],x[1],m,(float)((x[2]<<8)|x[3])))effects_cast++;
     }}
    player_store(p);AW_MwvmStateChanged();
    return 1;
}
static int host_call(int instance,int target,int function,const aw_mwcell_t *numbers,int count,
                     const unsigned char *strings,int nstrings,aw_mwcell_t *result){
    char own[64];const char *faction;int value=count>0?numbers[0].i:0,verb,bit;
    if((bit=control_function(function,&verb))!=0){
        int before=AW_ControlsDisabled();
        if(verb==2){result->i=!AW_ControlAllowed(bit);return AW_MWVM_CALL_READ;}
        if(!AW_ControlSet(bit,verb==1)){control_refused++;Con_DPrintf("MWScript: a control switch not kept (named facts full)\n");return 0;}
        control_calls++;
        if(AW_ControlsDisabled()!=before)AW_MwvmStateChanged();   /* a script that repeats the call each frame wakes no one */
        return 1;
    }
    if((bit=small_call(instance,target,function,numbers,count,strings,nstrings,result))!=0)return bit;   /* v0.0.62 */
    if((bit=gap_call(instance,target,function,numbers,count,strings,nstrings,result))!=0)return bit;   /* MWSCRIPT-GAP-FUNCTIONS-62 */
    switch(function){
    /* CRIME-59 (aw_crime.h): OnMurder (OpenMW statsextensions.cpp OpOnMurder: 1 once after the actor's murder was
     * reported), PayFine / PayFineThief / GotoJail (miscextensions.cpp OpPayFine, OpPayFineThief, OpGoToJail),
     * GetPCInJail (OpGetPcInJail) */
    case AWF_ONMURDER:{
        vec3_t at;int n=locate(instance,target,at);edict_t *e=n>0?edict_of(n):NULL;eval_t *r=e?GetEdictFieldValue(e,"aw_ref"):NULL;
        result->i=r && r->_float>0 && AW_CrimeOnMurder((unsigned long)r->_float);
        return AW_MWVM_CALL_READ;}
    case AWF_PAYFINE:case AWF_PAYFINETHIEF:
        AW_CrimePayFine(function==AWF_PAYFINE);standing_calls++;AW_MwvmStateChanged();return 1;
    case AWF_GOTOJAIL:AW_CrimeGoToJail();standing_calls++;AW_MwvmStateChanged();return 1;
    case AWF_GETPCINJAIL:result->i=AW_CrimeInJail();return AW_MWVM_CALL_READ;
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
    case AWF_ENABLESTATSMENU:case AWF_ENABLEINVENTORYMENU:case AWF_ENABLEMAGICMENU:case AWF_ENABLEMAPMENU:{
        /* the census office's scripts turn the menus on (CENSUS-INTRO-SCRIPTS-62; OpenMW OpEnableWindow): saved */
        int menu=function==AWF_ENABLESTATSMENU?AW_MENU_STATS:function==AWF_ENABLEINVENTORYMENU?AW_MENU_INVENTORY:
                 function==AWF_ENABLEMAGICMENU?AW_MENU_MAGIC:AW_MENU_MAP,before=AW_StoryMenus();
        if(!AW_StoryMenuEnable(menu)){Con_DPrintf("MWScript: a menu switch not kept (named facts full)\n");return 0;}
        if(AW_StoryMenus()!=before)AW_MwvmStateChanged();
        return 1;}
    case AWF_ENABLERACEMENU:
        /* v0.0.63 (MWSCRIPT-GAPS-63; OpenMW OpShowDialogue GM_Race, CharGenRaceNPC): the race window (aw_opening.c) */
        if(!AW_OpeningScriptMenu(1))return 0;
        AW_MwvmStateChanged();return 1;
    case AWF_ENABLENAMEMENU:
        /* v0.0.63 (OpShowDialogue GM_Name, CharGenNameNPC): the name window (aw_intro.c) */
        if(!AW_IntroNamePrompt())return 0;
        AW_MwvmStateChanged();return 1;
    case AWF_ENABLEREST:{
        /* v0.0.63 (OpenMW OpEnableRest, CharGenBed): the rest allowed while the opening's restriction holds, saved
         * with the scripts' menus (aw_story.c AW_MENU_REST) */
        int before=AW_StoryMenus();
        if(!AW_StoryMenuEnable(AW_MENU_REST)){Con_DPrintf("MWScript: EnableRest not kept (named facts full)\n");return 0;}
        if(AW_StoryMenus()!=before)AW_MwvmStateChanged();
        return 1;}
    case AWF_ENABLECLASSMENU:case AWF_ENABLEBIRTHMENU:case AWF_ENABLESTATREVIEWMENU:
        /* the clerk's class, birth and review windows (CharGenClassNPC; OpenMW OpShowDialogue): aw_opening.c */
        if(!AW_OpeningScriptMenu(function==AWF_ENABLECLASSMENU?2:function==AWF_ENABLEBIRTHMENU?3:4))return 0;
        AW_MwvmStateChanged();return 1;
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
    case AWF_POSITIONCELL:
        /* PositionCell of anything but the player (v0.0.62; see position_cell above) */
        return position_cell(instance,target,numbers,count);
    case AWF_PLACEATPC:case AWF_PLACEATME:case AWF_PLACEITEM:case AWF_PLACEITEMCELL:
        /* the placing family (v0.0.62, MWSCRIPT-PLACE-OBJECTS-62; see place_call above) */
        return place_call(instance,target,function,numbers,count);
    case AWF_AIFOLLOWCELL:case AWF_AIESCORT:case AWF_AIESCORTCELL:
        /* v0.0.62: see ai_package above */
        return ai_package(instance,target,function,numbers,count,strings,nstrings);
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
        const char *id=call_string(strings,nstrings,0);vec3_t at;edict_t *e,*t;int n=locate(instance,target,at),pl=0;
        e=n>0?edict_of(n):NULL;
        result->i=0;
        if(!id || !e || e==sv_player)return AW_MWVM_CALL_READ;
        /* COMBAT-ACTOR-VS-ACTOR-62 (v0.0.63): the actor's target, the player or another actor (by its record id) */
        t=AW_CombatTargetOf(e,&pl);
        if(!Q_strcasecmp((char *)id,"player"))result->i=pl;
        else if(t){eval_t *w=GetEdictFieldValue(t,"aw_source_id");
                   result->i=w && w->string && !Q_strcasecmp(pr_strings+w->string,(char *)id);}
        return AW_MWVM_CALL_READ;}
    case AWF_ROTATE:{
        /* Rotate AXIS DEGREES-A-SECOND (OpenMW transformationextensions.cpp OpRotate: by that many degrees times the
         * frame's duration; the player only around z): on an object with an entity; the CHIM scenery without one
         * cannot turn yet. Quake's yaw turns the other way round from the original's z. */
        const char *axis=call_string(strings,nstrings,0);vec3_t at;edict_t *e;int n=locate(instance,target,at);
        float step=count>=1?numbers[0].f*(float)host_frametime:0;
        e=n>0?edict_of(n):NULL;
        if(axis && (!e || e->free)){
            /* WORLD-BUTTONS-62 part 2: a scripted mover placement (a crank, a bar door, a Dwemer door) turns the
             * same way about its own axes */
            float d[3]={0,0,0};int a=tolower((unsigned char)axis[0]);
            if(a=='z')d[1]=-step;else if(a=='x')d[0]=step;else if(a=='y')d[2]=step;
            if((d[0] || d[1] || d[2] || !step) && AW_MoverTurn(transform_reference(instance,target),d)){
                mover_moves++;rotations++;return 1;}
        }
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
    case AWF_PLAYBINK:
        /* PlayBink FILE SKIP (OpenMW 0.51 miscextensions.cpp OpPlayBink, WindowManager::playVideo: the video plays over
         * the game, then the game goes on; a video that cannot be played is skipped): the converted video of that
         * catalogue name plays as the debug video does, and the scene goes on after it (aw_movie.c AW_MovieScript);
         * a build without it says so once and the script goes on. Esc skips it whatever SKIP says. */
        if(AW_MovieScript(call_string(strings,nstrings,0)))binks++;else binks_missed++;
        return 1;
    case AWF_BECOMEWEREWOLF:case AWF_UNDOWEREWOLF:case AWF_ISWEREWOLF:{
        int set=function==AWF_BECOMEWEREWOLF,i;
        if(target!=AW_MWVM_PLAYER){
            vec3_t at;int n=locate(instance,target,at);uint32_t ref=n>0?ref_of_edict(edict_of(n)):0;
            if(!ref)ref=target_reference(instance,target);
            i=were_npc_find(ref);
            if(function==AWF_ISWEREWOLF){result->i=i>=0;return AW_MWVM_CALL_READ;}
            if(!ref)return 1;
            if(set && i<0){
                for(i=0;i<WERE_NPCS && were_npc[i];i++);
                if(i==WERE_NPCS){Con_DPrintf("MWScript: a werewolf NPC not kept (16 at most)\n");return 1;}
                were_npc[i]=ref;AW_MwvmStateChanged();
            }else if(!set && i>=0){were_npc[i]=0;AW_MwvmStateChanged();}
            were_calls++;return 1;
        }
        if(function==AWF_ISWEREWOLF){result->i=were.player;return AW_MWVM_CALL_READ;}
        if(were.player==set)return 1;
        {aw_actor_t *p=player_record();
         if(set){
             /* player.cpp setWerewolfStats: his own kept, the werewolf's from the game settings (Acrobatics apart:
              * SetWerewolfAcrobatics); inventorystore.cpp unequipAll */
             if(p){
                 for(i=0;i<8;i++)were.attr[i]=p->attr_base[i];
                 for(i=0;i<27;i++)were.skill[i]=p->skill_base[i];
                 were.kept=1;
                 for(i=0;i<8+27;i++){
                     int v=count>i/4?(int)(((uint32_t)numbers[i/4].i>>(8*(3-i%4)))&255):255;
                     if(v==255 || i==8+20)continue;   /* no setting; Acrobatics stays */
                     if(i<8)p->attr_base[i]=(short)v;else p->skill_base[i-8]=(short)v;
                 }
                 player_store(p);
             }
             for(i=0;i<AW_INVENTORY_SLOTS;i++)if(aw_state.inventory.equipped[i][0]){
                 char id[64];Q_strncpy(id,aw_state.inventory.equipped[i],sizeof(id)-1);id[sizeof(id)-1]=0;
                 AW_InventoryUnequip(&aw_state,id);
             }
         }else if(p && were.kept){   /* player.cpp restoreStats */
             for(i=0;i<8;i++)p->attr_base[i]=were.attr[i];
             for(i=0;i<27;i++)p->skill_base[i]=were.skill[i];
             were.kept=0;player_store(p);
         }}
        were.player=set;aw_move_werewolf=set;were_calls++;AW_MwvmStateChanged();return 1;}
    case AWF_SETWEREWOLFACROBATICS:{
        /* mechanicsmanagerimp.cpp applyWerewolfAcrobatics: Acrobatics to fWerewolfAcrobatics (the compiler's number) */
        aw_actor_t *p=target==AW_MWVM_PLAYER?player_record():NULL;
        if(!p || count<1)return 1;
        p->skill_base[20]=(short)numbers[0].i;player_store(p);were_calls++;AW_MwvmStateChanged();return 1;}
    case AWF_GETWEREWOLFKILLS:
        /* OpenMW OpGetWerewolfKills: the player's count, whoever asks */
        result->i=were.kills;return AW_MWVM_CALL_READ;
    case AWF_SETSCALE:case AWF_MODSCALE:case AWF_GETSCALE:{
        /* SetScale / ModScale / GetScale (v0.0.63, MWSCRIPT-GAPS-63; OpenMW transformationextensions.cpp OpSetScale,
         * OpModScale, OpGetScale, World::scaleObject): the object's drawn size, the edict's aw_scale (the client draws
         * it, AWU_SCALE); an object without an entity is not scaled (counted). Not kept past the map: a room or area
         * load builds its objects at the game data's size again */
        vec3_t at;int n=locate(instance,target,at);edict_t *e=n>0?edict_of(n):NULL;eval_t *v=e?GetEdictFieldValue(e,"aw_scale"):NULL;
        float now=v && v->_float>0?v->_float:1;
        if(function==AWF_GETSCALE){result->f=now;return AW_MWVM_CALL_READ;}
        if(!v || count<1){transforms_missed++;return 1;}
        now=function==AWF_SETSCALE?numbers[0].f:now+numbers[0].f;
        if(!(now>0))now=0.01f;
        if(v->_float!=now){v->_float=now;SV_LinkEdict(e,false);AW_MwvmStateChanged();}   /* GetScale wakes with it */
        transforms++;return 1;}
    case AWF_GETPCTRAVELING:
        /* OpenMW miscextensions.cpp OpGetPcTraveling, World::isPlayerTraveling: 1 only inside the travel's own
         * teleport step, which no script frame sees here (a travel is one step): 0 */
        result->i=0;return AW_MWVM_CALL_READ;
    case AWF_GETSPELLEFFECTS:{
        /* GetSpellEffects SPELL (v0.0.63, MWSCRIPT-GAPS-63; OpenMW miscextensions.cpp OpGetSpellEffects,
         * ActiveSpells::isSpellActive): 1 while an effect of the spell (the compiler's ASPT row) is active on the actor */
        aw_effect_info_t fx;edict_t *e;aw_actor_t *a;uint32_t owner;int k;
        result->i=0;
        if(count<1)return AW_MWVM_CALL_READ;
        if(target==AW_MWVM_PLAYER)owner=AW_ACTOR_PLAYER_REF;
        else if((a=actor_of(instance,target,&e))!=NULL)owner=a->reference;
        else return AW_MWVM_CALL_READ;
        for(k=0;k<AW_EffectsCount() && AW_EffectsAt(k,&fx);k++)
            if(fx.owner==owner && fx.source==numbers[0].i){result->i=1;break;}
        return AW_MWVM_CALL_READ;}
    case AWF_GETATTACKED:{
        vec3_t at;int n=locate(instance,target,at);edict_t *e=n>0?edict_of(n):NULL;
        result->i=e && e!=sv_player && attacked_now(e);return AW_MWVM_CALL_READ;}
    case AWF_EXPLODESPELL:{
        /* ExplodeSpell SPELL (v0.0.63, MWSCRIPT-GAPS-63; OpenMW miscextensions.cpp OpExplodeSpell): the compiler hands
         * the spell's ASPT row; the object casts it on itself, its effects' areas reach the actors around it (aw_cast.c
         * AW_CastExplode) */
        vec3_t at;int n=locate(instance,target,at);
        if(count<1 || n<0 || AW_CastExplode(at,numbers[0].i)<0){explodes_missed++;return 1;}
        explodes++;return 1;}
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
            if(!land_spfx(numbers[0].i))return 0;
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
    if(fn==49){                                                            /* Alarmed (CRIME-59): the speaker's mark */
        edict_t *e=c->speaker>0 && c->speaker<sv.num_edicts?EDICT_NUM(c->speaker):NULL;eval_t *r=e?GetEdictFieldValue(e,"aw_ref"):NULL;
        *out=r && r->_float>0 && AW_CrimeAlarmed((unsigned long)r->_float);return 1;}
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
/* the speaker's script local: its attached instance's slot; else its parked locals, where a dialogue result run
 * without an attached instance keeps them (AW_MwvmRunDialogue: "set state to -1" in Sellus Gravius's Greeting 1 while
 * his script is not attached; CENSUS-INTRO-SCRIPTS-62); neither: 0, OpenMW's empty locals */
static int live_local(const aw_glut_cond_t *c,int slot,int is_float,float *out){
    int k,n=AW_MwvmInstanceCount(),script;aw_mwvm_instance_t *in;aw_mwcell_t v;eval_t *ref;
    *out=0;
    for(k=0;c->speaker>0 && k<n;k++)
        if((in=AW_MwvmInstance(k))!=NULL && (in->flags&AWI_USED) && in->entity==c->speaker){
            v=AW_MwvmLocal(k,slot);*out=is_float?v.f:(float)v.i;return 1;}
    if(c->speaker>0 && c->speaker<sv.num_edicts && (ref=GetEdictFieldValue(EDICT_NUM(c->speaker),"aw_ref"))!=NULL &&
       ref->_float>0 && AW_MwvmLocalGet((uint32_t)ref->_float,slot,&script,&v))
        *out=is_float?v.f:(float)v.i;
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
static int crime_set_global(const char *name,int value);   /* below, CRIME-59 */
void AW_MwscriptDispositionFacts(const char *record,unsigned long reference,int base,const char *faction,aw_dial_facts_t *f){
    int row=-1;aw_actor_base_t b;aw_actor_t *a;char race[64];
    memset(f,0,sizeof(*f));
    f->base=base;f->faction=faction;f->rank=standing_rank;f->bounty=AW_StandingCrime();
    f->personality=aw_character.valid?(float)aw_character.attributes[6]:50.0f;
    f->diseased=disposition_diseased(1);f->weapon_drawn=disposition_weapon_drawn();f->charm=disposition_charm(reference);
    /* CRIME-59: a conversation opens: the crime gold globals the guards' lines test (updateDialogueGlobals) */
    AW_CrimeDialogueGlobals(crime_set_global,AW_StateGet(&aw_state,AW_ITEM,"gold_001"));
    if(!AW_MwscriptActors() || !record || (row=AW_ActorFind(record))<0 || !AW_ActorBase(row,&b))return;
    if(reference && (a=AW_ActorGet((uint32_t)reference,row,0))!=NULL)f->base=(int)AW_ActorStat(disposition_restore(a),AWA_DISPOSITION);
    else f->base=disposition_kept(reference,f->base);
    f->base+=AW_CrimeDispositionOf(reference);   /* the crime's temporary change (OpenMW crime disposition modifier) */
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
    /* DBG-GIVE-MONEY-62: the sum held at the gold cap (aw_state.h AW_GOLD_MAX) before it could pass 32 bits */
    if(delta){gold=delta>0 && gold>AW_GOLD_MAX-delta?AW_GOLD_MAX:gold+delta;if(gold<0)gold=0;
              AW_StateSet(&aw_state,AW_ITEM,"gold_001",(int32_t)gold);AW_MwvmStateChanged();}
    return (int)AW_StateGet(&aw_state,AW_ITEM,"gold_001");
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
/* a new game (aw_save.c AW_SaveReset, every opening and quick start): its run-once scripts start on the next tick */
static int new_game_pending,new_game_started;static unsigned long new_games;
static void new_game_hook(void){new_game_pending=1;new_game_started=0;}
static int load(void){
    FILE *f=NULL;int length,i,n;unsigned char head[16];uint32_t wanted;char name[64];long base;
    if(resident || load_failed)return resident!=NULL;
    load_failed=1;string_cache_clear();results_close();
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
    AW_MwscriptResultsPrepare();   /* MWSCRIPT-RESULT-LONG-FRAME-62: the results' index at the load, not in a talk */
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
    leaving_count=0;             /* a map change took this map's actors with it (PositionCell, v0.0.62) */
    /* the object state: what a script disabled or the player took stays hidden on this map too */
    if(aw_ledger_on){ledger_attach();return;}      /* CELL-CHANGES-59: this map's rows of the world change list */
    for(i=0;i<object_count;i++)if(objects[i].disabled){objects[i].entity=-1;object_hide(&objects[i]);}
}
/* MWSCRIPT-UNPLACED-ATTACH-62 (OpenMW 0.51 mwclass/creaturelevlist.cpp: a levelled list's pick is an actor of that
 * record, its script runs as a placed actor's): aw_actors.c hands over each actor a levelled list gave as it spawns
 * (its entity and its record's hash, the actor table's base hash); queued, then attached under the list's reference
 * after the map's own bindings (attach_map would otherwise park it at once). Cost: one binary search of the LACT
 * rows per levelled spawn. */
#define LEVELLED_QUEUE 32
static struct {int entity;uint32_t ref,hash;} levelled_queue[LEVELLED_QUEUE];static int nlevelled;
static unsigned long levelled_attached,levelled_refused;
static void levelled_spawned(edict_t *e,unsigned hash){
    eval_t *v;
    if(!e || e->free || nlevelled>=LEVELLED_QUEUE || !(v=GetEdictFieldValue(e,"aw_ref")) || v->_float<=0)return;
    levelled_queue[nlevelled].entity=NUM_FOR_EDICT(e);levelled_queue[nlevelled].ref=(uint32_t)v->_float;
    levelled_queue[nlevelled++].hash=hash;
}
static void levelled_flush(void){
    int i,script,k;
    for(i=0;i<nlevelled;i++){
        edict_t *e=edict_of(levelled_queue[i].entity);eval_t *v;aw_mwvm_instance_t *in;
        if(!e || e->free || !(v=GetEdictFieldValue(e,"aw_ref")) || (uint32_t)v->_float!=levelled_queue[i].ref ||
           !AW_MwvmLevelledScript(levelled_queue[i].hash,&script))continue;
        /* the list rolled another actor since (a respawn): the old pick's values are parked, the new one attached */
        for(k=0;k<AW_MwvmInstanceCount();k++)
            if((in=AW_MwvmInstance(k))!=NULL && (in->flags&(AWI_USED|AWI_GLOBAL))==AWI_USED &&
               in->reference==levelled_queue[i].ref && (int)in->script!=script){AW_MwvmDetach(levelled_queue[i].ref);break;}
        if(attach_script(levelled_queue[i].ref,script,map_room?AWB_INTERIOR:0,levelled_queue[i].entity,e->v.origin)>=0)
            levelled_attached++;
        else levelled_refused++;
    }
    nlevelled=0;
}
/* MWSCRIPT-INVENTORY-HITONME-62 (OpenMW 0.51 mwworld/localscripts.cpp addCell, AddContainerItemScriptsVisitor: the
 * scripts of the items in the active cells' containers, NPCs and creatures run, each on its item): the BIND_HELD rows
 * of this map (tools/mwscript/compiler.py held_bindings) attach under their held key while the holder still has an
 * item of that script: a container by its contents now (the loaded area's record and the world change list), an
 * actor by its live record when it has one (the area load makes them), else by its record's list. At most HELD_MAX a
 * map; a held item's values are not parked or saved (each visit starts them again). When the player gains an item of
 * such a script (taken from the container or the body), the held instances of that script are checked again. */
#define HELD_MAX 32
static int held_attached_now;
static unsigned long held_attached,held_absent,held_over;
static int held_present(uint32_t holder,int entity,int script){
    aw_container_item_t items[AW_CONTAINER_ITEMS];int n=AW_ContainerContents(holder,items,AW_CONTAINER_ITEMS,NULL),i,s,slot;
    if(n>=0){
        for(i=0;i<n;i++)
            if(items[i].count>0 && AW_MwvmPcAddRow(AW_MwvmTextHash(items[i].id,(int)strlen(items[i].id)),&s,&slot) &&
               s==script)return 1;
        return 0;
    }
    {edict_t *e=entity>0?edict_of(entity):NULL;aw_actor_t *a;int row,ids[32],counts[32],worn[32];char id[40];
     if(!e || e->free || !AW_MwscriptActors() || (row=row_of_edict(e))==AW_ACTOR_NONE ||
        !(a=AW_ActorGet(holder,row,0)))return 1;     /* no live record: the record's own list holds it */
     n=AW_ActorItems(a,ids,counts,worn,32);
     for(i=0;i<n;i++)
         if(counts[i]>0 && AW_ActorItemId(ids[i],id,sizeof(id)) &&
            AW_MwvmPcAddRow(AW_MwvmTextHash(id,(int)strlen(id)),&s,&slot) && s==script)return 1;
     return 0;}
}
static int held_attach(uint32_t ref,int script,int flags,int entity,const float origin[3]){
    int k;
    if(held_attached_now>=HELD_MAX){held_over++;return -1;}
    if(!held_present(AWB_HELD_HOLDER(ref),entity,script)){held_absent++;return -1;}
    if((k=attach_script(ref,script,flags,-1,origin))>=0){held_attached++;held_attached_now++;}
    return k;
}
/* the player gained an item of SCRIPT: a held instance of it whose holder no longer has one stops */
static void held_recheck(int script){
    int k;
    for(k=0;k<AW_MwvmInstanceCount();k++){
        aw_mwvm_instance_t *in=AW_MwvmInstance(k);uint32_t holder;
        if(!in || (in->flags&(AWI_USED|AWI_GLOBAL))!=AWI_USED || !AWB_HELD_KEY(in->reference) || (int)in->script!=script)
            continue;
        holder=AWB_HELD_HOLDER(in->reference);
        if(!held_present(holder,entity_of_reference(holder),script)){AW_MwvmDetach(in->reference);held_absent++;
                                                                     if(held_attached_now>0)held_attached_now--;}
    }
}
static void attach_map(void){
    FILE *f=NULL;int length,i,k,nroom=0,anchored=0;long base,room;uint32_t offset,rows,bytes,r;unsigned char row[24];
    vec3_t local,shift;float source[3];edict_t *e;int outdoors;
    AW_MwvmBeginMap();held_attached_now=0;
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
        if(flags&AWB_HELD){
            /* an item a container or an actor holds: at its holder (an actor not spawned here waits for it) */
            entity=entity_of_reference(AWB_HELD_HOLDER(ref));
            if(entity>0){
                e=EDICT_NUM(entity);
                if(held_attach(ref,script,flags|AWB_INTERIOR*(!outdoors),entity,e->v.origin)<0)attach_refused++;
                continue;
            }
            if(flags&AWB_ACTOR)continue;
        }else entity=entity_of_reference(ref);
        if(entity>0){
            e=EDICT_NUM(entity);
            k=attach_script(ref,script,flags|AWB_INTERIOR*(!outdoors),entity,e->v.origin);
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
        k=flags&AWB_HELD?held_attach(ref,script,flags,-1,local):attach_script(ref,script,flags,-1,local);
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
        k=((p[6]<<8)|p[7])&AWB_HELD?held_attach(ref,(p[4]<<8)|p[5],(p[6]<<8)|p[7],-1,local):
                                     attach_script(ref,(p[4]<<8)|p[5],(p[6]<<8)|p[7],-1,local);
        if(k>=0)attach_rooms++;else attach_refused++;
    }
}
/* TOMB-MUSIC-OVER-AMBIENT-60: a dungeon ambience loop (a tomb's Haunted or spirit voices, a cave's drip or wind) is
 * playing on this map: the exploration music rests (aw_music.c AW_MusicAmbience; battle music still plays). */
static int ambience_playing(void){
    int i;for(i=0;i<LOOPS;i++)if(loops[i].used && loops[i].looping && loops[i].ambience)return 1;
    return 0;
}
/* --- who joins a fight (v0.0.63, COMBAT-ACTOR-VS-ACTOR-62; rules from OpenMW 0.51 mwmechanics/actors.cpp
 * engageCombat, written independently). Once a second, every live NPC or creature within the actors' processing range
 * (7168 original units) of the player that does not fight yet is checked against each fighter:
 *   allies: the actor it follows or escorts and the actors following or escorting it (AiPackage sideWithTarget,
 *     one level each way); an ally fighting X makes it aggressive to X, the player included;
 *   guards (class Guard): a creature in a fight within fAlarmRadius makes a guard aggressive to it, unless the
 *     creature follows or escorts someone;
 * an aggressive actor joins only when it sees X and notices it (World::getLOS, MechanicsManager::awarenessCheck: the
 * crime rules' sight and detection here). The Fight-value aggression against the player stays the ambient tables'
 * (aw_ambient.c aggro). Not yet: OpenMW's "both sides are in combat with actor1" rule for player followers. */
static float join_clock;static unsigned long joins_allies,joins_guards;
static int crime_guard(edict_t *e);
static int fight_sheet(edict_t *e,aw_fighter_t *out){
    eval_t *v=GetEdictFieldValue(e,"aw_source_id");aw_actor_t *a=record_of_edict(e);
    if(!a || (a->flags&AWL_DEAD) || !v || !v->string || !AW_CombatActorLoad(pr_strings+v->string,out))return 0;
    to_fighter(a,out);return 1;
}
static void join_against(edict_t *e,edict_t *x){
    aw_fighter_t sheet;aw_actor_t *a=record_of_edict(e);
    if(!fight_sheet(e,&sheet))return;
    if(x==sv_player){if(AW_CombatEngage(e,&sheet,NULL) && a)a->flags|=AWL_COMBAT;}
    else if(AW_CombatEngageAgainst(e,&sheet,x,NULL) && a)a->flags|=AWL_COMBAT;
}
static void join_fights(float dt){
    /* the fighters once (at most the combat layer's 16 slots), then each actor against them: the cost is the actors
     * in range x the fighters, once a second, and nothing while nobody fights */
    struct {edict_t *f,*t;const aw_fighter_t *ff;edict_t *leader;} fights[32];
    int i,j,nf=0;float range=7168*AW_MOVE_UNIT_SCALE,alarm;
    join_clock+=dt;if(join_clock<1)return;join_clock=0;
    if(!sv_player || sv_player->v.health<=0 || !AW_MwscriptActors())return;
    for(j=1;j<sv.num_edicts && nf<32;j++){
        edict_t *f=EDICT_NUM(j),*t;const aw_fighter_t *ff;int pl=0;
        if(f->free || f==sv_player || !(ff=AW_CombatFighter(f)) || ff->dead)continue;
        t=AW_CombatTargetOf(f,&pl);if(pl)t=sv_player;
        if(!t)continue;
        fights[nf].f=f;fights[nf].t=t;fights[nf].ff=ff;fights[nf].leader=AW_AmbientLeaderOf(f);nf++;
    }
    if(!nf)return;
    alarm=AW_CrimeAlarmRadius();
    for(i=1;i<sv.num_edicts;i++){
        edict_t *e=EDICT_NUM(i),*leader,*x=NULL;vec3_t d;int guard,why;
        if(e->free || e==sv_player || !is_actor(e) || AW_CombatFighter(e) || e->v.health<0)continue;
        VectorSubtract(e->v.origin,sv_player->v.origin,d);
        if(DotProduct(d,d)>range*range)continue;
        leader=AW_AmbientLeaderOf(e);guard=-1;why=0;
        for(j=0;j<nf && !x;j++){
            edict_t *f=fights[j].f,*t=fights[j].t;const aw_fighter_t *ff=fights[j].ff;
            if(f==e || t==e)continue;
            /* the player's own follower or escort: the player is its ally, so an actor fighting the player (it attacked
             * the player, or the player attacked it) becomes its enemy (OpenMW: the ally's hit attempt actor) */
            if(leader==sv_player && t==sv_player){x=f;why=1;break;}
            /* an ally fights T: aggressive to T */
            if(f==leader || fights[j].leader==e){x=t;why=1;break;}
            /* a guard: a creature in a fight within fAlarmRadius, unless it follows or escorts someone */
            if(ff->creature && alarm>0 && !fights[j].leader){
                vec3_t g;
                if(guard<0)guard=crime_guard(e);
                VectorSubtract(f->v.origin,e->v.origin,g);
                if(guard && DotProduct(g,g)<=alarm*alarm){x=f;why=2;break;}
            }
        }
        if(!x || (x!=sv_player && x->free))continue;
        if(!AW_CrimeSight(e,x) || !detected(e,x))continue;   /* getLOS and the awareness check */
        join_against(e,x);
        if(why==1)joins_allies++;else joins_guards++;
    }
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
        if(new_game_pending){
            /* NPC-STORY-DISABLED-AT-START-42: a new game began (AW_SaveReset). The scripts start from the game data
             * (a file loaded this tick already did; one kept from an earlier game is reset from the cleared list),
             * then the original's run-once new-game scripts start: Startup disables its story characters */
            new_game_pending=0;
            if(was)script_import(&aw_ledger);
            new_game_started=AW_MwvmNewGame();new_games++;
            new_game_weather();   /* CharGen's ChangeWeather, carried by AmiWind's own opening (v0.0.63) */
        }
        t1=Sys_FloatTime();
        if(script_model!=map_model){script_model=map_model;attach_map();carried_sync();}
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
    carried_tick(player);   /* the carried items' scripts (OnPCEquip, MWSCRIPT-GAP-FUNCTIONS-62) */
    {int sm,any=AW_EffectsCount()>0;   /* SUMMONED-CREATURES-62: nothing to look at without an effect or a summon */
     for(sm=0;!any && sm<SUMMONS;sm++)any=summons[sm].used;
     if(any)summons_tick();}
    pcadd_flush();   /* the items the player gained since the last frame: their scripts' OnPCAdd */
    removed_flush();   /* the items the player no longer carries: their carried scripts stop */
    levelled_flush();   /* the actors levelled lists gave since the last frame: their records' scripts */
    {double t0=Sys_FloatTime();
     AW_MwvmTick(dt,player);
     if(Sys_FloatTime()-t0>.3)Con_Printf("MWScript tick: %.0f ms (scripts run this frame).\n",(Sys_FloatTime()-t0)*1000);}
    leave_now();   /* PositionCell: the actors moved to another place leave this map now */
    AW_ActorsPlacedTick(placed_spawn);   /* the actors scripts placed here come back (once a second; MWSCRIPT-PLACE-OBJECTS-62) */
    /* SCRIPTED-EVENT-FALLING-MAGE-61: actors held on an object a script removes fall once it is gone (aw_fall.c) */
    AW_FallTick(dt);
    AW_CrimeTick(dt);   /* CRIME-59: the guards' pursuit and arrest on sight, a jail waiting for its conversation to end */
    join_fights(dt);    /* COMBAT-ACTOR-VS-ACTOR-62: allies and guards join fights (OpenMW Actors::engageCombat) */
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
    Con_Printf("new games %lu: %d run-once scripts started%s\n",new_games,new_game_started,
               new_game_pending?" (one pending)":"");
    Con_Printf("actors enabled in a loaded area: %lu (an edict of this map shown again, or a kept actor spawned at once)\n",
               actors_enabled);
    Con_Printf("Say: %lu started, %lu not started (no actor, voice or sample); last on entity %d, %.1f s\n",
               says_started,says_missed,say_last_entity,say_last_seconds);
    AW_FallStatus();
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
                "OnActivate %lu, Activate %lu; OnPCAdd set %lu on a taken placement, %lu on a carried item\n",
                disabled,locks,object_count,OBJECTS,objects_hidden,objects_full,intercepted,activated,
                pcadd_placed,pcadd_carried);
     Con_Printf("carried item scripts: %lu started, %lu stopped, %lu inventory checks; levelled actors' scripts: %lu "
                "attached, %lu refused; PlayBink %lu played, %lu absent\n",carried_started,carried_stopped,
                carried_syncs,levelled_attached,levelled_refused,binks,binks_missed);
     Con_Printf("held item scripts: %d attached on this map (at most %d), %lu attached, %lu no longer held, %lu over "
                "the limit\n",held_attached_now,HELD_MAX,held_attached,held_absent,held_over);
     Con_Printf("HitOnMe: %lu weapon blows kept (%d of %d rows held, %d bytes), %lu by NPCs not kept; %lu reads, %lu "
                "matched\n",hits_kept,AW_CombatLastHitCount(),AW_COMBAT_LAST_HITS,
                (int)(AW_COMBAT_LAST_HITS*2*sizeof(unsigned long)),hits_npc,hits_read,hits_matched);
     Con_Printf("region weather by scripts: %lu ChangeWeather and ModRegion calls kept, %lu refused (%d bytes)\n",
                weather_calls,weather_refused,(int)sizeof(aw_weather_script_t));}
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
    Con_Printf("PositionCell: %lu moved here, %lu to another place, %lu not possible; arrivals spawned %lu (%lu with no "
               "entity to spawn); %d leaving\n",poscells,poscells_away,poscells_refused,visitors_spawned,visitors_no_text,
               leaving_count);
    Con_Printf("Place calls: %lu made (%lu kept for another place), %lu not possible; placed actors spawned %lu (%lu with "
               "no entity to spawn), of them objects %lu\n",places,places_away,places_refused,placed_spawned,placed_no_text,
               placed_objects);
    AW_ActorsPlacedStatus();
    {int sm,alive=0;for(sm=0;sm<SUMMONS;sm++)alive+=summons[sm].used;
     Con_Printf("Summoned creatures: %d now; %lu called up, %lu back by the player, %lu ended with their effect, %lu died, "
                "%lu with no creature (%d summoning settings read)\n",alive,summons_made,summons_back,summons_ended,
                summons_died,summons_no_creature,summon_id_count<0?0:summon_id_count);}
    Con_Printf("AIFollowCell %lu (%lu not possible), AIEscort and AIEscortCell %lu (%lu not possible); followers through "
               "a door with the player %lu (%lu could not come: no entity, no row or no spawn)\n",cell_follows,
               cell_follows_refused,escorts,escorts_refused,crossed,crossed_lost);
    Con_Printf("Angles, moves, SetAtStart and SetDelete %lu (%lu with no entity or axis); GetDetected %lu (%lu detected), GetLOS "
               "%lu; knockdowns read %lu; WakeUpPC %lu\n",transforms,transforms_missed,detections,detections_yes,
               sightings,knockouts,wakeups);
    Con_Printf("Scripted movers (placements without an entity, WORLD-BUTTONS-62): %d in the table, %d away from their "
               "start, %lu moves and returns\n",AW_MoverCount(),AW_MoverMoved(),mover_moves);
    Con_Printf("Fades %lu (black now %.2f); ForceSneak and ClearForceSneak %lu (%lu not kept), the player forced %d; "
               "resistances read or changed %lu (%lu with no actor or no room); soul gem calls %lu; the player hurt standing "
               "on an object %lu frames; Drop %lu; Resurrect %lu (%lu not possible); OnPCEquip set %lu, PCSkipEquip took %lu, "
               "carried scripts not run %lu\n",fades,(double)V_ScreenFadeLevel(),
               forced_calls,forced_refused,aw_move_force_sneak,resist_calls,resist_refused,gem_calls,hurts,drops,
               resurrections,resurrect_refused,equip_reactions,equip_skipped,carried_refused);
    {   /* MWSCRIPT-PLAYER-CONTROL-62: the switches a script turned off now, by name */
        char off[160];int b;off[0]=0;
        for(b=1;b<=AW_CONTROL_LEVITATION;b<<=1)if(!AW_ControlAllowed(b)){
            if(off[0])strncat(off,", ",sizeof(off)-strlen(off)-1);
            strncat(off,AW_ControlName(b),sizeof(off)-strlen(off)-1);}
        Con_Printf("Control switches: %lu calls (%lu not kept); off now: %s\n",control_calls,control_refused,off[0]?off:"none");
    }
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
#ifdef AW_COMBAT_EFFECT_MAGNITUDE
    if(ref && AW_MwscriptActors()){
        aw_actor_t *a=AW_ActorGet(ref,AW_ACTOR_NONE,0);
        Con_Printf("  resistance to normal weapons from its abilities: %.0f (weakness %.0f); ability lookups read %lu, "
                   "kept %lu\n",a?AW_ActorPassiveMagnitude(a,AW_EFFECT_RESIST_NORMAL_WEAPONS):0.0f,
                   a?AW_ActorPassiveMagnitude(a,AW_EFFECT_WEAKNESS_NORMAL_WEAPONS):0.0f,passive_reads,passive_kept);
    }
#endif
}
static void status(void){
    char *a=Cmd_Argc()>1?Cmd_Argv(1):"";int k,on=-1;
    if(!Q_strcasecmp(a,"on") || !Q_strcasecmp(a,"true") || !Q_strcasecmp(a,"yes") || !strcmp(a,"1"))on=1;
    else if(!Q_strcasecmp(a,"off") || !Q_strcasecmp(a,"false") || !Q_strcasecmp(a,"no") || !strcmp(a,"0"))on=0;
    if(!Q_strcasecmp(a,"stats")){stats_readout();return;}
    if(!Q_strcasecmp(a,"result")){
        /* "aw_mwscript_status result TOPIC NPC [N]" (dbg mwscript result; MWSCRIPT-PLAYER-CONTROL-62's test aid): the
         * result script of NPC's answer on TOPIC runs as the dialogue window runs it, without the window: the answer
         * the NPC would give now, or its N-th answer on the topic (from 1, in the table's order) whatever its
         * conditions say. TOPIC and NPC in quotes when they hold spaces. */
        int nth=Cmd_Argc()>4?atoi(Cmd_Argv(4)):0;
        if(Cmd_Argc()<4 || Cmd_Argc()>5 || nth<0){
            Con_Printf("dbg mwscript result TOPIC NPC [N]: the result script of NPC's answer on TOPIC (N: its N-th answer)\n");
            return;
        }
        if(!load()){Con_Printf("dbg mwscript result: the scripts are not loaded\n");return;}
        AW_DialWindowRunResult(Cmd_Argv(2),Cmd_Argv(3),nth);
        return;
    }
    if(!Q_strcasecmp(a,"summon")){
        /* "aw_mwscript_status summon EFFECT SECONDS" (SUMMONED-CREATURES-62): a summoning effect lands on the player for
         * SECONDS, as a cast's Self effect does (a test and evidence route) */
        aw_actor_t *p;int effect=Cmd_Argc()>2?Q_atoi(Cmd_Argv(2)):0;float seconds=Cmd_Argc()>3?(float)Q_atoi(Cmd_Argv(3)):30;
        if(!AW_EffectSummon(effect) || !(seconds>0 && seconds<=3600) || !(p=player_record())){
            Con_Printf("Usage: aw_mwscript_status summon EFFECT SECONDS (EFFECT 102-116, 134; SECONDS 1-3600)\n");return;}
        Con_Printf("Summon: effect %d on you for %.0f s: %s (creature %s)\n",effect,seconds,
                   AW_EffectsLand(p,effect,AW_EFFECT_NO_ARG,1,seconds,AW_EFFECT_NO_SOURCE)?"landed":"refused",
                   summon_creature(effect)?summon_creature(effect):"none named");
        player_store(p);
        return;
    }
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
        if(!Q_strcasecmp(f,"placeatpc")){
            /* MWSCRIPT-PLACE-OBJECTS-62: "call placeatpc ID [COUNT DISTANCE DIRECTION]" (ID: the record id of a PLAC row,
             * in quotes when it has a space), as a script's PlaceAtPC through the same host route */
            uint32_t off,rows,bytes,row;char id[64];aw_mwcell_t c[4];int found=-1;
            if(!load() || Cmd_Argc()<4 || !AW_MwvmSection("PLAC",&off,&rows,&bytes)){
                Con_Printf("dbg mwscript call placeatpc ID [COUNT DISTANCE DIRECTION]: the file must be loaded\n");return;}
            for(row=0;row<rows && found<0;row++){
                if(resident && off+12*row+12<=resident_bytes){
                    const unsigned char *p=resident+off+12*row;
                    if(read_string((p[0]<<8)|p[1],id,sizeof(id)) && same_id(id,Cmd_Argv(3)))found=(int)row;
                }
            }
            if(found<0){Con_Printf("dbg mwscript call placeatpc: %s is not named by any Place call of the game\n",Cmd_Argv(3));return;}
            c[0].i=Cmd_Argc()>4?atoi(Cmd_Argv(4)):1;c[1].f=Cmd_Argc()>5?(float)Q_atof(Cmd_Argv(5)):128.0f;
            c[2].i=Cmd_Argc()>6?atoi(Cmd_Argv(6)):0;c[3].i=found;
            {unsigned long before=places,spawned=placed_spawned;
             place_call(-1,AW_MWVM_PLAYER,AWF_PLACEATPC,c,4);
             Con_Printf("dbg mwscript call placeatpc: %s (row %d): %lu made, %lu actors spawned (%s)\n",Cmd_Argv(3),found,
                        places-before,placed_spawned-spawned,places>before?"placed":"not possible: see aw_mwscript_status");}
            return;
        }
        {   /* "call disableplayercontrols" / "call enableplayermagic" / "call getplayerjumpingdisabled" ... (the control
             * switches, MWSCRIPT-PLAYER-CONTROL-62): by the same host route a script's call takes */
            static const short fns[3][9]={
                {AWF_DISABLEPLAYERCONTROLS,AWF_DISABLEPLAYERFIGHTING,AWF_DISABLEPLAYERJUMPING,AWF_DISABLEPLAYERLOOKING,
                 AWF_DISABLEPLAYERMAGIC,AWF_DISABLEPLAYERVIEWSWITCH,AWF_DISABLEVANITYMODE,AWF_DISABLETELEPORTING,
                 AWF_DISABLELEVITATION},
                {AWF_ENABLEPLAYERCONTROLS,AWF_ENABLEPLAYERFIGHTING,AWF_ENABLEPLAYERJUMPING,AWF_ENABLEPLAYERLOOKING,
                 AWF_ENABLEPLAYERMAGIC,AWF_ENABLEPLAYERVIEWSWITCH,AWF_ENABLEVANITYMODE,AWF_ENABLETELEPORTING,
                 AWF_ENABLELEVITATION},
                {AWF_GETPLAYERCONTROLSDISABLED,AWF_GETPLAYERFIGHTINGDISABLED,AWF_GETPLAYERJUMPINGDISABLED,
                 AWF_GETPLAYERLOOKINGDISABLED,AWF_GETPLAYERMAGICDISABLED,AWF_GETPLAYERVIEWSWITCHDISABLED,
                 AWF_GETVANITYMODEDISABLED,-1,-1}};
            static const char *const pre[3]={"disable","enable","get"};
            int v,b;char name[48];
            for(v=0;v<3;v++)for(b=0;b<9;b++){
                if(fns[v][b]<0)continue;
                Q_snprintf(name,sizeof(name),"%s%s%s",pre[v],AW_ControlName(1<<b),v==2?"disabled":"");
                if(Q_strcasecmp(f,name))continue;
                r.i=0;done=host_call(-1,AW_MWVM_PLAYER,fns[v][b],NULL,0,NULL,0,&r);
                Con_Printf("dbg mwscript call %s: %s%s; switches off now: mask %d\n",name,done?"done":"not kept",
                           v==2?(r.i?", reads 1 (off)":", reads 0 (on)"):"",AW_ControlsDisabled());
                return;
            }
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
    if(!global && AWB_HELD_KEY(reference))return;   /* a held item's values are not saved (MWSCRIPT-INVENTORY-HITONME-62) */
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
     t+=k;
     k=forced_export(out+n+s+t,capacity-n-s-t-8);            /* the forced sneak and the fade (AWFS, v0.0.62) */
     if(k<0)return -1;
     t+=k;
     k=AW_WeatherScriptSave(out+n+s+t,capacity-n-s-t-8);     /* the scripts' region weather (AWWR, v0.0.62) */
     if(k<0)return -1;
     t+=k;
     k=AW_CrimeActorsExport(out+n+s+t,capacity-n-s-t-8);     /* the NPCs' crime marks and pursuers (AWCR, v0.0.62) */
     if(k<0)return -1;
     t+=k;
     k=forced_run_export(out+n+s+t,capacity-n-s-t-8);        /* the forced run (AWRN, v0.0.63) */
     if(k<0)return -1;
     t+=k;
     k=were_export(out+n+s+t,capacity-n-s-t-8);              /* the werewolf state (AWWF, v0.0.63) */
     if(k<0)return -1;
     t+=k;
     k=AW_MoverExport(out+n+s+t,capacity-n-s-t-8);           /* the scripts' moved placements (AWMV, v0.0.63) */
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
    forced_reset();V_ScreenFade(0,0);   /* MWSCRIPT-GAP-FUNCTIONS-62: an older save has no AWFS block: none, unfaded */
    AW_MoverReset();                    /* WORLD-BUTTONS-62: every scripted mover at its start until the AWMV block */
    AW_CombatLastHitReset();            /* MWSCRIPT-INVENTORY-HITONME-62: no blow of the last game is remembered */
    AW_WeatherScriptClear();            /* MWSCRIPT-COMPLETE-LANDMARK: no region's weather changed by a script */
    carried_reset();                     /* the carried items' scripts run again from their next equipping */
    AW_StandingReset();AW_CrimeActorsReset();AW_EffectsReset();AW_SoldReset();AW_MadeReset();AW_GemsReset();AW_DialReactionsReset();AW_RevealedReset();AW_DialHeardReset();
    if(aw_mwscript_packages_import)aw_mwscript_packages_import(NULL,0);   /* none until the save's block says */
    if(topic_bytes)memset(known_topics,0,topic_bytes);
    if(data && bytes>=8 && !memcmp(data+bytes-4,"AWTR",4)){
        unsigned long tail=((unsigned long)data[bytes-8]<<24)|((unsigned long)data[bytes-7]<<16)|
                           ((unsigned long)data[bytes-6]<<8)|data[bytes-5];
        if(tail<=(unsigned long)(bytes-8)){
            const unsigned char *p=data+bytes-8-tail;int s;
            actors=(int)(bytes-8-tail);
            s=p[0]=='A' && tail>=12?12+38*p[5]:0;
            if(s>0 && p[4]==2)s+=8;   /* AWPS2 (v0.0.62, CRIME-59): the crimes' numbers after the factions */
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
                if(rest+11<=tail && !memcmp(p+rest,"AWFS",4)){   /* the forced sneak and the fade (v0.0.62) */
                    int k=forced_import(p+rest,(int)(tail-rest));
                    if(k<0)Con_Printf("Saved forced sneak and fade unreadable: none kept.\n");else rest+=(unsigned long)k;
                }
                if(rest+5<=tail && !memcmp(p+rest,"AWWR",4)){   /* the scripts' region weather (v0.0.62) */
                    int k=AW_WeatherScriptLoad(p+rest,(int)(tail-rest));
                    if(k<0)Con_Printf("Saved region weather of the scripts unreadable: the game's own.\n");
                    else rest+=(unsigned long)k;
                }
                if(rest+6<=tail && !memcmp(p+rest,"AWCR",4)){   /* the NPCs' crime marks and pursuers (v0.0.62) */
                    int k=AW_CrimeActorsImport(p+rest,(int)(tail-rest));
                    if(k<0)Con_Printf("Saved crime marks unreadable: none kept.\n");else rest+=(unsigned long)k;
                }
                if(rest+7<=tail && !memcmp(p+rest,"AWRN",4)){   /* the forced run (v0.0.63) */
                    int k=forced_run_import(p+rest,(int)(tail-rest));
                    if(k<0)Con_Printf("Saved forced run unreadable: none kept.\n");else rest+=(unsigned long)k;
                }
                if(rest+79<=tail && !memcmp(p+rest,"AWWF",4)){   /* the werewolf state (v0.0.63) */
                    int k=were_import(p+rest,(int)(tail-rest));
                    if(k<0)Con_Printf("Saved werewolf state unreadable: none kept.\n");else rest+=(unsigned long)k;
                }
                if(rest+7<=tail && !memcmp(p+rest,"AWMV",4)){   /* the scripts' moved placements (v0.0.63) */
                    int k=AW_MoverImport(p+rest,(int)(tail-rest));
                    if(k<0){AW_MoverReset();Con_Printf("Saved moved objects unreadable: they stand where the game put them.\n");}
                    else rest+=(unsigned long)k;
                }
                if(rest+6<=tail && !memcmp(p+rest,"AWPK",4) && aw_mwscript_packages_import &&
                   !aw_mwscript_packages_import(p+rest,(int)(tail-rest)))Con_Printf("Saved actor packages unreadable: none kept.\n");
            }
        }
    }
    if(!AW_MwscriptActors())return;
    if(!AW_ActorStateImport(data,actors))Con_Printf("Saved actor records unreadable: actors start from the game data.\n");
}
/* NEWGAME-STATE-RESET-62 (the reset registry, aw_reset.h; registered in aw_loadfail.c): the scripts' whole session as a
 * fresh start has it. The interpreter is loaded again from the kept file (every instance, local, timer and running
 * script gone, the globals at their start values), the journal topics forgotten, the session tables a save load
 * resets (standing and crime, effects, sold, made, gems, faction reactions, revealed places, topic pages, forced
 * sneak and fade, the actors' packages and changed actor records: actors_import with no save), and the object state
 * of this session dropped (the old fixed table, the hidden edicts, the reference cache); the next map attaches anew.
 * A menu New Game used to keep all of it (only the globals were set again from the cleared list), so a second game's
 * scripts ran on with the first game's instances: the Census office's lights out, its items not to be taken. */
void AW_MwscriptNewGameReset(void){
    actors_import(NULL,0);
    if(resident && AW_MwvmLoaded()){
        if(!AW_MwvmLoad(resident,resident_bytes,&host)){free(resident);resident=NULL;load_failed=0;}
        else AW_MwscriptResultsPrepare();
        if(topic_values && topic_offsets)memset(topic_values,0,sizeof(int32_t)*(size_t)AW_MwvmTopicCount());
    }
    if(topic_bytes && known_topics)memset(known_topics,0,topic_bytes);
    object_count=0;hidden_count=0;edict_ref_count=0;leaving_count=0;crossing_count=0;
    nremoved=0;nlevelled=0;npcadd=0;last_taken=0;   /* MWSCRIPT-UNPLACED-ATTACH-62: nothing of the old game queued */
    memset(knocks,0,sizeof(knocks));player_diseased=-1;
    map_model=script_model=NULL;map_name[0]=0;
}
/* the scripts' state for the reset check, the same whether the file is loaded yet or not (a fresh start has not
 * loaded it): the globals that differ from their start values and the topics known. The instance count is left out:
 * a loaded interpreter starts its global scripts at once (seen 7 November 2026: it always differed from the boot). */
unsigned long AW_MwscriptDigest(void){
    unsigned long h=2166136261UL,changed=0,known=0;int g,i;
    for(g=0;g<AW_MwvmGlobalCount();g++)if(AW_MwvmGlobalBits(g)!=AW_MwvmGlobalStart(g))changed++;
    for(i=0;known_topics && i<topic_bytes;i++)if(known_topics[i])known++;
    h=((h^changed)*16777619UL)&0xffffffffUL;
    return ((h^known)*16777619UL)&0xffffffffUL;
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
static void crime_disposition(edict_t *e,int change,int permanent);
static void crime_calm(edict_t *e);
static int crime_guard(edict_t *e);
static int crime_greet(edict_t *e);
/* DIALOGUE-AGGRO-62 (quakedef.h aw_ambient_fight_now): the Fight of E's live record (a SetFight or ModFight of a script
 * or an answer lands there), -1 when it has none or is dead; never a search of the actor table on disk */
static int ambient_fight_now(edict_t *e){
    eval_t *r=e && e!=sv_player?GetEdictFieldValue(e,"aw_ref"):NULL;aw_actor_t *a;
    a=r && r->_float>0?AW_ActorGet((uint32_t)r->_float,AW_ACTOR_NONE,0):NULL;
    return a && !(a->flags&AWL_DEAD)?(int)AW_ActorStat(a,AWA_FIGHT):-1;
}
void AW_MwscriptInit(void){
    Cvar_RegisterVariable(&mwscript);
    stats_hooks();
    aw_actors_ref_flags=actors_ref_flags;aw_actors_forget=AW_ActorForget;aw_save_notice=save_notice;
    aw_save_other_ok=save_other_ok;aw_save_ident_refresh=save_ident_refresh;aw_save_migrate=save_migrate;
    aw_save_drop_actor_records=save_drop_actor_records;
    aw_save_new_game=new_game_hook;   /* the original's run-once new-game scripts (NPC-STORY-DISABLED-AT-START-42) */
    AW_FallInit();                    /* held and falling actors (SCRIPTED-EVENT-FALLING-MAGE-61) */
    aw_worldui_equip_script=equip_script;   /* OnPCEquip and PCSkipEquip (MWSCRIPT-GAP-FUNCTIONS-62) */
    aw_inventory_equip_script=equip_script;   /* and the console's equip / unequip (MWSCRIPT-UNPLACED-RECORD-SCRIPTS-61) */
    AW_StandingReset();AW_EffectsReset();
    aw_save_actors_export=actors_export;aw_save_actors_import=actors_import;   /* the actor record (feature 16) */
    aw_save_objects_export=objects_export;aw_save_objects_import=objects_import;
    aw_save_script_export=script_export;aw_save_script_import=script_import;   /* CELL-CHANGES-59 slice 4 */
    aw_state_fact_get=fact_get;aw_state_fact_set=fact_set;   /* named globals past 32: the list's facts (slice 4) */
    aw_object_lock_level=AW_ObjectLockLevel;   /* the doors read a script's Lock and Unlock */
    aw_object_lock=AW_ObjectLock;aw_door_open=door_open;   /* CELL-CHANGES-59 slice 2: the key's unlock, door poses */
    aw_scene_intercept=aw_hinged_intercept=object_intercept;
    aw_item_added=item_added;   /* OnPCAdd (CENSUS-INTRO-SCRIPTS-62) */
    aw_item_removed=item_removed;   /* a carried item's script stops with the last one (MWSCRIPT-UNPLACED-ATTACH-62) */
    aw_actors_levelled_spawned=levelled_spawned;   /* a levelled pick runs its record's script (the same item) */
    aw_inventory_intercept=object_intercept;   /* OnActivate takes a placed item's use */   /* OnActivate takes a door's use */
    aw_actor_disabled=AW_ObjectDisabled;   /* the CHIM window spawns no disabled actor */
    aw_actors_visitors=room_visitors;      /* PositionCell: a room spawns the actors moved into it (v0.0.62) */
    aw_scene_followers=followers;          /* the player's followers through a door (v0.0.62) */
    aw_static_flame_gone=AW_ObjectDisabled;   /* a taken candle's flame goes with it (TAKEN-LIGHT-FLAME-STAYS-60) */
    aw_lamp_gone=AW_ObjectDisabled;           /* and outdoors its night lamp light (TAKEN-LIGHT-FLAME-61) */
    aw_inventory_made_item=AW_MadeItemAt;   /* enchanted items (aw_made_N) read through the inventory */
#ifdef AW_COMBAT_EFFECT_MAGNITUDE
    aw_combat_effect_magnitude=effect_magnitude_of;   /* RESIST-NORMAL-WEAPONS-61: the blow's resistance (v0.0.61-weapons) */
#endif
    Cmd_AddCommand("aw_mwscript_status",status);
    Cmd_AddCommand("aw_mw_target",mw_target);   /* MW-CONSOLE-COMMANDS-62: the console target finder (dbg mw target) */
    /* STEAL-WITNESSED-NO-CRIME-61: the crime rules read the witnesses and the player here */
    aw_crime_witness=crime_witness;aw_crime_attack=crime_attack;aw_crime_thief=crime_thief;
    /* CRIME-59: the other crimes, the arrest and the fine */
    aw_crime_disposition=crime_disposition;aw_crime_calm=crime_calm;aw_crime_greet=crime_greet;aw_crime_guard=crime_guard;
    /* StopCombat and the crime's calm end an actor's fight (MWSCRIPT-STOPCOMBAT-UNWIRED-62: the hook was never set,
     * so StopCombat and a paid fine left the fight going) */
    if(!aw_mwscript_combat_end)aw_mwscript_combat_end=AW_CombatActorEnd;
    aw_combat_attacked=attacked_hook;   /* GetAttacked (MWSCRIPT-GAPS-63) */
    aw_combat_player_kill=were_kill_hook;   /* GetWerewolfKills (MWSCRIPT-GAPS-63) */
    aw_combat_weapon_hit=weapon_hit;   /* HitOnMe: the last weapon per victim (MWSCRIPT-INVENTORY-HITONME-62) */
    aw_ambient_fight_now=ambient_fight_now;   /* DIALOGUE-AGGRO-62: a bystander's raised Fight counts */
    AW_CrimeInit();
}
/* the speaker of a conversation attacks when its Fight rating with the conversation's disposition reaches 100 */
int AW_MwscriptSpeakerAggro(edict_t *e,int disposition){
    eval_t *v,*r;aw_actor_t *a;aw_fighter_t sheet;int got;
    if(!e || e==sv_player || !(v=GetEdictFieldValue(e,"aw_source_id")) || !v->string)return -1;
    r=GetEdictFieldValue(e,"aw_ref");
    if(!(a=speaker_actor(pr_strings+v->string,r?(unsigned long)r->_float:0)) || (a->flags&AWL_DEAD))return -1;
    if(AW_CombatFighter(e))return 0;              /* fighting already (an answer's StartCombat) */
    if(!AW_CombatActorLoad(pr_strings+v->string,&sheet))return -1;
    to_fighter(a,&sheet);
    /* DIALOGUE-AGGRO-62: the Fight the actor has now (an answer's SetFight, a persuasion's change), not the sheet's */
    {float f=AW_ActorStat(a,AWA_FIGHT);sheet.fight=(unsigned char)(f<0?0:f>100?100:f);}
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
/* isClass(actor, "guard"): the class string read once per class (a few classes in an area), then kept by its string
 * number (16 rows) */
static int guard_class(int clas){
    static struct {int clas,guard;} known[16];static int nknown;int i;char name[32];
    if(clas==AW_ACTOR_NONE)return 0;
    for(i=0;i<nknown;i++)if(known[i].clas==clas)return known[i].guard;
    i=read_string(clas,name,sizeof(name)) && !Q_strcasecmp(name,"guard");
    if(nknown<16){known[nknown].clas=clas;known[nknown].guard=i;nknown++;}
    return i;
}
static aw_actor_t *crime_actor(edict_t *e){
    eval_t *v,*r;aw_actor_t *a;
    if(!e || e==sv_player || !(v=GetEdictFieldValue(e,"aw_source_id")) || !v->string)return NULL;
    r=GetEdictFieldValue(e,"aw_ref");
    /* the live record by its reference alone (the area load made it from the area's stat block): no search of the
     * actor table on disk; s12: the first theft's seven searches and class reads took 650 ms. The search only for a
     * record not made yet. */
    a=r && r->_float>0?AW_ActorGet((uint32_t)r->_float,AW_ACTOR_NONE,0):NULL;
    if(!a)a=speaker_actor(pr_strings+v->string,r?(unsigned long)r->_float:0);
    return a && a->kind==0?a:NULL;   /* NPCs only */
}
static int crime_witness(edict_t *e,aw_crime_witness_t *w){
    aw_actor_t *a;aw_actor_base_t b;const aw_fighter_t *f;int want=w->want_faction;vec3_t d;
    memset(w,0,sizeof(*w));
    if(!(a=crime_actor(e)))return 0;
    f=AW_CombatFighter(e);
    w->can_report=!(a->flags&AWL_DEAD) && e->v.health>=0 && !(f && (f->dead || f->knocked));   /* canReportCrime */
    w->engaged=f && !f->dead;
    w->alarm=(int)AW_ActorStat(a,AWA_ALARM);w->fight=(int)AW_ActorStat(a,AWA_FIGHT);
    w->disposition=(int)AW_ActorStat(disposition_restore(a),AWA_DISPOSITION);
    w->reference=a->reference;
    if(AW_ActorBase(a->base,&b)){
        w->guard=guard_class(b.clas);
        if(want && b.faction!=AW_ACTOR_NONE && !read_string(b.faction,w->faction,sizeof(w->faction)))w->faction[0]=0;
    }
    /* isAggressive: its Fight with the disposition and distance biases at 100, or fighting already */
    if(sv_player && AW_CombatAiLoaded()){
        VectorSubtract(e->v.origin,sv_player->v.origin,d);
        w->aggressive=w->engaged || AW_CombatFightRating(&aw_combat_ai,w->fight,w->disposition+AW_CrimeDispositionOf(a->reference),
                                                         (float)Length(d)/AW_MOVE_UNIT_SCALE)>=100;
    }
    w->observer.sneak=AW_ActorStat(a,AWA_SKILL+19);w->observer.agility=AW_ActorStat(a,AWA_ATTRIBUTE+3);
    w->observer.luck=AW_ActorStat(a,AWA_ATTRIBUTE+7);
    w->observer.blind=a->reference?AW_EffectsMagnitude(a->reference,47,AW_EFFECT_NO_ARG):0;   /* Blind */
    w->observer.fatigue_term=fatigue_term_of(a->dyn_cur[2],a->dyn_base[2]);
    return 1;
}
/* CRIME-59: the crime rules' other acts on an NPC: a disposition change for good (a victim's: its base), the calm after
 * a fine (its fight ends, its Fight back to its record's), the guard's arrest talk, its class */
static void crime_disposition(edict_t *e,int change,int permanent){
    aw_actor_t *a=crime_actor(e);
    if(!a || !permanent)return;
    AW_ActorModStat(disposition_restore(a),AWA_DISPOSITION,(float)change);disposition_keep(a);AW_MwvmStateChanged();
}
static void crime_calm(edict_t *e){
    aw_actor_t *a=crime_actor(e);aw_actor_base_t b;
    if(AW_CombatFighter(e) && aw_mwscript_combat_end){aw_mwscript_combat_end(e);combat_stops++;}
    if(!a)return;
    a->flags&=~AWL_COMBAT;
    if(AW_ActorBase(a->base,&b))AW_ActorSetStat(a,AWA_FIGHT,(float)b.fight);   /* getBaseFightRating */
    AW_MwvmStateChanged();
}
/* AiPursue's arrest (OpenMW 0.51 aipursue.cpp: pushGuiMode(GM_Dialogue, actor) once near and in sight, whatever the
 * talk prompt's rules): the greeting as a talk would play it; when the general talk rule refuses the actor (an
 * opening-scene role: the census office's guards, STEAL-WITNESSED-NO-CRIME-61) the conversation opens directly, its
 * greeting picked from the dialogue table with the live conditions (Alarmed, CharGenState). Not a dead or fighting one. */
static int crime_greet(edict_t *e){
    aw_actor_t *a=crime_actor(e);const aw_fighter_t *f=e?AW_CombatFighter(e):NULL;
    if(force_greeting(e))return 1;
    if(!a || (a->flags&AWL_DEAD) || f || AW_DialWindowActive())return 0;
    if(!AW_DialWindowOpen(e,"",0))return 0;
    greetings++;return 1;
}
static int crime_guard(edict_t *e){
    aw_actor_t *a=crime_actor(e);aw_actor_base_t b;
    return a && AW_ActorBase(a->base,&b) && guard_class(b.clas);
}
/* a global by name set to VALUE (updateDialogueGlobals); 0 when the file has no such global */
static int crime_set_global(const char *name,int value){
    int g,type=0;aw_mwcell_t c;
    if(!AW_MwvmLoaded())return 0;
    global_names_load();
    for(g=0;global_names && global_offsets && g<global_count;g++)
        if(global_offsets[g]>=0 && same_id(global_names+global_offsets[g],name)){
            AW_MwvmGlobalName(g,&type);
            if(type==2)c.f=(float)value;else c.i=value;
            if(AW_MwvmGlobalBits(g)!=(uint32_t)c.i)AW_MwvmGlobalSetBits(g,(uint32_t)c.i);
            return 1;
        }
    return 0;
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
    f->base+=AW_CrimeDispositionOf(reference);   /* CRIME-59: the crime's temporary change */
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
/* MWSCRIPT-RESULT-LONG-FRAME-62: a result held its frame 4.6 to 8.4 s: every result opened the file and binary-searched
 * the 7,411 DRSC rows on disk, each probe a seek that refilled the 16 KB file buffer. Now the file is opened once (a
 * 1 KB buffer, kept open as the strings' handle is), the DRSC index is read when a talk opens, and a result reads one
 * block of 64 rows (768 bytes) into memory, which the probes then use. */
static FILE *results_file;static long results_base;
static unsigned char results_block[12*AW_DRSC_BLOCK];static long results_block_at=-1;static uint32_t results_block_bytes;
static unsigned long results_reads;   /* disk reads for the DRSC rows (the test and dbg count) */
static int results_open(void){
    if(!results_file){
        extern int com_fopen_buffer;int got;
        com_fopen_buffer=1024;got=COM_FOpenFile(FILE_NAME,&results_file);com_fopen_buffer=0;
        if(got<=0 || !results_file){if(results_file)fclose(results_file);results_file=NULL;return 0;}
        results_base=ftell(results_file);results_block_at=-1;
    }
    return 1;
}
/* the file's bytes at OFFSET (from its start), for the DRSC rows: served from the block in memory when it holds them */
static int read_file_at(void *user,uint32_t offset,void *out,uint32_t bytes){
    uint32_t off,rows,size,at;(void)user;
    if(!results_file)return 0;
    if(AW_MwvmSection("DRSC",&off,&rows,&size) && offset>=off && offset+bytes<=off+12u*rows){
        at=off+(offset-off)/sizeof(results_block)*sizeof(results_block);
        if(results_block_at!=(long)at){
            uint32_t n=off+12u*rows-at;if(n>sizeof(results_block))n=sizeof(results_block);
            results_reads++;results_block_at=-1;
            if(fseek(results_file,results_base+(long)at,SEEK_SET) || fread(results_block,1,n,results_file)!=n)return 0;
            results_block_at=(long)at;results_block_bytes=n;
        }
        if(offset-at+bytes>results_block_bytes)return 0;
        memcpy(out,results_block+(offset-at),bytes);return 1;
    }
    results_reads++;
    return !fseek(results_file,results_base+(long)offset,SEEK_SET) && fread(out,1,bytes,results_file)==bytes;
}
static void results_close(void){if(results_file){fclose(results_file);results_file=NULL;}results_block_at=-1;}
/* the index's reads (every block's first row, in order): each block read whole and in sequence, so the section is
 * read once from start to end (no seek between blocks), about 89 KB, at the scripts' load */
static long index_next=-1;
static int read_index_row(void *user,uint32_t offset,void *out,uint32_t bytes){
    uint32_t off,rows,size,n;(void)user;
    if(!results_file || !AW_MwvmSection("DRSC",&off,&rows,&size) || offset<off)return 0;
    n=off+12u*rows-offset;if(n>sizeof(results_block))n=sizeof(results_block);
    if(n<bytes)return 0;
    if(index_next!=(long)offset && fseek(results_file,results_base+(long)offset,SEEK_SET))return 0;
    results_reads++;results_block_at=-1;
    if(fread(results_block,1,n,results_file)!=n){index_next=-1;return 0;}
    index_next=(long)offset+(long)n;
    memcpy(out,results_block,bytes);return 1;
}
/* the scripts' load and a talk's open (aw_dialwin.c): the DRSC index read once per load, so a result reads one block */
void AW_MwscriptResultsPrepare(void){
    if(AW_MwvmLoaded() && results_open()){index_next=-1;AW_MwvmDialogueIndex(read_index_row,NULL);index_next=-1;}
}
/* --- the original's console commands (MW-CONSOLE-COMMANDS-62, aw_mwconsole.h): a stat line runs through host_actor,
 * the call a compiled SetStrength or GetHealth makes; the player now (a target from the console finder later) --- */
static void console_exec(const char *text){
    if(!strncmp(text,"toggle ",7)){
        /* v0.0.63 (MW-CONSOLE-COMMANDS-62): an alias's "toggle CVAR" flips an AmiWind switch 0 <-> 1 (the original's
         * console-only toggles: ToggleCombatStats, ToggleLights), no new command */
        cvar_t *v=Cvar_FindVar((char *)text+7);
        if(!v){Con_Printf("%s: no such setting\n",text+7);return;}
        Cvar_SetValue(v->name,v->value?0.0f:1.0f);
        Con_Printf("%s %s\n",v->name,v->value?"on":"off");return;
    }
    Cbuf_InsertText("\n");Cbuf_InsertText((char *)text);
}
/* the console target (dbg mw target: picked in the finder or named): an entity and its id; 0 none (the player) */
static int console_entity;static char console_id[64];
static const char *edict_id(edict_t *e){
    eval_t *v=e?GetEdictFieldValue(e,"aw_source_id"):NULL;
    return v && v->string?pr_strings+v->string:NULL;
}
/* TARGET as a line names it ("" the console target or else the player; "player"; a reference's id: the nearest
 * entity of that id on this map, as AIFollow finds its target); NULL none */
static edict_t *console_resolve(const char *target){
    int i;float best=0;edict_t *found=NULL;
    if(!sv.active || !sv_player)return NULL;
    if(!target[0]){
        if(console_entity>0 && console_entity<sv.num_edicts){
            edict_t *e=EDICT_NUM(console_entity);const char *id=edict_id(e);
            if(!e->free && id && !Q_strcasecmp((char *)id,console_id))return e;
            console_entity=0;Con_Printf("The console target %s is gone; lines run on the player.\n",console_id);
        }
        return sv_player;
    }
    if(!Q_strcasecmp((char *)target,"player"))return sv_player;
    for(i=1;i<sv.num_edicts;i++){
        edict_t *x=EDICT_NUM(i);const char *id;vec3_t d;float dd;
        if(x->free || !(id=edict_id(x)) || Q_strcasecmp((char *)id,(char *)target))continue;
        VectorSubtract(x->v.origin,sv_player->v.origin,d);dd=DotProduct(d,d);
        if(!found || dd<best){found=x;best=dd;}
    }
    return found;
}
/* the line's target as the VM's own: the player, or a scratch instance on the reference (AW_MWVM_SELF, as a script's
 * own reference is found); 0 none */
static int console_begin(const char *target,int *instance,int *who,edict_t **edict){
    edict_t *e=console_resolve(target);eval_t *r;
    *instance=-1;*who=AW_MWVM_PLAYER;*edict=e;
    if(!e)return 0;
    if(e==sv_player)return 1;
    if(!(r=GetEdictFieldValue(e,"aw_ref")) || r->_float<=0)return 0;
    if((*instance=AW_MwvmScratch((uint32_t)r->_float,NUM_FOR_EDICT(e)))<0)return 0;
    *who=AW_MWVM_SELF;
    return 1;
}
static int console_stat(const char *target,int verb,int stat,float *value){
    static const int verbs[4]={AWV_GET,AWV_SET,AWV_MOD,AWV_MODCURRENT};
    aw_mwcell_t v,out;int whole=stat>=AWA_LEVEL,k,who;edict_t *e;
    if(!AW_MwscriptActors() || !console_begin(target,&k,&who,&e))return 0;
    if(whole)v.i=(int32_t)*value;else v.f=*value;
    out=host_actor(k,who,verbs[verb],stat,v);
    AW_MwvmScratchEnd(k);
    if(verb==AW_MWCON_GET)*value=whole?(float)out.i:out.f;
    return 1;
}
/* the AITM row of an item id (the actor table's items: what an actor carries or a script names), -1 none; the ASPT
 * row of a spell id. A scan of the rows on disk: a console line, never a frame of play */
static unsigned long console_id_probes;   /* rows read by the id lookups */
static int console_row_id(int spell,int row,char *s,int capacity){   /* the id string of an AITM / ASPT row */
    uint32_t off,rows,bytes;unsigned char b[4];aw_item_t it;
    console_id_probes++;
    if(!spell)return AW_ActorItem(row,&it) && read_string(it.id,s,capacity);
    return AW_MwvmSection("ASPT",&off,&rows,&bytes) && actor_read(NULL,off+4u*(uint32_t)row,b,4) &&
           read_string((b[0]<<8)|b[1],s,capacity);
}
static int id_compare(const char *a,const char *b){   /* folded, unsigned bytes: the builder's sort (cp1252) */
    for(;;a++,b++){
        int x=tolower((unsigned char)*a),y=tolower((unsigned char)*b);
        if(x!=y || !x)return x-y;
    }
}
/* the row of an item (SPELL 0, AITM) or spell (1, ASPT) id: a binary search over the build's sorted index (AIDX,
 * ASPX: about 13 probes), else (an older file) a scan of every row; -1 none */
static int console_row(int spell,const char *id){
    uint32_t off,rows,bytes,lo=0,hi;unsigned char b[2];char s[64];int row,c;
    if(AW_MwvmSection(spell?"ASPX":"AIDX",&off,&rows,&bytes) && rows){
        hi=rows;
        while(lo<hi){
            uint32_t mid=(lo+hi)/2;
            if(!actor_read(NULL,off+2u*mid,b,2))return -1;
            row=(b[0]<<8)|b[1];
            if(!console_row_id(spell,row,s,sizeof(s)))return -1;
            if(!(c=id_compare(s,id)))return row;
            if(c<0)lo=mid+1;else hi=mid;
        }
        return -1;
    }
    if(!AW_MwvmSection(spell?"ASPT":"AITM",&off,&rows,&bytes))return -1;
    for(lo=0;lo<rows;lo++)if(console_row_id(spell,(int)lo,s,sizeof(s)) && same_id(s,id))return (int)lo;
    return -1;
}
static int console_item_row(const char *id){return console_row(0,id);}
static int console_spell_row(const char *id){return console_row(1,id);}
static float console_number(const char *s){return (float)Q_atof((char *)s);}
static int console_command(const char *target,int command,const aw_mwcon_line_t *l,char *answer,int capacity){
    int k,who,row,n,i;edict_t *e;aw_mwcell_t numbers[6],result;unsigned char strings[4];int32_t values[13];
    const char *name=AW_MwConsoleCommandName(command,NULL);
    if(!console_begin(target,&k,&who,&e))return 0;
    result.i=0;memset(numbers,0,sizeof(numbers));memset(strings,0,sizeof(strings));
    switch(command){
    case AW_MWCON_ADDITEM:case AW_MWCON_REMOVEITEM:case AW_MWCON_GETITEMCOUNT:
        n=l->args>1?(int)console_number(l->arg[1]):1;
        if(who==AW_MWVM_PLAYER && command==AW_MWCON_ADDITEM && (row=console_item_row(l->arg[0]))<0){
            /* an item no actor carries and no script names: the player's inventory by its id (dbg give's own call) */
            if(AW_InventoryGive(l->arg[0],n))Q_snprintf(answer,capacity,"%s: %d %s given.\n",name,n,l->arg[0]);
            else Q_snprintf(answer,capacity,"%s: no such item id: %s\n",name,l->arg[0]);
            break;
        }
        if((row=console_item_row(l->arg[0]))<0){Q_snprintf(answer,capacity,"%s: no such item id: %s\n",name,l->arg[0]);break;}
        n=(int)host_item(k,who,command==AW_MWCON_ADDITEM?1:command==AW_MWCON_REMOVEITEM?2:0,row,n);
        Q_snprintf(answer,capacity,"%s %s -> %d\n",name,l->arg[0],n);
        break;
    case AW_MWCON_EQUIP:{
        aw_inventory_item_t it;
        if(who!=AW_MWVM_PLAYER){Q_snprintf(answer,capacity,"%s: the player only for now.\n",name);break;}
        if(!AW_InventoryRead(l->arg[0],&it) || !AW_InventoryEquip(&aw_state,&it))
            Q_snprintf(answer,capacity,"%s: %s not equipped (no such item, or not carried).\n",name,l->arg[0]);
        break;}
    case AW_MWCON_ADDSPELL:case AW_MWCON_REMOVESPELL:
        if((row=console_spell_row(l->arg[0]))<0){Q_snprintf(answer,capacity,"%s: no such spell id: %s\n",name,l->arg[0]);break;}
        n=(int)host_spell(k,who,command==AW_MWCON_ADDSPELL?1:2,row);
        Q_snprintf(answer,capacity,"%s %s -> %d\n",name,l->arg[0],n);
        break;
    case AW_MWCON_ENABLE:case AW_MWCON_DISABLE:case AW_MWCON_GETDISABLED:
        n=(int)host_object(k,who,command==AW_MWCON_ENABLE?AWM_ENABLE:command==AW_MWCON_DISABLE?AWM_DISABLE:AWM_GETDISABLED,0);
        if(command==AW_MWCON_GETDISABLED)Q_snprintf(answer,capacity,"%s -> %d\n",name,n);
        break;
    case AW_MWCON_GETPOS:
        i=tolower((unsigned char)l->arg[0][0])-'x';
        if(i<0 || i>2){Q_snprintf(answer,capacity,"%s: X, Y or Z.\n",name);break;}
        Q_snprintf(answer,capacity,"%s %c -> %g\n",name,'X'+i,(double)host_position(k,who,i));
        break;
    case AW_MWCON_SETPOS:case AW_MWCON_SETANGLE:case AW_MWCON_GETANGLE:
        console_texts[0]=l->arg[0];strings[0]=CONSOLE_STRING>>8;strings[1]=CONSOLE_STRING&255;
        numbers[0].f=l->args>1?console_number(l->arg[1]):0;
        host_call(k,who,command==AW_MWCON_SETPOS?AWF_SETPOS:command==AW_MWCON_SETANGLE?AWF_SETANGLE:AWF_GETANGLE,
                  numbers,command==AW_MWCON_GETANGLE?0:1,strings,1,&result);
        if(command==AW_MWCON_GETANGLE)Q_snprintf(answer,capacity,"%s %s -> %g\n",name,l->arg[0],(double)result.f);
        break;
    case AW_MWCON_POSITION:case AW_MWCON_AITRAVEL:
        for(i=0;i<3;i++)numbers[i].f=console_number(l->arg[i]);
        numbers[3].f=l->args>3?console_number(l->arg[3]):0;
        host_call(k,who,command==AW_MWCON_POSITION?AWF_POSITION:AWF_AITRAVEL,numbers,4,strings,0,&result);
        break;
    case AW_MWCON_POSITIONCELL:
        /* PositionCell X Y Z ZROT CELL: the player to the cell by dbg tp (as CenterOnCell); the point in it is not
         * applied yet. Another reference: not yet (its PMOV row is the compiler's) */
        if(who!=AW_MWVM_PLAYER || l->args<5){Q_snprintf(answer,capacity,"%s: the player and a cell name only for now.\n",name);break;}
        Q_snprintf(answer,capacity,"%s: to %s (dbg tp).\n",name,l->arg[4]);
        {char line[128];Q_snprintf(line,sizeof(line),"dbg tp \"%s\"",l->arg[4]);console_exec(line);}
        break;
    case AW_MWCON_AIWANDER:
        for(n=0;n<l->args && n<AW_MWCON_ARGS;n++)values[n]=(int32_t)console_number(l->arg[n]);
        host_wander(k,who,values,n);
        break;
    case AW_MWCON_AIFOLLOW:case AW_MWCON_AIESCORT:
        /* AIFollow ID DURATION [X Y Z]; AIEscort ID DURATION X Y Z */
        console_texts[0]=l->arg[0];strings[0]=CONSOLE_STRING>>8;strings[1]=CONSOLE_STRING&255;
        for(i=1;i<l->args && i<5;i++)numbers[i-1].f=console_number(l->arg[i]);
        host_call(k,who,command==AW_MWCON_AIFOLLOW?AWF_AIFOLLOW:AWF_AIESCORT,numbers,4,strings,1,&result);
        break;
    }
    console_texts[0]=NULL;
    AW_MwvmScratchEnd(k);
    return 1;
}
/* --- every other function the interpreter carries out, by the compiler's own table (id1/mwconsole-functions.txt,
 * tools/mwscript_console.py from tools/mwscript/functions.py): read a line at a time from the disk when a name is
 * not one of the console's own; nothing of it stays in memory. A line: NAME KIND ...; kind host: NUMBER RET ARGS
 * (the host's call by number, the arguments typed by the letters: c S a string, l s a whole number, f a fraction,
 * x z X j the game ignores them); actor: VERB STAT RET (host_actor); special: NUMBER RET ARGS (below) --- */
static int console_table_find(const char *name,char *out,int capacity){
    FILE *f=NULL;int n=(int)strlen(name),found=0;
    {extern int com_fopen_buffer;com_fopen_buffer=1024;COM_FOpenFile("mwconsole-functions.txt",&f);com_fopen_buffer=0;}
    if(!f)return 0;
    while(fgets(out,capacity,f))
        if(!Q_strncasecmp(out,(char *)name,n) && out[n]==' '){found=1;break;}
    fclose(f);
    return found;
}
static int console_special(const char *name,int k,int who,edict_t *e,const aw_mwcon_line_t *l,char *answer,int capacity){
    int32_t v;int row;
    if(!strcmp(name,"lock")){host_object(k,who,AWM_LOCK,l->args?(int32_t)console_number(l->arg[0]):-1);return 1;}
    if(!strcmp(name,"unlock")){host_object(k,who,AWM_UNLOCK,0);return 1;}
    if(!strcmp(name,"activate")){host_object(k,who,AWM_ACTIVATE,0);return 1;}
    if(!strcmp(name,"getlocked")){Q_snprintf(answer,capacity,"getlocked -> %ld\n",(long)host_object(k,who,AWM_GETLOCKED,0));return 1;}
    if(!strcmp(name,"startcombat") || !strcmp(name,"stopcombat")){
        if(name[1]=='t' && name[2]=='a' && (!l->args || Q_strcasecmp((char *)l->arg[0],"player"))){
            Q_snprintf(answer,capacity,"startcombat: against the player only from the console for now.\n");return 1;}
        host_combat(k,who,name[2]=='a'?0:1,AW_MWVM_PLAYER);return 1;
    }
    if(!strcmp(name,"getdeadcount")){
        row=l->args?AW_ActorFind(l->arg[0]):AW_ACTOR_NONE;
        Q_snprintf(answer,capacity,"getdeadcount -> %ld\n",(long)(row==AW_ACTOR_NONE?0:host_dead_count(row)));return 1;
    }
    if(!strcmp(name,"getcurrentaipackage") || !strcmp(name,"getaipackagedone")){
        v=host_ai_package(k,who,name[3]=='c'?0:1);Q_snprintf(answer,capacity,"%s -> %ld\n",name,(long)v);return 1;}
    if(!strcmp(name,"getspell")){
        row=l->args?console_spell_row(l->arg[0]):-1;
        Q_snprintf(answer,capacity,"getspell -> %ld\n",(long)(row<0?0:host_spell(k,who,0,row)));return 1;
    }
    if(!strcmp(name,"getcommondisease") || !strcmp(name,"getblightdisease")){
        v=host_spell(k,who,name[3]=='c'?AWM_SPELL_COMMON_DISEASE:AWM_SPELL_BLIGHT_DISEASE,0);
        Q_snprintf(answer,capacity,"%s -> %ld\n",name,(long)v);return 1;
    }
    if(!strcmp(name,"getdistance")){   /* the game units between the target and the reference named (as GetDistance) */
        edict_t *o=l->args?console_resolve(l->arg[0]):NULL;vec3_t d;
        if(!o || !e){Q_snprintf(answer,capacity,"getdistance: no such reference here.\n");return 1;}
        VectorSubtract(o->v.origin,e->v.origin,d);
        Q_snprintf(answer,capacity,"getdistance -> %g\n",(double)(sqrt(DotProduct(d,d))*4));return 1;
    }
    return 0;
}
static int console_table(const char *target,const aw_mwcon_line_t *l,char *answer,int capacity){
    static char row[160];char name[64],kind[16],ret[4],args[64];int a,b,k,who,i,j,nn=0,ns=0,got;edict_t *e;
    aw_mwcell_t numbers[16],result;unsigned char strings[8];const char *p;
    if(!console_table_find(l->name,row,sizeof(row)))return -1;
    args[0]=0;b=0;
    if(Q_sscanf(row,"%63s %15s",name,kind)<2)return -1;
    if(!strcmp(kind,"actor")){if(Q_sscanf(row,"%63s %15s %d %d %3s",name,kind,&a,&b,ret)<5)return -1;}
    else if(Q_sscanf(row,"%63s %15s %d %3s %63s",name,kind,&a,ret,args)<4)return -1;
    if(!console_begin(target,&k,&who,&e))return 0;
    memset(numbers,0,sizeof(numbers));memset(strings,0,sizeof(strings));result.i=0;
    if(!strcmp(kind,"actor")){   /* A the verb, B the stat */
        aw_mwcell_t v;int whole=b>=AWA_LEVEL && a!=AWV_RATIO;
        v.i=0;
        if(a!=AWV_GET && a!=AWV_RATIO){
            if(!l->args){Q_snprintf(answer,capacity,"%s: one number.\n",l->name);AW_MwvmScratchEnd(k);return 1;}
            if(whole)v.i=(int32_t)console_number(l->arg[0]);else v.f=console_number(l->arg[0]);
        }
        result=host_actor(k,who,a,b,v);
        if(a==AWV_GET || a==AWV_RATIO)Q_snprintf(answer,capacity,"%s -> %g\n",l->name,whole?(double)result.i:(double)result.f);
        AW_MwvmScratchEnd(k);return 1;
    }
    if(!strcmp(kind,"special")){
        got=console_special(name,k,who,e,l,answer,capacity);
        AW_MwvmScratchEnd(k);return got?1:-1;
    }
    for(i=0,j=0,p=args;*p && *p!='\n' && j<l->args;p++){
        if(*p=='/' || *p=='-')continue;
        if(*p=='j'){continue;}
        if((*p=='c' || *p=='S' || *p=='x' || (*p=='z' && !isdigit((unsigned char)l->arg[j][0]))) && ns<4){
            console_texts[ns]=l->arg[j];strings[2*ns]=CONSOLE_STRING>>8;strings[2*ns+1]=(unsigned char)(CONSOLE_STRING&255)+ns;
            ns++;j++;
        }else if(nn<16){
            if(*p=='f')numbers[nn].f=console_number(l->arg[j]);else numbers[nn].i=(int32_t)console_number(l->arg[j]);
            nn++;j++;
        }
        i++;
    }
    got=host_call(k,who,a,numbers,nn,strings,ns,&result);
    for(i=0;i<4;i++)console_texts[i]=NULL;
    AW_MwvmScratchEnd(k);
    if(!got)Q_snprintf(answer,capacity,"%s: not carried out here with these arguments.\n",l->name);
    else if(ret[0]=='l')Q_snprintf(answer,capacity,"%s -> %ld\n",l->name,(long)result.i);
    else if(ret[0]=='f')Q_snprintf(answer,capacity,"%s -> %g\n",l->name,(double)result.f);
    return 1;
}
static void console_print(const char *text){Con_Printf("%s",text);}
int AW_MwConsoleLine(const char *text){
    static const aw_mwcon_host_t h={console_exec,console_command,console_stat,console_print,console_table};
    return AW_MwConsoleRun(text,&h);
}
/* --- the console target finder (dbg mw target; the original selects by a click): the references of this map with an
 * id, nearest first, typed to filter by name, id, kind; Enter sets the target of lines without "id->". The rows are
 * held only while the box is open --- */
#define FINDER_ROWS 256
typedef struct {short entity;char label[80];} finder_row_t;
static finder_row_t *finder;static int finder_count;
static const char *finder_label(void *ctx,int row){(void)ctx;return row>=0 && row<finder_count?finder[row].label:"";}
static void finder_set(edict_t *e){
    const char *id=edict_id(e);
    if(!e || !id){console_entity=0;console_id[0]=0;Con_Printf("Console target: the player.\n");return;}
    console_entity=NUM_FOR_EDICT(e);Q_snprintf(console_id,sizeof(console_id),"%s",id);
    Con_Printf("Console target: %s (lines without id-> run on it; dbg mw target clear: the player).\n",console_id);
}
static void finder_chosen(void *ctx,int row){(void)ctx;if(row>=0 && row<finder_count)finder_set(EDICT_NUM(finder[row].entity));}
static void finder_closed(void *ctx){(void)ctx;if(finder)free(finder);finder=NULL;finder_count=0;}
static int finder_near(const void *a,const void *b){
    return atoi(((const finder_row_t *)a)->label+67)-atoi(((const finder_row_t *)b)->label+67);
}
static void mw_target(void){
    aw_listbox_spec_t s;int i;
    if(Cmd_Argc()>=2 && !Q_strcasecmp(Cmd_Argv(1),"clear")){finder_set(NULL);return;}
    if(!sv.active || !sv_player){Con_Printf("Not in a game.\n");return;}
    if(Cmd_Argc()>=2){
        edict_t *e=console_resolve(Cmd_Argv(1));
        if(!e || e==sv_player)Con_Printf("No reference %s on this map.\n",Cmd_Argv(1));else finder_set(e);
        return;
    }
    if(finder || !(finder=(finder_row_t *)AW_TryMalloc(FINDER_ROWS*sizeof(*finder)))){Con_Printf("Target list: no memory.\n");return;}
    for(i=1;i<sv.num_edicts && finder_count<FINDER_ROWS;i++){
        edict_t *x=EDICT_NUM(i);const char *id=edict_id(x),*name;vec3_t d;finder_row_t *r;
        if(x->free || !id || x==sv_player)continue;
        name=x->v.netname && pr_strings[x->v.netname]?pr_strings+x->v.netname:id;
        VectorSubtract(x->v.origin,sv_player->v.origin,d);
        r=&finder[finder_count++];r->entity=(short)i;
        /* name, id, kind (its class), distance in the original's units; the distance at column 67 for the sort */
        Q_snprintf(r->label,sizeof(r->label),"%-22.22s %-24.24s %-18.18s %5d",name,id,pr_strings+x->v.classname,
                   (int)(sqrt(DotProduct(d,d))*4));
    }
    if(!finder_count){finder_closed(NULL);Con_Printf("No reference with an id on this map.\n");return;}
    qsort(finder,(size_t)finder_count,sizeof(*finder),finder_near);
    memset(&s,0,sizeof(s));
    s.title="Console target: type to filter (name, id, kind), Enter sets it";
    s.count=finder_count;s.label=finder_label;s.chosen=finder_chosen;s.closed=finder_closed;
    if(!AW_ListBoxOpen(&s))finder_closed(NULL);
}
/* the console prompt's label of the target ("" the player) */
const char *AW_MwConsoleTarget(void){return console_entity?console_id:"";}
int AW_MwscriptRunResult(const char *record,unsigned long reference,const char *text,int length){
    int speaker=-1,k,chosen,row_speaker,broken;
    if(!text || length<=0)return 0;
    for(k=0;k<AW_MwvmInstanceCount();k++){   /* the speaker's attached script, when it has one */
        aw_mwvm_instance_t *in=AW_MwvmInstance(k);
        if(in && (in->flags&(AWI_USED|AWI_GLOBAL))==AWI_USED && in->reference==(uint32_t)reference){speaker=in->script;break;}
    }
    AW_MwscriptResultsPrepare();
    if(!results_file)return 0;
    chosen=AW_MwvmFindDialogue(read_file_at,NULL,AW_MwvmTextHash(text,length),length,speaker,&row_speaker,&broken);
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
