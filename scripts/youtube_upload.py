#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
youtube_upload.py — sube el video final a YouTube.
Usa JSON puro para el token (compatible con cualquier version de google-auth).
"""
import os
import json
import base64
import tempfile

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def _obtener_credenciales():
    yt_token_b64 = os.environ.get("YT_TOKEN")
    yt_secret_str = os.environ.get("YT_CLIENT_SECRET")

    if not yt_token_b64 or not yt_secret_str:
        raise ValueError("Faltan YT_TOKEN o YT_CLIENT_SECRET")

    # Decodificar el token (viene como pickle base64 de la PC)
    # Lo convertimos a Credentials directamente extrayendo los campos
    import pickle
    token_bytes = base64.b64decode(yt_token_b64)
    creds_pickle = pickle.loads(token_bytes)

    # Extraer campos del objeto pickle y reconstruir con JSON
    secret = json.loads(yt_secret_str)
    installed = secret.get("installed", secret)

    creds = Credentials(
        token=creds_pickle.token,
        refresh_token=creds_pickle.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=installed["client_id"],
        client_secret=installed["client_secret"],
        scopes=list(creds_pickle.scopes) if creds_pickle.scopes else [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube",
        ],
    )

    # Refrescar si es necesario
    if not creds.valid:
        creds.refresh(Request())

    return creds


def subir(mp4_path, titulo, descripcion, tags=None, categoria="22", privacidad="public"):
    creds = _obtener_credenciales()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": titulo[:100],
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
        chunksize=10 * 1024 * 1024,
        resumable=True,
    )

    print(f"  Subiendo: {titulo}")
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

    url = f"https://www.youtube.com/watch?v={response['id']}"
    print(f"  Subido: {url}")
    return url
