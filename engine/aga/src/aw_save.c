/* SPDX-License-Identifier: GPL-2.0-or-later
 * Character folders, bounded slots and two validated generations per slot.
 * Writing the inactive generation never renames or truncates the active one. */
#include "quakedef.h"
#include "aw_save.h"
#include "aw_maps.h"
#ifdef AMIGA
#include <proto/dos.h>
#else
#include <dirent.h>
#endif
#include <sys/stat.h>
#include <time.h>
#include <errno.h>
static aw_save_t world,pending;
static int loading,scheduled,content_ready;
static double last_auto,settle;
static byte content_id[32];
static cvar_t autosaves={"aw_autosaves","3",true};
static const char *actor_fields[]={"aw_hello_count","aw_manual_count","aw_hello_done"};
static int make_directory(const char *directory)
{
#ifdef AMIGA
    BPTR lock=CreateDir((char *)directory);
    if(lock){UnLock(lock);return 0;}
    errno=IoErr()==ERROR_OBJECT_EXISTS?EEXIST:EIO;return -1;
#else
    return mkdir(directory,0777);
#endif
}

static int content(void)
{
    FILE *f=NULL;int n,ok;
    if(content_ready)return 1;
    n=COM_FOpenFile("save-content.bin",&f);if(!f)return 0;
    ok=n==32 && fread(content_id,1,32,f)==32;fclose(f);
    content_ready=ok;return ok;
}
static int path(char *out,int capacity,uint32_t profile,int slot,int generation)
{
    int n;
    if(!profile || slot<0 || slot>20 || generation<0 || generation>1)return 0;
    n=snprintf(out,capacity,"%s/saves/p%08lx/%c%02ld%c.aws",com_gamedir,(unsigned long)profile,
               slot<5?'m':'a',(long)(slot<5?slot:slot-4),generation?'b':'a');
    return n>0 && n<capacity;
}
static int read_file(uint32_t profile,int slot,int generation,aw_save_t *state)
{
    char filename[384];byte raw[AW_SAVE_BYTES];FILE *f;int n,extra,ok;
    if(!path(filename,sizeof(filename),profile,slot,generation))return 0;
    f=fopen(filename,"rb");if(!f)return 0;
    n=fread(raw,1,sizeof(raw),f);extra=fgetc(f);ok=!ferror(f) && extra==EOF;
    fclose(f);
    return ok && AW_SaveDecode(raw,n,state) && state->profile==profile &&
        content() && !memcmp(state->content,content_id,32);
}
static int newest(uint32_t profile,int slot,aw_save_t *state)
{
    aw_save_t other;int a=read_file(profile,slot,0,state),b=read_file(profile,slot,1,&other);
    if(b && (!a || other.sequence>state->sequence)){*state=other;return 1;}
    return a?0:-1;
}
static int scene_id(void){return AW_MapId(sv.name);}
static uint32_t actor_id(edict_t *e)
{
    eval_t *v=GetEdictFieldValue(e,"aw_ref");
    if(v && v->_float>0)return (uint32_t)v->_float;
    v=GetEdictFieldValue(e,"aw_intro_role");
    return v && v->_float>0?0x800000U+(uint32_t)v->_float:0;
}
void AW_SaveCapture(void)
{
    int i,j,k,scene;uint32_t ref;edict_t *e;eval_t *v;aw_saved_actor_t *a;
    if(!sv.active || (scene=scene_id())<0 || aw_story.stage==AW_STAGE_DEMO)return;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free || strcmp(pr_strings+e->v.classname,"aw_npc"))continue;
        ref=actor_id(e);if(!ref)continue;
        for(j=0;j<world.actor_count;j++)if(world.actors[j].reference==ref && world.actors[j].scene==scene)break;
        if(j==world.actor_count){if(j==AW_SAVE_ACTORS){Con_Printf("Save actor limit reached.\n");return;}world.actor_count++;}
        a=&world.actors[j];a->reference=ref;a->scene=scene;
        VectorCopy(e->v.origin,a->position);VectorCopy(e->v.angles,a->angles);a->angles[1]=anglemod(a->angles[1]);a->health=e->v.health;
        for(k=0;k<3;k++){
            v=GetEdictFieldValue(e,(char *)actor_fields[k]);
            if(k==0)a->hello_count=v?(int)v->_float:0;
            else if(k==1)a->manual_count=v?(int)v->_float:0;
            else a->hello_done=v?(int)v->_float:0;
        }
    }
}
void AW_SaveSpawn(void)
{
    int i,j,k,scene=scene_id();edict_t *e;eval_t *v;uint32_t ref;aw_saved_actor_t *a;
    if(loading){
        if(strcmp(sv.name,pending.scene)){loading=0;Con_Printf("Saved scene could not be loaded.\n");return;}
        world=pending;aw_story=world.story;aw_character=world.character;aw_state=world.state;
        AW_BarrierLoad();AW_OpeningSpawn();
    }
    if(aw_story.stage==AW_STAGE_DEMO)return;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);if(e->free || strcmp(pr_strings+e->v.classname,"aw_npc"))continue;
        ref=actor_id(e);if(!ref)continue;
        for(j=0;j<world.actor_count;j++){
            a=&world.actors[j];if(a->reference!=ref || a->scene!=scene)continue;
            VectorCopy(a->position,e->v.origin);VectorCopy(a->angles,e->v.angles);e->v.health=a->health;
            for(k=0;k<3;k++){
                v=GetEdictFieldValue(e,(char *)actor_fields[k]);
                if(v)v->_float=k==0?a->hello_count:k==1?a->manual_count:a->hello_done;
            }
            SV_LinkEdict(e,false);break;
        }
    }
    if(loading){
        e=svs.clients[0].edict;
        VectorCopy(world.position,e->v.origin);VectorCopy(world.position,e->v.oldorigin);
        VectorCopy(world.angles,e->v.angles);VectorCopy(world.angles,cl.viewangles);e->v.fixangle=1;
        VectorCopy(vec3_origin,e->v.velocity);e->v.health=aw_character.current[0];SV_LinkEdict(e,false);
        loading=0;scheduled=0;last_auto=realtime;Con_Printf("Game restored: %s.\n",aw_story.name);
    }else AW_SaveSchedule();
}
void AW_SaveReset(void){memset(&world,0,sizeof(world));loading=scheduled=0;last_auto=realtime;}
int AW_SaveAllowed(void)
{
    return sv.active && svs.maxclients==1 && aw_story.stage==AW_STAGE_RELEASED && aw_character.valid &&
        svs.clients && svs.clients[0].edict && svs.clients[0].edict->v.health>0 &&
        svs.clients[0].edict->v.movetype==MOVETYPE_WALK &&
        !AW_CharacterActive() && !AW_ReaderActive() && !loading && scene_id()>=0;
}
uint32_t AW_SaveProfile(void){return world.profile;}
int AW_AutosaveCount(void)
{
    int n=(int)autosaves.value;if(n<0)n=0;if(n>16)n=16;return n;
}
void AW_SetAutosaveCount(int n)
{
    if(n<0)n=0;
    if(n>16)n=16;
    Cvar_SetValue(autosaves.name,n);
}
static int make_profile(void)
{
    char directory[384],info[400];uint32_t id;int i,n;FILE *f;
    n=snprintf(directory,sizeof(directory),"%s/saves",com_gamedir);
    if(n<1 || n>=(int)sizeof(directory))return 0;
    if(make_directory(directory)<0 && errno!=EEXIST)return 0;
    if(world.profile)return 1;
#ifdef AMIGA
    {
        struct DateStamp stamp;
        DateStamp(&stamp);
        id=(uint32_t)stamp.ds_Days*86400U+(uint32_t)stamp.ds_Minute*60U+(uint32_t)stamp.ds_Tick/50U;
    }
#else
    id=(uint32_t)time(NULL);
#endif
    if(!id)id=1;
    for(i=0;i<100;i++,id++){
        snprintf(directory,sizeof(directory),"%s/saves/p%08lx",com_gamedir,(unsigned long)id);
        if(make_directory(directory)==0)break;
        if(errno!=EEXIST)return 0;
    }
    if(i==100)return 0;
    world.profile=id;
    /* Advisory browser label only. It is never trusted as saved gameplay data. */
    snprintf(info,sizeof(info),"%s/name.txt",directory);f=fopen(info,"wb");
    if(f){fwrite(aw_story.name,1,strlen(aw_story.name),f);fclose(f);}
    return 1;
}
int AW_SaveWrite(int slot)
{
    byte raw[AW_SAVE_BYTES];aw_save_t check;char filename[384],label[32];
    FILE *f;int n,side,ok,i;edict_t *p;
    if(!AW_SaveAllowed() || slot<0 || slot>20 || !content() || !make_profile()){
        Con_Printf("Save unavailable: complete registration and release first, and check the writable save folder.\n");return 0;
    }
    AW_SaveCapture();p=svs.clients[0].edict;
    world.story=aw_story;world.state=aw_state;world.character=aw_character;world.character.current[0]=p->v.health;
    VectorCopy(p->v.origin,world.position);VectorCopy(cl.viewangles,world.angles);world.angles[1]=anglemod(world.angles[1]);strcpy(world.scene,sv.name);
    memcpy(world.content,content_id,32);
    if(world.sequence==0xffffffffU)return 0;
    world.sequence++;
    sprintf(label,slot>=5?"Autosave %ld":slot?"Manual %ld":"Quicksave",(long)(slot>=5?slot-4:slot));
    memset(world.label,0,sizeof(world.label));strcpy(world.label,label);
    n=AW_SaveEncode(raw,sizeof(raw),&world);if(!n){Con_Printf("Save state validation failed; previous saves retained.\n");return 0;}
    side=newest(world.profile,slot,&check);side=side==0?1:0;
    if(!path(filename,sizeof(filename),world.profile,slot,side))return 0;
    f=fopen(filename,"wb");if(!f)return 0;
    ok=fwrite(raw,1,n,f)==(size_t)n;
    if(fflush(f))ok=0;
    if(fclose(f))ok=0;
    if(!ok || !read_file(world.profile,slot,side,&check) || check.sequence!=world.sequence){
        Con_Printf("Save write/readback failed; previous generation retained.\n");return 0;
    }
    /* Retention reduction only follows a successful new autosave. Manual and
     * other character files are never pruned by the autosave quota. */
    if(slot>=5)for(i=AW_AutosaveCount()+5;i<=20;i++){
        if(path(filename,sizeof(filename),world.profile,i,0))remove(filename);
        if(path(filename,sizeof(filename),world.profile,i,1))remove(filename);
    }
    Con_Printf("Saved %s (%ld bytes, generation %lu).\n",label,(long)n,(unsigned long)world.sequence);
    return 1;
}
int AW_SaveRead(uint32_t profile,int slot)
{
    aw_save_t candidate,other;FILE *f=NULL;char map[40];int n,i;
    if(!AW_CharacterLoad() || !content() || newest(profile,slot,&candidate)<0){
        Con_Printf("No valid compatible save generation; current game retained.\n");return 0;
    }
    snprintf(map,sizeof(map),"maps/%s.bsp",candidate.scene);n=COM_FOpenFile(map,&f);
    if(!f || n<124){if(f)fclose(f);Con_Printf("Saved scene unavailable; current game retained.\n");return 0;}
    fclose(f);
    /* Loading an older manual save must still produce newer generations than
     * every existing autosave of this character. */
    for(i=0;i<=20;i++)if(newest(profile,i,&other)>=0 && other.sequence>candidate.sequence)candidate.sequence=other.sequence;
    pending=candidate;loading=1;scheduled=0;
    IN_AWClearButtons();key_dest=key_game;
    snprintf(map,sizeof(map),"map %s\n",candidate.scene);Cbuf_AddText(map);return 1;
}
void AW_SaveSchedule(void){if(aw_story.stage==AW_STAGE_RELEASED){scheduled=1;settle=realtime+3;}}
void AW_SaveTick(void)
{
    int n,slot;aw_save_t info;uint32_t oldest=0xffffffffU;
    if(!AW_SaveAllowed() || key_dest!=key_game || sv.paused || !AW_AutosaveCount())return;
    if(!scheduled && realtime-last_auto>=300)AW_SaveSchedule();
    if(!scheduled || realtime<settle || AW_SpeechRemaining()>0)return;
    slot=5;
    for(n=5;n<5+AW_AutosaveCount();n++){
        if(!world.profile || newest(world.profile,n,&info)<0){slot=n;break;}
        if(info.sequence<oldest){oldest=info.sequence;slot=n;}
    }
    scheduled=0;last_auto=realtime;
    if(!AW_SaveWrite(slot))AW_UISubtitle("","Autosave failed. Previous saves retained.",6);
}
int AW_SaveDescription(uint32_t profile,int slot,char *out,int capacity)
{
    aw_save_t info;
    if(capacity<1)return 0;
    if(newest(profile,slot,&info)<0){out[0]=0;return 0;}
    snprintf(out,capacity,"%s / %s / L%ld",info.story.name,info.scene,(long)info.character.level);return 1;
}
static int profile_entry(const char *directory,const char *entry,uint32_t *id,char name[32])
{
    char filename[420],*endp;FILE *f;int n,i;unsigned long value;
    if(strlen(entry)!=9 || entry[0]!='p')return 0;
    for(i=1;i<9;i++)if(!((entry[i]>='0' && entry[i]<='9') || (entry[i]>='a' && entry[i]<='f')))return 0;
    value=strtoul(entry+1,&endp,16);if(*endp || !value || value>0xffffffffUL)return 0;
    *id=(uint32_t)value;memset(name,0,32);
    snprintf(filename,sizeof(filename),"%s/%.9s/name.txt",directory,entry);f=fopen(filename,"rb");
    if(f){n=fread(name,1,31,f);name[n]=0;fclose(f);}
    for(i=0;name[i];i++)if((unsigned char)name[i]<32)name[i]=' ';
    if(!name[0])strcpy(name,"Unnamed character");
    return 1;
}
int AW_SaveProfiles(uint32_t *ids,char names[][32],int capacity)
{
    char directory[384];int count=0;
#ifdef AMIGA
    BPTR lock;struct FileInfoBlock info;
#else
    DIR *dir;struct dirent *entry;
#endif
    snprintf(directory,sizeof(directory),"%s/saves",com_gamedir);
#ifdef AMIGA
    lock=Lock(directory,ACCESS_READ);if(!lock)return 0;
    if(Examine(lock,&info))while(count<capacity && ExNext(lock,&info)){
        if(info.fib_DirEntryType>0 && profile_entry(directory,(const char *)info.fib_FileName,&ids[count],names[count]))count++;
    }
    UnLock(lock);
#else
    dir=opendir(directory);if(!dir)return 0;
    while(count<capacity && (entry=readdir(dir))!=NULL){
        if(profile_entry(directory,entry->d_name,&ids[count],names[count]))count++;
    }
    closedir(dir);
#endif
    return count;
}
static void quicksave(void){AW_SaveWrite(0);}
static void quickload(void){if(world.profile)AW_SaveRead(world.profile,0);else Con_Printf("Choose a character in Load game first.\n");}
void AW_SaveInit(void)
{
    Cvar_RegisterVariable(&autosaves);Cmd_AddCommand("aw_quicksave",quicksave);Cmd_AddCommand("aw_quickload",quickload);
}
