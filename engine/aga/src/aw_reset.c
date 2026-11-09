/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_reset.c: the game-state reset registry (aw_reset.h). No engine dependencies (host-tested). */
#include <string.h>
#include "aw_reset.h"

static struct {
    const char *name;
    aw_reset_fn reset;
    aw_reset_digest_fn digest;
    unsigned long boot;
} modules[AW_RESET_MODULES];
static int count,booted;

int AW_ResetRegister(const char *name, aw_reset_fn reset, aw_reset_digest_fn digest)
{
    int i;
    if (!reset)
        return 0;
    for (i = 0; i < count; i++)
        if (modules[i].reset == reset) {
            modules[i].name = name;modules[i].digest = digest;
            return 1;
        }
    if (count >= AW_RESET_MODULES)
        return 0;
    modules[count].name = name;modules[count].reset = reset;modules[count].digest = digest;modules[count].boot = 0;
    count++;
    return 1;
}
int AW_ResetModules(void) {return count;}
int AW_ResetAll(int new_game)
{
    int i;
    for (i = 0; i < count; i++)
        modules[i].reset(new_game);
    return count;
}
unsigned long AW_ResetModuleDigest(int i)
{
    if (i < 0 || i >= count)
        return (unsigned long)-1;
    return modules[i].digest ? modules[i].digest() & 0xffffffffUL : 0;
}
const char *AW_ResetModuleName(int i) {return i < 0 || i >= count ? NULL : modules[i].name ? modules[i].name : "?";}
unsigned long AW_ResetHash(unsigned long seed, const void *bytes, unsigned long size)
{
    const unsigned char *p = (const unsigned char *)bytes;
    unsigned long h = seed & 0xffffffffUL;
    while (p && size--) {
        h ^= *p++;
        h = (h * 16777619UL) & 0xffffffffUL;
    }
    return h;
}
void AW_ResetMarkBoot(void)
{
    int i;
    for (i = 0; i < count; i++)
        modules[i].boot = AW_ResetModuleDigest(i);
    booted = 1;
}
int AW_ResetCompareBoot(char *out, int capacity)
{
    int i, differ = 0, used = 0, n;
    if (capacity > 0)
        out[0] = 0;
    for (i = 0; i < count; i++) {
        if (!modules[i].digest || AW_ResetModuleDigest(i) == modules[i].boot)
            continue;
        differ++;
        n = (int)strlen(AW_ResetModuleName(i));
        if (out && used + n + 3 < capacity) {
            if (used) {out[used++] = ',';out[used++] = ' ';}
            memcpy(out + used, AW_ResetModuleName(i), n);used += n;out[used] = 0;
        }
    }
    return booted ? differ : -1;
}
