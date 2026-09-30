/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
static cvar_t *allow,*cap;
static const char *table;
static int reads;
int COM_FOpenFile(char *name,FILE **file){
 ++reads;assert(!strcmp(name,"model-budgets.txt"));*file=NULL;
 if(!table)return -1;
 *file=tmpfile();assert(*file);fputs(table,*file);rewind(*file);return strlen(table);
}
static unsigned int checksum(const byte *raw,int size){
 unsigned int crc=0xffffffffU;int i,b;
 for(i=0;i<size;i++){crc^=raw[i];for(b=0;b<8;b++)crc=(crc>>1)^(0xedb88320U&-(crc&1));}
 return crc^0xffffffffU;
}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Cvar_RegisterVariable(cvar_t *v){v->value=atof(v->string);if(!strcmp(v->name,"aw_allow_poly_budget_over"))allow=v;else cap=v;}
int main(void){
 byte raw[84]={0};char record[200];
 Mod_Init();assert(allow && cap && allow->value==0 && !strcmp(cap->string,"auto"));
 assert(AW_AliasBudgetAllows(1998,666));assert(AW_AliasBudgetAllows(2000,1000));
 assert(!AW_AliasBudgetAllows(2001,667));allow->value=1;
 assert(AW_AliasBudgetAllows(2331,777));assert(!AW_AliasBudgetAllows(2332,777));
 assert(!AW_AliasBudgetAllows(2331,778));cap->string="700";cap->value=700;
 assert(AW_AliasBudgetAllows(2100,700));assert(!AW_AliasBudgetAllows(2103,701));
 cap->string="10000";cap->value=10000;assert(!AW_AliasBudgetAllows(2331,777));cap->string="700.5";cap->value=700.5;
 assert(!AW_AliasBudgetAllows(2001,667));cap->string="777";cap->value=777;allow->value=0;
 assert(!AW_AliasBudgetAllows(2001,667));assert(!AW_AliasBudgetAllows(0,1));
 assert(AW_AliasExceptionAllows("normal.mdl",1998,666,NULL,0));assert(!reads);
 assert(!AW_AliasExceptionAllows("gallery/test.mdl",2295,765,raw,84));assert(!reads);
 allow->value=1;cap->string="auto";
 assert(!AW_AliasExceptionAllows("gallery/test.mdl",2295,765,raw,84));assert(reads==1);
 sprintf(record,"AWPB1\ngallery/test.mdl 2295 765 84 %08x\n",checksum(raw,84));table=record;
 assert(AW_AliasExceptionAllows("gallery/test.mdl",2295,765,raw,84));
 assert(!AW_AliasExceptionAllows("gallery/other.mdl",2295,765,raw,84));
 raw[20]=1;assert(!AW_AliasExceptionAllows("gallery/test.mdl",2295,765,raw,84));raw[20]=0;
 assert(!AW_AliasExceptionAllows("gallery/test.mdl",2298,766,raw,84));
 table="AWPB1\nbroken\n";assert(!AW_AliasExceptionAllows("gallery/test.mdl",2295,765,raw,84));
 return 0;
}
