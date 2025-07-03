import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urljoin, urlparse

os.makedirs('data', exist_ok=True)

def fetch_content_and_links(url: str):
    """
    Fetches a URL's raw HTML, discovers relevant links, and returns both.
    """
    print(f"Fetching: {url}")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        response.raise_for_status()

        html_content = response.content
        
        # Discover links from the raw HTML
        links = discover_links(url, html_content)
        
        return {
            "url": url,
            "html": html_content.decode('utf-8', 'ignore'), # Save HTML for parsing
        }, links

    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None, []

def discover_links(base_url: str, html_content: str):
    """
    Discovers and filters relevant links from HTML content.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    discovered_links = set()
    
    # We now look for any link on the page
    for link_tag in soup.find_all('a', href=True):
        href = link_tag['href']
        
        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)
        
        # --- The Fix for Bad Links ---
        # 1. Only allow 'http' or 'https' schemes.
        # 2. Only allow URLs on the 'reactflow.dev' domain.
        # 3. Ignore anchor links (#) and query parameters (?).
        if (parsed_url.scheme in ['http', 'https'] and 
            parsed_url.netloc == 'reactflow.dev'):
            
            clean_url = parsed_url._replace(query="", fragment="").geturl()
            discovered_links.add(clean_url)
            
    return list(discovered_links)

def save_to_json(data, filename="data/scraped_content_raw.json"):
    """Saves a list of dictionaries to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nScraping complete. Raw HTML data saved to {filename}")