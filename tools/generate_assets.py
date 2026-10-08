"""Rebuild all original GFC art, SNESMOD effects, and comment data. No packages.

Run with Python 3.10+. Outputs are checked in, so Python is optional to compile.
SNES graphics use native 4bpp tiles, RGB555 palettes, and a 32x32 tilemap.
"""
from pathlib import Path
import json
import struct
import textwrap
import zlib

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

# Original 5x7 pixel alphabet, one row per five-bit mask. No external font.
FONT = {
    "A": [14,17,17,31,17,17,17], "B": [30,17,17,30,17,17,30],
    "C": [14,17,16,16,16,17,14], "D": [30,17,17,17,17,17,30],
    "E": [31,16,16,30,16,16,31], "F": [31,16,16,30,16,16,16],
    "G": [14,17,16,23,17,17,15], "H": [17,17,17,31,17,17,17],
    "I": [14,4,4,4,4,4,14], "J": [7,2,2,2,18,18,12],
    "K": [17,18,20,24,20,18,17], "L": [16,16,16,16,16,16,31],
    "M": [17,27,21,21,17,17,17], "N": [17,25,21,19,17,17,17],
    "O": [14,17,17,17,17,17,14], "P": [30,17,17,30,16,16,16],
    "Q": [14,17,17,17,21,18,13], "R": [30,17,17,30,20,18,17],
    "S": [15,16,16,14,1,1,30], "T": [31,4,4,4,4,4,4],
    "U": [17,17,17,17,17,17,14], "V": [17,17,17,17,17,10,4],
    "W": [17,17,17,21,21,21,10], "X": [17,17,10,4,10,17,17],
    "Y": [17,17,10,4,4,4,4], "Z": [31,1,2,4,8,16,31],
    "0": [14,17,19,21,25,17,14], "1": [4,12,4,4,4,4,14],
    "2": [14,17,1,2,4,8,31], "3": [30,1,1,14,1,1,30],
    "4": [2,6,10,18,31,2,2], "5": [31,16,16,30,1,1,30],
    "6": [14,16,16,30,17,17,14], "7": [31,1,2,4,8,8,8],
    "8": [14,17,17,14,17,17,14], "9": [14,17,17,15,1,1,14],
    " ": [0]*7, ".": [0,0,0,0,0,12,12], ",": [0,0,0,0,0,4,8],
    ":": [0,12,12,0,12,12,0], ";": [0,12,12,0,0,4,8],
    "!": [4,4,4,4,4,0,4], "?": [14,17,1,2,4,0,4],
    "-": [0,0,0,31,0,0,0], "/": [1,1,2,4,8,16,16],
    "+": [0,4,4,31,4,4,0], "'": [4,4,8,0,0,0,0],
    "(": [2,4,8,8,8,4,2], ")": [8,4,2,2,2,4,8],
}
COLORS = [
    "141c28", "192332", "0b111a", "353e47", "454e56", "59636a",
    "8a959c", "e9e6da", "fff9e8", "c3c8bf", "509d92", "8bd6b0",
    "677c94", "e78f75", "a5bed7", "293340",
]
RGB = [tuple(bytes.fromhex(c)) for c in COLORS]


class Canvas:
    def __init__(self, w, h, color=0):
        self.w, self.h = w, h
        self.p = [[color]*w for _ in range(h)]

    def pixel(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y][x] = color

    def rect(self, x, y, w, h, color, radius=0):
        for yy in range(y, y+h):
            for xx in range(x, x+w):
                dx = max(x+radius-xx, 0, xx-(x+w-1-radius))
                dy = max(y+radius-yy, 0, yy-(y+h-1-radius))
                if dx*dx+dy*dy <= radius*radius:
                    self.pixel(xx, yy, color)

    def text(self, x, y, value, color=7, scale=1, spacing=6):
        for ch in value.upper():
            for yy, bits in enumerate(FONT[ch]):
                for xx in range(5):
                    if bits & (1 << (4-xx)):
                        self.rect(x+xx*scale, y+yy*scale, scale, scale, color)
            x += spacing*scale

    def center(self, y, value, color=7, spacing=6):
        self.text((self.w-(len(value)*spacing-1))//2, y, value, color, spacing=spacing)


def tile4bpp(pixels):
    """SNES bitplanes 0/1 interleaved, then bitplanes 2/3 interleaved."""
    out = bytearray()
    for pair in (0, 2):
        for row in pixels:
            for plane in (pair, pair+1):
                out.append(sum(((v >> plane) & 1) << (7-x) for x,v in enumerate(row)))
    return bytes(out)


def chunk(kind, data):
    return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data))


def png(path, canvas):
    rows = b"".join(b"\0"+bytes(v for c in row for v in RGB[c]) for row in canvas.p)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" +
                     chunk(b"IHDR",struct.pack(">IIBBBBB",canvas.w,canvas.h,8,2,0,0,0)) +
                     chunk(b"IDAT",zlib.compress(rows)) + chunk(b"IEND",b""))


