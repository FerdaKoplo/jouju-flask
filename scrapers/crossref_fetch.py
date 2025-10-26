import requests
import time
from urllib.parse import quote_plus

CROSSREF_SEARCH = "https://api.crossref.org/works"


def fetch_crossref(query="computer science OR cloud computing", rows=50, offset=0):
    params = {"query": query, "rows": rows, "offset": offset}
    r = requests.get(CROSSREF_SEARCH, params=params, timeout=30)
    r.raise_for_status()
    items = r.json().get("message", {}).get("items", [])
    results = []
    for it in items:
        doi = it.get("DOI")
        title = (it.get("title") or [""])[0]
        authors = []
        for a in it.get("author", [])[:10]:
            authors.append(" ".join(filter(None, [a.get("given"), a.get("family")])))
        results.append({
            "source":"crossref",
            "doi": doi,
            "title": title,
            "authors": authors,
            "abstract": it.get("abstract"),
            "year": it.get("issued", {}).get("date-parts", [[None]])[0][0],
            "link": it.get("URL")
        })
    return results
