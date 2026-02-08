import threading
import discord
import aiohttp
import os
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from io import BytesIO
import requests
import asyncio

load_dotenv()
bot_token = os.getenv("DISCORD_TOKEN")
guild_id = int(os.getenv("GUILD_ID"))
channel_id = int(os.getenv("CHANNEL_ID"))

def fetch_avatar_sync(url, size):
    resp = requests.get(url, timeout=5)
    img = Image.open(BytesIO(resp.content)).convert("L")
    return img.resize(size)

class DiscordApp:
    def __init__(
        self,
        epd,
        image,
        draw,
        area=(425, 0, 800, 75),
        bg_color=255,
        avatar_size=(50, 50),
        padding=10,
        max_users = 6
    ):
        self.epd = epd
        self.image = image
        self.draw = draw

        self.area = area
        self.bg_color = bg_color
        self.avatar_size = avatar_size
        self.padding = padding

        self.prev_online_users = set()

        intents = discord.Intents.default()
        intents.members = True
        intents.presences = True
        self.client = discord.Client(intents=intents)

        threading.Thread(target=self.run_bot, daemon=True).start()
        self.schedule_update()

    def run_bot(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.client.run(bot_token)

    def schedule_update(self):
        threading.Timer(10, self.update_online_users).start()

    def update_online_users(self):
        try:
            guild = self.client.get_guild(guild_id)
            if not guild:
                print("Guild not found")
                self.schedule_update()
                return

            channel = guild.get_channel(channel_id)
            if not channel:
                print("Channel not found")
                self.schedule_update()
                return

            online_members = [
                m for m in guild.members
                if m.status == discord.Status.online
                and channel.permissions_for(m).view_channel
                and not m.bot
            ]

            current_names = {m.name for m in online_members}
            prev_names = {m.name for m in self.prev_online_users}
            if current_names == prev_names:
                self.schedule_update()
                return

            self.prev_online_users = online_members
            online_members = online_members[:6]

            avatar_images = [
                fetch_avatar_sync(m.display_avatar.url, self.avatar_size)
                for m in online_members
            ]

            x1, y1, x2, y2 = self.area

            # Clear custom region with custom background color
            self.draw.rectangle((x1, y1, x2, y2), fill=self.bg_color)

            # Start drawing from the right edge of the region
            x_offset = x2 - self.padding
            y_offset = y1 + self.padding

            for avIm in avatar_images:
                w, h = avIm.size
                x_current = x_offset - w
                self.image.paste(avIm, (x_current, y_offset))
                x_offset -= (w + self.padding)

        except Exception as e:
            print("Discord update failed:", e)

        self.schedule_update()