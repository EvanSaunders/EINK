import sys, os
import time
from datetime import datetime
import random
from spotifyEInkApp import SpotifyEInkApp
sys.path.append("/home/evans/e-Paper/RaspberryPi_JetsonNano/python/lib")
from waveshare_epd import epd7in5_V2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

epd = epd7in5_V2.EPD()
epd.init()
epd.Clear()
width, height = epd.width, epd.height
image = Image.new('1', (width, height), 255)
draw = ImageDraw.Draw(image)

image_dir = "/home/evans/EINK/images"
rand_img = random.choice(os.listdir(image_dir))
img_path = os.path.join(image_dir, rand_img)
#img_path = os.path.join(os.path.dirname(__file__), "images", "floatzel.jpg")
logo = Image.open(img_path).convert("L")

logo_clean = logo.point(lambda x: 255 if x > 225 else x)
#logo_clean = logo.convert("1", dither=Image.FLOYDSTEINBERG)
#logo_clean = logo_bw.filter(ImageFilter.MedianFilter(size=3))

MAX_H = 450
MIN_H = 200
MAX_W = 350

w, h = logo_clean.size

if h > MAX_H:
    scale = MAX_H / h
    w = int(w * scale)
    h = MAX_H
elif h < MIN_H:
    scale = MIN_H / h
    w = int(w * scale)
    h = MIN_H

if w > MAX_W:
    scale = MAX_W / w
    w = MAX_W
    h = int(h * scale)

logo_clean = logo_clean.resize((w, h), Image.BICUBIC)

x = width - w
y = height - h
image.paste(logo_clean, (x, y))

#fonts
time_font = ImageFont.truetype("/usr/share/fonts/type1/urw-base35/URWGothic-BookOblique.t1", 70)
font = ImageFont.truetype("/usr/share/fonts/type1/urw-base35/URWGothic-BookOblique.t1", 36)

today = datetime.now()
date_str = today.strftime("%a, %b %d, %Y")
draw.text((10, 95), date_str, font=font, fill=0)
epd.display(epd.getbuffer(image))


epd.init_part()
x0, y0, x1, y1 = 10, 10, 400, 100

spotify_app = SpotifyEInkApp(epd, image, draw)

partial_count = 0
FULL_REFRESH_INTERVAL = 600

y = 300
box_w = 40
box_h = 40


while True:
    draw.rectangle((x0, y0, x1, y1), fill=255)
    text = time.strftime('%I:%M:%S %p').lstrip('0')
    draw.text((x0, y0), text, font=time_font, fill=0)
    
    
    epd.display_Partial(epd.getbuffer(image), 0, 0, epd.width, epd.height)
    
    if partial_count >= FULL_REFRESH_INTERVAL:
        partial_count = 0
        epd.init()
        epd.display(epd.getbuffer(image))  # full refresh
        epd.init_part()
    partial_count += 1
    time.sleep(1 - (time.time() % 1))

# Sleep to save power (never reached in this loop)
epd.sleep()
