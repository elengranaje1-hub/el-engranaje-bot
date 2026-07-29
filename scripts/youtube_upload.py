import os, json, base64
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def _obtener_credenciales():
    yt_token_b64 = os.environ.get("YT_TOKEN")
    if not yt_token_b64:
        raise ValueError("Falta YT_TOKEN en los secrets")
    token_data = json.loads(base64.b64decode(yt_token_b64).decode())
    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"],
    )
    if not creds.valid:
        creds.refresh(Request())
    return creds

def subir(mp4_path, titulo, descripcion, tags=None, categoria="22", privacidad="public"):
    creds = _obtener_credenciales()
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {"title": titulo[:100], "description": descripcion[:5000], "tags": tags or [], "categoryId": categoria, "defaultLanguage": "es"},
        "status": {"privacyStatus": privacidad, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(mp4_path, mimetype="video/mp4", chunksize=10*1024*1024, resumable=True)
    print(f"  Subiendo: {titulo}")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Progreso: {int(status.progress() * 100)}%")
    url = f"https://www.youtube.com/watch?v={response['id']}"
    print(f"  Subido: {url}")
    return url
