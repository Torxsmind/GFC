ifeq ($(strip $(PVSNESLIB_HOME)),)
$(error Set PVSNESLIB_HOME to your PVSnesLib directory; see README.md)
endif

export ROMNAME := gfc
export ROMTITLE := GOOD FAST CHEAP
SRC := src
AUDIOFILES := assets/effects.it assets/music.it
export SOUNDBANK := assets/soundbank
include $(PVSNESLIB_HOME)/devkitsnes/snes_rules
SMCONVFLAGS := -s -o $(SOUNDBANK) -V -b 5

# Invoke the real build directly: propagate compiler/linker errors to the shell.
.PHONY: all clean
all: $(ROMNAME).sfc
src/main.obj: src/assets.h src/game.h src/comments.h assets/soundbank.h
assets/soundbank.h: assets/soundbank.asm
	@test -f $@
src/game.obj: src/game.h
src/assets.obj: assets/panel.pic assets/panel.map assets/palette.pal assets/font.pic assets/knob.pic assets/knob.pal
clean: cleanBuildRes cleanRom
