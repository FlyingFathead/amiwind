/* SPDX-License-Identifier: GPL-2.0-or-later
 * A pure-CHIM disk: the towns' legacy exterior maps (region maps, the alias
 * maps balmora.bsp and seyda.bsp, intro_docks.bsp, sncourt.bsp) are gone,
 * only maps/<town>-chim.bsp and the region tables remain. Every path that
 * checks a scene exists (arrivals for dbg tp, quick start and doors, saves,
 * the scene picker, the town checks) resolves to the CHIM frame map; saving
 * in CHIM Balmora and loading restores the position. The same paths still
 * work on a legacy disk. No original game data. */
#include <assert.h>
#include <stdarg.h>
#include "aw_save.c"
#include "aw_region.h"
#include "aw_world.h"
#ifndef VectorSet
#define VectorSet(v,x,y,z) ((v)[0]=(x),(v)[1]=(y),(v)[2]=(z))
#endif
server_t sv;server_static_t svs;client_state_t cl;
double realtime;char com_gamedir[MAX_OSPATH];int pr_edict_size;
char *pr_strings;vec3_t vec3_origin;keydest_t key_dest;
static char strings[64]="\0progs/v_nord.mdl\0aw_npc";
static eval_t field_values[5];
static const char *field_names[]={"aw_hand_goal","aw_hand_state","aw_torch","aw_hand_started","aw_attack_latched"};
static edict_t player;static client_t client;
edict_t *EDICT_NUM(int n){assert(n==1);return &player;}
aw_story_t aw_story;
eval_t *GetEdictFieldValue(edict_t *p,char *name){int i;assert(p==&player);for(i=0;i<5;i++)if(!strcmp(name,field_names[i]))return &field_values[i];return NULL;}
char *ED_NewString(char *s){int i;for(i=0;i<60;i++)if(!strcmp(pr_strings+i,s))return pr_strings+i;assert(0);return NULL;}
void ED_Free(edict_t *e){e->free=true;}
void Con_Printf(char *fmt,...){va_list a;va_start(a,fmt);vprintf(fmt,a);va_end(a);}
int AW_BarrierLoad(void){return 1;}void AW_OpeningSpawn(void){}
int AW_NPCFloor(edict_t *p){return 1;}
void SV_LinkEdict(edict_t *p,qboolean b){}int AW_ReaderActive(void){return 0;}
int AW_IntroPromptActive(void){return 0;}
int AW_SectionSelect(const char *name,const float *p){return 0;}
int AW_SectionContains(const char *name,const float *p){return 0;}
void IN_AWClearButtons(void){}
float anglemod(float a){return a;}
static char command[64];
void Cbuf_InsertText(char *text){strncpy(command,text,sizeof(command)-1);}

/* The disk. legacy 1: every town map exists (and no CHIM frame map is asked
 * for); 0: only the CHIM frame maps of Balmora and Seyda Neen. */
