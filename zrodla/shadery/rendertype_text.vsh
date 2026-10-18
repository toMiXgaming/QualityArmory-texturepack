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

// AxonMap: ekran mapy na cały ekran. Musi się zgadzać z pluginem (OverlayLayout).
#define AXON_COLS 4
#define AXON_ROWS 3
#define AXON_HEIGHT 0.9

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

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);

    vertexDistance = fog_distance(Position, FogShape);
    vertexColor = Color * texelFetch(Sampler2, UV2 / 16, 0);
    texCoord0 = UV0;
    axonMap = 0;

    int tile = axonTileIndex();
    if (tile >= 0) {
        axonMap = 1;
        // ProjMat[1][1] / ProjMat[0][0] = szerokość / wysokość ekranu.
        float screenAspect = ProjMat[1][1] / ProjMat[0][0];
        float h = 2.0 * AXON_HEIGHT;
        float w = h * float(AXON_COLS) / float(AXON_ROWS) / screenAspect;
        if (w > 1.9) {
            h *= 1.9 / w;
            w = 1.9;
        }
        vec2 tileSize = vec2(w / float(AXON_COLS), h / float(AXON_ROWS));
        int tx = tile % AXON_COLS;
        int ty = tile / AXON_COLS;
        vec2 topLeft = vec2(-w / 2.0 + float(tx) * tileSize.x, h / 2.0 - float(ty) * tileSize.y);
        gl_Position = vec4(topLeft + vec2(UV0.x * tileSize.x, -UV0.y * tileSize.y), -0.99, 1.0);
        vertexDistance = 0.0;
    }
}
