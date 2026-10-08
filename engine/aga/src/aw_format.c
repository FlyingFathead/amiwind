/* SPDX-License-Identifier: GPL-2.0-or-later
 * Text <-> number conversion without the C library's floating-point code.
 *
 * The C library's float parsing (atof, strtod, scanf %f) and float printing
 * (printf %e/%f/%g) execute FINTRZ, which the 68040 does not implement: on a
 * machine without an FPU support library the first such instruction ends
 * the program (ENGINE-FPU-UNIMPL-31, ENGINE-FPSP-MISSING-31). Scene text,
 * entity fields and console arguments are parsed during play, and messages
 * print floats during play, so the engine does both itself, the Quake way:
 * Quake's Q_atof (common.c) parses with integer digit arithmetic, and Quake
 * III's game-module C library (bg_lib.c) has its own sscanf and a printf
 * whose float output is built from integer digits.
 *
 * Only instructions the 68040 executes in hardware are used: FADD, FSUB,
 * FMUL, FDIV, FCMP and FMOVE (integer <-> float conversion with the rounding
 * mode set to truncate, as GCC does for -m68040 code), in double or the
 * FPU's extended precision. Accuracy: parsing scales once by an exact power
 * of ten (correctly rounded for up to 15 significant digits and exponents up
 * to 22, otherwise within about one unit in the last place; results below
 * the smallest normal double become 0, never a denormal, which a 68040
 * would trap on); printing generates digits by repeated multiplication by
 * ten in extended precision (exact for values of 1 and above, so %f of a
 * float matches the C library), and %f of values of 1e18 and above prints
 * in %e form.
 *
 * Q_vsnprintf supports the conversions d i u o x X c s p n % e E f F g G
 * (a and A print as e and E), the flags - + space # 0, field width and
 * precision (also *), and the lengths hh h l ll L z j t q. The link maps
 * sprintf, snprintf, vsprintf, vsnprintf, fprintf, vfprintf, printf and
 * vprintf onto it (engine/aga/Makefile FORMAT_WRAPS), so the C library's
 * printf code is not linked. Q_sscanf and Q_fscanf support d i u o x X f e
 * g E G a c s [set] n %, the * suppression, field width and the same
 * lengths; the engine calls them instead of sscanf and fscanf.
 */
#include <errno.h>
#include <float.h>
#include <limits.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "aw_format.h"

/* Extended precision (68881/68040 96-bit, x86 80-bit) for digit
 * generation; plain double on a soft-float build. */
#if defined(__HAVE_68881__) || !defined(AMIGA)
typedef long double wide_t;
#else
typedef double wide_t;
#endif

#ifndef va_copy
#define va_copy(d, s) __builtin_va_copy(d, s)
#endif

static const double exact_powers[23] = {
    1e0, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10, 1e11,
    1e12, 1e13, 1e14, 1e15, 1e16, 1e17, 1e18, 1e19, 1e20, 1e21, 1e22
};

/* w * 10^e in the extended type: powers of ten up to 10^27 are exact there,
 * larger exponents go in steps of 10^27. */
static wide_t scale10_wide(wide_t w, int e)
{
    wide_t power = 1;
    int k, negative = e < 0;
    if (negative)
        e = -e;
    while (e > 27) {
        w = negative ? w / 1e27L : w * 1e27L;
        e -= 27;
    }
    for (k = 0; k < e; k++)
        power *= 10;
    return negative ? w / power : w * power;
}

static int is_space(int c)
{
    return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v';
}

