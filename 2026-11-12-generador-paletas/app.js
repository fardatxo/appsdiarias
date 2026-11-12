// Interfaz: conecta la lógica de colores.js con el DOM.
// colores.js se carga antes con <script>, así que sus funciones (generarPaleta,
// contraste, textoLegible) y ARMONIAS ya son globales y se usan directamente.

const $paleta = document.getElementById("paleta");
const $armonia = document.getElementById("armonia");
const $generar = document.getElementById("generar");
const $aviso = document.getElementById("aviso");
const $tabla = document.getElementById("contrastes");

let paletaActual = [];
// Los colores "fijados" (candado) se conservan al generar una paleta nueva.
let fijados = [false, false, false, false, false];

// Rellena el desplegable con las armonías disponibles.
Object.keys(ARMONIAS).forEach((nombre) => {
  const opcion = document.createElement("option");
  opcion.value = nombre;
  opcion.textContent = nombre.charAt(0).toUpperCase() + nombre.slice(1);
  $armonia.appendChild(opcion);
});

function nuevaPaleta() {
  const tono = Math.floor(Math.random() * 360);
  const nueva = generarPaleta(tono, $armonia.value);
  paletaActual = nueva.map((color, i) => (fijados[i] && paletaActual[i] ? paletaActual[i] : color));
  pintar();
}

function mostrarAviso(texto) {
  $aviso.textContent = texto;
  clearTimeout(mostrarAviso.temporizador);
  mostrarAviso.temporizador = setTimeout(() => ($aviso.textContent = ""), 1800);
}

async function copiar(hex) {
  try {
    await navigator.clipboard.writeText(hex);
    mostrarAviso(`Copiado ${hex}`);
  } catch {
    mostrarAviso(`No se pudo copiar; el código es ${hex}`);
  }
}

function pintar() {
  $paleta.innerHTML = "";
  paletaActual.forEach((color, i) => {
    const tarjeta = document.createElement("div");
    tarjeta.className = "color";
    tarjeta.style.background = color.hex;
    tarjeta.style.color = textoLegible(color.rgb);

    const codigo = document.createElement("button");
    codigo.className = "codigo";
    codigo.textContent = color.hex;
    codigo.title = "Copiar al portapapeles";
    codigo.addEventListener("click", () => copiar(color.hex));

    const candado = document.createElement("button");
    candado.className = "candado";
    candado.textContent = fijados[i] ? "Fijado" : "Fijar";
    candado.setAttribute("aria-pressed", String(fijados[i]));
    candado.addEventListener("click", () => {
      fijados[i] = !fijados[i];
      pintar();
    });

    tarjeta.append(codigo, candado);
    $paleta.appendChild(tarjeta);
  });
  pintarContrastes();
}

// Tabla con el contraste de cada color frente a blanco y negro (nivel AA: 4.5).
function pintarContrastes() {
  $tabla.innerHTML = "";
  paletaActual.forEach((color) => {
    const fila = document.createElement("tr");
    const blanco = contraste(color.rgb, [255, 255, 255]);
    const negro = contraste(color.rgb, [0, 0, 0]);
    const celda = (ratio) => `<td>${ratio.toFixed(2)} ${ratio >= 4.5 ? "✔ AA" : "✘"}</td>`;
    fila.innerHTML = `<td><span class="muestra" style="background:${color.hex}"></span>${color.hex}</td>${celda(blanco)}${celda(negro)}`;
    $tabla.appendChild(fila);
  });
}

$generar.addEventListener("click", nuevaPaleta);
$armonia.addEventListener("change", nuevaPaleta);
// La barra espaciadora también genera una paleta (si no se está sobre un control).
document.addEventListener("keydown", (e) => {
  if (e.code === "Space" && !["BUTTON", "SELECT"].includes(e.target.tagName)) {
    e.preventDefault();
    nuevaPaleta();
  }
});

nuevaPaleta();
