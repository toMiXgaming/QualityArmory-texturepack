#version 150

#moj_import <minecraft:fog.glsl>

uniform sampler2D Sampler0;

uniform vec4 ColorModulator;
uniform float FogStart;
uniform float FogEnd;
uniform vec4 FogColor;

in float vertexDistance;
in vec4 vertexColor;
in vec2 texCoord0;
flat in int axonMap;

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
        return;
    }

    vec4 color = texture(Sampler0, texCoord0) * vertexColor * ColorModulator;
    if (color.a < 0.1) {
        discard;
    }
    fragColor = linear_fog(color, vertexDistance, FogStart, FogEnd, FogColor);
}
