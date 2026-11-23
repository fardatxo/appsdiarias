# NutriSnap 🍽️📸

App web progresiva (PWA) para iPhone: haz una foto a tu plato y la IA (Claude) calcula calorías y macros. Incluye plan de déficit calórico, registro de peso con tendencia y diario de comidas. Diseño inspirado en iOS.

## Funciones
- **Escáner IA**: foto o descripción → ingredientes, gramos, kcal, proteína, carbohidratos, grasa, fibra y azúcar; gramos y ración editables.
- **Plan de peso**: Mifflin-St Jeor + nivel de actividad → gasto diario (TDEE); déficit según ritmo (0,25–1 kg/semana), mínimo seguro de calorías, macros y fecha estimada de objetivo. Se recalcula con cada pesaje.
- **Resumen**: anillo de calorías, anillos de macros, peso con tendencia, déficit de 7 días y agua.
- **Diario** por días y comidas, **Peso** con gráfica de tendencia (media exponencial), IMC y ritmo real.
- **Offline** (service worker), datos en el dispositivo (IndexedDB) y copia de seguridad JSON.

## Instalar en iPhone
1. Abre la URL en **Safari**.
2. Compartir → **Añadir a pantalla de inicio**.
3. En Perfil → *Clave de API*, pega una clave de [console.anthropic.com](https://console.anthropic.com/settings/keys).

## Arquitectura
`index.html` — un solo archivo organizado en módulos: `Util`, `Icons`, `Engine` (cálculo nutricional puro), `Store` (IndexedDB), `AI` (API de Anthropic), `Charts`, `Views`, `App` (router y eventos).
`sw.js` — caché del app shell · `manifest.webmanifest` — instalación PWA.

> La clave de API se guarda solo en el navegador del usuario. Las estimaciones de la IA son aproximadas y no sustituyen a un profesional sanitario.
