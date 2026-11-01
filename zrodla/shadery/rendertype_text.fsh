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
flat in vec2 axonCursor;
flat in vec4 axonSpriteA[AXON_SPRITES];
flat in vec4 axonSpriteB[AXON_SPRITES];
flat in vec2 axonSpriteLim[AXON_SPRITES];
flat in float axonClock;

out vec4 fragColor;


// ---------------------------------------------------------------- sprity
// Rodzaje: 1 znacznik skali (trójkąt, trzonek i poświata), 2 rozżarzony pręt, 3 płomienie.
// Pozycja = (x, y) w chwili "stamp" + prędkość * czas, który minął na zegarze klienta (tick + część ticka).

const float AXON_TAU = 6.2831853;

vec3 axonEffectColor(int index, float heat) {
    if (index == 15) {
        vec3 cold = vec3(96.0, 104.0, 116.0) / 255.0;
        vec3 red = vec3(200.0, 60.0, 30.0) / 255.0;
        vec3 hot = vec3(255.0, 240.0, 190.0) / 255.0;
        return heat < 0.5 ? mix(cold, red, heat * 2.0) : mix(red, hot, (heat - 0.5) * 2.0);
    }
    if (index == 1) return vec3(70.0, 230.0, 140.0) / 255.0;
    if (index == 2) return vec3(255.0, 100.0, 80.0) / 255.0;
    if (index == 3) return vec3(255.0, 200.0, 60.0) / 255.0;
    if (index == 4) return vec3(90.0, 200.0, 255.0) / 255.0;
    if (index == 5) return vec3(255.0, 140.0, 40.0) / 255.0;
    if (index == 6) return vec3(150.0, 160.0, 177.0) / 255.0;
    return vec3(1.0);
}

void axonBlend(inout vec3 base, vec3 color, float alpha) {
    base = mix(base, color, clamp(alpha, 0.0, 1.0));
}

void axonSprite(inout vec3 base, vec2 p, float px, int i) {
    vec4 a = axonSpriteA[i];
    vec4 b = axonSpriteB[i];
    int kind = int(b.x + 0.5);
    if (kind == 0) {
        return;
    }
    float dt = mod(axonClock - b.w, AXON_CLOCK_PERIOD);
    vec2 pos = a.xy + a.zw * dt;
    vec2 lim = axonSpriteLim[i];
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
        float glowDistance = length(p - vec2(pos.x, pos.y + size * 0.5));
        axonBlend(base, color, 0.35 * clamp(1.0 - glowDistance / 26.0, 0.0, 1.0));
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
        float glowDistance = length(p - vec2(cx, pos.y));
        axonBlend(base, color, min(0.5, heat * 0.6) * clamp(1.0 - glowDistance / 150.0, 0.0, 1.0));
        vec2 q = abs(p - vec2(cx, pos.y)) - vec2(halfW - 10.0, halfH - 10.0);
        float dist = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - 10.0;
        float shade = mix(1.3, 0.7, clamp((p.y - (pos.y - halfH)) / (2.0 * halfH), 0.0, 1.0));
        vec3 rod = clamp(color * shade, 0.0, 1.0);
        float body = clamp(0.5 - dist / px, 0.0, 1.0);
        axonBlend(base, rod, body);
        float edge = clamp(1.0 - abs(dist + 0.6) / (1.2 * px), 0.0, 1.0) * body;
        axonBlend(base, vec3(1.0), 0.2 * edge);
    } else if (kind == 3) {
        // Płomienie pod prętem: 9 języków między lim.x + 30 a lim.y - 30, baza na pos.y.
        float first = lim.x + 30.0;
        float step_ = (lim.y - lim.x - 60.0) / 8.0;
        float j = clamp(floor((p.x - first) / step_ + 0.5), 0.0, 8.0);
        float fx = first + j * step_;
        float h = 26.0 + 14.0 * sin(axonClock * AXON_TAU * 4.0 / AXON_CLOCK_PERIOD + j * 1.7);
        float u = (pos.y - p.y) / h;
        float w = 9.0 * (1.0 - u * u);
        float inside = (w - abs(p.x - fx)) / px;
        float cover = clamp(inside + 0.5, 0.0, 1.0) * clamp(u * h / px + 0.5, 0.0, 1.0) * clamp((1.0 - u) * h / px + 0.5, 0.0, 1.0);
        vec3 flame = mix(vec3(255.0, 90.0, 20.0), vec3(255.0, 230.0, 120.0), clamp(u, 0.0, 1.0)) / 255.0;
        axonBlend(base, flame, 0.9 * cover);
    }
}

void main() {
    if (axonMap == 1) {
        // Mapa AxonMap: bez światła i mgły; piksele znacznika zastępujemy sąsiednim wierszem.
        ivec2 pixel = clamp(ivec2(texCoord0 * 128.0), ivec2(0), ivec2(127));
        if (pixel.y == 0 && pixel.x < 24) {
            pixel.y = 1;
        } else if (pixel.y == 127) {
            // znacznik (x < 8) i tabela sprite'ów (reszta wiersza) nie są obrazem
            pixel.y = 126;
        }
        fragColor = vec4(texelFetch(Sampler0, pixel, 0).rgb, 1.0);

        // Sprity: rysowane w pikselach całej mapy, z wygładzaniem do rozdzielczości ekranu.
        vec2 spritePixel = vec2(float(axonTile % AXON_COLS), float(axonTile / AXON_COLS)) * 128.0 + texCoord0 * 128.0;
        float spriteAa = max(fwidth(spritePixel.x), 1e-3);
        vec3 spriteBase = fragColor.rgb;
        for (int i = 0; i < AXON_SPRITES; i++) {
            axonSprite(spriteBase, spritePixel, spriteAa, i);
        }
        fragColor = vec4(spriteBase, 1.0);

        // Kursor: krzyżyk z obwódką, w pikselach całej mapy.
        vec2 mapPixel = vec2(float(axonTile % AXON_COLS), float(axonTile / AXON_COLS)) * 128.0 + texCoord0 * 128.0;
        vec2 cursorPixel = axonCursor * vec2(float(AXON_COLS), float(AXON_ROWS)) * 128.0;
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
