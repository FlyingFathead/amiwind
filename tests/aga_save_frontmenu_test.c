/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_save.h"
#include "aw_state.h"
#include <assert.h>
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>

char com_gamedir[MAX_OSPATH];
aw_story_t aw_story;
aw_state_t aw_state;
aw_character_t aw_character;
aw_race_t aw_races[16];
aw_class_t aw_classes[32];
aw_birth_t aw_births[16];
aw_part_t aw_parts[384];
int aw_race_count,aw_class_count,aw_birth_count,aw_part_count;
static int catalogue_loads;

int32_t AW_StateGet(const aw_state_t *s,int kind,const char *id){(void)s;(void)kind;(void)id;return -1;}
int AW_CharacterLoad(void)
{
    catalogue_loads++;
    if(!aw_race_count){
        strcpy(aw_races[0].id,"race");strcpy(aw_classes[0].id,"class");strcpy(aw_births[0].id,"birth");
        strcpy(aw_parts[0].id,"head");aw_parts[0].kind=0;
        strcpy(aw_parts[1].id,"hair");aw_parts[1].kind=1;
        aw_race_count=aw_class_count=aw_birth_count=1;aw_part_count=2;
    }
    return 1;
}
int COM_FOpenFile(char *name,FILE **out)
{
    char path[MAX_OSPATH*2];FILE *f;long size;
    if(strcmp(name,"save-content.bin")){*out=NULL;return -1;}
    snprintf(path,sizeof(path),"%s/save-content.bin",com_gamedir);
    f=fopen(path,"rb");if(!f){*out=NULL;return -1;}
    fseek(f,0,SEEK_END);size=ftell(f);fseek(f,0,SEEK_SET);*out=f;return (int)size;
}
static void make_dir(const char *p){if(mkdir(p,0777) && errno!=EEXIST){perror(p);abort();}}
static void write_bytes(const char *p,const void *data,size_t n)
{FILE *f=fopen(p,"wb");assert(f);assert(fwrite(data,1,n,f)==n);assert(!fclose(f));}
int main(int argc,char **argv)
{
    aw_save_t save;unsigned char raw[AW_SAVE_BYTES],content[32];char path[MAX_OSPATH*3],description[96];int n,shown;
    assert(argc==1);assert(getcwd(com_gamedir,sizeof(com_gamedir)));
    make_dir(com_gamedir);snprintf(path,sizeof(path),"%s/saves",com_gamedir);make_dir(path);
    snprintf(path,sizeof(path),"%s/saves/p00000002",com_gamedir);make_dir(path);
    memset(content,0x42,sizeof(content));
    snprintf(path,sizeof(path),"%s/save-content.bin",com_gamedir);write_bytes(path,content,sizeof(content));
    /* Prepare the same valid catalogue-bound AWS4 save before simulating a fresh process. */
    assert(AW_CharacterLoad());catalogue_loads=0;
    memset(&save,0,sizeof(save));save.sequence=1;save.profile=2;memset(save.content,0x42,32);
    strcpy(save.scene,"seyda");strcpy(save.label,"Quicksave");strcpy(save.story.name,"Hors");
    save.story.stage=AW_STAGE_RELEASED;save.story.ship_disabled=1;save.story.captain=-1;
    save.character.valid=1;save.character.level=1;save.character.head=0;save.character.hair=1;
    save.state.harvest.slots=AW_HARVEST_SLOTS;memset(save.state.harvest.catalogue,0x42,32);
    n=AW_SaveEncode(raw,sizeof(raw),&save);assert(n>0 && !memcmp(raw,"AWS4",4));
    snprintf(path,sizeof(path),"%s/saves/p00000002/m00a.aws",com_gamedir);write_bytes(path,raw,n);
    /* Fresh front menu: no catalogue has yet been initialized. */
    aw_race_count=aw_class_count=aw_birth_count=aw_part_count=0;description[0]=0;
    shown=AW_SaveDescription(2,0,description,sizeof(description));
#ifdef EXPECT_BASELINE_FAILURE
    assert(!shown && !description[0] && catalogue_loads==0);
    assert(AW_CharacterLoad());description[0]=0;
    assert(AW_SaveDescription(2,0,description,sizeof(description)));
    assert(strstr(description,"Hors / seyda / L1"));
    puts("baseline reproduced: valid AWS4 hidden before catalogue init; same file visible after init");
#else
    assert(shown && strstr(description,"Hors / seyda / L1"));
    assert(catalogue_loads==1);
    puts("candidate passed: first description initializes catalogue and reads existing AWS4");
#endif
    return 0;
}