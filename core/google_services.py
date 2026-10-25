"""Google OAuth connections, stored per API and never embedded in source."""
import json
from pathlib import Path
import threading

ROOT = Path(__file__).resolve().parent.parent
SCOPES = {
    "gmail":["https://www.googleapis.com/auth/gmail.modify"],
    "calendar":["https://www.googleapis.com/auth/calendar.events"],
    "drive":["https://www.googleapis.com/auth/drive"],
}
VERSIONS = {"gmail":"v1","calendar":"v3","drive":"v3"}
_lock = threading.Lock()


def get_service(name, authorize=False):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    token = ROOT / "config" / "google_tokens" / f"{name}.json"
    with _lock:
        credentials = None
        if token.exists():
            credentials = Credentials.from_authorized_user_file(str(token), SCOPES[name])
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        if not credentials or not credentials.valid or not credentials.has_scopes(SCOPES[name]):
            if not authorize:
                raise ValueError(f"{name} no está conectado. Usa Ajustes → Herramientas → Conectar Google.")
            client = ROOT / "config" / "google_credentials.json"
            if not client.exists():
                raise ValueError("Guarda las credenciales OAuth de aplicación de escritorio en config/google_credentials.json.")
            credentials = InstalledAppFlow.from_client_secrets_file(str(client), SCOPES[name]).run_local_server(
                port=0, timeout_seconds=120, authorization_prompt_message="Autoriza Kler en el navegador.",
                success_message="Kler conectado. Ya puedes cerrar esta pestaña.")
        token.parent.mkdir(parents=True, exist_ok=True)
        temp = token.with_suffix(".tmp")
        temp.write_text(credentials.to_json(), encoding="utf-8")
        temp.replace(token)
    return build(name,VERSIONS[name],http=AuthorizedHttp(credentials,http=httplib2.Http(timeout=20)),cache_discovery=False)
