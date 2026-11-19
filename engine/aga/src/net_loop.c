/*
Copyright (C) 1996-1997 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

*/
// net_loop.c

#include "quakedef.h"
#include "net_loop.h"
#include "aw_tryalloc.h"	/* the grown buffers: allocations that can say no (the Amiga's malloc traps instead) */

qboolean	localconnectpending = false;
qsocket_t	*loop_client = NULL;
qsocket_t	*loop_server = NULL;

/* NET-VIVEC-ENTITY-PACKET-OVERFLOW-66: what the game's server sends the client in this program arrives in an allocated
 * buffer that grows instead of the client socket's fixed array (NET_MAXMESSAGE), and the client reads each message
 * into net_message, which grows with it. sv_main.c sizes both at the first frame of a game (its settings
 * aw_net_buffer and aw_net_frame) and grows them between frames when a frame asks for more; never in the middle of a
 * message, never smaller. What is unread stays. The server's own receive buffer (the client's moves and commands)
 * keeps its fixed array. */
static byte *loop_receive;
static int loop_receive_size;
static byte *Loop_Buffer (qsocket_t *sock)
{
	return sock == loop_client && loop_receive ? loop_receive : sock->receiveMessage;
}
static int Loop_Size (qsocket_t *sock)
{
	return sock == loop_client && loop_receive ? loop_receive_size : NET_MAXMESSAGE;
}
int Loop_ReceiveSize (void)	/* the client's receive buffer now */
{
	return loop_receive ? loop_receive_size : NET_MAXMESSAGE;
}
int Loop_Unread (void)		/* what the client has not read yet */
{
	return loop_client ? loop_client->receiveMessageLength : 0;
}
/* Grow the client's receive buffer to RECEIVE bytes and net_message to MESSAGE bytes (each only when larger than now;
 * 0 leaves it). 1 when both are at least that large afterwards, 0 when memory was short (nothing changed then). */
int Loop_Grow (int receive, int message)
{
	byte *r = NULL, *m = NULL;
	if (receive > Loop_ReceiveSize ())
	{
		if (!(r = AW_TryMalloc (receive)))
			return 0;
		if (loop_client && loop_client->receiveMessageLength)
			Q_memcpy (r, Loop_Buffer (loop_client), loop_client->receiveMessageLength);
	}
	if (message > net_message.maxsize)
	{
		if (!(m = AW_TryMalloc (message)))
		{
			if (r)
				free (r);
			return 0;
		}
		if (net_message.cursize)
			Q_memcpy (m, net_message.data, net_message.cursize);
	}
	if (r)
	{
		if (loop_receive)
			free (loop_receive);
		loop_receive = r;
		loop_receive_size = receive;
	}
	if (m)
	{
		/* the first net_message is the Hunk's (net_main.c SZ_Alloc): never freed, only replaced */
		static byte *grown;
		if (grown)
			free (grown);
		grown = m;
		net_message.data = m;
		net_message.maxsize = message;
	}
	return 1;
}

int Loop_Init (void)
{
	if (cls.state == ca_dedicated)
		return -1;
	return 0;
}


void Loop_Shutdown (void)
{
}


void Loop_Listen (qboolean state)
{
}


void Loop_SearchForHosts (qboolean xmit)
{
	if (!sv.active)
		return;

	hostCacheCount = 1;
	if (Q_strcmp(hostname.string, "UNNAMED") == 0)
		Q_strcpy(hostcache[0].name, "local");
	else
		Q_strcpy(hostcache[0].name, hostname.string);
	Q_strcpy(hostcache[0].map, sv.name);
	hostcache[0].users = net_activeconnections;
	hostcache[0].maxusers = svs.maxclients;
	hostcache[0].driver = net_driverlevel;
	Q_strcpy(hostcache[0].cname, "local");
}


qsocket_t *Loop_Connect (char *host)
{
	if (Q_strcmp(host,"local") != 0)
		return NULL;

	localconnectpending = true;

	if (!loop_client)
	{
		if ((loop_client = NET_NewQSocket ()) == NULL)
		{
			Con_Printf("Loop_Connect: no qsocket available\n");
			return NULL;
		}
		Q_strcpy (loop_client->address, "localhost");
	}
	loop_client->receiveMessageLength = 0;
	loop_client->sendMessageLength = 0;
	loop_client->canSend = true;

	if (!loop_server)
	{
		if ((loop_server = NET_NewQSocket ()) == NULL)
		{
			Con_Printf("Loop_Connect: no qsocket available\n");
			return NULL;
		}
		Q_strcpy (loop_server->address, "LOCAL");
	}
	loop_server->receiveMessageLength = 0;
	loop_server->sendMessageLength = 0;
	loop_server->canSend = true;

	loop_client->driverdata = (void *)loop_server;
	loop_server->driverdata = (void *)loop_client;

	return loop_client;
}