static int legacy;
int COM_FOpenFile(char *name,FILE **f){
    const char *table="AWBR1 4 96 540 50 50 30 90 -500 12 20 66\n"
        "bm000 -512 -512 1024 1024 -512 -512 2048 2048\n"
        "bm001 1024 0 2048 1024 0 0 2048 2048\n"
        "bm002 0 1024 1024 2048 0 0 2048 2048\n"
        "bm003 1024 1024 2048 2048 0 0 2048 2048\n";
    int i;
    *f=NULL;
    /* The world directory (aw_world.c): Seyda Neen's and Balmora's handoff
     * frames (origin, core) and one open-world region vf0000 east of them. */
    if(!strcmp(name,"world/regions.awr")){
        static const float slots[2][7]={{0,0,0,-2000,-2000,2000,2000},{10000,0,0,-2000,-2000,2000,2000}};
        static const float region[11]={20000,0,0,-1000,-1000,1000,1000,-1900,-1900,1900,1900};
        unsigned char b[4];int k;
        *f=tmpfile();assert(*f);
        fwrite("AWR2",1,4,*f);b[0]=1;b[1]=b[2]=b[3]=0;fwrite(b,1,4,*f);
        for(i=0;i<2;i++)fwrite(slots[i],4,7,*f);
        fwrite("vf0000\0\0",1,8,*f);fwrite(region,4,11,*f);
        k=(int)ftell(*f);assert(k==64+52);rewind(*f);return k;
    }
    /* The region tables: Balmora's bm###, Seyda Neen's sn###, the Arena's va###. */
    if(!strcmp(name,"balmora-regions.txt") || !strcmp(name,"seyda-regions.txt") || !strcmp(name,"vivec_arena-regions.txt")){
        const char *prefix=name[0]=='s'?"sn":name[0]=='v'?"va":"bm";
        *f=tmpfile();assert(*f);
        for(i=0;table[i];i++)fputc(table[i]=='b' && table[i+1]=='m'?prefix[0]:table[i]=='m' && i && table[i-1]=='b'?prefix[1]:table[i],*f);
        rewind(*f);return (int)strlen(table);
    }
    if(!legacy && !strcmp(name,"maps/prison.bsp"))return -1;   /* the CHIM disk of this test has no ship */
    if(!strncmp(name,"maps/",5) && (legacy || !strcmp(name,"maps/balmora-chim.bsp") || !strcmp(name,"maps/seyda-chim.bsp") ||
       !strcmp(name,"maps/vivec_arena-chim.bsp") ||
       !strcmp(name,"maps/intro_docks-chim.bsp") || !strcmp(name,"maps/sncourt-chim.bsp"))){
        *f=tmpfile();assert(*f);for(i=0;i<200;i++)fputc(0,*f);rewind(*f);return 200;
    }
    return -1;
}
/* chim/chim_world.c TownMap: a town's frame map, when the file exists. */
static const char *town_map(const char *town)
{
    static char path[64];FILE *f=NULL;
    sprintf(path,"maps/%s-chim.bsp",town);
    if(COM_FOpenFile(path,&f)<0 || !f)return NULL;
    fclose(f);return path;
}
extern const char *(*aw_chim_town_map)(const char *);

static void setup(void)
{
    aw_race_count=aw_class_count=aw_birth_count=1;aw_part_count=2;
    strcpy(aw_races[0].id,"test_race");strcpy(aw_classes[0].id,"test_class");
    strcpy(aw_births[0].id,"test_sign");strcpy(aw_parts[0].id,"test_head");
    strcpy(aw_parts[1].id,"test_hair");aw_parts[1].kind=1;
    memset(&world,0,sizeof(world));world.profile=2;
    aw_story.stage=AW_STAGE_RELEASED;aw_story.ship_disabled=1;aw_story.captain=-1;strcpy(aw_story.name,"Synthetic");
    memset(&aw_character,0,sizeof(aw_character));aw_character.level=1;aw_character.hair=1;aw_character.valid=1;
    aw_character.current[0]=aw_character.maximum[0]=50;
    /* The state the section-save test writes (aga_section_save_test.c). */
    memset(&aw_state,0,sizeof(aw_state));
    assert(AW_StateSet(&aw_state,AW_GLOBAL,"chargenstate",-1));
    assert(AW_ItemAdd(&aw_state,"ingredient_test",1));
    aw_state.harvest.slots=4;memset(aw_state.harvest.catalogue,0x36,32);aw_state.harvest.facts[0]=0x40100001U;
    pr_strings=strings;sv.active=1;sv.num_edicts=1;sv.time=10;sv.model_precache[1]="progs/v_nord.mdl";
    svs.maxclients=1;svs.clients=&client;client.edict=&player;
    memset(&player,0,sizeof(player));player.v.health=50;player.v.movetype=MOVETYPE_WALK;
    memset(field_values,0,sizeof(field_values));
    content_ready=1;memset(content_id,7,32);loading=0;key_dest=key_game;
}

