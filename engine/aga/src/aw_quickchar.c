/* SPDX-License-Identifier: GPL-2.0-or-later
 * The quick character screen (aw_quickchar.h): the census office's own menus
 * (aw_character.c: appearance with the head model, class, birthsign, review of
 * attributes and skills) and the ship's name entry, run as one sequence over
 * the current scene. Pages before the last are accepted with Enter; the last
 * asks "Really choose this character?" as the census does. Nothing here builds
 * stats: aw_character.c's builder does, as in the normal flow.
 * Callers: New Game with aw_skip_census (aw_scene.c), dbg quickchar (any
 * scene), and any test or combat set-up through AW_QuickCharOpen.
 * Resident cost: the state below (under 64 bytes) and the name buffer.
 */
#include "quakedef.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_quickchar.h"

static cvar_t skip_census={"aw_skip_census","0"};
static cvar_t voice={"aw_quickchar_voice","1",true};
static int active,pages,page,scripted;
static aw_quickchar_done_t done;
static char name[32];
static const int order[5]={AW_QC_NAME,AW_QC_APPEARANCE,AW_QC_CLASS,AW_QC_BIRTHSIGN,AW_QC_REVIEW};
static const char *words[5]={"name","race","class","birthsign","review"};
/* The original effect "Book Page" (Sound/Fx/item/bookpag1.wav) in the converted
 * sound pool (tools/prepare_media_assets.py sound_output); the game has no
 * stamp sound, so none is made up. Skipped when absent. */
#define PAGE_SOUND "pool/a5db2581e86f75e13.wav"
/* The census officer's greeting and the dock guard's "fit right in" line:
 * the introductory lines the intro stage converts (tools/prepare_intro.py). */
#define GREETING "chargen_class1"
#define CONFIRMED "chargendock2"

int AW_SkipCensus(void){return skip_census.value!=0;}
int AW_QuickCharActive(void){return active;}
int AW_QuickCharScripted(void){return scripted && aw_character.valid;}

