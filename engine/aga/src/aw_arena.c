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
 */
#include "quakedef.h"
#include "aw_combat.h"
#include "aw_character.h"

#define MAP_PIT "vai000"
#define MAP_FLOOR "charplane"
enum {PHASE_NONE,PHASE_SETUP,PHASE_TITLE,PHASE_FIGHT,PHASE_RESULT};
enum {SOURCE_FIGHTER,SOURCE_GALLERY,SOURCE_STANDIN};
#define TITLE_SECONDS 3.0

/* The chosen opponent: about 260 bytes. */
static struct {
    char id[32],name[32],model[64],layout[128];
    int source,pick;            /* pick: position in fighters + gallery order */
    aw_fighter_t sheet;
} foe;
static int phase,map_choice=-1,standin_index,help,replay,setup_called,drawn_once;
static double phase_started;
static unsigned long replay_seed;
static float saved_seed;
static edict_t *opponent;
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
    aw_fighter_t sheet;
    if(!AW_CombatSettingsLoad()){Con_Printf("Combat data missing (combat/settings.txt); rebuild the image.\n");return 0;}
    if(!AW_CombatActorLoad(id,&sheet)){Con_Printf("No combat sheet for %s (combat/actors.txt); rebuild the image or choose another NPC.\n",id);return 0;}
    memset(&foe,0,sizeof(foe));
    strncpy(foe.id,id,31);strncpy(foe.name,name && *name?name:sheet.name,31);
    strncpy(foe.model,model?model:"",63);strncpy(foe.layout,layout?layout:"",127);
    foe.source=source;foe.pick=pick;foe.sheet=sheet;
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

/* ---- the map ---- */
static const char *map_name(void) {
    int c=map_choice;
    if(c<0)c=file_size("maps/" MAP_PIT ".bsp")>=124?0:file_size("maps/" MAP_FLOOR ".bsp")>=124?1:2;
    if(c==0 && file_size("maps/" MAP_PIT ".bsp")<124){Con_Printf("The Arena Pit is not in this build; using the gallery floor.\n");c=1;}
    if(c==1 && file_size("maps/" MAP_FLOOR ".bsp")<124){Con_Printf("No gallery floor in this build; fighting here.\n");c=2;}
    return c==0?MAP_PIT:c==1?MAP_FLOOR:"";        /* "" = the current scene */
}

int AW_ArenaActive(void) {return phase!=PHASE_NONE;}

/* Called while the arena map spawns (before baselines; precaching is legal):
 * spectators leave, the opponent arrives. */
