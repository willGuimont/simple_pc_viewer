#version 330 core
precision mediump float;

in vec3 vertPos;
in float intensity;

out vec4 FragColor;

void main()
{
    vec2 circCoord = 2.0 * gl_PointCoord - 1.0;
    if (dot(circCoord, circCoord) > 1.0) {
        discard;
    }
    FragColor = vec4(intensity * vec3(1, 1, 1), 1);
}
