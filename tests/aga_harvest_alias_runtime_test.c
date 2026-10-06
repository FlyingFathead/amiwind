/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Extend the original runtime test; preserve all legacy brush assertions. */
#define main original_runtime_main
#define COM_FOpenFile legacy_open
#define S_LocalSound legacy_sound
#define AW_HARVEST_EXTERNAL_FIXTURE 1
#include "aga_harvest_runtime_test.c"
#undef main
#undef COM_FOpenFile
#undef S_LocalSound
int cl_numvisedicts,mod_numknown;
viddef_t vid;static byte colormap[256*64];
entity_t *cl_visedicts[MAX_VISEDICTS];model_t mod_known[256];
static int external,model_missing;static model_t alias;
qboolean Mod_CanFindName(const char *name){(void)name;return mod_numknown<256;}
model_t *Mod_ForName(char *name,qboolean crash){(void)crash;assert(!strcmp(name,"progs/harvest/test.mdl"));return model_missing?NULL:&alias;}
int COM_FOpenFile(char *name,FILE **out)
{
    FILE *f;int bytes;
    if(!external || !strcmp(name,"sound/pool/a031af0520e9edfa2.wav"))return legacy_open(name,out);
    assert(!strcmp(name,"harvest-vf0000.txt"));f=tmpfile();assert(f);*out=f;
    fputs("AWH4 1 1 1 1 1111111111111111111111111111111111111111111111111111111111111111 1\n",f);
    fputs("progs/harvest/test.mdl 2222222222222222222222222222222222222222222222222222222222222222 -8 -1 -2 3 1 2\n",f);
    fprintf(f,"%d 0 0 0 0 synthetic_ingredient\tOriginal ingredient name\n0 0 2\n",empty?2:0);
    fputs("aw:h:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 1 42 @0 11 0 1 20 0 0 0 0 0 2 Synthetic mushroom\n",f);
    bytes=(int)ftell(f);rewind(f);return bytes;
}
void S_LocalSound(char *name)
{
    if(!external){legacy_sound(name);return;}
    assert(!strcmp(name,"pool/a031af0520e9edfa2.wav") && !AW_HarvestHint());sounds++;
}
static void setup(void)
{
    reset();memset(&alias,0,sizeof alias);alias.type=mod_alias;alias.numframes=1;
    alias.mins[0]=-8;alias.mins[1]=-1;alias.mins[2]=-2;
    alias.maxs[0]=3;alias.maxs[1]=1;alias.maxs[2]=2;
    cl_numvisedicts=0;model_missing=0;vid.colormap=colormap;AW_HarvestSpawn();AW_HarvestLink();
}
int main(void)
{
    int i;char id[64];original_runtime_main();external=1;setup();
    assert(!AW_HarvestProtect(&edicts[2]));assert(cl_numvisedicts==1 && !strcmp(AW_HarvestHint(),"Synthetic mushroom"));
    /* Actual inverse-scale picking: model front is20+(-8*2)=4. A wall
     * at5 permits pickup; a wall at3 occludes it. Unscaled picking would miss. */
    wall=3.f/72;assert(!AW_HarvestHint());wall=5.f/72;assert(AW_HarvestHint());
    assert(AW_HarvestUse() && AW_StateGet(&aw_state,AW_ITEM,"synthetic_ingredient")==2);
    assert(sounds==1 && subtitle==1 && !strcmp(notice,"Picked up 2 Original ingredient name."));
    assert(!AW_HarvestUse() && !AW_HarvestHint());AW_HarvestBegin();AW_HarvestSpawn();cl_numvisedicts=0;AW_HarvestLink();
    assert(!cl_numvisedicts && !AW_HarvestHint());
    setup();empty=1;AW_HarvestBegin();AW_HarvestSpawn();cl_numvisedicts=0;AW_HarvestLink();
    assert(!cl_numvisedicts && !AW_HarvestHint() && !AW_HarvestUse() && !sounds && !subtitle);
    setup();for(i=0;i<AW_STATE_VALUES;i++){sprintf(id,"capacity%d",i);assert(AW_ItemAdd(&aw_state,id,1));}
    assert(AW_HarvestUse() && AW_HarvestHint() && !sounds);aw_state.count[AW_ITEM]=0;
    assert(AW_HarvestUse() && !AW_HarvestHint() && sounds==1);
    setup();model_missing=1;AW_HarvestBegin();AW_HarvestSpawn();cl_numvisedicts=0;AW_HarvestLink();
    assert(!cl_numvisedicts && !AW_HarvestHint() && !AW_HarvestUse() && !AW_StateGet(&aw_state,AW_ITEM,"synthetic_ingredient"));
    AW_HarvestClear();assert(!AW_HarvestHint());puts("AWH4 actual runtime scaled picking, occlusion, prompt, item transaction, empty-before-draw, return and missing model passed");return 0;
}
