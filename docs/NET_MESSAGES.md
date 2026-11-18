# The frame message: what the game sends its screen side

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

The engine runs the world as an internal server and the picture as a client in the same program, as Quake does. Every
frame the server writes one message for the client: the time, the player's own state, an update for everything in
sight, then the frame's sounds and effects. This page says how that message is kept within its buffer, what happens
when something still goes wrong, and how to look at it in the game (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66).

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
| A network packet (`MAX_DATAGRAM`) | 1024 |
| The game's own connection (the loopback: both sides in this program) | up to 8192 |
| The loopback's receive buffer (`NET_MAXMESSAGE`), shared with the reliable message | 16384 |
| The largest update of one entity, computed from the message format | 28 with 3-byte coordinates |

The largest update is worked out from the format (the bits, the entity number, the model number, frame, colormap,
skin, effects, three coordinates, three angles and the AmiWind fields), never written down as a number, and a test
writes the largest update there is and checks it is exactly that size.

## How the message is filled

- Every update is built whole in its own buffer first, then copied into the message only when it fits. Nothing is
  written into the message that has not been measured.
- When everything in sight fits (almost always on the game's own connection), everything goes, in entity order.
- When it does not fit: the player first, then the actors (residents, creatures, guards: things that walk or fly)
  before still scenery (plants, items, static models), the nearest first, what is in front of the player before what
  is behind him. Every update that has to wait moves forward a step each frame, without a cap, so nothing waits for
  good: with 599 of the largest updates on a 1024-byte packet the longest wait is 21 frames, and the actors never wait.
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
code LF9. The same error again within a minute in the same map opens the load menu instead.

## Looking at it in the game

`dbg netstat` prints the last frame: how many things are in sight, the bytes their updates want against the room in
the message, how many went and how many wait for the next frames; the fullest frame since the map started; and the
models that took the most bytes in the last frame.

## Testing it

`tests/test_net_overflow.py` builds two native tests. `tests/aga_netsend_test.c` runs the real server code with 600
things in sight, each with the largest update: the message never runs past its buffer, everything in it reads back
whole, the creatures and the nearest go first, nothing waits more than a few frames, the game's own connection takes up
to 8 KB and keeps room for the reliable message, and an overflow that still happens is caught, said once and not sent.
It also shows the old rule running past the buffer. `tests/aga_netparse_test.c` runs the real client code on a cut
message and on an unreadable one: both are dropped without ending the game.

## Cost

Memory: the 8 KB message buffer of the game's own connection and the tables of one frame's order (about 6 KB), static.
Time: each update is built once and copied; only a frame that does not fit is sorted and built a second time for the
updates that go.
