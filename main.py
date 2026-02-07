import sys
import os
import time
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageSequence, ImageFilter
import threading

# Custom apps
from spotifyEInkApp import SpotifyEInkApp
from discordApp import DiscordApp
from gifPlayer import GifPlayer

# Waveshare e-ink library
sys.path.append("/home/evans/e-Paper/RaspberryPi_JetsonNano/python/lib")
from waveshare_epd import epd7in5_V2

# ========================
# Constants
# ========================
IMAGE_DIR = "/home/evans/EINK/images"
GIF_DIR= "/home/evans/EINK/gifs"

MAX_LOGO_H = 400
MIN_LOGO_H = 200
MAX_LOGO_W = 350

FONT_PATH_BOLD = "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf"
TIME_FONT_SIZE = 70
DATE_FONT_SIZE = 36

GIF_X, GIF_Y = 0, 390
GIF_W, GIF_H = 100, 100

FULL_REFRESH_INTERVAL = 600

# Clock area coordinates
CLOCK_X0, CLOCK_Y0, CLOCK_X1, CLOCK_Y1 = -3, -10, 420, 100

# ========================
# Initialize E-Paper
# ========================
epd = epd7in5_V2.EPD()
epd.init()
epd.Clear()
width, height = epd.width, epd.height

image = Image.new('1', (width, height), 255)
draw = ImageDraw.Draw(image)
image_lock = threading.Lock()

# ========================
# Load and paste random logo
# ========================
def load_logo(image_dir):
    rand_img = random.choice(os.listdir(image_dir))
    img_path = os.path.join(image_dir, rand_img)
    logo = Image.open(img_path).convert("L")

    # Clean logo: thresholding
    logo = logo.point(lambda x: 255 if x > 225 else x)

    # Resize logo
    w, h = logo.size
    if h > MAX_LOGO_H:
        scale = MAX_LOGO_H / h
        w, h = int(w * scale), MAX_LOGO_H
    elif h < MIN_LOGO_H:
        scale = MIN_LOGO_H / h
        w, h = int(w * scale), MIN_LOGO_H
    if w > MAX_LOGO_W:
        scale = MAX_LOGO_W / w
        w, h = MAX_LOGO_W, int(h * scale)

    return logo.resize((w, h), Image.BICUBIC)

logo_clean = load_logo(IMAGE_DIR)
image.paste(logo_clean, (width - logo_clean.width, height - logo_clean.height))

# ========================
# Load fonts
# ========================
time_font = ImageFont.truetype(FONT_PATH_BOLD, TIME_FONT_SIZE)
date_font = ImageFont.truetype(FONT_PATH_BOLD, DATE_FONT_SIZE)

# ========================
# Draw date
# ========================
today = datetime.now()
date_str = today.strftime("%a, %b %d, %Y")
draw.text((0, 70), date_str, font=date_font, fill=0)

# Initial full display
epd.display(epd.getbuffer(image))

# Partial update mode
epd.init_part()

# ========================
# Initialize apps
# ========================
spotify_app = SpotifyEInkApp(epd, image, draw)
discord_app = DiscordApp(epd, image, draw)

rand_img = random.choice(os.listdir(GIF_DIR))
img_path = os.path.join(GIF_DIR, rand_img)

gif1 = GifPlayer(epd, image, draw, img_path, 0, 385, 100, 100, lock=image_lock)
rand_img = random.choice(os.listdir(GIF_DIR))
img_path = os.path.join(GIF_DIR, rand_img)
gif1 = GifPlayer(epd, image, draw, img_path, 100, 385, 100, 100, lock=image_lock)
rand_img = random.choice(os.listdir(GIF_DIR))
img_path = os.path.join(GIF_DIR, rand_img)
gif1 = GifPlayer(epd, image, draw, img_path, 200, 385, 100, 100, lock=image_lock)
rand_img = random.choice(os.listdir(GIF_DIR))
img_path = os.path.join(GIF_DIR, rand_img)
gif1 = GifPlayer(epd, image, draw, img_path, 300, 385, 100, 100, lock=image_lock)
rand_img = random.choice(os.listdir(GIF_DIR))
img_path = os.path.join(GIF_DIR, rand_img)
gif1 = GifPlayer(epd, image, draw, img_path, 400, 385, 100, 100, lock=image_lock)


# ========================
# Main loop
# ========================
partial_count = 0
while True:
    now = time.time()
    with image_lock:
        # Draw clock
        draw.rectangle((CLOCK_X0, CLOCK_Y0, CLOCK_X1, 65), fill=255)
        current_time = time.strftime('%I:%M %p').lstrip('0')
        draw.text((CLOCK_X0, CLOCK_Y0), current_time, font=time_font, fill=0)
        epd.display_Partial(epd.getbuffer(image), 0, 0, epd.width, epd.height)

    # Full refresh
    partial_count += 1
    if partial_count >= FULL_REFRESH_INTERVAL:
        with image_lock:
            partial_count = 0
            epd.init()
            epd.display(epd.getbuffer(image))
            epd.init_part()

    #time.sleep(1 - (time.time() % 1))

# Sleep to save power (never reached)
epd.sleep()