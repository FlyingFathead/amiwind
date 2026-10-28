/* SPDX-License-Identifier: GPL-2.0-or-later
 * Vivec Arena: a small combat minigame inside the debugger (dbgmode arenapit,
 * docs/COMBAT.md). It exercises the shared combat layer (aw_combat.c), which
 * every NPC uses; nothing here is arena-only game logic.
 *
 * Flow: (set up fighter) -> title card -> fight -> result -> rematch / next
 * opponent / pick opponent / exit. The session (capture, map load, return)
 * is the gallery's captured-and-restored debug room (aw_gallery.c), so the
 * game is restored exactly on exit and the save format does not change.
 *
 * Map: the Vivec Arena Pit (maps/vai000.bsp) when the image has it, else the
 * gallery floor, else the current scene ("here"). Spectators are removed.
 * Opponent: a baked Arena fighter (arena/fighters.txt: combat frames), any
 * humanoid NPC of the gallery (one pose) or any NPC record with a stand-in
 * model; stats always from combat/actors.txt (the record's own sheet).
 *
 * The combat playground (docs/COMBAT.md "Combat playground", the MiniWind preset combat-playground) is this
 * minigame's modes: duel (the minigame as it was), anim (one actor plays every combat group of its animation
 * table in turn, labelled), aggro (up to four actors who start a fight on their own by the Fight rule and flee by
 * the Flee rule), group (up to four fighters at once, with the measured cost of their thinks) and sounds (every
 * combat sound in turn and a creature's sound generators, labelled).
 */
#include "quakedef.h"
#include "aw_links.h"
#include "aw_combat.h"
#include "aw_character.h"
#include "aw_mappath.h"
#include "aw_animkit.h"
#include "aw_anim.h"

#define MAP_PIT "vai000"
#define MAP_FLOOR "charplane"
enum {PHASE_NONE,PHASE_SETUP,PHASE_TITLE,PHASE_FIGHT,PHASE_RESULT};
enum {SOURCE_FIGHTER,SOURCE_GALLERY,SOURCE_STANDIN};
#define TITLE_SECONDS 3.0
/* The playground's modes and their cast: at most the combat layer's four slots (aw_combat.c SLOTS). */
enum {MODE_DUEL,MODE_ANIM,MODE_AGGRO,MODE_GROUP,MODE_SOUNDS,MODE_COUNT};
static const char *const mode_names[MODE_COUNT]={"duel","anim","aggro","group","sounds"};
/* sounds: the combat sound table, one entry every SOUND_SECONDS: the swing's sounds (combat/settings.txt, the keys of
 * aw_combat.h AW_SND_*), then a creature's sound generators (combat/sndg.txt, tools/prepare_combat.py
 * sound_generators). The labels name the event and the sound record (OpenMW 0.51, aw_combat.h AW_CombatSwingSounds). */
#define SOUND_SECONDS 1.6
static const char *const sound_labels[AW_SND_COUNT]={
    "Health Damage: a blow takes health","miss: your swing misses","Hand To Hand Hit: a punch tires",
    "Light Armor Hit: light armour struck","Medium Armor Hit: medium armour struck","Heavy Armor Hit: heavy armour struck",
    "Weapon Swish: every melee swing","critical damage: a critical strike","Body Fall Medium: knocked down, dies",
    "Hand To Hand Hit 2: a punch tires"};
#define GENERATORS 8
static const char *const generator_names[GENERATORS]={"left foot","right foot","swim left","swim right","moan","roar",
                                                      "scream","land"};
static char sound_creature[32]="daedroth";
static char generator_path[GENERATORS][32];
static int sound_entry,generator_count;
static double sound_next;
static float saved_sounds=-1;
#define FOES 4

/* A chosen opponent: about 260 bytes. foes[0] is the duel's opponent and every mode's lead. */
static struct foe_s {
    char id[32],name[32],model[64],layout[128];
    int source,pick;            /* pick: position in fighters + gallery order */
    aw_fighter_t sheet;
} foes[FOES];
#define foe foes[0]
static int choosing;            /* the foe take() fills */
static int mode,cast_count=1;
static int phase,map_choice=-1,standin_index,help,replay,setup_called,drawn_once;
static double phase_started;
static unsigned long replay_seed;
static float saved_seed,saved_flee=-1;
static edict_t *opponents[FOES];
#define opponent opponents[0]
/* aggro: each actor's engage timer (OpenMW actor.hpp mEngageCombat: 1 s, deviating by 0.25 s) and last numbers */
static struct {double next;int rating,state;float distance;} aggro[FOES];
static unsigned long jitter_state=0x2545f491UL;
static int anim_model;          /* the first skeletal resident model of the scene (the anim mode's actor) */
static char anim_name[32];
/* The arena player's set sheet (config/arena_player.json -> arena/player.txt);
 * aw_arena_player 0 fights with the game's own character instead. */
static aw_fighter_t player_preset;
static char loadout[24],loadout_used[24];   /* "" = the file's default loadout */
static cvar_t arena_player={"aw_arena_player","1"};
static char result_line[4][64];
/* Planned quick-character module (the quick-start job): set up the player's
 * (and optionally the opponent's) stats before the title card. NULL until it
 * lands; done() continues to the title card. */
int (*aw_arena_setup)(void (*done)(void));

/* aw_gallery.c: the captured session. */
extern int AW_GalleryArenaEnter(const char *map);
extern void AW_GalleryArenaReload(void);
extern void AW_GalleryArenaLeave(void);
extern int AW_GalleryArenaBack(vec3_t origin,vec3_t angles);
extern void AW_GalleryHandsDrawn(edict_t *p);
extern int AW_GalleryFind(const char *search,int index,char *id,char *name,char *model,int *total);
extern void SetMinMaxSize(edict_t *e,float *min,float *max,qboolean rotate);   /* pr_cmds.c, the setsize builtin */

