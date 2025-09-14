# Admin Password Change Script

This script allows you to change the admin password for the ProdVision application.

## Usage

### Method 1: Direct execution
```bash
python3 change_admin_password.py
```

### Method 2: Make executable and run
```bash
chmod +x change_admin_password.py
./change_admin_password.py
```

## Requirements

- Python 3.7 or higher
- The ProdVision application must have been run at least once to initialize the database
- You must know the current admin password

## Password Requirements

The new password must meet the following criteria:
- At least 6 characters long
- Maximum 128 characters
- Must contain at least one letter
- Must contain at least one number

## Process

1. The script will prompt you for the current admin password
2. After verification, you'll be asked to enter a new password
3. You'll need to confirm the new password
4. The password will be securely hashed and stored in the database

## Security Notes

- The current password is required for verification
- Passwords are hashed using bcrypt before storage
- The script uses `getpass` to hide password input
- No passwords are stored in plain text

## Troubleshooting

- If you get "No admin password found", run the main application first
- If you get "Current password is incorrect", double-check your current password
- If password validation fails, ensure your new password meets all requirements
