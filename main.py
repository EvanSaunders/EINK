import sys, os
sys.path.append("/home/evans/e-Paper/RaspberryPi_JetsonNano/python/lib")
from waveshare_epd import epd7in5_V2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Initialize the display
epd = epd7in5_V2.EPD()
epd.init()
epd.Clear()

# Create a blank image with mode '1' for 1-bit color
width, height = epd.width, epd.height
image = Image.new('1', (width, height), 255)  # 255 = white background

# Get drawing context
draw = ImageDraw.Draw(image)

# Draw text
font = ImageFont.load_default()
text = "Hello, e-Ink!"
draw.text((100, 100), text, font=font, fill=0)  # 0 = black

# Open and paste an image
img_path = os.path.join(os.path.dirname(__file__), "images", "chopper.jpg")
logo = Image.open(img_path).convert('L')  # Convert to grayscale

# Apply threshold to remove off-white background
threshold = 200  # adjust as needed
logo_bw = logo.point(lambda x: 0 if x < threshold else 255, '1')  # Convert to 1-bit B/W

# Optional: remove small black dots
logo_clean = logo_bw.filter(ImageFilter.MedianFilter(size=3))

# Paste onto main image
image.paste(logo_clean, (50, 100))  # Position of the image

# Display the image on the e-ink
epd.display(epd.getbuffer(image))

# Sleep to save power
epd.sleep()


