.include "hdr.asm"

.section ".gfc_panel" superfree
panelTiles:
.incbin "assets/panel.pic"
panelTilesEnd:
panelMap:
.incbin "assets/panel.map"
panelPalette:
.incbin "assets/palette.pal"
.ends

.section ".gfc_font" superfree
fontTiles:
.incbin "assets/font.pic"
fontTilesEnd:
knobTiles:
.incbin "assets/knob.pic"
knobTilesEnd:
knobPalette:
.incbin "assets/knob.pal"
; Keep the continuation bank: the audio driver crosses banks dynamically,
; which the linker's unused-section removal cannot infer.
.dw SOUNDBANK__1
.ends

