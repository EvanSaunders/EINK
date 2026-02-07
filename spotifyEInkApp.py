from dotenv import load_dotenv
import os, requests, time, threading
from PIL import Image, ImageFont
from io import BytesIO




load_dotenv()
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")

def refresh_access_token():
        url = "https://accounts.spotify.com/api/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        auth_header = requests.auth.HTTPBasicAuth(client_id, client_secret)
        response = requests.post(url, data=payload, auth=auth_header)
        response.raise_for_status()
        return response.json()["access_token"]
    
    
MAX_WIDTH = 400
def truncate_text(text, font, max_width):
    def text_width(s):
        bbox = font.getbbox(s)
        return bbox[2] - bbox[0]

    if text_width(text) <= max_width:
        return text
    while text_width(text + "...") > max_width:
        text = text[:-1]
    return text + "..."
    
class SpotifyEInkApp:
    def __init__(self, epd, image, draw):
        self.epd = epd
        self.image = image
        self.draw = draw
        self.access_token = refresh_access_token()
        self.token_expires_at = time.time() + 3600
        self.image_url = None
        self.album_img = None
        
        self.image_url = None
        self.album_img = None
        self.last_track_name = None
        self.last_artist_name = None

        self.update_now_playing()  # initial fetch
        self.schedule_update()

    def schedule_update(self):
        threading.Timer(10, self.update_now_playing).start()
        
    

    def update_now_playing(self):
        if time.time() >= self.token_expires_at - 60:
            self.access_token = refresh_access_token()
            self.token_expires_at = time.time() + 3600

        url = "https://api.spotify.com/v1/me/player/currently-playing?fields=item(name,artists(name),album(images(url)))"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data and "item" in data and data["item"]:
                    track_name = data["item"]["name"]
                    artist_name = data["item"]["artists"][0]["name"]
                    album_img_url = data["item"]["album"]["images"][0]["url"]
                    
                    if (track_name != self.last_track_name or
                        artist_name != self.last_artist_name):
                        
                        print(track_name)

                        self.last_track_name = track_name
                        self.last_artist_name = artist_name

                        if self.image_url != album_img_url:
                            self.image_url = album_img_url
                            img_resp = requests.get(self.image_url, timeout=5)
                            img = Image.open(BytesIO(img_resp.content)).convert("L")
                            img = img.resize((200, 200))
                            self.album_img = img

                        # Draw onto e-ink
                        font = ImageFont.truetype("/usr/share/fonts/type1/urw-base35/URWGothic-BookOblique.t1", 35)
                        self.draw.rectangle((8, 165, 410, 500), fill=255)  # clear area
                        track_display = truncate_text(track_name, font, MAX_WIDTH)
                        artist_display = truncate_text(artist_name, font, MAX_WIDTH)
                        self.draw.text((8, 170), track_display, font=font, fill=0)
                        self.draw.text((10, 205), artist_display, font=font, fill=0)
                        if self.album_img:
                            self.image.paste(self.album_img, (10, 255))

                        #self.epd.display_Partial(self.epd.getbuffer(self.image), 0, 0, self.epd.width, self.epd.height)
                        
                        #self.epd.init()
                        #self.epd.display(self.epd.getbuffer(self.image))
        except Exception as e:
            print("Spotify update failed:", e)

        self.schedule_update()
