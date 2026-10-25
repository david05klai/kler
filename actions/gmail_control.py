"""Real Gmail operations; results come from the API, never fabricated."""
import base64
import json
from email.message import EmailMessage
from email.utils import parseaddr
from core.google_services import get_service


def _decode_part(payload):
    text = []
    if payload.get("mimeType") == "text/plain" and payload.get("body",{}).get("data"):
        text.append(base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8",errors="replace"))
    for part in payload.get("parts",[]):
        text.extend(_decode_part(part))
    return text


def gmail_control(parameters: dict, player=None):
    try:
        action = parameters.get("action","inbox")
        service = get_service("gmail", authorize=action=="connect")
        if action == "connect":
            return "Gmail conectado."
        messages = service.users().messages()
        if action == "labels":
            return json.dumps(service.users().labels().list(userId="me").execute().get("labels",[]),ensure_ascii=False)
        if action in {"inbox","search"}:
            query = parameters.get("query","in:inbox" if action=="inbox" else "")
            items = messages.list(userId="me",q=query,maxResults=min(20,max(1,int(parameters.get("count",5))))).execute().get("messages",[])
            results = []
            for item in items:
                msg = messages.get(userId="me",id=item["id"],format="metadata",metadataHeaders=["Subject","From","Date"]).execute()
                results.append({"id":msg["id"],"headers":msg.get("payload",{}).get("headers",[]),"snippet":msg.get("snippet","")})
            return json.dumps(results,ensure_ascii=False)
        message_id = parameters.get("message_id")
        if action in {"read","reply","archive","delete","mark_read"} and not message_id:
            raise ValueError("Falta message_id; obtén el ID completo con inbox o search.")
        if action == "read":
            msg = messages.get(userId="me",id=message_id,format="full").execute()
            return json.dumps({"id":msg["id"],"headers":msg.get("payload",{}).get("headers",[]),
                "body":"\n".join(_decode_part(msg.get("payload",{})))[:18000],"snippet":msg.get("snippet","")},ensure_ascii=False)
        if action in {"send","reply"}:
            mail = EmailMessage()
            to = str(parameters.get("to","")).strip()
            subject = str(parameters.get("subject","")).strip()
            body = parameters.get("body","")
            request = {}
            if action == "reply":
                original = messages.get(userId="me",id=message_id,format="metadata").execute()
                headers = {h["name"].lower():h["value"] for h in original.get("payload",{}).get("headers",[])}
                to = to or headers.get("reply-to",headers.get("from",""))
                subject = subject or headers.get("subject","")
                subject = subject if subject.lower().startswith("re:") else "Re: " + subject
                if headers.get("message-id"):
                    mail["In-Reply-To"] = headers["message-id"]
                    mail["References"] = headers.get("references","") + " " + headers["message-id"]
                request["threadId"] = original["threadId"]
            if not parseaddr(to)[1] or "@" not in parseaddr(to)[1] or not body:
                raise ValueError("Faltan destinatario válido o cuerpo del correo.")
            mail["To"], mail["Subject"] = to,subject
            mail.set_content(str(body))
            request["raw"] = base64.urlsafe_b64encode(mail.as_bytes()).decode()
            result = messages.send(userId="me",body=request).execute()
            return f"Correo enviado. ID: {result['id']}"
        if action in {"archive","mark_read"}:
            label = "INBOX" if action=="archive" else "UNREAD"
            messages.modify(userId="me",id=message_id,body={"removeLabelIds":[label]}).execute()
            return f"Correo {message_id}: {action} aplicado."
        if action == "delete":
            if not parameters.get("confirm"):
                return "Falta confirm=true para mover el correo a la papelera."
            messages.trash(userId="me",id=message_id).execute()
            return f"Correo {message_id} movido a la papelera."
        raise ValueError("Acción de Gmail no soportada.")
    except Exception as exc:
        return f"Error de Gmail: {exc}"
