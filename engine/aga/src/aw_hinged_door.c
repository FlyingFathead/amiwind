/* SPDX-License-Identifier: GPL-2.0-or-later
 * Ordinary hinged doors: placed DOOR records without a destination. The use
 * key turns one about its placement's origin and Z axis (the model's hinge)
 * by 90 degrees over one second, and back on the next use; its drawing and
 * collision turn with it. Rules from OpenMW (read, not copied):
 *   apps/openmw/mwclass/door.cpp Door::activate: a locked door plays
 *     "LockedDoor" and stays shut; an idle door at its placed rotation opens,
 *     otherwise closes; a moving door reverses; opening plays the DOOR
 *     record's Open Sound (SNAM), closing its Close Sound (ANAM).
 *   apps/openmw/mwworld/worldimp.cpp World::rotateDoor: Z rotation from the
 *     placed value to +90 degrees at 90 degrees a second; a step that would
 *     turn the door into an actor is undone (the door holds, its sound stops)
 *     and tried again on the next frame.
 *   components/esm3/cellref.cpp: a content file's reference is locked when it
 *     has a lock level above 0 or names a key (the builder's LOCKED flag).
 * Quake mechanisms reused: a legacy room map's door is its func_wall edict
 * (angles drawn by R_RotateBmodel, collided by SV_ClipMoveToEntity, relinked
 * by SV_LinkEdict with the rotation box); a CHIM placement keeps its yaw in
 * its render entity and its collision sine/cosine (chim/chim_chunks.c
 * ChimChunks_DoorYaw on a frame, chim/chim_room.c ChimRoom_DoorYaw in a CHIM
 * room). The census hall door is one of them; the opening story holds its
 * lock (aw_hinged_story, aw_opening.c). Cost: a closed or open door does nothing per frame;
 * the prompt looks only when a door is within reach (one point trace), and
 * only moving doors (at most one second each) are turned and tested. */
#include "quakedef.h"
#include "aw_hinged_door.h"
#include "aw_activated.h"
#include "aw_state.h"
#include "aw_inventory.h"
#include "chim/chim.h"

#define HD_ROWS 2048		/* placed doors in the table (the original game has 1,026) */
#define HD_BASES 256		/* DOOR base records named by the rows */
#define HD_SOUNDS 64		/* converted samples */
#define HD_PLACED 256		/* doors of the current map (edicts and CHIM placements) */
#define HD_REACH 56.f		/* the load doors' reach (aw_scene.c door_hit) */
#define HD_CHANNEL 6
#define HD_NAME 32
typedef struct {unsigned ref;unsigned short base;unsigned char lock,flags;} hd_row_t;
typedef struct {short open,close;char name[HD_NAME];} hd_base_t;
typedef struct {char path[28];float volume,seconds;} hd_sound_t;
typedef struct {
    unsigned pid,ref;		/* pid: the CHIM placement (edict 0) */
    int edict,row;			/* edict: the func_wall's number, 0 for a placement */
    vec3_t origin;
    float radius,closed,amount;	/* closed: placed yaw; amount: degrees open, 0..90 */
    signed char dir,sounding;	/* dir: +1 opening, -1 closing, 0 still */
    signed char held;			/* 1 while it holds against the player (the words are shown once) */
} hd_door_t;
static hd_row_t rows[HD_ROWS];static hd_base_t bases[HD_BASES];static hd_sound_t sounds[HD_SOUNDS];
static int row_count,base_count,sound_count,locked_sound=-1,loaded;
static hd_door_t placed[HD_PLACED];static int placed_count,moving,overflow;
/* DEBUG-GOD-LOCKED-DOORS-51: the K rows (every locked load door, every hinged door naming a key) and their key IDs. */
#define HD_LOCKS 512
#define HD_KEY_POOL 6144
typedef struct {unsigned ref;unsigned char lock,flags;unsigned short key;} hd_lock_t;   /* key: pool offset + 1, 0 none */
static hd_lock_t locks[HD_LOCKS];static int lock_count,key_pool_used;static char key_pool[HD_KEY_POOL];
static char key_used[48];   /* GMST sKeyUsed */
/* WORLD-BUTTONS-62: the M rows, references ascending; pid: its CHIM placement once loaded (0 none); shift: how far
 * the scripts moved it (map units); since: travel since its efrags were last relinked. 128 x 24 = 3,072 bytes. */
#define HD_MOVERS 128
typedef struct {unsigned ref,pid;vec3_t shift;float since;} hd_mover_t;
static hd_mover_t movers[HD_MOVERS];static int mover_count,mover_pending;
static void movers_pending(void);
/* dbg doorlocks on|off (the coordinator, 2026-10-27: on by default, a debug switch until lockpicks and the Open
 * spell exist; no cvar: the resident registry is full). Not saved. */
static int door_locks=1;
int (*aw_hinged_story)(unsigned ref,int event);
static int story(unsigned ref,int event){return aw_hinged_story?aw_hinged_story(ref,event):-1;}

