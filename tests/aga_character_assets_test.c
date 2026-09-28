/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_character.h"
#include <assert.h>
static byte raw[1024];static int at;
static void text_field(char *s,int width){strcpy((char *)raw+at,s);at+=width;}
int main(void)
{
    int i,n,part_at;byte head[88];
    memset(raw,0,sizeof(raw));memcpy(raw,"AWC1",4);raw[4]=raw[6]=raw[8]=1;raw[10]=4;at=72;
    text_field("race",64);text_field("Race",48);memset(raw+at,40,16);at+=16+27+16+2+1;
    text_field("class",64);text_field("Class",48);raw[at++]=0;raw[at++]=5;raw[at++]=0;
    for(i=0;i<10;i++)raw[at++]=i;
    text_field("sign",64);text_field("Sign",48);at+=16+2+1;part_at=at;
    for(i=0;i<4;i++){char name[16];sprintf(name,"part%d",i);text_field(name,64);raw[at++]=0;raw[at++]=i/2;raw[at++]=i%2;raw[at++]=0;}
    n=at;assert(AW_CharacterDecode(raw,n));assert(aw_part_count==4);
    for(i=0;i<n;i++){assert(!AW_CharacterDecode(raw,i));assert(!aw_race_count && !aw_part_count);}
    assert(AW_CharacterDecode(raw,n));raw[part_at+68+4]='0';assert(!AW_CharacterDecode(raw,n));raw[part_at+68+4]='1';
    memset(raw+72,'x',64);assert(!AW_CharacterDecode(raw,n));
    memset(head,0,sizeof(head));memcpy(head,"AWH1",4);head[4]=1;
    assert(AW_HeadDecode(0,head,sizeof(head)));
    for(i=0;i<(int)sizeof(head);i++)assert(!AW_HeadDecode(0,head,i));
    assert(!AW_HeadDecode(-1,head,sizeof(head)));assert(!AW_HeadDecode(2,head,sizeof(head)));
    head[4]=255;head[5]=255;assert(!AW_HeadDecode(0,head,sizeof(head)));
    AW_HeadClear();return 0;
}
