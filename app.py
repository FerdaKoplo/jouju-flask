from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from scrapers import crossref_fetch, iee_scraper, pubmed_scraper, arxsiv_scraper, openalex_fetch

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app)

AVAILABLE_SCRAPERS = {
    'pubmed': pubmed_scraper.scope_pubmed,
    'arxsiv': arxsiv_scraper.scope_arxsiv,
    'ieee' : iee_scraper.scope_ieee,
    'Crossref' : crossref_fetch.fetch_crossref,
    'OpenAlex' : openalex_fetch.fetch_openalex,
}

@app.route('/', methods=['GET'])
def search():
    query = request.args.get('q')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    source = request.args.get('source')

    results = {}
    sources_to_search = [source] if source and source in AVAILABLE_SCRAPERS else list(AVAILABLE_SCRAPERS.keys())

    if source and source not in AVAILABLE_SCRAPERS:
        return jsonify({"error": f"Source '{source}' not available. Try one of: {list(AVAILABLE_SCRAPERS.keys())}"}), 400

    has_any_valid_results = False

    for src in sources_to_search:
        scraper_function = AVAILABLE_SCRAPERS[src]
        logging.info(f"Scraping source: {src} | query='{query}' | page={page}")

        try:
            # Pass pagination or row limits if scraper supports it
            if "rows" in scraper_function.__code__.co_varnames:
                data = scraper_function(query, rows=limit, offset=(page - 1) * limit)
            elif "per_page" in scraper_function.__code__.co_varnames:
                data = scraper_function(query, per_page=limit, page=page)
            else:
                data = scraper_function(query, page)

            if isinstance(data, list) and len(data) > 0:
                results[src] = data
                has_any_valid_results = True
            else:
                results[src] = []
        except Exception as e:
            logging.error(f"Error scraping {src.upper()}: {e}")
            results[src] = {"error": str(e)}

    # ✅ Don’t overwrite all results if one source failed
    if not has_any_valid_results:
        return jsonify({"message": "No valid results found from any source.", "query": query}), 404

    return jsonify({
        "query": query or "latest articles",
        "page": page,
        "limit": limit,
        "results": results
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)