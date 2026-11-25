"""Draws the video frames from scene.html, or a few test stills when given --stills."""
import argparse
import asyncio
import json
import shutil
from pathlib import Path

from playwright.async_api import async_playwright

PROJECT = Path(__file__).parent
FRAMES_DIRECTORY = PROJECT / "frames"
STILLS_DIRECTORY = PROJECT / "stills"
FRAMES_PER_SECOND = 30
WORKER_COUNT = 6
REQUIRED_FONTS = ["700 40px Fredoka", "800 40px Poppins", "700 40px Poppins", "600 40px Poppins"]


class SceneError(Exception):
    """The scene page could not be drawn correctly."""


async def open_scene(browser, timeline):
    """Opens one tab with the scene built, and stops if a brand font failed to load."""
    page = await browser.new_page(viewport={"width": 1080, "height": 1920})
    page.on("pageerror", lambda error: print("PAGE ERROR", error))
    await page.goto(f"file://{PROJECT}/scene.html")
    await page.evaluate("fonts => Promise.all(fonts.map(font => document.fonts.load(font)))", REQUIRED_FONTS)
    missing = await page.evaluate("fonts => fonts.filter(font => !document.fonts.check(font))", REQUIRED_FONTS)
    if missing:
        raise SceneError(f"Fonts did not load: {missing}")
    await page.evaluate("timeline => setup(timeline)", timeline)
    return page


async def draw_frames(browser, timeline, frame_numbers):
    """Draws one worker's share of the frames."""
    page = await open_scene(browser, timeline)
    for number in frame_numbers:
        await page.evaluate(f"render({number / FRAMES_PER_SECOND})")
        await page.screenshot(path=FRAMES_DIRECTORY / f"f{number:05d}.jpg", type="jpeg", quality=95)
    await page.close()


async def draw_all_frames(timeline):
    """Shares the frames between several browser tabs so the render finishes sooner."""
    shutil.rmtree(FRAMES_DIRECTORY, ignore_errors=True)
    FRAMES_DIRECTORY.mkdir()
    frame_total = round(timeline["duration"] * FRAMES_PER_SECOND)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        shares = [range(worker, frame_total, WORKER_COUNT) for worker in range(WORKER_COUNT)]
        await asyncio.gather(*(draw_frames(browser, timeline, share) for share in shares))
        await browser.close()
    print(f"{frame_total} frames drawn")


async def draw_stills(timeline, seconds):
    """Saves test pictures at the given moments, to check the look before a full render."""
    STILLS_DIRECTORY.mkdir(exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await open_scene(browser, timeline)
        for second in seconds:
            await page.evaluate(f"render({second})")
            await page.screenshot(path=STILLS_DIRECTORY / f"s{second:06.2f}.jpg", type="jpeg", quality=85)
        await browser.close()


def main():
    """Reads the timeline, then draws either the test stills or the whole video."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--stills", type=float, nargs="*")
    arguments = parser.parse_args()
    timeline = json.loads((PROJECT / "timeline.json").read_text())
    if arguments.stills:
        asyncio.run(draw_stills(timeline, arguments.stills))
    else:
        asyncio.run(draw_all_frames(timeline))


if __name__ == "__main__":
    main()
