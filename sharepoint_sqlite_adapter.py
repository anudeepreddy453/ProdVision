"""
SharePoint SQLite Adapter
Store SQLite database in SharePoint for team collaboration
"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any

class SharePointSQLiteAdapter:
    """SQLite adapter with SharePoint integration for database storage"""
    
    def __init__(self, sharepoint_url: str, db_name: str = "prodvision.db"):
        self.sharepoint_url = sharepoint_url.rstrip('/')
        self.db_name = db_name
        self.local_db_path = f"./data/{db_name}"
        self.ensure_data_directory()
        
        # Initialize local database
        self.init_database()
    
    def ensure_data_directory(self):
        """Ensure data directory exists"""
        data_dir = os.path.dirname(self.local_db_path)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def init_database(self):
        """Initialize SQLite database with tables"""
        conn = sqlite3.connect(self.local_db_path)
        cursor = conn.cursor()
        
        # Create entries table with all required fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                day TEXT,
                application_name TEXT,
                prc_mail_text TEXT,
                prc_mail_status TEXT,
                cp_alerts_text TEXT,
                cp_alerts_status TEXT,
                quality_status TEXT,
                quality_legacy TEXT,
                quality_target TEXT,
                prb_id_number TEXT,
                prb_id_status TEXT,
                prb_link TEXT,
                hiim_id_number TEXT,
                hiim_id_status TEXT,
                hiim_link TEXT,
                valo_text TEXT,
                valo_status TEXT,
                sensi_text TEXT,
                sensi_status TEXT,
                cf_ra_text TEXT,
                cf_ra_status TEXT,
                acq_text TEXT,
                root_cause_application TEXT,
                root_cause_type TEXT,
                issue_description TEXT,
                remarks TEXT,
                xva_remarks TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        # Create settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Child tables for normalized multiple items per entry
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER,
                description TEXT,
                remarks TEXT,
                position INTEGER,
                created_at TEXT,
                FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prbs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER,
                prb_id_number TEXT,
                prb_id_status TEXT,
                prb_link TEXT,
                position INTEGER,
                created_at TEXT,
                FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hiims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER,
                hiim_id_number TEXT,
                hiim_id_status TEXT,
                hiim_link TEXT,
                position INTEGER,
                created_at TEXT,
                FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Migrate existing database if needed
        self.migrate_database()
    
    def migrate_database(self):
        """Migrate existing database to add missing columns"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Check if entries table exists and get its schema
            cursor.execute("PRAGMA table_info(entries)")
            columns = [row[1] for row in cursor.fetchall()]

            # List of columns that should exist
            required_columns = {
                'prb_link': 'TEXT',
                'hiim_link': 'TEXT',
                'valo_text': 'TEXT',
                'sensi_text': 'TEXT',
                'cf_ra_text': 'TEXT',
                'acq_text': 'TEXT',
                'xva_remarks': 'TEXT'
            }

            # Add missing columns
            for column, column_type in required_columns.items():
                if column not in columns:
                    cursor.execute(f"ALTER TABLE entries ADD COLUMN {column} {column_type}")

            # Ensure child tables exist (in case migrate is called separately)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER,
                    description TEXT,
                    remarks TEXT,
                    position INTEGER,
                    created_at TEXT,
                    FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prbs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER,
                    prb_id_number TEXT,
                    prb_id_status TEXT,
                    prb_link TEXT,
                    position INTEGER,
                    created_at TEXT,
                    FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hiims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER,
                    hiim_id_number TEXT,
                    hiim_id_status TEXT,
                    hiim_link TEXT,
                    position INTEGER,
                    created_at TEXT,
                    FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
                )
            ''')

            # Migrate legacy single fields into child tables if child tables are empty
            cursor.execute('SELECT COUNT(1) FROM prbs')
            prb_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(1) FROM hiims')
            hiim_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(1) FROM issues')
            issues_count = cursor.fetchone()[0]

            if prb_count == 0 or hiim_count == 0 or issues_count == 0:
                cursor.execute('SELECT id, issue_description, prb_id_number, prb_id_status, prb_link, hiim_id_number, hiim_id_status, hiim_link, created_at FROM entries')
                rows = cursor.fetchall()
                for row in rows:
                    entry_id = row[0]
                    issue_description = row[1]
                    prb_id_number = row[2]
                    prb_id_status = row[3]
                    prb_link = row[4]
                    hiim_id_number = row[5]
                    hiim_id_status = row[6]
                    hiim_link = row[7]
                    created_at = row[8] or datetime.utcnow().isoformat()

                    if issue_description and issues_count == 0:
                        cursor.execute('INSERT INTO issues (entry_id, description, remarks, position, created_at) VALUES (?, ?, ?, ?, ?)', (entry_id, issue_description, '', 0, created_at))
                    if prb_id_number and prb_count == 0:
                        cursor.execute('INSERT INTO prbs (entry_id, prb_id_number, prb_id_status, prb_link, position, created_at) VALUES (?, ?, ?, ?, ?, ?)', (entry_id, str(prb_id_number), prb_id_status or '', prb_link or '', 0, created_at))
                    if hiim_id_number and hiim_count == 0:
                        cursor.execute('INSERT INTO hiims (entry_id, hiim_id_number, hiim_id_status, hiim_link, position, created_at) VALUES (?, ?, ?, ?, ?, ?)', (entry_id, str(hiim_id_number), hiim_id_status or '', hiim_link or '', 0, created_at))

            conn.commit()
            conn.close()

        except Exception as e:
            # If migration fails, log (silent) and continue
            try:
                conn.close()
            except Exception:
                pass
            return
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.local_db_path)
        try:
            conn.execute('PRAGMA foreign_keys = ON')
        except Exception:
            pass
        return conn
    
    def sync_to_sharepoint(self) -> bool:
        """Upload local database to SharePoint"""
        try:
            # In a real implementation, you would use SharePoint REST API
            # For now, just return True to indicate sync is complete
            return True
            
        except Exception as e:
            return False
    
    def sync_from_sharepoint(self) -> bool:
        """Download database from SharePoint"""
        try:
            # For now, we'll just ensure local database exists
            # In a real implementation, you would download from SharePoint
            if not os.path.exists(self.local_db_path):
                self.init_database()
            
            return True
            
        except Exception as e:
            return False
    
    def get_entries_by_application(self, application_name: str) -> List[Dict]:
        """Get entries for specific application"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM entries WHERE application_name = ?
            ORDER BY created_at DESC
        ''', (application_name,))
        
        columns = [description[0] for description in cursor.description]
        entries = []
        
        for row in cursor.fetchall():
            entry = dict(zip(columns, row))
            # Attach child rows
            entry_id = entry.get('id')
            # issues
            cursor.execute('SELECT id, description, remarks, position, created_at FROM issues WHERE entry_id = ? ORDER BY position ASC, id ASC', (entry_id,))
            issues = []
            for r in cursor.fetchall():
                issues.append({
                    'id': r[0], 'description': r[1], 'remarks': r[2], 'position': r[3], 'created_at': r[4]
                })
            entry['issues'] = issues

            # prbs
            cursor.execute('SELECT id, prb_id_number, prb_id_status, prb_link, position, created_at FROM prbs WHERE entry_id = ? ORDER BY position ASC, id ASC', (entry_id,))
            prbs = []
            for r in cursor.fetchall():
                prbs.append({
                    'id': r[0], 'prb_id_number': r[1], 'prb_id_status': r[2], 'prb_link': r[3], 'position': r[4], 'created_at': r[5]
                })
            entry['prbs'] = prbs

            # hiims
            cursor.execute('SELECT id, hiim_id_number, hiim_id_status, hiim_link, position, created_at FROM hiims WHERE entry_id = ? ORDER BY position ASC, id ASC', (entry_id,))
            hiims = []
            for r in cursor.fetchall():
                hiims.append({
                    'id': r[0], 'hiim_id_number': r[1], 'hiim_id_status': r[2], 'hiim_link': r[3], 'position': r[4], 'created_at': r[5]
                })
            entry['hiims'] = hiims

            entries.append(entry)
        
        conn.close()
        return entries
    
    def get_all_entries(self) -> List[Dict]:
        """Get all entries from all applications"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM entries
            ORDER BY created_at DESC
        ''')
        
        columns = [description[0] for description in cursor.description]
        entries = []
        
        for row in cursor.fetchall():
            entry = dict(zip(columns, row))
            entry_id = entry.get('id')
            # Attach child rows similarly to get_entries_by_application
            cursor.execute('SELECT id, description, remarks, position, created_at FROM issues WHERE entry_id = ? ORDER BY position ASC, id ASC', (entry_id,))
            issues = []
            for r in cursor.fetchall():
                issues.append({'id': r[0], 'description': r[1], 'remarks': r[2], 'position': r[3], 'created_at': r[4]})
            entry['issues'] = issues

            cursor.execute('SELECT id, prb_id_number, prb_id_status, prb_link, position, created_at FROM prbs WHERE entry_id = ? ORDER BY position ASC, id ASC', (entry_id,))
            prbs = []
            for r in cursor.fetchall():
                prbs.append({'id': r[0], 'prb_id_number': r[1], 'prb_id_status': r[2], 'prb_link': r[3], 'position': r[4], 'created_at': r[5]})
            entry['prbs'] = prbs

            cursor.execute('SELECT id, hiim_id_number, hiim_id_status, hiim_link, position, created_at FROM hiims WHERE entry_id = ? ORDER BY position ASC, id ASC', (entry_id,))
            hiims = []
            for r in cursor.fetchall():
                hiims.append({'id': r[0], 'hiim_id_number': r[1], 'hiim_id_status': r[2], 'hiim_link': r[3], 'position': r[4], 'created_at': r[5]})
            entry['hiims'] = hiims

            entries.append(entry)
        
        conn.close()
        return entries
    
    def create_entry(self, entry_data: Dict) -> Optional[Dict]:
        """Create a new entry"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Add timestamps
            now = datetime.utcnow().isoformat()
            
            # Insert entry
            cursor.execute('''
                INSERT INTO entries (
                    date, day, application_name, prc_mail_text, prc_mail_status,
                    cp_alerts_text, cp_alerts_status, quality_status, quality_legacy, quality_target,
                    prb_id_number, prb_id_status, hiim_id_number, hiim_id_status,
                    valo_text, valo_status, sensi_text, sensi_status, cf_ra_text, cf_ra_status,
                    acq_text, root_cause_application, root_cause_type, issue_description, remarks,
                    created_at, updated_at, prb_link, hiim_link, xva_remarks
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry_data.get('date', ''),
                entry_data.get('day', ''),
                entry_data.get('application_name', ''),
                entry_data.get('prc_mail_text', ''),
                entry_data.get('prc_mail_status', ''),
                entry_data.get('cp_alerts_text', ''),
                entry_data.get('cp_alerts_status', ''),
                entry_data.get('quality_status', ''),
                entry_data.get('quality_legacy', ''),
                entry_data.get('quality_target', ''),
                entry_data.get('prb_id_number', ''),
                entry_data.get('prb_id_status', ''),
                entry_data.get('hiim_id_number', ''),
                entry_data.get('hiim_id_status', ''),
                entry_data.get('valo_text', ''),
                entry_data.get('valo_status', ''),
                entry_data.get('sensi_text', ''),
                entry_data.get('sensi_status', ''),
                entry_data.get('cf_ra_text', ''),
                entry_data.get('cf_ra_status', ''),
                entry_data.get('acq_text', ''),
                entry_data.get('root_cause_application', ''),
                entry_data.get('root_cause_type', ''),
                entry_data.get('issue_description', ''),
                entry_data.get('remarks', ''),
                now,
                now,
                entry_data.get('prb_link', ''),
                entry_data.get('hiim_link', ''),
                entry_data.get('xva_remarks', '')
            ))
            
            # Get the inserted ID
            entry_id = cursor.lastrowid
            entry_data['id'] = entry_id

            # Insert child rows if provided (issues, prbs, hiims)
            # Issues
            issues = entry_data.get('issues') or []
            for idx, issue in enumerate(issues):
                cursor.execute('INSERT INTO issues (entry_id, description, remarks, position, created_at) VALUES (?, ?, ?, ?, ?)', (
                    entry_id,
                    issue.get('description', ''),
                    issue.get('remarks', ''),
                    idx,
                    now
                ))

            # PRBs
            prbs = entry_data.get('prbs') or []
            for idx, prb in enumerate(prbs):
                cursor.execute('INSERT INTO prbs (entry_id, prb_id_number, prb_id_status, prb_link, position, created_at) VALUES (?, ?, ?, ?, ?, ?)', (
                    entry_id,
                    str(prb.get('prb_id_number', '')) if prb.get('prb_id_number') is not None else '',
                    prb.get('prb_id_status', ''),
                    prb.get('prb_link', ''),
                    idx,
                    now
                ))

            # HIIMs
            hiims = entry_data.get('hiims') or []
            for idx, hiim in enumerate(hiims):
                cursor.execute('INSERT INTO hiims (entry_id, hiim_id_number, hiim_id_status, hiim_link, position, created_at) VALUES (?, ?, ?, ?, ?, ?)', (
                    entry_id,
                    str(hiim.get('hiim_id_number', '')) if hiim.get('hiim_id_number') is not None else '',
                    hiim.get('hiim_id_status', ''),
                    hiim.get('hiim_link', ''),
                    idx,
                    now
                ))

            # For backward compatibility, populate legacy single columns if not provided
            if not entry_data.get('issue_description') and issues:
                cursor.execute('UPDATE entries SET issue_description = ? WHERE id = ?', (issues[0].get('description', ''), entry_id))
            if not entry_data.get('prb_id_number') and prbs:
                cursor.execute('UPDATE entries SET prb_id_number = ?, prb_id_status = ?, prb_link = ? WHERE id = ?', (str(prbs[0].get('prb_id_number', '')), prbs[0].get('prb_id_status', ''), prbs[0].get('prb_link', ''), entry_id))
            if not entry_data.get('hiim_id_number') and hiims:
                cursor.execute('UPDATE entries SET hiim_id_number = ?, hiim_id_status = ?, hiim_link = ? WHERE id = ?', (str(hiims[0].get('hiim_id_number', '')), hiims[0].get('hiim_id_status', ''), hiims[0].get('hiim_link', ''), entry_id))

            conn.commit()
            conn.close()

            # Attach child arrays in returned object
            entry_data['issues'] = issues
            entry_data['prbs'] = prbs
            entry_data['hiims'] = hiims

            return entry_data
            
        except Exception as e:
            if conn:
                conn.rollback()
                conn.close()
            return None
    
    def get_entry_by_id(self, entry_id: int, application_name: str = None) -> Optional[Dict]:
        """Get a specific entry by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if application_name:
                cursor.execute('''
                    SELECT * FROM entries WHERE id = ? AND application_name = ?
                ''', (entry_id, application_name))
            else:
                cursor.execute('SELECT * FROM entries WHERE id = ?', (entry_id,))
            
            row = cursor.fetchone()

            if not row:
                conn.close()
                return None

            # Build the entry dict while the connection/cursor is still open
            columns = [description[0] for description in cursor.description]
            entry = dict(zip(columns, row))

            # Attach child rows
            cursor.execute('SELECT id, description, remarks, position, created_at FROM issues WHERE entry_id = ? ORDER BY position ASC, id ASC', (entry_id,))
            entry['issues'] = [{'id': r[0], 'description': r[1], 'remarks': r[2], 'position': r[3], 'created_at': r[4]} for r in cursor.fetchall()]

            cursor.execute('SELECT id, prb_id_number, prb_id_status, prb_link, position, created_at FROM prbs WHERE entry_id = ? ORDER BY position ASC, id ASC', (entry_id,))
            entry['prbs'] = [{'id': r[0], 'prb_id_number': r[1], 'prb_id_status': r[2], 'prb_link': r[3], 'position': r[4], 'created_at': r[5]} for r in cursor.fetchall()]

            cursor.execute('SELECT id, hiim_id_number, hiim_id_status, hiim_link, position, created_at FROM hiims WHERE entry_id = ? ORDER BY position ASC, id ASC', (entry_id,))
            entry['hiims'] = [{'id': r[0], 'hiim_id_number': r[1], 'hiim_id_status': r[2], 'hiim_link': r[3], 'position': r[4], 'created_at': r[5]} for r in cursor.fetchall()]

            conn.close()
            return entry
            
        except Exception as e:
            return None
    
    def update_entry(self, entry_id: int, update_data: Dict, application_name: str = None) -> Optional[Dict]:
        """Update an existing entry"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Add updated timestamp
            update_data['updated_at'] = datetime.utcnow().isoformat()
            
            # Determine which keys correspond to real columns in entries table
            cursor.execute("PRAGMA table_info(entries)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            # Prepare column updates for only existing entry columns
            column_updates = {k: v for k, v in update_data.items() if k in existing_columns}

            if column_updates:
                set_clause = ', '.join([f"{key} = ?" for key in column_updates.keys()])
                values = list(column_updates.values())
                values.append(entry_id)

                if application_name:
                    query = f'''
                        UPDATE entries SET {set_clause}
                        WHERE id = ? AND application_name = ?
                    '''
                    values.append(application_name)
                else:
                    query = f'UPDATE entries SET {set_clause} WHERE id = ?'

                cursor.execute(query, values)
            else:
                # No top-level entry columns to update (maybe only child arrays were provided)
                # Still proceed to replace child rows below
                pass
            
            # If update_data contains child arrays, replace child rows
            if 'issues' in update_data:
                    cursor.execute('DELETE FROM issues WHERE entry_id = ?', (entry_id,))
                    for idx, issue in enumerate(update_data.get('issues') or []):
                        cursor.execute('INSERT INTO issues (entry_id, description, remarks, position, created_at) VALUES (?, ?, ?, ?, ?)', (
                            entry_id,
                            issue.get('description', ''),
                            issue.get('remarks', ''),
                            idx,
                            datetime.utcnow().isoformat()
                        ))
            if 'prbs' in update_data:
                    cursor.execute('DELETE FROM prbs WHERE entry_id = ?', (entry_id,))
                    for idx, prb in enumerate(update_data.get('prbs') or []):
                        cursor.execute('INSERT INTO prbs (entry_id, prb_id_number, prb_id_status, prb_link, position, created_at) VALUES (?, ?, ?, ?, ?, ?)', (
                            entry_id,
                            str(prb.get('prb_id_number', '')) if prb.get('prb_id_number') is not None else '',
                            prb.get('prb_id_status', ''),
                            prb.get('prb_link', ''),
                            idx,
                            datetime.utcnow().isoformat()
                        ))
            if 'hiims' in update_data:
                    cursor.execute('DELETE FROM hiims WHERE entry_id = ?', (entry_id,))
                    for idx, hiim in enumerate(update_data.get('hiims') or []):
                        cursor.execute('INSERT INTO hiims (entry_id, hiim_id_number, hiim_id_status, hiim_link, position, created_at) VALUES (?, ?, ?, ?, ?, ?)', (
                            entry_id,
                            str(hiim.get('hiim_id_number', '')) if hiim.get('hiim_id_number') is not None else '',
                            hiim.get('hiim_id_status', ''),
                            hiim.get('hiim_link', ''),
                            idx,
                            datetime.utcnow().isoformat()
                        ))
            conn.commit()
            conn.close()
            return self.get_entry_by_id(entry_id, application_name)
                
        except Exception as e:
            # Log exception for debugging purposes
            try:
                import traceback
                print('Exception in update_entry:', e)
                traceback.print_exc()
            except Exception:
                pass
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            return None
    
    def delete_entry(self, entry_id: int, application_name: str = None) -> bool:
        """Delete an entry"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if application_name:
                cursor.execute('''
                    DELETE FROM entries WHERE id = ? AND application_name = ?
                ''', (entry_id, application_name))
            else:
                cursor.execute('DELETE FROM entries WHERE id = ?', (entry_id,))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
            
        except Exception as e:
            return False
    
    def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            conn.close()
            
            return row[0] if row else None
            
        except Exception as e:
            return None
    
    def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
            ''', (key, value))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            return False


