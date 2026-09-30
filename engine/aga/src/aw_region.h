/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_REGION_H
#define AW_REGION_H
#define AW_REGION_MAX 64
typedef struct {char name[8];float low[2],high[2],cover_low[2],cover_high[2];} aw_region_t;
int AW_RegionOwner(const aw_region_t *,int,const float *,int,float);
int AW_RegionSelect(const char *,const float *,int);
const char *AW_RegionWorldModel(const char *,int);
int AW_RegionCrossing(const float *,int);
int AW_RegionContains(const float *);
int AW_BalmoraArrival(int,float *,float *);
int AW_BalmoraSelect(const float *);
const char *AW_BalmoraWorldModel(void);
int AW_BalmoraCrossing(const float *);
int AW_BalmoraContains(const float *);
#endif