static int file_size(const char *path) {
    FILE *f=NULL;int n=COM_FOpenFile((char *)path,&f);if(f)fclose(f);return n;
}
/* ---- opponents ---- */
/* Row k of arena/fighters.txt (k<0: count only). Returns the count. */
static int fighter_row(int k,char *id,char *model,char *name,char *layout) {
    FILE *f=NULL;char line[320],*field[4],*s;int total=0,i,n=0;
    if(COM_FOpenFile("arena/fighters.txt",&f)<0 || !f)return 0;
    if(!fgets(line,sizeof(line),f) || Q_sscanf(line,"AWAF1 %d",&total)!=1 || total<0 || total>64){fclose(f);return 0;}
    while(k>=0 && fgets(line,sizeof(line),f)){
        line[strcspn(line,"\r\n")]=0;
        for(s=line,i=0;i<4;i++){field[i]=s;s=strchr(s,'\t');if(i<3){if(!s)break;*s++=0;}}
        if(i<4)break;
        if(n++!=k)continue;
        if(strlen(field[0])>=32 || strlen(field[1])>=64 || strlen(field[2])>=32 || strlen(field[3])>=128)break;
        strcpy(id,field[0]);strcpy(model,field[1]);strcpy(name,field[2]);strcpy(layout,field[3]);
        fclose(f);return total;
    }
    fclose(f);return k<0?total:0;
}
static int fighter_count(void) {return fighter_row(-1,NULL,NULL,NULL,NULL);}
static int gallery_count(void) {
    char id[96],name[96],model[64];int total=0;
    return AW_GalleryFind(NULL,0,id,name,model,&total)?total:0;
}
static void normalize(const char *in,char *out,int size) {
    int n=0;unsigned char c;
    while((c=(unsigned char)*in++) && n<size-1){if(c>='A' && c<='Z')c+=32;if((c>='a' && c<='z') || (c>='0' && c<='9'))out[n++]=c;}
    out[n]=0;
}
/* The sheet decides: a choice without combat data is refused. */
static int take(const char *id,const char *name,const char *model,const char *layout,int source,int pick) {
    aw_fighter_t sheet;struct foe_s *o=&foes[choosing];
    if(!AW_CombatSettingsLoad()){Con_Printf("Combat data missing (combat/settings.txt); rebuild the image.\n");return 0;}
    if(!AW_CombatActorLoad(id,&sheet)){Con_Printf("No combat sheet for %s (combat/actors.txt); rebuild the image or choose another NPC.\n",id);return 0;}
    memset(o,0,sizeof(*o));
    Q_strcpy_bounded(o->id,id,sizeof(o->id));Q_strcpy_bounded(o->name,name && *name?name:sheet.name,sizeof(o->name));
    Q_strcpy_bounded(o->model,model?model:"",sizeof(o->model));Q_strcpy_bounded(o->layout,layout?layout:"",sizeof(o->layout));
    o->source=source;o->pick=pick;o->sheet=sheet;
    return 1;
}
static int choose_fighter(int k) {
    char id[32],model[64],name[32],layout[128];
    if(!fighter_row(k,id,model,name,layout))return 0;
    return take(id,name,model,layout,SOURCE_FIGHTER,k);
}
static int choose_gallery(int index,const char *search) {
    char id[96],name[96],model[64];int total=0;
    if(!AW_GalleryFind(search,index,id,name,model,&total))return 0;
    if(strlen(id)>31){Con_Printf("Record ID too long for the arena: %s\n",id);return 0;}
    return take(id,name,model,"",SOURCE_GALLERY,fighter_count()+index);
}
/* Pick position p in fighters + gallery order, wrapping. */
static int choose_pick(int p) {
    int f=fighter_count(),g=gallery_count(),n=f+g,tries;
    if(n<1)return 0;
    for(tries=0;tries<n;tries++,p++){
        p=(p%n+n)%n;
        if(p<f?choose_fighter(p):choose_gallery(p-f,NULL))return 1;
    }
    return 0;
}
/* A record ID, a fighter's name, a gallery number (#N or N) or name. */
static int choose(const char *spec) {
    char id[32],model[64],name[32],layout[128],want[96],a[96],b[96];int k,f=fighter_count();
    normalize(spec,want,sizeof(want));
    if(!want[0])return 0;
    for(k=0;k<f;k++){
        if(!fighter_row(k,id,model,name,layout))break;
        normalize(id,a,sizeof(a));normalize(name,b,sizeof(b));
        if(!strcmp(a,want) || !strcmp(b,want))return take(id,name,model,layout,SOURCE_FIGHTER,k);
    }
    if(spec[0]=='#')spec++;
    if(choose_gallery(0,spec))return 1;
    /* Any NPC record: stats from its sheet, a stand-in model. */
    {
        aw_fighter_t sheet;char lowered[32];int i;
        for(i=0;i<31 && spec[i];i++)lowered[i]=(spec[i]>='A' && spec[i]<='Z')?spec[i]+32:spec[i];
        lowered[i]=0;
        if(AW_CombatActorLoad(lowered,&sheet))return take(sheet.id,sheet.name,"","",SOURCE_STANDIN,-1);
    }
    Con_Printf("No fighter, gallery NPC or NPC record matches \"%s\" (dbgmode arenapit list).\n",spec);
    return 0;
}
static int choose_into(int k,const char *spec) {int was=choosing,ok;choosing=k;ok=choose(spec);choosing=was;return ok;}
static int fighter_into(int k,int row) {int was=choosing,ok;choosing=k;ok=choose_fighter(row);choosing=was;return ok;}
static void list(void) {
    char id[32],model[64],name[32],layout[128];int k,f=fighter_count(),g=gallery_count();
    Con_Printf("Vivec Arena opponents (dbgmode arenapit <name, record ID or gallery #>):\n");
    for(k=0;k<f;k++)if(fighter_row(k,id,model,name,layout))Con_Printf(" %ld. %s (%s) - combat frames\n",(long)(k+1),name,id);
    if(!f)Con_Printf(" (no baked fighters in this build)\n");
    if(g)Con_Printf(" + %ld humanoid NPCs of the gallery (one pose): dbg gallery browse, then their # or ID\n",(long)g);
    else Con_Printf(" (no NPC gallery in this build)\n");
    Con_Printf(" + any NPC record ID (stand-in model). next / prev step through fighters, then the gallery.\n");
    if(foe.id[0])Con_Printf("Current: %s (%s)\n",foe.name,foe.id);
}
static void modes(void) {
    Con_Printf("Combat playground modes (dbgmode combat <mode> ..., the same as dbgmode arenapit <mode> ...):\n");
    Con_Printf(" duel [opponent]          one opponent fights you (the Vivec Arena minigame)\n");
    Con_Printf(" anim [actor]             one actor plays every combat group of its animation table, labelled\n");
    Con_Printf(" aggro [id, id, ...]      up to 4 actors attack on sight by their Fight rating, flee by Flee\n");
    Con_Printf(" group [N] [id, id, ...]  N (1-4) fighters at once, with the cost of their thinks\n");
    Con_Printf(" sounds [creature]        every combat sound in turn, then a creature's sound generators, labelled\n");
    Con_Printf(" loadout NAME             your weapon and shield for the next fight (fists, sword_shield, ...)\n");
    Con_Printf(" creatures                what creature fights do and do not have yet\n");
}
static void creatures(void) {
    Con_Printf("Creature fights: a creature's sheet comes from the actor record (docs/ACTOR_STATE.md): its level,\n"
               "attributes, combat skill, health and its own attacks. Fight one here by its record ID (dbgmode arenapit\n"
               "daedroth: a stand-in model) or by hitting it in the world. Not yet: creatures' carried weapons, their\n"
               "own animation groups in a fight, their sound generators from their animations.\n");
}