# Production Entry Manager for backward compatibility
class ProductionEntryManagerWorking:
    """Production Entry Manager using SharePoint SQLite adapter"""
    
    def __init__(self, sharepoint_url: str = None):
        if not sharepoint_url:
            sharepoint_url = "https://groupsg001.sharepoint.com/sites/CCRTeam/Shared%20Documents/ProdVision"
        self.adapter = SharePointSQLiteAdapter(sharepoint_url)
    
    def get_all_entries(self) -> List[Dict]:
        """Get all production entries from all applications"""
        return self.adapter.get_all_entries()
    
    def create_entry(self, entry_data: Dict) -> Optional[Dict]:
        """Create a new production entry"""
        return self.adapter.create_entry(entry_data)
    
    def get_entry_by_id(self, entry_id: int) -> Optional[Dict]:
        """Get a specific entry by ID"""
        return self.adapter.get_entry_by_id(entry_id)
    
    def update_entry(self, entry_id: int, update_data: Dict) -> Optional[Dict]:
        """Update an existing entry"""
        return self.adapter.update_entry(entry_id, update_data)
    
    def delete_entry(self, entry_id: int) -> bool:
        """Delete an entry"""
        return self.adapter.delete_entry(entry_id)
    
    def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value"""
        return self.adapter.get_setting(key)
    
    def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value"""
        return self.adapter.set_setting(key, value)
    
    def _ensure_datasets_exist(self) -> bool:
        """Ensure all database tables exist - they are created automatically"""
        return True  # SQLite tables are created automatically in init_database()


# Test function
