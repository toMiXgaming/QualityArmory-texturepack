#version 330

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>
#moj_import <minecraft:globals.glsl>

#define AXON_SPRITES 5
#define AXON_SPRITE_NIBBLES 21
#define AXON_CLOCK_PERIOD 40.0
const vec3 AXON_NIB[16] = vec3[16](
    vec3(13.0, 13.0, 13.0) / 255.0,
    vec3(255.0, 255.0, 255.0) / 255.0,
    vec3(64.0, 64.0, 255.0) / 255.0,
    vec3(255.0, 0.0, 0.0) / 255.0,
    vec3(127.0, 204.0, 25.0) / 255.0,
    vec3(208.0, 109.0, 142.0) / 255.0,
    vec3(92.0, 219.0, 213.0) / 255.0,
    vec3(48.0, 115.0, 112.0) / 255.0,
    vec3(250.0, 238.0, 77.0) / 255.0,
    vec3(132.0, 44.0, 44.0) / 255.0,
    vec3(0.0, 217.0, 58.0) / 255.0,
    vec3(0.0, 124.0, 0.0) / 255.0,
    vec3(125.0, 53.0, 152.0) / 255.0,
    vec3(160.0, 160.0, 255.0) / 255.0,
    vec3(216.0, 127.0, 51.0) / 255.0,
    vec3(33.0, 33.0, 135.0) / 255.0);

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV2;

uniform sampler2D Sampler0;
uniform sampler2D Sampler2;

out float sphericalVertexDistance;
out float cylindricalVertexDistance;
out vec4 vertexColor;
out vec2 texCoord0;
flat out int axonMap;
flat out int axonTile;
flat out vec2 axonCursor;
flat out vec4 axonSpriteA[AXON_SPRITES];
flat out vec4 axonSpriteB[AXON_SPRITES];
flat out vec2 axonSpriteLim[AXON_SPRITES];
flat out float axonClock;

// AxonMap: ekran mapy na cały ekran. Musi się zgadzać z pluginem (OverlayLayout).
#define AXON_COLS 5
#define AXON_ROWS 3
// Kursor: o ile stopni trzeba obrócić głowę, żeby przejechać całą szerokość / wysokość mapy.
// Plugin ustawia graczowi yaw 0 i pitch 0 przy otwarciu mapy (OverlayLayout.CURSOR_*).
#define AXON_YAW_RANGE 180.0
#define AXON_PITCH_RANGE 100.0

// Sprity: ruchome elementy mini gier rysuje shader (60+ fps), a serwer wysyła tylko tabelę parametrów.
// Tabela leży w ostatnim wierszu kafla (piksel y=127, od x=8): każdy piksel to jeden z 16 kolorów
// (półbajt), rozpoznawany jako najbliższy z AXON_NIB. Pierwsze 4 półbajty to nagłówek; bez niego
// (np. zwykła mapa AxonMap) tabela jest ignorowana.

// Znacznik: w pierwszym wierszu mapy piksele 0-7 to na przemian biały (A) i czarny (B),
// w pikselach 8-23 liczba białych pikseli to numer kafelka, a w ostatnim wierszu
// piksele 0-7 to znowu na przemian A i B. Zwykłe mapy prawie nigdy tak nie wyglądają.
int axonTileIndex() {
    if (textureSize(Sampler0, 0) != ivec2(128, 128)) {
        return -1;
    }
    vec3 a = texelFetch(Sampler0, ivec2(0, 0), 0).rgb;
    vec3 b = texelFetch(Sampler0, ivec2(1, 0), 0).rgb;
    if (min(a.r, min(a.g, a.b)) < 0.95 || max(b.r, max(b.g, b.b)) > 0.15) {
        return -1;
    }
    for (int x = 0; x < 8; x++) {
        vec3 expected = (x % 2 == 0) ? a : b;
        if (texelFetch(Sampler0, ivec2(x, 0), 0).rgb != expected
                || texelFetch(Sampler0, ivec2(x, 127), 0).rgb != expected) {
            return -1;
        }
    }
    int index = 0;
    for (int x = 8; x < 24; x++) {
        vec3 c = texelFetch(Sampler0, ivec2(x, 0), 0).rgb;
        if (c == a) {
            index++;
        } else if (c != b) {
            return -1;
        }
    }
    return index < AXON_COLS * AXON_ROWS ? index : -1;
}

int axonNibble(int i) {
    vec3 c = texelFetch(Sampler0, ivec2(8 + i, 127), 0).rgb;
    int best = 0;
    float bestDistance = 1e9;
    for (int k = 0; k < 16; k++) {
        vec3 d = c - AXON_NIB[k];
        float dd = dot(d, d);
        if (dd < bestDistance) {
            bestDistance = dd;
            best = k;
        }
    }
    return best;
}

int axonNibbles(int first, int count) {
    int v = 0;
    for (int i = 0; i < count; i++) {
        v = v * 16 + axonNibble(first + i);
    }
    return v;
}

int axonSigned8(int v) {
    return v >= 128 ? v - 256 : v;
}

