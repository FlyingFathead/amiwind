/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include <stdarg.h>
client_static_t cls;client_state_t cl;sizebuf_t net_message;
cmd_source_t cmd_source=src_command;int host_framecount=100;double realtime=3;
static byte payload[MAX_MSGLEN];static int conversions;
static const char *mock_track;static int missing;
static int same_long(int value){conversions++;return value;}
static float same_float(float value){return value;}
int (*LittleLong)(int)=same_long;float (*LittleFloat)(float)=same_float;
void Con_Printf(char *format,...){(void)format;}
void Sys_Error(char *format,...){(void)format;assert(!"Malformed demo caused fatal exit");abort();}
void CL_Disconnect(void){CL_StopPlayback();cls.state=ca_disconnected;}
int NET_GetMessage(struct qsocket_s *socket){(void)socket;return 0;}
int Cmd_Argc(void){return 2;}
char *Cmd_Argv(int index){return index?"fixture":"timedemo";}
void COM_DefaultExtension(char *name,char *extension){(void)name;(void)extension;}
qboolean COM_FormatPath(char *out,int size,const char *format,...){
    va_list ap;int n;va_start(ap,format);n=vsnprintf(out,size,format,ap);va_end(ap);
    if(n<0 || n>=size){if(size>0)out[0]=0;return false;}return true;
}
int COM_FOpenFile(char *name,FILE **file){
    (void)name;if(missing){*file=NULL;return -1;}
    *file=tmpfile();assert(*file);assert(fwrite(mock_track,1,strlen(mock_track),*file)==strlen(mock_track));
    rewind(*file);return strlen(mock_track);
}
static void reset(const void *data,int bytes){
    memset(&cls,0,sizeof(cls));memset(&cl,0,sizeof(cl));cls.state=ca_connected;
    cls.demoplayback=true;cls.demofile=tmpfile();assert(cls.demofile);
    if(bytes)assert(fwrite(data,1,bytes,cls.demofile)==(size_t)bytes);
    rewind(cls.demofile);net_message.data=payload;net_message.maxsize=sizeof(payload);net_message.cursize=42;conversions=0;
}
static void stopped(void){assert(CL_GetMessage()==0);assert(!cls.demoplayback && !cls.demofile && cls.state==ca_disconnected);}
int main(void){
    byte packet[32]={0};int size=2,i;float angles[3]={12,34,56};
    reset(NULL,0);stopped();assert(!conversions); /* no swap of stale EOF length */
    memcpy(packet,&size,4);memcpy(packet+4,angles,12);packet[16]=svc_nop;packet[17]=svc_disconnect;
    for(i=1;i<18;i++){reset(packet,i);stopped();assert(net_message.cursize==42);}
    reset(packet,18);assert(CL_GetMessage()==1);assert(net_message.cursize==2 && payload[0]==svc_nop && payload[1]==svc_disconnect);
    for(i=0;i<3;i++)assert(cl.mviewangles[0][i]==angles[i]);stopped();assert(conversions==1);
    for(i=0;i<3;i++){size=i==0?-1:i==1?0:MAX_MSGLEN+1;memcpy(packet,&size,4);reset(packet,4);stopped();}
    mock_track="-1\n";cls.demonum=0;CL_TimeDemo_f();assert(cls.demoplayback && cls.timedemo && cls.demonum==-1 && cls.forcetrack==-1);CL_StopPlayback();
    mock_track="-0\n";CL_PlayDemo_f();assert(cls.demoplayback && cls.forcetrack==0);CL_StopPlayback();
    mock_track="2147483647\n";CL_PlayDemo_f();assert(cls.demoplayback && cls.forcetrack==2147483647);CL_StopPlayback();
    mock_track="-2147483648\n";CL_PlayDemo_f();assert(cls.demoplayback && cls.forcetrack==(-2147483647-1));CL_StopPlayback();
    {const char *invalid[]={"","-1","x\n","\n","--1\n","2147483648\n","-2147483649\n","00000000000\n"};
     for(i=0;i<8;i++){mock_track=invalid[i];CL_TimeDemo_f();assert(!cls.demoplayback && !cls.timedemo && !cls.demofile);}}
    missing=1;CL_TimeDemo_f();assert(!cls.demoplayback && !cls.timedemo);
    puts("Demo EOF/truncation/size/track guards and startup timedemo loop state passed.");return 0;
}
