import re
import os

from moviepy import (
    AudioFileClip,
    ImageClip,
    TextClip,
    CompositeVideoClip,
)

# ----------------------
# Config
# ----------------------

BASE_DIR = "Song/Ep2"

IMAGE = f"{BASE_DIR}/download/background.png"

SONG = f"{BASE_DIR}/download/Ready_to_Go.mp3"

LYRICS = f"{BASE_DIR}/download/lyrics.txt"

PROMPT_LYRICS = f"{BASE_DIR}/download/prompt_lyrics.txt"

PROMPT_SONG = f"{BASE_DIR}/download/prompt_song.txt"

PROMPT_IMAGE = f"{BASE_DIR}/download/prompt_image.txt"

VIDEO_DIR = f"{BASE_DIR}/output/videos"

OUTPUT = f"{VIDEO_DIR}/final_video.mp4"


# Nếu chưa có thì tạo file rỗng

os.makedirs(f"{BASE_DIR}", exist_ok=True)
dirs = ["output", "output/videos/", "download", "download/screenshots"]
for d in dirs:
    os.makedirs(f"{BASE_DIR}/{d}", exist_ok=True)

# topic_path = os.path.join(BASE_DIR, "topic.txt")
if not os.path.exists(LYRICS):
    open(LYRICS, "w", encoding="utf-8").close()
    
if not os.path.exists(PROMPT_SONG):
    open(PROMPT_SONG, "w", encoding="utf-8").close()

if not os.path.exists(PROMPT_IMAGE):
    open(PROMPT_IMAGE, "w", encoding="utf-8").close()
    
if not os.path.exists(PROMPT_LYRICS):
    open(PROMPT_LYRICS, "w", encoding="utf-8").close()

print("Đã tạo file rỗng nếu chưa tồn tại.")

WIDTH = 1080
HEIGHT = 1920

FONT = r"C:\Windows\Fonts\arial.ttf"

FONT_SIZE_EN = 60
FONT_SIZE_VI = 40

TEXT_COLOR = "yellow"
STROKE_COLOR = "black"
STROKE_WIDTH = 1

# ----------------------
# Đọc file lrc
# ----------------------

def read_lyrics(filename):

    pattern = r"\[(\d+\.?\d*):(\d+\.?\d*)\]\s*(.*)"

    data = []

    with open(filename, "r", encoding="utf8") as f:

        lines = [x.strip() for x in f if x.strip()]

    i = 0

    while i < len(lines):

        m1 = re.match(pattern, lines[i])

        m2 = re.match(pattern, lines[i+1])

        start = float(m1.group(1))
        end = float(m1.group(2))

        en = m1.group(3)
        vi = m2.group(3)

        data.append({
            "start": start,
            "end": end,
            "en": en,
            "vi": vi
        })

        i += 2

    return data
lyrics = read_lyrics(LYRICS)
print(lyrics)
audio = AudioFileClip(SONG)

duration = audio.duration


# ----------------------
# Background
# ----------------------

background = (
    ImageClip(IMAGE)
    .with_duration(duration)
    .resized((WIDTH, HEIGHT))
)

clips = [background]

for item in lyrics:

    start = item["start"]
    end = item["end"]

    # Text tiếng Anh
    txt_en = (
        TextClip(
            text=item["en"],
            font=FONT,
            font_size=FONT_SIZE_EN,
            color=TEXT_COLOR,
            stroke_color=STROKE_COLOR,
            stroke_width=STROKE_WIDTH,
            method="caption",
            size=(1000, None),
            text_align="center",
        )
        .with_start(start)
        .with_duration(end - start)
        .with_position(("center", "center"))
    )


    # Text tiếng Việt
    txt_vi = (
        TextClip(
            text=item["vi"],
            font=FONT,
            font_size=FONT_SIZE_VI,
            color=TEXT_COLOR,
            stroke_color=STROKE_COLOR,
            stroke_width=STROKE_WIDTH,
            method="caption",
            size=(1000, None),
            text_align="center",
        )
        .with_start(start)
        .with_duration(end - start)
        .with_position(("center", "center"))
    )

    # Điều chỉnh vị trí:
    # English ở trên
    txt_en = txt_en.with_position(
        ("center", 530)
    )

    # Vietnamese ở dưới
    txt_vi = txt_vi.with_position(
        ("center", 610)
    )


    clips.append(txt_en)
    clips.append(txt_vi)
# ----------------------
# Video
# ----------------------

video = CompositeVideoClip(clips)

video = video.with_audio(audio)

video.write_videofile(
    OUTPUT,
    fps=30,
    codec="libx264",
    audio_codec="aac",
)