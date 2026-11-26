"""Dataset de mensajes SMS en español (spam / ham) generado por código.

No descargamos nada: un generador con plantillas y huecos crea mensajes variados
con una semilla fija, así el corpus es siempre el mismo. Para que el problema no
sea trivial se mezclan:
  - mensajes normales que hablan de dinero, ofertas o enlaces (ham "difícil"),
  - spam que imita una conversación (spam "difícil"),
  - erratas aleatorias y un pequeño porcentaje de etiquetas mal puestas (ruido),
como pasa en los datos reales.
"""

import csv
import random
from pathlib import Path

import numpy as np

RUTA_CSV = Path(__file__).resolve().parent.parent / "datos" / "mensajes.csv"
ETIQUETAS = ("ham", "spam")  # 0 = ham (normal), 1 = spam

# --- Huecos de las plantillas ----------------------------------------------

NOMBRES = ["Lucía", "Marcos", "Ana", "Javi", "Carmen", "Dani", "Sara", "Pablo", "Elena",
           "Rubén", "Irene", "Hugo", "Marta", "Álvaro", "Nuria", "Sergio", "Laura", "Iker"]
SITIOS = ["el bar de siempre", "casa de mis padres", "la biblioteca", "el gimnasio",
          "la estación", "el centro", "la playa", "el cine", "la uni", "el parque",
          "la oficina", "el súper", "el restaurante chino", "la piscina"]
HORAS = ["a las 5", "a las 7 y media", "sobre las 9", "a mediodía", "esta tarde",
         "mañana por la mañana", "el sábado", "después de clase", "a las 8", "luego"]
COSAS = ["las llaves", "el cargador", "los apuntes", "la chaqueta", "el paraguas",
         "las entradas", "el libro", "la tarjeta del gimnasio", "el portátil", "la bici"]
PREMIOS = ["un iPhone 16", "un viaje a Cancún", "un cheque de 500€", "una tablet",
           "1000 euros", "un coche nuevo", "una tarjeta regalo de 300€", "un crucero",
           "una smart TV", "2000€ en efectivo"]
MARCAS = ["Movistar", "Amazon", "Correos", "tu banco", "Netflix", "DHL", "Hacienda",
          "Mercadona", "Vodafone", "PayPal", "Orange", "Zara"]
DOMINIOS = ["premios-ya.com", "bit.ly/x7Ka2", "ganador24.net", "oferta-flash.xyz",
            "verifica-cuenta.info", "tinyurl.com/ab9", "regalo-hoy.es", "promo-sms.ly",
            "entrega-paquete.com", "www.clubvip.org"]
URLS_NORMALES = ["https://maps.app/plaza", "www.youtube.com/watch?v=x1",
                 "https://docs.google.com/doc", "www.elpais.com/noticia",
                 "https://github.com/fardatxo", "www.renfe.com"]


def _telefono(rng: random.Random) -> str:
    return f"{rng.choice('6789')}{rng.randint(10, 99)} {rng.randint(100, 999)} {rng.randint(100, 999)}"


def _rellenar(plantilla: str, rng: random.Random) -> str:
    """Sustituye cada {hueco} por un valor aleatorio de su lista."""
    valores = {
        "nombre": rng.choice(NOMBRES), "sitio": rng.choice(SITIOS),
        "hora": rng.choice(HORAS), "cosa": rng.choice(COSAS),
        "premio": rng.choice(PREMIOS), "marca": rng.choice(MARCAS),
        "dominio": rng.choice(DOMINIOS), "url": rng.choice(URLS_NORMALES),
        "tel": _telefono(rng), "num": str(rng.randint(2, 99)),
        "euros": f"{rng.choice([5, 10, 15, 20, 25, 40, 50, 120])}€",
        "codigo": str(rng.randint(1000, 9999)),
    }
    return plantilla.format(**valores)


