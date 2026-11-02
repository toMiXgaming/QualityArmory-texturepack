#version 150

#moj_import <minecraft:fog.glsl>

// Musi się zgadzać z rendertype_text.vsh.
#define AXON_COLS 5
#define AXON_ROWS 3
#define AXON_SPRITES 5
#define AXON_CLOCK_PERIOD 40.0

uniform sampler2D Sampler0;

uniform vec4 ColorModulator;
uniform float FogStart;
uniform float FogEnd;
uniform vec4 FogColor;

in float vertexDistance;
in vec4 vertexColor;
in vec2 texCoord0;
flat in int axonMap;
flat in int axonTile;
flat in int axonDensity;
flat in vec2 axonCursor;
flat in vec4 axonSpriteA[AXON_SPRITES];
flat in vec4 axonSpriteB[AXON_SPRITES];
flat in vec2 axonSpriteLim[AXON_SPRITES];
flat in float axonClock;

out vec4 fragColor;


// ---------------------------------------------------------------- sprity
// Ruchome elementy mini gier. Serwer zapisuje parametry w ostatnim wierszu kafla (rendertype_text.vsh),
// a tutaj rysujemy je w każdej klatce klienta. Pozycja = (x, y) w chwili "stamp" + prędkość * czas, który
// minął na zegarze klienta. Rodzaje:
//  1 znacznik skali       2 rozżarzony pręt     3 płomienie       4 pulsujący cel
//  5 narzędzie przy kursorze (rozmiar = numer narzędzia, lo = 1 gdy narzędzie pracuje, x/y = punkt zaczepienia)
//  6 siatka celownika optyki (lo = procent przytrzymania)       7 ruchomy cel optyki (rozmiar = tolerancja)
// Animacje mają okres będący dzielnikiem 40 ticków, więc zawinięcie zegara jest niewidoczne.

const float AXON_TAU = 6.2831853;

vec3 axonEffectColor(int index, float heat) {
    if (index == 15) {
        vec3 cold = vec3(96.0, 104.0, 116.0) / 255.0;
        vec3 red = vec3(200.0, 60.0, 30.0) / 255.0;
        vec3 hot = vec3(255.0, 240.0, 190.0) / 255.0;
        return heat < 0.5 ? mix(cold, red, heat * 2.0) : mix(red, hot, (heat - 0.5) * 2.0);
    }
    if (index == 1) return vec3(52.0, 210.0, 123.0) / 255.0;
    if (index == 2) return vec3(239.0, 74.0, 74.0) / 255.0;
    if (index == 3) return vec3(255.0, 209.0, 102.0) / 255.0;
    if (index == 4) return vec3(94.0, 214.0, 224.0) / 255.0;
    if (index == 5) return vec3(255.0, 138.0, 61.0) / 255.0;
    if (index == 6) return vec3(150.0, 160.0, 172.0) / 255.0;
    if (index == 7) return vec3(150.0, 200.0, 255.0) / 255.0;
    if (index == 8) return vec3(86.0, 150.0, 255.0) / 255.0;
    if (index == 9) return vec3(52.0, 210.0, 123.0) / 255.0;
    if (index == 10) return vec3(255.0, 106.0, 90.0) / 255.0;
    if (index == 11) return vec3(188.0, 120.0, 255.0) / 255.0;
    if (index == 12) return vec3(255.0, 196.0, 70.0) / 255.0;
    if (index == 13) return vec3(70.0, 214.0, 214.0) / 255.0;
    if (index == 14) return vec3(255.0, 200.0, 110.0) / 255.0;
    return vec3(241.0, 244.0, 249.0) / 255.0;
}

void axonBlend(inout vec3 base, vec3 color, float alpha) {
    base = mix(base, color, clamp(alpha, 0.0, 1.0));
}

float axonHash(float n) {
    return fract(sin(n) * 43758.5453);
}

vec2 axonRot(vec2 p, float degreesCcw) {
    float a = radians(degreesCcw);
    float c = cos(a);
    float s = sin(a);
    return vec2(c * p.x + s * p.y, -s * p.x + c * p.y);
}

