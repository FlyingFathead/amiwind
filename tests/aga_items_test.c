/* Host fixture for aw_items.c's pure part: tag parsing and item posing
 * (tests/test_combat.py; tools/npc_items.py writes the tag files). */
#define AW_ITEMS_HOST_TEST
#include "aw_items.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

float Q_SinRad(float r) {return (float)sin(r);}
float Q_CosRad(float r) {return (float)cos(r);}

static int near(float a,float b) {return fabsf(a-b)<1e-3f;}

int main(void) {
    char paths[AW_ITEMS_KINDS][AW_ITEMS_PATH];float rows[3*AW_ITEMS_ROW],o[3],a[3];
    const char *good=
        "AWTG1 2\n"
        "weapon items/w0123456789ab.mdl\n"
        "shield -\n"
        "1.000 2.000 3.000 10.000 20.000 30.000 0.000 0.000 0.000 0.000 0.000 0.000\n"
        "-4.500 0.250 6.000 -5.000 90.000 0.000 0 0 0 0 0 0\n";
    assert(AW_ItemsParse(good,2,rows,3,paths)==2);
    assert(!strcmp(paths[0],"items/w0123456789ab.mdl") && paths[1][0]==0);
    assert(near(rows[0],1) && near(rows[5],30) && near(rows[12],-4.5f) && near(rows[13],.25f) && near(rows[15],-5));
    assert(!AW_ItemsParse(good,3,rows,3,paths));                         /* frame count must match the model */
    assert(!AW_ItemsParse("AWTG2 1\n",1,rows,3,paths));                  /* unknown version */
    assert(!AW_ItemsParse("AWTG1 1\nweapon ../x.mdl\nshield -\n0 0 0 0 0 0 0 0 0 0 0 0\n",1,rows,3,paths));   /* no parent paths */
    assert(!AW_ItemsParse("AWTG1 1\nweapon -\nshield -\n0 0 0 0 0 0 0 0 0 0 0\n",1,rows,3,paths));            /* short row */
    assert(!AW_ItemsParse("AWTG1 4\nweapon -\nshield -\n",4,rows,3,paths));                                    /* over the caller's rows */
    {   /* a skeletal model's tag (SKEL-ITEM-TAGS-52): item bones and the actor scale, no rows */
        int bones[AW_ITEMS_KINDS],lit=1;float scale[3],flame[3];char light[AW_ITEMS_PATH];
        const char *skel="AWTS1 2730\nweapon items/w_longsword.mdl\nshield -\nbones 14 -1\nscale 0.275 0.275 0.2375\n";
        const char *torch="AWTS1 2730\nweapon -\nshield items/a_shield.mdl\nbones -1 9\nscale 0.25 0.25 0.25\n"
                          "light items/gt_torch_0123456789ab.mdl\nemitter 1.5 -2.25 30.125\n";
        assert(AW_ItemsParseSkel(skel,2730,paths,bones,scale,light,flame,&lit)==2730 && !lit && !light[0]);
        assert(!strcmp(paths[0],"items/w_longsword.mdl") && !paths[1][0] && bones[0]==14 && bones[1]==-1);
        assert(near(scale[0],0.275f) && near(scale[2],0.2375f));
        /* a guard's torch: its own model beside the shield (the shield by day, the torch at night) */
        assert(AW_ItemsParseSkel(torch,2730,paths,bones,scale,light,flame,&lit)==2730 && lit);
        assert(!strcmp(paths[1],"items/a_shield.mdl") && !strcmp(light,"items/gt_torch_0123456789ab.mdl"));
        assert(near(flame[0],1.5f) && near(flame[1],-2.25f) && near(flame[2],30.125f) && bones[1]==9);
        assert(AW_ItemsParseSkel(torch,2730,paths,bones,scale,NULL,NULL,NULL)==2730);
        assert(!AW_ItemsParseSkel("AWTS1 10\nweapon -\nshield -\nbones 1 0\nscale 1 1 1\nlight t.mdl\nemitter 1 2\n",10,
                                  paths,bones,scale,light,flame,&lit));               /* a short emitter */
        assert(!AW_ItemsParseSkel("AWTS1 10\nweapon -\nshield -\nbones 1 0\nscale 1 1 1\nlight t.mdl\n",10,
                                  paths,bones,scale,light,flame,&lit));               /* a light without its flame */
        assert(!AW_ItemsParseSkel("AWTS1 10\nweapon -\nshield -\nbones 1 -1\nscale 1 1 1\nlight t.mdl\nemitter 1 2 3\n",
                                  10,paths,bones,scale,light,flame,&lit));            /* a light with no shield bone */
        assert(!AW_ItemsParseSkel(skel,2729,paths,bones,scale,NULL,NULL,NULL));        /* the table's frame count */
        assert(!AW_ItemsParse(skel,2730,rows,3,paths));                               /* old reader refuses it */
        assert(!AW_ItemsParseSkel("AWTS1 10\nweapon -\nshield -\nbones 64 0\nscale 1 1 1\n",10,paths,bones,scale,NULL,NULL,NULL));
        assert(!AW_ItemsParseSkel("AWTS1 10\nweapon -\nshield -\nbones 1.5 0\nscale 1 1 1\n",10,paths,bones,scale,NULL,NULL,NULL));
        assert(!AW_ItemsParseSkel("AWTS1 10\nweapon -\nshield -\nbones 1 0\nscale 1 0 1\n",10,paths,bones,scale,NULL,NULL,NULL));
        assert(!AW_ItemsParseSkel("AWTS1 10\nweapon -\nshield -\nbones 1 0\n",10,paths,bones,scale,NULL,NULL,NULL));
    }
    {   /* yaw 0: origin + tag, angles = tag; yaw 90: the tag's x turns into +y */
        float origin[3]={100,200,300},tag[6]={10,0,5,1,2,3};
        AW_ItemsPose(tag,origin,0,o,a);assert(near(o[0],110) && near(o[1],200) && near(o[2],305) && near(a[0],-1) && near(a[1],2) && near(a[2],3));   /* pitch negated for r_alias.c */
        AW_ItemsPose(tag,origin,90,o,a);assert(near(o[0],100) && near(o[1],210) && near(o[2],305) && near(a[1],92));
    }
    printf("items ok\n");
    return 0;
}