double Q_strtod(const char *text, char **end)
{
    const char *p = text;
    wide_t w = 0;
    double value;
    int negative = 0, digits = 0, significant = 0, exponent = 0;

    while (is_space((unsigned char)*p))
        p++;
    if (*p == '+' || *p == '-')
        negative = *p++ == '-';
    for (; *p >= '0' && *p <= '9'; p++) {
        digits++;
        if (significant < 19) {
            w = w * 10 + (*p - '0');
            if (w != 0)
                significant++;
        } else {
            exponent++;
        }
    }
    if (*p == '.') {
        for (p++; *p >= '0' && *p <= '9'; p++) {
            digits++;
            if (significant < 19) {
                w = w * 10 + (*p - '0');
                if (w != 0)
                    significant++;
                exponent--;
            }
        }
    }
    if (!digits) {
        if (end)
            *end = (char *)text;
        return 0;
    }
    if (*p == 'e' || *p == 'E') {
        const char *q = p + 1;
        int minus = 0, e = 0;
        if (*q == '+' || *q == '-')
            minus = *q++ == '-';
        if (*q >= '0' && *q <= '9') {
            for (; *q >= '0' && *q <= '9'; q++)
                if (e < 100000)
                    e = e * 10 + (*q - '0');
            exponent += minus ? -e : e;
            p = q;
        }
    }
    if (end)
        *end = (char *)p;
    if (w == 0) {
        value = 0;
    } else if (exponent < -360) {
        value = 0;
        errno = ERANGE;
    } else if (exponent > 330) {
        value = HUGE_VAL;
        errno = ERANGE;
    } else if (significant <= 15 && exponent >= -22 && exponent <= 22) {
        /* exact integer and exact power of ten: one correctly rounded
         * double multiplication or division */
        value = exponent < 0 ? (double)w / exact_powers[-exponent] : (double)w * exact_powers[exponent];
    } else {
        wide_t x = scale10_wide(w, exponent);
        if (x > DBL_MAX) {
            value = HUGE_VAL;
            errno = ERANGE;
        } else if (x < DBL_MIN) {   /* no denormals: they trap on a 68040 without support code */
            value = 0;
            errno = ERANGE;
        } else {
            value = (double)x;
        }
    }
    return negative ? -value : value;
}

/* ------------------------------------------------------------------ */
/* printf                                                              */

typedef struct {
    char *buffer;
    size_t size, length;
} output_t;

static void put(output_t *o, char c)
{
    if (o->length + 1 < o->size)
        o->buffer[o->length] = c;
    o->length++;
}

static void put_text(output_t *o, const char *s, int n)
{
    while (n-- > 0)
        put(o, *s++);
}

static void put_repeat(output_t *o, char c, int n)
{
    while (n-- > 0)
        put(o, c);
}

#define FLAG_LEFT  1
#define FLAG_PLUS  2
#define FLAG_SPACE 4
#define FLAG_ALT   8
#define FLAG_ZERO  16

/* prefix (sign, 0x), then zeros, then the body; padded to width. */
static void put_field(output_t *o, int flags, int width, const char *prefix, int zeros,
                      const char *body, int length)
{
    int prefix_length = (int)strlen(prefix), total = prefix_length + zeros + length;
    if (!(flags & (FLAG_LEFT | FLAG_ZERO)))
        put_repeat(o, ' ', width - total);
    put_text(o, prefix, prefix_length);
    if ((flags & (FLAG_LEFT | FLAG_ZERO)) == FLAG_ZERO)
        put_repeat(o, '0', width - total);
    put_repeat(o, '0', zeros);
    put_text(o, body, length);
    if (flags & FLAG_LEFT)
        put_repeat(o, ' ', width - total);
}

/* Digits of v in base 2..16 written backwards ending at end; returns count. */
static int unsigned_digits(char *end, unsigned long long v, int base, int upper)
{
    const char *set = upper ? "0123456789ABCDEF" : "0123456789abcdef";
    int n = 0;
    if (v <= ULONG_MAX) {
        unsigned long w = (unsigned long)v;
        while (w) {
            *--end = set[w % (unsigned)base];
            w /= (unsigned)base;
            n++;
        }
    } else {
        while (v) {
            *--end = set[v % (unsigned)base];
            v /= (unsigned)base;
            n++;
        }
    }
    return n;
}

#define FLOAT_DIGITS 120        /* fraction digits generated at most */

typedef struct {
    char integer[24];           /* integer part digits */
    int integer_length;
    char fraction[FLOAT_DIGITS];
    int fraction_length;
} digits_t;

/* 0 <= v < 1e18: decimal integer part and 'precision' rounded fraction
 * digits (round half to even on the remainder), carry propagated. Digits
 * come from repeated multiplication by ten in the extended type, which is
 * exact for v >= 1 (the remainder never needs more than 64 bits). */
