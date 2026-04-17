"""Web search and scraping module that uses DuckDuckGo for searching 
and Jina Reader for scraping web content. 
This module is designed to be used by the Researcher Agent to gather information about target companies and their HR contacts."""

import requests
from ddgs import DDGS
from itertools import islice
import logging

# basic logging setup we'll debug later
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class WebSearcher:
    def __init__(self):
        self.ddgs = DDGS()
        self.jina_base_url = "https://r.jina.ai/"

    def search_duckduckgo(self, query, max_results=3):
        logging.info(f"Searching web for: {query}")
        results = []
        try:
            # The new library syntax
            search_results = self.ddgs.text(query)
            
            for res in islice(search_results, max_results):
                results.append({
                    "title": res.get("title", ""),
                    "url": res.get("href", ""),
                    "snippet": res.get("body", "")
                })
            
            if not results:
                logging.warning("Search returned zero results.")
            return results
            
        except Exception as e:
            logging.error(f"Search failed: {e}")
            return []
    def fetch_page_content(self, url):
        """
        uses Jina Reader to convert any web page into clean, LLM-readable Markdown.
        """
        logging.info(f"Scraping content from: {url}")
        jina_url = f"{self.jina_base_url}{url}"
        
        headers = {
            "Accept": "application/json" 
        }
        
        try:
            response = requests.get(jina_url, headers=headers, timeout=100)
            response.raise_for_status()
            
            # Jina returns a JSON object containing the markdown text
            data = response.json()
            markdown_content = data.get("data", {}).get("content", "")
            
            #if the page is massive, we truncate it to save context window space for our small LLM
            if len(markdown_content) > 8000:
                markdown_content = markdown_content[:8000] + "\n...[Content Truncated]"
                
            return markdown_content
            
        except Exception as e:
            logging.error(f"Failed to fetch content from {url}: {e}")
            return f"Error fetching content: {e}"

#test block
if __name__ == "__main__":
    searcher = WebSearcher()
    # Test Search
    urls = searcher.search_duckduckgo("OneBit AI startup", max_results=1)
    if urls:
        print(f"Found URL: {urls[0]['url']}")
        # Test Scrape
        content = searcher.fetch_page_content(urls[0]['url'])
        print("\n--- Extracted Content (First 500 chars) ---")
        print(content[:500])