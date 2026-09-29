/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_CLOCK_H
#define AW_CLOCK_H
int AW_ClockEnsure(void);
int AW_ClockAdvance(int milliseconds);
int AW_ClockSetHour(double hour);
void AW_ClockDate(int *year,int *month,int *day,int *hour,int *minute);
#endif
