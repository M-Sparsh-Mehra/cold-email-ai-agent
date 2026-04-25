"""This agent takes the raw research and my dynamic profile.yaml to craft a highly targeted cold email.
We will use Ollama's JSON mode again to ensure the LLM separates the email subject line from the email body perfectly."""

import ollama
import json
import logging
from src.utils import load_yaml

class WriterAgent:
    def __init__(self, model_name="llama3.2", profile_path="configs/profile.yaml"):
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
            
            content = response['message']['content'].strip()
            
            # Clean up potential Markdown backticks from the LLM
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Single parse into a dictionary
            data = json.loads(content)
            
            logging.info(f"✅ Draft complete for {company_name}") 
            
            # Use .get() with smart fallbacks
            subject = data.get('subject', f"Data Science Inquiry - {company_name}")
            body = data.get('body', "I am writing to express my interest in joining your team.")
            
            # Combine for the DB and Gmail
            return f"SUBJECT: {subject}\n\n{body}"
        
        except Exception as e:
            logging.error(f"Failed to draft email for {company_name}: {e}")
            return "Error generating draft."