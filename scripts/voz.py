#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
voz.py — sintetiza el guion con edge-tts y devuelve:
  - el archivo de audio .mp3
  - lista de (palabra, duracion_seg) para los subtitulos animados

edge-tts entrega word boundaries con timestamps precisos, que usamos
directamente en lugar del reparto proporcional del mock.
"""
import asyncio
import os
import json

import edge_tts

# Voces neutras latinoamericanas disponibles en edge-tts
# Jorge: Mexico, masculino, grave y claro — ideal para el tono del canal
VOZ = "es-MX-JorgeNeural"

# Alternativas si quieres probar:
# "es-CO-GonzaloNeural"  — Colombia masculino
# "es-AR-TomasNeural"    — Argentina masculino
# "es-MX-DaliaNeural"    — Mexico femenino


async def _sintetizar(texto, ruta_mp3):
    """Corre edge-tts y recolecta los word boundaries."""
    comunicador = edge_tts.Communicate(texto, VOZ)
    palabras_raw = []

    with open(ruta_mp3, "wb") as f:
        async for chunk in comunicador.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                palabras_raw.append({
                    "word": chunk["text"],
                    "offset": chunk["offset"],   # en unidades de 100ns
                    "duration": chunk["duration"],
                })

    return palabras_raw


def _convertir_tiempos(palabras_raw):
    """
    Convierte los word boundaries de edge-tts (100ns) a
    lista de (palabra, duracion_seg) que espera composicion.py.
    """
    resultado = []
    for i, p in enumerate(palabras_raw):
        dur_seg = p["duration"] / 10_000_000  # 100ns -> segundos
        # agregar pequeña pausa entre palabras (ya incluida en duration)
        resultado.append((p["word"], max(0.12, dur_seg)))
    return resultado


def generar(texto, carpeta_salida):
    """
    Punto de entrada principal.
    Devuelve (ruta_mp3, palabras_tiempos).
    palabras_tiempos: [(palabra, duracion_seg), ...]
    """
    os.makedirs(carpeta_salida, exist_ok=True)
    ruta_mp3 = os.path.join(carpeta_salida, "voz.mp3")
    palabras_raw = asyncio.run(_sintetizar(texto, ruta_mp3))
    palabras_tiempos = _convertir_tiempos(palabras_raw)
    return ruta_mp3, palabras_tiempos


def duracion_audio(palabras_tiempos):
    """Suma total de duraciones = duracion real del audio."""
    return sum(d for _, d in palabras_tiempos)


if __name__ == "__main__":
    # prueba: python3 voz.py
    import tempfile
    txt = (
        "Cada mañana suena la alarma. Y sales a correr dentro de una "
        "rueda que tú no construiste. Pagas una deuda que empezó antes "
        "de que nacieras. Y te dijeron que eso era libertad."
    )
    with tempfile.TemporaryDirectory() as tmp:
        mp3, pt = generar(txt, tmp)
        print(f"Audio: {mp3} ({os.path.getsize(mp3)//1024} KB)")
        print(f"Palabras: {len(pt)}, duracion total: {duracion_audio(pt):.2f}s")
        print("Primeras 5:", pt[:5])