// Zaokrąglony prostokąt od (x, y) o rozmiarze (w, h) i promieniu r: odległość ze znakiem.
float axonRect(vec2 p, float x, float y, float w, float h, float r) {
    vec2 c = vec2(x + w * 0.5, y + h * 0.5);
    vec2 q = abs(p - c) - vec2(w * 0.5 - r, h * 0.5 - r);
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

float axonSegment(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a;
    vec2 ba = b - a;
    float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-4), 0.0, 1.0);
    return length(pa - ba * h);
}

float axonCover(float d, float px) {
    return clamp(0.5 - d / px, 0.0, 1.0);
}

// Kształt z pionowym gradientem koloru (od góry y0 do dołu y1).
void axonShape(inout vec3 base, float d, float px, vec2 p, float y0, float y1, vec3 top, vec3 bottom) {
    float k = clamp((p.y - y0) / max(y1 - y0, 1e-3), 0.0, 1.0);
    axonBlend(base, mix(top, bottom, k), axonCover(d, px));
}

void axonGlow(inout vec3 base, vec2 p, vec2 c, float radius, vec3 color, float alpha) {
    axonBlend(base, color, alpha * clamp(1.0 - length(p - c) / radius, 0.0, 1.0));
}

void axonSparks(inout vec3 base, vec2 p, vec2 c, float strength, vec3 color, float px) {
    if (length(p - c) > 40.0) {
        return;
    }
    float seed = floor(axonClock * 0.7);
    for (int i = 0; i < 9; i++) {
        float a = axonHash(seed * 13.17 + float(i) * 7.31) * AXON_TAU;
        float d = 4.0 + axonHash(seed * 5.71 + float(i) * 3.13) * 22.0 * strength;
        vec2 dir = vec2(cos(a), sin(a));
        vec2 from = c + dir * d * 0.4;
        vec2 to = c + dir * d + vec2(0.0, -3.0);
        axonBlend(base, color, 0.9 * axonCover(axonSegment(p, from, to) - 0.7, px));
    }
}

vec3 axonRgb(float r, float g, float b) {
    return vec3(r, g, b) / 255.0;
}

