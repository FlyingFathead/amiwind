/* SPDX-License-Identifier: GPL-2.0-or-later
 * awbench: asset-free hardware benchmark for AmiWind owners (docs/HARDWARE-BENCHMARK.md).
 *
 *   awbench cpu                 CPU, FPU and memory loops
 *   awbench disk FILE           create FILE (8 MB) if missing, then read it in
 *                               16 KiB and 64 KiB requests, sequential and with
 *                               seeks; MB/s and how much CPU time other tasks
 *                               still got while the disk was read
 *   awbench all FILE            both
 *
 * Every run starts with a setup block (AWBENCH-REPORT begin/end: CPU and FPU
 * from AttnFlags, the 68060's PCR when 68060.library has flagged one, memory,
 * Kickstart/Workbench versions, resident FPU support library, and the test
 * drive's file system, device, unit, buffers and MaxTransfer) with the fields
 * only the tester knows left to fill in. Every result line starts with
 * "AWBENCH" and holds key=value pairs, so a report can be redirected
 * (awbench >RAM:b.txt all DH1:awbench.dat). DOS requesters are off for the
 * run: a missing drive fails with a message.
 * Time comes from timer.device ReadEClock. "Free CPU" is measured the classic
 * way: a counting task at priority -100 runs whenever nothing else wants the
 * CPU; its counting rate while the file is read, against its rate while the
 * benchmark sleeps, is the share of the CPU the disk transfer left over
 * (PIO IDE copies every byte with the CPU, so it is often low).
 * Integer arithmetic only, except the FPU loop, which runs only when the
 * system reports an FPU and uses only FADD/FMUL (no 68040-unimplemented
 * instructions). Nothing here reads game data.
 */
#include <exec/types.h>
#include <exec/memory.h>
#include <exec/execbase.h>
#include <exec/tasks.h>
#include <devices/timer.h>
#include <dos/dos.h>
#include <dos/dosextens.h>
#include <dos/filehandler.h>
#include <proto/exec.h>
#include <proto/dos.h>
#include <proto/timer.h>
#include <clib/alib_protos.h>
#include <stdio.h>
#include <string.h>

#define FILE_BYTES (8UL * 1024 * 1024)
#define BIG_REQUEST (64UL * 1024)

extern struct ExecBase *SysBase;
struct Device *TimerBase;
static struct timerequest *timer_request;
static struct MsgPort *timer_port;
static ULONG eclock_rate;

static volatile ULONG idle_count;
static volatile int idle_stop, idle_done;

static unsigned long long now_ticks(void)
{
    struct EClockVal v;
    ReadEClock(&v);
    return ((unsigned long long)v.ev_hi << 32) | v.ev_lo;
}

static unsigned long microseconds(unsigned long long ticks)
{
    return (unsigned long)(ticks * 1000000ULL / eclock_rate);
}

/* value/1000 with three decimals, from integers */
static void thousandths(char *out, unsigned long long v)
{
    sprintf(out, "%lu.%03lu", (unsigned long)(v / 1000), (unsigned long)(v % 1000));
}

static void idle_task(void)
{
    while (!idle_stop)
        idle_count++;
    idle_done = 1;
    Wait(0);    /* parked until RemTask */
}

static struct Task *idle;

static int idle_start(void)
{
    idle_stop = idle_done = 0;
    idle_count = 0;
    idle = CreateTask((STRPTR)"awbench idle", -100, (APTR)idle_task, 4096);
    return idle != NULL;
}

static void idle_end(void)
{
    if (!idle)
        return;
    idle_stop = 1;
    while (!idle_done)
        Delay(1);
    DeleteTask(idle);
    idle = NULL;
}

/* idle counts per second over a sleeping interval */
static unsigned long idle_rate(void)
{
    ULONG c0;
    unsigned long long t0, t1;
    c0 = idle_count;
    t0 = now_ticks();
    Delay(50);
    t1 = now_ticks();
    return (unsigned long)((unsigned long long)(idle_count - c0) * eclock_rate / (t1 - t0 ? t1 - t0 : 1));
}

