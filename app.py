from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from scrapers import iee_scraper, pubmed_scraper, arxsiv_scraper

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app)

AVAILABLE_SCRAPERS = {
    'pubmed': pubmed_scraper.scope_pubmed,
    'arxsiv': arxsiv_scraper.scope_arxsiv,
    'ieee' : iee_scraper.scope_ieee
}

@app.route('/scrape', methods=['GET'])
def search():
    query = request.args.get('q')
    page = request.args.get('page', 1, type=int)
    source = request.args.get('source')

    results = {}
    sources_to_search = []

    if source:
        if source in AVAILABLE_SCRAPERS:
            sources_to_search.append(source)
        else:
            return jsonify({"error": f"Source '{source}' is not available. Try 'rsc', 'pubmed', or leave blank for all."}), 400
    else:
        sources_to_search = list(AVAILABLE_SCRAPERS.keys())

    has_any_valid_results = False
    for src in sources_to_search:
        scraper_function = AVAILABLE_SCRAPERS[src]
        log_query = f"'{query}'" if query else "latest articles"
        logging.info(f"Starting scrape for source: {src} with query: {log_query} on page: {page}")
        try:
            source_results = scraper_function(query, page)
            results[src] = source_results
            if isinstance(source_results, list) and source_results:
                has_any_valid_results = True
        except Exception as e:
            logging.error(f"An error occurred while scraping {src.upper()}: {e}")
            results[src] = {"error": f"Failed to retrieve results from {src.upper()}."}
            
    if not has_any_valid_results:
        return jsonify({
            "message": "No results found from any source.",
            "query": query
        }), 404
    
    display_query = query if query else "Latest Articles"
    return jsonify({
        "query" : display_query,
        "page" : page,
        "results" : results
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)