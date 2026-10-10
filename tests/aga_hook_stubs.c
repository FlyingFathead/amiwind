/* SPDX-License-Identifier: GPL-2.0-or-later
 * Weak stand-ins for engine modules that many native fixtures do not link:
 * the quick character screen (aw_quickchar.c), the test harness channels
 * (aw_testbox.c) and the partial-area notice (aw_miniwind.c). A fixture that
 * links the real module gets the real functions (strong symbols win); every
 * other fixture sees "not active / not present", which is what a normal game
 * without those features does. tests/test_aga_native_source.py adds this file
 * to every native compile. */
#include "quakedef.h"
#include "aw_miniwind.h"
#include "aw_quickchar.h"
#include "aw_testbox.h"
#define WEAK __attribute__((weak))
WEAK int AW_QuickCharActive(void){return 0;}
WEAK int AW_QuickCharKey(int key){(void)key;return 0;}
WEAK void AW_QuickCharDraw(void){}
WEAK void AW_QuickCharTick(void){}
WEAK int AW_QuickCharOpen(int pages,aw_quickchar_done_t on_done){(void)pages;(void)on_done;return 0;}
WEAK int AW_QuickCharScripted(void){return 0;}
WEAK int AW_SkipCensus(void){return 0;}
WEAK void AW_QuickCharInit(void){}
WEAK int AW_TestBootExec(void){return 0;}
WEAK int AW_TestBootSkipLogo(void){return 0;}
WEAK void AW_TestBoxFrame(void){}
WEAK void AW_TestPollFrame(void){}
WEAK void AW_TestBoxPrint(const char *text){(void)text;}
WEAK void AW_TestBoxInit(void){}
WEAK int AW_MiniwindActive(void){return 0;}
WEAK const aw_miniwind_t *AW_Miniwind(void){static aw_miniwind_t none;return &none;}
WEAK int AW_MenuHeaderLines(const char *text,int width,char lines[2][AW_MINIWIND_HEADER]){
    (void)text;(void)width;lines[0][0]=lines[1][0]=0;return 0;
}
/* The animation kit console (aw_animkit.c): nothing to drive in fixtures without it. */
WEAK void AW_AnimKitTick(void) {}
WEAK void AW_AnimKitInit(void) {}
