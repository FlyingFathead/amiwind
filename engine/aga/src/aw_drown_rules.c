/* SPDX-License-Identifier: GPL-2.0-or-later
 * NPCs drown: the pure rules of aw_drown.h (ACTOR-DROWNING-NOT-CARRIED-67). No engine state: the host test
 * tests/aga_drown_rules_test.c links this file with aw_breath_rules.c. */
#include <stdio.h>
#include <string.h>
#include "aw_breath.h"
#include "aw_drown.h"

int AW_DrownRow(aw_drown_table_t *t,uint32_t reference,int create){
    int i;
    if(!t || !reference)return -1;
    for(i=0;i<t->count;i++)if(t->row[i].reference==reference)return i;
    if(!create)return -1;
    if(t->count>=AW_DROWN_ROWS){t->full++;return -1;}
    t->row[t->count].reference=reference;t->row[t->count].left=-1;t->row[t->count].sound=0;
    return t->count++;
}

void AW_DrownDrop(aw_drown_table_t *t,int index){
    if(!t || index<0 || index>=t->count)return;
    t->row[index]=t->row[t->count-1];
    t->count--;
}

float AW_DrownHeadHeight(float height){
    return height/AW_DROWN_SWIM_HEIGHT_SCALE;
}

int AW_DrownTakes(int fight_state,int drawn){
    return fight_state!=2 && drawn;
}

int AW_DrownStep(aw_drown_table_t *t,int index,int submerged,int breathing,float hold,float suffocation,float dt,
                 float *loss){
    float left;
    if(loss)*loss=0;
    if(!t || index<0 || index>=t->count)return 0;
    left=AW_BreathStep(t->row[index].left,hold,submerged,breathing,dt);
    t->row[index].left=left;
    if(loss)*loss=AW_BreathDamage(left,suffocation,dt);
    return submerged || left<hold;
}

int AW_DrownKnockedOut(aw_drown_table_t *t,int index,int knocked,int feet_under){
    if(!t || index<0 || index>=t->count || knocked!=2 || !feet_under)return 0;
    t->row[index].left=0;
    return 1;
}

int AW_DrownSoundDue(aw_drown_table_t *t,int index,float loss,float dt,float seconds){
    aw_drown_row_t *r;
    if(!t || index<0 || index>=t->count)return 0;
    r=&t->row[index];
    if(dt>0)r->sound-=dt;
    if(r->sound<0)r->sound=0;
    if(!(loss>0) || r->sound>0)return 0;
    r->sound=seconds>0.1f?seconds:0.1f;
    return 1;
}

void AW_DrownFactId(char out[32],uint32_t reference){
    sprintf(out,"amiwind:breath:%lu",(unsigned long)reference);
}

long AW_DrownFactValue(float left){
    int32_t bits;
    memcpy(&bits,&left,sizeof(bits));
    return (long)bits;
}

float AW_DrownFactLeft(long value){
    int32_t bits=(int32_t)value;float left;
    memcpy(&left,&bits,sizeof(left));
    return left;
}
