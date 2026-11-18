/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_netsend.inc: which entity updates go into a frame's message from the game's server to its screen side
 * (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66). Included by sv_main.c and by the host test tests/aga_netsend_test.c; plain C,
 * no engine state. An .inc, not a new engine file: the engine's file list stays as it is.
 *
 * Every update is sized exactly before it is written, so a frame's message can never run past its buffer. When the
 * updates of everything in sight do not fit, the nearest go first, those in front of the player before those behind
 * him, and every frame an update had to wait moves it forward: the rest go out in the next frames, a far one within a
 * few frames.
 */

/* AW_NETSEND_RECORD_MAX, the largest update of one entity, is the includer's, computed from its message format
 * (sv_main.c). The old check reserved 16 bytes, 12 fewer than an update with 3-byte coordinates, a 2-byte model and
 * the AmiWind fields can take. */
#ifndef AW_NETSEND_RECORD_MAX
#error "aw_netsend.inc: define AW_NETSEND_RECORD_MAX from the message format first"
#endif
#define AW_NETSEND_MISSED_MAX 255   /* never a cap that ties the waiting ones and lets the farthest wait for good */

typedef struct {int key;short e;short bytes;} aw_netsend_t;

/* The order key of one update (lower first): its distance in world units; still scenery (a plant, an item, a static
 * model: no actor) after the actors within 8192 units (the joined creatures and residents are the highest entity
 * numbers, the ones the old loop left out in every full frame: OUTDOOR-CREATURES-REGRESSION-66); behind the player
 * after everything in front of him within 16384 units; and 4096 units forward for every frame it waited (a far one
 * beats a near one that did not wait after a few frames, so with many waiting every one goes out within about the
 * frames it takes to send them all once). The player's own entity takes AW_NETSEND_FIRST. */
#define AW_NETSEND_FIRST (-0x7fffffff)
static int AW_NetSendKey(float dist,int behind,int scenery,int missed)
{
    int k=dist>0?(dist<60000?(int)dist:60000):0;
    if(scenery)k+=8192;
    if(behind)k+=16384;
    if(missed>AW_NETSEND_MISSED_MAX)missed=AW_NETSEND_MISSED_MAX;
    if(missed<0)missed=0;
    return k-missed*4096;
}
static int AW_NetSendCompare(const void *a,const void *b)
{
    const aw_netsend_t *x=(const aw_netsend_t *)a,*y=(const aw_netsend_t *)b;
    if(x->key!=y->key)return x->key<y->key?-1:1;
    return x->e-y->e;
}
/* Marks in SEND (one flag per candidate, in C's order after the call) the updates of the N candidates C that go into
 * BUDGET bytes, and returns the bytes they take. All of them fit: none is moved (the entity order stays). Otherwise C
 * is sorted by key and taken in that order; one that does not fit is left for a later frame and a smaller one after it
 * still goes in. Never more than BUDGET. */
static int AW_NetSendChoose(aw_netsend_t *c,int n,int budget,unsigned char *send)
{
    int i,total=0,used=0;
    for(i=0;i<n;i++)total+=c[i].bytes>0?c[i].bytes:0;
    if(total<=budget){
        for(i=0;i<n;i++)send[i]=1;
        return total;
    }
    qsort(c,(size_t)n,sizeof(*c),AW_NetSendCompare);
    for(i=0;i<n;i++){
        send[i]=(unsigned char)(c[i].bytes>0 && c[i].bytes<=budget-used);
        if(send[i])used+=c[i].bytes;
    }
    return used;
}
