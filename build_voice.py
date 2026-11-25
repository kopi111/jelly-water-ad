"""Records every voice-over line with Kokoro and saves how long each one runs."""
import json
from pathlib import Path

import soundfile
from kokoro_onnx import Kokoro

VOICE_DIRECTORY = Path(__file__).parent / "voice"
MODEL_DIRECTORY = Path.home() / "kokoro"
VOICE_NAME = "af_heart"
SPEAKING_SPEED = 1.0

# Each line is spelled the way it should sound, so numbers are written out as words.
SPOKEN_LINES = {
    "heat": "Hot sun. Long day.",
    "real": "You need something real.",
    "name": "Jelly Water. One hundred percent pure coconut water.",
    "pure": "Straight from the coconut. Nothing added.",
    "hydrating": "Naturally hydrating.",
    "electrolytes": "Packed with electrolytes.",
    "potassium": "Rich in potassium.",
    "sugar": "No added sugar.",
    "cold": "Ice cold. Fresh. Natural. Jamaican.",
    "order": "Order your Jelly Water today. Call or WhatsApp.",
    "phone": "Eight seven six. Four six four. Four seven six two.",
}


def record_line(engine, line_name, spoken_text):
    """Speaks one line into its own wav file and returns its length in seconds."""
    samples, sample_rate = engine.create(spoken_text, voice=VOICE_NAME, speed=SPEAKING_SPEED, lang="en-us")
    soundfile.write(VOICE_DIRECTORY / f"{line_name}.wav", samples, sample_rate)
    return round(len(samples) / sample_rate, 3)


def main():
    """Records all the lines and writes their lengths to durations.json."""
    VOICE_DIRECTORY.mkdir(exist_ok=True)
    engine = Kokoro(str(MODEL_DIRECTORY / "kokoro-v1.0.onnx"), str(MODEL_DIRECTORY / "voices-v1.0.bin"))
    durations = {name: record_line(engine, name, words) for name, words in SPOKEN_LINES.items()}
    (VOICE_DIRECTORY / "durations.json").write_text(json.dumps(durations, indent=2))
    print(json.dumps(durations, indent=2))


if __name__ == "__main__":
    main()
