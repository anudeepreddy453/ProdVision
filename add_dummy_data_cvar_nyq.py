#!/usr/bin/env python3
"""
Script to add dummy data for CVAR NYQ application for the last 3 months
Excludes weekends (Saturday and Sunday) and ensures no duplicate dates
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta
import random

# Add the current directory to Python path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sharepoint_sqlite_adapter import ProductionEntryManagerWorking
from config import SHAREPOINT_URL

def get_weekday_dates_last_3_months():
    """Get all weekdays (Monday-Friday) from the last 3 months"""
    today = datetime.now()
    three_months_ago = today - timedelta(days=90)
    
    dates = []
    current_date = three_months_ago
    
    while current_date <= today:
        # Check if it's a weekday (Monday=0, Sunday=6)
        if current_date.weekday() < 5:  # Monday to Friday
            dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    
    return dates

def generate_dummy_cvar_nyq_data(date_str):
    """Generate dummy data for CVAR NYQ entry"""
    # Convert date to day name
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    day_name = date_obj.strftime('%A')
    
    # Generate random times (HH:MM format)
    def random_time():
        hour = random.randint(8, 18)  # Business hours
        minute = random.choice([0, 15, 30, 45])
        return f"{hour:02d}:{minute:02d}"
    
    # Generate random status
    def random_status():
        return random.choice(['Red', 'Yellow', 'Green'])
    
    # Generate random quality status
    def random_quality():
        return random.choice(['Red', 'Yellow', 'Green'])
    
    # Generate random PRB and HIIM data
    prb_count = random.randint(0, 2)
    hiim_count = random.randint(0, 2)
    issue_count = random.randint(1, 3)
    
    # Generate issues
    issues = []
    issue_descriptions = [
        "NYQ calculation engine timeout",
        "Market data feed interruption",
        "Risk calculation error",
        "Configuration mismatch",
        "Database query optimization needed",
        "Memory allocation issue",
        "Network connectivity problem",
        "Data validation failure"
    ]
    
    for i in range(issue_count):
        issues.append({
            "description": random.choice(issue_descriptions),
            "remarks": f"NYQ Issue #{i+1} - {random.choice(['Critical', 'High', 'Medium', 'Low'])} priority"
        })
    
    # Generate PRBs
    prbs = []
    for i in range(prb_count):
        prbs.append({
            "prb_id_number": str(random.randint(20000, 29999)),
            "prb_id_status": random.choice(['active', 'closed']),
            "prb_link": f"https://prb.example.com/{random.randint(20000, 29999)}"
        })
    
    # Generate HIIMs
    hiims = []
    for i in range(hiim_count):
        hiims.append({
            "hiim_id_number": str(random.randint(2000, 2999)),
            "hiim_id_status": random.choice(['active', 'closed']),
            "hiim_link": f"https://hiim.example.com/{random.randint(2000, 2999)}"
        })
    
    # Base entry data
    entry_data = {
        "date": date_str,
        "day": day_name,
        "application_name": "CVAR NYQ",
        "prc_mail_text": random_time(),
        "prc_mail_status": random_status(),
        "cp_alerts_text": random_time() if random.random() > 0.4 else "",
        "cp_alerts_status": random_status() if random.random() > 0.4 else "",
        "quality_status": random_quality(),
        "issues": issues,
        "prbs": prbs,
        "hiims": hiims,
        "remarks": f"NYQ production report for {date_str} - {random.choice(['NYQ calculations completed', 'Market data processing successful', 'Risk metrics updated', 'NYQ system stable'])}"
    }
    
    return entry_data

def main():
    """Main function to add dummy data"""
    print("🚀 Starting CVAR NYQ dummy data generation...")
    
    # Initialize entry manager
    entry_manager = ProductionEntryManagerWorking(SHAREPOINT_URL)
    
    # Get all weekdays from last 3 months
    dates = get_weekday_dates_last_3_months()
    print(f"📅 Found {len(dates)} weekdays in the last 3 months")
    
    # Check existing entries to avoid duplicates
    existing_entries = entry_manager.get_all_entries()
    existing_dates = set()
    for entry in existing_entries:
        if entry.get('application_name') == 'CVAR NYQ':
            existing_dates.add(entry.get('date'))
    
    print(f"📊 Found {len(existing_dates)} existing CVAR NYQ entries")
    
    # Filter out existing dates
    new_dates = [date for date in dates if date not in existing_dates]
    print(f"✨ Will create {len(new_dates)} new CVAR NYQ entries")
    
    if not new_dates:
        print("ℹ️  No new entries to create (all dates already exist)")
        return
    
    # Create entries
    success_count = 0
    error_count = 0
    
    for i, date in enumerate(new_dates, 1):
        try:
            print(f"📝 Creating entry {i}/{len(new_dates)} for {date}...")
            
            # Generate dummy data
            entry_data = generate_dummy_cvar_nyq_data(date)
            
            # Create entry
            result = entry_manager.create_entry(entry_data)
            
            if result:
                success_count += 1
                print(f"✅ Successfully created entry for {date}")
            else:
                error_count += 1
                print(f"❌ Failed to create entry for {date}")
                
        except Exception as e:
            error_count += 1
            print(f"❌ Error creating entry for {date}: {str(e)}")
    
    print(f"\n🎉 CVAR NYQ dummy data generation completed!")
    print(f"✅ Successfully created: {success_count} entries")
    print(f"❌ Failed: {error_count} entries")
    print(f"📊 Total entries processed: {len(new_dates)}")

if __name__ == "__main__":
    main()
