"""Mixes the licensed music, the sound effects and the voice-over into the finished soundtrack."""
import json
from pathlib import Path

import numpy
import soundfile
from scipy.signal import butter, resample_poly, sosfilt

PROJECT = Path(__file__).parent
SAMPLE_RATE = 44100
VOICE_SAMPLE_RATE = 24000
DROP_FADE_SECONDS = 0.04
OPENING_CUTOFF_HERTZ = 800
OPENING_VOLUME = 0.6
ENDING_FADE_SECONDS = 1.4
MUSIC_BELOW_VOICE_DECIBELS = 5
VOICE_DIP = 0.38

def frequency_of(midi_note):
    """Converts a MIDI note number to its pitch in hertz."""
    return 440.0 * 2 ** ((midi_note - 69) / 12)


def time_axis(seconds):
    """Returns the time of every sample in a sound of the given length."""
    return numpy.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE


def filtered(samples, kind, cutoff):
    """Runs a sound through a low-pass, high-pass or band-pass filter."""
    return sosfilt(butter(4, cutoff, kind, fs=SAMPLE_RATE, output="sos"), samples)


def white_noise(seconds, seed):
    """Returns repeatable random noise, the raw material for hats, wind and water."""
    return numpy.random.default_rng(seed).uniform(-1, 1, int(seconds * SAMPLE_RATE))


def add_at(track, start_seconds, sound, volume=1.0):
    """Mixes a sound into a track, trimming anything that runs past the end."""
    start = int(start_seconds * SAMPLE_RATE)
    length = min(len(sound), len(track) - start)
    if length > 0:
        track[start:start + length] += sound[:length] * volume


def licensed_recording(file_name, starts_at, duration):
    """Loads the part of the recorded track the ad uses, as left and right channels."""
    samples, sample_rate = soundfile.read(PROJECT / file_name, always_2d=True)
    if sample_rate != SAMPLE_RATE:
        raise ValueError(f"{file_name} is {sample_rate} Hz, expected {SAMPLE_RATE} Hz")
    first_sample = int(starts_at * SAMPLE_RATE)
    return samples[first_sample:first_sample + int(duration * SAMPLE_RATE)]


def low_pass_both_channels(stereo, cutoff):
    """Muffles both channels, so the music sounds far away."""
    return numpy.column_stack([filtered(stereo[:, channel], "lowpass", cutoff) for channel in range(2)])


def build_music(duration, drop_at, music):
    """Plays the music muffled through the hot opening, then opens it up fully on the machete cut."""
    recording = licensed_recording(music["file"], music["startsAt"], duration)
    time = time_axis(duration)
    opened = numpy.clip((time - drop_at) / DROP_FADE_SECONDS, 0, 1)[:, None]
    muffled = low_pass_both_channels(recording, OPENING_CUTOFF_HERTZ) * OPENING_VOLUME
    fade_out = numpy.clip((duration - time) / ENDING_FADE_SECONDS, 0, 1)[:, None]
    return (muffled * (1 - opened) + recording * opened) * fade_out


def whoosh(seconds):
    """Air rushing past, for things flying in and scene changes."""
    time = time_axis(seconds)
    return filtered(white_noise(seconds, 21), "bandpass", (300, 2600)) * numpy.sin(numpy.pi * time / seconds) ** 2


def machete_chop():
    """A sharp cut with a low thud under it."""
    time = time_axis(0.4)
    crack = filtered(white_noise(0.4, 31), "highpass", 1800) * numpy.exp(-28 * time)
    thud = numpy.sin(2 * numpy.pi * 95 * time) * numpy.exp(-14 * time)
    return crack + thud


def coconut_thud():
    """A heavy coconut landing."""
    time = time_axis(0.35)
    return numpy.sin(2 * numpy.pi * 72 * time) * numpy.exp(-13 * time)


def pouring_water(seconds):
    """Coconut water filling the bottle, rising in pitch as it fills."""
    time = time_axis(seconds)
    bubbling = 0.7 + 0.3 * numpy.sin(2 * numpy.pi * 17 * time)
    low_half = filtered(white_noise(seconds, 41), "bandpass", (500, 1700))
    high_half = filtered(white_noise(seconds, 42), "bandpass", (1500, 4200))
    rising = time / seconds
    return (low_half * (1 - rising) + high_half * rising) * bubbling * numpy.minimum(1, (seconds - time) / 0.08)


