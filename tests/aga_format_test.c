/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_format.c (ENGINE-FPSP-MISSING-31): the engine's own text/number
 * conversion against the host C library. Integer and string printf output
 * must be identical; float output identical for float-precision values and
 * within one unit of the last printed digit for arbitrary doubles; Q_strtod
 * correctly rounded (equal to strtod) up to 15 significant digits; Q_sscanf
 * and Q_fscanf return the same counts and values for the engine's formats. */
#include <assert.h>
#include <limits.h>
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_format.h"

static int failures;
static void same_text(const char *what, const char *mine, const char *libc)
{
    if (strcmp(mine, libc)) {
        if (failures < 40)
            printf("MISMATCH %s: mine \"%s\" libc \"%s\"\n", what, mine, libc);
        failures++;
    }
}

static void check_int(const char *format, long long v)
{
    char a[128], b[128], what[64];
    int na, nb;
    if (strstr(format, "ll")) {
        na = Q_snprintf(a, sizeof a, format, v);
        nb = snprintf(b, sizeof b, format, v);
    } else if (strchr(format, 'l')) {
        na = Q_snprintf(a, sizeof a, format, (long)v);
        nb = snprintf(b, sizeof b, format, (long)v);
    } else {
        na = Q_snprintf(a, sizeof a, format, (int)v);
        nb = snprintf(b, sizeof b, format, (int)v);
    }
    snprintf(what, sizeof what, "%s %lld", format, v);
    same_text(what, a, b);
    assert(na == nb);
}

static void check_float(const char *format, double v, int exact)
{
    char a[400], b[400], what[96];
    if (fabs(v) >= 1e18 && strpbrk(format, "fF") && !isinf(v))
        return;     /* documented: %f of 1e18 and above prints in %e form */
    Q_snprintf(a, sizeof a, format, v);
    snprintf(b, sizeof b, format, v);
    snprintf(what, sizeof what, "%s %.17g", format, v);
    if (exact || !strcmp(a, b)) {
        same_text(what, a, b);
        return;
    }
    {   /* arbitrary doubles: within one unit of the last printed digit */
        double x = strtod(a, NULL), y = strtod(b, NULL), unit;
        const char *dot = strchr(b, '.'), *e = strpbrk(b, "eE");
        int decimals = 0;
        if (dot)
            for (dot++; *dot >= '0' && *dot <= '9'; dot++)
                decimals++;
        unit = pow(10, -decimals);
        if (e)
            unit *= pow(10, atoi(e + 1));
        if (!(fabs(x - y) <= unit * 1.0001 + fabs(y) * 1e-15))
            same_text(what, a, b);
    }
}

static unsigned long seed = 12345;
static unsigned long next(void)
{
    seed = seed * 1103515245UL + 12345UL;
    return (seed >> 8) & 0xffffff;
}

static void check_strtod(const char *s, int exact)
{
    char *ea, *eb;
    double a = Q_strtod(s, &ea), b = strtod(s, &eb);
    if (ea - s != eb - s || (exact ? a != b || signbit(a) != signbit(b) : fabs(a - b) > fabs(b) * 2.3e-16)) {
        if (failures < 40)
            printf("MISMATCH strtod \"%s\": %.17g/%d vs %.17g/%d\n", s, a, (int)(ea - s), b, (int)(eb - s));
        failures++;
    }
}

typedef struct { char s1[96], s2[96], s3[96]; int i1, i2, i3, i4, i5; unsigned u; long lx; float f[12]; char c; } scan_t;

static void compare_scan(const char *what, int ra, int rb, scan_t *a, scan_t *b)
{
    if (ra != rb || memcmp(a, b, sizeof *a)) {
        if (failures < 40)
            printf("MISMATCH scan %s: %d vs %d\n", what, ra, rb);
        failures++;
    }
}

