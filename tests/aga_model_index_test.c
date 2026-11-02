/* ENGINE-MODEL-TABLE-58: a model index above 255 round-trips through the message writer and reader
 * (protocol.h MSG_WriteModel / MSG_ReadModel), and every model-numbered table follows MAX_MODELS. */
#include "quakedef.h"
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

sizebuf_t net_message;
static byte buffer[256];

void Sys_Error(char *error, ...)
{
    fprintf(stderr, "%s", error);
    exit(2);
}
void Con_Printf(char *fmt, ...) { (void)fmt; }
void Con_DPrintf(char *fmt, ...) { (void)fmt; }

int main(void)
{
    static const int index[] = {0, 1, 255, 256, 257, 300, 511, MAX_MODELS - 1};
    int i, n = (int)(sizeof(index) / sizeof(index[0]));
    if (MAX_MODELS < 512 || PROTOCOL_VERSION != AW_COORD_PROTOCOL + 1)
        return 10;
#ifndef AW_COORD_NARROW
    if (PROTOCOL_VERSION != 1016)
        return 11;
#endif
    if (sizeof(((server_t *)0)->model_precache) / sizeof(char *) != MAX_MODELS ||
        sizeof(((server_t *)0)->models) / sizeof(struct model_s *) != MAX_MODELS ||
        sizeof(((client_state_t *)0)->model_precache) / sizeof(struct model_s *) != MAX_MODELS ||
        AW_EDGE_CACHE_MODEL_LIMIT != MAX_MODELS)
        return 12;
    memset(&net_message, 0, sizeof(net_message));
    net_message.data = buffer;
    net_message.maxsize = sizeof(buffer);
    for (i = 0; i < n; i++)
    {
        MSG_WriteModel(&net_message, index[i]);
        MSG_WriteByte(&net_message, 0x5a);             /* the next field stays in step */
    }
    if (net_message.cursize != n * 3)
        return 13;
    MSG_BeginReading();
    for (i = 0; i < n; i++)
    {
        int back = MSG_ReadModel();
        if (back != index[i])
        {
            printf("index %d read back as %d\n", index[i], back);
            return 14;
        }
        if (MSG_ReadByte() != 0x5a)
            return 15;
    }
    if (msg_badread)
        return 16;
    printf("model index round trip ok, MAX_MODELS %d, protocol %d\n", MAX_MODELS, PROTOCOL_VERSION);
    return 0;
}
