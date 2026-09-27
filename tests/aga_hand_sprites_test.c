/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
int main(void){
 byte data[230];memset(data,0,sizeof(data));memcpy(data,"AWS1",4);data[5]=160;data[7]=100;data[9]=1;
 data[15]=20;data[19]=220;
 assert(AW_HandSpritesValidate(data,220));
 data[19]=219;assert(!AW_HandSpritesValidate(data,220));data[19]=220;
 data[21]=1;assert(!AW_HandSpritesValidate(data,220)); /* declared run has zero length */
 data[21]=0;data[9]=33;assert(!AW_HandSpritesValidate(data,220));data[9]=1;
 data[5]=159;assert(!AW_HandSpritesValidate(data,220));
 return 0;
}