def graphics():
    c = Canvas(256,224)
    c.center(14, "GOOD / FAST / CHEAP", 7, spacing=7)
    c.center(30, "CHOOSE YOUR ARCHITECTURE PRINCIPLES", 12)
    c.rect(20,52,216,110,2,10)   # panel shadow
    c.rect(20,48,216,110,6,10)   # one-pixel beveled edge
    c.rect(21,49,214,108,4,9)
    c.rect(22,51,212,105,3,8)
    # Quiet, deterministic stippling recalls the reference's textured panel.
    for y in range(54,153):
        for x in range(27,229):
            if (x*13+y*7) % 47 == 0:
                c.pixel(x,y,4)
    for row,(label,button,color) in enumerate((("GOOD","B",11),("FAST","X",14),("CHEAP","A",13))):
        y = 62+row*32
        c.text(35,y+2,label,2,2)
        c.text(34,y,label,8,2)
        c.rect(148,y,56,18,5,8)
        c.rect(149,y+1,54,16,2,7)
        c.rect(151,y+7,50,2,3)
        c.rect(194,y+7,4,2,10)
        c.rect(208,y,18,18,2,8)
        c.rect(209,y,16,16,color,7)
        c.text(214,y+4,button,2)
        if row < 2:
            c.rect(34,y+24,190,1,4)
    c.rect(12,164,232,36,15,5)
    c.rect(13,165,230,34,1,4)
    c.center(210,"START: RESET   ONE OR TWO ONLY",12)
    # Deduplicate the static screen. Include tile zero as an empty background.
    tiles = [tile4bpp([[0]*8 for _ in range(8)])]
    lookup = {tiles[0]:0}
    tilemap = []
    for ty in range(32):
        for tx in range(32):
            pixels = [[c.p[y][x] if y<c.h else 0 for x in range(tx*8,tx*8+8)]
                      for y in range(ty*8,ty*8+8)]
            tile = tile4bpp(pixels)
            if tile not in lookup:
                lookup[tile] = len(tiles)
                tiles.append(tile)
            tilemap.append(lookup[tile])
    assert len(tiles)*32 <= 0x4000, "Panel overlaps OBJ VRAM"
    (ASSETS/"panel.pic").write_bytes(b"".join(tiles))
    (ASSETS/"panel.map").write_bytes(struct.pack("<1024H",*tilemap))
    # BG1 palette 0; BG2 palettes 1..4. Font foreground=1, shadow=2.
    pals = list(RGB)
    for foreground in (7,6,11,13):
        pals.extend([RGB[0],RGB[foreground],RGB[2]]+[RGB[0]]*13)
    pals.extend([RGB[0]]*(128-len(pals)))
    (ASSETS/"palette.pal").write_bytes(b"".join(struct.pack("<H", (r>>3)|((g>>3)<<5)|((b>>3)<<10)) for r,g,b in pals))
    font = []
    for code in range(32,128):
        glyph = Canvas(8,8)
        ch = chr(code).upper()
        if ch in FONT:
            for yy,bits in enumerate(FONT[ch]):
                for xx in range(5):
                    if bits & (1 << (4-xx)):
                        glyph.pixel(xx+2,yy+1,2)
            for yy,bits in enumerate(FONT[ch]):
                for xx in range(5):
                    if bits & (1 << (4-xx)):
                        glyph.pixel(xx+1,yy,1)
        font.append(tile4bpp(glyph.p))
    # White ON rails overlay the static dark OFF rails on BG2. The 64x24
    # patch aligns to hardware tiles; transparent margins preserve the panel.
    rail = Canvas(64,24)
    rail.rect(4,6,56,18,6,8)
    rail.rect(5,7,54,16,9,7)
    rail.rect(7,8,50,12,7,6)
    rail.rect(10,8,44,1,8)
    for ty in range(3):
        for tx in range(8):
            font.append(tile4bpp([r[tx*8:tx*8+8] for r in rail.p[ty*8:ty*8+8]]))
    (ASSETS/"font.pic").write_bytes(b"".join(font))
    # BG2 palette 5 is the base art palette, used by the white rail patch.
    pals[80:96] = RGB
    (ASSETS/"palette.pal").write_bytes(b"".join(struct.pack("<H", (r>>3)|((g>>3)<<5)|((b>>3)<<10)) for r,g,b in pals))
    knob = Canvas(16,16)
    knob.rect(1,1,15,15,2,7)
    knob.rect(0,0,15,15,9,7)
    knob.rect(1,0,13,12,7,6)
    knob.rect(3,1,9,6,8,3)
    knob.rect(5,12,6,1,6)
    # OBJ tiles use a 16-tile row stride: second half begins at tile 16.
    obj = [bytes(32) for _ in range(18)]
    for ty in range(2):
        for tx in range(2):
            obj[ty*16+tx] = tile4bpp([r[tx*8:tx*8+8] for r in knob.p[ty*8:ty*8+8]])
    (ASSETS/"knob.pic").write_bytes(b"".join(obj))
    dim = list(RGB)
    dim[7], dim[8], dim[9] = RGB[5], RGB[6], RGB[4]
    (ASSETS/"knob.pal").write_bytes(b"".join(struct.pack("<H",(r>>3)|((g>>3)<<5)|((b>>3)<<10)) for r,g,b in RGB+dim))
    # Preview combines the same pixels, font spacing, and default knob positions.
    for row,on in enumerate((True,True,False)):
        c.text(113,64+row*32,"ON" if on else "OFF",11 if on else 6,spacing=8)
        if on:
            for yy,r in enumerate(rail.p):
                for xx,v in enumerate(r):
                    if v: c.pixel(144+xx,56+row*32+yy,v)
        for yy,r in enumerate(knob.p):
            for xx,v in enumerate(r):
                if v: c.pixel((184 if on else 152)+xx,62+row*32+yy, ({7:5,8:6,9:4}.get(v,v) if not on else v))
    c.text(17,168,"ON TIME. ON SPEC.",7,spacing=8)
    c.text(17,184,"OFF BUDGET.",7,spacing=8)
    png(ASSETS/"preview.png",c)
    print(f"Graphics: {len(tiles)} unique panel tiles, original 5x7 font, 16x16 knob")


