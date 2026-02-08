import sys, os
import time
from datetime import datetime
import random
from spotifyEInkApp import SpotifyEInkApp
from discordApp import DiscordApp
sys.path.append("/home/evans/e-Paper/RaspberryPi_JetsonNano/python/lib")
from waveshare_epd import epd7in5_V2
from PIL import Image, ImageDraw, ImageFont, ImageFilter


epd = epd7in5_V2.EPD()
epd.init()
epd.Clear()
width, height = epd.width, epd.height
image = Image.new('1', (width, height), 255)
draw = ImageDraw.Draw(image)

image_dir = "/home/evans/EINK/"
img_path = os.path.join(image_dir, "dashboardBackground.png")
#img_path = os.path.join(os.path.dirname(__file__), "images", "turbogranny.jpg")
logo = Image.open(img_path).convert("L")

logo = logo.resize((epd.width, epd.height), Image.BICUBIC)
image.paste(logo, (0, 0))

time_font = ImageFont.truetype("Eurostile Extended #2 Regular.otf", 35)

draw.text((68, 110),"LAPTIME", font=time_font, fill=255)

discord_app = DiscordApp(
    epd,
    image,
    draw,
    area=(200, 14, 620, 65),
    bg_color=0,
    avatar_size=(35, 35),
    padding=12,
    max_users = 10
)

epd.init_part()
x0, y0, x1 = 65, 150, 420
y1  = y0 + 75

partial_count = 0
FULL_REFRESH_INTERVAL = 600


while True:
    draw.rectangle((x0, y0, x1, y1), fill=0)
    text = time.strftime('%I:%M:%S').lstrip('0')
    draw.text((x0, y0), text, font=time_font, fill=255)
    
    
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
