"""Cuts each real-footage clip to vertical and saves its frames for the scene page to show."""
import json
import shutil
import subprocess
from pathlib import Path

PROJECT = Path(__file__).parent
FRAMES_DIRECTORY = PROJECT / "clip_frames"
FRAMES_PER_SECOND = 30


def vertical_crop_filter(crop_centre):
    """Crops a wide picture to 9:16 around the chosen point, sized and coloured to match the ad."""
    crop_left = f"max(0,min(iw-ih*9/16,iw*{crop_centre}-ih*9/32))"
    return f"crop=ih*9/16:ih:'{crop_left}':0,scale=1080:1920,eq=saturation=1.12:contrast=1.04,fps={FRAMES_PER_SECOND}"


def extract_clip(clip):
    """Saves the frames one clip needs, numbered from 1."""
    destination = FRAMES_DIRECTORY / clip["name"]
    destination.mkdir(parents=True)
    seconds = clip["end"] - clip["start"]
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-ss", str(clip["sourceStart"]), "-i", str(PROJECT / clip["source"]),
        "-t", str(seconds), "-vf", vertical_crop_filter(clip["cropCentre"]), "-q:v", "3", str(destination / "f%04d.jpg"),
    ], check=True)
    print(clip["name"], len(list(destination.glob("*.jpg"))), "frames")


def main():
    """Replaces any old clip frames with a fresh set."""
    shutil.rmtree(FRAMES_DIRECTORY, ignore_errors=True)
    for clip in json.loads((PROJECT / "timeline.json").read_text())["clips"]:
        extract_clip(clip)


if __name__ == "__main__":
    main()
