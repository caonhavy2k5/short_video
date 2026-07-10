import json
import os
import cv2
import asyncio
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
from moviepy import AudioFileClip
import edge_tts

# =========================================================
# CONFIG
# =========================================================

BASE_DIR = "Podcast/Ep8"

IMAGE = "podcast_prompt_image/background.png"

SCRIPT = f"{BASE_DIR}/topic.txt"

AUDIO = f"{BASE_DIR}/output/audios/voice.mp3"

TIMESTAMP_JSON = f"{BASE_DIR}/output/audios/timestamps.json"

VIDEO_DIR = f"{BASE_DIR}/output/videos"

VIDEO_NO_AUDIO = f"{VIDEO_DIR}/video_no_audio.mp4"

OUTPUT = f"{VIDEO_DIR}/final_video.mp4"

FONT_PATH = "C:/Windows/Fonts/arial.ttf"

THUMBNAIL = f"{BASE_DIR}/output/images/thumbnail.png"

THUMBNAIL_DURATION = 2.0

# Nếu chưa có thì tạo file rỗng

os.makedirs(f"{BASE_DIR}", exist_ok=True)
dirs = ["output", "output/audios/", "output/images/", "output/videos/"]
for d in dirs:
    os.makedirs(f"{BASE_DIR}/{d}", exist_ok=True)

    
topic_path = os.path.join(BASE_DIR, "topic.txt")
if not os.path.exists(topic_path):
    open(topic_path, "w", encoding="utf-8").close()

print("Đã tạo file rỗng nếu chưa tồn tại.")

WIDTH = 1280
HEIGHT = 720

FPS = 15

VOICE = "en-US-JennyNeural"

# waveform

WAVE_Y = 620

BAR_WIDTH = 12

BAR_GAP = 12

WAVE_HEIGHT = 25

WAVE_COLOR = (255,255,255)


# =========================================================
# CREATE VOICE
# =========================================================
async def create_voice(text):

    communicate = edge_tts.Communicate(
        text,
        VOICE,
        rate="+0%"
    )

    if os.path.exists(AUDIO):
        os.remove(AUDIO)

    if os.path.exists(TIMESTAMP_JSON):
        os.remove(TIMESTAMP_JSON)

    audio_file=open(
        AUDIO,
        "wb"
    )

    timestamp_file=open(
        TIMESTAMP_JSON,
        "w",
        encoding="utf-8"
    )

    count=0

    async for chunk in communicate.stream():

        print(chunk["type"])

        if chunk["type"]=="audio":

            audio_file.write(
                chunk["data"]
            )

        elif chunk["type"]=="SentenceBoundary":

            count += 1

            data = {
                "offset":
                chunk["offset"],
                "duration":
                chunk["duration"],
                "text":
                chunk["text"].strip()
            }

            timestamp_file.write(
                json.dumps(
                    data,
                    ensure_ascii=False
                )
                +
                "\n"
            )
    audio_file.close()
    timestamp_file.close()   
# =========================================================
# LOAD TIMESTAMP
# =========================================================

def load_timestamp():

    result=[]


    with open(
        TIMESTAMP_JSON,
        encoding="utf-8"
    ) as f:


        for line in f:

            obj=json.loads(line)


            result.append({

                "start":
                obj["offset"]/10000000,


                "end":
                (
                    obj["offset"]
                    +
                    obj["duration"]
                )
                /
                10000000,


                "text":
                obj["text"]

            })


    return result
# =========================================================
# BACKGROUND
# =========================================================

class ThumbnailManager:

    def __init__(
            self,
            image_path,
            width,
            height,
            fps,
            duration=2.0,
            zoom_start=1.0,
            zoom_end=1.12,
            pan_x=0.5,
            pan_y=0.5
    ):

        self.width = width
        self.height = height
        self.frames = []

        img = cv2.imread(image_path)

        if img is None:
            raise FileNotFoundError(image_path)

        h, w = img.shape[:2]

        total_frames = int(duration * fps)

        for i in range(total_frames):

            t = i / max(total_frames - 1, 1)

            # SmoothStep
            t = t * t * (3 - 2 * t)

            scale = zoom_start + (zoom_end - zoom_start) * t

            nw = int(w * scale)
            nh = int(h * scale)

            resized = cv2.resize(
                img,
                (nw, nh),
                interpolation=cv2.INTER_LINEAR
            )

            cx = int(nw * pan_x)
            cy = int(nh * pan_y)

            x = max(
                0,
                min(
                    cx - width // 2,
                    nw - width
                )
            )

            y = max(
                0,
                min(
                    cy - height // 2,
                    nh - height
                )
            )

            frame = resized[
                y:y + height,
                x:x + width
            ]

            self.frames.append(frame)

    def get_frame(self, index):

        if index >= len(self.frames):
            return self.frames[-1]

        return self.frames[index]