static void cpu_tests(void)
{
    unsigned long long t0, t1;
    unsigned long i, x = 1, us;
    unsigned char *fast, *chip;
    char rate[32];

    t0 = now_ticks();
    for (i = 0; i < 10000000UL; i++)
        x = x * 1103515245UL + 12345UL;
    t1 = now_ticks();
    us = microseconds(t1 - t0);
    thousandths(rate, 10000000ULL * 1000ULL / (us ? us : 1));
    printf("AWBENCH cpu test=intmul loops=10000000 us=%lu mloops_per_s=%s check=%lu\n", us, rate, x & 0xff);

    {
        volatile unsigned long sink = 0;
        unsigned long a = 0;
        t0 = now_ticks();
        for (i = 0; i < 20000000UL; i++)
            a += i ^ (a >> 3);
        sink = a;
        t1 = now_ticks();
        us = microseconds(t1 - t0);
        thousandths(rate, 20000000ULL * 1000ULL / (us ? us : 1));
        printf("AWBENCH cpu test=intadd loops=20000000 us=%lu mloops_per_s=%s check=%lu\n", us, rate, sink & 0xff);
    }

    if (SysBase->AttnFlags & (AFF_68881 | AFF_68882 | AFF_FPU40)) {
        volatile double sink;
        double a = 1.0, b = 0.0;
        t0 = now_ticks();
        for (i = 0; i < 4000000UL; i++) {
            a = a * 1.0000001 + 1e-9;
            b = b + a * 0.5;
        }
        sink = a + b;
        t1 = now_ticks();
        us = microseconds(t1 - t0);
        thousandths(rate, 4000000ULL * 1000ULL / (us ? us : 1));
        printf("AWBENCH cpu test=fpu loops=4000000 us=%lu mloops_per_s=%s\n", us, rate);
        (void)sink;
    } else {
        printf("AWBENCH cpu test=fpu skipped=no_fpu\n");
    }

    fast = (unsigned char *)AllocMem(2 * 262144, MEMF_FAST | MEMF_CLEAR);
    if (fast) {
        t0 = now_ticks();
        for (i = 0; i < 32; i++)
            CopyMemQuick(fast, fast + 262144, 262144);
        t1 = now_ticks();
        us = microseconds(t1 - t0);
        thousandths(rate, 8388608ULL * 1000000ULL / (us ? us : 1) * 1000ULL / 1048576ULL);
        printf("AWBENCH mem test=fastcopy bytes=8388608 us=%lu mb_per_s=%s\n", us, rate);
        FreeMem(fast, 2 * 262144);
    } else {
        printf("AWBENCH mem test=fastcopy skipped=no_fast_ram\n");
    }

    chip = (unsigned char *)AllocMem(65536, MEMF_CHIP | MEMF_CLEAR);
    if (chip) {
        volatile ULONG *p;
        unsigned long pass, k;
        t0 = now_ticks();
        for (pass = 0; pass < 128; pass++)
            for (p = (volatile ULONG *)chip, k = 0; k < 65536 / 4; k++)
                *p++ = pass;
        t1 = now_ticks();
        us = microseconds(t1 - t0);
        thousandths(rate, 8388608ULL * 1000000ULL / (us ? us : 1) * 1000ULL / 1048576ULL);
        printf("AWBENCH mem test=chipwrite bytes=8388608 us=%lu mb_per_s=%s\n", us, rate);
        FreeMem(chip, 65536);
    }
}

