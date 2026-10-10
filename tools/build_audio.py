#!/usr/bin/env python3
"""Synthesise every sound in the game from assets_src/audio/.

Nothing is sampled: square, triangle, saw, sine and noise oscillators run
through an ADSR envelope and are written as 44100 Hz 16-bit stereo WAV.

    assets_src/audio/sfx.json        one entry per sound effect
    assets_src/audio/songs/*.song    tiny tracker JSON, one entry per track
        -> assets/audio/sfx/<name>.wav
        -> assets/audio/music/<name>.wav

    python tools/build_audio.py [--only sfx|music] [--force]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets_src" / "audio"
OUT = ROOT / "assets" / "audio"
RATE = 44100

#: named ADSR shapes, in seconds except sustain level
ENVELOPES: dict[str, tuple[float, float, float, float]] = {
    #        attack  decay  sustain  release
    "hit":    (0.001, 0.04, 0.00, 0.03),
    "pluck":  (0.004, 0.06, 0.35, 0.08),
    "blip":   (0.002, 0.02, 0.00, 0.02),
    "pad":    (0.030, 0.10, 0.70, 0.18),
    "organ":  (0.010, 0.02, 0.90, 0.10),
    "swell":  (0.090, 0.10, 0.80, 0.25),
    "stab":   (0.002, 0.12, 0.10, 0.06),
    "bell":   (0.001, 0.30, 0.15, 0.40),
    "long":   (0.010, 0.05, 0.85, 0.35),
}

NOTE_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_freq(name: str) -> float:
    """Frequency of a note name such as C4, F#3 or Bb5 (A4 = 440 Hz)."""
    letter = name[0].upper()
    semi = NOTE_SEMITONE[letter]
    i = 1
    while i < len(name) and name[i] in "#b":
        semi += 1 if name[i] == "#" else -1
        i += 1
    octave = int(name[i:])
    midi = 12 * (octave + 1) + semi
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def osc(wave_name: str, phase: float, duty: float, rng: random.Random, state: list[float]) -> float:
    """One sample of an oscillator at ``phase`` in [0, 1)."""
    if wave_name == "square":
        return 1.0 if (phase % 1.0) < duty else -1.0
    if wave_name == "triangle":
        p = phase % 1.0
        return 4.0 * abs(p - 0.5) - 1.0
    if wave_name == "saw":
        return 2.0 * (phase % 1.0) - 1.0
    if wave_name == "sine":
        return math.sin(2.0 * math.pi * phase)
    if wave_name == "noise":
        if phase - state[0] >= 1.0 or state[0] == 0.0:
            state[0] = phase
            state[1] = rng.uniform(-1.0, 1.0)
        return state[1]
    raise ValueError(f"unknown wave {wave_name!r}")


def envelope(n: int, name: str, hold: float) -> list[float]:
    """ADSR gain curve of ``n`` samples; ``hold`` is the gate length in seconds."""
    a, d, s, r = ENVELOPES.get(name, ENVELOPES["pluck"])
    out: list[float] = []
    gate = int(hold * RATE)
    for i in range(n):
        t = i / RATE
        if i >= gate:
            tail = (i - gate) / RATE
            level = s if s > 0 else 0.0
            g = max(0.0, level * (1.0 - tail / r)) if r > 0 else 0.0
        elif t < a:
            g = t / a if a > 0 else 1.0
        elif t < a + d:
            g = 1.0 - (1.0 - s) * ((t - a) / d if d > 0 else 1.0)
        else:
            g = s
        out.append(max(0.0, min(1.0, g)))
    return out


def render_tone(wave_name: str, f0: float, f1: float, dur: float, vol: float,
                env: str, duty: float = 0.5, hold: float | None = None,
                vibrato: float = 0.0, seed: int = 1) -> list[float]:
    """One note or blip: a frequency sweep from f0 to f1 through an envelope."""
    n = max(1, int(dur * RATE))
    gains = envelope(n, env, dur if hold is None else hold)
    rng = random.Random(seed)
    state = [0.0, 0.0]
    buf: list[float] = []
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = f0 + (f1 - f0) * t
        if vibrato:
            freq *= 1.0 + vibrato * math.sin(2.0 * math.pi * 6.0 * i / RATE)
        phase += freq / RATE
        buf.append(osc(wave_name, phase, duty, rng, state) * gains[i] * vol)
    return buf


def mix_into(dst: list[float], src: list[float], offset: int) -> None:
    """Add ``src`` into ``dst`` starting at sample ``offset``, growing dst as needed."""
    need = offset + len(src)
    if len(dst) < need:
        dst.extend([0.0] * (need - len(dst)))
    for i, v in enumerate(src):
        dst[offset + i] += v


def write_wav(path: Path, mono: list[float], pan: float = 0.0) -> None:
    """Write a mono buffer as 16-bit stereo, soft-clipped."""
    path.parent.mkdir(parents=True, exist_ok=True)
    left = 0.5 * (1.0 - pan)
    right = 0.5 * (1.0 + pan)
    frames = bytearray()
    for v in mono:
        v = math.tanh(v)
        frames += struct.pack("<hh", int(v * left * 32767 * 2), int(v * right * 32767 * 2))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))


