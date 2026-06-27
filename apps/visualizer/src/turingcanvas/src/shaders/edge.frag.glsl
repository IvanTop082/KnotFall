varying vec3 vColor;
varying vec2 vUv;
varying vec2 vScale;

uniform float uOpacity;

void main() {
    // BreachPath displays graph relationships as clean undirected lines.
    // Direction and risk still live in edge metadata for analysis.
    float ny = vUv.y * 2.0 - 1.0;

    const float relLineThickness = 0.12;
    const float relPadding = 0.04;

    float padding = relPadding / vScale.x;
    float xFeather = min(0.5 / max(vScale.x, 0.001), 0.04);
    float yFeather = 0.12;

    float lineAlongX = smoothstep(padding - xFeather, padding + xFeather, vUv.x)
        * smoothstep(1.0 - padding + xFeather, 1.0 - padding - xFeather, vUv.x);
    float lineAlongY = 1.0 - smoothstep(
        relLineThickness - yFeather,
        relLineThickness + yFeather,
        abs(ny)
    );

    float alpha = lineAlongX * lineAlongY;
    if (alpha <= 0.001) discard;
    gl_FragColor = vec4(vColor, alpha * uOpacity);
}
