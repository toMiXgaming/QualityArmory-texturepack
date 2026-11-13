#!/usr/bin/env python3
"""Dźwięki AXON robione od zera (synteza, bez nagrań): trzeszczenie drzewa przed upadkiem.

Pękające drzewo: pojedyncze, ostre trzaski pękających włókien (krótki szum przez wysokie rezonanse
twardego drewna, z cichym stuknięciem pnia), coraz gęstsze i mocniejsze, a na końcu jeden głośny
TRZASK z drzazgowym ogonem i niskim tąpnięciem. Bez ciągłego skrzypienia (pierwsza wersja z tarciem
stick-slip brzmiała jak buczenie z horroru).

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


def snap(rng, size):
    """Jedno pęknięcie włókna: krótki, ostry trzask drewna (szum 0,5–3 ms przez rezonanse drewna) z cichym stuknięciem."""
    m = int(0.09 * SR)
    burst_len = int((0.0005 + 0.0025 * rng.random()) * SR)
    x = np.zeros(m)
    x[:burst_len] = rng.standard_normal(burst_len) * np.exp(-np.arange(burst_len) / (burst_len / 3 + 1))
    out = np.zeros(m)
    # twarde drewno: kilka wysokich rezonansów, każde pęknięcie trochę inne
    for f, q, g in ((750, 7, 0.7), (1500, 9, 1.0), (2600, 10, 0.8), (4200, 8, 0.45)):
        out += g * resonator(x, f * (0.8 + 0.4 * rng.random()), q)
    out += 0.35 * x   # sam „klik” na początku
    knock = resonator(x, 160 + 120 * rng.random(), 5) * (0.5 + size)   # większe pęknięcie = więcej dołu
    out += knock
    return out * size


def creak(seed, length=2.2):
    """Pękające drzewo: najpierw pojedyncze trzaski włókien, coraz gęstsze, na końcu jeden głośny TRZASK.

    Bez ciągłego skrzypienia (brzmiało jak buczenie z horroru): prawdziwe drzewo przed upadkiem
    głównie trzeszczy pękającymi włóknami, coraz szybciej, aż puszcza."""
    rng = np.random.default_rng(seed)
    n = int(SR * length)
    out = np.zeros(n + SR)
    t = 0.04
    main_at = length - 0.75 - 0.15 * rng.random()   # główny trzask
    while t < main_at:
        progress = t / main_at
        rate = 3 + 45 * progress ** 2.2              # trzasków na sekundę: z rzadkich do gęstych
        size = min(1.0, 0.18 + 0.55 * progress ** 1.5 + 0.35 * rng.lognormal(-1.2, 0.6))
        sn = snap(rng, size)
        a = int(t * SR)
        out[a:a + len(sn)] += sn
        if rng.random() < 0.25:                      # czasem dwa-trzy trzaski tuż po sobie
            for _ in range(int(rng.integers(1, 3))):
                t2 = t + 0.008 + 0.02 * rng.random()
                sn = snap(rng, size * (0.5 + 0.4 * rng.random()))
                a = int(t2 * SR)
                out[a:a + len(sn)] += sn
        t += rng.exponential(1.0 / rate)
    # Główny TRZASK: mocne pęknięcie z drzazgowym ogonem i niskim tąpnięciem pnia.
    a = int(main_at * SR)
    for k in range(3):
        sn = snap(rng, 1.6 - 0.4 * k)
        b = a + int(k * 0.012 * SR)
        out[b:b + len(sn)] += sn
    tail = int(0.25 * SR)
    for j in range(60):                              # drzazgi: gęsty, gasnący chrzęst
        dt = rng.exponential(0.06)
        if dt > 0.25:
            continue
        sn = snap(rng, 0.5 * math.exp(-dt / 0.08) * (0.4 + 0.6 * rng.random()))
        b = a + int((0.02 + dt) * SR)
        out[b:b + len(sn)] += sn
    thump = np.zeros(tail)
    thump[:int(0.004 * SR)] = rng.standard_normal(int(0.004 * SR))
    thump = resonator(thump, 85, 4) * 3.0
    out[a:a + tail] += thump
    mix = out[:n]
    fade = int(0.02 * SR)
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
