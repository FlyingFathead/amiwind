/*
Copyright (C) 2000 Peter McGavin.

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
// net_udp.c

#include "quakedef.h"

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <sys/param.h>
#include <sys/ioctl.h>
#include <errno.h>

#include <exec/exec.h>
#ifdef __PPC__
#if defined(__STORM__) || defined(__VBCC__)
#include <clib/exec_protos.h>
#else
#include <proto/exec.h>
#endif
#include <clib/socket_protos.h>
#else
#include <proto/exec.h>
#include <proto/socket.h>
#endif

extern void I_Error (char *error, ...);
extern cvar_t hostname;

struct Library *SocketBase = NULL;

static int net_acceptsocket = -1;		// socket for fielding new connections
static int net_controlsocket = -1;
static int net_broadcastsocket = 0;
static struct qsockaddr broadcastaddr;

static unsigned long myAddr;

#include "net_udp.h"

//=============================================================================

int UDP_Init (void)
{
	struct hostent *local;
	char	buff[MAXHOSTNAMELEN];
	struct qsockaddr addr;
	char *colon;
	
//	Con_Printf ("UDP_Init()\n");
	if (COM_CheckParm ("-noudp"))
		return -1;

        if ((SocketBase = OpenLibrary ("bsdsocket.library", 0)) == NULL) {
          Con_Printf ("OpenLibrary(\"bsdsocket.library\") failed, no networking available\n");
          return -1;
        }

	// determine my name & address
	gethostname(buff, MAXHOSTNAMELEN);
	local = gethostbyname(buff);
	myAddr = *(int *)local->h_addr_list[0];

	// if the quake hostname isn't set, set it to the machine name
	if (Q_strcmp(hostname.string, "UNNAMED") == 0)
	{
		buff[15] = 0;
		Cvar_Set ("hostname", buff);
	}

	if ((net_controlsocket = UDP_OpenSocket (0)) == -1)
		Sys_Error("UDP_Init: Unable to open control socket\n");

	((struct sockaddr_in *)&broadcastaddr)->sin_family = AF_INET;
	((struct sockaddr_in *)&broadcastaddr)->sin_addr.s_addr = INADDR_BROADCAST;
	((struct sockaddr_in *)&broadcastaddr)->sin_port = htons(net_hostport);

	UDP_GetSocketAddr (net_controlsocket, &addr);
	Q_strcpy(my_tcpip_address,  UDP_AddrToString (&addr));
	colon = Q_strrchr (my_tcpip_address, ':');
	if (colon)
		*colon = 0;

	Con_Printf("UDP Initialized\n");
	tcpipAvailable = true;

	return net_controlsocket;
}

//=============================================================================

void UDP_Shutdown (void)
{
//	Con_Printf ("UDP_Shutdown()\n");
	if (SocketBase != NULL) {
		UDP_Listen (false);
		if (net_controlsocket != -1) {
			UDP_CloseSocket (net_controlsocket);
			net_controlsocket = -1;
		}
		CloseLibrary (SocketBase);
		SocketBase = NULL;
	}
}

//=============================================================================

void UDP_Listen (qboolean state)
{
//	Con_Printf ("UDP_Listen()\n");
	// enable listening
	if (state)
	{
		if (net_acceptsocket != -1)
			return;
		if ((net_acceptsocket = UDP_OpenSocket (net_hostport)) == -1)
			Sys_Error ("UDP_Listen: Unable to open accept socket\n");
		return;
	}

	// disable listening
	if (net_acceptsocket == -1)
		return;
	UDP_CloseSocket (net_acceptsocket);
	net_acceptsocket = -1;
}

//=============================================================================

int UDP_OpenSocket (int port)
{
	int newsocket;
	struct sockaddr_in address;
	long _true = true;

//	Con_Printf ("UDP_OpenSocket()\n");
	if ((newsocket = socket (PF_INET, SOCK_DGRAM, IPPROTO_UDP)) == -1)
		return -1;

	if (IoctlSocket (newsocket, FIONBIO, (char *)&_true) == -1)
		goto ErrorReturn;

	address.sin_family = AF_INET;
	address.sin_addr.s_addr = INADDR_ANY;
	address.sin_port = htons(port);
	if( bind (newsocket, (void *)&address, sizeof(address)) == -1)
		goto ErrorReturn;

	return newsocket;

ErrorReturn:
	CloseSocket (newsocket);
	return -1;
}

//=============================================================================

int UDP_CloseSocket (int socket)
{
//	Con_Printf ("UDP_CloseSocket()\n");
	if (socket == net_broadcastsocket)
		net_broadcastsocket = 0;
	return CloseSocket (socket);
}


//=============================================================================
/*
============
PartialIPAddress

this lets you type only as much of the net address as required, using
the local network components to fill in the rest
============
*/
static int PartialIPAddress (char *in, struct qsockaddr *hostaddr)
{
	char buff[256];
	char *b;
	int addr;
	int num;
	int mask;
	int run;
	int port;
	
//	Con_Printf ("UDP_PartialIPAddress()\n");
	buff[0] = '.';
	b = buff;
	strcpy(buff+1, in);
	if (buff[1] == '.')
		b++;

	addr = 0;
	mask=-1;
	while (*b == '.')
	{
		b++;
		num = 0;
		run = 0;
		while (!( *b < '0' || *b > '9'))
		{
		  num = num*10 + *b++ - '0';
		  if (++run > 3)
		  	return -1;
		}
		if ((*b < '0' || *b > '9') && *b != '.' && *b != ':' && *b != 0)
			return -1;
		if (num < 0 || num > 255)
			return -1;
		mask<<=8;
		addr = (addr<<8) + num;
	}
	
	if (*b++ == ':')
		port = Q_atoi(b);
	else
		port = net_hostport;

	((struct sockaddr_in *)hostaddr)->sin_family = AF_INET;
	((struct sockaddr_in *)hostaddr)->sin_port = htons((short)port);	
	((struct sockaddr_in *)hostaddr)->sin_addr.s_addr = (myAddr & htonl(mask)) | htonl(addr);
	
	return 0;
}
//=============================================================================