def sounds():
    generated = []
    for name,duration in (("click",0.055),("reject",0.13),("kick",0.085)):
        samples = []
        phase = 0.0
        count = int(8000*duration)
        for i in range(count):
            t = i/count
            hz = (1200+600*t) if name=="click" else (145 if name=="reject" else 1700-950*t)
            phase += hz/8000
            pulse = 1 if phase%1<0.5 else -1
            env = min(1,i/12)*(1-t)**2
            samples.append(round(11000*pulse*env))
        generated.append((name,samples))
    # Minimal Impulse Tracker module: three signed, 16-bit, non-looping samples
    # and an empty pattern. smconv packs the samples for preloaded SNESMOD SFX.
    # Preloading at boot avoids freezing input while streaming each click.
    data = bytearray(192)
    data[:4] = b"IMPM"
    data[4:4+len(b"GFC ORIGINAL EFFECTS")] = b"GFC ORIGINAL EFFECTS"
    struct.pack_into("<8H",data,32,2,0,3,1,0x214,0x214,1,0)
    data[48:54] = bytes((128,48,6,125,128,0))
    data[64:128] = bytes([32]*64)
    data[128:192] = bytes([64]*64)
    data.extend(bytes((0,255)))
    for i in range(3): data.extend(struct.pack("<I",210+i*80))
    data.extend(struct.pack("<I",0)) # empty pattern
    sample_pos = 210+3*80
    for name,samples in generated:
        header = bytearray(80)
        header[:4] = b"IMPS"
        header[17:20] = bytes((64,3,64))
        header[20:20+len(name)] = name.encode("ascii")
        header[46] = 1 # signed PCM
        header[47] = 32
        struct.pack_into("<I",header,48,len(samples))
        struct.pack_into("<I",header,60,8000)
        struct.pack_into("<I",header,72,sample_pos)
        sample_pos += len(samples)*2
        data.extend(header)
    for _,samples in generated: data.extend(struct.pack(f"<{len(samples)}h",*samples))
    (ASSETS/"effects.it").write_bytes(data)
    print("Audio: three original 8kHz mono effects; effects.it for preloaded SFX")


def comments():
    pools = json.loads((ASSETS/"comments.json").read_text(encoding="utf-8"))
    expected = ["FAST only","CHEAP only","GOOD only","FAST + CHEAP","FAST + GOOD","CHEAP + GOOD"]
    assert list(pools) == expected
    assert len({c for pool in pools.values() for c in pool}) == 144
    header = ["/* Generated by tools/generate_assets.py from assets/comments.json. */",
              "#ifndef GFC_COMMENTS_H", "#define GFC_COMMENTS_H",
              "static const char gfcComments[6][24][2][29] = {"]
    document = ["# All 144 comments", "", "Source: [assets/comments.json](../assets/comments.json). Each pool has 24 entries.", ""]
    for state,pool in pools.items():
        assert len(pool)==24, state
        header.append(f"    {{ /* {state} */")
        document += [f"## {state}", ""]
        for index,comment in enumerate(pool,1):
            assert all(ch.upper() in FONT for ch in comment), comment
            lines = textwrap.wrap(comment.upper(),28,break_long_words=False,break_on_hyphens=False)
            assert len(lines)<=2 and all(len(line)<=28 for line in lines), comment
            lines += [""]*(2-len(lines))
            header.append("        {"+", ".join(json.dumps(line) for line in lines)+"},")
            document.append(f"{index}. {comment}")
        header.append("    },")
        document.append("")
    header += ["};", "#endif", ""]
    (ROOT/"src/comments.h").write_text("\n".join(header),encoding="ascii")
    (ROOT/"docs").mkdir(exist_ok=True)
    (ROOT/"docs/comments.md").write_text("\n".join(document),encoding="utf-8")
    print("Comments: 6 pools x 24 unique entries, wrapped to 2 x 28 characters")


if __name__ == "__main__":
    comments()
    graphics()
    sounds()