/* A creature's sound generators (combat/sndg.txt "AWSG1 N", then sorted rows "id<tab>g0<tab>...<tab>g7", each
 * generator a comma list of sound names under sound/combat/g/ or "-"): one of each type's sounds, picked as OpenMW
 * picks among them (mwclass/creature.cpp getSoundIdFromSndGen: a random one). Returns how many types have a sound,
 * -1 when the creature has no row. */
static int creature_generators(const char *id,char path[GENERATORS][32]) {
    FILE *f=NULL;char line[768],want[32],*field[GENERATORS+1],*s;int i,k,n,found=-1,count=0;
    static unsigned long pick=0x6a09e667UL;
    for(i=0;i<31 && id[i];i++)want[i]=(id[i]>='A' && id[i]<='Z')?id[i]+32:id[i];
    want[i]=0;
    memset(path,0,GENERATORS*32);
    if(COM_FOpenFile("combat/sndg.txt",&f)<0 || !f)return -1;
    if(!fgets(line,sizeof(line),f) || strncmp(line,"AWSG1 ",6)){fclose(f);return -1;}
    while(found<0 && fgets(line,sizeof(line),f)){
        line[strcspn(line,"\r\n")]=0;
        for(s=line,i=0;i<=GENERATORS;i++){field[i]=s;s=strchr(s,'\t');if(i<GENERATORS){if(!s)break;*s++=0;}}
        if(i<=GENERATORS || strcmp(field[0],want))continue;
        found=0;
        for(k=0;k<GENERATORS;k++){
            char *names=field[k+1],*pickname;int choices=1;
            if(!strcmp(names,"-") || !*names)continue;
            for(s=names;*s;s++)if(*s==',')choices++;
            pick^=(pick<<13)&0xffffffffUL;pick^=pick>>17;pick^=(pick<<5)&0xffffffffUL;
            for(n=(int)((pick>>8)%(unsigned long)choices),pickname=names;n>0;n--)pickname=strchr(pickname,',')+1;
            s=strchr(pickname,',');if(s)*s=0;
            if(strlen(pickname)>16 || strstr(pickname,".."))continue;
            sprintf(path[k],"combat/g/%s.wav",pickname);count++;
        }
    }
    fclose(f);
    return found<0?-1:count;
}
/* The sounds mode: entries 0..AW_SND_COUNT-1 the swing's sounds, then the creature's generator types that have one. */
static void sounds_start(void) {
    generator_count=creature_generators(sound_creature,generator_path);
    if(generator_count<0)Con_Printf("Combat playground: no sound generators for %s (combat/sndg.txt; a creature record ID).\n",sound_creature);
    sound_entry=-1;sound_next=realtime;
}
static void sounds_tick(char *label,int size) {
    int total=AW_SND_COUNT+GENERATORS,tries;
    if(realtime>=sound_next){
        for(tries=0;tries<total;tries++){
            sound_entry=(sound_entry+1)%total;
            if(sound_entry<AW_SND_COUNT?AW_CombatSoundPlay(sound_entry):
               generator_path[sound_entry-AW_SND_COUNT][0] && (S_LocalSound(generator_path[sound_entry-AW_SND_COUNT]),1))break;
        }
        if(tries==total)sound_entry=-1;
        sound_next=realtime+SOUND_SECONDS;
    }
    if(sound_entry<0)Q_strcpy_bounded(label,"No combat sounds in this build",size);
    else if(sound_entry<AW_SND_COUNT)Q_strcpy_bounded(label,sound_labels[sound_entry],size);
    else{   /* "creature: type" (the creature's ID is at most 31 characters, the type 10: fits 64) */
        Q_strcpy_bounded(label,sound_creature,size);
        strncat(label,": ",size-strlen(label)-1);strncat(label,generator_names[sound_entry-AW_SND_COUNT],size-strlen(label)-1);
    }
}

/* ---- the map ---- */
static const char *map_name(void) {
    int c=map_choice;
    char pit[AW_MAP_PATH_SIZE],floor[AW_MAP_PATH_SIZE];
    AW_MapPath(MAP_PIT,pit,sizeof(pit));AW_MapPath(MAP_FLOOR,floor,sizeof(floor));
    if(c<0)c=file_size(pit)>=124?0:file_size(floor)>=124?1:2;
    if(c==0 && file_size(pit)<124){Con_Printf("The Arena Pit is not in this build; using the gallery floor.\n");c=1;}
    if(c==1 && file_size(floor)<124){Con_Printf("No gallery floor in this build; fighting here.\n");c=2;}
    return c==0?MAP_PIT:c==1?MAP_FLOOR:"";        /* "" = the current scene */
}

int AW_ArenaActive(void) {return phase!=PHASE_NONE;}

/* One opponent's model: its own, else (the anim mode) a skeletal resident's, else a stand-in. Returns the model
 * index, 0 when there is none. */
static int foe_model(struct foe_s *o,int standin) {
    int i;model_t *m=NULL;char *model=o->model;
    if(model[0] && file_size(model)>=72)m=Mod_ForName(model,false);
    if(!m && o->source!=SOURCE_STANDIN && model[0])Con_Printf("Opponent model %s missing; using a stand-in.\n",model);
    if(m){
        for(i=1;i<MAX_MODELS && sv.model_precache[i];i++)if(!strcmp(sv.model_precache[i],model))break;
        if(i==MAX_MODELS){Con_Printf("Arena: model table full.\n");return 0;}
        if(!sv.model_precache[i]){sv.model_precache[i]=ED_NewString(model);sv.models[i]=m;}
        return i;
    }
    {   /* A stand-in: a resident's model of this scene, else a fighter's. */
        char id[32],path[64],name[32],layout[128];
        if(!standin && fighter_row(0,id,path,name,layout) && file_size(path)>=72 && (m=Mod_ForName(path,false))){
            for(i=1;i<MAX_MODELS && sv.model_precache[i];i++);
            if(i<MAX_MODELS){sv.model_precache[i]=ED_NewString(path);sv.models[i]=m;standin=i;}
        }
        o->layout[0]=0;
        if(!standin)Con_Printf("Arena: no model for a stand-in opponent.\n");
        return standin;
    }
}
/* Called while the arena map spawns (before baselines; precaching is legal):
 * spectators leave, the opponents arrive. */
