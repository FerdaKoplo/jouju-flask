import requests
import time
from urllib.parse import quote_plus

OPENALEX_SEARCH = "https://api.openalex.org/works"
UNPAYWALL_API = "https://api.unpaywall.org/v2/"

def fetch_openalex(query="computer science OR cloud computing", per_page=50, page=1, email="your_email@example.com"):
    if not isinstance(query, str):
        query = str(query)
    query_encoded = quote_plus(query)

    params = {
        "search": query,
        "per-page": per_page,
        "page": page,
        "mailto": email
    }
    try:
        r = requests.get(OPENALEX_SEARCH, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch from OpenAlex: {e}")

    results = []
    for it in data.get("results", []):
        doi = it.get("doi", "").lower() if it.get("doi") else None
        title = it.get("title", "No Title")
        authors = [
            auth.get("author", {}).get("display_name", "")
            for auth in it.get("authorships", [])
        ]
        abstract = it.get("abstract_inverted_index")
        if abstract:
            abstract = " ".join(sum([[k]*len(v) for k, v in abstract.items()], []))

        record = {
            "source": "openalex",
            "doi": doi,
            "title": title,
            "authors": ", ".join(filter(None, authors)) or "Unknown",
            "abstract": abstract or "No abstract available",
            "year": it.get("publication_year", "Unknown"),
            "link": it.get("id", "")
        }

        if doi:
            try:
                ua_resp = requests.get(f"{UNPAYWALL_API}{doi}", params={"email": email}, timeout=15)
                if ua_resp.status_code == 200:
                    ua_data = ua_resp.json()
                    record["is_oa"] = ua_data.get("is_oa", False)
                    record["oa_pdf"] = ua_data.get("best_oa_location", {}).get("url_for_pdf")
                else:
                    record["is_oa"] = False
                    record["oa_pdf"] = None
            except Exception:
                record["is_oa"] = False
                record["oa_pdf"] = None
            time.sleep(0.2) 

        results.append(record)

    return results
