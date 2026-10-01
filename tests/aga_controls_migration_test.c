/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
extern char *keybindings[256];
void AW_ControlsMigrate(void);
void *Z_Malloc(int n){return calloc(1,n);}
void Z_Free(void *p){free(p);}
int Q_strlen(char *s){return strlen(s);}
void Q_strcpy(char *a,char *b){strcpy(a,b);}
int main(void){
    Key_SetBinding('1',"aw_drawdistance 450");Key_SetBinding('2',"impulse 2");
    Key_SetBinding('3',"aw_drawdistance 1000");Key_SetBinding('4',"aw_drawdistance 540");
    AW_ControlsMigrate();
    assert(!*keybindings['1'] && !*keybindings['3']);
    assert(!strcmp(keybindings['2'],"impulse 2") && !strcmp(keybindings['4'],"aw_drawdistance 540"));
    assert(!strcmp(keybindings['j'],"aw_journal") && !strcmp(keybindings['m'],"aw_worldmap"));
    Key_SetBinding('j',"custom_journal");Key_SetBinding('m',"");
    AW_ControlsMigrate();assert(!strcmp(keybindings['j'],"custom_journal") && !strcmp(keybindings['m'],"aw_worldmap"));
    assert(Key_AmigaRaw(0x26)=='j' && Key_AmigaRaw(0x37)=='m');
    AW_ControlsMigrate();assert(!strcmp(keybindings['2'],"impulse 2"));
    return 0;
}