void AW_ArenaEntities(void) {
    int i,k,standin=0,index;edict_t *e;
    for(k=0;k<FOES;k++)opponents[k]=NULL;
    anim_model=0;anim_name[0]=0;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free)continue;
        if(!strcmp(pr_strings+e->v.classname,"aw_npc") || !strcmp(pr_strings+e->v.classname,"aw_corpse")){
            if(!standin && e->v.modelindex>0)standin=(int)e->v.modelindex;
            if(mode==MODE_ANIM && !anim_model && e->v.modelindex>0 && !strcmp(pr_strings+e->v.classname,"aw_npc") &&
               AW_AnimKitSkeletal((int)e->v.modelindex)){
                anim_model=(int)e->v.modelindex;
                Q_strcpy_bounded(anim_name,e->v.netname?pr_strings+e->v.netname:"resident",sizeof(anim_name));
            }
            ED_Free(e);
        }
    }
    for(k=0;k<cast_count && k<FOES;k++){
        struct foe_s *o=&foes[k];
        if(!o->id[0])continue;
        index=foe_model(o,standin);
        /* the anim mode wants an animation table: a resident's skeletal model when the opponent's is baked */
        if(mode==MODE_ANIM && k==0 && anim_model && (!index || !AW_AnimKitSkeletal(index))){
            index=anim_model;o->layout[0]=0;
            Con_Printf("Combat playground: the animations play on %s's model (a skeletal resident of this scene).\n",anim_name);
        }
        if(!index)return;
        if(k==0)standin_index=index;
        e=ED_Alloc();
        e->v.classname=ED_NewString("aw_npc")-pr_strings;e->v.netname=ED_NewString(o->name)-pr_strings;
        e->v.model=sv.model_precache[index]-pr_strings;e->v.modelindex=index;
        e->v.movetype=MOVETYPE_NONE;e->v.solid=SOLID_BBOX;e->v.health=o->sheet.health;
        {   /* the residents' standing box (world.qc aw_npc_floor), through setsize's own code */
            static vec3_t low={-7.32f,-7.12f,0},high={7.32f,7.12f,33.25f};
            SetMinMaxSize(e,low,high,false);
        }
        {eval_t *v=GetEdictFieldValue(e,"aw_source_id");if(v)v->string=ED_NewString(o->id)-pr_strings;}
        if(mode!=MODE_DUEL)AW_AnimPrep(e);     /* its <model>.anm: the anim mode's groups of a baked model */
        opponents[k]=e;
    }
}
/* Floor under (x, y) from z down: the hull's resting origin, 0 if none. */
static int floor_at(edict_t *e,float x,float y,float z,vec3_t out) {
    vec3_t a,b;trace_t tr;
    a[0]=b[0]=x;a[1]=b[1]=y;a[2]=z;b[2]=z-512;
    tr=SV_Move(a,e->v.mins,e->v.maxs,b,MOVE_NOMONSTERS,e);
    if(tr.startsolid || tr.allsolid || tr.fraction>=1 || tr.plane.normal[2]<AW_WALKABLE_Z)return 0;
    VectorCopy(tr.endpos,out);return 1;
}
static void face(edict_t *e,vec3_t at,float offset) {
    e->v.angles[0]=e->v.angles[2]=0;
    e->v.angles[1]=(float)(Q_atan2(at[1]-e->v.origin[1],at[0]-e->v.origin[0])*180/M_PI)+offset;
}
static void set_phase(int p) {phase=p;phase_started=realtime;drawn_once=0;if(p==PHASE_SETUP)setup_called=0;}
/* Where foe k stands on the pit or the floor (map units), the player at *you: the duel's two spots 300 apart on
 * the long axis; a group side by side; the aggro cast in a row along the pit's length at growing distances
 * (150 to 480 map units, 600 to 1920 original units), so the distance term decides who attacks first. */
static void spot(int k,float *x,float *y,float *you_x,float *you_y) {
    if(mode==MODE_AGGRO){*you_x=-240;*you_y=0;*x=-240+150+110*(float)k;*y=k&1?30:-30;return;}
    *you_x=0;*you_y=-150;*y=150;
    *x=mode==MODE_GROUP?((float)k-(float)(cast_count-1)*.5f)*48:0;
}
void AW_ArenaSpawn(edict_t *p) {
    vec3_t you_at,foe_at[FOES],back,back_angles,forward,right,up;int placed=0,k,n=0;float x,y,yx,yy,z=0;
    if(!opponent || opponent->free){Con_Printf("Arena: no opponent spawned.\n");return;}
    for(k=0;k<FOES;k++)if(opponents[k] && !opponents[k]->free)n=k+1;
    /* The pit floor (original z -464, x -1142..1170, y -918..920): the duel's two
     * fighters 300 units apart on the long axis, facing each other. */
    if(!strcmp(sv.name,MAP_PIT))z=-60;
    else if(!strcmp(sv.name,MAP_FLOOR))z=48;
    if(z!=0){
        spot(0,&x,&y,&yx,&yy);
        placed=floor_at(p,yx,yy,z,you_at);
        for(k=0;k<n && placed;k++){
            if(!opponents[k])continue;
            spot(k,&x,&y,&yx,&yy);
            if(!floor_at(opponents[k],x,y,z,foe_at[k]))placed=0;
        }
    }
    if(!placed){
        /* Here: where the game was captured, the opponents ahead (on the pit
         * or the floor without a clear spot: the map's own spawn point). */
        if(!strcmp(sv.name,MAP_PIT) || !strcmp(sv.name,MAP_FLOOR) || !AW_GalleryArenaBack(back,back_angles)){
            VectorCopy(p->v.origin,back);VectorCopy(p->v.angles,back_angles);
        }
        back_angles[0]=back_angles[2]=0;AngleVectors(back_angles,forward,right,up);
        VectorCopy(back,you_at);
        for(k=0;k<n;k++){
            float ahead=mode==MODE_AGGRO?150+110*(float)k:160,side=mode==MODE_GROUP?((float)k-(float)(n-1)*.5f)*40:0,near=64;
            edict_t *o=opponents[k];
            if(!o)continue;
            if(floor_at(o,back[0]+forward[0]*ahead+right[0]*side,back[1]+forward[1]*ahead+right[1]*side,back[2]+24,foe_at[k]) ||
               floor_at(o,back[0]+forward[0]*near+right[0]*side,back[1]+forward[1]*near+right[1]*side,back[2]+24,foe_at[k]))continue;
            VectorCopy(back,foe_at[k]);foe_at[k][0]+=forward[0]*near+right[0]*side;foe_at[k][1]+=forward[1]*near+right[1]*side;
            foe_at[k][2]+=p->v.mins[2];
        }
    }
    VectorCopy(you_at,p->v.origin);VectorCopy(you_at,p->v.oldorigin);VectorCopy(vec3_origin,p->v.velocity);
    for(k=0;k<n;k++){
        edict_t *o=opponents[k];
        if(!o)continue;
        VectorCopy(foe_at[k],o->v.origin);VectorCopy(foe_at[k],o->v.oldorigin);
        face(o,you_at,-90);
        o->v.flags=(int)o->v.flags|FL_ONGROUND;
        SV_LinkEdict(o,false);
        memset(&aggro[k],0,sizeof(aggro[k]));
    }
    face(p,foe_at[0],0);
    VectorCopy(p->v.angles,p->v.v_angle);VectorCopy(p->v.angles,cl.viewangles);
    p->v.movetype=MOVETYPE_WALK;p->v.fixangle=1;
    SV_LinkEdict(p,false);
    /* The set fighter (the captured character comes back on exit). */
    aw_combat_player_preset=NULL;
    if(arena_player.value && AW_CombatLoadout(loadout,&player_preset,loadout_used)){
        aw_combat_player_preset=&player_preset;
        if(aw_character.valid){aw_character.maximum[0]=player_preset.health_max;aw_character.maximum[2]=player_preset.fatigue_max;}
        Con_Printf("Arena: you fight as %s (level %ld, loadout %s; aw_arena_player 0 = your own character).\n",
            player_preset.name,(long)player_preset.level,loadout_used);
    }
    /* Fresh fighters: full health and fatigue, hands raised. */
    if(aw_character.valid){
        aw_character.current[0]=aw_character.maximum[0];aw_character.current[2]=aw_character.maximum[2];
        p->v.health=aw_character.maximum[0];
    }else p->v.health=aw_combat_player_preset?player_preset.health_max:100;
    AW_GalleryHandsDrawn(p);
    help=0;result_line[0][0]=0;
    set_phase(aw_arena_setup?PHASE_SETUP:PHASE_TITLE);
}
static void setup_done(void) {if(phase==PHASE_SETUP)set_phase(PHASE_TITLE);}
/* The aggro and group modes switch the Flee rule on for their session (AW_CombatRule AW_RULE_FLEE); the rest of the
 * game keeps its setting, which comes back when the mode ends. */