def soft_pop():
    """The little pop as a benefit is ticked."""
    time = time_axis(0.14)
    return numpy.sin(2 * numpy.pi * (620 * time + 1800 * time * time)) * numpy.exp(-30 * time)


def ice_clink(pitch):
    """One ice cube knocking against glass."""
    time = time_axis(0.16)
    return (numpy.sin(2 * numpy.pi * pitch * time) + 0.6 * numpy.sin(2 * numpy.pi * pitch * 2.7 * time)) * numpy.exp(-34 * time)


def build_effects(duration, moments, voice):
    """Places every sound effect on the moments the picture needs them."""
    track = numpy.zeros(int(duration * SAMPLE_RATE))
    add_at(track, moments["coconutFalls"], whoosh(0.5), 0.5)
    add_at(track, moments["coconutLands"], coconut_thud(), 0.9)
    add_at(track, moments["slash"], machete_chop(), 1.0)
    add_at(track, moments["pourStarts"], pouring_water(moments["pourEnds"] - moments["pourStarts"]), 0.5)
    add_at(track, moments["capOn"], soft_pop(), 0.5)
    for line_name in ("hydrating", "electrolytes", "potassium", "sugar"):
        add_at(track, voice[line_name] - 0.05, soft_pop(), 0.7)
    for offset, pitch in ((0, 2500), (0.28, 3100), (0.5, 2200), (0.86, 2900), (1.15, 3400)):
        add_at(track, moments["coldStarts"] + offset, ice_clink(pitch), 0.32)
    add_at(track, moments["endCardStarts"] - 0.15, whoosh(0.45), 0.42)
    return track


def build_voice_track(duration, voice):
    """Lays each recorded voice line at its cue in the timeline."""
    track = numpy.zeros(int(duration * SAMPLE_RATE))
    for line_name, start in voice.items():
        samples, _ = soundfile.read(PROJECT / "voice" / f"{line_name}.wav")
        add_at(track, start, resample_poly(samples, SAMPLE_RATE, VOICE_SAMPLE_RATE))
    return track


def music_volume_under(voice_track):
    """Follows the voice and returns how far to turn the music down at each moment."""
    speaking = filtered(numpy.abs(voice_track), "lowpass", 8)
    window = int(0.15 * SAMPLE_RATE)
    smoothed = numpy.convolve(numpy.clip(speaking / 0.03, 0, 1), numpy.ones(window) / window, "same")
    return 1 - VOICE_DIP * smoothed


def speaking_level(voice_track):
    """Measures how loud the voice is while actually speaking."""
    return numpy.sqrt(numpy.mean(voice_track[numpy.abs(voice_track) > 0.01] ** 2))


def music_level_matching(voice_track, music):
    """Returns the gain that places the music just under the voice."""
    music_level = numpy.sqrt(numpy.mean(music ** 2))
    return speaking_level(voice_track) * 10 ** (-MUSIC_BELOW_VOICE_DECIBELS / 20) / music_level


def main():
    """Builds all three tracks, balances them and saves the finished soundtrack."""
    timeline = json.loads((PROJECT / "timeline.json").read_text())
    duration, moments, voice = timeline["duration"], timeline["moments"], timeline["voice"]
    voice_track = build_voice_track(duration, voice)
    music = build_music(duration, moments["slash"], timeline["music"])
    music = music * music_level_matching(voice_track, music) * music_volume_under(voice_track)[:, None]
    centre_sounds = 0.4 * build_effects(duration, moments, voice) + voice_track
    mix = music + centre_sounds[:, None]
    mix = numpy.tanh(mix / numpy.max(numpy.abs(mix)) * 1.15) * 0.9
    soundfile.write(PROJECT / "soundtrack.wav", mix, SAMPLE_RATE)
    print(f"soundtrack {len(mix) / SAMPLE_RATE:.2f}s")


if __name__ == "__main__":
    main()
