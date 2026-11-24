/* SPDX-License-Identifier: GPL-2.0-or-later
 * The load errors' rules alone (engine/aga/src/aw_loaderr.c, SCENE-LOAD-FAIL-FALLBACK-67, DBG-TP-NOT-FOUND-BOX-67): the
 * codes, the OK box's text in the maintainer's form for every kind, the way back that failed, the load menu's notice,
 * the console's debug block, the cleaning of engine text and the map header check before leaving.
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_loaderr.h"

static aw_loaderr_t make(int kind,const char *map,const char *place){
    aw_loaderr_t e;memset(&e,0,sizeof(e));e.kind=kind;e.lump=-1;e.offset=-1;e.file_bytes=-1;e.fast_free=e.chip_free=-1;
    strcpy(e.map,map);strcpy(e.place,place);
    strcpy(e.here_map,"seyda");strcpy(e.here_place,"Seyda Neen");e.here_ok=1;e.here[0]=1;e.here[1]=2;e.here[2]=3;
    return e;
}
static const char *box(const aw_loaderr_t *e){static char t[1024];AW_LoadErrBox(e,t,sizeof(t));return t;}
static void put32(unsigned char *p,long v){unsigned long u=(unsigned long)v;p[0]=u&255;p[1]=(u>>8)&255;p[2]=(u>>16)&255;p[3]=(u>>24)&255;}

static void codes(void){
    int k;
    assert(!strcmp(AW_LoadErrCode(AW_LOADERR_NONE),"") && !strcmp(AW_LoadErrCode(AW_LOADERR_KINDS),""));
    for(k=1;k<AW_LOADERR_KINDS;k++){char c[8];sprintf(c,"LF%d",k);assert(!strcmp(AW_LoadErrCode(k),c));}
    assert(!strcmp(AW_LoadErrKind(AW_LOADERR_BROKEN),"broken map file"));
    assert(!strcmp(AW_LoadErrLumpName(7),"faces") && !strcmp(AW_LoadErrLumpName(0),"entities") &&
           !strcmp(AW_LoadErrLumpName(14),"models") && !strcmp(AW_LoadErrLumpName(15),"?"));
}
/* every kind in the maintainer's form: the sentence, the reason on the next line, the code, "You are in <place>." */
static void boxes(void){
    aw_loaderr_t e;
    e=make(AW_LOADERR_NOT_FOUND,"nowhere","");
    assert(!strcmp(box(&e),"Map nowhere was not found. Code LF1.\nYou are in Seyda Neen."));
    e=make(AW_LOADERR_NOT_ON_DISK,"ri8c361151ce","Andrano Ancestral Tomb");
    assert(!strcmp(box(&e),"Map ri8c361151ce (Andrano Ancestral Tomb) was not found.\nIt is not on this disk. Code LF2.\n"
                           "You are in Seyda Neen."));
    e=make(AW_LOADERR_NO_POINT,"","");e.x=1900000;e.y=-75120.5f;
    assert(!strcmp(box(&e),"No map holds the point 1900000 -75120. Code LF3.\nYou are in Seyda Neen."));
    e=make(AW_LOADERR_BROKEN,"bmcaius","Caius Cosades' House");e.broken=AW_BROKEN_HEADER;
    assert(!strcmp(box(&e),"Map bmcaius (Caius Cosades' House) was found but could not be loaded.\n"
                           "Broken map file (bad header). Code LF4.\nYou are in Seyda Neen."));
    e.broken=AW_BROKEN_SHORT;assert(strstr(box(&e),"\nBroken map file (short read). Code LF4.\n"));
    e.broken=AW_BROKEN_LUMP;e.lump=7;assert(strstr(box(&e),"\nBroken map file (bad lump 7). Code LF4.\n"));
    e.broken=AW_BROKEN_DATA;e.lump=-1;assert(strstr(box(&e),"\nBroken map file (bad data). Code LF4.\n"));
    /* MEMORY-EMERGENCY-PURGE-64, the maintainer's text: the place, the memory figures in KiB, the code; refused before
     * leaving, where he is; after the way back, OK returns him to the place he came in from */
    e=make(AW_LOADERR_MEMORY,"vivec_city","Vivec");e.need=3*1024*1024+1;e.have=512*1024;
    assert(!strcmp(box(&e),"Not enough memory to load Vivec (needs 3073 KiB, 512 KiB available). Code LF5.\n"
                           "You are in Seyda Neen."));
    e.way=AW_WAY_BACK;strcpy(e.back_map,"balmora");
    assert(!strcmp(box(&e),"Not enough memory to load Vivec (needs 3073 KiB, 512 KiB available). Code LF5.\n"
                           "OK returns you to Seyda Neen, where you came in."));
    e.place[0]=0;assert(!strncmp(box(&e),"Not enough memory to load vivec_city (needs",43));   /* no name: the map */
    strcpy(e.place,"Vivec");
    e.here_place[0]=e.here_map[0]=0;e.here_ok=0;   /* the console's block, before the way back has arrived */
    assert(strstr(box(&e),"\nOK returns you to balmora, where you came in."));
    e.back_failed=1;   /* the way back failed too: no promise of a return */
    assert(strstr(box(&e),"(needs 3073 KiB, 512 KiB available), and the way back to balmora failed as well. Code LF5.\n"));
    assert(!strstr(box(&e),"OK returns you"));
    e=make(AW_LOADERR_NO_SPAWN,"census","");assert(strstr(box(&e),"\nThe map did not spawn. Code LF6.\n"));
    e=make(AW_LOADERR_TIMEOUT,"census","");assert(strstr(box(&e),"\nThe load did not finish. Code LF7.\n"));
    e=make(AW_LOADERR_MISSING_FILE,"census","");strcpy(e.detail,"Model progs/x.mdl not found");
    assert(strstr(box(&e),"\nA file it needs is missing (Model progs/x.mdl not found). Code LF8.\n"));
    e=make(AW_LOADERR_ERROR,"census","");strcpy(e.detail,"forced failure (dbg loadfail)");
    assert(strstr(box(&e),"\nLoad error: forced failure (dbg loadfail). Code LF9.\n"));
    /* the place's name equal to the map's: once */
    e=make(AW_LOADERR_NOT_FOUND,"balmora","balmora");assert(!strncmp(box(&e),"Map balmora was not found.",26));
    /* no place known: the map */
    e=make(AW_LOADERR_NOT_FOUND,"x","");e.here_place[0]=0;assert(strstr(box(&e),"\nYou are in seyda."));
    /* none / out of range: no box */
    {char small[8];e=make(AW_LOADERR_NONE,"x","");assert(!AW_LoadErrBox(&e,small,sizeof(small)) && !small[0]);}
    e.kind=AW_LOADERR_KINDS;assert(!*box(&e));
}
/* the way back failed as well, and no place to go back to: the load menu */
static void no_place(void){
    aw_loaderr_t e;char n[80];
    e=make(AW_LOADERR_BROKEN,"bmcaius","");e.broken=AW_BROKEN_LUMP;e.lump=3;e.way=AW_WAY_FAILED;strcpy(e.back_map,"balmora");
    assert(!strcmp(box(&e),"Map bmcaius was found but could not be loaded, and the way back to balmora failed as well.\n"
                           "Broken map file (bad lump 3). Code LF4.\nLoad a saved game to go on."));
    AW_LoadErrNotice(&e,n,sizeof(n));assert(!strcmp(n,"LF4: map bmcaius did not load; no way back."));
    e.way=AW_WAY_NOWHERE;assert(strstr(box(&e),"\nLoad a saved game to go on.") && !strstr(box(&e),"way back"));
    AW_LoadErrNotice(&e,n,sizeof(n));assert(!strcmp(n,"LF4: map bmcaius did not load."));
    e=make(AW_LOADERR_NOT_ON_DISK,"prison","");e.way=AW_WAY_FAILED;
    AW_LoadErrNotice(&e,n,sizeof(n));assert(!strcmp(n,"LF2: map prison was not found; no way back."));
    e=make(AW_LOADERR_NO_POINT,"","");AW_LoadErrNotice(&e,n,sizeof(n));assert(!strcmp(n,"LF3: no map holds that point."));
    /* one line of the load menu (about 58 characters): the longest notice, a long map name cut to 20 characters */
    e=make(AW_LOADERR_MISSING_FILE,"a_map_name_far_longer_than_twenty","");e.way=AW_WAY_FAILED;
    AW_LoadErrNotice(&e,n,sizeof(n));assert(!strcmp(n,"LF8: map a_map_name_far_longe did not load; no way back.") && strlen(n)<=56);
    /* a short buffer stays terminated */
    AW_LoadErrNotice(&e,n,10);assert(strlen(n)==9);
}
/* NET-VIVEC-ENTITY-PACKET-OVERFLOW-66: an error in play, no load running: the place is loaded again */
static void in_play(void){
    aw_loaderr_t e;char n[80],t[1536];
    e=make(AW_LOADERR_ERROR,"bc_m2","Bitter Coast Region");e.in_play=1;e.way=AW_WAY_BACK;strcpy(e.back_map,"bc_m2");
    strcpy(e.detail,"The reliable message to the screen side overflowed (16380 bytes)");
    assert(!strcmp(box(&e),"An error stopped the game in bc_m2 (Bitter Coast Region); it was loaded again.\n"
                           "Error: The reliable message to the screen side overflowed (16380 bytes). Code LF9.\n"
                           "You are in Seyda Neen."));
    e.here_map[0]=e.here_place[0]=0;e.here_ok=0;
    assert(strstr(box(&e),"Code LF9.\nLoading bc_m2 again."));
    strcpy(e.from_map,"bc_m2");e.from_ok=1;AW_LoadErrConsole(&e,t,sizeof(t));
    assert(strstr(t,"  stopped at: bc_m2 at 0 0 0\n") && strstr(t,"  now: loading again bc_m2\n"));
    e.way=AW_WAY_FAILED;assert(!strncmp(box(&e),"An error stopped the game in bc_m2 (Bitter Coast Region), and loading it again "
                                                 "failed as well.\n",95));
    e.way=AW_WAY_NOWHERE;assert(!strncmp(box(&e),"An error stopped the game in bc_m2 (Bitter Coast Region) again soon after.\n",74));
    assert(strstr(box(&e),"\nLoad a saved game to go on."));
    AW_LoadErrNotice(&e,n,sizeof(n));assert(!strcmp(n,"LF9: an error stopped the game in bc_m2."));
    strcpy(e.map,"a_map_name_far_longer_than_twenty");AW_LoadErrNotice(&e,n,sizeof(n));assert(strlen(n)<=56);
}
/* AW-RECOVER (no error in play ends the game): the steps after the way back, the last autosave and the previous map;
 * the steps that did not load either; the console's "now" line before and after the arrival */