static int file_size(const char *path){
    FILE *f=NULL;int n=COM_FOpenFile((char *)path,&f);
    if(f)fclose(f);
    return f?n:-1;
}
static void play(const char *sound){
    sfx_t *sfx;char path[64];
    sprintf(path,"sound/%s",sound);
    if(file_size(path)<=44 || !(sfx=S_PrecacheSound((char *)sound)))return;
    S_StartSound(cl.viewentity,2,sfx,vec3_origin,1,0);
}
/* An introductory line over the screen, with its subtitle, when both files exist. */
static void say(const char *stem){
    FILE *f=NULL;char path[48],text[1024],expanded[1024];int n;sfx_t *sfx;sfxcache_t *sc;double duration=5;
    if(!(pages&AW_QC_VOICE) || !voice.value)return;
    sprintf(path,"sound/intro/%s.wav",stem);
    if(file_size(path)<=44)return;
    sprintf(path,"intro/%s.wav",stem);
    if(!(sfx=S_PrecacheSound(path)))return;
    if((sc=S_LoadSound(sfx))!=NULL && sc->speed>0)duration=(double)sc->length/sc->speed;
    S_StartSound(cl.viewentity,2,sfx,vec3_origin,.9,0);
    sprintf(path,"intro/%s.txt",stem);n=COM_FOpenFile(path,&f);
    if(!f)return;
    if(n>0 && n<(int)sizeof(text) && fread(text,1,n,f)==(size_t)n && !text[n-1]){
        AW_ExpandPlayerName(expanded,sizeof(expanded),text);AW_UIVoiceSubtitle("",expanded,duration);
    }
    fclose(f);
}
static void finish(int accepted){
    aw_quickchar_done_t callback=done;edict_t *p;
    if(!active)return;
    if(AW_CharacterActive())AW_CharacterClose();
    active=page=0;done=NULL;IN_AWClearButtons();
    if(accepted){
        if(sv.active && svs.maxclients==1 && svs.clients && (p=svs.clients[0].edict))p->v.health=aw_character.current[0];
        if((pages&AW_QC_VOICE) && voice.value)play(PAGE_SOUND);
        say(CONFIRMED);
        Con_Printf("Quick character: %s, %s, %s, %s.\n",aw_story.name,aw_races[aw_character.race].name,
            aw_classes[aw_character.clas].name,aw_births[aw_character.birth].name);
    }
    if(callback)callback(accepted);
}
static int last_page(int bit){
    int i,later=0;
    for(i=0;i<5;i++)if(order[i]>bit && (pages&order[i]))later=1;
    return !later;
}
static void open_page(int bit){
    int kind=bit==AW_QC_APPEARANCE?1:bit==AW_QC_CLASS?2:bit==AW_QC_BIRTHSIGN?3:4;
    page=bit;
    if(bit==AW_QC_NAME){IN_AWClearButtons();return;}
    if(!AW_CharacterOpenQuick(kind,last_page(bit))){Con_Printf("Quick character: menu unavailable.\n");finish(0);}
}
static void advance(void){
    int i;
    for(i=0;i<5;i++)if(order[i]>page && (pages&order[i])){open_page(order[i]);return;}
    finish(1);
}
int AW_QuickCharOpen(int wanted,aw_quickchar_done_t on_done){
    if(active || !(wanted&AW_QC_ALL) || (wanted&~(AW_QC_ALL|AW_QC_VOICE)))return 0;
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !svs.clients[0].edict || cls.state!=ca_connected){
        Con_Printf("Quick character: start or load a game first.\n");return 0;
    }
    if(AW_StoryRestricted() || AW_CharacterActive()){Con_Printf("Quick character: not during the story's own registration.\n");return 0;}
    if(!AW_CharacterLoad()){Con_Printf("Quick character: character catalogue unavailable.\n");return 0;}
    if(!aw_character.valid)AW_CharacterReset();
    if(!aw_character.valid){Con_Printf("Quick character: character catalogue unavailable.\n");return 0;}
    strncpy(name,aw_story.name[0]?aw_story.name:"Player",sizeof(name)-1);name[sizeof(name)-1]=0;
    active=1;pages=wanted;page=0;done=on_done;
    say(GREETING);
    advance();
    return active;
}
void AW_QuickCharCancel(void){finish(0);}
int AW_QuickCharPages(int argc,char **argv,int first){
    int i,j,result=0;
    for(i=first;i<argc;i++){
        if(!Q_strcasecmp(argv[i],"all")){result|=AW_QC_ALL;continue;}
        if(!Q_strcasecmp(argv[i],"appearance") || !Q_strcasecmp(argv[i],"head")){result|=AW_QC_APPEARANCE;continue;}
        if(!Q_strcasecmp(argv[i],"birth") || !Q_strcasecmp(argv[i],"attributes") || !Q_strcasecmp(argv[i],"skills")){
            result|=Q_strcasecmp(argv[i],"birth")?AW_QC_REVIEW:AW_QC_BIRTHSIGN;continue;
        }
        for(j=0;j<5;j++)if(!Q_strcasecmp(argv[i],(char *)words[j]))break;
        if(j==5)return 0;
        result|=order[j];
    }
    return result;
}
int AW_QuickCharKey(int key){
    if(!active || page!=AW_QC_NAME || key_dest!=key_game)return 0;
    if(key==K_ESCAPE)return 0; /* Pause menu; the page stays. */
    if(AW_NameEdit(name,sizeof(name),key)){strcpy(aw_story.name,name);advance();}
    return 1;
}
void AW_QuickCharDraw(void){
    int gold,muted;extern int scr_copyeverything;
    if(!active || page!=AW_QC_NAME || key_dest!=key_game)return;
    if(AW_ModalBlackBackground())AW_UIFill(0,0,vid.width,vid.height,AW_UIColor(0,0,0));
    scr_copyeverything=1;
    gold=AW_UIColor(223,199,144);muted=AW_UIColor(120,109,87);
    AW_UIBox(2,2,316,196);
    AW_UITextBox(10,8,300,20,"Choose your name",gold);
    AW_UIBox(10,72,300,28);AW_NameDraw(18,78,name);
    AW_UITextBox(10,133,300,23,"Type a name",muted);
    AW_UITextBox(10,166,300,22,"Enter: next",gold);
}
void AW_QuickCharTick(void){
    if(!active)return;
    if(!sv.active){finish(0);return;}
    if(page==AW_QC_NAME || AW_CharacterActive())return;
    /* The menu closed: accepted (its page) or taken away by a reset. */
    if(AW_CharacterDone())advance();else finish(0);
}
static void on_debug_done(int accepted){
    if(!accepted)Con_Printf("Quick character: cancelled; character unchanged.\n");
}
/* dbg quickchar [pages]: the screen over the current scene (default: all pages). */
static void quickchar_command(void){
    char *argv[8];int i,n=Cmd_Argc(),wanted;
    if(cmd_source!=src_command)return;
    if(n>8){Con_Printf("Usage: dbg quickchar [name race class birthsign review | all]\n");return;}
    for(i=0;i<n;i++)argv[i]=Cmd_Argv(i);
    wanted=n>1?AW_QuickCharPages(n,argv,1):AW_QC_ALL;
    if(!wanted){Con_Printf("Usage: dbg quickchar [name race class birthsign review | all]\n");return;}
    if(key_dest==key_console)Con_ToggleConsole_f();
    if(!AW_QuickCharOpen(wanted|AW_QC_VOICE,on_debug_done) && key_dest==key_game && !sv.active)Cbuf_AddText("aw_main_menu\n");
}
/* aw_quickchar_set FIELD VALUE [N]: a fully specified character without menus, for
 * scripted tests (test.cfg, the command mailbox): race/class/birthsign/sex VALUE first,
 * then attribute NAME N, skill NAME N, level N, name TEXT. Works before a world exists;
 * the player gets the health on the next arrival (or now, in a world). */
