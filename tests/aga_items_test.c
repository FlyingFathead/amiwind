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
    {   /* yaw 0: origin + tag, angles = tag; yaw 90: the tag's x turns into +y */
        float origin[3]={100,200,300},tag[6]={10,0,5,1,2,3};
        AW_ItemsPose(tag,origin,0,o,a);assert(near(o[0],110) && near(o[1],200) && near(o[2],305) && near(a[0],-1) && near(a[1],2) && near(a[2],3));   /* pitch negated for r_alias.c */
        AW_ItemsPose(tag,origin,90,o,a);assert(near(o[0],100) && near(o[1],210) && near(o[2],305) && near(a[1],92));
    }
    printf("items ok\n");
    return 0;
}
