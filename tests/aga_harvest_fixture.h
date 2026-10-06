/* SPDX-License-Identifier: GPL-2.0-or-later
 * Existing mutation-oriented tests use reserved writable strings. Production
 * catalogues and the compact fixture exercise the actual interning parser. */
#include <stdlib.h>
#define HSTR(field) (h.text+(field))
static void harvest_fixture_storage(void)
{
    unsigned at=1;int i;
    assert(AW_HarvestReserve(&h,AW_HARVEST_MODELS,AW_HARVEST_NODES,AW_HARVEST_EDGES,AW_HARVEST_PLANTS));
    h.text=(char *)calloc(1,AW_HARVEST_TEXT_BYTES);assert(h.text);h.text_bytes=AW_HARVEST_TEXT_BYTES;
    for(i=0;i<AW_HARVEST_MODELS;i++){h.model[i].path=(unsigned short)at;at+=64;}
    for(i=0;i<AW_HARVEST_NODES;i++){
        h.node[i].id=(unsigned short)at;at+=64;h.node[i].label=(unsigned short)at;at+=64;
    }
    for(i=0;i<AW_HARVEST_PLANTS;i++){
        h.plant[i].key=(unsigned short)at;at+=64;h.plant[i].label=(unsigned short)at;at+=64;
        h.plant[i].model=(unsigned short)at;at+=64;
    }
    assert(at<AW_HARVEST_TEXT_BYTES);h.models=h.nodes=h.edges=h.plants=0;
}