static int create_file(const char *name, UBYTE *buffer)
{
    BPTR f;
    unsigned long done = 0, seed = 1, k;
    unsigned long long t0, t1;
    char rate[32];
    f = Open((STRPTR)name, MODE_OLDFILE);
    if (f) {
        LONG size;
        Seek(f, 0, OFFSET_END);
        size = Seek(f, 0, OFFSET_BEGINNING);
        Close(f);
        if ((unsigned long)size >= FILE_BYTES)
            return 1;
    }
    f = Open((STRPTR)name, MODE_NEWFILE);
    if (!f) {
        printf("AWBENCH error=cannot_create file=%s\n", name);
        return 0;
    }
    t0 = now_ticks();
    while (done < FILE_BYTES) {
        for (k = 0; k < BIG_REQUEST; k++) {
            seed = seed * 1103515245UL + 12345UL;
            buffer[k] = (UBYTE)(seed >> 16);
        }
        if (Write(f, buffer, BIG_REQUEST) != (LONG)BIG_REQUEST) {
            Close(f);
            printf("AWBENCH error=write_failed file=%s\n", name);
            return 0;
        }
        done += BIG_REQUEST;
    }
    Close(f);
    t1 = now_ticks();
    thousandths(rate, (unsigned long long)FILE_BYTES * 1000000ULL / (microseconds(t1 - t0) ? microseconds(t1 - t0) : 1) * 1000ULL / 1048576ULL);
    printf("AWBENCH disk test=create bytes=%lu us=%lu mb_per_s=%s (includes generating the data)\n",
           FILE_BYTES, microseconds(t1 - t0), rate);
    return 1;
}

static void read_pass(const char *name, UBYTE *buffer, unsigned long request, int seeks, unsigned long baseline)
{
    BPTR f = Open((STRPTR)name, MODE_OLDFILE);
    unsigned long blocks = FILE_BYTES / request, i, seed = 7, idle0, us, free_permille;
    unsigned long long t0, t1;
    char rate[32], cpu[32];
    if (!f) {
        printf("AWBENCH error=cannot_open file=%s\n", name);
        return;
    }
    idle0 = idle_count;
    t0 = now_ticks();
    for (i = 0; i < blocks; i++) {
        if (seeks) {
            unsigned long block;
            seed = seed * 1103515245UL + 12345UL;
            block = (seed >> 8) % blocks;
            Seek(f, (LONG)(block * request), OFFSET_BEGINNING);
        }
        if (Read(f, buffer, request) != (LONG)request) {
            printf("AWBENCH error=short_read file=%s\n", name);
            break;
        }
    }
    t1 = now_ticks();
    Close(f);
    us = microseconds(t1 - t0);
    thousandths(rate, (unsigned long long)request * i * 1000000ULL / (us ? us : 1) * 1000ULL / 1048576ULL);
    free_permille = baseline ? (unsigned long)((unsigned long long)(idle_count - idle0) * eclock_rate / (t1 - t0 ? t1 - t0 : 1) * 1000ULL / baseline) : 0;
    if (free_permille > 1000)
        free_permille = 1000;
    sprintf(cpu, "%lu.%lu", free_permille / 10, free_permille % 10);
    printf("AWBENCH disk test=read request=%lu pattern=%s bytes=%lu us=%lu mb_per_s=%s cpu_free_pct=%s\n",
           request, seeks ? "seek" : "seq", request * i, us, rate, cpu);
}

/* ------------------------------------------------------------------ */
/* Setup report: what the machine says about itself, printed as a block
 * the tester copies into the report, plus the fields only the tester knows. */

/* 68060 only: MOVEC PCR,D0 in supervisor mode (via exec Supervisor()). */
ULONG aw_read_pcr(void) __asm__("aw_read_pcr");
__asm__(
"	.text\n"
"	.even\n"
"	.globl aw_read_pcr\n"
"aw_read_pcr:\n"
"	.short 0x4e7a,0x0808\n"     /* movec pcr,d0 */
"	rte\n");

#ifndef AFF_68060
#define AFF_68060 (1 << 7)
#endif
#define ATTN_68080 (1 << 10)    /* set by the Vampire's 68080 */

