/* Engine review fixes (v0.0.35): pak header checks, va/COM_FileBase bounds,
 * anglemod range, Q_GammaPow against pow. Host build with common.c, crc.c
 * and mathlib.c. */
#include "quakedef.h"
#include <setjmp.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <math.h>

/* Same layout as common.c's in-memory pak records. */
typedef struct { char name[MAX_QPATH]; int filepos, filelen; } packfile_t;
typedef struct pack_s { char filename[MAX_OSPATH]; int handle; int numfiles; packfile_t *files; } pack_t;
pack_t *COM_LoadPackFile(char *packfile);
int LongNoSwap(int l);

static jmp_buf error_jump;
static char error_text[512];
static FILE *handles[4];
static byte hunk[1 << 16];
static int hunk_used;

void Sys_Error(char *error, ...)
{
    va_list ap;
    va_start(ap, error);
    vsnprintf(error_text, sizeof(error_text), error, ap);
    va_end(ap);
    longjmp(error_jump, 1);
}
void Con_Printf(char *fmt, ...) { (void)fmt; }
void Con_DPrintf(char *fmt, ...) { (void)fmt; }
void *Hunk_AllocName(int size, char *name)
{
    void *p;
    (void)name;
    if (size < 0 || hunk_used + size > (int)sizeof(hunk)) { printf("hunk overflow %d\n", size); exit(40); }
    p = hunk + hunk_used;
    hunk_used += (size + 7) & ~7;
    return p;
}
void *Hunk_Alloc(int size) { return Hunk_AllocName(size, "x"); }
int Sys_FileOpenRead(char *path, int *hndl)
{
    FILE *f = fopen(path, "rb");
    long n;
    if (!f) { *hndl = -1; return -1; }
    handles[0] = f;
    *hndl = 0;
    fseek(f, 0, SEEK_END);
    n = ftell(f);
    fseek(f, 0, SEEK_SET);
    return (int)n;
}
int Sys_FileRead(int h, void *dest, int count) { return (int)fread(dest, 1, count, handles[h]); }
void Sys_FileSeek(int h, int position) { fseek(handles[h], position, SEEK_SET); }

static void put32(byte *p, int v)
{
    p[0] = v; p[1] = v >> 8; p[2] = v >> 16; p[3] = v >> 24;
}

/* A pak with one 16-byte entry "a.txt"; the header fields can be bent. */
static int pak_case(const char *path, int dirofs, int dirlen, int filepos, int filelen,
                    int truncate, const char *expect)
{
    byte data[12 + 16 + 64];
    FILE *f;
    pack_t *pack;
    int size = sizeof(data) - truncate;
    memset(data, 0, sizeof(data));
    memcpy(data, "PACK", 4);
    put32(data + 4, dirofs);
    put32(data + 8, dirlen);
    memcpy(data + 28, "a.txt", 5);
    put32(data + 28 + 56, filepos);
    put32(data + 28 + 60, filelen);
    f = fopen(path, "wb");
    if (!f) return 50;
    fwrite(data, 1, size, f);
    fclose(f);
    error_text[0] = 0;
    if (setjmp(error_jump)) {
        fclose(handles[0]);
        if (!expect) { printf("unexpected error: %s\n", error_text); return 51; }
        if (!strstr(error_text, expect)) { printf("wrong error: %s\n", error_text); return 52; }
        return 0;
    }
    pack = COM_LoadPackFile((char *)path);
    fclose(handles[0]);
    if (expect) { printf("accepted a bad pak, wanted: %s\n", expect); return 53; }
    if (!pack || pack->numfiles != 1 || strcmp(pack->files[0].name, "a.txt") ||
        pack->files[0].filepos != filepos || pack->files[0].filelen != filelen)
        return 54;
    return 0;
}

