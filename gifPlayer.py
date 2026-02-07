import threading
import time
from PIL import Image, ImageSequence

class GifPlayer:
    def __init__(self, epd, image, draw, gif_path, x, y, w, h, frame_skip=1, refresh_interval=0.1, lock=None):
        self.epd = epd
        self.image = image
        self.draw = draw
        self.gif_path = gif_path
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.frame_skip = frame_skip
        self.refresh_interval = refresh_interval
        self.lock = lock  # store the shared lock

        self.frames = []
        self.index = 0
        self.load_frames()
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def load_frames(self):
        gif = Image.open(self.gif_path)
        for i, frame in enumerate(ImageSequence.Iterator(gif)):
            if i % self.frame_skip != 0:
                continue
            frame = frame.convert("RGBA")
            bg = Image.new("RGBA", frame.size, (255, 255, 255, 255))
            combined = Image.alpha_composite(bg, frame)
            self.frames.append(combined.convert("L"))

    def get_next_frame(self):
        frame = self.frames[self.index].resize((self.w, self.h))
        self.index = (self.index + 1) % len(self.frames)
        return frame

    def run(self):
        while True:
            frame = self.get_next_frame()
            self.draw.rectangle((self.x, self.y, self.x + self.w, self.y + self.h), fill=255)
            self.image.paste(frame, (self.x, self.y))
                    #self.epd.display_Partial(self.epd.getbuffer(self.image), 0, 0, self.epd.width, self.epd.height)
            time.sleep(self.refresh_interval)