static void fixed_digits(wide_t v, int precision, digits_t *d)
{
    long high, low;
    wide_t rest, fraction;
    char *end;
    int i, n;

    if (precision > FLOAT_DIGITS)
        precision = FLOAT_DIGITS;
    high = (long)(v / 1e9);
    rest = v - (wide_t)high * 1e9;
    if (rest < 0) {
        high--;
        rest += 1e9;
    } else if (rest >= 1e9) {
        high++;
        rest -= 1e9;
    }
    low = (long)rest;
    if (low < 0)
        low = 0;
    if (low > 999999999)
        low = 999999999;
    fraction = rest - (wide_t)low;
    if (fraction < 0)
        fraction = 0;
    for (i = 0; i < precision; i++) {
        int digit;
        fraction *= 10;
        digit = (int)fraction;
        if (digit > 9)
            digit = 9;
        if (digit < 0)
            digit = 0;
        d->fraction[i] = (char)('0' + digit);
        fraction -= digit;
    }
    d->fraction_length = precision;
    /* round on what is left */
    if (fraction > 0.5 || (fraction == 0.5 &&
        (precision ? (d->fraction[precision - 1] - '0') & 1 : low & 1))) {
        for (i = precision - 1; i >= 0; i--) {
            if (d->fraction[i] == '9') {
                d->fraction[i] = '0';
            } else {
                d->fraction[i]++;
                break;
            }
        }
        if (i < 0 && ++low > 999999999) {
            low = 0;
            high++;
        }
    }
    end = d->integer + sizeof d->integer;
    if (high) {
        n = unsigned_digits(end, (unsigned long)low, 10, 0);
        while (n < 9)
            end[-++n] = '0';
        n += unsigned_digits(end - n, (unsigned long)high, 10, 0);
    } else {
        n = unsigned_digits(end, (unsigned long)low, 10, 0);
        if (!n)
            end[-++n] = '0';
    }
    memmove(d->integer, end - n, n);
    d->integer_length = n;
}

/* v > 0 finite: mantissa in [1, 10) and decimal exponent (extended
 * precision; scaling by 10 or 100 is exact for double inputs). */
static wide_t normalise(wide_t v, int *exponent)
{
    static const wide_t big[9] = {1e256L, 1e128L, 1e64L, 1e32L, 1e16L, 1e8L, 1e4L, 1e2L, 1e1L};
    static const int bits[9] = {256, 128, 64, 32, 16, 8, 4, 2, 1};
    int e = 0, i;
    if (v >= 10) {
        for (i = 0; i < 9; i++)
            if (v >= big[i]) {
                v /= big[i];
                e += bits[i];
            }
    } else if (v < 1) {
        for (i = 0; i < 9; i++)
            if (v * big[i] < 10) {
                v *= big[i];
                e -= bits[i];
            }
        if (v < 1) {
            v *= 10;
            e--;
        }
    }
    if (v >= 10) {          /* rounding of the steps above */
        v /= 10;
        e++;
    }
    *exponent = e;
    return v;
}

/* Exponent form: one integer digit, 'precision' fraction digits. */
static void exponent_digits(wide_t v, int precision, digits_t *d, int *exponent)
{
    int e = 0;
    if (v != 0)
        v = normalise(v, &e);
    fixed_digits(v, precision, d);
    if (d->integer_length > 1) {    /* 9.99.. rounded up to 10 */
        fixed_digits(1.0, precision, d);
        e++;
    }
    *exponent = e;
}

static int float_bits(double v, int *negative)
{
    /* 0 finite, 1 infinite, 2 not a number (from the bits: no FPU compares) */
    unsigned long long bits;
    unsigned exponent;
    memcpy(&bits, &v, sizeof bits);
    *negative = (int)(bits >> 63);
    exponent = (unsigned)(bits >> 52) & 0x7ff;
    if (exponent != 0x7ff)
        return 0;
    return (bits & 0xfffffffffffffULL) ? 2 : 1;
}

