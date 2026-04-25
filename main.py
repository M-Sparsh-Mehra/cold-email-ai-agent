"""Reads the configs, initializes the database, and passes the baton between Agent 1, Agent 2, and Gmail."""

import logging
import time
from src.db_manager import DatabaseManager
from src.tools.gmail_api import GmailDraftCreator  
from src.agents.researcher import ResearcherAgent
from src.agents.writer import WriterAgent
from src.utils import load_yaml

# Sets up logging to track the terminal output cleanly
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')

def main():
    print("\n🚀 Starting Local AI Job Agent Pipeline...\n")
    
    # init DB and Configs
    db = DatabaseManager()
    settings = load_yaml("configs/settings.yaml")
    targets = load_yaml("configs/targets.yaml")
    
    llm_model = settings.get('llm', {}).get('model', 'llama3.2') # Assuming you switched to the faster model!
    
    # Add targets from yaml to SQLite Database (Ignores duplicates)
    companies = targets.get('companies', [])
    for target in companies:
        # Handle both string and dict formats for targets.yaml to allow for optional location field
        if isinstance(target, dict):
            company_name = target['name']
            location = target.get('location', '')
        else:
            company_name = target
            location = ''
            
        # We append the location to the name for the DB so it stays unique
        db_target_name = f"{company_name} ({location})" if location else company_name
        db.add_target(db_target_name)
        
    # Fetches companies that haven't been processed yet
    pending_companies = db.get_pending_companies()
    if not pending_companies:
        print("✅ No new companies to process. Add more to configs/targets.yaml!")
        return

    print(f"📌 Found {len(pending_companies)} pending companies in the queue.\n")

    # Init the Agents
    researcher = ResearcherAgent(model_name=llm_model)
    writer = WriterAgent(model_name=llm_model)

    # Init Gmail API handler
    print("🔑 Checking Google Credentials... (A browser window may open)")
    gmail = GmailDraftCreator()

    # Execution loop
    for company in pending_companies:
        print(f"--- Processing: {company} ---")
        
        # Research Phase
        hr_name, hr_email, notes = researcher.research_company(company)
        db.update_research(company, hr_name, hr_email, notes)
        
        # Pause to prevent hitting rate limits on DuckDuckGo/Jina
        time.sleep(2) 
        
        # Drafting Phase
        draft = writer.draft_email(company, hr_name, notes)
        db.update_draft(company, draft)
        
        # Action Phase: Push to Gmail
        if "Unknown" not in hr_email:
            print(f"📤 Pushing draft to Gmail for {hr_email}...")
            success = gmail.create_draft(to_email=hr_email, raw_draft_text=draft)
            if success:
                print("✅ Successfully saved to Gmail Drafts.")
            else:
                print("❌ Failed to save to Gmail.")
        else:
            print("⚠️ HR Email is Unknown. Skipping Gmail push (Draft saved in local DB only).")
        
        print(f"🏁 Finished {company}.\n")
        time.sleep(2)

    # Final status
    metrics = db.get_dashboard_metrics()
    print("📊 Pipeline Complete! Current Database Metrics:")
    for status, count in metrics.items():
        print(f"  - {status}: {count}")
    
    print("\n💡 Check your actual Gmail Drafts folder!")

if __name__ == "__main__":
    main()