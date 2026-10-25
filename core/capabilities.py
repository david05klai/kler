"""Advertise only implemented tools; advanced integrations are enabled explicitly."""
from pathlib import Path

DEFAULT_TOOLS = {
    "get_current_time","open_app","window_control","browser_control","file_controller",
    "weather_report","web_search","reminder","scheduler","sleep_mode","save_memory",
    "shutdown_jarvis","jarvis_ui_control","system_monitor","rules_engine","user_profile",
    "knowledge_base","google_maps","morning_brief","agent_task","activate_protocol"
}
ADVANCED_CODE = {"auto_programmer","tool_creator","self_edit"}

def available_tools(declarations, config):
    requested = set(config.get("enabled_tools", DEFAULT_TOOLS))
    requested.update({"get_current_time","sleep_mode","shutdown_jarvis"})
    if not config.get("allow_generated_code", False):
        requested -= ADVANCED_CODE
    requested.discard("arca_invoice")
    if config.get("ai_provider") != "ollama" and not config.get("openrouter_api_key"):
        requested.discard("agent_task")
    return [d for d in declarations if d["name"] in requested]

def for_request(declarations, text):
    # The user-selected set is already bounded (21 by default), and must remain
    # stable for follow-up commands such as "ahora borra el segundo".
    return declarations

TOOL_LABELS = {'get_current_time': 'Hora actual', 'open_app': 'Abrir aplicaciones', 'window_control': 'Ventanas', 'browser_control': 'Navegador', 'file_controller': 'Archivos', 'weather_report': 'Clima', 'web_search': 'Búsqueda web', 'reminder': 'Recordatorios', 'scheduler': 'Tareas programadas', 'sleep_mode': 'Espera por voz', 'save_memory': 'Memoria', 'shutdown_jarvis': 'Cerrar Kler', 'jarvis_ui_control': 'Paneles de Kler', 'system_monitor': 'Estado del equipo', 'rules_engine': 'Reglas por frase', 'user_profile': 'Preferencias', 'knowledge_base': 'Conocimiento local', 'google_maps': 'Mapas', 'morning_brief': 'Resumen del día', 'agent_task': 'Investigación en segundo plano', 'activate_protocol': 'Protocolos', 'google_calendar': 'Google Calendar', 'gmail_control': 'Gmail', 'google_drive': 'Google Drive', 'image_generation': 'Generar imágenes', 'git_control': 'Git', 'codebase': 'Proyectos de código', 'desktop_control': 'Escritorio', 'flight_finder': 'Buscar vuelos en navegador', 'social_media': 'Borradores de redes sociales', 'smart_home': 'Home Assistant', 'tiktok_analyzer': 'Metadatos públicos de TikTok', 'spotify_control': 'Spotify', 'computer_control': 'Teclado y ratón', 'screen_vision': 'Consultar pantalla', 'terminal_agent': 'Terminal', 'code_helper': 'Archivos de código', 'document_creator': 'Crear documentos', 'document_manager': 'Gestionar documentos', 'smart_file_organizer': 'Organizar archivos', 'native_ui': 'Control de ventanas nativo', 'camera_bus': 'Cámara gestual', 'vision_guardian': 'Asistencia visual proactiva', 'auto_programmer': 'Código generado (avanzado)', 'tool_creator': 'Crear herramientas (avanzado)', 'self_edit': 'Modificar Kler (avanzado)'}