/* One disk: every check that a scene exists, then a save and a load. */
static void disk(int on_legacy)
{
    char path[64];float point[3],yaw;
    legacy=on_legacy;setup();
    aw_chim_town_map=on_legacy?NULL:town_map;
    strcpy(sv.name,"balmora");strcpy(sv.modelname,on_legacy?"maps/bm000.bsp":"maps/balmora-chim.bsp");
    /* The town's map: its own on a legacy disk, its frame map on a CHIM one. */
    assert(AW_SceneMapSize("balmora",path,sizeof path)>=124);
    assert(!strcmp(path,on_legacy?"maps/balmora.bsp":"maps/balmora-chim.bsp"));
    assert(AW_SceneMapSize("seyda",path,sizeof path)>=124);
    assert(!strcmp(path,on_legacy?"maps/seyda.bsp":"maps/seyda-chim.bsp"));
    assert((AW_SceneMapSize("bm000",NULL,0)>=0)==on_legacy);
    /* M3 stage A: the Vivec Arena (dbg tp vivec/arena, its doors and saves). */
    assert(AW_SceneMapSize("vivec_arena",path,sizeof path)>=124);
    assert(!strcmp(path,on_legacy?"maps/vivec_arena.bsp":"maps/vivec_arena-chim.bsp"));
    assert(AW_TownArrival("vivec_arena",0,point,&yaw) && AW_RegionSelect("vivec_arena",point,0));
    assert(!strcmp(AW_RegionWorldModel("vivec_arena",0),on_legacy?"maps/va000.bsp":"maps/vivec_arena-chim.bsp"));
    /* Arrivals (dbg tp, quick start, doors into the town) and their world model. */
    assert(AW_TownArrival("balmora",0,point,&yaw));
    assert(AW_RegionSelect("balmora",point,0));
    assert(!strcmp(AW_RegionWorldModel("balmora",0),on_legacy?"maps/bm000.bsp":"maps/balmora-chim.bsp"));
    /* dbg tp X Y [Z] (DEBUG-TP-CHIM-33): original coordinates in a town go to the
     * town, whose map is its CHIM frame map on a CHIM disk; the open world's
     * region maps are not on this CHIM disk, so a point there is unavailable. */
    {
        char target[16],names[256];float world[3],local[3];
        VectorSet(world,(10000+120)*4,(-35)*4,(7)*4);
        assert(AW_WorldMapTarget(world,target,point) && !strcmp(target,"balmora"));
        assert(point[0]==120 && point[1]==-35 && point[2]==0);
        assert(AW_SourceToWorld("balmora",world,local) && local[2]==7);
        VectorSet(world,(0-300)*4,(250)*4,0);
        assert(AW_WorldMapTarget(world,target,point) && !strcmp(target,"seyda"));
        VectorSet(world,(20000+10)*4,0,0);
        assert(AW_WorldMapTarget(world,target,point)==on_legacy && !strcmp(target,"vf0000"));
        /* Walking from the open world into Balmora's core hands over to the town. */
        VectorSet(local,-(20000-10000)+1500,0,0);
        if(on_legacy)assert(AW_WorldDestination("vf0000",local,target,point) && !strcmp(target,"balmora"));
        /* The help and error lines list only the destinations this disk has. */
        assert(AW_TeleportDestinations(names,sizeof names)>=3);
        assert(strstr(names,"seydaneen") && strstr(names,"balmora") && strstr(names,"vivec"));
        assert((strstr(names,"prisonship")!=NULL)==on_legacy);
        assert(on_legacy || !strstr(names,"vivec_foreign"));   /* the legacy stub disk has every map */
        printf("tp %s: %s\n",on_legacy?"legacy":"chim",names);
    }
    /* Save is allowed on the town's map (its scene id is the town's); noclip
     * turns it off by design. */
    assert(scene_id()>=0 && AW_SaveAllowed());
    player.v.movetype=MOVETYPE_NOCLIP;assert(!AW_SaveAllowed());player.v.movetype=MOVETYPE_WALK;
    /* Save, move, load: the saved scene resolves, the player is put back. */
    VectorSet(player.v.origin,123,-45,60);
    assert(AW_SaveWrite(0));
    VectorSet(player.v.origin,0,0,0);command[0]=0;
    assert(AW_SaveRead(world.profile,0) && !strcmp(command,"map balmora\n") && loading);
    AW_SaveSpawn();
    assert(!loading && player.v.origin[0]==123 && player.v.origin[1]==-45 && player.v.origin[2]==60);
    /* Without the CHIM frame maps a CHIM disk has no town at all. */
    if(!on_legacy){
        aw_chim_town_map=NULL;
        assert(AW_SceneMapSize("balmora",NULL,0)<0 && !AW_TownArrival("balmora",0,point,&yaw));
        assert(!AW_SaveRead(world.profile,0));
    }
    printf("disk %s ok\n",on_legacy?"legacy":"chim");
}

int main(int argc,char **argv)
{
    setvbuf(stdout,NULL,_IONBF,0);
    assert(argc==2);strcpy(com_gamedir,argv[1]);
    disk(0);
    disk(1);
    return 0;
}