void axonReadSprites() {
    for (int i = 0; i < AXON_SPRITES; i++) {
        axonSpriteA[i] = vec4(0.0);
        axonSpriteB[i] = vec4(0.0);
        axonSpriteLim[i] = vec2(0.0);
    }
    if (axonNibble(0) != 10 || axonNibble(1) != 5 || axonNibble(2) != 12 || axonNibble(3) != 3) {
        return;
    }
    for (int i = 0; i < AXON_SPRITES; i++) {
        int base = 4 + i * AXON_SPRITE_NIBBLES;
        int kind = axonNibble(base + 9);
        if (kind == 0) {
            continue;
        }
        // Pozycja to x + 1024 * y (po 10 bitów).
        int xy = axonNibbles(base, 5);
        float y = float(xy / 1024);
        float x = float(xy - (xy / 1024) * 1024);
        float vx = float(axonSigned8(axonNibbles(base + 5, 2))) * 0.25;
        float vy = float(axonSigned8(axonNibbles(base + 7, 2))) * 0.25;
        float color = float(axonNibble(base + 10));
        float size = float(axonNibbles(base + 11, 2));
        float stamp = float(axonNibbles(base + 13, 2));
        axonSpriteA[i] = vec4(x, y, vx, vy);
        axonSpriteB[i] = vec4(float(kind), color, size, stamp);
        axonSpriteLim[i] = vec2(float(axonNibbles(base + 15, 3)), float(axonNibbles(base + 18, 3)));
    }
}

// AxonMap: przy otwartej mapie plugin ustawia graczowi czas gry, którego reszta z 24000 jest
// w [AXON_HUD_TIME, AXON_HUD_TIME + AXON_HUD_WINDOW) (OverlayLayout.HUD_TIME). Wtedy GUI chowa
// hotbar, serduszka, pasek doświadczenia i celownik.
#define AXON_HUD_TIME 12000.0
#define AXON_HUD_WINDOW 60.0

bool axonMapOpen(float gameTime) {
    float t = gameTime * 24000.0;
    return t >= AXON_HUD_TIME && t < AXON_HUD_TIME + AXON_HUD_WINDOW;
}

// Pozycja w pikselach GUI (0,0 w lewym górnym rogu) i rozmiar GUI, z rzutu ortogonalnego.
vec2 axonGuiSize(mat4 proj) {
    return vec2(2.0 / proj[0][0], -2.0 / proj[1][1]);
}

vec2 axonGuiPos(vec4 clip, mat4 proj) {
    return vec2(clip.x + 1.0, 1.0 - clip.y) * 0.5 * axonGuiSize(proj);
}

// Hotbar ze wszystkim nad nim (serduszka, głód, pancerz, doświadczenie) i celownik na środku.
bool axonInHud(vec2 pos, vec2 size, float hudHeight) {
    vec2 center = size * 0.5;
    bool hotbar = abs(pos.x - center.x) <= 92.0 && pos.y >= size.y - hudHeight;
    bool crosshair = abs(pos.x - center.x) <= 8.0 && abs(pos.y - center.y) <= 8.0;
    return hotbar || crosshair;
}

// Poziom doświadczenia nad hotbarem: zielony napis z czarną obwódką.
bool axonIsXpText() {
    vec3 c = floor(Color.rgb * 255.0 + 0.5);
    return c == vec3(128.0, 255.0, 32.0) || c == vec3(0.0);
}

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);

    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);
    vertexColor = Color * texelFetch(Sampler2, UV2 / 16, 0);
    texCoord0 = UV0;
    axonMap = 0;
    axonTile = 0;
    axonCursor = vec2(-1.0);
    axonClock = mod(GameTime * 24000.0 - 12000.0, AXON_CLOCK_PERIOD);
    for (int s = 0; s < AXON_SPRITES; s++) {
        axonSpriteA[s] = vec4(0.0);
        axonSpriteB[s] = vec4(0.0);
        axonSpriteLim[s] = vec2(0.0);
    }

    if (ProjMat[2][3] == 0.0 && axonMapOpen(GameTime) && axonIsXpText()
            && axonInHud(axonGuiPos(gl_Position, ProjMat), axonGuiSize(ProjMat), 40.0)) {
        gl_Position = vec4(-10.0, -10.0, -10.0, 1.0);
        return;
    }

    int tile = axonTileIndex();
    if (tile >= 0) {
        axonMap = 1;
        axonTile = tile;
        axonReadSprites();
        // Kierunek kamery z ModelViewMat (świat -> widok): przód = -trzeci wiersz macierzy.
        vec3 forward = -vec3(ModelViewMat[0][2], ModelViewMat[1][2], ModelViewMat[2][2]);
        float yaw = degrees(atan(-forward.x, forward.z));
        float pitch = degrees(asin(clamp(-forward.y, -1.0, 1.0)));
        axonCursor = clamp(vec2(0.5 + yaw / AXON_YAW_RANGE, 0.5 + pitch / AXON_PITCH_RANGE), 0.0, 1.0);
        // Mapa wypełnia cały ekran (przy 16:9 jest lekko rozciągnięta w poziomie).
        vec2 tileSize = vec2(2.0 / float(AXON_COLS), 2.0 / float(AXON_ROWS));
        int tx = tile % AXON_COLS;
        int ty = tile / AXON_COLS;
        vec2 topLeft = vec2(-1.0 + float(tx) * tileSize.x, 1.0 - float(ty) * tileSize.y);
        gl_Position = vec4(topLeft + vec2(UV0.x * tileSize.x, -UV0.y * tileSize.y), -0.99, 1.0);
        sphericalVertexDistance = 0.0;
        cylindricalVertexDistance = 0.0;
    }
}
