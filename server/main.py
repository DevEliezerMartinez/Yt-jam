"""
YT Jam Server — FastAPI
Recibe videoId desde la extensión Chrome y lo agrega a tu playlist de YouTube.
"""

import os
import json
import logging
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ── Config ──────────────────────────────────────────────────────────────────
PLAYLIST_ID   = os.getenv("YT_PLAYLIST_ID", "")   # tu playlist "Oficina"
TOKEN_FILE    = "token.json"
CREDS_FILE    = "credentials.json"                 # descargado de Google Cloud
SCOPES        = ["https://www.googleapis.com/auth/youtube"]
SECRET_KEY    = os.getenv("SECRET_KEY", "cambia-esto-en-produccion")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("yt-jam")

app = FastAPI(title="YT Jam Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],               # la extensión viene de chrome-extension://...
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ── Auth helper ──────────────────────────────────────────────────────────────
def get_youtube_client():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
        else:
            if not os.path.exists(CREDS_FILE):
                raise RuntimeError(
                    f"No se encontró {CREDS_FILE}. "
                    "Descárgalo de Google Cloud Console > APIs > Credenciales."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)

# ── Schemas ──────────────────────────────────────────────────────────────────
class QueueRequest(BaseModel):
    videoId: str
    title:   str | None = None    # opcional, para el log
    secret:  str | None = None    # clave simple anti-spam

# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ok", "playlist": PLAYLIST_ID or "NO CONFIGURADA"}


@app.post("/queue")
def add_to_queue(body: QueueRequest):
    # Validación mínima de clave secreta
    if body.secret != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Clave incorrecta")

    if not PLAYLIST_ID:
        raise HTTPException(status_code=500, detail="YT_PLAYLIST_ID no configurado")

    if not body.videoId or len(body.videoId) != 11:
        raise HTTPException(status_code=400, detail="videoId inválido")

    try:
        yt = get_youtube_client()
        yt.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": PLAYLIST_ID,
                    "resourceId": {
                        "kind":    "youtube#video",
                        "videoId": body.videoId,
                    },
                }
            },
        ).execute()

        log.info(f"✅ Agregado: {body.videoId} — '{body.title or 'sin título'}'")
        return {"ok": True, "videoId": body.videoId}

    except HttpError as e:
        log.error(f"YouTube API error: {e}")
        raise HTTPException(status_code=502, detail=f"Error de YouTube API: {e.reason}")

    except Exception as e:
        log.error(f"Error inesperado: {e}")
        raise HTTPException(status_code=500, detail=str(e))