"""reads the configs, initializes the database, and passes the baton between Agent 1 and Agent 2."""

import logging
import time
from src.db_manager import DatabaseManager
from src.agents.researcher import ResearcherAgent
from src.agents.writer import WriterAgent
from src.utils import load_yaml

# sets up logging to track the terminal output cleanly
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')

def main():
    print("\n🚀 Starting Local AI Job Agent Pipeline...\n")
    
    # init DB and Configs
    db = DatabaseManager()
    settings = load_yaml("configs/settings.yaml")
    targets = load_yaml("configs/targets.yaml")
    
    llm_model = settings.get('llm', {}).get('model', 'phi3')
    
    #add targets from yml to SQLite Database (Ignores duplicates)
    companies = targets.get('companies', [])
    for company in companies:
        db.add_target(company)
        
    #fetches companies that haven't been processed yet
    pending_companies = db.get_pending_companies()
    if not pending_companies:
        print("✅ No new companies to process. Add more to configs/targets.yaml!")
        return

    print(f"📌 Found {len(pending_companies)} pending companies in the queue.\n")

    #init the Agents
    researcher = ResearcherAgent(model_name=llm_model)
    writer = WriterAgent(model_name=llm_model)

    #execution
    for company in pending_companies:
        print(f"--- Processing: {company} ---")
        
        #Research 
        hr_name, hr_email, notes = researcher.research_company(company)
        db.update_research(company, hr_name, hr_email, notes)
        
        #to give the system a brief pause to prevent hitting rate limits on DuckDuckGo/Jina
        time.sleep(2) 
        
        #drafting
        draft = writer.draft_email(company, hr_name, notes)
        db.update_draft(company, draft)
        
        print(f"✅ Finished {company}. Saved to Database.\n")
        time.sleep(2)

    #final status
    metrics = db.get_dashboard_metrics()
    print("📊 Pipeline Complete! Current Database Metrics:")
    for status, count in metrics.items():
        print(f"  - {status}: {count}")
    
    print("\n💡 You can now query your database to review the drafts!")

if __name__ == "__main__":
    main()