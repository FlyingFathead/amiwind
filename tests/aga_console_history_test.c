/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Console line editing and history through the engine's own key routing
 * (CONSOLE-HISTORY-EMPTY-32, CONSOLE-HISTORY-ARROWS-32, the aw_console_mode
 * terminal editor, KEYS-AMIGA-EDIT-32): native Amiga raw keys and qualifiers,
 * as Sys_SendKeyEvents delivers them, into Key_Event and Key_Console, with the
 * default game binding on the arrows. Both modes: classic Quake and terminal. */
#include "quakedef.h"
#include <assert.h>
client_static_t cls;client_state_t cl; qboolean con_forcedup; double realtime;
char queued[4096];int con_backscroll;
int Con_ScrollPage(void){return 10;}int Con_ScrollMax(void){return 100;}
void *Z_Malloc(int n){return calloc(1,n);} void Z_Free(void *p){free(p);}
int Q_strlen(char *s){return strlen(s);} void Q_strcpy(char *a,char *b){strcpy(a,b);}
int Q_strcmp(char *a,char *b){return strcmp(a,b);} int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Con_Printf(char *fmt,...){} void S_LocalSound(char *s){}
void Cmd_AddCommand(char *name,void (*fn)(void)){}
void Cbuf_AddText(char *s){strcat(queued,s);} void Cbuf_InsertText(char *s){strcat(queued,s);}
int Cmd_Argc(void){return 0;} char *Cmd_Argv(int n){return "";}
char *Cmd_CompleteCommand(char *s){return !strcmp(s,"ec")?"echo":NULL;} char *Cvar_CompleteVariable(char *s){return NULL;}
void Sys_Error(char *s,...){assert(0);} void SCR_UpdateScreen(void){}
void M_Keydown(int key){} void M_ToggleMenu_f(void){}
int AW_MovieKey(int k,int d){return 0;} int AW_WorldUIKey(int k,int d){return 0;}
int AW_GalleryKey(int k,int d,int s,int c){return 0;}
int AW_TravelKey(int k){return 0;} int AW_WaitKey(int k){return 0;} int AW_IntroKey(int k){return 0;}
int AW_ConsoleCharHeight(void){return 8;} int AW_ConsoleCharWidth(void){return 4;}
extern char key_lines[32][256];extern int edit_line,history_line,key_linepos;
static cvar_t *mode;
void Cvar_RegisterVariable(cvar_t *v){mode=v;v->value=atof(v->string);}
static void set_mode(const char *s){mode->string=(char *)s;mode->value=atof(s);}
void AW_ControlsMigrate(void);
#define RAW_UP 0x4c
#define RAW_DOWN 0x4d
#define RAW_RETURN 0x44
#define RAW_KEYPAD_8 0x3e
#define RAW_KEYPAD_2 0x1e
/* One raw key press and release, routed as Sys_SendKeyEvents routes IDCMP_RAWKEY. */
static void raw(int code,unsigned qualifier){
 int up;
 for(up=0;up<2;up++){
  int c=code|(up?0x80:0);
  Key_AmigaQualifiers(qualifier);
  if((c&0x7f)>=0x60 && (c&0x7f)<=0x67)continue;
  if(Key_AmigaRaw(c))Key_Event(Key_AmigaRaw(c),(c&0x80)==0);
 }
}
/* One raw key event (press or release) as Sys_SendKeyEvents routes it. */
static void raw_event(int code,int down,unsigned qualifier){
 int c=code|(down?0:0x80);
 Key_AmigaQualifiers(qualifier);
 if(Key_AmigaRaw(c))Key_Event(Key_AmigaRaw(c),(c&0x80)==0);
}
/* The main-keyboard raw code that types c (unshifted), from the engine's table. */
static int raw_for(int c){
 int r;
 for(r=0;r<0x60;r++)
  if(r!=0x0f && (r<0x1d || r>0x1f) && (r<0x2d || r>0x2f) && (r<0x3c || r>0x3f) && Key_AmigaRaw(r)==c)return r;
 assert(0);return 0;
}
static void type_text(const char *text){const char *p;for(p=text;*p;p++)raw(raw_for(*p),0);}
static void type_line(const char *text){type_text(text);raw(RAW_RETURN,0);}
static void expect(const char *line){
 /* The line ends at key_linepos, as Con_DrawInput shows and cuts it. */
 if(key_linepos!=(int)strlen(line) || strncmp(key_lines[edit_line],line,key_linepos)){
  fprintf(stderr,"edit line '%.*s', expected '%s'\n",key_linepos,key_lines[edit_line],line);assert(0);
 }
}
/* Terminal mode: the whole line and the cursor. */
static void line_is(const char *line,int cursor){
 if(strcmp(key_lines[edit_line],line) || key_linepos!=cursor){
  fprintf(stderr,"edit line '%s' cursor %d, expected '%s' cursor %d\n",key_lines[edit_line],key_linepos,line,cursor);assert(0);
 }
}
static void reset_console(void){
 int i;for(i=0;i<32;i++){key_lines[i][0]=']';key_lines[i][1]=0;}
 edit_line=history_line=0;key_linepos=1;queued[0]=0;con_backscroll=0;
}
static const char *saved(void){
 static char text[16384];size_t n=0;FILE *f=fopen("console-history.txt","rb");
 text[0]=0;if(f){n=fread(text,1,sizeof text-1,f);fclose(f);}text[n]=0;return text;
}
static void history_section(void);
static void terminal_section(void);
int main(void){
 Key_Init();AW_ControlsMigrate(); /* the arrows carry +forward/+back in the game */
 remove("console-history.txt");
 Key_ConsoleInit(".");assert(mode && !strcmp(mode->name,"aw_console_mode"));
 assert(Key_ConsoleTerminal()); /* default: terminal */
 set_mode("false");assert(!Key_ConsoleTerminal());set_mode("FALSE");assert(!Key_ConsoleTerminal());
 set_mode("0");assert(!Key_ConsoleTerminal());set_mode("true");assert(Key_ConsoleTerminal());
 set_mode("1");assert(Key_ConsoleTerminal());
 cls.state=ca_connected;key_dest=key_console;
 /* The history walk behaves the same in both modes. */
 set_mode("0");reset_console();history_section();
 assert(!*saved()); /* classic mode never writes the history file */
 set_mode("1");reset_console();history_section();
 terminal_section();
 return 0;
}
static void history_section(void){
 assert(Key_AmigaRaw(RAW_UP)==K_UPARROW && Key_AmigaRaw(RAW_DOWN)==K_DOWNARROW);
 raw(RAW_UP,0);expect("]"); /* nothing typed yet: Up keeps the empty line */
 /* Releases still queue "-forward" (id: key ups reach button bindings in
  * every mode), but a press in the console never starts a binding. */
 assert(!strstr(queued,"+forward"));
 queued[0]=0;
 type_line("echo one");type_line("echo two");type_line("echo three");
 assert(!strcmp(queued,"echo one\necho two\necho three\n"));
 raw(RAW_UP,0);expect("]echo three");
 raw(RAW_UP,0);expect("]echo two");
 raw(RAW_UP,0);expect("]echo one");
 /* Past the oldest entry Up stays on it; id's code showed an empty line here
  * and every further Up stayed empty until Down was pressed. */
 raw(RAW_UP,0);expect("]echo one");
 raw(RAW_UP,0);expect("]echo one");
 raw(RAW_DOWN,0);expect("]echo two");
 raw(RAW_DOWN,0);expect("]echo three");
 raw(RAW_DOWN,0);expect("]");
 raw(RAW_DOWN,0);expect("]");
 /* Shift+Up/Down page the scrollback and leave the line alone. */
 raw(RAW_UP,1);expect("]");assert(con_backscroll==10);
 raw(RAW_DOWN,2);expect("]");assert(con_backscroll==0);
 /* A recalled line runs again and becomes the newest entry. */
 raw(RAW_UP,0);raw(RAW_UP,0);expect("]echo two");
 assert(!strstr(queued,"+forward") && !strstr(queued,"+back"));
 queued[0]=0;raw(RAW_RETURN,0);assert(!strcmp(queued,"echo two\n"));
 raw(RAW_UP,0);expect("]echo two");raw(RAW_UP,0);expect("]echo three");
 /* The owner's FS-UAE trace (CONSOLE-HISTORY-ARROWS-32): every event carries
  * IEQUALIFIER_RELATIVEMOUSE (0x8000, mouse grabbed), and a held Down repeats
  * its press before the release. After a command: Down x4, Up, Down. */
 raw(RAW_DOWN,0);expect("]echo two");raw(RAW_DOWN,0);expect("]");type_line("echo ten");
 raw_event(RAW_DOWN,1,0x8000);raw_event(RAW_DOWN,0,0x8000);expect("]");
 raw_event(RAW_DOWN,1,0x8000);raw_event(RAW_DOWN,1,0x8000);raw_event(RAW_DOWN,0,0x8000);expect("]");
 raw_event(RAW_DOWN,1,0x8000);raw_event(RAW_DOWN,0,0x8000);
 raw_event(RAW_DOWN,1,0x8000);raw_event(RAW_DOWN,0,0x8000);expect("]");
 raw_event(RAW_UP,1,0x8000);expect("]echo ten");raw_event(RAW_UP,0,0x8000);
 raw_event(RAW_UP,1,0x8000);raw_event(RAW_UP,0,0x8000);expect("]echo two");
 raw_event(RAW_DOWN,1,0x8000);raw_event(RAW_DOWN,0,0x8000);expect("]echo ten");
 raw_event(RAW_DOWN,1,0x8000);raw_event(RAW_DOWN,0,0x8000);expect("]");
 /* Many Ups with few commands (the old code's permanent empty line). */
 { int i; for(i=0;i<8;i++){raw_event(RAW_UP,1,0x8000);raw_event(RAW_UP,0,0x8000);} }
 assert(key_linepos>1 && key_lines[edit_line][1]);
 /* The Amiga keypad has no cursor keys: 8 and 2 type digits. */
 history_line=edit_line;key_lines[edit_line][1]=0;key_linepos=1;
 raw(RAW_KEYPAD_8,0);raw(RAW_KEYPAD_2,0);expect("]82");
 history_line=edit_line;key_lines[edit_line][1]=0;key_linepos=1;
}
static void terminal_section(void){
 int i;FILE *f;
 set_mode("true");reset_console();remove("console-history.txt");
 /* Raw codes: Amiga Del is Delete, not F11; Home/End from a PC keyboard
  * (0x70/0x71) and from the FS-UAE preset's actions (0x6a/0x6c). */
 assert(Key_AmigaRaw(0x46)==K_DEL && Key_AmigaRaw(0x70)==K_HOME && Key_AmigaRaw(0x71)==K_END);
 assert(Key_AmigaRaw(0x6a)==K_HOME && Key_AmigaRaw(0x6c)==K_END && Key_AmigaRaw(0x45)==K_ESCAPE);
 /* Left/Right move without deleting; typing inserts at the cursor. */
 type_text("ech");line_is("]ech",4);
 raw(0x4f,0);raw(0x4f,0);line_is("]ech",2);
 type_text("x");line_is("]exch",3);
 raw(0x4e,0);line_is("]exch",4);
 raw(0x41,0);line_is("]exh",3);		/* Backspace deletes before the cursor */
 raw(0x46,0);line_is("]ex",3);		/* Delete deletes at the cursor */
 raw(0x46,0);line_is("]ex",3);		/* nothing after the cursor */
 raw(0x4e,0);line_is("]ex",3);		/* Right stops at the end */
 raw(0x70,0);line_is("]ex",1);raw(0x4f,0);line_is("]ex",1);
 raw(0x41,0);line_is("]ex",1);		/* Backspace at the start keeps the prompt */
 raw(0x71,0);line_is("]ex",3);
 raw(0x6a,0x8000);line_is("]ex",1);raw(0x6c,0x8000);line_is("]ex",3);
 /* Ctrl+A / Ctrl+E jump, Ctrl+U / Ctrl+K cut; no other Ctrl letter types,
  * and Ctrl in the console does not run its game binding. */
 Key_SetBinding(K_CTRL,"+attack");queued[0]=0;
 raw(raw_for('a'),8);line_is("]ex",1);
 raw(raw_for('e'),8);line_is("]ex",3);
 raw(raw_for('q'),8);line_is("]ex",3);
 raw(raw_for('a'),8|4);line_is("]ex",1);	/* with Caps Lock too */
 Key_AmigaQualifiers(0);assert(!strstr(queued,"+attack"));
 raw(0x71,0);type_text(" one two");line_is("]ex one two",11);
 for(i=0;i<4;i++)raw(0x4f,0);
 line_is("]ex one two",7);
 raw(raw_for('k'),8);line_is("]ex one",7);
 raw(0x4f,0);raw(0x4f,0);raw(0x4f,0);raw(raw_for('u'),8);line_is("]one",1);
 raw(raw_for('e'),8);line_is("]one",4);
 Key_AmigaQualifiers(0);
 /* Held Left and Delete repeat; held Up does not walk the history twice. */
 Key_Event(K_LEFTARROW,true);Key_Event(K_LEFTARROW,true);Key_Event(K_LEFTARROW,true);Key_Event(K_LEFTARROW,false);
 line_is("]one",1);
 Key_Event(K_DEL,true);Key_Event(K_DEL,true);Key_Event(K_DEL,false);line_is("]e",1);
 raw(0x46,0);line_is("]",1);
 /* Enter stores non-empty lines once: no empty or repeated entries. */
 type_line("echo one");type_line("echo two");type_line("echo two");raw(RAW_RETURN,0);type_line("echo three");
 assert(!strcmp(saved(),"echo one\necho two\necho three\n"));
 assert(edit_line==3);
 Key_Event(K_UPARROW,true);Key_Event(K_UPARROW,true);Key_Event(K_UPARROW,false);line_is("]echo three",11);
 raw(RAW_UP,0x8000);line_is("]echo two",9);
 raw(RAW_UP,0x8000);line_is("]echo one",9);
 raw(RAW_UP,0x8000);line_is("]echo one",9);
 raw(RAW_DOWN,0x8000);raw(RAW_DOWN,0x8000);line_is("]echo three",11);
 raw(RAW_DOWN,0x8000);line_is("]",1);
 /* Down past the newest entry returns the line being typed. */
 type_text("ech");raw(0x4f,0);line_is("]ech",3);
 raw(RAW_UP,0);line_is("]echo three",11);raw(RAW_UP,0);line_is("]echo two",9);
 raw(RAW_DOWN,0);raw(RAW_DOWN,0);line_is("]ech",4);
 raw(RAW_DOWN,0);line_is("]ech",4);
 /* A recalled line can be edited and run; it is stored as a new entry. */
 raw(0x41,0);raw(0x41,0);raw(0x41,0);raw(RAW_UP,0);line_is("]echo three",11);
 for(i=0;i<5;i++)raw(0x41,0);
 type_text("two");line_is("]echo two",9);
 queued[0]=0;raw(RAW_RETURN,0);assert(!strcmp(queued,"echo two\n"));
 assert(!strcmp(saved(),"echo one\necho two\necho three\necho two\n"));
 /* Tab completion, then typing continues after it. */
 type_text("ec");raw(0x42,0);line_is("]echo ",6);type_text("x");line_is("]echo x",7);
 /* Keypad 8/2 are digits, inserted at the cursor. */
 raw(0x4f,0);raw(RAW_KEYPAD_8,0);raw(RAW_KEYPAD_2,0);line_is("]echo 82x",8);
 /* Shift+Up/Down page and Shift+Home/End jump the scrollback; the line stays. */
 raw(RAW_UP,1);assert(con_backscroll==10);raw(0x70,2);assert(con_backscroll==100);
 raw(0x71,1);assert(con_backscroll==0);line_is("]echo 82x",8);
 Key_AmigaQualifiers(0);
 /* Classic mode on the same line: id's Left deletes, Right does nothing. */
 raw(0x71,0);set_mode("0");
 raw(0x4f,0);expect("]echo 82");raw(0x4e,0);expect("]echo 82");
 set_mode("1");key_lines[edit_line][key_linepos]=0;
 /* Saved history comes back at start-up, newest last. */
 reset_console();Key_ConsoleInit(".");
 assert(edit_line==4 && history_line==4);line_is("]",1);
 raw(RAW_UP,0);line_is("]echo two",9);raw(RAW_UP,0);line_is("]echo three",11);
 /* A longer file keeps its last 31 lines; CR LF and empty lines are skipped. */
 f=fopen("console-history.txt","wb");assert(f);
 for(i=0;i<40;i++)fprintf(f,"say %d\r\n",i);
 fclose(f);
 reset_console();Key_ConsoleInit(".");
 assert(edit_line==31);
 raw(RAW_UP,0);line_is("]say 39",7);
 for(i=0;i<40;i++)raw(RAW_UP,0);
 line_is("]say 9",6);
 f=fopen("console-history.txt","wb");assert(f);fputs("\n\nsay a\n\r\nsay b",f);fclose(f);
 reset_console();Key_ConsoleInit(".");assert(edit_line==2);
 raw(RAW_UP,0);line_is("]say b",6);raw(RAW_UP,0);line_is("]say a",6);
 /* No file: nothing loaded, nothing breaks. */
 remove("console-history.txt");reset_console();Key_ConsoleInit(".");assert(edit_line==0);
}