class Background:

    def __init__(self):

        img=cv2.imread(IMAGE)

        img=cv2.resize(img,(WIDTH,HEIGHT))

        img=cv2.convertScaleAbs(img,alpha=1,beta=-20)

        self.img=img

    def get(self):
        return self.img.copy()

# =========================================================
# SUBTITLE
# =========================================================

class SubtitleManager:

    def __init__(self, timestamp):

        self.timestamp=timestamp
        self.index=0
        self.cache={}
        self.font=ImageFont.truetype(FONT_PATH,42)

    # -------------------------------------

    def wrap_text(self,draw,text,max_width=950):

        words=text.split()
        lines=[]
        line=""

        for word in words:
            test=line+" "+word
            box=draw.textbbox((0,0),test,font=self.font)

            width=box[2]-box[0]

            if width <= max_width:
                line=test.strip()
            else:
                if line:
                    lines.append(line)
                line=word

        if line:
            lines.append(line)

        return lines

    # -------------------------------------

    def create_text(self,text):
        img=Image.new(
            "RGBA",
            (WIDTH,HEIGHT),
            (0,0,0,0)
        )

        draw=ImageDraw.Draw(img)
        
         # Xóa toàn bộ dấu chấm khi hiển thị subtitle
        display_text = text.replace(".", "")

        if display_text in self.cache:
            return self.cache[display_text]

        lines=self.wrap_text(draw,display_text)

        line_height=45

        start_y=430

        for i,line in enumerate(lines):

            box=draw.textbbox(
                (0,0),
                line,
                font=self.font
            )

            w=box[2]-box[0]

            x=(WIDTH-w)//2

            draw.text(
                (x,start_y+i*line_height),
                line,
                font=self.font,
                fill=(255,255,255,255),
                stroke_width=3,
                stroke_fill=(0,0,0,255)
            )

        result=cv2.cvtColor(np.array(img),cv2.COLOR_RGBA2BGRA)

        self.cache[display_text]=result

        return result
    
    # -------------------------------------

    def draw(self,frame,current_time):

        if len(self.timestamp)==0:
            return frame

        # chạy index theo thời gian
        while (

            self.index < len(self.timestamp)-1
            and
            current_time >=
            self.timestamp[self.index]["end"]

        ):

            self.index += 1

        item=self.timestamp[self.index]


        if (

            item["start"]

            <=

            current_time

            <=

            item["end"]+0.15

        ):

            subtitle=self.create_text(
                item["text"]
            )

            alpha=subtitle[:,:,3]/255.0

            alpha=np.expand_dims(
                alpha,
                2
            )

            frame[:]=(
                frame*(1-alpha)
                +
                subtitle[:,:,:3]*alpha
            ).astype(
                np.uint8
            )

        return frame

# =========================================================
# WAVEFORM
# =========================================================

