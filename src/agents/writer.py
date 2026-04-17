"""This agent takes the raw research and my dynamic profile.yaml to craft a highly targeted cold email.
We will use Ollama's JSON mode again to ensure the LLM separates the email subject line from the email body perfectly."""

import ollama
import json
import logging
from src.utils import load_yaml

class WriterAgent:
    def __init__(self, model_name="phi3", profile_path="configs/profile.yaml"):
        self.model = model_name
        self.profile = load_yaml(profile_path)
        
    def draft_email(self, company_name, hr_name, research_notes):
        logging.info(f"✍️ Agent 2: Drafting email for {company_name} (Contact: {hr_name})...")
        
        #yaml profile dictionary into a readable string for the LLM
        profile_context = json.dumps(self.profile, indent=2)
        
        # Read the prompt template from the file
        with open("prompts/writer_prompt.txt", "r", encoding="utf-8") as f:
            prompt_template = f.read()
            
        # Inject the dynamic variables
        prompt = prompt_template.format(
            company_name=company_name,
            hr_name=hr_name,
            research_notes=research_notes,
            profile_context=profile_context
        )
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                format='json'
            )
            
            result = json.loads(response['message']['content'])
            subject = result.get('subject', f"Application inquiry for {company_name}")
            body = result.get('body', "Failed to generate body.")
            
            #combines subject and body into one clean string for our database
            final_draft = f"SUBJECT: {subject}\n\n{body}"
            logging.info(f"✅ Draft complete for {company_name}")
            return final_draft
            
        except Exception as e:
            logging.error(f"Failed to draft email for {company_name}: {e}")
            return "Error generating draft."