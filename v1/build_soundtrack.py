"""Makes the original backing track and sound effects, then mixes them with the voice-over."""
import json
from pathlib import Path

import numpy
import soundfile
from scipy.signal import butter, resample_poly, sosfilt

PROJECT = Path(__file__).parent
SAMPLE_RATE = 44100
BEAT_SECONDS = 0.6
BAR_SECONDS = BEAT_SECONDS * 4
VOICE_SAMPLE_RATE = 24000

# Four chords on repeat, as MIDI note numbers: G, D, E minor, C.
CHORD_NOTES = [(67, 71, 74), (62, 66, 69), (64, 67, 71), (60, 64, 67)]
BASS_ROOTS = [43, 38, 40, 36]

# The steel-pan tune: (bar in the eight-bar loop, beat in the bar, MIDI note).
PAN_TUNE = [
    (0, 0, 79), (0, 1, 83), (0, 1.5, 86), (0, 3, 83), (1, 0, 81), (1, 1.5, 78), (1, 3, 74),
    (2, 0, 76), (2, 1, 79), (2, 1.5, 83), (2, 3, 79), (3, 0, 76), (3, 1.5, 72), (3, 3, 74),
    (4, 0, 86), (4, 1, 83), (4, 1.5, 79), (4, 3, 83), (5, 0, 81), (5, 1.5, 83), (5, 3, 86),
    (6, 0, 88), (6, 1, 86), (6, 1.5, 83), (6, 3, 79), (7, 0, 81), (7, 1.5, 76), (7, 3, 79),
]


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


def kick_drum():
    """A short drum thump that falls quickly in pitch."""
    time = time_axis(0.3)
    return numpy.sin(2 * numpy.pi * (50 * time + 14 * (1 - numpy.exp(-30 * time)))) * numpy.exp(-11 * time)


def rim_shot():
    """A dry click for the one-drop backbeat."""
    time = time_axis(0.09)
    return filtered(white_noise(0.09, 3), "bandpass", (1400, 4200)) * numpy.exp(-55 * time) * 2.2


def hi_hat(seed):
    """A tight high tick."""
    time = time_axis(0.05)
    return filtered(white_noise(0.05, seed), "highpass", 7500) * numpy.exp(-90 * time)


def chord_stab(notes):
    """A short bright guitar-style chord, the off-beat skank of a reggae groove."""
    time = time_axis(0.2)
    wave = sum(numpy.sign(numpy.sin(2 * numpy.pi * frequency_of(note) * time)) for note in notes) / len(notes)
    return filtered(wave, "bandpass", (500, 3200)) * numpy.exp(-20 * time)


def bass_note(midi_note, seconds):
    """A round bass note with a soft start and end."""
    time = time_axis(seconds)
    pitch = 2 * numpy.pi * frequency_of(midi_note) * time
    fade = numpy.minimum(1, numpy.minimum(time / 0.012, (seconds - time) / 0.04))
    return (numpy.sin(pitch) + 0.3 * numpy.sin(2 * pitch)) * fade


def steel_pan_note(midi_note):
    """A ringing steel-pan style note built from a few overtones."""
    time = time_axis(0.8)
    pitch = 2 * numpy.pi * frequency_of(midi_note) * time
    return (numpy.sin(pitch) + 0.5 * numpy.sin(2 * pitch) + 0.22 * numpy.sin(3 * pitch)) * numpy.exp(-6 * time) / 1.7


def add_one_bar(track, bar_start, chord_index):
    """Plays one bar of the groove: drums, off-beat chords and the bass line."""
    add_at(track, bar_start + 2 * BEAT_SECONDS, kick_drum(), 0.95)
    add_at(track, bar_start + 2 * BEAT_SECONDS, rim_shot(), 0.45)
    for eighth in range(8):
        add_at(track, bar_start + eighth * BEAT_SECONDS / 2, hi_hat(eighth), 0.16 if eighth % 2 else 0.1)
    for beat in (1, 3):
        add_at(track, bar_start + beat * BEAT_SECONDS, chord_stab(CHORD_NOTES[chord_index]), 0.42)
    root = BASS_ROOTS[chord_index]
    for beat, step, seconds in ((0, 0, 0.5), (1.5, 7, 0.26), (2.5, 0, 0.3), (3, 12, 0.26)):
        add_at(track, bar_start + beat * BEAT_SECONDS, bass_note(root + step, seconds), 0.62)


def add_steel_pan(track, first_bar_start, bar_total):
    """Plays the steel-pan tune over the groove, repeating every eight bars."""
    for bar in range(bar_total):
        for loop_bar, beat, note in PAN_TUNE:
            if loop_bar == bar % 8:
                add_at(track, first_bar_start + bar * BAR_SECONDS + beat * BEAT_SECONDS, steel_pan_note(note), 0.17)


def add_heat_haze(track, seconds):
    """The quiet shimmering wind under the hot opening, before the beat arrives."""
    time = time_axis(seconds)
    wind = filtered(white_noise(seconds, 11), "bandpass", (250, 900)) * (0.6 + 0.4 * numpy.sin(2 * numpy.pi * 0.7 * time))
    drone = 0.45 * numpy.sin(2 * numpy.pi * frequency_of(43) * time)
    add_at(track, 0, (wind * 0.35 + drone) * numpy.minimum(1, time / 0.3), 0.32)


def add_final_chord(track, start):
    """Lets the tune finish on one held chord that fades away."""
    time = time_axis(2.4)
    wave = sum(numpy.sin(2 * numpy.pi * frequency_of(note) * time) for note in (55, 67, 71, 74)) / 4
    add_at(track, start, wave * numpy.exp(-1.5 * time), 0.5)
    add_at(track, start, bass_note(43, 1.6), 0.6)


def build_music(duration, groove_start):
    """Builds the music: heat haze first, then the groove from the machete cut."""
    track = numpy.zeros(int(duration * SAMPLE_RATE))
    add_heat_haze(track, groove_start)
    last_groove_start = duration - BAR_SECONDS
    bar_total = round((last_groove_start - groove_start) / BAR_SECONDS)
    for bar in range(bar_total):
        add_one_bar(track, groove_start + bar * BAR_SECONDS, bar % 4)
    add_steel_pan(track, groove_start, bar_total)
    add_final_chord(track, last_groove_start)
    return track


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
    return 1 - 0.55 * smoothed


def main():
    """Builds all three tracks, balances them and saves the finished soundtrack."""
    timeline = json.loads((PROJECT / "timeline.json").read_text())
    duration, moments, voice = timeline["duration"], timeline["moments"], timeline["voice"]
    voice_track = build_voice_track(duration, voice)
    music = build_music(duration, moments["slash"]) * music_volume_under(voice_track)
    mix = 0.95 * music + 0.55 * build_effects(duration, moments, voice) + 1.15 * voice_track
    mix = numpy.tanh(mix / numpy.max(numpy.abs(mix)) * 1.15) * 0.9
    soundfile.write(PROJECT / "soundtrack.wav", numpy.column_stack((mix, mix)), SAMPLE_RATE)
    print(f"soundtrack {len(mix) / SAMPLE_RATE:.2f}s")


if __name__ == "__main__":
    main()
