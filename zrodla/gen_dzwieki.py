#!/usr/bin/env python3
"""Dźwięki AXON robione od zera (synteza, bez nagrań): trzeszczenie drzewa przed upadkiem.

Pękający pień dużego drzewa: krótkie, ziarniste rozdarcia włókien (gęste serie mikrotrzasków), coraz
dłuższe i głośniejsze, a na końcu długie TRZAAASK z głuchym tąpnięciem pnia. Niskie rezonanse grubego
drewna (ok. 60–170 Hz pień, 260–2400 Hz włókna) i pogłos lasu. v1 (skrzypienie) brzmiało jak horror,
v2 (pojedyncze wysokie kliki) jak łamany patyk.

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


def lowpass(x, freq):
    """Jednobiegunowy filtr dolnoprzepustowy (zabiera ostrość „patyka”)."""
    a = math.exp(-2 * math.pi * freq / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def rip(rng, fibre, trunk, start, length, size, density):
    """Rozdarcie włókien: gęsta seria mikrotrzasków (to daje „krrrrk” dużego pnia, a nie jeden klik patyka).

    Dopisuje impulsy do pobudzenia włókien (fibre) i pnia (trunk)."""
    t = 0.0
    while t < length:
        env = math.sin(math.pi * min(1.0, t / length)) ** 0.6   # narasta i gaśnie
        amp = size * env * (0.3 + 0.7 * rng.random())
        a = int((start + t) * SR)
        k = int((0.0008 + 0.004 * rng.random()) * SR)
        if a + k >= len(fibre):
            break
        burst = rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 3 + 1))
        fibre[a:a + k] += amp * burst
        trunk[a:a + k] += amp * size * burst * 0.8
        t += rng.exponential(1.0 / density)


def creak(seed, length=2.8):
    """Pękający pień: kilka krótkich rozdarć włókien, coraz dłuższych i głośniejszych, na końcu długie
    TRZAAASK z głuchym tąpnięciem pnia. Wszystko przez niskie rezonanse grubego drewna i pogłos lasu.

    Wcześniejsze wersje: v1 (ciągłe skrzypienie) brzmiało jak horror, v2 (pojedyncze wysokie kliki)
    jak łamany patyk. Duże drzewo brzmi nisko, ziarniście i długo."""
    rng = np.random.default_rng(seed)
    n = int(SR * length)
    fibre = np.zeros(n)
    trunk = np.zeros(n)
    main_at = length - 1.45 - 0.15 * rng.random()
    t = 0.05
    while t < main_at - 0.15:
        p = t / main_at
        dur = 0.04 + 0.16 * p * rng.random() + 0.05 * rng.random()
        rip(rng, fibre, trunk, t, dur, 0.5 + 0.4 * p ** 1.3, 180 + 300 * rng.random())
        t += dur + min(0.3, rng.exponential(0.2 * (1 - 0.6 * p))) + 0.04
    # Główne pęknięcie: długie, gęste rozdarcie i mocne uderzenia na starcie.
    rip(rng, fibre, trunk, main_at, 0.55 + 0.15 * rng.random(), 1.0, 650)
    for k in range(3):
        a = int((main_at + 0.01 * k) * SR)
        m = int(0.006 * SR)
        trunk[a:a + m] += (1.5 - 0.4 * k) * rng.standard_normal(m)
        fibre[a:a + m] += (1.2 - 0.3 * k) * rng.standard_normal(m)
    shift = 0.85 + 0.3 * rng.random()   # każdy wariant to trochę inny pień
    wood = np.zeros(n)
    for f, q, g in ((260, 6, 1.0), (470, 8, 0.9), (820, 9, 0.6), (1450, 8, 0.35), (2400, 6, 0.15)):
        wood += g * resonator(fibre, f * shift, q)
    body = np.zeros(n)
    for f, q, g in ((62, 9, 1.4), (105, 12, 1.0), (170, 10, 0.6)):
        body += g * resonator(trunk, f * shift, q)
    dry = lowpass(wood + 1.3 * body, 3200)
    # Pogłos lasu: gasnący, przyciemniony szum jako odpowiedź impulsowa.
    ir_len = int(1.3 * SR)
    ir = rng.standard_normal(ir_len) * np.exp(-np.arange(ir_len) / (0.28 * SR))
    ir = lowpass(ir, 1800)
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    size = 1 << int(math.ceil(math.log2(n + ir_len)))
    wet = np.fft.irfft(np.fft.rfft(dry, size) * np.fft.rfft(ir, size), size)[:n]
    mix = dry + 0.45 * wet * (np.max(np.abs(dry)) / (np.max(np.abs(wet)) + 1e-9))
    fade = int(0.25 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade) ** 2
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
