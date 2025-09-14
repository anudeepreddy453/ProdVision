#!/usr/bin/env python3
"""
Admin Password Change Script for ProdVision
This script allows changing the admin password for the ProdVision application.
"""

import sys
import getpass
import bcrypt
from sharepoint_sqlite_adapter import ProductionEntryManagerWorking
from config import SHAREPOINT_URL

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    
    # Check for at least one letter and one number
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)
    
    if not has_letter:
        return False, "Password must contain at least one letter"
    
    if not has_number:
        return False, "Password must contain at least one number"
    
    return True, "Password is valid"

def change_admin_password():
    """Change the admin password"""
    print("🔐 ProdVision Admin Password Change")
    print("=" * 40)
    
    try:
        # Initialize database manager
        entry_manager = ProductionEntryManagerWorking(SHAREPOINT_URL)
        
        # Check if admin password exists
        current_password = entry_manager.get_setting('admin_password')
        if not current_password:
            print("❌ Error: No admin password found in database")
            print("Please run the main application first to initialize the database")
            return False
        
        # Get current password for verification
        print("Enter current admin password for verification:")
        current_input = getpass.getpass("Current password: ")
        
        # Verify current password
        if not bcrypt.checkpw(current_input.encode('utf-8'), current_password.encode('utf-8')):
            print("❌ Error: Current password is incorrect")
            return False
        
        print("✅ Current password verified")
        print()
        
        # Get new password
        while True:
            new_password = getpass.getpass("Enter new admin password: ")
            
            # Validate password
            is_valid, message = validate_password(new_password)
            if not is_valid:
                print(f"❌ {message}")
                continue
            
            # Confirm password
            confirm_password = getpass.getpass("Confirm new admin password: ")
            
            if new_password != confirm_password:
                print("❌ Passwords do not match. Please try again.")
                continue
            
            break
        
        # Hash the new password
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # Update password in database
        success = entry_manager.set_setting('admin_password', hashed_password.decode('utf-8'))
        
        if success:
            print("✅ Admin password updated successfully!")
            print("You can now use the new password to log into the ProdVision dashboard.")
            return True
        else:
            print("❌ Error: Failed to update password in database")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Main function"""
    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7.0 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    
    print("Starting password change process...")
    print()
    
    success = change_admin_password()
    
    if success:
        print()
        print("🎉 Password change completed successfully!")
        sys.exit(0)
    else:
        print()
        print("💥 Password change failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
