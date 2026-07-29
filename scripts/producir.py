#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
producir.py — orquestador principal de El Engranaje.
Corre completo en GitHub Actions (cron 3x/día).
"""
import os
import json
import subprocess
import tempfile

import guion
import voz
import arte
import composicion as comp
import youtube_upload as yt

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(AQUI, "..")
ESTADO_PATH = os.path.join(RAIZ, "config", "estado_serie.json")


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


def leer_estado():
    if os.path.exists(ESTADO_PATH):
        with open(ESTADO_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"tema_idx": 0, "videos_producidos": 0}


def guardar_estado(estado):
    os.makedirs(os.path.dirname(ESTADO_PATH), exist_ok=True)
    with open(ESTADO_PATH, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def sujetos_de(guion_data):
    titulo = guion_data.get("titulo_video", "")
    return [
        f"person trapped running in a giant hamster wheel, city background, allegorical, {titulo}",
        f"hands reaching for coins with invisible chains, dramatic light, symbolic, {titulo}",
        f"crowd of people looking up at a giant clock, symbolic, moody, {titulo}",
    ]


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

        # 4. Composición
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

        # 5. Mezcla audio + video
        print("Mezclando audio...")
        video_final = os.path.join(tmp, "final.mp4")
        mezclar(video_mudo, mp3, video_final)
        tam = os.path.getsize(video_final) // (1024 * 1024)
        print(f"  Video final: {tam} MB, {dur_total:.1f}s")
        telegram(f"🎬 Video listo ({tam} MB, {dur_total:.1f}s)")

        # 6. Subida a YouTube
        print("Subiendo a YouTube...")
        desc = (
            f"{guion_data['guion_completo']}\n\n"
            + " ".join(guion_data.get("hashtags", []))
        )
        hashtags = guion_data.get("hashtags", [])
        tags = [t.replace("#", "") for t in hashtags]

        try:
            url = yt.subir(
                mp4_path=video_final,
                titulo=guion_data["titulo_video"],
                descripcion=desc,
                tags=tags,
            )
            telegram(f"✅ Subido a YouTube: {url}")
        except Exception as e:
            print(f"Error subiendo a YouTube: {e}")
            telegram(f"⚠️ Error en subida: {e}")
            url = None

    # 7. Guardar estado
    estado["videos_producidos"] = estado.get("videos_producidos", 0) + 1
    guardar_estado(estado)
    print(f"Listo. Total producidos: {estado['videos_producidos']}")
    telegram(f"📊 Total producidos: {estado['videos_producidos']}")


if __name__ == "__main__":
    main()
