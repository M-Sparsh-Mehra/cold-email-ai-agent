''' database manager for handling all interactions with the SQLite database. 
This includes creating tables, inserting new records, 
and updating existing records based on the actions of the Researcher and Writer agents'''

import sqlite3
import datetime

class DatabaseManager:
    def __init__(self, db_path="database.db"):
        self.db_path = db_path
        self._create_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        """Initializes the updated companies table with Location routing."""
        query = """
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE NOT NULL,
            location TEXT DEFAULT 'Unknown',
            hr_name TEXT DEFAULT 'Unknown',
            hr_email TEXT DEFAULT 'Unknown',
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'Pending',
            draft TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        with self._get_connection() as conn:
            conn.execute(query)
            conn.commit()

    def update_status(self, company_name, status):
        """Allows agents to stream granular status updates to the UI."""
        query = "UPDATE companies SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE company_name = ?"
        with self._get_connection() as conn:
            conn.execute(query, (status, company_name))
            conn.commit()        

    def add_target(self, company_name, location):
        """Adds a new company to the database with location data."""
        query = "INSERT OR IGNORE INTO companies (company_name, location, status) VALUES (?, ?, 'Pending')"
        with self._get_connection() as conn:
            conn.execute(query, (company_name, location))
            conn.commit()

    def get_all_leads(self):
        """Fetches all leads including location for the UI feed."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT id, company_name, location, hr_name, hr_email, status FROM companies ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

    def update_research(self, company_name, hr_name, hr_email, notes):
        query = """
        UPDATE companies 
        SET hr_name = ?, hr_email = ?, notes = ?, status = 'Researched', updated_at = CURRENT_TIMESTAMP
        WHERE company_name = ?
        """
        with self._get_connection() as conn:
            conn.execute(query, (hr_name, hr_email, notes, company_name))
            conn.commit()

    def update_draft(self, company_name, draft):
        query = """
        UPDATE companies 
        SET draft = ?, status = 'Draft Created', updated_at = CURRENT_TIMESTAMP
        WHERE company_name = ?
        """
        with self._get_connection() as conn:
            conn.execute(query, (draft, company_name))
            conn.commit()

    def get_pending_companies(self):
        """Fetches pending companies ALONG WITH their location for the Researcher Agent."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT company_name, location FROM companies WHERE status = 'Pending'")
            return [dict(row) for row in cursor.fetchall()]
        
    def get_dashboard_metrics(self):
        query = "SELECT status, COUNT(*) FROM companies GROUP BY status"
        with self._get_connection() as conn:
            cursor = conn.execute(query)
            return dict(cursor.fetchall())

    
    def get_company_by_id(self, company_id):
        """Fetches a single company for the Skill-Gap engine."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        
    def delete_target(self, target_id):
        """Scrub a target from the database using its ID."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM companies WHERE id = ?", (target_id,))
            conn.commit()    