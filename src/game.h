#ifndef GFC_GAME_H
#define GFC_GAME_H

#include <snes.h>

#define GFC_FAST  1
#define GFC_CHEAP 2
#define GFC_GOOD  4
#define GFC_DEFAULT (GFC_FAST | GFC_GOOD)
#define GFC_REJECT 0
#define GFC_TOGGLE 1
#define GFC_KICK   2

extern u8 gfcState;
extern u16 gfcRandom;
u16 gfcRandomNext(void);
u8 gfcRandomBelow(u8 bound);
u8 gfcToggle(u8 selected);
u8 gfcPool(u8 state);

#endif
