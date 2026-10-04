/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "d_local.h"
#include "aw_sky.h"
#include <assert.h>
float d_sdivzstepu,d_tdivzstepu,d_zistepu,d_sdivzstepv,d_tdivzstepv,d_zistepv;
float d_sdivzorigin,d_tdivzorigin,d_ziorigin;
fixed16_t sadjust,tadjust,bbextents,bbextentt;
unsigned int d_zwidth=8;
int screenwidth=8,cachewidth=1;
byte *cacheblock,*d_viewbuffer;short *d_pzbuffer;
void D_SpriteDrawSpans(sspan_t *);
int main(void){
    byte pixels[10],texture=42;short depth[10];sspan_t spans[2];int i;
    memset(spans,0,sizeof(spans));spans[0].count=8;spans[1].count=DS_SPAN_LIST_END;
    memset(pixels,99,sizeof(pixels));for(i=0;i<10;i++)depth[i]=AW_SKY_BACKGROUND_DEPTH;
    d_viewbuffer=pixels+1;d_pzbuffer=depth+1;cacheblock=&texture;d_ziorigin=1.0f/256;
    depth[3]=256; /* nearer opaque surface must still occlude the sprite */
    D_SpriteDrawSpans(spans);
    assert(pixels[0]==99 && pixels[9]==99 && depth[0]==AW_SKY_BACKGROUND_DEPTH && depth[9]==AW_SKY_BACKGROUND_DEPTH);
    for(i=1;i<=8;i++)if(i==3){assert(pixels[i]==99 && depth[i]==256);}
        else {assert(pixels[i]==42 && depth[i]==128);}
    /* Transparent texels never write color or depth. */
    texture=255;memset(pixels,99,sizeof(pixels));for(i=0;i<10;i++)depth[i]=AW_SKY_BACKGROUND_DEPTH;
    D_SpriteDrawSpans(spans);
    for(i=0;i<10;i++)assert(pixels[i]==99 && depth[i]==AW_SKY_BACKGROUND_DEPTH);
    texture=42;d_ziorigin=1.5f;for(i=0;i<10;i++)depth[i]=AW_SKY_BACKGROUND_DEPTH;
    D_SpriteDrawSpans(spans);for(i=1;i<=8;i++)assert(depth[i]==32767 && pixels[i]==42);
    return 0;
}
