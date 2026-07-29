#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
youtube_upload.py — lee token desde archivo JSON en disco (no desde variable de entorno).
"""
import os
import json

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def _obtener_credenciales():
    token_file = os.environ.get("YT_TOKEN_FILE", "/tmp/yt_token.json")
    secret_file = os.environ.get("YT_SECRET_FILE", "/tmp/yt_client_secret.json")

    with open(token_file) as f:
        token_data = json.load(f)

    with open(secret_file) as f:
        secret_data = json.load(f)

    installed = secret_data.get("installed", secret_data)

    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id") or installed["client_id"],
        client_secret=token_data.get("client_secret") or installed["client_secret"],
        scopes=token_data.get("scopes", [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube",
        ]),
    )

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
