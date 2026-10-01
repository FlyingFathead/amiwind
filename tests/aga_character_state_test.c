/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
server_t sv;server_static_t svs;
#include "aw_save.h"
#include "aw_maps.h"
#include <assert.h>
#include <stdint.h>
#include "aw_clock.h"
keydest_t key_dest=key_game;
void IN_AWClearButtons(void){}
void AW_HeadClear(void){}
int AW_HeadLoad(int a,int b){return 1;}
void Con_Printf(char *s,...){}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
int COM_FOpenFile(char *s,FILE **f){*f=NULL;return -1;}
static void legacy_header(byte *raw,int size)
{
    uint32_t crc=0xffffffffU;int i,j;
    memcpy(raw,"AWS1",4);
    for(i=12;i<size;i++){crc^=raw[i];for(j=0;j<8;j++)crc=(crc>>1)^((crc&1)?0xedb88320U:0);}
    crc^=0xffffffffU;
    for(i=0;i<4;i++){raw[4+i]=(size>>(8*i))&255;raw[8+i]=(crc>>(8*i))&255;}
}
static void setup(void)
{
    int i;
    aw_race_count=aw_class_count=aw_birth_count=1;aw_part_count=4;
    strcpy(aw_races[0].id,"test race");strcpy(aw_classes[0].id,"test class");strcpy(aw_births[0].id,"test sign");
    for(i=0;i<16;i++)aw_races[0].attributes[i]=40+(i&1)*10;
    aw_races[0].skills[0]=10;aw_classes[0].attributes[0]=0;aw_classes[0].attributes[1]=5;
    for(i=0;i<10;i++)aw_classes[0].skills[i]=i;
    aw_births[0].modifiers[5]=25;aw_races[0].magicka=5;
    for(i=0;i<4;i++){sprintf(aw_parts[i].id,"part%d",i);aw_parts[i].race=0;aw_parts[i].female=i/2;aw_parts[i].kind=i%2;}
}
int main(void)
{
    aw_character_t c;aw_save_t source,decoded,unchanged;byte raw[AW_SAVE_BYTES];int n,i;char out[64];
    setup();assert(!AW_CharacterHors());
    strcpy(aw_races[0].id,"Nord");strcpy(aw_classes[0].id,"Barbarian");strcpy(aw_births[0].id,"Charioteer");
    assert(AW_CharacterHors());assert(!strcmp(aw_story.name,"Hors") && aw_character.valid && !aw_character.female);
    assert(aw_story.stage==AW_STAGE_RELEASED && !AW_StoryRestricted() && AW_Ring() && AW_Package());
    assert(AW_StateGet(&aw_state,AW_ITEM,"gold_001")==87 && aw_character.maximum[0]==50);
    memset(&c,0,sizeof(c));c.head=0;c.hair=1;
    assert(AW_CharacterRebuild(&c));assert(c.attributes[0]==50 && c.attributes[5]==50);
    assert(c.modifiers[5]==25 && c.maximum[0]==50 && c.maximum[1]==60 && c.maximum[2]==205);
    assert(c.skills[0]==30 && c.skills[1]==35);
    c.female=1;c.head=2;c.hair=3;assert(AW_CharacterRebuild(&c));assert(c.maximum[0]==60);
    c.head=0;assert(!AW_CharacterRebuild(&c));c.head=2;
    aw_character=c;assert(AW_CharacterOpen(1));AW_CharacterMouse(0,0);
    for(i=0;i<5;i++)AW_CharacterKey(K_ENTER);
    assert(AW_CharacterActive() && !AW_CharacterDone());
    AW_CharacterKey('n');assert(AW_CharacterActive() && !AW_CharacterDone());
    AW_CharacterKey(K_ENTER);AW_CharacterKey('y');
    assert(!AW_CharacterActive() && AW_CharacterDone()==1);
    assert(AW_CharacterOpen(4));
    AW_CharacterKey(K_ENTER);assert(AW_CharacterActive() && !AW_CharacterDone());
    AW_CharacterKey(K_ESCAPE);assert(AW_CharacterActive() && !AW_CharacterDone());
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_LEFTARROW);AW_CharacterKey(K_ENTER);
    assert(AW_CharacterActive() && !AW_CharacterDone());
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);
    assert(!AW_CharacterActive() && AW_CharacterDone()==4 && !AW_CharacterDone());
    for(i=1;i<=3;i++){
        int presses;assert(AW_CharacterOpen(i));
        for(presses=0;presses<(i==1?5:1);presses++)AW_CharacterKey(K_ENTER);
        assert(AW_CharacterActive());AW_CharacterKey(K_ENTER);
        assert(!AW_CharacterActive() && AW_CharacterDone()==i);
    }
    /* Birthsign arrows and WASD cycle values; pointer motion cannot consume keys. */
    aw_birth_count=3;aw_births[1]=aw_births[0];aw_births[2]=aw_births[0];
    aw_character.birth=0;assert(AW_CharacterOpen(3));
    AW_CharacterKey(K_RIGHTARROW);AW_CharacterMouse(7,0);
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);assert(aw_character.birth==1);
    assert(AW_CharacterOpen(3));AW_CharacterKey(K_LEFTARROW);
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);assert(aw_character.birth==0);
    assert(AW_CharacterOpen(3));AW_CharacterKey('d');
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);assert(aw_character.birth==1);
    assert(AW_CharacterOpen(3));AW_CharacterKey('a');
    AW_CharacterKey(K_ENTER);AW_CharacterKey(K_ENTER);assert(aw_character.birth==0);
    /* Click the right Sex arrow, then Choose; no keyboard row assumptions. */
    aw_character.female=0;aw_character.head=0;aw_character.hair=1;
    assert(AW_CharacterOpen(1));AW_CharacterMouse(85,22);AW_CharacterKey(K_MOUSE1);
    AW_CharacterMouse(-85,106);AW_CharacterKey(K_MOUSE1);AW_CharacterKey(K_ENTER);
    assert(aw_character.female==1 && !AW_CharacterActive());
    AW_StoryReset(1);assert(AW_StoryRestricted());assert(!AW_StoryTransition(AW_STAGE_OFFICE));
    assert(AW_CourtyardRingAvailable() && AW_CourtyardTakeRing());
    assert(AW_Ring()==1 && !AW_CourtyardTakeRing());
    assert(AW_ItemAdd(&aw_state,"ring_keley",-1));
    assert(!AW_CourtyardRingAvailable() && !AW_CourtyardTakeRing());
    strcpy(aw_story.name,"%PCName %%n");AW_ExpandPlayerName(out,sizeof(out),"Hello %PCName!");assert(!strcmp(out,"Hello %PCName %%n!"));
    AW_ExpandPlayerName(out,3,"%PCName");assert(!strcmp(out,"%P"));
    assert(AW_StateGet(&aw_state,AW_JOURNAL,"A1_1_FindSpymaster")==0);
    assert(AW_CaptainDuties());assert(AW_StateGet(&aw_state,AW_ITEM,"GOLD_001")==87);
    assert(AW_ItemAdd(&aw_state,"bk_a1_1_caiuspackage",-1));assert(!AW_CaptainDuties());
    assert(AW_StateGet(&aw_state,AW_ITEM,"gold_001")==87); /* Item loss is not quest reset. */
    assert(AW_JournalAdd(&aw_state,"A1_1_FindSpymaster",12));
    assert(AW_JournalAdd(&aw_state,"A1_1_FindSpymaster",1));
    assert(AW_StateTest(&aw_state,AW_JOURNAL,"a1_1_findspymaster",AW_GE,12));
    assert(AW_StateSet(&aw_state,AW_JOURNAL,"a1_1_findspymaster",5)); /* Explicit branch/index update. */
    assert(AW_StateTest(&aw_state,AW_JOURNAL,"a1_1_findspymaster",AW_EQ,5));
    assert(!AW_ItemAdd(&aw_state,"gold_001",-88));
    assert(AW_StateSet(&aw_state,AW_ITEM,"overflow",INT32_MAX));assert(!AW_ItemAdd(&aw_state,"overflow",1));
    memset(&source,0,sizeof(source));source.sequence=3;source.profile=4;
    source.character=c;source.story=aw_story;source.story.stage=AW_STAGE_RELEASED;
    source.story.hall=1;source.story.ship_disabled=1;source.story.captain=-1;
    assert(AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1));assert(AW_ClockEnsure() && AW_ClockAdvance(86400000));source.state=aw_state;
    strcpy(source.scene,"seyda");strcpy(source.label,"Manual 1");source.position[0]=12.25;
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>500 && n<2000);
    memset(&decoded,0x5a,sizeof(decoded));unchanged=decoded;
    for(i=0;i<n;i++){assert(!AW_SaveDecode(raw,i,&decoded));assert(!memcmp(&decoded,&unchanged,sizeof(decoded)));}
    assert(AW_SaveDecode(raw,n,&decoded));assert(decoded.state.journal_count==2 && decoded.state.journal[0].stage==1 && decoded.state.journal[1].stage==12);assert(AW_StateGet(&decoded.state,AW_GLOBAL,"amiwind:clock:days")==1);assert(decoded.position[0]==12.25 && decoded.character.maximum[0]==60);
    assert(decoded.story.hall==1 && AW_StateGet(&decoded.state,AW_GLOBAL,"amiwind:ref:172851:ring_taken")==1);
    assert(AW_StateGet(&decoded.state,AW_JOURNAL,"a1_1_findspymaster")==5);
    assert(!AW_StateGet(&decoded.state,AW_ITEM,"bk_a1_1_caiuspackage")); /* Released saves may lack a former quest item. */
    for(i=12;i<n;i++){raw[i]^=1;assert(!AW_SaveDecode(raw,n,&decoded));raw[i]^=1;}
    /* Legacy bytes have indices, no dates; decoding must not invent history. */
    i=n-4-source.state.journal_count*16;legacy_header(raw,i);
    assert(AW_SaveDecode(raw,i,&decoded) && !decoded.state.journal_count);
    assert(AW_StateGet(&decoded.state,AW_JOURNAL,"a1_1_findspymaster")==5);
    strcpy(source.scene,"addamasartus");source.actor_count=1;
    source.actors[0].reference=42;source.actors[0].scene=15;
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>0);
    assert(AW_SaveDecode(raw,n,&decoded));assert(!strcmp(decoded.scene,"addamasartus"));
    assert(decoded.actors[0].scene==15 && decoded.actors[0].reference==42);
    strcpy(source.scene,"balmora");source.actors[0].scene=16;
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>0);
    assert(AW_SaveDecode(raw,n,&decoded));assert(!strcmp(decoded.scene,"balmora"));
    assert(decoded.actors[0].scene==16);
    strcpy(source.scene,"bmastius");source.actors[0].scene=17;
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>0 && AW_SaveDecode(raw,n,&decoded));
    assert(!strcmp(decoded.scene,"bmastius") && decoded.actors[0].scene==17);
    strcpy(source.scene,"tharystomb");source.actor_count=AW_SAVE_ACTORS;
    for(i=0;i<AW_SAVE_ACTORS;i++){source.actors[i]=source.actors[0];source.actors[i].scene=AW_MAP_COUNT-1;source.actors[i].reference=i+1;}
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>0 && AW_SaveDecode(raw,n,&decoded));
    assert(decoded.actor_count==AW_SAVE_ACTORS && decoded.actors[AW_SAVE_ACTORS-1].reference==AW_SAVE_ACTORS);
    for(i=0;i<AW_JOURNAL_ENTRIES;i++){
        source.state.journal[i].quest=0;source.state.journal[i].stage=1000+i;
        source.state.journal[i].days=i;source.state.journal[i].milliseconds=43200000;
    }
    source.state.journal_count=AW_JOURNAL_ENTRIES;
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>0 && n<AW_SAVE_BYTES && AW_SaveDecode(raw,n,&decoded));
    assert(decoded.state.journal_count==AW_JOURNAL_ENTRIES && decoded.state.journal[255].stage==1255);
    source.state.journal[0].quest=AW_STATE_VALUES;assert(!AW_SaveEncode(raw,sizeof(raw),&source));
    source.state.journal[0].quest=0;source.state.journal[1]=source.state.journal[0];
    assert(!AW_SaveEncode(raw,sizeof(raw),&source));source.state.journal_count=0;
    source.actors[0].scene=AW_MapId("vf2525");
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>0 && AW_SaveDecode(raw,n,&decoded));
    assert(decoded.actors[0].scene==AW_MapId("vf2525"));
    source.actors[0].scene=AW_SCENE_COUNT;assert(!AW_SaveEncode(raw,sizeof(raw),&source));source.actor_count=0;
    strcpy(source.scene,"../bad");assert(!AW_SaveEncode(raw,sizeof(raw),&source));strcpy(source.scene,"seyda");
    source.character.head=384;assert(!AW_SaveEncode(raw,sizeof(raw),&source));source.character=c;
    source.character.current[0]=NAN;assert(!AW_SaveEncode(raw,sizeof(raw),&source));
    return 0;
}
