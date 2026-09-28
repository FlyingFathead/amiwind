/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
client_state_t cl;
entity_t cl_entities[MAX_EDICTS];
viddef_t vid;
double host_frametime;
static byte base[768], output[768];
byte *host_basepal=base;
static int reads;
static byte menu[768];static int menu_active;
byte *AW_MoviePalette(void){return NULL;}
byte *AW_UIMenuPalette(void){return menu_active?menu:NULL;}
int MSG_ReadByte(void){return reads++ ? 40 : 0;}
float MSG_ReadCoord(void){return 0;}
void VID_ShiftPalette(unsigned char *pal){memcpy(output,pal,768);}
void V_SetContentsColor(int);
void V_ParseDamage(void);
void V_UpdatePalette(void);
extern cvar_t v_gamma;
int main(void) {
 int red,blue;
 memset(base,128,sizeof(base));v_gamma.value=1;host_frametime=0;
 V_SetContentsColor(CONTENTS_EMPTY);V_UpdatePalette();
 assert(output[0]==128 && output[1]==128 && output[2]==128);
 V_SetContentsColor(CONTENTS_WATER);V_UpdatePalette();
 assert(cl.cshifts[CSHIFT_DAMAGE].percent==0);
 assert(output[2]>output[1] && output[1]>output[0]);
 red=output[0];blue=output[2];
 V_ParseDamage();V_UpdatePalette();
 assert(cl.cshifts[CSHIFT_DAMAGE].percent>0);
 assert(output[0]>red && output[2]<blue); /* Red damage over blue water. */
 assert(cl.cshifts[CSHIFT_CONTENTS].percent>0);
 host_frametime=2;V_UpdatePalette();V_UpdatePalette();
 assert(cl.cshifts[CSHIFT_DAMAGE].percent==0);
 assert(output[0]==red && output[2]==blue); /* Water persists as damage fades. */
 host_frametime=0;V_SetContentsColor(CONTENTS_EMPTY);V_UpdatePalette();
 assert(output[0]==128 && output[1]==128 && output[2]==128);
 reads=0;V_ParseDamage();V_UpdatePalette();
 assert(output[0]>output[1] && output[1]==output[2]); /* Damage on land. */
 V_SetContentsColor(CONTENTS_WATER);V_SetContentsColor(CONTENTS_EMPTY);
 assert(cl.cshifts[CSHIFT_DAMAGE].percent>0); /* Leaving water retains damage. */
 memset(menu,64,sizeof(menu));menu_active=1;V_UpdatePalette();assert(output[0]==64 && output[1]==64 && output[2]==64);
 menu_active=0;V_UpdatePalette();assert(output[0]>output[1]); /* World shift is restored without a gamma change. */
 puts("blue water, red damage, combined shifts, fading and surfacing passed");
 return 0;
}