void axonTool(inout vec3 base, vec2 p, float px, vec2 cursor, int tool, bool on, vec3 color, vec2 anchor) {
    vec2 q = p - cursor;
    if (tool == 9) {
        // przeciągana część (układanie): przerywana linia od miejsca części do kursora i część przy kursorze
        float t = dot(p - anchor, normalize(cursor - anchor + 1e-4));
        float dash = step(0.5, fract(t / 10.0 - axonClock / 40.0 * 4.0));
        axonBlend(base, color, 0.6 * dash * axonCover(axonSegment(p, anchor, cursor) - 0.8, px));
        if (length(q) > 40.0) return;
        axonBlend(base, vec3(0.0), 0.27 * axonCover(length(q * vec2(1.0, 1.1) - vec2(0.0, 3.0)) - 23.0, px));
        float d = axonRect(q, -22.0, -22.0, 44.0, 44.0, 8.0);
        axonShape(base, d, px, q, -22.0, 22.0, clamp(color * 1.15, 0.0, 1.0), color * 0.7);
        axonBlend(base, vec3(1.0), 0.9 * axonCover(abs(d + 0.7) - 0.7, px));
        float ang = atan(q.y, q.x) - axonClock * AXON_TAU / 40.0 * 2.0;
        float teeth = 11.0 + 2.0 * step(0.0, sin(ang * 8.0));
        float gear = max(length(q) - teeth, 4.0 - length(q));
        axonBlend(base, vec3(1.0), 0.84 * axonCover(gear, px));
        return;
    }
    if (length(q) > 90.0) return;
    if (tool == 1) {
        // śrubokręt
        vec2 r = axonRot(q - vec2(4.0, on ? 3.0 : 0.0), 35.0);
        axonShape(base, axonRect(r, -3.0, 6.0, 6.0, 16.0, 2.0), px, r, 6.0, 22.0, axonRgb(190.0, 196.0, 206.0), axonRgb(150.0, 156.0, 166.0));
        float h = axonRect(r, -8.0, 22.0, 16.0, 34.0, 7.0);
        axonShape(base, h, px, r, 22.0, 56.0, axonRgb(255.0, 160.0, 80.0), axonRgb(190.0, 80.0, 30.0));
        axonBlend(base, axonRgb(60.0, 30.0, 14.0), axonCover(abs(h + 0.5) - 0.5, px));
    } else if (tool == 2) {
        // młotek: przy uderzeniu przechylony do przodu
        vec2 r = axonRot(q, on ? 20.0 : -40.0);
        axonShape(base, axonRect(r, -3.0, -52.0, 6.0, 52.0, 3.0), px, r, -52.0, 0.0, axonRgb(150.0, 100.0, 56.0), axonRgb(120.0, 80.0, 44.0));
        axonShape(base, axonRect(r, -17.0, -66.0, 34.0, 20.0, 4.0), px, r, -66.0, -46.0, axonRgb(200.0, 206.0, 216.0), axonRgb(86.0, 94.0, 108.0));
    } else if (tool == 3) {
        // szlifierka: tarcza z obracającymi się ziarnami
        axonBlend(base, vec3(0.0), 0.27 * axonCover(length(q * vec2(1.0, 1.1) - vec2(0.0, 3.0)) - 21.0, px));
        axonBlend(base, axonRgb(40.0, 44.0, 52.0), axonCover(length(q) - 20.0, px));
        float spin = axonClock * AXON_TAU / 40.0 * (on ? 12.0 : 1.0);
        float sector = AXON_TAU / 12.0;
        float a = atan(q.y, q.x) - spin;
        float am = mod(a + sector * 0.5, sector) - sector * 0.5;
        axonBlend(base, axonRgb(190.0, 120.0, 70.0), axonCover(length(vec2(length(q) * am, length(q) - 17.0)) - 2.2, px));
        axonBlend(base, axonRgb(150.0, 158.0, 170.0), axonCover(length(q) - 8.0, px));
        if (on) axonSparks(base, p, cursor + vec2(14.0, 12.0), 1.2, axonRgb(255.0, 210.0, 120.0), px);
    } else if (tool == 4) {
        // strug i wióry
        axonShape(base, axonRect(q, -8.0, -28.0, 36.0, 32.0, 5.0), px, q, -28.0, 4.0, axonRgb(230.0, 160.0, 70.0), axonRgb(150.0, 90.0, 36.0));
        axonBlend(base, axonRgb(190.0, 196.0, 206.0), axonCover(axonRect(q, -12.0, 4.0, 44.0, 7.0, 2.0), px));
        axonBlend(base, axonRgb(120.0, 70.0, 30.0), axonCover(axonRect(q, 8.0, -42.0, 7.0, 16.0, 3.0), px));
        if (on) {
            for (int i = 0; i < 4; i++) {
                float a = axonClock * AXON_TAU / 40.0 * 3.0 + float(i);
                vec2 c = vec2(20.0 + cos(a) * 9.0 + float(i) * 4.0, 8.0 - abs(sin(a)) * 12.0);
                axonBlend(base, axonRgb(236.0, 206.0, 150.0), axonCover(length(q - c) - 2.4, px));
            }
        }
    } else if (tool == 5) {
        // gąbka i bąbelki
        vec2 r = axonRot(q, -12.0);
        axonShape(base, axonRect(r, -22.0, -14.0, 44.0, 28.0, 8.0), px, r, -14.0, 14.0, axonRgb(255.0, 220.0, 90.0), axonRgb(200.0, 150.0, 30.0));
        axonBlend(base, axonRgb(90.0, 160.0, 90.0), axonCover(axonRect(r, -22.0, -14.0, 44.0, 8.0, 4.0), px));
        if (on) {
            float seed = floor(axonClock * 0.4);
            for (int i = 0; i < 6; i++) {
                vec2 c = vec2((axonHash(seed * 3.1 + float(i) * 1.7) - 0.5) * 46.0, (axonHash(seed * 4.3 + float(i) * 2.9) - 0.5) * 36.0);
                float rad = 3.0 + axonHash(seed * 7.7 + float(i)) * 4.0;
                axonBlend(base, axonRgb(200.0, 235.0, 255.0), 0.8 * axonCover(abs(length(q - c) - rad) - 0.6, px));
            }
        }
    } else if (tool == 6) {
        // palnik spawalniczy: przy spawaniu niebieska poświata, punkt i iskry
        if (on) {
            axonGlow(base, p, cursor, 34.0, axonRgb(150.0, 200.0, 255.0), 0.55);
            axonBlend(base, vec3(1.0), axonCover(length(q) - 5.0, px));
            axonSparks(base, p, cursor, 1.5, axonRgb(255.0, 200.0, 110.0), px);
        }
        vec2 r = axonRot(q, 35.0);
        axonShape(base, axonRect(r, -4.0, -60.0, 8.0, 54.0, 3.0), px, r, -60.0, -6.0, axonRgb(120.0, 128.0, 140.0), axonRgb(60.0, 66.0, 76.0));
        axonBlend(base, axonRgb(200.0, 206.0, 216.0), axonCover(axonRect(r, -3.0, -8.0, 6.0, 10.0, 2.0), px));
    } else if (tool == 7) {
        // wiertarka: drży i kręci gwintem przy wierceniu
        vec2 r = q - vec2(on ? sin(axonClock * AXON_TAU / 40.0 * 19.0) * 1.2 : 0.0, 0.0);
        float body = axonRect(r, -5.0, -64.0, 10.0, 58.0, 3.0);
        axonShape(base, body, px, r, -64.0, -6.0, axonRgb(170.0, 176.0, 188.0), axonRgb(80.0, 86.0, 98.0));
        float scroll = on ? axonClock * 2.0 : 0.0;
        float yy = mod(r.y + 6.0 - scroll, 4.0) - 2.0;
        float thread = max(abs(yy - r.x * 0.3) - 0.5, max(abs(r.x) - 5.0, max(r.y + 6.0, -22.0 - r.y)));
        axonBlend(base, axonRgb(40.0, 44.0, 52.0), axonCover(thread, px));
        if (on) axonSparks(base, p, cursor, 1.0, axonRgb(255.0, 214.0, 140.0), px);
    } else if (tool == 8) {
        // frez: tarcza z czterema ostrzami
        axonBlend(base, vec3(0.0), 0.27 * axonCover(length(q * vec2(1.0, 1.1) - vec2(0.0, 3.0)) - 13.0, px));
        axonBlend(base, axonRgb(60.0, 66.0, 78.0), axonCover(length(q) - 13.0, px));
        float spin = axonClock * AXON_TAU / 40.0 * (on ? 16.0 : 1.0);
        for (int i = 0; i < 4; i++) {
            float a = spin + float(i) * AXON_TAU / 4.0;
            axonBlend(base, axonRgb(210.0, 216.0, 226.0), axonCover(axonSegment(q, vec2(0.0), vec2(cos(a), sin(a)) * 12.0) - 1.7, px));
        }
        axonBlend(base, axonRgb(30.0, 32.0, 38.0), axonCover(length(q) - 3.0, px));
        if (on) axonSparks(base, p, cursor, 0.8, axonRgb(255.0, 214.0, 140.0), px);
    }
}