static void recovered(void){
    aw_loaderr_t e;char t[1536];
    /* in play, the same error again soon after: the last autosave */
    e=make(AW_LOADERR_ERROR,"seyda","");e.in_play=1;e.again=1;e.way=AW_WAY_AUTOSAVE;strcpy(e.save_label,"Autosave 2");
    strcpy(e.detail,"forced error in a script step (dbg hosterror script)");
    strcpy(e.here_place,"Census and Excise Office");
    assert(!strcmp(box(&e),"An error stopped the game in seyda again soon after.\n"
                           "Error: forced error in a script step (dbg hosterror script). Code LF9.\n"
                           "The last autosave (Autosave 2) was loaded. You are in Census and Excise Office."));
    AW_LoadErrConsole(&e,t,sizeof(t));assert(strstr(t,"  now: seyda at 1 2 3 (Census and Excise Office), the last autosave (Autosave 2)\n"));
    /* written before the arrival: which one is loading */
    e.here_map[0]=e.here_place[0]=0;e.here_ok=0;
    assert(strstr(box(&e),"Code LF9.\nThe last autosave (Autosave 2) is loading."));
    AW_LoadErrConsole(&e,t,sizeof(t));assert(strstr(t,"  now: loading the last autosave (Autosave 2)\n"));
    /* in play, the place again failed: ", and loading it again failed as well", then the autosave */
    e=make(AW_LOADERR_ERROR,"seyda","");e.in_play=1;e.back_failed=1;e.way=AW_WAY_AUTOSAVE;
    assert(!strncmp(box(&e),"An error stopped the game in seyda, and loading it again failed as well.\n",73));
    assert(strstr(box(&e),"\nThe last autosave was loaded. You are in Seyda Neen."));
    /* a load whose way back failed, the autosave too: the previous map */
    e=make(AW_LOADERR_ERROR,"prison","");strcpy(e.detail,"forced failure (dbg loadfail)");e.back_failed=1;e.save_failed=1;
    strcpy(e.back_map,"seyda");e.way=AW_WAY_PREVIOUS;strcpy(e.previous_map,"census");strcpy(e.here_place,"Census and Excise Office");
    assert(!strcmp(box(&e),"Map prison was found but could not be loaded, and the way back to seyda failed as well.\n"
                           "Load error: forced failure (dbg loadfail). Code LF9.\nThe last autosave did not load either.\n"
                           "The previous map, census, was loaded. You are in Census and Excise Office."));
    AW_LoadErrConsole(&e,t,sizeof(t));assert(strstr(t,"(Census and Excise Office), the previous map\n"));
    e.here_map[0]=e.here_place[0]=0;e.here_ok=0;AW_LoadErrConsole(&e,t,sizeof(t));
    assert(strstr(t,"  now: loading the previous map census\n") && strstr(t,"The previous map, census, is loading."));
    /* every step failed: the load menu, the steps that did not load either */
    e.previous_failed=1;e.way=AW_WAY_FAILED;
    assert(strstr(box(&e),"Code LF9.\nThe last autosave and the previous map did not load either.\nLoad a saved game to go on."));
    e.save_failed=0;assert(strstr(box(&e),"Code LF9.\nThe previous map did not load either.\nLoad a saved game to go on."));
    /* a way back that was never tried (a load from no place) and no autosave: no "way back" in the text */
    e=make(AW_LOADERR_ERROR,"prison","");e.way=AW_WAY_PREVIOUS;strcpy(e.previous_map,"census");
    assert(!strncmp(box(&e),"Map prison was found but could not be loaded.\n",46) && !strstr(box(&e),"way back"));
}
/* engine text in a box or a line: no codes the box or the console could read */
static void cleaning(void){
    char c[32];aw_loaderr_t e;
    AW_LoadErrClean(c,sizeof(c),"a%sb^c\n\x01\xe9" "z");assert(!strcmp(c,"a?sb?c???z"));
    AW_LoadErrClean(c,4,"abcdef");assert(!strcmp(c,"abc"));
    e=make(AW_LOADERR_ERROR,"m%d","");strcpy(e.detail,"bad %s here");
    assert(strstr(box(&e),"Map m?d was found") && strstr(box(&e),"Load error: bad ?s here."));
}
/* the console's debug block: the command, the map and its file, the error with the lump and offset, the memory, the
 * place left, where the player is now */
