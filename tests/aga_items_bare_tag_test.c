/* Host fixture (tests/test_creature_held_tags.py, CREATURE-COMBAT-WEAPON-54): the engine reads an armed creature's
 * item tag, which names no item: only the table frames, the weapon and shield bones and the model's scale. The items
 * themselves are the actor's own record's (ACTOR-HELD-ITEMS-NOT-LIVE-INVENTORY-69). The text is the one the builder
 * writes (tools/creature_held_tags.py tag_text), handed in by the test. */
#define AW_ITEMS_HOST_TEST
#include "aw_items.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

float Q_SinRad(float r) {(void)r;return 0;}
float Q_CosRad(float r) {(void)r;return 1;}
int AW_ItemsTagFrames(const char *text,int numframes);

int main(int argc,char **argv) {
    char text[512],paths[AW_ITEMS_KINDS][AW_ITEMS_PATH],light[AW_ITEMS_PATH];
    int bones[AW_ITEMS_KINDS],lit=1,frames,want_frames,want_weapon,want_shield;float scale[3],flame[3];
    FILE *f;size_t n;
    assert(argc==5);
    f=fopen(argv[1],"rb");assert(f);
    n=fread(text,1,sizeof(text)-1,f);fclose(f);text[n]=0;
    want_frames=atoi(argv[2]);want_weapon=atoi(argv[3]);want_shield=atoi(argv[4]);
    /* the model's frames are the table's: known at spawn or read from the tag itself, the same answer */
    assert(AW_ItemsTagFrames(text,0)==want_frames);
    frames=AW_ItemsParseSkel(text,want_frames,paths,bones,scale,light,flame,&lit);
    assert(frames==want_frames);
    assert(!paths[0][0] && !paths[1][0]);                   /* no item named: the actor's record says */
    assert(bones[0]==want_weapon && bones[1]==want_shield); /* but the two bones to hold them on */
    assert(scale[0]>0.2499f && scale[0]<0.2501f && scale[1]>0.2499f && scale[1]<0.2501f && scale[2]>0.2499f &&
           scale[2]<0.2501f);
    assert(!lit && !light[0]);
    /* against another frame count the tag is refused, as every tag */
    assert(!AW_ItemsParseSkel(text,want_frames+1,paths,bones,scale,light,flame,&lit));
    printf("creature item tag: %d frames, weapon bone %d, shield bone %d, no item named\n",frames,bones[0],bones[1]);
    return 0;
}
