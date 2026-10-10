/* SPDX-License-Identifier: GPL-2.0-or-later
 * The partial-area build's notice file (aw_miniwind.c): the builder's own file
 * (argv[1], written by tools/miniwind.py data_file) parses; damaged files are
 * refused and the game runs as a normal build. */
#include "quakedef.h"
#include "aw_miniwind.h"
#include <assert.h>
static const char *file_text;static int file_size,printed;
int COM_FOpenFile(char *name,FILE **f){
    *f=NULL;
    if(strcmp(name,AW_MINIWIND_FILE) || !file_text)return -1;
    *f=tmpfile();assert(*f);fwrite(file_text,1,file_size,*f);rewind(*f);return file_size;
}
void Con_Printf(char *fmt,...){printed++;}
/* Title screen measure for the header wrap: 7 pixels per character. */
int AW_UIWidth(const char *s){return 7*(int)strlen(s);}
static int parses(const char *text){aw_miniwind_t m;return AW_MiniwindParse(text,(int)strlen(text),&m);}
int main(int argc,char **argv){
    static char builder[2048];aw_miniwind_t m;FILE *f;int n;char big[1200];
    assert(argc==2);
    f=fopen(argv[1],"rb");assert(f);n=(int)fread(builder,1,sizeof(builder),f);fclose(f);
    /* The builder's file: town, title and generated feature line. */
    assert(AW_MiniwindParse(builder,n,&m) && m.valid);
    assert(!strcmp(m.town,"balmora"));
    assert(!strcmp(m.title,"ATTENTION: THIS IS A MINIWIND PLAYTEST BUILD"));
    assert(!strncmp(m.features,"FEATURES ONLY: Balmora exterior (CHIM)",38));
    /* No file: a normal build, nothing changes. */
    file_text=NULL;AW_MiniwindInit();
    assert(!AW_MiniwindActive() && !strcmp(AW_MiniwindAfterLogo(),"aw_main_menu\n") && !printed);
    /* The builder's file: active, the notice is printed, the logo leads to the quick start. */
    file_text=builder;file_size=n;AW_MiniwindInit();
    assert(AW_MiniwindActive() && !strcmp(AW_Miniwind()->town,"balmora") && printed==1);
    assert(!strcmp(AW_MiniwindAfterLogo(),"aw_quick_start\n"));
    /* Damaged files are refused (reported once) and leave a normal build. */
    file_text="AWMW1\ntown balmora\n";file_size=(int)strlen(file_text);AW_MiniwindInit();
    assert(!AW_MiniwindActive() && printed==2 && !strcmp(AW_MiniwindAfterLogo(),"aw_main_menu\n"));
    assert(parses("AWMW1\ntown balmora\ntitle T\nfeatures FEATURES ONLY: x\n"));
    assert(!parses("AWMW2\ntown balmora\ntitle T\nfeatures F\n"));            /* magic */
    assert(!parses("AWMW1\ntown balmora\ntitle T\nfeatures F"));              /* unterminated */
    assert(!parses("AWMW1\ntown balmora\ntitle T\nfeatures F\nextra x\n"));   /* trailing line */
    assert(!parses("AWMW1\r\ntown balmora\r\ntitle T\r\nfeatures F\r\n"));     /* CRLF */
    assert(!parses("AWMW1\ntitle T\ntown balmora\nfeatures F\n"));            /* order */
    assert(!parses("AWMW1\ntown atlantis\ntitle T\nfeatures F\n"));           /* not a town */
    assert(!parses("AWMW1\ntown Balmora\ntitle T\nfeatures F\n"));            /* table names only */
    assert(!parses("AWMW1\ntown balmora\ntitle \nfeatures F\n"));             /* empty */
    assert(!parses("AWMW1\ntown balmora\ntitle T\tab\nfeatures F\n"));        /* control character */
    /* A direct start (tools/direct_start.py): optional start and character lines, in that order. */
    assert(parses("AWMW1\ntown balmora\ntitle T\nfeatures F\nstart map bmcouncil 12.5 -34 77 180\n"));
    assert(parses("AWMW1\ntown balmora\ntitle T\nfeatures F\nstart town balmora\n"
                  "character Dark Elf|Battlemage|Charioteer|f|Ilmeni\n"));
    assert(parses("AWMW1\ntown balmora\ntitle T\nfeatures F\ncharacter Nord|Barbarian|Charioteer|m|Hors\n"));
    assert(!parses("AWMW1\ntown balmora\ntitle T\nfeatures F\nstart map bmcouncil 12.5 -34 77\n"));      /* no yaw */
    assert(!parses("AWMW1\ntown balmora\ntitle T\nfeatures F\nstart map BmCouncil 1 2 3 4\n"));         /* map name */
    assert(!parses("AWMW1\ntown balmora\ntitle T\nfeatures F\nstart map bmcouncil 1 2 3 400\n"));       /* yaw */
    assert(!parses("AWMW1\ntown balmora\ntitle T\nfeatures F\nstart map bmcouncil 99999 2 3 4\n"));     /* bounds */
    assert(!parses("AWMW1\ntown balmora\ntitle T\nfeatures F\nstart town atlantis\n"));                 /* not a town */
    assert(!parses("AWMW1\ntown balmora\ntitle T\nfeatures F\nstart cell -3 -2\n"));                    /* kind */
    assert(!parses("AWMW1\ntown balmora\ntitle T\nfeatures F\ncharacter Nord|Barbarian|m|Hors\n"));     /* fields */
    assert(!parses("AWMW1\ntown balmora\ntitle T\nfeatures F\ncharacter Nord|Barbarian|Charioteer|x|Hors\n"));
    assert(!parses("AWMW1\ntown balmora\ntitle T\nfeatures F\ncharacter Nord|Barbarian|Charioteer|m|\n"));
    assert(!parses("AWMW1\ntown balmora\ntitle T\nfeatures F\ncharacter Nord|Barbarian|Charioteer|m|Hors\n"
                   "start town balmora\n"));                                                                /* order */
    {
        const char *t="AWMW1\ntown balmora\ntitle T\nfeatures F\nstart map bmcouncil 12.5 -34 77 180\n"
            "character Dark Elf|Battlemage|Charioteer|f|Ilmeni\n";
        aw_quick_start_t s;char race[32],clas[32],birth[32],name[32];int female;
        assert(AW_MiniwindParse(t,(int)strlen(t),&m));
        assert(AW_MiniwindStart(&m,&s) && s.kind==2 && !strcmp(s.map,"bmcouncil"));
        assert(s.point[0]==12.5f && s.point[1]==-34 && s.point[2]==77 && s.yaw==180);
        assert(AW_MiniwindCharacter(&m,race,clas,birth,&female,name,32));
        assert(!strcmp(race,"Dark Elf") && !strcmp(clas,"Battlemage") && !strcmp(birth,"Charioteer") && female &&
               !strcmp(name,"Ilmeni"));
        t="AWMW1\ntown balmora\ntitle T\nfeatures F\nstart town balmora\n";
        assert(AW_MiniwindParse(t,(int)strlen(t),&m) && AW_MiniwindStart(&m,&s) && s.kind==1 && !strcmp(s.map,"balmora"));
        assert(!AW_MiniwindCharacter(&m,race,clas,birth,&female,name,32));
        /* The builder's own MiniWind file has neither line: the town's arrival and the Hors preset. */
        assert(AW_MiniwindParse(builder,n,&m) && !AW_MiniwindStart(&m,&s) && s.kind==0);
    }
    /* The title buffer holds 79 characters, one more is refused. */
    {
        char title[81];
        memset(title,'T',79);title[79]=0;
        sprintf(big,"AWMW1\ntown balmora\ntitle %s\nfeatures F\n",title);assert(parses(big));
        memset(title,'T',80);title[80]=0;
        sprintf(big,"AWMW1\ntown balmora\ntitle %s\nfeatures F\n",title);assert(!parses(big));
    }
    /* The optional header line (the title screen of a test build), after start and character. */
    {
        char lines[2][AW_MINIWIND_HEADER];int lines_used;
        const char *t="AWMW1\ntown balmora\ntitle T\nfeatures F\nstart town balmora\nheader MINIWIND TEST UNIT: Balmora\n";
        assert(AW_MiniwindParse(t,(int)strlen(t),&m) && !strcmp(m.header,"MINIWIND TEST UNIT: Balmora"));
        assert(parses("AWMW1\ntown balmora\ntitle T\nfeatures F\nheader H\n"));
        assert(!parses("AWMW1\ntown balmora\ntitle T\nfeatures F\nheader H\nstart town balmora\n"));  /* order */
        /* No header in the builder's plain notice: nothing drawn. */
        assert(AW_MiniwindParse(builder,n,&m) && !m.header[0]);
        /* Wrapped to 300 px (42 characters here), two lines at most, "..." when cut. */
        lines_used=AW_MenuHeaderLines("MINIWIND TEST UNIT: Balmora",300,lines);
        assert(lines_used==1 && !strcmp(lines[0],"MINIWIND TEST UNIT: Balmora"));
        lines_used=AW_MenuHeaderLines("MINIWIND TEST UNIT: Balmora on CHIM, incremental streaming, photo mode",300,lines);
        assert(lines_used==2 && !strcmp(lines[0],"MINIWIND TEST UNIT: Balmora on CHIM,") &&
               !strcmp(lines[1],"incremental streaming, photo mode"));
        lines_used=AW_MenuHeaderLines("MINIWIND TEST UNIT: Balmora on CHIM, incremental streaming, photo mode and a lot "
                                      "more words here",300,lines);
        assert(lines_used==2 && !strcmp(lines[1],"incremental streaming, photo mode and a...") &&
               AW_UIWidth(lines[1])<=300);
    }
    puts("partial-area notice file parsed; damaged files refused");
    return 0;
}
