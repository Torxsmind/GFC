#include <snes.h>
#include "assets.h"
#include "game.h"
#include "comments.h"
#include "assets/soundbank.h"

#define PANEL_MAP 0x6000
#define TEXT_MAP  0x6400
#define FONT_GFX  0x4000
#define KNOB_GFX  0x2000
#define TEXT_WHITE 1
#define TEXT_MUTED 2
#define TEXT_GREEN 3
#define TEXT_RED   4

/* These readable globals also let the emulator checks inspect the actual ROM. */
u8 gfcReady = 0;
u8 gfcCommentIndex = 0;
u8 gfcCommentPool = 4;
u8 gfcLastResult = GFC_TOGGLE;
u16 gfcFrame = 0;
u32 gfcChangeCount = 0;
char gfcScoreDigits[11] = "0000000000";
u16 textMap[1024];
u8 textDirty = 1;
u16 lastPad = 0;
u16 knobX[3];
/* Visual order differs from the state-bit and comment-pool order. */
u8 sliderBits[3] = {GFC_GOOD, GFC_FAST, GFC_CHEAP};
/* Music + effects occupy two LoROM banks; smconv suffixes the first label 0. */
extern u8 SOUNDBANK__0;

/* Each character occupies an 8x8 hardware tile. No printf, heap, or console
 * layer is needed. Drawing edits WRAM; a small DMA uploads it during VBlank. */
void textAt(u8 x, u8 y, const char *text, u8 palette)
{
    u16 pos = y * 32 + x;
    while (*text && x < 32) {
        textMap[pos++] = ((*text++) - 32) | (palette << 10) | BG_TIL_PRIO;
        x++;
    }
    textDirty = 1;
}

void clearLine(u8 y)
{
    u8 x;
    for (x = 0; x < 32; x++) textMap[y * 32 + x] = 0;
    textDirty = 1;
}

void showScore(void)
{
    u8 pos = 0, length, x, pair;
    while (pos < 4 && gfcScoreDigits[pos] == '0') pos++;
    length = 10 - pos;
    x = 31 - ((length + 1) >> 1);
    clearLine(0);
    if (length & 1) {
        pair = 100 + gfcScoreDigits[pos++] - '0';
        textMap[x++] = (120 + pair) | (TEXT_WHITE << 10) | BG_TIL_PRIO;
    }
    while (pos < 10) {
        pair = (gfcScoreDigits[pos] - '0') * 10 + gfcScoreDigits[pos+1] - '0';
        textMap[x++] = (120 + pair) | (TEXT_WHITE << 10) | BG_TIL_PRIO;
        pos += 2;
    }
}

void countPress(void)
{
    u8 pos = 10;
    gfcChangeCount++;
    /* Decimal carry avoids slow 32-bit division on the SNES CPU. */
    while (pos) {
        pos--;
        if (gfcScoreDigits[pos] < '9') {
            gfcScoreDigits[pos]++;
            break;
        }
        gfcScoreDigits[pos] = '0';
    }
}

void showState(void)
{
    u8 row, bit, x, y;
    for (row = 0; row < 3; row++) {
        bit = sliderBits[row];
        textAt(14, 8 + row * 4, (gfcState & bit) ? "ON " : "OFF",
               (gfcState & bit) ? TEXT_GREEN : TEXT_MUTED);
        for (y = 0; y < 3; y++) {
            for (x = 0; x < 8; x++) {
                textMap[(7 + row * 4 + y) * 32 + 18 + x] = (gfcState & bit) ?
                    (96 + y * 8 + x) | (5 << 10) | BG_TIL_PRIO : 0;
            }
        }
    }
}

void chooseComment(void)
{
    u8 pool = gfcPool(gfcState);
    u8 previous = gfcCommentIndex;
    if (gfcReady && pool == gfcCommentPool) {
        /* Select uniformly from the other 23 comments without retrying. */
        gfcCommentIndex = gfcRandomBelow(23);
        if (gfcCommentIndex >= previous) gfcCommentIndex++;
    } else {
        gfcCommentIndex = gfcRandomBelow(24);
    }
    gfcCommentPool = pool;
    clearLine(21);
    clearLine(23);
    textAt(2, 21, gfcComments[gfcCommentPool][gfcCommentIndex][0], TEXT_WHITE);
    textAt(2, 23, gfcComments[gfcCommentPool][gfcCommentIndex][1], TEXT_WHITE);
}

void playEffect(u8 effect)
{
    /* Preloaded samples: click=0, reject=1, kick=2. 2 means 8kHz, centered. */
    spcEffect(2, effect, 12 * 16 + 8);
}

