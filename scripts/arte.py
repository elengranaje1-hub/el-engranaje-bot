#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arte.py — genera imágenes con Pollinations.ai (Flux, gratis, sin API key).
Devuelve objetos PIL.Image listos para pasar a composicion.py.

Pollinations no tiene SLA. Si falla, el pipeline usa placas de fallback
generadas proceduralmente (mismo look que el mock de prueba).
"""
import os
import time
import random
import requests
from PIL import Image, ImageDraw, ImageFilter
from io import BytesIO
from urllib.parse import quote

AQUI = os.path.dirname(os.path.abspath(__file__))
PROMPT_PATH = os.path.join(AQUI, "..", "config", "prompt_arte.txt")

# Pollinations — endpoint publico, sin key
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
ANCHO, ALTO = 1080, 1920
TIMEOUT = 45  # segundos por intento
MAX_INTENTOS = 3


def _prompt_para(sujeto):
    with open(PROMPT_PATH, encoding="utf-8") as f:
        plantilla = f.read()
    lineas = []
    negativo = ""
    for linea in plantilla.splitlines():
        if linea.startswith("--negative"):
            negativo = linea.replace("--negative:", "").strip()
        else:
            lineas.append(linea)
    prompt_positivo = " ".join(lineas).replace("{sujeto}", sujeto).strip()
    return prompt_positivo, negativo


def _pedir_imagen(prompt_positivo, negativo, seed=None):
    """Llama a Pollinations y devuelve PIL.Image o None si falla."""
    if seed is None:
        seed = random.randint(1, 99999)
    params = {
        "width": ANCHO,
        "height": ALTO,
        "seed": seed,
        "model": "flux",
        "nologo": "true",
    }
    if negativo:
        params["negative"] = negativo

    prompt_enc = quote(prompt_positivo)
    url = POLLINATIONS_URL.format(prompt=prompt_enc)

    for intento in range(1, MAX_INTENTOS + 1):
        try:
            print(f"  Arte: intento {intento}/{MAX_INTENTOS} (seed={seed})...")
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
                return Image.open(BytesIO(resp.content)).convert("RGB")
            print(f"  Arte: respuesta inesperada {resp.status_code}")
        except Exception as e:
            print(f"  Arte: error en intento {intento}: {e}")
        time.sleep(4 * intento)
    return None


def _fallback(seed):
    """Placa procedural de emergencia — mismo look verde-oliva del demo."""
    random.seed(seed)
    w, h = int(ANCHO * 1.35), int(ALTO * 1.35)
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


def _ampliar_para_ken_burns(img):
    """Escala la imagen a 1.35x para que el zoom de Ken Burns tenga margen."""
    w, h = int(ANCHO * 1.35), int(ALTO * 1.35)
    return img.resize((w, h), Image.LANCZOS)


def generar_placas(sujetos):
    """
    sujetos: lista de 2-3 strings describiendo el contenido visual de cada escena.
    Devuelve lista de PIL.Image listas para composicion.renderizar().
    """
    prompt_base, negativo = _prompt_para(sujetos[0])
    placas = []
    for i, sujeto in enumerate(sujetos):
        prompt, _ = _prompt_para(sujeto)
        img = _pedir_imagen(prompt, negativo, seed=42 + i * 7)
        if img is None:
            print(f"  Arte: usando fallback para escena {i+1}")
            img = _fallback(i + 1)
        placas.append(_ampliar_para_ken_burns(img))
    return placas


if __name__ == "__main__":
    # prueba: python3 arte.py
    sujetos = [
        "a person running in a hamster wheel inside a city",
        "hands counting coins with chains attached to wrists",
    ]
    placas = generar_placas(sujetos)
    for i, p in enumerate(placas):
        p.save(f"/tmp/placa_{i}.png")
        print(f"Placa {i}: {p.size}")