void axonSprite(inout vec3 base, vec2 p, float px, vec2 cursor, int i) {
    vec4 a = axonSpriteA[i];
    vec4 b = axonSpriteB[i];
    int kind = int(b.x + 0.5);
    if (kind == 0) {
        return;
    }
    float dt = mod(axonClock - b.w, AXON_CLOCK_PERIOD);
    vec2 lim = axonSpriteLim[i];
    vec2 pos = a.xy;
    if (kind != 5) {
        pos += a.zw * dt;
    }
    float heat = 0.0;
    if (lim.y > lim.x) {
        pos.x = clamp(pos.x, lim.x, lim.y);
        heat = (pos.x - lim.x) / (lim.y - lim.x);
    }
    float size = b.z;
    int colorIndex = int(b.y + 0.5);
    vec3 color = axonEffectColor(colorIndex, heat);

    if (kind == 1) {
        // Znacznik skali: pos.y to czubek trójkąta, size to długość trzonka.
        if (abs(p.x - pos.x) > 30.0) return;
        axonGlow(base, p, vec2(pos.x, pos.y + size * 0.5), 26.0, color, 0.35);
        float stem = (1.5 - abs(p.x - pos.x)) / px;
        float stemY = min(p.y - pos.y, pos.y + size - p.y) / px;
        axonBlend(base, color, clamp(stem + 0.5, 0.0, 1.0) * clamp(stemY + 0.5, 0.0, 1.0));
        float u = (p.y - (pos.y - 12.0)) / 12.0;
        float half_ = 8.0 * (1.0 - u);
        float inside = (half_ - abs(p.x - pos.x)) * 0.83 / px;
        float cover = clamp(inside + 0.5, 0.0, 1.0) * clamp(min(u, 1.0 - u) * 12.0 / px + 0.5, 0.0, 1.0);
        axonBlend(base, color, cover);
    } else if (kind == 2) {
        // Rozżarzony pręt od lim.x do lim.y, wysokość 2 * size, kolor zależy od temperatury.
        float cx = (lim.x + lim.y) * 0.5;
        float halfW = (lim.y - lim.x) * 0.5;
        float halfH = size;
        axonGlow(base, p, vec2(cx, pos.y), 150.0, color, min(0.5, heat * 0.6));
        vec2 q = abs(p - vec2(cx, pos.y)) - vec2(halfW - 10.0, halfH - 10.0);
        float dist = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - 10.0;
        float shade = mix(1.3, 0.7, clamp((p.y - (pos.y - halfH)) / (2.0 * halfH), 0.0, 1.0));
        float body = axonCover(dist, px);
        axonBlend(base, clamp(color * shade, 0.0, 1.0), body);
        axonBlend(base, vec3(1.0), 0.2 * axonCover(abs(dist + 0.6) - 0.6, px) * body);
    } else if (kind == 3) {
        // Płomienie pod prętem: 9 języków między lim.x + 30 a lim.y - 30, baza na pos.y.
        if (p.y > pos.y + 2.0 || p.y < pos.y - 44.0) return;
        float first = lim.x + 30.0;
        float step_ = (lim.y - lim.x - 60.0) / 8.0;
        float j = clamp(floor((p.x - first) / step_ + 0.5), 0.0, 8.0);
        float fx = first + j * step_;
        float h = 26.0 + 14.0 * sin(axonClock * AXON_TAU * 4.0 / AXON_CLOCK_PERIOD + j * 1.7);
        float u = (pos.y - p.y) / h;
        float w = 9.0 * (1.0 - u * u);
        float inside = (w - abs(p.x - fx)) / px;
        float cover = clamp(inside + 0.5, 0.0, 1.0) * clamp(u * h / px + 0.5, 0.0, 1.0) * clamp((1.0 - u) * h / px + 0.5, 0.0, 1.0);
        vec3 flame = mix(axonRgb(255.0, 90.0, 20.0), axonRgb(255.0, 230.0, 120.0), clamp(u, 0.0, 1.0));
        axonBlend(base, flame, 0.9 * cover);
    } else if (kind == 4) {
        // Pulsujący cel: poświata i pierścień, które oddychają 1,5 razy na sekundę.
        float d = length(p - pos);
        if (d > size * 2.6 + 4.0) return;
        float pulse = 0.5 + 0.5 * sin(axonClock * AXON_TAU * 3.0 / AXON_CLOCK_PERIOD);
        axonGlow(base, p, pos, size * 2.4, color, 0.3 + 0.2 * pulse);
        axonBlend(base, color, 0.8 * axonCover(abs(d - (size + 3.0 + pulse * 3.0)) - 1.0, px));
    } else if (kind == 5) {
        // Narzędzie przy kursorze: rysowane tam, gdzie celuje gracz, bez opóźnienia serwera.
        axonTool(base, p, px, cursor, int(size + 0.5), lim.x > 0.5, color, a.xy);
    } else if (kind == 6) {
        // Siatka celownika optyki z łukiem przytrzymania (lo = procent).
        vec2 q = p - pos;
        if (length(q) > 40.0) return;
        float ring = abs(length(q) - 18.0) - 0.8;
        float cross_ = min(
            max(abs(q.y) - 0.8, abs(abs(q.x) - 21.0) - 13.0),
            max(abs(q.x) - 0.8, abs(abs(q.y) - 21.0) - 13.0));
        axonBlend(base, color, axonCover(min(ring, cross_), px));
        float frac = lim.x / 100.0;
        float ang = mod(atan(q.x, -q.y), AXON_TAU) / AXON_TAU;
        if (ang <= frac) {
            axonBlend(base, axonEffectColor(1, 0.0), axonCover(abs(length(q) - 24.0) - 1.7, px));
        }
    } else if (kind == 7) {
        // Ruchomy cel optyki: poświata, dwa pierścienie i czerwony środek (size = tolerancja).
        float d = length(p - pos);
        if (d > size * 2.6) return;
        vec3 green = axonEffectColor(1, 0.0);
        axonGlow(base, p, pos, size * 2.5, green, 0.28);
        axonBlend(base, green, 0.9 * axonCover(abs(d - size) - 1.0, px));
        axonBlend(base, green, 0.5 * axonCover(abs(d - size * 0.55) - 0.7, px));
        axonBlend(base, axonEffectColor(2, 0.0), axonCover(d - 4.0, px));
    }
}

