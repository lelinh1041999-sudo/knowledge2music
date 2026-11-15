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
SECTION_NAME = r"(?:intro|verse|pre[- ]chorus|chorus|post[- ]chorus|bridge|hook|instrumental|solo|outro)(?:\s+\d+)?"
SECTION = re.compile(rf"^\s*\[({SECTION_NAME})\]\s*", re.I)
SCENE_ALIASES = {
    "mở đầu": "intro", "đoạn": "verse", "điệp khúc": "chorus", "chuyển đoạn": "bridge", "kết": "outro",
    "イントロ": "intro", "aメロ": "verse", "サビ": "chorus", "間奏": "bridge", "アウトロ": "outro",
}
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
    sections = [("verse", [])]
    for line in lyrics.splitlines():
        label = SECTION.match(line)
        if label:
            name = " ".join(label[1].lower().replace("-", " ").split())
            sections.append((name, []))
        text = line[label.end():].strip() if label else line.strip()
        if text:
            sections[-1][1].append(text)

    groups = [(section, "\n".join(lines[i:i + 3])) for section, lines in sections for i in range(0, len(lines), 3)]
    if not groups:
        raise ValueError("Add lyrics before making a lyric video.")
    has_silent_intro = sections[:2] == [("verse", []), ("intro", [])]
    lead_in = min(4, duration * 0.07) if has_silent_intro else 0
    weights = [max(8, len(text)) for _, text in groups]
    total_weight = sum(weights)
    elapsed = 0
    cues = []
    for (section, text), weight in zip(groups, weights):
        start = lead_in + (duration - lead_in) * elapsed / total_weight
        cues.append({"start": round(start, 3), "lyrics": text, "section": section})
        elapsed += weight
    return cues


def scene_timeline(brief, cues, genre="", mood=""):
    """Apply named scene directions to the caption timings."""
    general = []
    directions = {}
    for line in brief.splitlines():
        label, separator, description = line.replace("：", ":", 1).partition(":")
        key = " ".join(label.strip(" []\t").casefold().replace("-", " ").split())
        numbered = re.fullmatch(r"(.+?)( \d+)?", key)
        if numbered:
            key = SCENE_ALIASES.get(numbered[1], numbered[1]) + (numbered[2] or "")
        if separator and re.fullmatch(SECTION_NAME, key, flags=re.I):
            if description.strip():
                directions[key] = description.strip()
        elif line.strip():
            general.append(line.strip())

    broad = " ".join(general)
    style = ", ".join(part for part in (genre, mood) if part)
    starts = [(cue["start"], cue.get("section", "verse")) for cue in cues]
    if starts and starts[0][0] > 0:
        starts.insert(0, (0, "intro"))
    timeline = []
    for start, section in starts:
        base = re.sub(r"\s+\d+$", "", section)
        specific = directions.get(section) or directions.get(base)
        description = " ".join(part for part in (broad, specific) if part)
        prompt = None
        if description:
            prompt = f"{description} Music mood: {style}." if style else description
            prompt += " Background animation for a lyric video, leave clear space for captions."
        if not timeline or timeline[-1][1] != prompt:
            timeline.append((start, prompt))
    return timeline


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


def _draw_card(background, accent, title, text):
    frame = background.copy()
    draw = ImageDraw.Draw(frame)
    w, _ = FRAME_SIZE
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
        first_y = 274 - (len(lines) - 1) * row_height / 2
        for i, line in enumerate(lines):
            draw.text((w / 2, first_y + i * row_height), line, font=font,
                      fill=(250, 248, 255), anchor="mm", stroke_width=2, stroke_fill=(16, 17, 26))
    return frame


def validate_cues(cues, duration):
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


def render_lyric_video(audio_path, title, duration, cues, theme, image=None, scenes=None, waveform=True, show_lyrics=True):
    validate_cues(cues, duration)
    slides = list(cues)
    if slides and slides[0]["start"] > 0:
        slides.insert(0, {"start": 0, "lyrics": ""})
    color, accent = THEMES[theme]
    animated = scenes and any(clip for _, clip in scenes)
    background = Image.new("RGBA", FRAME_SIZE) if animated else _make_background(color, image)

    with TemporaryDirectory(prefix="knowledge2music-video-") as tmp:
        folder = Path(tmp)
        concat = ["ffconcat version 1.0"]
        for i, cue in enumerate(slides):
            next_start = slides[i + 1]["start"] if i + 1 < len(slides) else duration
            name = f"card-{i:04d}.png"
            _draw_card(background, accent, title, cue["lyrics"] if show_lyrics else "").save(folder / name)
            concat.extend((f"file '{name}'", f"duration {next_start - cue['start']:.6f}"))
        concat.append(f"file '{name}'")  # Give the last card a closing timestamp.
        playlist = folder / "video.ffconcat"
        playlist.write_text("\n".join(concat) + "\n", encoding="ascii")
        output = folder / "lyric-video.mp4"
        sources = ["-f", "concat", "-safe", "1", "-i", playlist, "-i", audio_path]
        filters = ["[0:v]fps=24[captions]"]
        output_label = "captions"
        if animated:
            _add_scene_filters(folder, scenes, duration, color, sources, filters)
            filters.append("[background][captions]overlay=shortest=1[scenes_with_captions]")
            output_label = "scenes_with_captions"
        if waveform:
            accent_hex = "".join(f"{channel:02x}" for channel in accent)
            filters.extend([
                f"[1:a]aformat=channel_layouts=mono,showwaves=s=832x52:r=24:mode=cline:colors=0x{accent_hex},format=rgba,colorkey=black:0.04[wave]",
                f"[{output_label}][wave]overlay=x=64:y=457:eof_action=pass[video]",
            ])
            output_label = "video"
        result = _ffmpeg(
            "-loglevel", "error", *sources, "-filter_complex_threads", "2", "-filter_complex", ";".join(filters),
            "-map", f"[{output_label}]", "-map", "1:a:0", "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-threads", "2", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", output, timeout=240,
        )
        if result.returncode or not output.is_file() or not output.stat().st_size:
            raise RuntimeError("FFmpeg could not encode the lyric video.")
        return output.read_bytes()


def _add_scene_filters(folder, scenes, duration, color, sources, filters):
    clip_paths = {}
    next_input = 2
    color_hex = "".join(f"{channel:02x}" for channel in color)
    for i, (start, clip) in enumerate(scenes):
        end = scenes[i + 1][0] if i + 1 < len(scenes) else duration
        seconds = f"{end - start:.6f}"
        if clip:
            if clip not in clip_paths:
                path = folder / f"scene-{i}.mp4"
                path.write_bytes(clip)
                clip_paths[clip] = path
            sources.extend(["-threads", "1", "-stream_loop", "-1", "-i", clip_paths[clip]])
            filters.append(
                f"[{next_input}:v]scale=960:540:force_original_aspect_ratio=increase,crop=960:540,"
                f"setsar=1,fps=24,eq=brightness=-0.25,trim=duration={seconds},setpts=PTS-STARTPTS[scene{i}]"
            )
            next_input += 1
        else:
            filters.append(f"color=c=0x{color_hex}:s=960x540:r=24:d={seconds}[scene{i}]")
    labels = "".join(f"[scene{i}]" for i in range(len(scenes)))
    filters.append(f"{labels}concat=n={len(scenes)}:v=1:a=0[background]")