static int valid_path(const char *s){
    int i;
    if(strncmp(s,"doors/d",7) || strlen(s)!=27 || strcmp(s+23,".wav"))return 0;
    for(i=7;i<23;i++)if(!((s[i]>='0' && s[i]<='9') || (s[i]>='a' && s[i]<='f')))return 0;
    return 1;
}
/* id1/hinged-doors.txt (tools/prepare_door_audio.py), read once:
 *   AWHD1
 *   W <doors/d<16 hex>.wav> <volume 0..1> <seconds>     samples, numbered in order
 *   B <open W or -1> <close W or -1> <name>             DOOR records, numbered in order
 *   D <reference> <B> <lock level 0..255> <flags>       placed doors, references ascending
 *   L <W>                                               the locked sound
 * A D row that breaks a rule is left out. A bad W or B row would renumber
 * every row after it, so it drops the whole table (no doors, never wrong
 * sounds or names). */
static void load(void){
    FILE *f=NULL;char line[192],path[64],extra;int a,b,c,n,bad=0;unsigned ref;float level,seconds;
    if(loaded)return;
    loaded=1;
    if(COM_FOpenFile("hinged-doors.txt",&f)<0 || !f)return;
    if(!fgets(line,sizeof(line),f) || strcmp(line,"AWHD1\n")){fclose(f);return;}
    while(fgets(line,sizeof(line),f)){
        if(line[0]=='W' && line[1]==' '){
            if(sound_count>=HD_SOUNDS || Q_sscanf(line+2,"%63s %f %f %c",path,&level,&seconds,&extra)!=3 ||
               !valid_path(path) || !(level>=0 && level<=1) || !(seconds>=0 && seconds<=30)){bad=1;break;}
            strcpy(sounds[sound_count].path,path);sounds[sound_count].volume=level;sounds[sound_count++].seconds=seconds;
        }else if(line[0]=='B' && line[1]==' '){
            hd_base_t *e;
            if(base_count>=HD_BASES || Q_sscanf(line+2,"%d %d %n",&a,&b,&n)!=2 || a<-1 || b<-1 ||
               a>=sound_count || b>=sound_count){bad=1;break;}
            e=&bases[base_count++];e->open=(short)a;e->close=(short)b;
            for(c=0;c<HD_NAME-1 && line[2+n+c] && line[2+n+c]!='\n' && line[2+n+c]!='\r';c++)
                e->name[c]=(unsigned char)line[2+n+c]<32?'?':line[2+n+c];
            e->name[c]=0;
        }else if(line[0]=='D' && line[1]==' '){
            if(row_count>=HD_ROWS || Q_sscanf(line+2,"%u %d %d %d %c",&ref,&a,&b,&c,&extra)!=4 || a<0 || a>=base_count ||
               b<0 || b>255 || c<0 || c>15 || (row_count && ref<=rows[row_count-1].ref))continue;
            rows[row_count].ref=ref;rows[row_count].base=(unsigned short)a;
            rows[row_count].lock=(unsigned char)b;rows[row_count++].flags=(unsigned char)c;
        }else if(line[0]=='L' && line[1]==' '){
            if(Q_sscanf(line+2,"%d %c",&a,&extra)==1 && a>=0 && a<sound_count)locked_sound=a;
        }else if(line[0]=='K' && line[1]==' '){
            /* a lock row: left out when it breaks a rule (out of order, no room); never renumbers anything */
            char *key;int len;
            n=0;
            if(lock_count>=HD_LOCKS || Q_sscanf(line+2,"%u %d %d%n",&ref,&b,&c,&n)!=3 || b<0 || b>255 || c<0 || c>15 ||
               (lock_count && ref<=locks[lock_count-1].ref))continue;
            key=line+2+n;while(*key==' ')key++;
            len=(int)strcspn(key,"\r\n");
            locks[lock_count].key=0;
            if(len>0){
                if(len>63 || key_pool_used+len+1>HD_KEY_POOL)continue;
                memcpy(key_pool+key_pool_used,key,len);key_pool[key_pool_used+len]=0;
                locks[lock_count].key=(unsigned short)(key_pool_used+1);key_pool_used+=len+1;
            }
            locks[lock_count].ref=ref;locks[lock_count].lock=(unsigned char)b;locks[lock_count++].flags=(unsigned char)c;
        }else if(line[0]=='U' && line[1]==' '){
            n=(int)strcspn(line+2,"\r\n");if(n>(int)sizeof(key_used)-1)n=sizeof(key_used)-1;
            memcpy(key_used,line+2,n);key_used[n]=0;
        }else if(line[0]=='M' && line[1]==' '){
            /* a scripted mover (WORLD-BUTTONS-62): left out when out of order or there is no room */
            if(mover_count>=HD_MOVERS || Q_sscanf(line+2,"%u %c",&ref,&extra)!=1 ||
               (mover_count && ref<=movers[mover_count-1].ref))continue;
            memset(&movers[mover_count],0,sizeof(movers[0]));movers[mover_count++].ref=ref;
        }else{bad=1;break;}
    }
    if(bad){row_count=base_count=sound_count=lock_count=key_pool_used=mover_count=0;locked_sound=-1;key_used[0]=0;}
    fclose(f);
}
int AW_HingedDoorRow(unsigned reference){
    int low=0,high,mid;
    load();high=row_count-1;
    while(low<=high){
        mid=(low+high)/2;
        if(rows[mid].ref==reference)return mid;
        if(rows[mid].ref<reference)low=mid+1;else high=mid-1;
    }
    return -1;
}
/* Every placed DOOR without a destination, the census hall door included: its
 * lock is the story's (aw_hinged_story, aw_opening.c), its turn is everyone's. */
