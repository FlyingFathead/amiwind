/* SPDX-License-Identifier: GPL-2.0-or-later
 * Text <-> number conversion without the C library's floating-point code
 * (aw_format.c; ENGINE-FPU-UNIMPL-31, ENGINE-FPSP-MISSING-31).
 */
#ifndef AW_FORMAT_H
#define AW_FORMAT_H
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>

double Q_strtod(const char *text, char **end);
int Q_vsscanf(const char *text, const char *format, va_list ap);
int Q_sscanf(const char *text, const char *format, ...) __attribute__((format(scanf, 2, 3)));
int Q_fscanf(FILE *f, const char *format, ...) __attribute__((format(scanf, 2, 3)));
int Q_vsnprintf(char *out, size_t size, const char *format, va_list ap);
int Q_snprintf(char *out, size_t size, const char *format, ...) __attribute__((format(printf, 3, 4)));

#endif
