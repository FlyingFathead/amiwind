/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_character.h"
#include "aw_story.h"
#include <assert.h>
aw_story_t aw_story;
server_t sv;server_static_t svs;keydest_t key_dest=key_game;
int AW_UIMode(void){return 2;}
void IN_AWClearButtons(void){}
void Con_Printf(char *s,...){}
int COM_FOpenFile(char *s,FILE **f){*f=NULL;return -1;}
static byte raw[1024];static int at;
static void text_field(char *s,int width){strcpy((char *)raw+at,s);at+=width;}
int main(void)
{
    int i,n,part_at;byte head[88];edict_t player;client_t client;
    memset(raw,0,sizeof(raw));memcpy(raw,"AWC1",4);raw[4]=raw[6]=raw[8]=1;raw[10]=4;at=72;
    text_field("race",64);text_field("Race",48);memset(raw+at,40,16);at+=16+27+16+2+1;
    text_field("class",64);text_field("Class",48);raw[at++]=0;raw[at++]=5;raw[at++]=0;
    for(i=0;i<10;i++)raw[at++]=i;
    text_field("sign",64);text_field("Sign",48);at+=16+2+1;part_at=at;
    for(i=0;i<4;i++){char name[16];sprintf(name,"part%d",i);text_field(name,64);raw[at++]=0;raw[at++]=i/2;raw[at++]=i%2;raw[at++]=0;}
    n=at;assert(AW_CharacterDecode(raw,n));assert(aw_part_count==4);
    for(i=0;i<n;i++){assert(!AW_CharacterDecode(raw,i));assert(!aw_race_count && !aw_part_count);}
    assert(AW_CharacterDecode(raw,n));raw[part_at+68+4]='0';assert(!AW_CharacterDecode(raw,n));raw[part_at+68+4]='1';
    /* Legacy catalogues remain readable; optional source camera data rejects
     * truncated, invalid and out-of-range values before exposing race tables. */
    assert(AW_CharacterDecode(raw,n));assert(AW_CharacterEyeHeight()==0);
    memcpy(raw+n,"AWE1",4);raw[n+4]=raw[n+5]=0;
    raw[n+6]=30000&255;raw[n+7]=30000>>8;raw[n+8]=28000&255;raw[n+9]=28000>>8;
    assert(AW_CharacterDecode(raw,n+10));assert(fabs(AW_CharacterEyeHeight()-30)<.001);
    aw_character.valid=1;aw_character.female=1;aw_character.head=2;aw_character.hair=3;
    aw_story.stage=AW_STAGE_RELEASED;
    assert(fabs(AW_CharacterEyeHeight()-28)<.001);
    aw_story.stage=AW_STAGE_SHIP;assert(fabs(AW_CharacterEyeHeight()-30)<.001);
    /* Accepting a choice must update the live eye even before the opening
     * changes stage. Cancelling leaves the live camera and physical box alone. */
    memset(&player,0,sizeof(player));memset(&client,0,sizeof(client));
    sv.active=true;svs.maxclients=1;svs.clients=&client;client.edict=&player;
    player.v.mins[2]=-16.625f;player.v.maxs[2]=16.625f;player.v.view_ofs[2]=13.375f;
    assert(AW_CharacterOpen(4));AW_CharacterKey(K_ENTER);AW_CharacterKey('n');
    assert(player.v.view_ofs[2]==13.375f && AW_CharacterActive());
    AW_CharacterKey(K_ENTER);AW_CharacterKey('y');
    assert(!AW_CharacterActive() && AW_CharacterDone()==4);
    assert(fabs(player.v.view_ofs[2]-11.375f)<.001f);
    assert(player.v.mins[2]==-16.625f && player.v.maxs[2]==16.625f);
    aw_story.stage=AW_STAGE_OFFICE;assert(fabs(AW_CharacterEyeHeight()-28)<.001);
    for(i=n+1;i<n+10;i++)assert(!AW_CharacterDecode(raw,i));
    raw[n+4]=1;assert(!AW_CharacterDecode(raw,n+10));raw[n+4]=0;
    raw[n+6]=raw[n+7]=0;assert(!AW_CharacterDecode(raw,n+10));
    memset(raw+72,'x',64);assert(!AW_CharacterDecode(raw,n));
    memset(head,0,sizeof(head));memcpy(head,"AWH1",4);head[4]=1;
    assert(AW_HeadDecode(0,head,sizeof(head)));
    for(i=0;i<(int)sizeof(head);i++)assert(!AW_HeadDecode(0,head,i));
    assert(!AW_HeadDecode(-1,head,sizeof(head)));assert(!AW_HeadDecode(2,head,sizeof(head)));
    head[4]=255;head[5]=255;assert(!AW_HeadDecode(0,head,sizeof(head)));
    AW_HeadClear();return 0;
}