static void bstr(char *out, int size, BSTR b)
{
    const UBYTE *s = (const UBYTE *)BADDR(b);
    int n = s ? s[0] : 0;
    if (n > size - 1)
        n = size - 1;
    if (n > 0)
        memcpy(out, s + 1, n);
    out[n > 0 ? n : 0] = 0;
}

static void library_version(char *out, int size, const char *name)
{
    struct Library *lib;
    Forbid();
    lib = (struct Library *)FindName(&SysBase->LibList, (STRPTR)name);
    if (lib)
        snprintf(out, size, "%s %u.%u", name, (unsigned)lib->lib_Version, (unsigned)lib->lib_Revision);
    else
        out[0] = 0;
    Permit();
}

static void dostype(char *out, ULONG t)
{
    int i;
    for (i = 0; i < 3; i++) {
        UBYTE c = (UBYTE)(t >> (24 - 8 * i));
        out[i] = c >= 32 && c < 127 ? (char)c : '?';
    }
    sprintf(out + 3, "\\%lu", (unsigned long)(t & 0xff));
}

static void report_system(void)
{
    UWORD attn = SysBase->AttnFlags;
    const char *cpu = attn & ATTN_68080 ? "68080" : attn & AFF_68060 ? "68060" : attn & AFF_68040 ? "68040" :
                      attn & AFF_68030 ? "68030" : attn & AFF_68020 ? "68020" : attn & AFF_68010 ? "68010" : "68000";
    const char *fpu = attn & ATTN_68080 ? "080" : attn & AFF_FPU40 ? (attn & AFF_68060 ? "060" : "040") :
                      attn & AFF_68882 ? "68882" : attn & AFF_68881 ? "68881" : "none";
    unsigned long chip = 0, fast = 0;
    struct MemHeader *mh;
    struct Library *version;
    char lib040[48], lib060[48], lib080[48];

    printf("AWBENCH-REPORT begin (copy from here to AWBENCH-REPORT end)\n");
    printf("system cpu=%s fpu=%s attn=%04x", cpu, fpu, (unsigned)attn);
    if ((attn & AFF_68060) && !(attn & ATTN_68080)) {
        ULONG pcr = Supervisor((APTR)aw_read_pcr);
        printf(" pcr=%08lx id=%04lx rev=%lu fpu_disabled=%lu", (unsigned long)pcr, (unsigned long)(pcr >> 16),
               (unsigned long)((pcr >> 8) & 0xff), (unsigned long)((pcr >> 1) & 1));
    }
    printf("\n");
    Forbid();
    for (mh = (struct MemHeader *)SysBase->MemList.lh_Head; mh->mh_Node.ln_Succ;
         mh = (struct MemHeader *)mh->mh_Node.ln_Succ) {
        unsigned long size = (unsigned long)mh->mh_Upper - (unsigned long)mh->mh_Lower;
        if (mh->mh_Attributes & MEMF_CHIP)
            chip += size;
        else
            fast += size;
    }
    Permit();
    printf("system chip_kb=%lu fast_kb=%lu chip_free_kb=%lu fast_free_kb=%lu\n", chip / 1024, fast / 1024,
           (unsigned long)AvailMem(MEMF_CHIP) / 1024, (unsigned long)AvailMem(MEMF_FAST) / 1024);
    version = OpenLibrary((STRPTR)"version.library", 0);
    printf("system exec=%u.%u kickstart_softver=%u dos=%u.%u workbench=",
           (unsigned)SysBase->LibNode.lib_Version, (unsigned)SysBase->LibNode.lib_Revision, (unsigned)SysBase->SoftVer,
           (unsigned)((struct Library *)DOSBase)->lib_Version, (unsigned)((struct Library *)DOSBase)->lib_Revision);
    if (version) {
        printf("%u.%u\n", (unsigned)version->lib_Version, (unsigned)version->lib_Revision);
        CloseLibrary(version);
    } else {
        printf("none\n");
    }
    library_version(lib040, sizeof lib040, "68040.library");
    library_version(lib060, sizeof lib060, "68060.library");
    library_version(lib080, sizeof lib080, "68080.library");
    printf("system fpu_support=%s%s%s%s%s%s\n", lib040, *lib040 && (*lib060 || *lib080) ? ", " : "", lib060,
           *lib060 && *lib080 ? ", " : "", lib080, *lib040 || *lib060 || *lib080 ? "" : "none resident");
    printf("system eclock_hz=%lu\n", (unsigned long)eclock_rate);
}

