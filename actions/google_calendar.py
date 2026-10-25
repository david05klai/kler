"""Google Calendar with real event IDs and timezone-aware timestamps."""
import json
from datetime import timedelta
from core.google_services import get_service
from core.jobs import local_now, parse_datetime

def google_calendar(parameters: dict, player=None):
    try:
        action = parameters.get("action","list")
        service = get_service("calendar", authorize=action=="connect")
        if action == "connect":
            return "Calendario conectado."
        events = service.events()
        if action == "list":
            now = local_now()
            result = events.list(calendarId="primary",timeMin=now.isoformat(),
                timeMax=(now+timedelta(days=min(365,max(1,int(parameters.get("days_ahead",7)))))).isoformat(),
                singleEvents=True,orderBy="startTime",maxResults=50).execute()
            return json.dumps([{"id":e["id"],"summary":e.get("summary",""),"start":e["start"],"end":e["end"]}
                               for e in result.get("items",[])],ensure_ascii=False)
        event_id = parameters.get("event_id")
        if action in {"edit","delete"} and not event_id:
            raise ValueError("Falta event_id completo; consulta list primero.")
        if action == "delete":
            events.delete(calendarId="primary",eventId=event_id).execute()
            return f"Evento {event_id} eliminado."
        if action not in {"create","edit"}:
            raise ValueError("Acción de calendario desconocida.")
        body = {k:parameters[k] for k in ["summary","description","location"] if k in parameters}
        if parameters.get("start"):
            start = parse_datetime(parameters["start"])
            end = parse_datetime(parameters["end"]) if parameters.get("end") else start+timedelta(hours=1)
            if end <= start:
                raise ValueError("El final debe ser posterior al inicio.")
            body.update(start={"dateTime":start.isoformat()},end={"dateTime":end.isoformat()})
        elif parameters.get("end"):
            body["end"] = {"dateTime":parse_datetime(parameters["end"]).isoformat()}
        if action == "create":
            if not body.get("summary") or not body.get("start"):
                raise ValueError("Crear un evento requiere summary y start.")
            result = events.insert(calendarId="primary",body=body).execute()
        else:
            result = events.patch(calendarId="primary",eventId=event_id,body=body).execute()
        return json.dumps({"id":result["id"],"url":result.get("htmlLink"),"summary":result.get("summary")},ensure_ascii=False)
    except Exception as exc:
        return f"Error de Calendar: {exc}"
