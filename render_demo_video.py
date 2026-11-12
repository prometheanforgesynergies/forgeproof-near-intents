#!/usr/bin/env python3
"""Render the demo transcript into a terminal-style video.

Every line on screen comes verbatim from demo_transcript_2026-11-11.txt;
nothing is scripted for the camera. The transcript is split at the
second "$" command line into two screens (refusal, then live quote)
so the text stays legible.

Usage: python3 render_demo_video.py [transcript] [output.mp4]
Requires: Pillow, ffmpeg, DejaVuSansMono.
"""
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
BG = (13, 17, 23)
FG = (230, 237, 243)
GREEN = (126, 231, 135)
RED = (255, 123, 114)
CYAN = (121, 192, 255)
DIM = (139, 148, 158)
YELLOW = (233, 196, 106)
FPS = 8
FRAMES_PER_LINE = 6
MARGIN = 56
TOP = 64
LINE_H = 34

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def fonts(size):
    return (
        ImageFont.truetype(FONT_PATH, size),
        ImageFont.truetype(BOLD_PATH, size),
    )


def wrap_lines(lines, font, max_width):
    wrapped = []
    for line in lines:
        if line == "":
            wrapped.append("")
            continue
        # textwrap on character count derived from measured width, with
        # a safety margin so no line can touch the right edge.
        import math
        avg = max(1, math.ceil(font.getlength("x")))
        width_chars = max(20, (max_width - 48) // avg)
        parts = textwrap.wrap(line, width=width_chars,
                              expand_tabs=False, replace_whitespace=False,
                              drop_whitespace=False)
        wrapped.extend(parts or [""])
    return wrapped


def color_for(line, bold_font, font):
    if line.startswith("$"):
        return GREEN, bold_font
    if line.startswith("SCOUT: REFUSED"):
        return RED, bold_font
    if line.startswith("SCOUT: EVIDENCE"):
        return GREEN, bold_font
    if line.startswith("DRY QUOTE"):
        return CYAN, bold_font
    if line.strip().startswith("NOTE:"):
        return DIM, font
    if line.startswith("No evidence"):
        return YELLOW, bold_font
    if line.startswith("  deposit address:"):
        return CYAN, bold_font
    return FG, font


def draw_terminal(visible_lines, font, bold_font):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 44], fill=(22, 27, 34))
    draw.text((MARGIN, 10), "forgeproof — near-entry — demo.py",
              font=font, fill=DIM)
    y = TOP
    for line in visible_lines:
        color, use_font = color_for(line, bold_font, font)
        draw.text((MARGIN, y), line, font=use_font, fill=color)
        y += LINE_H
    # Cursor block after the last visible line.
    if visible_lines:
        last = visible_lines[-1]
        _, use_font = color_for(last, bold_font, font)
        x = MARGIN + int(use_font.getlength(last)) + 6
        draw.rectangle([x, y - LINE_H + 6, x + 12, y - 6], fill=FG)
    return img


def draw_card(title_lines, sub_lines, font, bold_font, big):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    y = H // 2 - 130
    for line in title_lines:
        tw = int(big.getlength(line))
        draw.text(((W - tw) // 2, y), line, font=big, fill=FG)
        y += 64
    y += 16
    for line in sub_lines:
        tw = int(font.getlength(line))
        draw.text(((W - tw) // 2, y), line, font=font, fill=DIM)
        y += 34
    return img


def main():
    here = Path(__file__).resolve().parent
    transcript = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "demo_transcript_2026-11-11.txt"
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else here / "demo-quote-moment.mp4"
    lines = transcript.read_text(encoding="utf-8").splitlines()

    # Split into screens at each "$" command line.
    screens, current = [], []
    for line in lines:
        if line.startswith("$") and current:
            screens.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        screens.append(current)

    font, bold_font = fonts(21)
    big = ImageFont.truetype(BOLD_PATH, 44)
    frames = []

    title = draw_card(
        ["ForgeProof + NEAR Intents"],
        ["Dry-quote demo — local run, Nov 11, 2026",
         "Scout gate first. Quotes only. No wallet. No deposit."],
        font, bold_font, big,
    )
    frames.extend([title] * (FPS * 3))

    for screen in screens:
        wrapped = wrap_lines(screen, font, W - 2 * MARGIN)
        shown = []
        for line in wrapped:
            shown.append(line)
            frame = draw_terminal(shown, font, bold_font)
            frames.extend([frame] * FRAMES_PER_LINE)
        frames.extend([draw_terminal(shown, font, bold_font)] * FPS)  # hold

    end = draw_card(
        ["No evidence, no quote."],
        ["ForgeProof + NEAR Intents — dry quotes only.",
         "Verbatim transcript: demo_transcript_2026-11-11.txt"],
        font, bold_font, big,
    )
    frames.extend([end] * (FPS * 4))

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for i, frame in enumerate(frames):
            frame.save(tmpdir / f"f{i:04d}.png")
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-framerate", str(FPS),
            "-i", str(tmpdir / "f%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output),
        ]
        subprocess.run(cmd, check=True)
    print(f"wrote {output} ({len(frames)} frames, {len(frames)/FPS:.1f}s)")


if __name__ == "__main__":
    main()
