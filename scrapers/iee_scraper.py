import time
import logging
import json
from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup
try:
    import undetected_chromedriver as uc
except Exception as e:
    uc = None
    logging.warning("undetected-chromedriver not available: %s", e)


def scope_ieee(query=None, page=1, use_uc=True, timeout=10):
    if not query:
        query = "computer science OR cloud computing"

    query_encoded = quote_plus(query)
    search_url = f"https://ieeexplore.ieee.org/search/searchresult.jsp?queryText={query_encoded}&pageNumber={page}"

    html = None

    if use_uc and uc is not None:
        try:
            options = uc.ChromeOptions()
            options.add_argument("--headless=new")        
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("window-size=1920,1080")
            options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            driver = uc.Chrome(options=options)
            driver.get(search_url)

            time.sleep(3 + min(timeout, 7))

            html = driver.page_source
            driver.quit()

        except Exception as e:
            logging.warning("Browser rendering failed (%s); will fallback to requests. Error: %s", type(e).__name__, e)
            try:
                driver.quit()
            except Exception:
                pass
            html = None

    if not html:
        logging.info("Falling back to a requests-based approach (may return fewer results).")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://ieeexplore.ieee.org/"
            }
            r = requests.get(search_url, headers=headers, timeout=15)
            r.raise_for_status()
            html = r.text
        except Exception as e:
            logging.error("Requests fallback failed: %s", e)
            html = None

    if not html:
        return crossref_fallback(query, page)

    soup = BeautifulSoup(html, "html.parser")

    script = None
    for candidate_id in ("xplGlobal", "__INITIAL_DATA__", "react-server-data"):
        script = soup.find("script", id=candidate_id)
        if script:
            break

    if not script:
        scripts = soup.find_all("script")
        for s in scripts:
            text = s.string or ""
            if "xplGlobal.document" in text or "global.document" in text or "window.__INITIAL_DATA__" in text:
                script = s
                break

    records = []
    if script and script.string:
        txt = script.string.strip()
        try:
            if "xplGlobal.document.metadata" in txt:
                json_str = txt.split("xplGlobal.document.metadata", 1)[1]
                json_str = json_str.split("=", 1)[1].strip().rstrip(";")
                data = json.loads(json_str)
                records = data.get("records", []) or data.get("results", [])
            elif "window.__INITIAL_DATA__" in txt or "__INITIAL_DATA__" in txt:
                json_str = txt.split("=", 1)[1].strip().rstrip(";")
                data = json.loads(json_str)
                records = data.get("records", []) or data.get("articles", []) or data.get("searchResults", [])
            else:
                try:
                    data = json.loads(txt)
                    records = data.get("records", []) or data.get("articles", []) or data.get("results", [])
                except Exception:
                    records = []
        except Exception as e:
            logging.debug("Failed to parse embedded JSON: %s", e)
            records = []

    results = []

    if records:
        for article in records:
            try:
                title = article.get("articleTitle") or article.get("title") or article.get("paperTitle") or "No Title"
                authors_list = article.get("authors", []) or article.get("authorsList", [])
                authors = ", ".join(a.get("preferredName") if isinstance(a, dict) else str(a) for a in authors_list) or "No Authors"
                link = article.get("documentLink") or article.get("htmlLink") or article.get("url") or ""
                if link and link.startswith("/"):
                    link = "https://ieeexplore.ieee.org" + link
                results.append({"title": title, "authors": authors, "link": link})
            except Exception:
                continue

    if not results:
        item_selectors = [
            "div.List-results-items",          
            "div.List-results-item",           
            "div.Issue-item",                  
            "div.result-item"                  
        ]
        items = []
        for sel in item_selectors:
            items = soup.select(sel)
            if items:
                break

        if not items:
            items = soup.select("a[href^='/document/']")[:50]

        for it in items:
            try:
                a = it.find("a", href=True)
                if not a:
                    a = it.select_one("a[href^='/document/']")
                title = a.get_text(strip=True) if a else (it.get_text(strip=True)[:120] + "...")
                link = a["href"] if a and a.has_attr("href") else ""
                if link and link.startswith("/"):
                    link = "https://ieeexplore.ieee.org" + link
                author_p = it.find(lambda tag: tag.name in ("p", "span") and "author" in (tag.get("class") or []))
                authors = author_p.get_text(" ", strip=True) if author_p else "No Authors Found"
                results.append({"title": title, "authors": authors, "link": link})
            except Exception:
                continue

    if not results:
        logging.info("No results extracted from rendered HTML; using CrossRef fallback.")
        return crossref_fallback(query, page)

    return results

def crossref_fallback(query, page=1):
   
    try:
        params = {"query": query, "rows": 10, "offset": (page - 1) * 10}
        r = requests.get("https://api.crossref.org/works", params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = data.get("message", {}).get("items", [])[:10]
        results = []
        for it in items:
            title = it.get("title", ["No Title"])[0] if it.get("title") else "No Title"
            authors = ", ".join(
                "{} {}".format(a.get("given", ""), a.get("family", "")).strip() for a in it.get("author", [])[:5]
            ) or "No Authors"
            link = it.get("URL", "")
            results.append({"title": title, "authors": authors, "link": link})
        return results
    
    except Exception as e:
        logging.error("CrossRef fallback failed: %s", e)
        return []