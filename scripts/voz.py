#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
voz.py — sintetiza el guion con gTTS (sin restricciones en GitHub Actions).
Estima timestamps de palabras proporcionales a la duracion real del audio.
"""
import os
import asyncio
import tempfile
import subprocess

# Intentar edge-tts primero, caer a gTTS si falla
def _duracion_mp3(path):
    """Obtiene la duracion en segundos con ffprobe."""
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path
    ], capture_output=True, text=True)
    return float(result.stdout.strip())


def _timestamps_proporcional(texto, duracion_total):
    """
    Reparte la duracion proporcional al largo de cada palabra.
    Suficientemente preciso para subtitulos animados.
    """
    palabras = texto.split()
    pesos = [max(3, len(p)) for p in palabras]
    total = sum(pesos)
    return [(p, duracion_total * w / total) for p, w in zip(palabras, pesos)]


def _con_gtts(texto, ruta_mp3):
    """Genera audio con gTTS (es-co = espanol colombiano)."""
    from gtts import gTTS
    # Intentar voz colombiana, fallback a espanol generico
    for lang_tld in [("es", "com.co"), ("es", "com"), ("es", "es")]:
        try:
            tts = gTTS(text=texto, lang=lang_tld[0], tld=lang_tld[1], slow=False)
            # guardar en mp3 temporal para medir duracion
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tts.save(tmp.name)
                # reencoder a mp3 limpio con ffmpeg
                subprocess.run([
                    "ffmpeg", "-y", "-i", tmp.name,
                    "-codec:a", "libmp3lame", "-qscale:a", "2",
                    ruta_mp3
                ], check=True, capture_output=True)
                os.unlink(tmp.name)
            return True
        except Exception as e:
            print(f"  gTTS ({lang_tld}): {e}")
    return False


async def _con_edge_tts(texto, ruta_mp3):
    """Intenta edge-tts. Devuelve (exito, palabras_raw)."""
    try:
        import edge_tts
        VOZ = "es-MX-JorgeNeural"
        comunicador = edge_tts.Communicate(texto, VOZ)
        palabras_raw = []
        with open(ruta_mp3, "wb") as f:
            async for chunk in comunicador.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    palabras_raw.append({
                        "word": chunk["text"],
                        "duration": chunk["duration"] / 10_000_000,
                    })
        if os.path.getsize(ruta_mp3) < 1000:
            return False, []
        return True, palabras_raw
    except Exception as e:
        print(f"  edge-tts fallo: {e}")
        return False, []


def generar(texto, carpeta_salida):
    """
    Punto de entrada. Devuelve (ruta_mp3, palabras_tiempos).
    Intenta edge-tts, cae a gTTS si falla.
    """
    os.makedirs(carpeta_salida, exist_ok=True)
    ruta_mp3 = os.path.join(carpeta_salida, "voz.mp3")

    # 1. Intentar edge-tts
    ok, palabras_raw = asyncio.run(_con_edge_tts(texto, ruta_mp3))
    if ok and palabras_raw:
        print("  Voz: edge-tts OK")
        palabras_t = [(p["word"], max(0.12, p["duration"])) for p in palabras_raw]
        return ruta_mp3, palabras_t

    # 2. Caer a gTTS
    print("  Voz: usando gTTS (edge-tts no disponible)")
    if os.path.exists(ruta_mp3):
        os.remove(ruta_mp3)
    exito = _con_gtts(texto, ruta_mp3)
    if not exito:
        raise RuntimeError("No se pudo generar audio con ninguna opcion")

    dur = _duracion_mp3(ruta_mp3)
    palabras_t = _timestamps_proporcional(texto, dur)
    print(f"  gTTS OK: {dur:.1f}s, {len(palabras_t)} palabras")
    return ruta_mp3, palabras_t


def duracion_audio(palabras_tiempos):
    return sum(d for _, d in palabras_tiempos)


if __name__ == "__main__":
    import tempfile
    txt = "Cada mañana suena la alarma. Y sales a correr dentro de una rueda que tú no construiste."
    with tempfile.TemporaryDirectory() as tmp:
        mp3, pt = generar(txt, tmp)
        print(f"Audio: {os.path.getsize(mp3)//1024} KB, {duracion_audio(pt):.1f}s")
