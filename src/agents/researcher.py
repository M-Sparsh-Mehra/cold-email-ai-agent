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
        logging.info(f"Agent 1: Starting research on {company_name}...")
        
        #targeted search query
        # The 'site:linkedin.com/in/' forces it to only look at user profiles.
        # The quotes around the company name force an exact match.
        query = f'site:linkedin.com/in/ "{company_name}" ("talent acquisition" OR "human resources" OR "recruiter" OR "HR" OR "people operations" OR "hiring" OR "Talent Acquisition" OR "Recruiting")'
        search_results = self.search_tool.search_duckduckgo(query, max_results=2)
        
        if not search_results:
            return "Unknown", "Unknown", "No search results found."
            
        #scrape the top result using our Jina Reader tool
        target_url = search_results[0]['url']
        target_snippet = search_results[0].get('snippet', 'No snippet available.')
        logging.info(f"Scraping top lead: {target_url}")
        scraped_content = self.search_tool.fetch_page_content(target_url)
        
        # Read the prompt template from the file
        with open("prompts/researcher_prompt.txt", "r", encoding="utf-8") as f:
            prompt_template = f.read()
            
        # Inject the dynamic variables using .format()
        prompt = prompt_template.format(
            company_name=company_name, 
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