static int door_row(unsigned reference){return AW_HingedDoorRow(reference);}
/* The door's own lock in the game data: its level (1 when it is locked by a key only), 0 unlocked. */
static int original_lock(int row){
    if(!(rows[row].flags&AW_HINGE_LOCKED))return 0;
    return rows[row].lock?rows[row].lock:1;
}
/* A script's Lock and Unlock (aw_mwhost.c, set there; NULL in builds and tests without it): the level the scripts
 * left on REFERENCE, ORIGINAL when they set none. */
int (*aw_object_lock_level)(unsigned reference,int original);
/* CELL-CHANGES-59 slice 2 (aw_hinged_door.h; aw_mwhost.c sets them): a lock change kept on the world change list, and
 * a door's pose there. */
int (*aw_object_lock)(unsigned reference,int lock,int level);
int (*aw_door_open)(unsigned reference,int set);
/* The pose the door comes back in: open when the world change list holds it open, or (the census hall door, and an
 * older save) when the story says so. */
static int saved_open(unsigned reference){
    return (aw_door_open && aw_door_open(reference,-1)==1) || story(reference,AW_HINGE_STORY_SPAWN)==1;
}
/* Locked now: the story's word where it has one (the opening), else a script's lock, else the table's flag. */
static int locked(const hd_door_t *d){
    int s=story(d->ref,AW_HINGE_STORY_LOCK),original=original_lock(d->row);
    if(s>=0)return s!=0;
    return door_locks && (aw_object_lock_level?aw_object_lock_level(d->ref,original):original)>0;
}
/* The K row of REFERENCE, NULL for none (binary search; rows ascending). */
static const hd_lock_t *lock_row(unsigned reference){
    int low=0,high,mid;
    load();high=lock_count-1;
    while(low<=high){
        mid=(low+high)/2;
        if(locks[mid].ref==reference)return &locks[mid];
        if(locks[mid].ref<reference)low=mid+1;else high=mid-1;
    }
    return NULL;
}
/* The game data's lock level of a placed door (GetLocked on a door no script has locked), -1 not a door here:
 * a hinged door's D row, else a load door's K row (0 when it is not locked: a load door without a K row). */
int AW_HingedDoorOriginalLock(unsigned reference){
    int row=AW_HingedDoorRow(reference);const hd_lock_t *k;
    if(row>=0)return original_lock(row);
    k=lock_row(reference);
    return k && (k->flags&AW_HINGE_LOCKED)?(k->lock?k->lock:1):-1;
}
/* The locked door's way through (OpenMW apps/openmw/mwclass/door.cpp Door::activate, rule read, not copied): the
 * player who carries the door's key opens it ("<key> used to open lock", GMST sKeyUsed); else, in god mode (dbg god),
 * the player goes through and the message box says so (the maintainer, 25 October 2026: "it should throw a
 * rectangle box text: 'God mode used to enter a locked door'"). 1 = through, 0 = refused. */
static int lock_pass(unsigned reference){
    const hd_lock_t *k=lock_row(reference);const char *key=k && k->key?key_pool+k->key-1:NULL;edict_t *p;
    char text[160];aw_inventory_item_t item;
    if(key && AW_StateGet(&aw_state,AW_ITEM,key)>0){
        memset(&item,0,sizeof(item));
        snprintf(text,sizeof(text),"%s %s",AW_InventoryRead(key,&item) && item.name[0]?item.name:key,
                 key_used[0]?key_used:"used to open lock");
        AW_UISubtitle("",text,3);
        /* the key unlocks it for good (OpenMW 0.51 door.cpp: the reference is unlocked, its level kept for a Lock) */
        if(aw_object_lock)aw_object_lock(reference,0,0);
        return 1;
    }
    p=sv.active && svs.clients?svs.clients[0].edict:NULL;
    if(p && ((int)p->v.flags&FL_GODMODE)){AW_UISubtitle("",AW_DOOR_GOD_TEXT,4);return 1;}
    return 0;
}
/* aw_scene.c (through aw_load_door_lock): a load door's lock. USE 0: 1 when it is locked now (the prompt says
 * Locked). USE 1, the player's use: 1 = refused (the LockedDoor sound to the player), 0 = through (unlocked, the
 * key, god mode, dbg doorlocks off). A script's Lock / Unlock counts (aw_object_lock_level). */
