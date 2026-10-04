#include "quakedef.h"
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

sizebuf_t net_message;
static qsocket_t writer, reader;
static byte outgoing[MAX_MSGLEN], incoming[NET_MAXMESSAGE];
extern int Loop_SendMessage(qsocket_t *, sizebuf_t *);
extern int Loop_GetMessage(qsocket_t *);

void Sys_Error(char *error, ...)
{
    fprintf(stderr, "%s", error);
    exit(2);
}
void Con_Printf(char *fmt, ...) { (void)fmt; }
void Con_DPrintf(char *fmt, ...) { (void)fmt; }

int main(void)
{
    sizebuf_t message;
    int i;
    if (sizeof(((server_t *)0)->signon_buf) != MAX_MSGLEN ||
        NET_MAXMESSAGE < MAX_MSGLEN + 4 || MAX_MSGLEN < 15000)
        return 10;
    memset(&writer, 0, sizeof(writer));
    memset(&reader, 0, sizeof(reader));
    writer.driverdata = &reader;
    reader.driverdata = &writer;
    net_message.data = incoming;
    net_message.maxsize = sizeof(incoming);
    memset(&message, 0, sizeof(message));
    message.data = outgoing;
    message.maxsize = sizeof(outgoing);
    message.cursize = MAX_MSGLEN;
    for (i = 0; i < message.cursize; i++) outgoing[i] = (byte)(i * 13);
    if (Loop_SendMessage(&writer, &message) != 1) return 11;
    if (Loop_GetMessage(&reader) != 1 || net_message.cursize != message.cursize)
        return 12;
    if (memcmp(incoming, outgoing, message.cursize) || reader.receiveMessageLength)
        return 13;
    if (!writer.canSend) return 14;
    return 0;
}