static void flee_rule(int on) {
    if(on && saved_flee<0)saved_flee=(float)AW_CombatRule(AW_RULE_FLEE,1);
    else if(!on && saved_flee>=0){AW_CombatRule(AW_RULE_FLEE,(int)saved_flee);saved_flee=-1;}
}
/* The same for the swing's sounds as OpenMW plays them (AW_RULE_SOUNDS): on in the aggro, group and sounds modes. */
static void sounds_rule(int on) {
    if(on && saved_sounds<0)saved_sounds=(float)AW_CombatRule(AW_RULE_SOUNDS,1);
    else if(!on && saved_sounds>=0){AW_CombatRule(AW_RULE_SOUNDS,(int)saved_sounds);saved_sounds=-1;}
}
/* xorshift32 for the engage timers' deviation (not the fight's generator: a seed still replays a fight) */
static float jitter(void) {
    unsigned long x=jitter_state;
    x^=(x<<13)&0xffffffffUL;x^=x>>17;x^=(x<<5)&0xffffffffUL;jitter_state=x;
    return (float)((x>>8)&0xffff)/65535.0f*.5f-.25f;
}
static void fight(void) {
    int k;
    if(!opponent || opponent->free){set_phase(PHASE_RESULT);return;}
    if(mode==MODE_ANIM){
        if(!AW_AnimKitCombatCycle(opponent))Con_Printf("Combat playground: %s has no animation groups to play.\n",foe.name);
        set_phase(PHASE_FIGHT);return;
    }
    flee_rule(mode==MODE_AGGRO || mode==MODE_GROUP);
    sounds_rule(mode==MODE_AGGRO || mode==MODE_GROUP || mode==MODE_SOUNDS);
    if(mode==MODE_SOUNDS){sounds_start();set_phase(PHASE_FIGHT);return;}
    if(mode==MODE_AGGRO){
        for(k=0;k<FOES;k++){aggro[k].next=realtime+1.0f+jitter();aggro[k].state=0;}
        replay=0;set_phase(PHASE_FIGHT);return;
    }
    saved_seed=Cvar_VariableValue("aw_combat_seed");
    if(replay && replay_seed)Cvar_SetValue("aw_combat_seed",(float)replay_seed);
    for(k=0;k<FOES;k++){
        struct foe_s *o=&foes[k];
        if(opponents[k] && !opponents[k]->free)AW_CombatEngage(opponents[k],&o->sheet,o->layout[0]?o->layout:NULL);
    }
    if(replay)Cvar_SetValue("aw_combat_seed",saved_seed);
    replay=0;set_phase(PHASE_FIGHT);
}
/* aggro: each calm actor's check on its engage timer */
static void aggro_tick(void) {
    int k;
    for(k=0;k<FOES;k++){
        edict_t *e=opponents[k];struct foe_s *o=&foes[k];
        if(!e || e->free || aggro[k].state==1 || realtime<aggro[k].next)continue;
        aggro[k].next=realtime+1.0f+jitter();
        aggro[k].state=AW_CombatAggro(e,&o->sheet,o->layout[0]?o->layout:NULL,50,&aggro[k].rating,&aggro[k].distance);
    }
}
static void result(int won) {
    const aw_combat_stats_t *s=AW_CombatStats();double t=s->ended-s->started;edict_t *p;
    if(phase!=PHASE_FIGHT)return;
    set_phase(PHASE_RESULT);
    sprintf(result_line[0],"%s",won?"VICTORY":"DEFEAT");
    sprintf(result_line[1],"Time %ld.%ld s  seed %lu",(long)t,(long)(t*10)%10,s->seed);
    sprintf(result_line[2],"You: %ld hits, %ld misses",(long)s->player_hits,(long)s->player_misses);
    sprintf(result_line[3],"Dealt %ld/%ld  taken %ld/%ld",(long)s->dealt_health,(long)s->dealt_fatigue,
        (long)s->taken_health,(long)s->taken_fatigue);
    replay_seed=s->seed;
    Con_Printf("Vivec Arena: %s vs %s in %ld.%ld s (seed %lu): you %ld hits %ld misses, %s %ld hits %ld misses; "
        "dealt %ld health %ld fatigue, taken %ld health %ld fatigue\n",won?"won":"lost",foe.name,(long)t,(long)(t*10)%10,s->seed,
        (long)s->player_hits,(long)s->player_misses,foe.name,(long)s->npc_hits,(long)s->npc_misses,
        (long)s->dealt_health,(long)s->dealt_fatigue,(long)s->taken_health,(long)s->taken_fatigue);
    if(!won && (p=svs.clients[0].edict))p->v.movetype=MOVETYPE_NONE;    /* the fallen stay down */
}
static void rematch(int same_seed) {replay=same_seed;AW_GalleryArenaReload();}
static void step(int dir) {if(choose_pick(foe.pick+dir))AW_GalleryArenaReload();}