int AW_HingedDoorLoadLock(unsigned reference,int use){
    int level=AW_HingedDoorOriginalLock(reference);
    if(level<0)level=0;
    if(aw_object_lock_level)level=aw_object_lock_level(reference,level);
    if(level<=0 || !door_locks)return 0;
    if(!use)return 1;
    if(lock_pass(reference))return 0;
    AW_HingedDoorLockedSound();
    return 1;
}
static int sound_entity(const hd_door_t *d){return d->edict?d->edict:MAX_EDICTS+(int)(d-placed);}
static void play(hd_door_t *d,int sample){
    sfx_t *s;
    S_StopSound(sound_entity(d),HD_CHANNEL);d->sounding=0;
    if(sample<0 || sample>=sound_count || !Cvar_VariableValue("aw_door_sounds"))return;
    s=S_PrecacheSound(sounds[sample].path);if(!s)return;
    S_StartSound(sound_entity(d),HD_CHANNEL,s,d->origin,sounds[sample].volume,1);d->sounding=1;
}
static void pose(hd_door_t *d,float amount){
    float yaw=d->closed-amount;edict_t *e;
    if(d->edict){
        e=EDICT_NUM(d->edict);
        if(e->free)return;
        e->v.angles[1]=yaw;SV_LinkEdict(e,false);
    }else if(aw_chim_door_yaw)aw_chim_door_yaw(d->pid,yaw);
}
/* The door's own collision, nothing else: 1 and *tr when it is there. */
static int clip(hd_door_t *d,vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,trace_t *tr){
    edict_t *e;
    memset(tr,0,sizeof(*tr));tr->fraction=1;VectorCopy(end,tr->endpos);
    if(d->edict){
        e=EDICT_NUM(d->edict);
        if(e->free || !e->v.modelindex || e->v.solid!=SOLID_BSP)return 0;
        *tr=SV_ClipMoveToEntity(e,start,mins,maxs,end);return 1;
    }
    return aw_chim_door_clip && aw_chim_door_clip(d->pid,start,mins,maxs,end,tr);
}
/* The edict number of the player or solid actor near it that the door's
 * present pose overlaps, 0 for none. */
static int overlaps(hd_door_t *d){
    int i,k;edict_t *e;trace_t tr;float reach;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free || i==d->edict || (e->v.solid!=SOLID_SLIDEBOX && e->v.solid!=SOLID_BBOX) ||
           e->v.movetype==MOVETYPE_NOCLIP)continue;
        reach=d->radius+(e->v.maxs[0]>e->v.maxs[1]?e->v.maxs[0]:e->v.maxs[1])+1;
        for(k=0;k<2;k++)if(fabs(e->v.origin[k]-d->origin[k])>reach)break;
        if(k<2)continue;
        if(clip(d,e->v.origin,e->v.mins,e->v.maxs,e->v.origin,&tr) && (tr.startsolid || tr.allsolid))return i;
    }
    return 0;
}
static int is_player(int n){return n>0 && svs.clients && svs.clients[0].edict && EDICT_NUM(n)==svs.clients[0].edict;}
void AW_HingedDoorTick(double seconds){
    int i,who;hd_door_t *d;float next,old;
    if(mover_pending)movers_pending();   /* WORLD-BUTTONS-62: a moved mover loaded again goes where it was left */
    if(!moving || !sv.active)return;
    if(seconds>.1)seconds=.1;
    if(seconds<=0)return;
    for(i=0;i<placed_count;i++){
        d=&placed[i];if(!d->dir)continue;
        old=d->amount;next=old+d->dir*(float)seconds*AW_HINGE_DEGREES_PER_SECOND;
        if(next<0)next=0;
        if(next>AW_HINGE_OPEN_DEGREES)next=AW_HINGE_OPEN_DEGREES;
        pose(d,next);
        if((who=overlaps(d))!=0){
            pose(d,old);
            /* Somebody already inside the old pose (noclip, a spawn): turning on may free them. */
            if(!overlaps(d)){
                if(d->sounding){S_StopSound(sound_entity(d),HD_CHANNEL);d->sounding=0;}
                /* the player in its swing: said once per hold (AW_HINGE_HELD_TEXT) */
                if(is_player(who) && !d->held){d->held=1;AW_UISubtitle("",AW_HINGE_HELD_TEXT,3);}
                continue;
            }
            pose(d,next);
        }
        d->held=0;
        d->amount=next;
        if(next<=0 || next>=AW_HINGE_OPEN_DEGREES){
            d->dir=0;d->sounding=0;moving--;
            if(next<=0)story(d->ref,AW_HINGE_STORY_CLOSED);
        }
    }
}
static int near_eye(const hd_door_t *d,const vec3_t eye){
    vec3_t delta;float r=HD_REACH+d->radius;
    VectorSubtract(d->origin,eye,delta);
    return DotProduct(delta,delta)<r*r;
}
/* The door under the crosshair: the first thing a point trace from the eye
 * meets within reach (actors and other objects in front hide it). */
