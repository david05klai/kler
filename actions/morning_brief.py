"""Daily briefing assembled from actual local jobs and configured integrations."""
from datetime import date
from core.storage import get_state,set_state
from core.jobs import local_now,list_jobs

def already_briefed_today():
    return get_state("brief_date")==local_now().date().isoformat()
def mark_briefed():
    set_state("brief_date",local_now().date().isoformat())
def morning_brief(parameters: dict, player=None):
    if already_briefed_today() and not parameters.get("force"):
        return "El resumen de hoy ya fue presentado. Usa force=true para repetirlo."
    now=local_now()
    jobs=[j for j in list_jobs() if j["enabled"] and j["status"]=="pending"]
    todos=get_state("todos",[])
    tasks=[t["text"] for t in todos if not t.get("done")]
    report=[f"Hoy es {now:%Y-%m-%d}, {now:%H:%M}.",f"Recordatorios y automatizaciones pendientes: {len(jobs)}.",
            "Tareas: "+("; ".join(tasks[:10]) if tasks else "sin pendientes guardados.")]
    from pathlib import Path
    if (Path(__file__).resolve().parent.parent/"config"/"google_tokens"/"calendar.json").exists():
        from actions.google_calendar import google_calendar
        report.append("Calendario: "+google_calendar({"action":"list","days_ahead":1}))
    result="\n".join(report)
    mark_briefed()
    if player:
        player.write_log(result)
    return result
