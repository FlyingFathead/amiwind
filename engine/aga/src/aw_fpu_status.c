/* SPDX-License-Identifier: GPL-2.0-or-later
 * FPU support status (ENGINE-FPSP-MISSING-31). A real 68040 or 68060 traps
 * on FPU instructions it does not implement and on denormalized operands; the
 * user's own 68040.library / 68060.library handles those traps. The builder's
 * --amiga-libs option installs it and AmiWindFPU opens it at boot (see
 * docs/FPU_SUPPORT_LIBRARY.md). At start-up this prints one console line, and
 * `dbg fpu` (aw_fpu_status) prints it again. Residency is read the same way
 * as the boot check does: the library's node in SysBase->LibList, found by
 * name under Forbid; nothing is opened or loaded from disk. */
#include "quakedef.h"
#ifdef AMIGA
#include <proto/exec.h>
#include <exec/execbase.h>
#endif

#define AW_ATTN_68040 (1u<<3)
#define AW_ATTN_68060 (1u<<7)

/* One status line, without a newline. attn = SysBase->AttnFlags; library =
 * resident support library name or NULL. */
void AW_FpuStatusFormat(char *out, int size, unsigned attn, const char *library, int version, int revision)
{
    const char *cpu = (attn & AW_ATTN_68060) ? "68060" : (attn & AW_ATTN_68040) ? "68040" : NULL;
    if (library)
        snprintf(out, size, "FPU support: %s v%d.%d active%s%s%s", library, version, revision,
                 cpu ? " (CPU " : "", cpu ? cpu : "", cpu ? ")" : "");
    else if (cpu)
        snprintf(out, size, "FPU support: none (CPU %s): rare FPU cases may crash on a real 68040/68060; "
                 "see the docs, FPU support library", cpu);
    else
        snprintf(out, size, "FPU support: none (no 68040/68060 reported)");
}

/* Kickstart 3.1 reports a 68060 as a 68040 until 68060.library sets
 * AFF_68060, so the CPU named here is AttnFlags' view. */
static void probe(unsigned *attn, char *library, int size, int *version, int *revision)
{
    *attn = 0; library[0] = 0; *version = *revision = 0;
#ifdef AMIGA
    {
        static const char *const names[2] = {"68060.library", "68040.library"};
        struct Library *found = NULL;
        int i;
        *attn = SysBase->AttnFlags;
        Forbid();
        for (i = 0; i < 2 && !found; i++) {
            found = (struct Library *)FindName(&SysBase->LibList, (CONST_STRPTR)names[i]);
            if (found) {
                Q_strncpy(library, (char *)names[i], size - 1);
                library[size - 1] = 0;
                *version = found->lib_Version;
                *revision = found->lib_Revision;
            }
        }
        Permit();
    }
#else
    (void)size;
#endif
}

static void fpu_status_command(void)
{
    char line[160], library[32];
    unsigned attn;
    int version, revision;
    probe(&attn, library, sizeof library, &version, &revision);
    AW_FpuStatusFormat(line, sizeof line, attn, library[0] ? library : NULL, version, revision);
    Con_Printf("%s\n", line);
}

void AW_FpuStatusInit(void)
{
    Cmd_AddCommand("aw_fpu_status", fpu_status_command);
    fpu_status_command();
}
