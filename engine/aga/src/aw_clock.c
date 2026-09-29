/* SPDX-License-Identifier: GPL-2.0-or-later
 * Bounded calendar, stored in ordinary saved globals. Old saves initialize at
 * the base master's 09:00, day 16, month 7 (zero-based), year 427.
 */
#include "aw_state.h"
#include "aw_clock.h"
#define DAY_MS 86400000
#define MAX_DAYS 365000
static const char *ready="amiwind:clock:ready",*days="amiwind:clock:days",*ms="amiwind:clock:ms";
static const int month_days[12]={31,28,31,30,31,30,31,31,30,31,30,31};
int AW_ClockEnsure(void) {
    int d,t;aw_state_t next;
    if(AW_StateGet(&aw_state,AW_GLOBAL,ready)==1){
        d=AW_StateGet(&aw_state,AW_GLOBAL,days);t=AW_StateGet(&aw_state,AW_GLOBAL,ms);
        return d>=0 && d<=MAX_DAYS && t>=0 && t<DAY_MS;
    }
    next=aw_state;
    if(!AW_StateSet(&next,AW_GLOBAL,ready,1) || !AW_StateSet(&next,AW_GLOBAL,days,0) ||
       !AW_StateSet(&next,AW_GLOBAL,ms,32400000))return 0;
    aw_state=next;return 1;
}
int AW_ClockAdvance(int milliseconds) {
    int d,t;
    if(milliseconds<0 || milliseconds>DAY_MS || !AW_ClockEnsure())return 0;
    d=AW_StateGet(&aw_state,AW_GLOBAL,days);t=AW_StateGet(&aw_state,AW_GLOBAL,ms)+milliseconds;
    if(t>=DAY_MS){t-=DAY_MS;d++;}if(d>MAX_DAYS)return 0;
    AW_StateSet(&aw_state,AW_GLOBAL,days,d);AW_StateSet(&aw_state,AW_GLOBAL,ms,t);return 1;
}
int AW_ClockSetHour(double hour) {
    if(!(hour>=0 && hour<24) || !AW_ClockEnsure())return 0;
    return AW_StateSet(&aw_state,AW_GLOBAL,ms,(int)(hour*3600000));
}
void AW_ClockDate(int *year,int *month,int *day,int *hour,int *minute) {
    int d=227,t=32400000,m=0;
    if(AW_ClockEnsure()){d+=AW_StateGet(&aw_state,AW_GLOBAL,days);t=AW_StateGet(&aw_state,AW_GLOBAL,ms);}
    *year=427+d/365;d%=365;
    while(d>=month_days[m])d-=month_days[m++];
    *month=m+1;*day=d+1;*hour=t/3600000;*minute=(t/60000)%60;
}
