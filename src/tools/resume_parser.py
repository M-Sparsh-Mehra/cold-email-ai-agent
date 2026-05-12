"""resume_parser.py - A tool to extract and structure information from PDF resumes using LLMs."""

import ollama
import json
import logging
from pypdf import PdfReader
import yaml
import os

def get_profile_data(config_path="configs/profile.yaml"):
        """
        Retrieves the extracted resume data from the local YAML engram.
        Used by the Skill-Gap engine to evaluate the candidate against job targets.
        """
        if not os.path.exists(config_path):
            # Fallback if the pipeline runs before a resume is uploaded
            return {"skills": "System Error: No profile.yaml found. Initiate parse sequence first."}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                profile = yaml.safe_load(file)
                return profile if profile else {"skills": "Profile YAML is empty."}
        except yaml.YAMLError as exc:
            print(f"[!] Critical Error reading profile engram: {exc}")
            return {"skills": f"Parsing Error: {exc}"}

def parse_pdf_to_yaml(pdf_path, output_yaml="configs/profile.yaml"):
    """
    Extracts raw text from the PDF, passes it to the local LLM to format 
    into a structured JSON engram, and saves it to YAML.
    """
    try:
        #Strip the text from the PDF
        reader = PdfReader(pdf_path)
        raw_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                raw_text += text + "\n"

        #Prompt llama3.2 to extract the structured vectors
        prompt = f"""
        [SYSTEM] Extract core professional data from this resume. 
        Return ONLY a valid JSON object. No markdown, no pre-text, no post-text.
        Do NOT infer or guess any information.

        [KNOWN FACTS (VERIFIED)]
        - current_institution: IIT Delhi
        - github_profile: https://github.com/M-Sparsh-Mehra
        - linkedin_profile: https://www.linkedin.com/in/m-sparsh-mehra-b100b0225
        - proof_of_work:  AQI predictor dashboard -- https://urban-air-quality-index-predictor-m-sparsh-mehra.streamlit.app/


        [INSTRUCTIONS]
        Never override resume content.
        
        Required Schema (take known facts as ground truth and do not override):
        {{
            "name": "Candidate Name",
            "skills": ["Skill1", "Skill2", "Skill3"],
            "education": ["Degree1", "Degree2"],
            "current_institution": "FROM KNWON FACTS",
            "projects": ["Project1", "Project2"],
            "github_profile": ["from known facts"],
            "linkedin_profile": ["from knwown facts"],
            "proof_of_work": ["from known facts"],
            "experience_summary": "A punchy 1-sentence summary"
        }}

        [RESUME TEXT]
        {raw_text[:4000]} 
        """
        
        #init the local inference
        response = ollama.generate(model="llama3.2", prompt=prompt)
        response_text = response['response'].strip()

        # Clean the output in case Ollama wraps it in markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].strip()

        # 4. Parse the LLM output into a dictionary
        parsed_data = json.loads(response_text)
        parsed_data["status"] = "Vector extraction complete"

        # 5. Write the engram to configs/profile.yaml
        os.makedirs(os.path.dirname(output_yaml), exist_ok=True)
        with open(output_yaml, 'w', encoding='utf-8') as f:
            yaml.dump(parsed_data, f, default_flow_style=False, sort_keys=False)

        return parsed_data

    except json.JSONDecodeError as e:
        print(f"[!] LLM failed to return valid JSON: {response_text}")
        raise Exception("LLM Formatting Error. Could not parse JSON.")
    except Exception as e:
        print(f"[!] Parsing Error: {str(e)}")
        raise Exception(f"Extraction failed: {str(e)}")


class ResumeParser:
    def __init__(self, model_name="llama3.2"):
        self.model = model_name

    def extract_text_from_pdf(self, pdf_path):
        """Extracts raw text from a PDF file."""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            logging.error(f"Failed to read PDF: {e}")
            return None


    def parse_resume_to_json(self, pdf_path):
        """Converts raw resume text into structured profile JSON using LLM."""
        raw_text = self.extract_text_from_pdf(pdf_path)
        if not raw_text:
            return None

        logging.info("🧠 Analyzing resume with Llama 3.2...")

        prompt = f"""
        You are an expert career consultant. Analyze the following resume text and convert it into a structured JSON profile.
        
        STRICT RULES:
        1. Distinguish between a 'Master's Thesis' and other projects.
        2. Identify the current role or most recent experience or projects.
        3. Extract core technical competencies (skills).
        4. Maintain a professional, analytically driven tone.
        5. Use the best projects to highlight the candidate's expertise, especially those relevant to data science and machine learning.

        RESUME TEXT:
        {raw_text[:6000]}

        Return ONLY a JSON object with these keys:
        - 'name': (String)
        - 'education': {{ 'degree': (String), 'institution': (String), 'thesis_project': (String) }}
        - 'current_role': {{ 'title': (String), 'company': (String), 'responsibilities': (String) }}
        - 'other_key_projects': [List of Strings]
        - 'core_competencies': [List of Strings]
        - 'tone_preference': "Professional, concise, and analytically driven."
        """

        try:
            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                format='json'
            )
            return json.loads(response['message']['content'])
        except Exception as e:
            logging.error(f"LLM Parsing failed: {e}")
            return None