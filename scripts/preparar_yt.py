import os, base64, json, sys

yt_token = os.environ.get("YT_TOKEN", "").strip()
yt_secret = os.environ.get("YT_CLIENT_SECRET", "").strip()

if not yt_token:
    print("ERROR: YT_TOKEN vacio")
    sys.exit(1)

try:
    data = base64.b64decode(yt_token + "==").decode("utf-8")
    json.loads(data)
    open("/tmp/yt_token.json", "w").write(data)
    open("/tmp/yt_client_secret.json", "w").write(yt_secret)
    print("Credenciales OK")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
