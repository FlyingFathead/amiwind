/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Execute the real boot-volume validation wait (BOOT-VOLUME-NOT-VALIDATED-33)
 * against scripted AmigaDOS answers. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef long BPTR;
typedef long LONG;
#define ACCESS_READ (-2)
#define GVF_LOCAL_ONLY 0x200
#define MEMF_PUBLIC 1
#define MEMF_CLEAR 0x10000
#define ID_WRITE_PROTECTED 80
#define ID_VALIDATING 81
#define ID_VALIDATED 82
struct InfoData {LONG id_NumSoftErrors, id_UnitNumber, id_DiskState;};
static int validating_polls, info_calls, delays, locks, unlocks, allocs, frees, lock_fails, alloc_fails;
static const char *variable;
static char printed[4096];
static LONG GetVar(const char *name, char *buffer, LONG size, LONG flags) {
    assert(!strcmp(name, "AmiWindValidateWait"));
    assert(flags & GVF_LOCAL_ONLY); /* ENV: is not assigned on the boot disk */
    if (!variable) return -1;
    strncpy(buffer, variable, size - 1); buffer[size - 1] = 0;
    return (LONG)strlen(buffer);
}
static BPTR Lock(const char *name, LONG mode) {
    assert(!strcmp(name, "PROGDIR:")); assert(mode == ACCESS_READ);
    if (lock_fails) return 0;
    locks++; return 7;
}
static void UnLock(BPTR lock) {assert(lock == 7); unlocks++;}
static void *AllocVec(unsigned long size, unsigned long flags) {
    assert(size == sizeof(struct InfoData)); assert(flags & MEMF_CLEAR);
    if (alloc_fails) return NULL;
    allocs++; return calloc(1, size);
}
static void FreeVec(void *memory) {frees++; free(memory);}
static LONG Info(BPTR lock, struct InfoData *info) {
    assert(lock == 7);
    info_calls++;
    info->id_DiskState = info_calls <= validating_polls ? ID_VALIDATING : ID_VALIDATED;
    return 1;
}
static void Delay(LONG ticks) {assert(ticks == 50); delays++;}
static void PutStr(const char *text) {strcat(printed, text);}

#include "actual_validate_wait.inc"

static void reset(int polls) {
    validating_polls = polls; info_calls = delays = locks = unlocks = allocs = frees = 0;
    lock_fails = alloc_fails = 0; variable = NULL; printed[0] = 0;
}

static void check_lines(void) {
    const char *line = printed;
    while (*line) {
        const char *end = strchr(line, '\n');
        size_t length = end ? (size_t)(end - line) : strlen(line);
        assert(length <= 63); /* 64-column boot console (BOOT-CONSOLE-WIDTH-32) */
        line += length + (end ? 1 : 0);
    }
}

int main(void) {
    /* Clean volume: one Info call, no wait, nothing printed. */
    reset(0);
    assert(AW_WaitBootVolumeValidated() == 0);
    assert(info_calls == 1 && delays == 0 && printed[0] == 0);
    assert(locks == unlocks && allocs == frees);

    /* Validating for 3 polls: waits 3 s, says so once, then reports the end. */
    reset(3);
    assert(AW_WaitBootVolumeValidated() == 3);
    assert(delays == 3 && info_calls == 4);
    assert(strstr(printed, "being validated"));
    assert(strstr(printed, "Volume validated.\n"));
    { const char *first = strstr(printed, "being validated"); assert(!strstr(first + 1, "being validated")); }
    check_lines();
    assert(locks == unlocks && allocs == frees);

    /* Never finishes: gives up at the limit and starts anyway. */
    reset(1000000);
    assert(AW_WaitBootVolumeValidated() == AW_VALIDATE_WAIT_LIMIT);
    assert(delays == AW_VALIDATE_WAIT_LIMIT);
    assert(strstr(printed, "starting anyway"));
    check_lines();
    assert(locks == unlocks && allocs == frees);

    /* Previous behaviour, selectable: AmiWindValidateWait=0 starts at once. */
    reset(5); variable = "0";
    assert(AW_WaitBootVolumeValidated() == -1);
    assert(info_calls == 0 && delays == 0 && locks == 0 && printed[0] == 0);
    reset(2); variable = "1";
    assert(AW_WaitBootVolumeValidated() == 2);

    /* No lock or no memory: never blocks the start. */
    reset(5); lock_fails = 1;
    assert(AW_WaitBootVolumeValidated() == 0 && info_calls == 0);
    reset(5); alloc_fails = 1;
    assert(AW_WaitBootVolumeValidated() == 0 && info_calls == 0 && unlocks == 1);

    puts("validate wait ok");
    return 0;
}
