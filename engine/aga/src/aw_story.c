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
    if(reference==113889)return AW_Ring()>0;
    if(reference==119659)return AW_Package()>0;
    return 1;
}

int AW_StoryFighting(void)
{
    /* CharGenDoorGuardTalker enables fighting when papers unlock the hall.
     * This persistent permission is independent of the exterior enclosure. */
    return !AW_StoryRestricted() || aw_story.hall;
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
