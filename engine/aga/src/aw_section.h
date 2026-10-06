/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_SECTION_H
#define AW_SECTION_H
#include <stdio.h>
#define AW_SECTION_MAX 8
#define AW_SECTION_PORTALS 8
typedef struct {char name[16];float low[3],high[3];} aw_section_record_t;
typedef struct {int a,b,axis;float split,margin,low[3],high[3];} aw_section_portal_t;
typedef struct {
    int count,portals;
    aw_section_record_t section[AW_SECTION_MAX];
    aw_section_portal_t portal[AW_SECTION_PORTALS];
} aw_section_directory_t;
int AW_SectionRead(FILE *,aw_section_directory_t *);
int AW_SectionChoose(const aw_section_directory_t *,const char *,const float *);
int AW_SectionSelect(const char *,const float *);
int AW_SectionContains(const char *,const float *);
int AW_SectionDestination(const char *,const float *,char *);
const char *AW_SectionAhead(const char *,const float *,const float *,float);
unsigned AW_SectionStaticBytes(void);
#endif
