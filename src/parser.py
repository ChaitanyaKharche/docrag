import json
import os
from bs4 import BeautifulSoup

def parse_table(table_element):
    """Converts an HTML table element to a Markdown table string."""
    headers = [th.get_text(strip=True) for th in table_element.select('thead th')]
    
    # Handle tables that might not have a thead
    if not headers:
        header_row = table_element.select_one('tr')
        if header_row:
            headers = [cell.get_text(strip=True) for cell in header_row.find_all(['th', 'td'])]

    if not headers:
        return "" # Cannot parse table without headers

    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(['---'] * len(headers)) + " |"
    
    rows = []
    for row in table_element.select('tbody tr'):
        cells = [td.get_text(separator=' ', strip=True).replace('\n', ' ') for td in row.find_all('td')]
        if len(cells) == len(headers): # Ensure row matches header count
            rows.append("| " + " | ".join(cells) + " |")
            
    return "\n".join([header_line, separator_line] + rows)

def parse_element_to_markdown(element):
    """Recursively parses a BeautifulSoup element into Markdown."""
    if not element:
        return ""

    if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        level = int(element.name[1])
        return f"\n{'#' * level} {element.get_text(strip=True)}\n"
    
    elif element.name == 'p':
        return element.get_text(strip=True) + "\n"

    elif element.name == 'table':
        return parse_table(element) + "\n"

    elif element.name == 'pre':
        # Preserve newlines and indentation within code blocks
        return f"```\n{element.get_text()}\n```\n"

    elif element.name == 'code':
        # Inline code
        return f"`{element.get_text(strip=True)}`"

    elif element.name == 'ul':
        items = [f"* {li.get_text(strip=True)}" for li in element.find_all('li', recursive=False)]
        return "\n".join(items) + "\n"

    elif element.name == 'div' or element.name == 'main':
         # Process children of divs and main, concatenating results
        return "".join(parse_element_to_markdown(child) for child in element.contents)
    
    elif hasattr(element, 'get_text'):
         # For other tags, just get the text if they don't have special handling
        return element.get_text(strip=True)

    return "" # Ignore tags we don't know how to handle


def process_html_file(html):
    """Processes a single HTML file to extract structured content."""
    soup = BeautifulSoup(html, 'lxml')
    main_content = soup.find('main')
    
    if not main_content:
        return ""

    # This will build the markdown string from the parsed elements
    return parse_element_to_markdown(main_content).strip()

def main():
    in_filename = 'data/scraped_content_raw.json'
    out_filename = 'data/parsed_structured_content.json'

    if not os.path.exists(in_filename):
        print(f"Error: Input file not found at {in_filename}")
        print("Please run the scraper (main.py) first.")
        return

    with open(in_filename, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    parsed_data = []
    print("Starting parsing of raw HTML files...")
    for i, item in enumerate(raw_data):
        print(f"Parsing {i+1}/{len(raw_data)}: {item['url']}")
        structured_content = process_html_file(item['html'])
        if structured_content:
            parsed_data.append({
                "url": item['url'],
                "content": structured_content
            })
        else:
            print(f"  -> No main content found, skipping.")

    with open(out_filename, 'w', encoding='utf-8') as f:
        json.dump(parsed_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nParsing complete. Structured data saved to {out_filename}")

if __name__ == "__main__":
    main()