/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <string.h>
#include "aw_story.h"

aw_story_t aw_story;

void AW_StoryReset(int new_game)
{
    memset(&aw_story,0,sizeof(aw_story));
    AW_StateReset();
    if(new_game)AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",1);
    aw_story.stage=new_game?AW_STAGE_SHIP:AW_STAGE_DEMO;
}

int AW_StoryTransition(int next)
{
    /* Restart/demo/load use explicit reset/validated restoration. Ordinary
     * gameplay may only advance one stage, never accidentally skip a gate. */
    if(aw_story.stage==AW_STAGE_DEMO || next!=aw_story.stage+1 ||
       next>AW_STAGE_RELEASED)return 0;
    if(next==AW_STAGE_COURTYARD && !AW_Papers())return 0;
    if(next==AW_STAGE_CAPTAIN && !AW_Ring())return 0;
    if(next==AW_STAGE_RELEASED){
        if(!AW_Package() || !AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1))return 0;
    }
    aw_story.stage=next;
    return 1;
}

int AW_StoryRestricted(void)
{
    return aw_story.stage!=AW_STAGE_DEMO && AW_StateGet(&aw_state,AW_GLOBAL,"CharGenState")>=0;
}

int AW_StoryDoor(unsigned reference)
{
    /* Stable placed-reference IDs, never model names shared by other doors. */
    if(!AW_StoryRestricted())return 1;
    if(reference==119513)return 0; /* Registration entrance back to the pier. */
    if(reference==113889)return AW_Ring()>0;
    if(reference==119659)return AW_Package()>0;
    return 1;
}

int AW_StoryFighting(void)
{
    /* CharGenStatsSheet OnPCAdd enables fighting before the hall guard.
     * COURTYARD records successful paper pickup, even while still in Census.
     * Hall permission is retained for older snapshots; doors remain separate. */
    return !AW_StoryRestricted() || aw_story.stage>=AW_STAGE_COURTYARD || aw_story.hall;
}

int AW_StoryHudChannels(void)
{
    int channels=0;
    if(!AW_StoryRestricted())return AW_HUD_ALL;
    if(aw_story.stage>=AW_STAGE_PAPERS)channels|=AW_HUD_STATS;
    if(aw_story.stage>=AW_STAGE_COURTYARD || aw_story.hall ||
       (aw_story.stage>=AW_STAGE_PAPERS && AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:opening:papers_read")))
        channels|=AW_HUD_WEAPON;
    /* The placed-container fact survives dropping/returning the ring. */
    if(aw_story.stage>=AW_STAGE_CAPTAIN || !AW_CourtyardRingAvailable())channels|=AW_HUD_MAGIC;
    return channels;
}

int AW_StoryPapersRead(void)
{
    if(!AW_StoryRestricted())return 1;
    if(aw_story.stage<AW_STAGE_PAPERS)return 0;
    /* Activation unlocks InventoryMenu even if the papers are left behind.
     * Use the existing serialized global table, not a new save-layout field. */
    return AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:opening:papers_read",1);
}

int AW_StoryViewAllowed(void)
{
    /* CharGen disables both view switching and vanity. CharGenClassNPC
     * enables both after the papers instruction (census state 30 -> -1).
     * Use existing saved state: old saves and completed character presets
     * need no new permission bit or save-format migration. */
    return !AW_StoryRestricted() || aw_story.stage>AW_STAGE_PAPERS ||
        (aw_story.stage==AW_STAGE_PAPERS && aw_story.census==-1);
}

void AW_ExpandPlayerName(char *out,unsigned capacity,const char *text)
{
    unsigned n=0;
    const char *p;
    if(!capacity)return;
    while(*text && n+1<capacity){
        if(!strncmp(text,"%PCName",7)){
            /* Name is literal user data, not another substitution template. */
            for(p=aw_story.name;*p && n+1<capacity;p++)out[n++]=*p;
            text+=7;
        }else out[n++]=*text++;
    }
    out[n]=0;
}
