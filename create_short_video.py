import subprocess
import cv2
import numpy as np
from pydub import AudioSegment
import asyncio
import edge_tts
import os
from PIL import Image, ImageDraw, ImageFont
import ast

# ==================================
# FONT LOAD
# ==================================

BASE_DIR = "Episodes/Ep42/"
FONT_PATH = "C:/Windows/Fonts/arial.ttf"

font_en = ImageFont.truetype(FONT_PATH, 45)
font_en_bold = ImageFont.truetype("fonts/arialbd.ttf", 54)
font_vi = ImageFont.truetype(FONT_PATH, 34)
font_emoji = ImageFont.truetype(
    "C:/Windows/Fonts/seguiemj.ttf",
    32
)

VOICE_MALE = "en-US-ChristopherNeural"
VOICE_FEMALE = "en-US-JennyNeural"

VOICE_VN_FEMALE = "vi-VN-HoaiMyNeural"
VOICE_VN_MALE = "vi-VN-NamMinhNeural"

width = 1080
height = 1920

os.makedirs(f"{BASE_DIR}", exist_ok=True)
dirs = ["download", "output", "download/screenshort", "output/audios/", "output/images/", "output/videos/"]
for d in dirs:
    os.makedirs(f"{BASE_DIR}/{d}", exist_ok=True)

# Đường dẫn file
background_path = os.path.join(f"{BASE_DIR}/download/screenshort", "prompt_background.txt")
topic_path = os.path.join(BASE_DIR, "topic.txt")

# Nếu chưa có thì tạo file rỗng
if not os.path.exists(background_path):
    open(background_path, "w", encoding="utf-8").close()

if not os.path.exists(topic_path):
    open(topic_path, "w", encoding="utf-8").close()

print("Đã tạo file rỗng nếu chưa tồn tại.")

# Copy background và resize lại:background
if not os.path.exists(f"{BASE_DIR}/output/images/background.png"):
    background = (Image
              .open(f"{BASE_DIR}/download/background.png")
              .resize((width, height))
              .save(f"{BASE_DIR}/output/images/background.png"))
print("background: Done!")

# Load dialogue:
with open(f"{BASE_DIR}/topic.txt", "r", encoding="utf-8") as f:
    dialogue = ast.literal_eval(f.read())

# ==================================
# TTS
# ==================================

async def text_to_speech(text, output_file, voice=VOICE_FEMALE):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)
    return output_file


def get_audio_duration(audio_path):
    audio = AudioSegment.from_file(audio_path)
    return len(audio) / 1000


def merge_audio_files(audio_files, output_file):
    combined = AudioSegment.empty()
    for f in audio_files:
        combined += AudioSegment.from_file(f)

    combined.export(output_file, format="mp3")
    return output_file


# ==================================
# TIMELINE
# ==================================

async def build_timeline(dialogue):

    tasks = []

    for i, text in enumerate(dialogue["en"]):
        audio_file = f"{BASE_DIR}/output/audios/audio_{i:03d}.mp3"
        tasks.append(text_to_speech(text, audio_file))

    await asyncio.gather(*tasks)

    timeline = []
    audio_files = []
    current_time = 0

    for i in range(len(dialogue["en"])):

        # audio_file = f"audio_{i:03d}.mp3"
        audio_file = f"{BASE_DIR}output/audios/audio_{i:03d}.mp3"

        duration = get_audio_duration(audio_file)

        timeline.append({
            "en": dialogue["en"][i],
            "vi": dialogue["vi"][i],
            "start": current_time,
            "end": current_time + duration
        })

        audio_files.append(audio_file)

        current_time += duration

    return timeline, audio_files

def get_current_index(current_time, timeline):
    for i, item in enumerate(timeline):
        if item["start"] <= current_time < item["end"]:
            return i
    return -1


# ==================================
# BACKGROUND IMAGE
# ==================================

def resize_crop(image, target_w, target_h):
    h, w = image.shape[:2]
    target_ratio = target_w / target_h
    img_ratio = w / h

    if img_ratio > target_ratio:
        # crop width
        new_w = int(h * target_ratio)
        x = (w - new_w) // 2
        image = image[:, x:x+new_w]
    else:
        # crop height
        new_h = int(w / target_ratio)
        y = (h - new_h) // 2
        image = image[y:y+new_h, :]

    return cv2.resize(image, (target_w, target_h))

def create_frame(image_path, width, height):
    img = cv2.imread(image_path)

    if img is None:
        return np.zeros((height, width, 3), dtype=np.uint8)

    return cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)

# ==================================
# PIL TEXT DRAW (FIX VIETNAMESE)
# ==================================

def draw_flower_divider(frame, y, font, color=(0, 0, 0)):
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)

    W, H = img.size

    left_leaf = "༺❦༻"
    flower = "🌸"
    right_leaf = "༺❦༻"

    gap = 12

    bbox1 = draw.textbbox((0, 0), left_leaf, font=font)
    bbox2 = draw.textbbox((0, 0), flower, font=font)
    bbox3 = draw.textbbox((0, 0), right_leaf, font=font)

    w_leaf1 = bbox1[2] - bbox1[0]
    w_flower = bbox2[2] - bbox2[0]
    w_leaf2 = bbox3[2] - bbox3[0]

    center_width = w_leaf1 + gap + w_flower + gap + w_leaf2
    x_center = (W - center_width) // 2

    line_y = y + 15

    draw.line([(50, line_y), (x_center - 20, line_y)], fill=color, width=2)

    draw.text((x_center, y), left_leaf, font=font, fill=color)
    x_flower = x_center + w_leaf1 + gap
    draw.text((x_flower, y), flower, font=font, fill=color)

    x_leaf2 = x_flower + w_flower + gap
    draw.text((x_leaf2, y), right_leaf, font=font, fill=color)

    x_line = x_leaf2 + w_leaf2 + 20
    draw.line([(x_line, line_y), (W - 50, line_y)], fill=color, width=2)

    # 🔥 quan trọng: tính height
    divider_h = 20

    return np.array(img), divider_h