static void format_float(output_t *o, double v, int conversion, int flags, int width, int precision)
{
    char body[FLOAT_DIGITS + 64], prefix[2] = {0, 0};
    int upper = conversion == 'E' || conversion == 'F' || conversion == 'G' || conversion == 'A';
    int negative, kind = float_bits(v, &negative), n = 0, i, exponent = 0, style;
    digits_t d;

    if (negative) {
        prefix[0] = '-';
        v = -v;
    } else if (flags & FLAG_PLUS) {
        prefix[0] = '+';
    } else if (flags & FLAG_SPACE) {
        prefix[0] = ' ';
    }
    if (kind) {
        put_field(o, flags & ~FLAG_ZERO, width, prefix, 0,
                  kind == 1 ? (upper ? "INF" : "inf") : (upper ? "NAN" : "nan"), 3);
        return;
    }
    if (precision < 0)
        precision = 6;
    if (precision > FLOAT_DIGITS)
        precision = FLOAT_DIGITS;
    style = conversion | 32;            /* lower case */
    if (style == 'a')
        style = 'e';
    if (style == 'g') {
        int p = precision ? precision : 1;
        exponent_digits(v, p - 1, &d, &exponent);
        if (p > exponent && exponent >= -4) {
            style = 'f';
            precision = p - 1 - exponent;
        } else {
            style = 'e';
            precision = p - 1;
        }
        if (style == 'f' && v >= 1e18) {   /* beyond the fixed range */
            style = 'e';
            precision = p - 1;
        }
        if (style == 'f')
            fixed_digits(v, precision, &d);
        if (!(flags & FLAG_ALT)) {
            while (d.fraction_length && d.fraction[d.fraction_length - 1] == '0')
                d.fraction_length--;
            precision = d.fraction_length;
        }
    } else if (style == 'f' && v < 1e18) {
        fixed_digits(v, precision, &d);
    } else {
        style = 'e';
        exponent_digits(v, precision, &d, &exponent);
    }
    memcpy(body, d.integer, d.integer_length);
    n = d.integer_length;
    if (precision || (flags & FLAG_ALT))
        body[n++] = '.';
    for (i = 0; i < precision && i < d.fraction_length; i++)
        body[n++] = d.fraction[i];
    if (style == 'e') {
        char digits[8], *end = digits + sizeof digits;
        int m;
        body[n++] = upper ? 'E' : 'e';
        body[n++] = exponent < 0 ? '-' : '+';
        m = unsigned_digits(end, (unsigned long)(exponent < 0 ? -exponent : exponent), 10, 0);
        while (m < 2)
            end[-++m] = '0';
        memcpy(body + n, end - m, m);
        n += m;
    }
    put_field(o, flags, width, prefix, 0, body, n);
}

