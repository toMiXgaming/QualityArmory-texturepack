#version 150

in vec3 Position;
in vec2 UV0;
in vec4 Color;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;
uniform float GameTime;

out vec2 texCoord0;
out vec4 vertexColor;
out vec2 axonGui;
flat out int axonHide;

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

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);

    texCoord0 = UV0;
    vertexColor = Color;
    axonGui = vec2(0.0);
    axonHide = 0;
    // GUI ma rzut ortogonalny (ProjMat[2][3] == 0).
    if (ProjMat[2][3] == 0.0 && axonMapOpen(GameTime)) {
        axonGui = axonGuiPos(gl_Position, ProjMat);
        axonHide = 1;
    }
}
