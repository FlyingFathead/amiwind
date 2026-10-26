/* SPDX-License-Identifier: GPL-2.0-or-later
 * The game side of the compiled scripts (aw_mwvm.c): the file id1/mwscript.awm, the objects of the loaded map,
 * sounds, voices, music, the journal and the player (docs/MWSCRIPT_BYTECODE.md).
 *
 * EXPERIMENTAL, off by default (aw_mwscript 0; dbg mwscript on): the file's resident part (scripts, code and the
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

#define FILE_NAME "mwscript.awm"
#define MAX_RESIDENT (1024*1024)
#define LOOPS 32
#define SAYS 16
#define EDICT_REFS 1024
#define LOOP_ENTITY 30000          /* sound channels of placements without an edict (never a real edict) */
#define CHAN_SCRIPT 5
#define CHAN_SCRIPT_VOICE 2

static cvar_t mwscript={"aw_mwscript","0",true};
static unsigned char *resident;static unsigned long resident_bytes;
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

static const aw_mwvm_host_t host={host_sound,host_sound_playing,host_say,host_say_done,host_music,host_distance,
    host_menu_mode,host_query,host_journal_get,host_journal_set,host_notyet,host_warn,host_object,host_message,
    host_button};

/* --- loading and the map's objects --- */
static int load(void){
    FILE *f=NULL;int length,i,n;unsigned char head[16];uint32_t wanted;char name[64];long base;
    if(resident || load_failed)return resident!=NULL;
    load_failed=1;
    length=COM_FOpenFile(FILE_NAME,&f);
    if(!f){Con_Printf("MWScript: no %s in this image.\n",FILE_NAME);return 0;}
    if(length<16 || fread(head,1,16,f)!=16 || memcmp(head,"AWMS",4)){fclose(f);Con_Printf("MWScript: bad file.\n");return 0;}
    wanted=((uint32_t)head[12]<<24)|((uint32_t)head[13]<<16)|((uint32_t)head[14]<<8)|head[15];
    if(wanted<16 || wanted>MAX_RESIDENT || wanted>(uint32_t)length || !(resident=(unsigned char *)AW_TryMalloc(wanted))){
        fclose(f);Con_Printf("MWScript: cannot keep %lu bytes.\n",(unsigned long)wanted);return 0;}
    memcpy(resident,head,16);
    if(fread(resident+16,1,wanted-16,f)!=wanted-16){fclose(f);free(resident);resident=NULL;return 0;}
    fclose(f);resident_bytes=wanted;
    if(!AW_MwvmLoad(resident,resident_bytes,&host)){free(resident);resident=NULL;Con_Printf("MWScript: refused.\n");return 0;}
    n=AW_MwvmTopicCount();
    topic_offsets=(int *)AW_TryMalloc(sizeof(int)*(n+1));topic_values=(int32_t *)AW_TryMalloc(sizeof(int32_t)*(n+1));
    topic_names=(char *)AW_TryMalloc(64*(n+1));
    if(!topic_offsets || !topic_values || !topic_names){Con_Printf("MWScript: no memory for the journal names.\n");return 0;}
    f=NULL;length=COM_FOpenFile(FILE_NAME,&f);
    base=f?ftell(f):0;     /* the file's start (inside a PAK it is not 0) */
    for(i=0;i<n;i++){
        topic_offsets[i]=64*i;topic_values[i]=0;
        if(!f || length<=0 || !read_string_from(f,base,AW_MwvmTopicName(i),name,sizeof(name)))name[0]=0;
        strcpy(topic_names+64*i,name);
    }
    if(f)fclose(f);
    load_failed=0;
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
    AW_MwvmTick(dt,player);
}
static void status(void){
    const aw_mwvm_stats_t *s=AW_MwvmStats();int k,n=AW_MwvmInstanceCount(),attached=0,global=0,active=0,looping=0;
    if(!resident){Con_Printf("MWScript %s; file not loaded (dbg mwscript on).\n",mwscript.value?"on":"off");return;}
    for(k=0;k<n;k++){aw_mwvm_instance_t *in=AW_MwvmInstance(k);if(!in || !(in->flags&AWI_USED))continue;
        if(in->flags&AWI_GLOBAL)global++;else attached++;if(in->flags&AWI_ACTIVE)active++;}
    for(k=0;k<LOOPS;k++)looping+=loops[k].used;
    Con_Printf("MWScript %s: %d scripts, %lu bytes kept; map %s: %d objects (session: %lu by edict, %lu outdoor "
               "places, %lu room places, %lu not attached), %d global scripts, %d active, %d sounds\n",
               mwscript.value?"on":"off",AW_MwvmScriptCount(),resident_bytes,map_name,attached,attach_edicts,
               attach_places,attach_rooms,attach_refused,global,active,looping);
    Con_Printf("frames %lu runs %lu quiet-skips %lu far %lu deferred %lu ops %lu (max %lu a frame) aborted %lu not-yet calls %lu\n",
               s->frames,s->runs,s->skipped_quiet,s->skipped_far,s->deferred,s->ops,s->max_ops_frame,s->aborted,s->notyet_calls);
    {int i,disabled=0,locks=0;
     for(i=0;i<object_count;i++){disabled+=objects[i].disabled;locks+=objects[i].lock_set;}
     Con_Printf("object state: %d disabled, %d locks set (%d of %d kept; %lu hidden, %lu over the table); uses taken by "
                "OnActivate %lu, Activate %lu\n",disabled,locks,object_count,OBJECTS,objects_hidden,objects_full,
                intercepted,activated);}
}
void AW_MwscriptInit(void){
    Cvar_RegisterVariable(&mwscript);
    aw_save_objects_export=objects_export;aw_save_objects_import=objects_import;
    aw_object_lock_level=AW_ObjectLockLevel;   /* the doors read a script's Lock and Unlock */
    aw_scene_intercept=aw_hinged_intercept=object_intercept;   /* OnActivate takes a door's use */
    aw_actor_disabled=AW_ObjectDisabled;   /* the CHIM window spawns no disabled actor */
    Cmd_AddCommand("aw_mwscript_status",status);
}
