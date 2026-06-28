varying vec3 vColor;
varying vec2 vUv;
varying vec2 vScale;

uniform float uOpacity;
uniform float uDashEnabled;
uniform float uDashSeverity;
uniform float uTime;

void main() {
    // BreachPath displays graph relationships as clean undirected lines.
    // Direction and risk still live in edge metadata for analysis.
    float ny = vUv.y * 2.0 - 1.0;

    float severity = clamp(uDashSeverity, 0.0, 4.0);
    float dashEnabled = step(0.5, uDashEnabled);
    float relLineThickness = mix(0.12, 0.13 + severity * 0.025, dashEnabled);
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

    float dashRepeats = max(vScale.x * 3.5, 4.0);
    float dashSpeed = mix(0.9, 1.8, severity / 4.0);
    float dashPosition = fract(vUv.x * dashRepeats - uTime * dashSpeed);
    float dashLength = mix(0.45, 0.68, severity / 4.0);
    float dashFeather = 0.04;
    float dashMask = 1.0 - smoothstep(dashLength, dashLength + dashFeather, dashPosition);

    float glowThickness = relLineThickness + 0.14 + severity * 0.03;
    float glow = 1.0 - smoothstep(
        glowThickness - yFeather,
        glowThickness + yFeather,
        abs(ny)
    );
    float pulse = 0.75 + 0.25 * sin(uTime * mix(4.0, 7.0, severity / 4.0));
    float animatedAlpha = (lineAlongY + glow * 0.35) * dashMask * pulse;

    float alpha = lineAlongX * mix(lineAlongY, animatedAlpha, dashEnabled);
    if (alpha <= 0.001) discard;
    gl_FragColor = vec4(vColor, alpha * uOpacity);
}
