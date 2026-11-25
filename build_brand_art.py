"""Exports the bottle, coconut and logo from the label code, so the video matches the printed label."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "projects/jelly-water-logo"))

from build_door_poster import BOTTLE_DEFINITIONS, BOTTLE_OUTLINE, bottle_cap_and_body, bottle_label, natural_seal
from build_logos import SHARED_DEFINITIONS, coconut
from build_nature_fresh_logo import nature_fresh_logo

OUTPUT_FILE = Path(__file__).parent / "brand_art.js"
COCONUT_BODY_START = '<path d="M129 135'
BOTTLE_GLASS_START = f'<path d="{BOTTLE_OUTLINE}"'


def split_before(artwork, marker):
    """Cuts one drawing in two at the marker, so the two halves can move separately."""
    position = artwork.index(marker)
    return artwork[:position], artwork[position:]


def coconut_parts():
    """Returns the straw and the coconut body, with the group wrapper from the logo removed."""
    drawing = coconut().strip().removeprefix('<g transform="">').removesuffix("</g>")
    straw, body = split_before(drawing, COCONUT_BODY_START)
    return {"straw": straw, "coconutBody": body}


def bottle_parts():
    """Returns the cap, the filled bottle and the wrap-around label as separate drawings."""
    cap, glass = split_before(bottle_cap_and_body(), BOTTLE_GLASS_START)
    return {"cap": cap, "glass": glass, "label": bottle_label(), "outline": BOTTLE_OUTLINE}


def main():
    """Writes every drawing into a small script the scene page can load."""
    art = {
        "definitions": SHARED_DEFINITIONS + BOTTLE_DEFINITIONS,
        "seal": natural_seal(20, 20),
        "logo": nature_fresh_logo(0, 0, 100, "#063D1C", "#0B8F3D"),
        **coconut_parts(),
        **bottle_parts(),
    }
    OUTPUT_FILE.write_text(f"window.ART = {json.dumps(art)};\n")


if __name__ == "__main__":
    main()
