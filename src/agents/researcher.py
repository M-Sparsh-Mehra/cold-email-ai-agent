"""we will use the ollama Python library's built-in JSON Mode. 
This forces the model to output strict, predictable JSON that our database can read perfectly."""

import ollama
import json
import logging
from src.tools.search import WebSearcher

class ResearcherAgent:
    def __init__(self, model_name="phi3"):
        self.model = model_name
        self.search_tool = WebSearcher()

    def research_company(self, company_name):
        logging.info(f"🕵️‍♂️ Agent 1: Starting research on {company_name}...")
        
        #names
        actual_name = company_name
        location_dork = ""
        if "(" in company_name and ")" in company_name:
            actual_name = company_name.split(" (")[0].strip() # This strips out "(Delhi, India)"
            loc = company_name.split(" (")[1].replace(")", "")
            location_dork = f'"{loc}"'

        #new dork
        query_1 = f'site:linkedin.com/in/ "{actual_name}" {location_dork} ("talent acquisition" OR "human resources" OR "recruiter")'
        search_results = self.search_tool.search_duckduckgo(query_1, max_results=2)
        
        if not search_results:
            return "Unknown", "Unknown", "No search results found."
            
        #URL, Snippet, AND the Title
        target_url = search_results[0]['url']
        target_snippet = search_results[0].get('snippet', 'No snippet.')
        target_title = search_results[0].get('title', 'No title.') # <-- Grab the title!
        
        logging.info(f"Scraping top lead: {target_url}")
        scraped_content = self.search_tool.fetch_page_content(target_url)
        
        with open("prompts/researcher_prompt.txt", "r", encoding="utf-8") as f:
            prompt_template = f.read()
            
        #clean name and the title
        prompt = prompt_template.format(
            company_name=actual_name,      # Uses the clean name 
            title=target_title,            # Passes the search title
            snippet=target_snippet,
            scraped_content=scraped_content[:4000]
        )          
        
        logging.info(f"Asking {self.model} to analyze text and extract JSON...")
        try:
            #enforces format='json' so the small model doesn't hallucinate conversational text
            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                format='json' 
            )
            
            #parses the LLM's output directly into Python variables
            result = json.loads(response['message']['content'])
            hr_name = result.get('hr_name', 'Unknown')
            hr_email = result.get('hr_email', 'Unknown')
            notes = result.get('notes', f"Found via {target_url}")
            
            logging.info(f"✅ Extraction Complete: {hr_name} | {hr_email}")
            return hr_name, hr_email, notes
            
        except json.JSONDecodeError:
            logging.error("The LLM failed to output valid JSON.")
            return "Unknown", "Unknown", "LLM formatting error."
        except Exception as e:
            logging.error(f"LLM extraction failed: {e}")
            return "Unknown", "Unknown", f"Error: {e}"

#local test block
if __name__ == "__main__":
    agent = ResearcherAgent(model_name="phi3")
    name, email, note = agent.research_company("OneBit AI")
    print(f"\nResults:\nName: {name}\nEmail: {email}\nNotes: {note}")