qsocket_t *Loop_CheckNewConnections (void)
{
	if (!localconnectpending)
		return NULL;

	localconnectpending = false;
	loop_server->sendMessageLength = 0;
	loop_server->receiveMessageLength = 0;
	loop_server->canSend = true;
	loop_client->sendMessageLength = 0;
	loop_client->receiveMessageLength = 0;
	loop_client->canSend = true;
	return loop_server;
}


static int IntAlign(int value)
{
	return (value + (sizeof(int) - 1)) & (~(sizeof(int) - 1));
}


int Loop_GetMessage (qsocket_t *sock)
{
	int		ret;
	int		length;

	byte	*buffer = Loop_Buffer (sock);

	if (sock->receiveMessageLength == 0)
		return 0;

	/* the length is three bytes (a grown message is longer than 65535 bytes; NET-VIVEC-ENTITY-PACKET-OVERFLOW-66) */
	ret = buffer[0];
	length = buffer[1] + (buffer[2] << 8) + (buffer[3] << 16);
	SZ_Clear (&net_message);
	SZ_Write (&net_message, &buffer[4], length);

	length = IntAlign(length + 4);
	sock->receiveMessageLength -= length;

	if (sock->receiveMessageLength)
		Q_memcpy(buffer, &buffer[length], sock->receiveMessageLength);

	if (sock->driverdata && ret == 1)
		((qsocket_t *)sock->driverdata)->canSend = true;

	return ret;
}


int Loop_SendMessage (qsocket_t *sock, sizebuf_t *data)
{
	byte *buffer;
	int  *bufferLength;

	if (!sock->driverdata)
		return -1;

	bufferLength = &((qsocket_t *)sock->driverdata)->receiveMessageLength;

	/* NET-VIVEC-ENTITY-PACKET-OVERFLOW-66: the session ends (the way back or the place loaded again, the box), never
	 * the game; the server's frame message keeps room for this one (sv_main.c SV_LoopDatagramRoom) */
	if (IntAlign (*bufferLength + data->cursize + 4) > Loop_Size ((qsocket_t *)sock->driverdata))
		Host_Error("Loop_SendMessage: overflow (%ld unread, %ld more)", (long)*bufferLength, (long)data->cursize);

	buffer = Loop_Buffer ((qsocket_t *)sock->driverdata) + *bufferLength;

	// message type
	*buffer++ = 1;

	// length: three bytes (the fourth of the header was an unused alignment byte)
	*buffer++ = data->cursize & 0xff;
	*buffer++ = (data->cursize >> 8) & 0xff;
	*buffer++ = (data->cursize >> 16) & 0xff;

	// message
	Q_memcpy(buffer, data->data, data->cursize);
	*bufferLength = IntAlign(*bufferLength + data->cursize + 4);

	sock->canSend = false;
	return 1;
}


int Loop_SendUnreliableMessage (qsocket_t *sock, sizebuf_t *data)
{
	byte *buffer;
	int  *bufferLength;

	if (!sock->driverdata)
		return -1;

	bufferLength = &((qsocket_t *)sock->driverdata)->receiveMessageLength;

	/* the whole record (its 4-byte header, aligned) must fit: the old test counted 3 header bytes */
	if (IntAlign (*bufferLength + data->cursize + 4) > Loop_Size ((qsocket_t *)sock->driverdata))
		return 0;

	buffer = Loop_Buffer ((qsocket_t *)sock->driverdata) + *bufferLength;

	// message type
	*buffer++ = 2;

	// length: three bytes (the fourth of the header was an unused alignment byte)
	*buffer++ = data->cursize & 0xff;
	*buffer++ = (data->cursize >> 8) & 0xff;
	*buffer++ = (data->cursize >> 16) & 0xff;

	// message
	Q_memcpy(buffer, data->data, data->cursize);
	*bufferLength = IntAlign(*bufferLength + data->cursize + 4);
	return 1;
}


qboolean Loop_CanSendMessage (qsocket_t *sock)
{
	if (!sock->driverdata)
		return false;
	return sock->canSend;
}


qboolean Loop_CanSendUnreliableMessage (qsocket_t *sock)
{
	return true;
}


void Loop_Close (qsocket_t *sock)
{
	if (sock->driverdata)
		((qsocket_t *)sock->driverdata)->driverdata = NULL;
	sock->receiveMessageLength = 0;
	sock->sendMessageLength = 0;
	sock->canSend = true;
	if (sock == loop_client)
		loop_client = NULL;
	else
		loop_server = NULL;
}
