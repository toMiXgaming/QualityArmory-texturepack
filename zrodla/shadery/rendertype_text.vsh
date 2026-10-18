#version 150

#moj_import <minecraft:fog.glsl>

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV2;

uniform sampler2D Sampler0;
uniform sampler2D Sampler2;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;
uniform int FogShape;

out float vertexDistance;
out vec4 vertexColor;
out vec2 texCoord0;
flat out int axonMap;
flat out int axonTile;
flat out vec2 axonCursor;
flat out int axonPanel;

// AxonMap: ekran mapy na cały ekran. Musi się zgadzać z pluginem (OverlayLayout).
#define AXON_COLS 5
#define AXON_ROWS 3
// Kursor: o ile stopni trzeba obrócić głowę, żeby przejechać całą szerokość / wysokość mapy.
// Plugin ustawia graczowi yaw 0 i pitch 0 przy otwarciu mapy (OverlayLayout.CURSOR_*).
#define AXON_YAW_RANGE 180.0
#define AXON_PITCH_RANGE 100.0
// Panel zasłaniający hotbar i serduszka: tytuł ze znakiem z czcionki axonmap:panel w tym kolorze
// (OverlayLayout.PANEL_COLOR). Cień tekstu ma ten kolor razy 0.25. Rozmiar w pikselach GUI.
#define AXON_PANEL_COLOR vec3(164.0, 92.0, 24.0)
#define AXON_PANEL_WIDTH 190.0
#define AXON_PANEL_HEIGHT 54.0

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

bool axonIsPanel() {
    // GUI ma rzut ortogonalny (ProjMat[2][3] == 0), świat perspektywiczny (-1).
    if (ProjMat[2][3] != 0.0) {
        return false;
    }
    vec3 c = floor(Color.rgb * 255.0 + 0.5);
    return c == AXON_PANEL_COLOR || c == floor(AXON_PANEL_COLOR * 0.25);
}

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);

    vertexDistance = fog_distance(Position, FogShape);
    vertexColor = Color * texelFetch(Sampler2, UV2 / 16, 0);
    texCoord0 = UV0;
    axonMap = 0;
    axonTile = 0;
    axonCursor = vec2(-1.0);
    axonPanel = 0;

    if (axonIsPanel()) {
        // Wierzchołki znaku: 0 lewy górny, 1 lewy dolny, 2 prawy dolny, 3 prawy górny.
        int corner = gl_VertexID % 4;
        vec2 local = vec2(corner >= 2 ? 1.0 : 0.0, (corner == 1 || corner == 2) ? 1.0 : 0.0);
        float guiWidth = 2.0 / ProjMat[0][0];
        float guiHeight = -2.0 / ProjMat[1][1];
        float halfWidth = AXON_PANEL_WIDTH / guiWidth;
        float top = -1.0 + 2.0 * AXON_PANEL_HEIGHT / guiHeight;
        gl_Position = vec4(mix(-halfWidth, halfWidth, local.x), mix(top, -1.0, local.y), gl_Position.z, 1.0);
        texCoord0 = local;
        axonPanel = 1;
        return;
    }

    int tile = axonTileIndex();
    if (tile >= 0) {
        axonMap = 1;
        axonTile = tile;
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
        vertexDistance = 0.0;
    }
}