int main(int argc, char **argv)
{
    const char *path = argc > 1 ? argv[1] : "review.pak";
    int r, i, g10;
    char out[COM_FILEBASE_SIZE + 8], longname[200], *s;
    LittleLong = LongNoSwap;
    /* 12-byte header, then 12 bytes of data at 12, directory (64 bytes) at 28;
     * the file is 12 + 16 + 64 = 92 bytes long. */
    if ((r = pak_case(path, 28, 64, 12, 16, 0, NULL))) return r;
    if ((r = pak_case(path, 28, -64, 12, 16, 0, "bad directory length"))) return 100 + r;
    if ((r = pak_case(path, 28, 63, 12, 16, 0, "bad directory length"))) return 200 + r;
    if ((r = pak_case(path, 28, 64 * 4096, 12, 16, 0, "files"))) return 300 + r;
    if ((r = pak_case(path, 92, 64, 12, 16, 0, "outside the file"))) return 400 + r;
    if ((r = pak_case(path, -4, 64, 12, 16, 0, "outside the file"))) return 500 + r;
    if ((r = pak_case(path, 28, 64, 12, 16, 8, "outside the file"))) return 600 + r;
    if ((r = pak_case(path, 28, 64, 80, 16, 0, "lies outside"))) return 700 + r;
    if ((r = pak_case(path, 28, 64, 12, -1, 0, "lies outside"))) return 800 + r;
    if ((r = pak_case(path, 28, 64, -12, 16, 0, "lies outside"))) return 900 + r;
    if ((r = pak_case(path, 28, 64, 12, 0x7fffffff, 0, "lies outside"))) return 1000 + r;
    if ((r = pak_case(path, 28, 64, 12, 16, 85, "too short"))) return 1100 + r;
    remove(path);

    /* va: bounded to its 1024-byte buffer. */
    memset(longname, 'x', sizeof(longname) - 1);
    longname[sizeof(longname) - 1] = 0;
    s = va("%s%s%s%s%s%s%s", longname, longname, longname, longname, longname, longname, longname);
    if (strlen(s) != 1023) return 1200;

    /* COM_FileBase: base name, bounded, no walk before the start. */
    memset(out, '#', sizeof(out));
    COM_FileBase("progs/player.mdl", out);
    if (strcmp(out, "player")) return 1300;
    COM_FileBase("maps/sub/bm019.bsp", out);
    if (strcmp(out, "bm019")) return 1301;
    COM_FileBase("noslash.bsp", out);
    if (strcmp(out, "noslash")) return 1302;
    COM_FileBase("progs/.mdl", out);
    if (strcmp(out, "?model?")) return 1303;
    memset(out, '#', sizeof(out));
    sprintf(longname, "progs/%s.mdl", "abcdefghijabcdefghijabcdefghijabcdefghij");
    COM_FileBase(longname, out);
    if (strlen(out) != COM_FILEBASE_SIZE - 1 || out[COM_FILEBASE_SIZE] != '#') return 1304;

    /* anglemod: always [0,360), NaN and huge values give 0. */
    if (anglemod(-360) != 0 || anglemod(360) != 0 || anglemod(-720) != 0) return 1400;
    if (fabs(anglemod(-90) - 270) > 1e-3 || fabs(anglemod(450) - 90) > 1e-3) return 1401;
    if (anglemod(-1e-8f) < 0 || anglemod(-1e-8f) >= 360) return 1402;
    if (anglemod(NAN) != 0 || anglemod(1e30f) != 0 || anglemod(-1e30f) != 0) return 1403;

    /* Q_GammaPow: the gamma table it builds equals the pow one. */
    for (g10 = 1; g10 <= 40; g10++) {
        double g = g10 / 10.0;
        for (i = 0; i < 256; i++) {
            double x = (i + 0.5) / 255.5;
            int a = 255 * pow(x, g) + 0.5, b = 255 * Q_GammaPow(x, g) + 0.5;
            if (fabs(Q_GammaPow(x, g) - pow(x, g)) > 1e-9 || a != b) {
                printf("gamma %g entry %d: %d vs %d\n", g, i, a, b);
                return 1500;
            }
        }
    }
    return 0;
}
