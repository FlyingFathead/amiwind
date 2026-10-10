/* SPDX-License-Identifier: GPL-2.0-or-later
 * Test harness channels (aw_testbox.c): the command mailbox, the AWTEST: drive
 * and the test start-up options. */
#ifndef AW_TESTBOX_H
#define AW_TESTBOX_H
#define AW_CMDBOX_VERSION 1
#define AW_CMDBOX_COMMAND 512
#define AW_CMDBOX_RESULT 512
#define AW_CMDBOX_OK 0
#define AW_CMDBOX_REFUSED 1   /* command not 0-terminated within the buffer, or control characters */
#define AW_CMDBOX_DISABLED 2  /* aw_cmdbox 0, or a normal build without aw_cmdbox 1 */
/* Layout for harnesses (big-endian 32-bit fields on the Amiga; offsets in
 * docs/chim/build_guide/DIRECT_START.md): find "AWCMDBOX", check self == its
 * address and version, write command (0-terminated), then command_seq += 1;
 * wait until result_seq == command_seq, read status, frame and result. */
typedef struct {
    char magic[8];                       /* "AWCMDBOX", no terminator */
    unsigned long version;               /* AW_CMDBOX_VERSION */
    unsigned long size;                  /* sizeof(aw_cmdbox_t) */
    void *self;                          /* its own address, set at start-up */
    char build[32];                      /* AmiWind version, 0-terminated */
    volatile unsigned long command_seq;  /* written by the harness after command */
    char command[AW_CMDBOX_COMMAND];
    volatile unsigned long result_seq;   /* set by the engine when result is complete */
    volatile long status;
    volatile unsigned long frame;        /* host frame of the result */
    char result[AW_CMDBOX_RESULT];       /* console output of the command's frame, 0-terminated */
} aw_cmdbox_t;
extern aw_cmdbox_t aw_cmdbox;
#define AW_TEST_FILE 8192
void AW_TestBoxInit(void);
/* Once per frame (host.c): the mailbox compare and the AWTEST:cmd.cfg poll. */
void AW_TestBoxFrame(void);
void AW_TestPollFrame(void);
/* Console output while a mailbox command runs (console.c Con_Printf). */
void AW_TestBoxPrint(const char *text);
/* The drive's path prefix ("AWTEST:") when the volume is mounted; 0 otherwise. */
int AW_TestDrive(char *out,int capacity);
/* Start-up: queue AWTEST:test.cfg and then aw_startup_continue; 0 when absent. */
int AW_TestBootExec(void);
/* After test.cfg: 1 when the logo is skipped (a game was started, aw_boot_console, aw_test_start). */
int AW_TestBootSkipLogo(void);
/* aw_scene.c: 1 while a scene load it queued is pending. */
int AW_SceneStarting(void);
#endif
