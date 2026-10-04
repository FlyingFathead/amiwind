/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Execute the real Sys_Error with deterministic AmigaDOS failure injection. */
#include <assert.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "amiwind_version.h"
typedef long BPTR;
typedef long LONG;
typedef int qboolean;
#define true 1
#define false 0
#define MODE_NEWFILE 1
#define MODE_OLDFILE 2
#define ACCESS_READ 0
static struct {void *membase;} quakeparms;
static void *aw_heap_allocation;
static unsigned long aw_heap_allocation_size;
static jmp_buf terminated;
static int mode, phase, exit_status, close_count, read_count;
static long saved_length, cursor;
static char saved[2048], output[4096];
static void AW_HeapAuditPhase(void *unused, const char *name) {
    (void)unused; assert(!strcmp(name,"fatal-exit")); assert(phase==0); phase=1;
}
static BPTR Open(const char *name, int access) {
    assert(phase==1); assert(!strcmp(name,"ERROR.TXT"));
    if(access==MODE_NEWFILE) return mode==1 ? 0 : 1;
    assert(access==MODE_OLDFILE); cursor=0; return mode==4 ? 0 : 2;
}
static LONG Write(BPTR handle, const void *data, LONG length) {
    assert(handle==1); saved_length=length; memcpy(saved,data,length);
    return mode==2 ? length-1 : length;
}
static int Close(BPTR handle) {
    close_count++; return !((handle==1 && mode==3) || (handle==2 && mode==7));
}
static LONG Read(BPTR handle, void *data, LONG length) {
    LONG amount; assert(handle==2); read_count++;
    amount=saved_length-cursor; if(amount>length)amount=length;
    memcpy(data,saved+cursor,amount); cursor+=amount;
    if(mode==5 && amount) ((char *)data)[0]^=1;
    if(mode==6 && !amount) {((char *)data)[0]='x'; return 1;}
    return amount;
}
static BPTR Lock(const char *name, int access) {
    assert(!strcmp(name,"ERROR.TXT")); assert(access==ACCESS_READ);
    return mode==9 ? 0 : 3;
}
static int NameFromLock(BPTR handle, char *path, unsigned long size) {
    assert(handle==3); assert(size>strlen("AmiWind:ERROR.TXT"));
    if(mode==8)return 0; strcpy(path,"AmiWind:ERROR.TXT"); return 1;
}
static void UnLock(BPTR handle) {assert(handle==3);}
static void Host_Shutdown(void) {assert(phase==1);phase=2;}
static void FreeMem(void *memory, unsigned long size) {
    assert(phase==2 && memory==aw_heap_allocation && size==16);phase=3;
}
static void AW_PlatformClose(void) {assert(phase==3);phase=4;}
static void PutStr(const char *text) {
    assert(phase==4); assert(strlen(output)+strlen(text)<sizeof(output));
    strcat(output,text);
}
static void mocked_exit(int status) {exit_status=status;longjmp(terminated,1);}
#define exit mocked_exit
#include "actual_sys_error.inc"
#undef exit
int main(void) {
    char cause[200]; int i;
    for(i=0;i<150;i++)cause[i]=(char)('a'+i%26);cause[150]=0;
    for(mode=0;mode<10;mode++) {
        phase=exit_status=close_count=read_count=0; output[0]=0;
        aw_heap_allocation=&phase; aw_heap_allocation_size=16;
        quakeparms.membase=aw_heap_allocation;
        if(!setjmp(terminated)) Sys_Error("fixture error: %s",cause);
        assert(exit_status==EXIT_FAILURE && phase==4);
        assert(!quakeparms.membase && !aw_heap_allocation);
        assert(strstr(output,"AmiWind v" AMIWIND_VERSION " crashed!\nCrash details: fixture error: "));
        assert(strstr(output,cause));
        if(mode==0 || mode>=8) {
            assert(read_count>=4); /* Three fixed chunks and EOF. */
            assert(strstr(output,"Crash log is at "));
            assert(strstr(output,mode==0 ? "AmiWind:ERROR.TXT\n" : "ERROR.TXT (in the launch directory)\n"));
        } else {
            assert(!strstr(output,"Crash log is at "));
            assert(strstr(output,"Crash log could not be verified at ERROR.TXT (in the launch directory).\n"));
        }
        assert(strstr(output,"\n------------------------------------------------------\nTo restart AmiWind"));
    }
    puts("fatal report: screen-close ordering and 10 DOS result paths passed");
    return 0;
}
