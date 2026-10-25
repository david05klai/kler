"""Small deterministic commands, avoiding an LLM round trip for explicit text commands."""
import re
from datetime import datetime

def route(text):
    value = text.strip()
    if re.fullmatch(r"(?:kler[, ]+)?(?:qué hora es|que hora es|dime la hora|hora)[?.! ]*", value, re.I):
        return ("get_current_time", {})
    match = re.fullmatch(r"(?:kler[, ]+)?(?:abre|abrir|inicia)\s+([\w .+-]{1,60})[.!]?", value, re.I)
    if match:
        return ("open_app", {"app_name": match[1].strip()})
    if re.fullmatch(r"(?:kler[, ]+)?(?:duerme|dormir|modo suspensión|modo suspension)[.! ]*", value, re.I):
        return ("sleep_mode", {})
    return None
