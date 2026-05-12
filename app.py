from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from src.tools.resume_parser import ResumeParser
from src.tools.resume_parser import get_profile_data, parse_pdf_to_yaml
from src.agents.researcher import ResearcherAgent
from src.agents.writer import WriterAgent
from src.tools.gmail_api import GmailDraftCreator
from src.tools.resume_parser import get_profile_data
from src.db_manager import DatabaseManager 
import asyncio
from pydantic import BaseModel
from fastapi import BackgroundTasks
import yaml
import os
from pydantic import BaseModel
import shutil
from fastapi import Form
import ollama

app = FastAPI()
templates = Jinja2Templates(directory="templates")
parser = ResumeParser(model_name="llama3.2")
db = DatabaseManager()



class TargetRequest(BaseModel):
    name: str


@app.on_event("startup")
async def startup_event():
    """Rehydrates the SQLite database from the offline YAML engram on boot."""
    filepath = "configs/targets.yaml"
    if not os.path.exists(filepath):
        return
        
    print("[*] Initiating core sequence: Rehydrating DB from YAML engram...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'company_name' in item:
                        # Push the offline data back into the live SQLite feed
                        db.add_target(item['company_name'], item.get('location', 'Unknown'))
                        
        print("[+] DB Rehydration complete. All targets synchronized.")
    except Exception as e:
        print(f"[!] Rehydration Failure: {e}")    

async def execute_agentic_pipeline():
    """The master background sequence for Researcher and Writer agents."""
    pending_targets = db.get_pending_companies()
    
    if not pending_targets:
        return
        
    # Instantiate the agents
    researcher = ResearcherAgent(model_name="llama3.2")
    writer = WriterAgent(model_name="llama3.2")  # <-- 2. Arm the Writer
    
    for target in pending_targets:
        company_name = target['company_name']
        location = target['location']
        
        try:
            # --- PHASE 1: RESEARCHER ---
            db.update_status(company_name, "[1/2] Deploying LinkedIn Scraper...")
            search_string = f"{company_name} ({location})"
            
            hr_name, hr_email, notes = researcher.research_company(search_string)
            db.update_research(company_name, hr_name, hr_email, notes)
            
            # --- PHASE 2: WRITER ---
            db.update_status(company_name, "[2/2] llama3.2 Drafting Outreach...")
            
            # THE REAL EXECUTION
            final_draft = writer.draft_email(company_name, hr_name, notes)
            
            db.update_draft(company_name, final_draft)
            
        except Exception as e:
            # Pushes the crash log directly to the Live Mission Feed UI
            db.update_status(company_name, f"FAILED: {str(e)[:25]}")


@app.post("/run-pipeline")
async def run_pipeline(background_tasks: BackgroundTasks):
    # Prevent infinite clicking: Check if there's actual work to do
    pending_targets = db.get_pending_companies()
    if not pending_targets:
        return JSONResponse(status_code=400, content={"error": "No pending targets."})
        
    # Hand the heavy lifting off to the background so the UI doesn't freeze
    background_tasks.add_task(execute_agentic_pipeline)
    return {"status": "Agents Deployed"}

# Add this new route so the frontend can spy on the database:
@app.get("/api/leads")
async def get_api_leads():
    """Provides a live JSON feed of the database for the UI radar."""
    return db.get_all_leads()



@app.post("/add_target")
async def add_target(target: TargetRequest):
    # This calls your existing DB method
    db.add_target(target.name)
    return {"status": "success"}

@app.post("/run_pipeline")
async def trigger_pipeline():
    # In a real app, this would run in a background thread
    # For now, we'll just acknowledge the command
    print("🚀 Pipeline Execution Triggered via UI")
    return {"status": "initiated"}


def sync_to_yaml(company_name, location, filepath="configs/targets.yaml"):
    """Nuke-proof YAML sync that survives corrupted files."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    data = []
    
    # 1. Safely attempt to read the existing file
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
                # STRICT check: Only accept it if it's a list, and only keep dictionaries inside it
                if isinstance(content, list):
                    data = [item for item in content if isinstance(item, dict)]
        except Exception as e:
            print(f"[*] Engram corrupted, overriding with fresh data: {e}")
            data = [] # Fallback to empty list
            
    # 2. Append the new target
    try:
        if not any(d.get('company_name') == company_name for d in data):
            data.append({
                "company_name": company_name,
                "location": location,
                "status": "Pending"
            })
            
        # 3. Write cleanly back to the file
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            
    except Exception as e:
        print(f"[!] Critical Write Error: {e}")
        raise e
    

def remove_from_yaml(company_name, filepath="configs/targets.yaml"):
    """Scrubs a terminated target from the offline YAML engram."""
    if not os.path.exists(filepath):
        return
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)
            
        if isinstance(content, list):
            # Rebuild the list, keeping everything EXCEPT the target company
            data = [
                item for item in content 
                if isinstance(item, dict) and item.get('company_name') != company_name
            ]
            
            # Overwrite the file with the scrubbed list
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
                
    except Exception as e:
        print(f"[!] Engram Scrub Error: {e}")


@app.post("/add-target")
async def add_new_target(company_name: str = Form(...), location: str = Form(...)):
    try:
        # 1. Save to SQLite
        db.add_target(company_name, location)
        
        # 2. Sync to local engram
        filepath = "configs/targets.yaml"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = []
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f) or []
                
        # Prevent duplicates in the YAML
        if not any(d.get('company_name') == company_name for d in data):
            data.append({
                "company_name": company_name,
                "location": location,
                "status": "Pending"
            })
            with open(filepath, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
                
        return {"status": "Target Locked"}
    except Exception as e:
        print(f"[!] Target Lock Failure: {str(e)}") # This will print the exact crash reason to your terminal
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/delete-target/{target_id}")
async def remove_target(target_id: int):
    try:
        # 1. Identify the target BEFORE we delete it from the database
        company = db.get_company_by_id(target_id)
        if not company:
            return JSONResponse(status_code=404, content={"error": "Target not found in DB."})
            
        company_name = company['company_name']

        # 2. Erase from SQLite DB
        db.delete_target(target_id)
        
        # 3. Erase from the offline YAML engram
        remove_from_yaml(company_name)
        
        return {"status": "Target Completely Terminated"}
    except Exception as e:
        print(f"[!] Termination Protocol Failure: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/skill-gap/{company_id}")
async def analyze_skill_gap(company_id: int):
    company = db.get_company_by_id(company_id) 
    job_description = company['notes']
    
    user_profile = get_profile_data() 
    
    prompt = f"""
    [SYSTEM] Analyze the gap between the Candidate and the Job.
    Candidate Skills: {user_profile['skills']}
    Job Description: {job_description}
    
    Return a JSON with:
    - "match_score": (0-100)
    - "missing_skills": []
    - "bridge_strategy": "How to spin existing Physics/ML experience to fit."
    """
    
    analysis = ollama.generate(model="llama3.2", prompt=prompt)
    return JSONResponse(content=analysis)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # 1. Fetch Metrics
    metrics = db.get_dashboard_metrics()
    
    # 2. Fetch All Processed Leads for the table
    # We need to add a method to db_manager to get all leads
    leads = db.get_all_leads() 
    
    return templates.TemplateResponse(
    request=request,
    name="index.html",
    context={
        "processed": metrics.get('Draft Created', 0),
        "pending": metrics.get('Target Added', 0),
        "leads": leads
    }
)
@app.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    try:
        os.makedirs("src/uploads", exist_ok=True)
        file_path = f"src/uploads/{file.filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # THE REAL DEAL: Run the parser sequence
        real_parsed_data = parse_pdf_to_yaml(file_path)
        
        return {"profile": real_parsed_data}

    except Exception as e:
        return JSONResponse(
            status_code=500, 
            content={"error": str(e)}
        )
    
@app.post("/run-pipeline")
async def run_pipeline():
    try:
        pending_targets = db.get_pending_companies() 
        
        if not pending_targets:
            return {"status": "No targets in queue."}

        for company in pending_targets:
            print(f"[*] Initializing Researcher Agent for: {company}")
            mock_hr_name = "System Auto-Detect"
            mock_email = f"recruitment@{company.lower().replace(' ', '')}.com"
            mock_notes = "Data Scientist / ML Engineer roles detected."
            
            db.update_research(company, mock_hr_name, mock_email, mock_notes)            
        return {"status": "Pipeline execution complete"}
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


class DraftUpdate(BaseModel):
    draft: str

@app.get("/api/draft/{company_id}")
async def get_draft(company_id: int):
    company = db.get_company_by_id(company_id)
    if not company:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return {"company_name": company['company_name'], "draft": company['draft']}

@app.post("/api/push-draft/{company_id}")
async def push_draft_to_gmail(company_id: int, payload: DraftUpdate):
    try:
        company = db.get_company_by_id(company_id)
        
        # 1. Update the DB with any manual edits you made in the modal
        final_draft = payload.draft
        db.update_draft(company['company_name'], final_draft)
        
        # 2. ---> GMAIL API INJECTION <---
        # Initialize the tool. (If token.json is missing, this will pop open a browser window for OAuth)
        print(f"[*] Initiating secure Uplink to Gmail API for {company['hr_email']}...")
        gmail_tool = GmailDraftCreator()
        
        # Push the payload
        success = gmail_tool.create_draft(company['hr_email'], final_draft)
        
        if success:
            # 3. Update status to signify deployment
            db.update_status(company['company_name'], "Deployed to Gmail")
            return {"status": "Deployment Successful"}
        else:
            return JSONResponse(status_code=500, content={"error": "Gmail API failed to create draft."})
            
    except Exception as e:
        print(f"[!] Deployment Failure: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/reject-draft/{company_id}")
async def reject_draft(company_id: int):
    company = db.get_company_by_id(company_id)
    db.update_status(company['company_name'], "Draft Rejected")
    return {"status": "Rejected"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)