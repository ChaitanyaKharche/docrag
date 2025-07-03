from scraper import fetch_content_and_links, save_to_json
from collections import deque
import time

START_URL = "https://reactflow.dev/api-reference"

def main():
    print("Starting documentation crawl...")
    
    urls_to_visit = deque([START_URL])
    visited_urls = set()
    all_scraped_data = []

    while urls_to_visit:
        current_url = urls_to_visit.popleft()

        if current_url in visited_urls:
            continue

        visited_urls.add(current_url)

        scraped_page, new_links = fetch_content_and_links(current_url)

        if scraped_page:
            all_scraped_data.append(scraped_page)
            
            for link in new_links:
                if link not in visited_urls:
                    urls_to_visit.append(link)
        
        time.sleep(0.2) # Be polite

    if all_scraped_data:
        save_to_json(all_scraped_data)

    print(f"Crawling process finished. Scraped {len(all_scraped_data)} pages.")

if __name__ == "__main__":
    main()