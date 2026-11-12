/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_tutorial_rules.c alone (OPENING-TUTORIAL-KEYS-65): every row of the tutorial table filled from a binding table,
 * the bound key in each, a rebound key shown as rebound, an unbound one as "not bound", a once row shown once per game,
 * a window's key list read and matched. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_tutorial.h"

/* the shipped bindings (config/keymaps.cfg) of the commands the table names; the window lists (aw_worldui.c) */
static struct {const char *command;const char *key;} binds[]={
    {"aw_stats","P"},{"aw_inventory","I"},{"aw_magicmenu","O"},{"aw_worldmap","M"},{"aw_journal","J"},
    {"impulse 202","F"},{"+attack","the left mouse button"},{"winkey:inv_use","E) or (Enter"},{"aw_magicfx ready","R"}};
static const char *bound(const char *command){
    int i;
    for(i=0;i<(int)(sizeof(binds)/sizeof(binds[0]));i++)if(!strcmp(binds[i].command,command))return binds[i].key;
    return NULL;
}
static const char *nothing(const char *command){(void)command;return NULL;}

int main(void){
    char out[1024],words[64];int i,n;const aw_tutorial_row_t *r;
    /* the hash: case and white space do not count */
    assert(AW_TutorialHash("You now have  a map.")==AW_TutorialHash(" you now HAVE a\nmap. "));
    assert(AW_TutorialHash("a map")!=AW_TutorialHash("a mop"));
    /* every row resolves: no placeholder left, a key in parentheses in its key column, nothing unbound with the
     * shipped keys, no '[' (the game font's '[' and ']' are ornaments) */
    n=AW_TutorialRows();assert(n>=16);
    for(i=0;i<n;i++){
        r=AW_TutorialRow(i);
        if(r->once==AW_TUTORIAL_HIDE){assert(!r->text[0]);continue;}   /* a box not shown (TUTORIAL-BOX-SHOWN-TWICE-65) */
        AW_TutorialFill(r->text,"ORIGINAL TEXT",bound,out,sizeof(out));
        assert(!strstr(out,"{") && !strstr(out,"}") && !strstr(out,"not bound") && !strchr(out,'[') && !strchr(out,']'));
        assert(strstr(out,"\t(") || strstr(out,"^Action"));
        assert(AW_TutorialFind(r->hash)==r->text);
    }
    /* the stats box after the review: P, then rebound to K it says K; unbound it says so */
    r=NULL;for(i=0;i<n;i++)if(AW_TutorialRow(i)->hash==0xa1068e72UL)r=AW_TutorialRow(i);
    assert(r);
    AW_TutorialFill(r->text,"",bound,out,sizeof(out));assert(strstr(out,"View your character\t(P)"));
    binds[0].key="K";AW_TutorialFill(r->text,"",bound,out,sizeof(out));assert(strstr(out,"(K)") && !strstr(out,"(P)"));
    binds[0].key="P";
    AW_TutorialFill(r->text,"",nothing,out,sizeof(out));assert(strstr(out,"(not bound)"));
    /* the dagger: the inventory key, the window's own equip keys, the ready key, in the maintainer's format */
    r=NULL;for(i=0;i<n;i++)if(AW_TutorialRow(i)->hash==0xc2ddd5caUL)r=AW_TutorialRow(i);
    AW_TutorialFill(r->text,"",bound,out,sizeof(out));
    assert(!strcmp(out,"To equip the dagger:\n\nOpen your inventory\t(I)\nSelect the dagger\t(E) or (Enter)\n"
                       "(or double-click it)\t\nReady or sheathe it\t(F)\n\n"));
    /* the magic box: two actions, both from the bindings */
    r=NULL;for(i=0;i<n;i++)if(AW_TutorialRow(i)->hash==0xbf4fbd1dUL)r=AW_TutorialRow(i);
    AW_TutorialFill(r->text,"",bound,out,sizeof(out));assert(strstr(out,"Open it\t(O)\nReady magic\t(R)\n"));
    /* an "add" row keeps the original text first */
    r=NULL;for(i=0;i<n;i++)if(AW_TutorialRow(i)->hash==0x62ac0e03UL)r=AW_TutorialRow(i);
    AW_TutorialFill(r->text,"Equip lights.",bound,out,sizeof(out));assert(!strncmp(out,"Equip lights.\n",14));
    /* a once row (the journal's first update): the first time only, again after a New Game */
    {char text[64];strcpy(text,"x");
     /* a text with no row is left alone */
     assert(!AW_TutorialApply("No such box.",bound,out,sizeof(out)));
     r=NULL;for(i=0;i<n;i++)if(AW_TutorialRow(i)->once==AW_TUTORIAL_ONCE)r=AW_TutorialRow(i);
     assert(r && r->hash==0x14a11b94UL);
     /* the original's second menu hints after the stats and the inventory boxes: hidden, never the same box twice */
     {int hidden=0;for(i=0;i<n;i++){r=AW_TutorialRow(i);
         if(r->hash==0x63f76653UL || r->hash==0x0640f16dUL){assert(r->once==AW_TUTORIAL_HIDE);hidden++;}}
      assert(hidden==2);}
     assert(AW_TutorialApply("Your journal has been updated.",bound,out,sizeof(out)) && strstr(out,"(J)"));
     assert(!AW_TutorialApply("Your journal has been updated.",bound,out,sizeof(out)));
     AW_TutorialReset();assert(AW_TutorialApply("your journal has  been updated.",bound,out,sizeof(out)));(void)text;}
    /* a window's key list: matched by name, read in the parenthesis form */
    assert(AW_WinKeyMatch("E ENTER","enter") && AW_WinKeyMatch("E ENTER","e") && !AW_WinKeyMatch("E ENTER","d"));
    AW_WinKeyWords("E ENTER",words,sizeof(words));assert(!strcmp(words,"E) or (Enter"));
    AW_WinKeyWords("k",words,sizeof(words));assert(!strcmp(words,"K"));
    AW_WinKeyWords("",words,sizeof(words));assert(!words[0]);
    /* the output never runs past its capacity */
    assert(AW_TutorialFill("{text}{text}","0123456789",bound,out,8)==7 && strlen(out)==7);
    printf("tutorial table ok: %d rows\n",n);
    return 0;
}