static void scans(void)
{
    static const char *scene[] = {
        "seyda balmora 123 1.5 -2.25 3e2 0 0.125 -7 8 9.75 10 11 label text here",
        "seyda balmora 123 1.5 -2.25",
        "",
        "   ",
        "a b x 1 2",
        "seyda balmora 4294967295 -0 +.5 5. 1e-3 2E+2 .25 -1e1 3 4 5 a",
    };
    static const char *spots[] = {
        "3 1 77 balmora -20088.5 -14638 113 -3 Mages Guild door",
        "1 0 0 seyda 1 2 3 4 x",
        "1 0 0 seyda 1 2 3",
    };
    static const char *models[] = {"maps/x.bsp 12 34 56 1a2b", "maps/x.bsp 12 34 56 1a2b q", "maps/x.bsp 1 2"};
    scan_t a, b;
    int i, ra, rb, na, nb;
    for (i = 0; i < (int)(sizeof scene / sizeof *scene); i++) {
        memset(&a, 0, sizeof a); memset(&b, 0, sizeof b);
        ra = Q_sscanf(scene[i], "%15s %15s %u %f %f %f %f %f %f %f %f %f %f %95[^\r\n]", a.s1, a.s2, &a.u,
            &a.f[0], &a.f[1], &a.f[2], &a.f[3], &a.f[4], &a.f[5], &a.f[6], &a.f[7], &a.f[8], &a.f[9], a.s3);
        rb = sscanf(scene[i], "%15s %15s %u %f %f %f %f %f %f %f %f %f %f %95[^\r\n]", b.s1, b.s2, &b.u,
            &b.f[0], &b.f[1], &b.f[2], &b.f[3], &b.f[4], &b.f[5], &b.f[6], &b.f[7], &b.f[8], &b.f[9], b.s3);
        compare_scan(scene[i], ra, rb, &a, &b);
        memset(&a, 0, sizeof a); memset(&b, 0, sizeof b);
        ra = Q_sscanf(scene[i], "%15s %15s %f %f %f %f %f %f %f %c", a.s1, a.s2,
            &a.f[0], &a.f[1], &a.f[2], &a.f[3], &a.f[4], &a.f[5], &a.f[6], &a.c);
        rb = sscanf(scene[i], "%15s %15s %f %f %f %f %f %f %f %c", b.s1, b.s2,
            &b.f[0], &b.f[1], &b.f[2], &b.f[3], &b.f[4], &b.f[5], &b.f[6], &b.c);
        compare_scan(scene[i], ra, rb, &a, &b);
    }
    for (i = 0; i < (int)(sizeof spots / sizeof *spots); i++) {
        memset(&a, 0, sizeof a); memset(&b, 0, sizeof b);
        na = nb = -1;
        ra = Q_sscanf(spots[i], "%d %d %u %15s %f %f %f %f %95[^\r\n]%n", &a.i1, &a.i2, &a.u, a.s1,
            &a.f[0], &a.f[1], &a.f[2], &a.f[3], a.s2, &na);
        rb = sscanf(spots[i], "%d %d %u %15s %f %f %f %f %95[^\r\n]%n", &b.i1, &b.i2, &b.u, b.s1,
            &b.f[0], &b.f[1], &b.f[2], &b.f[3], b.s2, &nb);
        compare_scan(spots[i], ra, rb, &a, &b);
        assert(na == nb);
    }
    for (i = 0; i < 3; i++) {
        memset(&a, 0, sizeof a); memset(&b, 0, sizeof b);
        ra = Q_sscanf(models[i], "%63s %d %d %d %lx %c", a.s1, &a.i1, &a.i2, &a.i3, &a.lx, &a.c);
        rb = sscanf(models[i], "%63s %d %d %d %lx %c", b.s1, &b.i1, &b.i2, &b.i3, &b.lx, &b.c);
        compare_scan(models[i], ra, rb, &a, &b);
    }
    {
        static const char *more[][2] = {
            {"AWG1 %d %c", "AWG1 25"}, {"AWG1 %d %c", "AWG1 25 x"}, {"AWG1 %d %c", "AWGX 25"},
            {"%d.%d.%d.%d:%d", "192.168.1.20:26000"}, {"%d %d %d", "255 210 140"}, {"%d %d %d", "255 x"},
            {"%63s %d %d", "balmora 3 7"}, {"%d %31s %63s%n", "4 intro intro/mw_intro.awv"},
            {"%7s %d %f %d %f", "AWR1 3 0.5 9 -12.75"}, {"%i %i %i", "0x1f 017 -9"}, {"%x %o", "ff 17"},
            {"%f %f %f", "1 2"}, {"%f", "-"}, {"%d%%%d", "3%4"},
        };
        for (i = 0; i < (int)(sizeof more / sizeof *more); i++) {
            memset(&a, 0, sizeof a); memset(&b, 0, sizeof b);
            na = nb = -1;
            if (strstr(more[i][0], "%f")) {
                ra = Q_sscanf(more[i][1], more[i][0], &a.f[0], &a.f[1], &a.f[2], &a.f[3], &a.f[4]);
                rb = sscanf(more[i][1], more[i][0], &b.f[0], &b.f[1], &b.f[2], &b.f[3], &b.f[4]);
                if (!strcmp(more[i][0], "%7s %d %f %d %f")) {
                    memset(&a, 0, sizeof a); memset(&b, 0, sizeof b);
                    ra = Q_sscanf(more[i][1], more[i][0], a.s1, &a.i1, &a.f[0], &a.i2, &a.f[1]);
                    rb = sscanf(more[i][1], more[i][0], b.s1, &b.i1, &b.f[0], &b.i2, &b.f[1]);
                } else if (!strcmp(more[i][0], "%f %d")) {
                    memset(&a, 0, sizeof a); memset(&b, 0, sizeof b);
                    ra = Q_sscanf(more[i][1], more[i][0], &a.f[0], &a.i1);
                    rb = sscanf(more[i][1], more[i][0], &b.f[0], &b.i1);
                }
            } else if (strstr(more[i][0], "%63s") || strstr(more[i][0], "%31s")) {
                if (more[i][0][1] == 'd') {
                    ra = Q_sscanf(more[i][1], more[i][0], &a.i1, a.s1, a.s2, &na);
                    rb = sscanf(more[i][1], more[i][0], &b.i1, b.s1, b.s2, &nb);
                } else {
                    ra = Q_sscanf(more[i][1], more[i][0], a.s1, &a.i1, &a.i2);
                    rb = sscanf(more[i][1], more[i][0], b.s1, &b.i1, &b.i2);
                }
            } else if (strstr(more[i][0], "%c")) {
                ra = Q_sscanf(more[i][1], more[i][0], &a.i1, &a.c);
                rb = sscanf(more[i][1], more[i][0], &b.i1, &b.c);
            } else if (!strcmp(more[i][0], "%x %o")) {
                ra = Q_sscanf(more[i][1], more[i][0], &a.u, &a.i1);
                rb = sscanf(more[i][1], more[i][0], &b.u, &b.i1);
            } else {
                ra = Q_sscanf(more[i][1], more[i][0], &a.i1, &a.i2, &a.i3, &a.i4, &a.i5);
                rb = sscanf(more[i][1], more[i][0], &b.i1, &b.i2, &b.i3, &b.i4, &b.i5);
            }
            compare_scan(more[i][1], ra, rb, &a, &b);
            assert(na == nb);
        }
    }
    {   /* an incomplete exponent is left unread (string input) */
        float x = 0;
        int n = 0;
        char rest[8] = "";
        assert(Q_sscanf("1e+ 5", "%f%n%7s", &x, &n, rest) == 2 && x == 1 && n == 1 && !strcmp(rest, "e+"));
    }
    {   /* Q_fscanf on a file, as the harvest table and save files use it */
        FILE *f = tmpfile();
        char label[64], word[8];
        float x, y;
        int n, m;
        assert(f);
        fputs("AWH4 3 4 5\n 1.25 -2e-3\tLabel with spaces\r\n77", f);
        rewind(f);
        assert(Q_fscanf(f, "%7s %d %d %d", word, &n, &m, &n) == 4 && !strcmp(word, "AWH4") && n == 5 && m == 4);
        assert(Q_fscanf(f, " %f", &x) == 1 && x == 1.25f);
        assert(Q_fscanf(f, " %f", &y) == 1 && y == -2e-3f);
        assert(fgetc(f) == '\t' && Q_fscanf(f, "%63[^\r\n]", label) == 1 && !strcmp(label, "Label with spaces"));
        assert(Q_fscanf(f, "%d", &n) == 1 && n == 77);
        assert(Q_fscanf(f, "%d", &n) == EOF);
        fclose(f);
    }
}

