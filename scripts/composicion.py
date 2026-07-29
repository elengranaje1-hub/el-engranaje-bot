#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor de composicion visual — El Engranaje.
Renderiza tipografia frame a frame con Pillow (sin depender de libass)
y encoda con ffmpeg. Recibe el guion estructurado del pipeline y produce
el video vertical final.
"""
import os
import subprocess
import shutil
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
AQUI = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(AQUI, "..", "fonts", "Anton.ttf")

ROJO = (216, 22, 30)
BLANCO = (247, 245, 240)
NEGRO = (10, 10, 10)


def fuente(size):
    return ImageFont.truetype(FONT_PATH, size)


def medir(txt, f):
    b = f.getbbox(txt)
    return b[2] - b[0], b[3] - b[1], b[0], b[1]


def texto_contorno(draw, xy, txt, f, fill, stroke=(0, 0, 0), grosor=9):
    draw.text(xy, txt, font=f, fill=fill, stroke_width=grosor, stroke_fill=stroke)


def ease_back(p):
    c = 1.70158
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


def capa_cartel(lineas, t, colores=None):
    """lineas: lista de strings (2-3). colores alterna ROJO/BLANCO si no se da."""
    if colores is None:
        colores = [(ROJO, BLANCO), (BLANCO, NEGRO), (ROJO, BLANCO)]
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y = int(H * 0.30)
    rots = [-2.0, 1.5, -1.2]
    for i, txt in enumerate(lineas):
        bg, fg = colores[i % len(colores)]
        rot = rots[i % len(rots)]
        t0 = 0.10 + i * 0.22
        p = max(0.0, min(1.0, (t - t0) / 0.38))
        if p <= 0:
            y += 250
            continue
        e = ease_back(p)
        f = fuente(126)
        tw, th, ox, oy = medir(txt, f)
        pad_x, pad_y = 46, 30
        bw, bh = tw + pad_x * 2, th + pad_y * 2
        blk = Image.new("RGBA", (bw + 60, bh + 60), (0, 0, 0, 0))
        db = ImageDraw.Draw(blk)
        db.rectangle([34, 34, 34 + bw, 34 + bh], fill=(0, 0, 0, 150))
        db.rectangle([26, 26, 26 + bw, 26 + bh], fill=bg + (255,))
        db.text((26 + pad_x - ox, 26 + pad_y - oy), txt, font=f, fill=fg + (255,))
        blk = blk.rotate(rot, resample=Image.BICUBIC, expand=True)
        dirx = -1 if i % 2 == 0 else 1
        x = int(W * 0.5 - blk.width / 2 + dirx * (1 - e) * W * 0.85)
        capa.alpha_composite(blk, (x, y - 30))
        y += bh + 34
    return capa


def _grupos_de_tres(palabras_tiempos):
    for i in range(0, len(palabras_tiempos), 3):
        yield palabras_tiempos[i:i + 3]


def capa_subs(palabras_tiempos, t):
    """palabras_tiempos: [(palabra, duracion_seg), ...] ya alineado con el audio."""
    ac, idx_activo = 0.0, None
    for k, (_, d) in enumerate(palabras_tiempos):
        if t < ac + d:
            idx_activo = k
            local_t = t - ac
            break
        ac += d
    if idx_activo is None:
        return None

    ini_grupo = (idx_activo // 3) * 3
    grupo = palabras_tiempos[ini_grupo:ini_grupo + 3]
    activo_local = idx_activo - ini_grupo

    f = fuente(96)
    espacio = 26
    anchos = [medir(w, f)[0] for w, _ in grupo]
    total = sum(anchos) + espacio * (len(grupo) - 1)

    capa = Image.new("RGBA", (W, 340), (0, 0, 0, 0))
    x = (W - total) // 2
    for j, (w, _) in enumerate(grupo):
        if j > activo_local:
            x += anchos[j] + espacio
            continue
        esc = 1.0
        if j == activo_local:
            p = min(1.0, local_t / 0.14)
            esc = 0.74 + 0.34 * ease_back(p)
        tw, th, ox, oy = medir(w, f)
        pal = Image.new("RGBA", (tw + 60, th + 60), (0, 0, 0, 0))
        dp = ImageDraw.Draw(pal)
        texto_contorno(dp, (30 - ox, 30 - oy), w, f, BLANCO, (0, 0, 0), 9)
        if esc != 1.0:
            nw, nh = max(1, int(pal.width * esc)), max(1, int(pal.height * esc))
            pal = pal.resize((nw, nh), Image.LANCZOS)
        capa.alpha_composite(pal, (x - (pal.width - anchos[j] - 60) // 2 - 30,
                                    140 - pal.height // 2))
        x += anchos[j] + espacio
    return capa


def capa_marca(nombre="EL ENGRANAJE"):
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    f = fuente(38)
    tw, th, ox, oy = medir(nombre, f)
    d.rectangle([44, 62, 44 + tw + 42, 62 + th + 30], fill=ROJO + (235,))
    d.text((44 + 21 - ox, 62 + 15 - oy), nombre, font=f, fill=BLANCO + (255,))
    return capa


def fondo_en(placa, t, dur):
    """Ken Burns sobre una placa de arte generada (mas grande que el frame)."""
    p = t / dur
    z = 1.30 - 0.22 * p
    cw, ch = int(W * z), int(H * z)
    max_x, max_y = placa.width - cw, placa.height - ch
    x = int(max(0, max_x) * (0.35 + 0.30 * p))
    y = int(max(0, max_y) * (0.60 - 0.25 * p))
    return placa.crop((x, y, x + cw, y + ch)).resize((W, H), Image.LANCZOS)


def renderizar(placas_por_escena, cartel_lineas, palabras_tiempos,
                dur_total, carpeta_salida, nombre_marca="EL ENGRANAJE"):
    """
    placas_por_escena: lista de (imagen_PIL, inicio_seg, fin_seg)
    cartel_lineas: lineas del gancho inicial (2-3 strings)
    palabras_tiempos: [(palabra, duracion_seg), ...] para TODO el guion
    """
    frames_dir = os.path.join(carpeta_salida, "frames")
    shutil.rmtree(frames_dir, ignore_errors=True)
    os.makedirs(frames_dir)
    marca = capa_marca(nombre_marca)
    dur_cartel = 0.10 + len(cartel_lineas) * 0.22 + 0.5
    n = int(dur_total * FPS)

    for i in range(n):
        t = i / FPS
        placa, ini, fin = next(
            ((p, a, b) for p, a, b in placas_por_escena if a <= t < b),
            placas_por_escena[-1]
        )
        fr = fondo_en(placa, t - ini, max(0.01, fin - ini)).convert("RGBA")

        if t < dur_cartel:
            fr.alpha_composite(capa_cartel(cartel_lineas, t))
        else:
            s = capa_subs(palabras_tiempos, t - dur_cartel)
            if s is not None:
                fr.alpha_composite(s, (0, int(H * 0.66)))

        fr.alpha_composite(marca)
        fr.convert("RGB").save(os.path.join(frames_dir, f"f_{i:05d}.png"))

    salida_mp4 = os.path.join(carpeta_salida, "video.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "f_%05d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19",
        "-preset", "medium", "-movflags", "+faststart", salida_mp4
    ], check=True, capture_output=True)
    shutil.rmtree(frames_dir, ignore_errors=True)
    return salida_mp4