/* ---- the command (dbgmode arenapit and its aliases) ---- */
static int mode_of(const char *word) {
    int m;
    if(!Q_strcasecmp((char *)word,"animations") || !Q_strcasecmp((char *)word,"animation"))return MODE_ANIM;
    for(m=0;m<MODE_COUNT;m++)if(!Q_strcasecmp((char *)word,(char *)mode_names[m]))return m;
    return -1;
}
/* A mode's default cast (arena/casts.txt, tools/prepare_combat.py casts_file): "MODE<tab>id, id, ..." into out. */
static int default_cast(int m,char *out,int size) {
    FILE *f=NULL;char line[256],*tab;int n=strlen(mode_names[m]);
    out[0]=0;
    if(COM_FOpenFile("arena/casts.txt",&f)<0 || !f)return 0;
    if(!fgets(line,sizeof(line),f) || strncmp(line,"AWAC1",5)){fclose(f);return 0;}
    while(fgets(line,sizeof(line),f)){
        line[strcspn(line,"\r\n")]=0;tab=strchr(line,'\t');
        if(!tab || tab-line!=n || strncmp(line,mode_names[m],n))continue;
        Q_strcpy_bounded(out,tab+1,size);break;
    }
    fclose(f);return out[0]!=0;
}
/* "<mode> [N] [spec, spec, ...]": the cast of a mode; 0 when nobody could be chosen. */
static int choose_cast(int m,int argc,char **argv) {
    char text[200],*s,*next;int i,n=0,want=FOES,k=0;
    if(argc>2 && m==MODE_GROUP && argv[2][0]>='1' && argv[2][0]<='9' && !argv[2][1]){want=argv[2][0]-'0';if(want>FOES)want=FOES;i=3;}
    else i=2;
    for(text[0]=0;i<argc;i++){
        if(n+(int)strlen(argv[i])+2>(int)sizeof(text)){Con_Printf("Cast too long.\n");return 0;}
        if(n)text[n++]=' ';
        strcpy(text+n,argv[i]);n+=strlen(argv[i]);text[n]=0;
    }
    if(m==MODE_SOUNDS){             /* the argument names the creature whose generators play; the duel's foe stands by */
        if(text[0]){char *c;Q_strcpy_bounded(sound_creature,text,sizeof(sound_creature));
            for(c=sound_creature;*c;c++)if(*c>='A' && *c<='Z')*c+=32;}     /* record IDs are matched lower case */
        return foe.id[0] || choose_pick(0);
    }
    if(m==MODE_DUEL || m==MODE_ANIM){
        if(text[0])return choose_into(0,text);
        return foe.id[0] || choose_pick(0);
    }
    /* a comma list of opponents, else the mode's default cast, else the baked fighters */
    if(!text[0] && default_cast(m,text,sizeof(text)))Con_Printf("Combat playground: the default %s cast: %s\n",mode_names[m],text);
    for(s=text;*s && k<want;s=next){
        next=strchr(s,',');if(next)*next++=0;else next=s+strlen(s);
        while(*s==' ')s++;
        if(*s && choose_into(k,s))k++;
    }
    if(!text[0])for(i=0;i<fighter_count() && k<want;i++)if(fighter_into(k,i))k++;
    if(!k)Con_Printf("No opponent for %s mode (give record IDs separated by commas).\n",mode_names[m]);
    cast_count=k?k:1;
    return k>0;
}
void AW_ArenaCommand(int argc,char **argv) {
    char spec[96];int i,n=0,m;const char *a=argc>1?argv[1]:"";
    if(argc==2 && !Q_strcasecmp((char *)a,"exit")){AW_GalleryArenaLeave();return;}
    if(argc==2 && !Q_strcasecmp((char *)a,"list")){list();return;}
    if(argc==2 && !Q_strcasecmp((char *)a,"modes")){modes();return;}
    if(argc>=2 && (!Q_strcasecmp((char *)a,"creature") || !Q_strcasecmp((char *)a,"creatures"))){creatures();return;}
    if(argc==2 && !Q_strcasecmp((char *)a,"help")){help=phase!=PHASE_NONE;
        Con_Printf("dbgmode arenapit [opponent | list | next | prev | here | pit | floor | seed N | loadout NAME | rematch | setup | exit]\n");
        modes();return;}
    if(argc==2 && !Q_strcasecmp((char *)a,"setup")){
        if(aw_arena_setup)Con_Printf("Fighter setup runs before the next title card.\n");
        else Con_Printf("Fighter setup arrives with the quick character screen; fighters use their own sheets.\n");
        return;
    }
    if(argc==3 && !Q_strcasecmp((char *)a,"loadout")){
        aw_fighter_t probe;char used[24];
        if(!AW_CombatLoadout(argv[2],&probe,used)){Con_Printf("No loadout %s in arena/player.txt (config/arena_player.json).\n",argv[2]);return;}
        strcpy(loadout,used);Con_Printf("Arena loadout: %s%s.\n",used,phase!=PHASE_NONE?" (rematch to use it)":"");return;
    }
    if(argc==3 && !Q_strcasecmp((char *)a,"seed")){
        Cvar_SetValue("aw_combat_seed",Q_atof(argv[2]));
        Con_Printf("Arena seed %s (0: a new seed each fight).\n",argv[2]);return;
    }
    if(argc==2 && (!Q_strcasecmp((char *)a,"here") || !Q_strcasecmp((char *)a,"pit") || !Q_strcasecmp((char *)a,"floor"))){
        map_choice=!Q_strcasecmp((char *)a,"pit")?0:!Q_strcasecmp((char *)a,"floor")?1:2;
        if(phase==PHASE_NONE){a="";argc=1;}else{Con_Printf("Arena map: %s from the next entry.\n",a);return;}
    }
    if(argc>=2 && (m=mode_of(a))>=0){
        int was=mode,count=cast_count;
        if(phase!=PHASE_NONE && mode==MODE_ANIM)AW_AnimKitStop();
        mode=m;cast_count=1;
        if(!choose_cast(m,argc,argv)){mode=was;cast_count=count;return;}
        if(m!=MODE_AGGRO && m!=MODE_GROUP)cast_count=1;
        if(m!=MODE_AGGRO && m!=MODE_GROUP)flee_rule(0);
        if(m!=MODE_AGGRO && m!=MODE_GROUP && m!=MODE_SOUNDS)sounds_rule(0);
        Con_Printf("Combat playground: %s mode, %ld actor%s (dbgmode combat modes).\n",mode_names[m],(long)cast_count,cast_count==1?"":"s");
        if(phase!=PHASE_NONE){AW_GalleryArenaReload();return;}
        AW_GalleryArenaEnter(map_name());return;
    }
    if(phase!=PHASE_NONE){
        if(argc==2 && !Q_strcasecmp((char *)a,"rematch")){rematch(0);return;}
        if(argc==2 && !Q_strcasecmp((char *)a,"next")){step(1);return;}
        if(argc==2 && (!Q_strcasecmp((char *)a,"prev") || !Q_strcasecmp((char *)a,"previous"))){step(-1);return;}
    }
    for(i=1;i<argc;i++){
        if(n+(int)strlen(argv[i])+2>(int)sizeof(spec)){Con_Printf("Opponent name too long.\n");return;}
        if(n)spec[n++]=' ';
        strcpy(spec+n,argv[i]);n+=strlen(argv[i]);
    }
    spec[n]=0;
    if(n && Q_strcasecmp(spec,"next") && Q_strcasecmp(spec,"prev") && Q_strcasecmp(spec,"previous")){
        if(!choose(spec))return;
        if(mode!=MODE_DUEL){if(mode==MODE_ANIM && phase!=PHASE_NONE)AW_AnimKitStop();flee_rule(0);sounds_rule(0);}
        mode=MODE_DUEL;cast_count=1;      /* an opponent by name: the duel */
    }
    else if(!foe.id[0] || n){
        int dir=!n?0:!Q_strcasecmp(spec,"next")?1:-1;
        if(!choose_pick(foe.id[0]?foe.pick+dir:dir>0?0:dir)){Con_Printf("No opponent available (no fighters, gallery or combat data in this build).\n");return;}
    }
    if(phase!=PHASE_NONE){AW_GalleryArenaReload();return;}
    if(!AW_GalleryArenaEnter(map_name()))return;
}
static void command(void) {
    char *argv[16];int argc=Cmd_Argc(),i;
    if(argc>16)argc=16;
    for(i=0;i<argc;i++)argv[i]=Cmd_Argv(i);
    AW_ArenaCommand(argc,argv);
}
/* dbgmode <mode> [args]: the debug test modes by name. */
static void dbgmode(void) {
    char line[256];int i,n;
    if(Cmd_Argc()<2){
        Con_Printf("dbgmode arenapit [opponent]   Vivec Arena combat minigame (also dbg arenapit/battlearena/arenatest/arena/combattest, testarena)\n");
        Con_Printf("dbgmode combat <mode> [...]   combat playground: duel, anim, aggro, group, sounds (dbgmode combat modes)\n");
        Con_Printf("dbgmode combattest            empty gallery floor, current hands (dbg combattest gallery)\n");
        Con_Printf("dbgmode torchtest             dark room, torch\n");
        Con_Printf("dbgmode gallery               NPC model gallery\n");
        return;
    }
    if(!Q_strcasecmp(Cmd_Argv(1),"arenapit") || !Q_strcasecmp(Cmd_Argv(1),"arena") || !Q_strcasecmp(Cmd_Argv(1),"combat") ||
       !Q_strcasecmp(Cmd_Argv(1),"playground"))strcpy(line,"aw_arenapit");
    else if(!Q_strcasecmp(Cmd_Argv(1),"combattest"))strcpy(line,"aw_combattest gallery");
    else if(!Q_strcasecmp(Cmd_Argv(1),"torchtest"))strcpy(line,"aw_torchtest");
    else if(!Q_strcasecmp(Cmd_Argv(1),"gallery"))strcpy(line,"aw_charplane");
    else {Con_Printf("Unknown debug mode %s (dbgmode lists them).\n",Cmd_Argv(1));return;}
    if(Cmd_Argc()==2 && (!Q_strcasecmp(Cmd_Argv(1),"combat") || !Q_strcasecmp(Cmd_Argv(1),"playground")))strcat(line," modes");
    for(i=2;i<Cmd_Argc();i++){
        n=strlen(line);
        if(n+strlen(Cmd_Argv(i))+3>=sizeof(line))break;
        line[n]=' ';strcpy(line+n+1,Cmd_Argv(i));
    }
    strcat(line,"\n");Cbuf_InsertText(line);
}
static void testarena(void) {command();}
void AW_ArenaInit(void) {
    Cvar_RegisterVariable(&arena_player);
    Cmd_AddCommand("aw_arenapit",command);
    Cmd_AddCommand("dbgmode",dbgmode);
    Cmd_AddCommand("testarena",testarena);
    aw_combat_result=result;
}
/* aw_gallery.c: the session ended or the map is not ours any more. */
void AW_ArenaEnd(void) {
    int k;
    if(phase==PHASE_NONE)return;
    if(mode==MODE_ANIM)AW_AnimKitStop();
    flee_rule(0);sounds_rule(0);
    AW_CombatClear();phase=PHASE_NONE;help=0;aw_combat_player_preset=NULL;
    for(k=0;k<FOES;k++)opponents[k]=NULL;
}

