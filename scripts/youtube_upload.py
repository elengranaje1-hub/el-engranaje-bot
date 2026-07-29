#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
youtube_upload.py — sube el video final a YouTube.
Lee YT_CLIENT_SECRET y YT_TOKEN desde variables de entorno (GitHub Secrets).
"""
import os
import json
import pickle
import base64
import tempfile

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def _obtener_credenciales():
    """Reconstruye las credenciales desde los secrets de GitHub Actions."""
    # El token viene como base64 del pickle original
    yt_token = os.environ.get("YT_TOKEN")
    yt_secret = os.environ.get("YT_CLIENT_SECRET")

    if not yt_token or not yt_secret:
        raise ValueError("Faltan YT_TOKEN o YT_CLIENT_SECRET en los secrets")

    # Reconstruir credenciales desde pickle base64
    token_bytes = base64.b64decode(yt_token)
    creds = pickle.loads(token_bytes)

    # Refrescar si está vencido
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise ValueError("Token de YouTube inválido y sin refresh_token")

    return creds


def subir(mp4_path, titulo, descripcion, tags=None, categoria="22", privacidad="public"):
    """
    Sube el video a YouTube.
    Devuelve la URL del video subido.
    categoria 22 = "People & Blogs" (adecuado para video-ensayo)
    """
    creds = _obtener_credenciales()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": titulo[:100],  # YouTube limita a 100 caracteres
            "description": descripcion[:5000],
            "tags": tags or [],
            "categoryId": categoria,
            "defaultLanguage": "es",
        },
        "status": {
            "privacyStatus": privacidad,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        mp4_path,
        mimetype="video/mp4",
        chunksize=10 * 1024 * 1024,  # 10 MB por chunk
        resumable=True,
    )

    print(f"  Subiendo a YouTube: {titulo}")
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Progreso: {int(status.progress() * 100)}%")

    video_id = response["id"]
    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"  ✅ Subido: {url}")
    return url


if __name__ == "__main__":
    # Prueba rápida de autenticación
    try:
        creds = _obtener_credenciales()
        print(f"Token válido: {creds.valid}")
        print(f"Expira: {creds.expiry}")
    except Exception as e:
        print(f"Error: {e}")
