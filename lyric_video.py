"""Build a lyric video from an existing audio file and editable captions."""

import math
import os
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw, ImageFont, ImageOps


FRAME_SIZE = (960, 540)
THEMES = {
    "night": ((12, 20, 40), (132, 208, 255)),
    "plum": ((35, 16, 43), (240, 167, 230)),
    "forest": ((12, 39, 32), (170, 233, 186)),
}
SECTION = re.compile(r"^\s*\[(?:intro|verse|pre[- ]chorus|chorus|post[- ]chorus|bridge|hook|instrumental|solo|outro)(?:\s+\d+)?\]\s*", re.I)
CJK = re.compile(r"[\u3000-\u30ff\u3400-\u9fff\uff00-\uffef]")


def _ffmpeg(*args, timeout):
    # Load the bundled executable only when someone uses the video feature.
    from imageio_ffmpeg import get_ffmpeg_exe

    return subprocess.run(
        [get_ffmpeg_exe(), "-hide_banner", "-nostdin", *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def audio_duration(audio_path):
    result = _ffmpeg("-i", audio_path, "-map", "0:a:0", "-t", "0", "-f", "null", "-", timeout=15)
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if result.returncode or not match:
        raise ValueError("Could not read the duration of this audio file.")
    hours, minutes, seconds = map(float, match.groups())
    duration = hours * 3600 + minutes * 60 + seconds
    if duration <= 0:
        raise ValueError("The audio file has no playable duration.")
    return duration


def estimate_cues(lyrics, duration):
    sections = [[]]
    for line in lyrics.splitlines():
        label = SECTION.match(line)
        if label and sections[-1]:
            sections.append([])
        text = line[label.end():].strip() if label else line.strip()
        if text:
            sections[-1].append(text)

    groups = ["\n".join(lines[i:i + 3]) for lines in sections for i in range(0, len(lines), 3)]
    if not groups:
        raise ValueError("Add lyrics before making a lyric video.")
    weights = [max(8, len(text)) for text in groups]
    total_weight = sum(weights)
    elapsed = 0
    cues = []
    for text, weight in zip(groups, weights):
        cues.append({"start": round(duration * elapsed / total_weight, 3), "lyrics": text})
        elapsed += weight
    return cues


def _video_font(text, size):
    windows = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    if CJK.search(text):
        fonts = (
            windows / "meiryo.ttc",
            windows / "YuGothM.ttc",
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"),
        )
    else:
        fonts = (
            windows / "segoeui.ttf",
            Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        )
    for path in fonts:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    raise RuntimeError("A compatible text font is missing. Install Noto Sans and Noto Sans CJK JP.")


def _wrap_lyrics(text, font, width):
    lines = []
    for paragraph in text.splitlines():
        line = ""
        for char in paragraph:
            if line and font.getlength(line + char) > width:
                before, gap, after = line.rpartition(" ")
                lines.append(before if gap and before else line)
                line = after if gap and before else ""
            line = (line + char).lstrip()
        if line:
            lines.append(line)
    return lines


def _make_background(color, image):
    if image is not None:
        fitted = ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"), FRAME_SIZE)
        return Image.blend(fitted, Image.new("RGB", FRAME_SIZE, color), 0.72)
    background = Image.new("RGB", FRAME_SIZE)
    draw = ImageDraw.Draw(background)
    for y in range(FRAME_SIZE[1]):
        shade = tuple(min(255, channel + y // 28) for channel in color)
        draw.line((0, y, FRAME_SIZE[0], y), fill=shade)
    return background


def _draw_card(background, accent, title, text, progress):
    frame = background.copy()
    draw = ImageDraw.Draw(frame)
    w, h = FRAME_SIZE
    title_font = _video_font(title, 29)
    title_line = _wrap_lyrics(" ".join(title.split()), title_font, w - 128)
    if title_line:
        draw.text((64, 54), title_line[0] + ("…" if len(title_line) > 1 else ""),
                  font=title_font, fill=accent, anchor="lt")
    draw.line((64, 108, w - 64, 108), width=2, fill=accent)

    if text:
        for size in (46, 40, 34, 28):
            font = _video_font(text, size)
            lines = _wrap_lyrics(text, font, w - 152)
            row_height = int(size * 1.46)
            if len(lines) * row_height <= 330:
                break
        else:
            raise ValueError("A caption is too long for one slide. Shorten that caption in the timing editor.")
        first_y = 301 - (len(lines) - 1) * row_height / 2
        for i, line in enumerate(lines):
            draw.text((w / 2, first_y + i * row_height), line, font=font,
                      fill=(250, 248, 255), anchor="mm")

    draw.rounded_rectangle((64, h - 44, w - 64, h - 37), radius=4, fill=(95, 103, 119))
    draw.rounded_rectangle((64, h - 44, 64 + (w - 128) * progress, h - 37),
                           radius=4, fill=accent)
    return frame


def render_lyric_video(audio_path, title, duration, cues, theme, image=None, background_video=None):
    if not cues:
        raise ValueError("Add lyrics before making a lyric video.")
    previous = -1
    for cue in cues:
        start = cue["start"]
        if start is None or not math.isfinite(start) or not previous < start < duration or start < 0:
            raise ValueError("Caption times must increase and stay within the song duration.")
        if not cue["lyrics"] or not cue["lyrics"].strip():
            raise ValueError("Each caption needs lyrics.")
        previous = start

    slides = list(cues)
    if slides and slides[0]["start"] > 0:
        slides.insert(0, {"start": 0, "lyrics": ""})
    color, accent = THEMES[theme]
    background = Image.new("RGBA", FRAME_SIZE) if background_video else _make_background(color, image)

    with TemporaryDirectory(prefix="knowledge2music-video-") as tmp:
        folder = Path(tmp)
        concat = ["ffconcat version 1.0"]
        for i, cue in enumerate(slides):
            next_start = slides[i + 1]["start"] if i + 1 < len(slides) else duration
            name = f"card-{i:04d}.png"
            _draw_card(background, accent, title, cue["lyrics"], next_start / duration).save(folder / name)
            concat.extend((f"file '{name}'", f"duration {next_start - cue['start']:.6f}"))
        concat.append(f"file '{name}'")  # Give the last card a closing timestamp.
        playlist = folder / "video.ffconcat"
        playlist.write_text("\n".join(concat) + "\n", encoding="ascii")
        output = folder / "lyric-video.mp4"
        sources = ["-f", "concat", "-safe", "1", "-i", playlist, "-i", audio_path]
        video_filter = ["-map", "0:v:0", "-vf", "fps=24"]
        if background_video:
            clip = folder / "background.mp4"
            clip.write_bytes(background_video)
            sources.extend(["-stream_loop", "-1", "-i", clip])
            video_filter = [
                "-filter_complex_threads", "2", "-filter_complex",
                "[2:v]scale=960:540:force_original_aspect_ratio=increase,crop=960:540,setsar=1,"
                "fps=24,eq=brightness=-0.21[background];"
                "[0:v]fps=24[captions];[background][captions]overlay=shortest=1[video]",
                "-map", "[video]",
            ]
        result = _ffmpeg(
            "-loglevel", "error", *sources, *video_filter, "-map", "1:a:0", "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-threads", "2", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", output, timeout=240,
        )
        if result.returncode or not output.is_file() or not output.stat().st_size:
            raise RuntimeError("FFmpeg could not encode the lyric video.")
        return output.read_bytes()