# ----- sound effects -----------------------------------------------------
def build_sfx(force: bool) -> int:
    """Render every entry of assets_src/audio/sfx.json."""
    spec = json.loads((SRC / "sfx.json").read_text(encoding="utf-8"))
    count = 0
    for name, entry in spec.items():
        if name.startswith("_"):
            continue
        path = OUT / "sfx" / f"{name}.wav"
        if path.exists() and not force:
            count += 1
            continue
        buf: list[float] = []
        for seg in entry["segments"]:
            tone = render_tone(
                seg.get("wave", "square"), float(seg["f0"]), float(seg.get("f1", seg["f0"])),
                float(seg["dur"]), float(seg.get("vol", 0.4)), seg.get("env", "hit"),
                float(seg.get("duty", 0.5)), seg.get("hold"), float(seg.get("vib", 0.0)),
                seed=abs(hash(name)) % 9973 + 1)
            mix_into(buf, tone, int(float(seg.get("at", 0.0)) * RATE))
        write_wav(path, buf, float(entry.get("pan", 0.0)))
        count += 1
    print(f"  sfx: {count} sounds")
    return count


# ----- music -------------------------------------------------------------
def _rows(pattern: list[str] | str) -> list[str]:
    """A channel pattern as row tokens.

    A plain string is split on spaces. ``C4:4`` means "this note, held four
    rows" and expands to ``C4 . . .``; ``r:4`` is four rows of rest.
    """
    tokens = pattern.split() if isinstance(pattern, str) else list(pattern)
    rows: list[str] = []
    for token in tokens:
        head, _, count = token.partition(":")
        n = int(count) if count else 1
        head = "-" if head == "r" else head
        rows.append(head)
        rows.extend(["." if head not in ("-", ".") else "-"] * (n - 1))
    return rows


def render_song(song: dict) -> list[float]:
    """Render one .song tracker file to a mono buffer."""
    bpm = float(song.get("bpm", 120))
    rows_per_beat = int(song.get("rows_per_beat", 4))
    row_seconds = 60.0 / bpm / rows_per_beat
    total_rows = max(len(_rows(ch["pattern"])) for ch in song["channels"])
    buf: list[float] = [0.0] * int(total_rows * row_seconds * RATE + RATE)
    for ci, ch in enumerate(song["channels"]):
        pattern = _rows(ch["pattern"])
        row = 0
        while row < len(pattern):
            token = pattern[row].strip()
            if token in (".", "-", ""):
                row += 1
                continue
            length = 1
            while row + length < len(pattern) and pattern[row + length].strip() == ".":
                length += 1
            dur = length * row_seconds
            freq = note_freq(token)
            tone = render_tone(ch.get("wave", "square"), freq, freq * float(ch.get("bend", 1.0)),
                               dur, float(ch.get("vol", 0.25)), ch.get("env", "pluck"),
                               float(ch.get("duty", 0.5)), hold=dur * float(ch.get("gate", 0.85)),
                               vibrato=float(ch.get("vib", 0.0)), seed=ci + 7)
            mix_into(buf, tone, int(row * row_seconds * RATE))
            row += length
    return buf


def build_music(force: bool) -> int:
    """Render every .song in assets_src/audio/songs/."""
    count = 0
    for path in sorted((SRC / "songs").glob("*.song")):
        out = OUT / "music" / f"{path.stem}.wav"
        if out.exists() and not force:
            count += 1
            continue
        song = json.loads(path.read_text(encoding="utf-8"))
        write_wav(out, render_song(song))
        count += 1
    print(f"  music: {count} tracks")
    return count


def compress(quality: int = 3, music_quality: int = 2) -> int:
    """Write an OGG beside every WAV, with ffmpeg. Returns how many it made.

    Thirty-eight megabytes of WAV is nothing on a laptop and far too much
    down a phone line, so a build for the web ships these instead. The game
    prefers an OGG wherever it finds one.
    """
    import shutil
    import subprocess
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        print("  no ffmpeg: install it to build the small audio", file=sys.stderr)
        return 0
    made = 0
    before = after = 0
    for folder in (OUT / "sfx", OUT / "music"):
        if not folder.is_dir():
            continue
        q = music_quality if folder.name == "music" else quality
        for wav in sorted(folder.glob("*.wav")):
            ogg = wav.with_suffix(".ogg")
            before += wav.stat().st_size
            if ogg.exists() and ogg.stat().st_mtime >= wav.stat().st_mtime:
                after += ogg.stat().st_size
                continue
            result = subprocess.run(
                [ffmpeg, "-y", "-loglevel", "error", "-i", str(wav),
                 "-c:a", "libvorbis", "-q:a", str(q), str(ogg)], check=False)
            if result.returncode:
                print(f"  ffmpeg failed on {wav.name}", file=sys.stderr)
                continue
            after += ogg.stat().st_size
            made += 1
    if before:
        print(f"  compressed: {before / 1e6:.1f} MB of WAV → {after / 1e6:.1f} MB of OGG")
    return made


def main(argv: list[str] | None = None) -> int:
    """Build the audio assets."""
    p = argparse.ArgumentParser(description="synthesise Eldermoor's audio")
    p.add_argument("--only", choices=("sfx", "music"), default=None)
    p.add_argument("--force", action="store_true", help="re-render even if the WAV exists")
    p.add_argument("--ogg", action="store_true",
                   help="also write a small OGG beside every WAV (needs ffmpeg)")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    print("building audio →", OUT)
    if args.only != "music":
        build_sfx(args.force)
    if args.only != "sfx":
        build_music(args.force)
    if args.ogg:
        compress()
    return 0


if __name__ == "__main__":
    sys.exit(main())