PLANTILLAS_HAM = [
    "¿Quedamos {hora} en {sitio}?",
    "Oye {nombre}, ¿te has dejado {cosa} en mi casa?",
    "Llego tarde, estoy saliendo ya. Espérame en {sitio}",
    "Vale, nos vemos {hora}. Llevo yo {cosa}",
    "Mamá dice que vengas a cenar {hora}",
    "¿Has hecho los ejercicios de mates? Pásame los apuntes porfa",
    "Jajaja qué bueno, luego te cuento lo de {nombre}",
    "Te debo {euros} de la cena, te hago un bizum luego",
    "Al final no puedo ir {hora}, lo siento mucho",
    "Mira este vídeo, es buenísimo {url}",
    "¿Me pasas el enlace de la reunión? Creo que es {url}",
    "{nombre} ha ganado el partido, ¡qué crack!",
    "Feliz cumpleaños!! Que pases un día genial",
    "El examen es el día {num}, no te olvides de estudiar",
    "En el súper hay oferta de fruta, ¿compro algo?",
    "Me ha llamado el banco por lo de la hipoteca, luego hablamos",
    "Gracias por todo, de verdad. Mañana te devuelvo {cosa}",
    "¿Sabes si {nombre} viene {hora}?",
    "Estoy en {sitio}, ¿dónde estáis?",
    "Ya he reservado la mesa para {num} personas {hora}",
    "He ganado {euros} en la porra del trabajo jaja",
    "¿Llamas tú a {nombre} o la llamo yo? Su número es {tel}",
    "El tren sale {hora}, mira los horarios en {url}",
    "Qué pereza el lunes. ¿Café {hora}?",
    "Te he mandado el documento por correo, revísalo cuando puedas",
    "No encuentro {cosa}, ¿lo has visto?",
    "Buenas noches, descansa",
    "Recuerda pagar tu parte del regalo de {nombre}, son {euros}",
    "¿Te apuntas al cine {hora}? Hay una peli nueva",
    "Mi código del gimnasio es {codigo}, entra tú primero",
]

PLANTILLAS_SPAM = [
    "¡¡ENHORABUENA!! Has ganado {premio}. Reclama tu premio GRATIS en {dominio}",
    "Has sido seleccionado para recibir {premio}. Llama ya al {tel}",
    "{marca}: tu cuenta ha sido bloqueada. Verifica tus datos en {dominio}",
    "URGENTE: tu paquete de {marca} está retenido. Paga {euros} de aduanas en {dominio}",
    "Oferta exclusiva solo hoy: {premio} por solo {euros}. Entra en {dominio}",
    "GRATIS! Consigue {premio} respondiendo SI a este mensaje",
    "Último aviso: tienes un premio pendiente de {premio}. Código {codigo}. {dominio}",
    "Gana dinero desde casa sin experiencia, hasta {euros} al día. Info {tel}",
    "{marca} te regala {premio}. Haz clic aquí: {dominio}",
    "Préstamo rápido sin papeles, dinero en 10 minutos. Llama al {tel}",
    "Tu suscripción de {marca} ha caducado. Renueva ahora en {dominio} para no perder tu cuenta",
    "Felicidades, eres el cliente número {num}! Reclama {premio} en {dominio}",
    "Hacienda: tiene una devolución pendiente de {euros}. Acceda a {dominio}",
    "Descuento del {num}% solo hoy en {marca}! Compra ya en {dominio}",
    "Envía GANAR al {codigo} y participa en el sorteo de {premio}",
    "Tu código de verificación es {codigo}. Si no lo has pedido llama urgente al {tel}",
    "Has ganado un sorteo! Para recibir {premio} confirma tus datos bancarios en {dominio}",
    "Oferta limitada!!! Seguro de coche desde {euros} al mes. Llama gratis {tel}",
]

# Spam "disfrazado" de conversación y ham que suena a anuncio: los casos difíciles.
PLANTILLAS_SPAM_DIFICIL = [
    "Hola soy {nombre}, te he visto en el perfil y me gustaría conocerte. Escríbeme en {dominio}",
    "Hola! Perdona que te escriba, ¿eres tú el de esta foto? {dominio}",
    "{nombre} te ha enviado un mensaje de voz. Escúchalo aquí {dominio}",
    "Hola mamá, se me ha roto el móvil, este es mi número nuevo. Hazme un bizum de {euros} porfa",
    "Buenas, ¿quedamos {hora}? Te paso la ubicación: {dominio}",
]
PLANTILLAS_HAM_DIFICIL = [
    "He visto una oferta de vuelos baratísima, ¿nos vamos? Mira {url}",
    "Me ha tocado {euros} en la lotería del trabajo, ¡invito yo!",
    "Gratis la entrada al museo el domingo, ¿vamos {hora}?",
    "El banco me ha mandado un código de verificación, ¿sabes qué es?",
    "Urgente: llámame cuando puedas, es por lo de {nombre}",
]

