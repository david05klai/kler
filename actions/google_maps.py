"""Open official Maps URLs; never invent travel durations."""
from urllib.parse import urlencode
import webbrowser

def google_maps(parameters: dict, player=None):
    try:
        action = parameters.get("action","search")
        if action=="directions":
            if not parameters.get("destination"):
                raise ValueError("Falta el destino.")
            params = {"api":1,"destination":parameters["destination"],
                      "travelmode":{"car":"driving","walk":"walking","bike":"bicycling"}.get(parameters.get("mode","car"),"driving")}
            if parameters.get("origin"):
                params["origin"] = parameters["origin"]
            url = "https://www.google.com/maps/dir/?" + urlencode(params)
        elif action=="search":
            query = parameters.get("query",parameters.get("destination",""))
            if not query:
                raise ValueError("Falta el lugar a buscar.")
            url = "https://www.google.com/maps/search/?" + urlencode({"api":1,"query":query})
        else:
            raise ValueError("Acción no soportada.")
        if not webbrowser.open(url):
            raise RuntimeError("No se pudo abrir el navegador.")
        return f"Mapa abierto: {url}. Consulta allí las rutas y los tiempos actualizados."
    except Exception as exc:
        return f"Error de Maps: {exc}"