class WaveVisualizer:

    def __init__(self, audio_file, duration):

        audio = AudioSegment.from_file(audio_file)

        samples = np.array(
            audio.get_array_of_samples(),
            dtype=np.float32
        )

        # Stereo -> Mono
        if audio.channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1)

        self.samples = samples
        self.sample_rate = audio.frame_rate

        self.total_frames = int(duration * FPS)

        self.step = max(
            2048,
            len(self.samples) // self.total_frames
        )

        self.bars = WIDTH // (BAR_WIDTH + BAR_GAP)

        self.position = np.zeros(self.bars)
        self.velocity = np.zeros(self.bars)
        self.peaks = np.zeros(self.bars)

        # Cache FFT
        self.cache = []

        print("Precompute waveform...")

        for i in range(self.total_frames):
            self.cache.append(self.analyze(i))

    # ---------------------------------

    def analyze(
            self,
            frame_index
    ):

        start=frame_index*self.step

        end=start+self.step

        chunk=self.samples[start:end].copy()

        if len(chunk)<512:

            return np.zeros(self.bars)

        chunk*=np.hanning(len(chunk))

        spectrum=np.abs(np.fft.rfft(chunk))

        spectrum=spectrum[:len(spectrum)//2]

        values=np.array_split(
            spectrum,
            self.bars
        )

        values=np.array([x.mean() if len(x) else 0 for x in values])

        values=np.log1p(values)

        if values.max()>0:

            values/=values.max()

        values*=np.sin(
            np.linspace(
                0,
                np.pi,
                self.bars
            )
        )
        
        return values*WAVE_HEIGHT

    def spring(
            self,
            target
    ):

        force=target-self.position

        # self.velocity+=force*0.12
        self.velocity+=force*0.35
        # self.velocity*=0.75
        self.velocity*=0.85
        self.position+=self.velocity
        self.position=np.clip(
            self.position,
            2,
            WAVE_HEIGHT
        )

        return self.position

    def draw(
            self,
            frame,
            frame_index
    ):
        #Mới
        target = self.cache[frame_index] # Mới
        
        heights=self.spring(target)
        self.peaks = np.maximum(
            self.peaks - 0.6,
            heights
        )
    
        # Mới
        for i, h in enumerate(self.peaks):
            x=i*(BAR_WIDTH+BAR_GAP)

            h=int(h)

            cv2.rectangle(
                frame,
                (
                    x - BAR_WIDTH // 2,
                    WAVE_Y - int(h)
                ),
                (
                    x + BAR_WIDTH // 2,
                    WAVE_Y + int(h)
                ),
                WAVE_COLOR,
                -1
            )

        return frame

# =========================================================
# VIDEO RENDERER
# =========================================================

class VideoRenderer:

    def __init__(
            self,
            duration,
            subtitle,
            waveform
    ):
        self.thumbnail = ThumbnailManager(
            THUMBNAIL,
            WIDTH,
            HEIGHT,
            FPS,
            duration=2.0,
            zoom_start=1.0,
            zoom_end=1.05,
            pan_x=0.5,
            pan_y=0.5
        )

        self.total_frames=int(duration*FPS)
        self.background=Background()
        self.subtitle=subtitle
        self.waveform=waveform
        
    def blend(self, img1, img2, alpha):

        return cv2.addWeighted(
            img1,
            1 - alpha,
            img2,
            alpha,
            0
        )

    def render(self):

        writer=cv2.VideoWriter(
            VIDEO_NO_AUDIO,
            cv2.VideoWriter_fourcc(*"mp4v"),FPS, (WIDTH,HEIGHT)
        )

        print("Rendering...")

        for i in range(self.total_frames):

            current_time=i/FPS
            
            thumbnail_duration = THUMBNAIL_DURATION
            fade_duration = 0.6

            if current_time < thumbnail_duration:

                thumb = self.thumbnail.get_frame(i)

                bg = self.background.get()

                # bắt đầu fade ở 1.4s
                if current_time < thumbnail_duration - fade_duration:

                    frame = thumb

                else:
                    t = (
                        current_time
                        - (thumbnail_duration - fade_duration)
                    ) / fade_duration

                    # Ease
                    t = t * t * (3 - 2 * t)

                    frame = self.blend(thumb, bg, t)

            else:
                frame = self.background.get()
            
            if current_time > 1.6:

                frame = self.subtitle.draw(frame, current_time)

                frame = self.waveform.draw(frame, i)

            # TEXT

            writer.write(frame)

            if i%100==0:

                print(f"{i}/{self.total_frames}")

        writer.release()

        print("Video completed")

# =========================================================
# MERGE AUDIO
# =========================================================

def merge_audio():

    cmd=[
        "ffmpeg",
        "-y",
        "-i",
        VIDEO_NO_AUDIO,
        "-i",
        AUDIO,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "22",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        OUTPUT
    ]

    subprocess.run(cmd)

# =========================================================
# MAIN
# =========================================================

def main():

    print("="*60)

    with open(SCRIPT, encoding="utf-8") as f:

        sentences=[x.strip() for x in f if x.strip()]

    text=" ".join(sentences)

    print("Creating voice...")

    asyncio.run(create_voice(text))

    audio=AudioFileClip(AUDIO)

    duration=audio.duration

    audio.close()

    print("Duration:", duration)

    timestamp=load_timestamp()

    print("Subtitle:", len(timestamp))


    if len(timestamp)==0:

        print("WARNING: No timestamp found!")

    subtitle=SubtitleManager(timestamp)
    
    print("Caching subtitles...")

    for item in timestamp:
        subtitle.create_text(item["text"])

    wave=WaveVisualizer(AUDIO, duration)

    renderer=VideoRenderer(
        duration,
        subtitle,
        wave
    )

    renderer.render()

    print("Merging...")

    merge_audio()

    print("DONE:")

    print(OUTPUT)

if __name__=="__main__":

    main()