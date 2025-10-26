import requests
from bs4 import BeautifulSoup
import logging

def scope_pubmed(query="computer science OR cloud computing", page=1):
    
    search_url = f"https://pubmed.ncbi.nlm.nih.gov/?term={query}&page={page}"
    logging.info(f"Scraping PubMed URL: {search_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    } 

    try:
        response = requests.get(search_url, headers=headers, timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching PubMed page: {e}")
        return []   

    soup = BeautifulSoup(response.content, 'html.parser')
    articles = soup.find_all('article', class_='full-docsum')
    
    if not articles:
        logging.warning("No articles found on the PubMed page.")
        return []

    results = []
    for article in articles:
        try:
            title_element = article.find('a', class_='docsum-title')
            title = title_element.get_text(strip=True) if title_element else "No Title Found"

            authors_element = article.find('span', class_='docsum-authors')
            authors = authors_element.get_text(strip=True) if authors_element else "No Authors Found"

            relative_link = title_element['href'] if title_element else ''
            absolute_link = f"https://pubmed.ncbi.nlm.nih.gov{relative_link}" if relative_link.startswith('/') else relative_link

            results.append({
                'title' : title,
                'authors' : authors,
                'link' : absolute_link
            })

        except Exception as e:
            logging.error(f"Error parsing article: {e}")
            continue

    return results