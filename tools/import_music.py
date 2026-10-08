"""Convert a phrase of a supplied MP3 into a one-channel looping IT module.

Dependencies: miniaudio and numpy (workspace-local .tools/python-packages works).
The resulting music.it is self-contained; ordinary ROM builds need no MP3.
"""
from pathlib import Path
import argparse
import json
import struct
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".tools/python-packages"))
import miniaudio
import numpy as np


def pattern(first=False):
    # IT packed pattern: note C5, sample 1, volume 48, then blank rows.
    rows = bytearray((0x81, 7, 60, 1, 48, 0)) if first else bytearray((0,))
    rows.extend(bytes(62))
    # Pattern 1 loops to itself without retriggering the already-looping sample.
    rows.extend(bytes((0x81, 8, 2, 1, 0))) # B01 position jump
    return struct.pack("<HHI", len(rows), 64, 0) + rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--start", type=float, default=0.137)
    parser.add_argument("--seconds", type=float, default=12.96)
    parser.add_argument("--rate", type=int, default=6000)
    args = parser.parse_args()
    if args.rate < 4000 or args.rate > 8000 or args.seconds*args.rate > 92000:
        parser.error("Use 4-8kHz and at most 92000 samples to fit SNES audio RAM")
    info = miniaudio.get_file_info(str(args.source))
    audio = miniaudio.decode_file(str(args.source), nchannels=1, sample_rate=args.rate)
    source = np.asarray(audio.samples, dtype=np.float64)
    begin = round(args.start*args.rate)
    length = round(args.seconds*args.rate)//16*16
    if begin < 0 or begin+length > len(source):
        parser.error("Loop range is outside the supplied audio")
    samples = source[begin:begin+length].copy()
    # Remove DC and normalize with headroom. Blend endpoint differences gently
    # over 12ms to prevent a BRR loop-boundary click without shifting beat timing.
    samples -= samples.mean()
    samples *= 23000/max(1,np.max(np.abs(samples)))
    cross = min(round(args.rate*0.012), length//8)
    midpoint = (samples[0]+samples[-1])/2
    samples[:cross] += (midpoint-samples[0])*np.linspace(1,0,cross)
    samples[-cross:] += (midpoint-samples[-1])*np.linspace(0,1,cross)
    pcm = np.clip(np.rint(samples),-32768,32767).astype("<i2").tobytes()
    # IT: 3 orders [intro, sustain, end], 1 instrument/sample, 2 patterns.
    # SNESMOD music needs instrument mode; a sample-only IT is sufficient only
    # for our effects bank, whose samples are triggered directly from C.
    data = bytearray(192)
    data[:4] = b"IMPM"
    title = b"GFC BACKGROUND LOOP"
    data[4:4+len(title)] = title
    struct.pack_into("<8H",data,32,3,1,1,2,0x214,0x214,5,0)
    data[48:54] = bytes((128,48,12,148,128,0))
    data[64:128] = bytes([32]+[160]*63) # one active music channel
    data[128:192] = bytes([64]*64)
    data.extend(bytes((0,1,255)))
    instrument_offset = 192+3+4+4+8
    instrument = bytearray(554)
    instrument[:4] = b"IMPI"
    instrument[23:26] = bytes((60,128,32))
    struct.pack_into("<H",instrument,28,0x214)
    instrument[30] = 1
    instrument[32:36] = b"LOOP"
    for note in range(120):
        instrument[64+note*2:66+note*2] = bytes((note,1))
    sample_header = instrument_offset+len(instrument)
    p0, p1 = pattern(True), pattern(False)
    pattern0 = sample_header+80
    pattern1 = pattern0+len(p0)
    sample_data = pattern1+len(p1)
    data.extend(struct.pack("<4I",instrument_offset,sample_header,pattern0,pattern1))
    h = bytearray(80)
    h[:4] = b"IMPS"
    h[17:20] = bytes((64,19,64)) # present, 16-bit, forward loop
    h[20:24] = b"LOOP"
    h[46:48] = bytes((1,32)) # signed, centered
    struct.pack_into("<4I",h,48,length,0,length,args.rate)
    struct.pack_into("<I",h,72,sample_data)
    data.extend(instrument+h+p0+p1+pcm)
    (ROOT/"assets/music.it").write_bytes(data)
    (ROOT/"build").mkdir(exist_ok=True)
    with wave.open(str(ROOT/"build/music-loop-preview.wav"),"wb") as wav:
        wav.setparams((1,2,args.rate,0,"NONE","not compressed"))
        wav.writeframes(pcm*2)
    metadata = dict(source_name=args.source.name, source_duration_seconds=info.duration,
                    start_seconds=args.start, loop_seconds=length/args.rate,
                    sample_rate=args.rate, music_channels=1,
                    expected_brr_bytes=length//16*9)
    (ROOT/"assets/music.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(metadata,indent=2))


if __name__ == "__main__":
    main()
