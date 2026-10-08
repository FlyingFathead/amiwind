/* SPDX-License-Identifier: GPL-2.0-or-later
 * FPU support status (ENGINE-FPSP-MISSING-31): the start-up console line and
 * `dbg fpu` name the resident support library, or say "none" with the docs
 * pointer on a 68040/68060. Host build: no Exec, so the probe reports none. */
#include "quakedef.h"
#include <assert.h>
static void (*status_command)(void);
static char printed[512];
static int prints;
void Cmd_AddCommand(char *n,void (*f)(void)){assert(!strcmp(n,"aw_fpu_status"));status_command=f;}
void Con_Printf(char *fmt,...){
    va_list ap;size_t used=strlen(printed);
    va_start(ap,fmt);vsnprintf(printed+used,sizeof printed-used,fmt,ap);va_end(ap);prints++;}
void Q_strncpy(char *dest,char *src,int count){strncpy(dest,src,count);}
int main(void){
    char line[160];
    AW_FpuStatusFormat(line,sizeof line,0x7f,"68040.library",40,2);
    assert(!strcmp(line,"FPU support: 68040.library v40.2 active (CPU 68040)"));
    AW_FpuStatusFormat(line,sizeof line,0xff,"68060.library",46,16);
    assert(!strcmp(line,"FPU support: 68060.library v46.16 active (CPU 68060)"));
    /* A 68060 under Kickstart 3.1 before its library: AttnFlags says 68040. */
    AW_FpuStatusFormat(line,sizeof line,0x4f,NULL,0,0);
    assert(!strcmp(line,"FPU support: none (CPU 68040): rare FPU cases may crash on a real 68040/68060; "
                        "see the docs, FPU support library"));
    AW_FpuStatusFormat(line,sizeof line,0xcf,NULL,0,0);
    assert(strstr(line,"none (CPU 68060)"));
    AW_FpuStatusFormat(line,sizeof line,0x07,NULL,0,0);
    assert(!strcmp(line,"FPU support: none (no 68040/68060 reported)"));
    /* Small buffers truncate, never overflow. */
    AW_FpuStatusFormat(line,12,0x7f,"68040.library",40,2);
    assert(strlen(line)==11);
    /* Start-up: registers the command and prints one line; the command repeats it. */
    AW_FpuStatusInit();
    assert(status_command && prints==1);
    assert(!strcmp(printed,"FPU support: none (no 68040/68060 reported)\n"));
    printed[0]=0;status_command();
    assert(prints==2 && !strcmp(printed,"FPU support: none (no 68040/68060 reported)\n"));
    puts("fpu status ok");
    return 0;
}