/* The drive the benchmark file is on: volume, file system, device, unit, buffers. */
static void report_disk(const char *name)
{
    BPTR lock = Lock((STRPTR)name, ACCESS_READ);
    struct InfoData *info = (struct InfoData *)AllocMem(sizeof(struct InfoData), MEMF_PUBLIC | MEMF_CLEAR);
    struct MsgPort *port;
    struct DosList *dl;
    char volume[64] = "?", device[64] = "?", handler[64] = "", type[16];
    if (!lock || !info) {
        printf("disk drive=%s info=unavailable (no such drive or directory?)\n", name);
        if (lock)
            UnLock(lock);
        if (info)
            FreeMem(info, sizeof(struct InfoData));
        return;
    }
    port = ((struct FileLock *)BADDR(lock))->fl_Task;
    if (Info(lock, info)) {
        if (info->id_VolumeNode)
            bstr(volume, sizeof volume, ((struct DosList *)BADDR(info->id_VolumeNode))->dol_Name);
        dostype(type, (ULONG)info->id_DiskType);
        printf("disk drive=%s volume=%s disktype=%s block_bytes=%ld blocks=%ld used=%ld\n", name, volume, type,
               (long)info->id_BytesPerBlock, (long)info->id_NumBlocks, (long)info->id_NumBlocksUsed);
    }
    dl = LockDosList(LDF_DEVICES | LDF_READ);
    while ((dl = NextDosEntry(dl, LDF_DEVICES)) != NULL) {
        BPTR startup;
        struct FileSysStartupMsg *fssm;
        if (dl->dol_Task != port)
            continue;
        bstr(device, sizeof device, dl->dol_Name);
        startup = dl->dol_misc.dol_handler.dol_Startup;
        fssm = (struct FileSysStartupMsg *)BADDR(startup);
        if ((ULONG)startup > 64 && TypeOfMem(fssm)) {
            ULONG *env = (ULONG *)BADDR(fssm->fssm_Environ);
            bstr(handler, sizeof handler, fssm->fssm_Device);
            printf("disk dosdevice=%s: exec_device=%s unit=%lu", device, handler, (unsigned long)fssm->fssm_Unit);
            if (env && TypeOfMem(env) && env[DE_TABLESIZE] >= DE_MASK) {
                printf(" buffers=%lu maxtransfer=0x%lx mask=0x%lx", (unsigned long)env[DE_NUMBUFFERS],
                       (unsigned long)env[DE_MAXTRANSFER], (unsigned long)env[DE_MASK]);
                if (env[DE_TABLESIZE] >= DE_DOSTYPE) {
                    dostype(type, env[DE_DOSTYPE]);
                    printf(" dostype=%s", type);
                }
                printf(" bufmemtype=0x%lx", (unsigned long)env[DE_MEMBUFTYPE]);
            }
            printf("\n");
        } else {
            printf("disk dosdevice=%s: exec_device=unknown\n", device);
        }
        break;
    }
    UnLockDosList(LDF_DEVICES | LDF_READ);
    UnLock(lock);
    FreeMem(info, sizeof(struct InfoData));
}

static void report_tester(void)
{
    printf("tester card=<fill in: accelerator name, e.g. Blizzard 1240, Apollo 1260, PiStorm>\n");
    printf("tester clock_mhz=<fill in: CPU clock>\n");
    printf("tester medium=<fill in: internal IDE hard disk / CF card and adapter / other; card or disk model>\n");
    printf("tester filesystem=<fill in if known: FFS, PFS3, SFS and version; AddBuffers you use>\n");
    printf("AWBENCH-REPORT end\n");
}