int Q_vsnprintf(char *out, size_t size, const char *format, va_list ap)
{
    output_t o;
    const char *f;

    o.buffer = out;
    o.size = size;
    o.length = 0;
    for (f = format; *f; f++) {
        int flags = 0, width = 0, precision = -1, length = 0, conversion;
        unsigned long long magnitude = 0;
        int negative = 0, is_signed = 0, base = 10;

        if (*f != '%') {
            put(&o, *f);
            continue;
        }
        for (f++;; f++) {
            if (*f == '-') flags |= FLAG_LEFT;
            else if (*f == '+') flags |= FLAG_PLUS;
            else if (*f == ' ') flags |= FLAG_SPACE;
            else if (*f == '#') flags |= FLAG_ALT;
            else if (*f == '0') flags |= FLAG_ZERO;
            else break;
        }
        if (*f == '*') {
            width = va_arg(ap, int);
            if (width < 0) {
                flags |= FLAG_LEFT;
                width = -width;
            }
            f++;
        } else {
            while (*f >= '0' && *f <= '9')
                width = width * 10 + (*f++ - '0');
        }
        if (*f == '.') {
            f++;
            precision = 0;
            if (*f == '*') {
                precision = va_arg(ap, int);
                f++;
            } else {
                while (*f >= '0' && *f <= '9')
                    precision = precision * 10 + (*f++ - '0');
            }
        }
        /* length: 1 hh, 2 h, 3 l, 4 ll/q/j, 5 L, 6 z/t */
        if (*f == 'h') {
            length = 2;
            if (*++f == 'h') {
                length = 1;
                f++;
            }
        } else if (*f == 'l') {
            length = 3;
            if (*++f == 'l') {
                length = 4;
                f++;
            }
        } else if (*f == 'q' || *f == 'j') {
            length = 4;
            f++;
        } else if (*f == 'L') {
            length = 5;
            f++;
        } else if (*f == 'z' || *f == 't') {
            length = 6;
            f++;
        }
        conversion = *f;
        if (!conversion)
            break;
        switch (conversion) {
        case '%':
            put(&o, '%');
            continue;
        case 'c': {
            char c = (char)va_arg(ap, int);
            put_field(&o, flags & ~FLAG_ZERO, width, "", 0, &c, 1);
            continue;
        }
        case 's': {
            const char *s = va_arg(ap, const char *);
            int n = 0;
            if (!s)
                s = "(null)";
            while (s[n] && (precision < 0 || n < precision))
                n++;
            put_field(&o, flags & ~FLAG_ZERO, width, "", 0, s, n);
            continue;
        }
        case 'n':
            switch (length) {
            case 1: *va_arg(ap, signed char *) = (signed char)o.length; break;
            case 2: *va_arg(ap, short *) = (short)o.length; break;
            case 3: *va_arg(ap, long *) = (long)o.length; break;
            case 4: *va_arg(ap, long long *) = (long long)o.length; break;
            case 6: *va_arg(ap, size_t *) = o.length; break;
            default: *va_arg(ap, int *) = (int)o.length; break;
            }
            continue;
        case 'e': case 'E': case 'f': case 'F': case 'g': case 'G': case 'a': case 'A': {
            double v = length == 5 ? (double)va_arg(ap, long double) : va_arg(ap, double);
            format_float(&o, v, conversion, flags, width, precision);
            continue;
        }
        case 'p':
            magnitude = (unsigned long)va_arg(ap, void *);
            flags |= FLAG_ALT;
            base = 16;
            break;
        case 'd': case 'i':
            is_signed = 1;
            {
                long long v;
                switch (length) {
                case 1: v = (signed char)va_arg(ap, int); break;
                case 2: v = (short)va_arg(ap, int); break;
                case 3: v = va_arg(ap, long); break;
                case 4: v = va_arg(ap, long long); break;
                case 6: v = (long)va_arg(ap, size_t); break;
                default: v = va_arg(ap, int); break;
                }
                negative = v < 0;
                magnitude = negative ? 0 - (unsigned long long)v : (unsigned long long)v;
            }
            break;
        case 'u': case 'o': case 'x': case 'X':
            base = conversion == 'u' ? 10 : conversion == 'o' ? 8 : 16;
            switch (length) {
            case 1: magnitude = (unsigned char)va_arg(ap, unsigned int); break;
            case 2: magnitude = (unsigned short)va_arg(ap, unsigned int); break;
            case 3: magnitude = va_arg(ap, unsigned long); break;
            case 4: magnitude = va_arg(ap, unsigned long long); break;
            case 6: magnitude = va_arg(ap, size_t); break;
            default: magnitude = va_arg(ap, unsigned int); break;
            }
            break;
        default:            /* unknown: print it as written */
            put(&o, '%');
            put(&o, (char)conversion);
            continue;
        }
        {
            char digits[24], *end = digits + sizeof digits;
            char prefix[3] = {0, 0, 0};
            int n = unsigned_digits(end, magnitude, base, conversion == 'X');
            int zeros = 0;
            if (is_signed) {
                if (negative) prefix[0] = '-';
                else if (flags & FLAG_PLUS) prefix[0] = '+';
                else if (flags & FLAG_SPACE) prefix[0] = ' ';
            }
            if ((flags & FLAG_ALT) && base == 16 && magnitude) {
                prefix[0] = '0';
                prefix[1] = conversion == 'X' ? 'X' : 'x';
            }
            if (precision >= 0) {
                flags &= ~FLAG_ZERO;
                if (precision > n)
                    zeros = precision - n;
            } else if (!n) {
                zeros = 1;      /* value 0 prints "0" */
            }
            if ((flags & FLAG_ALT) && base == 8 && !zeros && (!n || end[-n] != '0'))
                zeros = 1;
            put_field(&o, flags, width, prefix, zeros, end - n, n);
        }
    }
    if (size)
        out[o.length < size ? o.length : size - 1] = 0;
    return o.length > INT_MAX ? INT_MAX : (int)o.length;
}

int Q_snprintf(char *out, size_t size, const char *format, ...)
{
    va_list ap;
    int n;
    va_start(ap, format);
    n = Q_vsnprintf(out, size, format, ap);
    va_end(ap);
    return n;
}

