# The frame message: what the game sends its screen side

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

The engine runs the world as an internal server and the picture as a client in the same program, as Quake does. Every
frame the server writes one message for the client: the time, the player's own state, an update for everything in
sight, then the frame's sounds and effects. This page says how that message is kept within its buffer, how its room
grows, the two ways of filling it, what happens when something still goes wrong, and how to look at it in the game
(NET-VIVEC-ENTITY-PACKET-OVERFLOW-66).

## What went wrong before

The message was 1024 bytes and the updates went in in entity order. The loop stopped ("packet overflow") once fewer
than 16 bytes were left, but an update has taken up to 21 bytes since the 3-byte coordinates of v0.0.36, 22 since the
2-byte model numbers of v0.0.59-dev4, and the AmiWind fields of v0.0.52 (a scale, a frame over 255) were reserved on
top. Where many things are in sight at once (Vivec, the Bitter Coast with its plants and creatures), the last update
could run up to 6 bytes past the buffer, whose overflow was never set up to be caught: the message was cleared and
written on from the middle of an update, and the client stopped on it ("CL_ParseServerMessage: Illegible server
message"), leaving the loading screen up. In every full frame the highest entity numbers were left out: the creatures
and residents a town joins last.

## The limits

| What | Bytes |
| --- | --- |
| A network packet (`MAX_DATAGRAM`), for a client on the network | 1024 |
| The frame message's room on the game's own connection (the loopback: both sides in this program), at the start | 32768 (`aw_net_frame`) |
| The largest room it grows to | 262144 (`aw_net_max`) |
| The client's receive buffer on the game's own connection, at the start; it is always at least the room plus a reliable message | 65536 (`aw_net_buffer`) |
| A reliable message (`MAX_MSGLEN`), unchanged | 16380 |
| The largest update of one entity, computed from the message format | 28 with 3-byte coordinates |

The largest update is worked out from the format (the bits, the entity number, the model number, frame, colormap,
skin, effects, three coordinates, three angles and the AmiWind fields), never written down as a number, and a test
writes the largest update there is and checks it is exactly that size. With every entity the engine holds in sight at
once, the fullest frame today is about 18 KB, so the starting room already takes it whole.

## How the room grows

The frame buffer and the client's receive buffer are allocated, not fixed arrays. When a frame wants more than three
quarters of its room, the room doubles for the next frame (never in the middle of a message; what the client has not
read yet is kept), up to `aw_net_max`, and the console says so once per growth:
"Frame message: the room grows from 32768 to 65536 bytes for the next frame (a frame on MAP wanted N)". Nothing shrinks
while a map runs. A raised setting counts from the next frame on. At the largest room, a frame that still does not fit
sends the nearest first (below), with one console line. The length of a message on the game's own connection is three
bytes, so a grown message can be longer than 65535 bytes; a recorded demo of grown frames plays back.

## The two methods

`aw_net_method` switches between two ways of filling the message, live from the console and saved with the settings:

- **1, FULL**: every update in sight goes every frame, the room growing as needed.
- **2, PACED**: at most `aw_net_send` bytes of updates a frame (4096 at the start), the nearest first, the rest in the
  next frames.

The default is the method that measured better in the game ([performance/NET_FRAME.md](performance/NET_FRAME.md):
frame time, the client's reading time and the waits, at Vivec, on the Bitter Coast and in the wilderness).

## How the message is filled

- Every update is built whole in its own buffer first, then copied into the message only when it fits. Nothing is
  written into the message that has not been measured.
- When everything in sight fits, everything goes, in entity order.
- When it does not fit (PACED past its budget, FULL at its largest room, a client on the network): the player first,
  then the actors (residents, creatures, guards: things that walk or fly) before still scenery (plants, items, static
  models), the nearest first, what is in front of the player before what is behind him. Every update that has to wait
  moves forward a step each frame, without a cap, so nothing waits for good: with 599 of the largest updates on a
  1024-byte packet the longest wait is 21 frames, and the actors never wait.
- The frame's sounds and effects keep their room after the entities.
- The game's own connection keeps room in its receive buffer for this frame's reliable message and for whatever the
  client has not read yet.

## When something still overflows

Every message buffer allows its overflow explicitly, so an overflow marks the buffer instead of stopping the game.
Where the buffer is sent, a marked one is dropped whole and the console says so at most once every 30 seconds
("Message overflow caught"): the frame's message, its sounds and effects, a broadcast to every client, the client's
own commands and moves. A sign-on that does not fit ends that load: the way back and the box
([LOAD_ERRORS.md](LOAD_ERRORS.md)).

On the client, a frame's message that is cut short, or holds a byte no command starts with, is dropped with one console
line ("Frame update dropped", at most one every 10 seconds) and the next frame's message reads as usual. A reliable
message that does not read still ends the session.

An error in play, when no load is running, no longer ends the game: the place the player is in loads again, he stands
where he was, and the box says why: "An error stopped the game in <map>; it was loaded again." with the error and the
code LF9. The same error again within a minute loads the last autosave, then the previous map; the load menu opens
only when all of them fail ([LOAD_ERRORS.md](LOAD_ERRORS.md)).

## Looking at it in the game

`dbg netstat` prints the method and its budget, the room and the receive buffer and how often they grew; the last
frame: how many things are in sight, the bytes their updates want against the budget, how many went and how many wait;
since the map started (or since `dbg netstat reset`, which starts a new measuring window): the fullest frame and how
close it came to the room in percent, the longest and the average wait, the frame time and the client's reading time
per frame; and the models that took the most bytes in the last frame.

## Testing it

`tests/test_net_overflow.py` builds two native tests. `tests/aga_netsend_test.c` runs the real server code with 600
things in sight, each with the largest update: the message never runs past its buffer, everything in it reads back
whole, the creatures and the nearest go first, nothing waits more than a few frames, and an overflow that still happens
is caught, said once and not sent. FULL: a frame larger than the room grows it and goes whole the next frame; a raised
setting counts, nothing shrinks; at the largest room the nearest go first without an overflow. PACED stays within its
budget with the creatures in it. It also shows the old rule running past the buffer. `tests/aga_netparse_test.c` runs
the real client code on a cut message and on an unreadable one (both dropped without ending the game) and reads a
grown message of 70000 bytes whole through the game's own connection.

## Cost

Memory, allocated at the first frame of a game: the frame buffer (32 KB), the client's receive buffer (64 KB) and the
client's message buffer (32 KB), 128 KB at the start settings and about 0.8 MB at `aw_net_max`; the tables of one
frame's order (about 6 KB), static. Time: each update is built once and copied; only a frame that does not fit is
sorted and built a second time for the updates that go.
