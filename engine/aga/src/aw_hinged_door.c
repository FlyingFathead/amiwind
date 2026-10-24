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
        }else{bad=1;break;}
    }
    if(bad){row_count=base_count=sound_count=0;locked_sound=-1;}
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
/* Locked now: the story's word where it has one, else the table's flag. */
static int locked(const hd_door_t *d){
    int s=story(d->ref,AW_HINGE_STORY_LOCK);
    return s>=0?s!=0:(rows[d->row].flags&AW_HINGE_LOCKED)!=0;
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
static int use(int force){
    hd_door_t *d=aimed();const hd_row_t *r;const hd_base_t *b;
    if(!d)return 0;
    r=&rows[d->row];b=&bases[r->base];
    if(!force && locked(d)){play(d,locked_sound);story(d->ref,AW_HINGE_STORY_REFUSED);return 1;}
    if(!d->dir){d->dir=d->amount>0?-1:1;moving++;}
    else d->dir=(signed char)-d->dir;
    d->held=0;
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
void AW_HingedDoorMapBegin(void){load();placed_count=moving=overflow=0;}
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
    /* The story's saved pose (the census hall door: aw_story.hall_open). */
    for(i=0;i<placed_count;i++){
        d=&placed[i];
        if(d->dir || d->amount>0 || story(d->ref,AW_HINGE_STORY_SPAWN)!=1)continue;
        d->amount=AW_HINGE_OPEN_DEGREES;pose(d,d->amount);
    }
}
int AW_HingedDoorPlacement(unsigned pid,unsigned reference,const float *origin,float radius,float *yaw){
    int i,row;hd_door_t *d;
    if((row=door_row(reference))<0)return 0;
    for(i=0;i<placed_count;i++){
        d=&placed[i];
        if(!d->edict && d->pid==pid){*yaw=d->closed-d->amount;return 1;}
    }
    d=add(reference,row,origin,radius,*yaw);
    if(!d)return 0;
    d->pid=pid;
    return 1;
}
void AW_HingedDoorRecentre(const float *d){
    int i,k;
    for(i=0;i<placed_count;i++)if(!placed[i].edict)for(k=0;k<2;k++)placed[i].origin[k]-=d[k];
}
/* dbg door: open or close the door under the crosshair, locks ignored;
 * "status" counts, "list" each door of the map. */
static void command(void){
    char *a=Cmd_Argc()>1?Cmd_Argv(1):"";int i,list=!Q_strcasecmp(a,"list");hd_door_t *d;
    load();
    if(list || !Q_strcasecmp(a,"status")){
        int edicts=0;
        for(i=0;i<placed_count;i++)edicts+=placed[i].edict!=0;
        Con_Printf("Hinged doors: %ld in the table, %ld here (%ld room map edicts, %ld CHIM placements), %ld moving%s\n",
            (long)row_count,(long)placed_count,(long)edicts,(long)(placed_count-edicts),(long)moving,
            overflow?", some left out (over 256)":"");
        for(i=0;list && i<placed_count;i++){
            d=&placed[i];
            Con_Printf("  %lu %s %ld/90 deg%s lock %ld%s%s%s at %ld %ld %ld\n",(unsigned long)d->ref,d->edict?"edict":"CHIM",
                (long)d->amount,d->dir>0?" opening":d->dir<0?" closing":"",(long)rows[d->row].lock,
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
}
