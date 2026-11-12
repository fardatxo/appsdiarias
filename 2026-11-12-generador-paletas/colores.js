// Lógica pura de color (sin DOM): se puede usar en el navegador y probar con Node.

// Convierte HSL (h: 0-360, s y l: 0-100) a RGB (0-255 por canal).
function hslARgb(h, s, l) {
  s /= 100;
  l /= 100;
  const k = (n) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return [f(0), f(8), f(4)].map((v) => Math.round(v * 255));
}

// Convierte [r, g, b] a un texto hexadecimal tipo "#1A2B3C".
function rgbAHex([r, g, b]) {
  return "#" + [r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("").toUpperCase();
}

// Convierte "#1A2B3C" (o "#abc") a [r, g, b]. Devuelve null si no es válido.
function hexARgb(hex) {
  let limpio = hex.trim().replace(/^#/, "");
  if (/^[0-9a-f]{3}$/i.test(limpio)) {
    limpio = limpio.split("").map((c) => c + c).join("");
  }
  if (!/^[0-9a-f]{6}$/i.test(limpio)) return null;
  return [0, 2, 4].map((i) => parseInt(limpio.slice(i, i + 2), 16));
}

// Luminancia relativa según WCAG 2.1 (0 = negro, 1 = blanco).
function luminancia([r, g, b]) {
  const canal = (v) => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b);
}

// Ratio de contraste WCAG entre dos colores RGB (de 1 a 21).
function contraste(rgb1, rgb2) {
  const l1 = luminancia(rgb1);
  const l2 = luminancia(rgb2);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}

// Elige texto negro o blanco, el que más contraste tenga sobre el fondo dado.
function textoLegible(rgb) {
  const negro = contraste(rgb, [0, 0, 0]);
  const blanco = contraste(rgb, [255, 255, 255]);
  return negro >= blanco ? "#000000" : "#FFFFFF";
}

// Cada armonía es una lista de desplazamientos (en grados) sobre la rueda de color.
const ARMONIAS = {
  analoga: [-60, -30, 0, 30, 60],
  complementaria: [0, 20, 180, 200, 160],
  triada: [0, 120, 240, 60, 180],
  tetrada: [0, 90, 180, 270, 45],
  monocromatica: [0, 0, 0, 0, 0],
};

// Genera una paleta de 5 colores a partir de un tono base y un tipo de armonía.
// `azar` es una función que devuelve números entre 0 y 1 (inyectable para tests).
function generarPaleta(tonoBase, armonia, azar = Math.random) {
  const desplazamientos = ARMONIAS[armonia] || ARMONIAS.analoga;
  return desplazamientos.map((d, i) => {
    const h = (((tonoBase + d) % 360) + 360) % 360;
    const s = 45 + Math.round(azar() * 40); // saturación entre 45 y 85
    // En monocromática repartimos la luminosidad; en el resto la variamos un poco.
    const l = armonia === "monocromatica" ? 20 + i * 15 : 35 + Math.round(azar() * 35);
    const rgb = hslARgb(h, s, l);
    return { hex: rgbAHex(rgb), rgb, hsl: [h, s, l] };
  });
}

const Colores = { hslARgb, rgbAHex, hexARgb, luminancia, contraste, textoLegible, generarPaleta, ARMONIAS };

// Exporta para Node (tests) sin romper el uso con <script> en el navegador.
if (typeof module !== "undefined" && module.exports) module.exports = Colores;
