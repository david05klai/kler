"""Persistent local automations."""
import json
from datetime import timedelta
from core.jobs import create_job, list_jobs, change_job, local_now, start_runner


def scheduler(parameters: dict, player=None, speak=None) -> str:
    try:
        action = parameters.get('action', 'list')
        if action == 'list':
            return json.dumps(list_jobs(), ensure_ascii=False)
        if action in {'delete', 'enable', 'disable', 'run_now'}:
            job_id = change_job(parameters.get('task_id', parameters.get('name', '')), action)
            return f'Tarea {job_id}: {action}.'
        if action != 'create':
            raise ValueError('Acción de programación desconocida.')
        now = local_now()
        frequency = parameters.get('frequency', 'once')
        interval = float(parameters.get('interval_minutes', 60)) * 60
        if frequency == 'interval':
            due = now + timedelta(seconds=interval)
        else:
            due = now.replace(hour=int(parameters.get('hour', 9)), minute=int(parameters.get('minute', 0)), second=0, microsecond=0)
            if frequency == 'weekly':
                weekdays = {'monday':0,'lunes':0,'tuesday':1,'martes':1,'wednesday':2,'miércoles':2,'miercoles':2,'thursday':3,'jueves':3,'friday':4,'viernes':4,'saturday':5,'sábado':5,'sabado':5,'sunday':6,'domingo':6}
                day = weekdays[str(parameters.get('weekday', 'monday')).lower()]
                due += timedelta(days=(day - now.weekday()) % 7)
                if due <= now:
                    due += timedelta(days=7)
            elif due <= now:
                due += timedelta(days=1)
        job_id = create_job(str(parameters.get('name', 'Tarea de Kler')), due.timestamp(), parameters.get('task_action', 'notify'), parameters.get('task_parameters', {}), frequency, interval)
        start_runner(player, speak)
        return f'Tarea {job_id} guardada para {due.isoformat()}. Kler debe estar abierto.'
    except Exception as exc:
        return f'Error al programar: {exc}'