static hd_door_t *aimed(void){
    edict_t *p;vec3_t eye,end,forward,right,up;trace_t tr,own;int i;hd_door_t *d,*best=NULL;float nearest;
    if(!placed_count || !sv.active || !svs.clients)return NULL;
    p=svs.clients[0].edict;if(!p || p->v.movetype!=MOVETYPE_WALK)return NULL;
    VectorAdd(p->v.origin,p->v.view_ofs,eye);
    for(i=0;i<placed_count && !near_eye(&placed[i],eye);i++);
    if(i==placed_count)return NULL;
    AngleVectors(cl.viewangles,forward,right,up);VectorMA(eye,HD_REACH,forward,end);
    tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NORMAL,p);
    if(tr.startsolid || tr.fraction>=1)return NULL;
    nearest=tr.fraction+.5f/HD_REACH;
    for(;i<placed_count;i++){
        d=&placed[i];
        if(!near_eye(d,eye))continue;
        if(d->edict){if(tr.ent==EDICT_NUM(d->edict))return d;continue;}
        if(tr.ent!=sv.edicts || !clip(d,eye,vec3_origin,vec3_origin,end,&own))continue;
        if(own.fraction<1 && own.fraction<=nearest){best=d;nearest=own.fraction;}
    }
    return best;
}
/* Object state (v0.0.51, aw_mwhost.c sets it; NULL without the scripts): 1 when a script that reads OnActivate
 * takes the use of the door REFERENCE (the original's rule); it opens on the script's Activate. */
int (*aw_hinged_intercept)(unsigned reference);
static int use_door(hd_door_t *d,int force);
static int use(int force){
    hd_door_t *d=aimed();
    if(!d)return 0;
    if(!force && aw_hinged_intercept && aw_hinged_intercept(d->ref))return 1;
    return use_door(d,force);
}
/* A script's Activate on a placed door (aw_mwhost.c): its own use, locks kept. 0 when REFERENCE is no door here. */
int AW_HingedDoorActivate(unsigned reference){
    int i;
    for(i=0;i<placed_count;i++)if(placed[i].ref==reference)return use_door(&placed[i],0);
    return 0;
}
static int use_door(hd_door_t *d,int force){
    const hd_row_t *r=&rows[d->row];const hd_base_t *b=&bases[r->base];
    /* the story's lock (the census hall door) holds for everyone; any other lock lets the key or god mode through */
    if(!force && locked(d) && (story(d->ref,AW_HINGE_STORY_LOCK)>=0 || !lock_pass(d->ref))){
        play(d,locked_sound);story(d->ref,AW_HINGE_STORY_REFUSED);return 1;
    }
    if(!d->dir){d->dir=d->amount>0?-1:1;moving++;}
    else d->dir=(signed char)-d->dir;
    d->held=0;
    if(aw_door_open)aw_door_open(d->ref,d->dir>0);    /* where it goes, kept across maps and saves */
    if(d->dir>0)story(d->ref,AW_HINGE_STORY_OPEN);
    play(d,d->dir>0?b->open:b->close);
    return 1;
}
int AW_HingedDoorUse(void){return use(0);}
int AW_HingedDoorHint(const char **name,const char **action){
    hd_door_t *d=aimed();const hd_row_t *r;
    if(!d)return 0;
    r=&rows[d->row];
    *name=bases[r->base].name[0]?bases[r->base].name:"Door";
    *action=locked(d)?"Locked":d->dir>0 || (!d->dir && d->amount>0)?"Close: E":"Open: E";
    return 1;
}
static hd_door_t *add(unsigned reference,int row,const float *origin,float radius,float yaw){
    hd_door_t *d;
    if(placed_count>=HD_PLACED){overflow++;return NULL;}
    d=&placed[placed_count++];memset(d,0,sizeof(*d));
    d->ref=reference;d->row=row;VectorCopy(origin,d->origin);d->radius=radius;d->closed=yaw;
    return d;
}
void AW_HingedDoorMapBegin(void){
    int i;
    load();placed_count=moving=overflow=0;
    for(i=0;i<mover_count;i++){movers[i].pid=0;movers[i].since=0;}   /* placed again as the new map's chunks load */
}
/* ---- Scripted movers (WORLD-BUTTONS-62). The Ghostgate's switches (scripts GG_OpenGate1/2) raise their
 * portcullis with "ex_gg_portcullis_01"->MoveWorld z 70 for three seconds and put it back with SetAtStart; in the
 * CHIM world the portcullis is a placement without an entity, so the script's move had nothing to move. The rule
 * (OpenMW 0.51 transformationextensions.cpp OpMoveWorld, OpSetAtStart): the reference itself moves, its drawing and
 * collision with it, and SetAtStart puts it back at its placed position. Cost: a binary search of at most 128 rows
 * per placement loaded (only while the table has rows), and per moving frame one pass over the loaded chunks'
 * records of that pid; its efrags are relinked every AW_MOVER_RELINK units of travel and at the end. */
static int mover_find(unsigned reference){
    int low=0,high,mid;
    load();high=mover_count-1;
    while(low<=high){
        mid=(low+high)/2;
        if(movers[mid].ref==reference)return mid;
        if(movers[mid].ref<reference)low=mid+1;else high=mid-1;
    }
    return -1;
}
int AW_MoverCount(void){load();return mover_count;}
int AW_MoverMoved(void){
    int i,n=0;
    for(i=0;i<mover_count;i++)if(movers[i].shift[0] || movers[i].shift[1] || movers[i].shift[2])n++;
    return n;
}
/* The frames' door hook for a mover (through AW_HingedDoorPlacement): 1, the placement keeps its pid; one that has
 * moved is put where the scripts left it on the next tick (the record is still being read now). */
