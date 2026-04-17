''' database manager for handling all interactions with the SQLite database. 
This includes creating tables, inserting new records, 
and updating existing records based on the actions of the Researcher and Writer agents'''

import sqlite3
import datetime
import os

class DatabaseManager:
    def __init__(self, db_path="database.db"):
        self.db_path = db_path
        self.setup_db()

    def _get_connection(self):
        # Creates a new connection for each transaction to avoid threading/locking issues
        return sqlite3.connect(self.db_path)

    def setup_db(self):
        """inits the db schema if doesn't exist."""
        query = """
        CREATE TABLE IF NOT EXISTS outreach_pipeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE NOT NULL,
            hr_name TEXT,
            hr_email TEXT,
            research_notes TEXT,
            email_draft TEXT,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            
    def add_target(self, company_name):
        """Adds a new company to the database if it doesn't already exist."""
        query = """
        INSERT OR IGNORE INTO outreach_pipeline (company_name, status)
        VALUES (?, 'Pending')
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (company_name,))
            conn.commit()

    def update_research(self, company_name, hr_name, hr_email, research_notes):
        """Updates the db with result frm the researcher agent."""
        query = """
        UPDATE outreach_pipeline 
        SET hr_name = ?, hr_email = ?, research_notes = ?, status = 'Researched', updated_at = CURRENT_TIMESTAMP
        WHERE company_name = ?
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (hr_name, hr_email, research_notes, company_name))
            conn.commit()

    def update_draft(self, company_name, email_draft):
        """updates the db with the draft frm writer agent."""
        query = """
        UPDATE outreach_pipeline 
        SET email_draft = ?, status = 'Draft Created', updated_at = CURRENT_TIMESTAMP
        WHERE company_name = ?
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (email_draft, company_name))
            conn.commit()

    def get_pending_companies(self):
        """fetches companies that haven't been researched yet."""
        query = "SELECT company_name FROM outreach_pipeline WHERE status = 'Pending'"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [row[0] for row in cursor.fetchall()]

    def get_dashboard_metrics(self):
        """for UI to quickly grab pipeline stats."""
        query = "SELECT status, COUNT(*) FROM outreach_pipeline GROUP BY status"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return dict(cursor.fetchall())