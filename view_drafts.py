import sqlite3

def view_drafts():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Fetch all completed drafts
    cursor.execute("SELECT company_name, hr_name, email_draft FROM outreach_pipeline WHERE status = 'Draft Created'")
    drafts = cursor.fetchall()
    
    if not drafts:
        print("No drafts found in the database yet.")
        return

    print(f"\n=== Found {len(drafts)} Drafts ===\n")
    for company, hr_name, draft in drafts:
        print(f"🏢 Target: {company} (Contact: {hr_name})")
        print("-" * 40)
        print(draft)
        print("=" * 60 + "\n")

if __name__ == "__main__":
    view_drafts()