int UDP_Connect (int socket, struct qsockaddr *addr)
{
//	Con_Printf ("UDP_Connect()\n");
	return 0;
}

//=============================================================================

int UDP_CheckNewConnections (void)
{
	long	available;

//	Con_Printf ("UDP_CheckNewConnections()\n");
	if (net_acceptsocket == -1)
		return -1;

	if (IoctlSocket (net_acceptsocket, FIONREAD, (char *)&available) == -1)
		Sys_Error ("UDP: ioctlsocket (FIONREAD) failed\n");
	if (available)
		return net_acceptsocket;
	return -1;
}

//=============================================================================

int UDP_Read (int socket, byte *buf, int len, struct qsockaddr *addr)
{
	LONG addrlen = sizeof (struct qsockaddr);
	int ret;
	long err;

//	Con_Printf ("UDP_Read()\n");
	ret = recvfrom (socket, buf, len, 0, (struct sockaddr *)addr, &addrlen);
	err = Errno();
	if (ret == -1 && (err == EWOULDBLOCK || err == ECONNREFUSED))
		return 0;
	return ret;
}

//=============================================================================

int UDP_MakeSocketBroadcastCapable (int socket)
{
	int				i = 1;

//	Con_Printf ("UDP_MakeSocketBroadcastCapable()\n");
	// make this socket broadcast capable
	if (setsockopt(socket, SOL_SOCKET, SO_BROADCAST, (char *)&i, sizeof(i)) < 0)
		return -1;
	net_broadcastsocket = socket;

	return 0;
}

//=============================================================================

int UDP_Broadcast (int socket, byte *buf, int len)
{
	int ret;

//	Con_Printf ("UDP_Broadcast()\n");
	if (socket != net_broadcastsocket)
	{
		if (net_broadcastsocket != 0)
			Sys_Error("Attempted to use multiple broadcasts sockets\n");
		ret = UDP_MakeSocketBroadcastCapable (socket);
		if (ret == -1)
		{
			Con_Printf("Unable to make socket broadcast capable\n");
			return ret;
		}
	}

	return UDP_Write (socket, buf, len, &broadcastaddr);
}

//=============================================================================

int UDP_Write (int socket, byte *buf, int len, struct qsockaddr *addr)
{
	int ret;

//	Con_Printf ("UDP_Write()\n");
	ret = sendto (socket, buf, len, 0, (struct sockaddr *)addr, sizeof(struct qsockaddr));
	if (ret == -1 && Errno() == EWOULDBLOCK)
		return 0;
	return ret;
}

//=============================================================================

char *UDP_AddrToString (struct qsockaddr *addr)
{
	static char buffer[22];
	int haddr;

//	Con_Printf ("UDP_AddrToString()\n");
	haddr = ntohl(((struct sockaddr_in *)addr)->sin_addr.s_addr);
	sprintf(buffer, "%d.%d.%d.%d:%d", (haddr >> 24) & 0xff,
	        (haddr >> 16) & 0xff, (haddr >> 8) & 0xff, haddr & 0xff,
	        ntohs(((struct sockaddr_in *)addr)->sin_port));
	return buffer;
}

