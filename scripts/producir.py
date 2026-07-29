#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orquestador de "El Engranaje".

MODO ACTUAL: prueba (mock). Genera un video completo con datos de ejemplo
para validar el motor de composicion de punta a punta, SIN gastar en
APIs. Cuando conectemos Groq + Pollinations + edge-tts, este archivo
se actualiza para llamarlas de verdad — la funcion renderizar() de
composicion.py no cambia.
"""
import os
import random
from PIL import Image, ImageDraw, ImageFilter
import composicion as comp

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "..", "salida")

GUION_PRUEBA = {
    "titulo_video": "Te vendieron una vida que no es tuya",
    "cartel_gancho": ["TE VENDIERON", "UNA VIDA", "QUE NO ES TUYA"],
    "guion_completo": (
        "Cada mañana suena la alarma. Y sales a correr dentro de una "
        "rueda que tú no construiste. Pagas una deuda que empezó "
        "antes de que nacieras. Y te dijeron que eso era libertad. "
        "El sistema no te encerró. Te vendió la llave y te cobró "
        "la renta de la jaula."
    ),
}


def placa_de_prueba(seed):
    random.seed(seed)
    w, h = int(1080 * 1.35), int(1920 * 1.35)
    base = Image.new("RGB", (w // 6, h // 6))
    px = base.load()
    for y in range(base.height):
        for x in range(base.width):
            n = random.random()
            t = y / base.height
            r = int(28 + 34 * n + 18 * (1 - t))
            g = int(38 + 40 * n + 26 * (1 - t))
            b = int(26 + 28 * n + 12 * (1 - t))
            px[x, y] = (r, g, b)
    img = base.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(12))
    d = ImageDraw.Draw(img, "RGBA")
    for _ in range(26):
        cx, cy = random.randint(0, w), random.randint(0, h)
        rx, ry = random.randint(90, 340), random.randint(60, 220)
        a = random.randint(10, 34)
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(150, 160, 110, a))
    return img.filter(ImageFilter.GaussianBlur(28))


def palabras_con_tiempo(texto, duracion_total):
    """
    MOCK: reparte el tiempo por longitud de palabra.
    Cuando conectemos edge-tts real, esto se reemplaza por las marcas
    de tiempo (word boundaries) que la libreria entrega de verdad.
    """
    palabras = texto.split()
    pesos = [max(3, len(p)) for p in palabras]
    total_peso = sum(pesos)
    return [(p, duracion_total * peso / total_peso) for p, peso in zip(palabras, pesos)]


def main():
    os.makedirs(SALIDA, exist_ok=True)
    print("Generando placas de arte (prueba)...")
    placas = [placa_de_prueba(s) for s in (1, 2, 3)]

    dur_voz = 9.5  # segundos — vendra del audio real de edge-tts
    palabras_t = palabras_con_tiempo(GUION_PRUEBA["guion_completo"], dur_voz)

    dur_cartel = 0.10 + len(GUION_PRUEBA["cartel_gancho"]) * 0.22 + 0.5
    dur_total = dur_cartel + dur_voz

    tercio = dur_total / 3
    placas_por_escena = [
        (placas[0], 0, tercio),
        (placas[1], tercio, tercio * 2),
        (placas[2], tercio * 2, dur_total),
    ]

    print(f"Renderizando {int(dur_total * comp.FPS)} frames...")
    mp4 = comp.renderizar(
        placas_por_escena=placas_por_escena,
        cartel_lineas=GUION_PRUEBA["cartel_gancho"],
        palabras_tiempos=palabras_t,
        dur_total=dur_total,
        carpeta_salida=SALIDA,
    )
    print("Video listo:", mp4)
    print("(Falta: voz real de edge-tts, arte real de Pollinations, subida a YouTube)")


if __name__ == "__main__":
    main()
