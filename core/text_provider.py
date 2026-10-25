"""Actual Ollama / OpenRouter chat, with bounded HTTP calls and tool responses."""
import json
import requests


def json_schema(value):
    if isinstance(value, dict):
        return {k: str(v).lower() if k == "type" else json_schema(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_schema(v) for v in value]
    return value


class TextProvider:
    def __init__(self, config):
        self.provider = config.get("ai_provider", "ollama")
        self.config = dict(config)
        self.supports_tools = True

    def chat(self, messages, declarations):
        tools = [{"type":"function","function":{"name":d["name"],"description":d["description"],
                  "parameters":json_schema(d.get("parameters", {"type":"object","properties":{}}))}}
                 for d in declarations]
        if self.provider == "ollama":
            url = self.config.get("ollama_url", "http://127.0.0.1:11434").rstrip("/") + "/api/chat"
            payload = {"model":self.config.get("ollama_model", "qwen2.5:3b"),
                       "messages":messages,"stream":False,"options":{"num_predict":768,"temperature":0.2}}
            headers = {}
        elif self.provider == "openrouter":
            key = str(self.config.get("openrouter_api_key", "")).strip()
            if not key:
                raise ValueError("Falta la clave de OpenRouter en Ajustes.")
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {"Authorization":f"Bearer {key}","X-Title":"Kler"}
            payload = {"model":self.config.get("openrouter_model", "google/gemini-2.5-flash"),
                       "messages":messages,"max_tokens":768}
        else:
            raise ValueError("Proveedor de texto no soportado.")
        if not self.supports_tools:
            payload["messages"] = list(messages) + [{"role":"system","content":"No tienes herramientas disponibles en este modelo. No afirmes ejecutar acciones."}]
        if tools and self.supports_tools:
            payload["tools"] = tools
        # Never retry a tool-producing request automatically: it may have already executed an action.
        response = requests.post(url, json=payload, headers=headers, timeout=(5, 45))
        if self.provider == "ollama" and response.status_code == 400 and "tool" in response.text.lower() and "support" in response.text.lower():
            # Rejected before execution. Models without tool support can still converse;
            # deterministic commands continue to run locally.
            self.supports_tools = False
            payload.pop("tools", None)
            payload["messages"] = list(messages) + [{"role":"system","content":"Este modelo no admite herramientas. No afirmes haber ejecutado acciones. Las órdenes locales sencillas se procesan por separado."}]
            response = requests.post(url, json=payload, headers=headers, timeout=(5, 45))
        if response.status_code == 429:
            raise RuntimeError("El proveedor alcanzó su cuota. Espera antes de volver a pedirlo.")
        response.raise_for_status()
        body = response.json()
        if self.provider == "ollama":
            message = body.get("message")
        else:
            choices = body.get("choices", [])
            message = choices[0].get("message") if choices else None
        if not isinstance(message, dict):
            raise ValueError("El proveedor devolvió una respuesta sin mensaje.")
        return message
