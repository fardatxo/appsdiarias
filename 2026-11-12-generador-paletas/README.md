# Generador de paletas

Genera paletas de 5 colores a partir de armonías de la rueda de color (análoga, complementaria, tríada, tétrada y monocromática). Permite fijar colores para conservarlos entre generaciones, copiar el código hexadecimal con un clic y ver el contraste WCAG de cada color sobre blanco y sobre negro.

## Tecnologías

HTML, CSS y JavaScript puro, sin dependencias ni paso de build.

## Cómo ejecutarla

Abre `index.html` en el navegador (doble clic). Pulsa **Espacio** o el botón **Generar**.

Para lanzar las pruebas de la lógica (requiere Node.js):

```bash
node test.js
```

## Archivos

- `colores.js`: lógica pura (conversiones HSL/RGB/HEX, luminancia, contraste, generación de la paleta).
- `app.js`: interfaz (eventos y pintado en el DOM).
- `index.html` / `estilos.css`: estructura y estilos.
- `test.js`: pruebas con `assert` de Node.

## Qué se aprende

- **Modelos de color**: por qué HSL es cómodo para generar armonías (basta con sumar grados al tono) y cómo convertirlo a RGB y hexadecimal.
- **Accesibilidad**: cálculo de la luminancia relativa y del ratio de contraste WCAG (4.5 para el nivel AA) para elegir un texto legible.
- **Separar lógica e interfaz**: `colores.js` no toca el DOM, así que se puede probar con Node; además recibe el generador de azar como parámetro para que los tests sean deterministas.
- **Ámbito global de los `<script>`**: las funciones de un script clásico son globales para los siguientes, y volver a declararlas con `const` en otro script provoca un error.