//=============================================================================

int UDP_StringToAddr (char *string, struct qsockaddr *addr)
{
	int ha1, ha2, ha3, ha4, hp;
	int ipaddr;

//	Con_Printf ("UDP_StringToAddr()\n");
	sscanf(string, "%d.%d.%d.%d:%d", &ha1, &ha2, &ha3, &ha4, &hp);
	ipaddr = (ha1 << 24) | (ha2 << 16) | (ha3 << 8) | ha4;

	((struct sockaddr_in *)addr)->sin_family = AF_INET;
	((struct sockaddr_in *)addr)->sin_addr.s_addr = htonl(ipaddr);
	((struct sockaddr_in *)addr)->sin_port = htons(hp);
	return 0;
}

//=============================================================================

int UDP_GetSocketAddr (int socket, struct qsockaddr *addr)
{
	LONG addrlen = sizeof(struct qsockaddr);
	unsigned int a;

//	Con_Printf ("UDP_GetSocketAddr()\n");
	Q_memset(addr, 0, sizeof(struct qsockaddr));
	getsockname(socket, (struct sockaddr *)addr, &addrlen);
	a = ((struct sockaddr_in *)addr)->sin_addr.s_addr;
	if (a == 0 || a == inet_addr("127.0.0.1"))
		((struct sockaddr_in *)addr)->sin_addr.s_addr = myAddr;

	return 0;
}

//=============================================================================

int UDP_GetNameFromAddr (struct qsockaddr *addr, char *name)
{
	struct hostent *hostentry;

//	Con_Printf ("UDP_GetNameFromAddr()\n");
	hostentry = gethostbyaddr ((char *)&((struct sockaddr_in *)addr)->sin_addr, sizeof(struct in_addr), AF_INET);
	if (hostentry)
	{
		Q_strncpy (name, (char *)hostentry->h_name, NET_NAMELEN - 1);
		return 0;
	}

	Q_strcpy (name, UDP_AddrToString (addr));
	return 0;
}

//=============================================================================

int UDP_GetAddrFromName(char *name, struct qsockaddr *addr)
{
	struct hostent *hostentry;

//	Con_Printf ("UDP_GetAddrFromName()\n");
	if (name[0] >= '0' && name[0] <= '9')
		return PartialIPAddress (name, addr);
	
	hostentry = gethostbyname (name);
	if (!hostentry)
		return -1;

	((struct sockaddr_in *)addr)->sin_family = AF_INET;
	((struct sockaddr_in *)addr)->sin_port = htons(net_hostport);	
	((struct sockaddr_in *)addr)->sin_addr.s_addr = *(int *)hostentry->h_addr_list[0];

	return 0;
}

//=============================================================================

int UDP_AddrCompare (struct qsockaddr *addr1, struct qsockaddr *addr2)
{
//	Con_Printf ("UDP_AddrCompare()\n");

	if (((struct sockaddr_in *)addr1)->sin_family !=
            ((struct sockaddr_in *)addr2)->sin_family)
		return -1;

	if (((struct sockaddr_in *)addr1)->sin_addr.s_addr !=
            ((struct sockaddr_in *)addr2)->sin_addr.s_addr)
		return -1;

	if (((struct sockaddr_in *)addr1)->sin_port !=
            ((struct sockaddr_in *)addr2)->sin_port)
		return 1;

	return 0;
}

//=============================================================================

int UDP_GetSocketPort (struct qsockaddr *addr)
{
//	Con_Printf ("UDP_GetSocketPort()\n");
	return ntohs(((struct sockaddr_in *)addr)->sin_port);
}


int UDP_SetSocketPort (struct qsockaddr *addr, int port)
{
	((struct sockaddr_in *)addr)->sin_port = htons(port);
	return 0;
}

/**********************************************************************/

#ifdef __SASC
void _STD_UDP_Shutdown (void)
{
//  Con_Printf ("_STD_UDP_Shutdown()\n");
  UDP_Shutdown ();
}
#endif

/**********************************************************************/
#ifdef __STORM__
void EXIT_9_UDP_Shutdown (void)
{
//  Con_Printf ("EXIT_9_UDP_Shutdown()\n");
  UDP_Shutdown ();
}
#endif

/**********************************************************************/
#ifdef __VBCC__
void _EXIT_9_UDP_Shutdown (void)
{
//  Con_Printf ("_EXIT_9_UDP_Shutdown()\n");
  UDP_Shutdown ();
}
#endif

/**********************************************************************/