_TECLAS_VECINAS = "qwertyuiopasdfghjklñzxcvbnm"


def _errata(texto: str, rng: random.Random) -> str:
    """Introduce una errata: cambia, duplica o borra una letra al azar."""
    posiciones = [i for i, c in enumerate(texto) if c.isalpha()]
    if not posiciones:
        return texto
    i = rng.choice(posiciones)
    accion = rng.choice(["cambiar", "duplicar", "borrar"])
    if accion == "cambiar":
        return texto[:i] + rng.choice(_TECLAS_VECINAS) + texto[i + 1:]
    if accion == "duplicar":
        return texto[:i] + texto[i] + texto[i:]
    return texto[:i] + texto[i + 1:]


def generar_mensajes(n: int = 1200, prop_spam: float = 0.35, ruido: float = 0.03,
                     semilla: int = 42) -> list[tuple[str, str]]:
    """Genera n mensajes (texto, etiqueta) sin duplicados.

    prop_spam: proporción de spam (en SMS reales el spam es minoría).
    ruido: proporción de etiquetas invertidas a propósito.
    """
    rng = random.Random(semilla)
    vistos: set[str] = set()
    mensajes: list[tuple[str, str]] = []
    intentos = 0
    while len(mensajes) < n and intentos < n * 50:
        intentos += 1
        es_spam = rng.random() < prop_spam
        dificil = rng.random() < 0.12
        if es_spam:
            plantillas = PLANTILLAS_SPAM_DIFICIL if dificil else PLANTILLAS_SPAM
        else:
            plantillas = PLANTILLAS_HAM_DIFICIL if dificil else PLANTILLAS_HAM
        texto = _rellenar(rng.choice(plantillas), rng)
        # A veces todo en mayúsculas (típico del spam, pero también de gente con prisa).
        if rng.random() < (0.15 if es_spam else 0.03):
            texto = texto.upper()
        for _ in range(rng.choice([0, 0, 0, 1, 1, 2])):
            texto = _errata(texto, rng)
        if texto in vistos:
            continue
        vistos.add(texto)
        etiqueta = "spam" if es_spam else "ham"
        if rng.random() < ruido:
            etiqueta = "ham" if es_spam else "spam"
        mensajes.append((texto, etiqueta))
    return mensajes


def guardar_csv(mensajes: list[tuple[str, str]], ruta: Path = RUTA_CSV) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["etiqueta", "texto"])
        for texto, etiqueta in mensajes:
            escritor.writerow([etiqueta, texto])


def cargar_csv(ruta: Path = RUTA_CSV) -> tuple[list[str], np.ndarray]:
    """Devuelve (textos, y) con y = 1 para spam y 0 para ham."""
    if not Path(ruta).exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Genera el dataset con: python main.py generar"
        )
    textos, y = [], []
    with open(ruta, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila["etiqueta"] not in ETIQUETAS:
                raise ValueError(f"Etiqueta desconocida: {fila['etiqueta']!r}")
            textos.append(fila["texto"])
            y.append(ETIQUETAS.index(fila["etiqueta"]))
    return textos, np.array(y, dtype=int)


def dividir_train_test(textos: list[str], y: np.ndarray, prop_test: float = 0.25,
                       semilla: int = 0):
    """División estratificada: train y test conservan la misma proporción de spam."""
    rng = np.random.default_rng(semilla)
    idx_train, idx_test = [], []
    for clase in np.unique(y):
        idx = np.flatnonzero(y == clase)
        rng.shuffle(idx)
        n_test = int(round(len(idx) * prop_test))
        idx_test.extend(idx[:n_test])
        idx_train.extend(idx[n_test:])
    idx_train = rng.permutation(idx_train)
    idx_test = rng.permutation(idx_test)
    seleccionar = lambda idx: [textos[i] for i in idx]  # noqa: E731
    return seleccionar(idx_train), seleccionar(idx_test), y[idx_train], y[idx_test]
