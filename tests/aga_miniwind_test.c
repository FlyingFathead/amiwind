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
    /* The title buffer holds 79 characters, one more is refused. */
    {
        char title[81];
        memset(title,'T',79);title[79]=0;
        sprintf(big,"AWMW1\ntown balmora\ntitle %s\nfeatures F\n",title);assert(parses(big));
        memset(title,'T',80);title[80]=0;
        sprintf(big,"AWMW1\ntown balmora\ntitle %s\nfeatures F\n",title);assert(!parses(big));
    }
    puts("partial-area notice file parsed; damaged files refused");
    return 0;
}