int AW_MoverPlacement(unsigned pid,unsigned reference){
    int i;
    if(!mover_count && loaded)return 0;
    if((i=mover_find(reference))<0)return 0;
    movers[i].pid=pid;
    if(movers[i].shift[0] || movers[i].shift[1] || movers[i].shift[2]){movers[i].since=-1;mover_pending=1;}
    return 1;
}
static void mover_place(hd_mover_t *m,const float *d,int relink){
    if(m->pid && aw_chim_place_shift)aw_chim_place_shift(m->pid,d,relink);
}
static void movers_pending(void){
    int i;
    mover_pending=0;
    for(i=0;i<mover_count;i++)if(movers[i].since<0){movers[i].since=0;mover_place(&movers[i],movers[i].shift,1);}
}
int AW_MoverShift(unsigned reference,const float *d){
    int i,relink;hd_mover_t *m;
    if((i=mover_find(reference))<0)return 0;
    m=&movers[i];
    VectorAdd(m->shift,d,m->shift);
    if(m->since<0)return 1;   /* loaded, not yet placed: the pending pass puts it at the whole shift */
    m->since+=(float)sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]);
    relink=m->since>=AW_MOVER_RELINK;if(relink)m->since=0;
    mover_place(m,d,relink);
    return 1;
}
int AW_MoverAtStart(unsigned reference){
    int i;hd_mover_t *m;vec3_t back;
    if((i=mover_find(reference))<0)return 0;
    m=&movers[i];
    VectorScale(m->shift,-1,back);m->shift[0]=m->shift[1]=m->shift[2]=0;
    if(m->since>=0 && (back[0] || back[1] || back[2]))mover_place(m,back,1);   /* a pending one is still at its start */
    m->since=0;
    return 1;
}
void AW_MoverReset(void){
    int i;
    for(i=0;i<mover_count;i++)AW_MoverAtStart(movers[i].ref);
}
int AW_HingedDoorProtect(edict_t *e){
    eval_t *v=GetEdictFieldValue(e,"aw_ref");
    return v && v->_float>0 && door_row((unsigned)v->_float)>=0;
}
void AW_HingedDoorSpawn(void){
    int i,j,row,k;edict_t *e;eval_t *v;model_t *m;hd_door_t *d;float corner[2];
    load();
    /* a second spawn of the same map: its edicts again, its placements kept */
    for(i=j=0;i<placed_count;i++){
        if(placed[i].edict){if(placed[i].dir)moving--;continue;}
        placed[j++]=placed[i];
    }
    placed_count=j;
    if(!row_count || !sv.active)return;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free || !e->v.classname || strcmp(pr_strings+e->v.classname,"func_wall") || e->v.solid!=SOLID_BSP)continue;
        v=GetEdictFieldValue(e,"aw_ref");
        if(!v || v->_float<=0 || (row=door_row((unsigned)v->_float))<0)continue;
        k=(int)e->v.modelindex;m=k>0 && k<MAX_MODELS?sv.models[k]:NULL;
        /* a CHIM frame's collision-only marker (no faces) is not the door */
        if(!m || m->type!=mod_brush || !m->nummodelsurfaces)continue;
        for(k=0;k<2;k++)corner[k]=fabs(m->mins[k])>fabs(m->maxs[k])?fabs(m->mins[k]):fabs(m->maxs[k]);
        d=add((unsigned)v->_float,row,e->v.origin,(float)sqrt(corner[0]*corner[0]+corner[1]*corner[1]),e->v.angles[1]);
        if(!d)break;
        d->edict=i;
    }
    /* A CHIM placement door (a frame's or a CHIM room's) is drawn and collided
     * by its placement. The collision-only marker edict a CHIM map keeps for
     * an activated object (tools/chim/frame_map.py keep_activated: the census
     * hall door) would stand shut in its doorway and hide the placement from
     * the aim, so it stops being solid. */
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free || !e->v.classname || strcmp(pr_strings+e->v.classname,"func_wall") || e->v.solid!=SOLID_BSP)continue;
        v=GetEdictFieldValue(e,"aw_ref");
        k=(int)e->v.modelindex;m=k>0 && k<MAX_MODELS?sv.models[k]:NULL;
        if(!v || v->_float<=0 || !m || m->type!=mod_brush || m->nummodelsurfaces)continue;
        for(j=0;j<placed_count;j++)
            if(!placed[j].edict && placed[j].ref==(unsigned)v->_float){e->v.solid=SOLID_NOT;SV_LinkEdict(e,false);break;}
    }
    /* The saved pose: the world change list's open doors (CELL-CHANGES-59), and the story's (the census hall door:
     * aw_story.hall_open, which an older save carries alone). */
    for(i=0;i<placed_count;i++){
        d=&placed[i];
        if(d->dir || d->amount>0 || !saved_open(d->ref))continue;
        d->amount=AW_HINGE_OPEN_DEGREES;pose(d,d->amount);
    }
}
int AW_HingedDoorPlacement(unsigned pid,unsigned reference,const float *origin,float radius,float *yaw){
    int i,row;hd_door_t *d;
    if((row=door_row(reference))<0)return AW_MoverPlacement(pid,reference);   /* WORLD-BUTTONS-62 */
    for(i=0;i<placed_count;i++){
        d=&placed[i];
        if(!d->edict && d->pid==pid){*yaw=d->closed-d->amount;return 1;}
    }
    d=add(reference,row,origin,radius,*yaw);
    if(!d)return 0;
    d->pid=pid;
    /* a door left open (the world change list, or the story's) comes back open in its placement too */
    if(saved_open(reference)){d->amount=AW_HINGE_OPEN_DEGREES;*yaw=d->closed-d->amount;}
    return 1;
}
void AW_HingedDoorRecentre(const float *d){
    int i,k;
    for(i=0;i<placed_count;i++)if(!placed[i].edict)for(k=0;k<2;k++)placed[i].origin[k]-=d[k];
}
/* aw_hinged_door go [N] (test sessions, CELL-CHANGES-59 slice 2): the player 40 units in front of door N of the list
 * (on the side they stand), the eye 8 units above its origin, aimed at its middle; the side of the hinge the door's
 * leaf lies on is tried both ways (and the other face last); when none of them aims at it, the first spot is kept (for
 * a picture). The spot is not checked for room to stand: noclip after it. 1 when the door is under the crosshair. */