static void console(void){
    char t[1536];aw_loaderr_t e;
    e=make(AW_LOADERR_BROKEN,"bmcaius","Caius Cosades' House");e.broken=AW_BROKEN_SHORT;e.lump=7;e.offset=40960;
    strcpy(e.command,"dbg tp bmcaius");strcpy(e.file,"maps/bmcaius.bsp");e.file_bytes=52344;strcpy(e.detail,"Short BSP section");
    e.fast_free=8*1024*1024;e.chip_free=1024*1024;e.way=AW_WAY_BACK;strcpy(e.back_map,"seyda");
    strcpy(e.from_map,"seyda");e.from[0]=120;e.from[1]=-45;e.from[2]=77;e.from_ok=1;
    AW_LoadErrConsole(&e,t,sizeof(t));
    assert(!strncmp(t,"Load error LF4 (broken map file): Map bmcaius (Caius Cosades' House) was found but could not be loaded. "
                      "Broken map file (short read). Code LF4. You are in Seyda Neen.\n",160));
    assert(strstr(t,"  command: dbg tp bmcaius\n"));
    assert(strstr(t,"  map: bmcaius (Caius Cosades' House), file maps/bmcaius.bsp, 52344 bytes\n"));
    assert(strstr(t,"  error: short read in lump 7 (faces) at offset 40960: Short BSP section\n"));
    assert(strstr(t,"  memory: Fast 8192 KB free, Chip 1024 KB free\n"));
    assert(strstr(t,"  left: seyda at 120 -45 77\n"));
    assert(strstr(t,"  now: seyda at 1 2 3 (Seyda Neen), back where the load started\n"));
    /* written when the load fails, before the way back has arrived: where the player is going */
    e.here_map[0]=e.here_place[0]=0;e.here_ok=0;AW_LoadErrConsole(&e,t,sizeof(t));
    assert(strstr(t,"Code LF4. Going back to seyda.\n") && strstr(t,"  now: going back to seyda\n"));
    e=make(AW_LOADERR_MEMORY,"vivec_city","");e.need=2048;e.have=1024;strcpy(e.arena,"hunk");
    AW_LoadErrConsole(&e,t,sizeof(t));
    assert(strstr(t,"  memory: needs 2 KB, 1 KB free (hunk); Fast and Chip free not known\n"));
    assert(strstr(t,"  command: (not recorded)\n") && strstr(t,"  left: nothing (refused before the load)\n"));
    e=make(AW_LOADERR_NO_POINT,"","");e.x=10;e.y=20;AW_LoadErrConsole(&e,t,sizeof(t));
    assert(strstr(t,"  point: 10 20 (original coordinates)\n") && !strstr(t,"  map: "));
    e.way=AW_WAY_FAILED;AW_LoadErrConsole(&e,t,sizeof(t));
    assert(strstr(t,"  now: no place: the way back failed; the load menu\n"));
    /* a block cut to its buffer stays terminated */
    assert(AW_LoadErrConsole(&e,t,40)==39 && strlen(t)==39);
}
/* the map header check before leaving: version 29, lumps inside the file */
static void header(void){
    unsigned char h[124];int i,lump;
    memset(h,0,sizeof(h));put32(h,29);
    for(i=0;i<15;i++){put32(h+4+i*8,124+i*100);put32(h+8+i*8,100);}
    assert(AW_LoadErrMapHeader(h,124,124+1500,&lump)==0 && lump==-1);
    /* a truncated file: the last lumps run past its end (short read, the first such lump named) */
    assert(AW_LoadErrMapHeader(h,124,124+1250,&lump)==AW_BROKEN_SHORT && lump==12);
    /* shorter than a header, or a header read short */
    assert(AW_LoadErrMapHeader(h,124,100,&lump)==AW_BROKEN_HEADER && lump==-1);
    assert(AW_LoadErrMapHeader(h,60,1624,&lump)==AW_BROKEN_HEADER);
    /* another version */
    put32(h,30);assert(AW_LoadErrMapHeader(h,124,1624,&lump)==AW_BROKEN_HEADER);put32(h,29);
    /* a negative lump */
    put32(h+4+5*8,-4);assert(AW_LoadErrMapHeader(h,124,1624,&lump)==AW_BROKEN_HEADER && lump==5);
    assert(AW_LoadErrMapHeader(NULL,0,0,NULL)==AW_BROKEN_HEADER);
}
/* MEMORY-EMERGENCY-PURGE-64: a load that did not fit is tried once more after the emergency purge only when that can
 * change the answer */
