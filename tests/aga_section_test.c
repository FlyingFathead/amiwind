/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_maps.h"
#include "aw_section.h"
#include <assert.h>
static const char *fixture="AWIS1 2 1\n"
 "mi5b8154939f7aa -600 600 -600 320 1600 300\n"
 "mi5b8154939f7ab -300 600 -600 1000 1600 300\n"
 "mi5b8154939f7aa mi5b8154939f7ab 0 -128 16 -192 960 -256 -64 1216 -128\n";
void Con_Printf(char *s,...){}
int COM_FOpenFile(char *name,FILE **f){assert(!strcmp(name,"interior-sections.txt"));*f=tmpfile();assert(*f);fputs(fixture,*f);rewind(*f);return strlen(fixture);}
static int read_fixture(const char *s,aw_section_directory_t *d){FILE *f=tmpfile();int n;assert(f);fputs(s,f);rewind(f);n=AW_SectionRead(f,d);fclose(f);return n;}
int main(int argc,char **argv)
{
 aw_section_directory_t d,old;char target[16],name[16],bad[1024];float p[3]={-112,1088,-192},v[3]={20,0,0};int i;
 for(i=0;i<8252;i++){strcpy(name,AW_MapName(i));assert(AW_MapId(name)==i);assert(AW_MapLogicalId(name)==i);}
 assert(AW_MapId("mi5b8154939f7aa")==8252 && AW_MapId("mi5b8154939f7ab")==8253);
 assert(AW_MapLogicalId("mi5b8154939f7ab")==8252);
 assert(!strcmp(AW_MapName(8253),"mi5b8154939f7ab") && !strcmp(AW_MapTitle(8253),"Abaelun Mine"));
 assert(!strcmp(AW_MapName(8251),"vf8191") && !strcmp(AW_MapTitle(8251),"Vvardenfell"));
 assert(AW_MapId("vf8192")==-1 && !*AW_MapName(8254));
 assert(read_fixture(fixture,&d));old=d;
 assert(AW_SectionChoose(&d,"mi5b8154939f7aa",p)==-1);p[0]+=.001f;
 assert(AW_SectionChoose(&d,"mi5b8154939f7aa",p)==1);
 assert(AW_SectionChoose(&d,"mi5b8154939f7ab",p)==-1);
 p[0]=-144;assert(AW_SectionChoose(&d,"mi5b8154939f7ab",p)==-1);
 p[0]-=.001f;assert(AW_SectionChoose(&d,"mi5b8154939f7ab",p)==0);
 p[0]=-100;p[1]=959;assert(AW_SectionChoose(&d,"mi5b8154939f7aa",p)==-1);
 p[1]=1088;p[2]=-127;assert(AW_SectionChoose(&d,"mi5b8154939f7aa",p)==-1);
 p[2]=-192;p[0]=NAN;assert(AW_SectionChoose(&d,"mi5b8154939f7aa",p)==-1);
 assert(!read_fixture("AWIS1 9 1\n",&d) && !memcmp(&d,&old,sizeof(d)));
 strcpy(bad,fixture);strcat(bad,"trailing\n");assert(!read_fixture(bad,&d));
 strcpy(bad,fixture);strstr(bad," -128 ")[1]='n';assert(!read_fixture(bad,&d));
 assert(!memcmp(&d,&old,sizeof(d)));
 p[0]=-100;assert(AW_SectionDestination("mi5b8154939f7aa",p,target));assert(!strcmp(target,"mi5b8154939f7ab"));
 assert(AW_SectionSelect(target,p));p[0]=-700;assert(!AW_SectionSelect(target,p));
 assert(AW_SectionSelect("seyda",p));p[0]=-130;
 assert(!strcmp(AW_SectionAhead("mi5b8154939f7aa",p,v,1),"maps/mi5b8154939f7ab.bsp"));
 assert(!AW_SectionAhead("mi5b8154939f7aa",p,v,NAN));
 if(argc==2){FILE *f=fopen(argv[1],"rb");assert(f && AW_SectionRead(f,&d));fclose(f);
  assert(d.count==2 && d.portals==1);p[0]=-111;p[1]=1088;p[2]=-227;
  assert(AW_SectionChoose(&d,"mi5b8154939f7aa",p)==1);
  p[0]=-145;assert(AW_SectionChoose(&d,"mi5b8154939f7ab",p)==0);
 }
 printf("Section parser, all8252 legacy IDs, logical/physical split, finite portal and bidirectional hysteresis passed; static %u bytes\n",AW_SectionStaticBytes());
 return 0;
}
