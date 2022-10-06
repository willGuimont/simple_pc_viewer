#version 330 core

layout (location = 0) in vec4 lidarHit;

out vec3 vertPos;
out float intensity;

uniform mat4 projMat;
uniform mat4 viewMat;
uniform mat4 modelMat;
uniform float pointSize;

void main()
{
    vec3 pos = lidarHit.xyz;

    gl_Position = projMat * viewMat * modelMat * vec4(pos, 1.0);
    gl_PointSize = pointSize;

    vec4 vertPos4 = viewMat * vec4(pos, 1.0);
    vertPos = vec3(vertPos4) / vertPos4.w;
    intensity = lidarHit.w;
}
