"""
ProdVision SQLite + SharePoint Configuration
Production configuration for your SQLite database with SharePoint integration
"""

# Application Configuration
SECRET_KEY = 'prod-secret-key-change-in-production'  # Change this in production!
DEBUG = False  # Set to False for production
HOST = '0.0.0.0'  # Allow external connections for server
PORT = 7070

# SharePoint Configuration
SHAREPOINT_URL = "https://groupsg001.sharepoint.com/sites/CCRTeam/Shared%20Documents/ProdVision"

# Database Configuration
DATABASE_PATH = "./data/prodvision.db"

# Production Server Configuration
SERVER_MODE = True  # Enable server-specific features
SHAREPOINT_SYNC_ENABLED = False  # Disable SharePoint sync

# Instructions:
# 1. The application uses SQLite database stored locally and synced to SharePoint
# 2. Database file: ./data/prodvision.db
# 3. SharePoint sync: Automatic on all database operations (can be disabled)
# 4. For production: Set DEBUG=False and use a proper WSGI server
# 5. For 24/7 operation: Use systemd, supervisor, or similar process manager
