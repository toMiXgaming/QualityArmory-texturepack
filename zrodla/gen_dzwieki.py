#!/usr/bin/env python3
"""Dźwięki AXON robione od zera (synteza, bez nagrań): trzeszczenie drzewa przed upadkiem.

Trzeszczenie drewna to tarcie typu stick-slip: włókna na przemian się blokują i ześlizgują, więc
słychać szybki ciąg drobnych uderzeń, których tempo pływa (wolno = niskie „skrzypienie”, szybko =
wyższy jęk). Każde uderzenie pobudza rezonanse pnia (kilka filtrów rezonansowych o różnym tłumieniu).
Do tego co jakiś czas pęka włókno: krótki, szerokopasmowy trzask z twardym dzwonieniem drewna.

Wynik: trzy warianty (gra losuje jeden), mono 44,1 kHz, Ogg Vorbis (ffmpeg + libvorbis), zapisane do
zrodla/dzwieki/; axoncore/dzwieki.py dokłada je do paczki z wpisem w assets/axon/sounds.json.

python3 gen_dzwieki.py  (potrzebne: numpy, ffmpeg)"""
import math
import os
import subprocess
import tempfile
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'dzwieki')
SR = 44100


def resonator(x, freq, q):
    """Filtr rezonansowy (biquad pasmowy, stały szczyt 0 dB)."""
    w = 2 * math.pi * freq / SR
    alpha = math.sin(w) / (2 * q)
    b0, b2 = alpha, -alpha
    a0, a1, a2 = 1 + alpha, -2 * math.cos(w), 1 - alpha
    b0, b2, a1, a2 = b0 / a0, b2 / a0, a1 / a0, a2 / a0
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, v in enumerate(x):
        out = b0 * v + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1 = x1, v
        y2, y1 = y1, out
        y[i] = out
    return y


def smooth_noise(rng, n, points):
    """Gładko zmienna krzywa 0..1 (interpolacja kosinusowa między losowymi punktami)."""
    knots = rng.random(points + 1)
    t = np.linspace(0, points, n)
    i = np.minimum(t.astype(int), points - 1)
    f = t - i
    f = (1 - np.cos(f * math.pi)) / 2
    return knots[i] * (1 - f) + knots[i + 1] * f


def creak(seed, length=2.4):
    rng = np.random.default_rng(seed)
    n = int(SR * length)
    t = np.arange(n) / SR

    # Tempo stick-slip: od wolnego skrzypienia (ok. 25 uderzeń/s) do jęku (ok. 140/s) i z powrotem,
    # z drobnym drganiem, żeby nie brzmiało jak syntezator.
    curve = smooth_noise(rng, n, 5)
    rate = 25 + 115 * curve ** 1.4
    rate *= 1 + 0.06 * (rng.random(n) - 0.5)

    # Głośność: kilka „napięć” pnia, każde narasta i puszcza; między nimi prawie cisza.
    env = np.zeros(n)
    pos = 0.05
    while pos < length - 0.25:
        dur = 0.35 + rng.random() * 0.55
        a = int(pos * SR)
        b = min(n, int((pos + dur) * SR))
        seg = np.linspace(0, 1, b - a)
        env[a:b] += (np.sin(seg * math.pi) ** 1.5) * (0.6 + 0.4 * rng.random())
        pos += dur * (0.55 + rng.random() * 0.5)
    env = np.minimum(env, 1.0)

    # Ciąg impulsów: faza tempa, impuls przy każdym przejściu przez całość; siła zależna od obwiedni.
    phase = np.cumsum(rate / SR)
    ticks = np.diff(np.floor(phase), prepend=0) > 0
    exc = np.zeros(n)
    idx = np.nonzero(ticks)[0]
    exc[idx] = env[idx] * (0.6 + 0.4 * rng.random(len(idx)))
    # Każde ześlizgnięcie to nie igła, a krótki szum (szorstkie włókna).
    grain = rng.standard_normal(48) * np.exp(-np.arange(48) / 9.0)
    exc = np.convolve(exc, grain)[:n]

    # Rezonanse pnia: niskie „ciało” i kilka wyższych modów (lekko inne w każdym wariancie).
    modes = [(170, 9, 1.0), (310, 12, 0.8), (620, 16, 0.55), (1180, 20, 0.35), (2300, 26, 0.18)]
    body = np.zeros(n)
    for f, q, g in modes:
        body += g * resonator(exc, f * (0.92 + 0.16 * rng.random()), q)

    # Pękające włókna: 2–4 trzaski w drugiej połowie (drzewo coraz bliżej upadku).
    cracks = np.zeros(n)
    for _ in range(int(rng.integers(2, 5))):
        at = int((0.45 + rng.random() * 0.5) * n)
        m = int(0.06 * SR)
        burst = rng.standard_normal(m) * np.exp(-np.arange(m) / (0.008 * SR))
        cracks[at:at + m] += burst[: max(0, min(m, n - at))] * (0.5 + 0.5 * rng.random())
    cracks = resonator(cracks, 900 + 600 * rng.random(), 3) * 1.6 + resonator(cracks, 2800, 4) * 0.8

    # Niski pomruk naprężonego pnia pod spodem.
    rumble = resonator(rng.standard_normal(n) * env * 0.08, 90, 6)

    # Każda warstwa normalizowana osobno: inaczej trzaski (krótkie i głośne) zgniotłyby skrzypienie do szeptu.
    body /= np.max(np.abs(body)) + 1e-9
    cracks /= np.max(np.abs(cracks)) + 1e-9
    rumble /= np.max(np.abs(rumble)) + 1e-9
    mix = 0.9 * body + 0.75 * cracks + 0.25 * rumble
    mix = np.tanh(mix * 1.4)   # miękkie ograniczenie szczytów, skrzypienie wyraźniejsze
    # Wyciszenie brzegów, normalizacja do -1 dBFS.
    fade = int(0.02 * SR)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix /= np.max(np.abs(mix)) + 1e-9
    return mix * 10 ** (-1 / 20)


def write_ogg(samples, path):
    pcm = (np.clip(samples, -1, 1) * 32767).astype('<i2')
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        wav = tmp.name
    try:
        with wave.open(wav, 'wb') as w:
            w.setnchannels(1)   # mono: tylko mono jest słyszalne przestrzennie (z kierunku drzewa)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-c:a', 'libvorbis', '-q:a', '5',
                        '-map_metadata', '-1', path], check=True)
    finally:
        os.remove(wav)


def main():
    os.makedirs(OUT, exist_ok=True)
    for i, seed in enumerate((11, 23, 37), start=1):
        path = os.path.join(OUT, 'trzeszczenie%d.ogg' % i)
        write_ogg(creak(seed), path)
        print('zapisano', path, os.path.getsize(path), 'B')


if __name__ == '__main__':
    main()
