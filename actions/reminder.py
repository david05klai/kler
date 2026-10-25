"""Durable reminders with absolute dates and relative delays."""
import re
from datetime import timedelta
from core.jobs import create_job, local_now, parse_datetime, start_runner


def reminder(parameters: dict, response=None, player=None, speak=None) -> str:
    try:
        message = str(parameters.get("message", "")).strip()
        if not message:
            raise ValueError("Indica el mensaje del recordatorio.")
        value = str(parameters.get("time", "")).strip().lower()
        if parameters.get("date"):
            due = parse_datetime(f"{parameters['date']} {value}")
        else:
            match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([smhd]?)", value)
            if not match:
                raise ValueError("Usa fecha y hora HH:MM, o un plazo como 30s, 10m, 2h o 1d.")
            seconds = float(match[1]) * {"":1,"s":1,"m":60,"h":3600,"d":86400}[match[2]]
            due = local_now() + timedelta(seconds=seconds)
        if due <= local_now():
            raise ValueError("El recordatorio debe ser para una fecha futura.")
        job_id = create_job(message, due.timestamp(), "notify", {"message": message})
        start_runner(player, speak)
        result = f"Recordatorio {job_id} guardado para {due.isoformat()}. Kler debe estar abierto; si lo cierras, avisará al volver."
        if player:
            player.write_log(result)
        return result
    except Exception as exc:
        return f"Error al crear recordatorio: {exc}"
