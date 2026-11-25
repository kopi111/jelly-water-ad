"""Joins the frames and soundtrack into the final video, and saves the cover and caption beside it."""
import shutil
import subprocess
from pathlib import Path

PROJECT = Path(__file__).parent
DELIVERY_DIRECTORY = Path.home() / "Desktop/Videos/Jelly Water Ad"
VIDEO_NAME = "Jelly-Water-Ad.mp4"
COVER_NAME = "Jelly-Water-Ad-Cover.jpg"
CAPTION_NAME = "Jelly-Water-Ad-Caption.txt"
COVER_FRAME = "f00285.jpg"

CAPTION = """Hot sun. Long day. You need something real. 🥥

Jelly Water is 100% pure coconut water, straight from the coconut with nothing added.
Naturally hydrating. Packed with electrolytes. Rich in potassium. No added sugar.
Product of Jamaica 🇯🇲 Best served ice cold.

Call or WhatsApp to order: (876) 464-4762

#JellyWater #CoconutWater #Jamaica #NaturalDrinks #NatureFresh #JamaicaBusiness #StayHydrated
"""


def encode_video(output_path):
    """Encodes the frames with the soundtrack at the loudness social apps expect."""
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-framerate", "30", "-start_number", "0", "-i", str(PROJECT / "frames/f%05d.jpg"),
        "-i", str(PROJECT / "soundtrack.wav"), "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-shortest", str(output_path),
    ], check=True)


def main():
    """Puts the video, cover and caption together in the delivery folder."""
    DELIVERY_DIRECTORY.mkdir(parents=True, exist_ok=True)
    encode_video(DELIVERY_DIRECTORY / VIDEO_NAME)
    shutil.copy(PROJECT / "frames" / COVER_FRAME, DELIVERY_DIRECTORY / COVER_NAME)
    (DELIVERY_DIRECTORY / CAPTION_NAME).write_text(CAPTION)
    print(f"Delivered to {DELIVERY_DIRECTORY}")


if __name__ == "__main__":
    main()
