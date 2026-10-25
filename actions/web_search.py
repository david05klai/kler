"""Return actual search results with their source URLs."""
import json

def web_search(parameters: dict, player=None):
    try:
        from duckduckgo_search import DDGS
        query = str(parameters.get("query","")).strip()
        if not query:
            raise ValueError("Indica qué quieres buscar.")
        if parameters.get("mode")=="compare":
            query = " vs ".join(parameters.get("items",[])) + " " + str(parameters.get("aspect",""))
        results = list(DDGS(timeout=12).text(query,max_results=5))
        if not results:
            return "No se encontraron resultados. No hay datos verificados para responder."
        return json.dumps([{"title":r.get("title"),"url":r.get("href"),"snippet":r.get("body")}
                           for r in results],ensure_ascii=False)
    except Exception as exc:
        return f"Error de búsqueda web: {exc}"