/* ---- keys and drawing ---- */
int AW_ArenaKey(int key,int down) {
    if(phase==PHASE_NONE || key_dest!=key_game)return 0;
    if(key==K_F1){if(down)help=!help;return 1;}
    if(help){if(down && key==K_ESCAPE)help=0;return 1;}
    if(phase!=PHASE_RESULT)return 0;            /* the fight: normal movement and hands */
    if(!down)return 1;
    if(key>='A' && key<='Z')key+='a'-'A';
    if(key==K_ENTER || key=='r'){rematch(0);return 1;}
    if(key=='s'){rematch(1);return 1;}
    if(key=='n'){step(1);return 1;}
    if(key=='b'){step(-1);return 1;}
    if(key=='p'){list();Con_ToggleConsole_f();return 1;}
    if(key==K_ESCAPE){AW_GalleryArenaLeave();return 1;}
    return 1;
}
static void text_at(int x,int y,const char *s) {
    int w=AW_ConsoleCharWidth();
    if(y<0 || y+AW_ConsoleCharHeight()>(int)vid.height)return;
    for(;*s && x+w<=(int)vid.width;s++,x+=w)if(x>=0)AW_ConsoleCharacter(x,y,(unsigned char)*s);
}
static void centred(int y,const char *s) {text_at((vid.width-(int)strlen(s)*AW_ConsoleCharWidth())/2,y,s);}
/* One line per actor of the aggro and group modes: its state and, in aggro, the Fight rule's numbers. */
static void cast_lines(int y) {
    int k,h=AW_ConsoleCharHeight();char text[96];
    for(k=0;k<FOES;k++){
        edict_t *e=opponents[k];const aw_fighter_t *f;const char *state;
        if(!e || e->free)continue;
        f=AW_CombatFighter(e);
        state=!f?"calm":f->dead?"dead":AW_CombatActorFleeing(e)?"FLEEING":f->knocked?"down":"HOSTILE";
        if(mode==MODE_AGGRO){
            if(aggro[k].state<0)sprintf(text,"%.14s F%ld: no rule (rebuild)",foes[k].name,(long)foes[k].sheet.fight);
            else sprintf(text,"%.14s F%ld at %ld: %ld %s",foes[k].name,(long)foes[k].sheet.fight,(long)aggro[k].distance,
                         (long)aggro[k].rating,state);
        }else sprintf(text,"%.14s %ld/%ld %s",foes[k].name,(long)(f?f->health:foes[k].sheet.health),
                      (long)foes[k].sheet.health_max,state);
        text_at(4,y,text);y+=h;
    }
    if(mode==MODE_GROUP){
        float per,mean,longest;int fighting;
        AW_CombatCost(&per,&mean,&longest,&fighting);
        /* 40 characters fit a 320 pixel screen: thinks a second, the mean and the longest think */
        sprintf(text,"%ld fighting %ld/s %ld.%02ld ms max %ld.%02ld",(long)fighting,(long)per,
                (long)mean,(long)(mean*100)%100,(long)longest,(long)(longest*100)%100);
        text_at(4,y,text);
    }
}
void AW_ArenaDraw(void) {
    char text[96];int h=AW_ConsoleCharHeight(),y;double t=realtime-phase_started;
    extern int scr_copyeverything;
    if(phase==PHASE_NONE)return;
    /* The title card's clock starts at its first drawn frame, not while the
     * map still loads (a slow disk would otherwise skip the card). */
    if(cls.signon!=SIGNONS || AW_LoadingScreen())drawn_once=0;      /* still loading: the clock waits */
    if(!drawn_once){drawn_once=cls.signon==SIGNONS && !AW_LoadingScreen();phase_started=realtime;t=0;}
    if(phase==PHASE_SETUP){
        centred(vid.height/3,"VIVEC ARENA");centred(vid.height/3+2*h,"Set up your fighter");
        if(!aw_arena_setup)setup_done();
        else if(!setup_called){setup_called=1;aw_arena_setup(setup_done);}
    }else if(phase==PHASE_TITLE){
        y=vid.height/3;
        centred(y,"VIVEC ARENA");
        if(mode==MODE_DUEL){
            sprintf(text,"%s, level %ld",foe.name,(long)foe.sheet.level);centred(y+2*h,text);
            sprintf(text,"%s%s",foe.sheet.weapon?"armed":"hand to hand",foe.sheet.shield?", shield":"");centred(y+3*h,text);
            if(t>=TITLE_SECONDS-1)centred(y+5*h,"FIGHT!");
        }else{
            sprintf(text,"Combat playground: %s",mode_names[mode]);centred(y+2*h,text);
            if(cast_count>1)sprintf(text,"%s and %ld more",foe.name,(long)(cast_count-1));
            else sprintf(text,"%s",foe.name);
            centred(y+3*h,text);
            if(t>=TITLE_SECONDS-1)centred(y+5*h,mode==MODE_ANIM?"WATCH":mode==MODE_SOUNDS?"LISTEN":mode==MODE_AGGRO?"COME CLOSER":"FIGHT!");
        }
        if(t>=TITLE_SECONDS)fight();
    }else if(phase==PHASE_FIGHT){
        const aw_fighter_t *f=opponent?AW_CombatFighter(opponent):NULL;
        if(mode==MODE_AGGRO)aggro_tick();
        if(mode==MODE_DUEL){
            sprintf(text,"Vivec Arena: %s",foe.name);text_at(4,4,text);
            if(f && f->knocked)text_at(4,4+h,f->knocked==2?"Knocked out":"Knocked down");
            text_at(4,4+2*h,"F1: help  Ctrl+X: leave");
        }else if(mode==MODE_ANIM){
            char label[64];
            sprintf(text,"Animations: %s",anim_model && standin_index==anim_model?anim_name:foe.name);text_at(4,4,text);
            if(AW_AnimKitLabel(label,sizeof(label))){
                int w=AW_ConsoleCharWidth()*((int)strlen(label)+2);
                y=vid.height-4*h;AW_UIBox((vid.width-w)/2,y-4,w,h+8);centred(y,label);
            }
        }else if(mode==MODE_SOUNDS){
            char label[64];int w;
            text_at(4,4,"Combat playground: sounds");
            sounds_tick(label,sizeof(label));
            w=AW_ConsoleCharWidth()*((int)strlen(label)+2);
            y=vid.height-4*h;AW_UIBox((vid.width-w)/2,y-4,w,h+8);centred(y,label);
        }else{
            sprintf(text,"Combat playground: %s",mode_names[mode]);text_at(4,4,text);
            cast_lines(4+2*h);
        }
    }else{
        int w=AW_ConsoleCharWidth()*34,x=(vid.width-w)/2;
        y=vid.height/4;
        AW_UIBox(x-6,y-6,w+12,9*h+12);
        centred(y,result_line[0]);
        sprintf(text,"%s, level %ld",foe.name,(long)foe.sheet.level);centred(y+h+2,text);
        centred(y+3*h,result_line[1]);centred(y+4*h,result_line[2]);centred(y+5*h,result_line[3]);
        centred(y+7*h,"Enter: rematch  S: same seed");
        centred(y+8*h,"N/B: next/prev  P: pick  Esc: leave");
    }
    if(help){
        AW_UIBox(2,2,vid.width-4,vid.height-4);
        text_at(8,8,"Vivec Arena - debug combat minigame");
        text_at(8,8+2*h,"Attack: punch (F raises hands)");
        text_at(8,8+3*h,"WASD + mouse: move; keep in reach");
        text_at(8,8+5*h,"dbgmode arenapit list / next / prev");
        text_at(8,8+6*h,"dbgmode arenapit <name, ID or #>");
        text_at(8,8+7*h,"dbgmode arenapit seed N (replay)");
        text_at(8,8+8*h,"dbg combat readout on/off: per swing");
        text_at(8,8+9*h,"dbgmode combat duel/anim/aggro/group");
        text_at(8,8+10*h,"Ctrl+X or dbgmode arenapit exit");
        text_at(8,8+11*h,"F1 / Esc: close help");
    }
    scr_copyeverything=1;
}