void toggle(u8 bit)
{
    gfcLastResult = gfcToggle(bit);
    if (gfcLastResult == GFC_REJECT) {
        clearLine(21);
        clearLine(23);
        textAt(2, 21, "NICE TRY. PICK AT LEAST ONE.", TEXT_RED);
        textAt(2, 23, "CHAOS STILL NEEDS A SPEC.", TEXT_WHITE);
        playEffect(1);
    } else {
        showState();
        chooseComment();
        playEffect((gfcLastResult == GFC_KICK) ? 2 : 0);
    }
}

void animateKnobs(void)
{
    u8 row, bit;
    u16 target;
    for (row = 0; row < 3; row++) {
        bit = sliderBits[row];
        target = (gfcState & bit) ? 184 : 152;
        if (knobX[row] < target) knobX[row] += 4;
        if (knobX[row] > target) knobX[row] -= 4;
        oamSet(row * 4, knobX[row], 62 + row * 32, 3, 0, 0, 0,
               (gfcState & bit) ? 0 : 1);
    }
}

int main(void)
{
    u16 pad, pressed, i;
    u8 row;
    /* All bulk DMA happens with the screen blanked by the library startup. */
    spcBoot();
    spcSetBank(&SOUNDBANK__0);
    spcAllocateSoundRegion(0);
    spcStop();
    spcLoad(MOD_MUSIC);
    for (row = 0; row < 3; row++) spcLoadEffect(row);
    spcSetModuleVolume(95); /* quieter bed; slider effects remain clear */
    spcPlay(0);

    dmaCopyVram(&panelTiles, 0, &panelTilesEnd - &panelTiles);
    dmaCopyVram(&panelMap, PANEL_MAP, 2048);
    dmaCopyCGram(&panelPalette, 0, 256);
    dmaCopyVram(&fontTiles, FONT_GFX, &fontTilesEnd - &fontTiles);
    oamInitGfxSet(&knobTiles, &knobTilesEnd - &knobTiles,
                 &knobPalette, 64, 0, KNOB_GFX, OBJ_SIZE16_L32);
    for (i = 0; i < 1024; i++) textMap[i] = 0;
    for (row = 0; row < 3; row++) {
        knobX[row] = (gfcState & sliderBits[row]) ? 184 : 152;
        oamSet(row * 4, knobX[row], 62 + row * 32, 3, 0, 0, 0,
               (gfcState & sliderBits[row]) ? 0 : 1);
        oamSetEx(row * 4, OBJ_SMALL, OBJ_SHOW);
    }
    setMode(BG_MODE1, 0);
    bgSetGfxPtr(0, 0);
    bgSetMapPtr(0, PANEL_MAP, SC_32x32);
    bgSetGfxPtr(1, FONT_GFX);
    bgSetMapPtr(1, TEXT_MAP, SC_32x32);
    bgSetScroll(0, 0, 0);
    bgSetScroll(1, 0, 0);
    bgSetDisable(2);
    showState();
    chooseComment();
    showScore();
    dmaCopyVram((u8 *)textMap, TEXT_MAP, 2048);
    textDirty = 0;
    setScreenOn();
    gfcReady = 1;

    while (1) {
        /* Prepare outside VBlank. WaitForVBlank uploads OAM via the library
         * ISR; then upload only 2KB of text while VRAM is safely writable. */
        spcProcess();
        WaitForVBlank();
        if (textDirty) {
            dmaCopyVram((u8 *)textMap, TEXT_MAP, 2048);
            textDirty = 0;
        }
        gfcFrame++;
        gfcRandomNext();
        pad = padsCurrent(0);
        pressed = pad & ~lastPad; /* edge-triggered: holding never repeats */
        lastPad = pad;
        /* Count each action-button edge, including rejected choices. Holding
         * never repeats. Simultaneous buttons each count; SELECT retains priority. */
        if (pressed & KEY_X) countPress();
        if (pressed & KEY_Y) countPress();
        if (pressed & KEY_A) countPress();
        if (pressed & KEY_B) countPress();
        if (pressed & KEY_SELECT) countPress();
        if (pressed & (KEY_X | KEY_Y | KEY_A | KEY_B | KEY_SELECT)) showScore();
        if (pressed & KEY_SELECT) {
            gfcState = GFC_DEFAULT;
            gfcLastResult = GFC_TOGGLE;
            showState();
            chooseComment();
            playEffect(0);
        } else {
            /* Simultaneous edges are handled in this stable X, A, B, Y order.
             * Every intermediate state still satisfies the one-or-two rule. */
            if (pressed & KEY_X) toggle(GFC_FAST);
            if (pressed & KEY_A) toggle(GFC_CHEAP);
            if (pressed & KEY_B) toggle(GFC_GOOD);
            if (pressed & KEY_Y) {
                gfcRandomize();
                gfcLastResult = GFC_TOGGLE;
                showState();
                chooseComment();
                playEffect(0);
            }
        }
        animateKnobs();
    }
    return 0;
}
