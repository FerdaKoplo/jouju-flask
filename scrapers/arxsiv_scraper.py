import requests
from bs4 import BeautifulSoup
import logging

def scope_arxsiv(query, page=1):
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    start_index = (page - 1) * 50
    
    if query:
        search_url = f"https://arxiv.org/search/?query={query}&searchtype=all&source=header&start={start_index}"
        logging.info(f"Scraping arXiv search URL: {search_url}")
    else: 
        search_url = "https://arxiv.org/list/cs/new"
        logging.info(f"Scraping arXiv for latest CS articles: {search_url}")

    try:
        response = requests.get(search_url, headers=headers, timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching arXiv page: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')

    results = []

    if query:
        articles = soup.find_all('li', class_='arxiv-result')
        for article in articles:
            try:
                title_element = article.find('p', class_='title')
                title = title_element.get_text(strip=True) if title_element else "No Title Found"

                link_element = article.find('p', class_='list-title').find('a')
                link = link_element['href'] if link_element else ''

                authors_element = article.find('p', class_='authors')
                authors_list = [a.get_text(strip=True) for a in authors_element.find_all('a')]
                authors = ', '.join(authors_list) if authors_list else "No Authors Found"

                results.append({
                    'title': title,
                    'authors': authors,
                    'link': link
                })
            except Exception as e:
                logging.error(f"Error parsing an arXiv article: {e}")
                continue
    else:
        entries = soup.select('dl > dt')
        for dt in entries[:20]: 
            try:
                link = "https://arxiv.org" + dt.find('a', title='Abstract')['href']
                title_tag = dt.find_next_sibling('dd').find('div', class_='list-title mathjax')
                title = title_tag.get_text(strip=True).replace('Title:', '') if title_tag else "No Title Found"

                authors_tag = dt.find_next_sibling('dd').find('div', class_='list-authors')
                authors = ', '.join(a.get_text(strip=True) for a in authors_tag.find_all('a')) if authors_tag else "No Authors Found"

                results.append({
                    'title': title,
                    'authors': authors,
                    'link': link
                })
            except Exception as e:
                logging.error(f"Error parsing new arXiv entry: {e}")
                continue

    if not results:
        logging.warning("No articles found on the arXiv page.")
    return results