def draw_text_pil(frame, text, position, font, color):
    from PIL import Image, ImageDraw
    from textwrap import wrap
    import numpy as np

    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)

    W, H = img.size
    x, y = position

    lines = wrap(text, width=50)

    line_height = font.getbbox("A")[3] - font.getbbox("A")[1]

    total_h = len(lines) * (line_height + 5)
    
    ascent, descent = font.getmetrics()
    line_height = ascent + descent
    line_spacing = 10      # khoảng cách giữa các dòng

    total_h = len(lines) * line_height + (len(lines)-1) * line_spacing


    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]

        x_line = (W - text_w) // 2
        y_line = y + i * (line_height + 20) - 100

        draw.text((x_line, y_line), line, font=font, fill=color)

    return np.array(img), total_h

def draw_texts(frame, timeline, current_index):

    h, w = frame.shape[:2]
    img_h = int(h * 0.46)

    current_y = img_h + 0
    
    # ENGLISH
    for i, item in enumerate(timeline):

        color = (255, 0, 0) if i == current_index else (0, 0, 0)
        font = font_en_bold if i == 0 else font_en

        frame, h_text = draw_text_pil(
            frame,
            item["en"],
            (50, current_y),
            font,
            color,
        )
        current_y +=h_text + 10
        
    frame, divider_h = draw_flower_divider(
    frame,
    current_y - 80,
    font_emoji,
    color=(80, 80, 80)
)

    current_y += divider_h + 0

    current_y += 10   # khoảng cách xuống phần tiếng Việt

        # Vẽ tiếng việt
    current_y = img_h + 400

    for i, item in enumerate(timeline):

        color = (255,0,0) if i == current_index else (0,0,0)
        font = font_en_bold if i == 0 else font_en

        frame, h_text = draw_text_pil(
        frame,
        item["vi"],
        (50, current_y),
        font,
        color,
        )

        current_y += h_text + 18
    return frame

# ==================================
# RENDER VIDEO
# ==================================

def render_video(timeline, audio_duration, image_path,
                 output_path, fps=30, width=1080, height=1920):

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_frames = int(audio_duration * fps)

    for i in range(total_frames):

        t = i / fps

        frame = create_frame(image_path, width, height)

        current_index = get_current_index(t, timeline)

        frame = draw_texts(frame, timeline, current_index)
        Image.fromarray(frame).save(
        f"{BASE_DIR}/output/images/final_layout.png"
        )

        writer.write(frame)

        if i % 100 == 0:
            print(f"{i}/{total_frames}")

    writer.release()

# ==================================
# MERGE AUDIO + VIDEO
# ==================================
def run_ffmpeg(cmd):
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)

def get_audio_duration(audio_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())
def merge_audio_video(video_path, audio_path, output_path):

    run_ffmpeg([
        "ffmpeg", "-y",

        "-i", video_path,
        "-i", audio_path,

        "-c:v", "h264_qsv",
        "-global_quality", "28",
        "-pix_fmt", "nv12",
        "-fps_mode", "cfr",

        "-c:a", "aac",
        "-b:a", "192k",

        "-shortest",

        output_path
    ])

def add_background_music(video, music, output):
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", video,
        "-stream_loop", "-1", "-i", music,   # lặp vô hạn nhạc nền
        "-filter_complex", "[1:a]volume=0.04[a1];[0:a][a1]amix=inputs=2:duration=first[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac",
        output
    ])
# ==================================
# MAIN
# ==================================

async def main():

    image_path = f"{BASE_DIR}/output/images/background.png"
    first_video = f"{BASE_DIR}/output/videos/video.mp4"
    final_video = f"{BASE_DIR}/output/videos/final.mp4"
    final_video_music = f"{BASE_DIR}/output/videos/final_video_music.mp4"
    bg_music = "music.mp3"
    output_audio = f"{BASE_DIR}/output/audios/full_audio.mp3"

    timeline, audio_files = await build_timeline(dialogue)

    full_audio = merge_audio_files(audio_files, output_audio)

    duration = get_audio_duration(full_audio)

    if not os.path.exists(first_video):
        render_video(
            timeline,
            duration,
            image_path,
            first_video
        )

    if not os.path.exists(final_video):
        merge_audio_video(
            f"{BASE_DIR}/output/videos/video.mp4",
            full_audio,
            f"{BASE_DIR}/output/videos/final.mp4"
        )
    
    os.remove(f"{BASE_DIR}/output/videos/video.mp4")
    
    
    add_background_music(final_video, bg_music, final_video_music)
    os.remove(final_video)
    
    print("DONE")


if __name__ == "__main__":
    asyncio.run(main())