void AW_ArenaEntities(void) {
    int i,standin=0;edict_t *e;model_t *m=NULL;char *model=foe.model;
    opponent=NULL;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free)continue;
        if(!strcmp(pr_strings+e->v.classname,"aw_npc") || !strcmp(pr_strings+e->v.classname,"aw_corpse")){
            if(!standin && e->v.modelindex>0)standin=(int)e->v.modelindex;
            ED_Free(e);
        }
    }
    if(model[0] && file_size(model)>=72)m=Mod_ForName(model,false);
    if(!m && foe.source!=SOURCE_STANDIN && model[0])Con_Printf("Opponent model %s missing; using a stand-in.\n",model);
    if(m){
        for(i=1;i<MAX_MODELS && sv.model_precache[i];i++)if(!strcmp(sv.model_precache[i],model))break;
        if(i==MAX_MODELS){Con_Printf("Arena: model table full.\n");return;}
        if(!sv.model_precache[i]){sv.model_precache[i]=ED_NewString(model);sv.models[i]=m;}
        standin_index=i;
    }else{
        /* A stand-in: a resident's model of this scene, else a fighter's. */
        char id[32],path[64],name[32],layout[128];
        if(!standin && fighter_row(0,id,path,name,layout) && file_size(path)>=72 && (m=Mod_ForName(path,false))){
            for(i=1;i<MAX_MODELS && sv.model_precache[i];i++);
            if(i<MAX_MODELS){sv.model_precache[i]=ED_NewString(path);sv.models[i]=m;standin=i;foe.layout[0]=0;}
        }
        if(!standin){Con_Printf("Arena: no model for a stand-in opponent.\n");return;}
        standin_index=standin;foe.layout[0]=0;
    }
    e=ED_Alloc();
    e->v.classname=ED_NewString("aw_npc")-pr_strings;e->v.netname=ED_NewString(foe.name)-pr_strings;
    e->v.model=sv.model_precache[standin_index]-pr_strings;e->v.modelindex=standin_index;
    e->v.movetype=MOVETYPE_NONE;e->v.solid=SOLID_BBOX;e->v.health=foe.sheet.health;
    {   /* the residents' standing box (world.qc aw_npc_floor), through setsize's own code */
        static vec3_t low={-7.32f,-7.12f,0},high={7.32f,7.12f,33.25f};
        SetMinMaxSize(e,low,high,false);
    }
    {eval_t *v=GetEdictFieldValue(e,"aw_source_id");if(v)v->string=ED_NewString(foe.id)-pr_strings;}
    opponent=e;
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
void AW_ArenaSpawn(edict_t *p) {
    vec3_t you_at,foe_at,back,back_angles,forward,right,up;int placed=0;
    if(!opponent || opponent->free){Con_Printf("Arena: no opponent spawned.\n");return;}
    /* The pit floor (original z -464, x -1142..1170, y -918..920): the two
     * fighters 300 units apart on the long axis, facing each other. */
    if(!strcmp(sv.name,MAP_PIT))
        placed=floor_at(p,0,-150,-60,you_at) && floor_at(opponent,0,150,-60,foe_at);
    else if(!strcmp(sv.name,MAP_FLOOR))
        placed=floor_at(p,0,-150,48,you_at) && floor_at(opponent,0,150,48,foe_at);
    if(!placed){
        /* Here: where the game was captured, the opponent ahead (on the pit
         * or the floor without a clear spot: the map's own spawn point). */
        if(!strcmp(sv.name,MAP_PIT) || !strcmp(sv.name,MAP_FLOOR) || !AW_GalleryArenaBack(back,back_angles)){
            VectorCopy(p->v.origin,back);VectorCopy(p->v.angles,back_angles);
        }
        back_angles[0]=back_angles[2]=0;AngleVectors(back_angles,forward,right,up);
        VectorCopy(back,you_at);
        placed=floor_at(opponent,back[0]+forward[0]*160,back[1]+forward[1]*160,back[2]+24,foe_at) ||
               floor_at(opponent,back[0]+forward[0]*64,back[1]+forward[1]*64,back[2]+24,foe_at);
        if(!placed){VectorCopy(back,foe_at);foe_at[0]+=forward[0]*64;foe_at[1]+=forward[1]*64;foe_at[2]+=p->v.mins[2];}
    }
    VectorCopy(you_at,p->v.origin);VectorCopy(you_at,p->v.oldorigin);VectorCopy(vec3_origin,p->v.velocity);
    VectorCopy(foe_at,opponent->v.origin);VectorCopy(foe_at,opponent->v.oldorigin);
    face(p,foe_at,0);face(opponent,you_at,-90);
    VectorCopy(p->v.angles,p->v.v_angle);VectorCopy(p->v.angles,cl.viewangles);
    p->v.movetype=MOVETYPE_WALK;p->v.fixangle=1;
    opponent->v.flags=(int)opponent->v.flags|FL_ONGROUND;
    SV_LinkEdict(p,false);SV_LinkEdict(opponent,false);
    /* Fresh fighters: full health and fatigue, hands raised. */
    if(aw_character.valid){
        aw_character.current[0]=aw_character.maximum[0];aw_character.current[2]=aw_character.maximum[2];
        p->v.health=aw_character.maximum[0];
    }else p->v.health=100;
    AW_GalleryHandsDrawn(p);
    help=0;result_line[0][0]=0;
    set_phase(aw_arena_setup?PHASE_SETUP:PHASE_TITLE);
}
static void setup_done(void) {if(phase==PHASE_SETUP)set_phase(PHASE_TITLE);}
static void fight(void) {
    if(!opponent || opponent->free){set_phase(PHASE_RESULT);return;}
    saved_seed=Cvar_VariableValue("aw_combat_seed");
    if(replay && replay_seed)Cvar_SetValue("aw_combat_seed",(float)replay_seed);
    AW_CombatEngage(opponent,&foe.sheet,foe.layout[0]?foe.layout:NULL);
    if(replay)Cvar_SetValue("aw_combat_seed",saved_seed);
    replay=0;set_phase(PHASE_FIGHT);
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
void AW_ArenaCommand(int argc,char **argv) {
    char spec[96];int i,n=0;const char *a=argc>1?argv[1]:"";
    if(argc==2 && !Q_strcasecmp((char *)a,"exit")){AW_GalleryArenaLeave();return;}
    if(argc==2 && !Q_strcasecmp((char *)a,"list")){list();return;}
    if(argc==2 && !Q_strcasecmp((char *)a,"help")){help=phase!=PHASE_NONE;
        Con_Printf("dbgmode arenapit [opponent | list | next | prev | here | pit | floor | seed N | rematch | setup | exit]\n");return;}
    if(argc==2 && !Q_strcasecmp((char *)a,"setup")){
        if(aw_arena_setup)Con_Printf("Fighter setup runs before the next title card.\n");
        else Con_Printf("Fighter setup arrives with the quick character screen; fighters use their own sheets.\n");
        return;
    }
    if(argc==3 && !Q_strcasecmp((char *)a,"seed")){
        Cvar_SetValue("aw_combat_seed",Q_atof(argv[2]));
        Con_Printf("Arena seed %s (0: a new seed each fight).\n",argv[2]);return;
    }
    if(argc==2 && (!Q_strcasecmp((char *)a,"here") || !Q_strcasecmp((char *)a,"pit") || !Q_strcasecmp((char *)a,"floor"))){
        map_choice=!Q_strcasecmp((char *)a,"pit")?0:!Q_strcasecmp((char *)a,"floor")?1:2;
        if(phase==PHASE_NONE){a="";argc=1;}else{Con_Printf("Arena map: %s from the next entry.\n",a);return;}
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
    if(n && Q_strcasecmp(spec,"next") && Q_strcasecmp(spec,"prev") && Q_strcasecmp(spec,"previous")){if(!choose(spec))return;}
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
        Con_Printf("dbgmode combattest            empty gallery floor, current hands (dbg combattest gallery)\n");
        Con_Printf("dbgmode torchtest             dark room, torch\n");
        Con_Printf("dbgmode gallery               NPC model gallery\n");
        return;
    }
    if(!Q_strcasecmp(Cmd_Argv(1),"arenapit") || !Q_strcasecmp(Cmd_Argv(1),"arena"))strcpy(line,"aw_arenapit");
    else if(!Q_strcasecmp(Cmd_Argv(1),"combattest"))strcpy(line,"aw_combattest gallery");
    else if(!Q_strcasecmp(Cmd_Argv(1),"torchtest"))strcpy(line,"aw_torchtest");
    else if(!Q_strcasecmp(Cmd_Argv(1),"gallery"))strcpy(line,"aw_charplane");
    else {Con_Printf("Unknown debug mode %s (dbgmode lists them).\n",Cmd_Argv(1));return;}
    for(i=2;i<Cmd_Argc();i++){
        n=strlen(line);
        if(n+strlen(Cmd_Argv(i))+3>=sizeof(line))break;
        line[n]=' ';strcpy(line+n+1,Cmd_Argv(i));
    }
    strcat(line,"\n");Cbuf_InsertText(line);
}
static void testarena(void) {command();}
void AW_ArenaInit(void) {
    Cmd_AddCommand("aw_arenapit",command);
    Cmd_AddCommand("dbgmode",dbgmode);
    Cmd_AddCommand("testarena",testarena);
    aw_combat_result=result;
}
/* aw_gallery.c: the session ended or the map is not ours any more. */
void AW_ArenaEnd(void) {
    if(phase==PHASE_NONE)return;
    AW_CombatClear();phase=PHASE_NONE;opponent=NULL;help=0;
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
    if(y<0 || y+AW_ConsoleCharHeight()>vid.height)return;
    for(;*s && x+w<=vid.width;s++,x+=w)if(x>=0)AW_ConsoleCharacter(x,y,(unsigned char)*s);
}
static void centred(int y,const char *s) {text_at((vid.width-(int)strlen(s)*AW_ConsoleCharWidth())/2,y,s);}
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
        sprintf(text,"%s, level %ld",foe.name,(long)foe.sheet.level);centred(y+2*h,text);
        sprintf(text,"%s%s",foe.sheet.weapon?"armed":"hand to hand",foe.sheet.shield?", shield":"");centred(y+3*h,text);
        if(t>=TITLE_SECONDS-1)centred(y+5*h,"FIGHT!");
        if(t>=TITLE_SECONDS)fight();
    }else if(phase==PHASE_FIGHT){
        const aw_fighter_t *f=opponent?AW_CombatFighter(opponent):NULL;
        sprintf(text,"Vivec Arena: %s",foe.name);text_at(4,4,text);
        if(f && f->knocked)text_at(4,4+h,f->knocked==2?"Knocked out":"Knocked down");
        text_at(4,4+2*h,"F1: help  Ctrl+X: leave");
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
        text_at(8,8+10*h,"Ctrl+X or dbgmode arenapit exit");
        text_at(8,8+11*h,"F1 / Esc: close help");
    }
    scr_copyeverything=1;
}
