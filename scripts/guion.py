#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guion.py — genera el guion estructurado usando Groq.
Devuelve un dict con titulo_video, cartel_gancho, guion_completo, hashtags.
"""
import json
import os
import re
from groq import Groq

AQUI = os.path.dirname(os.path.abspath(__file__))
PROMPT_PATH = os.path.join(AQUI, "..", "config", "prompt_guion.txt")

MODELO = "llama3-70b-8192"

TEMAS = [
    "la carrera de la rata y el trabajo moderno",
    "por qué nunca tienes suficiente dinero aunque trabajes más",
    "el consumismo como trampa del sistema",
    "por qué las redes sociales te hacen sentir pobre",
    "el mito de que estudiar garantiza el éxito",
    "por qué el tiempo libre te da culpa",
    "cómo el crédito te convierte en esclavo voluntario",
    "por qué compararte con otros te mantiene quieto",
    "el trabajo de tus sueños como mentira moderna",
    "por qué ser productivo se convirtió en una identidad",
    "cómo la publicidad te hace creer que te falta algo",
    "el precio real de una vida normal",
    "por qué nadie te enseñó a manejar dinero en el colegio",
    "la trampa de la casa propia como meta de vida",
    "por qué trabajas para pagar cosas que no necesitas",
    "el negocio detrás de hacerte sentir que no eres suficiente",
    "cómo el sistema necesita que estés ocupado para que no pienses",
    "por qué el éxito ajeno te paraliza",
    "la ilusión del emprendimiento como libertad",
    "por qué los ricos hablan de mentalidad y no de herencia",
]


def tema_del_dia(estado):
    """Rota los temas en orden. estado es el dict de config/estado_serie.json"""
    idx = estado.get("tema_idx", 0) % len(TEMAS)
    estado["tema_idx"] = idx + 1
    return TEMAS[idx]


def generar(tema, api_key=None):
    """Llama a Groq y devuelve el dict estructurado del guion."""
    key = api_key or os.environ["GROQ_API_KEY"]
    cliente = Groq(api_key=key)

    with open(PROMPT_PATH, encoding="utf-8") as f:
        prompt = f.read().replace("{tema}", tema)

    resp = cliente.chat.completions.create(
        model=MODELO,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
        max_tokens=600,
    )
    raw = resp.choices[0].message.content.strip()

    # limpiar posibles backticks que el modelo agrega a veces
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()

    return json.loads(raw)


if __name__ == "__main__":
    # prueba rapida: python3 guion.py
    resultado = generar("la carrera de la rata y el trabajo moderno")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