/* ------------------------------------------------------------------ */
/* scanf                                                               */

typedef struct {
    const char *text;           /* string source, or */
    FILE *file;                 /* file source */
    int count;                  /* characters consumed (%n) */
} input_t;

static int get(input_t *in)
{
    int c;
    if (in->file)
        c = getc(in->file);
    else
        c = *in->text ? (unsigned char)*in->text++ : EOF;
    if (c != EOF)
        in->count++;
    return c;
}

static void unget(input_t *in, int c)
{
    if (c == EOF)
        return;
    in->count--;
    if (in->file)
        ungetc(c, in->file);
    else
        in->text--;
}

static int skip_space(input_t *in)
{
    int c;
    do
        c = get(in);
    while (c != EOF && is_space(c));
    unget(in, c);
    return c;
}

static int digit_value(int c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return 99;
}

/* Returns 1 on a stored or suppressed conversion, 0 on a matching failure,
 * -1 on input failure (end of input before any character of the field). */
static int scan_integer(input_t *in, int conversion, int width, unsigned long long *out, int *negative)
{
    int base = conversion == 'o' ? 8 : (conversion == 'x' || conversion == 'X') ? 16 :
               conversion == 'i' ? 0 : 10;
    int c, used = 0, digits = 0;
    unsigned long long v = 0;
    if (width <= 0)
        width = INT_MAX;
    *negative = 0;
    c = get(in);
    if (c == EOF)
        return -1;
    if ((c == '+' || c == '-') && used < width) {
        *negative = c == '-';
        used++;
        c = get(in);
    }
    if (c == '0' && used < width && (base == 0 || base == 16)) {
        used++;
        digits = 1;
        c = get(in);
        if ((c == 'x' || c == 'X') && used < width) {
            base = 16;
            used++;
            digits = 0;
            c = get(in);
        } else if (base == 0) {
            base = 8;
        }
    }
    if (base == 0)
        base = 10;
    while (used < width && digit_value(c) < base) {
        v = v * (unsigned)base + (unsigned)digit_value(c);
        digits++;
        used++;
        c = get(in);
    }
    unget(in, c);
    if (!digits)
        return 0;
    *out = v;
    return 1;
}

static int scan_float(input_t *in, int width, double *out)
{
    char token[80], *end;
    int c, n = 0, digits = 0, state = 0;
    if (width <= 0 || width > (int)sizeof token - 1)
        width = (int)sizeof token - 1;
    /* state: 0 sign, 1 integer digits, 2 fraction digits, 3 exponent sign, 4 exponent digits */
    c = get(in);
    if (c == EOF)
        return -1;
    while (n < width && c != EOF) {
        if (state == 0 && (c == '+' || c == '-')) {
            state = 1;
        } else if (state <= 1 && c >= '0' && c <= '9') {
            state = 1;
            digits++;
        } else if (state <= 1 && c == '.') {
            state = 2;
        } else if (state == 2 && c >= '0' && c <= '9') {
            digits++;
        } else if (state >= 1 && state <= 2 && digits && (c == 'e' || c == 'E')) {
            state = 3;
        } else if (state == 3 && (c == '+' || c == '-')) {
            state = 4;
        } else if (state >= 3 && c >= '0' && c <= '9') {
            state = 5;
        } else if (state == 5 && c >= '0' && c <= '9') {
        } else {
            break;
        }
        token[n++] = (char)c;
        c = get(in);
    }
    unget(in, c);
    token[n] = 0;
    *out = Q_strtod(token, &end);
    if (end == token)
        return 0;
    if (!in->file && *end) {    /* give back an incomplete exponent */
        size_t extra = strlen(end);
        in->text -= extra;
        in->count -= (int)extra;
    }
    return 1;
}

