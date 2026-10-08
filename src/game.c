#include "game.h"

u8 gfcState = GFC_DEFAULT;
u16 gfcRandom = 0xACE1;

/* Nonzero xorshift16: full 65535-value period. Advanced every frame, so human
 * press timing changes the sequence. This is a toy, not a secure RNG. */
u16 gfcRandomNext(void)
{
    gfcRandom ^= gfcRandom << 7;
    gfcRandom ^= gfcRandom >> 9;
    gfcRandom ^= gfcRandom << 8;
    return gfcRandom;
}

/* Rejection sampling avoids the modulo bias of rand % 24. */
u8 gfcRandomBelow(u8 bound)
{
    u8 value;
    u16 limit = 256 - (256 % bound);
    do {
        value = gfcRandomNext() >> 8;
    } while (value >= limit);
    return value % bound;
}

u8 gfcToggle(u8 selected)
{
    u8 others, victim;
    if (gfcState & selected) {
        if (gfcState == selected) return GFC_REJECT;
        gfcState ^= selected;
        return GFC_TOGGLE;
    }
    /* Two bits means two existing choices. Pick one of those, never selected.
     * Compute the final valid mask before committing; 0 and 7 are never stored. */
    others = gfcState;
    if ((others & (others - 1)) != 0) {
        victim = others & (0 - others); /* lowest of the two active bits */
        if (gfcRandomNext() & 1) victim = others ^ victim;
        gfcState = (others ^ victim) | selected;
        return GFC_KICK;
    }
    gfcState |= selected;
    return GFC_TOGGLE;
}

/* Canonical comment-pool order: FAST, CHEAP, GOOD, F+C, F+G, C+G. */
u8 gfcPool(u8 state)
{
    switch (state) {
        case GFC_FAST: return 0;
        case GFC_CHEAP: return 1;
        case GFC_GOOD: return 2;
        case GFC_FAST | GFC_CHEAP: return 3;
        case GFC_FAST | GFC_GOOD: return 4;
        default: return 5; /* CHEAP | GOOD; callers always hold a valid mask. */
    }
}
