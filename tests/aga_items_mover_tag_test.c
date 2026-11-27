/* Host fixture (tests/test_held_item_mover_tag.py, GUARD-WEAPON-INVISIBLE-65): the item tag of a model that is not
 * loaded when its actor spawns is read with the tag's own frame count.
 *
 * The opening's people (the boat guard and the dock guard of Seyda Neen among them) are baked models whose layout names
 * an actor-library model as its mover: the skeletal full kit they wear to walk and fight. At spawn the mover is
 * registered by name only (aw_anim.c lazy_index: nothing loaded; its slot holds 0, or the count of the model the slot
 * held before) and AW_ItemsPrep read the mover's tag against that count. The skeletal tag form demands its count
 * (the table's 2932 frames) to equal the one it is read against, so every such tag was refused ("Item tags ...:
 * invalid, items not drawn") and its actor fought with nothing drawn in its hands. Now the count of a model not known
 * at spawn is the tag's own (aw_items.c AW_ItemsTagFrames, both forms), and the model's frames are checked when it is
 * loaded and worn (frames_match), as the row form's movers have been since ANIMKIT-ITEM-TAG-FRAMES-35. The tags below
 * are the two guards' own, byte for byte as the build writes them. */
#define AW_ITEMS_HOST_TEST
#include "aw_items.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

float Q_SinRad(float r) {(void)r;return 0;}
float Q_CosRad(float r) {(void)r;return 1;}
int AW_ItemsTagFrames(const char *text,int numframes);

static const char *const boat_guard=   /* progs/n_795b72e8da35d80f.tag, the mover of progs/np_deck.mdl */
    "AWTS1 2932\nweapon items/wed2c14f9ae68.mdl\nshield -\nbones 18 9\nscale 0.275000 0.275000 0.255000\n";
static const char *const dock_guard=   /* progs/n_67bdae9dfda6bc38.tag, the mover of progs/np_dock.mdl */
    "AWTS1 2932\nweapon items/wed2c14f9ae68.mdl\nshield -\nbones 18 9\nscale 0.312500 0.312500 0.250000\n";
static const char *const torch_guard=  /* a skeletal guard carrying his torch (SKEL-ITEM-TAGS-52) */
    "AWTS1 2932\nweapon items/w.mdl\nshield -\nbones 18 9\nscale 0.25 0.25 0.25\nlight items/torch.mdl\nemitter 1 2 3\n";
static const char *const row_mover=    /* a baked full kit's rows (the form ANIMKIT-ITEM-TAG-FRAMES-35 already read so) */
    "AWTG1 2\nweapon items/w.mdl\nshield -\n"
    "1 2 3 4 5 6 0 0 0 0 0 0\n"
    "1.5 2 3 4 5 6 0 0 0 0 0 0\n";

/* prep()'s skeletal branch on TEXT read against COUNT: the frames (0 = refused) */
static int skel(const char *text,int count,char paths[AW_ITEMS_KINDS][AW_ITEMS_PATH],int bones[AW_ITEMS_KINDS],
                float scale[3],int *lit) {
    char light[AW_ITEMS_PATH];float flame[3];
    return count?AW_ItemsParseSkel(text,count,paths,bones,scale,light,flame,lit):0;
}

int main(void) {
    const char *tag[2];char paths[AW_ITEMS_KINDS][AW_ITEMS_PATH];int bones[AW_ITEMS_KINDS],lit,g,slot;float scale[3];
    /* the slot counts a mover registered by name only can hold at spawn: none, or a reused slot's (a static model,
     * the "2 model frames" of an rc4 test engine, a baked standing model, an older table) */
    static const int slots[]={0,1,2,21,2587};
    tag[0]=boat_guard;tag[1]=dock_guard;
    for(g=0;g<2;g++){
        int i;
        for(i=0;i<(int)(sizeof(slots)/sizeof(slots[0]));i++){
            slot=slots[i];
            /* BEFORE: the mover branch passed its slot count and the skeletal parse refused the tag */
            assert(!skel(tag[g],slot,paths,bones,scale,&lit));
            /* AFTER: a mover's count is not known at spawn (AW_ItemsPrep hands 0): the tag's own */
            assert(AW_ItemsTagFrames(tag[g],0)==2932);
            assert(skel(tag[g],AW_ItemsTagFrames(tag[g],0),paths,bones,scale,&lit)==2932);
            assert(!strcmp(paths[0],"items/wed2c14f9ae68.mdl") && !paths[1][0] && bones[0]==18 && bones[1]==9 && !lit);
        }
        printf("guard %d: mover tag read with its own 2932 frames: weapon %s on bone %d, scale %.4f\n",g+1,paths[0],
               bones[0],scale[0]);
    }
    assert(scale[0]>0.31f && scale[0]<0.32f);       /* the dock guard's own scale, the last one read */
    /* a known count is kept, so a loaded model's tag is still checked against its frames at spawn */
    assert(AW_ItemsTagFrames(boat_guard,2932)==2932);
    assert(AW_ItemsTagFrames(boat_guard,1)==1 && !skel(boat_guard,AW_ItemsTagFrames(boat_guard,1),paths,bones,scale,&lit));
    assert(AW_ItemsTagFrames(boat_guard,2931)==2931 && !skel(boat_guard,2931,paths,bones,scale,&lit));
    /* a carried light rides along (the torch guard's carrier) */
    assert(skel(torch_guard,AW_ItemsTagFrames(torch_guard,0),paths,bones,scale,&lit)==2932 && lit);
    /* the row form: the same rule, as its movers were read before */
    {
        float rows[2*AW_ITEMS_ROW];
        assert(AW_ItemsTagFrames(row_mover,0)==2);
        assert(AW_ItemsParse(row_mover,AW_ItemsTagFrames(row_mover,0),rows,2,paths)==2 && rows[AW_ITEMS_ROW]==1.5f);
        assert(AW_ItemsTagFrames(row_mover,17)==17 && !AW_ItemsParse(row_mover,17,rows,2,paths));
    }
    /* no tag, no count, a count past the form's limit, a fraction, a negative count: nothing */
    assert(!AW_ItemsTagFrames(NULL,0));
    assert(!AW_ItemsTagFrames("",0) && !AW_ItemsTagFrames("AWTX1 10\n",0) && !AW_ItemsTagFrames("AWTS1\n",0));
    assert(!AW_ItemsTagFrames("AWTS1 0\n",0) && !AW_ItemsTagFrames("AWTS1 65536\n",0) && !AW_ItemsTagFrames("AWTS1 12.5\n",0));
    assert(AW_ItemsTagFrames("AWTS1 65535\n",0)==65535);
    assert(AW_ItemsTagFrames("AWTG1 256\n",0)==256 && !AW_ItemsTagFrames("AWTG1 257\n",0));
    assert(!AW_ItemsTagFrames(boat_guard,-1));
    printf("item tags mover count ok\n");
    return 0;
}