// Piksel obrazu mapy bez znacznika i tabeli sprite'ów (zastąpione sąsiednim wierszem).
vec3 axonTexel(ivec2 pixel) {
    pixel = clamp(pixel, ivec2(0), ivec2(127));
    int markerWidth = axonDensity > 1 ? 32 : 24;
    if (pixel.y == 0 && pixel.x < markerWidth) {
        pixel.y = 1;
    } else if (pixel.y == 127) {
        // znacznik (x < 8) i tabela sprite'ów (reszta wiersza) nie są obrazem
        pixel.y = 126;
    }
    return texelFetch(Sampler0, pixel, 0).rgb;
}

// Ostre skalowanie z wygładzonymi krawędziami: wewnątrz piksela obrazu kolor jest stały, a przejście
// do sąsiada trwa jeden piksel ekranu. Przy niecałkowitej skali (np. 1280 px obrazu na 1920 px ekranu)
// piksele nie są nierówne, a przy całkowitej obraz jest tak ostry jak przy texelFetch.
vec3 axonSharp(vec2 uv) {
    vec2 texel = uv * 128.0;
    vec2 perScreen = max(fwidth(texel), vec2(1e-4));
    vec2 scale = max(1.0 / perScreen, vec2(1.0));
    vec2 base = floor(texel);
    vec2 inside = texel - base - 0.5;
    vec2 range = 0.5 - 0.5 / scale;
    vec2 f = (inside - clamp(inside, -range, range)) * scale;
    vec2 p = base + 0.5 + f - 0.5;
    ivec2 i = ivec2(floor(p));
    vec2 w = fract(p);
    vec3 c00 = axonTexel(i);
    vec3 c10 = axonTexel(i + ivec2(1, 0));
    vec3 c01 = axonTexel(i + ivec2(0, 1));
    vec3 c11 = axonTexel(i + ivec2(1, 1));
    return mix(mix(c00, c10, w.x), mix(c01, c11, w.x), w.y);
}

