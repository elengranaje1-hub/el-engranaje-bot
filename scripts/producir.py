#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
producir.py — orquestador principal de El Engranaje.
Corre completo en GitHub Actions (cron 3x/día).

Flujo:
  1. Lee/actualiza estado de la serie (config/estado_serie.json)
  2. Genera guion con Groq
  3. Genera voz con edge-tts (+ word boundaries para subtítulos)
  4. Genera 3 placas de arte con Pollinations
  5. Renderiza el video con composicion.py
  6. Mezcla audio + video con ffmpeg
  7. Sube a YouTube
  8. Notifica por Telegram
"""
import os
import sys
import json
import subprocess
import tempfile

import guion
import voz
import arte
import composicion as comp

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(AQUI, "..")
ESTADO_PATH = os.path.join(RAIZ, "config", "estado_serie.json")

# ── Telegram ────────────────────────────────────────────────────────────────
def telegram(msg):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat  = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"Telegram error: {e}")

# ── Estado de la serie ───────────────────────────────────────────────────────
def leer_estado():
    if os.path.exists(ESTADO_PATH):
        with open(ESTADO_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"tema_idx": 0, "videos_producidos": 0}

def guardar_estado(estado):
    os.makedirs(os.path.dirname(ESTADO_PATH), exist_ok=True)
    with open(ESTADO_PATH, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)

# ── YouTube ──────────────────────────────────────────────────────────────────
def subir_youtube(mp4, titulo, descripcion, hashtags):
    """
    Reutiliza el módulo de subida de SpiritualWave.
    Por ahora guarda el video localmente si no hay credenciales.
    """
    yt_secret = os.environ.get("YT_CLIENT_SECRET")
    yt_token  = os.environ.get("YT_TOKEN")
    if not yt_secret or not yt_token:
        print("YouTube: sin credenciales — video guardado localmente.")
        return None

    # TODO: conectar módulo youtube_upload.py (fase 3)
    print("YouTube: subida pendiente de implementar (fase 3)")
    return None

# ── Sujetos visuales para cada escena ───────────────────────────────────────
def sujetos_de(guion_data):
    """
    Extrae 3 sujetos visuales del guion para las 3 placas de arte.
    Por ahora los deriva del tema — en fase 3 lo hace Groq directamente.
    """
    titulo = guion_data.get("titulo_video", "")
    return [
        f"person trapped running in a giant hamster wheel, city background, {titulo}",
        f"hands reaching for coins with invisible chains, dramatic light, {titulo}",
        f"crowd of people looking up at a giant clock, symbolic, {titulo}",
    ]

# ── Mezcla audio + video ─────────────────────────────────────────────────────
def mezclar(video_sin_audio, audio_mp3, salida_final):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_sin_audio,
        "-i", audio_mp3,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        salida_final,
    ], check=True, capture_output=True)

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    estado = leer_estado()
    telegram("⚙️ <b>El Engranaje</b> — iniciando producción...")

    # 1. Guion
    print("Generando guion...")
    tema = guion.tema_del_dia(estado)
    print(f"  Tema: {tema}")
    guion_data = guion.generar(tema)
    print(f"  Título: {guion_data['titulo_video']}")
    telegram(f"📝 Guion listo: <i>{guion_data['titulo_video']}</i>")

    with tempfile.TemporaryDirectory() as tmp:

        # 2. Voz
        print("Generando voz...")
        mp3, palabras_t = voz.generar(guion_data["guion_completo"], tmp)
        dur_voz = voz.duracion_audio(palabras_t)
        print(f"  Audio: {dur_voz:.2f}s, {len(palabras_t)} palabras")
        telegram(f"🎙️ Voz lista ({dur_voz:.1f}s)")

        # 3. Arte
        print("Generando arte...")
        sujetos = sujetos_de(guion_data)
        placas = arte.generar_placas(sujetos)
        telegram(f"🎨 Arte listo ({len(placas)} escenas)")

        # 4. Composición (video sin audio)
        print("Renderizando video...")
        dur_cartel = 0.10 + len(guion_data["cartel_gancho"]) * 0.22 + 0.5
        dur_total  = dur_cartel + dur_voz
        tercio = dur_total / 3
        placas_por_escena = [
            (placas[0], 0,       tercio),
            (placas[1], tercio,  tercio * 2),
            (placas[2], tercio * 2, dur_total),
        ]
        video_mudo = comp.renderizar(
            placas_por_escena=placas_por_escena,
            cartel_lineas=guion_data["cartel_gancho"],
            palabras_tiempos=palabras_t,
            dur_total=dur_total,
            carpeta_salida=tmp,
        )

        # 5. Mezclar audio
        print("Mezclando audio...")
        video_final = os.path.join(tmp, "final.mp4")
        mezclar(video_mudo, mp3, video_final)
        tam = os.path.getsize(video_final) // (1024 * 1024)
        print(f"  Video final: {tam} MB")
        telegram(f"🎬 Video listo ({tam} MB, {dur_total:.1f}s)")

        # 6. Subida (fase 3)
        desc = (
            f"{guion_data['guion_completo']}\n\n"
            + " ".join(guion_data.get("hashtags", []))
        )
        url = subir_youtube(video_final, guion_data["titulo_video"], desc,
                            guion_data.get("hashtags", []))
        if url:
            telegram(f"✅ Subido: {url}")
        else:
            telegram("⚠️ Video producido pero subida pendiente (fase 3)")

    # 7. Guardar estado
    estado["videos_producidos"] = estado.get("videos_producidos", 0) + 1
    guardar_estado(estado)
    print(f"Listo. Total producidos: {estado['videos_producidos']}")
    telegram(f"📊 Total producidos: {estado['videos_producidos']}")


if __name__ == "__main__":
    main()
