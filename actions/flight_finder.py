"""Open a real flight search, without claiming unverified fares."""
import webbrowser
from urllib.parse import urlencode

def flight_finder(parameters: dict, player=None):
    if not all(parameters.get(k) for k in ["origin","destination","date"]):
        return "Error: faltan origen, destino o fecha."
    query = f"Flights from {parameters['origin']} to {parameters['destination']} on {parameters['date']}"
    if parameters.get("return_date"):
        query += " return " + str(parameters["return_date"])
    query += f" {parameters.get('passengers',1)} passengers {parameters.get('cabin','economy')}"
    url = "https://www.google.com/travel/flights?" + urlencode({"q":query})
    if not webbrowser.open(url):
        return "Error: no se pudo abrir el navegador."
    return f"Búsqueda de vuelos abierta: {url}. Los precios y la disponibilidad deben consultarse allí."
