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

def fetch_avatar_sync(url):
    """Fetch avatar image synchronously using requests"""
    resp = requests.get(url, timeout=5)
    img = Image.open(BytesIO(resp.content)).convert("L")
    return img.resize((50, 50))

class DiscordApp:
    def __init__(self, epd, image, draw):
        self.epd = epd
        self.image = image
        self.draw = draw
        self.prev_online_users = set()

        intents = discord.Intents.default()
        intents.members = True
        intents.presences = True
        self.client = discord.Client(intents=intents)

        # Start Discord client in background thread
        threading.Thread(target=self.run_bot, daemon=True).start()

        # Start periodic update
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

            # Only update if list changed
            current_names = {m.name for m in online_members}
            prev_names = {m.name for m in self.prev_online_users}
            if current_names == prev_names:
                self.schedule_update()
                return

            self.prev_online_users = online_members
            print("Online users:", [m.name for m in online_members])

            online_members = online_members[:6]  # max 6 users
            avatar_images = [fetch_avatar_sync(m.display_avatar.url) for m in online_members]

            # Draw avatars onto e-ink
            self.draw.rectangle((425, 0, 800, 75), fill=255)  # clear area
            padding = 10
            x_offset = self.image.width - padding
            y_offset = padding
            for avIm in avatar_images:
                w, h = avIm.size
                x_offset_current = x_offset - w
                self.image.paste(avIm, (x_offset_current, y_offset))
                x_offset -= (w + padding)

            #self.epd.init()
            #self.epd.display(self.epd.getbuffer(self.image))  # full refresh
            #self.epd.init_part()

        except Exception as e:
            print("Discord update failed:", e)

        # Schedule next update
        self.schedule_update()
