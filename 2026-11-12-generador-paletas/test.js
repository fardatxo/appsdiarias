// Pruebas rápidas de la lógica: `node test.js`
const assert = require("assert");
const C = require("./colores.js");

assert.deepStrictEqual(C.hslARgb(0, 100, 50), [255, 0, 0]);
assert.deepStrictEqual(C.hslARgb(120, 100, 50), [0, 255, 0]);
assert.deepStrictEqual(C.hslARgb(0, 0, 100), [255, 255, 255]);
assert.strictEqual(C.rgbAHex([26, 43, 60]), "#1A2B3C");
assert.deepStrictEqual(C.hexARgb("#abc"), [170, 187, 204]);
assert.strictEqual(C.hexARgb("zzz"), null);
assert.strictEqual(Math.round(C.contraste([0, 0, 0], [255, 255, 255])), 21);
assert.strictEqual(C.contraste([10, 20, 30], [10, 20, 30]), 1);
assert.strictEqual(C.textoLegible([255, 255, 0]), "#000000");
assert.strictEqual(C.textoLegible([0, 0, 128]), "#FFFFFF");

for (const armonia of Object.keys(C.ARMONIAS)) {
  const paleta = C.generarPaleta(200, armonia);
  assert.strictEqual(paleta.length, 5);
  paleta.forEach((c) => assert.match(c.hex, /^#[0-9A-F]{6}$/));
}
// Con un "azar" fijo el resultado es determinista.
assert.deepStrictEqual(C.generarPaleta(0, "triada", () => 0.5), C.generarPaleta(0, "triada", () => 0.5));

console.log("Todas las pruebas pasan ✔");