static void set_command(void){
    edict_t *p;
    if(Cmd_Argc()==2 && !Q_strcasecmp(Cmd_Argv(1),"clear")){scripted=0;Con_Printf("Scripted character cleared.\n");return;}
    if(Cmd_Argc()<3 || Cmd_Argc()>4){
        Con_Printf("Usage: aw_quickchar_set race|class|birthsign|sex|name VALUE, attribute|skill NAME N, level N\n");return;
    }
    if(!AW_CharacterLoad()){Con_Printf("Character catalogue unavailable.\n");return;}
    if(!aw_character.valid)AW_CharacterReset();
    if(!Q_strcasecmp(Cmd_Argv(1),"name")){
        if(strlen(Cmd_Argv(2))>=sizeof(aw_story.name)){Con_Printf("Name too long.\n");return;}
        strcpy(aw_story.name,Cmd_Argv(2));scripted=1;return;
    }
    if(!AW_CharacterSet(&aw_character,Cmd_Argv(1),Cmd_Argv(2),Cmd_Argc()==4?Cmd_Argv(3):NULL)){
        Con_Printf("Not set: %s %s (unknown field, name or value).\n",Cmd_Argv(1),Cmd_Argv(2));return;
    }
    scripted=1;
    if(sv.active && svs.maxclients==1 && svs.clients && (p=svs.clients[0].edict))p->v.health=aw_character.current[0];
}
/* aw_quickchar_show: the current character as one console line per group (read-back for tests). */
static void show_command(void){
    int i;
    if(!aw_character.valid){Con_Printf("No character.\n");return;}
    Con_Printf("Character: %s / %s / %s / %s / %s / level %ld / health %ld\n",aw_story.name,
        aw_races[aw_character.race].name,aw_character.female?"f":"m",aw_classes[aw_character.clas].name,
        aw_births[aw_character.birth].name,(long)aw_character.level,(long)aw_character.current[0]);
    Con_Printf("Attributes:");
    for(i=0;i<8;i++)Con_Printf(" %ld",(long)(aw_character.attributes[i]+aw_character.modifiers[i]));
    Con_Printf("\nSkills:");
    for(i=0;i<27;i++)Con_Printf(" %ld",(long)aw_character.skills[i]);
    Con_Printf("\n");
}
/* aw_seed N: the C library's random sequence (fire, embers, harvest rolls), for repeatable tests. */
static void seed_command(void){
    if(Cmd_Argc()!=2){Con_Printf("Usage: aw_seed N\n");return;}
    srand((unsigned)Q_atoi(Cmd_Argv(1)));Con_Printf("Random seed %s.\n",Cmd_Argv(1));
}
void AW_QuickCharInit(void){
    Cvar_RegisterVariable(&skip_census);Cvar_RegisterVariable(&voice);
    Cmd_AddCommand("aw_quickchar",quickchar_command);
    Cmd_AddCommand("aw_quickchar_set",set_command);
    Cmd_AddCommand("aw_quickchar_show",show_command);
    Cmd_AddCommand("aw_seed",seed_command);
}