static void disk_tests(const char *name)
{
    UBYTE *buffer = (UBYTE *)AllocMem(BIG_REQUEST, MEMF_ANY);
    unsigned long baseline;
    if (!buffer) {
        printf("AWBENCH error=no_memory\n");
        return;
    }
    if (create_file(name, buffer)) {
        if (!idle_start())
            printf("AWBENCH note=no_idle_task (cpu_free_pct is 0)\n");
        baseline = idle_rate();
        printf("AWBENCH idle counts_per_s=%lu\n", baseline);
        read_pass(name, buffer, 16384, 0, baseline);
        read_pass(name, buffer, BIG_REQUEST, 0, baseline);
        read_pass(name, buffer, 16384, 1, baseline);
        read_pass(name, buffer, BIG_REQUEST, 1, baseline);
        idle_end();
    }
    FreeMem(buffer, BIG_REQUEST);
}

int main(void)
{
    /* AmigaDOS argument parsing (ReadArgs), so the shell's own rules apply:
     * awbench cpu, awbench disk DH1:awbench.dat, awbench all DH1:awbench.dat */
    LONG values[2] = {0, 0};
    struct RDArgs *rd = ReadArgs((STRPTR)"MODE/A,FILE", values, NULL);
    const char *mode = rd ? (const char *)values[0] : "";
    const char *file = rd ? (const char *)values[1] : NULL;
    int status = 0;
    struct Process *self = (struct Process *)FindTask(NULL);
    APTR window = self->pr_WindowPtr;
    if (strcmp(mode, "cpu") && (!file || (strcmp(mode, "disk") && strcmp(mode, "all")))) {
        printf("usage: awbench cpu | awbench disk FILE | awbench all FILE\n"
               "FILE is created (8 MB) on the drive to test if missing; delete it afterwards.\n");
        if (rd)
            FreeArgs(rd);
        return 5;
    }
    /* a missing drive or a full disk fails with a message instead of a requester
     * (the benchmark may run with no screen to answer one) */
    self->pr_WindowPtr = (APTR)-1;
    timer_port = CreateMsgPort();
    timer_request = timer_port ? (struct timerequest *)CreateIORequest(timer_port, sizeof *timer_request) : NULL;
    if (!timer_request || OpenDevice((STRPTR)TIMERNAME, UNIT_MICROHZ, (struct IORequest *)timer_request, 0)) {
        printf("AWBENCH error=no_timer_device\n");
        self->pr_WindowPtr = window;
        return 20;
    }
    TimerBase = timer_request->tr_node.io_Device;
    {
        struct EClockVal v;
        eclock_rate = ReadEClock(&v);
    }
    printf("AWBENCH start version=2\n");
    report_system();
    if (file) {
        /* the drive of FILE: lock its directory (the file may not exist yet) */
        char dir[256];
        const char *cut = strrchr(file, '/');
        size_t n;
        if (!cut)
            cut = strchr(file, ':') ? strchr(file, ':') + 1 : file;
        n = (size_t)(cut - file);
        if (n >= sizeof dir)
            n = sizeof dir - 1;
        memcpy(dir, file, n);
        dir[n] = 0;
        report_disk(dir);
    }
    report_tester();
    if (!strcmp(mode, "cpu") || !strcmp(mode, "all"))
        cpu_tests();
    if (!strcmp(mode, "disk") || !strcmp(mode, "all"))
        disk_tests(file);
    printf("AWBENCH end\n");
    CloseDevice((struct IORequest *)timer_request);
    DeleteIORequest((struct IORequest *)timer_request);
    DeleteMsgPort(timer_port);
    FreeArgs(rd);
    self->pr_WindowPtr = window;
    return status;
}