void main() {
    if (axonMap == 1) {
        // Mapa AxonMap: bez światła i mgły. Ostry ekran (gęstość 2) skalujemy gładko, zwykły jak dotąd.
        if (axonDensity > 1) {
            fragColor = vec4(axonSharp(texCoord0), 1.0);
        } else {
            fragColor = vec4(axonTexel(ivec2(texCoord0 * 128.0)), 1.0);
        }

        // Sprity i kursor są w pikselach logicznych ekranu 640x384, niezależnie od gęstości siatki.
        int cols = AXON_COLS * axonDensity;
        float density = float(axonDensity);
        vec2 mapPixel = (vec2(float(axonTile % cols), float(axonTile / cols)) * 128.0 + texCoord0 * 128.0) / density;
        vec2 cursorPixel = axonCursor * vec2(float(AXON_COLS), float(AXON_ROWS)) * 128.0;

        // Sprity: rysowane w pikselach logicznych, z wygładzaniem do rozdzielczości ekranu.
        float spriteAa = max(fwidth(mapPixel.x), 1e-3);
        vec3 spriteBase = fragColor.rgb;
        for (int i = 0; i < AXON_SPRITES; i++) {
            axonSprite(spriteBase, mapPixel, spriteAa, cursorPixel, i);
        }
        fragColor = vec4(spriteBase, 1.0);

        // Kursor: krzyżyk z obwódką.
        vec2 d = abs(floor(mapPixel) - floor(cursorPixel));
        if ((d.x <= 5.0 && d.y <= 0.0) || (d.y <= 5.0 && d.x <= 0.0)) {
            fragColor = vec4(1.0);
        } else if ((d.x <= 6.0 && d.y <= 1.0) || (d.y <= 6.0 && d.x <= 1.0)) {
            fragColor = vec4(0.0, 0.0, 0.0, 1.0);
        }
        return;
    }

    vec4 color = texture(Sampler0, texCoord0) * vertexColor * ColorModulator;
    if (color.a < 0.1) {
        discard;
    }
    fragColor = linear_fog(color, vertexDistance, FogStart, FogEnd, FogColor);
}