static int go_door(int k){
    hd_door_t *d;edict_t *p;float c,s,side,leaf,eye_z;vec3_t mid,delta,angles,forward,right,up;int tries;
    if(k<0 || k>=placed_count || !sv.active || !svs.clients || !(p=svs.clients[0].edict))return 0;
    /* the door's facing through the engine's own AngleVectors (no libm sin/cos: 68040-unimplemented paths) */
    d=&placed[k];angles[0]=angles[2]=0;angles[1]=d->closed-d->amount;AngleVectors(angles,forward,right,up);
    c=forward[0];s=forward[1];
    side=(p->v.origin[0]-d->origin[0])*c+(p->v.origin[1]-d->origin[1])*s>=0?1.f:-1.f;
    eye_z=d->origin[2]+8;
    for(tries=0;tries<5;tries++){
        leaf=d->radius*.5f*((tries&1)?-1.f:1.f);
        mid[0]=d->origin[0]-s*leaf;mid[1]=d->origin[1]+c*leaf;mid[2]=eye_z;
        p->v.origin[0]=mid[0]+((tries&2)?-side:side)*40*c;p->v.origin[1]=mid[1]+((tries&2)?-side:side)*40*s;
        p->v.origin[2]=eye_z-p->v.view_ofs[2];SV_LinkEdict(p,false);
        VectorSubtract(mid,p->v.origin,delta);delta[2]-=p->v.view_ofs[2];
        cl.viewangles[0]=0;cl.viewangles[1]=(float)(atan2(delta[1],delta[0])*180/M_PI);cl.viewangles[2]=0;
        if(tries<4 && aimed()==d)return 1;      /* the fifth: back to the first spot, not aimed */
    }
    return 0;
}
/* the door of a test command: the door number N given as the argument at ARG, else the one under the crosshair */
static hd_door_t *chosen(int arg){
    int k=-1;
    if(Cmd_Argc()>arg && Q_sscanf(Cmd_Argv(arg),"%d",&k)==1)return k>=0 && k<placed_count?&placed[k]:NULL;
    return aimed();
}
/* dbg door: open or close the door under the crosshair, locks ignored;
 * "status" counts, "list" each door of the map. */