static int vscan(input_t *in, const char *f, va_list ap)
{
    int assigned = 0, converted = 0, c;
    while (*f) {
        int suppress = 0, width = 0, length = 0, conversion, result = 1;
        if (is_space((unsigned char)*f)) {
            while (is_space((unsigned char)*f))
                f++;
            skip_space(in);
            continue;
        }
        if (*f != '%' || f[1] == '%') {
            if (*f == '%') {
                f++;
                skip_space(in);
            }
            c = get(in);
            if (c != (unsigned char)*f) {
                unget(in, c);
                return c == EOF && !converted ? EOF : assigned;
            }
            f++;
            continue;
        }
        f++;
        if (*f == '*') {
            suppress = 1;
            f++;
        }
        while (*f >= '0' && *f <= '9')
            width = width * 10 + (*f++ - '0');
        if (*f == 'h') {
            length = 2;
            if (*++f == 'h') {
                length = 1;
                f++;
            }
        } else if (*f == 'l') {
            length = 3;
            if (*++f == 'l') {
                length = 4;
                f++;
            }
        } else if (*f == 'q' || *f == 'j') {
            length = 4;
            f++;
        } else if (*f == 'L') {
            length = 5;
            f++;
        } else if (*f == 'z' || *f == 't') {
            length = 6;
            f++;
        }
        conversion = *f++;
        switch (conversion) {
        case 'n':
            if (!suppress) {
                switch (length) {
                case 1: *va_arg(ap, signed char *) = (signed char)in->count; break;
                case 2: *va_arg(ap, short *) = (short)in->count; break;
                case 3: *va_arg(ap, long *) = in->count; break;
                case 4: *va_arg(ap, long long *) = in->count; break;
                case 6: *va_arg(ap, size_t *) = (size_t)in->count; break;
                default: *va_arg(ap, int *) = in->count; break;
                }
            }
            continue;
        case 'c': {
            char *dst = suppress ? NULL : va_arg(ap, char *);
            int i;
            if (width <= 0)
                width = 1;
            for (i = 0; i < width; i++) {
                c = get(in);
                if (c == EOF)
                    break;
                if (dst)
                    dst[i] = (char)c;
            }
            result = i ? 1 : -1;
            break;
        }
        case 's': {
            char *dst = suppress ? NULL : va_arg(ap, char *);
            int i = 0;
            skip_space(in);
            if (width <= 0)
                width = INT_MAX;
            while (i < width && (c = get(in)) != EOF) {
                if (is_space(c)) {
                    unget(in, c);
                    break;
                }
                if (dst)
                    dst[i] = (char)c;
                i++;
            }
            if (dst && i)
                dst[i] = 0;
            result = i ? 1 : -1;
            break;
        }
        case '[': {
            unsigned char set[256];
            char *dst;
            int negate = 0, i = 0, previous = -1;
            memset(set, 0, sizeof set);
            if (*f == '^') {
                negate = 1;
                f++;
            }
            if (*f == ']') {
                set[(unsigned char)']'] = 1;
                previous = ']';
                f++;
            }
            while (*f && *f != ']') {
                if (*f == '-' && previous >= 0 && f[1] && f[1] != ']') {
                    int k;
                    for (k = previous; k <= (unsigned char)f[1]; k++)
                        set[k] = 1;
                    previous = -1;
                    f += 2;
                    continue;
                }
                previous = (unsigned char)*f;
                set[previous] = 1;
                f++;
            }
            if (*f == ']')
                f++;
            dst = suppress ? NULL : va_arg(ap, char *);
            if (width <= 0)
                width = INT_MAX;
            c = EOF;
            while (i < width && (c = get(in)) != EOF) {
                if ((set[c] != 0) == negate) {
                    unget(in, c);
                    break;
                }
                if (dst)
                    dst[i] = (char)c;
                i++;
            }
            if (dst && i)
                dst[i] = 0;
            result = i ? 1 : (c == EOF ? -1 : 0);
            break;
        }
        case 'd': case 'i': case 'u': case 'o': case 'x': case 'X': {
            unsigned long long v;
            int negative;
            skip_space(in);
            result = scan_integer(in, conversion, width, &v, &negative);
            if (result == 1 && !suppress) {
                long long s = negative ? -(long long)v : (long long)v;
                void *p = va_arg(ap, void *);
                switch (length) {
                case 1: *(char *)p = (char)s; break;
                case 2: *(short *)p = (short)s; break;
                case 3: *(long *)p = (long)s; break;
                case 4: *(long long *)p = s; break;
                case 6: *(size_t *)p = (size_t)s; break;
                default: *(int *)p = (int)s; break;
                }
            }
            break;
        }
        case 'f': case 'e': case 'g': case 'E': case 'G': case 'a': case 'A': case 'F': {
            double v;
            skip_space(in);
            result = scan_float(in, width, &v);
            if (result == 1 && !suppress) {
                if (length == 3)
                    *va_arg(ap, double *) = v;
                else if (length == 5)
                    *va_arg(ap, long double *) = v;
                else
                    *va_arg(ap, float *) = (float)v;
            }
            break;
        }
        default:
            return assigned;    /* unsupported conversion: stop */
        }
        if (result < 0)
            return !converted ? EOF : assigned;
        if (!result)
            return assigned;
        converted++;
        if (!suppress)
            assigned++;
    }
    return assigned;
}

