#!/usr/bin/env python3
"""
Script to add dummy data for XVA application for the last 3 months
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

def generate_dummy_xva_data(date_str):
    """Generate dummy data for XVA entry"""
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
        "XVA calculation engine timeout",
        "CVA calculation error",
        "DVA computation failure",
        "FVA calculation issue",
        "KVA computation problem",
        "XVA aggregation error",
        "Counterparty data missing",
        "XVA model validation failure"
    ]
    
    for i in range(issue_count):
        issues.append({
            "description": random.choice(issue_descriptions),
            "remarks": f"XVA Issue #{i+1} - {random.choice(['Critical', 'High', 'Medium', 'Low'])} priority"
        })
    
    # Generate PRBs
    prbs = []
    for i in range(prb_count):
        prbs.append({
            "prb_id_number": str(random.randint(30000, 39999)),
            "prb_id_status": random.choice(['active', 'closed']),
            "prb_link": f"https://prb.example.com/{random.randint(30000, 39999)}"
        })
    
    # Generate HIIMs
    hiims = []
    for i in range(hiim_count):
        hiims.append({
            "hiim_id_number": str(random.randint(3000, 3999)),
            "hiim_id_status": random.choice(['active', 'closed']),
            "hiim_link": f"https://hiim.example.com/{random.randint(3000, 3999)}"
        })
    
    # XVA-specific fields
    root_cause_applications = [
        "XVA Engine", "CVA Calculator", "DVA Processor", "FVA Module",
        "KVA Component", "XVA Aggregator", "Risk Engine", "Pricing System"
    ]
    
    root_cause_types = [
        "Performance Issue", "Data Quality", "Configuration Error",
        "Memory Leak", "Network Timeout", "Calculation Error",
        "Model Validation", "System Integration"
    ]
    
    # Base entry data
    entry_data = {
        "date": date_str,
        "day": day_name,
        "application_name": "XVA",
        "issues": issues,
        "prbs": prbs,
        "hiims": hiims,
        "acq_text": random_time() if random.random() > 0.5 else "",
        "valo_text": random_time(),
        "valo_status": random_status(),
        "sensi_text": random_time(),
        "sensi_status": random_status(),
        "cf_ra_text": random_time(),
        "cf_ra_status": random_status(),
        "quality_legacy": random_quality(),
        "quality_target": random_quality(),
        "root_cause_application": random.choice(root_cause_applications),
        "root_cause_type": random.choice(root_cause_types),
        "xva_remarks": f"XVA production report for {date_str} - {random.choice(['XVA calculations completed successfully', 'CVA/DVA processing finished', 'FVA/KVA computations updated', 'XVA system performance stable'])}"
    }
    
    return entry_data

def main():
    """Main function to add dummy data"""
    print("🚀 Starting XVA dummy data generation...")
    
    # Initialize entry manager
    entry_manager = ProductionEntryManagerWorking(SHAREPOINT_URL)
    
    # Get all weekdays from last 3 months
    dates = get_weekday_dates_last_3_months()
    print(f"📅 Found {len(dates)} weekdays in the last 3 months")
    
    # Check existing entries to avoid duplicates
    existing_entries = entry_manager.get_all_entries()
    existing_dates = set()
    for entry in existing_entries:
        if entry.get('application_name') == 'XVA':
            existing_dates.add(entry.get('date'))
    
    print(f"📊 Found {len(existing_dates)} existing XVA entries")
    
    # Filter out existing dates
    new_dates = [date for date in dates if date not in existing_dates]
    print(f"✨ Will create {len(new_dates)} new XVA entries")
    
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
            entry_data = generate_dummy_xva_data(date)
            
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
    
    print(f"\n🎉 XVA dummy data generation completed!")
    print(f"✅ Successfully created: {success_count} entries")
    print(f"❌ Failed: {error_count} entries")
    print(f"📊 Total entries processed: {len(new_dates)}")

if __name__ == "__main__":
    main()