static void command(void){
    char *a=Cmd_Argc()>1?Cmd_Argv(1):"";int i,list=!Q_strcasecmp(a,"list");hd_door_t *d;
    load();
    /* dbg doorlocks [on/off]: every door's lock (load and hinged) on or off; no argument prints it */
    if(!Q_strcasecmp(a,"locks")){
        char *w=Cmd_Argc()>2?Cmd_Argv(2):"";
        if(Cmd_Argc()>3 || (*w && Q_strcasecmp(w,"on") && Q_strcasecmp(w,"off") && strcmp(w,"1") && strcmp(w,"0") &&
           Q_strcasecmp(w,"true") && Q_strcasecmp(w,"false"))){
            Con_Printf("Usage: dbg doorlocks [on/off, true/false or 1/0]\n");return;
        }
        if(*w)door_locks=!Q_strcasecmp(w,"on") || !strcmp(w,"1") || !Q_strcasecmp(w,"true");
        else door_locks=!door_locks;   /* DBG-SUPERSPEED-62: bare turns it the other way */
        Con_Printf("Door locks %s (%ld locked load doors and keyed doors in the table; god mode or the key opens them).\n",
                   door_locks?"on":"off: every lock ignored",(long)lock_count);
        return;
    }
    /* CELL-CHANGES-59 slice 2, test sessions (N: the door's number in "list"; without it the door under the crosshair):
     *   go [N]                 the player in front of it (go_door)
     *   use [N]                the player's use of it (its lock holds, as E: a script's Activate, OpenMW's rule)
     *   lock [N [level]]       the console's Lock (no level: the level it had last), kept like a script's
     *   unlock [N]             the console's Unlock, kept the same way */
    if(!Q_strcasecmp(a,"use")){
        if(!(d=chosen(2))){Con_Printf("No such hinged door here (%ld doors).\n",(long)placed_count);return;}
        use_door(d,0);
        Con_Printf("Door %lu %s.\n",(unsigned long)d->ref,d->dir>0?"opening":d->dir<0?"closing":"stays as it is (locked)");
        return;
    }
    if(!Q_strcasecmp(a,"go")){
        int k=0;
        if(Cmd_Argc()>2 && Q_sscanf(Cmd_Argv(2),"%d",&k)!=1)k=-1;
        if(k<0 || k>=placed_count){Con_Printf("aw_hinged_door go: %ld doors here.\n",(long)placed_count);return;}
        Con_Printf("aw_hinged_door go: door %lu %s.\n",(unsigned long)placed[k].ref,
                   go_door(k)?"under the crosshair":"not under the crosshair from its front");
        return;
    }
    if(!Q_strcasecmp(a,"lock") || !Q_strcasecmp(a,"unlock")){
        int lock=!Q_strcasecmp(a,"lock"),level=-1;
        if(Cmd_Argc()>3 && Q_sscanf(Cmd_Argv(3),"%d",&level)!=1)level=-1;
        d=chosen(2);
        if(!d){Con_Printf("No such hinged door here (%ld doors).\n",(long)placed_count);return;}
        if(!aw_object_lock || !aw_object_lock(d->ref,lock,level<0?-1:level>100?100:level)){
            Con_Printf("Locks are not kept in this build.\n");return;}
        Con_Printf("Door %lu %s%s.\n",(unsigned long)d->ref,locked(d)?"locked":"unlocked",
                   lock && !door_locks?" (dbg doorlocks off: every lock ignored)":"");
        return;
    }
    if(list || !Q_strcasecmp(a,"status")){
        int edicts=0;
        for(i=0;i<placed_count;i++)edicts+=placed[i].edict!=0;
        Con_Printf("Hinged doors: %ld in the table, %ld here (%ld room map edicts, %ld CHIM placements), %ld moving%s\n",
            (long)row_count,(long)placed_count,(long)edicts,(long)(placed_count-edicts),(long)moving,
            overflow?", some left out (over 256)":"");
        for(i=0;list && i<placed_count;i++){
            d=&placed[i];
            Con_Printf("  %lu %s %ld/90 deg%s lock %ld%s%s%s at %ld %ld %ld\n",(unsigned long)d->ref,d->edict?"edict":"CHIM",
                (long)d->amount,d->dir>0?" opening":d->dir<0?" closing":"",
                /* the level now: a script's or the console's (the world change list), else the game data's */
                (long)(aw_object_lock_level?aw_object_lock_level(d->ref,original_lock(d->row)):original_lock(d->row)),
                locked(d)?" locked":"",story(d->ref,AW_HINGE_STORY_LOCK)>=0?" (story)":"",
                rows[d->row].flags&AW_HINGE_TRAP?" trap":"",
                (long)d->origin[0],(long)d->origin[1],(long)d->origin[2]);
        }
        return;
    }
    if(!use(1))Con_Printf("No hinged door under the crosshair (within %ld units).\n",(long)HD_REACH);
}
extern int (*aw_hinged_use)(void);
extern int (*aw_hinged_hint)(const char **name,const char **action);
extern void (*aw_hinged_spawn)(void);
extern void (*aw_hinged_tick)(double seconds);
extern void (*aw_hinged_map_begin)(void);
extern int (*aw_hinged_protect)(edict_t *e);
extern int (*aw_hinged_locked_sound)(void);
extern int (*aw_load_door_lock)(unsigned reference,int use);
/* The original LockedDoor sound to the player, not at a door (aw_scene.c: a
 * room door this start cannot open, CHIM-ROOM-16MB-REFUSAL-48). 1 when played. */
int AW_HingedDoorLockedSound(void){
    sfx_t *s;
    load();
    if(locked_sound<0 || !Cvar_VariableValue("aw_door_sounds"))return 0;
    s=S_PrecacheSound(sounds[locked_sound].path);if(!s)return 0;
    S_StartSound(MAX_EDICTS+HD_PLACED,HD_CHANNEL,s,vec3_origin,sounds[locked_sound].volume,0);
    return 1;
}
void AW_HingedDoorInit(void){
    Cmd_AddCommand("aw_hinged_door",command);
    aw_hinged_use=AW_HingedDoorUse;aw_hinged_hint=AW_HingedDoorHint;aw_hinged_spawn=AW_HingedDoorSpawn;
    aw_hinged_tick=AW_HingedDoorTick;aw_hinged_map_begin=AW_HingedDoorMapBegin;aw_hinged_protect=AW_HingedDoorProtect;
    aw_hinged_locked_sound=AW_HingedDoorLockedSound;
    aw_load_door_lock=AW_HingedDoorLoadLock;
}