int Q_vsscanf(const char *text, const char *format, va_list ap)
{
    input_t in;
    in.text = text;
    in.file = NULL;
    in.count = 0;
    return vscan(&in, format, ap);
}

int Q_sscanf(const char *text, const char *format, ...)
{
    va_list ap;
    int n;
    va_start(ap, format);
    n = Q_vsscanf(text, format, ap);
    va_end(ap);
    return n;
}

int Q_fscanf(FILE *f, const char *format, ...)
{
    input_t in;
    va_list ap;
    int n;
    in.text = NULL;
    in.file = f;
    in.count = 0;
    va_start(ap, format);
    n = vscan(&in, format, ap);
    va_end(ap);
    return n;
}

/* ------------------------------------------------------------------ */
/* Link-time replacements for the C library's printf family (Amiga
 * link only: -Wl,--wrap=<name>, engine/aga/Makefile FORMAT_WRAPS). */
#ifdef AMIGA
int __wrap_vsnprintf(char *out, size_t size, const char *format, va_list ap);
int __wrap_snprintf(char *out, size_t size, const char *format, ...);
int __wrap_vsprintf(char *out, const char *format, va_list ap);
int __wrap_sprintf(char *out, const char *format, ...);
int __wrap_vfprintf(FILE *f, const char *format, va_list ap);
int __wrap_fprintf(FILE *f, const char *format, ...);
int __wrap_vprintf(const char *format, va_list ap);
int __wrap_printf(const char *format, ...);

int __wrap_vsnprintf(char *out, size_t size, const char *format, va_list ap)
{
    return Q_vsnprintf(out, size, format, ap);
}

int __wrap_snprintf(char *out, size_t size, const char *format, ...)
{
    va_list ap;
    int n;
    va_start(ap, format);
    n = Q_vsnprintf(out, size, format, ap);
    va_end(ap);
    return n;
}

int __wrap_vsprintf(char *out, const char *format, va_list ap)
{
    return Q_vsnprintf(out, INT_MAX, format, ap);
}

int __wrap_sprintf(char *out, const char *format, ...)
{
    va_list ap;
    int n;
    va_start(ap, format);
    n = Q_vsnprintf(out, INT_MAX, format, ap);
    va_end(ap);
    return n;
}

int __wrap_vfprintf(FILE *f, const char *format, va_list ap)
{
    char local[1024], *text = local;
    va_list again;
    int n;
    va_copy(again, ap);
    n = Q_vsnprintf(local, sizeof local, format, ap);
    if (n >= (int)sizeof local) {
        text = (char *)malloc((size_t)n + 1);
        if (text)
            Q_vsnprintf(text, (size_t)n + 1, format, again);
        else {
            text = local;
            n = (int)sizeof local - 1;
        }
    }
    va_end(again);
    if (n > 0 && fwrite(text, 1, (size_t)n, f) != (size_t)n)
        n = -1;
    if (text != local)
        free(text);
    return n;
}

int __wrap_fprintf(FILE *f, const char *format, ...)
{
    va_list ap;
    int n;
    va_start(ap, format);
    n = __wrap_vfprintf(f, format, ap);
    va_end(ap);
    return n;
}

int __wrap_vprintf(const char *format, va_list ap)
{
    return __wrap_vfprintf(stdout, format, ap);
}

int __wrap_printf(const char *format, ...)
{
    va_list ap;
    int n;
    va_start(ap, format);
    n = __wrap_vfprintf(stdout, format, ap);
    va_end(ap);
    return n;
}
#endif
