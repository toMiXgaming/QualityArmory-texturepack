#version 330

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>

// Musi się zgadzać z rendertype_text.vsh.
#define AXON_COLS 5
#define AXON_ROWS 3

uniform sampler2D Sampler0;

in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in vec4 vertexColor;
in vec2 texCoord0;
flat in int axonMap;
flat in int axonTile;
flat in vec2 axonCursor;

out vec4 fragColor;

void main() {
    if (axonMap == 1) {
        // Mapa AxonMap: bez światła i mgły; piksele znacznika zastępujemy sąsiednim wierszem.
        ivec2 pixel = clamp(ivec2(texCoord0 * 128.0), ivec2(0), ivec2(127));
        if (pixel.y == 0 && pixel.x < 24) {
            pixel.y = 1;
        } else if (pixel.y == 127 && pixel.x < 8) {
            pixel.y = 126;
        }
        fragColor = vec4(texelFetch(Sampler0, pixel, 0).rgb, 1.0);

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
    fragColor = apply_fog(color, sphericalVertexDistance, cylindricalVertexDistance, FogEnvironmentalStart, FogEnvironmentalEnd, FogRenderDistanceStart, FogRenderDistanceEnd, FogColor);
}
