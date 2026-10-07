/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
static void (*handlers[3])(void);
static char output[256];
void Con_Printf(char *fmt,...){va_list ap;va_start(ap,fmt);vsnprintf(output,sizeof output,fmt,ap);va_end(ap);}
void Cmd_AddCommand(char *name,void (*fn)(void)){
 if(!strcmp(name,"aw_interiorluma_set"))handlers[0]=fn;
 else if(!strcmp(name,"aw_luma_status"))handlers[2]=fn;
 else {assert(!strcmp(name,"aw_exteriorluma_set"));handlers[1]=fn;}
}
void R_InteriorLumaInit(void);
int main(void){R_InteriorLumaInit();assert(handlers[0] && handlers[1] && handlers[2]);
 handlers[2]();assert(!strcmp(output,"Luma: original light (built without luma controls).\n"));
 handlers[0]();assert(!strcmp(output,"Can't adjust interior luma: built without luma controls.\n"));
 handlers[1]();assert(!strcmp(output,"Can't adjust exterior luma: built without luma controls.\n"));return 0;}