static void purge_retry(void){
    aw_loaderr_t e=make(AW_LOADERR_MEMORY,"rifa4ef181ed","");strcpy(e.arena,"room");
    assert(AW_LoadErrPurgeRetry(&e,0,2048L*1024,0));          /* the purge gave back 2 MiB of the Fast RAM: once more */
    assert(!AW_LoadErrPurgeRetry(&e,1,2048L*1024,0));         /* the one retry is used */
    assert(!AW_LoadErrPurgeRetry(&e,0,-1,0) && !AW_LoadErrPurgeRetry(&e,0,-1,1));   /* switched off, the test too */
    assert(!AW_LoadErrPurgeRetry(&e,0,0,0));                  /* nothing given back: it would fail the same way */
    assert(AW_LoadErrPurgeRetry(&e,0,0,1));                   /* the test aid's shortage, which the retry cures */
    strcpy(e.arena,"fast");assert(AW_LoadErrPurgeRetry(&e,0,1,0));
    {   /* the Hunk's own memory: a purge of the Fast RAM does not grow it */
        const char *hunk[4]={"hunk","cache","zone","map"};int i;
        for(i=0;i<4;i++){strcpy(e.arena,hunk[i]);assert(!AW_LoadErrPurgeRetry(&e,0,4096L*1024,0));
                         assert(AW_LoadErrPurgeRetry(&e,0,4096L*1024,1));}
    }
    e.kind=AW_LOADERR_ERROR;strcpy(e.arena,"room");assert(!AW_LoadErrPurgeRetry(&e,0,4096L*1024,1));   /* not memory */
    assert(!AW_LoadErrPurgeRetry(NULL,0,4096L*1024,1));
}
int main(void){
    codes();boxes();no_place();in_play();recovered();cleaning();console();header();purge_retry();
    puts("load errors: codes, boxes, the way back, notices, cleaning, the console block, the header check and the purge's retry rule passed");
    return 0;
}