int main(void)
{
    static const char *int_formats[] = {"%d", "%5d", "%-5d|", "%05d", "%+d", "% d", "%.3d", "%5.3d", "%.0d",
        "%x", "%X", "%#x", "%#X", "%#o", "%o", "%u", "%i", "%08x", "%-8x|", "%ld", "%lu", "%lx", "%5ld",
        "%02ld", "%lld", "%llu", "%llx", "%hd", "%hhu", "%#.0o", "[%3d]", "%+05d", "% 05d", "%.10d"};
    static const long long ints[] = {0, 1, -1, 7, 42, -42, 99, 100, 255, 256, 65535, 65536, -65536,
        123456789, INT_MAX, INT_MIN, 4000000000LL, -9000000000LL};
    static const char *float_formats[] = {"%f", "%.0f", "%.1f", "%.2f", "%5.1f", "%4.1f", "%4.2f", "%.3f",
        "%.5f", "%.6f", "%g", "%.3g", "%10.4f", "%-10.2f|", "%+.2f", "% .1f", "%e", "%.3e", "%E", "%G",
        "%#.0f", "%#g", "%010.3f", "%.12f", "%.0e", "%12.4e", "%.1g", "%.10g", "%-12g|", "%f%%"};
    static const double values[] = {0.0, -0.0, 1, -1, 0.5, 1.5, 2.5, -2.5, 0.1, 0.125, 0.375, 3.14159,
        -2.71828, 123456.789, 1e-5, 1e10, 9.9999999, 9.5, 99.95, 0.0001234, 1e17, 255.0, 1.0 / 3,
        192.0, 0.7f, 0.00333333333f, -20088.0f, 1.25e-3, 6.02e23, 1e-30, 4e9, 1e15 + 0.5, 0.05, 0.95};
    static const char *strings[] = {"0", "1", "-1", "3.14159", "1e-5", "1E10", "-0.0", "+.5", "5.",
        "0.000123", "123456789012345", "1e308", "1e-300", "  42", "1e", "1e+", "abc", ".", "-", "",
        "2.5e-3x", "0.1", "0.7", "192", "-20088.5", "1e22", "9007199254740993", "1e-400", "1e400"};
    char a[256], b[256];
    int i, j, k;

    for (i = 0; i < (int)(sizeof int_formats / sizeof *int_formats); i++)
        for (j = 0; j < (int)(sizeof ints / sizeof *ints); j++)
            check_int(int_formats[i], ints[j]);
    /* strings, characters, star width and precision, %%, %n, truncation */
    Q_snprintf(a, sizeof a, "[%s|%10s|%-10s|%.2s|%c|%3c|%-3c|%%|%*d|%-*d|%.*s|%*.*f]", "abc", "abc", "abc", "abc",
               'x', 'y', 'z', 6, 42, 6, 42, 3, "abcdef", 9, 2, 3.14159);
    snprintf(b, sizeof b, "[%s|%10s|%-10s|%.2s|%c|%3c|%-3c|%%|%*d|%-*d|%.*s|%*.*f]", "abc", "abc", "abc", "abc",
             'x', 'y', 'z', 6, 42, 6, 42, 3, "abcdef", 9, 2, 3.14159);
    same_text("strings", a, b);
    {
        int na = 0, nb = 0;
        Q_snprintf(a, sizeof a, "abc%ndef", &na);
        snprintf(b, sizeof b, "abc%ndef", &nb);
        same_text("%n", a, b);
        assert(na == 3 && nb == 3);
        assert(Q_snprintf(a, 5, "%s", "abcdefgh") == 8 && !strcmp(a, "abcd"));
        assert(Q_snprintf(NULL, 0, "%d", 12345) == 5);
        assert(Q_snprintf(a, 1, "xyz") == 3 && !a[0]);
    }
    for (i = 0; i < (int)(sizeof float_formats / sizeof *float_formats); i++)
        for (j = 0; j < (int)(sizeof values / sizeof *values); j++)
            check_float(float_formats[i], values[j],
                        fabs(values[j]) < 1e16 && fabs(values[j]) > 1e-10 && !strstr(float_formats[i], "12f"));
    check_float("%f", INFINITY, 1);
    check_float("%5.1f", -INFINITY, 1);
    check_float("%F", INFINITY, 1);
    check_float("%e", NAN, 1);
    /* float-precision values (what the engine prints): identical in %f */
    for (k = 0; k < 20000; k++) {
        float v = (float)((double)next() / 0x1000000 * pow(10, (int)(next() % 9) - 3) * (next() & 1 ? 1 : -1));
        check_float("%.6f", v, 1);
        check_float("%5.1f", v, 1);
        check_float("%.2f", v, 1);
        check_float("%g", v, 0);
        check_float("%e", v, 0);
    }
    /* arbitrary doubles: within one unit of the last digit */
    for (k = 0; k < 20000; k++) {
        double v = ((double)next() * 0x1000000 + next()) / 281474976710656.0 * pow(10, (int)(next() % 40) - 20);
        check_float("%.10g", v, 0);
        check_float("%.8e", v, 0);
        if (v < 1e15)
            check_float("%.9f", v, 0);
    }
    for (i = 0; i < (int)(sizeof strings / sizeof *strings); i++)
        check_strtod(strings[i], strcmp(strings[i], "9007199254740993") && strcmp(strings[i], "1e308") && strcmp(strings[i], "1e-300"));
    for (k = 0; k < 50000; k++) {   /* up to 15 significant digits, decimal exponent within -22..15: exact */
        char s[64];
        int digits = 1 + (int)(next() % 15), point = (int)(next() % (digits + 1)), n = 0, e;
        e = digits - point - 22 + (int)(next() % (unsigned)(37 - (digits - point)));
        if (next() & 1)
            s[n++] = '-';
        for (j = 0; j < digits; j++) {
            if (j == point)
                s[n++] = '.';
            s[n++] = (char)('0' + next() % 10);
        }
        n += sprintf(s + n, "e%d", e);
        s[n] = 0;
        check_strtod(s, 1);
    }
    scans();
    printf("format failures %d\n", failures);
    return failures != 0;
}
