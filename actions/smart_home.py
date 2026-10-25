"""Control configured Home Assistant entities with real service responses."""
import json
import requests
from memory.config_manager import load_api_keys

def smart_home(parameters: dict, player=None):
    try:
        cfg=load_api_keys()
        base=str(cfg.get("home_assistant_url","")).rstrip("/")
        token=cfg.get("home_assistant_token","")
        if not base.startswith(("http://","https://")) or not token:
            raise ValueError("Configura home_assistant_url y home_assistant_token en Ajustes → Herramientas.")
        headers={"Authorization":"Bearer "+str(token)}
        action=parameters.get("action","status")
        result=requests.get(base+"/api/states",headers=headers,timeout=(5,10));result.raise_for_status()
        entities=result.json()
        if action in {"list","setup"}:
            return json.dumps([{"id":e["entity_id"],"name":e.get("attributes",{}).get("friendly_name"),"state":e["state"]}
                               for e in entities if e["entity_id"].split(".")[0] in {"light","switch","climate","scene"}],ensure_ascii=False)
        device=str(parameters.get("device",parameters.get("scene",""))).casefold()
        matches=[e for e in entities if device and (device==e["entity_id"].casefold() or device==str(e.get("attributes",{}).get("friendly_name","")).casefold())]
        if len(matches)!=1:
            raise ValueError("Indica un dispositivo único usando su ID de list.")
        entity=matches[0];domain=entity["entity_id"].split(".")[0]
        if action=="status":
            return json.dumps(entity,ensure_ascii=False)
        payload={"entity_id":entity["entity_id"]}
        service={"on":"turn_on","off":"turn_off","toggle":"toggle","scene":"turn_on"}.get(action)
        if action=="brightness":
            domain="light";service="turn_on"
            payload["brightness_pct"]=min(100,max(0,int(parameters.get("brightness",parameters.get("value",100)))))
        elif action=="color":
            from PIL import ImageColor
            colors={"rojo":"red","azul":"blue","verde":"green","blanco":"white","amarillo":"yellow","morado":"purple"}
            value=str(parameters.get("color","white"))
            domain="light";service="turn_on";payload["rgb_color"]=list(ImageColor.getrgb(colors.get(value,value)))
        elif action=="temperature":
            if domain=="climate":
                service="set_temperature";payload["temperature"]=float(parameters["value"])
            elif domain=="light":
                service="turn_on";payload["color_temp_kelvin"]=int(parameters["value"])
        if not service:
            raise ValueError("Acción no soportada.")
        result=requests.post(f"{base}/api/services/{domain}/{service}",headers=headers,json=payload,timeout=(5,10))
        result.raise_for_status()
        return "Home Assistant aceptó la operación: "+json.dumps(result.json(),ensure_ascii=False)[:10000]
    except Exception as exc:
        return f"Error de hogar: {exc}"
